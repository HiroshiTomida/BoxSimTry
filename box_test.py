import zipfile
import os
import json
import re

folder = r"C:\Users\ttdcuser\Desktop\BOX_test\uploaad"

# zip_path = r"C:\Users\ttdcuser\Desktop\BOX_test\uploaad\750_20260707_003010.zip"
extract_dir = "extracted_files"

if not os.path.exists(extract_dir):
    os.makedirs(extract_dir, exist_ok=True)

pattern = re.compile(r"^\d+_\d{8}_\d{6}\.zip$")

# 特定の形式のzipファイルを解凍する
for file in os.listdir(folder):
    if pattern.match(file):
        found = True
        zip_path = os.path.join(folder, file)
        
        #zipごとに解凍フォルダを作成
        unzip_dir = os.path.join(extract_dir, file.replace(".zip", ""))
        os.makedirs(unzip_dir, exist_ok=True)
        
        # zipファイル解凍
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(unzip_dir)
        print("解凍が完了しました。")

        # 解凍したフォルダからjsonを探す
        summary_path = os.path.join(unzip_dir, "summary.json")

        if os.path.exists(summary_path):
            # jsonファイルを読み込む
            with open(summary_path, encoding="utf-8") as f:
                data = json.load(f)

            #新しい中身を作成する
            data_new= {
                "file_id": data["file_id"],
                "original_file_name": data["original_file_name"],
                "box_url": "url",
                "updated_datetime": "time"
            }
            print(data_new)

            output_path = os.path.join(r"C:\Users\ttdcuser\Desktop\BOX_test\complete", file.replace(".zip","_result.json"))
            # jsonファイルをcompleteに返す
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data_new, f, ensure_ascii=False, indent=4)
        else:
            print("json形式のファイルが見つかりません。")
if not found:
    print("一致するzipファイルが見つかりません")
