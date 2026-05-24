#!/usr/bin/env python3
"""
Generate high-quality cartoon sprites using Pillow.
Creates distinct character shapes for each theme.

Usage: python3 scripts/generate_sprites.py [--theme fruits] [--size 300]
"""

import math
import argparse
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
SPRITES_DIR = ROOT / "assets" / "sprites"


# ── Drawing helpers ────────────────────────────────────────────────────────────

def new_canvas(size: int) -> tuple[Image.Image, ImageDraw.Draw]:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def clamp_color(r, g, b) -> tuple:
    return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))


def darken(color: tuple, amount: int = 40) -> tuple:
    return clamp_color(color[0] - amount, color[1] - amount, color[2] - amount)


def lighten(color: tuple, amount: int = 50) -> tuple:
    return clamp_color(color[0] + amount, color[1] + amount, color[2] + amount)


def add_face(draw: ImageDraw.Draw, cx: int, cy: int, face_w: int,
             skin=(255, 220, 180), eye_offset_y: int = 0) -> None:
    """Draw eyes, pupils, and smile."""
    ew = max(4, face_w // 9)
    eye_y = cy - face_w // 9 + eye_offset_y
    ex1, ex2 = cx - face_w // 4, cx + face_w // 4

    # White of eyes
    draw.ellipse([ex1 - ew, eye_y - ew, ex1 + ew, eye_y + ew], fill=(255, 255, 255, 255))
    draw.ellipse([ex2 - ew, eye_y - ew, ex2 + ew, eye_y + ew], fill=(255, 255, 255, 255))

    # Pupils
    pw = max(2, ew // 2)
    draw.ellipse([ex1 - pw, eye_y - pw, ex1 + pw, eye_y + pw], fill=(40, 30, 30, 255))
    draw.ellipse([ex2 - pw, eye_y - pw, ex2 + pw, eye_y + pw], fill=(40, 30, 30, 255))

    # Glint
    gw = max(1, pw // 2)
    draw.ellipse([ex1 - ew // 3 - gw, eye_y - ew // 3 - gw,
                  ex1 - ew // 3 + gw, eye_y - ew // 3 + gw], fill=(255, 255, 255, 220))
    draw.ellipse([ex2 - ew // 3 - gw, eye_y - ew // 3 - gw,
                  ex2 - ew // 3 + gw, eye_y - ew // 3 + gw], fill=(255, 255, 255, 220))

    # Smile
    sw = face_w // 4
    smile_y = cy + face_w // 10
    draw.arc([cx - sw, smile_y, cx + sw, smile_y + face_w // 5],
             start=10, end=170, fill=(40, 30, 30, 255), width=max(2, face_w // 22))

    # Cheeks
    cr = face_w // 8
    cheek_y = cy + face_w // 14
    draw.ellipse([cx - face_w // 3 - cr, cheek_y - cr // 2,
                  cx - face_w // 3 + cr, cheek_y + cr // 2],
                 fill=(255, 150, 150, 90))
    draw.ellipse([cx + face_w // 3 - cr, cheek_y - cr // 2,
                  cx + face_w // 3 + cr, cheek_y + cr // 2],
                 fill=(255, 150, 150, 90))


def add_highlight(img: Image.Image, cx: int, cy: int, r: int) -> None:
    """Add a subtle top-left highlight to a circular shape."""
    hl = Image.new("RGBA", img.size, (0, 0, 0, 0))
    hl_draw = ImageDraw.Draw(hl)
    hl_draw.ellipse([cx - r // 2, cy - r // 2, cx, cy], fill=(255, 255, 255, 60))
    hl = hl.filter(ImageFilter.GaussianBlur(r // 5))
    img.alpha_composite(hl)


# ── Fruit sprites ──────────────────────────────────────────────────────────────

def make_apple(size: int) -> Image.Image:
    img, draw = new_canvas(size)
    cx, cy = size // 2, size // 2 + size // 14
    r = int(size * 0.38)
    color = (220, 50, 50)

    # Body (slightly irregular — two overlapping circles)
    draw.ellipse([cx - r, cy - r + size // 10, cx + r, cy + r + size // 10], fill=color + (255,))
    draw.ellipse([cx - r + size // 10, cy - r, cx + r - size // 10, cy + r], fill=color + (255,))

    # Leaf
    leaf_pts = [(cx + size // 10, cy - r), (cx + size // 3, cy - r - size // 5),
                (cx + size // 4, cy - r + size // 10)]
    draw.polygon(leaf_pts, fill=(60, 180, 60, 255))

    # Stem
    draw.line([(cx + size // 14, cy - r), (cx + size // 14, cy - r - size // 7)],
              fill=(100, 60, 20, 255), width=max(2, size // 30))

    add_face(draw, cx, cy, r * 2 - size // 6)
    add_highlight(img, cx - r // 3, cy - r // 2, r // 2)
    return img


def make_banana(size: int) -> Image.Image:
    img, draw = new_canvas(size)
    color = (255, 220, 0)
    dark = darken(color, 50)

    # Curved banana body using a thick arc
    w = size // 6
    margin = size // 8
    for offset in range(-w, w):
        draw.arc([margin + abs(offset) // 2, margin, size - margin,
                  size - margin // 2], start=200, end=340,
                 fill=color + (255,), width=3)

    # Fill the banana shape properly
    points = []
    import math as m
    ox, oy = size * 0.52, size * 0.48
    for angle in range(200, 341, 3):
        rx, ry = size * 0.40, size * 0.36
        x = ox + rx * m.cos(m.radians(angle))
        y = oy + ry * m.sin(m.radians(angle))
        points.append((x, y))
    # Outer arc (thicker)
    for angle in range(340, 199, -3):
        rx, ry = size * 0.30, size * 0.26
        x = ox + rx * m.cos(m.radians(angle))
        y = oy + ry * m.sin(m.radians(angle))
        points.append((x, y))
    if len(points) >= 3:
        draw.polygon(points, fill=color + (255,))

    # Tip ends
    draw.ellipse([size // 8 - 8, size // 2 - 8, size // 8 + 8, size // 2 + 8],
                 fill=dark + (255,))
    draw.ellipse([size - size // 6 - 8, size // 4 - 8,
                  size - size // 6 + 8, size // 4 + 8], fill=dark + (255,))

    # Simple face in the middle
    cx, cy = int(size * 0.48), int(size * 0.52)
    add_face(draw, cx, cy, size // 3)
    return img


def make_generic_round(size: int, color: tuple, leaf_color=None) -> Image.Image:
    """Generic round fruit/vegetable sprite."""
    img, draw = new_canvas(size)
    cx, cy = size // 2, size // 2
    r = int(size * 0.40)
    draw.ellipse([cx - r, cy - r + size // 14, cx + r, cy + r - size // 14],
                 fill=color + (255,))

    if leaf_color:
        lc = leaf_color
        draw.polygon([(cx - size // 8, cy - r), (cx + size // 10, cy - r - size // 5),
                       (cx + size // 5, cy - r)], fill=lc + (255,))
        draw.line([(cx, cy - r), (cx, cy - r - size // 8)],
                  fill=darken(color, 40) + (255,), width=max(2, size // 28))

    add_face(draw, cx, cy, r * 2 - size // 8)
    add_highlight(img, cx - r // 2, cy - r // 2, r // 2)
    return img


def make_strawberry(size: int) -> Image.Image:
    img, draw = new_canvas(size)
    cx, cy = size // 2, size // 2 + size // 12
    color = (230, 50, 70)

    # Heart-like strawberry shape
    r = int(size * 0.37)
    draw.polygon(
        [(cx, cy + r), (cx - r, cy - r // 3), (cx - r // 3, cy - r),
         (cx, cy - r // 2), (cx + r // 3, cy - r), (cx + r, cy - r // 3)],
        fill=color + (255,),
    )

    # Seeds (tiny dots)
    import random as rnd
    rnd.seed(42)
    for _ in range(12):
        sx = cx + rnd.randint(-r // 2, r // 2)
        sy = cy + rnd.randint(-r // 3, r // 2)
        sd = max(2, size // 40)
        draw.ellipse([sx - sd, sy - sd, sx + sd, sy + sd],
                     fill=(200, 220, 150, 200))

    # Leaves
    for angle in [-30, 0, 30]:
        rad = math.radians(angle - 90)
        lx = cx + int(r * 0.5 * math.cos(rad))
        ly = (cy - r) + int(r * 0.4 * math.sin(rad))
        draw.polygon([(cx, cy - r), (lx - size // 12, ly - size // 8),
                       (lx + size // 12, ly)], fill=(50, 170, 50, 255))

    add_face(draw, cx, cy, r - size // 10)
    add_highlight(img, cx - r // 2, cy - r // 2, r // 2)
    return img


# ── Animal sprites ─────────────────────────────────────────────────────────────

def make_cat(size: int) -> Image.Image:
    img, draw = new_canvas(size)
    cx, cy = size // 2, size // 2
    r = int(size * 0.35)
    color = (200, 165, 125)

    # Body
    draw.ellipse([cx - r, cy - r + size // 10, cx + r, cy + r], fill=color + (255,))

    # Head (slightly above center)
    hr = int(size * 0.28)
    hx, hy = cx, cy - size // 6
    draw.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=color + (255,))

    # Ears (triangles)
    ear_size = hr // 2
    for side in [-1, 1]:
        ex = hx + side * int(hr * 0.65)
        draw.polygon(
            [(ex, hy - hr + 4), (ex - side * ear_size, hy - hr - ear_size),
             (ex + side * ear_size // 2, hy - hr - ear_size + 4)],
            fill=color + (255,),
        )
        # Inner ear
        draw.polygon(
            [(ex, hy - hr + 6), (ex - side * (ear_size - 4), hy - hr - ear_size + 4),
             (ex + side * (ear_size // 2 - 2), hy - hr - ear_size + 6)],
            fill=(255, 180, 180, 220),
        )

    # Face details
    add_face(draw, hx, hy, hr * 2 - size // 10, eye_offset_y=-size // 20)

    # Nose
    draw.polygon([(hx, hy + hr // 6), (hx - hr // 8, hy),
                   (hx + hr // 8, hy)], fill=(255, 150, 150, 255))

    # Whiskers
    wl = hr // 2
    wy = hy + hr // 10
    for side in [-1, 1]:
        for dy in [-2, 2, 6]:
            draw.line([(hx + side * hr // 5, wy + dy),
                        (hx + side * (hr // 5 + wl), wy + dy - side * 2)],
                       fill=(100, 80, 60, 180), width=1)

    add_highlight(img, hx - hr // 2, hy - hr // 2, hr // 2)
    return img


def make_bear(size: int) -> Image.Image:
    img, draw = new_canvas(size)
    cx, cy = size // 2, size // 2
    r = int(size * 0.36)
    color = (155, 110, 70)
    light = lighten(color, 60)

    # Body
    draw.ellipse([cx - r, cy - r // 2, cx + r, cy + r], fill=color + (255,))

    # Tummy
    tr = int(r * 0.55)
    draw.ellipse([cx - tr, cy - tr // 3, cx + tr, cy + tr - r // 5],
                 fill=light + (255,))

    # Head
    hr = int(size * 0.28)
    hx, hy = cx, cy - int(r * 0.6)
    draw.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=color + (255,))

    # Ears
    er = int(hr * 0.38)
    for side in [-1, 1]:
        ex = hx + side * int(hr * 0.78)
        draw.ellipse([ex - er, hy - hr + 2, ex + er, hy - hr + 2 + er * 2],
                     fill=color + (255,))
        draw.ellipse([ex - er + 4, hy - hr + 6, ex + er - 4, hy - hr + er * 2 - 2],
                     fill=light + (200,))

    # Snout
    sn_r = int(hr * 0.35)
    draw.ellipse([hx - sn_r, hy + hr // 8, hx + sn_r, hy + hr // 8 + sn_r],
                 fill=light + (255,))
    draw.ellipse([hx - sn_r // 3, hy + hr // 5, hx + sn_r // 3, hy + hr // 5 + sn_r // 2],
                 fill=(80, 50, 40, 255))

    add_face(draw, hx, hy, hr * 2 - size // 10, eye_offset_y=-size // 18)
    add_highlight(img, hx - hr // 2, hy - hr // 2, hr // 2)
    return img


def make_rabbit(size: int) -> Image.Image:
    img, draw = new_canvas(size)
    cx, cy = size // 2, size // 2
    r = int(size * 0.34)
    color = (235, 225, 215)
    pink = (255, 180, 200)

    # Body
    draw.ellipse([cx - r, cy, cx + r, cy + r + size // 8], fill=color + (255,))

    # Head
    hr = int(size * 0.27)
    hx, hy = cx, cy - size // 10
    draw.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=color + (255,))

    # Long ears
    for side in [-1, 1]:
        ex = hx + side * int(hr * 0.5)
        ear_h = int(hr * 1.4)
        ear_w = int(hr * 0.28)
        draw.ellipse([ex - ear_w, hy - hr - ear_h, ex + ear_w, hy - hr + 10],
                     fill=color + (255,))
        draw.ellipse([ex - ear_w + 5, hy - hr - ear_h + 6,
                      ex + ear_w - 5, hy - hr + 4], fill=pink + (200,))

    # Nose
    draw.ellipse([hx - 5, hy + hr // 6 - 4, hx + 5, hy + hr // 6 + 4],
                 fill=pink + (255,))

    add_face(draw, hx, hy, hr * 2 - size // 10, eye_offset_y=-size // 18)
    add_highlight(img, hx - hr // 2, hy - hr // 2, hr // 2)
    return img


def make_duck(size: int) -> Image.Image:
    img, draw = new_canvas(size)
    cx, cy = size // 2, size // 2
    r = int(size * 0.36)
    color = (255, 225, 30)

    # Body (egg shape)
    draw.ellipse([cx - r, cy - r // 2, cx + r, cy + r + size // 12], fill=color + (255,))

    # Head
    hr = int(size * 0.24)
    hx, hy = cx + r // 4, cy - int(r * 0.5)
    draw.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=color + (255,))

    # Bill
    bill_pts = [(hx + hr - 4, hy), (hx + hr + size // 8, hy - size // 16),
                (hx + hr + size // 8, hy + size // 16)]
    draw.polygon(bill_pts, fill=(255, 140, 0, 255))

    # Wing hint
    draw.arc([cx - r + 4, cy - r // 4, cx + r - 4, cy + r // 2],
             start=200, end=340, fill=darken(color, 30) + (180,),
             width=max(2, size // 20))

    add_face(draw, hx, hy, hr * 2 - size // 12, eye_offset_y=-size // 22)
    add_highlight(img, hx - hr // 2, hy - hr // 2, hr // 2)
    return img


def make_elephant(size: int) -> Image.Image:
    img, draw = new_canvas(size)
    cx, cy = size // 2, size // 2
    r = int(size * 0.36)
    color = (150, 150, 175)

    # Body
    draw.ellipse([cx - r, cy - r // 3, cx + r, cy + r], fill=color + (255,))

    # Head
    hr = int(size * 0.29)
    hx, hy = cx, cy - int(r * 0.5)
    draw.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=color + (255,))

    # Big ears
    for side in [-1, 1]:
        ear_cx = hx + side * int(hr * 0.9)
        ear_r = int(hr * 0.7)
        draw.ellipse([ear_cx - ear_r, hy - ear_r + 8,
                      ear_cx + ear_r, hy + ear_r + 8], fill=color + (255,))
        draw.ellipse([ear_cx - ear_r + 8, hy - ear_r + 14,
                      ear_cx + ear_r - 8, hy + ear_r], fill=(200, 160, 160, 160,))

    # Trunk
    trunk_pts = [(hx - hr // 5, hy + hr // 2),
                 (hx + hr // 5, hy + hr // 2),
                 (hx + hr // 4 + 4, hy + hr),
                 (hx - hr // 4 + 4, hy + hr + hr // 2),
                 (hx - hr // 2, hy + hr + hr // 2 + 4),
                 (hx - hr // 2 - 4, hy + hr + hr // 2 - 4)]
    draw.polygon(trunk_pts, fill=color + (255,))

    add_face(draw, hx, hy, hr * 2 - size // 8, eye_offset_y=-size // 16)
    add_highlight(img, hx - hr // 2, hy - hr // 2, hr // 2)
    return img


# ── Shape sprites ──────────────────────────────────────────────────────────────

def make_star(size: int, color=(255, 220, 0)) -> Image.Image:
    img, draw = new_canvas(size)
    cx, cy = size // 2, size // 2
    outer, inner = size * 0.42, size * 0.18
    points = []
    for i in range(10):
        angle = math.radians(i * 36 - 90)
        r = outer if i % 2 == 0 else inner
        points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    draw.polygon(points, fill=color + (255,))
    add_face(draw, cx, cy + size // 20, int(inner * 2))
    add_highlight(img, cx - int(outer // 2), cy - int(outer // 2), int(outer // 2))
    return img


def make_heart(size: int, color=(255, 80, 110)) -> Image.Image:
    img, draw = new_canvas(size)
    cx, cy = size // 2, int(size * 0.52)
    r = int(size * 0.25)
    # Two circles top + triangle bottom
    draw.ellipse([cx - r * 2 + 2, cy - r * 2, cx, cy], fill=color + (255,))
    draw.ellipse([cx, cy - r * 2, cx + r * 2 - 2, cy], fill=color + (255,))
    draw.polygon([(cx - r * 2 + 4, cy - r // 2),
                   (cx + r * 2 - 4, cy - r // 2),
                   (cx, cy + int(r * 2.2))], fill=color + (255,))
    add_face(draw, cx, cy - r // 2, int(r * 1.6))
    add_highlight(img, cx - r, cy - r * 2, r)
    return img


# ── Theme registry ─────────────────────────────────────────────────────────────

THEME_GENERATORS = {
    "fruits": {
        "apple":      lambda s: make_apple(s),
        "banana":     lambda s: make_banana(s),
        "grape":      lambda s: make_generic_round(s, (130, 50, 180), (50, 140, 50)),
        "orange":     lambda s: make_generic_round(s, (255, 145, 0), (50, 160, 50)),
        "strawberry": lambda s: make_strawberry(s),
        "watermelon": lambda s: make_generic_round(s, (50, 185, 95), (50, 140, 50)),
        "cherry":     lambda s: make_generic_round(s, (180, 30, 60), (50, 140, 50)),
        "lemon":      lambda s: make_generic_round(s, (245, 240, 45), (60, 160, 40)),
        "peach":      lambda s: make_generic_round(s, (255, 185, 125), (80, 155, 40)),
        "kiwi":       lambda s: make_generic_round(s, (90, 155, 55), None),
    },
    "vegetables": {
        "carrot":     lambda s: make_generic_round(s, (255, 130, 0), (50, 170, 50)),
        "broccoli":   lambda s: make_generic_round(s, (45, 170, 45), None),
        "tomato":     lambda s: make_generic_round(s, (215, 55, 55), (50, 170, 50)),
        "corn":       lambda s: make_generic_round(s, (255, 230, 30), (60, 160, 40)),
        "eggplant":   lambda s: make_generic_round(s, (115, 45, 160), (60, 170, 40)),
        "pumpkin":    lambda s: make_generic_round(s, (230, 105, 25), (50, 150, 40)),
        "pea":        lambda s: make_generic_round(s, (100, 200, 75), None),
        "radish":     lambda s: make_generic_round(s, (215, 75, 95), (50, 170, 50)),
    },
    "animals": {
        "cat":        lambda s: make_cat(s),
        "bear":       lambda s: make_bear(s),
        "rabbit":     lambda s: make_rabbit(s),
        "duck":       lambda s: make_duck(s),
        "elephant":   lambda s: make_elephant(s),
        "dog":        lambda s: make_generic_round(s, (210, 170, 110), None),
        "giraffe":    lambda s: make_generic_round(s, (240, 200, 70), None),
        "penguin":    lambda s: make_generic_round(s, (60, 60, 80), None),
        "fox":        lambda s: make_generic_round(s, (220, 115, 45), None),
        "koala":      lambda s: make_generic_round(s, (170, 170, 185), None),
    },
    "shapes": {
        "star":     lambda s: make_star(s, (255, 220, 0)),
        "heart":    lambda s: make_heart(s, (255, 80, 110)),
        "circle":   lambda s: make_generic_round(s, (100, 185, 255), None),
        "square":   lambda s: make_generic_round(s, (255, 150, 80), None),
        "triangle": lambda s: make_generic_round(s, (100, 220, 150), None),
        "diamond":  lambda s: make_generic_round(s, (200, 100, 255), None),
    },
}


def generate_theme(theme: str, size: int = 300, overwrite: bool = False) -> None:
    if theme not in THEME_GENERATORS:
        print(f"Unknown theme: {theme}. Available: {list(THEME_GENERATORS)}")
        return

    out_dir = SPRITES_DIR / theme
    out_dir.mkdir(parents=True, exist_ok=True)

    generators = THEME_GENERATORS[theme]
    for name, fn in generators.items():
        path = out_dir / f"{name}.png"
        if path.exists() and not overwrite:
            continue
        try:
            img = fn(size)
            img.save(path)
            print(f"  ✓ {theme}/{name}.png")
        except Exception as e:
            print(f"  ✗ {theme}/{name}: {e}")


def main():
    parser = argparse.ArgumentParser(description="Generate cartoon sprites")
    parser.add_argument("--theme", default="all", help="Theme name or 'all'")
    parser.add_argument("--size", type=int, default=300, help="Sprite size in px")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing files")
    args = parser.parse_args()

    themes = list(THEME_GENERATORS) if args.theme == "all" else [args.theme]
    print(f"Generating sprites ({args.size}px)...")
    for theme in themes:
        print(f"\n{theme}:")
        generate_theme(theme, args.size, args.overwrite)
    print("\nDone.")


if __name__ == "__main__":
    main()
