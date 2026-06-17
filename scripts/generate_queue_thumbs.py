#!/usr/bin/env python3
"""
Generate unique thumb_{stem}.png for every MP4 in output/queue/, queue_ar/, and queue_id/.

Each video type and character gets distinct colors, layout, and visual style.
Layouts: hero_center, hero_left, crowd, burst — chosen by video type.

Usage:
  python3 scripts/generate_queue_thumbs.py              # EN + AR queues (both)
  python3 scripts/generate_queue_thumbs.py --queue all  # all 3 queues
  python3 scripts/generate_queue_thumbs.py --queue en
  python3 scripts/generate_queue_thumbs.py --queue ar
  python3 scripts/generate_queue_thumbs.py --queue id
  python3 scripts/generate_queue_thumbs.py --force      # regenerate all
"""
import argparse
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import yaml
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SPRITES_NEW = ROOT / "assets" / "sprites_new"
SPRITES_OLD = ROOT / "assets" / "sprites"

W, H = 1280, 720   # YouTube 16:9

# ── Per-character color palettes ──────────────────────────────────────────────
CHAR_PALETTE = {
    # Animals
    "bear":       {"bg1": (255,165, 60), "bg2": (200, 90, 10), "txt": (255,240,60)},
    "tiger":      {"bg1": (255,140, 20), "bg2": (180, 70, 10), "txt": (255,240,80)},
    "frog":       {"bg1": ( 80,210, 80), "bg2": ( 30,150, 40), "txt": (240,255,80)},
    "penguin":    {"bg1": ( 60,160,240), "bg2": ( 20, 90,200), "txt": (255,240,60)},
    "lion":       {"bg1": (245,190, 50), "bg2": (190,130, 20), "txt": (255,255,255)},
    "panda":      {"bg1": (190,210,190), "bg2": ( 80,130, 80), "txt": (255,255,255)},
    "koala":      {"bg1": (170,150,200), "bg2": ( 90, 70,150), "txt": (255,240,80)},
    "fox":        {"bg1": (245,120, 50), "bg2": (180, 60, 20), "txt": (255,240,80)},
    "rabbit":     {"bg1": (255,175,210), "bg2": (200, 90,150), "txt": (255,255,255)},
    "cow":        {"bg1": (200,225,255), "bg2": ( 90,140,210), "txt": (255,240,60)},
    "duck":       {"bg1": (255,225, 50), "bg2": (200,160, 10), "txt": (255,255,255)},
    "pig":        {"bg1": (255,160,180), "bg2": (220, 90,130), "txt": (255,255,255)},
    "elephant":   {"bg1": (175,175,225), "bg2": ( 90, 90,175), "txt": (255,240,80)},
    "monkey":     {"bg1": (205,155, 80), "bg2": (140, 90, 30), "txt": (255,240,60)},
    "dog":        {"bg1": (225,180,120), "bg2": (160,100, 50), "txt": (255,240,60)},
    "cat":        {"bg1": (255,200,160), "bg2": (200,120, 70), "txt": (255,240,60)},
    "owl":        {"bg1": (155,120,210), "bg2": ( 90, 60,170), "txt": (255,240,80)},
    "unicorn":    {"bg1": (255,170,240), "bg2": (200, 80,210), "txt": (255,255,100)},
    "dino":       {"bg1": ( 80,220,120), "bg2": ( 30,160, 60), "txt": (255,240,60)},
    "parrot":     {"bg1": ( 60,205,205), "bg2": ( 20,140,160), "txt": (255,240,60)},
    # Fruits
    "apple":      {"bg1": (255, 55, 55), "bg2": (180, 15, 15), "txt": (255,240,60)},
    "banana":     {"bg1": (255,225, 40), "bg2": (200,155, 10), "txt": (255,255,255)},
    "strawberry": {"bg1": (255, 55,100), "bg2": (200, 15, 55), "txt": (255,240,80)},
    "watermelon": {"bg1": ( 60,205, 80), "bg2": ( 20,145, 40), "txt": (255,240,60)},
    "orange":     {"bg1": (255,140, 20), "bg2": (200, 85, 10), "txt": (255,255,255)},
    "grapes":     {"bg1": (155, 55,225), "bg2": ( 95, 15,175), "txt": (255,240,80)},
    "pineapple":  {"bg1": (255,205, 20), "bg2": (190,140, 10), "txt": (255,255,255)},
    "cherry":     {"bg1": (225, 15, 55), "bg2": (160,  5, 35), "txt": (255,240,80)},
    "lemon":      {"bg1": (255,235, 40), "bg2": (200,175, 10), "txt": (255,255,255)},
    "peach":      {"bg1": (255,185,120), "bg2": (200,120, 60), "txt": (255,255,255)},
    "pear":       {"bg1": (175,225, 55), "bg2": (110,170, 20), "txt": (255,255,255)},
    "melon":      {"bg1": (175,225,100), "bg2": (110,170, 40), "txt": (255,255,255)},
    # Vegetables
    "carrot":     {"bg1": (255,140, 40), "bg2": (200, 85, 10), "txt": (255,240,60)},
    "broccoli":   {"bg1": ( 55,185, 55), "bg2": ( 15,125, 15), "txt": (255,240,60)},
    "corn":       {"bg1": (255,215, 40), "bg2": (200,155, 10), "txt": (255,255,255)},
    "tomato":     {"bg1": (225, 50, 50), "bg2": (160, 15, 15), "txt": (255,240,60)},
    "cucumber":   {"bg1": ( 75,205, 80), "bg2": ( 30,145, 40), "txt": (255,240,60)},
    "eggplant":   {"bg1": (130, 35,185), "bg2": ( 75,  5,135), "txt": (255,240,80)},
    "onion":      {"bg1": (220,155,205), "bg2": (155, 85,150), "txt": (255,255,255)},
    "pepper":     {"bg1": (225, 55, 40), "bg2": (165, 15, 10), "txt": (255,240,60)},
    "potato":     {"bg1": (205,185,120), "bg2": (145,120, 60), "txt": (255,255,255)},
    "pumpkin":    {"bg1": (245,130, 30), "bg2": (185, 75, 10), "txt": (255,240,60)},
}

