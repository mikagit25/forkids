#!/usr/bin/env python3
"""
generate_transform_block_4.py — Transform Block 4: Patterns and Symmetry
4 videos × 20-25 min → EN + AR + ID queues.

Videos:
  4.1  Fruit Kaleidoscope  (TransformLong kaleidoscope mode)
  4.2  Mirror World        (DanceShapeLong symmetric pairs)
  4.3  Chaos to Order      (DanceShapeLong DRIFT → MARCH)
  4.4  Sort by Size        (DanceShapeLong multi-size SWAY)

Usage:
  python3 scripts/generate_transform_block_4.py --list
  python3 scripts/generate_transform_block_4.py --videos all [--dry-run] [--force]
  python3 scripts/generate_transform_block_4.py --regen-meta
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
    "4.1": {
        "name_en": "Fruit Kaleidoscope",
        "name_ar": "كالايدوسكوب الفواكه",
        "name_id": "Kaleidoskop Buah-buahan",
        "comp": "TransformLong",
        "dur_label": "20 min",
        "props": {
            "mode": "kaleidoscope",
            "bgColor": "#040C18",
            "accentColor": "#FFD700",
            "musicFile": "Merry Go.mp3",
            "volume": 0.18,
            "cycleDuration": 60,
            "spriteSize": 210,
            "spritePaths": [
                "fruits/apple.png",
                "fruits/orange.png",
                "fruits/banana.png",
                "fruits/strawberry.png",
                "fruits/grapes.png",
                "fruits/lemon.png",
            ],
            "seed": 41,
        },
    },
    "4.2": {
        "name_en": "Mirror World",
        "name_ar": "عالم المرايا",
        "name_id": "Dunia Cermin",
        "comp": "DanceShapeLong",
        "dur_label": "25 min",
        "props": {
            "bgColor": "#080814",
            "musicFile": "Heartwarming.mp3",
            "volume": 0.18,
            "shapes": [
                # Left side
                {"shape": "star",    "color": "#FFD700", "size": 200, "posX": 0.20, "posY": 0.42, "seed": 1},
                {"shape": "circle",  "color": "#E53935", "size": 175, "posX": 0.32, "posY": 0.55, "seed": 2},
                {"shape": "diamond", "color": "#1E88E5", "size": 185, "posX": 0.22, "posY": 0.62, "seed": 3},
                # Right side (mirrored — same seeds offset by 10)
                {"shape": "star",    "color": "#FFD700", "size": 200, "posX": 0.80, "posY": 0.42, "seed": 11},
                {"shape": "circle",  "color": "#E53935", "size": 175, "posX": 0.68, "posY": 0.55, "seed": 12},
                {"shape": "diamond", "color": "#1E88E5", "size": 185, "posX": 0.78, "posY": 0.62, "seed": 13},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 250,  "motion": "FADEIN", "amplitude": 70},
                {"startSec": 250,  "endSec": 700,  "motion": "SWAY",   "period": 5, "amplitude": 60},
                {"startSec": 700,  "endSec": 1100, "motion": "BOB",    "period": 4, "amplitude": 45,
                 "colorPalette": RAINBOW, "colorCycleSec": 65},
                {"startSec": 1100, "endSec": 1500, "motion": "DRIFT",  "period": 14, "amplitude": 130,
                 "colorPalette": RAINBOW, "colorCycleSec": 60},
            ],
        },
    },
    "4.3": {
        "name_en": "Chaos to Order",
        "name_ar": "من الفوضى إلى النظام",
        "name_id": "Dari Kekacauan ke Keteraturan",
        "comp": "DanceShapeLong",
        "dur_label": "25 min",
        "props": {
            "bgColor": "#06080E",
            "musicFile": "Life of Riley.mp3",
            "volume": 0.18,
            "shapes": [
                {"shape": "circle",   "color": "#E53935", "size": 160, "posX": 0.12, "posY": 0.42, "seed": 1},
                {"shape": "square",   "color": "#FF9800", "size": 150, "posX": 0.25, "posY": 0.42, "seed": 2},
                {"shape": "triangle", "color": "#FDD835", "size": 155, "posX": 0.38, "posY": 0.42, "seed": 3},
                {"shape": "star",     "color": "#43A047", "size": 150, "posX": 0.51, "posY": 0.42, "seed": 4},
                {"shape": "diamond",  "color": "#1E88E5", "size": 155, "posX": 0.64, "posY": 0.42, "seed": 5},
                {"shape": "hexagon",  "color": "#9C27B0", "size": 150, "posX": 0.77, "posY": 0.42, "seed": 6},
                {"shape": "circle",   "color": "#E91E63", "size": 155, "posX": 0.90, "posY": 0.42, "seed": 7},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 200,  "motion": "FADEIN", "amplitude": 120},
                {"startSec": 200,  "endSec": 600,  "motion": "DRIFT",  "period": 10, "amplitude": 250},
                {"startSec": 600,  "endSec": 900,  "motion": "BOUNCE", "period": 2,  "amplitude": 60},
                {"startSec": 900,  "endSec": 1200, "motion": "MARCH",  "period": 14, "bobAmplitude": 20},
                {"startSec": 1200, "endSec": 1500, "motion": "WAVE",   "period": 3,  "amplitude": 55, "waveDelay": 0.35},
            ],
        },
    },
    "4.4": {
        "name_en": "Big, Medium, Small",
        "name_ar": "كبير، متوسط، صغير",
        "name_id": "Besar, Sedang, Kecil",
        "comp": "DanceShapeLong",
        "dur_label": "25 min",
        "props": {
            "bgColor": "#04080E",
            "musicFile": "Wholesome.mp3",
            "volume": 0.18,
            "shapes": [
                # Big shapes
                {"shape": "circle",  "color": "#E53935", "size": 320, "posX": 0.18, "posY": 0.40, "seed": 1},
                {"shape": "square",  "color": "#1E88E5", "size": 310, "posX": 0.82, "posY": 0.40, "seed": 2},
                # Medium shapes
                {"shape": "star",    "color": "#FDD835", "size": 200, "posX": 0.40, "posY": 0.42, "seed": 3},
                {"shape": "diamond", "color": "#43A047", "size": 195, "posX": 0.60, "posY": 0.42, "seed": 4},
                # Small shapes
                {"shape": "circle",  "color": "#9C27B0", "size": 100, "posX": 0.30, "posY": 0.62, "seed": 5},
                {"shape": "square",  "color": "#FF9800", "size": 95,  "posX": 0.50, "posY": 0.62, "seed": 6},
                {"shape": "star",    "color": "#E91E63", "size": 100, "posX": 0.70, "posY": 0.62, "seed": 7},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 250,  "motion": "FADEIN"},
                {"startSec": 250,  "endSec": 700,  "motion": "SWAY",   "period": 5, "amplitude": 50},
                {"startSec": 700,  "endSec": 1100, "motion": "PULSE",  "period": 4, "amplitude": 20,
                 "colorPalette": RAINBOW, "colorCycleSec": 60},
                {"startSec": 1100, "endSec": 1500, "motion": "BOB",    "period": 4, "amplitude": 40,
                 "colorPalette": RAINBOW, "colorCycleSec": 55},
            ],
        },
    },
}

SERIES_EN = "Transform Block 4: Patterns and Symmetry"
SERIES_AR = "المجموعة 4: الأنماط والتناسق"
SERIES_ID = "Blok 4: Pola dan Simetri"

PROMPTS = {
    "4.1": "beautiful kaleidoscope made of colorful cartoon fruits, mandala pattern, dark background, children's animation",
    "4.2": "colorful 3D shapes arranged symmetrically like a mirror, dark background, children's animation",
    "4.3": "colorful 3D shapes moving from chaos into perfect order, dark background, children's animation",
    "4.4": "colorful 3D shapes of three different sizes arranged neatly, dark background, children's animation",
}


def make_meta(video_id: str, lang: str) -> dict:
    v  = VIDEOS[video_id]
    ch = {"en": "@HappyBearKids1", "ar": "@happybearkidsar", "id": "@happybearkidsin"}
    name = v[f"name_{lang}"]
    dur  = v["dur_label"]
    if lang == "en":
        title = f"{name} | {dur} Baby Animation | Happy Bear Kids"
        description = (
            f"✨ {name} — beautiful patterns and symmetry for babies!\n\n"
            f"Watch shapes arrange themselves into beautiful symmetric patterns. "
            f"No words, no text — pure visual pattern exploration.\n\n"
            f"🎯 Age: 0–3 years | Part of the {SERIES_EN} series.\n\n"
            f"🔔 Subscribe → {ch['en']}\n"
            f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
            f"#HappyBearKids #PatternBaby #BabyAnimation #SymmetryBaby "
            f"#NoTalking #ToddlerTV #VisualStimulation"
        )
        tags = ["pattern baby", "baby animation", "symmetry", "happy bear kids", dur,
                "no talking", "visual stimulation", name.lower()]
    elif lang == "ar":
        title = f"{name} | {dur} رسوم أطفال | هابي بير كيدز"
        description = (
            f"✨ {name} — أنماط وتناسق رائع للرضع والأطفال!\n\n"
            f"شاهد الأشكال تترتب في أنماط متماثلة جميلة. بدون كلمات.\n\n"
            f"جزء من سلسلة {SERIES_AR}.\n\n"
            f"🔔 اشتركوا → {ch['ar']}\n"
            f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
            f"#هابي_بير_كيدز #أنماط #رسوم_أطفال #تحفيز_بصري #بدون_كلام"
        )
        tags = ["هابي بير كيدز", "أنماط", "رسوم أطفال", "تحفيز بصري", name]
    else:
        title = f"{name} | {dur} Animasi Bayi | Happy Bear Kids"
        description = (
            f"✨ {name} — pola dan simetri yang indah untuk bayi!\n\n"
            f"Saksikan bentuk-bentuk tersusun menjadi pola simetris yang cantik. Tanpa kata-kata.\n\n"
            f"Bagian dari seri {SERIES_ID}.\n\n"
            f"🔔 Subscribe → {ch['id']}\n"
            f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
            f"#HappyBearKids #PolaBentuk #StimulasiBayi #TanpaSuara"
        )
        tags = ["happy bear kids", "pola bentuk", "stimulasi bayi", "tanpa suara", name]
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
    slug = f"transform4_{video_id.replace('.', '')}_{DATE_STR}.mp4"
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

    print(f"=== Transform Block 4 — {len(ids)} videos ===\n")
    for vid in ids:
        print(f"[{vid}] {VIDEOS[vid]['name_en']}")
        slug = f"transform4_{vid.replace('.', '')}_{DATE_STR}"
        mp4  = QUEUE_EN / f"{slug}.mp4"
        if args.regen_meta:
            distribute(mp4, vid, args.dry_run); continue
        mp4 = render_video(vid, args.force, args.dry_run)
        if mp4 and (mp4.exists() or args.dry_run):
            distribute(mp4, vid, args.dry_run)

    print("\n=== Done ===")


if __name__ == "__main__":
    main()
