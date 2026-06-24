#!/usr/bin/env python3
"""
Generate Construction & Music series — 6 videos, 30 min, no text.
Uses ShapeDanceLong Remotion composition with tool/instrument-inspired color palettes.
No text → EN+AR+ID (1 render, 3 queues).

Usage:
  python3 scripts/generate_construction_music.py
  python3 scripts/generate_construction_music.py --regen-meta
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
    "hammers": {
        "shapes": ["diamond", "square", "hexagon"],
        "colors": ["#FF8C00", "#CC6600", "#FFD700", "#8B4513"],
        "bgColor": "#080400", "bpm": 95,
        "music": "Quirky Dog.mp3",
        "thumb_prompt": "cute cartoon hammers and tools dancing rhythmically, orange brown gold colors, dark background, toddler animation",
    },
    "drums": {
        "shapes": ["circle", "oval", "hexagon"],
        "colors": ["#FF3333", "#8B0000", "#CC0000", "#FFD700"],
        "bgColor": "#0A0000", "bpm": 100,
        "music": "Hyperfun.mp3",
        "thumb_prompt": "cartoon drums and percussion instruments dancing with energy, red gold dark colors, dark background, exciting kids animation",
    },
    "guitars": {
        "shapes": ["oval", "diamond", "star"],
        "colors": ["#8B4513", "#CD853F", "#DEB887", "#FF6600"],
        "bgColor": "#050200", "bpm": 85,
        "music": "Merry Go.mp3",
        "thumb_prompt": "cute cartoon guitars and string instruments dancing, warm brown orange wood colors, dark background, music for toddlers",
    },
    "building": {
        "shapes": ["square", "triangle", "hexagon", "diamond"],
        "colors": ["#FFD700", "#FF8C00", "#4169E1", "#CC0000"],
        "bgColor": "#050505", "bpm": 90,
        "music": "Happy Happy Game Show.mp3",
        "thumb_prompt": "cartoon construction tools blocks shapes dancing and building, yellow orange blue red construction colors, dark background, baby animation",
    },
    "horns": {
        "shapes": ["oval", "triangle", "star"],
        "colors": ["#FFD700", "#DAA520", "#B8860B", "#FFF8DC"],
        "bgColor": "#030200", "bpm": 78,
        "music": "Wholesome.mp3",
        "thumb_prompt": "cute cartoon trumpets and brass instruments dancing, gold yellow gleaming colors, dark background, musical toddler animation",
    },
    "tools_music_mix": {
        "shapes": ["circle", "square", "triangle", "star", "hexagon"],
        "colors": ["#FF6600", "#FFD700", "#CC0000", "#4169E1", "#228B22"],
        "bgColor": "#030303", "bpm": 92,
        "music": "Monkeys Spinning Monkeys.mp3",
        "thumb_prompt": "cartoon tools and musical instruments all dancing together in celebration, rainbow colorful, dark background, vibrant kids animation",
    },
}

TITLE_EN = "🔨 {name} | 30 Minutes | Happy Bear Kids"
TITLE_AR = "🔨 {name_ar} | ٣٠ دقيقة | Happy Bear Kids"
TITLE_ID = "🔨 {name_id} | 30 Menit | Happy Bear Kids"

TITLES_EN = {
    "hammers":        "Hammers and Tools Dance",
    "drums":          "Drums Beat Dance Party",
    "guitars":        "Guitar Music Dance",
    "building":       "Building and Construction Dance",
    "horns":          "Horns and Trumpets Dance",
    "tools_music_mix":"Tools and Music Mix Party",
}
TITLES_AR = {
    "hammers":        "رقصة الأدوات والمطارق",
    "drums":          "حفلة الطبول",
    "guitars":        "رقصة الجيتار",
    "building":       "رقصة البناء والتشييد",
    "horns":          "رقصة الأبواق",
    "tools_music_mix":"مزيج الأدوات والموسيقى",
}
TITLES_ID = {
    "hammers":        "Palu dan Alat Berdansa",
    "drums":          "Pesta Drum yang Seru",
    "guitars":        "Tarian Gitar",
    "building":       "Tarian Bangunan dan Konstruksi",
    "horns":          "Tarian Terompet dan Tanduk",
    "tools_music_mix":"Campuran Alat dan Musik",
}

DESC_EN = """\
Welcome to Happy Bear Kids! 🐻

30 minutes of colourful {name} for babies and toddlers! Watch as vibrant shapes dance \
in {name_lower} inspired patterns — a wonderful treat for curious little minds!

Our Construction & Music series combines the excitement of tools and instruments with \
soothing, rhythmic visual motion. Perfect for babies who love sound and movement!

🌟 Key features:
• Tool and instrument inspired colour themes in constant, rhythmic motion
• Perfect visual stimulation for babies aged 0-3 years
• Calming yet engaging — great for focus and relaxation
• No words, no voices — universally enjoyable for every child
• Upbeat background music that supports brain development
• 30 full minutes of uninterrupted visual joy

👶 Great for:
• Tummy time — high-contrast shapes support visual tracking
• Calm play — shapes and colours spark curiosity
• Background entertainment during feeding or rest
• Toddlers who love building, music and rhythm

