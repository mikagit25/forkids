#!/usr/bin/env python3
"""
Generate ShapeDance shorts using Remotion.
Single shape or multi-shape combos bouncing to a beat.
Output: output/queue/short_dance_shapes_{combo}_{date}.mp4

Usage:
  python3 scripts/generate_shape_dance_shorts.py
  python3 scripts/generate_shape_dance_shorts.py --combos circle square+circle+triangle
"""
import argparse
import json
import subprocess
import yaml
from datetime import datetime
from pathlib import Path

ROOT      = Path(__file__).resolve().parent.parent
REMOTION  = ROOT / "remotion"
QUEUE_DIR = ROOT / "output" / "queue"

# Color per shape
SHAPE_COLORS = {
    "circle":   "#E74C3C",
    "square":   "#27AE60",
    "triangle": "#2980B9",
    "star":     "#F39C12",
    "diamond":  "#8E44AD",
    "heart":    "#E91E63",
    "hexagon":  "#00897B",
    "oval":     "#5C6BC0",
}

# Predefined combos: name → [shapes]
COMBOS = {
    "circle":                    ["circle"],
    "square":                    ["square"],
    "triangle":                  ["triangle"],
    "star":                      ["star"],
    "diamond":                   ["diamond"],
    "heart":                     ["heart"],
    "circle_square":             ["circle", "square"],
    "square_triangle":           ["square", "triangle"],
    "circle_triangle":           ["circle", "triangle"],
    "circle_square_triangle":    ["circle", "square", "triangle"],
    "star_circle_square":        ["star", "circle", "square"],
    "heart_star_circle":         ["heart", "star", "circle"],
    "all_four":                  ["circle", "square", "triangle", "star"],
}

MUSIC_TRACKS = [
    "Quirky Dog.mp3", "Monkeys Spinning Monkeys.mp3", "Happy Happy Game Show.mp3",
    "Hyperfun.mp3", "Sneaky Snitch.mp3", "Pinball Spring.mp3",
]

BG_COLORS = {
    "circle":                 "#FFFDE7",
    "square":                 "#F1F8E9",
    "triangle":               "#E3F2FD",
    "star":                   "#FFF9C4",
    "diamond":                "#F3E5F5",
    "heart":                  "#FCE4EC",
    "circle_square":          "#FFFDE7",
    "square_triangle":        "#E8F5E9",
    "circle_triangle":        "#E3F2FD",
    "circle_square_triangle": "#FFFFF0",
    "star_circle_square":     "#FFFDE7",
    "heart_star_circle":      "#FFF0F5",
    "all_four":               "#FAFAFA",
}


def pick_music(idx: int) -> str:
    return MUSIC_TRACKS[idx % len(MUSIC_TRACKS)]


def make_meta(combo: str, shapes: list, out_path: Path):
    shape_str = " & ".join(s.capitalize() for s in shapes)
    meta = {
        "title":            f"{shape_str} | Dancing Shapes for Kids | Happy Bear Kids #shorts",
        "video_type":       "short_shape_dance",
        "theme":            "shapes",
        "language":         "en",
        "duration_minutes": 1,
        "is_short":         True,
        "tags":             [
            "shapes for kids", "dancing shapes", "shape dance",
            *[s for s in shapes],
            "toddler learning", "preschool", "happy bear kids",
            "educational", "shorts",
        ],
        "status": "public",
    }
    meta_path = out_path.parent / f"meta_{out_path.stem}.yaml"
    with open(meta_path, "w") as f:
        yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def render(combo: str, shapes: list, date_str: str, force: bool, idx: int) -> bool:
    out_name = f"short_sdance_{combo}_{date_str}.mp4"
    out_path = QUEUE_DIR / out_name

    if out_path.exists() and not force:
        print(f"  [{combo}] skip (exists)")
        return True

    colors = [SHAPE_COLORS.get(s, "#888888") for s in shapes]
    bg     = BG_COLORS.get(combo, "#FAFAFA")
    music  = pick_music(idx)

    props = {
        "shapes":     shapes,
        "colors":     colors,
        "bgColor":    bg,
        "bpm":        100 + (idx % 4) * 10,   # 100–130 BPM variety
        "showLabels": True,
        "audioFile":  None,
        "musicFile":  music,
    }

    shape_label = "+".join(shapes)
    print(f"  [{shape_label:30}]", end="  ", flush=True)
    cmd = [
        "npx", "remotion", "render",
        "src/index.ts", "ShapeDanceShort",
        str(out_path),
        "--props", json.dumps(props),
        "--log", "error",
        "--video-image-format=jpeg",
        "--jpeg-quality=85",
        "--concurrency=4",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REMOTION))
    if result.returncode == 0 and out_path.exists():
        size_mb = out_path.stat().st_size / 1024 / 1024
        print(f"✓  {out_name}  {size_mb:.1f}MB")
        make_meta(combo, shapes, out_path)
        return True
    err = (result.stderr or result.stdout)[-200:].strip()
    print(f"✗  {err}")
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--combos", nargs="+", default=list(COMBOS.keys()),
                        help="Combo names from COMBOS dict, or 'shape1+shape2'")
    parser.add_argument("--force",  action="store_true")
    args = parser.parse_args()

    # Allow inline combos like "circle+square"
    combos_to_run = {}
    for c in args.combos:
        if "+" in c:
            parts = c.split("+")
            key = "_".join(parts)
            combos_to_run[key] = parts
        elif c in COMBOS:
            combos_to_run[c] = COMBOS[c]

    date_str = datetime.now().strftime("%Y%m%d")
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\nGenerating {len(combos_to_run)} ShapeDance shorts\n")

    ok = 0
    for idx, (combo, shapes) in enumerate(combos_to_run.items()):
        if render(combo, shapes, date_str, args.force, idx):
            ok += 1

    print(f"\nDone: {ok}/{len(combos_to_run)} shape dance shorts generated")


if __name__ == "__main__":
    main()
