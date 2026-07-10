#!/usr/bin/env python3
"""
Generate black silhouette versions of 3D sprites for Shadow Puppet Show series.

Reads *_3d.png from assets/sprites_new/{animals,fruits,vegetables}/
Outputs black-filled silhouettes (RGB→0, alpha preserved) to:
  assets/sprites_new/silhouettes/{animals,fruits,vegetables}/
  remotion/public/sprites/silhouettes/{animals,fruits,vegetables}/

Usage:
  python3 scripts/generate_silhouettes.py
  python3 scripts/generate_silhouettes.py --categories animals
  python3 scripts/generate_silhouettes.py --force
"""
import argparse
from pathlib import Path

import numpy as np
from PIL import Image

ROOT          = Path(__file__).resolve().parent.parent
SPRITES_SRC   = ROOT / "assets" / "sprites_new"
SPRITES_DEST  = ROOT / "assets" / "sprites_new" / "silhouettes"
REMOTION_DEST = ROOT / "remotion" / "public" / "sprites" / "silhouettes"

CATEGORIES = ["animals", "fruits", "vegetables"]


def make_silhouette(src: Path, dst: Path) -> None:
    img  = Image.open(src).convert("RGBA")
    data = np.array(img, dtype=np.uint8)
    # Zero out RGB, keep alpha untouched → pure black silhouette
    data[:, :, 0] = 0
    data[:, :, 1] = 0
    data[:, :, 2] = 0
    Image.fromarray(data).save(dst, "PNG")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--categories", nargs="+", default=CATEGORIES,
                        choices=CATEGORIES, help="Which categories to process")
    parser.add_argument("--force", action="store_true",
                        help="Re-generate even if output already exists")
    args = parser.parse_args()

    total_new = 0
    total_skip = 0

    for cat in args.categories:
        src_dir = SPRITES_SRC / cat
        if not src_dir.exists():
            print(f"  SKIP {cat}: source dir not found")
            continue

        srcs = sorted(src_dir.glob("*_3d.png"))
        if not srcs:
            print(f"  SKIP {cat}: no *_3d.png found")
            continue

        dst_assets  = SPRITES_DEST / cat
        dst_remotion = REMOTION_DEST / cat
        dst_assets.mkdir(parents=True, exist_ok=True)
        dst_remotion.mkdir(parents=True, exist_ok=True)

        print(f"\n[{cat}] {len(srcs)} sprites")
        for src in srcs:
            dst_a = dst_assets  / src.name
            dst_r = dst_remotion / src.name

            if dst_a.exists() and not args.force:
                total_skip += 1
                continue

            make_silhouette(src, dst_a)
            # Mirror to remotion/public (copy, not symlink — Remotion needs real files)
            dst_r.write_bytes(dst_a.read_bytes())
            print(f"  ✓ {src.name}")
            total_new += 1

    print(f"\nDone: {total_new} new silhouettes, {total_skip} skipped (already exist).")
    print(f"Paths:")
    print(f"  assets: {SPRITES_DEST}")
    print(f"  remotion: {REMOTION_DEST}")


if __name__ == "__main__":
    main()
