#!/usr/bin/env python3
"""
Upload a video to YouTube Kids channel.

Usage:
    python upload_youtube.py --file output/video.mp4 --theme fruits
    python upload_youtube.py --file output/video.mp4 --title "My Title" --status unlisted
"""

import os
import sys
import time
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

# Per-channel credential files (token JSON + pickle fallback)
CHANNEL_CREDS = {
    "en": {
        "json":   ROOT / "credentials" / "youtube_token.json",
        "pickle": ROOT / "credentials" / "token.pickle",
    },
    "ar": {
        "json":   ROOT / "credentials" / "youtube_token_ar.json",
        "pickle": ROOT / "credentials" / "token_ar.pickle",
    },
    "id": {
        "json":   ROOT / "credentials" / "youtube_token_id.json",
        "pickle": ROOT / "credentials" / "token_id.pickle",
    },
    "sd": {
        "json":   ROOT / "credentials" / "youtube_token_ar.json",
        "pickle": ROOT / "credentials" / "token_ar.pickle",
    },
}

CHANNEL_METADATA = {
    "en": ROOT / "config" / "channel_metadata.yaml",
    "ar": ROOT / "config" / "channel_metadata_ar.yaml",
    "id": ROOT / "config" / "channel_metadata_id.yaml",
    "sd": ROOT / "sacred_drift" / "config" / "channel_metadata_sd.yaml",
}

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
    """Merge base tags + video-specific tags, deduplicated.
    YouTube limits: each tag ≤30 chars, ≤500 cumulative chars, ≤30 tags total."""
    base = meta.get("video_defaults", {}).get("tags_base", [])
    seen: set = set()
    result: list = []
    total_chars = 0
    for t in extra_tags + base:  # video tags take priority over base
        if t and t not in seen and len(t) <= 30:
            if len(result) >= 30 or total_chars + len(t) > 500:
                break
            seen.add(t)
            result.append(t)
            total_chars += len(t)
    return result


def load_playlists() -> dict:
    with open(PLAYLISTS_PATH) as f:
        return yaml.safe_load(f)


def get_youtube_service(config: dict, channel: str = "en"):
    import json as _json, datetime as _dt
    ch_creds  = CHANNEL_CREDS.get(channel, CHANNEL_CREDS["en"])
    json_path   = ch_creds["json"]
    pickle_path = ch_creds["pickle"]

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
                expires_at = t.get("expires_at")
                if expires_at:
                    creds.expiry = _dt.datetime.utcfromtimestamp(float(expires_at))
                log.info(f"Using JSON token [{channel}] (web OAuth)")
        except Exception as e:
            log.warning(f"JSON token load failed [{channel}]: {e} — falling back to pickle")
            creds = None

    # Fall back to legacy pickle token
    if creds is None and pickle_path.exists():
        with open(pickle_path, "rb") as f:
            creds = pickle.load(f)
        log.info(f"Using pickle token [{channel}] (legacy)")

    if not creds:
        raise RuntimeError(
            f"No token found for channel '{channel}'. Run:\n"
            f"  python3 scripts/reauth_youtube.py --channel {channel}"
        )

    if not creds.valid:
        if creds.expired and creds.refresh_token:
            log.info(f"Refreshing access token [{channel}]...")
            creds.refresh(Request())
            if json_path.exists() and json_path.stat().st_size > 2:
                with open(json_path) as f:
                    t = _json.load(f)
                t["access_token"] = creds.token
                t["expires_at"] = creds.expiry.timestamp() if creds.expiry else 0
                import os as _os
                tmp = json_path.with_suffix(".tmp")
                with open(tmp, "w") as f:
                    _json.dump(t, f, indent=2)
                _os.replace(str(tmp), str(json_path))
            else:
                with open(pickle_path, "wb") as f:
                    pickle.dump(creds, f)
        else:
            raise RuntimeError(
                f"Token invalid for channel '{channel}'. Run:\n"
                f"  python3 scripts/reauth_youtube.py --channel {channel}"
            )

    return build("youtube", "v3", credentials=creds)


def _wait_for_processing(youtube, video_id: str, max_wait_sec: int = 600) -> dict:
    """Poll video status until YouTube finishes processing. Returns status dict."""
    deadline = time.time() + max_wait_sec
    interval = 30
    while time.time() < deadline:
        try:
            resp = youtube.videos().list(part="status", id=video_id).execute()
            if resp.get("items"):
                st = resp["items"][0]["status"]
                upload_status = st.get("uploadStatus", "")
                log.info(f"  Stage check: uploadStatus={upload_status}")
                if upload_status in ("processed", "rejected", "failed"):
                    return st
        except Exception as e:
            log.warning(f"  Stage check poll error: {e}")
        time.sleep(interval)
    log.warning(f"  Stage check: timeout after {max_wait_sec}s — assuming clean")
    return {"uploadStatus": "timeout"}


