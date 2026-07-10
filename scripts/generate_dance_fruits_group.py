#!/usr/bin/env python3
"""
generate_dance_fruits_group.py — Group fruit & vegetable dance videos.
8 videos | 25-30 min | No text → universal (EN + AR + ID)

Groups by color family:
  1. Red family: apple, strawberry, tomato (25 min)
  2. Red + cherry: apple, strawberry, tomato, cherry (25 min)
  3. Yellow family: banana, lemon, corn (25 min)
  4. Yellow + orange: banana, pineapple, orange, carrot (28 min → DanceSpriteLong30)
  5. Green family: watermelon, broccoli, cucumber, pepper (28 min → DanceSpriteLong30)
  6. Orange family: orange, carrot, pumpkin (25 min)
  7. Big parade: apple, banana, carrot, watermelon, pineapple (28 min → DanceSpriteLong30)
  8. All together: apple, banana, orange, strawberry, carrot, pineapple (30 min → DanceSpriteLong30)

Dark background #0A1628 per scenario spec — bright fruits on dark = max contrast.

Usage:
  python3 scripts/generate_dance_fruits_group.py --list
  python3 scripts/generate_dance_fruits_group.py --videos all [--dry-run] [--force]
  python3 scripts/generate_dance_fruits_group.py --videos 1 2 3
  python3 scripts/generate_dance_fruits_group.py --regen-meta
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
TOGETHER_URL   = "https://api.together.xyz/v1/images/generations"
TOGETHER_MODEL = "black-forest-labs/FLUX.1-schnell"
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

# ── Sprite map (relative to remotion/public/sprites/ = assets/sprites_new/) ──
S = {
    "apple":      "fruits/apple.png",
    "strawberry": "fruits/strawberry.png",
    "tomato":     "vegetables/tomato.png",
    "cherry":     "fruits/cherry.png",
    "banana":     "fruits/banana.png",
    "lemon":      "fruits/lemon.png",
    "corn":       "vegetables/corn.png",
    "pineapple":  "fruits/pineapple.png",
    "orange":     "fruits/orange.png",
    "carrot":     "vegetables/carrot.png",
    "watermelon": "fruits/watermelon.png",
    "broccoli":   "vegetables/broccoli.png",
    "cucumber":   "vegetables/cucumber.png",
    "pepper":     "vegetables/pepper.png",   # green pepper substitutes for pea
    "pumpkin":    "vegetables/pumpkin_3d.png",
}

BG     = "#0A1628"
ACCENT = "#FFFFFF"


# ── Props builders ─────────────────────────────────────────────────────────────

def _sp(name: str, posX: float, posY: float, size: int, seed: int) -> dict:
    return {"path": S[name], "size": size, "posX": posX, "posY": posY, "seed": seed}


def make_props_3(items: list, music: str) -> dict:
    """3 items in a row — DanceSpriteLong (25 min)"""
    xs = [0.25, 0.50, 0.75]
    sprites = [_sp(items[i], xs[i], 0.45, 350, i + 1) for i in range(3)]
    blocks = [
        {"startSec": 0,    "endSec": 90,   "motion": "FADEIN"},
        {"startSec": 90,   "endSec": 390,  "motion": "BOB",   "period": 2.8, "amplitude": 50},
        {"startSec": 390,  "endSec": 690,  "motion": "WAVE",  "period": 2.5, "amplitude": 55,
         "waveDelay": 0.35},
        {"startSec": 690,  "endSec": 990,  "motion": "SWAY",  "period": 4.0, "amplitude": 60},
        {"startSec": 990,  "endSec": 1290, "motion": "ORBIT",
         "orbitCenterX": 0.5, "orbitCenterY": 0.45},
        {"startSec": 1290, "endSec": 1380, "motion": "SWAY",  "period": 5.5, "amplitude": 45},
        {"startSec": 1380, "endSec": 1500, "motion": "DRIFT", "period": 12,  "amplitude": 280},
    ]
    return {"bgColor": BG, "accentColor": ACCENT, "musicFile": music,
            "bgEffect": "bubbles", "sprites": sprites, "blocks": blocks}


def make_props_4_short(items: list, music: str) -> dict:
    """4 items in a row — DanceSpriteLong (25 min)"""
    xs = [0.2, 0.4, 0.6, 0.8]
    sprites = [_sp(items[i], xs[i], 0.45, 300, i + 1) for i in range(4)]
    blocks = [
        {"startSec": 0,    "endSec": 120,  "motion": "FADEIN"},
        {"startSec": 120,  "endSec": 420,  "motion": "WAVE",   "period": 2.5,
         "amplitude": 50,  "waveDelay": 0.30},
        {"startSec": 420,  "endSec": 720,  "motion": "ORBIT",
         "orbitCenterX": 0.5, "orbitCenterY": 0.45},
        {"startSec": 720,  "endSec": 1020, "motion": "SWAY",   "period": 4.5, "amplitude": 55},
        {"startSec": 1020, "endSec": 1320, "motion": "SWAY",   "period": 5.5, "amplitude": 45},
        {"startSec": 1320, "endSec": 1500, "motion": "DRIFT",  "period": 12,  "amplitude": 280},
    ]
    return {"bgColor": BG, "accentColor": ACCENT, "musicFile": music,
            "bgEffect": "bubbles", "sprites": sprites, "blocks": blocks}


def make_props_4_long(items: list, music: str) -> dict:
    """4 items — DanceSpriteLong30 (28 min content in 30 min slot)"""
    xs = [0.2, 0.4, 0.6, 0.8]
    sprites = [_sp(items[i], xs[i], 0.45, 300, i + 1) for i in range(4)]
    blocks = [
        {"startSec": 0,    "endSec": 90,   "motion": "FADEIN"},
        {"startSec": 90,   "endSec": 390,  "motion": "BOB",    "period": 2.5, "amplitude": 50},
        {"startSec": 390,  "endSec": 750,  "motion": "WAVE",   "period": 2.8,
         "amplitude": 52,  "waveDelay": 0.30},
        {"startSec": 750,  "endSec": 1100, "motion": "ORBIT",
         "orbitCenterX": 0.5, "orbitCenterY": 0.45},
        {"startSec": 1100, "endSec": 1460, "motion": "SWAY",   "period": 5.0, "amplitude": 50},
        {"startSec": 1460, "endSec": 1700, "motion": "DRIFT",  "period": 12,  "amplitude": 260},
        {"startSec": 1700, "endSec": 1800, "motion": "FADEOUT"},
    ]
    return {"bgColor": BG, "accentColor": ACCENT, "musicFile": music,
            "bgEffect": "bubbles", "sprites": sprites, "blocks": blocks}


def make_props_5(items: list, music: str) -> dict:
    """5 items parade — DanceSpriteLong30 (28 min)"""
    xs = [0.10, 0.28, 0.50, 0.72, 0.90]
    sprites = [_sp(items[i], xs[i], 0.45, 260, i + 1) for i in range(5)]
    blocks = [
        {"startSec": 0,    "endSec": 180,  "motion": "MARCH",  "period": 10,  "bobAmplitude": 20},
        {"startSec": 180,  "endSec": 480,  "motion": "WAVE",   "period": 2.5,
         "amplitude": 55,  "waveDelay": 0.28},
        {"startSec": 480,  "endSec": 880,  "motion": "ORBIT",
         "orbitCenterX": 0.5, "orbitCenterY": 0.45},
        {"startSec": 880,  "endSec": 1320, "motion": "SWAY",   "period": 5.0, "amplitude": 48},
        {"startSec": 1320, "endSec": 1620, "motion": "DRIFT",  "period": 10,  "amplitude": 250},
        {"startSec": 1620, "endSec": 1800, "motion": "DRIFT",  "period": 14,  "amplitude": 200},
    ]
    return {"bgColor": BG, "accentColor": ACCENT, "musicFile": music,
            "bgEffect": "bubbles", "sprites": sprites, "blocks": blocks}


def make_props_6(items: list, music: str) -> dict:
    """6 items in 2 rows of 3 — DanceSpriteLong30 (30 min)"""
    xs = [0.22, 0.50, 0.78]
    sprites = (
        [_sp(items[i],   xs[i], 0.28, 280, i + 1) for i in range(3)] +
        [_sp(items[i+3], xs[i], 0.65, 280, i + 4) for i in range(3)]
    )
    blocks = [
        {"startSec": 0,    "endSec": 180,  "motion": "FADEIN"},
        {"startSec": 180,  "endSec": 540,  "motion": "PULSE",  "period": 2.5, "amplitude": 12},
        {"startSec": 540,  "endSec": 900,  "motion": "ORBIT",
         "orbitCenterX": 0.5, "orbitCenterY": 0.46},
        {"startSec": 900,  "endSec": 1380, "motion": "SWAY",   "period": 6.0, "amplitude": 42},
        {"startSec": 1380, "endSec": 1680, "motion": "ORBIT",
         "orbitCenterX": 0.5, "orbitCenterY": 0.46},
        {"startSec": 1680, "endSec": 1800, "motion": "DRIFT",  "period": 14,  "amplitude": 220},
    ]
    return {"bgColor": BG, "accentColor": ACCENT, "musicFile": music,
            "bgEffect": "bubbles", "sprites": sprites, "blocks": blocks}


# ── Video table ────────────────────────────────────────────────────────────────

VIDEOS = {
    "1": {"name_en": "Red Family Dance",
          "items":   ["apple", "strawberry", "tomato"],
          "comp":    "DanceSpriteLong",
          "dur_en":  "25 minutes",
          "make":    lambda: make_props_3(["apple", "strawberry", "tomato"], "Carefree.mp3")},
    "2": {"name_en": "Red Family + Cherry",
          "items":   ["apple", "strawberry", "tomato", "cherry"],
          "comp":    "DanceSpriteLong",
          "dur_en":  "25 minutes",
          "make":    lambda: make_props_4_short(["apple", "strawberry", "tomato", "cherry"],
                                                "Wholesome.mp3")},
    "3": {"name_en": "Yellow Family Dance",
          "items":   ["banana", "lemon", "corn"],
          "comp":    "DanceSpriteLong",
          "dur_en":  "25 minutes",
          "make":    lambda: make_props_3(["banana", "lemon", "corn"], "Quirky Dog.mp3")},
    "4": {"name_en": "Yellow & Orange Dance",
          "items":   ["banana", "pineapple", "orange", "carrot"],
          "comp":    "DanceSpriteLong30",
          "dur_en":  "28 minutes",
          "make":    lambda: make_props_4_long(["banana", "pineapple", "orange", "carrot"],
                                               "Merry Go.mp3")},
    "5": {"name_en": "Green Family Dance",
          "items":   ["watermelon", "broccoli", "cucumber", "pepper"],
          "comp":    "DanceSpriteLong30",
          "dur_en":  "28 minutes",
          "make":    lambda: make_props_4_long(["watermelon", "broccoli", "cucumber", "pepper"],
                                               "Gymnopedie No 1.mp3")},
    "6": {"name_en": "Orange Family Dance",
          "items":   ["orange", "carrot", "pumpkin"],
          "comp":    "DanceSpriteLong",
          "dur_en":  "25 minutes",
          "make":    lambda: make_props_3(["orange", "carrot", "pumpkin"], "Heartwarming.mp3")},
    "7": {"name_en": "Big Fruit Parade",
          "items":   ["apple", "banana", "carrot", "watermelon", "pineapple"],
          "comp":    "DanceSpriteLong30",
          "dur_en":  "28 minutes",
          "make":    lambda: make_props_5(["apple", "banana", "carrot", "watermelon", "pineapple"],
                                          "Hyperfun.mp3")},
    "8": {"name_en": "All Together! Grand Finale",
          "items":   ["apple", "banana", "orange", "strawberry", "carrot", "pineapple"],
          "comp":    "DanceSpriteLong30",
          "dur_en":  "30 minutes",
          "make":    lambda: make_props_6(
              ["apple", "banana", "orange", "strawberry", "carrot", "pineapple"],
              "Happy Happy Game Show.mp3")},
}


# ── Meta generation ────────────────────────────────────────────────────────────

def make_meta(video_id: str, lang: str) -> dict:
    ch = {"en": "@HappyBearKids1", "ar": "@happybearkidsar", "id": "@happybearkidsin"}
    v        = VIDEOS[video_id]
    name_en  = v["name_en"]
    dur_en   = v["dur_en"]
    n_min    = dur_en.split()[0]
    items_en = ", ".join(i.capitalize() for i in v["items"])
    items_id = ", ".join(i.capitalize() for i in v["items"])

    series_en = "Colorful Fruits & Veggies Dance"
    series_ar = "رقصة الفواكه والخضروات الملونة"
    series_id = "Tarian Buah & Sayur Warna-warni"

    if lang == "en":
        title = f"Dancing {name_en}! 🍎 {n_min} Min Baby Animation | Happy Bear Kids"
        description = (
            f"✨ Watch {items_en} come alive and dance together for {dur_en}!\n\n"
            f"No words, no text — pure visual delight with cheerful music. "
            f"Bright colorful fruits and vegetables dancing to gentle rhythms.\n\n"
            f"🎯 Perfect for:\n"
            f"• Background video during play time\n"
            f"• Visual stimulation for babies 0–3\n"
            f"• Calming, colorful screen time\n"
            f"• Toddler nap time wind-down\n\n"
            f"🍎 Part of the {series_en} series!\n\n"
            f"🔔 Subscribe → {ch['en']} for more baby animations every day!\n\n"
            f"🎵 Music: Kevin MacLeod (incompetech.com)\n"
            f"Licensed under Creative Commons Attribution 4.0 (CC BY 4.0)\n\n"
            f"#FruitDance #HappyBearKids #BabyAnimation #ToddlerTV "
            f"#ColorfulFruits #NoTalking #VisualBaby #BabyBackground "
            f"#DancingFruits #CuteAnimation #KevinMacLeod #BabyTV #KidsAnimation"
        )
    elif lang == "ar":
        title = f"رقصة {name_en}! 🍎 {n_min} دقيقة رسوم أطفال | هابي بير كيدز"
        description = (
            f"✨ شاهد الفواكه والخضروات الملونة ترقص معاً لمدة {n_min} دقيقة!\n\n"
            f"بدون كلمات أو نصوص — بهجة بصرية خالصة مع موسيقى مرحة. "
            f"فواكه وخضروات ملونة ترقص على إيقاعات هادئة.\n\n"
            f"🎯 مثالي لـ:\n"
            f"• فيديو خلفية أثناء وقت اللعب\n"
            f"• تحفيز بصري للأطفال 0–3 سنوات\n"
            f"• وقت شاشة هادئ وملون\n"
            f"• الاسترخاء قبل قيلولة الطفل\n\n"
            f"🍎 جزء من سلسلة {series_ar}!\n\n"
            f"🔔 اشتركوا → {ch['ar']} للمزيد من رسوم الأطفال كل يوم!\n\n"
            f"🎵 الموسيقى: Kevin MacLeod (incompetech.com)\n"
            f"رخصة المشاع الإبداعي Attribution 4.0\n\n"
            f"#رسوم_أطفال #هابي_بير_كيدز #رقصة_فواكه #بدون_كلام "
            f"#فيديو_للرضع #فواكه_ملونة #رسوم_متحركة #موسيقى_أطفال"
        )
    else:  # id
        title = f"Tarian {name_en}! 🍎 {n_min} Menit Animasi Bayi | Happy Bear Kids"
        description = (
            f"✨ Saksikan {items_id} menari bersama selama {dur_en}!\n\n"
            f"Tanpa kata-kata, tanpa teks — hiburan visual murni dengan musik ceria. "
            f"Buah dan sayuran warna-warni menari dengan irama lembut.\n\n"
            f"🎯 Sempurna untuk:\n"
            f"• Video latar saat waktu bermain\n"
            f"• Stimulasi visual untuk bayi 0–3 tahun\n"
            f"• Waktu layar yang menenangkan\n"
            f"• Bersiap tidur siang\n\n"
            f"🍎 Bagian dari seri {series_id}!\n\n"
            f"🔔 Subscribe → {ch['id']} untuk animasi bayi setiap hari!\n\n"
            f"🎵 Musik: Kevin MacLeod (incompetech.com)\n"
            f"Lisensi Creative Commons Attribution 4.0\n\n"
            f"#AnimasiAnak #HappyBearKids #TarianBuah #TanpaSuara "
            f"#VideoUntukBayi #BuahWarnaWarni #AnimasiLucu #TelevisiBayi"
        )

    return {
        "title":       title,
        "description": description,
        "tags": ["fruit dance", "vegetable dance", "baby animation", "happy bear kids",
                 dur_en, "colorful fruits", "no talking", "visual baby",
                 "baby background", "toddler tv", "dancing fruits"],
        "video_type": "dance_fruits_group",
        "language":   lang,
        "is_short":   False,
        "status":     "public",
    }


# ── Thumbnail generation ───────────────────────────────────────────────────────

def generate_thumbnail(video_id: str, out_path: Path, lang: str = "en") -> bool:
    if out_path.exists():
        return True
    try:
        key = TOGETHER_KEY_FILE.read_text().strip()
    except Exception:
        return False

    v     = VIDEOS[video_id]
    items = " and ".join(v["items"][:3])
    notext = "" if lang == "en" else ", no text, no letters, no words, no numbers"
    prompt = (
        f"cute 3D cartoon {items} dancing together, Pixar style, "
        f"dark blue background, bright colorful fruits, children's YouTube thumbnail, "
        f"fun and energetic{notext}"
    )
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("gat", ROOT / "scripts" / "generate_ai_thumbs.py")
        gat = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gat)
        img = gat.together_generate_image(prompt, key)
        if img:
            out_path.write_bytes(gat.resize_to_720p(img))
            print(f"    ✓ thumb → {out_path.name}")
            return True
        print(f"    ! thumb failed: API returned no image")
        return False
    except Exception as e:
        print(f"    ! thumb failed: {e}")
        return False


# ── Render ─────────────────────────────────────────────────────────────────────

def render_video(video_id: str, force: bool, dry_run: bool) -> Path | None:
    v        = VIDEOS[video_id]
    slug     = f"fruits_group_{video_id}_{DATE_STR}.mp4"
    out_path = QUEUE_EN / slug

    if out_path.exists() and not force:
        sz = out_path.stat().st_size / 1024 / 1024
        print(f"  skip {slug} ({sz:.0f}MB)")
        return out_path

    props = v["make"]()
    comp  = v["comp"]

    print(f"\n  Rendering Video {video_id}: {v['name_en']} → {slug}")
    if dry_run:
        print(f"    [DRY RUN] {comp}  sprites={len(props['sprites'])}")
        return out_path

    QUEUE_EN.mkdir(parents=True, exist_ok=True)
    cmd = [
        "npx", "remotion", "render",
        "src/index.ts", comp,
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
        sz      = out_path.stat().st_size / 1024 / 1024
        print(f"    ✓ {sz:.0f}MB in {elapsed:.0f}min")
        return out_path
    else:
        print(f"    ✗ FAILED: {result.stderr[-400:]}")
        return None


# ── Publish ────────────────────────────────────────────────────────────────────

def publish_to_all_channels(mp4_path: Path, video_id: str, ep_idx: int, dry_run: bool):
    v        = VIDEOS[video_id]
    props_en = v["make"]()
    en_music = props_en["musicFile"]
    comp     = v["comp"]
    stem     = mp4_path.stem

    for lang, queue in [("en", QUEUE_EN), ("ar", QUEUE_AR), ("id", QUEUE_ID)]:
        queue.mkdir(parents=True, exist_ok=True)
        if lang == "en":
            target      = mp4_path
            target_stem = stem
        else:
            target_stem = f"{stem}_{lang}"
            target      = queue / f"{target_stem}.mp4"
            if not target.exists() and not dry_run:
                lang_music = alt_music(en_music, ep_idx, lang)
                props_lang = dict(props_en)
                props_lang["musicFile"] = lang_music
                print(f"  Rendering ({lang}) {target.name}")
                cmd = [
                    "npx", "remotion", "render",
                    "src/index.ts", comp,
                    str(target),
                    "--props", json.dumps(props_lang),
                    "--concurrency", "1",
                    "--log", "error",
                ]
                start  = time.time()
                result = subprocess.run(cmd, cwd=str(REMOTION),
                                        capture_output=True, text=True, timeout=21600)
                if result.returncode == 0 and target.exists():
                    elapsed = (time.time() - start) / 60
                    sz      = target.stat().st_size / 1024 / 1024
                    print(f"    ✓ {sz:.0f}MB in {elapsed:.0f}min")
                else:
                    print(f"    ✗ FAILED ({lang}): {result.stderr[-400:]}")
                    continue

        meta_path  = queue / f"meta_{target_stem}.yaml"
        thumb_path = queue / f"thumb_{target_stem}.png"

        if not meta_path.exists():
            meta = make_meta(video_id, lang)
            if not dry_run:
                with open(meta_path, "w") as f:
                    yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
                print(f"    meta {lang.upper()} → {meta_path.name}")
            else:
                print(f"    [DRY RUN] meta {lang.upper()}")

        if not thumb_path.exists() and not dry_run:
            time.sleep(0.5)
            generate_thumbnail(video_id, thumb_path, lang)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate fruit/vegetable group dance videos")
    parser.add_argument("--list",      action="store_true")
    parser.add_argument("--videos",    nargs="*",
                        help="Video IDs (1-8 or 'all')")
    parser.add_argument("--dry-run",   action="store_true")
    parser.add_argument("--force",     action="store_true")
    parser.add_argument("--regen-meta", action="store_true")
    args = parser.parse_args()

    if args.list:
        print("Fruit Group Dance Videos:")
        for vid, cfg in VIDEOS.items():
            n = len(cfg["items"])
            print(f"  {vid}.  {cfg['name_en']:35s}  {n} items  {cfg['dur_en']:10s}  {cfg['comp']}")
        return

    video_ids = (list(VIDEOS) if not args.videos or args.videos == ["all"]
                 else args.videos)
    invalid = [v for v in video_ids if v not in VIDEOS]
    if invalid:
        print(f"Unknown IDs: {', '.join(invalid)}. Available: {', '.join(VIDEOS)}")
        sys.exit(1)

    print(f"=== Dance Fruits Group — {len(video_ids)} videos ===\n")

    all_video_ids = list(VIDEOS.keys())
    for video_id in video_ids:
        v      = VIDEOS[video_id]
        ep_idx = all_video_ids.index(video_id)
        print(f"[Video {video_id}] {v['name_en']}")

        slug = f"fruits_group_{video_id}_{DATE_STR}.mp4"
        mp4  = QUEUE_EN / slug

        if args.regen_meta:
            if mp4.exists():
                publish_to_all_channels(mp4, video_id, ep_idx, args.dry_run)
            else:
                print(f"  ! No MP4 at {mp4}")
            continue

        mp4 = render_video(video_id, args.force, args.dry_run)
        if mp4 and (mp4.exists() or args.dry_run):
            publish_to_all_channels(mp4, video_id, ep_idx, args.dry_run)

    print("\n=== Done ===")


if __name__ == "__main__":
    main()
