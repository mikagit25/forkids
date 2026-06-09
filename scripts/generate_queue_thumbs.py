#!/usr/bin/env python3
"""
Generate thumb_{stem}.png for every MP4 in output/queue/ and output/queue_ar/
that doesn't already have one.

Reads meta_*.yaml sidecar to get title and video_type.
Falls back to filename parsing when meta is missing.

Usage:
  python3 scripts/generate_queue_thumbs.py              # both queues
  python3 scripts/generate_queue_thumbs.py --queue en   # English only
  python3 scripts/generate_queue_thumbs.py --queue ar   # Arabic only
  python3 scripts/generate_queue_thumbs.py --force      # regenerate all
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import yaml
from PIL import Image, ImageDraw, ImageFont

# ── Sprite directories ────────────────────────────────────────────────────────
SPRITES_NEW = ROOT / "assets" / "sprites_new"
SPRITES_OLD = ROOT / "assets" / "sprites"

W, H = 1280, 720  # YouTube thumbnail

# ── Color schemes ─────────────────────────────────────────────────────────────
SCHEMES = {
    "dance":             {"top": (255, 200, 40),  "bot": (255, 120, 20),  "accent": (255, 60, 60)},
    "short_dance":       {"top": (255, 200, 40),  "bot": (255, 120, 20),  "accent": (255, 60, 60)},
    "short_colorlearn":  {"top": (255, 100, 180), "bot": (180, 40, 140),  "accent": (255, 240, 80)},
    "short_shape_float": {"top": (160, 100, 255), "bot": (90,  40, 200),  "accent": (255, 220, 60)},
    "short_shape_dance": {"top": (100, 200, 255), "bot": (30, 120, 220),  "accent": (255, 230, 40)},
    "short_vocab":       {"top": (255, 170, 60),  "bot": (200, 100, 20),  "accent": (255, 240, 80)},
    "short_color":       {"top": (250, 100, 180), "bot": (180, 40, 140),  "accent": (255, 240, 80)},
    "short_counting":    {"top": (80,  200, 200), "bot": (20, 130, 160),  "accent": (255, 240, 60)},
    "counting":          {"top": (80,  200, 200), "bot": (20, 130, 160),  "accent": (255, 240, 60)},
    "default":           {"top": (60,  180, 255), "bot": (20, 100, 220),  "accent": (255, 240, 60)},
}

COLOR_BG = {
    "red": (220,50,50), "orange": (230,120,30), "yellow": (220,200,30),
    "green": (50,170,70), "blue": (50,120,220), "purple": (130,70,200),
    "pink": (220,80,160), "brown": (130,80,40),
}

THEME_FOR_CHARACTER = {}  # populated below


def _build_character_map():
    animals = ["bear","tiger","frog","penguin","lion","panda","koala","fox","rabbit",
               "cow","duck","pig","elephant","monkey","dog","cat","owl","unicorn","dino","parrot"]
    fruits  = ["apple","banana","strawberry","watermelon","orange","grapes","pineapple",
               "cherry","lemon","peach","pear","melon"]
    vegs    = ["carrot","broccoli","corn","tomato","cucumber","eggplant","onion",
               "pepper","potato","pumpkin","mushroom"]
    for a in animals: THEME_FOR_CHARACTER[a] = "animals"
    for f in fruits:  THEME_FOR_CHARACTER[f] = "fruits"
    for v in vegs:    THEME_FOR_CHARACTER[v] = "vegetables"

_build_character_map()


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
        "/usr/share/fonts/truetype/noto/NotoKufiArabic-Bold.ttf",
    ]:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return load_font(size)


def gradient_bg(top, bot) -> Image.Image:
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        r = int(top[0] * (1-t) + bot[0] * t)
        g = int(top[1] * (1-t) + bot[1] * t)
        b = int(top[2] * (1-t) + bot[2] * t)
        draw.line([(0,y),(W,y)], fill=(r,g,b))
    return img


def add_dots(img: Image.Image, seed=0, alpha=40) -> Image.Image:
    overlay = Image.new("RGBA", (W, H), (0,0,0,0))
    d = ImageDraw.Draw(overlay)
    import math
    for i in range(18):
        r = 18 + (seed * 13 + i * 37) % 28
        cx = (seed * 97 + i * 173) % W
        cy = (seed * 53 + i * 211) % H
        d.ellipse([cx-r,cy-r,cx+r,cy+r], fill=(255,255,255,alpha))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def text_w(draw, text, font):
    try:
        return draw.textbbox((0,0), text, font=font)[2]
    except:
        return len(text) * 14


def outlined_text(draw, pos, text, font, fill, outline=(0,0,0), stroke=3):
    x, y = pos
    for dx in range(-stroke, stroke+1):
        for dy in range(-stroke, stroke+1):
            if dx or dy:
                draw.text((x+dx, y+dy), text, font=font, fill=outline)
    draw.text((x, y), text, font=font, fill=fill)


def title_band(img: Image.Image, title: str, is_ar=False) -> Image.Image:
    """Draw title text in lower band."""
    draw = ImageDraw.Draw(img)
    font = load_arabic_font(58) if is_ar else load_font(62)
    line_h = 72
    words = title.replace("#shorts", "").replace("#Shorts", "").strip().split()
    lines, cur = [], []
    for w in words:
        test = " ".join(cur + [w])
        if text_w(draw, test, font) > W - 80:
            if cur: lines.append(" ".join(cur))
            cur = [w]
        else:
            cur.append(w)
    if cur: lines.append(" ".join(cur))
    lines = lines[:3]

    band_h = max(120, len(lines) * line_h + 24)
    draw.rectangle([0, H - band_h, W, H], fill=(0, 0, 0, 180))
    y0 = H - band_h + (band_h - len(lines) * line_h) // 2
    for line in lines:
        tw = text_w(draw, line, font)
        x = (W - tw) // 2
        outlined_text(draw, (x, y0), line, font, fill=(255,255,255))
        y0 += line_h
    return img


def find_sprite(name: str, theme: str) -> Path | None:
    """Find best sprite PNG for a character name."""
    # Try new sprites first
    for folder, ext in [
        (SPRITES_NEW / theme, f"{name}.png"),
        (SPRITES_NEW / f"{theme}_cartoon", f"{name}.png"),
        (SPRITES_NEW / f"{theme}_3d", f"{name}.png"),
        (SPRITES_OLD / theme, f"{name}.png"),
    ]:
        p = folder / ext
        if p.exists(): return p
    return None


def load_sprite_img(path: Path, size=300) -> Image.Image:
    img = Image.open(path).convert("RGBA")
    img.thumbnail((size, size), Image.LANCZOS)
    return img


def make_thumb_dance(title: str, theme: str, character: str = "", is_ar=False, seed=0) -> Image.Image:
    sc = SCHEMES["short_dance"]
    img = gradient_bg(sc["top"], sc["bot"])
    img = add_dots(img, seed=seed)

    # Find sprites: prefer the specific character, then fallback variety
    sprites_to_show = []
    if character:
        sp = find_sprite(character, theme)
        if sp: sprites_to_show.append(sp)

    # Fill up to 3 sprites from the theme
    theme_dir = SPRITES_NEW / theme
    if not theme_dir.exists():
        theme_dir = SPRITES_NEW / "animals"
    all_sp = sorted(theme_dir.glob("*.png"))
    used_names = {s.stem for s in sprites_to_show}
    for s in all_sp:
        if s.stem not in used_names and len(sprites_to_show) < 3:
            sprites_to_show.append(s)

    positions = [(180,300),(640,240),(1100,300)]
    sizes     = [320, 360, 320]
    for sp_path, (px,py), sz in zip(sprites_to_show[:3], positions, sizes):
        sp = load_sprite_img(sp_path, sz)
        img.paste(sp, (px - sp.width//2, py - sp.height//2), sp)

    title_band(img, title, is_ar=is_ar)
    return img


def make_thumb_colorlearn(color: str, title: str, is_ar=False) -> Image.Image:
    bg = COLOR_BG.get(color, (100, 150, 200))
    img = Image.new("RGB", (W, H), bg)
    img = add_dots(img, seed=hash(color) % 20)

    # Big color circle in center
    overlay = Image.new("RGBA", (W, H), (0,0,0,0))
    d = ImageDraw.Draw(overlay)
    r = 220
    cx, cy = W//2, H//2 - 60
    # White ring
    d.ellipse([cx-r-12,cy-r-12,cx+r+12,cy+r+12], fill=(255,255,255,230))
    d.ellipse([cx-r,cy-r,cx+r,cy+r], fill=(*bg, 255))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    # Color name as big text in circle
    draw = ImageDraw.Draw(img)
    font = load_arabic_font(120) if is_ar else load_font(130)
    label = color.upper() if not is_ar else title.split("|")[0].strip().split()[-1] if "|" in title else color
    tw = text_w(draw, label, font)
    outlined_text(draw, ((W-tw)//2, cy-65), label, font,
                  fill=(255,255,255), outline=(0,0,0), stroke=5)

    title_band(img, title, is_ar=is_ar)
    return img


def make_thumb_shape(shape: str, title: str, is_ar=False, seed=0) -> Image.Image:
    sc = SCHEMES["short_shape_float"]
    img = gradient_bg(sc["top"], sc["bot"])
    img = add_dots(img, seed=seed)

    # Try loading shape sprite
    sp_path = SPRITES_OLD / "shapes" / f"{shape}.png"
    if sp_path.exists():
        sp = load_sprite_img(sp_path, 400)
        img.paste(sp, (W//2 - sp.width//2, H//2 - sp.height//2 - 60), sp)

    title_band(img, title, is_ar=is_ar)
    return img


def make_thumb_generic(video_type: str, title: str, theme="animals", is_ar=False, seed=0) -> Image.Image:
    sc = SCHEMES.get(video_type, SCHEMES["default"])
    img = gradient_bg(sc["top"], sc["bot"])
    img = add_dots(img, seed=seed)

    # One large sprite
    theme_dir = SPRITES_NEW / theme
    if not theme_dir.exists():
        theme_dir = SPRITES_NEW / "animals"
    all_sp = sorted(theme_dir.glob("*.png"))
    if all_sp:
        sp_path = all_sp[seed % len(all_sp)]
        sp = load_sprite_img(sp_path, 420)
        img.paste(sp, (W//2 - sp.width//2, H//2 - sp.height//2 - 50), sp)

    title_band(img, title, is_ar=is_ar)
    return img


def add_shorts_badge(img: Image.Image) -> Image.Image:
    """Small #Shorts badge in top-right corner."""
    draw = ImageDraw.Draw(img)
    font = load_font(36)
    text = "#Shorts"
    tw = text_w(draw, text, font)
    pad = 14
    bw, bh = tw + pad*2, 52
    bx, by = W - bw - 20, 18
    draw.rounded_rectangle([bx, by, bx+bw, by+bh], radius=16, fill=(255,60,60,220))
    draw.text((bx+pad, by+8), text, font=font, fill=(255,255,255))
    return img


