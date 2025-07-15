import re
import logging
import requests
from urllib.parse import urlparse

from flask import Flask, request
from dotenv import load_dotenv

from config import BOT_TOKEN, DATABASE_URL, DOWNLOAD_ROOT
from models import db
from helpers import (
    download_instagram_media,
    send_cached,
    upload_and_cache,
    cleanup_downloads,
)

load_dotenv()

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s:%(name)s: %(message)s")
logger = logging.getLogger(__name__)

with app.app_context():
    db.create_all()


@app.route("/", methods=["GET"])
def home():
    logger.info("Health check received")
    return {"ok": True}


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    logger.info(f"Received webhook data: {data}")
    chat_id = str(data.get("message", {}).get("chat", {}).get("id", ""))
    text = data.get("message", {}).get("text", "")
    urls = re.findall(r"https?://www\.instagram\.com/[^\s]+", text)

    if not urls:
        logger.info("No Instagram URLs found; ignoring")
        return "ok"

    shortcode = urlparse(urls[-1]).path.rstrip("/").split("/")[-1]
    logger.info(f"Processing shortcode: {shortcode}")

    load_resp = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": "Yuklanmoqda..."}
    )
    load_resp.raise_for_status()
    loading_message_id = load_resp.json()["result"]["message_id"]

    if send_cached(shortcode, chat_id):
        logger.info(f"Sent cached media for {shortcode} to chat {chat_id}")
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",
            json={"chat_id": chat_id, "message_id": loading_message_id},
        )
        return "ok"

    try:
        download_instagram_media(urls[-1])
        media_files = list(DOWNLOAD_ROOT.iterdir())
        logger.info(f"Downloaded media files: {[f.name for f in media_files]}")

        videos = [f for f in media_files if f.suffix.lower() in (".mp4", ".mov")]
        to_send = videos or [f for f in media_files if f.suffix.lower() in (".jpg", ".jpeg", ".png")]

        for media in to_send:
            upload_and_cache(media, shortcode, chat_id)
            logger.info(f"Uploaded and cached file: {media.name}")

        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage",
            json={"chat_id": chat_id, "message_id": loading_message_id},
        )

    except Exception as e:
        logger.error(f"Error handling webhook for {shortcode}: {e}", exc_info=True)
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={
                "chat_id": chat_id,
                "text": f"❗ Error: {e}",
            },
        )
    finally:
        cleanup_downloads()
        logger.info("Cleaned up downloads")

    return "ok"


if __name__ == "__main__":
    logger.info("Starting Flask app on http://0.0.0.0:5005")
    app.run(host="0.0.0.0", port=5005)
