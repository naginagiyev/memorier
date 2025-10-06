import os
import json
import shutil
import warnings
import imagehash
import subprocess
from tqdm import tqdm
from PIL import Image
from datetime import datetime
warnings.filterwarnings("ignore")

class Memorier:
    def __init__(self, folder: str):
        self.folder = folder
        self.founded_paths = []
        self.image_exts = {'.jpg', '.jpeg', '.png', '.heic', '.webp'}
        self.video_exts = {'.mp4', '.avi', '.mkv', '.mov', '.webm'}
        self.valid_exts = self.image_exts.union(self.video_exts)
        self.errors = []
        print(f"Memorier initialized with folder: {self.folder}\n")

    def validateFiles(self):
        if not os.path.exists(self.folder):
            self.errors.append(f"Folder does not exist: {self.folder}")
            return False
        
        if not os.path.isdir(self.folder):
            self.errors.append(f"Path is not a directory: {self.folder}")
            return False
        
        total_files = sum(len(files) for _, _, files in os.walk(self.folder))
        if total_files == 0:
            self.errors.append("No files found in the specified folder")
            return False
        
        corrupted_files = []
        with tqdm(total=total_files, desc="Validating files", unit="file") as pbar:
            for root, dirs, files in os.walk(self.folder):
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in self.valid_exts:
                        full_path = os.path.join(root, file)
                        if not os.path.isfile(full_path):
                            corrupted_files.append(full_path)
                        else:
                            try:
                                if ext in self.image_exts:
                                    with Image.open(full_path) as img:
                                        img.verify()
                                elif ext in self.video_exts:
                                    cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_streams', full_path]
                                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                                    if result.returncode != 0:
                                        corrupted_files.append(full_path)
                            except:
                                corrupted_files.append(full_path)
                    pbar.update(1)
        
        if corrupted_files:
            deleted_count = 0
            for bad_path in corrupted_files:
                try:
                    if os.path.exists(bad_path):
                        os.remove(bad_path)
                        deleted_count += 1
                except Exception:
                    pass
        
        print("All files validated successfully!\n")
        return True

    def removeLargeFiles(self, max_image_bytes=20 * 1024 * 1024, max_video_bytes=1024 * 1024 * 1024):
        removed_files = []
        with tqdm(total=len(self.founded_paths), desc="Removing large files", unit="file") as pbar:
            for file_path in self.founded_paths[:]:
                ext = os.path.splitext(file_path)[1].lower()
                try:
                    size = os.path.getsize(file_path)
                except Exception:
                    size = None

                should_remove = False
                reason = ""

                if size is None:
                    should_remove = True
                    reason = "unable to read size"
                elif ext in self.image_exts and size > max_image_bytes:
                    should_remove = True
                    reason = f"image too large ({size} > {max_image_bytes})"
                elif ext in self.video_exts and size > max_video_bytes:
                    should_remove = True
                    reason = f"video too large ({size} > {max_video_bytes})"

                if should_remove:
                    try:
                        os.remove(file_path)
                        removed_files.append((file_path, reason))
                        self.founded_paths.remove(file_path)
                    except Exception as e:
                        print(f"Failed to remove large file '{file_path}': {e}")

                pbar.update(1)

        print(f"\n{len(removed_files)} large files were removed.")

    def collectFiles(self):
        total_files = sum(len(files) for _, _, files in os.walk(self.folder))
        with tqdm(total=total_files, desc="Collecting files", unit="file") as pbar:
            for root, dirs, files in os.walk(self.folder):
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in self.valid_exts:
                        full_path = os.path.join(root, file)
                        self.founded_paths.append(full_path)
                    pbar.update(1)
        print(f"\n{len(self.founded_paths)} files have been collected!")

    def convertTypes(self):
        converted_paths = []
        converted_count = 0
        with tqdm(total=len(self.founded_paths), desc="Converting files", unit="file") as pbar:
            for file_path in self.founded_paths:
                ext = os.path.splitext(file_path)[1].lower()
                new_path = file_path
                try:
                    try:
                        pbar.set_postfix({"file": os.path.basename(file_path)})
                    except Exception:
                        pass

                    if ext in ['.heic', '.webp']:
                        if ext == '.heic':
                            heif_supported = False
                            try:
                                import pillow_heif  # type: ignore
                                pillow_heif.register_heif_opener()
                                heif_supported = True
                            except Exception:
                                heif_supported = False
                            if not heif_supported:
                                print(f"Skipping HEIC (no decoder): {file_path}")
                                new_path = file_path
                            else:
                                with Image.open(file_path) as img:
                                    if img.mode in ('RGBA', 'LA', 'P'):
                                        img = img.convert('RGB')
                                    new_path = os.path.splitext(file_path)[0] + '.png'
                                    img.save(new_path, 'PNG')
                                os.remove(file_path)
                                converted_count += 1
                        else:
                            with Image.open(file_path) as img:
                                if img.mode in ('RGBA', 'LA', 'P'):
                                    img = img.convert('RGB')
                                new_path = os.path.splitext(file_path)[0] + '.png'
                                img.save(new_path, 'PNG')
                            os.remove(file_path)
                            converted_count += 1

                    elif ext in ['.avi', '.mkv', '.mov', '.webm']:
                        new_path = os.path.splitext(file_path)[0] + '.mp4'
                        cmd = [
                            'ffmpeg', '-v', 'error', '-i', file_path,
                            '-c:v', 'libx264', '-c:a', 'aac', '-movflags', '+faststart', '-y', new_path
                        ]
                        try:
                            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
                        except subprocess.TimeoutExpired:
                            print(f"ffmpeg timed out: {file_path}")
                            result = None
                        if result and result.returncode == 0 and os.path.exists(new_path):
                            os.remove(file_path)
                            converted_count += 1
                        else:
                            if result and result.stderr:
                                print(f"ffmpeg failed for {file_path}: {result.stderr.strip()[:300]}...")
                            new_path = file_path

                except Exception as e:
                    print(f"Failed to convert '{file_path}': {e}")
                    new_path = file_path
                finally:
                    converted_paths.append(new_path)
                    pbar.update(1)
        self.founded_paths = converted_paths
        print(f"\n{converted_count} files have been converted.")

    def getImageHashes(self):
        hashes = {}
        with tqdm(total=len(self.founded_paths), desc="Hashing images", unit="img") as pbar:
            for path in self.founded_paths:
                ext = os.path.splitext(path)[1].lower()
                if ext in self.image_exts:
                    img = Image.open(path)
                    hashes[path] = imagehash.phash(img)
                pbar.update(1)
        return hashes

    def removeDuplicateImages(self, threshold=95):
        hashes = self.getImageHashes()
        paths = list(hashes.keys())
        seen = set()
        deleted = set()

        with tqdm(total=len(paths), desc="Removing duplicates", unit="img") as pbar:
            for i in range(len(paths)):
                if paths[i] in seen:
                    pbar.update(1)
                    continue
                for j in range(i + 1, len(paths)):
                    if paths[j] in seen:
                        continue
                    distance = hashes[paths[i]] - hashes[paths[j]]
                    similarity = (1 - distance / len(hashes[paths[i]].hash) ** 2) * 100
                    if similarity >= threshold:
                        os.remove(paths[j])
                        deleted.add(paths[j])
                        seen.add(paths[j])
                seen.add(paths[i])
                pbar.update(1)

        self.founded_paths = [p for p in self.founded_paths if p not in deleted]
        print(f"\n{len(deleted)} duplicate images have been removed.")

    def checkQuality(self, min_image_size=(600, 400), min_video_size=(600, 400)):

        removed_files = []
        
        with tqdm(total=len(self.founded_paths), desc="Removing low-quality files", unit="file") as pbar:
            for file_path in self.founded_paths[:]:
                ext = os.path.splitext(file_path)[1].lower()
                
                should_remove = False
                reason = ""
                
                if ext in self.image_exts:
                    with Image.open(file_path) as img:
                        width, height = img.size
                        if width < min_image_size[0] or height < min_image_size[1]:
                            should_remove = True
                            reason = f"dimensions too small ({width}x{height} < {min_image_size[0]}x{min_image_size[1]})"
                
                elif ext in self.video_exts:
                    cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', 
                          '-show_streams', file_path]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    
                    if result.returncode == 0:
                        data = json.loads(result.stdout)
                        video_stream = None
                        
                        for stream in data.get('streams', []):
                            if stream.get('codec_type') == 'video':
                                video_stream = stream
                                break
                        
                        if video_stream:
                            width = video_stream.get('width', 0)
                            height = video_stream.get('height', 0)
                            
                            if width < min_video_size[0] or height < min_video_size[1]:
                                should_remove = True
                                reason = f"dimensions too small ({width}x{height} < {min_video_size[0]}x{min_video_size[1]})"
                        else:
                            should_remove = True
                            reason = "no video stream found"
                    else:
                        should_remove = True
                        reason = "unable to analyze video"
                
                if should_remove:
                    os.remove(file_path)
                    removed_files.append((file_path, reason))
                    self.founded_paths.remove(file_path)
                
                pbar.update(1)
        
        print(f"\n{len(removed_files)} low-quality files were removed.")

    def createFolders(self):        
        project_dir = os.path.dirname(os.path.abspath(__file__))
        memories_dir = os.path.join(project_dir, "Memories")
        photos_dir = os.path.join(memories_dir, "Photos")
        videos_dir = os.path.join(memories_dir, "Videos")
        
        os.makedirs(photos_dir, exist_ok=True)
        os.makedirs(videos_dir, exist_ok=True)
                
        file_dates = {}
        with tqdm(total=len(self.founded_paths), desc="Extracting file dates", unit="file") as pbar:
            for file_path in self.founded_paths:
                stat = os.stat(file_path)
                file_time = stat.st_mtime
                file_date = datetime.fromtimestamp(file_time)
                file_dates[file_path] = file_date
                pbar.update(1)
        
        if not file_dates:
            return
        
        years_with_files = set()
        months_with_files = {}
        
        for file_path, file_date in file_dates.items():
            year = file_date.year
            month = file_date.month
            years_with_files.add(year)
            
            if year not in months_with_files:
                months_with_files[year] = set()
            months_with_files[year].add(month)
        
        months = ['January', 'February', 'March', 'April', 'May', 'June',
                 'July', 'August', 'September', 'October', 'November', 'December']
        
        for year in sorted(years_with_files):
            year_photos_dir = os.path.join(photos_dir, str(year))
            year_videos_dir = os.path.join(videos_dir, str(year))
            os.makedirs(year_photos_dir, exist_ok=True)
            os.makedirs(year_videos_dir, exist_ok=True)
            
            for month_num in sorted(months_with_files[year]):
                month_name = months[month_num - 1]
                month_photos_dir = os.path.join(year_photos_dir, month_name)
                month_videos_dir = os.path.join(year_videos_dir, month_name)
                os.makedirs(month_photos_dir, exist_ok=True)
                os.makedirs(month_videos_dir, exist_ok=True)
        
        self.file_dates = file_dates
        self.memories_dir = memories_dir
        self.photos_dir = photos_dir
        self.videos_dir = videos_dir
        self.months = months

        print("\nCreated folders successfully!")

    def organizeMemories(self):
        ask = input("Press any key to continue...")
        moved_count = 0
        with tqdm(total=len(self.founded_paths), desc="Copying files", unit="file") as pbar:
            for file_path in self.founded_paths:
                file_date = self.file_dates[file_path]
                year = file_date.year
                month = self.months[file_date.month - 1]
                
                ext = os.path.splitext(file_path)[1].lower()
                if ext in self.image_exts:
                    target_dir = os.path.join(self.photos_dir, str(year), month)
                elif ext in self.video_exts:
                    target_dir = os.path.join(self.videos_dir, str(year), month)
                else:
                    pbar.update(1)
                    continue
                
                filename = os.path.basename(file_path)
                target_path = os.path.join(target_dir, filename)
                
                counter = 1
                while os.path.exists(target_path):
                    name, ext = os.path.splitext(filename)
                    target_path = os.path.join(target_dir, f"{name}_{counter}{ext}")
                    counter += 1
                
                shutil.copy2(file_path, target_path)
                moved_count += 1
                
                pbar.update(1)
        
        print(f"\nSuccessfully copied {moved_count} files into Memories folder!")

memorier = Memorier("C:\\Users\\nagin\\OneDrive\\Belgeler\\memories")
if memorier.validateFiles():
    memorier.collectFiles()
    memorier.removeLargeFiles()
    memorier.convertTypes()
    memorier.checkQuality()
    memorier.removeDuplicateImages()
    memorier.createFolders()
    memorier.organizeMemories()
else:
    for error in memorier.errors:
        print(f"Error: {error}")