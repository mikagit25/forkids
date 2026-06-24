#!/usr/bin/env python3
"""
Generate ShapeLearnLong2 videos — 30-min shape learning, v2.

Improvements over v1:
- 3D PNG sprites (FLUX-generated) instead of CSS flat shapes
- DVD screensaver bounce, fly-in from edges, orbit sections
- Count 1→5 (not just 1→3), each flies in from screen edge
- Wobble (PIP/BWW) on all sprites
- CSS hue-rotate for rainbow section
- Two music tracks with crossfade at 15 min

8 shapes: circle, square, triangle, star, diamond, heart, hexagon, oval
Output: shape_learn2_{shape}_{DATE}.mp4 on all 3 channels (EN / AR / ID)

Usage:
  python3 scripts/generate_shape_learn_v2.py              # all 8 shapes
  python3 scripts/generate_shape_learn_v2.py --shapes circle star
  python3 scripts/generate_shape_learn_v2.py --dry-run
  python3 scripts/generate_shape_learn_v2.py --regen-meta
"""
import argparse
import base64
import json
import subprocess
import sys
import time
import yaml
from datetime import datetime
from pathlib import Path

ROOT     = Path(__file__).resolve().parent.parent
REMOTION = ROOT / "remotion"
QUEUE_EN = ROOT / "output" / "queue"
QUEUE_AR = ROOT / "output" / "queue_ar"
QUEUE_ID = ROOT / "output" / "queue_id"

TOGETHER_KEY_FILE = ROOT / "credentials" / "together_api_key.txt"
TOGETHER_URL      = "https://api.together.xyz/v1/images/generations"
TOGETHER_MODEL    = "black-forest-labs/FLUX.1-schnell"

DATE_STR  = datetime.now().strftime("%Y%m%d")
FPS       = 30
LONG_DUR  = 1800   # 30 minutes

# 20-track pool (same as all other scripts)
_ALL_TRACKS = [
    "Carefree.mp3", "Crinoline Dreams.mp3", "Gymnopedie No 1.mp3",
    "Happy Happy Game Show.mp3", "Heartwarming.mp3", "Hyperfun.mp3",
    "Life of Riley.mp3", "Merry Go.mp3", "Monkeys Spinning Monkeys.mp3",
    "Overworld.mp3", "Pinball Spring.mp3", "Pixelland.mp3",
    "Quirky Dog.mp3", "Salty Ditty.mp3", "Sneaky Snitch.mp3",
    "Wholesome.mp3", "Fluffing a Duck.mp3", "Walking Along.mp3",
    "George Street Shuffle.mp3", "Circus of Freaks.mp3",
]


def alt_music(en_music: str, ep_idx: int, lang: str) -> str:
    if lang == "en":
        return en_music
    offset = 7 if lang == "ar" else 14
    pool = [t for t in _ALL_TRACKS if t != en_music]
    return pool[(ep_idx + offset) % len(pool)]


def alt_music2(en_music2: str, ep_idx: int, lang: str) -> str:
    """Second track (second half of video) — offset further to ensure unique."""
    if lang == "en":
        return en_music2
    offset = 10 if lang == "ar" else 17
    pool = [t for t in _ALL_TRACKS if t != en_music2]
    return pool[(ep_idx + offset) % len(pool)]


# Shape config: colour, background, sprite PNG (in shapes_3d/)
SHAPES = {
    "circle":   {"color": "#2980B9", "bg": "#E3F2FD", "bg2": "#B3D4F5", "color_en": "blue",   "color_ar": "أزرق", "color_id": "biru"},
    "square":   {"color": "#E74C3C", "bg": "#FFEBEE", "bg2": "#F8BBD0", "color_en": "red",    "color_ar": "أحمر", "color_id": "merah"},
    "triangle": {"color": "#27AE60", "bg": "#F1F8E9", "bg2": "#C8E6C9", "color_en": "green",  "color_ar": "أخضر", "color_id": "hijau"},
    "star":     {"color": "#F9A825", "bg": "#FFFDE7", "bg2": "#FFF9C4", "color_en": "yellow", "color_ar": "أصفر", "color_id": "kuning"},
    "diamond":  {"color": "#8E44AD", "bg": "#F3E5F5", "bg2": "#E1BEE7", "color_en": "purple", "color_ar": "بنفسجي", "color_id": "ungu"},
    "heart":    {"color": "#E91E63", "bg": "#FCE4EC", "bg2": "#F8BBD0", "color_en": "pink",   "color_ar": "وردي", "color_id": "merah muda"},
    "hexagon":  {"color": "#E67E22", "bg": "#FFF3E0", "bg2": "#FFE0B2", "color_en": "orange", "color_ar": "برتقالي", "color_id": "oranye"},
    "oval":     {"color": "#16A085", "bg": "#E0F7FA", "bg2": "#B2EBF2", "color_en": "teal",   "color_ar": "أخضر مزرق", "color_id": "biru kehijauan"},
}

