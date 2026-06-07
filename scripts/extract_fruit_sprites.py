#!/usr/bin/env python3
"""
Extract individual cartoon fruit sprites from AI-generated images.
Removes backgrounds, detects bounding boxes, saves individual PNGs.

Usage:
    python3 scripts/extract_fruit_sprites.py
"""
import os
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw
from rembg import remove

SRC  = Path(__file__).resolve().parent.parent / "assets" / "sprites_gdrive" / "kids"
OUT  = Path(__file__).resolve().parent.parent / "assets" / "sprites_new" / "fruits_cartoon"
OUT.mkdir(parents=True, exist_ok=True)

# Fruit names for each image's characters (left→right order)
GEMINI_A_NAMES = ["pear", "pineapple", "plum", "kiwi"]          # tw0z — 4 fruits
GEMINI_B_NAMES = ["apple", "orange", "banana", "strawberry", "grape"]  # w2iy — 5 fruits
GRID_NAMES     = [                                                # a_продолж 3×3
    "grape", "banana", "pomegranate",
    "orange", "apple_green", "pineapple",
    "kiwi", "peach", "avocado",
]
MAI_NAMES      = ["apple", "banana", "orange", "plum", "strawberry"]  # mai — already transparent


def find_sprite_boxes(rgba: Image.Image, n: int, axis: str = "h") -> list[tuple]:
    """
    Split image into n equal strips and find tight bounding boxes per strip.
    axis: 'h' = split horizontally (n columns), 'v' = split vertically (n rows).
    Returns list of (x1, y1, x2, y2) tight crop boxes with padding.
    """
    w, h = rgba.size
    alpha = np.array(rgba)[:, :, 3]
    boxes = []

    for i in range(n):
        if axis == "h":
            x0 = w * i // n
            x1 = w * (i + 1) // n
            strip_alpha = alpha[:, x0:x1]
            rows = np.any(strip_alpha > 20, axis=1)
            cols = np.any(strip_alpha > 20, axis=0)
        else:
            y0 = h * i // n
            y1 = h * (i + 1) // n
            strip_alpha = alpha[y0:y1, :]
            rows = np.any(strip_alpha > 20, axis=1)
            cols = np.any(strip_alpha > 20, axis=0)

        if not rows.any() or not cols.any():
            boxes.append(None)
            continue

        r0, r1 = np.where(rows)[0][[0, -1]]
        c0, c1 = np.where(cols)[0][[0, -1]]

        pad = 20
        if axis == "h":
            bx1 = max(0, x0 + c0 - pad)
            by1 = max(0, r0 - pad)
            bx2 = min(w, x0 + c1 + pad)
            by2 = min(h, r1 + pad)
        else:
            bx1 = max(0, c0 - pad)
            by1 = max(0, y0 + r0 - pad)
            bx2 = min(w, c1 + pad)
            by2 = min(h, y0 + r1 + pad)

        boxes.append((bx1, by1, bx2, by2))

    return boxes


def square_pad(img: Image.Image, size: int = 512) -> Image.Image:
    """Pad RGBA image to square and resize to target size."""
    w, h = img.size
    side  = max(w, h)
    out   = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    out.paste(img, ((side - w) // 2, (side - h) // 2))
    return out.resize((size, size), Image.LANCZOS)


def process_gemini(path: Path, names: list[str]) -> int:
    print(f"\n  Processing {path.name} ({len(names)} fruits)...")
    img  = Image.open(path).convert("RGB")
    rgba = remove(img)   # rembg → RGBA transparent
    boxes = find_sprite_boxes(rgba, len(names), axis="h")
    saved = 0
    for name, box in zip(names, boxes):
        if box is None:
            print(f"    {name}: no content found"); continue
        crop   = rgba.crop(box)
        sprite = square_pad(crop, 512)
        out_p  = OUT / f"{name}.png"
        sprite.save(out_p)
        print(f"    ✓ {name}.png  ({box[2]-box[0]}×{box[3]-box[1]}px)")
        saved += 1
    return saved


def process_grid(path: Path, names: list[str], cols: int = 3) -> int:
    """3×3 grid — each cell has solid-color background → rembg per cell."""
    print(f"\n  Processing {path.name} ({len(names)} fruits, {cols}-col grid)...")
    img  = Image.open(path).convert("RGB")
    w, h = img.size
    rows = len(names) // cols
    cw, ch = w // cols, h // rows
    saved = 0
    for i, name in enumerate(names):
        row, col = i // cols, i % cols
        cell = img.crop((col*cw, row*ch, (col+1)*cw, (row+1)*ch))
        rgba = remove(cell)
        # tight bounding box of the character
        arr  = np.array(rgba)
        mask = arr[:, :, 3] > 20
        if not mask.any():
            print(f"    {name}: empty"); continue
        ys, xs = np.where(mask)
        pad = 20
        box = (max(0, xs.min()-pad), max(0, ys.min()-pad),
               min(cw, xs.max()+pad), min(ch, ys.max()+pad))
        crop   = rgba.crop(box)
        sprite = square_pad(crop, 512)
        out_p  = OUT / f"{name}.png"
        sprite.save(out_p)
        print(f"    ✓ {name}.png  ({box[2]-box[0]}×{box[3]-box[1]}px)")
        saved += 1
    return saved


def process_mai(path: Path, names: list[str]) -> int:
    """mai image — already transparent background."""
    print(f"\n  Processing {path.name} ({len(names)} fruits, pre-transparent)...")
    img = Image.open(path).convert("RGBA")
    # Check if truly transparent
    arr = np.array(img)
    if arr[:, :, 3].min() > 200:
        print("    No transparency detected — applying rembg...")
        img = remove(img.convert("RGB"))
    boxes = find_sprite_boxes(img, len(names), axis="h")
    saved = 0
    for name, box in zip(names, boxes):
        if box is None:
            print(f"    {name}: no content found"); continue
        out_name = f"{name}_b.png"  # _b suffix = second style variant
        out_p    = OUT / out_name
        if (OUT / f"{name}.png").exists():
            # Primary already exists from Gemini — save as variant
            pass
        else:
            out_name = f"{name}.png"
            out_p    = OUT / out_name
        crop   = img.crop(box)
        sprite = square_pad(crop, 512)
        sprite.save(out_p)
        print(f"    ✓ {out_name}  ({box[2]-box[0]}×{box[3]-box[1]}px)")
        saved += 1
    return saved


def main():
    src_files = {f.name: f for f in SRC.glob("*.png")}
    total = 0

    # 1. Gemini A — 4 fruits (pear, pineapple, plum, kiwi)
    f = next((v for k, v in src_files.items() if "tw0z" in k), None)
    if f:
        total += process_gemini(f, GEMINI_A_NAMES)

    # 2. Gemini B — 5 fruits (apple, orange, banana, strawberry, grape)
    f = next((v for k, v in src_files.items() if "w2iy" in k), None)
    if f:
        total += process_gemini(f, GEMINI_B_NAMES)

    # 3. Grid 3×3 — 9 fruits
    f = next((v for k, v in src_files.items() if "продолж" in k), None)
    if f:
        total += process_grid(f, GRID_NAMES, cols=3)

    # 4. mai — 5 fruits (pre-transparent, second variants)
    f = next((v for k, v in src_files.items() if "mai-image" in k), None)
    if f:
        total += process_mai(f, MAI_NAMES)

    print(f"\n{'='*50}")
    print(f"  Total sprites saved: {total}")
    print(f"  Output: {OUT}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
