#!/usr/bin/env python3
"""
Privatize (hide) all existing videos on the Classical Night Relax channel.
Uses the channel's uploads playlist to find all videos, then sets each to private.

This is a one-time operation for the channel rebranding pivot.

Usage:
  python3 scripts/hide_old_videos.py --dry-run   # show what would be hidden
  python3 scripts/hide_old_videos.py              # actually privatize all videos
  python3 scripts/hide_old_videos.py --status unlisted  # set to unlisted instead
"""
import argparse, json, logging, sys, time
from pathlib import Path

ROOT     = Path(__file__).resolve().parent.parent
CREDS    = ROOT / "credentials" / "youtube_token_id.json"

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def get_youtube():
    import datetime
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    if not CREDS.exists():
        log.error(f"No token: {CREDS}")
        log.error("Run: python3 scripts/reauth_youtube.py --channel id")
        sys.exit(1)

    t = json.loads(CREDS.read_text())
    creds = Credentials(
        token=t.get("access_token"),
        refresh_token=t["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=t["client_id"],
        client_secret=t["client_secret"],
        scopes=["https://www.googleapis.com/auth/youtube.force-ssl"],
    )
    if t.get("expires_at"):
        creds.expiry = datetime.datetime.utcfromtimestamp(float(t["expires_at"]))
    if not creds.valid and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        t["access_token"] = creds.token
        t["expires_at"] = creds.expiry.timestamp() if creds.expiry else 0
        CREDS.write_text(json.dumps(t, indent=2))

    return build("youtube", "v3", credentials=creds)


def get_uploads_playlist_id(youtube) -> str:
    res = youtube.channels().list(
        part="contentDetails,snippet", mine=True
    ).execute()
    item = res["items"][0]
    title = item["snippet"]["title"]
    uploads_id = item["contentDetails"]["relatedPlaylists"]["uploads"]
    log.info(f"Channel: {title} | Uploads playlist: {uploads_id}")
    return uploads_id


def get_all_video_ids(youtube, playlist_id: str) -> list[dict]:
    """Return list of {video_id, title} dicts from the uploads playlist."""
    videos = []
    page_token = None
    while True:
        req = youtube.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=page_token,
        )
        res = req.execute()
        for item in res.get("items", []):
            vid_id = item["contentDetails"]["videoId"]
            title  = item["snippet"]["title"]
            videos.append({"id": vid_id, "title": title})
        page_token = res.get("nextPageToken")
        if not page_token:
            break
        time.sleep(0.3)
    return videos


def get_video_statuses(youtube, video_ids: list[str]) -> dict:
    """Batch-fetch current privacy status for video IDs (max 50 per request)."""
    statuses = {}
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        res = youtube.videos().list(
            part="status",
            id=",".join(batch),
        ).execute()
        for item in res.get("items", []):
            statuses[item["id"]] = item["status"]["privacyStatus"]
    return statuses


def set_video_private(youtube, video_id: str, privacy: str = "private") -> bool:
    try:
        youtube.videos().update(
            part="status",
            body={
                "id": video_id,
                "status": {"privacyStatus": privacy},
            }
        ).execute()
        return True
    except Exception as e:
        log.error(f"  Failed {video_id}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Hide all videos on Classical Night Relax channel")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed, don't change")
    parser.add_argument("--status",  default="private", choices=["private", "unlisted"],
                        help="Target privacy status (default: private)")
    parser.add_argument("--skip-already", action="store_true",
                        help="Skip videos already at target status (default: True)",
                        default=True)
    args = parser.parse_args()

    youtube = get_youtube()

    log.info("Fetching uploads playlist…")
    playlist_id = get_uploads_playlist_id(youtube)

    log.info("Fetching all video IDs…")
    videos = get_all_video_ids(youtube, playlist_id)
    log.info(f"Found {len(videos)} videos on channel")

    if not videos:
        log.info("No videos found.")
        return

    # Fetch current statuses
    log.info("Checking current privacy statuses…")
    video_ids = [v["id"] for v in videos]
    statuses  = get_video_statuses(youtube, video_ids)

    # Filter to those that need changing
    to_change = [v for v in videos if statuses.get(v["id"]) != args.status]
    already   = len(videos) - len(to_change)

    log.info(f"\n{'─'*60}")
    log.info(f"  Total videos:    {len(videos)}")
    log.info(f"  Already {args.status}: {already}")
    log.info(f"  To change:       {len(to_change)}")
    log.info(f"{'─'*60}")

    if not to_change:
        log.info("Nothing to do.")
        return

    if args.dry_run:
        log.info(f"\n[DRY RUN] Would set {len(to_change)} videos to '{args.status}':")
        for v in to_change[:20]:
            cur = statuses.get(v["id"], "?")
            log.info(f"  {v['id']}  [{cur}] → {args.status}  {v['title'][:60]}")
        if len(to_change) > 20:
            log.info(f"  … and {len(to_change)-20} more")
        return

    log.info(f"\nSetting {len(to_change)} videos to '{args.status}'…")
    done, failed = 0, 0
    for i, v in enumerate(to_change, 1):
        cur = statuses.get(v["id"], "?")
        ok  = set_video_private(youtube, v["id"], args.status)
        if ok:
            done += 1
            log.info(f"  [{i}/{len(to_change)}] ✓ {v['id']}  [{cur}→{args.status}]  {v['title'][:55]}")
        else:
            failed += 1
        time.sleep(0.5)  # avoid quota burst

    log.info(f"\nDone: {done} hidden, {failed} failed out of {len(to_change)} total.")


if __name__ == "__main__":
    main()
