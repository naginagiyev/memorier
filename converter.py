import shutil
import subprocess
from PIL import Image
from mediainfo import file_hash
from config import CONVERT_TO_JPG, CONVERT_TO_MP4, JPG_QUALITY

def convert_to_jpg(source, temp):
    try:
        with Image.open(source) as img:
            exif = img.getexif()
            profile = img.info.get("icc_profile")
            img.convert("RGB").save(temp, "JPEG", quality=JPG_QUALITY, exif=exif, icc_profile=profile)
        return True
    except Exception:
        temp.unlink(missing_ok=True)
        return False

def convert_to_mp4(source, temp):
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(source), "-map_metadata", "0", "-c", "copy",
           "-movflags", "use_metadata_tags", "-f", "mp4", str(temp)]
    result = subprocess.run(cmd, capture_output=True, stdin=subprocess.DEVNULL)
    if result.returncode != 0:
        temp.unlink(missing_ok=True)
    return result.returncode == 0

def free_path(folder, name, md5):
    base = folder / name
    dest = base
    count = 0
    while dest.exists():
        if file_hash(dest) == md5:
            return None
        count += 1
        dest = folder / f"{base.stem}_{count}{base.suffix}"
    return dest

def place_file(source, folder, md5):
    folder.mkdir(parents=True, exist_ok=True)
    temp = folder / f"{md5}.part"
    suffix = source.suffix.lower()
    name = source.name

    if suffix in CONVERT_TO_JPG and convert_to_jpg(source, temp):
        name = f"{source.stem}.jpg"
    elif suffix in CONVERT_TO_MP4 and convert_to_mp4(source, temp):
        name = f"{source.stem}.mp4"
    else:
        shutil.copy2(source, temp)

    shutil.copystat(source, temp)
    dest = free_path(folder, name, md5)
    if dest is None:
        temp.unlink()
        return False
    temp.replace(dest)
    return True
