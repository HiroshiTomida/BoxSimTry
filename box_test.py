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
) -> None:
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
        print("json形式のファイルが見つかりません。")
        return

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
    print(data_new)

    # 一時コンプリートフォルダ
    complete_dir = f"{tmp_dir}/temp_complete"
    if not os.path.exists(complete_dir):
        os.makedirs(complete_dir, exist_ok=True)

    save_file_path: str = os.path.join(complete_dir, file.replace(".zip", ".json"))
    # jsonファイルをcompleteに返す
    with open(save_file_path, "w", encoding="utf-8") as f:
        json.dump(data_new, f, ensure_ascii=False, indent=4)

    # ftpサーバ上にコンプリートフォルダ作成
    ftp_complete_path: str = root_path + f"{folder}/complete"
    ftp.make_dirs(ftp_complete_path)

    # ftpサーバー上にアップロード
    ftp.upload(save_file_path, ftp_complete_path)

    # 元ファイル名をcompleteに変更する
    rename_path: str = root_path + f"{folder}/upload/complete_{file}"
    ftp.rename_file(target_path, rename_path)


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
        print(tmp_dir)

        # zipダウンロードディレクトリ
        download_dir: str = f"{tmp_dir}/download_files"
        if not os.path.exists(download_dir):
            os.makedirs(download_dir, exist_ok=True)

        # 検索フォルダ
        search_folders: str = ["s_tltp", "ecam3"]
        for folder in search_folders:
            files = ftp.list_files(f"{folder}/upload", ".zip")

            # ルートパス(階層の一番上)
            root_path: str = os.environ.get("FTP_ROOT_PATH", "/")

            for file in files:
                if not file.startswith("complete_"):
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

    ftp.disconnect()


def main():
    """
    指定時間ごとに処理を繰り返す
    """
    repeat_time_sec: int = 600
    # 指定時間ごとに処理を繰り返す
    while True:
        start_time = time.monotonic()

        box()
        # 経過時間
        elapsed_time = time.monotonic() - start_time
        # 〇秒ごとに処理を繰り返す(処理が長引いた場合はすぐ繰り返す)
        wait_time = max(0, repeat_time_sec - elapsed_time)
        # print(elapsed_time)
        time.sleep(wait_time)


if __name__ == "__main__":
    main()