🎯 Educational value:
• Colour recognition — learn tool and instrument colours
• Shape awareness through geometric forms
• Pattern and rhythm recognition
• Visual tracking and focus development

🎵 Music by Kevin MacLeod (incompetech.com)
Licensed under Creative Commons: By Attribution 4.0 License
http://creativecommons.org/licenses/by/4.0/

© Happy Bear Kids 2026 — All rights reserved
New videos every week! Subscribe ▶ @HappyBearKids1

#HappyBearKids #ConstructionForKids #MusicForKids #KidsAnimation #BabyVideo \
#ToddlerVideo #ToolsForKids #30Minutes #VisualLearning #BabyDance"""

DESC_AR = """\
أهلاً بكم في Happy Bear Kids! 🐻

٣٠ دقيقة كاملة من ألوان الأدوات والموسيقى الراقصة! شاهد أشكالاً زاهية تتحرك وترقص \
في أنماط مستوحاة من أدوات البناء والآلات الموسيقية!

🌟 المميزات الرئيسية:
• ألوان مستوحاة من الأدوات والموسيقى في حركة إيقاعية مستمرة
• تحفيز بصري مثالي للأطفال من ٠ إلى ٣ سنوات
• بدون كلمات أو أصوات — مناسب لجميع الأطفال
• ٣٠ دقيقة متواصلة من المتعة البصرية

🎯 القيمة التعليمية:
• التعرف على الألوان والأشكال
• الوعي بالأنماط والإيقاع
• تنمية الانتباه والتركيز

🎵 موسيقى Kevin MacLeod (incompetech.com)
ترخيص Creative Commons: النسب 4.0
© Happy Bear Kids 2026 — جميع الحقوق محفوظة
اشترك ▶ @happybearkidsar

#HappyBearKids #أدوات_للأطفال #موسيقى_أطفال #فيديو_أطفال #تعليم"""

DESC_ID = """\
Selamat datang di Happy Bear Kids! 🐻

30 menit penuh warna-warni bertema alat dan musik yang menari! Saksikan bentuk-bentuk \
berwarna-warni bergerak dalam pola yang terinspirasi alat bangunan dan alat musik!

🌟 Fitur utama:
• Tema warna alat dan instrumen musik dalam gerakan ritmis
• Stimulasi visual sempurna untuk bayi usia 0-3 tahun
• Tanpa kata-kata atau suara — cocok untuk semua anak
• 30 menit penuh kesenangan visual tanpa gangguan

🎯 Nilai edukatif:
• Pengenalan warna dan bentuk
• Kesadaran pola dan ritme
• Pengembangan perhatian dan fokus

🎵 Musik oleh Kevin MacLeod (incompetech.com)
Lisensi Creative Commons: Atribusi 4.0
© Happy Bear Kids 2026 — Hak cipta dilindungi
Subscribe ▶ @happybearkidsin

#HappyBearKids #AlatAnak #MusikAnak #AnimasiAnak #VideoBalita"""


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
            "model": "black-forest-labs/FLUX.1-schnell-Free",
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

    if lang == "en":
        title = TITLE_EN.format(name=name_en)
        desc  = DESC_EN.format(name=name_en, name_lower=name_en.lower())
        tags  = ["construction for kids", "music for kids", "kids animation", "baby video",
                 "happy bear kids", "30 minutes", "toddler", "visual stimulation",
                 "tools for kids", "instruments for kids", "baby dance", "calming for kids"]
    elif lang == "ar":
        title = TITLE_AR.format(name_ar=name_ar)
        desc  = DESC_AR
        tags  = ["أدوات للأطفال", "موسيقى أطفال", "فيديو أطفال", "happy bear kids",
                 "تعليم الأطفال", "ترفيه", "رقص"]
    else:
        title = TITLE_ID.format(name_id=name_id)
        desc  = DESC_ID
        tags  = ["alat anak", "musik anak", "animasi anak", "happy bear kids",
                 "video balita", "hiburan anak", "konstruksi"]

    meta = {
        "title": title, "description": desc,
        "video_type": "construction_music", "theme": "tools",
        "language": lang, "duration_minutes": 30,
        "is_short": False, "status": "public",
        "tags": tags,
    }
    meta_path = queue / f"meta_{Path(out_name).stem}.yaml"
    with open(meta_path, "w", encoding="utf-8") as f:
        yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def render_episode(ep_key, ep, ep_num, ep_idx, dry_run, regen_meta):
    out_name = f"construction_music_{ep_key}_{DATE_STR}.mp4"
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

    print(f"\n=== Construction & Music: {len(EPISODES)} episodes → EN+AR+ID ===\n")
    ok = 0
    for ep_num, (ep_key, ep) in enumerate(EPISODES.items(), 1):
        print(f"[{ep_num}/{len(EPISODES)}] {ep_key}")
        if render_episode(ep_key, ep, ep_num, ep_num - 1, args.dry_run, args.regen_meta):
            ok += 1
    print(f"\nDone: {ok}/{len(EPISODES)} episodes")


if __name__ == "__main__":
    main()
