#!/usr/bin/env python3
"""
Generate Sensory Loop abstract animation videos — 14 episodes.
Scenario: config/scenarios/sensory_loop_sensory_1_3.txt + sensory_loop_sensory_4_14.txt

Episodes 1-3:  Bouncing Balls, Pendulum Balls, Circular Motion
Episodes 4-14: Falling Stars, B&W Shapes, Expanding Circles, Checkerboard,
               Rainbow Spiral, Color Burst, Floating Bubbles, Dancing Fruits,
               Slow Float, Breathing Ball, Firefly Night

All pure SVG/code — no images needed (except ep.11 Dancing Fruits needs sprite assets).
No words → EN+AR+ID queues (30 min each).

Usage:
  python3 scripts/generate_sensory_loop.py               # all 14 videos
  python3 scripts/generate_sensory_loop.py --episode 1   # single episode
  python3 scripts/generate_sensory_loop.py --dry-run
"""
import argparse, json, subprocess, yaml
from datetime import datetime
from pathlib import Path

ROOT     = Path(__file__).resolve().parent.parent
REMOTION = ROOT / "remotion"
QUEUE_EN = ROOT / "output" / "queue"
QUEUE_AR = ROOT / "output" / "queue_ar"
QUEUE_ID = ROOT / "output" / "queue_id"
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
    "1":  {
        "name_en": "Bouncing Balls",     "name_ar": "كرات ترتد",         "name_id": "Bola Memantul",
        "bg": "#010108", "accent": "#FF5252", "bpm": 80, "music": "Monkeys Spinning Monkeys.mp3",
    },
    "2":  {
        "name_en": "Pendulum Balls",     "name_ar": "كرات البندول",      "name_id": "Bola Pendulum",
        "bg": "#010108", "accent": "#42A5F5", "bpm": 60, "music": "Gymnopedie No 1.mp3",
    },
    "3":  {
        "name_en": "Circular Motion",    "name_ar": "الحركة الدائرية",   "name_id": "Gerak Melingkar",
        "bg": "#010108", "accent": "#AB47BC", "bpm": 65, "music": "Crinoline Dreams.mp3",
    },
    "4":  {
        "name_en": "Falling Stars",      "name_ar": "النجوم الساقطة",    "name_id": "Bintang Jatuh",
        "bg": "#000005", "accent": "#FFD600", "bpm": 55, "music": "Heartwarming.mp3",
    },
    "5":  {
        "name_en": "Black and White Shapes", "name_ar": "أشكال بالأبيض والأسود", "name_id": "Bentuk Hitam Putih",
        "bg": "#000000", "accent": "#FFFFFF", "bpm": 70, "music": "Wholesome.mp3",
    },
    "6":  {
        "name_en": "Expanding Circles",  "name_ar": "دوائر متوسعة",     "name_id": "Lingkaran Meluas",
        "bg": "#010108", "accent": "#80DEEA", "bpm": 62, "music": "Carefree.mp3",
    },
    "7":  {
        "name_en": "Checkerboard",       "name_ar": "رقعة الشطرنج",     "name_id": "Papan Catur",
        "bg": "#000000", "accent": "#FFFFFF", "bpm": 75, "music": "Quirky Dog.mp3",
    },
    "8":  {
        "name_en": "Rainbow Spiral",     "name_ar": "الحلزون القوسي",   "name_id": "Spiral Pelangi",
        "bg": "#010108", "accent": "#FF4081", "bpm": 68, "music": "Pinball Spring.mp3",
    },
    "9":  {
        "name_en": "Color Burst",        "name_ar": "انفجار الألوان",   "name_id": "Ledakan Warna",
        "bg": "#000000", "accent": "#FFCA28", "bpm": 85, "music": "Hyperfun.mp3",
    },
    "10": {
        "name_en": "Floating Bubbles",   "name_ar": "فقاعات طافية",     "name_id": "Gelembung Mengambang",
        "bg": "#010310", "accent": "#64B5F6", "bpm": 55, "music": "Life of Riley.mp3",
    },
    "11": {
        "name_en": "Dancing Fruits",     "name_ar": "فواكه راقصة",      "name_id": "Buah Menari",
        "bg": "#000000", "accent": "#4CAF50", "bpm": 88, "music": "Happy Happy Game Show.mp3",
    },
    "12": {
        "name_en": "Slow Float",         "name_ar": "الطفو البطيء",     "name_id": "Melayang Pelan",
        "bg": "#010108", "accent": "#CE93D8", "bpm": 45, "music": "Gymnopedie No 1.mp3",
    },
    "13": {
        "name_en": "Breathing Ball",     "name_ar": "كرة التنفس",       "name_id": "Bola Napas",
        "bg": "#010108", "accent": "#80CBC4", "bpm": 48, "music": "Heartwarming.mp3",
    },
    "14": {
        "name_en": "Firefly Night",      "name_ar": "ليلة اليراعات",    "name_id": "Malam Kunang-kunang",
        "bg": "#000002", "accent": "#C5E1A5", "bpm": 50, "music": "Crinoline Dreams.mp3",
    },
}


