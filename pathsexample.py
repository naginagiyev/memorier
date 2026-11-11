from pathlib import Path, PurePosixPath

root_dir = Path(__file__).resolve().parent
data_dir = root_dir / "data"
memories_dir = data_dir / "memories"
output_dir = data_dir / "organized"
index_file = output_dir / "index.json"
phone_dir = memories_dir
pc_from_dir = data_dir / "pcfrom"
pc_to_dir = data_dir / "pcto"
share_dir = data_dir / "share"

phone_root = PurePosixPath("/storage/emulated/0")
whatsapp_dir = phone_root / "Android" / "media" / "com.whatsapp" / "WhatsApp" / "Media"
phone_dirs = [
    phone_root / "DCIM" / "Camera",
    phone_root / "DCIM" / "Screenshots",
    phone_root / "Pictures",
    phone_root / "Movies" / "WhatsApp",
    whatsapp_dir / "WhatsApp Images",
    whatsapp_dir / "WhatsApp Video",
]
