#!/usr/bin/env python3
"""
Generate SortFixLong — shape sorting game for kids.

Each round (~5 s): wrong shape tries the slot (buzz+shake+✕),
then the right shape snaps in with ding+sparkles.

Default: 216 rounds ≈ 18 min.  Output goes to EN + AR queues (no text).

Usage:
    python3 scripts/generate_sort_fix.py
    python3 scripts/generate_sort_fix.py --rounds 216 --seed 42 --dry-run
    python3 scripts/generate_sort_fix.py --rounds 60 --music "Wholesome.mp3"
"""
import argparse
import json
import random
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

ROOT     = Path(__file__).resolve().parent.parent
REMOTION = ROOT / "remotion"
QUEUE_EN = ROOT / "output" / "queue"
QUEUE_AR = ROOT / "output" / "queue_ar"

FPS          = 30
ROUND_FRAMES = 150   # 5 s per round

SHAPES = ["star", "circle", "square", "triangle"]

SLOT_COLORS = [
    "#FF6B6B",  # coral red
    "#4ECDC4",  # teal
    "#45B7D1",  # sky blue
    "#FED766",  # warm yellow
    "#9B59B6",  # purple
    "#2ECC71",  # green
    "#E67E22",  # orange
    "#E91E63",  # pink
]


def generate_rounds(n: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    rounds = []
    for i in range(n):
        slot_shape = SHAPES[i % len(SHAPES)]
        slot_color = SLOT_COLORS[i % len(SLOT_COLORS)]
        wrong_shape = rng.choice([s for s in SHAPES if s != slot_shape])
        wrong_color = rng.choice([c for c in SLOT_COLORS if c != slot_color])
        rounds.append({
            "slotShape":  slot_shape,
            "slotColor":  slot_color,
            "wrongShape": wrong_shape,
            "wrongColor": wrong_color,
        })
    return rounds


def make_meta(n_rounds: int, lang: str, out_path: Path) -> None:
    duration_sec = (n_rounds * ROUND_FRAMES) // FPS
    duration_min = duration_sec // 60

    if lang == "ar":
        title = f"العب مع الأشكال! ⭐ {duration_min} دقيقة | تعلم الأشكال للأطفال"
        description = (
            "لعبة فرز الأشكال الممتعة للأطفال الصغار! "
            "شاهد الشكل الصحيح وهو يندمج في المكان المناسب مع صوت رنين ممتع! "
            f"تحتوي على {n_rounds} جولة من فرز الأشكال: النجوم والدوائر والمربعات والمثلثات.\n\n"
            "مثالي للأطفال من 0-5 سنوات. بدون نص، مناسب لجميع اللغات.\n\n"
            "#أشكال #تعليم_أطفال #أطفال #تعلم_الأشكال #هابي_بير_كيدز"
        )
        tags = [
            "أشكال للأطفال", "تعلم الأشكال", "فرز الأشكال", "ألعاب أطفال",
            "تعليم الأطفال", "نجمة دائرة مربع", "فيديو أطفال", "هابي بير",
            "أشكال هندسية", "تعليمي", "children shapes arabic",
        ]
    else:
        title = f"Find the Right Shape! ⭐ {duration_min} min | Shape Sorting for Toddlers"
        description = (
            f"Fun shape sorting game for babies and toddlers! "
            f"Watch as the right shape snaps into the slot with a satisfying ding! "
            f"Features {n_rounds} rounds of shape matching: stars, circles, squares, and triangles.\n\n"
            "Each round shows a shape slot — a wrong shape tries to fit in (buzz! ✕) "
            "and then the correct shape snaps into place with sparkles and a chime!\n\n"
            "Perfect for babies, toddlers, and preschoolers aged 0–5 years. "
            "No text, suitable for all languages.\n\n"
            "Watch more Happy Bear Kids videos for fun, engaging learning!\n\n"
            "🎵 Original music by Happy Bear Kids (AI-generated, © 2026)\n\n"
            "#shapes #toddlers #preschool #learning #shapesfortoddlers "
            "#kidslearning #educational #happybearkids #shapesorting #babyvideo"
        )
        tags = [
            "shapes for kids", "shape sorting", "toddler learning", "preschool shapes",
            "kids educational video", "shape game", "circle square triangle star",
            "baby shapes", "learning shapes", "shape puzzle", "kids shapes video",
            "educational for toddlers", "shape activities", "sorting game",
            "happy bear kids", "shapes and colors", "toddler video",
            "preschool learning", "shape recognition", "shape matching game",
        ]

    meta = {
        "title":        title,
        "description":  description,
        "tags":         tags,
        "video_type":   "sort_fix",
        "language":     lang,
        "is_short":     False,
        "status":       "public",
        "made_for_kids": True,
        "duration_sec": duration_sec,
        "duration_min": duration_min,
        "n_rounds":     n_rounds,
        "ai_generated": True,
    }
    out_path.write_text(yaml.dump(meta, allow_unicode=True, default_flow_style=False))


def render(props: dict, out_path: Path, n_rounds: int, dry_run: bool) -> bool:
    total_frames = n_rounds * ROUND_FRAMES
    cmd = [
        "npx", "remotion", "render",
        "src/index.ts", "SortFixLong",
        str(out_path),
        "--props", json.dumps(props),
        "--frames", f"0-{total_frames - 1}",
        "--concurrency", "1",
        "--log", "error",
    ]
    dur_min = (total_frames // FPS) // 60
    print(f"  Rendering {n_rounds} rounds × {ROUND_FRAMES}f = {total_frames}f ({dur_min} min) → {out_path.name}")
    if dry_run:
        print(f"  [DRY RUN] {' '.join(cmd[:6])} ...")
        return True
    res = subprocess.run(cmd, cwd=str(REMOTION), capture_output=True, text=True, timeout=7200)
    if res.returncode != 0:
        print(f"  ✗ Render failed:\n{res.stderr[-800:]}")
        return False
    sz = out_path.stat().st_size // 1024 // 1024
    print(f"  ✓ Rendered ({sz} MB)")
    return True


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds",       type=int,   default=216,
                    help="Number of rounds (216 = ~18 min, 60 = ~5 min)")
    ap.add_argument("--seed",         type=int,   default=42)
    ap.add_argument("--music",        default="Monkeys Spinning Monkeys.mp3")
    ap.add_argument("--music-volume", type=float, default=0.20)
    ap.add_argument("--bg-color",     default="#FFF8E1")
    ap.add_argument("--lang",         default="kids", choices=["en", "ar", "kids"],
                    help="kids = both EN+AR queues")
    ap.add_argument("--dry-run",      action="store_true")
    args = ap.parse_args()

    rounds = generate_rounds(args.rounds, seed=args.seed)
    print(f"SortFixLong: {args.rounds} rounds ≈ {args.rounds * ROUND_FRAMES // FPS // 60} min")

    props = {
        "rounds":      rounds,
        "musicFile":   args.music,
        "musicVolume": args.music_volume,
        "bgColor":     args.bg_color,
    }

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    targets = []
    if args.lang in ("en", "kids"):
        QUEUE_EN.mkdir(parents=True, exist_ok=True)
        targets.append(("en", QUEUE_EN))
    if args.lang in ("ar", "kids"):
        QUEUE_AR.mkdir(parents=True, exist_ok=True)
        targets.append(("ar", QUEUE_AR))

    # Render once; for "kids" (no text) copy the same video to both queues
    first_lang, first_queue = targets[0]
    basename_en = f"sort_fix_{first_lang}_{stamp}"
    out_mp4_first = first_queue / f"{basename_en}.mp4"
    out_meta_first = first_queue / f"meta_{basename_en}.yaml"

    print(f"\n── Render → {first_queue.name} ──")
    if not render(props, out_mp4_first, args.rounds, args.dry_run):
        sys.exit(1)
    make_meta(args.rounds, first_lang, out_meta_first)
    print(f"  ✓ Meta: {out_meta_first.name}")

    # Copy to remaining queues (video has no text → same file works everywhere)
    import shutil
    for lang, queue in targets[1:]:
        basename = f"sort_fix_{lang}_{stamp}"
        out_mp4  = queue / f"{basename}.mp4"
        out_meta = queue / f"meta_{basename}.yaml"
        print(f"\n── Copy → {queue.name} ──")
        if not args.dry_run:
            shutil.copy2(out_mp4_first, out_mp4)
            sz = out_mp4.stat().st_size // 1024 // 1024
            print(f"  ✓ Copied ({sz} MB) → {out_mp4.name}")
        else:
            print(f"  [DRY RUN] Would copy → {out_mp4.name}")
        make_meta(args.rounds, lang, out_meta)
        print(f"  ✓ Meta: {out_meta.name}")

    print("\nDone.")


if __name__ == "__main__":
    main()
