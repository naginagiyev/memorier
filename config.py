IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".webp"}
VIDEO_EXTS = {".mp4", ".avi", ".mkv", ".mov", ".webm"}
MEDIA_EXTS = IMAGE_EXTS | VIDEO_EXTS
CONVERT_TO_JPG = {".heic", ".webp"}
CONVERT_TO_MP4 = {".avi", ".mkv", ".mov", ".webm"}

GARBAGE_WORDS = {"trash", "tmp", "temp", "cache"}
MAX_NAME_LENGTH = 19
MIN_IMAGE_SIDE = 720
MIN_VIDEO_SECONDS = 3
MIN_YEAR = 2000
JPG_QUALITY = 100

PHASH_DISTANCE = 6
VIDEO_DURATION_GAP = 0.5

BLUR_LIMIT = 100
DARK_LIMIT = 25
BRIGHT_LIMIT = 235
REVIEW_NO_CAMERA = True
SCREEN_SIZES = {
    (720, 1600), (1080, 1920), (1080, 2160), (1080, 2340), (1080, 2400), (1170, 2532),
    (1179, 2556), (1284, 2778), (1290, 2796), (1440, 2560), (1440, 3040), (1440, 3200),
}

CLIP_MODEL = "openai/clip-vit-base-patch32"
CLIP_BATCH_SIZE = 16
CLIP_THRESHOLD = 0.4
CLIP_SIMILARITY = 0.95
CLIP_LABELS = {
    "a screenshot of a phone screen": "screenshots",
    "a meme with text on it": "memes",
    "a photo of a document or receipt": "documents",
    "a photo of people": None,
    "a photo of an animal or pet": None,
    "a photo of a place or landscape": None,
    "a photo of food or a drink": None,
    "a photo of a vehicle or machine": None,
    "a photo of an everyday object": None,
    "a close-up photo of a texture or surface": None,
}
