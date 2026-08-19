import json
import os
import re
import tempfile
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
def proccess_zip(file, extract_dir, temp_zip, ftp, tmp_dir, root_path, list):
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

    # 一時コンプリートフォルダ
    complete_dir = f"{tmp_dir}/temp_complete"
    if not os.path.exists(complete_dir):
        os.makedirs(complete_dir, exist_ok=True)

    save_file_path = os.path.join(complete_dir, file.replace(".zip", "_result.json"))
    # jsonファイルをcompleteに返す
    with open(save_file_path, "w", encoding="utf-8") as f:
        json.dump(data_new, f, ensure_ascii=False, indent=4)

    # ftpサーバ上にコンプリートフォルダ作成
    complete_path = root_path + f"{list}/complete"
    ftp.make_dirs(complete_path)

    # ftpサーバー上にアップロード
    ftp.upload(save_file_path, complete_path)


# main関数
def main():

    ftp = FtpAccessor()
    # ftpサーバーと接続
    if not ftp.connect():
        print("接続失敗")
        return

    # 一時フォルダ置き場(withを抜けたら削除される)
    with tempfile.TemporaryDirectory() as tmp_dir:
        print(tmp_dir)

        # zipダウンロードディレクトリ
        extract_dir = f"{tmp_dir}/extracted_files"

        if not os.path.exists(extract_dir):
            os.makedirs(extract_dir, exist_ok=True)

        # 検索フォルダ
        serch_folders = ["s_tltp", "ecam3"]

        for list in serch_folders:

            files = ftp.list_files(f"{list}/upload", ".zip")

            # ルートパス(階層の一番上)
            root_path = os.environ.get("FTP_ROOT_PATH", "/")

            for file in files:
                if not file.startswith("complete_"):
                    target_path = root_path + f"{list}/upload/{file}"
                    zip_data = ftp.download_bytes(target_path)

                    temp_zip = os.path.join(extract_dir, file)

                    with open(temp_zip, "wb") as f:
                        f.write(zip_data)

                    proccess_zip(
                        file, extract_dir, temp_zip, ftp, tmp_dir, root_path, list
                    )

                    # 元ファイル名をcompleteに変更する
                    rename_path = root_path + f"{list}/upload/complete_{file}"
                    ftp.rename_file(target_path, rename_path)

    ftp.disconnect()


if __name__ == "__main__":
    main()