SHAPES_AR = {
    "circle": "دائرة", "square": "مربع", "triangle": "مثلث",
    "star": "نجمة", "diamond": "معين", "heart": "قلب",
    "hexagon": "سداسي", "oval": "بيضاوي",
}

SHAPES_ID = {
    "circle": "lingkaran", "square": "persegi", "triangle": "segitiga",
    "star": "bintang", "diamond": "belah ketupat", "heart": "hati",
    "hexagon": "segi enam", "oval": "oval",
}

# Two-track pairs per shape (both halves of video)
MUSIC_PAIRS = [
    ("Carefree.mp3",              "Wholesome.mp3"),
    ("Merry Go.mp3",              "Pinball Spring.mp3"),
    ("Happy Happy Game Show.mp3", "Quirky Dog.mp3"),
    ("Life of Riley.mp3",         "Hyperfun.mp3"),
    ("Monkeys Spinning Monkeys.mp3", "Crinoline Dreams.mp3"),
    ("Salty Ditty.mp3",           "Walking Along.mp3"),
    ("Heartwarming.mp3",          "George Street Shuffle.mp3"),
    ("Overworld.mp3",             "Pixelland.mp3"),
]

# Thumbnail accent color per shape
THUMB_ACCENT = {
    "circle": "blue", "square": "red", "triangle": "green",
    "star": "yellow", "diamond": "purple", "heart": "pink",
    "hexagon": "orange", "oval": "teal",
}


# ── Meta ─────────────────────────────────────────────────────────────────────

def make_meta_en(shape: str) -> dict:
    d = SHAPES[shape]
    color_en = d["color_en"]
    shape_cap = shape.capitalize()
    description = (
        f"🔷 30 minutes of {shape} shape learning for babies and toddlers!\n\n"
        f"Introducing the {shape_cap} Shape — our most engaging version yet!\n"
        f"Watch as one {shape} grows into five, each flying in from a different direction.\n\n"
        f"What your child learns:\n"
        f"🚀 BOUNCE — 1 bouncing {shape} travels across the whole screen (like a screensaver!)\n"
        f"💫 DUO — 2 shapes drift in opposite directions\n"
        f"🌀 TRIO — 3 shapes orbit around each other\n"
        f"🌈 RAINBOW — The {shape} slowly changes through every color\n"
        f"1️⃣ COUNT — Shapes fly in one by one: 1, 2, 3, 4, 5!\n"
        f"✨ HYPNO — Calming color-loop animation, perfect for nap time\n\n"
        f"🌟 Why this video works:\n"
        f"• One shape only — deep focus builds real shape recognition\n"
        f"• 3D animated {shape} with constant movement (never static!)\n"
        f"• Beautiful rainbow colors — visual color learning built in\n"
        f"• Count 1 to 5 — shapes fly in from screen edges\n"
        f"• No text or voice — universal content for any language!\n"
        f"• Gentle pace — perfect background video during play\n"
        f"• Safe, ad-free content for babies ages 0–3\n\n"
        f"Shape Series: Circle · Square · Triangle · Star · Diamond · Heart · Hexagon · Oval\n\n"
        f"🔔 Subscribe → @HappyBearKids1\n\n"
        f"🎵 Music: Kevin MacLeod (incompetech.com) · CC BY 4.0\n"
        f"http://creativecommons.org/licenses/by/4.0/\n\n"
        f"#LearnShapes #{shape_cap}Shape #ShapesForKids #ToddlerLearning "
        f"#BabyEducation #HappyBearKids #PreschoolShapes #VisualLearning "
        f"#ShapeRecognition #CountingForKids\n\n© Happy Bear Kids 2026"
    )
    return {
        "title":       f"Learn the {shape_cap}! 3D Shape for Babies 🔷 30 Min | Happy Bear Kids",
        "description": description,
        "tags": [
            "learn shapes", f"{shape} shape", "shapes for kids", "toddler learning",
            "baby education", "happy bear kids", "preschool", "shape recognition",
            "3D shapes", "counting 1 to 5", "visual learning", "no talking",
            "30 minutes", shape, shape_cap, color_en,
        ],
        "video_type": "shapes_long",
        "language":   "en",
        "is_short":   False,
        "status":     "public",
    }


