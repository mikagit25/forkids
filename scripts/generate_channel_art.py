#!/usr/bin/env python3
"""
Generate YouTube channel art for Happy Bear Kids.

Outputs:
  output/channel/banner.png   — 2560×1440 (YouTube channel banner)
  output/channel/icon.png     — 800×800   (channel profile picture)
  output/channel/thumbnail_template.png — 1280×720 (video thumbnail base)

Safe zone for banner: center 1546×423px (visible on all devices)
"""

import math
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT    = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "output" / "channel"

# ── Colour palette ────────────────────────────────────────────────────────────
BG_TOP    = (255, 240, 100)   # warm yellow
BG_BOTTOM = (255, 180,  60)   # orange-yellow
ACCENT1   = (255, 107, 107)   # coral red
ACCENT2   = ( 77, 150, 255)   # bright blue
ACCENT3   = (107, 203, 119)   # green
WHITE     = (255, 255, 255)
DARK      = ( 60,  30,  10)   # dark brown (text shadow)

SPRITES_DIR = ROOT / "assets" / "sprites"


def load_sprite(path: Path, size: int) -> Image.Image:
    img = Image.open(path).convert("RGBA")
    img.thumbnail((size, size), Image.LANCZOS)
    return img


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def draw_gradient(img: Image.Image, top_color, bottom_color):
    draw = ImageDraw.Draw(img)
    W, H = img.size
    for y in range(H):
        r = int(top_color[0] + (bottom_color[0] - top_color[0]) * y / H)
        g = int(top_color[1] + (bottom_color[1] - top_color[1]) * y / H)
        b = int(top_color[2] + (bottom_color[2] - top_color[2]) * y / H)
        draw.line([(0, y), (W, y)], fill=(r, g, b))


def draw_polka_dots(img: Image.Image, color, alpha=40, count=60, rng_seed=42):
    """Subtle polka dots decoration."""
    W, H = img.size
    rng = random.Random(rng_seed)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for _ in range(count):
        x = rng.randint(0, W)
        y = rng.randint(0, H)
        r = rng.randint(20, 70)
        d.ellipse([x-r, y-r, x+r, y+r], fill=color + (alpha,))
    img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"),
              (0, 0))


