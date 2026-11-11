import os
import subprocess
from tqdm import tqdm
from pathlib import PurePosixPath
from paths import phone_dir, phone_dirs
from ppadb.client import Client as AdbClient
from config import IMAGE_EXTS, MEDIA_EXTS, VIDEO_EXTS

phone_dir.mkdir(parents=True, exist_ok=True)

subprocess.run(["adb", "start-server"], capture_output=True, stdin=subprocess.DEVNULL)
adb_client = AdbClient()
connected_devices = adb_client.devices()

if not connected_devices:
    print("No device found, check your connection.")
    exit()

device = connected_devices[0]

def list_files(from_dir):
    shell_output = device.shell(f"find '{from_dir}' -type f -exec stat -c '%s %Y %n' {{}} + 2>/dev/null")
    files = {}
    for line in shell_output.strip().split("\n"):
        parts = line.strip().split(" ", 2)
        if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit():
            if PurePosixPath(parts[2]).suffix.lower() in MEDIA_EXTS:
                files[parts[2]] = (int(parts[0]), int(parts[1]))
    return files

print("Scanning phone...\n")

phone_files = {}

for from_dir in phone_dirs:
    files_in_dir = list_files(from_dir)
    phone_files.update(files_in_dir)
    print(f"{from_dir.name}: {len(files_in_dir)} files found!")
print()

pc_files = {f.name: f for f in phone_dir.rglob("*") if f.suffix.lower() in MEDIA_EXTS}

for phone_path, (_, modified) in phone_files.items():
    name = PurePosixPath(phone_path).name
    if name in pc_files:
        os.utime(pc_files[name], (modified, modified))

phone_images = [f for f in phone_files if PurePosixPath(f).suffix.lower() in IMAGE_EXTS]
phone_videos = [f for f in phone_files if PurePosixPath(f).suffix.lower() in VIDEO_EXTS]

new_images = [f for f in phone_images if PurePosixPath(f).name not in pc_files]
new_videos = [f for f in phone_videos if PurePosixPath(f).name not in pc_files]

files_to_copy = new_images + new_videos
total_size = sum(phone_files[f][0] for f in files_to_copy)

print(f"{len(new_images)}/{len(phone_images)} images are not in {phone_dir}")
print(f"{len(new_videos)}/{len(phone_videos)} videos are not in {phone_dir}\n")

progress = tqdm(total=total_size, unit="B", unit_scale=True, desc="Syncing")
failed_count = 0

for phone_path in files_to_copy:
    size, modified = phone_files[phone_path]
    dest = phone_dir / PurePosixPath(phone_path).name
    temp = dest.with_name(f"{dest.name}.part")
    device.pull(phone_path, str(temp))
    if temp.exists() and temp.stat().st_size == size:
        temp.replace(dest)
        os.utime(dest, (modified, modified))
    else:
        temp.unlink(missing_ok=True)
        failed_count += 1
    progress.update(size)

progress.close()

print(f"Done! {failed_count} files failed, run again to retry them.")