THEME_PALETTE = {
    "animals":    {"bg1": (255,165, 50), "bg2": (200, 90, 10), "txt": (255,240,60)},
    "fruits":     {"bg1": (255, 80,120), "bg2": (200, 20, 80), "txt": (255,240,80)},
    "vegetables": {"bg1": ( 60,200, 70), "bg2": ( 20,140, 35), "txt": (255,240,60)},
    "shapes":     {"bg1": (100,140,255), "bg2": ( 40, 70,220), "txt": (255,240,80)},
    "counting":   {"bg1": ( 80,215,215), "bg2": ( 20,145,165), "txt": (255,240,60)},
    "colors":     {"bg1": (255,100,200), "bg2": (180, 30,160), "txt": (255,240,80)},
    "default":    {"bg1": ( 55,175,255), "bg2": ( 15, 95,225), "txt": (255,240,60)},
}

COLOR_BG = {
    "red":    (220, 45, 45),  "orange": (230,120, 30), "yellow": (220,200, 30),
    "green":  ( 50,170, 70),  "blue":   ( 50,120,220), "purple": (130, 65,205),
    "pink":   (225, 75,165),  "brown":  (130, 80, 40), "cool":   ( 80,180,220),
    "neon":   (180, 60,220),  "pastel": (200,180,255), "rainbow":(255,100,100),
    "sunset": (255,140, 50),  "warm":   (220,120, 60), "ocean":  ( 40,140,200),
    "candy":  (255,120,180),
}

THEME_FOR_CHARACTER = {}

def _build_character_map():
    for a in ["bear","tiger","frog","penguin","lion","panda","koala","fox","rabbit",
              "cow","duck","pig","elephant","monkey","dog","cat","owl","unicorn","dino","parrot"]:
        THEME_FOR_CHARACTER[a] = "animals"
    for f in ["apple","banana","strawberry","watermelon","orange","grapes","pineapple",
              "cherry","lemon","peach","pear","melon"]:
        THEME_FOR_CHARACTER[f] = "fruits"
    for v in ["carrot","broccoli","corn","tomato","cucumber","eggplant","onion",
              "pepper","potato","pumpkin","mushroom"]:
        THEME_FOR_CHARACTER[v] = "vegetables"

