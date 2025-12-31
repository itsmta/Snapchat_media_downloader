import json
import os
import urllib.request
from datetime import datetime
import zipfile
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

JSON_FILE = "./memories_history.json"
OUTPUT_DIR = "./downloads"

os.makedirs(OUTPUT_DIR, exist_ok=True)

existing_files = set(os.listdir(OUTPUT_DIR))
files_lock = Lock()

MAX_WORKERS = 6 


def base_name(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S UTC")
    return dt.strftime("%Y-%m-%d_%H-%M-%S")


def unique_name(base, suffix, ext):
    with files_lock:
        i = 1
        name = f"{base}_{suffix}{ext}"
        while name in existing_files:
            i += 1
            name = f"{base}_{i:02d}_{suffix}{ext}"
        existing_files.add(name)
        return name


def process_item(item):
    date_str = item.get("Date")
    url = item.get("Media Download Url")
    media_type = item.get("Media Type", "").lower()

    if not date_str or not url:
        return

    base = base_name(date_str)
    zip_path = os.path.join(OUTPUT_DIR, f"{base}.zip")

    print(f"Downloading {base}")

    try:
        urllib.request.urlretrieve(url, zip_path)

        if zipfile.is_zipfile(zip_path):
            temp_dir = zip_path + "_unzipped"
            os.makedirs(temp_dir, exist_ok=True)

            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(temp_dir)

            os.remove(zip_path)

            for f in os.listdir(temp_dir):
                if f.startswith("._"):
                    continue

                src = os.path.join(temp_dir, f)
                lf = f.lower()

                if lf.endswith(".png"):
                    out = unique_name(base, "caption", ".png")
                elif lf.endswith(".jpg"):
                    out = unique_name(base, "image", ".jpg")
                elif lf.endswith(".mp4"):
                    out = unique_name(base, "video", ".mp4")
                else:
                    continue

                shutil.move(src, os.path.join(OUTPUT_DIR, out))

            shutil.rmtree(temp_dir)

        else:
            ext = ".mp4" if media_type == "video" else ".jpg"
            out = unique_name(base, "media", ext)
            shutil.move(zip_path, os.path.join(OUTPUT_DIR, out))

    except Exception as e:
        print(f"Failed {base}: {e}")


# ---- Main ----

with open(JSON_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

media_items = data.get("Saved Media", [])

with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    futures = [executor.submit(process_item, item) for item in media_items]

    for f in as_completed(futures):
        pass

print("Snapchat memories download complete (concurrent, no skips)")
