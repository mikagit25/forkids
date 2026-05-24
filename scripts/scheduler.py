#!/usr/bin/env python3
"""
Daily scheduler — generates and uploads videos using the batch pipeline.

Cron: 0 8 * * 1,2,3,5,6 cd /opt/kids_channel && python3 scripts/scheduler.py

Steps:
  1. batch_generate.py  — generate all videos from weekly_plan.yaml
  2. publish_queue.py   — upload from output/queue/ to YouTube

Usage:
    python3 scheduler.py            # full run (generate + upload)
    python3 scheduler.py --dry-run  # simulate without generating
    python3 scheduler.py --upload-only  # only upload existing queue
"""

import argparse
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT    = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "scheduler.log"),
    ],
)
log = logging.getLogger(__name__)


def run(cmd: list, description: str) -> bool:
    log.info(f"→ {description}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        log.error(f"  FAILED: {description}")
        return False
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--upload-only", action="store_true",
                        help="Skip generation, only upload queue")
    args = parser.parse_args()

    log.info("=" * 60)
    log.info(f"Scheduler run: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    log.info("=" * 60)

    py = sys.executable

    if not args.upload_only:
        # Step 1: generate this week's plan (rotates based on history)
        cmd = [py, str(ROOT / "scripts" / "plan_week.py")]
        if args.dry_run:
            cmd.append("--dry-run")
        ok = run(cmd, "Generating weekly plan")
        if not ok:
            log.error("Plan generation failed — aborting")
            sys.exit(1)

        # Step 2: generate all videos from the plan
        cmd = [py, str(ROOT / "scripts" / "batch_generate.py"),
               "--plan", str(ROOT / "config" / "weekly_plan.yaml")]
        if args.dry_run:
            cmd.append("--dry-run")
        ok = run(cmd, "Batch generate videos")
        if not ok:
            log.error("Batch generation failed — aborting")
            sys.exit(1)

    # Step 2: publish queue to YouTube
    cmd = [py, str(ROOT / "scripts" / "publish_queue.py")]
    if args.dry_run:
        cmd.append("--dry-run")
    run(cmd, "Publish queue to YouTube")

    log.info("=" * 60)
    log.info("Scheduler done.")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
