#!/usr/bin/env python3
"""
Generate OCD Vehicles series — 6 calming vehicle-themed shape dance videos, 30 min, no text.
Uses ShapeDanceLong Remotion composition with vehicle-inspired color palettes.
No text → EN+AR+ID (1 render, 3 queues).

Usage:
  python3 scripts/generate_ocd_vehicles.py
  python3 scripts/generate_ocd_vehicles.py --regen-meta
"""
import argparse, base64, json, subprocess, yaml
from datetime import datetime
from pathlib import Path
import requests

ROOT     = Path(__file__).resolve().parent.parent
REMOTION = ROOT / "remotion"
QUEUE_EN = ROOT / "output" / "queue"
QUEUE_AR = ROOT / "output" / "queue_ar"
QUEUE_ID = ROOT / "output" / "queue_id"
TOGETHER_KEY_FILE = ROOT / "credentials" / "together_api_key.txt"
TOGETHER_URL      = "https://api.together.xyz/v1/images/generations"
DATE_STR = datetime.now().strftime("%Y%m%d")

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

EPISODES = {
    "cars": {
        "shapes": ["circle", "square", "diamond"],
        "colors": ["#FF3333", "#3366FF", "#FFCC00", "#FF6633"],
        "bgColor": "#080810", "bpm": 72,
        "music": "Happy Happy Game Show.mp3",
        "thumb_prompt": "cute cartoon toy cars bouncing and dancing in a row, red blue yellow cars, dark background, toddler animation",
    },
    "trains": {
        "shapes": ["square", "hexagon", "diamond"],
        "colors": ["#CC2222", "#888888", "#AAAAAA", "#FFD700"],
        "bgColor": "#050508", "bpm": 65,
        "music": "Wholesome.mp3",
        "thumb_prompt": "cute cartoon toy trains moving in a circle, red silver gold colors, dark background, baby animation, railway shapes",
    },
    "planes": {
        "shapes": ["triangle", "diamond", "star"],
        "colors": ["#87CEEB", "#FFFFFF", "#4169E1", "#C0C0C0"],
        "bgColor": "#010510", "bpm": 78,
        "music": "Carefree.mp3",
        "thumb_prompt": "cute cartoon toy planes flying in a circle, sky blue white silver colors, dark background, kids animation",
    },
    "boats": {
        "shapes": ["oval", "circle", "hexagon"],
        "colors": ["#006994", "#00BFFF", "#FF4500", "#FFFFFF"],
        "bgColor": "#010810", "bpm": 60,
        "music": "Pinball Spring.mp3",
        "thumb_prompt": "cute cartoon toy boats sailing in a round dance, ocean blue white orange, dark background, soothing toddler animation",
    },
    "buses": {
        "shapes": ["square", "circle", "star"],
        "colors": ["#FFD700", "#FF8C00", "#333333", "#FFFFFF"],
        "bgColor": "#0A0800", "bpm": 82,
        "music": "Quirky Dog.mp3",
        "thumb_prompt": "cute cartoon school buses bouncing and dancing, bright yellow orange colors, dark background, fun kids animation",
    },
    "vehicles_mix": {
        "shapes": ["circle", "square", "triangle", "star", "diamond"],
        "colors": ["#FF3333", "#3366FF", "#FFD700", "#00AA44", "#FF6600"],
        "bgColor": "#050505", "bpm": 88,
        "music": "Monkeys Spinning Monkeys.mp3",
        "thumb_prompt": "cute cartoon vehicles cars buses trains planes boats all dancing together, rainbow colors, dark background, exciting toddler animation",
    },
}

TITLE_EN = "🚗 {name} | 30 Minutes | Happy Bear Kids"
TITLE_AR = "🚗 {name_ar} | ٣٠ دقيقة | Happy Bear Kids"
TITLE_ID = "🚗 {name_id} | 30 Menit | Happy Bear Kids"

TITLES_AR = {
    "cars": "سيارات تتحرك!",
    "trains": "قطارات رائعة",
    "planes": "طائرات ترقص",
    "boats": "قوارب تمرح",
    "buses": "حافلات مرحة",
    "vehicles_mix": "كل المركبات",
}
TITLES_ID = {
    "cars": "Mobil-Mobil Menari!",
    "trains": "Kereta Luar Biasa",
    "planes": "Pesawat Berdansa",
    "boats": "Kapal Bermain",
    "buses": "Bus yang Ceria",
    "vehicles_mix": "Semua Kendaraan",
}
TITLES_EN = {
    "cars": "Cars Dance Party",
    "trains": "Amazing Trains",
    "planes": "Planes in the Sky",
    "boats": "Boats on the Water",
    "buses": "Busy Buses",
    "vehicles_mix": "All Vehicles Party",
}

