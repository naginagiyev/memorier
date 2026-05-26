import sys
import shutil
from tqdm import tqdm
from pathlib import Path

imageExts = {'.jpg', '.jpeg', '.png', '.heic', '.webp'}
videoExts = {'.mp4', '.avi', '.mkv', '.mov', '.webm'}
allExts   = imageExts | videoExts
def scanMedia(directory: Path) -> dict[str, Path]:
    found: dict[str, Path] = {}
    allFiles = [p for p in directory.rglob('*') if p.is_file()]
    for path in tqdm(allFiles, desc="Scanning", unit="file"):
        if path.suffix.lower() in allExts:
            key = path.name.lower()
            if key not in found:
                found[key] = path
    return found

def sync(fromDir: Path, toDir: Path) -> None:
    if not fromDir.is_dir():
        sys.exit(f"[ERROR] fromDir does not exist or is not a directory: {fromDir}")
    if not toDir.is_dir():
        sys.exit(f"[ERROR] toDir does not exist or is not a directory: {toDir}")

    fromFiles = scanMedia(fromDir)
    toFiles   = scanMedia(toDir)

    missingKeys   = set(fromFiles.keys()) - set(toFiles.keys())
    missingImages = [k for k in missingKeys if fromFiles[k].suffix.lower() in imageExts]
    missingVideos = [k for k in missingKeys if fromFiles[k].suffix.lower() in videoExts]

    print(f"Found {len(missingVideos)} videos that is not in toDir")
    print(f"Found {len(missingImages)} images that is not in toDir")

    if not missingKeys:
        return

    for key in tqdm(sorted(missingKeys), desc="Moving", unit="file"):
        src = fromFiles[key]
        dst = toDir / src.name
        try:
            shutil.copy2(src, dst)
        except Exception as exc:
            tqdm.write(f"[ERROR] {src.name}: {exc}")

if __name__ == '__main__':
    fromDir = Path("path/to/your/folder")
    toDir = Path("path/to/your/folder")
    sync(fromDir, toDir)