def make_meta_ar(shape: str) -> dict:
    ar = SHAPES_AR[shape]
    d = SHAPES[shape]
    description = (
        f"🔷 30 دقيقة من تعلم شكل {ar} للرضع والأطفال الصغار!\n\n"
        f"شاهدوا شكل {ar} ثلاثي الأبعاد يتحرك ويقفز ويطير عبر الشاشة!\n\n"
        f"ماذا يتعلم طفلك:\n"
        f"🚀 القفز — {ar} يتحرك عبر الشاشة كاملة\n"
        f"💫 الثنائي — شكلان يتحركان في اتجاهين متعاكسين\n"
        f"🌀 الثلاثي — ثلاثة أشكال تدور حول بعضها\n"
        f"🌈 قوس قزح — الشكل يتغير تدريجياً عبر كل الألوان\n"
        f"1️⃣ العد — الأشكال تطير واحداً تلو الآخر: 1، 2، 3، 4، 5!\n"
        f"✨ التأمل — رسوم هادئة مثالية لوقت النوم\n\n"
        f"🌟 بدون كلام أو نص — محتوى بصري لجميع اللغات!\n"
        f"محتوى آمن وبدون إعلانات للأطفال من 0 إلى 3 سنوات\n\n"
        f"سلسلة الأشكال: دائرة · مربع · مثلث · نجمة · معين · قلب · سداسي · بيضاوي\n\n"
        f"🔔 اشتركوا → @happybearkidsar\n\n"
        f"🎵 موسيقى: Kevin MacLeod · CC BY 4.0\n\n"
        f"#تعلم_الأشكال #{ar} #أشكال_للأطفال #تعليم_أطفال "
        f"#هابي_بير_كيدز #الأشكال_الهندسية #رضع #أطفال\n\n© Happy Bear Kids 2026"
    )
    return {
        "title":       f"تعلم شكل {ar}! 🔷 30 دقيقة | هابي بير كيدز",
        "description": description,
        "tags": [
            "تعلم الأشكال", f"شكل {ar}", "أشكال للأطفال", "تعليم أطفال",
            "هابي بير كيدز", "رضع", "أشكال هندسية", "مواد تعليمية", "30 دقيقة",
        ],
        "video_type": "shapes_long",
        "language":   "ar",
        "is_short":   False,
        "status":     "public",
    }


def make_meta_id(shape: str) -> dict:
    id_name = SHAPES_ID[shape]
    d = SHAPES[shape]
    color_id = d["color_id"]
    description = (
        f"🔷 30 menit belajar bentuk {id_name} untuk bayi dan balita!\n\n"
        f"Lihat bentuk {id_name} 3D yang melompat, bergerak, dan terbang di layar!\n\n"
        f"Yang dipelajari anak Anda:\n"
        f"🚀 PANTUL — 1 {id_name} memantul di seluruh layar\n"
        f"💫 DUA — 2 bentuk bergerak ke arah berlawanan\n"
        f"🌀 TIGA — 3 bentuk mengorbit satu sama lain\n"
        f"🌈 PELANGI — Bentuk perlahan berubah melalui semua warna\n"
        f"1️⃣ HITUNG — Bentuk terbang satu per satu: 1, 2, 3, 4, 5!\n"
        f"✨ HYPNO — Animasi menenangkan, cocok untuk tidur siang\n\n"
        f"🌟 Tanpa teks atau suara — konten universal untuk semua bahasa!\n"
        f"Konten aman dan bebas iklan untuk bayi usia 0–3 tahun\n\n"
        f"Seri Bentuk: Lingkaran · Persegi · Segitiga · Bintang · Belah Ketupat · Hati · Segi Enam · Oval\n\n"
        f"🔔 Subscribe → @happybearkidsin\n\n"
        f"🎵 Musik: Kevin MacLeod · CC BY 4.0\n\n"
        f"#BelajarBentuk #{id_name.replace(' ', '')} #BentukUntukAnak #PendidikanAnak "
        f"#HappyBearKids #Balita #BabyLearning\n\n© Happy Bear Kids 2026"
    )
    return {
        "title":       f"Belajar Bentuk {id_name.title()}! 🔷 30 Menit | Happy Bear Kids",
        "description": description,
        "tags": [
            "belajar bentuk", id_name, "bentuk untuk anak", "pendidikan anak",
            "happy bear kids", "balita", "bayi", "bentuk geometri", "30 menit",
        ],
        "video_type": "shapes_long",
        "language":   "id",
        "is_short":   False,
        "status":     "public",
    }