def _set_privacy(youtube, video_id: str, privacy: str, publish_at: Optional[str] = None) -> None:
    """Update video privacy (and optional scheduled publishAt)."""
    body: dict = {"privacyStatus": privacy}
    if publish_at:
        body["publishAt"] = publish_at
    youtube.videos().update(
        part="status",
        body={"id": video_id, "status": body},
    ).execute()
    suffix = f" (scheduled {publish_at})" if publish_at else ""
    log.info(f"  Privacy → {privacy}{suffix}")


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
    channel: str = "en",
    made_for_kids: bool = True,
    stage_check: bool = False,
) -> Optional[str]:
    if config is None:
        config = load_config()

    youtube = get_youtube_service(config, channel=channel)

    # stage_check: always upload private first, make public only after copyright scan
    desired_status   = status
    desired_publish_at = publish_at

    video_status: dict = {
        "madeForKids": made_for_kids,
        "selfDeclaredMadeForKids": made_for_kids,
    }
    if stage_check:
        video_status["privacyStatus"] = "private"
    elif publish_at:
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
            "categoryId": "10" if channel == "id" else "27",
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

    if thumbnail_path and Path(thumbnail_path).exists() and Path(thumbnail_path).stat().st_size > 0:
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path, mimetype="image/png"),
            ).execute()
            log.info("Thumbnail set.")
        except Exception as thumb_exc:
            log.warning(f"Thumbnail upload failed (video already uploaded): {thumb_exc}")
    elif thumbnail_path and Path(thumbnail_path).exists() and Path(thumbnail_path).stat().st_size == 0:
        log.warning(f"Thumbnail is 0 bytes, skipping: {thumbnail_path}")

    # Stage check: wait for YouTube to scan, then publish or delete
    if stage_check:
        log.info("Stage check: waiting for YouTube copyright scan (~5 min)…")
        st = _wait_for_processing(youtube, video_id)
        upload_status  = st.get("uploadStatus", "timeout")
        rejection      = st.get("rejectionReason", "")

        if upload_status == "rejected" and rejection in ("claim", "copyright"):
            log.error(f"  COPYRIGHT BLOCK detected (reason={rejection}) — deleting {video_id}")
            try:
                youtube.videos().delete(id=video_id).execute()
                log.info(f"  Video {video_id} deleted.")
            except Exception as del_e:
                log.warning(f"  Delete failed: {del_e}")
            return None  # caller checks for None → exit(2)

        if upload_status == "rejected":
            log.warning(f"  Video rejected (reason={rejection}) — not copyright, proceeding")

        # Clean — set final visibility
        try:
            final_privacy = desired_status if not desired_publish_at else "private"
            _set_privacy(youtube, video_id, final_privacy, desired_publish_at)
        except Exception as e:
            log.warning(f"  Could not set final privacy: {e}")

    # Add to playlists
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from manage_playlists import add_to_playlists
        n = add_to_playlists(youtube, video_id, video_type, language=language)
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
                        help="BCP-47 language code: en, ar, id, etc.")
    parser.add_argument("--channel", default=None,
                        choices=["en", "ar", "id", "sd"],
                        help="Target YouTube channel. Defaults to matching --language (ar→ar, id→id, else en).")
    parser.add_argument("--meta-path", default=None,
                        help="Path to meta YAML sidecar — video ID will be written back after upload")
    parser.add_argument("--made-for-kids", default=None, choices=["true", "false"],
                        help="Override madeForKids flag (default: true for EN/AR, false for id/CNR)")
    parser.add_argument("--stage-check", action="store_true",
                        help="Upload private first, wait for YouTube copyright scan, then publish")
    args = parser.parse_args()

    config   = load_config()

    # Auto-detect channel from language if not specified
    ch = args.channel or (args.language if args.language in ("ar", "id", "sd") else "en")
    meta_path_cfg = CHANNEL_METADATA.get(ch, CHANNEL_METADATA["en"])
    with open(meta_path_cfg) as _f:
        meta = yaml.safe_load(_f)

    channel_name = meta.get("channel", {}).get("name", config["channel"]["name"])
    title_tpl    = config["youtube"]["title_template"]
    title = args.title or title_tpl.format(
        theme=args.theme.capitalize(),
        channel_name=channel_name,
    )

    description = args.description or build_description(args.video_type, args.theme, meta)

    extra_tags = [t.strip() for t in args.tags.split(",")] if args.tags else []
    tags = build_tags(args.video_type, args.theme, extra_tags, meta)

    # Determine made_for_kids: explicit flag > channel default (CNR=false, kids=true)
    if args.made_for_kids is not None:
        made_for_kids = args.made_for_kids == "true"
    else:
        made_for_kids = ch not in ("id", "sd")   # adult channels → false

    video_id = upload_video(
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
        channel=ch,
        made_for_kids=made_for_kids,
        stage_check=args.stage_check,
    )

    if video_id is None and args.stage_check:
        # Copyright block — write flag to meta so publish_queue skips this video
        if args.meta_path:
            meta_path = Path(args.meta_path)
            if meta_path.exists():
                try:
                    with open(meta_path) as f:
                        m = yaml.safe_load(f) or {}
                    m["upload_blocked"] = "copyright_claim_detected — video deleted by stage_check"
                    tmp = meta_path.with_suffix(".yaml.tmp")
                    with open(tmp, "w") as f:
                        yaml.dump(m, f, allow_unicode=True, default_flow_style=False)
                    tmp.replace(meta_path)
                    log.info(f"Marked upload_blocked in {meta_path.name}")
                except Exception as e:
                    log.warning(f"Failed to write upload_blocked to meta: {e}")
        sys.exit(2)  # distinct exit code for copyright rejection

    if args.meta_path and video_id:
        meta_path = Path(args.meta_path)
        if meta_path.exists():
            try:
                with open(meta_path) as f:
                    m = yaml.safe_load(f) or {}
                m["youtube_id"] = video_id
                tmp = meta_path.with_suffix(".yaml.tmp")
                with open(tmp, "w") as f:
                    yaml.dump(m, f, allow_unicode=True, default_flow_style=False)
                tmp.replace(meta_path)
                log.info(f"Saved youtube_id={video_id} → {meta_path.name}")
            except Exception as e:
                log.warning(f"Failed to save youtube_id to meta: {e}")


# Fix missing import for Optional
from typing import Optional

if __name__ == "__main__":
    main()
