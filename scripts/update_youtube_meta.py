#!/usr/bin/env python3
"""
Update description, title, tags, and/or thumbnail for already-uploaded YouTube videos.

Usage:
    # Update all videos in uploaded/ that have a meta sidecar
    python3 scripts/update_youtube_meta.py --all

    # Update a specific video by YouTube ID
    python3 scripts/update_youtube_meta.py --video-id g-IvIO5ovIE --meta uploaded/meta_dance_shapes_rainbow_20260529.yaml

    # Dry run
    python3 scripts/update_youtube_meta.py --all --dry-run
"""

import argparse
import logging
import sys
from pathlib import Path

import yaml
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from upload_youtube import get_youtube_service, load_config

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

UPLOADED_DIR = ROOT / "uploaded"


def load_meta(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


class QuotaExceeded(Exception):
    pass


def update_video(youtube, video_id: str, meta: dict, thumb_path: Path | None,
                 dry_run: bool = False) -> bool:
    title       = meta.get("title", "")
    description = meta.get("description", "")
    tags        = meta.get("tags", [])

    print(f"\n  Video ID: {video_id}")
    print(f"  Title:    {title[:80]}")
    print(f"  Desc len: {len(description)} chars")
    print(f"  Thumb:    {thumb_path.name if thumb_path and thumb_path.exists() else 'none'}")

    if dry_run:
        print("  [DRY RUN] would update")
        return True

    try:
        body = {
            "id": video_id,
            "snippet": {
                "title":       title[:100],
                "description": description[:5000],
                "tags":        tags[:500],
                "categoryId":  "27",
            },
        }
        youtube.videos().update(part="snippet", body=body).execute()
        print("  Snippet updated.")
    except HttpError as e:
        if "quotaExceeded" in str(e):
            raise QuotaExceeded("YouTube quota exceeded — try again tomorrow")
        log.error(f"  Snippet update failed: {e}")
        return False

    if thumb_path and thumb_path.exists():
        try:
            media = MediaFileUpload(str(thumb_path), mimetype="image/png")
            youtube.thumbnails().set(videoId=video_id, media_body=media).execute()
            print("  Thumbnail updated.")
        except HttpError as e:
            if "quotaExceeded" in str(e):
                log.warning("  Quota exceeded on thumbnail — snippet was saved")
            else:
                log.warning(f"  Thumbnail update failed: {e}")

    return True


def find_video_id(meta: dict, stem: str) -> str | None:
    vid = meta.get("youtube_id") or meta.get("video_id")
    if vid:
        return vid
    # Check uploaded_log.yaml if it exists
    log_path = ROOT / "uploaded" / "uploaded_log.yaml"
    if log_path.exists():
        with open(log_path) as f:
            log_data = yaml.safe_load(f) or {}
        return log_data.get(stem)
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all",      action="store_true", help="Update all uploaded videos with meta sidecars")
    parser.add_argument("--video-id", help="Specific YouTube video ID")
    parser.add_argument("--meta",     help="Path to meta YAML file (use with --video-id)")
    parser.add_argument("--dry-run",  action="store_true")
    parser.add_argument("--force",    action="store_true", help="Re-update even if meta_updated=True")
    args = parser.parse_args()

    config  = load_config()
    youtube = get_youtube_service(config)

    if args.video_id and args.meta:
        meta = load_meta(Path(args.meta))
        thumb = Path(args.meta).parent / f"thumb_{Path(args.meta).stem.replace('meta_', '')}.png"
        update_video(youtube, args.video_id, meta, thumb if thumb.exists() else None,
                     dry_run=args.dry_run)
        return

    if args.all:
        metas = sorted(UPLOADED_DIR.glob("meta_*.yaml"))
        # Only process videos not yet marked as meta_updated
        pending = []
        for mp in metas:
            m = load_meta(mp)
            if not m.get("youtube_id"):
                continue
            if m.get("meta_updated") and not args.force:
                continue
            pending.append(mp)

        print(f"Found {len(metas)} meta files | {len(pending)} need update")
        updated = skipped = failed = 0
        try:
            for meta_path in pending:
                stem = meta_path.stem.replace("meta_", "")
                meta = load_meta(meta_path)
                video_id = meta["youtube_id"]
                thumb = UPLOADED_DIR / f"thumb_{stem}.png"
                ok = update_video(youtube, video_id, meta,
                                  thumb if thumb.exists() else None,
                                  dry_run=args.dry_run)
                if ok:
                    if not args.dry_run:
                        meta["meta_updated"] = True
                        with open(meta_path, "w") as f:
                            yaml.dump(meta, f, allow_unicode=True, default_flow_style=False)
                    updated += 1
                else:
                    failed += 1
        except QuotaExceeded as e:
            print(f"\n⚠️  {e}")
            print(f"  Completed {updated} before quota ran out.")
            print(f"  Remaining: {len(pending) - updated - failed} — run again tomorrow.")
        print(f"\nDone: {updated} updated, {failed} failed, {skipped} skipped")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
