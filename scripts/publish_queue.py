#!/usr/bin/env python3
"""
Publish videos from the output/queue/ directory to YouTube.

Reads weekly_plan.yaml for metadata (title, tags, status).
Uploads all .mp4 files in queue/ and moves them to uploaded/ after success.

Usage:
    python3 publish_queue.py              # upload all in queue
    python3 publish_queue.py --dry-run    # show what would be uploaded
    python3 publish_queue.py --limit 2    # upload at most N videos
"""

import argparse
import shutil
import sys
import yaml
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUEUE_DIR   = ROOT / "output" / "queue"
UPLOADED_DIR = ROOT / "uploaded"
PLAN_PATH   = ROOT / "config" / "weekly_plan.yaml"


def load_plan() -> list:
    if not PLAN_PATH.exists():
        return []
    with open(PLAN_PATH) as f:
        return yaml.safe_load(f).get("videos", [])


def match_metadata(filename: str, plan: list) -> dict:
    """Find best matching plan entry for a queue file."""
    # filename pattern: {type}_{theme}_{timestamp}.mp4
    parts = filename.replace(".mp4", "").split("_")
    video_type = parts[0] if parts else "dance"
    theme = parts[1] if len(parts) > 1 else "animals"

    for entry in plan:
        if (entry.get("video_type") == video_type and
                entry.get("theme", "animals") == theme):
            return entry

    # Fallback defaults
    return {
        "title": f"Happy Bear Kids — {theme.capitalize()} {video_type.capitalize()}",
        "status": "unlisted",
        "tags": ["kids", "children", theme, video_type],
        "video_type": video_type,
        "theme": theme,
    }


def upload_video(mp4_path: Path, metadata: dict, dry_run: bool = False) -> bool:
    import subprocess

    title  = metadata.get("title", mp4_path.stem)
    status = metadata.get("status", "unlisted")
    theme  = metadata.get("theme", "animals")

    print(f"\n  File:   {mp4_path.name}")
    print(f"  Title:  {title}")
    print(f"  Status: {status}")

    if dry_run:
        print(f"  [DRY RUN] would upload")
        return True

    video_type = metadata.get("video_type", "dance")
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "upload_youtube.py"),
        "--file",       str(mp4_path),
        "--title",      title,
        "--video-type", video_type,
        "--theme",      theme,
        "--status",     status,
    ]

    result = subprocess.run(cmd, capture_output=False)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Publish queue to YouTube")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0, help="Max videos to upload")
    args = parser.parse_args()

    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADED_DIR.mkdir(parents=True, exist_ok=True)

    queue = sorted(QUEUE_DIR.glob("*.mp4"), key=lambda p: p.stat().st_mtime)
    if not queue:
        print("Queue is empty. Run batch_generate.py first.")
        return

    plan = load_plan()
    limit = args.limit if args.limit > 0 else len(queue)

    print(f"\nPublish queue — {len(queue)} video(s) waiting")
    if args.dry_run:
        print("DRY RUN mode")

    uploaded = 0
    failed   = 0

    for mp4_path in queue[:limit]:
        metadata = match_metadata(mp4_path.name, plan)
        success  = upload_video(mp4_path, metadata, dry_run=args.dry_run)

        if success:
            if not args.dry_run:
                dest = UPLOADED_DIR / mp4_path.name
                shutil.move(str(mp4_path), str(dest))
                print(f"  → moved to uploaded/")
            uploaded += 1
        else:
            failed += 1

    print(f"\n{'='*50}")
    print(f"  Uploaded: {uploaded}   Failed: {failed}")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