# ── Thumbnail ─────────────────────────────────────────────────────────────────

def generate_thumbnail(shape: str, lang: str, out_path: Path, api_key: str) -> bool:
    import requests
    d = SHAPES[shape]
    shape_cap = shape.capitalize()
    color_en = d["color_en"]

    lang_prompts = {
        "en": f"A cute glossy 3D {color_en} {shape} toy shape, Pixar style, "
              f"on a colorful pastel background with sparkles, children's YouTube thumbnail, "
              f"bright vivid colors, no text",
        "ar": f"A cute glossy 3D {color_en} {shape} toy shape, Pixar style, "
              f"on a colorful pastel background with sparkles, children's YouTube thumbnail, "
              f"bright vivid colors, no text, no letters, no words, no numbers",
        "id": f"A cute glossy 3D {color_en} {shape} toy shape, Pixar style, "
              f"on a colorful pastel background with sparkles, children's YouTube thumbnail, "
              f"bright vivid colors, no text",
    }
    prompt = lang_prompts.get(lang, lang_prompts["en"])

    try:
        resp = requests.post(
            TOGETHER_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": TOGETHER_MODEL,
                "prompt": prompt,
                "width": 1280, "height": 720,
                "steps": 4, "n": 1,
                "response_format": "b64_json",
            },
            timeout=60,
        )
        resp.raise_for_status()
        b64 = resp.json()["data"][0]["b64_json"]
        out_path.write_bytes(base64.b64decode(b64))
        print(f"    thumb {lang.upper()} → {out_path.name}")
        return True
    except Exception as e:
        print(f"    thumbnail {lang} failed: {e}")
        return False


# ── Render ────────────────────────────────────────────────────────────────────

def render_v2(shape: str, lang: str, ep_idx: int, dry_run: bool) -> Path | None:
    d      = SHAPES[shape]
    queue  = {"en": QUEUE_EN, "ar": QUEUE_AR, "id": QUEUE_ID}[lang]
    suffix = f"shape_learn2_{shape}_{lang}_{DATE_STR}" if lang != "en" else f"shape_learn2_{shape}_{DATE_STR}"
    out    = queue / f"{suffix}.mp4"

    if out.exists():
        print(f"  skip {out.name} ({out.stat().st_size/1024/1024:.0f}MB)")
        return out

    music1_en, music2_en = MUSIC_PAIRS[ep_idx % len(MUSIC_PAIRS)]
    music1 = alt_music(music1_en, ep_idx, lang)
    music2 = alt_music2(music2_en, ep_idx, lang)

    props = {
        "spritePath":  f"shapes_3d/{shape}.png",
        "shapeColor":  d["color"],
        "bgColor":     d["bg"],
        "bgColorEnd":  d["bg2"],
        "musicFile":   music1,
        "musicFile2":  music2,
        "accentColor": "#FFFFFF",
    }

    print(f"  [{lang.upper()}] {out.name} | {music1} + {music2}")

    if dry_run:
        print(f"    [DRY RUN]")
        return out

    queue.mkdir(parents=True, exist_ok=True)
    cmd = [
        "npx", "remotion", "render",
        "src/index.ts", "ShapeLearnLong2",
        str(out),
        "--props", json.dumps(props),
        "--concurrency", "1",
        "--log", "error",
    ]
    start  = time.time()
    result = subprocess.run(cmd, cwd=str(REMOTION),
                            capture_output=True, text=True, timeout=21600)
    if result.returncode == 0 and out.exists():
        elapsed = (time.time() - start) / 60
        print(f"    ✓ {out.stat().st_size/1024/1024:.0f}MB in {elapsed:.0f}min")
        return out
    else:
        print(f"    ✗ FAILED: {result.stderr[-300:]}")
        return None


