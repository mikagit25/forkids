#!/usr/bin/env python3
"""
Create and manage YouTube playlists for Happy Bear Kids channel.

Usage:
    python3 manage_playlists.py --create-all       # create all playlists, save IDs
    python3 manage_playlists.py --list             # show current playlists with IDs
    python3 manage_playlists.py --add VIDEO_ID --video-type dance  # add video to playlists
"""

import argparse
import json
import logging
import pickle
import sys
import yaml
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
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


def get_youtube_service(config: dict, channel: str = "en"):
    """Auth: load token for the given channel (en/ar/id), fall back to pickle."""
    TOKEN_MAP = {
        "en": ROOT / "credentials" / "youtube_token.json",
        "ar": ROOT / "credentials" / "youtube_token_ar.json",
        "id": ROOT / "credentials" / "youtube_token_id.json",
    }
    PICKLE_MAP = {
        "en": ROOT / config["youtube"]["token"],
        "ar": ROOT / "credentials" / "token_ar.pickle",
        "id": ROOT / "credentials" / "token_id.pickle",
    }
    json_path   = TOKEN_MAP.get(channel, TOKEN_MAP["en"])
    pickle_path = PICKLE_MAP.get(channel, PICKLE_MAP["en"])
    creds = None

    if json_path.exists():
        try:
            t = json.loads(json_path.read_text())
            if t.get("refresh_token"):
                creds = Credentials(
                    token=t.get("access_token"),
                    refresh_token=t["refresh_token"],
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=t.get("client_id"),
                    client_secret=t.get("client_secret"),
                )
                log.info(f"Using JSON token [{channel}] (web OAuth)")
        except Exception as e:
            log.warning(f"JSON token load failed: {e}")

    if creds is None and pickle_path.exists():
        with open(pickle_path, "rb") as f:
            creds = pickle.load(f)
        log.info(f"Using pickle token [{channel}] (legacy)")

    if creds is None:
        log.error(f"No valid token found for channel '{channel}'.")
        sys.exit(1)

    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            log.error("Token expired. Re-authenticate.")
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


def add_to_playlists(youtube, video_id: str, video_type: str,
                     language: str = "en") -> int:
    """Add video to matching playlists. AR videos → AR playlists only."""
    playlists = load_playlists()
    count = 0

    for pl in playlists:
        pl_types = pl.get("video_types", [])
        pl_lang  = pl.get("language", "en")

        if language in ("ar", "id"):
            # AR/ID video: only add to same-language playlists
            if pl_lang != language:
                continue
            # Match {type}_ar or {type}_id, or just {type}_{lang}
            if (f"{video_type}_{language}" not in pl_types and
                    video_type not in pl_types):
                continue
        else:
            # EN video: only add to EN (non-language-tagged) playlists
            if pl_lang in ("ar", "id"):
                continue
            if video_type not in pl_types:
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
    """Create EN-only playlists (no language tag). AR/ID playlists use --create-ar / --create-id."""
    playlists = load_playlists()
    created = 0
    for pl in playlists:
        if pl.get("language") in ("ar", "id"):
            continue  # AR/ID playlists must be created on their own channel
        if pl.get("id") and not pl["id"].startswith("PLACEHOLDER"):
            log.info(f"  '{pl['name']}' already exists: {pl['id']}")
            continue
        playlist_id = create_playlist(youtube, pl["name"], pl["description"].strip())
        pl["id"] = playlist_id
        created += 1
    save_playlists(playlists)
    log.info(f"Created {created} new EN playlists, saved to {PLAYLISTS_PATH}")


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


CHANNEL_ID = "UCIOerrKr02oTAAk2_oOg0Xg"

# Channel sections: each entry maps to one section on the homepage
SECTIONS = [
    {
        "title": "🇸🇦 بالعربي — Arabic Videos",
        "playlist_keys": ["dance_ar", "counting_ar", "colors_ar", "shapes_ar"],
    },
    {
        "title": "🇬🇧 English Videos",
        "playlist_keys": ["dance", "numbers", "colors", "shapes"],
    },
]


def cmd_create_ar(youtube, force: bool = False):
    """Create Arabic playlists on the AR channel. Use --force to recreate."""
    playlists = load_playlists()
    created = 0
    for pl in playlists:
        if pl.get("language") != "ar":
            continue
        existing_id = pl.get("id", "")
        if existing_id and not existing_id.startswith("PLACEHOLDER") and not force:
            log.info(f"  '{pl['name']}' already exists: {existing_id}  (use --force to recreate)")
            continue
        playlist_id = create_playlist(youtube, pl["name"], pl.get("description", "").strip())
        pl["id"] = playlist_id
        created += 1
    save_playlists(playlists)
    log.info(f"Created {created} Arabic playlists")


