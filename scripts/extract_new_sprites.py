#!/usr/bin/env python3
"""
Extract sprites from the new AI-generated images (Groups 1-5).
Output:
  - Fruits → assets/sprites_new/fruits_cartoon/
  - Vegetables → assets/sprites_new/vegetables_cartoon/

Usage:
    python3 scripts/extract_new_sprites.py
    python3 scripts/extract_new_sprites.py --group 1 2 3
    python3 scripts/extract_new_sprites.py --dry-run
"""
import argparse
import shutil
import numpy as np
from pathlib import Path
from PIL import Image
from rembg import remove

ROOT     = Path(__file__).resolve().parent.parent
SRC      = ROOT / "assets" / "sprites_gdrive"
FRUITS   = ROOT / "assets" / "sprites_new" / "fruits_cartoon"
VEGS     = ROOT / "assets" / "sprites_new" / "vegetables_cartoon"
REM_PUB  = ROOT / "remotion" / "public" / "sprites"

GROUPS = {
    # Group 1: Fruits row 1 (watermelon slice, cherry, lemon, mango)
    1: {
        "file":   "reve-v1.5_b_Create_a_set_of_4_cu.png",
        "names":  ["watermelon", "cherry", "lemon", "mango"],
        "layout": "grid2x2",
        "out":    FRUITS,
    },
    # Group 1 variant (gpt-image-2)
    "1b": {
        "file":   "gpt-image-2 (medium)_a_Create_a_set_of_4_cu.png",
        "names":  ["watermelon_b", "cherry_b", "lemon_b", "mango_b"],
        "layout": "grid2x2",
        "out":    FRUITS,
    },
    # Group 2: Fruits row 2 (blueberry, raspberry, coconut, dragonfruit)
    2: {
        "file":   "b_Create_a_set_of_4_cu.jpeg",
        "names":  ["blueberry", "raspberry", "coconut", "dragonfruit"],
        "layout": "grid2x2",
        "out":    FRUITS,
    },
    # Group 2 variant
    "2b": {
        "file":   "a_Create_a_set_of_4_cu.png",
        "names":  ["blueberry_b", "raspberry_b", "coconut_b", "dragonfruit_b"],
        "layout": "grid2x2",
        "out":    FRUITS,
    },
    # Group 3: mandarin, melon, watermelon_whole, pineapple_v2 (horizontal row)
    3: {
        "file":   "hidream-o1-image-1.5_b_Create_a_set_of_4_cu.png",
        "names":  ["mandarin", "melon_cartoon", "watermelon_whole", "pineapple_v2"],
        "layout": "row4",
        "out":    FRUITS,
    },
    # Group 4: Vegetables (carrot, broccoli, corn, tomato, pumpkin) — 2×3 grid, 5 items
    4: {
        "file":   "imagen-3.0-generate-002_a_Create_a_set_of_5_cu.png",
        "names":  ["carrot", "broccoli", "corn", "tomato", None, "pumpkin"],  # None = skip dup
        "layout": "grid2x3",
        "out":    VEGS,
    },
    # Group 4 variant: horizontal row
    "4b": {
        "file":   "grok-imagine-image_b_Create_a_set_of_5_cu.jpeg",
        "names":  ["carrot_b", "broccoli_b", "corn_b", "tomato_b", "pumpkin_b"],
        "layout": "row5",
        "out":    VEGS,
    },
    # Group 5: Vegetables (cucumber, eggplant, pepper, potato, onion) — 2×3 grid, 5 items
    5: {
        "file":   "imagen-3.0-generate-002_a_Create_a_set_of_5_cu (1).png",
        "names":  ["cucumber", "eggplant", "pepper", "potato", None, "onion"],
        "layout": "grid2x3",
        "out":    VEGS,
    },
}


