import sys
import shutil
from tqdm import tqdm
from pathlib import Path
from paths import pc_from_dir, pc_to_dir
from config import IMAGE_EXTS, MEDIA_EXTS, VIDEO_EXTS

def scan_media(directory: Path) -> dict[str, Path]:
    found: dict[str, Path] = {}
    all_files = [p for p in directory.rglob("*") if p.is_file()]
    for path in tqdm(all_files, desc="Scanning", unit="file"):
        if path.suffix.lower() in MEDIA_EXTS:
            key = path.name.lower()
            if key not in found:
                found[key] = path
    return found

def sync(from_dir: Path, to_dir: Path) -> None:
    if not from_dir.is_dir():
        sys.exit(f"[ERROR] from_dir does not exist or is not a directory: {from_dir}")
    if not to_dir.is_dir():
        sys.exit(f"[ERROR] to_dir does not exist or is not a directory: {to_dir}")

    from_files = scan_media(from_dir)
    to_files = scan_media(to_dir)

    missing_keys = set(from_files.keys()) - set(to_files.keys())
    missing_images = [k for k in missing_keys if from_files[k].suffix.lower() in IMAGE_EXTS]
    missing_videos = [k for k in missing_keys if from_files[k].suffix.lower() in VIDEO_EXTS]

    print(f"Found {len(missing_videos)} videos that is not in to_dir")
    print(f"Found {len(missing_images)} images that is not in to_dir")

    if not missing_keys:
        return

    for key in tqdm(sorted(missing_keys), desc="Moving", unit="file"):
        src = from_files[key]
        dst = to_dir / src.name
        try:
            shutil.copy2(src, dst)
        except Exception as exc:
            tqdm.write(f"[ERROR] {src.name}: {exc}")

if __name__ == "__main__":
    sync(pc_from_dir, pc_to_dir)
