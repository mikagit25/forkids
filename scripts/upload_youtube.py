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
CONFIG_PATH   = ROOT / "config" / "settings.yaml"
METADATA_PATH = ROOT / "config" / "channel_metadata.yaml"
PLAYLISTS_PATH = ROOT / "config" / "playlists.yaml"

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def load_metadata() -> dict:
    if METADATA_PATH.exists():
        with open(METADATA_PATH) as f:
            return yaml.safe_load(f)
    return {}


def build_description(video_type: str, theme: str, meta: dict) -> str:
    """Build full video description from channel_metadata.yaml template."""
    descs = meta.get("video_descriptions", {})
    video_desc = descs.get(video_type, {}).get(theme, "") or \
                 descs.get(video_type, {}).get("animals", "") or \
                 "Fun educational video for kids!"
    template = meta.get("video_defaults", {}).get("description_template", "{video_description}")
    return template.format(video_description=video_desc)


def build_tags(video_type: str, theme: str, extra_tags: list, meta: dict) -> list:
    """Merge base tags + type-specific tags."""
    base = meta.get("video_defaults", {}).get("tags_base", [])
    return base + extra_tags


def load_playlists() -> dict:
    with open(PLAYLISTS_PATH) as f:
        return yaml.safe_load(f)


def get_youtube_service(config: dict):
    import json as _json, datetime as _dt
    creds_path  = ROOT / config["youtube"]["credentials"]
    pickle_path = ROOT / config["youtube"]["token"]
    json_path   = ROOT / "credentials" / "youtube_token.json"  # web OAuth token

    creds = None

    # Prefer JSON token (renewed via web OAuth link in Telegram)
    if json_path.exists():
        try:
            with open(json_path) as f:
                t = _json.load(f)
            if t.get("refresh_token"):
                creds = Credentials(
                    token=t.get("access_token"),
                    refresh_token=t["refresh_token"],
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=t["client_id"],
                    client_secret=t["client_secret"],
                    scopes=SCOPES,
                )
                # Set expiry so the library knows whether to refresh
                expires_at = t.get("expires_at")
                if expires_at:
                    creds.expiry = _dt.datetime.utcfromtimestamp(float(expires_at))
                log.info("Using JSON token (web OAuth)")
        except Exception as e:
            log.warning(f"JSON token load failed: {e} — falling back to pickle")
            creds = None

    # Fall back to legacy pickle token
    if creds is None and pickle_path.exists():
        with open(pickle_path, "rb") as f:
            creds = pickle.load(f)
        log.info("Using pickle token (legacy)")

    if not creds:
        raise RuntimeError(
            "No token found. Renew via Telegram link or run:\n"
            "  python3 scripts/reauth_youtube.py"
        )

    if not creds.valid:
        if creds.expired and creds.refresh_token:
            log.info("Refreshing access token...")
            creds.refresh(Request())
            # Write back to whichever format we loaded from
            if json_path.exists() and json_path.stat().st_size > 2:
                with open(json_path) as f:
                    t = _json.load(f)
                t["access_token"] = creds.token
                t["expires_at"] = creds.expiry.timestamp() if creds.expiry else 0
                with open(json_path, "w") as f:
                    _json.dump(t, f, indent=2)
            else:
                with open(pickle_path, "wb") as f:
                    pickle.dump(creds, f)
        else:
            raise RuntimeError(
                "Token invalid and cannot refresh. Renew via Telegram link or run:\n"
                "  python3 scripts/reauth_youtube.py"
            )

    return build("youtube", "v3", credentials=creds)


def upload_video(
    file_path: str,
    title: str,
    description: str,
    tags: list,
    status: str = "public",
    thumbnail_path: Optional[str] = None,
    video_type: str = "dance",
    publish_at: Optional[str] = None,
    config: dict = None,
    language: str = "en",
) -> str:
    if config is None:
        config = load_config()

    youtube = get_youtube_service(config)

    video_status: dict = {
        "madeForKids": True,
        "selfDeclaredMadeForKids": True,
    }
    if publish_at:
        # Scheduled: private until publishAt
        video_status["privacyStatus"] = "private"
        video_status["publishAt"] = publish_at
    else:
        video_status["privacyStatus"] = status

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags[:500],
            "categoryId": "27",       # Education
            "defaultLanguage": language,
            "defaultAudioLanguage": language,
        },
        "status": video_status,
    }

    media = MediaFileUpload(
        file_path, chunksize=10 * 1024 * 1024,
        resumable=True, mimetype="video/mp4"
    )

    log.info(f"Uploading: {Path(file_path).name}  [{publish_at or status}]")
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

    # Add to playlists
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from manage_playlists import add_to_playlists
        n = add_to_playlists(youtube, video_id, video_type)
        if n:
            log.info(f"Added to {n} playlist(s).")
    except Exception as exc:
        log.warning(f"Playlist add skipped: {exc}")

    return video_id


def main():
    parser = argparse.ArgumentParser(description="Upload video to YouTube")
    parser.add_argument("--file", required=True, help="MP4 file path")
    parser.add_argument("--video-type", default="dance",
                        help="video_type (dance, abc, numbers, short_letter, etc.)")
    parser.add_argument("--theme", default="animals", help="Theme (animals, fruits, shapes)")
    parser.add_argument("--title", default=None, help="Custom title (overrides template)")
    parser.add_argument("--description", default=None, help="Custom description (overrides template)")
    parser.add_argument("--tags", default=None, help="Extra comma-separated tags")
    parser.add_argument("--status", default="public",
                        choices=["public", "unlisted", "private"])
    parser.add_argument("--thumbnail",   default=None, help="Thumbnail PNG path")
    parser.add_argument("--publish-at",  default=None,
                        help="ISO 8601 UTC datetime to schedule (e.g. 2026-05-26T09:00:00Z)")
    parser.add_argument("--language", default="en",
                        help="BCP-47 language code: en, ar, etc.")
    args = parser.parse_args()

    config   = load_config()
    meta     = load_metadata()

    channel_name = config["channel"]["name"]
    title_tpl    = config["youtube"]["title_template"]
    title = args.title or title_tpl.format(
        theme=args.theme.capitalize(),
        channel_name=channel_name,
    )

    description = args.description or build_description(args.video_type, args.theme, meta)

    extra_tags = [t.strip() for t in args.tags.split(",")] if args.tags else []
    tags = build_tags(args.video_type, args.theme, extra_tags, meta)

    upload_video(
        file_path=args.file,
        title=title,
        description=description,
        tags=tags,
        status=args.status,
        thumbnail_path=args.thumbnail,
        video_type=args.video_type,
        publish_at=args.publish_at,
        config=config,
        language=args.language,
    )


# Fix missing import for Optional
from typing import Optional

if __name__ == "__main__":
    main()
