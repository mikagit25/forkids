#!/usr/bin/env python3
"""
Generate DanceShape videos — 12 abstract shape dance videos (no text, no voice).
Based on scenario: config/scenarios/dance_shape.txt

12 videos × 25 min, no text → publish to EN + AR + ID with separate meta.

Usage:
  python3 scripts/generate_dance_shape.py                  # all 12
  python3 scripts/generate_dance_shape.py --keys 1 4 7     # specific videos by number
  python3 scripts/generate_dance_shape.py --dry-run
  python3 scripts/generate_dance_shape.py --regen-meta
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

DATE_STR = datetime.now().strftime("%Y%m%d")
FPS      = 30
DURATION = 25 * 60  # 25 minutes

# 12 videos as defined in dance_shape.txt scenario
VIDEOS = {
    "1_circle":      {"shapes": ["circle"],                               "colors": ["#FF2222"],                                 "bg": "#0A1628", "bpm": 70,  "name_en": "One Circle", "name_ar": "دائرة واحدة",         "name_id": "Satu Lingkaran"},
    "2_circles":     {"shapes": ["circle", "circle", "circle"],           "colors": ["#FF2222", "#2255FF", "#FFDD00"],           "bg": "#0A1628", "bpm": 80,  "name_en": "Three Circles", "name_ar": "ثلاث دوائر",        "name_id": "Tiga Lingkaran"},
    "3_wave_circles":{"shapes": ["circle","circle","circle","circle"],    "colors": ["#FF2222","#FF8800","#FFDD00","#22CC44"],   "bg": "#0A1628", "bpm": 75,  "name_en": "Circle Wave", "name_ar": "موجة الدوائر",         "name_id": "Gelombang Lingkaran"},
    "4_squares":     {"shapes": ["square", "square", "square", "square"], "colors": ["#2255FF","#E67E22","#8E44AD","#27AE60"],  "bg": "#050A1A", "bpm": 90,  "name_en": "Squares March", "name_ar": "مسيرة المربعات",    "name_id": "Pawai Kotak"},
    "5_triangles":   {"shapes": ["triangle", "triangle", "triangle"],     "colors": ["#27AE60", "#E91E63", "#F9A825"],          "bg": "#0A1628", "bpm": 80,  "name_en": "Triangles Dance", "name_ar": "رقصة المثلثات",   "name_id": "Tari Segitiga"},
    "6_mix_shapes":  {"shapes": ["circle", "square", "triangle"],         "colors": ["#2980B9", "#E74C3C", "#27AE60"],          "bg": "#0A1628", "bpm": 85,  "name_en": "Shapes Together", "name_ar": "الأشكال معاً",     "name_id": "Bentuk Bersama"},
    "7_aquarium":    {"shapes": ["circle","square","triangle","star"],     "colors": ["#FF4444","#27AE60","#2980B9","#F9A825"], "bg": "#05050F", "bpm": 65,  "name_en": "Shape Aquarium", "name_ar": "أكواريوم الأشكال",   "name_id": "Akuarium Bentuk"},
    "8_stars":       {"shapes": ["star", "star", "star"],                 "colors": ["#FFDD00", "#FF8800", "#FF4444"],          "bg": "#05050F", "bpm": 65,  "name_en": "Dancing Stars", "name_ar": "النجوم الراقصة",      "name_id": "Bintang Menari"},
    "9_hearts":      {"shapes": ["heart", "heart", "heart"],              "colors": ["#FF2255", "#FF6688", "#FFAACC"],          "bg": "#0A0015", "bpm": 60,  "name_en": "Dancing Hearts", "name_ar": "القلوب الراقصة",     "name_id": "Hati Menari"},
    "10_colors":     {"shapes": ["circle","circle","circle","circle"],    "colors": ["#FF2222","#FF8800","#FFDD00","#22CC44"],  "bg": "#0A1628", "bpm": 75,  "name_en": "Rainbow Circles", "name_ar": "دوائر قوس قزح",    "name_id": "Lingkaran Pelangi"},
    "11_big_small":  {"shapes": ["circle", "triangle"],                   "colors": ["#2255FF", "#FF4444"],                     "bg": "#0A1628", "bpm": 80,  "name_en": "Big and Small", "name_ar": "كبير وصغير",         "name_id": "Besar dan Kecil"},
    "12_night":      {"shapes": ["circle", "star", "heart"],              "colors": ["#7B9EC7", "#A3C4E0", "#D0E4F2"],          "bg": "#050A1A", "bpm": 55,  "name_en": "Night Shapes", "name_ar": "أشكال الليل",          "name_id": "Bentuk Malam"},
}

MUSIC_MAP = {
    "1_circle":      "Carefree.mp3",
    "2_circles":     "Quirky Dog.mp3",
    "3_wave_circles":"Merry Go.mp3",
    "4_squares":     "Hyperfun.mp3",
    "5_triangles":   "Wholesome.mp3",
    "6_mix_shapes":  "Happy Happy Game Show.mp3",
    "7_aquarium":    "Gymnopedie No 1.mp3",
    "8_stars":       "Pinball Spring.mp3",
    "9_hearts":      "Heartwarming.mp3",
    "10_colors":     "Life of Riley.mp3",
    "11_big_small":  "Monkeys Spinning Monkeys.mp3",
    "12_night":      "Crinoline Dreams.mp3",
}


def make_meta_en(key: str) -> dict:
    v    = VIDEOS[key]
    name = v["name_en"]
    desc = (
        f"✨ {name} — 25 minutes of mesmerizing shape animation for babies and toddlers!\n\n"
        f"Pure visual magic — colorful shapes dancing and moving to gentle music. "
        f"No words, no text — just beautiful shapes in motion. Perfect for any language!\n\n"
        f"🎯 Perfect for:\n"
        f"• Background video during play time\n"
        f"• Calming screen time that stimulates visual development\n"
        f"• Nap time wind-down\n"
        f"• Building shape and color recognition naturally\n\n"
        f"🌈 What your baby sees:\n"
        f"• Smooth, predictable motion patterns\n"
        f"• Beautiful color transitions\n"
        f"• Rhythmic movement synced to gentle music\n"
        f"• No flashing or sudden changes — safe for young eyes\n\n"
        f"Part of our Dancing Shapes Series — 12 hypnotic shape videos.\n"
        f"Each video focuses on different shapes, movements, and moods.\n\n"
        f"🔔 Subscribe → @HappyBearKids1 for weekly educational videos!\n\n"
        f"🎵 Music: Kevin MacLeod (incompetech.com)\n"
        f"Licensed under Creative Commons Attribution 4.0\n"
        f"http://creativecommons.org/licenses/by/4.0/\n\n"
        f"#ShapesForBabies #DancingShapes #BabyVisualStimulation #ToddlerTV "
        f"#HappyBearKids #CalmBabyVideo #ShapeAnimation #EducationalVideo "
        f"#BabyLearning #VisualStimulation #SafeKidsContent\n\n"
        f"© Happy Bear Kids 2026"
    )
    return {
        "title":       f"{name} | Shape Dance for Babies | 25 min | Happy Bear Kids",
        "description": desc,
        "tags": ["dancing shapes", "shapes for babies", "baby visual stimulation",
                 "shape animation", "calm baby video", "happy bear kids",
                 "toddler tv", "25 minutes", name.lower(), "no talking",
                 "visual learning", "baby background video", "colorful shapes"],
        "video_type": "dance_shape",
        "language":   "en",
        "is_short":   False,
        "status":     "public",
    }


def make_meta_ar(key: str) -> dict:
    v    = VIDEOS[key]
    name = v["name_ar"]
    desc = (
        f"✨ {name} — 25 دقيقة من الرسوم المتحركة الرائعة للأشكال للرضع والأطفال الصغار!\n\n"
        f"سحر بصري خالص — أشكال ملونة ترقص وتتحرك على موسيقى هادئة. "
        f"بدون كلمات أو نصوص — فقط أشكال جميلة في حركة. مناسبة لجميع اللغات!\n\n"
        f"🎯 مثالية لـ:\n"
        f"• فيديو خلفية أثناء وقت اللعب\n"
        f"• وقت الشاشة الهادئ الذي يحفز التطور البصري\n"
        f"• الاسترخاء قبل القيلولة\n"
        f"• بناء التعرف على الأشكال والألوان بشكل طبيعي\n\n"
        f"🌈 ما يراه طفلك:\n"
        f"• أنماط حركة سلسة ومتوقعة\n"
        f"• تحولات لونية جميلة\n"
        f"• حركة إيقاعية متزامنة مع موسيقى هادئة\n"
        f"• بدون وميض أو تغييرات مفاجئة — آمن للعيون الصغيرة\n\n"
        f"جزء من سلسلة أشكال الرقص — 12 فيديو ساحر للأشكال.\n\n"
        f"🔔 اشتركوا → @happybearkidsar لفيديوهات تعليمية أسبوعية!\n\n"
        f"🎵 الموسيقى: Kevin MacLeod (incompetech.com)\n"
        f"رخصة Creative Commons Attribution 4.0\n\n"
        f"#أشكال_للأطفال #رقص_الأشكال #تحفيز_بصري #هابي_بير_كيدز "
        f"#فيديو_هادئ #رسوم_أشكال #تعليم_أطفال #ألوان_للأطفال\n\n"
        f"© هابي بير كيدز 2026"
    )
    return {
        "title":       f"{name} | رقص الأشكال للرضع | 25 دقيقة | هابي بير كيدز",
        "description": desc,
        "tags": ["رقص الأشكال", "أشكال للأطفال", "تحفيز بصري", "هابي بير كيدز",
                 "فيديو هادئ للأطفال", "رسوم الأشكال", "تعليم أطفال",
                 "25 دقيقة", name, "بدون كلام", "تعلم بصري"],
        "video_type": "dance_shape",
        "language":   "ar",
        "is_short":   False,
        "status":     "public",
    }


def make_meta_id(key: str) -> dict:
    v    = VIDEOS[key]
    name = v["name_id"]
    desc = (
        f"✨ {name} — 25 menit animasi bentuk yang memukau untuk bayi dan balita!\n\n"
        f"Keajaiban visual murni — bentuk berwarna menari dan bergerak mengikuti musik lembut. "
        f"Tanpa kata-kata atau teks — hanya bentuk indah yang bergerak. Cocok untuk semua bahasa!\n\n"
        f"🎯 Sempurna untuk:\n"
        f"• Video latar saat waktu bermain\n"
        f"• Waktu layar yang menenangkan dan merangsang perkembangan visual\n"
        f"• Bersiap tidur siang\n"
        f"• Membangun pengenalan bentuk dan warna secara alami\n\n"
        f"🌈 Yang bayi Anda lihat:\n"
        f"• Pola gerakan yang halus dan dapat diprediksi\n"
        f"• Transisi warna yang indah\n"
        f"• Gerakan ritmis disinkronkan dengan musik lembut\n"
        f"• Tidak ada kilatan atau perubahan mendadak — aman untuk mata muda\n\n"
        f"Bagian dari Seri Bentuk Menari kami — 12 video bentuk hipnotis.\n\n"
        f"🔔 Subscribe → @happybearkidsin untuk video edukasi mingguan!\n\n"
        f"🎵 Musik: Kevin MacLeod (incompetech.com)\n"
        f"Berlisensi Creative Commons Attribution 4.0\n\n"
        f"#BentukUntukBayi #TariBentuk #StimulasiVisualBayi #HappyBearKids "
        f"#VideoTenangBayi #AnimasiBentuk #BelajarAnak #WarnaUntukAnak\n\n"
        f"© Happy Bear Kids Indonesia 2026"
    )
    return {
        "title":       f"{name} | Tari Bentuk untuk Bayi | 25 menit | Happy Bear Kids",
        "description": desc,
        "tags": ["tari bentuk", "bentuk untuk bayi", "stimulasi visual bayi",
                 "animasi bentuk", "video tenang bayi", "happy bear kids",
                 "25 menit", name.lower(), "tanpa suara", "belajar visual"],
        "video_type": "dance_shape",
        "language":   "id",
        "is_short":   False,
        "status":     "public",
    }


def generate_thumbnail(key: str, lang: str, out_path: Path) -> bool:
    if out_path.exists():
        return True
    if not TOGETHER_KEY_FILE.exists():
        return False
    try:
        import requests as _req
    except ImportError:
        return False

    v    = VIDEOS[key]
    name = v["name_en"]
    shapes_str = " and ".join(set(v["shapes"][:2]))
    prompt = (
        f"Colorful animated {shapes_str} shapes dancing and floating, "
        f"mesmerizing pattern, dark blue background with glowing neon shapes, "
        f"Pixar 3D style, children's YouTube thumbnail, "
        f"bright vivid colors, smooth render, no text, no letters, "
        f"beautiful abstract motion blur effect"
    )

    print(f"    Generating thumbnail ({key}/{lang})...")
    try:
        key_str = TOGETHER_KEY_FILE.read_text().strip()
        r = _req.post(TOGETHER_URL,
            headers={"Authorization": f"Bearer {key_str}"},
            json={"model": TOGETHER_MODEL, "prompt": prompt,
                  "width": 1280, "height": 720, "steps": 4, "n": 1},
            timeout=90)
        if r.status_code == 429:
            print("    Rate limit — waiting 30s...")
            time.sleep(30)
            r = _req.post(TOGETHER_URL,
                headers={"Authorization": f"Bearer {key_str}"},
                json={"model": TOGETHER_MODEL, "prompt": prompt,
                      "width": 1280, "height": 720, "steps": 4, "n": 1},
                timeout=90)
        if r.status_code != 200:
            print(f"    Together error {r.status_code}")
            return False
        item = r.json()["data"][0]
        b64  = item.get("b64_json")
        if b64:
            img = base64.b64decode(b64)
        else:
            url = item.get("url", "")
            img = _req.get(url, timeout=30).content if url else None
        if not img:
            return False
        out_path.write_bytes(img)
        print(f"    Thumbnail saved: {out_path.name}")
        time.sleep(15)
        return True
    except Exception as e:
        print(f"    Thumbnail error: {e}")
        return False


def write_meta(meta: dict, path: Path):
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(meta, f, allow_unicode=True, default_flow_style=False)


def render_video(key: str, out_mp4: Path, dry_run: bool) -> bool:
    v     = VIDEOS[key]
    music = MUSIC_MAP.get(key, "Carefree.mp3")
    props = {
        "shapes":     v["shapes"],
        "colors":     v["colors"],
        "bgColor":    v["bg"],
        "bpm":        v["bpm"],
        "showLabels": False,
        "musicFile":  music,
    }
    cmd = [
        "npx", "remotion", "render", "ShapeDanceLong",
        f"--props={json.dumps(props)}",
        f"--output={str(out_mp4)}",
        "--log=verbose",
    ]
    print(f"  Render: {out_mp4.name}")
    if dry_run:
        print(f"    DRY RUN — would run: {' '.join(cmd[:3])} ... --output={out_mp4.name}")
        return True
    result = subprocess.run(cmd, cwd=str(REMOTION), capture_output=False, timeout=7200)
    return result.returncode == 0


def process_key(key: str, dry_run: bool, regen_meta: bool):
    v    = VIDEOS[key]
    date = DATE_STR

    queues = {
        "en": QUEUE_EN,
        "ar": QUEUE_AR,
        "id": QUEUE_ID,
    }

    # Render single MP4 (no text → same for all channels)
    out_mp4 = QUEUE_EN / f"dance_shape_{key}_{date}.mp4"

    if not regen_meta:
        if out_mp4.exists():
            print(f"  Already exists: {out_mp4.name}")
        else:
            ok = render_video(key, out_mp4, dry_run)
            if not ok:
                print(f"  FAILED render: {key}")
                return False

    if dry_run and not regen_meta:
        # Still write meta for dry-run so they can be checked
        pass

    # Copy MP4 to AR and ID queues
    if not dry_run and out_mp4.exists():
        for lang in ["ar", "id"]:
            dest = queues[lang] / out_mp4.name
            if not dest.exists():
                import shutil
                shutil.copy2(str(out_mp4), str(dest))
                print(f"  Copied to {lang}: {dest.name}")

    # Write meta for each language
    for lang, q in queues.items():
        meta_path = q / f"meta_{out_mp4.stem}.yaml"
        if meta_path.exists() and not regen_meta:
            continue
        if lang == "en":
            meta = make_meta_en(key)
        elif lang == "ar":
            meta = make_meta_ar(key)
        else:
            meta = make_meta_id(key)
        if not dry_run:
            write_meta(meta, meta_path)
        print(f"  Meta ({lang}): {meta_path.name}")

    # Thumbnails (EN only — AR/ID use same image, different meta)
    for lang, q in queues.items():
        thumb_path = q / f"thumb_{out_mp4.stem}.png"
        if not thumb_path.exists() and not dry_run:
            generate_thumbnail(key, lang, thumb_path)

    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--keys",      nargs="*", default=None)
    parser.add_argument("--dry-run",   action="store_true")
    parser.add_argument("--regen-meta",action="store_true")
    args = parser.parse_args()

    all_keys = list(VIDEOS.keys())
    keys = args.keys if args.keys else all_keys

    # Validate keys
    for k in keys:
        if k not in VIDEOS:
            print(f"Unknown key: {k}. Valid: {all_keys}")
            sys.exit(1)

    print(f"=== Dance Shape Generator ===")
    print(f"Videos to generate: {keys}")

    for k in keys:
        v = VIDEOS[k]
        print(f"\n[{k}] {v['name_en']}")
        ok = process_key(k, args.dry_run, args.regen_meta)
        if not ok:
            print(f"  ERROR: {k} failed")


if __name__ == "__main__":
    main()
