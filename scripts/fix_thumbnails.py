#!/usr/bin/env python3
"""
Fix thumbnails for all uploaded YouTube videos.
Generates unique, visually distinctive thumbnails using 3D cartoon sprites.

Usage:
  python3 scripts/fix_thumbnails.py --dry-run   # generate images only, no upload
  python3 scripts/fix_thumbnails.py             # generate + upload
  python3 scripts/fix_thumbnails.py --id VIDEO_ID  # single video
"""
import argparse
import io
import math
import pickle
import random
import re
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT        = Path(__file__).resolve().parent.parent
SPRITES_NEW = ROOT / "assets" / "sprites_new"
SPRITES_OLD = ROOT / "assets" / "sprites"
THUMB_DIR   = ROOT / "output" / "thumbnails" / "fixed"
CREDS       = ROOT / "credentials" / "token.pickle"

W, H = 1280, 720

# ── Sprite lookup ─────────────────────────────────────────────────────────────

SHAPE_3D = {
    "circle":   SPRITES_NEW / "shapes_3d" / "circle.png",
    "square":   SPRITES_NEW / "shapes_3d" / "square.png",
    "triangle": SPRITES_NEW / "shapes_3d" / "triangle.png",
    "circle_b": SPRITES_NEW / "shapes_3d" / "circle_b.png",
}

ANIMAL_3D = {
    "lion":     SPRITES_NEW / "animals_3d" / "lion.png",
    "elephant": SPRITES_NEW / "animals_3d" / "elephant.png",
    "duck":     SPRITES_NEW / "animals_3d" / "duck.png",
    "cat":      SPRITES_NEW / "animals_3d" / "cat.png",
    "whale":    SPRITES_NEW / "animals_3d" / "whale.png",
    "fish":     SPRITES_NEW / "animals_3d" / "fish.png",
}

ANIMAL_NEW = {
    p.stem: p
    for p in sorted((SPRITES_NEW / "animals").glob("*.png"))
}

VEG_CARTOON = {
    p.stem: p
    for p in sorted((SPRITES_NEW / "vegetables_cartoon").glob("*.png"))
    if not p.stem.endswith("_b")
}

FRUIT_CARTOON = {
    p.stem: p
    for p in sorted((SPRITES_NEW / "fruits_cartoon").glob("*.png"))
    if not p.stem.endswith("_b")
}

# Shape colors / backgrounds
SHAPE_COLORS = {
    "circle":   ((41, 128, 185), (174, 214, 241)),
    "square":   ((39, 174, 96),  (169, 223, 191)),
    "triangle": ((230, 126, 34), (250, 215, 160)),
    "star":     ((243, 156, 18), (252, 243, 207)),
    "diamond":  ((142, 68, 173), (215, 189, 226)),
    "heart":    ((231, 76, 60),  (245, 183, 177)),
    "hexagon":  ((22, 160, 133), (163, 228, 215)),
    "oval":     ((92, 99, 192),  (195, 193, 230)),
}

# Color learn backgrounds
COLOR_SCHEMES = {
    "red":    ((220, 50,  50),  (255, 180, 180)),
    "orange": ((230, 120, 30),  (255, 210, 150)),
    "yellow": ((200, 180, 20),  (255, 245, 150)),
    "green":  (( 50, 170, 70),  (170, 230, 170)),
    "blue":   (( 50, 120, 220), (170, 200, 255)),
    "purple": ((130, 70,  200), (210, 170, 240)),
    "pink":   ((220, 80,  160), (255, 180, 220)),
}

COLOR_FRUITS = {
    "red":    ["apple", "strawberry"],
    "orange": ["orange", "peach"],
    "yellow": ["banana", "pineapple"],
    "green":  ["kiwi", "avocado"],
    "blue":   ["blueberry", "dragonfruit"],
    "purple": ["grape", "plum"],
    "pink":   ["strawberry", "raspberry"],
}

