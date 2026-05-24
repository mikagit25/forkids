#!/usr/bin/env python3
"""
Upload a video to YouTube Kids channel.

Usage:
    python upload_youtube.py --file output/video.mp4 --theme fruits
    python upload_youtube.py --file output/video.mp4 --title "My Title" --status unlisted
"""

import os
import sys
import argparse
import logging
import pickle
from pathlib import Path
from typing import Optional

import yaml
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "settings.yaml"
PLAYLISTS_PATH = ROOT / "config" / "playlists.yaml"

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube"]


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def load_playlists() -> dict:
    with open(PLAYLISTS_PATH) as f:
        return yaml.safe_load(f)


def get_youtube_service(config: dict):
    creds_path = ROOT / config["youtube"]["credentials"]
    token_path = ROOT / config["youtube"]["token"]

    if not creds_path.exists():
        raise FileNotFoundError(
            f"YouTube credentials not found: {creds_path}\n"
            "Download OAuth 2.0 client JSON from Google Cloud Console."
        )

    creds = None
    if token_path.exists():
        with open(token_path, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            log.info("Refreshing access token...")
            creds.refresh(Request())
        else:
            log.info("Running OAuth flow (opens browser)...")
            flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
            creds = flow.run_local_server(port=8765)

        token_path.parent.mkdir(exist_ok=True)
        with open(token_path, "wb") as f:
            pickle.dump(creds, f)
        log.info(f"Token saved: {token_path}")

    return build("youtube", "v3", credentials=creds)


def upload_video(
    file_path: str,
    title: str,
    description: str,
    tags: list,
    status: str = "public",
    thumbnail_path: Optional[str] = None,
    config: dict = None,
) -> str:
    if config is None:
        config = load_config()

    youtube = get_youtube_service(config)

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags[:500],
            "categoryId": "22",       # People & Blogs (common for kids)
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus": status,
            "madeForKids": True,
            "selfDeclaredMadeForKids": True,
        },
    }

    media = MediaFileUpload(
        file_path, chunksize=10 * 1024 * 1024,
        resumable=True, mimetype="video/mp4"
    )

    log.info(f"Uploading: {Path(file_path).name}  [{status}]")
    log.info(f"Title: {title}")

    request = youtube.videos().insert(
        part=",".join(body.keys()), body=body, media_body=media
    )

    video_id = None
    while video_id is None:
        try:
            status_obj, response = request.next_chunk()
            if status_obj:
                pct = int(status_obj.progress() * 100)
                log.info(f"  Upload: {pct}%")
            if response:
                video_id = response["id"]
        except HttpError as e:
            log.error(f"Upload failed: {e}")
            raise

    log.info(f"Uploaded: https://youtu.be/{video_id}")

    if thumbnail_path and Path(thumbnail_path).exists():
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(thumbnail_path, mimetype="image/png"),
        ).execute()
        log.info("Thumbnail set.")

    return video_id


def main():
    parser = argparse.ArgumentParser(description="Upload video to YouTube")
    parser.add_argument("--file", required=True, help="MP4 file path")
    parser.add_argument("--theme", default="fruits", help="Theme (for title/tags lookup)")
    parser.add_argument("--title", default=None, help="Custom title")
    parser.add_argument("--description", default=None, help="Custom description")
    parser.add_argument("--tags", default=None, help="Comma-separated tags")
    parser.add_argument("--status", default="public",
                        choices=["public", "unlisted", "private"])
    parser.add_argument("--thumbnail", default=None, help="Thumbnail PNG path")
    args = parser.parse_args()

    config = load_config()
    playlists = load_playlists()
    theme_data = playlists["themes"].get(args.theme, {})

    channel_name = config["channel"]["name"]
    title_tpl = config["youtube"]["title_template"]
    title = args.title or title_tpl.format(
        theme=args.theme.capitalize(),
        channel_name=channel_name,
    )
    description = args.description or theme_data.get("description", f"Kids video: {args.theme}")
    if args.tags:
        tags = [t.strip() for t in args.tags.split(",")]
    else:
        tags = theme_data.get("tags", []) + ["kids", "babies", "sensory", "toddler"]

    upload_video(
        file_path=args.file,
        title=title,
        description=description,
        tags=tags,
        status=args.status,
        thumbnail_path=args.thumbnail,
        config=config,
    )


# Fix missing import for Optional
from typing import Optional

if __name__ == "__main__":
    main()
