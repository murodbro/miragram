import os
from pathlib import Path
from instaloader import Instaloader
from dotenv import load_dotenv


load_dotenv(override=True)

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
PROXY = os.getenv("PROXY")
IG_USERNAME = os.getenv("IG_USERNAME", "djan.gooo__")
IG_PASSWORD = os.getenv("IG_PASSWORD", "murodbro0604")

SESSION_FILE = f"{IG_USERNAME}.session"
DOWNLOAD_ROOT = Path("downloads")
DOWNLOAD_ROOT.mkdir(parents=True, exist_ok=True)


L = Instaloader(
    download_videos=True,
    save_metadata=False,
    quiet=True,
    download_video_thumbnails=False,
)
L.context._session.proxies.update(
    {
        "http": PROXY,
        "https": PROXY,
    }
)

try:
    L.load_session_from_file(username=IG_USERNAME, filename=str(SESSION_FILE))
    print(f"✅ Loaded Instagram session for {IG_USERNAME}")
except FileNotFoundError:
    L.login(IG_USERNAME, IG_PASSWORD)
    L.save_session_to_file(filename=str(SESSION_FILE))
    print(f"🔐 Logged in and saved session to {SESSION_FILE}")