DESC_EN = """\
Welcome to Happy Bear Kids! 🐻

30 minutes of fun {name} for babies and toddlers! Watch as colourful shapes bounce, \
spin and dance in calming, satisfying patterns — inspired by {name_lower}!

Our OCD Vehicles series is designed to captivate babies and young children with vivid, \
moving colours and soothing rhythmic motion. Pure visual joy for little eyes!

🌟 Key features:
• Vehicle-inspired colour themes in constant, rhythmic motion
• Perfect visual stimulation for babies aged 0-3 years
• Calming yet engaging — great for focus and relaxation
• No words, no voices — universally enjoyable for every child
• Upbeat background music that supports brain development
• 30 full minutes of uninterrupted visual joy

👶 Great for:
• Tummy time — high-contrast shapes support visual tracking
• Calm play — shapes and colours spark curiosity
• Background entertainment during feeding or rest
• Toddlers who love cars, trains, planes and vehicles

🎯 Educational value:
• Colour recognition — learn vehicle colours
• Shape awareness through vehicle-inspired forms
• Pattern and rhythm recognition
• Visual tracking and focus development

🎵 Music by Kevin MacLeod (incompetech.com)
Licensed under Creative Commons: By Attribution 4.0 License
http://creativecommons.org/licenses/by/4.0/

© Happy Bear Kids 2026 — All rights reserved
New videos every week! Subscribe ▶ @HappyBearKids1

#HappyBearKids #VehiclesForKids #{tag} #KidsAnimation #BabyVideo #ToddlerVideo \
#CarsForKids #TrainsForKids #VisualLearning #30Minutes"""

DESC_AR = """\
أهلاً بكم في Happy Bear Kids! 🐻

٣٠ دقيقة كاملة من الأشكال الملوّنة المستوحاة من المركبات! شاهد ألوان رائعة تتحرك وترقص \
في أنماط هادئة ومثيرة — مثالية للأطفال الرضّع والصغار.

🌟 المميزات الرئيسية:
• ألوان مستوحاة من المركبات في حركة إيقاعية مستمرة
• تحفيز بصري مثالي للأطفال من ٠ إلى ٣ سنوات
• بدون كلمات أو أصوات — مناسب لجميع الأطفال
• موسيقى خلفية مرحة
• ٣٠ دقيقة متواصلة من المتعة البصرية

🎯 القيمة التعليمية:
• التعرف على ألوان المركبات
• الوعي بالأشكال الهندسية
• التعرف على الأنماط والإيقاع

🎵 موسيقى Kevin MacLeod (incompetech.com)
ترخيص Creative Commons: النسب 4.0
© Happy Bear Kids 2026 — جميع الحقوق محفوظة
اشترك ▶ @happybearkidsar

#HappyBearKids #مركبات_للأطفال #سيارات #فيديو_أطفال #تعليم_الأطفال"""

DESC_ID = """\
Selamat datang di Happy Bear Kids! 🐻

30 menit penuh warna-warni bertema kendaraan yang menari! Saksikan bentuk-bentuk \
berwarna-warni bergerak dan berdansa dalam pola yang menenangkan dan menyenangkan!

🌟 Fitur utama:
• Tema warna kendaraan dalam gerakan ritmis yang terus-menerus
• Stimulasi visual sempurna untuk bayi usia 0-3 tahun
• Tanpa kata-kata atau suara — cocok untuk semua anak
• Musik latar yang ceria mendukung perkembangan otak
• 30 menit penuh kesenangan visual tanpa gangguan

🎯 Nilai edukatif:
• Pengenalan warna kendaraan
• Kesadaran bentuk geometris
• Pengenalan pola dan ritme

🎵 Musik oleh Kevin MacLeod (incompetech.com)
Lisensi Creative Commons: Atribusi 4.0
© Happy Bear Kids 2026 — Hak cipta dilindungi
Subscribe ▶ @happybearkidsin

#HappyBearKids #KendaraanAnak #MobilAnak #AnimasiAnak #VideoBalita"""

TAGS_EN = {
    "cars": ["cars for kids", "toy cars", "cars dance"],
    "trains": ["trains for kids", "toy trains", "train dance"],
    "planes": ["planes for kids", "airplanes", "plane dance"],
    "boats": ["boats for kids", "ships", "boat dance"],
    "buses": ["buses for kids", "school bus", "bus dance"],
    "vehicles_mix": ["vehicles for kids", "transport", "vehicles dance"],
}


