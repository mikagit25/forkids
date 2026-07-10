#!/usr/bin/env python3
"""
generate_transform_block_3.py — Transform Block 3: Physical Phenomena
4 videos × 20-25 min → EN + AR + ID queues.

Videos:
  3.1  Falling and Bouncing  (DanceShapeLong BOUNCE)
  3.2  Magnetic Shapes       (DanceShapeLong ORBIT attraction)
  3.3  Fruits Underwater     (DanceSpriteLong WAVE + BOB)
  3.4  Shape Shadows         (DanceShapeLong paired shapes — light + dark)

Usage:
  python3 scripts/generate_transform_block_3.py --list
  python3 scripts/generate_transform_block_3.py --videos all [--dry-run] [--force]
  python3 scripts/generate_transform_block_3.py --regen-meta
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

RAINBOW = ["#E53935","#FF9800","#FDD835","#43A047","#1E88E5","#9C27B0","#E91E63","#E53935"]

VIDEOS = {
    "3.1": {
        "name_en": "Falling and Bouncing",
        "name_ar": "السقوط والارتداد",
        "name_id": "Jatuh dan Memantul",
        "comp": "DanceShapeLong",
        "dur_label": "25 min",
        "props": {
            "bgColor": "#04100C",
            "musicFile": "Quirky Dog.mp3",
            "volume": 0.18,
            "shapes": [
                {"shape": "circle",   "color": "#E53935", "size": 220, "posX": 0.18, "posY": 0.50, "seed": 1},
                {"shape": "square",   "color": "#1E88E5", "size": 200, "posX": 0.36, "posY": 0.50, "seed": 2},
                {"shape": "triangle", "color": "#FDD835", "size": 210, "posX": 0.54, "posY": 0.50, "seed": 3},
                {"shape": "star",     "color": "#43A047", "size": 195, "posX": 0.72, "posY": 0.50, "seed": 4},
                {"shape": "diamond",  "color": "#9C27B0", "size": 205, "posX": 0.90, "posY": 0.50, "seed": 5},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 200,  "motion": "FADEIN"},
                {"startSec": 200,  "endSec": 600,  "motion": "BOUNCE", "period": 2.0, "amplitude": 65},
                {"startSec": 600,  "endSec": 900,  "motion": "BOUNCE", "period": 1.5, "amplitude": 80,
                 "colorPalette": RAINBOW, "colorCycleSec": 60},
                {"startSec": 900,  "endSec": 1200, "motion": "BOB",    "period": 3.0, "amplitude": 45},
                {"startSec": 1200, "endSec": 1500, "motion": "BOUNCE", "period": 2.5, "amplitude": 70,
                 "colorPalette": RAINBOW, "colorCycleSec": 55},
            ],
        },
    },
    "3.2": {
        "name_en": "Magnetic Attraction",
        "name_ar": "الجذب المغناطيسي",
        "name_id": "Daya Tarik Magnet",
        "comp": "DanceShapeLong",
        "dur_label": "25 min",
        "props": {
            "bgColor": "#081018",
            "musicFile": "Life of Riley.mp3",
            "volume": 0.18,
            "shapes": [
                # Anchor (no orbit) at center — the "magnet"
                {"shape": "diamond", "color": "#E53935", "size": 160, "posX": 0.50, "posY": 0.42,
                 "seed": 0, "orbitRadius": 0},
                # Orbiting shapes at different radii
                {"shape": "circle",  "color": "#1E88E5", "size": 180, "posX": 0.50, "posY": 0.42,
                 "seed": 1, "orbitRadius": 160, "orbitPeriodSec": 7},
                {"shape": "circle",  "color": "#FDD835", "size": 160, "posX": 0.50, "posY": 0.42,
                 "seed": 2, "orbitRadius": 220, "orbitPeriodSec": 10, "orbitCcw": True},
                {"shape": "star",    "color": "#43A047", "size": 150, "posX": 0.50, "posY": 0.42,
                 "seed": 3, "orbitRadius": 290, "orbitPeriodSec": 14},
                {"shape": "circle",  "color": "#9C27B0", "size": 140, "posX": 0.50, "posY": 0.42,
                 "seed": 4, "orbitRadius": 350, "orbitPeriodSec": 18, "orbitCcw": True},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 300,  "motion": "FADEIN"},
                {"startSec": 300,  "endSec": 800,  "motion": "ORBIT", "orbitCenterX": 0.5, "orbitCenterY": 0.42},
                {"startSec": 800,  "endSec": 1100, "motion": "PULSE", "period": 5, "amplitude": 15},
                {"startSec": 1100, "endSec": 1500, "motion": "ORBIT", "orbitCenterX": 0.5, "orbitCenterY": 0.42,
                 "colorPalette": RAINBOW, "colorCycleSec": 70},
            ],
        },
    },
    "3.3": {
        "name_en": "Fruits Underwater",
        "name_ar": "الفواكه تحت الماء",
        "name_id": "Buah-buahan di Bawah Air",
        "comp": "DanceSpriteLong",
        "dur_label": "25 min",
        "props": {
            "bgColor": "#01324A",
            "bgColorEnd": "#012438",
            "accentColor": "#4DD0E1",
            "musicFile": "Gymnopedie No 1.mp3",
            "volume": 0.18,
            "bgEffect": "bubbles",
            "sprites": [
                {"path": "fruits/apple.png",      "size": 240, "posX": 0.18, "posY": 0.44, "seed": 1},
                {"path": "fruits/orange.png",     "size": 230, "posX": 0.36, "posY": 0.44, "seed": 2},
                {"path": "fruits/banana.png",     "size": 240, "posX": 0.54, "posY": 0.44, "seed": 3},
                {"path": "fruits/grapes.png",     "size": 220, "posX": 0.72, "posY": 0.44, "seed": 4},
                {"path": "fruits/strawberry.png", "size": 215, "posX": 0.90, "posY": 0.44, "seed": 5},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 300,  "motion": "FADEIN", "amplitude": 50},
                {"startSec": 300,  "endSec": 700,  "motion": "WAVE",   "period": 3.5, "amplitude": 50, "waveDelay": 0.45},
                {"startSec": 700,  "endSec": 1100, "motion": "BOB",    "period": 4.0, "amplitude": 40},
                {"startSec": 1100, "endSec": 1300, "motion": "ORBIT",  "orbitCenterX": 0.5, "orbitCenterY": 0.44},
                {"startSec": 1300, "endSec": 1500, "motion": "WAVE",   "period": 3.0, "amplitude": 45, "waveDelay": 0.40},
            ],
        },
    },
    "3.4": {
        "name_en": "Shapes and Shadows",
        "name_ar": "الأشكال والظلال",
        "name_id": "Bentuk dan Bayangan",
        "comp": "DanceShapeLong",
        "dur_label": "25 min",
        "props": {
            "bgColor": "#E8E4D8",
            "musicFile": "Crinoline Dreams.mp3",
            "volume": 0.18,
            "shapes": [
                # Bright shapes (upper)
                {"shape": "circle",   "color": "#E53935", "size": 200, "posX": 0.25, "posY": 0.35, "seed": 1},
                {"shape": "square",   "color": "#1E88E5", "size": 190, "posX": 0.50, "posY": 0.33, "seed": 2},
                {"shape": "triangle", "color": "#FDD835", "size": 195, "posX": 0.75, "posY": 0.35, "seed": 3},
                # Shadow duplicates (lower, dark, same motion but offset)
                {"shape": "circle",   "color": "#2C1810", "size": 200, "posX": 0.25, "posY": 0.65, "seed": 11},
                {"shape": "square",   "color": "#1A2040", "size": 190, "posX": 0.50, "posY": 0.67, "seed": 12},
                {"shape": "triangle", "color": "#3A2E08", "size": 195, "posX": 0.75, "posY": 0.65, "seed": 13},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 250,  "motion": "FADEIN", "amplitude": 60},
                {"startSec": 250,  "endSec": 700,  "motion": "SWAY",   "period": 4, "amplitude": 55},
                {"startSec": 700,  "endSec": 1100, "motion": "BOB",    "period": 3, "amplitude": 40},
                {"startSec": 1100, "endSec": 1500, "motion": "DRIFT",  "period": 16, "amplitude": 180},
            ],
        },
    },
}

SERIES_EN = "Transform Block 3: Physical Phenomena"
SERIES_AR = "المجموعة 3: الظواهر الطبيعية"
SERIES_ID = "Blok 3: Fenomena Alam"

PROMPTS = {
    "3.1": "colorful 3D shapes bouncing and falling with gravity, dark background, children's animation",
    "3.2": "colorful 3D shapes orbiting a central magnet shape, space-like dark background, children's animation",
    "3.3": "cute cartoon fruits floating underwater, ocean blue background, bubbles, children's animation",
    "3.4": "bright colorful 3D shapes with soft shadows on a light background, children's animation",
}


def make_meta(video_id: str, lang: str) -> dict:
    v  = VIDEOS[video_id]
    ch = {"en": "@HappyBearKids1", "ar": "@happybearkidsar", "id": "@happybearkidsin"}
    name = v[f"name_{lang}"]
    dur  = v["dur_label"]
    if lang == "en":
        title = f"{name} | {dur} Baby Animation | Happy Bear Kids"
        description = (
            f"✨ {name} — fascinating physical phenomenon animation for babies!\n\n"
            f"Watch shapes and objects move, float, and dance according to natural forces. "
            f"No words, no text — pure visual exploration.\n\n"
            f"🎯 Age: 0–3 years | Part of the {SERIES_EN} series.\n\n"
            f"🔔 Subscribe → {ch['en']}\n"
            f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
            f"#HappyBearKids #BabyAnimation #VisualBaby #PhysicsBaby "
            f"#NoTalking #ToddlerTV #VisualStimulation"
        )
        tags = ["baby animation", "physics", "happy bear kids", dur,
                "no talking", "visual stimulation", name.lower()]
    elif lang == "ar":
        title = f"{name} | {dur} رسوم أطفال | هابي بير كيدز"
        description = (
            f"✨ {name} — رسوم متحركة جذابة للرضع والأطفال!\n\n"
            f"شاهد الأشكال والأشياء تتحرك وترقص. بدون كلمات.\n\n"
            f"جزء من سلسلة {SERIES_AR}.\n\n"
            f"🔔 اشتركوا → {ch['ar']}\n"
            f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
            f"#هابي_بير_كيدز #رسوم_أطفال #تحفيز_بصري #بدون_كلام"
        )
        tags = ["هابي بير كيدز", "رسوم أطفال", "تحفيز بصري", "بدون كلام", name]
    else:
        title = f"{name} | {dur} Animasi Bayi | Happy Bear Kids"
        description = (
            f"✨ {name} — animasi fenomena fisik untuk bayi!\n\n"
            f"Saksikan bentuk dan benda bergerak, mengapung, dan menari. Tanpa kata-kata.\n\n"
            f"Bagian dari seri {SERIES_ID}.\n\n"
            f"🔔 Subscribe → {ch['id']}\n"
            f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
            f"#HappyBearKids #AnimasiAnak #StimulasiBayi #TanpaSuara"
        )
        tags = ["happy bear kids", "animasi anak", "stimulasi bayi", "tanpa suara", name]
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
    slug = f"transform3_{video_id.replace('.', '')}_{DATE_STR}.mp4"
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
            print(f"  {vid}  {v['name_en']:35s}  {v['comp']}  {v['dur_label']}")
        return

    ids = list(VIDEOS) if not args.videos or args.videos == ["all"] else args.videos
    bad = [v for v in ids if v not in VIDEOS]
    if bad:
        print(f"Unknown: {bad}"); sys.exit(1)

    print(f"=== Transform Block 3 — {len(ids)} videos ===\n")
    for vid in ids:
        print(f"[{vid}] {VIDEOS[vid]['name_en']}")
        slug = f"transform3_{vid.replace('.', '')}_{DATE_STR}"
        mp4  = QUEUE_EN / f"{slug}.mp4"
        if args.regen_meta:
            distribute(mp4, vid, args.dry_run); continue
        mp4 = render_video(vid, args.force, args.dry_run)
        if mp4 and (mp4.exists() or args.dry_run):
            distribute(mp4, vid, args.dry_run)

    print("\n=== Done ===")


if __name__ == "__main__":
    main()
