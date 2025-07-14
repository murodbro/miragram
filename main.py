import os
import re
import shutil
import requests
import instaloader

from pathlib import Path
from urllib.parse import urlparse
from flask import Flask, request

from dotenv import load_dotenv

load_dotenv()


DOWNLOAD_ROOT = Path("downloads")
DOWNLOAD_ROOT.mkdir(parents=True, exist_ok=True)

L = instaloader.Instaloader(
    download_videos=True,
    save_metadata=False,
    quiet=True,
)

BOT_TOKEN = "6810197358:AAGuWZVyBoYLo9yrwbFUfGIhIAG6Zde8wP4"
CHAT_ID = os.getenv("CHAT_ID")
IG_USERNAME = "djan.gooo__"
IG_PASSWORD = "murodbro0604"
SESSION_FILE = "ig_session"


# if Path(SESSION_FILE).exists():
#     L.load_session_from_file(IG_USERNAME, SESSION_FILE)
# else:
#     L.login(IG_USERNAME, IG_PASSWORD)
#     L.save_session_to_file(IG_USERNAME, SESSION_FILE)


def download_instagram_media(url: str):
    shortcode = urlparse(url).path.rstrip("/").split("/")[-1]
    post = instaloader.Post.from_shortcode(L.context, shortcode)
    L.download_post(post, target=str(DOWNLOAD_ROOT))


def send_file(path: Path):
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png"}:
        method, key = "sendPhoto", "photo"
    elif suffix in {".mp4", ".mov"}:
        method, key = "sendVideo", "video"
    else:
        method, key = "sendDocument", "document"

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    with open(path, "rb") as fh:
        resp = requests.post(
            url,
            data={"chat_id": CHAT_ID},
            files={key: fh},
        )
    resp.raise_for_status()


def cleanup_downloads():
    shutil.rmtree(DOWNLOAD_ROOT)
    DOWNLOAD_ROOT.mkdir(exist_ok=True)


app = Flask(__name__)


@app.route("/", methods=["GET"])
def home():
    return {"ok": True}


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    chat_id = str(data.get("message", {}).get("chat", {}).get("id", ""))
    if chat_id != CHAT_ID:
        return "ok"

    text = data.get("message", {}).get("text", "")
    urls = re.findall(r"https?://www\.instagram\.com/[^\s]+", text)
    if not urls:
        return "ok"

    try:
        download_instagram_media(urls[-1])

        media_files = [f for f in DOWNLOAD_ROOT.iterdir() if f.is_file()]
        videos = [f for f in media_files if f.suffix.lower() in (".mp4", ".mov")]
        to_send = videos or [f for f in media_files if f.suffix.lower() in (".jpg", ".jpeg", ".png")]

        for media in to_send:
            send_file(media)

    except Exception as e:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={
                "chat_id": CHAT_ID,
                "text": f"❗ Error: {e}",
            },
        )
    finally:
        cleanup_downloads()

    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5005)
