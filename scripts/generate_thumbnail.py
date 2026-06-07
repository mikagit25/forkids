#!/usr/bin/env python3
"""
Generate custom YouTube thumbnails per video type.

Output: 1280×720 PNG — YouTube максимальное разрешение

Usage:
    python3 generate_thumbnail.py --type dance --theme animals --title "Animals Dance Party"
    python3 generate_thumbnail.py --type abc --theme animals --letter A --word Apple
    python3 generate_thumbnail.py --type short_number --number 3
    python3 generate_thumbnail.py --type short_color --color red
    python3 generate_thumbnail.py --type short_shape --shape circle
    python3 generate_thumbnail.py --all-previews   # генерирует все типы для просмотра
"""

import argparse
import math
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT       = Path(__file__).resolve().parent.parent
SPRITES    = ROOT / "assets" / "sprites"
OUT_DIR    = ROOT / "output" / "thumbnails"

W, H = 1280, 720

# Цветовые схемы по типу видео
SCHEMES = {
    "dance":        {"bg_top": (255, 200, 40),  "bg_bot": (255, 130, 30),  "accent": (255, 60, 60),   "text": (255,255,255)},
    "abc":          {"bg_top": (60,  180, 255),  "bg_bot": (20,  100, 220),  "accent": (255, 240, 60),  "text": (255,255,255)},
    "numbers":      {"bg_top": (100, 210, 100),  "bg_bot": (30,  140, 50),   "accent": (255, 230, 40),  "text": (255,255,255)},
    "colors":       {"bg_top": (250, 100, 180),  "bg_bot": (180, 40,  140),  "accent": (255, 240, 80),  "text": (255,255,255)},
    "short_letter": {"bg_top": (60,  180, 255),  "bg_bot": (20,  100, 220),  "accent": (255, 240, 60),  "text": (255,255,255)},
    "short_number": {"bg_top": (100, 210, 100),  "bg_bot": (30,  140, 50),   "accent": (255, 230, 40),  "text": (255,255,255)},
    "short_color":  {"bg_top": (250, 100, 180),  "bg_bot": (180, 40,  140),  "accent": (255, 240, 80),  "text": (255,255,255)},
    "short_shape":  {"bg_top": (160, 100, 255),  "bg_bot": (90,  40,  200),  "accent": (255, 220, 60),  "text": (255,255,255)},
    "short_dance":       {"bg_top": (255, 200, 40),   "bg_bot": (255, 130, 30),   "accent": (255, 60,  60),  "text": (255,255,255)},
    "short_vocabulary":  {"bg_top": (255, 170, 60),   "bg_bot": (200, 100, 20),   "accent": (255, 240, 80),  "text": (255,255,255)},
    "short_counting":    {"bg_top": (80,  200, 200),   "bg_bot": (20,  130, 160),  "accent": (255, 240, 60),  "text": (255,255,255)},
}

# Цвет фона для short_color thumbnails
COLOR_BG = {
    "red":    (220, 50,  50),
    "orange": (230, 120, 30),
    "yellow": (220, 200, 30),
    "green":  (50,  170, 70),
    "blue":   (50,  120, 220),
    "purple": (130, 70,  200),
    "pink":   (220, 80,  160),
    "brown":  (130, 80,  40),
}


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


def load_sprite(path: Path, size: int) -> Image.Image:
    img = Image.open(path).convert("RGBA")
    img.thumbnail((size, size), Image.LANCZOS)
    return img


def gradient_bg(top, bot) -> Image.Image:
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        r = int(top[0] + (bot[0] - top[0]) * y / H)
        g = int(top[1] + (bot[1] - top[1]) * y / H)
        b = int(top[2] + (bot[2] - top[2]) * y / H)
        d.line([(0, y), (W, y)], fill=(r, g, b))
    return img


def add_dots(img, color=(255,255,255), alpha=25, count=40, seed=1):
    W2, H2 = img.size
    rng = random.Random(seed)
    ov = Image.new("RGBA", (W2, H2), (0,0,0,0))
    d  = ImageDraw.Draw(ov)
    for _ in range(count):
        x, y = rng.randint(0, W2), rng.randint(0, H2)
        r = rng.randint(15, 55)
        d.ellipse([x-r, y-r, x+r, y+r], fill=color+(alpha,))
    base = img.convert("RGBA")
    return Image.alpha_composite(base, ov).convert("RGB")


def outlined_text(draw, pos, text, font, fill, outline, stroke=6):
    x, y = pos
    for dx in range(-stroke, stroke+1, 2):
        for dy in range(-stroke, stroke+1, 2):
            if dx*dx + dy*dy <= stroke*stroke:
                draw.text((x+dx, y+dy), text, font=font, fill=outline)
    draw.text(pos, text, font=font, fill=fill)