_build_character_map()


def clean_title_for_display(title: str, is_ar: bool = False) -> str:
    """Strip emojis, channel suffix, and shorten long pipe-separated titles."""
    t = re.sub(r'#\S+', '', title)
    # Remove channel name suffix wherever it appears
    for suffix in ["| هابي بير كيدز", "| Happy Bear Kids", "هابي بير كيدز", "Happy Bear Kids"]:
        t = t.replace(suffix, "")
    # Strip characters outside Basic Latin, Latin Extended, Arabic — catches all emoji
    t = re.sub(r'[^\x00-\u024F\u0600-\u06FF\s\d|\-!?.,:()\ \[\]]+', ' ', t)
    # Clean leading/trailing pipes and collapse whitespace
    t = re.sub(r'^\s*\|\s*', '', t)
    t = re.sub(r'\s*\|\s*$', '', t)
    t = re.sub(r'\s{2,}', ' ', t).strip()
    # Shorten titles with 3+ pipe sections — keep first 2 meaningful parts
    parts = [p.strip() for p in t.split('|') if p.strip()]
    if len(parts) >= 3:
        t = ' | '.join(parts[:2])
    return t


def load_font(size: int):
    for p in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    ]:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def load_arabic_font(size: int):
    for p in [
        str(ROOT / "remotion" / "public" / "fonts" / "NotoSansArabic-Bold.ttf"),
        "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf",
    ]:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return load_font(size)


def text_w(draw, text, font):
    try:
        return draw.textbbox((0, 0), text, font=font)[2]
    except Exception:
        return len(text) * 14


def outlined_text(draw, pos, text, font, fill, outline=(0, 0, 0), stroke=4):
    x, y = pos
    for dx in range(-stroke, stroke + 1):
        for dy in range(-stroke, stroke + 1):
            if dx or dy:
                draw.text((x + dx, y + dy), text, font=font, fill=outline)
    draw.text((x, y), text, font=font, fill=fill)


def gradient_bg(c1, c2) -> Image.Image:
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        r = int(c1[0] * (1 - t) + c2[0] * t)
        g = int(c1[1] * (1 - t) + c2[1] * t)
        b = int(c1[2] * (1 - t) + c2[2] * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))
    return img


