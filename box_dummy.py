import json
import os
import tempfile
import time
import zipfile
from datetime import datetime, timezone

from ftp_accessor import FtpAccessor


# 日時時刻取得
def get_time() -> str:
    """
    現在日時を取得する(UTC)
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# zip一つあたりの処理　解凍→json探す→データ作成→結果出力→ファイルリネーム
def process_zip_file(
    file: str,
    download_dir: str,
    tmp_zip_file_path: str,
    ftp,
    tmp_dir: str,
    root_path: str,
    folder: str,
    target_path: str,
) -> str:
    """
    zipファイル一つあたりの処理
    解凍→jsonファイル探す→新しいjsonデータ作成→ローカル出力→
    ftpサーバにアップロード→元ファイルリネーム

        Args:
            download_dir (str): ローカル側のダウンロード先ディレクトリ
            file (str): ローカルにダウンロードしたzipファイル名
            tmp_zip_file_path (str): ローカル側のファイルごとの一時的なダウンロードパス
            ftp:
            root_path (str): ルートパス
            tmp_dir (str): ローカル側の一時的な処理ディレクトリ
            folder (str): ftpサーバ上の探索フォルダ名
            target_path (str): ftp上の処理すべきzipファイルパス

    """

    # zipごとに解凍フォルダを作成
    unzip_dir: str = os.path.join(download_dir, file.replace(".zip", ""))
    os.makedirs(unzip_dir, exist_ok=True)

    # zip解凍
    with zipfile.ZipFile(tmp_zip_file_path, "r") as zip_ref:
        zip_ref.extractall(unzip_dir)
    # print("解凍が完了しました。")

    # 解凍したフォルダからjsonを探す
    summary_path: str = os.path.join(unzip_dir, "summary.json")

    if not os.path.exists(summary_path):
        print(f"{file}" + "にsummary.jsonが見つかりません")
        raise FileNotFoundError("summary.jsonがありません")

    # jsonファイルを読み込む
    with open(summary_path, encoding="utf-8") as f:
        data = json.load(f)
        json_reading_time = get_time()

    # 新しい中身を作成する
    data_new = {
        "file_id": data["file_id"],
        "original_file_name": data["original_file_name"],
        "box_url": "https://www.google.co.jp",
        "updated_datetime": json_reading_time,
    }
    # print(data_new)

    ftp_upload(
        tmp_dir,
        file,
        root_path,
        folder,
        ftp,
        target_path,
        data_new,
        "complete",
    )

    print(f"{file}" + "の処理が完了しました")

    return summary_path


def ftp_upload(
    tmp_dir, file, root_path, folder, ftp, target_path, json_data, result_type
) -> None:
    """
    .jsonをftpサーバにアップロードするまでの処理

    Args:
        tmp_dir (str): ローカル側の一時的な処理ディレクトリ
        file (str): ローカルにダウンロードしたzipファイル名
        root_path (str): ルートパス
        folder (str): ftpサーバ上の探索フォルダ名
        ftp
        target_path (str): ftp上の処理すべきzipファイルパス
        json_data :新しく作成した.jsonの中身
        result_type (str): complete/errorのどちらの場合か
    """

    # 一時jsonフォルダ
    temp_json_dir = f"{tmp_dir}/temp_{result_type}"
    if not os.path.exists(temp_json_dir):
        os.makedirs(temp_json_dir, exist_ok=True)

    save_file_path: str = os.path.join(temp_json_dir, file.replace(".zip", ".json"))
    # jsonファイルをcomplete/errorに返す
    with open(save_file_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=4)

    # ftpサーバ上にcomplete/errorフォルダ作成
    ftp_folder_path: str = root_path + f"{folder}/{result_type}"
    ftp.make_dirs(ftp_folder_path)

    # ftpサーバー上にアップロード
    ftp.upload(save_file_path, ftp_folder_path)

    # 元ファイル名をcomplete/errorに変更する
    rename_path: str = root_path + f"{folder}/upload/{result_type}_{file}"
    ftp.rename_file(target_path, rename_path)


def error(
    tmp_dir: str,
    file: str,
    is_s_tltp: bool,
    root_path: str,
    folder: str,
    ftp,
    target_path: str,
) -> None:
    """
    .jsonを作るときのエラー処理

        Args:
            tmp_dir (str): ローカル側の一時的な処理ディレクトリ
            file (str): ローカルにダウンロードしたzipファイル名
            is_s_tltp (bool): s_tltpフォルダの処理を行っているか
            root_path (str): ルートパス
            folder (str): ftpサーバ上の探索フォルダ名
            ftp:
            target_path (str): ftp上の処理すべきzipファイルパス

    """

    err_time = get_time()

    # もしsummary.jsonがなかったら
    # s_tltpのとき
    if is_s_tltp:
        err_data = {
            "file_id": file.split("_")[0],
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

    ftp_upload(tmp_dir, file, root_path, folder, ftp, target_path, err_data, "error")
    print("errorフォルダに" + file.replace(".zip", ".json") + "を追加しました")


# main関数
def box() -> None:
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
        # print("一時フォルダを作成しました")

        # zipダウンロードディレクトリ
        download_dir: str = f"{tmp_dir}/download_files"
        if not os.path.exists(download_dir):
            os.makedirs(download_dir, exist_ok=True)

        is_s_tltp: bool = True
        # 検索フォルダ
        search_folders = ["s_tltp", "ecam3"]
        for folder in search_folders:
            print(f"{folder}" + "の処理を行います")
            files = ftp.list_files(f"{folder}/upload", ".zip")
            if not files:
                print(f"{folder}" + "は存在しません")
                is_s_tltp = False
                continue

            # ルートパス(階層の一番上)
            root_path: str = os.environ.get("FTP_ROOT_PATH", "/")

            for file in files:
                if file.startswith(("complete_", "error_")):
                    continue
                try:
                    target_path: str = root_path + f"{folder}/upload/{file}"
                    zip_data = ftp.download_bytes(target_path)

                    tmp_zip_file_path: str = os.path.join(download_dir, file)
                    with open(tmp_zip_file_path, "wb") as f:
                        f.write(zip_data)

                    process_zip_file(
                        file,
                        download_dir,
                        tmp_zip_file_path,
                        ftp,
                        tmp_dir,
                        root_path,
                        folder,
                        target_path,
                    )

                except Exception as ex:
                    error(tmp_dir, file, is_s_tltp, root_path, folder, ftp, target_path)

            is_s_tltp = False
            print(f"{folder}" + "の処理が完了しました")

    ftp.disconnect()


def main():
    """
    指定時間ごとに処理を繰り返す
    """
    repeat_time_sec: int = 600
    # 指定時間ごとに処理を繰り返す
    while True:
        start_time = time.monotonic()
        print("処理を開始します")

        box()
        # 経過時間
        elapsed_time = time.monotonic() - start_time
        # 〇秒ごとに処理を繰り返す(処理が長引いた場合はすぐ繰り返す)
        wait_time = max(0, repeat_time_sec - elapsed_time)
        # print(elapsed_time)
        print("処理を終了しました")
        time.sleep(wait_time)


if __name__ == "__main__":
    main()
