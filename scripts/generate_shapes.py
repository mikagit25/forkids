#!/usr/bin/env python3
"""
Generate cartoon-style geometric shape sprites (512x512 RGBA PNG).
Shapes are drawn programmatically with PIL — no external images needed.

Usage:
    python3 generate_shapes.py           # generate all shapes
    python3 generate_shapes.py --preview # save a preview grid image
"""

import argparse
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

ROOT      = Path(__file__).resolve().parent.parent
OUT_DIR   = ROOT / "assets" / "sprites" / "shapes"

SIZE      = 512
MARGIN    = 56          # padding from edge
LINE_W    = 22          # outline thickness

# Bright kid-friendly fill colours (one per shape)
SHAPE_COLORS = {
    "circle":    ("#FF6B6B", "#C0392B"),  # red fill, dark outline
    "square":    ("#4D96FF", "#1A5FAB"),  # blue
    "triangle":  ("#6BCB77", "#1E8449"),  # green
    "rectangle": ("#FFD93D", "#B7950B"),  # yellow
    "oval":      ("#A29BFE", "#6C5CE7"),  # purple
    "star":      ("#FF922B", "#C0580A"),  # orange
    "heart":     ("#FD79A8", "#C0185E"),  # pink
    "diamond":   ("#55EFC4", "#00856F"),  # teal
}


def hex_to_rgb(h: str) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def make_canvas() -> tuple[Image.Image, ImageDraw.Draw]:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def draw_circle(fill, outline) -> Image.Image:
    img, d = make_canvas()
    r = (SIZE // 2) - MARGIN
    cx, cy = SIZE // 2, SIZE // 2
    d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=fill+(255,), outline=outline+(255,), width=LINE_W)
    return img


def draw_square(fill, outline) -> Image.Image:
    img, d = make_canvas()
    m = MARGIN
    r = 28  # corner radius
    d.rounded_rectangle([m, m, SIZE-m, SIZE-m], radius=r,
                        fill=fill+(255,), outline=outline+(255,), width=LINE_W)
    return img


