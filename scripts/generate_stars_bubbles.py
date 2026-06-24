#!/usr/bin/env python3
"""
generate_stars_bubbles.py — Stars and Bubbles sensory video.
1 video × 22 min → StarsBubblesLong composition → EN + AR + ID queues.

No text, no sprites — pure procedural bubbles + twinkling/shooting stars.
Universal content: same MP4 on all 3 channels.

Usage:
  python3 scripts/generate_stars_bubbles.py [--dry-run] [--force] [--regen-meta]
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

def alt_music(en_music: str, ep_idx: int, lang: str) -> str:
    if lang == "en":
        return en_music
    offset = 7 if lang == "ar" else 14
    pool = [t for t in _ALL_TRACKS if t != en_music]
    return pool[(ep_idx + offset) % len(pool)]

# ── Props for StarsBubblesLong ─────────────────────────────────────────────────

PROPS = {
    "bgColor":   "#020C1B",
    "musicFile": "Gymnopedie No 1.mp3",
    "volume":    0.18,
    "seed":      137,
    "segments": [
        # Intro: single bubble floats up
        {"startSec": 0,    "endSec": 30,   "mode": "intro",   "bgColor": "#020C1B"},
        # Act 1: single bubble adventures
        {"startSec": 30,   "endSec": 240,  "mode": "bubbles", "bubbleCount": 15},
        # Act 2: star show
        {"startSec": 240,  "endSec": 420,  "mode": "stars",   "starCount": 24, "shootRate": 8},
        # Calm 1: gentle float
        {"startSec": 420,  "endSec": 510,  "mode": "calm",    "bubbleCount": 4, "starCount": 6,
         "bgColor": "#040E20"},
        # Act 3: bubble party
        {"startSec": 510,  "endSec": 750,  "mode": "bubbles", "bubbleCount": 30},
        # Act 4: stars and bubbles together
        {"startSec": 750,  "endSec": 960,  "mode": "both",    "shootRate": 5},
        # Calm 2: night sky
        {"startSec": 960,  "endSec": 1050, "mode": "calm",    "bubbleCount": 3, "starCount": 20,
         "shootRate": 1, "bgColor": "#010810"},
        # Act 5: grand finale
        {"startSec": 1050, "endSec": 1290, "mode": "finale",  "shootRate": 14},
        # Outro: last star fades
        {"startSec": 1290, "endSec": 1320, "mode": "calm",    "bubbleCount": 1, "starCount": 3},
    ],
}

# ── Meta ───────────────────────────────────────────────────────────────────────

def make_meta(lang: str) -> dict:
    ch = {"en": "@HappyBearKids1", "ar": "@happybearkidsar", "id": "@happybearkidsin"}
    names = {
        "en": "Stars and Bubbles",
        "ar": "النجوم والفقاعات",
        "id": "Bintang dan Gelembung",
    }
    name = names[lang]

    if lang == "en":
        description = (
            f"✨ {name} — pure sensory magic for babies and toddlers!\n\n"
            f"Watch colorful transparent bubbles float gently upward, grow bigger and "
            f"bigger... then POP! ✨ While bubbles rise and pop, stars twinkle softly "
            f"across a deep night sky and shoot past in streaks of light.\n\n"
            f"22 minutes of captivating, soothing visual stimulation — perfect for "
            f"newborns, infants, and toddlers 0–3 years old.\n\n"
            f"🫧 BUBBLES: Colorful transparent spheres float upward with gentle sway, "
            f"then burst into sparkling rings. Every pop is satisfying!\n\n"
            f"⭐ STARS: Twinkling stars of gold, white, pink, and blue pulse gently "
            f"in the night sky. Shooting stars streak across with glowing trails.\n\n"
            f"🎵 Soft, dreamlike music at 80 BPM — music box and synth pads, no drums. "
            f"Designed for calm focus, not excitement.\n\n"
            f"🎯 Perfect for:\n"
            f"• Newborn visual tracking development\n"
            f"• Sensory stimulation 0–12 months\n"
            f"• Calming screen time for toddlers 1–3\n"
            f"• Background visuals during tummy time\n"
            f"• Winding down before nap or bedtime\n\n"
            f"No words, no text, no characters — universal visual language.\n\n"
            f"🔔 Subscribe for daily baby animations → {ch['en']}\n"
            f"🎵 Music: Kevin MacLeod (incompetech.com) — "
            f"Licensed under Creative Commons Attribution 4.0 (CC BY 4.0)\n\n"
            f"#StarsAndBubbles #HappyBearKids #SensoryVideo #BabyVisual "
            f"#BubblesPop #CalmBaby #NewbornVisual #ToddlerTV #BabyBackground "
            f"#NightSky #TwinklingStars #VisualStimulation #KevinMacLeod"
        )
        tags = [
            "stars and bubbles", "sensory video", "baby visual", "bubbles pop",
            "happy bear kids", "calming baby", "no talking", "22 minutes",
            "visual stimulation", "night sky", "twinkling stars", "newborn", "toddler",
        ]
    elif lang == "ar":
        description = (
            f"✨ {name} — بهجة حسية خالصة للرضع والأطفال الصغار!\n\n"
            f"شاهد الفقاعات الملونة الشفافة تطفو ببطء إلى الأعلى، تكبر أكثر فأكثر… "
            f"ثم تنفجر! ✨ بينما ترتفع الفقاعات وتنفجر، تتلألأ النجوم بلطف عبر "
            f"سماء الليل العميقة وتطير بخطوط ضوء ساحرة.\n\n"
            f"22 دقيقة من التحفيز البصري الهادئ والجذاب — مثالي للرضع والأطفال 0–3 سنوات.\n\n"
            f"🫧 فقاعات: كرات شفافة ملونة ترتفع بلطف، ثم تنفجر في حلقات متلألئة!\n"
            f"⭐ نجوم: نجوم ذهبية وبيضاء وزهرية وزرقاء تتلألأ في سماء الليل. "
            f"نجوم ساقطة تعبر الشاشة بذيول مضيئة.\n\n"
            f"بدون كلمات، بدون نصوص — لغة بصرية عالمية.\n\n"
            f"🔔 اشتركوا للمزيد من رسوم الأطفال اليومية → {ch['ar']}\n"
            f"🎵 الموسيقى: Kevin MacLeod — Creative Commons Attribution 4.0\n\n"
            f"#النجوم_والفقاعات #هابي_بير_كيدز #فيديو_حسي #تحفيز_بصري "
            f"#رسوم_أطفال #بدون_كلام #رضيع #سماء_الليل"
        )
        tags = [
            "النجوم والفقاعات", "فيديو حسي", "هابي بير كيدز", "تحفيز بصري",
            "بدون كلام", "رضيع", "رسوم أطفال",
        ]
    else:  # id
        description = (
            f"✨ {name} — kesenangan sensorik murni untuk bayi dan balita!\n\n"
            f"Saksikan gelembung transparan berwarna-warni mengapung perlahan ke atas, "
            f"membesar... lalu MELETUS! ✨ Sementara gelembung naik dan meletus, "
            f"bintang-bintang berkelip lembut di langit malam yang dalam dan meluncur "
            f"melintas dengan jejak cahaya yang memukau.\n\n"
            f"22 menit stimulasi visual yang menenangkan dan memikat — sempurna untuk "
            f"bayi baru lahir dan balita 0–3 tahun.\n\n"
            f"🫧 Gelembung: Bola transparan berwarna-warni mengapung ke atas dengan "
            f"gerakan lembut, lalu meledak menjadi cincin berkilau!\n"
            f"⭐ Bintang: Bintang emas, putih, merah muda, dan biru berdenyut lembut "
            f"di langit malam. Bintang jatuh melintasi layar dengan jejak bercahaya.\n\n"
            f"Tanpa kata-kata, tanpa teks — bahasa visual universal.\n\n"
            f"🔔 Subscribe untuk animasi bayi harian → {ch['id']}\n"
            f"🎵 Musik: Kevin MacLeod — Creative Commons Attribution 4.0\n\n"
            f"#BintangDanGelembung #HappyBearKids #VideoSensorik #StimulasiBayi "
            f"#AnimasiAnak #TanpaSuara #BayiBalita #LangitMalam"
        )
        tags = [
            "bintang dan gelembung", "video sensorik", "stimulasi bayi",
            "happy bear kids", "tanpa suara", "animasi anak", "bayi",
        ]

    return {
        "title":       f"{name} | 22 Min Sensory Baby Video | Happy Bear Kids"
                       if lang == "en"
                       else (f"{name} | فيديو حسي 22 دقيقة للرضع | هابي بير كيدز"
                             if lang == "ar"
                             else f"{name} | 22 Menit Video Sensorik Bayi | Happy Bear Kids"),
        "description": description,
        "tags":        tags,
        "video_type":  "stars_bubbles",
        "language":    lang,
        "is_short":    False,
        "status":      "public",
    }


# ── Thumbnail ──────────────────────────────────────────────────────────────────

def generate_thumbnail(out_path: Path, lang: str) -> bool:
    if out_path.exists():
        return True
    try:
        key = TOGETHER_KEY_FILE.read_text().strip()
    except Exception:
        print("    ! Together.ai key not found")
        return False

    notext = "" if lang in ("en", "id") else ", no text, no letters, no words, no numbers"
    prompt = (
        f"magical night sky with glowing transparent bubbles floating upward, "
        f"twinkling gold and white stars, soft dreamy light, deep dark blue background, "
        f"children's educational YouTube thumbnail, Pixar 3D style, vibrant colors{notext}"
    )
    import urllib.request
    try:
        payload = json.dumps({
            "model": TOGETHER_MODEL, "prompt": prompt,
            "width": 1280, "height": 720, "steps": 4, "n": 1,
        }).encode()
        req = urllib.request.Request(
            TOGETHER_URL, data=payload,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read())
        out_path.write_bytes(base64.b64decode(data["data"][0]["b64_json"]))
        print(f"    ✓ thumb → {out_path.name}")
        return True
    except Exception as e:
        print(f"    ! thumb failed: {e}")
        return False


# ── Render + distribute ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate Stars & Bubbles video")
    parser.add_argument("--dry-run",    action="store_true")
    parser.add_argument("--force",      action="store_true")
    parser.add_argument("--regen-meta", action="store_true")
    args = parser.parse_args()

    slug     = f"stars_bubbles_{DATE_STR}"
    out_mp4  = QUEUE_EN / f"{slug}.mp4"
    queues   = {"en": QUEUE_EN, "ar": QUEUE_AR, "id": QUEUE_ID}

    print("=== Stars and Bubbles — 1 video × 3 channels ===\n")

    # ── Render ─────────────────────────────────────────────────────────────────
    if not args.regen_meta:
        if out_mp4.exists() and not args.force:
            sz = out_mp4.stat().st_size / 1024 / 1024
            print(f"  skip render ({sz:.0f} MB already exists)")
        else:
            print(f"  Rendering → {out_mp4.name}")
            if args.dry_run:
                print("    [DRY RUN] StarsBubblesLong  1320s  seed=137")
            else:
                QUEUE_EN.mkdir(parents=True, exist_ok=True)
                cmd = [
                    "npx", "remotion", "render",
                    "src/index.ts", "StarsBubblesLong",
                    str(out_mp4),
                    "--props", json.dumps(PROPS),
                    "--concurrency", "1",
                    "--log", "error",
                ]
                start  = time.time()
                result = subprocess.run(cmd, cwd=str(REMOTION),
                                        capture_output=True, text=True, timeout=21600)
                if result.returncode == 0 and out_mp4.exists():
                    elapsed = (time.time() - start) / 60
                    sz = out_mp4.stat().st_size / 1024 / 1024
                    print(f"    ✓ {sz:.0f} MB in {elapsed:.0f} min")
                else:
                    print(f"    ✗ FAILED: {result.stderr[-500:]}")
                    sys.exit(1)

    # ── Render AR + ID with different music ────────────────────────────────────
    en_music = PROPS["musicFile"]
    if not args.dry_run and not args.regen_meta:
        for lang in ("ar", "id"):
            q    = queues[lang]
            dest = q / f"{slug}_{lang}.mp4"
            q.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                lang_music  = alt_music(en_music, 0, lang)
                props_lang  = dict(PROPS)
                props_lang["musicFile"] = lang_music
                print(f"  Rendering ({lang.upper()}) → {dest.name}")
                cmd = [
                    "npx", "remotion", "render",
                    "src/index.ts", "StarsBubblesLong",
                    str(dest),
                    "--props", json.dumps(props_lang),
                    "--concurrency", "1",
                    "--log", "error",
                ]
                r = subprocess.run(cmd, cwd=str(REMOTION),
                                   capture_output=True, text=True, timeout=21600)
                if r.returncode == 0 and dest.exists():
                    print(f"    ✓ {dest.stat().st_size/1024/1024:.0f}MB")
                else:
                    print(f"    ✗ FAILED ({lang}): {r.stderr[-300:]}")

    # ── Meta + thumbnails ──────────────────────────────────────────────────────
    for lang, q in queues.items():
        q.mkdir(parents=True, exist_ok=True)
        file_stem  = slug if lang == "en" else f"{slug}_{lang}"
        meta_path  = q / f"meta_{file_stem}.yaml"
        thumb_path = q / f"thumb_{file_stem}.png"

        if not meta_path.exists() or args.regen_meta:
            meta = make_meta(lang)
            if args.dry_run:
                print(f"  [DRY RUN] meta {lang.upper()}")
            else:
                with open(meta_path, "w", encoding="utf-8") as f:
                    yaml.dump(meta, f, allow_unicode=True,
                              default_flow_style=False, sort_keys=False)
                print(f"  meta {lang.upper()} → {meta_path.name}")

        if not thumb_path.exists() and not args.dry_run:
            time.sleep(0.5)
            generate_thumbnail(thumb_path, lang)

    print("\n=== Done ===")


if __name__ == "__main__":
    main()
