#!/usr/bin/env python3
"""
Batch video generator — reads weekly_plan.yaml, generates all videos.

Usage:
    python3 batch_generate.py                             # use default plan
    python3 batch_generate.py --plan config/weekly_plan.yaml
    python3 batch_generate.py --dry-run                  # show what would be generated
    python3 batch_generate.py --only dance               # only dance videos
    python3 batch_generate.py --only abc

Output: output/queue/{video_type}_{theme}_{timestamp}.mp4
         output/queue/thumb_{video_type}_{theme}_{timestamp}.png
"""

import argparse
import subprocess
import sys
import yaml
from datetime import datetime
from pathlib import Path

def write_meta(mp4_path: Path, video_cfg: dict):
    meta_path = mp4_path.parent / f"meta_{mp4_path.stem}.yaml"
    with open(meta_path, "w") as f:
        yaml.dump(video_cfg, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

ROOT = Path(__file__).resolve().parent.parent
QUEUE_DIR = ROOT / "output" / "queue"
SCRIPTS_DIR = ROOT / "config" / "scripts"

sys.path.insert(0, str(ROOT / "scripts"))
from generate_thumbnail import generate_thumbnail  # noqa: E402

COLORS_LIST = ["red", "orange", "yellow", "green", "blue", "purple", "pink", "brown"]
SHAPES_LIST = ["circle", "square", "triangle", "rectangle", "oval", "star", "heart", "diamond"]
LETTER_WORDS = {
    'A': 'Apple',    'B': 'Bear',     'C': 'Cat',      'D': 'Dog',
    'E': 'Elephant', 'F': 'Fish',     'G': 'Giraffe',  'H': 'Horse',
    'I': 'Iguana',   'J': 'Jaguar',   'K': 'Kangaroo', 'L': 'Lion',
    'M': 'Monkey',   'N': 'Narwhal',  'O': 'Owl',      'P': 'Panda',
    'Q': 'Quail',    'R': 'Rabbit',   'S': 'Sheep',    'T': 'Tiger',
    'U': 'Unicorn',  'V': 'Vulture',  'W': 'Wolf',     'X': 'X-ray',
    'Y': 'Yak',      'Z': 'Zebra',
}

TEMPLATE_MAP = {
    "dance":          ROOT / "config" / "scene_templates" / "default.yaml",
    "abc":            ROOT / "config" / "scene_templates" / "abc.yaml",
    "numbers":        ROOT / "config" / "scene_templates" / "numbers.yaml",
    "colors":         ROOT / "config" / "scene_templates" / "colors.yaml",
    # Shorts templates (60s, vertical 9:16)
    # short_letter cycles through 5 templates — see LETTER_TEMPLATES below
    "short_letter":     ROOT / "config" / "scene_templates" / "shorts_letter.yaml",
    "short_number":     ROOT / "config" / "scene_templates" / "shorts_number.yaml",
    "short_color":      ROOT / "config" / "scene_templates" / "shorts_color.yaml",
    "short_shape":      ROOT / "config" / "scene_templates" / "shorts_shape.yaml",
    "short_dance":      ROOT / "config" / "scene_templates" / "shorts_dance.yaml",
    "short_vocabulary": ROOT / "config" / "scene_templates" / "shorts_vocabulary.yaml",
    "short_counting":   ROOT / "config" / "scene_templates" / "shorts_counting.yaml",
}

# Letter group templates — cycled by variant_idx % 5
LETTER_TEMPLATES = [
    ROOT / "config" / "scene_templates" / "shorts_letter.yaml",      # A-E
    ROOT / "config" / "scene_templates" / "shorts_letter_fj.yaml",   # F-J
    ROOT / "config" / "scene_templates" / "shorts_letter_ko.yaml",   # K-O
    ROOT / "config" / "scene_templates" / "shorts_letter_pt.yaml",   # P-T
    ROOT / "config" / "scene_templates" / "shorts_letter_uz.yaml",   # U-Z
]
LETTER_START = ["A", "F", "K", "P", "U"]  # first letter of each group

# Types that should always render as vertical Shorts
SHORTS_TYPES = {
    "short_letter", "short_number", "short_color", "short_shape", "short_dance",
    "short_vocabulary", "short_counting",
}


def make_thumbnail(video_cfg: dict, mp4_path: Path, variant: int = 0) -> Path | None:
    video_type = video_cfg["video_type"]
    theme      = video_cfg.get("theme", "animals")
    title      = video_cfg["title"]
    is_shorts  = video_cfg.get("is_shorts", video_type in SHORTS_TYPES)

    letter = word = number = color = shape = ""

    if video_type == "short_letter":
        letter = LETTER_START[variant % len(LETTER_START)]
        word   = LETTER_WORDS.get(letter, letter)
    elif video_type == "abc":
        letter = chr(ord('A') + (variant % 26))
        word   = LETTER_WORDS.get(letter, letter)
    elif video_type in ("numbers", "short_number", "short_counting"):
        number = str((variant % 5) + 1)
    elif video_type in ("colors", "short_color"):
        color  = COLORS_LIST[variant % len(COLORS_LIST)]
    elif video_type == "short_shape":
        shape  = SHAPES_LIST[variant % len(SHAPES_LIST)]
        theme  = "shapes"
    # short_vocabulary uses thumb_generic (animals)

    thumb_path = mp4_path.parent / f"thumb_{mp4_path.stem}.png"
    try:
        generate_thumbnail(
            video_type=video_type, theme=theme, title=title,
            out_path=thumb_path, variant=variant,
            letter=letter, word=word, number=number,
            color=color, shape=shape, is_shorts=is_shorts,
        )
        return thumb_path
    except Exception as exc:
        print(f"  WARNING: thumbnail failed: {exc}")
        return None


def run_script(cmd: list, description: str) -> bool:
    print(f"\n  → {description}")
    print(f"    {' '.join(str(c) for c in cmd)}")
    result = subprocess.run(cmd, capture_output=False)
    if result.returncode != 0:
        print(f"  ERROR: {description} failed (exit {result.returncode})")
        return False
    return True


def generate_video(video_cfg: dict, dry_run: bool = False, variant_idx: int = 0) -> Path | None:
    title       = video_cfg["title"]
    video_type  = video_cfg["video_type"]
    theme       = video_cfg.get("theme", "animals")
    duration    = video_cfg.get("duration_minutes", 1)
    is_shorts   = video_cfg.get("is_shorts", video_type in SHORTS_TYPES)

    # Shape short uses shapes sprite theme
    if video_type == "short_shape":
        theme = "shapes"

    template = TEMPLATE_MAP.get(video_type)
    if video_type == "short_letter":
        template = LETTER_TEMPLATES[variant_idx % len(LETTER_TEMPLATES)]
    if not template:
        print(f"  Unknown video_type: {video_type}, skipping")
        return None

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = "_short" if is_shorts else ""
    output_path = QUEUE_DIR / f"{video_type}_{theme}{suffix}_{ts}.mp4"

    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"  type={video_type}  theme={theme}  duration={duration}min  shorts={is_shorts}")
    print(f"{'─'*60}")

    if dry_run:
        print(f"  [DRY RUN] would generate → {output_path.name}")
        return output_path

    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

    # Step 1: generate episode script
    ok = run_script(
        [sys.executable, str(ROOT / "scripts" / "generate_script.py"),
         "--duration", str(duration),
         "--theme", theme,
         "--template", str(template),
         "--output-dir", str(SCRIPTS_DIR)],
        f"Generating script ({duration}min, {theme})"
    )
    if not ok:
        return None

    # Find the just-generated script (latest in dir)
    scripts = sorted(SCRIPTS_DIR.glob("episode_*.yaml"), key=lambda p: p.stat().st_mtime)
    if not scripts:
        print("  ERROR: no script generated")
        return None
    latest_script = scripts[-1]

    # Step 2: generate video
    cmd = [
        sys.executable, str(ROOT / "scripts" / "generate_video.py"),
        "--theme", theme,
        "--script", str(latest_script),
        "--output", str(output_path),
    ]
    if is_shorts:
        cmd.append("--shorts")

    ok = run_script(cmd, f"Rendering video → {output_path.name}")
    if not ok:
        return None

    size_mb = output_path.stat().st_size / 1_000_000 if output_path.exists() else 0
    print(f"\n  ✓ Done: {output_path.name} ({size_mb:.1f} MB)")

    # Step 3: thumbnail
    thumb = make_thumbnail(video_cfg, output_path, variant=variant_idx)
    if thumb:
        print(f"  ✓ Thumbnail: {thumb.name}")

    # Step 4: metadata sidecar (for scheduled publishing)
    write_meta(output_path, video_cfg)

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Batch video generator")
    parser.add_argument("--plan", default=str(ROOT / "config" / "weekly_plan.yaml"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--only", help="Filter by video_type (dance, abc, etc.)")
    args = parser.parse_args()

    plan_path = Path(args.plan)
    if not plan_path.exists():
        print(f"Plan not found: {plan_path}")
        sys.exit(1)

    with open(plan_path) as f:
        plan = yaml.safe_load(f)

    videos = plan.get("videos", [])
    if args.only:
        videos = [v for v in videos if v.get("video_type") == args.only]

    print(f"\nBatch generator — {len(videos)} video(s) to produce")
    if args.dry_run:
        print("DRY RUN mode\n")

    generated = []
    failed = []
    type_variants: dict[str, int] = {}  # per-type variant counter

    for i, video_cfg in enumerate(videos, 1):
        vtype = video_cfg.get("video_type", "dance")
        vi = type_variants.get(vtype, 0)
        type_variants[vtype] = vi + 1

        print(f"\n[{i}/{len(videos)}]", end="")
        result = generate_video(video_cfg, dry_run=args.dry_run, variant_idx=vi)
        if result:
            generated.append(result)
        else:
            failed.append(video_cfg.get("title", "?"))

    print(f"\n{'='*60}")
    print(f"  Generated: {len(generated)}")
    if failed:
        print(f"  Failed:    {len(failed)}")
        for f in failed:
            print(f"    - {f}")
    print(f"  Queue dir: {QUEUE_DIR}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
