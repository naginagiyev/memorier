import re
from mediainfo import has_camera
from config import BLUR_LIMIT, BRIGHT_LIMIT, DARK_LIMIT, GARBAGE_WORDS, MAX_NAME_LENGTH, SCREEN_SIZES

CAMERA_NAME = re.compile(
    r"(?<!\d)20\d{2}[-_.]?\d{2}[-_.]?\d{2}[-_ .]\d{2}[-_.]?\d{2}[-_.]?\d{2}"
    r"|-wa\d+|mmexport\d{13}|fb_img_\d{13}"
)

def is_garbage(path):
    name = path.stem.lower()
    if any(word in name for word in GARBAGE_WORDS):
        return True
    return len(name) > MAX_NAME_LENGTH and not CAMERA_NAME.search(name) and not has_camera(path)

def name_reason(path):
    name = path.name.lower()
    if "screenshot" in name or "screenshots" in {part.lower() for part in path.parts}:
        return "screenshots"
    if "screen_recording" in name or "screenrecord" in name:
        return "screen-recordings"
    if name.startswith("stk-"):
        return "stickers"
    return None

def is_screen_size(memory):
    if memory["video"] or memory["camera"] or not memory["width"]:
        return False
    sides = sorted((memory["width"], memory["height"]))
    return tuple(sides) in SCREEN_SIZES

def quality_reason(memory):
    if memory["brightness"] < DARK_LIMIT:
        return "dark"
    if memory["brightness"] > BRIGHT_LIMIT:
        return "bright"
    if memory["blur"] < BLUR_LIMIT:
        return "blurry"
    return None
