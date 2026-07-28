import zipfile
import os
import json
import re
from datetime import datetime

#日時時刻取得
def get_time():
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

# 特定の形式のzipファイルを解凍する    
def searchzip(upload_folder, pattern):
    zip_files = []
    for f in os.listdir(upload_folder):
        if pattern.match(f):
            zip_files.append(f)
    return zip_files

# zipファイル解凍
def zipTounzip(zip_path, unzip_dir):
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(unzip_dir)
    print("解凍が完了しました。")

#zip一つあたりの処理　解凍→json探す→データ作成→結果出力
def proccess_zip(upload_folder, file, extract_dir, complete_folder):
    zip_path = os.path.join(upload_folder, file)
    
    #zipごとに解凍フォルダを作成
    unzip_dir = os.path.join(extract_dir, file.replace(".zip", ""))
    os.makedirs(unzip_dir, exist_ok=True)
    
    #zip解凍
    zipTounzip(zip_path, unzip_dir)

    # 解凍したフォルダからjsonを探す
    summary_path = os.path.join(unzip_dir, "summary.json")

    if not os.path.exists(summary_path):
        print("json形式のファイルが見つかりません。")
        return

    # jsonファイルを読み込む
    with open(summary_path, encoding="utf-8") as f:
        data = json.load(f)
        time = get_time()

    #新しい中身を作成する
    data_new= {
        "file_id": data["file_id"],
        "original_file_name": data["original_file_name"],
        "box_url": "url",
        "updated_datetime": time
    }
    print(data_new)

    output_path = os.path.join(complete_folder, file.replace(".zip","_result.json"))
    # jsonファイルをcompleteに返す
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data_new, f, ensure_ascii=False, indent=4)

#main関数
def main():
    upload_folder= r"C:\Users\ttdcuser\Desktop\BOX_test\upload"
    complete_folder= r"C:\Users\ttdcuser\Desktop\BOX_test\complete"

    # zip_path = r"C:\Users\ttdcuser\Desktop\BOX_test\upload\750_20260707_003010.zip"
    extract_dir = "extracted_files"
    pattern = re.compile(r"^\d+_\d{8}_\d{6}\.zip$")
    found = False
    
    if not os.path.exists(extract_dir):
        os.makedirs(extract_dir, exist_ok=True)
    
    zip_files = searchzip(upload_folder, pattern)

    if not zip_files:
        print("一致するzipファイルが見つかりません")
        return

    for file in zip_files:
        proccess_zip(upload_folder, file, extract_dir, complete_folder)     
        
if __name__ == "__main__":
    main()