import json
import os
import re
import tempfile
import time
import zipfile
from datetime import datetime

from ftp_accessor import FtpAccessor


# 日時時刻取得
def get_time():
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")  # noqa: DTZ005


# zip一つあたりの処理　解凍→json探す→データ作成→結果出力→ファイルリネーム
def process_zip_file(
    file, download_dir, temp_zip, ftp, tmp_dir, root_path, folder, target_path
):

    # zipごとに解凍フォルダを作成
    unzip_dir = os.path.join(download_dir, file.replace(".zip", ""))
    os.makedirs(unzip_dir, exist_ok=True)

    # zip解凍
    with zipfile.ZipFile(temp_zip, "r") as zip_ref:
        zip_ref.extractall(unzip_dir)
    # print("解凍が完了しました。")

    # 解凍したフォルダからjsonを探す
    summary_path = os.path.join(unzip_dir, "summary.json")

    if not os.path.exists(summary_path):
        print("json形式のファイルが見つかりません。")
        return

    # jsonファイルを読み込む
    with open(summary_path, encoding="utf-8") as f:
        data = json.load(f)
        time = get_time()

    # 新しい中身を作成する
    data_new = {
        "file_id": data["file_id"],
        "original_file_name": data["original_file_name"],
        "box_url": "url",
        "updated_datetime": time,
    }
    print(data_new)

    # 一時コンプリートフォルダ
    complete_dir = f"{tmp_dir}/temp_complete"
    if not os.path.exists(complete_dir):
        os.makedirs(complete_dir, exist_ok=True)

    save_file_path = os.path.join(complete_dir, file.replace(".zip", "_result.json"))
    # jsonファイルをcompleteに返す
    with open(save_file_path, "w", encoding="utf-8") as f:
        json.dump(data_new, f, ensure_ascii=False, indent=4)

    # ftpサーバ上にコンプリートフォルダ作成
    complete_path = root_path + f"{folder}/complete"
    ftp.make_dirs(complete_path)

    # ftpサーバー上にアップロード
    ftp.upload(save_file_path, complete_path)

    # 元ファイル名をcompleteに変更する
    rename_path = root_path + f"{folder}/upload/complete_{file}"
    ftp.rename_file(target_path, rename_path)


# main関数
def box():

    ftp = FtpAccessor()
    # ftpサーバーと接続
    if not ftp.connect():
        print("接続失敗")
        return

    # 一時フォルダ置き場(withを抜けたら削除される)
    with tempfile.TemporaryDirectory() as tmp_dir:
        print(tmp_dir)

        # zipダウンロードディレクトリ
        download_dir = f"{tmp_dir}/download_files"
        if not os.path.exists(download_dir):
            os.makedirs(download_dir, exist_ok=True)

        # 検索フォルダ
        search_folders = ["s_tltp", "ecam3"]
        for folder in search_folders:
            files = ftp.list_files(f"{folder}/upload", ".zip")

            # ルートパス(階層の一番上)
            root_path = os.environ.get("FTP_ROOT_PATH", "/")

            for file in files:
                if not file.startswith("complete_"):
                    target_path = root_path + f"{folder}/upload/{file}"
                    zip_data = ftp.download_bytes(target_path)

                    temp_zip = os.path.join(download_dir, file)
                    with open(temp_zip, "wb") as f:
                        f.write(zip_data)

                    process_zip_file(
                        file,
                        download_dir,
                        temp_zip,
                        ftp,
                        tmp_dir,
                        root_path,
                        folder,
                        target_path,
                    )

    ftp.disconnect()


def main():
    repeat_time = 10
    # 指定時間ごとに処理を繰り返す
    while True:
        start_time = time.monotonic()

        box()
        # 経過時間
        elapsed_time = time.monotonic() - start_time
        # 〇秒ごとに処理を繰り返す(処理が長引いた場合はすぐ繰り返す)
        wait_time = max(0, repeat_time - elapsed_time)
        # print(elapsed_time)
        time.sleep(wait_time)


if __name__ == "__main__":
    main()
