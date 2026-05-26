import os
import re
import cv2
import json
import shutil
import hashlib
import warnings
import subprocess
from tqdm import tqdm
from PIL import Image
from mutagen.mp4 import MP4
from datetime import datetime
from PIL.ExifTags import TAGS
from contextlib import contextmanager

Image.MAX_IMAGE_PIXELS = None
warnings.filterwarnings("ignore")

@contextmanager
def suppressStderr():
    devnull = open(os.devnull, 'w')
    oldFd = os.dup(2)
    os.dup2(devnull.fileno(), 2)
    try:
        yield
    finally:
        os.dup2(oldFd, 2)
        os.close(oldFd)
        devnull.close()

class Memorier:
    imageExtensions = {'.jpg', '.jpeg', '.png', '.heic', '.webp'}
    videoExtensions = {'.mp4', '.avi', '.mkv', '.mov', '.webm'}
    allExtensions = imageExtensions | videoExtensions

    def __init__(self, memoriesFolder: str, outputFolder: str):
        self.memoriesFolder = memoriesFolder
        self.outputFolder = outputFolder
        self.memories = []

    def findFiles(self):
        allFiles = []
        for root, _, files in os.walk(self.memoriesFolder):
            for file in files:
                allFiles.append(os.path.join(root, file))

        matchingFiles = []
        for filePath in tqdm(allFiles, desc="Finding files"):
            if os.path.splitext(filePath)[1].lower() in self.allExtensions:
                matchingFiles.append(filePath)
        self.memories = matchingFiles
        print(f"Found {len(self.memories)} files.\n")

    def convertToJPG(self, inputPath: str):
        outputPath = os.path.splitext(inputPath)[0] + ".jpg"
        subprocess.run(["ffmpeg", "-i", inputPath, outputPath], capture_output=True)
        return outputPath

    def convertHeicFiles(self):
        heicMemories = [f for f in self.memories if os.path.splitext(f)[1].lower() == ".heic"]
        convertedCount = 0
        for heicMemory in tqdm(heicMemories, desc="Converting HEIC to JPG"):
            outputPath = self.convertToJPG(heicMemory)
            if os.path.exists(outputPath):
                self.memories.append(outputPath)
                self.memories.remove(heicMemory)
                convertedCount += 1
        print(f"Converted {convertedCount} HEIC files.\n")

    def removeGarbageFiles(self):
        keywords = {"trash", "stk", "tmp", "temp", "cache"}
        cleanMemories = []
        garbageCount = 0
        for memory in tqdm(self.memories, desc="Removing garbage files"):
            nameWithoutExt = os.path.splitext(os.path.basename(memory))[0].lower()
            if any(kw in nameWithoutExt for kw in keywords) or len(nameWithoutExt) > 19:
                garbageCount += 1
            else:
                cleanMemories.append(memory)
        self.memories = cleanMemories
        print(f"Removed {garbageCount} garbage files.\n")

    def checkCorruptedFiles(self):
        validMemories = []
        corruptedCount = 0
        for memory in tqdm(self.memories, desc="Checking for corrupted files"):
            ext = os.path.splitext(memory)[1].lower()
            if ext in self.imageExtensions:
                try:
                    img = Image.open(memory)
                    img.verify()
                    validMemories.append(memory)
                except Exception:
                    corruptedCount += 1
            else:
                validMemories.append(memory)
        self.memories = validMemories
        print(f"Removed {corruptedCount} corrupted files.\n")

    def convertWebpFiles(self):
        webpMemories = [f for f in self.memories if os.path.splitext(f)[1].lower() == ".webp"]
        convertedCount = 0
        for webpMemory in tqdm(webpMemories, desc="Converting WebP to JPG"):
            outputPath = self.convertToJPG(webpMemory)
            if os.path.exists(outputPath):
                self.memories.append(outputPath)
                self.memories.remove(webpMemory)
                convertedCount += 1
        print(f"Converted {convertedCount} WebP files.\n")

    def convertToMp4(self, inputPath: str):
        outputPath = os.path.splitext(inputPath)[0] + ".mp4"
        subprocess.run(["ffmpeg", "-i", inputPath, "-c:v", "libx264", "-c:a", "aac", outputPath], capture_output=True)
        return outputPath

    def convertVideoFiles(self):
        videoMemories = [f for f in self.memories if os.path.splitext(f)[1].lower() in {".avi", ".mkv", ".mov", ".webm"}]
        convertedCount = 0
        for videoMemory in tqdm(videoMemories, desc="Converting videos to MP4"):
            outputPath = self.convertToMp4(videoMemory)
            if os.path.exists(outputPath):
                self.memories.append(outputPath)
                self.memories.remove(videoMemory)
                convertedCount += 1
        print(f"Converted {convertedCount} video files.\n")

    def getDimensions(self, filePath: str):
        ext = filePath.rsplit(".", 1)[-1].lower()
        if ext in ("jpg", "jpeg", "png"):
            img = Image.open(filePath)
            return img.size
        elif ext == "mp4":
            with suppressStderr():
                cap = cv2.VideoCapture(filePath)
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                cap.release()
            return w, h
        return None, None

    def filterByDimensions(self):
        highResMemories = []
        countLowResFiles = 0
        for memory in tqdm(self.memories, desc="Getting dimensions of files"):
            width, height = self.getDimensions(memory)
            if width is None or height is None:
                highResMemories.append(memory)
            elif height < 720 or width < 720:
                countLowResFiles += 1
            else:
                highResMemories.append(memory)
        self.memories = highResMemories
        print(f"Removed {countLowResFiles} low resolution files.\n")

    def imageHash(self, path: str):
        img = Image.open(path).convert("RGB").resize((32, 32))
        return hashlib.md5(img.tobytes()).hexdigest()

    def videoHash(self, path: str):
        h = hashlib.md5()
        with open(path, "rb") as f:
            h.update(f.read())
        return h.hexdigest()

    def removeDuplicates(self):
        seenImages = {}
        seenVideos = {}
        result = []

        for file in tqdm(self.memories, desc="Removing duplicates"):
            ext = file.split(".")[-1].lower()
            if ext in ["jpg", "jpeg", "png"]:
                h = self.imageHash(file)
                if h in seenImages:
                    old = seenImages[h]
                    if old.endswith((".jpg", ".jpeg")) and ext == "png":
                        result[result.index(old)] = file
                        seenImages[h] = file
                else:
                    seenImages[h] = file
                    result.append(file)
            elif ext == "mp4":
                h = self.videoHash(file)
                if h not in seenVideos:
                    seenVideos[h] = file
                    result.append(file)

        print(f"Removed {len(self.memories) - len(result)} duplicate files.\n")
        self.memories = result

    def getDuration(self, videoPath: str):
        try:
            cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", videoPath]
            result = subprocess.run(cmd, capture_output=True, text=True)
            return float(json.loads(result.stdout)["format"]["duration"])
        except Exception:
            return None

    def filterByDuration(self):
        validMemories = []
        removedCount = 0
        for memory in tqdm(self.memories, desc="Filtering videos by duration"):
            if memory.endswith(".mp4"):
                duration = self.getDuration(memory)
                if duration is not None and (duration < 3 or duration > 180):
                    removedCount += 1
                    continue
            validMemories.append(memory)
        self.memories = validMemories
        print(f"Removed {removedCount} videos (duration < 3s or > 180s).\n")

    def getTakenDate(self, filePath: str):  
        ext = os.path.splitext(filePath)[1].lower()

        if ext in ('.jpg', '.jpeg'):
            exifData = getattr(Image.open(filePath), '_getexif', lambda: None)()
            if exifData:
                for tag, value in exifData.items():
                    if TAGS.get(tag) == 'DateTimeOriginal':
                        return datetime.strptime(value, '%Y:%m:%d %H:%M:%S').strftime('%B %Y')

        elif ext == '.png':
            img = Image.open(filePath)
            xmp = img.info.get('XML:com.adobe.xmp', '')
            if xmp:
                match = re.search(r'<exif:DateTimeOriginal>(.*?)</exif:DateTimeOriginal>', xmp)
                if match:
                    try:
                        return datetime.fromisoformat(match.group(1)[:10]).strftime('%B %Y')
                    except Exception:
                        pass

        elif ext == '.mp4':
            tags = MP4(filePath).tags
            if tags:
                for key in ('©day', 'date', 'DATE'):
                    if key in tags:
                        try:
                            return datetime.fromisoformat(tags[key][0][:10]).strftime('%B %Y')
                        except Exception:
                            pass
            try:
                cmd = ["ffprobe", "-v", "error", "-show_entries", "format_tags=creation_time",
                       "-of", "json", filePath]
                result = subprocess.run(cmd, capture_output=True, text=True)
                creationTime = json.loads(result.stdout)["format"]["tags"]["creation_time"]
                return datetime.fromisoformat(creationTime[:10]).strftime('%B %Y')
            except Exception:
                pass

        return None

    def buildFolderStructure(self):
        self.folderStructure = {"Photos": {}, "Videos": {}}
        datedCount = 0
        unknownCount = 0

        for memory in tqdm(self.memories, desc="Getting file dates"):
            date = self.getTakenDate(memory)
            goesTo = "Videos" if str(memory).lower().endswith(".mp4") else "Photos"

            if date is not None:
                month, year = date.split()
                if year not in self.folderStructure[goesTo]:
                    self.folderStructure[goesTo][year] = {}
                if month not in self.folderStructure[goesTo][year]:
                    self.folderStructure[goesTo][year][month] = []
                self.folderStructure[goesTo][year][month].append(memory)
                datedCount += 1
            else:
                if "Unknown" not in self.folderStructure[goesTo]:
                    self.folderStructure[goesTo]["Unknown"] = []
                self.folderStructure[goesTo]["Unknown"].append(memory)
                unknownCount += 1

        print(f"Dated {datedCount} files, {unknownCount} without date.\n")

    def organizeFiles(self):
        outputRoot = self.outputFolder
        copyTasks = []

        for mediaType, years in self.folderStructure.items():
            for yearOrUnknown, value in years.items():
                if yearOrUnknown == "Unknown":
                    destFolder = os.path.join(outputRoot, mediaType, "Unknown")
                    os.makedirs(destFolder, exist_ok=True)
                    for filePath in value:
                        destFile = os.path.join(destFolder, os.path.basename(filePath))
                        copyTasks.append((filePath, destFile))
                else:
                    for month, files in value.items():
                        destFolder = os.path.join(outputRoot, mediaType, yearOrUnknown, month)
                        os.makedirs(destFolder, exist_ok=True)
                        for filePath in files:
                            destFile = os.path.join(destFolder, os.path.basename(filePath))
                            copyTasks.append((filePath, destFile))

        totalCopied = 0
        totalSkipped = 0

        for filePath, destFile in tqdm(copyTasks, desc="Copying files"):
            if not os.path.exists(destFile):
                shutil.copy2(filePath, destFile)
                totalCopied += 1
            else:
                totalSkipped += 1

        print(f"Copied {totalCopied} files, skipped {totalSkipped} existing files.\n")

    def run(self):
        self.findFiles()
        self.convertHeicFiles()
        self.removeGarbageFiles()
        self.checkCorruptedFiles()
        self.convertWebpFiles()
        self.convertVideoFiles()
        self.filterByDimensions()
        self.removeDuplicates()
        self.filterByDuration()
        self.buildFolderStructure()
        self.organizeFiles()

if __name__ == "__main__":
    memorier = Memorier(
        memoriesFolder="path\to\your\folder", # where the mixed files are in 
        outputFolder="path\to\your\folder" # where the organized files will be saved
    )
    memorier.run()