COLOR_VEGS = {
    "red":    ["tomato", "pepper"],
    "orange": ["carrot", "pumpkin"],
    "yellow": ["corn"],
    "green":  ["broccoli", "cucumber"],
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


def load_sprite(path: Path, size: int) -> Image.Image | None:
    if not path or not path.exists():
        return None
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


def add_confetti(img, seed=1):
    rng = random.Random(seed)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    colors = [(255,80,80), (80,200,80), (80,80,255), (255,220,40), (255,120,200), (40,220,220)]
    for _ in range(60):
        x = rng.randint(0, W)
        y = rng.randint(0, H)
        r = rng.randint(6, 18)
        c = rng.choice(colors) + (180,)
        d.ellipse([x-r, y-r, x+r, y+r], fill=c)
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")


def add_stars(img, seed=2, count=25):
    rng = random.Random(seed)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for _ in range(count):
        x = rng.randint(0, W)
        y = rng.randint(0, H)
        r = rng.randint(4, 14)
        d.ellipse([x-r, y-r, x+r, y+r], fill=(255, 240, 80, 160))
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")


def outlined_text(draw, pos, text, font, fill=(255,255,255), outline=(0,0,0), stroke=6):
    x, y = pos
    for dx in range(-stroke, stroke+1, 2):
        for dy in range(-stroke, stroke+1, 2):
            if dx*dx + dy*dy <= stroke*stroke:
                draw.text((x+dx, y+dy), text, font=font, fill=outline)
    draw.text(pos, text, font=font, fill=fill)


def center_x(draw, text, font):
    try:
        bb = draw.textbbox((0, 0), text, font=font)
        return (W - (bb[2] - bb[0])) // 2
    except Exception:
        return W // 2


def text_w(draw, text, font):
    try:
        bb = draw.textbbox((0, 0), text, font=font)
        return bb[2] - bb[0]
    except Exception:
        return len(text) * 20


def add_logo(draw):
    font = load_font(30)
    outlined_text(draw, (22, 18), "Happy Bear Kids", font,
                  fill=(255,255,255), outline=(0,0,0), stroke=3)


def add_shorts_badge(img):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    font = load_font(34)
    bw, bh = 260, 58
    x1, y1 = W - bw - 18, H - bh - 14
    d.rounded_rectangle([x1, y1, x1+bw, y1+bh], radius=29, fill=(220, 0, 0, 230))
    tw = text_w(d, "#SHORTS", font)
    d.text((x1 + (bw-tw)//2, y1 + (bh-34)//2), "#SHORTS", font=font, fill=(255,255,255,255))
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")


# ── Thumbnail generators ──────────────────────────────────────────────────────

def thumb_shape(shape: str, variant: int = 0) -> Image.Image:
    colors = SHAPE_COLORS.get(shape, ((100,100,200),(200,200,240)))
    img = gradient_bg(colors[1], colors[0])
    img = add_stars(img, seed=variant)

    # 3D sprite if available, else draw shape
    sp = None
    if shape in SHAPE_3D:
        sp = load_sprite(SHAPE_3D[shape], 520)
    if sp:
        img.paste(sp, ((W - sp.width)//2, (H - sp.height)//2 - 40), sp)
    else:
        # Draw geometric shape as fallback
        draw_shape_graphic(img, shape, colors[0])

    draw = ImageDraw.Draw(img)
    add_logo(draw)

    font = load_font(110)
    name = shape.capitalize()
    nx = center_x(draw, name, font)
    outlined_text(draw, (nx, H - 130), name, font,
                  fill=(255,255,255), outline=colors[0], stroke=7)
    return img


def draw_shape_graphic(img, shape: str, color):
    ov = Image.new("RGBA", (W, H), (0,0,0,0))
    d = ImageDraw.Draw(ov)
    cx, cy = W//2, H//2 - 40
    c = color + (220,)
    if shape == "star":
        pts = []
        for i in range(10):
            a = math.pi * i / 5 - math.pi/2
            r = 220 if i % 2 == 0 else 90
            pts.append((cx + r*math.cos(a), cy + r*math.sin(a)))
        d.polygon(pts, fill=c)
    elif shape == "heart":
        r = 120
        d.ellipse([cx-r-r+20, cy-r, cx+20, cy+r], fill=c)
        d.ellipse([cx-20, cy-r, cx+r+r-20, cy+r], fill=c)
        d.polygon([(cx-r*2+20, cy+30), (cx, cy+r*2-20), (cx+r*2-20, cy+30)], fill=c)
    elif shape == "diamond":
        d.polygon([(cx, cy-220), (cx+160, cy), (cx, cy+220), (cx-160, cy)], fill=c)
    elif shape == "hexagon":
        pts = [(cx + 200*math.cos(math.pi*i/3), cy + 200*math.sin(math.pi*i/3)) for i in range(6)]
        d.polygon(pts, fill=c)
    elif shape == "oval":
        d.ellipse([cx-240, cy-140, cx+240, cy+140], fill=c)
    else:
        d.ellipse([cx-200, cy-200, cx+200, cy+200], fill=c)
    img2 = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    img.paste(img2)


def thumb_animal_dance(animal: str, variant: int = 0) -> Image.Image:
    # Warm energetic background
    palettes = [
        ((255, 200, 40), (255, 130, 30)),
        ((255, 100, 150), (200, 40, 100)),
        ((80, 200, 120), (30, 140, 60)),
        ((100, 180, 255), (30, 100, 220)),
        ((200, 120, 255), (120, 40, 200)),
    ]
    top, bot = palettes[variant % len(palettes)]
    img = gradient_bg(top, bot)
    img = add_confetti(img, seed=variant)

    # 3D animal sprite (right side, large)
    sp = None
    if animal in ANIMAL_3D:
        sp = load_sprite(ANIMAL_3D[animal], 520)
    elif animal in ANIMAL_NEW:
        sp = load_sprite(ANIMAL_NEW[animal], 480)
    if sp:
        px = W - sp.width - 30
        py = (H - sp.height) // 2 - 20
        img.paste(sp, (px, py), sp)

    draw = ImageDraw.Draw(img)
    add_logo(draw)

    # "DANCING" label top-left
    font_big = load_font(90)
    font_sm  = load_font(72)
    outlined_text(draw, (30, 80), "DANCING", font_big,
                  fill=(255,255,255), outline=(0,0,0), stroke=6)
    anim_name = animal.upper()
    outlined_text(draw, (30, 178), anim_name, font_sm,
                  fill=(255,240,60), outline=(0,0,0), stroke=5)

    # Dance emoji stars
    font_em = load_font(55)
    outlined_text(draw, (30, H-110), "★ Fun Dance! ★", font_em,
                  fill=(255,255,255), outline=(0,0,0), stroke=3)
    return img


def thumb_vegetable_dance(vegetable: str, variant: int = 0) -> Image.Image:
    palettes = [
        ((50, 180, 80), (20, 120, 40)),
        ((100, 200, 100), (30, 150, 50)),
        ((60, 190, 160), (20, 130, 100)),
        ((150, 210, 60), (80, 160, 20)),
    ]
    top, bot = palettes[variant % len(palettes)]
    img = gradient_bg(top, bot)
    img = add_confetti(img, seed=variant + 10)

    sp = None
    veg_key = vegetable.lower()
    if veg_key in VEG_CARTOON:
        sp = load_sprite(VEG_CARTOON[veg_key], 500)
    if sp:
        px = W - sp.width - 40
        py = (H - sp.height) // 2 - 30
        img.paste(sp, (px, py), sp)

    draw = ImageDraw.Draw(img)
    add_logo(draw)

    font_big = load_font(90)
    font_sm  = load_font(72)
    outlined_text(draw, (30, 80), "DANCING", font_big,
                  fill=(255,255,255), outline=(0,0,0), stroke=6)
    outlined_text(draw, (30, 178), vegetable.upper(), font_sm,
                  fill=(255,240,60), outline=(0,0,0), stroke=5)
    font_em = load_font(55)
    outlined_text(draw, (30, H-110), "★ Veggie Dance! ★", font_em,
                  fill=(255,255,255), outline=(0,0,0), stroke=3)
    return img


def thumb_color_learn(color: str) -> Image.Image:
    scheme = COLOR_SCHEMES.get(color, ((150,150,200),(220,220,240)))
    img = gradient_bg(scheme[1], scheme[0])

    draw = ImageDraw.Draw(img)
    add_logo(draw)

    # Color name — big and bold
    font_big = load_font(200)
    name = color.upper()
    nx = center_x(draw, name, font_big)
    outlined_text(draw, (nx, 60), name, font_big,
                  fill=(255,255,255), outline=(0,0,0), stroke=12)

    # Arrange fruit/veg sprites at bottom
    sprites = []
    for fname in COLOR_FRUITS.get(color, []):
        if fname in FRUIT_CARTOON:
            s = load_sprite(FRUIT_CARTOON[fname], 200)
            if s:
                sprites.append(s)
    for fname in COLOR_VEGS.get(color, []):
        if fname in VEG_CARTOON:
            s = load_sprite(VEG_CARTOON[fname], 200)
            if s:
                sprites.append(s)

    sprites = sprites[:4]
    if sprites:
        total_w = sum(s.width for s in sprites) + 20*(len(sprites)-1)
        x0 = (W - total_w) // 2
        y0 = H - 240
        for sp in sprites:
            img.paste(sp, (x0, y0 + (200 - sp.height)//2), sp)
            x0 += sp.width + 20

    # "Learn Colors" subtitle
    font_sub = load_font(58)
    sub = "Learn Colors for Kids"
    sx = center_x(draw, sub, font_sub)
    outlined_text(draw, (sx, H - 70), sub, font_sub,
                  fill=(255,255,255), outline=(0,0,0), stroke=4)
    return img


def thumb_vocab(letter: str, word: str, sprite_path: Path | None = None) -> Image.Image:
    # Blue gradient like ABC
    img = gradient_bg((60, 180, 255), (20, 80, 200))
    img = add_stars(img, seed=ord(letter[0]) if letter else 1)

    # White left panel for letter
    ov = Image.new("RGBA", (W, H), (0,0,0,0))
    d = ImageDraw.Draw(ov)
    d.rounded_rectangle([25, 25, 490, H-25], radius=45, fill=(255,255,255,230))
    img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")

    draw = ImageDraw.Draw(img)
    add_logo(draw)

    # Big letter
    font_letter = load_font(300)
    font_word   = load_font(78)
    font_sub    = load_font(54)

    lx = (490 - text_w(draw, letter, font_letter)) // 2 + 25
    outlined_text(draw, (lx, 30), letter, font_letter,
                  fill=(255, 200, 40), outline=(30, 80, 180), stroke=8)
    # Word below letter
    wx = (490 - text_w(draw, word, font_word)) // 2 + 25
    outlined_text(draw, (wx, H - 130), word, font_word,
                  fill=(30, 80, 180), outline=(255,255,255), stroke=5)

    # Sprite on right side
    sp = load_sprite(sprite_path, 420) if sprite_path else None
    if sp:
        px = W - sp.width - 30
        py = (H - sp.height) // 2
        img.paste(sp, (px, py), sp)

    # "is for" text
    if_text = f"{letter} is for {word.capitalize()}"
    sx = center_x(draw, if_text, font_sub)
    # Place it below the sprite area
    outlined_text(draw, (sx if sx > 490 else 510, H - 80), if_text, font_sub,
                  fill=(255,255,255), outline=(0,0,0), stroke=3)
    return img


def thumb_shape_dance(shapes: list, variant: int = 0) -> Image.Image:
    img = gradient_bg((255, 230, 50), (200, 120, 20))
    img = add_confetti(img, seed=variant + 5)

    draw = ImageDraw.Draw(img)
    add_logo(draw)

    # Up to 3 shape sprites in a row
    sprites = []
    for sh in shapes[:3]:
        sp = None
        if sh in SHAPE_3D:
            sp = load_sprite(SHAPE_3D[sh], 300)
        if sp:
            sprites.append(sp)

    if sprites:
        total_w = sum(s.width for s in sprites) + 30*(len(sprites)-1)
        x0 = (W - total_w) // 2
        y0 = 120
        for sp in sprites:
            img.paste(sp, (x0, y0), sp)
            x0 += sp.width + 30

    font_big = load_font(90)
    font_sm  = load_font(62)
    outlined_text(draw, (center_x(draw, "DANCING SHAPES", font_big), H - 160),
                  "DANCING SHAPES", font_big, fill=(255,255,255), outline=(0,0,0), stroke=6)
    shape_names = " + ".join(s.capitalize() for s in shapes[:3])
    outlined_text(draw, (center_x(draw, shape_names, font_sm), H - 72),
                  shape_names, font_sm, fill=(255,240,80), outline=(0,0,0), stroke=4)
    return img


def thumb_arabic(title: str, color: tuple = (100, 150, 220), variant: int = 0) -> Image.Image:
    top = tuple(min(255, int(c*1.3)) for c in color)
    bot = tuple(max(0,   int(c*0.7)) for c in color)
    img = gradient_bg(top, bot)
    img = add_stars(img, seed=variant)
    draw = ImageDraw.Draw(img)
    add_logo(draw)

    # AR badge
    font_ar = load_font(42)
    ov = Image.new("RGBA", (W, H), (0,0,0,0))
    d = ImageDraw.Draw(ov)
    d.rounded_rectangle([W-170, 14, W-14, 74], radius=20, fill=(0,120,200,220))
    d.text((W-140, 22), "عربي", font=font_ar, fill=(255,255,255,255))
    img = Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")
    draw = ImageDraw.Draw(img)

    font_t = load_font(80)
    lines = []
    words = title.split()
    cur = []
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

    y0 = (H - len(lines)*90)//2
    for line in lines:
        nx = center_x(draw, line, font_t)
        outlined_text(draw, (nx, y0), line, font_t, fill=(255,255,255), outline=(0,0,0), stroke=5)
        y0 += 90
    return img


# ── Video → thumbnail mapping ─────────────────────────────────────────────────

VOCAB_SPRITES = {
    "A": (SPRITES_NEW / "fruits_cartoon" / "apple.png", "APPLE"),
    "B": (SPRITES_NEW / "fruits_cartoon" / "banana.png", "BANANA"),
    "C": (SPRITES_NEW / "animals_3d" / "cat.png", "CAT"),
    "D": (SPRITES_NEW / "animals" / "dog.png", "DOG"),
    "E": (SPRITES_NEW / "animals_3d" / "elephant.png", "ELEPHANT"),
    "F": (SPRITES_NEW / "animals" / "frog.png", "FROG"),
    "G": (None, "GIRAFFE"),
    "H": (None, "HIPPO"),
    "I": (None, "IGLOO"),
    "J": (None, "JELLYFISH"),
    "K": (SPRITES_NEW / "animals" / "koala.png", "KOALA"),
    "L": (SPRITES_NEW / "animals_3d" / "lion.png", "LION"),
    "M": (SPRITES_NEW / "animals" / "monkey.png", "MONKEY"),
    "N": (None, "NEST"),
    "O": (SPRITES_NEW / "animals" / "owl.png", "OWL"),
    "P": (SPRITES_NEW / "animals" / "penguin.png", "PENGUIN"),
    "Q": (None, "QUEEN"),
    "R": (SPRITES_NEW / "animals" / "rabbit.png", "RABBIT"),
    "S": (None, "STAR"),
    "T": (SPRITES_NEW / "animals" / "tiger.png", "TIGER"),
    "U": (None, "UMBRELLA"),
    "V": (None, "VIOLIN"),
    "W": (SPRITES_NEW / "fruits_cartoon" / "watermelon.png", "WATERMELON"),
    "X": (None, "XYLOPHONE"),
    "Y": (None, "YAK"),
    "Z": (None, "ZEBRA"),
}

SHAPE_KEYWORDS = ["circle","square","triangle","star","diamond","heart","hexagon","oval"]
ANIMAL_KEYWORDS = list(ANIMAL_3D.keys()) + list(ANIMAL_NEW.keys())
VEGETABLE_KEYWORDS = list(VEG_CARTOON.keys())
COLOR_KEYWORDS = list(COLOR_SCHEMES.keys())


def parse_video(video_id: str, title: str, description: str = "") -> dict:
    """Determine thumbnail params from video title."""
    t = title.lower()

    # Arabic video
    if "ar_" in video_id or "عربي" in title or "arabic" in t or "عر" in title:
        color_map = {"red": (200,50,50), "orange": (220,110,30), "yellow": (200,190,30),
                     "green": (50,160,60), "blue": (50,110,210), "purple": (120,60,190),
                     "pink": (210,70,150)}
        for c, col in color_map.items():
            if c in t:
                return {"type": "arabic", "title": title, "color": col, "variant": hash(video_id)%5}
        for sh in SHAPE_KEYWORDS:
            if sh in t:
                return {"type": "arabic_shape", "shape": sh, "title": title}
        return {"type": "arabic", "title": title, "color": (100,150,220), "variant": hash(video_id)%5}

    # Vocab short: "Letter X | X is for WORD"
    m = re.search(r"letter\s+([a-z])\b", t)
    if m:
        letter = m.group(1).upper()
        sp_path, word = VOCAB_SPRITES.get(letter, (None, letter))
        return {"type": "vocab", "letter": letter, "word": word, "sprite": sp_path}

    # Shape dance: "dancing shapes" or multiple shapes
    if "dancing shapes" in t or "shapes dance" in t:
        found = [sh for sh in SHAPE_KEYWORDS if sh in t]
        return {"type": "shape_dance", "shapes": found or ["circle","square","triangle"],
                "variant": hash(video_id)%5}

    # Shape float/learn: single shape
    for sh in SHAPE_KEYWORDS:
        if sh in t and ("shape" in t or "float" in t or "learn" in t or "learn shapes" in t):
            return {"type": "shape", "shape": sh, "variant": hash(video_id)%3}

    # Single shape name in title (e.g. "Circle | Learn Shapes")
    for sh in SHAPE_KEYWORDS:
        if re.search(rf"\b{sh}\b", t):
            if "shape" in t or "learn" in t or any(s in t for s in SHAPE_KEYWORDS if s!=sh):
                return {"type": "shape", "shape": sh, "variant": hash(video_id)%3}

    # Color learn: "color red" or "learn colors red"
    for c in COLOR_KEYWORDS:
        if re.search(rf"\b{c}\b", t) and ("color" in t or "colour" in t):
            return {"type": "color", "color": c}

    # Vegetable dance — use word boundary to avoid "corn" matching "unicorn"
    for v in VEGETABLE_KEYWORDS:
        if re.search(rf"\b{v}\b", t) and ("danc" in t or "vegeta" in t):
            return {"type": "vegetable", "vegetable": v, "variant": hash(video_id)%4}

    # Animal dance — extended list, whole-word match
    for a in ["lion","elephant","duck","cat","whale","fish","unicorn","bear","tiger",
              "monkey","penguin","rabbit","owl","koala","dog","frog","parrot","dino",
              "pig","cow","panda","fox"]:
        if re.search(rf"\b{a}\b", t):
            if "danc" in t or "cute" in t or "fun" in t or "happy" in t or "music" in t:
                return {"type": "animal", "animal": a, "variant": hash(video_id)%5}

    # Fallback for shapes without extra context
    for sh in SHAPE_KEYWORDS:
        if re.search(rf"\b{sh}\b", t):
            return {"type": "shape", "shape": sh, "variant": hash(video_id)%3}

    # Generic dance fallback — pick different animal per video so duplicates differ
    fallback_animals = ["bear","tiger","monkey","penguin","rabbit","owl","lion","elephant"]
    animal = fallback_animals[hash(video_id) % len(fallback_animals)]
    return {"type": "animal", "animal": animal, "variant": hash(video_id)%5}


def generate_thumbnail(params: dict, video_id: str, is_shorts: bool = True) -> Image.Image:
    t = params["type"]
    if t == "shape":
        img = thumb_shape(params["shape"], params.get("variant", 0))
    elif t == "shape_dance":
        img = thumb_shape_dance(params.get("shapes", ["circle","square","triangle"]),
                                params.get("variant", 0))
    elif t == "color":
        img = thumb_color_learn(params["color"])
    elif t == "vocab":
        img = thumb_vocab(params["letter"], params["word"], params.get("sprite"))
    elif t == "vegetable":
        img = thumb_vegetable_dance(params["vegetable"], params.get("variant", 0))
    elif t == "animal":
        img = thumb_animal_dance(params["animal"], params.get("variant", 0))
    elif t in ("arabic", "arabic_shape"):
        img = thumb_arabic(params.get("title",""), params.get("color",(100,150,220)),
                           params.get("variant", 0))
    else:
        img = thumb_animal_dance("bear", 0)

    if is_shorts:
        img = add_shorts_badge(img)
    return img


# ── YouTube API ───────────────────────────────────────────────────────────────

def get_youtube():
    if not CREDS.exists():
        print(f"ERROR: token.pickle not found at {CREDS}")
        sys.exit(1)
    with open(CREDS, "rb") as f:
        creds = pickle.load(f)
    from googleapiclient.discovery import build
    return build("youtube", "v3", credentials=creds)


def get_all_videos(yt) -> list[dict]:
    """Return list of {id, title, description} for all channel uploads."""
    # First get uploads playlist ID
    ch = yt.channels().list(part="contentDetails", mine=True).execute()
    uploads_id = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    videos = []
    page_token = None
    while True:
        resp = yt.playlistItems().list(
            part="snippet",
            playlistId=uploads_id,
            maxResults=50,
            pageToken=page_token,
        ).execute()
        for item in resp.get("items", []):
            sn = item["snippet"]
            videos.append({
                "id":          sn["resourceId"]["videoId"],
                "title":       sn["title"],
                "description": sn.get("description", ""),
            })
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return videos


def upload_thumbnail(yt, video_id: str, img: Image.Image) -> bool:
    from googleapiclient.http import MediaIoBaseUpload
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=92)
    buf.seek(0)
    media = MediaIoBaseUpload(buf, mimetype="image/jpeg", resumable=False)
    try:
        yt.thumbnails().set(videoId=video_id, media_body=media).execute()
        return True
    except Exception as e:
        print(f"  ✗ upload error: {e}")
        return False


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Generate thumbnails but don't upload")
    parser.add_argument("--id", dest="video_id",
                        help="Process a single video ID")
    parser.add_argument("--title", default="",
                        help="Title for single video (used with --id)")
    parser.add_argument("--only", nargs="+", metavar="VIDEO_ID",
                        help="Only re-upload these specific video IDs (fetch titles from API)")
    args = parser.parse_args()

    THUMB_DIR.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        print("\n[DRY RUN] Generating thumbnails only (no upload)\n")
    else:
        print("\nFix thumbnails: generate + upload to YouTube\n")

    yt = None
    if not args.dry_run:
        yt = get_youtube()

    if args.video_id:
        videos = [{"id": args.video_id, "title": args.title or args.video_id, "description": ""}]
    elif args.only:
        # Fetch details only for specified IDs
        if not yt:
            yt = get_youtube()
        resp = yt.videos().list(part="snippet", id=",".join(args.only)).execute()
        videos = [{"id": it["id"], "title": it["snippet"]["title"],
                   "description": it["snippet"].get("description","")}
                  for it in resp.get("items",[])]
        print(f"Processing {len(videos)} specified video(s)\n")
    else:
        if args.dry_run:
            # Use sample set for dry run without API call
            videos = [
                {"id": "TEST_circle",   "title": "Circle | Learn Shapes for Kids #shorts", "description": ""},
                {"id": "TEST_square",   "title": "Square | Learn Shapes for Kids #shorts", "description": ""},
                {"id": "TEST_lion",     "title": "Dancing Lion 🦁 Cute Animals Dancing #shorts", "description": ""},
                {"id": "TEST_elephant", "title": "Dancing Elephant 🐘 Happy Music #shorts", "description": ""},
                {"id": "TEST_red",      "title": "Color Red | Learn Colors for Kids #shorts", "description": ""},
                {"id": "TEST_green",    "title": "Color Green | Learn Colors for Kids #shorts", "description": ""},
                {"id": "TEST_A",        "title": "Letter A | A is for Apple | ABC for Kids #shorts", "description": ""},
                {"id": "TEST_B",        "title": "Letter B | B is for Banana | ABC for Kids #shorts", "description": ""},
                {"id": "TEST_sdance",   "title": "Dancing Shapes | Circle Square Triangle #shorts", "description": ""},
                {"id": "TEST_carrot",   "title": "Dancing Carrot 🥕 Happy Bear Kids #shorts", "description": ""},
            ]
        else:
            print("Fetching video list from YouTube...", flush=True)
            videos = get_all_videos(yt)
            print(f"Found {len(videos)} videos\n")

    ok = 0
    skip = 0
    for v in videos:
        vid   = v["id"]
        title = v["title"]
        is_short = "#shorts" in title.lower() or "ar_short" in vid.lower()

        params = parse_video(vid, title, v.get("description",""))
        img    = generate_thumbnail(params, vid, is_short)

        safe_title = re.sub(r"[^\w\-]", "_", title[:40])
        out_path   = THUMB_DIR / f"{vid}_{safe_title}.jpg"
        img.save(str(out_path), "JPEG", quality=92)

        type_str = params["type"]
        detail   = ""
        if "shape" in params: detail = params["shape"]
        elif "animal" in params: detail = params["animal"]
        elif "color" in params: detail = params["color"]
        elif "letter" in params: detail = f"{params['letter']}={params['word']}"
        elif "vegetable" in params: detail = params["vegetable"]

        if not args.dry_run and yt:
            success = upload_thumbnail(yt, vid, img)
            if success:
                print(f"  ✓ {vid}  [{type_str:12} {detail:10}]  {title[:50]}")
                ok += 1
            else:
                skip += 1
        else:
            print(f"  → {vid}  [{type_str:12} {detail:10}]  {title[:50]}")
            ok += 1

    print(f"\nDone: {ok}/{len(videos)} thumbnails {'uploaded' if not args.dry_run else 'generated'}")
    print(f"Saved to: {THUMB_DIR}")


if __name__ == "__main__":
    main()