def generate_thumbnail(ep_key, ep, queue, out_name, lang):
    thumb_path = queue / f"thumb_{Path(out_name).stem}.png"
    if thumb_path.exists():
        return True
    if not TOGETHER_KEY_FILE.exists():
        return False
    api_key = TOGETHER_KEY_FILE.read_text().strip()
    prompt = ep["thumb_prompt"]
    if lang == "ar":
        prompt += ", no text, no letters, no words, no numbers"
    try:
        resp = requests.post(TOGETHER_URL, headers={
            "Authorization": f"Bearer {api_key}", "Content-Type": "application/json"
        }, json={
            "model": "black-forest-labs/FLUX.1-schnell",
            "prompt": prompt, "width": 1280, "height": 720,
            "steps": 4, "n": 1, "response_format": "b64_json",
        }, timeout=60)
        if resp.status_code != 200:
            print(f"  thumb error {resp.status_code}: {resp.text[:100]}")
            return False
        data = resp.json()["data"][0]["b64_json"]
        thumb_path.write_bytes(base64.b64decode(data))
        print(f"  thumb → {thumb_path.name}")
        return True
    except Exception as e:
        print(f"  thumb error: {e}")
        return False


def make_meta(ep_key, ep_num, lang, queue, out_name):
    name_en = TITLES_EN.get(ep_key, ep_key.replace("_", " ").title())
    name_ar = TITLES_AR.get(ep_key, ep_key)
    name_id = TITLES_ID.get(ep_key, ep_key)
    tag = ep_key.replace("_", "").title()

    if lang == "en":
        title = TITLE_EN.format(name=name_en)
        desc  = DESC_EN.format(name=name_en, name_lower=name_en.lower(), tag=tag)
        tags  = ["vehicles for kids", "ocd vehicles", "kids animation", "baby video",
                 "happy bear kids", "30 minutes", "toddler", "visual stimulation",
                 "calming for kids", "transport"] + TAGS_EN.get(ep_key, [])
    elif lang == "ar":
        title = TITLE_AR.format(name_ar=name_ar)
        desc  = DESC_AR
        tags  = ["مركبات للأطفال", "سيارات", "فيديو أطفال", "happy bear kids",
                 "تعليم الأطفال", "ترفيه", "أطفال"]
    else:
        title = TITLE_ID.format(name_id=name_id)
        desc  = DESC_ID
        tags  = ["kendaraan anak", "mobil anak", "animasi anak", "happy bear kids",
                 "video balita", "belajar warna", "hiburan anak"]

    meta = {
        "title": title, "description": desc,
        "video_type": "ocd_vehicles", "theme": "vehicles",
        "language": lang, "duration_minutes": 30,
        "is_short": False, "status": "public",
        "tags": tags,
    }
    meta_path = queue / f"meta_{Path(out_name).stem}.yaml"
    with open(meta_path, "w", encoding="utf-8") as f:
        yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def render_episode(ep_key, ep, ep_num, ep_idx, dry_run, regen_meta):
    out_name = f"ocd_vehicles_{ep_key}_{DATE_STR}.mp4"
    ok = True

    for lang, queue in [("en", QUEUE_EN), ("ar", QUEUE_AR), ("id", QUEUE_ID)]:
        out_mp4    = queue / out_name
        lang_music = alt_music(ep["music"], ep_idx, lang)
        if out_mp4.exists() and not regen_meta:
            print(f"  SKIP {ep_key} ({lang}, exists)")
        elif not dry_run and not regen_meta:
            props = {
                "shapes": ep["shapes"], "colors": ep["colors"],
                "bgColor": ep["bgColor"], "bpm": ep["bpm"],
                "showLabels": False, "musicFile": lang_music,
            }
            cmd = ["npx", "remotion", "render", "ShapeDanceLong",
                   f"--props={json.dumps(props)}", f"--output={str(out_mp4)}",
                   "--log=error"]
            print(f"  Rendering {ep_key} ({lang}, 30 min)...", flush=True)
            r = subprocess.run(cmd, cwd=str(REMOTION), timeout=86400)
            if r.returncode != 0 or not out_mp4.exists():
                print(f"  FAILED render: {ep_key} ({lang})")
                ok = False
                continue
            print(f"  ✓ {out_name} ({out_mp4.stat().st_size/1024/1024:.1f}MB)")

        if out_mp4.exists() or dry_run:
            if not dry_run:
                make_meta(ep_key, ep_num, lang, queue, out_name)
                generate_thumbnail(ep_key, ep, queue, out_name, lang)
            else:
                print(f"  [dry] meta+thumb {lang}")

    return ok


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run",    action="store_true")
    parser.add_argument("--regen-meta", action="store_true")
    args = parser.parse_args()

    for d in (QUEUE_EN, QUEUE_AR, QUEUE_ID):
        d.mkdir(parents=True, exist_ok=True)

    print(f"\n=== OCD Vehicles: {len(EPISODES)} episodes → EN+AR+ID ===\n")
    ok = 0
    for ep_num, (ep_key, ep) in enumerate(EPISODES.items(), 1):
        print(f"[{ep_num}/{len(EPISODES)}] {ep_key}")
        if render_episode(ep_key, ep, ep_num, ep_num - 1, args.dry_run, args.regen_meta):
            ok += 1
    print(f"\nDone: {ok}/{len(EPISODES)} episodes")


if __name__ == "__main__":
    main()
