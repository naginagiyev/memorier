import re
import json
import hashlib
import imagehash
import subprocess
import numpy as np
from io import BytesIO
from config import VIDEO_EXTS
from PIL.ExifTags import Base, IFD
from pillow_heif import register_heif_opener
from PIL import Image, ImageOps, UnidentifiedImageError

Image.MAX_IMAGE_PIXELS = None
register_heif_opener()

def read_exif(img):
    try:
        exif = img.getexif()
        details = exif.get_ifd(IFD.Exif)
        dates = [
            details.get(Base.DateTimeOriginal),
            details.get(Base.DateTimeDigitized),
            exif.get(Base.DateTime),
        ]
        camera = bool(exif.get(Base.Make) or exif.get(Base.Model))
        return [date for date in dates if date], camera
    except Exception:
        return [], False

def read_xmp_date(img):
    xmp = img.info.get("XML:com.adobe.xmp") or img.info.get("xmp") or ""
    match = re.search(r"DateTimeOriginal[>=\"]+([\d:-]{10})", str(xmp))
    return [match.group(1)] if match else []

def upright_view(img, side):
    img.draft("RGB", (side, side))
    img.load()
    try:
        view = ImageOps.exif_transpose(img)
    except Exception:
        view = img
    view = view.convert("RGB")
    view.thumbnail((side, side))
    return view

def load_image(path, side):
    with Image.open(path) as img:
        return upright_view(img, side)

def read_image(path):
    try:
        with Image.open(path) as img:
            width, height = img.size
            view = upright_view(img, 512)
            dates, camera = read_exif(img)
            dates += read_xmp_date(img)
    except (OSError, ValueError, SyntaxError, UnidentifiedImageError):
        return None

    gray = np.asarray(view.convert("L"), dtype=np.float32)
    edges = gray[:-2, 1:-1] + gray[2:, 1:-1] + gray[1:-1, :-2] + gray[1:-1, 2:]
    edges = edges - 4 * gray[1:-1, 1:-1]
    return {
        "width": width,
        "height": height,
        "dates": dates,
        "camera": camera,
        "phash": str(imagehash.phash(view)),
        "blur": float(edges.var()) if edges.size else 0.0,
        "brightness": float(gray.mean()),
    }

def probe_video(path):
    cmd = ["ffprobe", "-v", "error", "-show_entries",
           "format=duration:format_tags:stream=width,height:stream_tags=creation_time",
           "-of", "json", str(path)]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                            errors="replace", stdin=subprocess.DEVNULL)
    try:
        data = json.loads(result.stdout)
    except (TypeError, ValueError):
        data = {}

    video_format = data.get("format", {})
    tags = video_format.get("tags", {})
    streams = [stream for stream in data.get("streams", []) if stream.get("width")]
    dates = [tags.get("com.apple.quicktime.creationdate"), tags.get("creation_time"),
             tags.get("date")]
    dates += [stream.get("tags", {}).get("creation_time") for stream in streams]
    try:
        duration = float(video_format["duration"])
    except (KeyError, ValueError):
        duration = None

    return {
        "width": streams[0]["width"] if streams else None,
        "height": streams[0].get("height") if streams else None,
        "duration": duration,
        "dates": [date for date in dates if date],
        "camera": any("make" in key.lower() or "com.android" in key.lower() for key in tags),
    }

def has_camera(path):
    if path.suffix.lower() in VIDEO_EXTS:
        return probe_video(path)["camera"]
    try:
        with Image.open(path) as img:
            return read_exif(img)[1]
    except (OSError, ValueError, SyntaxError, UnidentifiedImageError):
        return False

def file_hash(path):
    digest = hashlib.md5()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def frame_hashes(path, duration):
    hashes = []
    for share in (0.1, 0.5, 0.9):
        cmd = ["ffmpeg", "-v", "error", "-ss", str(duration * share), "-i", str(path),
               "-frames:v", "1", "-vf", "scale=256:-2", "-f", "image2pipe", "-c:v", "png", "-"]
        result = subprocess.run(cmd, capture_output=True, stdin=subprocess.DEVNULL)
        if result.returncode != 0 or not result.stdout:
            return []
        with Image.open(BytesIO(result.stdout)) as frame:
            hashes.append(str(imagehash.phash(frame)))
    return hashes
