import zipfile
import os

zip_path = r"C:\Users\ttdcuser\Desktop\BOX_test\uploaad\750_20260707_003010.zip"
extract_dir = "extracted_files"

if not os.path.exists(extract_dir):
    os.makedirs(extract_dir)

with zipfile.ZipFile(zip_path, "r") as zip_ref:
    zip_ref.extractall(extract_dir)

print("解凍が完了しました。")