# ── Filename → thumbnail parameters ──────────────────────────────────────────

def parse_video_params(stem: str, meta: dict) -> dict:
    """
    Extract thumbnail generation params from filename stem + meta sidecar.
    Returns dict with keys: vtype, theme, character, color, shape, title, is_ar, is_short
    """
    title    = meta.get("title", stem)
    vtype    = meta.get("video_type", "")
    theme    = meta.get("theme", "animals")
    is_ar    = meta.get("language", "en") == "ar"
    is_short = meta.get("is_short", False)

    # Normalise: strip ar_ prefix, strip date suffix
    name = re.sub(r'_\d{8}.*$', '', stem)   # remove _20260609_remotion etc.
    name = re.sub(r'^ar_', '', name)          # strip ar_ prefix

    character = ""
    color     = ""
    shape     = ""

    # ── Dance shorts ──────────────────────────────────────────────────────────
    if not vtype and re.match(r'short_dance_\w+', name):
        vtype = "short_dance"
    if vtype == "short_dance" or re.match(r'short_dance_\w+', name):
        vtype = "short_dance"
        m = re.match(r'(?:ar_)?short_dance_(\w+)', name)
        if m:
            character = m.group(1)
            theme = THEME_FOR_CHARACTER.get(character, "animals")

    # ── ColorLearn ────────────────────────────────────────────────────────────
    elif "colorlearn" in name:
        vtype = "short_colorlearn"
        m = re.search(r'colorlearn_(\w+)', name)
        if m: color = m.group(1)

    # ── Color shorts (short_color_red_animals etc.) ───────────────────────────
    elif re.match(r'(?:ar_)?short_color_\w+', name):
        vtype = "short_color"
        m = re.search(r'short_color_(\w+?)(?:_\w+)?$', name)
        if m: color = m.group(1)

    # ── Shape float ───────────────────────────────────────────────────────────
    elif "float" in name:
        vtype = "short_shape_float"
        m = re.search(r'float_(\w+?)_(?:tb|lr|diag|float)', name)
        if m: shape = m.group(1)

    # ── Shape dance (sdance) ──────────────────────────────────────────────────
    elif "sdance" in name:
        vtype = "short_shape_dance"
        m = re.search(r'sdance_(\w+)', name)
        if m: shape = m.group(1)

    # ── Shapes (short_shapes_*) ───────────────────────────────────────────────
    elif "shapes" in name:
        vtype = "short_shape_dance"

    # ── Vocab ─────────────────────────────────────────────────────────────────
    elif "vocab" in name:
        vtype = "short_vocab"

    # ── Counting ─────────────────────────────────────────────────────────────
    elif "counting" in name:
        vtype = "short_counting"

    # ── Long dance ────────────────────────────────────────────────────────────
    elif name.startswith("dance_") or name.startswith("ar_dance_"):
        vtype = "dance"
        if "animals" in name: theme = "animals"
        elif "fruits" in name: theme = "fruits"
        elif "vegetables" in name: theme = "vegetables"
        elif "shapes" in name: theme = "shapes"

    return {
        "vtype": vtype or "short_dance",
        "theme": theme,
        "character": character,
        "color": color,
        "shape": shape,
        "title": title,
        "is_ar": is_ar,
        "is_short": is_short,
    }


