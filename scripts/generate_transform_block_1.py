#!/usr/bin/env python3
"""
generate_transform_block_1.py — Transform Block 1: Transformations
4 videos × 20-25 min → EN + AR + ID queues.

Videos:
  1.1  Fruit Grows  (TransformLong grow mode)
  1.2  Shape Morphing (DanceShapeLong SPIN + colorPalette)
  1.3  Big and Small — Pulse (DanceShapeLong PULSE)
  1.4  Divide and Merge (DanceShapeLong ORBIT)

All no-text → 1 render → 3 channels.

Usage:
  python3 scripts/generate_transform_block_1.py --list
  python3 scripts/generate_transform_block_1.py --videos all [--dry-run] [--force]
  python3 scripts/generate_transform_block_1.py --videos 1.1 1.3
  python3 scripts/generate_transform_block_1.py --regen-meta
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

# ── Video props ───────────────────────────────────────────────────────────────

RAINBOW = ["#E53935","#FF9800","#FDD835","#43A047","#1E88E5","#9C27B0","#E53935"]

VIDEOS = {
    "1.1": {
        "name_en": "The Growing Apple",
        "name_ar": "التفاحة تنمو",
        "name_id": "Apel yang Tumbuh",
        "comp": "TransformLong",
        "dur_label": "20 min",
        "props": {
            "mode": "grow",
            "bgColor": "#0A1628",
            "accentColor": "#E53935",
            "altColor": "#4CAF50",
            "musicFile": "Gymnopedie No 1.mp3",
            "volume": 0.18,
            "cycleDuration": 150,
            "seed": 11,
        },
    },
    "1.2": {
        "name_en": "Shape Morphing Dance",
        "name_ar": "رقصة تحوّل الأشكال",
        "name_id": "Tarian Perubahan Bentuk",
        "comp": "DanceShapeLong",
        "dur_label": "25 min",
        "props": {
            "bgColor": "#0A1628",
            "musicFile": "Wholesome.mp3",
            "volume": 0.18,
            "shapes": [
                {"shape": "circle",   "color": "#E53935", "size": 260, "posX": 0.20, "posY": 0.44, "seed": 1},
                {"shape": "square",   "color": "#1E88E5", "size": 240, "posX": 0.40, "posY": 0.44, "seed": 2},
                {"shape": "triangle", "color": "#FDD835", "size": 260, "posX": 0.60, "posY": 0.44, "seed": 3},
                {"shape": "star",     "color": "#43A047", "size": 240, "posX": 0.80, "posY": 0.44, "seed": 4},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 200,  "motion": "FADEIN", "amplitude": 70},
                {"startSec": 200,  "endSec": 550,  "motion": "SPIN",   "period": 6},
                {"startSec": 550,  "endSec": 900,  "motion": "PULSE",  "period": 4, "amplitude": 20,
                 "colorPalette": RAINBOW, "colorCycleSec": 55},
                {"startSec": 900,  "endSec": 1200, "motion": "DRIFT",  "period": 12, "amplitude": 220,
                 "colorPalette": RAINBOW, "colorCycleSec": 60},
                {"startSec": 1200, "endSec": 1500, "motion": "WAVE",   "period": 3, "amplitude": 55,
                 "waveDelay": 0.40, "colorPalette": RAINBOW, "colorCycleSec": 50},
            ],
        },
    },
    "1.3": {
        "name_en": "Big and Small",
        "name_ar": "كبير وصغير",
        "name_id": "Besar dan Kecil",
        "comp": "DanceShapeLong",
        "dur_label": "25 min",
        "props": {
            "bgColor": "#040E24",
            "musicFile": "Heartwarming.mp3",
            "volume": 0.18,
            "shapes": [
                {"shape": "circle", "color": "#E53935", "size": 310, "posX": 0.50, "posY": 0.42, "seed": 1},
                {"shape": "circle", "color": "#1E88E5", "size": 180, "posX": 0.22, "posY": 0.50, "seed": 2},
                {"shape": "circle", "color": "#FDD835", "size": 200, "posX": 0.78, "posY": 0.50, "seed": 3},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 250,  "motion": "FADEIN"},
                {"startSec": 250,  "endSec": 650,  "motion": "PULSE",  "period": 4.5, "amplitude": 22},
                {"startSec": 650,  "endSec": 1000, "motion": "PULSE",  "period": 3.0, "amplitude": 28,
                 "colorPalette": RAINBOW, "colorCycleSec": 70},
                {"startSec": 1000, "endSec": 1500, "motion": "BOB",    "period": 4.0, "amplitude": 35,
                 "colorPalette": RAINBOW, "colorCycleSec": 65},
            ],
        },
    },
    "1.4": {
        "name_en": "Divide and Merge",
        "name_ar": "انقسام واندماج",
        "name_id": "Membelah dan Menyatu",
        "comp": "DanceShapeLong",
        "dur_label": "25 min",
        "props": {
            "bgColor": "#060C18",
            "musicFile": "Carefree.mp3",
            "volume": 0.18,
            "shapes": [
                {"shape": "circle", "color": "#E53935", "size": 210, "posX": 0.38, "posY": 0.42,
                 "seed": 1, "orbitRadius": 180, "orbitPeriodSec": 9},
                {"shape": "circle", "color": "#1E88E5", "size": 210, "posX": 0.62, "posY": 0.42,
                 "seed": 2, "orbitRadius": 180, "orbitPeriodSec": 9, "orbitCcw": True},
                {"shape": "circle", "color": "#FDD835", "size": 160, "posX": 0.50, "posY": 0.28,
                 "seed": 3, "orbitRadius": 260, "orbitPeriodSec": 14},
                {"shape": "circle", "color": "#43A047", "size": 160, "posX": 0.50, "posY": 0.56,
                 "seed": 4, "orbitRadius": 260, "orbitPeriodSec": 14, "orbitCcw": True},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 200,  "motion": "FADEIN"},
                {"startSec": 200,  "endSec": 600,  "motion": "ORBIT", "orbitCenterX": 0.5, "orbitCenterY": 0.42},
                {"startSec": 600,  "endSec": 900,  "motion": "PULSE", "period": 5, "amplitude": 18},
                {"startSec": 900,  "endSec": 1300, "motion": "ORBIT", "orbitCenterX": 0.5, "orbitCenterY": 0.42,
                 "colorPalette": RAINBOW, "colorCycleSec": 80},
                {"startSec": 1300, "endSec": 1500, "motion": "DRIFT", "period": 14, "amplitude": 200},
            ],
        },
    },
}

SERIES_EN = "Transform Block 1: Transformations"
SERIES_AR = "المجموعة 1: التحولات"
SERIES_ID = "Blok 1: Transformasi"


# ── Meta ───────────────────────────────────────────────────────────────────────

def make_meta(video_id: str, lang: str) -> dict:
    v  = VIDEOS[video_id]
    ch = {"en": "@HappyBearKids1", "ar": "@happybearkidsar", "id": "@happybearkidsin"}
    name = v[f"name_{lang}"]
    dur  = v["dur_label"]

    if lang == "en":
        title = f"{name} | {dur} Baby Animation | Happy Bear Kids"
        description = (
            f"✨ {name} — a beautiful abstract animation for babies and toddlers!\n\n"
            f"Watch shapes and colors transform slowly and peacefully. "
            f"Pure visual stimulation — no words, no text, just beautiful movement.\n\n"
            f"🎯 Perfect for babies 0–3 years:\n"
            f"• Visual tracking development\n"
            f"• Calm focused watching\n"
            f"• Background play time visuals\n"
            f"• Before nap wind-down\n\n"
            f"Part of the {SERIES_EN} series.\n\n"
            f"🔔 Subscribe → {ch['en']}\n"
            f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
            f"#HappyBearKids #BabyAnimation #VisualBaby #ToddlerTV "
            f"#AbstractBaby #CalmBaby #NoTalking #VisualStimulation"
        )
        tags = ["baby animation", "visual stimulation", "happy bear kids", dur,
                "no talking", "toddler tv", "abstract", name.lower()]
    elif lang == "ar":
        title = f"{name} | {dur} رسوم أطفال | هابي بير كيدز"
        description = (
            f"✨ {name} — رسوم متحركة تجريدية جميلة للرضع والأطفال الصغار!\n\n"
            f"شاهد الأشكال والألوان تتحول ببطء وهدوء. "
            f"تحفيز بصري خالص — بدون كلمات، بدون نصوص، فقط حركة جميلة.\n\n"
            f"جزء من سلسلة {SERIES_AR}.\n\n"
            f"🔔 اشتركوا → {ch['ar']}\n"
            f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
            f"#هابي_بير_كيدز #رسوم_أطفال #تحفيز_بصري #بدون_كلام"
        )
        tags = ["هابي بير كيدز", "رسوم أطفال", "تحفيز بصري", "بدون كلام", name]
    else:
        title = f"{name} | {dur} Animasi Bayi | Happy Bear Kids"
        description = (
            f"✨ {name} — animasi abstrak yang indah untuk bayi dan balita!\n\n"
            f"Saksikan bentuk dan warna berubah dengan perlahan dan damai. "
            f"Stimulasi visual murni — tanpa kata-kata, tanpa teks.\n\n"
            f"Bagian dari seri {SERIES_ID}.\n\n"
            f"🔔 Subscribe → {ch['id']}\n"
            f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
            f"#HappyBearKids #AnimasiAnak #StimulasiBayi #TanpaSuara"
        )
        tags = ["happy bear kids", "animasi anak", "stimulasi bayi", "tanpa suara", name]

    return {
        "title": title, "description": description, "tags": tags,
        "video_type": "transform", "language": lang, "is_short": False, "status": "public",
    }


# ── Thumbnail ──────────────────────────────────────────────────────────────────

def generate_thumbnail(video_id: str, out_path: Path, lang: str) -> bool:
    if out_path.exists():
        return True
    try:
        key = TOGETHER_KEY_FILE.read_text().strip()
    except Exception:
        return False
    v    = VIDEOS[video_id]
    name = v["name_en"]
    notext = "" if lang in ("en", "id") else ", no text, no letters, no words, no numbers"
    prompt = (
        f"abstract baby animation scene: {name.lower()}, Pixar 3D style, "
        f"deep dark blue background, bright vibrant colors, children's YouTube thumbnail{notext}"
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
    v    = VIDEOS[video_id]
    slug = f"transform1_{video_id.replace('.', '')}_{DATE_STR}.mp4"
    out  = QUEUE_EN / slug
    if out.exists() and not force:
        print(f"  skip {slug} ({out.stat().st_size // 1024 // 1024} MB)")
        return out
    print(f"\n  Rendering {video_id}: {v['name_en']} → {slug}")
    if dry_run:
        print(f"    [DRY RUN] {v['comp']}")
        return out
    QUEUE_EN.mkdir(parents=True, exist_ok=True)
    cmd = [
        "npx", "remotion", "render", "src/index.ts", v["comp"],
        str(out), "--props", json.dumps(v["props"]),
        "--concurrency", "1", "--log", "error",
    ]
    t0 = time.time()
    r  = subprocess.run(cmd, cwd=str(REMOTION), capture_output=True, text=True, timeout=21600)
    if r.returncode == 0 and out.exists():
        print(f"    ✓ {out.stat().st_size // 1024 // 1024} MB in {(time.time()-t0)/60:.0f} min")
        return out
    print(f"    ✗ FAILED: {r.stderr[-400:]}")
    return None


def distribute(mp4: Path, video_id: str, dry_run: bool):
    stem = mp4.stem
    for lang, q in [("en", QUEUE_EN), ("ar", QUEUE_AR), ("id", QUEUE_ID)]:
        q.mkdir(parents=True, exist_ok=True)
        tstem = stem if lang == "en" else f"{stem}_{lang}"
        tpath = q / f"{tstem}.mp4"
        if lang != "en" and not tpath.exists() and not dry_run:
            shutil.copy2(mp4, tpath)
            print(f"    copy → {tpath.name}")
        mpath = q / f"meta_{tstem}.yaml"
        if not mpath.exists():
            if dry_run:
                print(f"    [DRY RUN] meta {lang.upper()}")
            else:
                with open(mpath, "w", encoding="utf-8") as f:
                    yaml.dump(make_meta(video_id, lang), f, allow_unicode=True,
                              default_flow_style=False, sort_keys=False)
                print(f"    meta {lang.upper()} → {mpath.name}")
        tpath2 = q / f"thumb_{tstem}.png"
        if not tpath2.exists() and not dry_run:
            time.sleep(0.5)
            generate_thumbnail(video_id, tpath2, lang)


# ── Main ──────────────────────────────────────────────────────────────────────

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

    print(f"=== Transform Block 1 — {len(ids)} videos ===\n")
    for vid in ids:
        print(f"[{vid}] {VIDEOS[vid]['name_en']}")
        slug = f"transform1_{vid.replace('.', '')}_{DATE_STR}"
        mp4  = QUEUE_EN / f"{slug}.mp4"
        if args.regen_meta:
            distribute(mp4, vid, args.dry_run)
            continue
        mp4 = render_video(vid, args.force, args.dry_run)
        if mp4 and (mp4.exists() or args.dry_run):
            distribute(mp4, vid, args.dry_run)

    print("\n=== Done ===")


if __name__ == "__main__":
    main()
