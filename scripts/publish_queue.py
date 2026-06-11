#!/usr/bin/env python3
"""
Publish videos from the output/queue/ directory to YouTube.

Reads meta_*.yaml sidecar files for full metadata (title, tags, upload_day,
upload_time). Falls back to weekly_plan.yaml matching if no sidecar found.

Usage:
    python3 publish_queue.py                  # upload 1 of any type
    python3 publish_queue.py --type short     # upload shorts only
    python3 publish_queue.py --type long      # upload long videos only
    python3 publish_queue.py --dry-run        # show what would be uploaded
    python3 publish_queue.py --limit 2        # upload at most N videos

Content split strategy (6 uploads/day within 10k quota):
    --type long  at 09:00 and 13:00  → 2 long videos/day
    --type short at 11:00, 15:00, 17:00, 19:00 → 4 shorts/day
"""

import argparse
import os
import shutil
import subprocess
import sys
import yaml
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUEUE_DIR    = ROOT / "output" / "queue"
QUEUE_AR_DIR = ROOT / "output" / "queue_ar"
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
    title       = metadata.get("title", mp4_path.stem)
    theme       = metadata.get("theme", "animals")
    video_type  = metadata.get("video_type", "dance")
    tags        = metadata.get("tags", [])
    tags_str    = ",".join(str(t) for t in tags) if tags else ""
    description = metadata.get("description", "")

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

    language = metadata.get("language", "en")

    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "upload_youtube.py"),
        "--file",       str(mp4_path),
        "--title",      title,
        "--video-type", video_type,
        "--theme",      theme,
        "--status",     "private" if publish_at else metadata.get("status", "public"),
        "--language",   language,
    ]

    if tags_str:
        cmd += ["--tags", tags_str]

    if description:
        cmd += ["--description", description]

    thumb_path = mp4_path.parent / f"thumb_{mp4_path.stem}.png"
    if thumb_path.exists():
        cmd += ["--thumbnail", str(thumb_path)]
        print(f"  Thumb:  {thumb_path.name}")

    if publish_at:
        cmd += ["--publish-at", publish_at]

    # Tell upload_youtube.py where to write the video ID after upload
    meta_path = mp4_path.parent / f"meta_{mp4_path.stem}.yaml"
    if meta_path.exists():
        cmd += ["--meta-path", str(meta_path)]

    result = subprocess.run(cmd, capture_output=False)
    return result.returncode == 0


def _fix_ar_symlinks(old_path: Path, new_path: Path):
    """After an EN file moves to uploaded/, update any AR-queue symlinks that pointed to it."""
    for candidate in QUEUE_AR_DIR.glob("*.mp4"):
        try:
            if candidate.is_symlink() and Path(os.readlink(str(candidate))).resolve() == old_path.resolve():
                candidate.unlink()
                candidate.symlink_to(str(new_path))
        except Exception:
            pass


SHORT_PREFIXES = ("short_", "ar_short_")
LONG_PREFIXES  = ("dance_", "compilation_", "abc_", "numbers_", "colors_", "counting_",
                  "ar_dance_", "ar_counting_", "ar_colors_")


def is_short(path: Path) -> bool:
    return path.name.startswith(SHORT_PREFIXES)


def is_long(path: Path) -> bool:
    return not is_short(path)


def filter_queue(queue: list[Path], kind: str) -> list[Path]:
    if kind == "short":
        return [p for p in queue if is_short(p)]
    if kind == "long":
        return [p for p in queue if is_long(p)]
    return queue   # "any" — no filter


def main():
    parser = argparse.ArgumentParser(description="Publish queue to YouTube")
    parser.add_argument("--dry-run",     action="store_true")
    parser.add_argument("--limit",       type=int, default=1, help="Max videos to upload (default 1)")
    parser.add_argument("--type",        choices=["short", "long", "any"], default="any",
                        help="Filter: short=60s videos, long=30min videos, any=no filter")
    parser.add_argument("--no-schedule", action="store_true", default=True,
                        help="Upload as public immediately (default)")
    parser.add_argument("--queue", choices=["en", "ar"], default="en",
                        help="Which queue to publish from: en=output/queue/, ar=output/queue_ar/")
    args = parser.parse_args()

    active_queue_dir = QUEUE_AR_DIR if args.queue == "ar" else QUEUE_DIR
    active_queue_dir.mkdir(parents=True, exist_ok=True)
    UPLOADED_DIR.mkdir(parents=True, exist_ok=True)

    all_queue = sorted(
        [p for p in active_queue_dir.glob("*.mp4")
         if "test_" not in p.name and p.exists()],   # p.exists() skips broken symlinks
        key=lambda p: p.stat().st_mtime
    )
    queue = filter_queue(all_queue, args.type)

    if not queue:
        print(f"Queue is empty (type={args.type}). Nothing to upload.")
        return

    plan  = load_plan()
    limit = args.limit if args.limit > 0 else len(queue)

    shorts_count = len([p for p in all_queue if is_short(p)])
    longs_count  = len([p for p in all_queue if is_long(p)])
    print(f"\nPublish queue — {len(all_queue)} total ({longs_count} long, {shorts_count} shorts)")
    print(f"Uploading: {args.type} (limit={limit})")
    if args.dry_run:
        print("DRY RUN mode")

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
                # Fix any AR symlinks that pointed to this file — redirect to uploaded/
                _fix_ar_symlinks(mp4_path, dest)
                print(f"  → moved to uploaded/")
            uploaded += 1
        else:
            failed += 1

    print(f"\n{'='*50}")
    print(f"  Uploaded: {uploaded}   Failed: {failed}")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