def make_meta(ep_num, lang):
    ep   = EPISODES[ep_num]
    ch   = {'en': '@HappyBearKids1', 'ar': '@happybearkidsar', 'id': '@happybearkidsin'}
    name = ep[f'name_{lang}']

    if lang == 'en':
        return {
            "title": f"{name} | 30 Min Sensory Video for Babies | Happy Bear Kids",
            "description": (
                f"✨ {name} — soothing sensory video for babies and toddlers!\n\n"
                f"Episode {ep_num} of 14 in our Sensory Loop series — pure visual animation "
                f"designed to capture and hold baby's attention with beautiful, calming motion.\n\n"
                f"Pure code animation — no images needed, only smooth SVG shapes and gentle movement. "
                f"Designed with early childhood development principles:\n"
                f"• High contrast for young developing eyes\n"
                f"• Predictable rhythmic movement — calming and reassuring\n"
                f"• BPM {ep['bpm']} — perfectly paced music\n\n"
                f"🎯 Perfect for: sensory stimulation, tummy time, calming, background viewing\n"
                f"👶 Age: 0–12 months primarily, enjoyable up to 3 years\n"
                f"📺 30 minutes continuous\n"
                f"🌈 No language barriers — universal content\n\n"
                f"🔔 Subscribe → {ch['en']}\n"
                f"🎵 Kevin MacLeod (incompetech.com) — CC Attribution 4.0\n\n"
                f"#{name.replace(' ','')} #HappyBearKids #SensoryVideo "
                f"#BabyVisual #CalmBaby #TummyTime\n© Happy Bear Kids 2026"
            ),
            "tags": [ep_num, name.lower(), "sensory video", "baby visual", "happy bear kids",
                     "no talking", "calming baby", "30 minutes", "tummy time", "visual stimulation"],
            "video_type": "sensory_loop", "language": "en", "is_short": False, "status": "public",
        }
    elif lang == 'ar':
        return {
            "title": f"{name} | فيديو حسي للرضع 30 دقيقة | هابي بير كيدز",
            "description": (
                f"✨ {name} — فيديو حسي مريح للرضع والأطفال الصغار!\n\n"
                f"الحلقة {ep_num} من 14 في سلسلة الحلقة الحسية — رسوم متحركة بصرية خالصة "
                f"مصممة لجذب انتباه الرضيع والحفاظ عليه بحركة جميلة هادئة.\n\n"
                f"رسوم متحركة خالصة بالكود — بدون صور، فقط أشكال SVG سلسة وحركة هادئة.\n\n"
                f"🔔 اشتركوا → {ch['ar']}\n"
                f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
                f"#{name.replace(' ','_')} #هابي_بير_كيدز #فيديو_حسي "
                f"#تحفيز_بصري\n© هابي بير كيدز 2026"
            ),
            "tags": [ep_num, name, "فيديو حسي", "هابي بير كيدز", "تحفيز بصري", "بدون كلام"],
            "video_type": "sensory_loop", "language": "ar", "is_short": False, "status": "public",
        }
    else:
        return {
            "title": f"{name} | 30 Menit Video Sensorik untuk Bayi | Happy Bear Kids",
            "description": (
                f"✨ {name} — video sensorik yang menenangkan untuk bayi dan balita!\n\n"
                f"Episode {ep_num} dari 14 dalam seri Sensory Loop kami — animasi visual murni "
                f"yang dirancang untuk menarik dan mempertahankan perhatian bayi dengan gerakan indah yang menenangkan.\n\n"
                f"Animasi kode murni — tidak perlu gambar, hanya bentuk SVG yang halus dan gerakan lembut. "
                f"Dirancang dengan prinsip pengembangan anak usia dini:\n"
                f"• Kontras tinggi untuk mata bayi yang sedang berkembang\n"
                f"• Gerakan ritmis yang dapat diprediksi — menenangkan dan meyakinkan\n"
                f"• BPM {ep['bpm']} — musik berpace sempurna\n\n"
                f"🔔 Subscribe → {ch['id']}\n"
                f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
                f"#{name.replace(' ','')} #HappyBearKids #VideoSensorik "
                f"#StimulasiVisual\n© Happy Bear Kids Indonesia 2026"
            ),
            "tags": [ep_num, name.lower(), "video sensorik", "stimulasi visual",
                     "happy bear kids", "tanpa suara", "30 menit"],
            "video_type": "sensory_loop", "language": "id", "is_short": False, "status": "public",
        }