def draw_radial_glow(img: Image.Image, cx: int, cy: int, radius: int,
                     color=(255, 255, 255), alpha_max=80) -> Image.Image:
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for r in range(radius, 0, -10):
        a = int(alpha_max * (1 - r / radius) ** 1.5)
        d = ImageDraw.Draw(overlay)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*color, a))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def draw_starburst(img: Image.Image, cx: int, cy: int, rays=16,
                   r_inner=140, r_outer=280, color=(255, 240, 60), alpha=60) -> Image.Image:
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    pts = []
    for i in range(rays * 2):
        angle = math.pi * i / rays
        r = r_outer if i % 2 == 0 else r_inner
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    d.polygon(pts, fill=(*color, alpha))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def draw_sparkles(img: Image.Image, seed=0, count=12, color=(255, 255, 255)) -> Image.Image:
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    for i in range(count):
        # Deterministic pseudo-random positions
        cx = (seed * 173 + i * 317) % W
        cy = (seed * 97  + i * 211) % H
        sz = 8 + (seed * 7 + i * 13) % 16
        alpha = 120 + (seed * 11 + i * 19) % 100
        # 4-point star
        pts = [
            (cx, cy - sz), (cx + sz//4, cy - sz//4),
            (cx + sz, cy), (cx + sz//4, cy + sz//4),
            (cx, cy + sz), (cx - sz//4, cy + sz//4),
            (cx - sz, cy), (cx - sz//4, cy - sz//4),
        ]
        d.polygon(pts, fill=(*color, alpha))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def draw_bubbles(img: Image.Image, seed=0, count=14) -> Image.Image:
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    colors = [(255,100,100),(100,255,150),(100,150,255),(255,230,80),(255,120,200),(100,230,230)]
    for i in range(count):
        r  = 15 + (seed * 7  + i * 41) % 30
        cx = (seed * 113 + i * 197) % W
        cy = (seed * 67  + i * 151) % H
        c  = colors[(seed + i) % len(colors)]
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*c, 80))
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(*c, 160), width=2)
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def find_sprite(name: str, theme: str) -> Path | None:
    search = [
        SPRITES_NEW / theme / f"{name}.png",
        SPRITES_NEW / f"{theme}_cartoon" / f"{name}.png",
        SPRITES_NEW / f"{theme}_3d" / f"{name}.png",
        SPRITES_OLD / theme / f"{name}.png",
        SPRITES_NEW / "animals" / f"{name}.png",
    ]
    for p in search:
        if p.exists():
            return p
    return None


def load_sprite(path: Path, size: int) -> Image.Image:
    img = Image.open(path).convert("RGBA")
    img.thumbnail((size, size), Image.LANCZOS)
    return img


def theme_sprites(theme: str, exclude: str = "", count: int = 5) -> list[Path]:
    dirs = [
        SPRITES_NEW / theme,
        SPRITES_NEW / f"{theme}_cartoon",
    ]
    seen, result = set(), []
    for d in dirs:
        if d.exists():
            for p in sorted(d.glob("*.png")):
                if p.stem not in seen and p.stem != exclude and "_b" not in p.stem:
                    seen.add(p.stem)
                    result.append(p)
                    if len(result) >= count:
                        return result
    return result


def draw_title_band(img: Image.Image, title: str, is_ar=False, alpha=200) -> Image.Image:
    """Bottom dark band with title text."""
    clean = title  # already cleaned by clean_title_for_display
    draw = ImageDraw.Draw(img)
    font = load_arabic_font(60) if is_ar else load_font(64)
    words = clean.split()
    lines, cur = [], []
    for w in words:
        test = " ".join(cur + [w])
        if text_w(draw, test, font) > W - 100:
            if cur:
                lines.append(" ".join(cur))
            cur = [w]
        else:
            cur.append(w)
    if cur:
        lines.append(" ".join(cur))
    lines = lines[:3]
    line_h = 78
    band_h = max(110, len(lines) * line_h + 28)
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    d.rectangle([0, H - band_h, W, H], fill=(0, 0, 0, alpha))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)
    y0 = H - band_h + (band_h - len(lines) * line_h) // 2
    for line in lines:
        tw = text_w(draw, line, font)
        outlined_text(draw, ((W - tw) // 2, y0), line, font,
                      fill=(255, 255, 255), outline=(0, 0, 0), stroke=4)
        y0 += line_h
    return img


def draw_title_top(img: Image.Image, title: str, pal: dict, is_ar=False) -> Image.Image:
    """Colorful top badge with title."""
    clean = title  # already cleaned by clean_title_for_display
    draw = ImageDraw.Draw(img)
    font = load_arabic_font(56) if is_ar else load_font(60)
    lines, cur = [], []
    for w in clean.split():
        test = " ".join(cur + [w])
        if text_w(draw, test, font) > W - 80:
            if cur:
                lines.append(" ".join(cur))
            cur = [w]
        else:
            cur.append(w)
    if cur:
        lines.append(" ".join(cur))
    lines = lines[:2]
    line_h = 72
    band_h = len(lines) * line_h + 24
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    d.rounded_rectangle([20, 16, W - 20, band_h + 16], radius=22,
                         fill=(*pal["bg2"], 220))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)
    y0 = 28
    for line in lines:
        tw = text_w(draw, line, font)
        outlined_text(draw, ((W - tw) // 2, y0), line, font,
                      fill=pal["txt"], outline=(0, 0, 0), stroke=3)
        y0 += line_h
    return img


def add_badge(img: Image.Image, text: str, corner="tr", color=(255, 50, 50)) -> Image.Image:
    draw = ImageDraw.Draw(img)
    font = load_font(38)
    tw = text_w(draw, text, font)
    pad = 16
    bw, bh = tw + pad * 2, 56
    if corner == "tr":
        bx, by = W - bw - 16, 16
    elif corner == "tl":
        bx, by = 16, 16
    else:
        bx, by = W - bw - 16, H - bh - 16
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=16, fill=(*color, 230))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)
    draw.text((bx + pad, by + 10), text, font=font, fill=(255, 255, 255))
    return img


