#!/usr/bin/env python3
"""
generate_bubble_series.py — Multi-episode bubble color-learning series.

Each episode: single dominant bubble color on matching dark background, 22 min.
Composition: StarsBubblesLong with bubbleColors prop override.
Universal (no text): EN + AR + ID queues from one render.

Episodes:
  Solid colors: red, blue, green, yellow, orange, purple, pink, teal (×3 langs = 24 videos)
  Motion extra: swirl_blue, rain_purple, drift_rainbow               (×3 langs = 9  videos)
  Total: 33 videos

Usage:
  python3 scripts/generate_bubble_series.py                        # all episodes
  python3 scripts/generate_bubble_series.py --episodes red blue    # specific
  python3 scripts/generate_bubble_series.py --dry-run
  python3 scripts/generate_bubble_series.py --regen-meta           # meta+thumb only
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

ROOT      = Path(__file__).resolve().parent.parent
REMOTION  = ROOT / "remotion"
QUEUE_EN  = ROOT / "output" / "queue"
QUEUE_AR  = ROOT / "output" / "queue_ar"
QUEUE_ID  = ROOT / "output" / "queue_id"
TOGETHER_KEY_FILE = ROOT / "credentials" / "together_api_key.txt"
TOGETHER_URL   = "https://api.together.xyz/v1/images/generations"
TOGETHER_MODEL = "black-forest-labs/FLUX.1-schnell"
DATE_STR  = datetime.now().strftime("%Y%m%d")

_ALL_TRACKS = [
    "Carefree.mp3", "Crinoline Dreams.mp3", "Gymnopedie No 1.mp3",
    "Happy Happy Game Show.mp3", "Heartwarming.mp3", "Hyperfun.mp3",
    "Life of Riley.mp3", "Merry Go.mp3", "Monkeys Spinning Monkeys.mp3",
    "Overworld.mp3", "Pinball Spring.mp3", "Pixelland.mp3",
    "Quirky Dog.mp3", "Salty Ditty.mp3", "Sneaky Snitch.mp3",
    "Wholesome.mp3", "Fluffing a Duck.mp3", "Walking Along.mp3",
    "George Street Shuffle.mp3", "Circus of Freaks.mp3",
]

# ── Episode definitions ────────────────────────────────────────────────────────

# RGB tuples for bubbleColors prop — 4 shades of same hue for depth
EPISODES = {
    "red": {
        "bubble_rgb":   [[255, 80, 100], [255, 120, 130], [240, 60, 80], [255, 160, 170]],
        "bg_color":     "#140006",
        "motion":       "float_up",
        "music_en":     "Sneaky Snitch.mp3",
        "seed":         11,
        "thumb_scene":  "deep red glowing bubbles floating up in dark space, ruby red transparent spheres, magical glow, deep crimson background",
    },
    "blue": {
        "bubble_rgb":   [[80, 160, 255], [110, 190, 255], [60, 130, 220], [150, 210, 255]],
        "bg_color":     "#00061a",
        "motion":       "float_up",
        "music_en":     "Gymnopedie No 1.mp3",
        "seed":         22,
        "thumb_scene":  "glowing blue bubbles floating up in dark night sky, electric blue transparent spheres, sapphire glow, deep navy background",
    },
    "green": {
        "bubble_rgb":   [[60, 200, 120], [80, 220, 140], [40, 170, 100], [120, 240, 170]],
        "bg_color":     "#000f06",
        "motion":       "float_up",
        "music_en":     "Life of Riley.mp3",
        "seed":         33,
        "thumb_scene":  "glowing emerald green bubbles rising in dark space, jade transparent spheres, forest green glow, deep dark green background",
    },
    "yellow": {
        "bubble_rgb":   [[255, 230, 80], [255, 240, 120], [240, 210, 60], [255, 250, 160]],
        "bg_color":     "#0f0a00",
        "motion":       "float_up",
        "music_en":     "Happy Happy Game Show.mp3",
        "seed":         44,
        "thumb_scene":  "golden yellow glowing bubbles rising in dark amber space, sunny yellow transparent spheres, golden glow, deep dark amber background",
    },
    "orange": {
        "bubble_rgb":   [[255, 140, 40], [255, 160, 70], [240, 120, 30], [255, 190, 110]],
        "bg_color":     "#120600",
        "motion":       "float_up",
        "music_en":     "Carefree.mp3",
        "seed":         55,
        "thumb_scene":  "glowing orange bubbles floating up in dark space, tangerine transparent spheres, warm amber glow, deep dark brown-orange background",
    },
    "purple": {
        "bubble_rgb":   [[170, 80, 255], [190, 110, 255], [150, 60, 230], [210, 150, 255]],
        "bg_color":     "#08000f",
        "motion":       "float_up",
        "music_en":     "Crinoline Dreams.mp3",
        "seed":         66,
        "thumb_scene":  "glowing violet purple bubbles floating up in dark cosmic space, amethyst transparent spheres, purple glow, deep dark violet background",
    },
    "pink": {
        "bubble_rgb":   [[255, 120, 180], [255, 150, 200], [240, 100, 160], [255, 190, 220]],
        "bg_color":     "#10000a",
        "motion":       "float_up",
        "music_en":     "Heartwarming.mp3",
        "seed":         77,
        "thumb_scene":  "glowing rose pink bubbles floating in dark space, bubblegum pink transparent spheres, soft pink glow, deep dark magenta background",
    },
    "teal": {
        "bubble_rgb":   [[40, 210, 200], [60, 230, 220], [30, 180, 170], [100, 240, 235]],
        "bg_color":     "#000d0c",
        "motion":       "float_up",
        "music_en":     "Wholesome.mp3",
        "seed":         88,
        "thumb_scene":  "glowing teal cyan bubbles floating up in dark oceanic space, aquamarine transparent spheres, turquoise glow, deep dark teal background",
    },
    # Motion variants
    "swirl_blue": {
        "bubble_rgb":   [[80, 160, 255], [110, 190, 255], [60, 130, 220], [150, 210, 255]],
        "bg_color":     "#00061a",
        "motion":       "swirl",
        "music_en":     "Pixelland.mp3",
        "seed":         221,
        "thumb_scene":  "blue bubbles swirling in a spiral galaxy pattern in dark space, electric blue spheres orbiting in circles, cosmic blue glow",
    },
    "rain_purple": {
        "bubble_rgb":   [[170, 80, 255], [190, 110, 255], [150, 60, 230], [210, 150, 255]],
        "bg_color":     "#08000f",
        "motion":       "rain",
        "music_en":     "Quirky Dog.mp3",
        "seed":         332,
        "thumb_scene":  "purple bubbles falling like rain from above in dark space, violet transparent spheres descending gracefully, amethyst glow",
    },
    "drift_rainbow": {
        "bubble_rgb":   [[255, 80, 100], [80, 160, 255], [60, 200, 120], [255, 230, 80],
                         [170, 80, 255], [255, 140, 40]],
        "bg_color":     "#020C1B",
        "motion":       "drift",
        "music_en":     "Overworld.mp3",
        "seed":         443,
        "thumb_scene":  "rainbow colored bubbles drifting horizontally across dark space, colorful transparent spheres flowing sideways, magical rainbow glow",
    },
}

EPISODE_ORDER = [
    "red", "blue", "green", "yellow", "orange", "purple", "pink", "teal",
    "swirl_blue", "rain_purple", "drift_rainbow",
]

# ── Segment template (22 min = 1320 s) ────────────────────────────────────────

def make_segments(bg_color: str) -> list:
    return [
        {"startSec": 0,    "endSec": 30,   "mode": "intro",   "bgColor": bg_color},
        {"startSec": 30,   "endSec": 240,  "mode": "bubbles", "bubbleCount": 15},
        {"startSec": 240,  "endSec": 420,  "mode": "stars",   "starCount": 20, "shootRate": 6},
        {"startSec": 420,  "endSec": 510,  "mode": "calm",    "bubbleCount": 4, "starCount": 8},
        {"startSec": 510,  "endSec": 750,  "mode": "bubbles", "bubbleCount": 30},
        {"startSec": 750,  "endSec": 960,  "mode": "both",    "shootRate": 4},
        {"startSec": 960,  "endSec": 1050, "mode": "calm",    "bubbleCount": 3, "starCount": 18,
         "shootRate": 1, "bgColor": bg_color},
        {"startSec": 1050, "endSec": 1290, "mode": "finale",  "shootRate": 12},
        {"startSec": 1290, "endSec": 1320, "mode": "calm",    "bubbleCount": 1, "starCount": 3},
    ]

# ── Music helper ───────────────────────────────────────────────────────────────

def alt_music(en_music: str, ep_idx: int, lang: str) -> str:
    if lang == "en":
        return en_music
    offset = 7 if lang == "ar" else 14
    pool = [t for t in _ALL_TRACKS if t != en_music]
    return pool[(ep_idx + offset) % len(pool)]

# ── Meta ───────────────────────────────────────────────────────────────────────

COLOR_NAMES = {
    "red":          {"en": "Red",    "ar": "الأحمر",   "id": "Merah"},
    "blue":         {"en": "Blue",   "ar": "الأزرق",   "id": "Biru"},
    "green":        {"en": "Green",  "ar": "الأخضر",   "id": "Hijau"},
    "yellow":       {"en": "Yellow", "ar": "الأصفر",   "id": "Kuning"},
    "orange":       {"en": "Orange", "ar": "البرتقالي","id": "Oranye"},
    "purple":       {"en": "Purple", "ar": "البنفسجي", "id": "Ungu"},
    "pink":         {"en": "Pink",   "ar": "الوردي",   "id": "Merah Muda"},
    "teal":         {"en": "Teal",   "ar": "الزمردي",  "id": "Pirus"},
    "swirl_blue":   {"en": "Blue (Swirl)",  "ar": "الأزرق الدوامة",    "id": "Biru (Putaran)"},
    "rain_purple":  {"en": "Purple (Rain)", "ar": "البنفسجي المطر",    "id": "Ungu (Hujan)"},
    "drift_rainbow":{"en": "Rainbow (Drift)","ar":"قوس قزح المنجرف",   "id": "Pelangi (Hanyut)"},
}

def make_meta(ep_key: str, lang: str) -> dict:
    ch = {"en": "@HappyBearKids1", "ar": "@happybearkidsar", "id": "@happybearkidsin"}
    cname = COLOR_NAMES[ep_key][lang]

    if lang == "en":
        title = f"{cname} Bubbles | Color Learning | Happy Bear Kids"
        description = (
            f"✨ {cname} Bubbles — pure sensory magic for babies and toddlers!\n\n"
            f"Watch beautiful {cname.lower()} transparent bubbles float gently, twinkle, "
            f"and POP in a shower of sparkling light! 🫧\n\n"
            f"22 minutes of calm, captivating {cname.lower()} visual stimulation — perfect "
            f"for newborns, infants, and toddlers 0–3 years old.\n\n"
            f"🎨 COLOR LEARNING: Your baby's eyes are drawn to the beautiful {cname.lower()} "
            f"color throughout the video — an effortless way to introduce colors!\n\n"
            f"🫧 BUBBLES: Glowing {cname.lower()} transparent spheres rise, drift, and "
            f"burst into sparkling rings. Every pop is satisfying!\n\n"
            f"⭐ STARS: Twinkling stars pulse gently in the night sky. "
            f"Shooting stars streak across with glowing trails.\n\n"
            f"🎵 Soft, dreamlike music — gentle and calm, no sudden sounds.\n\n"
            f"🎯 Perfect for:\n"
            f"• Color recognition for babies\n"
            f"• Newborn visual tracking development\n"
            f"• Sensory stimulation 0–12 months\n"
            f"• Calming screen time for toddlers 1–3\n"
            f"• Background visuals during tummy time\n"
            f"• Winding down before nap or bedtime\n\n"
            f"No words, no text, no faces — universal visual content.\n\n"
            f"🔔 Subscribe for daily baby animations → {ch['en']}\n"
            f"🎵 Music: Kevin MacLeod (incompetech.com) — "
            f"Licensed under Creative Commons Attribution 4.0 (CC BY 4.0)\n\n"
            f"#{cname.replace(' ', '')}Bubbles #HappyBearKids #BabyColors #SensoryVideo "
            f"#ColorLearning #BabyVisual #BubblesPop #CalmBaby #NewbornVisual "
            f"#ToddlerTV #VisualStimulation #KevinMacLeod"
        )
        tags = [
            f"{cname.lower()} bubbles", "color learning", "baby colors", "sensory video",
            "baby visual", "bubbles pop", "calm baby", "newborn visual", "toddler tv",
            "visual stimulation", "happy bear kids", "baby animation",
        ]
    elif lang == "ar":
        title = f"فقاعات {cname} | تعلم الألوان | Happy Bear Kids"
        description = (
            f"✨ فقاعات {cname} — سحر حسي نقي للأطفال والرضع!\n\n"
            f"شاهد فقاعات {cname} الشفافة الجميلة تطفو بهدوء وتلمع وتنفجر "
            f"في شوارع من الضوء المتألق! 🫧\n\n"
            f"22 دقيقة من التحفيز البصري الهادئ والرائع بلون {cname} — مثالي "
            f"للمواليد الجدد والرضع والأطفال الصغار من 0 إلى 3 سنوات.\n\n"
            f"🎨 تعلم الألوان: تنجذب عيون طفلك إلى لون {cname} الجميل طوال الفيديو "
            f"— طريقة سهلة لتعريف الأطفال بالألوان!\n\n"
            f"🫧 الفقاعات: كرات شفافة بلون {cname} تتصاعد وتنفجر إلى حلقات متلألئة.\n\n"
            f"⭐ النجوم: نجوم متلألئة تنبض بلطف في سماء الليل.\n\n"
            f"🎯 مثالي لـ:\n"
            f"• التعرف على الألوان للأطفال\n"
            f"• تنمية التتبع البصري للمواليد\n"
            f"• التحفيز الحسي 0–12 شهرًا\n"
            f"• خلفية بصرية هادئة\n\n"
            f"بدون كلمات أو نصوص — محتوى عالمي.\n\n"
            f"🔔 اشترك → {ch['ar']}\n"
            f"🎵 الموسيقى: Kevin MacLeod — CC Attribution 4.0\n\n"
            f"#فقاعات_{cname.replace(' ', '_')} #HappyBearKids #تعلم_الألوان "
            f"#فيديو_الأطفال #تحفيز_حسي"
        )
        tags = [
            f"فقاعات {cname}", "تعلم الألوان", "فيديو الأطفال", "تحفيز حسي",
            "happy bear kids", "baby colors", "color learning",
        ]
    else:  # id
        title = f"Gelembung {cname} | Belajar Warna | Happy Bear Kids"
        description = (
            f"✨ Gelembung {cname} — keajaiban sensorik untuk bayi dan balita!\n\n"
            f"Saksikan gelembung transparan berwarna {cname.lower()} yang cantik melayang "
            f"dengan lembut, berkilau, dan MELEDAK dalam pancaran cahaya! 🫧\n\n"
            f"22 menit stimulasi visual warna {cname.lower()} yang menenangkan dan memukau "
            f"— sempurna untuk bayi baru lahir, bayi, dan balita usia 0–3 tahun.\n\n"
            f"🎨 BELAJAR WARNA: Mata bayi Anda tertarik pada warna {cname.lower()} "
            f"yang indah sepanjang video — cara mudah memperkenalkan warna!\n\n"
            f"🫧 GELEMBUNG: Bola transparan berwarna {cname.lower()} naik, melayang, "
            f"dan meledak menjadi cincin berkilau. Setiap ledakan memuaskan!\n\n"
            f"⭐ BINTANG: Bintang berkelip berdenyut lembut di langit malam. "
            f"Bintang jatuh melintas dengan jejak cahaya.\n\n"
            f"🎵 Musik lembut dan halus — tenang dan damai.\n\n"
            f"🎯 Sempurna untuk:\n"
            f"• Pengenalan warna untuk bayi\n"
            f"• Stimulasi visual bayi baru lahir\n"
            f"• Stimulasi sensorik 0–12 bulan\n"
            f"• Layar waktu yang menenangkan untuk balita\n"
            f"• Latar belakang visual\n\n"
            f"Tanpa kata-kata, teks, atau wajah — konten universal.\n\n"
            f"🔔 Subscribe → {ch['id']}\n"
            f"🎵 Musik: Kevin MacLeod (incompetech.com) — CC Attribution 4.0\n\n"
            f"#Gelembung{cname.replace(' ', '')} #HappyBearKids #BelajarWarna "
            f"#VideoBalita #StimulasiSensorik #KevinMacLeod"
        )
        tags = [
            f"gelembung {cname.lower()}", "belajar warna", "video bayi", "stimulasi sensorik",
            "happy bear kids", "baby colors", "color learning",
        ]

    return {
        "title":      title,
        "description": description,
        "tags":       tags,
        "language":   lang,
        "video_type": "stars_bubbles",
        "is_short":   False,
        "status":     "public",
    }

# ── Thumbnail ──────────────────────────────────────────────────────────────────

def _load_gat():
    import importlib.util
    spec = importlib.util.spec_from_file_location("gat", ROOT / "scripts" / "generate_ai_thumbs.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def gen_thumb(out_path: Path, prompt_en: str, lang: str) -> bool:
    key = TOGETHER_KEY_FILE.read_text().strip()
    no_text = "no text, no letters, no words, no numbers, " if lang == "ar" else ""
    full_prompt = (
        f"{prompt_en}, {no_text}dreamlike baby animation style, "
        f"glowing magical atmosphere, soft bokeh, beautiful 4K render"
    )
    try:
        gat = _load_gat()
        img = gat.together_generate_image(full_prompt, key)
        if img:
            out_path.write_bytes(gat.resize_to_720p(img))
            print(f"  ✓ thumb ({lang}): {out_path.name}")
            return True
        print(f"  ✗ thumb ({lang}) failed: API returned no image")
        return False
    except Exception as e:
        print(f"  ✗ thumb ({lang}) failed: {e}")
        return False

# ── Render ─────────────────────────────────────────────────────────────────────

def render_episode(ep_key: str, ep: dict, out_path: Path, lang: str,
                   ep_idx: int, dry_run: bool) -> bool:
    music = alt_music(ep["music_en"], ep_idx, lang)
    props = {
        "bgColor":      ep["bg_color"],
        "musicFile":    music,
        "volume":       0.18,
        "seed":         ep["seed"],
        "bubbleColors": ep["bubble_rgb"],
        "bubbleMotion": ep["motion"],
        "segments":     make_segments(ep["bg_color"]),
    }
    fps    = 30
    dur_s  = 1320  # 22 min
    frames = dur_s * fps

    cmd = [
        "npx", "remotion", "render",
        "StarsBubblesLong",
        str(out_path),
        f"--props={json.dumps(props)}",
        f"--frames=0-{frames - 1}",
        "--codec=h264",
        "--crf=23",
    ]
    print(f"\n  Render ({lang}): {out_path.name}")
    if dry_run:
        print(f"  [DRY RUN] cmd: {' '.join(cmd[:4])} ...")
        return True
    result = subprocess.run(cmd, cwd=str(REMOTION))
    return result.returncode == 0

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--episodes", nargs="+", choices=list(EPISODES.keys()),
                        default=EPISODE_ORDER, metavar="EP",
                        help="Which episodes to generate (default: all)")
    parser.add_argument("--dry-run",   action="store_true")
    parser.add_argument("--regen-meta", action="store_true",
                        help="Re-generate meta+thumbnail files only (skip render)")
    parser.add_argument("--force",     action="store_true",
                        help="Re-render even if output file exists")
    args = parser.parse_args()

    episodes = [k for k in args.episodes if k in EPISODES]
    total = len(episodes) * 3
    print(f"\nBubble series — {len(episodes)} episode(s) × 3 channels = {total} videos")
    if args.dry_run:
        print("DRY RUN mode")
    if args.regen_meta:
        print("REGEN META mode — skipping renders")

    for ep_idx, ep_key in enumerate(episodes):
        ep = EPISODES[ep_key]
        print(f"\n{'='*55}")
        print(f"Episode: {ep_key}  (motion={ep['motion']})")

        for lang, queue in [("en", QUEUE_EN), ("ar", QUEUE_AR), ("id", QUEUE_ID)]:
            stem     = f"bubbles_{ep_key}_{DATE_STR}_{lang}"
            mp4_path = queue / f"{stem}.mp4"
            meta_path= queue / f"meta_{stem}.yaml"
            thumb_path=queue / f"thumb_{stem}.png"

            # Render
            if not args.regen_meta:
                if mp4_path.exists() and not args.force:
                    print(f"  SKIP render ({lang}) — file exists")
                else:
                    ok = render_episode(ep_key, ep, mp4_path, lang, ep_idx, args.dry_run)
                    if not ok:
                        print(f"  ✗ render failed ({lang}), skipping meta/thumb")
                        continue
            else:
                if not mp4_path.exists():
                    print(f"  SKIP ({lang}) — no mp4 yet")
                    continue

            # Meta
            if not meta_path.exists() or args.regen_meta or args.force:
                if args.dry_run:
                    print(f"  [DRY RUN] would write meta ({lang})")
                else:
                    meta = make_meta(ep_key, lang)
                    with open(meta_path, "w") as f:
                        yaml.dump(meta, f, allow_unicode=True, default_flow_style=False)
                    print(f"  ✓ meta ({lang}): {meta_path.name}")
            else:
                print(f"  SKIP meta ({lang}) — exists")

            # Thumbnail
            if not thumb_path.exists() or args.regen_meta or args.force:
                if not args.dry_run:
                    gen_thumb(thumb_path, ep["thumb_scene"], lang)
                    time.sleep(1)
                else:
                    print(f"  [DRY RUN] would generate thumb ({lang})")
            else:
                print(f"  SKIP thumb ({lang}) — exists")

    print(f"\n{'='*55}")
    print("Bubble series generation complete.")
    print(f"Check queues:")
    print(f"  python3 scripts/publish_queue.py --dry-run --queue en --type long")


if __name__ == "__main__":
    main()