def process_shape(shape: str, ep_idx: int, dry_run: bool, api_key: str):
    print(f"\n{'='*60}")
    print(f"Shape: {shape.upper()} (ep {ep_idx})")
    print(f"{'='*60}")

    make_fn = {"en": make_meta_en, "ar": make_meta_ar, "id": make_meta_id}

    for lang in ["en", "ar", "id"]:
        queue  = {"en": QUEUE_EN, "ar": QUEUE_AR, "id": QUEUE_ID}[lang]
        suffix = f"shape_learn2_{shape}_{lang}_{DATE_STR}" if lang != "en" else f"shape_learn2_{shape}_{DATE_STR}"
        mp4    = queue / f"{suffix}.mp4"
        meta   = queue / f"meta_{suffix}.yaml"
        thumb  = queue / f"thumb_{suffix}.png"

        mp4_path = render_v2(shape, lang, ep_idx, dry_run)

        if not meta.exists() and not dry_run:
            queue.mkdir(parents=True, exist_ok=True)
            data = make_fn[lang](shape)
            with open(meta, "w") as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            print(f"    meta {lang.upper()} → {meta.name}")
        elif dry_run:
            print(f"    [DRY RUN] meta {lang.upper()}")

        if not thumb.exists() and not dry_run and api_key:
            time.sleep(1)
            generate_thumbnail(shape, lang, thumb, api_key)


def regen_meta_only(shapes: list[str], api_key: str):
    """Regenerate only meta + thumbnails for existing v2 MPs."""
    make_fn = {"en": make_meta_en, "ar": make_meta_ar, "id": make_meta_id}
    queues  = {"en": QUEUE_EN, "ar": QUEUE_AR, "id": QUEUE_ID}

    for shape in shapes:
        for lang in ["en", "ar", "id"]:
            queue  = queues[lang]
            suffix = f"shape_learn2_{shape}_{lang}_*" if lang != "en" else f"shape_learn2_{shape}_*"
            # find any matching MP4
            matches = sorted(queue.glob(f"shape_learn2_{shape}{'_'+lang if lang != 'en' else ''}_*.mp4"))
            if not matches:
                print(f"  no MP4 found for {shape}/{lang}, skipping")
                continue
            stem  = matches[-1].stem
            meta  = queue / f"meta_{stem}.yaml"
            thumb = queue / f"thumb_{stem}.png"

            data = make_fn[lang](shape)
            with open(meta, "w") as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            print(f"  meta {shape}/{lang} → {meta.name}")

            if not thumb.exists() and api_key:
                time.sleep(1)
                generate_thumbnail(shape, lang, thumb, api_key)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Generate ShapeLearnLong2 videos v2")
    ap.add_argument("--shapes",    nargs="+", choices=list(SHAPES), help="Specific shapes")
    ap.add_argument("--dry-run",   action="store_true")
    ap.add_argument("--regen-meta",action="store_true", help="Regen meta+thumb only")
    args = ap.parse_args()

    api_key = ""
    if TOGETHER_KEY_FILE.exists():
        api_key = TOGETHER_KEY_FILE.read_text().strip()

    shapes = args.shapes or list(SHAPES.keys())
    all_shapes = list(SHAPES.keys())

    if args.regen_meta:
        regen_meta_only(shapes, api_key)
        return

    print(f"\nShapeLearnLong2 v2 — {len(shapes)} shape(s) × 3 channels\n")

    for shape in shapes:
        ep_idx = all_shapes.index(shape)
        process_shape(shape, ep_idx, args.dry_run, api_key)

    print("\n✓ Done")


if __name__ == "__main__":
    main()
