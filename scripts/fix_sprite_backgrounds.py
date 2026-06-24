#!/usr/bin/env python3
"""
Remove backgrounds from sprites that are still opaque (non-transparent).
Run after manually adding new sprite images.
Skips sprites in backgrounds/ subdirs and already-transparent PNGs.

Usage:
  python3 scripts/fix_sprite_backgrounds.py           # dry-run, show what would be processed
  python3 scripts/fix_sprite_backgrounds.py --apply   # actually remove backgrounds
"""
import sys, io, argparse
from pathlib import Path
from PIL import Image

try:
    from rembg import remove as rembg_remove
except ImportError:
    print("ERROR: pip install rembg")
    sys.exit(1)

SPRITES_DIR = Path(__file__).resolve().parent.parent / "assets" / "sprites_new"

# Directories to skip — these are actual backgrounds, not sprites
SKIP_DIRS = {"backgrounds", "bg", "tiles", "textures"}


def has_transparent_background(img_path: Path) -> bool:
    """Return True if image already has a transparent background corner pixel."""
    try:
        img = Image.open(img_path).convert("RGBA")
        corner = img.getpixel((0, 0))
        return corner[3] == 0
    except Exception:
        return False


def process_sprite(img_path: Path, apply: bool) -> bool:
    """Return True if processed (or would be processed)."""
    try:
        if has_transparent_background(img_path):
            return False  # already transparent
        # Needs background removal
        if not apply:
            print(f"  [dry-run] would remove bg: {img_path.relative_to(SPRITES_DIR)}")
            return True
        print(f"  removing bg: {img_path.relative_to(SPRITES_DIR)} ...", end=" ", flush=True)
        raw = img_path.read_bytes()
        result_bytes = rembg_remove(raw)
        result = Image.open(io.BytesIO(result_bytes)).convert("RGBA")
        result.save(img_path, "PNG")
        print(f"done ({img_path.stat().st_size // 1024}KB)")
        return True
    except Exception as e:
        print(f"  ERROR on {img_path.name}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Remove backgrounds from non-transparent sprites")
    parser.add_argument("--apply", action="store_true", help="Actually apply changes (default: dry-run)")
    parser.add_argument("--dir", help="Specific subdirectory to process (e.g. fruits)")
    args = parser.parse_args()

    if args.dir:
        search_dirs = [SPRITES_DIR / args.dir]
    else:
        search_dirs = [d for d in SPRITES_DIR.iterdir() if d.is_dir() and d.name not in SKIP_DIRS]

    total = 0
    changed = 0
    for d in sorted(search_dirs):
        for img_path in sorted(d.glob("*.png")):
            total += 1
            if process_sprite(img_path, args.apply):
                changed += 1

    action = "would process" if not args.apply else "processed"
    print(f"\nTotal: {total} sprites checked, {changed} {action}")
    if not args.apply and changed > 0:
        print("Run with --apply to actually remove backgrounds")


if __name__ == "__main__":
    main()
