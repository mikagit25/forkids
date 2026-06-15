#!/usr/bin/env python3
"""
Generate ShapeLearnLong videos — 30-min "One Concept Deep" shape videos.
No text on screen → universal content → published on BOTH EN and AR channels
with separate bilingual descriptions.

8 shapes: circle, square, triangle, star, diamond, heart, hexagon, oval

Usage:
  python3 scripts/generate_shape_learn.py              # all 8 shapes
  python3 scripts/generate_shape_learn.py --shapes circle square
  python3 scripts/generate_shape_learn.py --dry-run
  python3 scripts/generate_shape_learn.py --regen-meta # regenerate meta+thumb only
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
STYLE_BASE        = "children's YouTube thumbnail, bright vivid colors, no text, 1280x720"

DATE_STR = datetime.now().strftime("%Y%m%d")
FPS      = 30
LONG_DUR = 1800  # 30 minutes

SHAPES = {
    "circle":   {"color": "#2980B9", "bg": "#E3F2FD", "color_en": "blue",   "color_ar": "أزرق"},
    "square":   {"color": "#E74C3C", "bg": "#FFEBEE", "color_en": "red",    "color_ar": "أحمر"},
    "triangle": {"color": "#27AE60", "bg": "#F1F8E9", "color_en": "green",  "color_ar": "أخضر"},
    "star":     {"color": "#F9A825", "bg": "#FFFDE7", "color_en": "yellow", "color_ar": "أصفر"},
    "diamond":  {"color": "#8E44AD", "bg": "#F3E5F5", "color_en": "purple", "color_ar": "بنفسجي"},
    "heart":    {"color": "#E91E63", "bg": "#FCE4EC", "color_en": "pink",   "color_ar": "وردي"},
    "hexagon":  {"color": "#E67E22", "bg": "#FFF3E0", "color_en": "orange", "color_ar": "برتقالي"},
    "oval":     {"color": "#16A085", "bg": "#E0F7FA", "color_en": "teal",   "color_ar": "أخضر مزرق"},
}

SHAPES_AR = {
    "circle":   "دائرة",
    "square":   "مربع",
    "triangle": "مثلث",
    "star":     "نجمة",
    "diamond":  "معين",
    "heart":    "قلب",
    "hexagon":  "سداسي",
    "oval":     "بيضاوي",
}

SHAPES_ID = {
    "circle":   "lingkaran",
    "square":   "persegi",
    "triangle": "segitiga",
    "star":     "bintang",
    "diamond":  "belah ketupat",
    "heart":    "hati",
    "hexagon":  "segi enam",
    "oval":     "oval",
}

MUSIC_TRACKS = [
    "Carefree.mp3", "Wholesome.mp3", "Merry Go.mp3", "Pinball Spring.mp3",
    "Happy Happy Game Show.mp3", "Quirky Dog.mp3", "Life of Riley.mp3",
    "Hyperfun.mp3",
]


def make_meta_en(shape: str) -> dict:
    ar = SHAPES_AR[shape]
    d  = SHAPES[shape]
    color_en = d["color_en"]
    shape_cap = shape.capitalize()

    description = (
        f"🔷 30 minutes of {shape} shape learning for babies and toddlers!\n\n"
        f"Using the \"One Concept Deep\" method — we spend the full 30 minutes "
        f"exploring just ONE shape: the {shape_cap}. "
        f"Repeated exposure builds lasting shape memory.\n\n"
        f"What your child learns in this video:\n"
        f"🔷 FORM — What does a {shape} look like? Where do we see {shape}s?\n"
        f"🎨 COLOR — The same {shape} in different beautiful colors\n"
        f"🔢 COUNT — 1 {shape}, 2 {shape}s, 3 {shape}s — visual counting\n"
        f"✨ HYPNO — Calming color-loop animation, perfect for nap time\n\n"
        f"🌟 Why this video works:\n"
        f"• One shape only — deep focus builds real shape recognition\n"
        f"• 30+ repetitions — not just a quick flash\n"
        f"• No talking or text — purely visual, great for any language!\n"
        f"• Calming pace — works as background video during play\n"
        f"• Safe, ad-free content for babies ages 0–3\n"
        f"• Rainbow color phase helps teach colors through {shape}s\n"
        f"• Dot counting visual — no pressure, just gentle exposure\n\n"
        f"Part of our complete Shape Series (8 shapes):\n"
        f"Circle · Square · Triangle · Star · Diamond · Heart · Hexagon · Oval\n\n"
        f"🔔 Subscribe → @HappyBearKids1\n"
        f"New educational videos every week!\n\n"
        f"🎵 Music: Kevin MacLeod (incompetech.com)\n"
        f"Licensed under Creative Commons Attribution 4.0\n"
        f"http://creativecommons.org/licenses/by/4.0/\n\n"
        f"#LearnShapes #{shape_cap}Shape #ShapesForKids #ToddlerLearning "
        f"#BabyEducation #HappyBearKids #PreschoolShapes #KidsEducation "
        f"#ShapeRecognition #VisualLearning\n\n"
        f"© Happy Bear Kids 2026"
    )
    return {
        "title":       f"Learn the {shape_cap} Shape! 30 Minutes | Happy Bear Kids",
        "description": description,
        "tags": [
            "learn shapes", f"{shape} shape", "shapes for kids", "toddler learning",
            "baby education", "happy bear kids", "preschool", "shape recognition",
            "educational video", "30 minutes", shape, shape_cap, color_en,
            "one concept deep", "visual learning", "no talking", "calm baby video",
        ],
        "video_type": "shapes_long",
        "language":   "en",
        "is_short":   False,
        "status":     "public",
    }


def make_meta_ar(shape: str) -> dict:
    ar      = SHAPES_AR[shape]
    d       = SHAPES[shape]
    color_ar = d["color_ar"]

    description = (
        f"🔷 30 دقيقة من تعلم شكل {ar} للرضع والأطفال الصغار!\n\n"
        f"باستخدام طريقة \"التعمق في مفهوم واحد\" — نقضي 30 دقيقة كاملة "
        f"في استكشاف شكل واحد فقط: {ar}. "
        f"التكرار المتعدد يبني ذاكرة قوية للأشكال الهندسية.\n\n"
        f"ماذا يتعلم طفلك في هذا الفيديو:\n"
        f"🔷 الشكل — كيف يبدو {ar}؟ أين نجد {ar} في حياتنا؟\n"
        f"🎨 اللون — نفس شكل {ar} بألوان مختلفة وجميلة\n"
        f"🔢 العد — {ar} واحد، {ar}ان، ثلاث {ar}ات — عد بصري\n"
        f"✨ التأمل — رسوم متحركة هادئة بألوان قوس قزح، مثالية لوقت النوم\n\n"
        f"🌟 لماذا يُجدي هذا الفيديو:\n"
        f"• شكل واحد فقط — التركيز العميق يبني تعرفاً حقيقياً على الأشكال\n"
        f"• 30+ تكراراً — ليس مجرد لمحة سريعة\n"
        f"• بدون كلام أو نص — بصري بالكامل، مناسب لجميع اللغات!\n"
        f"• إيقاع هادئ — رائع كفيديو خلفية أثناء اللعب\n"
        f"• محتوى آمن وبدون إعلانات للأطفال من 0 إلى 3 سنوات\n"
        f"• مرحلة ألوان قوس قزح تساعد على تعلم الألوان من خلال الأشكال\n"
        f"• عد نقاط بصري — بدون ضغط، مجرد تعرض لطيف\n\n"
        f"جزء من سلسلة الأشكال الكاملة (8 أشكال):\n"
        f"دائرة · مربع · مثلث · نجمة · معين · قلب · سداسي · بيضاوي\n\n"
        f"🔔 اشتركوا في هابي بير كيدز → @HappyBearKids1\n"
        f"فيديوهات تعليمية جديدة كل أسبوع!\n\n"
        f"🎵 الموسيقى الخلفية: Kevin MacLeod (incompetech.com)\n"
        f"رخصة Creative Commons Attribution 4.0\n"
        f"http://creativecommons.org/licenses/by/4.0/\n\n"
        f"#تعلم_الأشكال #{ar} #أشكال_للأطفال #تعليم_أطفال "
        f"#هابي_بير_كيدز #رياض_الأطفال #أشكال_هندسية #تعلم_بصري\n\n"
        f"© هابي بير كيدز 2026"
    )
    return {
        "title":       f"تعلم شكل {ar} | 30 دقيقة | هابي بير كيدز",
        "description": description,
        "tags": [
            "تعلم الأشكال", f"شكل {ar}", "أشكال للأطفال", "تعليم أطفال",
            "هابي بير كيدز", "رياض الأطفال", "أشكال هندسية", "تعلم بصري",
            "30 دقيقة", ar, color_ar, "فيديو هادئ للأطفال", "رضع",
        ],
        "video_type": "shapes_long",
        "language":   "ar",
        "is_short":   False,
        "status":     "public",
    }


def make_meta_id(shape: str) -> dict:
    id_name  = SHAPES_ID[shape]
    d        = SHAPES[shape]
    color_en = d["color_en"]
    shape_cap = shape.capitalize()

    description = (
        f"🔷 30 menit belajar bentuk {id_name} untuk bayi dan balita!\n\n"
        f"Menggunakan metode \"Satu Konsep Mendalam\" — kita menghabiskan 30 menit penuh "
        f"untuk menjelajahi SATU bentuk: {id_name.capitalize()}. "
        f"Paparan berulang membangun memori bentuk yang tahan lama.\n\n"
        f"Apa yang dipelajari anak dalam video ini:\n"
        f"🔷 BENTUK — Seperti apa {id_name}? Di mana kita melihat {id_name}?\n"
        f"🎨 WARNA — {id_name.capitalize()} yang sama dalam berbagai warna indah\n"
        f"🔢 HITUNG — 1 {id_name}, 2 {id_name}, 3 {id_name} — menghitung visual\n"
        f"✨ HIPNO — Animasi warna yang menenangkan, sempurna untuk waktu tidur siang\n\n"
        f"🌟 Mengapa video ini berhasil:\n"
        f"• Satu bentuk saja — fokus mendalam membangun pengenalan bentuk nyata\n"
        f"• 30+ pengulangan — bukan hanya kilasan singkat\n"
        f"• Tanpa narasi atau teks — murni visual, cocok untuk semua bahasa!\n"
        f"• Tempo menenangkan — berfungsi sebagai video latar saat bermain\n"
        f"• Konten aman tanpa iklan untuk bayi usia 0–3 tahun\n"
        f"• Fase warna pelangi membantu mengajarkan warna melalui bentuk\n"
        f"• Hitung visual dengan titik — tanpa tekanan, paparan lembut\n\n"
        f"Bagian dari Seri Bentuk lengkap kami (8 bentuk):\n"
        f"Lingkaran · Persegi · Segitiga · Bintang · Belah Ketupat · Hati · Segi Enam · Oval\n\n"
        f"🔔 Subscribe → @happybearkidsin\n"
        f"Video edukatif baru setiap minggu!\n\n"
        f"🎵 Musik: Kevin MacLeod (incompetech.com)\n"
        f"Berlisensi Creative Commons Attribution 4.0\n"
        f"http://creativecommons.org/licenses/by/4.0/\n\n"
        f"#BelajarBentuk #Bentuk{id_name.replace(' ', '').capitalize()} #BentukUntukAnak "
        f"#BelajarAnak #VideoEdukasi #HappyBearKids #PresekolahIndonesia "
        f"#PengenalanBentuk #BelajarVisual\n\n"
        f"© Happy Bear Kids Indonesia 2026"
    )
    return {
        "title":       f"Belajar Bentuk {id_name.capitalize()}! 30 Menit | Happy Bear Kids Indonesia",
        "description": description,
        "tags": [
            "belajar bentuk", f"bentuk {id_name}", "bentuk untuk anak", "belajar anak",
            "video edukasi", "happy bear kids", "prasekolah", "pengenalan bentuk",
            "belajar visual", "30 menit", id_name, shape, color_en,
            "tanpa suara", "video tenang anak",
        ],
        "video_type": "shapes_long",
        "language":   "id",
        "is_short":   False,
        "status":     "public",
    }


def generate_thumbnail(shape: str, lang: str, out_path: Path) -> bool:
    if out_path.exists():
        return True
    if not TOGETHER_KEY_FILE.exists():
        print("    no Together.ai key")
        return False
    try:
        import requests as _req
    except ImportError:
        return False

    ar = SHAPES_AR[shape]
    d  = SHAPES[shape]
    color_en = d["color_en"]

    if lang == "ar":
        prompt = (
            f"Big bold cartoon {shape} shape, colorful rainbow colors, "
            f"Arabic kids educational YouTube thumbnail, bright vivid background, "
            f"cute friendly character style, bold outlines, no text, 1280x720, {STYLE_BASE}"
        )
    else:
        prompt = (
            f"Big bold cartoon {shape} shape in {color_en}, colorful rainbow colors, "
            f"educational kids YouTube thumbnail, bright vivid background, "
            f"cute friendly style, bold outlines, no text, 1280x720, {STYLE_BASE}"
        )

    print(f"    Generating thumbnail ({shape}/{lang})...")
    try:
        key = TOGETHER_KEY_FILE.read_text().strip()
        r = _req.post(TOGETHER_URL,
            headers={"Authorization": f"Bearer {key}"},
            json={"model": TOGETHER_MODEL, "prompt": prompt,
                  "width": 1280, "height": 720, "steps": 4, "n": 1},
            timeout=90)
        if r.status_code != 200:
            print(f"    Together error {r.status_code}")
            return False
        item = r.json()["data"][0]
        b64 = item.get("b64_json")
        if b64:
            img = base64.b64decode(b64)
        else:
            url = item.get("url", "")
            img = _req.get(url, timeout=30).content if url else None
        if not img:
            return False
        out_path.write_bytes(img)
        print(f"    thumb → {out_path.name} ({len(img)//1024}KB)")
        return True
    except Exception as e:
        print(f"    thumbnail failed: {e}")
        return False


def render_shape(shape: str, force: bool, dry_run: bool) -> Path | None:
    """Render one ShapeLearnLong video. Returns path to MP4 or None on failure."""
    d        = SHAPES[shape]
    fname    = f"shape_learn_{shape}_{DATE_STR}.mp4"
    # Canonical file lives in EN queue; AR queue gets a copy
    out_path = QUEUE_EN / fname

    if out_path.exists() and not force:
        sz = out_path.stat().st_size / 1024 / 1024
        print(f"  skip {fname} ({sz:.0f}MB)")
        return out_path

    music_idx = list(SHAPES.keys()).index(shape)
    music     = MUSIC_TRACKS[music_idx % len(MUSIC_TRACKS)]

    props = {
        "shapeName":  shape,
        "shapeColor": d["color"],
        "bgColor":    d["bg"],
        "musicFile":  music,
    }

    print(f"\n  Rendering {fname}...")
    print(f"    Shape: {shape} | Color: {d['color']} | Music: {music}")

    if dry_run:
        print(f"    [DRY RUN]")
        return out_path

    QUEUE_EN.mkdir(parents=True, exist_ok=True)
    cmd = [
        "npx", "remotion", "render",
        "src/index.ts", "ShapeLearnLong",
        str(out_path),
        "--props", json.dumps(props),
        "--concurrency", "1",
        "--log", "error",
    ]
    start  = time.time()
    result = subprocess.run(cmd, cwd=str(REMOTION),
                            capture_output=True, text=True, timeout=21600)

    if result.returncode == 0 and out_path.exists():
        elapsed = (time.time() - start) / 60
        sz = out_path.stat().st_size / 1024 / 1024
        print(f"    ✓ {sz:.0f}MB in {elapsed:.0f}min")
        return out_path
    else:
        print(f"    ✗ FAILED: {result.stderr[-300:]}")
        return None


def publish_to_both_channels(mp4_path: Path, shape: str, dry_run: bool):
    """Create meta+thumb for EN queue (in place) and copy+meta+thumb to AR and ID queues."""
    import shutil
    stem_en = mp4_path.stem  # e.g. shape_learn_circle_20260614

    # ── EN channel ───────────────────────────────────────────────────────────
    meta_en  = QUEUE_EN / f"meta_{stem_en}.yaml"
    thumb_en = QUEUE_EN / f"thumb_{stem_en}.png"

    if not meta_en.exists() or dry_run:
        meta = make_meta_en(shape)
        if not dry_run:
            with open(meta_en, "w") as f:
                yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            print(f"    meta EN → {meta_en.name}")
        else:
            print(f"    [DRY RUN] meta EN → {meta_en.name}")

    if not thumb_en.exists() and not dry_run:
        time.sleep(1)
        generate_thumbnail(shape, "en", thumb_en)

    # ── AR channel (copy MP4 + separate meta/thumb) ───────────────────────────
    QUEUE_AR.mkdir(parents=True, exist_ok=True)
    ar_name  = f"shape_learn_{shape}_ar_{DATE_STR}.mp4"
    mp4_ar   = QUEUE_AR / ar_name
    meta_ar  = QUEUE_AR / f"meta_{mp4_ar.stem}.yaml"
    thumb_ar = QUEUE_AR / f"thumb_{mp4_ar.stem}.png"

    if not mp4_ar.exists() and not dry_run:
        shutil.copy2(str(mp4_path), str(mp4_ar))
        print(f"    copy → {mp4_ar.name}")
    elif dry_run:
        print(f"    [DRY RUN] copy → {ar_name}")

    if not meta_ar.exists() or dry_run:
        meta = make_meta_ar(shape)
        if not dry_run:
            with open(meta_ar, "w") as f:
                yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            print(f"    meta AR → {meta_ar.name}")
        else:
            print(f"    [DRY RUN] meta AR → {meta_ar.name}")

    if not thumb_ar.exists() and not dry_run:
        time.sleep(1)
        generate_thumbnail(shape, "ar", thumb_ar)

    # ── ID channel (copy MP4 + separate meta/thumb) ───────────────────────────
    QUEUE_ID.mkdir(parents=True, exist_ok=True)
    id_name  = f"shape_learn_{shape}_id_{DATE_STR}.mp4"
    mp4_id   = QUEUE_ID / id_name
    meta_id  = QUEUE_ID / f"meta_{mp4_id.stem}.yaml"
    thumb_id = QUEUE_ID / f"thumb_{mp4_id.stem}.png"

    if not mp4_id.exists() and not dry_run:
        shutil.copy2(str(mp4_path), str(mp4_id))
        print(f"    copy → {mp4_id.name}")
    elif dry_run:
        print(f"    [DRY RUN] copy → {id_name}")

    if not meta_id.exists() or dry_run:
        meta = make_meta_id(shape)
        if not dry_run:
            with open(meta_id, "w") as f:
                yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            print(f"    meta ID → {meta_id.name}")
        else:
            print(f"    [DRY RUN] meta ID → {meta_id.name}")

    if not thumb_id.exists() and not dry_run:
        time.sleep(1)
        generate_thumbnail(shape, "id", thumb_id)


def regen_meta(shape_filter: str | None):
    """Regenerate meta+thumbnail for all existing shape_learn MP4s."""
    updated = 0
    for queue_dir, lang in [(QUEUE_EN, "en"), (QUEUE_AR, "ar"), (QUEUE_ID, "id")]:
        for mp4 in sorted(queue_dir.glob("shape_learn_*.mp4")):
            parts = mp4.stem.split("_")
            # stem: shape_learn_{shape}[_ar|_id]_{date}
            shape_key = parts[2] if len(parts) >= 4 else None
            if not shape_key or shape_key not in SHAPES:
                continue
            if shape_filter and shape_key != shape_filter:
                continue
            if "ar" in parts[3:]:
                file_lang = "ar"
            elif "id" in parts[3:]:
                file_lang = "id"
            else:
                file_lang = "en"
            if file_lang != lang:
                continue

            print(f"\n  Regen {mp4.name} ({lang})")
            if lang == "ar":
                meta = make_meta_ar(shape_key)
            elif lang == "id":
                meta = make_meta_id(shape_key)
            else:
                meta = make_meta_en(shape_key)
            meta_path = mp4.parent / f"meta_{mp4.stem}.yaml"
            with open(meta_path, "w") as f:
                yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            thumb_path = mp4.parent / f"thumb_{mp4.stem}.png"
            time.sleep(1)
            generate_thumbnail(shape_key, lang, thumb_path)
            updated += 1
    print(f"\nRegen done: {updated} files updated")


def main():
    parser = argparse.ArgumentParser(description="Generate ShapeLearnLong videos (EN+AR)")
    parser.add_argument("--shapes",     nargs="+", choices=list(SHAPES.keys()),
                        help="Specific shapes to generate (default: all 8)")
    parser.add_argument("--force",      action="store_true", help="Re-render existing")
    parser.add_argument("--dry-run",    action="store_true", help="Show what would run")
    parser.add_argument("--regen-meta", action="store_true",
                        help="Regenerate meta+thumbnail for existing MP4s only")
    parser.add_argument("--shape",      help="Single shape for --regen-meta filter")
    args = parser.parse_args()

    QUEUE_EN.mkdir(parents=True, exist_ok=True)
    QUEUE_AR.mkdir(parents=True, exist_ok=True)
    QUEUE_ID.mkdir(parents=True, exist_ok=True)

    if args.regen_meta:
        regen_meta(args.shape)
        return

    shapes = args.shapes or list(SHAPES.keys())
    print(f"\nShapeLearnLong — {len(shapes)} shapes × 3 channels (EN + AR + ID)\n")

    ok = 0
    for shape in shapes:
        mp4 = render_shape(shape, args.force, args.dry_run)
        if mp4 or args.dry_run:
            publish_to_both_channels(mp4 or QUEUE_EN / f"shape_learn_{shape}_{DATE_STR}.mp4",
                                     shape, args.dry_run)
            ok += 1
        time.sleep(2)

    print(f"\n=== Done: {ok}/{len(shapes)} shapes ===")
    en_ready = sum(1 for p in QUEUE_EN.glob("shape_learn_*.mp4") if (QUEUE_EN / f"thumb_{p.stem}.png").exists())
    ar_ready = sum(1 for p in QUEUE_AR.glob("shape_learn_*.mp4") if (QUEUE_AR / f"thumb_{p.stem}.png").exists())
    id_ready = sum(1 for p in QUEUE_ID.glob("shape_learn_*.mp4") if (QUEUE_ID / f"thumb_{p.stem}.png").exists())
    print(f"  EN queue: {en_ready} shape_learn ready")
    print(f"  AR queue: {ar_ready} shape_learn ready")
    print(f"  ID queue: {id_ready} shape_learn ready")


if __name__ == "__main__":
    main()
