from tqdm import tqdm
from pathlib import Path
from ppadb.client import Client as AdbClient

imageExts = {'.jpg', '.jpeg', '.png', '.heic'}
videoExts = {'.mp4', '.avi', '.mkv', '.mov'}
mediaExts = imageExts | videoExts

fromDirs = [
    "/storage/emulated/0/DCIM/Camera",
    "/storage/emulated/0/Pictures",
    "/storage/emulated/0/Movies/WhatsApp",
    "/storage/emulated/0/Android/media/com.whatsapp/WhatsApp/Media/WhatsApp Images",
    "/storage/emulated/0/Android/media/com.whatsapp/WhatsApp/Media/WhatsApp Video",
]

toDir = Path("path\to\your\folder")
toDir.mkdir(parents=True, exist_ok=True)

adbClient = AdbClient()
connectedDevices = adbClient.devices()

if not connectedDevices:
    print("No device found, check your connection.")
    exit()

device = connectedDevices[0]

def getSize(filePath):
    return int(device.shell(f"stat -c %s '{filePath}'").strip() or 0)
    
def formatSize(bytesSize):
    gb = bytesSize / (1024 ** 3)
    return f"{gb:.2f} GB"

print("Scanning phone...\n")

phoneFiles = []
dirFileCount = {}

for fromDir in fromDirs:
    shellOutput = device.shell(f"find '{fromDir}' -type f 2>/dev/null")
    filesInDir = [f for f in shellOutput.strip().split("\n") if f and Path(f).suffix.lower() in mediaExts]
    phoneFiles.extend(filesInDir)
    
    dirName = fromDir.split("/")[-1] if fromDir.split("/")[-1] else fromDir.split("/")[-2]
    dirFileCount[dirName] = len(filesInDir)

for dirName, count in dirFileCount.items():
    print(f"{dirName}: {count} files found!")
print()

pcBasenames = {f.name for f in toDir.rglob("*") if f.suffix.lower() in mediaExts}
phoneImages = [f for f in phoneFiles if Path(f).suffix.lower() in imageExts]
phoneVideos = [f for f in phoneFiles if Path(f).suffix.lower() in videoExts]

newImages = [f for f in phoneImages if Path(f).name not in pcBasenames]
newVideos = [f for f in phoneVideos if Path(f).name not in pcBasenames]

filesToCopy = newImages + newVideos

fileSizes = {f: getSize(f) for f in filesToCopy}
totalSize = sum(fileSizes.values())

print(f"{len(newImages)}/{len(phoneImages)} images are not in {toDir}")
print(f"{len(newVideos)}/{len(phoneVideos)} videos are not in {toDir}\n")

progress = tqdm(total=totalSize, unit="B", unit_scale=True, desc="Syncing")

for phonePath in filesToCopy:
    dest = toDir / Path(phonePath).name
    device.pull(phonePath, str(dest))
    progress.update(fileSizes[phonePath])

progress.close()

print("Done!")