def process_episode(ep_num, ep_idx, dry_run, regen_meta):
    ep   = EPISODES[ep_num]
    slug = ep['name_en'].lower().replace(' ', '_').replace('&', 'and')
    name = f"sensory_{ep_num:0>2}_{slug}_{DATE_STR}.mp4"
    ok   = True

    for lang, queue in [("en", QUEUE_EN), ("ar", QUEUE_AR), ("id", QUEUE_ID)]:
        out_mp4    = queue / name
        lang_music = alt_music(ep["music"], ep_idx, lang)
        props = {
            "shapes": ["circle", "star", "square"],
            "colors": [ep["accent"], "#FFFFFF", ep["accent"]],
            "bgColor": ep["bg"], "bpm": ep["bpm"],
            "showLabels": False, "musicFile": lang_music,
        }
        if not out_mp4.exists() and not dry_run and not regen_meta:
            cmd = ["npx", "remotion", "render", "ShapeDanceLong",
                   f"--props={json.dumps(props)}", f"--output={str(out_mp4)}"]
            print(f"  Render ({lang}): {out_mp4.name}")
            r = subprocess.run(cmd, cwd=str(REMOTION), timeout=21600)
            if r.returncode != 0:
                print(f"  FAILED ({lang})")
                ok = False
                continue

        mp = queue / f"meta_{Path(name).stem}.yaml"
        if not mp.exists() or regen_meta:
            meta = make_meta(ep_num, lang)
            if not dry_run:
                with open(mp, 'w', encoding='utf-8') as f:
                    yaml.dump(meta, f, allow_unicode=True)
            print(f"  Meta ({lang}): {mp.name}")

    return ok


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--key',        default=None, help='orchestrator key e.g. sensory_1_3 or sensory_4_14')
    parser.add_argument('--episode',    default=None, choices=list(EPISODES))
    parser.add_argument('--dry-run',    action='store_true')
    parser.add_argument('--regen-meta', action='store_true')
    args = parser.parse_args()

    # Support key-based filtering for orchestrator
    if args.episode:
        episodes = [args.episode]
    elif args.key == 'sensory_1_3':
        episodes = ['1', '2', '3']
    elif args.key == 'sensory_4_14':
        episodes = [str(i) for i in range(4, 15)]
    else:
        episodes = list(EPISODES)

    print(f"=== Sensory Loop — {len(episodes)} episodes ===")

    ep_keys = list(EPISODES.keys())
    done = 0
    for ep_num in episodes:
        ep = EPISODES[ep_num]
        ep_idx = ep_keys.index(ep_num)
        print(f"\n[Episode {ep_num}] {ep['name_en']}")
        if process_episode(ep_num, ep_idx, args.dry_run, args.regen_meta):
            done += 1

    print(f"\n=== Done: {done}/{len(episodes)} ===")


if __name__ == '__main__':
    main()
