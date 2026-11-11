import json
import numpy as np
from mediainfo import file_hash
from config import CLIP_SIMILARITY, PHASH_DISTANCE, VIDEO_DURATION_GAP

def load_index(index_file):
    if index_file.exists():
        return json.loads(index_file.read_text(encoding="utf-8"))
    return {"hashes": {}, "done": {}, "images": [], "videos": []}

def save_index(index, index_file):
    index_file.parent.mkdir(parents=True, exist_ok=True)
    temp = index_file.with_name(f"{index_file.name}.part")
    temp.write_text(json.dumps(index), encoding="utf-8")
    temp.replace(index_file)

def cached_hash(index, path):
    stat = path.stat()
    key = f"{path}|{stat.st_size}|{stat.st_mtime_ns}"
    if key not in index["hashes"]:
        index["hashes"][key] = file_hash(path)
    return index["hashes"][key]

def group_pairs(count, pairs):
    parents = list(range(count))

    def find(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i

    for first, second in pairs:
        parents[find(first)] = find(second)

    groups = {}
    for i in range(count):
        groups.setdefault(find(i), []).append(i)
    return list(groups.values())

def image_pairs(values):
    numbers = np.array([int(value, 16) for value in values], dtype=np.uint64)
    for i in range(len(numbers) - 1):
        distances = np.bitwise_count(numbers[i + 1:] ^ numbers[i])
        for j in np.flatnonzero(distances <= PHASH_DISTANCE):
            yield i, i + 1 + int(j)

def frames_match(first, second):
    if not first or not second:
        return False
    distances = [(int(a, 16) ^ int(b, 16)).bit_count() for a, b in zip(first, second)]
    return max(distances) <= PHASH_DISTANCE

def video_pairs(values):
    order = sorted(range(len(values)), key=lambda i: values[i][0])
    for position, i in enumerate(order):
        for j in order[position + 1:]:
            if values[j][0] - values[i][0] > VIDEO_DURATION_GAP:
                break
            if frames_match(values[i][1], values[j][1]):
                yield i, j

def similar_pairs(embeddings):
    for start in range(0, len(embeddings), 1024):
        scores = embeddings[start:start + 1024] @ embeddings.T
        for row, column in zip(*np.nonzero(scores > CLIP_SIMILARITY)):
            if start + row < column:
                yield start + int(row), int(column)