# ── Layout: hero_center ───────────────────────────────────────────────────────

def layout_hero_center(sprite_path: Path, title: str, pal: dict,
                        is_ar=False, seed=0) -> Image.Image:
    """One big character centered, starburst behind, title at bottom."""
    img = gradient_bg(pal["bg1"], pal["bg2"])
    img = draw_starburst(img, W // 2, H // 2 - 40, color=pal["txt"], alpha=55, r_outer=320)
    img = draw_radial_glow(img, W // 2, H // 2 - 40, 300, color=(255, 255, 255), alpha_max=50)
    img = draw_sparkles(img, seed=seed, count=14, color=pal["txt"])
    img = draw_bubbles(img, seed=seed + 3, count=10)
    sp = load_sprite(sprite_path, 520)
    img.paste(sp, (W // 2 - sp.width // 2, H // 2 - sp.height // 2 - 50), sp)
    img = draw_title_band(img, title, is_ar=is_ar)
    return img


# ── Layout: hero_left ─────────────────────────────────────────────────────────

def layout_hero_left(sprite_path: Path, title: str, pal: dict,
                      is_ar=False, seed=0) -> Image.Image:
    """Character on left, bold title text on right half."""
    img = gradient_bg(pal["bg1"], pal["bg2"])
    img = draw_sparkles(img, seed=seed, count=10, color=pal["txt"])
    img = draw_bubbles(img, seed=seed + 5, count=8)
    # Character on left
    sp = load_sprite(sprite_path, 500)
    x_char = 60
    img.paste(sp, (x_char, H // 2 - sp.height // 2 - 30), sp)
    # Title text on right
    clean = title  # already cleaned by clean_title_for_display
    draw = ImageDraw.Draw(img)
    font = load_arabic_font(62) if is_ar else load_font(68)
    right_x = 560
    right_w = W - right_x - 40
    words, lines, cur = clean.split(), [], []
    for w in words:
        test = " ".join(cur + [w])
        if text_w(draw, test, font) > right_w:
            if cur:
                lines.append(" ".join(cur))
            cur = [w]
        else:
            cur.append(w)
    if cur:
        lines.append(" ".join(cur))
    lines = lines[:4]
    total_h = len(lines) * 82
    y0 = H // 2 - total_h // 2 - 20
    for line in lines:
        outlined_text(draw, (right_x, y0), line, font,
                      fill=(255, 255, 255), outline=(0, 0, 0), stroke=5)
        y0 += 82
    return img


# ── Layout: crowd ─────────────────────────────────────────────────────────────

def layout_crowd(sprites: list[Path], title: str, pal: dict,
                  is_ar=False, seed=0) -> Image.Image:
    """Multiple characters scattered, title at top."""
    img = gradient_bg(pal["bg1"], pal["bg2"])
    img = draw_sparkles(img, seed=seed, count=16, color=pal["txt"])
    img = draw_bubbles(img, seed=seed + 7, count=14)

    # Up to 5 sprites with varied positions and sizes
    configs_5 = [
        (640, 400, 480), (200, 380, 360), (1080, 370, 340),
        (420, 560, 280), (870, 570, 270),
    ]
    configs_4 = [
        (280, 390, 400), (740, 360, 420), (130, 580, 280), (1000, 560, 280),
    ]
    configs_3 = [
        (200, 400, 380), (640, 340, 420), (1090, 400, 380),
    ]

    n = min(len(sprites), 5)
    if n >= 5:
        cfgs = configs_5
    elif n == 4:
        cfgs = configs_4
    else:
        cfgs = configs_3

    for sp_path, (cx, cy, sz) in zip(sprites[:n], cfgs[:n]):
        sp = load_sprite(sp_path, sz)
        img.paste(sp, (cx - sp.width // 2, cy - sp.height // 2), sp)

    img = draw_title_top(img, title, pal, is_ar=is_ar)
    return img


# ── Layout: burst ─────────────────────────────────────────────────────────────

def layout_burst(sprite_path: Path, title: str, pal: dict,
                  is_ar=False, seed=0) -> Image.Image:
    """Character with multi-layer starburst, big text above."""
    img = gradient_bg(pal["bg2"], pal["bg1"])  # reversed gradient
    img = draw_starburst(img, W // 2, H // 2 + 30, rays=24,
                          r_inner=90, r_outer=380, color=pal["txt"], alpha=70)
    img = draw_starburst(img, W // 2, H // 2 + 30, rays=16,
                          r_inner=120, r_outer=250, color=(255, 255, 255), alpha=40)
    img = draw_sparkles(img, seed=seed, count=18, color=(255, 255, 255))
    sp = load_sprite(sprite_path, 480)
    img.paste(sp, (W // 2 - sp.width // 2, H // 2 - sp.height // 2 + 20), sp)
    img = draw_title_top(img, title, pal, is_ar=is_ar)
    return img


# ── Layout: duo ───────────────────────────────────────────────────────────────

def layout_duo(sp1: Path, sp2: Path, title: str, pal: dict,
               is_ar=False, seed=0) -> Image.Image:
    """Two characters side by side."""
    img = gradient_bg(pal["bg1"], pal["bg2"])
    img = draw_radial_glow(img, W // 2, H // 2, 350, color=(255, 255, 255), alpha_max=40)
    img = draw_sparkles(img, seed=seed, count=14, color=pal["txt"])
    img = draw_bubbles(img, seed=seed + 2, count=10)
    s1 = load_sprite(sp1, 430)
    s2 = load_sprite(sp2, 400)
    img.paste(s1, (W // 4 - s1.width // 2, H // 2 - s1.height // 2 - 40), s1)
    img.paste(s2, (3 * W // 4 - s2.width // 2, H // 2 - s2.height // 2 - 20), s2)
    img = draw_title_band(img, title, is_ar=is_ar)
    return img


# ── Layout picker ─────────────────────────────────────────────────────────────

def pick_layout(seed: int) -> str:
    return ["hero_center", "hero_left", "burst", "hero_center", "burst"][seed % 5]


# ── Main thumbnail builder ────────────────────────────────────────────────────

def make_thumbnail(stem: str, meta: dict, seed: int = 0) -> Image.Image:
    is_ar    = meta.get("language", "en") == "ar"
    title    = clean_title_for_display(meta.get("title", stem), is_ar=is_ar)
    vtype    = meta.get("video_type", "")
    theme    = meta.get("theme", "animals")
    is_short = meta.get("is_short", False)

    # Normalise stem
    name = re.sub(r'_\d{8}.*$', '', stem)
    name = re.sub(r'^ar_', '', name)

    # ── Extract character ─────────────────────────────────────────────────────
    character = ""
    color     = ""
    shape     = ""

    if vtype == "short_dance" or re.match(r'short_dance_\w+', name):
        m = re.match(r'(?:ar_)?short_dance_(\w+)', name)
        if m:
            character = m.group(1)
            theme = THEME_FOR_CHARACTER.get(character, theme)

    elif "colorlearn" in name:
        vtype = "short_colorlearn"
        m = re.search(r'colorlearn_(\w+)', name)
        if m:
            color = m.group(1)

    elif re.match(r'(?:ar_)?short_color_\w+', name):
        vtype = "short_color"
        m = re.search(r'short_color_(\w+?)(?:_\w+)?$', name)
        if m:
            color = m.group(1)

    elif "float" in name:
        vtype = "short_shape_float"
        m = re.search(r'float_(\w+)', name)
        if m:
            shape = m.group(1).split("_")[0]

    elif "sdance" in name:
        vtype = "short_shape_dance"
        m = re.search(r'sdance_(\w+)', name)
        if m:
            shape = m.group(1)

    elif "shapes" in name:
        vtype = "short_shape_dance"
        m = re.search(r'shapes?_(\w+?)(?:_\d|$)', name)
        if m:
            color = m.group(1)

    elif "vocab" in name:
        vtype = "short_vocab"
        m = re.search(r'vocab_([a-z])', name)
        if m:
            character = m.group(1).upper()

    elif "counting" in name:
        vtype = "counting"
        m = re.search(r'counting_(\w+?)(?:_\d|$)', name)
        if m:
            color = m.group(1)

    elif name.startswith("dance_") or "ar_dance_" in stem:
        vtype = "dance"
        for t in ("animals", "fruits", "vegetables", "shapes"):
            if t in name:
                theme = t
                break

    elif name.startswith("colors_"):
        vtype = "colors"

    # ── Palette ───────────────────────────────────────────────────────────────
    if character and character in CHAR_PALETTE:
        pal = CHAR_PALETTE[character]
    elif color and color in COLOR_BG:
        c = COLOR_BG[color]
        pal = {"bg1": c, "bg2": tuple(max(0, x - 60) for x in c), "txt": (255, 240, 60)}
    elif theme in THEME_PALETTE:
        pal = THEME_PALETTE[theme]
    else:
        pal = THEME_PALETTE["default"]

    # ── Build image ───────────────────────────────────────────────────────────
    img = None

    # Long dance (30 min): crowd layout with 4-5 characters from theme
    if vtype == "dance":
        sprites = theme_sprites(theme, count=5)
        if sprites:
            img = layout_crowd(sprites, title, pal, is_ar=is_ar, seed=seed)
        else:
            img = gradient_bg(pal["bg1"], pal["bg2"])
            img = draw_title_band(img, title, is_ar=is_ar)
        img = add_badge(img, "30 MIN", corner="tr", color=(220, 40, 40))

    # Single character dance short: alternating hero layouts
    elif character and character in THEME_FOR_CHARACTER:
        sp = find_sprite(character, theme)
        if sp:
            layout = pick_layout(seed)
            if layout == "hero_left":
                img = layout_hero_left(sp, title, pal, is_ar=is_ar, seed=seed)
            elif layout == "burst":
                img = layout_burst(sp, title, pal, is_ar=is_ar, seed=seed)
            else:
                img = layout_hero_center(sp, title, pal, is_ar=is_ar, seed=seed)

    # Color learn: big color circle + character from theme
    elif vtype in ("short_colorlearn", "short_color") and color:
        bg = COLOR_BG.get(color, (100, 150, 200))
        img = gradient_bg(bg, tuple(max(0, x - 60) for x in bg))
        img = draw_sparkles(img, seed=seed, count=12, color=(255, 255, 255))
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(overlay)
        r = 200
        cx, cy = W // 2 + 200, H // 2 - 30
        d.ellipse([cx - r - 14, cy - r - 14, cx + r + 14, cy + r + 14], fill=(255, 255, 255, 200))
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*bg, 255))
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(img)
        font = load_arabic_font(120) if is_ar else load_font(130)
        label = color.upper()
        tw = text_w(draw, label, font)
        outlined_text(draw, (cx - tw // 2, cy - 65), label, font,
                      fill=(255, 255, 255), outline=(0, 0, 0), stroke=6)
        sprites = theme_sprites(theme, count=2)
        if sprites:
            sp = load_sprite(sprites[seed % len(sprites)], 380)
            img.paste(sp, (80, H // 2 - sp.height // 2 - 20), sp)
        img = draw_title_band(img, title, is_ar=is_ar)

    # Shape float/dance: shape sprite + starburst
    elif vtype in ("short_shape_float", "short_shape_dance") or shape:
        sp_path = SPRITES_OLD / "shapes" / f"{shape}.png" if shape else None
        if sp_path and sp_path.exists():
            img = layout_hero_center(sp_path, title, pal, is_ar=is_ar, seed=seed)
        else:
            img = gradient_bg(pal["bg1"], pal["bg2"])
            img = draw_starburst(img, W // 2, H // 2, color=pal["txt"])
            img = draw_title_band(img, title, is_ar=is_ar)

    # Counting: big number + character
    elif vtype == "counting":
        img = gradient_bg(pal["bg1"], pal["bg2"])
        img = draw_sparkles(img, seed=seed, count=16, color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        font_big = load_font(240)
        digits = "1  2  3"
        tw = text_w(draw, digits, font_big)
        outlined_text(draw, ((W - tw) // 2, H // 2 - 150), digits, font_big,
                      fill=pal["txt"], outline=(0, 0, 0), stroke=8)
        sprites = theme_sprites("animals", count=3)
        positions = [(150, 560), (640, 580), (1130, 560)]
        sizes = [240, 260, 240]
        for sp_p, (px, py), sz in zip(sprites[:3], positions, sizes):
            sp = load_sprite(sp_p, sz)
            img.paste(sp, (px - sp.width // 2, py - sp.height // 2), sp)
        img = draw_title_band(img, title, is_ar=is_ar)

    # Colors all / color theme long
    elif vtype == "colors":
        img = gradient_bg(pal["bg1"], pal["bg2"])
        img = draw_sparkles(img, seed=seed, count=16, color=(255, 255, 255))
        sprites = theme_sprites("animals", count=5)
        if sprites:
            img = layout_crowd(sprites, title, pal, is_ar=is_ar, seed=seed)
        img = draw_title_band(img, title, is_ar=is_ar)

    # Fallback: pick a random sprite from theme
    if img is None:
        sprites = theme_sprites(theme, count=3)
        if sprites:
            sp = sprites[seed % len(sprites)]
            img = layout_hero_center(sp, title, pal, is_ar=is_ar, seed=seed)
        else:
            img = gradient_bg(pal["bg1"], pal["bg2"])
            img = draw_title_band(img, title, is_ar=is_ar)

    # #Shorts badge for short-form content
    if is_short or vtype.startswith("short_"):
        img = add_badge(img, "#Shorts", corner="tr", color=(255, 40, 40))

    return img


# ── Queue processor ───────────────────────────────────────────────────────────

def process_queue(queue_dir: Path, force: bool, label: str):
    mp4s = sorted([p for p in queue_dir.glob("*.mp4") if "test_" not in p.name])
    if not mp4s:
        print(f"  No videos in {queue_dir}")
        return

    ok = skip = err = 0
    for i, mp4 in enumerate(mp4s):
        thumb_path = queue_dir / f"thumb_{mp4.stem}.png"
        if thumb_path.exists() and not force:
            skip += 1
            continue

        meta_path = queue_dir / f"meta_{mp4.stem}.yaml"
        meta = {}
        if meta_path.exists():
            with open(meta_path) as f:
                meta = yaml.safe_load(f) or {}

        try:
            img = make_thumbnail(mp4.stem, meta, seed=i)
            img.save(str(thumb_path), "PNG", optimize=True)
            ok += 1
            if ok % 20 == 0 or ok <= 5:
                print(f"  [{label}] {ok}/{len(mp4s) - skip} — {mp4.name}")
        except Exception as e:
            import traceback
            print(f"  ERROR {mp4.name}: {e}")
            traceback.print_exc()
            err += 1

    print(f"  [{label}] Done: {ok} generated, {skip} skipped, {err} errors")


def process_uploaded(force: bool):
    """Regenerate thumbnails for already-uploaded videos (used by update_youtube_meta.py)."""
    uploaded_dir = ROOT / "uploaded"
    mp4s = sorted([p for p in uploaded_dir.glob("*.mp4") if "test_" not in p.name])
    if not mp4s:
        print("  No MP4s in uploaded/")
        return
    ok = skip = err = 0
    for i, mp4 in enumerate(mp4s):
        thumb_path = uploaded_dir / f"thumb_{mp4.stem}.png"
        if thumb_path.exists() and not force:
            skip += 1
            continue
        meta_path = uploaded_dir / f"meta_{mp4.stem}.yaml"
        meta = {}
        if meta_path.exists():
            with open(meta_path) as f:
                import yaml as _yaml
                meta = _yaml.safe_load(f) or {}
        try:
            img = make_thumbnail(mp4.stem, meta, seed=i)
            img.save(str(thumb_path), "PNG", optimize=True)
            ok += 1
        except Exception as e:
            print(f"  ERROR {mp4.name}: {e}")
            err += 1
    print(f"  [uploaded] Done: {ok} generated, {skip} skipped, {err} errors")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", choices=["en", "ar", "id", "both", "all", "uploaded"],
                        default="both")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.queue in ("en", "both", "all"):
        process_queue(ROOT / "output" / "queue", args.force, "EN")

    if args.queue in ("ar", "both", "all"):
        process_queue(ROOT / "output" / "queue_ar", args.force, "AR")

    if args.queue in ("id", "all"):
        process_queue(ROOT / "output" / "queue_id", args.force, "ID")

    if args.queue == "uploaded":
        process_uploaded(args.force)


if __name__ == "__main__":
    main()
