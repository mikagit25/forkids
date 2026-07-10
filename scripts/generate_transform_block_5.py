#!/usr/bin/env python3
"""
generate_transform_block_5.py — Transform Block 5: Natural Cycles
4 videos × 20-25 min → EN + AR + ID queues.

Videos:
  5.1  Day and Night       (TransformLong day_night mode)
  5.2  Four Seasons        (DanceShapeLong colorPalette season colors)
  5.3  Rain in the Garden  (TransformLong rain mode + vegetable sprites)
  5.4  Wind Swaying        (DanceSpriteLong SWAY high amplitude)

Usage:
  python3 scripts/generate_transform_block_5.py --list
  python3 scripts/generate_transform_block_5.py --videos all [--dry-run] [--force]
  python3 scripts/generate_transform_block_5.py --regen-meta
"""
import argparse, base64, json, shutil, subprocess, sys, time, yaml
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

# Season color palettes
SPRING  = ["#FFB7C5","#FF9EBC","#98D9A7","#7FCF95","#FFFDE7"]
SUMMER  = ["#43A047","#33691E","#F9A825","#FDD835","#27AE60"]
AUTUMN  = ["#E65100","#FF9800","#BF360C","#FDD835","#795548"]
WINTER  = ["#B0BEC5","#90CAF9","#E3F2FD","#ECEFF1","#78909C"]
SEASONS = SPRING + SUMMER + AUTUMN + WINTER + SPRING

VIDEOS = {
    "5.1": {
        "name_en": "Day and Night",
        "name_ar": "النهار والليل",
        "name_id": "Siang dan Malam",
        "comp": "TransformLong",
        "dur_label": "20 min",
        "props": {
            "mode": "day_night",
            "bgColor": "#87CEEB",
            "accentColor": "#FFD700",
            "altColor": "#F0F0D0",
            "musicFile": "Gymnopedie No 1.mp3",
            "volume": 0.18,
            "cycleDuration": 240,
            "seed": 51,
        },
    },
    "5.2": {
        "name_en": "Four Seasons",
        "name_ar": "فصول السنة الأربعة",
        "name_id": "Empat Musim",
        "comp": "DanceShapeLong",
        "dur_label": "25 min",
        "props": {
            "bgColor": "#0A1A0A",
            "musicFile": "Wholesome.mp3",
            "volume": 0.18,
            "shapes": [
                # Tree trunk / main shape at center
                {"shape": "hexagon", "color": "#795548", "size": 280, "posX": 0.50, "posY": 0.40, "seed": 1, "colorOffset": 0.00},
                # Side shapes representing seasonal elements
                {"shape": "circle",  "color": "#98D9A7", "size": 200, "posX": 0.22, "posY": 0.38, "seed": 2, "colorOffset": 0.12},
                {"shape": "circle",  "color": "#FFB7C5", "size": 185, "posX": 0.78, "posY": 0.38, "seed": 3, "colorOffset": 0.25},
                {"shape": "star",    "color": "#F9A825", "size": 160, "posX": 0.35, "posY": 0.58, "seed": 4, "colorOffset": 0.50},
                {"shape": "star",    "color": "#90CAF9", "size": 160, "posX": 0.65, "posY": 0.58, "seed": 5, "colorOffset": 0.75},
                {"shape": "diamond", "color": "#FDD835", "size": 130, "posX": 0.50, "posY": 0.65, "seed": 6, "colorOffset": 0.37},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 300,  "motion": "FADEIN", "amplitude": 60},
                # Spring (0–375s): soft pinks + greens
                {"startSec": 300,  "endSec": 680,  "motion": "BOB",    "period": 4, "amplitude": 30,
                 "colorPalette": SPRING, "colorCycleSec": 55},
                # Summer (680–1055s): greens + yellows
                {"startSec": 680,  "endSec": 1055, "motion": "SWAY",   "period": 5, "amplitude": 45,
                 "colorPalette": SUMMER, "colorCycleSec": 55},
                # Autumn (1055–1430s): reds + oranges
                {"startSec": 1055, "endSec": 1430, "motion": "DRIFT",  "period": 12, "amplitude": 130,
                 "colorPalette": AUTUMN, "colorCycleSec": 55},
                # Winter (1430–1500s): blues + whites
                {"startSec": 1430, "endSec": 1500, "motion": "PULSE",  "period": 5, "amplitude": 12,
                 "colorPalette": WINTER, "colorCycleSec": 50},
            ],
        },
    },
    "5.3": {
        "name_en": "Rain in the Garden",
        "name_ar": "المطر في الحديقة",
        "name_id": "Hujan di Kebun",
        "comp": "TransformLong",
        "dur_label": "20 min",
        "props": {
            "mode": "rain",
            "bgColor": "#2A3E28",
            "accentColor": "#80CBC4",
            "musicFile": "Crinoline Dreams.mp3",
            "volume": 0.18,
            "cycleDuration": 80,
            "spriteSize": 195,
            "spritePaths": [
                "vegetables/carrot.png",
                "vegetables/broccoli.png",
                "vegetables/corn.png",
                "vegetables/tomato.png",
            ],
            "seed": 53,
        },
    },
    "5.4": {
        "name_en": "Wind Swaying",
        "name_ar": "هبوب الريح",
        "name_id": "Diayun Angin",
        "comp": "DanceSpriteLong",
        "dur_label": "25 min",
        "props": {
            "bgColor": "#0A2010",
            "bgColorEnd": "#050D08",
            "accentColor": "#B2DFDB",
            "musicFile": "Life of Riley.mp3",
            "volume": 0.18,
            "bgEffect": "sparkles",
            "sprites": [
                {"path": "vegetables/corn.png",     "size": 260, "posX": 0.12, "posY": 0.44, "seed": 1},
                {"path": "vegetables/broccoli.png", "size": 240, "posX": 0.28, "posY": 0.44, "seed": 2},
                {"path": "fruits/banana.png",       "size": 250, "posX": 0.44, "posY": 0.44, "seed": 3},
                {"path": "vegetables/carrot.png",   "size": 245, "posX": 0.60, "posY": 0.44, "seed": 4},
                {"path": "fruits/apple.png",        "size": 250, "posX": 0.76, "posY": 0.44, "seed": 5},
                {"path": "fruits/pineapple.png",    "size": 240, "posX": 0.92, "posY": 0.44, "seed": 6},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 250,  "motion": "FADEIN", "amplitude": 60},
                # Gentle breeze
                {"startSec": 250,  "endSec": 550,  "motion": "SWAY",   "period": 4.0, "amplitude": 55},
                # Stronger wind — wave motion
                {"startSec": 550,  "endSec": 900,  "motion": "WAVE",   "period": 3.0, "amplitude": 75, "waveDelay": 0.40},
                # Gusty — high SWAY
                {"startSec": 900,  "endSec": 1200, "motion": "SWAY",   "period": 2.5, "amplitude": 90},
                # Calm again
                {"startSec": 1200, "endSec": 1500, "motion": "BOB",    "period": 5.0, "amplitude": 30},
            ],
        },
    },
}

