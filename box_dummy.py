import json
import logging
import os
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import requests

from ftp_accessor import FtpAccessor


# 日時時刻取得
def get_time() -> str:
    """
    現在日時を取得する(UTC)
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def return_url(zipline_upload_path: str) -> str:
    """
    ZiplineへファイルをアップロードしURLを取得する

    Args:
        zipline_upload_path (str): Ziplineへアップロードするファイルパス

    """
    url = os.environ["ZIPLINE_UPLOAD_URL"]
    headers = {
        "authorization": os.environ["ZIPLINE_AUTHORIZATION"],
        "x-zipline-format": "uuid",
        "x-zipline-original-name": "true",
    }

    with open(zipline_upload_path, "rb") as file:
        files = {"file": file}

        response = requests.post(
            url,
            headers=headers,
            files=files,
            timeout=30,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"Ziplineへのアップロードに失敗しました:{response.status_code}"
            )

        response_data = response.json()
        response_url = response_data["files"][0]["url"]
        response_name = response_data["files"][0]["name"]

    print(f"Ziplineへ{response_name}がアップロードされました")

    return response_url


# zip一つあたりの処理　解凍→json探す→データ作成→結果出力→ファイルリネーム
def __process_zip_file(
    zip_file_name: str,
    download_dir: str,
    tmp_zip_file_path: str,
    ftp,
    tmp_dir: str,
    root_path: str,
    ftp_folder: str,
    target_path: str,
    is_s_tltp: bool,
) -> str:
    """
    zipファイル一つあたりの処理
    解凍→jsonファイル探す→新しいjsonデータ作成→ローカル出力→
    ftpサーバにアップロード→元ファイルリネーム

        Args:
            download_dir (str): ローカル側のダウンロード先ディレクトリ
            zip_file_name (str): ローカルにダウンロードしたzipファイル名
            tmp_zip_file_path (str): ローカル側のファイルごとの一時的なダウンロードパス
            ftp:
            root_path (str): ルートパス
            tmp_dir (str): ローカル側の一時的な処理ディレクトリ
            ftp_folder (str): ftpサーバ上の探索フォルダ名
            target_path (str): ftp上の処理すべきzipファイルパス

    """

    # zipごとに解凍ディレクトリを作成
    # 一時ディレクトリ内に作るので、作りっぱなしでも問題なし
    unzip_dir: str = os.path.join(download_dir, Path(zip_file_name).stem)
    os.makedirs(unzip_dir, exist_ok=True)

    # zip解凍
    with zipfile.ZipFile(tmp_zip_file_path, "r") as zip_ref:
        zip_ref.extractall(unzip_dir)

    # 解凍したディレクトリからjsonを探す
    summary_path: str = os.path.join(unzip_dir, "summary.json")

    if not os.path.exists(summary_path):
        raise FileNotFoundError("summary.jsonがありません")

    # jsonファイルを読み込む
    with open(summary_path, encoding="utf-8") as f:
        data = json.load(f)
        json_reading_time = get_time()

    file_id = data["file_id"]
    original_file_name = data["original_file_name"]

    if is_s_tltp:
        zipline_upload_path = None
        for root, dirs, files in os.walk(unzip_dir):
            for f in files:
                if f != "summary.json":
                    zipline_upload_path = os.path.join(root, f)
                    break

    else:
        zip_files_path = []
        # summary.json以外のファイルパスを集める
        for root, dirs, files in os.walk(unzip_dir):
            for f in files:
                if f != "summary.json":
                    zip_files_path.append(os.path.join(root, f))

        # Ziplineへ送るzipファイルを作る
        zipline_upload_path = os.path.join(unzip_dir, zip_file_name)
        with zipfile.ZipFile(zipline_upload_path, "w", zipfile.ZIP_DEFLATED) as zip_ref:
            for upload_file_path in zip_files_path:
                zip_ref.write(
                    upload_file_path, os.path.relpath(upload_file_path, unzip_dir)
                )

    zipline_upload_url = return_url(
        str(zipline_upload_path)
    )  # os.path.joinはstr | None型だが、ここではNoneになることはない

    # 新しい中身を作成する
    data_new = {
        "file_id": file_id,
        "original_file_name": original_file_name,
        "box_url": zipline_upload_url,
        "updated_datetime": json_reading_time,
    }

    ftp_upload(
        tmp_dir,
        zip_file_name,
        root_path,
        ftp_folder,
        ftp,
        target_path,
        data_new,
        "complete",
    )

    print("[完了]")
    print("-" * 70)

    return summary_path


def ftp_upload(
    tmp_dir: str,
    zip_file_name: str,
    root_path: str,
    ftp_folder: str,
    ftp,
    target_path: str,
    json_data: dict,
    result_type: str,
) -> None:
    """
    .jsonをftpサーバにアップロードするまでの処理

    Args:
        tmp_dir (str): ローカル側の一時的な処理ディレクトリ
        zip_file_name (str): ローカルにダウンロードしたzipファイル名
        root_path (str): ルートパス
        ftp_folder (str): ftpサーバ上の探索フォルダ名
        ftp
        target_path (str): ftp上の処理すべきzipファイルパス
        json_data (dict) :新しく作成した.jsonの中身
        result_type (str): complete/errorのどちらの場合か
    """

    # 一時jsonフォルダ
    temp_json_dir = f"{tmp_dir}/temp_{result_type}"
    if not os.path.exists(temp_json_dir):
        os.makedirs(temp_json_dir, exist_ok=True)

    save_file_path: str = os.path.join(
        temp_json_dir, Path(zip_file_name).with_suffix(".json")
    )
    # jsonファイルをcomplete/errorに返す
    with open(save_file_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=4)

    # ftpサーバ上にcomplete/errorフォルダ作成
    ftp_folder_path: str = root_path + f"{ftp_folder}/{result_type}"
    ftp.make_dirs(ftp_folder_path)

    # ftpサーバー上にアップロード
    ftp.upload(save_file_path, ftp_folder_path)

    # 元ファイル名をcomplete/errorに変更する
    rename_path: str = root_path + f"{ftp_folder}/upload/{result_type}_{zip_file_name}"
    ftp.rename_file(target_path, rename_path)


def handle_error(
    tmp_dir: str,
    zip_file_name: str,
    is_s_tltp: bool,
    root_path: str,
    ftp_folder: str,
    ftp,
    target_path: str,
) -> None:
    """
    .jsonを作るときのエラー処理

        Args:
            tmp_dir (str): ローカル側の一時的な処理ディレクトリ
            zip_file_name (str): ローカルにダウンロードしたzipファイル名
            is_s_tltp (bool): s_tltpフォルダの処理を行っているか
            root_path (str): ルートパス
            ftp_folder (str): ftpサーバ上の探索フォルダ名
            ftp:
            target_path (str): ftp上の処理すべきzipファイルパス

    """

    err_time = get_time()

    # もしsummary.jsonがなかったら
    # s_tltp
    if is_s_tltp:
        err_data = {
            "file_id": zip_file_name.split("_")[0],
            "original_file_name": "",
            "err_description": "",
            "err_datetime": err_time,
        }

    # ecam3
    elif is_s_tltp == False:
        err_data = {
            "file_id": "",
            "original_file_name": "",
            "err_description": "",
            "err_datetime": err_time,
        }

    ftp_upload(
        tmp_dir,
        zip_file_name,
        root_path,
        ftp_folder,
        ftp,
        target_path,
        err_data,
        "error",
    )
    print(f"errorフォルダに{Path(zip_file_name).with_suffix(".json")}を追加しました")
    print("-" * 70)


# main関数
def upload_to_box() -> None:
    """
    ftpサーバに接続し、ftpサーバからダウンロードしてアップロードするまでの一連の処理を行い、
    ftpサーバとの接続を切断する
    """
    ftp = FtpAccessor()
    # ftpサーバーと接続
    if not ftp.connect():
        print("接続失敗")
        return

    # 一時フォルダ置き場(withを抜けたら削除される)
    with tempfile.TemporaryDirectory() as tmp_dir:

        # zipダウンロードディレクトリ
        download_dir: str = f"{tmp_dir}/download_files"
        if not os.path.exists(download_dir):
            os.makedirs(download_dir, exist_ok=True)

        is_s_tltp: bool = True
        # 検索フォルダ
        search_folders = ["s_tltp", "ecam3"]

        for ftp_folder in search_folders:
            print(f"【{ftp_folder}】")

            # uploadフォルダが存在するか確認
            if not ftp.directory_exists(f"{ftp_folder}/upload"):
                print(f"{ftp_folder}/uploadは存在しません")
                is_s_tltp = False
                continue

            # uploadフォルダが存在する場合だけファイル一覧を取得
            files = ftp.list_files(f"{ftp_folder}/upload", ".zip")

            if not files:
                print(f"{ftp_folder}/uploadにzipファイルがありません")
                is_s_tltp = False
                continue

            # ルートパス(階層の一番上)
            root_path: str = os.environ.get("FTP_ROOT_PATH", "/")

            has_unprocessed_zip: bool = False

            for zip_file_name in files:
                if zip_file_name.startswith(("complete_", "error_")):
                    continue

                has_unprocessed_zip = True

                try:
                    print(f"{zip_file_name}の処理を開始")
                    target_path: str = (
                        root_path + f"{ftp_folder}/upload/{zip_file_name}"
                    )
                    zip_data = ftp.download_bytes(target_path)

                    tmp_zip_file_path: str = os.path.join(download_dir, zip_file_name)
                    with open(tmp_zip_file_path, "wb") as f:
                        f.write(zip_data)

                    __process_zip_file(
                        zip_file_name,
                        download_dir,
                        tmp_zip_file_path,
                        ftp,
                        tmp_dir,
                        root_path,
                        ftp_folder,
                        target_path,
                        is_s_tltp,
                    )

                except Exception as e:
                    logger = logging.getLogger("example")
                    logger.exception(
                        f"[エラー]{zip_file_name}の処理中にエラーが発生しました"
                    )
                    handle_error(
                        tmp_dir,
                        zip_file_name,
                        is_s_tltp,
                        root_path,
                        ftp_folder,
                        ftp,
                        target_path,
                    )

            is_s_tltp = False
            if has_unprocessed_zip:
                print(f"{ftp_folder}の処理が完了しました")
            else:
                print(f"{ftp_folder}に未処理のzipファイルがありません")
                print("-" * 70)

    ftp.disconnect()


def main():
    """
    指定時間ごとに処理を繰り返す
    """
    repeat_time_sec: int = 600
    # 指定時間ごとに処理を繰り返す
    while True:
        start_time = time.monotonic()
        print("=" * 70)
        print("処理を開始します")

        upload_to_box()
        # 経過時間
        elapsed_time = time.monotonic() - start_time
        # 〇秒ごとに処理を繰り返す(処理が長引いた場合はすぐ繰り返す)
        wait_time = max(0, repeat_time_sec - elapsed_time)
        # print(elapsed_time)
        print("処理を終了しました")
        print("=" * 70)

        time.sleep(wait_time)


if __name__ == "__main__":
    main()
