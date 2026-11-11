import warnings
from tqdm import tqdm
from converter import place_file
from classifier import classify_images
from dates import find_date, parse_date
from paths import index_file, memories_dir, output_dir
from mediainfo import frame_hashes, probe_video, read_image
from useless import is_garbage, is_screen_size, name_reason, quality_reason
from config import MEDIA_EXTS, MIN_IMAGE_SIDE, MIN_VIDEO_SECONDS, REVIEW_NO_CAMERA, VIDEO_EXTS
from duplicates import (cached_hash, group_pairs, image_pairs, load_index, save_index,
                        similar_pairs, video_pairs)

warnings.filterwarnings("ignore")

def quality_rank(memory):
    has_date = any(parse_date(text) for text in memory["dates"])
    pixels = (memory["width"] or 0) * (memory["height"] or 0)
    return memory["camera"], has_date, pixels, memory["path"].stat().st_size

class Memorier:
    def __init__(self, memories_dir, output_dir, index_file):
        self.memories_dir = memories_dir
        self.output_dir = output_dir
        self.index_file = index_file
        self.index = load_index(index_file)
        self.memories = []
        self.run_hashes = set()

    def find_files(self):
        all_files = [path for path in self.memories_dir.rglob("*") if path.is_file()]
        self.memories = []
        for path in tqdm(all_files, desc="Finding files"):
            suffix = path.suffix.lower()
            if suffix in MEDIA_EXTS and self.output_dir not in path.parents:
                self.memories.append({"path": path, "video": suffix in VIDEO_EXTS, "review": None})
        print(f"Found {len(self.memories)} files.\n")

    def remove_garbage_files(self):
        clean_memories = []
        for memory in tqdm(self.memories, desc="Removing garbage files"):
            memory["review"] = name_reason(memory["path"])
            if memory["review"] or not is_garbage(memory["path"]):
                clean_memories.append(memory)
        print(f"Removed {len(self.memories) - len(clean_memories)} garbage files.\n")
        self.memories = clean_memories

    def remove_exact_duplicates(self):
        unique_memories = {}
        for memory in tqdm(self.memories, desc="Hashing files"):
            memory["md5"] = cached_hash(self.index, memory["path"])
            self.run_hashes.add(memory["md5"])
            if memory["md5"] not in self.index["done"]:
                unique_memories.setdefault(memory["md5"], memory)
        print(f"Skipped {len(self.memories) - len(unique_memories)} exact or old copies.\n")
        self.memories = list(unique_memories.values())

    def read_media(self):
        readable_memories = []
        for memory in tqdm(self.memories, desc="Reading files"):
            details = probe_video(memory["path"]) if memory["video"] else read_image(memory["path"])
            if details is not None:
                memory.update(details)
                readable_memories.append(memory)
        print(f"Removed {len(self.memories) - len(readable_memories)} corrupted files.\n")
        self.memories = readable_memories

    def filter_by_dimensions(self):
        high_res_memories = []
        for memory in self.memories:
            if not memory["review"] and is_screen_size(memory):
                memory["review"] = "screenshots"
            width, height = memory["width"], memory["height"]
            low_res = width and height and min(width, height) < MIN_IMAGE_SIDE
            if memory["review"] or not low_res:
                high_res_memories.append(memory)
        print(f"Removed {len(self.memories) - len(high_res_memories)} low resolution files.\n")
        self.memories = high_res_memories

    def filter_by_duration(self):
        valid_memories = []
        for memory in self.memories:
            duration = memory.get("duration")
            too_short = memory["video"] and duration is not None and duration < MIN_VIDEO_SECONDS
            if memory["review"] or not too_short:
                valid_memories.append(memory)
        print(f"Removed {len(self.memories) - len(valid_memories)} short videos.\n")
        self.memories = valid_memories

    def find_near_copies(self, memories, old_values, new_values, find_pairs):
        offset = len(old_values)
        copies = set()
        for group in group_pairs(offset + len(new_values), find_pairs(old_values + new_values)):
            members = [memories[i - offset] for i in group if i >= offset]
            if len(group) > 1 and members:
                best = max(members, key=quality_rank) if len(members) == len(group) else None
                copies.update(memory["md5"] for memory in members if memory is not best)
        return copies

    def remove_near_duplicates(self):
        images = [m for m in self.memories if not m["video"] and not m["review"]]
        videos = [m for m in self.memories if m["video"] and not m["review"]]

        for video in tqdm(videos, desc="Reading video frames"):
            video["frames"] = frame_hashes(video["path"], video["duration"] or 0)

        image_values = [image["phash"] for image in images]
        video_values = [[video["duration"] or 0, video["frames"]] for video in videos]
        copies = self.find_near_copies(images, self.index["images"], image_values, image_pairs)
        copies |= self.find_near_copies(videos, self.index["videos"], video_values, video_pairs)

        print(f"Removed {len(copies)} near duplicate files.\n")
        self.memories = [memory for memory in self.memories if memory["md5"] not in copies]

    def find_useless_images(self):
        images = [memory for memory in self.memories if not memory["video"]]
        for image in images:
            image["review"] = image["review"] or quality_reason(image)

        candidates = [image for image in images if not image["review"]]
        if not candidates:
            return

        reasons, embeddings = classify_images([image["path"] for image in candidates])
        for image, reason in zip(candidates, reasons):
            no_camera = REVIEW_NO_CAMERA and not image["camera"]
            image["review"] = reason or ("no-camera" if no_camera else None)

        kept = [i for i, image in enumerate(candidates) if not image["review"]]
        for group in group_pairs(len(kept), similar_pairs(embeddings[kept])):
            members = [candidates[kept[i]] for i in group]
            best = max(members, key=quality_rank)
            for image in members:
                if image is not best:
                    image["review"] = "similar"

        review_count = sum(1 for image in images if image["review"])
        print(f"Sent {review_count} images to Review.\n")

    def destination_folder(self, memory):
        base = self.output_dir / ("Videos" if memory["video"] else "Photos")
        if memory["review"]:
            base = self.output_dir / "Review" / memory["review"]
        date = find_date(memory["path"], memory["dates"])
        if date is None:
            return base / "Unknown"
        return base / date.strftime("%Y") / date.strftime("%m-%B")

    def organize_files(self):
        total_copied = 0
        total_skipped = 0

        for memory in tqdm(self.memories, desc="Copying files"):
            if place_file(memory["path"], self.destination_folder(memory), memory["md5"]):
                total_copied += 1
            else:
                total_skipped += 1

            self.index["done"][memory["md5"]] = True
            if memory["video"] and not memory["review"]:
                self.index["videos"].append([memory["duration"] or 0, memory["frames"]])
            elif not memory["review"]:
                self.index["images"].append(memory["phash"])

        print(f"Copied {total_copied} files, skipped {total_skipped} existing files.\n")

    def run(self):
        try:
            self.find_files()
            self.remove_garbage_files()
            self.remove_exact_duplicates()
            self.read_media()
            self.filter_by_dimensions()
            self.filter_by_duration()
            self.remove_near_duplicates()
            self.find_useless_images()
            self.organize_files()
            self.index["done"].update(dict.fromkeys(self.run_hashes, True))
        finally:
            save_index(self.index, self.index_file)

if __name__ == "__main__":
    memorier = Memorier(memories_dir, output_dir, index_file)
    memorier.run()