def make_thumbnail(params: dict, seed=0) -> Image.Image:
    vtype     = params["vtype"]
    theme     = params["theme"]
    character = params["character"]
    color     = params["color"]
    shape     = params["shape"]
    title     = params["title"]
    is_ar     = params["is_ar"]
    is_short  = params["is_short"]

    if vtype in ("short_dance", "dance") or character:
        img = make_thumb_dance(title, theme, character, is_ar=is_ar, seed=seed)
    elif vtype == "short_colorlearn" and color:
        img = make_thumb_colorlearn(color, title, is_ar=is_ar)
    elif color:
        img = make_thumb_colorlearn(color, title, is_ar=is_ar)
    elif shape or vtype in ("short_shape_float", "short_shape_dance"):
        img = make_thumb_shape(shape, title, is_ar=is_ar, seed=seed)
    else:
        img = make_thumb_generic(vtype, title, theme, is_ar=is_ar, seed=seed)

    if is_short:
        img = add_shorts_badge(img)

    return img


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

        # Load meta
        meta_path = queue_dir / f"meta_{mp4.stem}.yaml"
        if meta_path.exists():
            with open(meta_path) as f:
                meta = yaml.safe_load(f) or {}
        else:
            meta = {}

        params = parse_video_params(mp4.stem, meta)

        try:
            img = make_thumbnail(params, seed=i)
            img.save(str(thumb_path), "PNG", optimize=True)
            ok += 1
            if ok % 20 == 0 or ok <= 5:
                print(f"  [{label}] {ok}/{len(mp4s)-skip} — {mp4.name}")
        except Exception as e:
            print(f"  ERROR {mp4.name}: {e}")
            err += 1

    print(f"  [{label}] Done: {ok} generated, {skip} skipped, {err} errors")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", choices=["en", "ar", "both"], default="both")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.queue in ("en", "both"):
        q = ROOT / "output" / "queue"
        print(f"\nProcessing English queue: {q}")
        process_queue(q, args.force, "EN")

    if args.queue in ("ar", "both"):
        q = ROOT / "output" / "queue_ar"
        print(f"\nProcessing Arabic queue: {q}")
        process_queue(q, args.force, "AR")


if __name__ == "__main__":
    main()
