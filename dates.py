import re
from config import MIN_YEAR
from datetime import datetime

NAME_DATE_PATTERNS = [
    re.compile(r"(?<!\d)(20\d{2})(\d{2})(\d{2})(?!\d)"),
    re.compile(r"(?<!\d)(20\d{2})[-_.](\d{2})[-_.](\d{2})(?!\d)"),
]
UNIX_NAME_PATTERN = re.compile(r"(?:mmexport|FB_IMG_)(1\d{12})(?!\d)", re.IGNORECASE)

def check_date(date):
    if MIN_YEAR <= date.year and date <= datetime.now():
        return date
    return None

def parse_date(text):
    try:
        return check_date(datetime.strptime(str(text)[:10].replace(":", "-"), "%Y-%m-%d"))
    except ValueError:
        return None

def date_from_name(name):
    for pattern in NAME_DATE_PATTERNS:
        for match in pattern.finditer(name):
            date = parse_date("-".join(match.groups()))
            if date:
                return date
    match = UNIX_NAME_PATTERN.search(name)
    if match:
        return check_date(datetime.fromtimestamp(int(match.group(1)) / 1000))
    return None

def date_from_file(path):
    try:
        return check_date(datetime.fromtimestamp(path.stat().st_mtime))
    except (OSError, ValueError):
        return None

def find_date(path, metadata_dates):
    for text in metadata_dates:
        date = parse_date(text)
        if date:
            return date
    return date_from_name(path.stem) or date_from_file(path)