SERIES_EN = "Transform Block 5: Natural Cycles"
SERIES_AR = "المجموعة 5: دورات الطبيعة"
SERIES_ID = "Blok 5: Siklus Alam"

PROMPTS = {
    "5.1": "beautiful sunrise and sunset sky with sun and moon moving across, serene landscape, children's animation",
    "5.2": "tree showing four seasons spring summer autumn winter, colorful, children's animation",
    "5.3": "cute cartoon vegetables in a garden with gentle rain falling, green background, children's animation",
    "5.4": "cute cartoon fruits and vegetables swaying gently in the wind, garden background, children's animation",
}


def make_meta(video_id: str, lang: str) -> dict:
    v  = VIDEOS[video_id]
    ch = {"en": "@HappyBearKids1", "ar": "@happybearkidsar", "id": "@happybearkidsin"}
    name = v[f"name_{lang}"]
    dur  = v["dur_label"]
    if lang == "en":
        title = f"{name} | {dur} Baby Animation | Happy Bear Kids"
        description = (
            f"✨ {name} — beautiful natural cycle animation for babies!\n\n"
            f"Watch nature's most beautiful transformations — from day to night, "
            f"season to season, rain to sunshine. "
            f"No words, no text — pure visual wonder.\n\n"
            f"🎯 Age: 0–3 years | Part of the {SERIES_EN} series.\n\n"
            f"🔔 Subscribe → {ch['en']}\n"
            f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
            f"#HappyBearKids #NatureBaby #BabyAnimation #VisualBaby "
            f"#NaturalCycles #NoTalking #ToddlerTV #VisualStimulation"
        )
        tags = ["nature baby", "baby animation", "natural cycles", "happy bear kids", dur,
                "no talking", "visual stimulation", name.lower()]
    elif lang == "ar":
        title = f"{name} | {dur} رسوم أطفال | هابي بير كيدز"
        description = (
            f"✨ {name} — رسوم متحركة لدورات الطبيعة الجميلة للرضع!\n\n"
            f"شاهد تحولات الطبيعة الجميلة — من النهار إلى الليل، من موسم إلى آخر. "
            f"بدون كلمات.\n\n"
            f"جزء من سلسلة {SERIES_AR}.\n\n"
            f"🔔 اشتركوا → {ch['ar']}\n"
            f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
            f"#هابي_بير_كيدز #طبيعة #رسوم_أطفال #تحفيز_بصري #بدون_كلام"
        )
        tags = ["هابي بير كيدز", "طبيعة", "رسوم أطفال", "تحفيز بصري", name]
    else:
        title = f"{name} | {dur} Animasi Bayi | Happy Bear Kids"
        description = (
            f"✨ {name} — animasi siklus alam yang indah untuk bayi!\n\n"
            f"Saksikan transformasi alam yang indah — dari siang ke malam, "
            f"dari musim ke musim. Tanpa kata-kata.\n\n"
            f"Bagian dari seri {SERIES_ID}.\n\n"
            f"🔔 Subscribe → {ch['id']}\n"
            f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
            f"#HappyBearKids #AlamBayi #StimulasiBayi #TanpaSuara"
        )
        tags = ["happy bear kids", "alam bayi", "stimulasi bayi", "tanpa suara", name]
    return {"title": title, "description": description, "tags": tags,
            "video_type": "transform", "language": lang, "is_short": False, "status": "public"}


