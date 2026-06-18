#!/usr/bin/env python3
"""
generate_transform_block_2.py — Transform Block 2: Color as Character
4 videos × 20-25 min → EN + AR + ID queues.

Videos:
  2.1  Color Mixing       (DanceShapeLong ORBIT — 2 circles approach each other)
  2.2  Color Tide/Wave    (DanceShapeLong WAVE + rainbow colorPalette)
  2.3  Rainbow Gathers    (DanceShapeLong DRIFT + full rainbow palette)
  2.4  Fruits Recolor     (DanceShapeLong PULSE cycling through colors)

Usage:
  python3 scripts/generate_transform_block_2.py --list
  python3 scripts/generate_transform_block_2.py --videos all [--dry-run] [--force]
  python3 scripts/generate_transform_block_2.py --regen-meta
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
    "2.1": {
        "name_en": "Colors Mix Together",
        "name_ar": "الألوان تمتزج",
        "name_id": "Warna-warni Bercampur",
        "comp": "DanceShapeLong",
        "dur_label": "25 min",
        "props": {
            "bgColor": "#020A18",
            "musicFile": "Heartwarming.mp3",
            "volume": 0.18,
            "shapes": [
                {"shape": "circle", "color": "#E53935", "size": 280, "posX": 0.28, "posY": 0.42,
                 "seed": 1, "orbitRadius": 150, "orbitPeriodSec": 10},
                {"shape": "circle", "color": "#1E88E5", "size": 280, "posX": 0.72, "posY": 0.42,
                 "seed": 2, "orbitRadius": 150, "orbitPeriodSec": 10, "orbitCcw": True},
                {"shape": "circle", "color": "#FDD835", "size": 220, "posX": 0.50, "posY": 0.30,
                 "seed": 3, "orbitRadius": 230, "orbitPeriodSec": 15},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 180,  "motion": "FADEIN"},
                {"startSec": 180,  "endSec": 600,  "motion": "ORBIT",  "orbitCenterX": 0.5, "orbitCenterY": 0.42},
                {"startSec": 600,  "endSec": 1000, "motion": "PULSE",  "period": 5, "amplitude": 20,
                 "colorPalette": RAINBOW[:4], "colorCycleSec": 80},
                {"startSec": 1000, "endSec": 1500, "motion": "ORBIT",  "orbitCenterX": 0.5, "orbitCenterY": 0.42,
                 "colorPalette": RAINBOW, "colorCycleSec": 60},
            ],
        },
    },
    "2.2": {
        "name_en": "The Color Wave",
        "name_ar": "موجة الألوان",
        "name_id": "Gelombang Warna",
        "comp": "DanceShapeLong",
        "dur_label": "25 min",
        "props": {
            "bgColor": "#030C1A",
            "musicFile": "Carefree.mp3",
            "volume": 0.18,
            "shapes": [
                {"shape": "circle", "color": "#E53935", "size": 200, "posX": 0.12, "posY": 0.45, "seed": 1},
                {"shape": "circle", "color": "#FF9800", "size": 195, "posX": 0.27, "posY": 0.45, "seed": 2},
                {"shape": "circle", "color": "#FDD835", "size": 200, "posX": 0.42, "posY": 0.45, "seed": 3},
                {"shape": "circle", "color": "#43A047", "size": 195, "posX": 0.57, "posY": 0.45, "seed": 4},
                {"shape": "circle", "color": "#1E88E5", "size": 200, "posX": 0.72, "posY": 0.45, "seed": 5},
                {"shape": "circle", "color": "#9C27B0", "size": 195, "posX": 0.88, "posY": 0.45, "seed": 6},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 200,  "motion": "FADEIN", "amplitude": 60},
                {"startSec": 200,  "endSec": 600,  "motion": "WAVE",   "period": 3, "amplitude": 60, "waveDelay": 0.35},
                {"startSec": 600,  "endSec": 1000, "motion": "WAVE",   "period": 2, "amplitude": 70, "waveDelay": 0.30,
                 "colorPalette": RAINBOW, "colorCycleSec": 50},
                {"startSec": 1000, "endSec": 1300, "motion": "DRIFT",  "period": 14, "amplitude": 130,
                 "colorPalette": RAINBOW, "colorCycleSec": 55},
                {"startSec": 1300, "endSec": 1500, "motion": "WAVE",   "period": 2.5, "amplitude": 55, "waveDelay": 0.40},
            ],
        },
    },
    "2.3": {
        "name_en": "Rainbow Gathers",
        "name_ar": "قوس قزح يتجمّع",
        "name_id": "Pelangi Berkumpul",
        "comp": "DanceShapeLong",
        "dur_label": "25 min",
        "props": {
            "bgColor": "#020810",
            "musicFile": "Wholesome.mp3",
            "volume": 0.18,
            "shapes": [
                {"shape": "diamond", "color": "#E53935", "size": 220, "posX": 0.18, "posY": 0.38, "seed": 1, "colorOffset": 0.00},
                {"shape": "diamond", "color": "#FF9800", "size": 210, "posX": 0.35, "posY": 0.42, "seed": 2, "colorOffset": 0.14},
                {"shape": "diamond", "color": "#FDD835", "size": 215, "posX": 0.50, "posY": 0.38, "seed": 3, "colorOffset": 0.28},
                {"shape": "diamond", "color": "#43A047", "size": 210, "posX": 0.65, "posY": 0.42, "seed": 4, "colorOffset": 0.42},
                {"shape": "diamond", "color": "#1E88E5", "size": 220, "posX": 0.82, "posY": 0.38, "seed": 5, "colorOffset": 0.57},
                {"shape": "star",    "color": "#9C27B0", "size": 180, "posX": 0.50, "posY": 0.62, "seed": 6, "colorOffset": 0.71},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 200,  "motion": "FADEIN", "amplitude": 100},
                {"startSec": 200,  "endSec": 650,  "motion": "DRIFT",  "period": 14, "amplitude": 180,
                 "colorPalette": RAINBOW, "colorCycleSec": 60},
                {"startSec": 650,  "endSec": 1100, "motion": "SWAY",   "period": 6,  "amplitude": 80,
                 "colorPalette": RAINBOW, "colorCycleSec": 55},
                {"startSec": 1100, "endSec": 1500, "motion": "DRIFT",  "period": 18, "amplitude": 220,
                 "colorPalette": RAINBOW, "colorCycleSec": 50},
            ],
        },
    },
    "2.4": {
        "name_en": "Colorful Surprise",
        "name_ar": "مفاجأة الألوان",
        "name_id": "Kejutan Warna-warni",
        "comp": "DanceShapeLong",
        "dur_label": "25 min",
        "props": {
            "bgColor": "#04100A",
            "musicFile": "Happy Happy Game Show.mp3",
            "volume": 0.18,
            "shapes": [
                {"shape": "circle", "color": "#E53935", "size": 240, "posX": 0.25, "posY": 0.40, "seed": 1, "colorOffset": 0.00},
                {"shape": "circle", "color": "#FF9800", "size": 230, "posX": 0.50, "posY": 0.40, "seed": 2, "colorOffset": 0.20},
                {"shape": "circle", "color": "#1E88E5", "size": 240, "posX": 0.75, "posY": 0.40, "seed": 3, "colorOffset": 0.40},
                {"shape": "star",   "color": "#FDD835", "size": 190, "posX": 0.38, "posY": 0.62, "seed": 4, "colorOffset": 0.60},
                {"shape": "star",   "color": "#43A047", "size": 190, "posX": 0.62, "posY": 0.62, "seed": 5, "colorOffset": 0.80},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 180,  "motion": "FADEIN"},
                {"startSec": 180,  "endSec": 600,  "motion": "BOUNCE", "period": 2.5, "amplitude": 55,
                 "colorPalette": RAINBOW, "colorCycleSec": 45},
                {"startSec": 600,  "endSec": 1000, "motion": "PULSE",  "period": 3,   "amplitude": 22,
                 "colorPalette": RAINBOW, "colorCycleSec": 40},
                {"startSec": 1000, "endSec": 1500, "motion": "DRIFT",  "period": 12,  "amplitude": 200,
                 "colorPalette": RAINBOW, "colorCycleSec": 50},
            ],
        },
    },
}

SERIES_EN = "Transform Block 2: Color"
SERIES_AR = "المجموعة 2: الألوان"
SERIES_ID = "Blok 2: Warna"


def make_meta(video_id: str, lang: str) -> dict:
    v  = VIDEOS[video_id]
    ch = {"en": "@HappyBearKids1", "ar": "@happybearkidsar", "id": "@happybearkidsin"}
    name = v[f"name_{lang}"]
    dur  = v["dur_label"]
    if lang == "en":
        title = f"{name} | {dur} Baby Animation | Happy Bear Kids"
        description = (
            f"✨ {name} — colorful abstract animation for babies!\n\n"
            f"Watch beautiful colors move, blend, and transform across the screen. "
            f"No words, no text — pure visual color exploration.\n\n"
            f"🎯 Age: 0–3 years | Part of the {SERIES_EN} series.\n\n"
            f"🔔 Subscribe → {ch['en']}\n"
            f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
            f"#HappyBearKids #ColorBaby #BabyAnimation #VisualBaby "
            f"#ColorLearn #NoTalking #ToddlerTV #VisualStimulation"
        )
        tags = ["color baby", "baby animation", "happy bear kids", dur,
                "no talking", "visual stimulation", name.lower()]
    elif lang == "ar":
        title = f"{name} | {dur} رسوم ملونة للأطفال | هابي بير كيدز"
        description = (
            f"✨ {name} — رسوم متحركة ملونة للرضع والأطفال!\n\n"
            f"شاهد الألوان الجميلة تتحرك وتمتزج وتتحول. بدون كلمات.\n\n"
            f"جزء من سلسلة {SERIES_AR}.\n\n"
            f"🔔 اشتركوا → {ch['ar']}\n"
            f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
            f"#هابي_بير_كيدز #ألوان #رسوم_أطفال #تحفيز_بصري #بدون_كلام"
        )
        tags = ["هابي بير كيدز", "ألوان", "رسوم أطفال", "تحفيز بصري", name]
    else:
        title = f"{name} | {dur} Animasi Warna Bayi | Happy Bear Kids"
        description = (
            f"✨ {name} — animasi berwarna-warni untuk bayi!\n\n"
            f"Saksikan warna-warna indah bergerak, bercampur, dan berubah. Tanpa kata-kata.\n\n"
            f"Bagian dari seri {SERIES_ID}.\n\n"
            f"🔔 Subscribe → {ch['id']}\n"
            f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
            f"#HappyBearKids #AnimasiWarna #StimulasiBayi #TanpaSuara"
        )
        tags = ["happy bear kids", "animasi warna", "stimulasi bayi", "tanpa suara", name]
    return {"title": title, "description": description, "tags": tags,
            "video_type": "transform", "language": lang, "is_short": False, "status": "public"}


def generate_thumbnail(video_id: str, out_path: Path, lang: str) -> bool:
    if out_path.exists():
        return True
    try:
        key = TOGETHER_KEY_FILE.read_text().strip()
    except Exception:
        return False
    name = VIDEOS[video_id]["name_en"]
    notext = "" if lang in ("en", "id") else ", no text, no letters, no words, no numbers"
    prompt = (
        f"colorful abstract baby animation: {name.lower()}, bright rainbow colors, "
        f"Pixar 3D style, dark background, children's YouTube thumbnail{notext}"
    )
    import urllib.request
    try:
        payload = json.dumps({"model": TOGETHER_MODEL, "prompt": prompt,
                              "width": 1280, "height": 720, "steps": 4, "n": 1}).encode()
        req = urllib.request.Request(TOGETHER_URL, data=payload,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read())
        out_path.write_bytes(base64.b64decode(data["data"][0]["b64_json"]))
        print(f"    ✓ thumb → {out_path.name}")
        return True
    except Exception as e:
        print(f"    ! thumb failed: {e}"); return False


def render_video(video_id: str, force: bool, dry_run: bool) -> Path | None:
    v    = VIDEOS[video_id]
    slug = f"transform2_{video_id.replace('.', '')}_{DATE_STR}.mp4"
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

    print(f"=== Transform Block 2 — {len(ids)} videos ===\n")
    for vid in ids:
        print(f"[{vid}] {VIDEOS[vid]['name_en']}")
        slug = f"transform2_{vid.replace('.', '')}_{DATE_STR}"
        mp4  = QUEUE_EN / f"{slug}.mp4"
        if args.regen_meta:
            distribute(mp4, vid, args.dry_run); continue
        mp4 = render_video(vid, args.force, args.dry_run)
        if mp4 and (mp4.exists() or args.dry_run):
            distribute(mp4, vid, args.dry_run)

    print("\n=== Done ===")


if __name__ == "__main__":
    main()