def center_x(draw, text, font):
    try:
        bb = draw.textbbox((0,0), text, font=font)
        return (W - (bb[2]-bb[0])) // 2
    except Exception:
        return W//2


def text_w(draw, text, font):
    try:
        bb = draw.textbbox((0,0), text, font=font)
        return bb[2]-bb[0]
    except Exception:
        return len(text)*20


def add_logo_badge(draw):
    """Маленький логотип HBK в верхнем левом углу."""
    font = load_font(32)
    outlined_text(draw, (22, 18), "Happy Bear Kids", font,
                  fill=(255,255,255), outline=(0,0,0,180), stroke=3)


def add_shorts_badge(img):
    """Красный #SHORTS бейдж — нижний правый угол, не перекрывает текст."""
    ov   = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d    = ImageDraw.Draw(ov)
    font = load_font(36)
    bw, bh = 280, 62
    x1 = W - bw - 20
    y1 = H - bh - 16
    d.rounded_rectangle([x1, y1, x1 + bw, y1 + bh], radius=31, fill=(220, 0, 0, 235))
    tw = text_w(d, "#SHORTS", font)
    d.text((x1 + (bw - tw) // 2, y1 + (bh - 36) // 2), "#SHORTS",
           font=font, fill=(255, 255, 255, 255))
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")


# ── Thumbnail generators ──────────────────────────────────────────────────────

def thumb_dance(theme: str, title: str, variant: int = 0) -> Image.Image:
    sc  = SCHEMES["dance"]
    img = gradient_bg(sc["bg_top"], sc["bg_bot"])
    img = add_dots(img, seed=variant)

    # 3 sprites from the correct theme (fall back to animals)
    d = SPRITES / theme
    if not d.exists() or not list(d.glob("*.png")):
        d = SPRITES / "animals"
    sprites = sorted(d.glob("*.png"))
    chosen    = [sprites[(variant * 3 + i) % len(sprites)] for i in range(3)]
    positions = [(180, 310), (640, 250), (1100, 310)]
    for sp_path, (px, py) in zip(chosen, positions):
        sp = load_sprite(sp_path, 340)
        img.paste(sp, (px - sp.width//2, py - sp.height//2), sp)

    draw = ImageDraw.Draw(img)
    add_logo_badge(draw)

    # Title in lower dark band — height adapts to number of wrapped lines
    font_t    = load_font(66)
    line_h    = 76
    words     = title.replace(" #shorts", "").split()
    lines, cur = [], []
    for w in words:
        test = " ".join(cur + [w])
        if text_w(draw, test, font_t) > W - 80:
            if cur:
                lines.append(" ".join(cur))
            cur = [w]
        else:
            cur.append(w)
    if cur:
        lines.append(" ".join(cur))
    lines = lines[:3]   # cap at 3 lines max

    band_h = max(130, len(lines) * line_h + 28)
    draw.rectangle([0, H - band_h, W, H], fill=(0, 0, 0, 170))

    y0 = H - band_h + (band_h - len(lines) * line_h) // 2
    for line in lines:
        x = center_x(draw, line, font_t)
        outlined_text(draw, (x, y0), line, font_t,
                      fill=(255, 255, 255), outline=(0, 0, 0), stroke=4)
        y0 += line_h

    return img


def thumb_abc(theme: str, letter: str, word: str) -> Image.Image:
    sc  = SCHEMES["abc"]
    img = gradient_bg(sc["bg_top"], sc["bg_bot"])
    img = add_dots(img, color=(255,255,255), alpha=20)

    # Big letter on left panel
    ov  = Image.new("RGBA", (W, H), (0,0,0,0))
    d   = ImageDraw.Draw(ov)
    d.rounded_rectangle([30, 30, 520, H-30], radius=50, fill=(255,255,255,220))
    img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")

    draw = ImageDraw.Draw(img)
    font_letter = load_font(340)
    font_word   = load_font(82)
    add_logo_badge(draw)

    # Letter
    lx = (520 - text_w(draw, letter, font_letter)) // 2 + 30
    outlined_text(draw, (lx, 30), letter, font_letter,
                  fill=sc["accent"], outline=(30,80,180), stroke=8)
    # Word below
    wx = (520 - text_w(draw, word, font_word)) // 2 + 30
    outlined_text(draw, (wx, H-120), word, font_word,
                  fill=(30,80,180), outline=(255,255,255), stroke=5)

    # Animal on right
    d2 = SPRITES / theme
    animals = sorted(d2.glob("*.png"))
    if animals:
        idx = ord(letter.upper()) - ord('A') if letter.isalpha() else 0
        sp = load_sprite(animals[idx % len(animals)], 480)
        img.paste(sp, (W - sp.width - 40, (H - sp.height)//2), sp)

    return img


def thumb_numbers(theme: str, number: str) -> Image.Image:
    sc  = SCHEMES["numbers"]
    img = gradient_bg(sc["bg_top"], sc["bg_bot"])
    img = add_dots(img, color=(255,255,255), alpha=20)

    draw = ImageDraw.Draw(img)
    add_logo_badge(draw)

    # Big number
    font_num = load_font(400)
    n_str    = str(number)
    nx       = center_x(draw, n_str, font_num) - 150
    outlined_text(draw, (nx, 50), n_str, font_num,
                  fill=sc["accent"], outline=(20,100,40), stroke=10)

    # N animal sprites on the right
    d2 = SPRITES / theme
    animals = sorted(d2.glob("*.png"))
    n = min(int(number), 5)
    size = 170 if n <= 3 else 130
    cols = min(n, 3)
    rows = math.ceil(n / cols)
    start_x = W//2 + 40
    start_y = (H - rows*size) // 2
    for i in range(n):
        sp = load_sprite(animals[i % len(animals)], size)
        col, row = i % cols, i // cols
        px = start_x + col * (size + 10)
        py = start_y + row * (size + 10)
        img.paste(sp, (px, py), sp)

    return img


def thumb_colors(color_key: str) -> Image.Image:
    bg = COLOR_BG.get(color_key, (100, 100, 200))
    bg_top = tuple(min(255, int(c * 1.25)) for c in bg)
    bg_bot = tuple(max(0, int(c * 0.75)) for c in bg)
    img  = gradient_bg(bg_top, bg_bot)
    img  = add_dots(img, color=(255, 255, 255), alpha=30)

    draw = ImageDraw.Draw(img)
    add_logo_badge(draw)

    color_name = color_key.capitalize()
    font_big   = load_font(260)
    font_sub   = load_font(72)

    # Color name — pushed up to leave room for circle + badge
    cx = center_x(draw, color_name, font_big)
    outlined_text(draw, (cx, 70), color_name, font_big,
                  fill=(255, 255, 255), outline=(0, 0, 0), stroke=10)

    # Color swatch: white disk + lighter-colored inner fill (clearly visible)
    lighter = tuple(min(255, int(c * 1.6)) for c in bg)
    sw  = 120   # radius
    # Center circle in the space between title (ends ~y=330) and bottom badge area (starts ~y=640)
    cx2 = W // 2
    cy2 = 490
    ov  = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od  = ImageDraw.Draw(ov)
    # Shadow
    od.ellipse([cx2 - sw + 8, cy2 - sw + 8, cx2 + sw + 8, cy2 + sw + 8],
               fill=(0, 0, 0, 80))
    # White ring
    od.ellipse([cx2 - sw, cy2 - sw, cx2 + sw, cy2 + sw],
               fill=(255, 255, 255, 255))
    # Lighter color fill inside
    od.ellipse([cx2 - sw + 18, cy2 - sw + 18, cx2 + sw - 18, cy2 + sw - 18],
               fill=lighter + (255,))
    img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")

    return img


def thumb_shape(shape_name: str) -> Image.Image:
    sc  = SCHEMES["short_shape"]
    img = gradient_bg(sc["bg_top"], sc["bg_bot"])
    img = add_dots(img, color=(255,255,255), alpha=20)

    draw = ImageDraw.Draw(img)
    add_logo_badge(draw)

    # Shape sprite — large and centered
    sp_path = SPRITES / "shapes" / f"{shape_name}.png"
    if sp_path.exists():
        sp = load_sprite(sp_path, 500)
        img.paste(sp, ((W - sp.width)//2, (H - sp.height)//2 - 50), sp)

    font_name = load_font(110)
    nx = center_x(draw, shape_name.capitalize(), font_name)
    outlined_text(draw, (nx, H-130), shape_name.capitalize(), font_name,
                  fill=(255,255,255), outline=(60,20,160), stroke=6)

    return img


def thumb_generic(video_type: str, theme: str, title: str, variant: int = 0) -> Image.Image:
    """Fallback: gradient + animal + title."""
    sc  = SCHEMES.get(video_type, SCHEMES["dance"])
    img = gradient_bg(sc["bg_top"], sc["bg_bot"])
    img = add_dots(img, seed=variant)

    d2 = SPRITES / theme
    if not d2.exists():
        d2 = SPRITES / "animals"
    animals = sorted(d2.glob("*.png"))
    if animals:
        sp = load_sprite(animals[variant % len(animals)], 450)
        img.paste(sp, (W - sp.width - 60, (H - sp.height)//2), sp)

    draw = ImageDraw.Draw(img)
    add_logo_badge(draw)

    font_t = load_font(90)
    title_clean = title.replace(" #shorts","")
    words  = title_clean.split()
    lines, cur = [], []
    for w in words:
        test = " ".join(cur + [w])
        if text_w(draw, test, font_t) > W//2 - 40:
            lines.append(" ".join(cur))
            cur = [w]
        else:
            cur.append(w)
    if cur:
        lines.append(" ".join(cur))

    y0 = (H - len(lines)*100)//2
    for line in lines:
        outlined_text(draw, (40, y0), line, font_t,
                      fill=sc["text"], outline=(0,0,0), stroke=5)
        y0 += 100

    return img


# ── Public API ────────────────────────────────────────────────────────────────

def generate_thumbnail(
    video_type: str,
    theme: str,
    title: str,
    out_path: Path,
    variant: int = 0,
    # Optional overrides for educational content
    letter: str = "",
    word: str = "",
    number: str = "",
    color: str = "",
    shape: str = "",
    is_shorts: bool = False,
) -> Path:
    img = None

    if video_type in ("dance", "short_dance"):
        img = thumb_dance(theme, title, variant)
    elif video_type in ("abc", "short_letter") and letter:
        img = thumb_abc(theme, letter, word or letter)
    elif video_type in ("numbers", "short_number", "short_counting") and number:
        img = thumb_numbers(theme, number)
    elif video_type in ("colors", "short_color") and color:
        img = thumb_colors(color)
    elif video_type == "short_shape" and shape:
        img = thumb_shape(shape)
    else:
        img = thumb_generic(video_type, theme, title, variant)

    if is_shorts:
        img = add_shorts_badge(img)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(out_path), "PNG", optimize=True)
    return out_path


def generate_all_previews():
    """Generate one thumbnail per type for preview."""
    cases = [
        dict(video_type="dance",        theme="animals", title="Animals Dance Party 🐻 Happy Music for Kids"),
        dict(video_type="abc",           theme="animals", title="ABC Song A to Z 🔤", letter="A", word="Apple"),
        dict(video_type="numbers",       theme="animals", title="Numbers 1 to 10", number="3"),
        dict(video_type="colors",        theme="animals", title="Learn Colors", color="red"),
        dict(video_type="short_letter",  theme="animals", title="Learn ABC #shorts", letter="B", word="Banana", is_shorts=True),
        dict(video_type="short_number",  theme="animals", title="Count 1-5 #shorts", number="5", is_shorts=True),
        dict(video_type="short_color",   theme="animals", title="Colors #shorts", color="blue", is_shorts=True),
        dict(video_type="short_shape",   theme="shapes",  title="Shapes #shorts", shape="star", is_shorts=True),
        dict(video_type="short_dance",   theme="animals", title="Dance! #shorts", is_shorts=True),
    ]
    paths = []
    for c in cases:
        vt = c["video_type"]
        out = OUT_DIR / "previews" / f"{vt}.png"
        p = generate_thumbnail(out_path=out, **c)
        print(f"  {vt:<16} → {p.name}")
        paths.append(p)
    return paths


def main():
    parser = argparse.ArgumentParser(description="Generate video thumbnail")
    parser.add_argument("--type",   default="dance")
    parser.add_argument("--theme",  default="animals")
    parser.add_argument("--title",  default="Happy Bear Kids")
    parser.add_argument("--letter", default="")
    parser.add_argument("--word",   default="")
    parser.add_argument("--number", default="")
    parser.add_argument("--color",  default="")
    parser.add_argument("--shape",  default="")
    parser.add_argument("--variant",type=int, default=0)
    parser.add_argument("--shorts", action="store_true")
    parser.add_argument("--output", default=None)
    parser.add_argument("--all-previews", action="store_true")
    args = parser.parse_args()

    if args.all_previews:
        print(f"\nGenerating all preview thumbnails → {OUT_DIR}/previews/\n")
        generate_all_previews()
        print("\nDone.")
        return

    out = Path(args.output) if args.output else \
          OUT_DIR / f"thumb_{args.type}_{args.theme}.png"

    p = generate_thumbnail(
        video_type=args.type,
        theme=args.theme,
        title=args.title,
        out_path=out,
        variant=args.variant,
        letter=args.letter,
        word=args.word,
        number=args.number,
        color=args.color,
        shape=args.shape,
        is_shorts=args.shorts,
    )
    print(f"Saved: {p}")


if __name__ == "__main__":
    main()
