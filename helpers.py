import shutil
import requests
from pathlib import Path
from urllib.parse import urlparse
from instaloader import Post

from config import L, BOT_TOKEN, DOWNLOAD_ROOT
from models import Media, db
from user_agent import generate_user_agent


def download_instagram_media(url: str):
    user_agent = generate_user_agent()
    L.context._session.headers.update({"User-Agent": user_agent})

    shortcode = urlparse(url).path.rstrip("/").split("/")[-1]
    post = Post.from_shortcode(L.context, shortcode)
    L.download_post(post, target=str(DOWNLOAD_ROOT))


def get_cached(shortcode):
    return Media.query.filter_by(shortcode=shortcode).first()


def cache_file_id(shortcode, media_type, file_id):
    m = get_cached(shortcode)
    if not m:
        m = Media(shortcode=shortcode, media_type=media_type, file_id=file_id)
        db.session.add(m)
    else:
        m.file_id = file_id
    db.session.commit()
    return m


def send_cached(shortcode, chat_id):
    m = get_cached(shortcode)
    if not m or not m.file_id:
        return False
    method = "sendPhoto" if m.media_type == "photo" else "sendVideo"
    resp = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/{method}",
        json={
            "chat_id": chat_id,
            m.media_type: m.file_id,
            "caption": "🤖 @miragrambot orqali yuklab olindi.",
        },
    )
    resp.raise_for_status()
    return True


def upload_and_cache(path: Path, shortcode: str, chat_id):
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png"}:
        method, key, media_type = "sendPhoto", "photo", "photo"
    else:
        method, key, media_type = "sendVideo", "video", "video"

    with open(path, "rb") as fh:
        resp = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/{method}",
            data={
                "chat_id": chat_id,
                "caption": "🤖 @miragrambot orqali yuklab olindi.",
            },
            files={key: fh},
        )
    resp.raise_for_status()
    result = resp.json()["result"][key]
    cache_file_id(shortcode, media_type, result["file_id"])


def cleanup_downloads():
    shutil.rmtree(DOWNLOAD_ROOT)
    DOWNLOAD_ROOT.mkdir(exist_ok=True)