def draw_wavy_band(img: Image.Image, y_center: int, height: int, color, alpha=200):
    """Horizontal wavy band across the image."""
    W = img.width
    overlay = Image.new("RGBA", (W, img.height), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    pts = []
    for x in range(0, W + 10, 5):
        wave = math.sin(x / 80) * 18
        pts.append((x, y_center - height//2 + wave))
    for x in range(W, -10, -5):
        wave = math.sin(x / 80) * 18
        pts.append((x, y_center + height//2 + wave))
    d.polygon(pts, fill=color + (alpha,))
    base = img.convert("RGBA")
    img.paste(Image.alpha_composite(base, overlay).convert("RGB"), (0, 0))


def draw_stars_bg(img: Image.Image, count=40, rng_seed=7):
    """Small star sparkles."""
    W, H = img.size
    rng = random.Random(rng_seed)
    d = ImageDraw.Draw(img)
    for _ in range(count):
        x = rng.randint(30, W-30)
        y = rng.randint(30, H-30)
        r = rng.randint(3, 10)
        alpha = rng.randint(120, 220)
        star = Image.new("RGBA", (r*4, r*4), (0,0,0,0))
        sd = ImageDraw.Draw(star)
        # 4-point star
        cx, cy = r*2, r*2
        for angle in range(0, 360, 90):
            rad = math.radians(angle)
            x1 = cx + math.cos(rad) * r
            y1 = cy + math.sin(rad) * r
            x2 = cx + math.cos(rad + math.pi/4) * r//2
            y2 = cy + math.sin(rad + math.pi/4) * r//2
            x3 = cx + math.cos(rad + math.pi/2) * r
            y3 = cy + math.sin(rad + math.pi/2) * r
            sd.polygon([(cx,cy),(x1,y1),(x2,y2),(x3,y3)],
                        fill=(255,255,255,alpha))
        img.paste(star, (x - r*2, y - r*2), star)


def load_font(size: int):
    for path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def draw_outlined_text(draw, pos, text, font, fill, outline, outline_width=6):
    x, y = pos
    for dx in range(-outline_width, outline_width+1, 2):
        for dy in range(-outline_width, outline_width+1, 2):
            if dx*dx + dy*dy <= outline_width*outline_width:
                draw.text((x+dx, y+dy), text, font=font, fill=outline)
    draw.text(pos, text, font=font, fill=fill)


def text_center_x(draw, text, font, W):
    try:
        bb = draw.textbbox((0, 0), text, font=font)
        return (W - (bb[2] - bb[0])) // 2
    except Exception:
        return W // 2 - len(text) * font.size // 4


# ── BANNER (2560×1440) ────────────────────────────────────────────────────────

def generate_banner() -> Path:
    W, H = 2560, 1440
    # Safe zone: center 1546×423 px
    SAFE_X = (W - 1546) // 2  # 507
    SAFE_Y = (H - 423) // 2   # 508

    img = Image.new("RGB", (W, H))
    draw_gradient(img, BG_TOP, BG_BOTTOM)
    draw_polka_dots(img, WHITE, alpha=30, count=80)
    draw_stars_bg(img, count=50)

    # Wavy white band across safe zone
    draw_wavy_band(img, H//2, 500, WHITE, alpha=180)

    draw = ImageDraw.Draw(img)

    # Decorative shapes — LEFT side (outside safe zone)
    shapes_dir = SPRITES_DIR / "shapes"
    shape_files = [shapes_dir / n for n in
                   ["star.png", "heart.png", "circle.png", "diamond.png"]]
    positions_l = [(180, 280), (80, 680), (300, 1100), (150, 1250)]
    for (sx, sy), sf in zip(positions_l, shape_files):
        if sf.exists():
            sp = load_sprite(sf, 200)
            sp = sp.rotate(random.Random(sx).randint(-25, 25), expand=True)
            img.paste(sp, (sx - sp.width//2, sy - sp.height//2), sp)

    # Decorative shapes — RIGHT side
    positions_r = [(2380, 300), (2480, 750), (2260, 1050), (2420, 1250)]
    shape_files_r = [shapes_dir / n for n in
                     ["triangle.png", "square.png", "oval.png", "rectangle.png"]]
    for (sx, sy), sf in zip(positions_r, shape_files_r):
        if sf.exists():
            sp = load_sprite(sf, 200)
            sp = sp.rotate(random.Random(sx).randint(-20, 20), expand=True)
            img.paste(sp, (sx - sp.width//2, sy - sp.height//2), sp)

    # Animals — left cluster
    animals_dir = SPRITES_DIR / "animals"
    animal_names = ["bear.png", "bunny.png", "panda.png",
                    "elephant.png", "giraffe.png", "monkey.png"]
    left_positions = [
        (420, 580), (230, 820), (470, 1060),
        (700, 500), (680, 950), (500, 1200),
    ]
    for (ax, ay), an in zip(left_positions, animal_names):
        p = animals_dir / an
        if p.exists():
            sp = load_sprite(p, 220)
            img.paste(sp, (ax - sp.width//2, ay - sp.height//2), sp)

    # Animals — right cluster
    right_positions = [
        (2140, 580), (2330, 820), (2090, 1060),
        (1860, 500), (1880, 950), (2060, 1200),
    ]
    animal_names_r = ["duck.png", "frog.png", "owl.png",
                      "parrot.png", "penguin.png", "pig.png"]
    for (ax, ay), an in zip(right_positions, animal_names_r):
        p = animals_dir / an
        if p.exists():
            sp = load_sprite(p, 220)
            img.paste(sp, (ax - sp.width//2, ay - sp.height//2), sp)

    # ── SAFE ZONE TEXT ────────────────────────────────────────────────────────
    # Title
    font_title = load_font(200)
    font_sub   = load_font(80)
    font_tag   = load_font(56)

    title    = "Happy Bear Kids"
    subtitle = "Learn • Play • Grow"
    tagline  = "🔤 ABC  🔢 Numbers  🎨 Colors  ⭐ Shapes  🎵 Dance"

    draw = ImageDraw.Draw(img)

    tx = text_center_x(draw, title, font_title, W)
    draw_outlined_text(draw, (tx, SAFE_Y + 10), title, font_title,
                       fill=WHITE, outline=ACCENT1, outline_width=8)

    sx = text_center_x(draw, subtitle, font_sub, W)
    draw_outlined_text(draw, (sx, SAFE_Y + 220), subtitle, font_sub,
                       fill=ACCENT2, outline=WHITE, outline_width=5)

    tx2 = text_center_x(draw, tagline, font_tag, W)
    draw_outlined_text(draw, (tx2, SAFE_Y + 330), tagline, font_tag,
                       fill=DARK, outline=WHITE, outline_width=4)

    # Safe zone outline (for reference — comment out for final)
    # draw.rectangle([SAFE_X, SAFE_Y, SAFE_X+1546, SAFE_Y+423],
    #                outline=(255,0,0,128), width=3)

    out = OUT_DIR / "banner.png"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG", optimize=True)
    print(f"  Banner   → {out}  ({W}×{H})")
    return out


# ── ICON (800×800) ────────────────────────────────────────────────────────────

def generate_icon() -> Path:
    SIZE = 800
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))

    # Circle background
    d = ImageDraw.Draw(img)
    # Gradient simulation: draw concentric circles
    for r in range(SIZE//2, 0, -2):
        ratio = 1 - r / (SIZE//2)
        cr = int(BG_TOP[0] + (ACCENT1[0] - BG_TOP[0]) * ratio * 0.5)
        cg = int(BG_TOP[1] + (ACCENT1[1] - BG_TOP[1]) * ratio * 0.5)
        cb = int(BG_TOP[2] + (ACCENT1[2] - BG_TOP[2]) * ratio * 0.5)
        cx, cy = SIZE//2, SIZE//2
        d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(cr, cg, cb, 255))

    # Bear sprite — centered, large
    bear_path = SPRITES_DIR / "animals" / "bear.png"
    if bear_path.exists():
        bear = load_sprite(bear_path, 520)
        bx = (SIZE - bear.width) // 2
        by = (SIZE - bear.height) // 2 - 30
        img.paste(bear, (bx, by), bear)

    # "HBK" or star accent
    star_path = SPRITES_DIR / "shapes" / "star.png"
    if star_path.exists():
        star = load_sprite(star_path, 120)
        img.paste(star, (SIZE - 160, 40), star)

    # Circular white outline
    d2 = ImageDraw.Draw(img)
    margin = 12
    d2.ellipse([margin, margin, SIZE-margin, SIZE-margin],
               outline=WHITE, width=16)

    # Clip to circle
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, SIZE, SIZE], fill=255)
    result = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    result.paste(img, (0, 0), mask)

    out = OUT_DIR / "icon.png"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    result.save(out, "PNG")
    print(f"  Icon     → {out}  ({SIZE}×{SIZE})")
    return out


# ── THUMBNAIL TEMPLATE (1280×720) ─────────────────────────────────────────────

def generate_thumbnail_template() -> Path:
    W, H = 1280, 720
    img = Image.new("RGB", (W, H))
    draw_gradient(img, BG_TOP, BG_BOTTOM)
    draw_polka_dots(img, WHITE, alpha=25, count=40)

    # Left panel — white rounded rectangle for title text
    overlay = Image.new("RGBA", (W, H), (0,0,0,0))
    d = ImageDraw.Draw(overlay)
    d.rounded_rectangle([40, 40, W//2 - 20, H-40], radius=50,
                        fill=WHITE + (230,))
    img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"),
              (0, 0))

    draw = ImageDraw.Draw(img)

    # Logo text top-left
    font_logo = load_font(42)
    draw_outlined_text(draw, (70, 55), "Happy Bear Kids",
                       font_logo, fill=ACCENT1, outline=WHITE, outline_width=3)

    # Main text placeholder
    font_main = load_font(120)
    draw_outlined_text(draw, (70, 160), "ABC",
                       font_main, fill=ACCENT2, outline=DARK, outline_width=6)

    font_sub = load_font(64)
    draw_outlined_text(draw, (70, 320), "Learn the Alphabet",
                       font_sub, fill=DARK, outline=WHITE, outline_width=4)

    # Right side — animal sprite
    bear_path = SPRITES_DIR / "animals" / "bear.png"
    if bear_path.exists():
        bear = load_sprite(bear_path, 520)
        bx = W - bear.width - 30
        by = (H - bear.height) // 2
        img.paste(bear, (bx, by), bear)

    # Bottom strip
    d2 = ImageDraw.Draw(img)
    d2.rectangle([0, H-70, W, H], fill=ACCENT1)
    font_strip = load_font(44)
    strip_text = "🔤 🔢 🎨 ⭐ 🎵  Subscribe for more!"
    sx = text_center_x(d2, strip_text, font_strip, W)
    d2.text((sx, H-62), strip_text, font=font_strip, fill=WHITE)

    out = OUT_DIR / "thumbnail_template.png"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG")
    print(f"  Thumbnail→ {out}  ({W}×{H})")
    return out


def main():
    print(f"\nGenerating channel art → {OUT_DIR}/\n")
    generate_banner()
    generate_icon()
    generate_thumbnail_template()
    print("\nDone. Upload to YouTube Studio:\n"
          "  banner.png            — Customise Channel → Banner image\n"
          "  icon.png              — Customise Channel → Picture\n")


if __name__ == "__main__":
    main()
