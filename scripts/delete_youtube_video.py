#!/usr/bin/env python3
"""
Delete one or more YouTube videos by ID.

Usage:
    python3 scripts/delete_youtube_video.py --channel id NH3UD1Iubiw bKumAueBsYw
    python3 scripts/delete_youtube_video.py --channel id --dry-run NH3UD1Iubiw
"""

import argparse
import json
import sys
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

ROOT = Path(__file__).resolve().parent.parent

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
}

SCOPES = [
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]


def get_youtube_service(channel: str):
    ch = CHANNEL_CREDS.get(channel, CHANNEL_CREDS["en"])
    json_path = ch["json"]
    if not json_path.exists():
        print(f"Error: credentials not found at {json_path}")
        sys.exit(1)

    with open(json_path) as f:
        t = json.load(f)

    creds = Credentials(
        token=t.get("access_token"),
        refresh_token=t["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=t["client_id"],
        client_secret=t["client_secret"],
        scopes=SCOPES,
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        t["access_token"] = creds.token
        with open(json_path, "w") as f:
            json.dump(t, f, indent=2)

    return build("youtube", "v3", credentials=creds)


def get_video_title(youtube, video_id: str) -> str:
    try:
        resp = youtube.videos().list(part="snippet", id=video_id).execute()
        items = resp.get("items", [])
        if items:
            return items[0]["snippet"]["title"]
    except Exception:
        pass
    return "(unknown title)"


def main():
    parser = argparse.ArgumentParser(description="Delete YouTube videos by ID")
    parser.add_argument("video_ids", nargs="+", help="YouTube video ID(s) to delete")
    parser.add_argument("--channel", choices=["en", "ar", "id"], default="id",
                        help="Channel: en=Happy Bear Kids, ar=Arabic, id=Calm Classics (default: id)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be deleted without actually deleting")
    args = parser.parse_args()

    youtube = get_youtube_service(args.channel)

    ok = err = 0
    for vid in args.video_ids:
        title = get_video_title(youtube, vid)
        if args.dry_run:
            print(f"[DRY RUN] Would delete: {vid}  {title}")
            continue
        try:
            youtube.videos().delete(id=vid).execute()
            print(f"  Deleted: {vid}  {title}")
            ok += 1
        except HttpError as e:
            print(f"  ERROR deleting {vid}: {e}")
            err += 1

    if not args.dry_run:
        print(f"\nDone: {ok} deleted, {err} errors")


if __name__ == "__main__":
    main()
