import json
import os
import re
import zipfile
from datetime import datetime

from ftp_accessor import FtpAccessor


# 日時時刻取得
def get_time():
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")  # noqa: DTZ005


# # 特定の形式のzipファイルを解凍する
# def searchzip(files, pattern):
#     zip_files = []
#     for file in files:
#         if pattern.match(file):
#             zip_files.append(file)
#     return zip_files


# # zipファイル解凍
# def zipTounzip(temp_zip, unzip_dir):
#     with zipfile.ZipFile(temp_zip, "r") as zip_ref:
#         zip_ref.extractall(unzip_dir)
#     print("解凍が完了しました。")


# zip一つあたりの処理　解凍→json探す→データ作成→結果出力
def proccess_zip(file, extract_dir, temp_zip, ftp):
    # zip_path = os.path.join(upload_folder, file)

    # zipごとに解凍フォルダを作成
    unzip_dir = os.path.join(extract_dir, file.replace(".zip", ""))
    os.makedirs(unzip_dir, exist_ok=True)

    # zip解凍
    with zipfile.ZipFile(temp_zip, "r") as zip_ref:
        zip_ref.extractall(unzip_dir)
    print("解凍が完了しました。")

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

    complete_dir = "temp_complete"
    if not os.path.exists(complete_dir):
        os.makedirs(complete_dir, exist_ok=True)

    save_file_path = os.path.join(complete_dir, file.replace(".zip", "_result.json"))
    # jsonファイルをcompleteに返す
    with open(save_file_path, "w", encoding="utf-8") as f:
        json.dump(data_new, f, ensure_ascii=False, indent=4)

    ftp.upload(save_file_path, "/complete")


# main関数
def main():
    ftp = FtpAccessor()
    # ftpサーバーと接続
    if not ftp.connect():
        print("接続失敗")
        return

    extract_dir = "extracted_files"

    if not os.path.exists(extract_dir):
        os.makedirs(extract_dir, exist_ok=True)

    files = ftp.list_files("/upload", ".zip")

    pattern = re.compile(r"^\d+_\d{8}_\d{6}\.zip$")

    for file in files:
        if pattern.match(file):
            target_path = f"/upload/{file}"
            zip_data = ftp.download_bytes(target_path)

            temp_zip = os.path.join(extract_dir, file)

            with open(temp_zip, "wb") as f:
                f.write(zip_data)

            proccess_zip(file, extract_dir, temp_zip, ftp)
    # upload_folder = r"C:\Users\ttdcuser\Desktop\BOX_test\upload"
    # complete_folder = r"C:\Users\ttdcuser\Desktop\BOX_test\complete"

    # zip_path = r"C:\Users\ttdcuser\Desktop\BOX_test\upload\750_20260707_003010.zip"
    # zip_files = searchzip(files, pattern)

    # if not zip_files:
    #     print("一致するzipファイルが見つかりません")
    #     return

    # for file in zip_files:
    #     proccess_zip(upload_folder, file, extract_dir, complete_folder)

    ftp.disconnect()


if __name__ == "__main__":
    main()