def square_pad(img: Image.Image, size: int = 512) -> Image.Image:
    w, h = img.size
    side = max(w, h)
    out  = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    out.paste(img, ((side - w) // 2, (side - h) // 2))
    return out.resize((size, size), Image.LANCZOS)


def tight_crop(rgba: Image.Image, pad: int = 20) -> Image.Image:
    arr  = np.array(rgba)
    mask = arr[:, :, 3] > 20
    if not mask.any():
        return rgba
    ys, xs = np.where(mask)
    w, h = rgba.size
    box = (max(0, xs.min()-pad), max(0, ys.min()-pad),
           min(w, xs.max()+pad), min(h, ys.max()+pad))
    return rgba.crop(box)


def extract_grid(img_rgb: Image.Image, rows: int, cols: int, names: list) -> list:
    """Split into rows×cols cells, rembg each cell, return (name, sprite) pairs."""
    w, h = img_rgb.size
    cw, ch = w // cols, h // rows
    results = []
    for i, name in enumerate(names):
        if name is None:
            continue
        row, col = i // cols, i % cols
        cell = img_rgb.crop((col*cw, row*ch, (col+1)*cw, (row+1)*ch))
        rgba = remove(cell)
        crop = tight_crop(rgba)
        sprite = square_pad(crop, 512)
        results.append((name, sprite))
    return results


def extract_row(img_rgb: Image.Image, n: int, names: list) -> list:
    """Split horizontally into n strips (for horizontal-row images), rembg whole + split."""
    rgba = remove(img_rgb)
    w, h = rgba.size
    arr   = np.array(rgba)[:, :, 3]
    results = []
    for i, name in enumerate(names):
        if name is None:
            continue
        x0 = w * i // n
        x1 = w * (i + 1) // n
        strip_alpha = arr[:, x0:x1]
        rows_mask = np.any(strip_alpha > 20, axis=1)
        cols_mask = np.any(strip_alpha > 20, axis=0)
        if not rows_mask.any():
            print(f"    {name}: empty strip"); continue
        r0, r1 = np.where(rows_mask)[0][[0, -1]]
        c0, c1 = np.where(cols_mask)[0][[0, -1]]
        pad = 20
        box = (max(0, x0+c0-pad), max(0, r0-pad),
               min(w, x0+c1+pad), min(h, r1+pad))
        crop = rgba.crop(box)
        sprite = square_pad(crop, 512)
        results.append((name, sprite))
    return results


def process_group(gid, cfg: dict, dry_run: bool) -> int:
    src_path = SRC / cfg["file"]
    if not src_path.exists():
        # Try /tmp/gdrive_new/
        src_path = Path("/tmp/gdrive_new") / cfg["file"]
    if not src_path.exists():
        print(f"  [Group {gid}] FILE NOT FOUND: {cfg['file']}")
        return 0

    out_dir: Path = cfg["out"]
    out_dir.mkdir(parents=True, exist_ok=True)
    layout = cfg["layout"]
    names  = cfg["names"]

    print(f"\n  [Group {gid}] {cfg['file']} → {out_dir.name}/")

    img_rgb = Image.open(src_path).convert("RGB")

    if layout == "grid2x2":
        pairs = extract_grid(img_rgb, rows=2, cols=2, names=names)
    elif layout == "grid2x3":
        pairs = extract_grid(img_rgb, rows=2, cols=3, names=names)
    elif layout == "row4":
        pairs = extract_row(img_rgb, n=4, names=names)
    elif layout == "row5":
        pairs = extract_row(img_rgb, n=5, names=names)
    else:
        print(f"  Unknown layout: {layout}"); return 0

    saved = 0
    for name, sprite in pairs:
        out_path = out_dir / f"{name}.png"
        if dry_run:
            print(f"    would save → {out_path.relative_to(ROOT)}")
        else:
            sprite.save(out_path)
            print(f"    ✓ {name}.png")
        saved += 1

    return saved


def sync_to_remotion(dry_run: bool):
    """Copy new sprites to remotion/public/sprites/."""
    for sub in ["fruits_cartoon", "vegetables_cartoon"]:
        src = ROOT / "assets" / "sprites_new" / sub
        dst = REM_PUB / sub
        if not src.exists():
            continue
        dst.mkdir(parents=True, exist_ok=True)
        for png in src.glob("*.png"):
            d = dst / png.name
            if not d.exists() or png.stat().st_mtime > d.stat().st_mtime:
                if dry_run:
                    print(f"  would copy {png.name} → remotion/public/sprites/{sub}/")
                else:
                    shutil.copy2(png, d)
                    print(f"  synced {sub}/{png.name}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--group", nargs="+", default=None,
                        help="Which groups to process (1 2 3 4 4b 5). Default: all.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    targets = args.group or [str(k) for k in GROUPS]

    print(f"\nExtracting sprites {'(dry run)' if args.dry_run else ''}\n")
    total = 0
    for gid_str in targets:
        try:
            gid = int(gid_str)
        except ValueError:
            gid = gid_str
        if gid not in GROUPS:
            print(f"Unknown group: {gid}"); continue
        total += process_group(gid, GROUPS[gid], args.dry_run)

    print(f"\n{'='*50}")
    print(f"  Sprites saved: {total}")

    print("\nSyncing to remotion/public/sprites/...")
    sync_to_remotion(args.dry_run)
    print("Done.")


if __name__ == "__main__":
    main()
