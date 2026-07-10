#!/usr/bin/env python3
"""
Backfill uploaded videos into new playlists.
Reads config/pending_playlist_additions.json and adds each video.
Run after daily quota resets (midnight Pacific time).

Usage:
  python3 scripts/backfill_playlists.py
  python3 scripts/backfill_playlists.py --dry-run
  python3 scripts/backfill_playlists.py --channel ar   # process only AR additions
"""
import argparse, json, logging, sys
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

ROOT = Path(__file__).resolve().parent.parent
PENDING_PATH = ROOT / "config" / "pending_playlist_additions.json"

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

TOKEN_MAP = {
    "en": ROOT / "credentials" / "youtube_token.json",
    "ar": ROOT / "credentials" / "youtube_token_ar.json",
    "id": ROOT / "credentials" / "youtube_token_id.json",
}


def get_service(channel: str):
    import json as _json
    path = TOKEN_MAP[channel]
    t = _json.loads(path.read_text())
    creds = Credentials(
        token=t.get("access_token"),
        refresh_token=t["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=t.get("client_id"),
        client_secret=t.get("client_secret"),
    )
    if not creds.valid and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("youtube", "v3", credentials=creds)


def add_video_to_playlist(youtube, playlist_id: str, video_id: str) -> bool:
    try:
        youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {"kind": "youtube#video", "videoId": video_id},
                }
            },
        ).execute()
        return True
    except HttpError as e:
        if e.resp.status == 409:
            log.info(f"  Already in playlist {playlist_id}")
            return True
        if e.resp.status == 403 and "quotaExceeded" in str(e):
            log.error("Quota exceeded — stop and resume tomorrow")
            sys.exit(2)
        log.error(f"  HTTP {e.resp.status}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run",  action="store_true")
    parser.add_argument("--channel",  choices=["en", "ar", "id", "all"], default="all")
    parser.add_argument("--limit",    type=int, default=0, help="Max additions (0=all)")
    args = parser.parse_args()

    if not PENDING_PATH.exists():
        log.info("No pending additions file found — nothing to do.")
        return

    with open(PENDING_PATH) as f:
        additions = json.load(f)

    if args.channel != "all":
        additions = [a for a in additions if a["lang"] == args.channel]

    log.info(f"Pending additions: {len(additions)}")

    # Group by channel so we only create one service per channel
    by_channel: dict[str, list] = {"en": [], "ar": [], "id": []}
    for a in additions:
        by_channel[a["lang"]].append(a)

    done = []
    failed = []
    total_done = 0

    for ch, items in by_channel.items():
        if not items:
            continue
        if args.channel not in ("all", ch):
            continue
        log.info(f"\n--- Channel: {ch.upper()} ({len(items)} additions) ---")
        try:
            yt = get_service(ch)
        except Exception as e:
            log.error(f"  Could not auth {ch}: {e}")
            continue

        for item in items:
            if args.limit and total_done >= args.limit:
                break
            vid_id = item["video_id"]
            pl_id  = item["playlist_id"]
            pl_key = item["playlist_key"]
            log.info(f"  [{ch}] {vid_id} → {pl_key}")
            if args.dry_run:
                done.append(item)
                total_done += 1
                continue
            ok = add_video_to_playlist(yt, pl_id, vid_id)
            if ok:
                done.append(item)
                total_done += 1
            else:
                failed.append(item)

    # Remove done items from pending
    remaining = [a for a in additions if a not in done]
    # Re-merge with any channel-filtered-out items
    if args.channel != "all":
        other_lang = [a for a in json.loads(PENDING_PATH.read_text())
                      if a["lang"] != args.channel]
        remaining = other_lang + remaining

    if remaining:
        with open(PENDING_PATH, "w") as f:
            json.dump(remaining, f, indent=2)
        log.info(f"\n{len(remaining)} additions still pending — saved for next run")
    else:
        PENDING_PATH.unlink()
        log.info(f"\nAll done! {PENDING_PATH.name} removed.")

    log.info(f"Added: {total_done}   Failed: {len(failed)}")


if __name__ == "__main__":
    main()