def generate_thumbnail(video_id: str, out_path: Path, lang: str) -> bool:
    if out_path.exists():
        return True
    try:
        key = TOGETHER_KEY_FILE.read_text().strip()
    except Exception:
        return False
    notext = "" if lang in ("en", "id") else ", no text, no letters, no words, no numbers"
    prompt = PROMPTS.get(video_id, "abstract baby animation") + f", Pixar 3D style, YouTube thumbnail{notext}"
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
        print(f"    ! thumb failed: {e}"); return False


def render_video(video_id: str, force: bool, dry_run: bool) -> Path | None:
    v    = VIDEOS[video_id]
    slug = f"transform5_{video_id.replace('.', '')}_{DATE_STR}.mp4"
    out  = QUEUE_EN / slug
    if out.exists() and not force:
        print(f"  skip {slug} ({out.stat().st_size // 1024 // 1024} MB)"); return out
    print(f"\n  Rendering {video_id}: {v['name_en']} → {slug}")
    if dry_run:
        print(f"    [DRY RUN] {v['comp']}"); return out
    QUEUE_EN.mkdir(parents=True, exist_ok=True)
    cmd = ["npx", "remotion", "render", "src/index.ts", v["comp"],
           str(out), "--props", json.dumps(v["props"]),
           "--concurrency", "1", "--log", "error"]
    t0 = time.time()
    r  = subprocess.run(cmd, cwd=str(REMOTION), capture_output=True, text=True, timeout=21600)
    if r.returncode == 0 and out.exists():
        print(f"    ✓ {out.stat().st_size // 1024 // 1024} MB in {(time.time()-t0)/60:.0f} min")
        return out
    print(f"    ✗ FAILED: {r.stderr[-400:]}"); return None


def distribute(mp4: Path, video_id: str, dry_run: bool):
    stem = mp4.stem
    for lang, q in [("en", QUEUE_EN), ("ar", QUEUE_AR), ("id", QUEUE_ID)]:
        q.mkdir(parents=True, exist_ok=True)
        tstem = stem if lang == "en" else f"{stem}_{lang}"
        tpath = q / f"{tstem}.mp4"
        if lang != "en" and not tpath.exists() and not dry_run:
            shutil.copy2(mp4, tpath); print(f"    copy → {tpath.name}")
        mpath = q / f"meta_{tstem}.yaml"
        if not mpath.exists():
            if dry_run:
                print(f"    [DRY RUN] meta {lang.upper()}")
            else:
                with open(mpath, "w", encoding="utf-8") as f:
                    yaml.dump(make_meta(video_id, lang), f, allow_unicode=True,
                              default_flow_style=False, sort_keys=False)
                print(f"    meta {lang.upper()} → {mpath.name}")
        tp = q / f"thumb_{tstem}.png"
        if not tp.exists() and not dry_run:
            time.sleep(0.5); generate_thumbnail(video_id, tp, lang)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--list",       action="store_true")
    parser.add_argument("--videos",     nargs="*")
    parser.add_argument("--dry-run",    action="store_true")
    parser.add_argument("--force",      action="store_true")
    parser.add_argument("--regen-meta", action="store_true")
    args = parser.parse_args()

    if args.list:
        for vid, v in VIDEOS.items():
            print(f"  {vid}  {v['name_en']:40s}  {v['comp']}  {v['dur_label']}")
        return

    ids = list(VIDEOS) if not args.videos or args.videos == ["all"] else args.videos
    bad = [v for v in ids if v not in VIDEOS]
    if bad:
        print(f"Unknown: {bad}"); sys.exit(1)

    print(f"=== Transform Block 5 — {len(ids)} videos ===\n")
    for vid in ids:
        print(f"[{vid}] {VIDEOS[vid]['name_en']}")
        slug = f"transform5_{vid.replace('.', '')}_{DATE_STR}"
        mp4  = QUEUE_EN / f"{slug}.mp4"
        if args.regen_meta:
            distribute(mp4, vid, args.dry_run); continue
        mp4 = render_video(vid, args.force, args.dry_run)
        if mp4 and (mp4.exists() or args.dry_run):
            distribute(mp4, vid, args.dry_run)

    print("\n=== Done ===")


if __name__ == "__main__":
    main()
