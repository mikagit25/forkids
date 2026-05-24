#!/usr/bin/env python3
"""
Daily scheduler: generate N videos and upload to YouTube.
Run via cron: 0 8 * * * cd /opt/kids_channel && python scripts/scheduler.py

Or run manually: python scripts/scheduler.py [--dry-run]
"""

import os
import sys
import logging
import random
import time
import argparse
from pathlib import Path
from datetime import datetime

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

log_dir = ROOT / "logs"
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_dir / "scheduler.log"),
    ],
)
log = logging.getLogger(__name__)


def load_config() -> dict:
    with open(ROOT / "config" / "settings.yaml") as f:
        return yaml.safe_load(f)


def load_playlists() -> dict:
    with open(ROOT / "config" / "playlists.yaml") as f:
        return yaml.safe_load(f)


def run_day(dry_run: bool = False) -> None:
    config = load_config()
    playlists = load_playlists()

    n_videos = config["channel"]["videos_per_day"]
    themes = list(playlists["themes"].keys())
    duration_min = config["channel"]["default_duration_minutes"]

    log.info("=" * 60)
    log.info(f"Daily run: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    log.info(f"Plan: {n_videos} videos, themes: {themes}")
    log.info("=" * 60)

    if dry_run:
        log.info("[DRY RUN] No files will be generated or uploaded.")

    from generate_video import VideoGenerator
    from upload_youtube import upload_video, load_playlists as lp

    results = []
    for i in range(n_videos):
        theme = random.choice(themes)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = str(ROOT / "output" / f"{theme}_{ts}.mp4")

        log.info(f"\n[{i+1}/{n_videos}] Theme: {theme}, Duration: {duration_min}min")

        try:
            if not dry_run:
                gen = VideoGenerator(config, theme, duration_min * 60)
                gen.generate(output)
                log.info(f"  Generated: {output}")
            else:
                log.info(f"  [skip] Would generate: {output}")

            # Upload
            if not dry_run:
                theme_data = playlists["themes"].get(theme, {})
                channel_name = config["channel"]["name"]
                title = config["youtube"]["title_template"].format(
                    theme=theme.capitalize(),
                    channel_name=channel_name,
                )
                description = theme_data.get("description", "")
                tags = theme_data.get("tags", []) + ["kids", "babies", "sensory"]
                status = config["youtube"]["default_status"]

                video_id = upload_video(
                    file_path=output,
                    title=title,
                    description=description,
                    tags=tags,
                    status=status,
                    config=config,
                )
                log.info(f"  Uploaded: https://youtu.be/{video_id}")

                # Archive
                uploaded_dir = ROOT / "uploaded"
                uploaded_dir.mkdir(exist_ok=True)
                Path(output).rename(uploaded_dir / Path(output).name)

                results.append({"theme": theme, "video_id": video_id, "status": "ok"})
            else:
                results.append({"theme": theme, "status": "dry_run"})

            # Delay between uploads (avoid rate limits)
            if i < n_videos - 1 and not dry_run:
                delay = random.randint(300, 900)
                log.info(f"  Waiting {delay}s before next upload...")
                time.sleep(delay)

        except Exception as e:
            log.error(f"  FAILED: {e}", exc_info=True)
            results.append({"theme": theme, "status": "error", "error": str(e)})

    # Summary
    log.info("\n" + "=" * 60)
    log.info("Summary:")
    for r in results:
        vid = r.get("video_id", "-")
        log.info(f"  {r['theme']:15} {r['status']:10} {vid}")
    log.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Daily video scheduler")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done without generating anything")
    args = parser.parse_args()
    run_day(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
