import zipfile
import os
import json

zip_path = r"C:\Users\ttdcuser\Desktop\BOX_test\uploaad\750_20260707_003010.zip"
extract_dir = "extracted_files"

if not os.path.exists(extract_dir):
    os.makedirs(extract_dir)

# zipファイル解凍
with zipfile.ZipFile(zip_path, "r") as zip_ref:
    zip_ref.extractall(extract_dir)

print("解凍が完了しました。")

# jsonファイルを読み込む
with open(r"C:\usr\takezawa\BoxSimTry\extracted_files\summary.json", encoding="utf-8") as f:
     data = json.load(f)
print(data)

# 新しい中身を作成する
data_new= {
    "file_id": data["file_id"],
    "original_file_name": data["original_file_name"],
    "box_url": "url",
    "updated_datetime": "time"
}
print(data_new)

# jsonファイルをcompleteに返す
with open(r"C:\Users\ttdcuser\Desktop\BOX_test\complete\result.json", "w", encoding="utf-8") as f:
    json.dump(data_new, f, ensure_ascii=False, indent=4)

