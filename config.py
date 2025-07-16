import os
from pathlib import Path
from instaloader import Instaloader
from dotenv import load_dotenv

load_dotenv(override=True)

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

IG_USERNAME = os.getenv("IG_USERNAME")
IG_PASSWORD = os.getenv("IG_PASSWORD")
SESSION_FILE = os.getenv("SESSION_FILE", "ig_session")

DOWNLOAD_ROOT = Path("downloads")
DOWNLOAD_ROOT.mkdir(parents=True, exist_ok=True)

L = Instaloader(
    download_videos=True,
    save_metadata=False,
    quiet=True,
    download_video_thumbnails=False,
)
if Path(SESSION_FILE).exists():
    L.load_session_from_file(IG_USERNAME, SESSION_FILE)
else:
    L.login(IG_USERNAME, IG_PASSWORD)
    L.save_session_to_file(SESSION_FILE)
