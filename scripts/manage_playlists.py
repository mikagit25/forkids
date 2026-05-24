#!/usr/bin/env python3
"""
Create and manage YouTube playlists for Happy Bear Kids channel.

Usage:
    python3 manage_playlists.py --create-all       # create all playlists, save IDs
    python3 manage_playlists.py --list             # show current playlists with IDs
    python3 manage_playlists.py --add VIDEO_ID --video-type dance  # add video to playlists
"""

import argparse
import logging
import pickle
import sys
import yaml
from pathlib import Path

from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

ROOT          = Path(__file__).resolve().parent.parent
CONFIG_PATH   = ROOT / "config" / "settings.yaml"
PLAYLISTS_PATH = ROOT / "config" / "playlists.yaml"

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

SCOPES = ["https://www.googleapis.com/auth/youtube"]


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def load_playlists() -> list:
    with open(PLAYLISTS_PATH) as f:
        data = yaml.safe_load(f)
    return data.get("playlists", [])


def save_playlists(playlists: list):
    with open(PLAYLISTS_PATH) as f:
        data = yaml.safe_load(f)
    data["playlists"] = playlists
    with open(PLAYLISTS_PATH, "w") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)


def get_youtube_service(config: dict):
    creds_path = ROOT / config["youtube"]["credentials"]
    token_path = ROOT / config["youtube"]["token"]

    if not creds_path.exists():
        raise FileNotFoundError(f"Credentials not found: {creds_path}")

    creds = None
    if token_path.exists():
        with open(token_path, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            log.error("Token expired and cannot be refreshed. Re-run auth_youtube.py.")
            sys.exit(1)

    return build("youtube", "v3", credentials=creds)


def create_playlist(youtube, name: str, description: str) -> str:
    body = {
        "snippet": {
            "title": name[:150],
            "description": description[:5000],
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus": "public",
        },
    }
    response = youtube.playlists().insert(part="snippet,status", body=body).execute()
    playlist_id = response["id"]
    log.info(f"Created playlist '{name}' → {playlist_id}")
    return playlist_id


def add_video_to_playlist(youtube, playlist_id: str, video_id: str) -> bool:
    try:
        youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video_id,
                    },
                }
            },
        ).execute()
        return True
    except HttpError as e:
        if e.resp.status == 409:
            log.info(f"  Already in playlist {playlist_id}")
            return True
        log.error(f"  Failed to add to playlist {playlist_id}: {e}")
        return False


def add_to_playlists(youtube, video_id: str, video_type: str) -> int:
    """Add video to all matching playlists. Returns number of playlists updated."""
    playlists = load_playlists()
    count = 0
    for pl in playlists:
        if video_type not in pl.get("video_types", []):
            continue
        playlist_id = pl.get("id")
        if not playlist_id:
            log.warning(f"Playlist '{pl['key']}' has no ID — run --create-all first")
            continue
        if add_video_to_playlist(youtube, playlist_id, video_id):
            log.info(f"  Added to playlist: {pl['name']}")
            count += 1
    return count


def cmd_create_all(youtube):
    playlists = load_playlists()
    created = 0
    for pl in playlists:
        if pl.get("id"):
            log.info(f"  '{pl['name']}' already exists: {pl['id']}")
            continue
        playlist_id = create_playlist(youtube, pl["name"], pl["description"].strip())
        pl["id"] = playlist_id
        created += 1
    save_playlists(playlists)
    log.info(f"Created {created} new playlists, saved to {PLAYLISTS_PATH}")


def cmd_list(youtube):
    playlists = load_playlists()
    print(f"\n{'─'*70}")
    print(f"{'Key':<14} {'ID':<28} Name")
    print(f"{'─'*70}")
    for pl in playlists:
        pid = pl.get("id") or "(not created)"
        types = ", ".join(pl.get("video_types", []))
        print(f"  {pl['key']:<12} {pid:<28} {pl['name']}")
        print(f"  {'':12} {'':28} types: {types}")
    print(f"{'─'*70}\n")


def main():
    parser = argparse.ArgumentParser(description="Manage YouTube playlists")
    parser.add_argument("--create-all",  action="store_true", help="Create all playlists")
    parser.add_argument("--list",        action="store_true", help="Show all playlists")
    parser.add_argument("--add",         metavar="VIDEO_ID",  help="Add video to playlists")
    parser.add_argument("--video-type",  default="dance",     help="Video type for --add")
    args = parser.parse_args()

    if not any([args.create_all, args.list, args.add]):
        parser.print_help()
        return

    config  = load_config()
    youtube = get_youtube_service(config)

    if args.create_all:
        cmd_create_all(youtube)
    if args.list:
        cmd_list(youtube)
    if args.add:
        n = add_to_playlists(youtube, args.add, args.video_type)
        print(f"Added to {n} playlist(s).")


if __name__ == "__main__":
    main()