def cmd_setup_sections(youtube):
    """Create channel homepage sections grouping EN and AR playlists."""
    playlists = load_playlists()
    pl_by_key = {p["key"]: p for p in playlists}

    # List existing sections to avoid duplicates
    existing = youtube.channelSections().list(
        part="snippet", channelId=CHANNEL_ID).execute()
    existing_titles = {s["snippet"].get("title", "") for s in existing.get("items", [])}
    log.info(f"Existing sections: {existing_titles}")

    for section in SECTIONS:
        title = section["title"]
        if title in existing_titles:
            log.info(f"  Section '{title}' already exists — skipping")
            continue

        # Collect playlist IDs for this section
        playlist_ids = []
        for key in section["playlist_keys"]:
            pl = pl_by_key.get(key)
            if pl and pl.get("id"):
                playlist_ids.append(pl["id"])
            else:
                log.warning(f"  Playlist '{key}' has no ID — run --create-all/--create-ar first")

        if not playlist_ids:
            log.warning(f"  No valid playlists for section '{title}' — skipping")
            continue

        body = {
            "snippet": {
                "channelId": CHANNEL_ID,
                "title":     title,
                "type":      "multiplePlaylists",
                "style":     "verticalList",
            },
            "contentDetails": {
                "playlists": playlist_ids,
            },
        }
        try:
            resp = youtube.channelSections().insert(
                part="snippet,contentDetails", body=body).execute()
            log.info(f"  Created section '{title}' (id={resp['id']}) with {len(playlist_ids)} playlists")
        except HttpError as e:
            log.error(f"  Failed to create section '{title}': {e}")

    log.info("Channel sections setup complete.")


def cmd_create_id(youtube, force: bool = False):
    """Create Indonesian playlists on the ID channel. Use --force to recreate."""
    playlists = load_playlists()
    created = 0
    for pl in playlists:
        if pl.get("language") != "id":
            continue
        existing_id = pl.get("id", "")
        if existing_id and not existing_id.startswith("PLACEHOLDER") and not force:
            log.info(f"  '{pl['name']}' already exists: {existing_id}  (use --force to recreate)")
            continue
        playlist_id = create_playlist(youtube, pl["name"], pl.get("description", "").strip())
        pl["id"] = playlist_id
        created += 1
    save_playlists(playlists)
    log.info(f"Created {created} ID playlists, saved to {PLAYLISTS_PATH}")


def main():
    parser = argparse.ArgumentParser(description="Manage YouTube playlists and channel sections")
    parser.add_argument("--create-all",     action="store_true", help="Create all playlists (EN token)")
    parser.add_argument("--create-ar",      action="store_true", help="Create Arabic playlists (AR token)")
    parser.add_argument("--create-id",      action="store_true", help="Create Indonesian playlists (ID token)")
    parser.add_argument("--setup-sections", action="store_true", help="Create EN/AR sections on channel homepage")
    parser.add_argument("--list",           action="store_true", help="Show all playlists")
    parser.add_argument("--add",            metavar="VIDEO_ID",  help="Add video to playlists")
    parser.add_argument("--video-type",     default="dance",     help="Video type for --add")
    parser.add_argument("--language",       default="en",        help="Language for --add (en/ar/id)")
    parser.add_argument("--channel",        default=None,        choices=["en","ar","id"],
                        help="Which channel token to use (default: matches --language)")
    parser.add_argument("--force",          action="store_true", help="Recreate playlists even if IDs exist")
    args = parser.parse_args()

    if not any([args.create_all, args.create_ar, args.create_id,
                args.setup_sections, args.list, args.add]):
        parser.print_help()
        return

    config  = load_config()
    # Auto-pick channel from action if not specified
    channel = args.channel
    if channel is None:
        if args.create_ar:   channel = "ar"
        elif args.create_id: channel = "id"
        elif args.add:       channel = args.language if args.language in ("ar","id") else "en"
        else:                channel = "en"
    youtube = get_youtube_service(config, channel)

    if args.create_all:
        cmd_create_all(youtube)
    if args.create_ar:
        cmd_create_ar(youtube, force=args.force)
    if args.create_id:
        cmd_create_id(youtube, force=args.force)
    if args.setup_sections:
        cmd_setup_sections(youtube)
    if args.list:
        cmd_list(youtube)
    if args.add:
        n = add_to_playlists(youtube, args.add, args.video_type, language=args.language)
        print(f"Added to {n} playlist(s).")


if __name__ == "__main__":
    main()
