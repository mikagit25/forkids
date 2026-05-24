#!/usr/bin/env python3
"""
Batch video generator — reads weekly_plan.yaml, generates all videos.

Usage:
    python3 batch_generate.py                             # use default plan
    python3 batch_generate.py --plan config/weekly_plan.yaml
    python3 batch_generate.py --dry-run                  # show what would be generated
    python3 batch_generate.py --only dance               # only dance videos
    python3 batch_generate.py --only abc

Output: output/queue/{video_type}_{theme}_{timestamp}.mp4
"""

import argparse
import subprocess
import sys
import yaml
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUEUE_DIR = ROOT / "output" / "queue"
SCRIPTS_DIR = ROOT / "config" / "scripts"

TEMPLATE_MAP = {
    "dance":          ROOT / "config" / "scene_templates" / "default.yaml",
    "abc":            ROOT / "config" / "scene_templates" / "abc.yaml",
    "numbers":        ROOT / "config" / "scene_templates" / "numbers.yaml",
    "colors":         ROOT / "config" / "scene_templates" / "colors.yaml",
    # Shorts templates (60s, vertical 9:16)
    "short_letter":   ROOT / "config" / "scene_templates" / "shorts_letter.yaml",
    "short_number":   ROOT / "config" / "scene_templates" / "shorts_number.yaml",
    "short_color":    ROOT / "config" / "scene_templates" / "shorts_color.yaml",
    "short_shape":    ROOT / "config" / "scene_templates" / "shorts_shape.yaml",
    "short_dance":    ROOT / "config" / "scene_templates" / "shorts_dance.yaml",
}

# Types that should always render as vertical Shorts
SHORTS_TYPES = {"short_letter", "short_number", "short_color", "short_shape", "short_dance"}


def run_script(cmd: list, description: str) -> bool:
    print(f"\n  → {description}")
    print(f"    {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, capture_output=False)
    if result.returncode != 0:
        print(f"  ERROR: {description} failed (exit {result.returncode})")
        return False
    return True


def generate_video(video_cfg: dict, dry_run: bool = False) -> Path | None:
    title       = video_cfg["title"]
    video_type  = video_cfg["video_type"]
    theme       = video_cfg.get("theme", "animals")
    duration    = video_cfg.get("duration_minutes", 1)
    is_shorts   = video_cfg.get("is_shorts", video_type in SHORTS_TYPES)

    # Shape short uses shapes sprite theme
    if video_type == "short_shape":
        theme = "shapes"

    template = TEMPLATE_MAP.get(video_type)
    if not template:
        print(f"  Unknown video_type: {video_type}, skipping")
        return None

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = "_short" if is_shorts else ""
    output_path = QUEUE_DIR / f"{video_type}_{theme}{suffix}_{ts}.mp4"

    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"  type={video_type}  theme={theme}  duration={duration}min  shorts={is_shorts}")
    print(f"{'─'*60}")

    if dry_run:
        print(f"  [DRY RUN] would generate → {output_path.name}")
        return output_path

    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1: generate episode script
    ok = run_script(
        [sys.executable, str(ROOT / "scripts" / "generate_script.py"),
         "--duration", str(duration),
         "--theme", theme,
         "--template", str(template),
         "--output-dir", str(SCRIPTS_DIR)],
        f"Generating script ({duration}min, {theme})"
    )
    if not ok:
        return None

    # Find the just-generated script (latest in dir)
    scripts = sorted(SCRIPTS_DIR.glob("episode_*.yaml"), key=lambda p: p.stat().st_mtime)
    if not scripts:
        print("  ERROR: no script generated")
        return None
    latest_script = scripts[-1]

    # Step 2: generate video
    cmd = [
        sys.executable, str(ROOT / "scripts" / "generate_video.py"),
        "--theme", theme,
        "--script", str(latest_script),
        "--output", str(output_path),
    ]
    if is_shorts:
        cmd.append("--shorts")

    ok = run_script(cmd, f"Rendering video → {output_path.name}")
    if not ok:
        return None

    size_mb = output_path.stat().st_size / 1_000_000 if output_path.exists() else 0
    print(f"\n  ✓ Done: {output_path.name} ({size_mb:.1f} MB)")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Batch video generator")
    parser.add_argument("--plan", default=str(ROOT / "config" / "weekly_plan.yaml"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--only", help="Filter by video_type (dance, abc, etc.)")
    args = parser.parse_args()

    plan_path = Path(args.plan)
    if not plan_path.exists():
        print(f"Plan not found: {plan_path}")
        sys.exit(1)

    with open(plan_path) as f:
        plan = yaml.safe_load(f)

    videos = plan.get("videos", [])
    if args.only:
        videos = [v for v in videos if v.get("video_type") == args.only]

    print(f"\nBatch generator — {len(videos)} video(s) to produce")
    if args.dry_run:
        print("DRY RUN mode\n")

    generated = []
    failed = []

    for i, video_cfg in enumerate(videos, 1):
        print(f"\n[{i}/{len(videos)}]", end="")
        result = generate_video(video_cfg, dry_run=args.dry_run)
        if result:
            generated.append(result)
        else:
            failed.append(video_cfg.get("title", "?"))

    print(f"\n{'='*60}")
    print(f"  Generated: {len(generated)}")
    if failed:
        print(f"  Failed:    {len(failed)}")
        for f in failed:
            print(f"    - {f}")
    print(f"  Queue dir: {QUEUE_DIR}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
