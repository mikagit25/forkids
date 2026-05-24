#!/usr/bin/env python3
"""
Publish videos from the output/queue/ directory to YouTube.

Reads meta_*.yaml sidecar files for full metadata (title, tags, upload_day,
upload_time). Falls back to weekly_plan.yaml matching if no sidecar found.

Usage:
    python3 publish_queue.py              # upload all, schedule from plan
    python3 publish_queue.py --dry-run    # show what would be uploaded
    python3 publish_queue.py --limit 6    # upload at most N videos
    python3 publish_queue.py --no-schedule  # upload as public immediately
"""

import argparse
import shutil
import subprocess
import sys
import yaml
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUEUE_DIR    = ROOT / "output" / "queue"
UPLOADED_DIR = ROOT / "uploaded"
PLAN_PATH    = ROOT / "config" / "weekly_plan.yaml"

DAY_OFFSETS = {
    "monday": 0, "tuesday": 1, "wednesday": 2,
    "thursday": 3, "friday": 4, "saturday": 5,
}


def load_plan() -> list:
    if not PLAN_PATH.exists():
        return []
    with open(PLAN_PATH) as f:
        return yaml.safe_load(f).get("videos", [])


def load_sidecar(mp4_path: Path) -> dict | None:
    meta_path = mp4_path.parent / f"meta_{mp4_path.stem}.yaml"
    if meta_path.exists():
        with open(meta_path) as f:
            return yaml.safe_load(f)
    return None


def match_metadata(filename: str, plan: list) -> dict:
    """Fallback: find best matching plan entry for a queue file by type+theme."""
    parts = filename.replace(".mp4", "").split("_")
    video_type = parts[0] if parts else "dance"
    theme = parts[1] if len(parts) > 1 else "animals"

    for entry in plan:
        if (entry.get("video_type") == video_type and
                entry.get("theme", "animals") == theme):
            return entry

    return {
        "title": f"Happy Bear Kids — {theme.capitalize()} {video_type.capitalize()}",
        "status": "unlisted",
        "tags": ["kids", "children", theme, video_type],
        "video_type": video_type,
        "theme": theme,
    }


def calc_publish_at(upload_day: str, upload_time: str) -> str | None:
    """
    Calculate UTC ISO 8601 publishAt for the next occurrence of upload_day.

    The weekly plan runs Mon-Sat. We treat the current week as starting on
    the most recent Sunday and map Mon=+1 day, Tue=+2, ... Sat=+6.
    If the calculated time is already past, push to next week.
    """
    day_offset = DAY_OFFSETS.get(upload_day.lower())
    if day_offset is None:
        return None

    now = datetime.now(timezone.utc)
    # Find the most recent Sunday (weekday 6) at 00:00 UTC
    days_since_sunday = (now.weekday() + 1) % 7  # Mon=1..Sun=0
    last_sunday = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_since_sunday)

    # Parse time (HH:MM)
    h, m = int(upload_time[:2]), int(upload_time[3:5])
    publish_dt = last_sunday + timedelta(days=day_offset + 1, hours=h, minutes=m)

    # If already past, schedule for next week
    if publish_dt <= now:
        publish_dt += timedelta(weeks=1)

    return publish_dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def upload_video(mp4_path: Path, metadata: dict, schedule: bool = True,
                 dry_run: bool = False) -> bool:
    title      = metadata.get("title", mp4_path.stem)
    theme      = metadata.get("theme", "animals")
    video_type = metadata.get("video_type", "dance")
    tags       = metadata.get("tags", [])
    tags_str   = ",".join(str(t) for t in tags) if tags else ""

    publish_at = None
    if schedule:
        upload_day  = metadata.get("upload_day", "")
        upload_time = metadata.get("upload_time", "09:00")
        if upload_day:
            publish_at = calc_publish_at(upload_day, upload_time)

    status_label = f"scheduled {publish_at}" if publish_at else metadata.get("status", "public")

    print(f"\n  File:   {mp4_path.name}")
    print(f"  Title:  {title}")
    print(f"  Status: {status_label}")

    if dry_run:
        print(f"  [DRY RUN] would upload")
        return True

    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "upload_youtube.py"),
        "--file",       str(mp4_path),
        "--title",      title,
        "--video-type", video_type,
        "--theme",      theme,
        "--status",     "private" if publish_at else metadata.get("status", "public"),
    ]

    if tags_str:
        cmd += ["--tags", tags_str]

    thumb_path = mp4_path.parent / f"thumb_{mp4_path.stem}.png"
    if thumb_path.exists():
        cmd += ["--thumbnail", str(thumb_path)]
        print(f"  Thumb:  {thumb_path.name}")

    if publish_at:
        cmd += ["--publish-at", publish_at]

    result = subprocess.run(cmd, capture_output=False)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Publish queue to YouTube")
    parser.add_argument("--dry-run",     action="store_true")
    parser.add_argument("--limit",       type=int, default=0, help="Max videos to upload")
    parser.add_argument("--no-schedule", action="store_true", help="Upload as public immediately")
    args = parser.parse_args()

    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADED_DIR.mkdir(parents=True, exist_ok=True)

    queue = sorted(QUEUE_DIR.glob("*.mp4"), key=lambda p: p.stat().st_mtime)
    if not queue:
        print("Queue is empty. Run batch_generate.py first.")
        return

    plan  = load_plan()
    limit = args.limit if args.limit > 0 else len(queue)

    print(f"\nPublish queue — {len(queue)} video(s) waiting")
    if args.dry_run:
        print("DRY RUN mode")
    if not args.no_schedule:
        print("Scheduled publishing ON (videos will be private until publish time)")

    uploaded = 0
    failed   = 0

    for mp4_path in queue[:limit]:
        metadata = load_sidecar(mp4_path) or match_metadata(mp4_path.name, plan)
        success  = upload_video(
            mp4_path, metadata,
            schedule=not args.no_schedule,
            dry_run=args.dry_run,
        )

        if success:
            if not args.dry_run:
                dest = UPLOADED_DIR / mp4_path.name
                shutil.move(str(mp4_path), str(dest))
                for suffix in [f"thumb_{mp4_path.stem}.png", f"meta_{mp4_path.stem}.yaml"]:
                    side = mp4_path.parent / suffix
                    if side.exists():
                        shutil.move(str(side), str(UPLOADED_DIR / suffix))
                print(f"  → moved to uploaded/")
            uploaded += 1
        else:
            failed += 1

    print(f"\n{'='*50}")
    print(f"  Uploaded: {uploaded}   Failed: {failed}")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
