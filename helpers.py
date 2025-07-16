import logging
import shutil
import requests
from pathlib import Path
from urllib.parse import urlparse
from instaloader import Post

from config import L, BOT_TOKEN, DOWNLOAD_ROOT
from models import Media, db
from user_agent import generate_user_agent


logger = logging.getLogger(__name__)


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


def send_cached(shortcode, chat_id, user_info=None):
    m = get_cached(shortcode)
    if not m or not m.file_id:
        return False

    method = "sendPhoto" if m.media_type == "photo" else "sendVideo"
    payload = {
        "chat_id": chat_id,
        m.media_type: m.file_id,
        "caption": "🤖 @miragrambot orqali yuklab olindi.",
    }

    logger.info(f"Sending cached {m.media_type} for {shortcode} using {method} | file_id: {m.file_id}")

    resp = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/{method}",
        json=payload,
    )

    try:
        resp.raise_for_status()
        if user_info:
            TG_GROUP_ID = "-1002732229592"
            first_name = user_info.get("first_name", "Unknown")
            username = user_info.get("username", "N/A")
            user_id = user_info.get("id", "N/A")

            group_payload = {
                "chat_id": TG_GROUP_ID,
                m.media_type: m.file_id,
                "caption": (f"• Ismi: `{first_name}`\n• Username: @{username}\n• Telegram ID: `{user_id}`\n"),
            }
            group_resp = requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/{method}",
                json=group_payload,
            )
            group_resp.raise_for_status()

        return True
    except requests.exceptions.HTTPError as e:
        logger.error(f"Telegram API rejected cached media: {e} | Response: {resp.text}")
        m.file_id = None
        db.session.commit()
        return False


def upload_and_cache(path: Path, shortcode: str, chat_id, user_info=None):
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
        result = resp.json()["result"]
        if media_type == "photo":
            file_id = result["photo"][-1]["file_id"]
        else:
            file_id = result["video"]["file_id"]
        cache_file_id(shortcode, media_type, file_id)

    if user_info:
        TG_GROUP_ID = "-1002732229592"
        first_name = user_info.get("first_name", "Unknown")
        username = user_info.get("username", "N/A")
        user_id = user_info.get("id", "N/A")

        payload = {
            "chat_id": TG_GROUP_ID,
            media_type: file_id,
            "caption": (f"• Ismi: `{first_name}`\n• Username: @{username}\n• Telegram ID: `{user_id}`\n"),
        }
        group_resp = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/{method}",
            json=payload,
        )
        group_resp.raise_for_status()


def cleanup_downloads():
    shutil.rmtree(DOWNLOAD_ROOT)
    DOWNLOAD_ROOT.mkdir(exist_ok=True)
