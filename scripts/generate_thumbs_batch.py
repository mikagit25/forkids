#!/usr/bin/env python3
"""
Generate missing thumbnails for all videos in output/queue/.
Reads meta_*.yaml sidecar to determine type/theme, calls generate_thumbnail.py.

Usage:
    python3 scripts/generate_thumbs_batch.py
    python3 scripts/generate_thumbs_batch.py --force   # regenerate existing
"""
import argparse
import subprocess
import sys
import yaml
from pathlib import Path

ROOT      = Path(__file__).resolve().parent.parent
QUEUE_DIR = ROOT / "output" / "queue"
THUMB_GEN = ROOT / "scripts" / "generate_thumbnail.py"


def char_from_stem(stem: str) -> str:
    """Extract character name from filename like short_dance_apple_20260527."""
    parts = stem.split("_")
    # skip short/dance/color/etc prefixes and date suffix (8 digits)
    tokens = [p for p in parts if not p.isdigit() and len(p) != 8]
    # drop known prefixes
    skip = {"short", "dance", "color", "shape", "compilation", "mixed",
            "animals", "fruits", "vegetables", "interleave", "blocks",
            "shapes", "v2"}
    chars = [t for t in tokens if t not in skip]
    return chars[0] if chars else ""


def make_thumb_args(mp4: Path, meta: dict) -> list[str] | None:
    stem       = mp4.stem
    video_type = meta.get("video_type", "")
    theme      = meta.get("theme", "animals")
    title      = meta.get("title", stem)
    out        = QUEUE_DIR / f"thumb_{stem}.png"

    base = [sys.executable, str(THUMB_GEN), "--output", str(out)]

    if video_type in ("short_dance",):
        char = char_from_stem(stem)
        return base + ["--type", "dance", "--theme", theme,
                       "--title", char.capitalize(), "--shorts"]

    if video_type in ("short_color",):
        # stem: short_color_red_animals_...
        parts = stem.split("_")
        color = parts[2] if len(parts) > 2 else "red"
        return base + ["--type", "colors", "--theme", theme,
                       "--color", color, "--shorts"]

    if video_type in ("short_shape_dance", "shape_dance"):
        return base + ["--type", "dance", "--theme", "shapes",
                       "--title", "Shapes", "--shorts"]

    if video_type in ("short_abc", "short_vocab"):
        # Extract letter from stem: short_abc_a_20260529 or short_vocab_a_20260607
        parts = mp4.stem.split("_")
        letter = parts[2].upper() if len(parts) > 2 else "A"
        return base + ["--type", "abc", "--letter", letter,
                       "--word", letter, "--theme", "animals", "--shorts"]

    if video_type == "short_counting":
        return base + ["--type", "dance", "--theme", "shapes",
                       "--title", "Counting", "--shorts"]

    if video_type == "counting":
        return base + ["--type", "dance", "--theme", "shapes", "--title", title]

    if video_type == "abc":
        return base + ["--type", "abc", "--letter", "A", "--word", "Alphabet",
                       "--theme", "animals"]

    if video_type == "colors":
        return base + ["--type", "colors", "--color", "rainbow", "--theme", "animals"]

    if video_type == "short_color_learn":
        parts = mp4.stem.split("_")
        color = parts[2] if len(parts) > 2 else "red"
        return base + ["--type", "colors", "--color", color, "--theme", "shapes", "--shorts"]

    if video_type in ("short_shape_float", "short_shape_dance", "short_sdance"):
        parts = mp4.stem.split("_")
        shape = parts[2] if len(parts) > 2 else "circle"
        return base + ["--type", "dance", "--theme", "shapes",
                       "--title", shape.capitalize(), "--shorts"]

    if video_type == "dance":
        return base + ["--type", "dance", "--theme", theme, "--title", title]

    if video_type in ("compilation",):
        return base + ["--type", "dance", "--theme", theme, "--title", title]

    # fallback
    return base + ["--type", "dance", "--theme", theme, "--title", title]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Regenerate existing thumbs")
    args = parser.parse_args()

    mp4s = sorted(QUEUE_DIR.glob("*.mp4"))
    mp4s = [p for p in mp4s if "test_" not in p.name]

    done = skipped = failed = 0

    for mp4 in mp4s:
        thumb = QUEUE_DIR / f"thumb_{mp4.stem}.png"
        if thumb.exists() and not args.force:
            skipped += 1
            continue

        meta_path = QUEUE_DIR / f"meta_{mp4.stem}.yaml"
        if meta_path.exists():
            meta = yaml.safe_load(meta_path.read_text()) or {}
        else:
            meta = {}

        cmd = make_thumb_args(mp4, meta)
        if not cmd:
            print(f"  SKIP (no rule): {mp4.name}")
            skipped += 1
            continue

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and thumb.exists():
            print(f"  ✓ {thumb.name}")
            done += 1
        else:
            print(f"  ✗ {mp4.name}: {result.stderr[-200:].strip()}")
            failed += 1

    print(f"\nDone: {done} generated, {skipped} skipped, {failed} failed")


if __name__ == "__main__":
    main()