def draw_triangle(fill, outline) -> Image.Image:
    img, d = make_canvas()
    m = MARGIN
    pts = [(SIZE//2, m), (SIZE-m, SIZE-m), (m, SIZE-m)]
    d.polygon(pts, fill=fill+(255,), outline=outline+(255,))
    # Re-draw outline for thickness
    for i in range(LINE_W):
        scale = 1.0 - i * 0.003
        cx, cy = SIZE//2, SIZE//2
        scaled = [(cx + (x-cx)*scale, cy + (y-cy)*scale) for x, y in pts]
        d.line(scaled + [scaled[0]], fill=outline+(255,), width=max(1, LINE_W-i))
    return img


def draw_rectangle(fill, outline) -> Image.Image:
    img, d = make_canvas()
    mx, my = MARGIN, MARGIN + 60
    r = 24
    d.rounded_rectangle([mx, my, SIZE-mx, SIZE-my], radius=r,
                        fill=fill+(255,), outline=outline+(255,), width=LINE_W)
    return img


def draw_oval(fill, outline) -> Image.Image:
    img, d = make_canvas()
    mx, my = MARGIN, MARGIN + 55
    d.ellipse([mx, my, SIZE-mx, SIZE-my], fill=fill+(255,), outline=outline+(255,), width=LINE_W)
    return img


def draw_star(fill, outline, points=5) -> Image.Image:
    img, d = make_canvas()
    cx, cy = SIZE // 2, SIZE // 2
    outer_r = SIZE // 2 - MARGIN
    inner_r = outer_r * 0.42
    pts = []
    for i in range(points * 2):
        angle = math.pi * i / points - math.pi / 2
        r = outer_r if i % 2 == 0 else inner_r
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    d.polygon(pts, fill=fill+(255,), outline=outline+(255,))
    for i in range(LINE_W // 2):
        shrink = 1.0 - i * 0.005
        sp = [(cx + (x-cx)*shrink, cy + (y-cy)*shrink) for x,y in pts]
        d.line(sp + [sp[0]], fill=outline+(255,), width=2)
    return img


def draw_heart(fill, outline) -> Image.Image:
    img, d = make_canvas()
    cx, cy = SIZE // 2, SIZE // 2 + 20
    # Parametric heart: x=16sin³t, y=13cos(t)-5cos(2t)-2cos(3t)-cos(4t)
    scale = (SIZE // 2 - MARGIN) / 16.0
    pts = []
    steps = 200
    for i in range(steps):
        t = 2 * math.pi * i / steps
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2*t) - 2 * math.cos(3*t) - math.cos(4*t))
        pts.append((cx + x * scale, cy + y * scale))
    d.polygon(pts, fill=fill+(255,))
    # Outline
    for w in range(LINE_W, 0, -2):
        s = 1.0 - (LINE_W - w) * 0.005
        sp = [(cx + (x-cx)*s, cy + (y-cy)*s) for x,y in pts]
        d.line(sp + [sp[0]], fill=outline+(255,), width=w)
    return img


def draw_diamond(fill, outline) -> Image.Image:
    img, d = make_canvas()
    cx = SIZE // 2
    m = MARGIN
    pts = [(cx, m), (SIZE-m, SIZE//2), (cx, SIZE-m), (m, SIZE//2)]
    d.polygon(pts, fill=fill+(255,), outline=outline+(255,))
    for i in range(LINE_W // 2):
        shrink = 1.0 - i * 0.004
        sp = [(cx + (x-cx)*shrink, SIZE//2 + (y-SIZE//2)*shrink) for x,y in pts]
        d.line(sp + [sp[0]], fill=outline+(255,), width=2)
    return img


SHAPE_FUNCS = {
    "circle":    draw_circle,
    "square":    draw_square,
    "triangle":  draw_triangle,
    "rectangle": draw_rectangle,
    "oval":      draw_oval,
    "star":      draw_star,
    "heart":     draw_heart,
    "diamond":   draw_diamond,
}


def generate_all(overwrite: bool = False):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    generated = []

    for name, (fill_hex, outline_hex) in SHAPE_COLORS.items():
        out_path = OUT_DIR / f"{name}.png"
        if out_path.exists() and not overwrite:
            print(f"  {name:<12} ← already exists")
            generated.append(out_path)
            continue

        fill    = hex_to_rgb(fill_hex)
        outline = hex_to_rgb(outline_hex)
        func    = SHAPE_FUNCS[name]
        img     = func(fill, outline)

        # Light drop shadow
        shadow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow)
        sf = hex_to_rgb(outline_hex)
        shadow_img = func(sf, sf)
        shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(8))
        canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        canvas.paste(shadow_img, (6, 8), shadow_img)
        canvas.paste(img, (0, 0), img)

        canvas.save(out_path, "PNG")
        print(f"  {name:<12} → {out_path.name}")
        generated.append(out_path)

    return generated


def save_preview(paths: list):
    cols = 4
    rows = math.ceil(len(paths) / cols)
    thumb = 200
    preview = Image.new("RGB", (cols * thumb, rows * thumb), (240, 240, 240))
    for i, p in enumerate(paths):
        img = Image.open(p).convert("RGBA")
        img.thumbnail((thumb-20, thumb-20), Image.LANCZOS)
        bg = Image.new("RGBA", (thumb, thumb), (255, 255, 255, 255))
        ox = (thumb - img.width) // 2
        oy = (thumb - img.height) // 2
        bg.paste(img, (ox, oy), img)
        c, r = i % cols, i // cols
        preview.paste(bg.convert("RGB"), (c*thumb, r*thumb))
    out = ROOT / "output" / "shapes_preview.png"
    out.parent.mkdir(exist_ok=True)
    preview.save(out)
    print(f"\nPreview: {out}")


def main():
    parser = argparse.ArgumentParser(description="Generate cartoon shape sprites")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--preview",   action="store_true")
    args = parser.parse_args()

    print(f"\nGenerating shapes → {OUT_DIR}")
    paths = generate_all(overwrite=args.overwrite)
    print(f"\nDone. {len(paths)} shapes in {OUT_DIR}/")

    if args.preview:
        save_preview(paths)


if __name__ == "__main__":
    main()
