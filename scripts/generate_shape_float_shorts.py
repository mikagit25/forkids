#!/usr/bin/env python3
"""
Generate ShapeFloat shorts using Remotion.
Each shape × each mode = one 55s short.
Output: output/queue/short_float_{shape}_{mode}_{date}.mp4

Usage:
  python3 scripts/generate_shape_float_shorts.py
  python3 scripts/generate_shape_float_shorts.py --shapes circle square --modes tb lr
"""
import argparse
import json
import subprocess
import sys
import yaml
from datetime import datetime
from pathlib import Path

ROOT      = Path(__file__).resolve().parent.parent
REMOTION  = ROOT / "remotion"
QUEUE_DIR = ROOT / "output" / "queue"

SHAPES = {
    "circle":   {"color": "#2980B9", "bg": "#E3F2FD",
                 "audio": "circle__this_is_a_circle__a_circle.mp3"},
    "square":   {"color": "#27AE60", "bg": "#E8F5E9",
                 "audio": "square__this_is_a_square__a_square.mp3"},
    "triangle": {"color": "#E67E22", "bg": "#FFF3E0",
                 "audio": "triangle__this_is_a_triangle__a_triangle.mp3"},
    "star":     {"color": "#F39C12", "bg": "#FFFDE7",
                 "audio": "star__this_is_a_star__a_star.mp3"},
    "diamond":  {"color": "#8E44AD", "bg": "#F3E5F5",
                 "audio": "diamond__this_is_a_diamond__a_diamond.mp3"},
    "heart":    {"color": "#E74C3C", "bg": "#FFEBEE",
                 "audio": "heart__this_is_a_heart__a_heart.mp3"},
    "hexagon":  {"color": "#16A085", "bg": "#E0F7FA",
                 "audio": None},
    "oval":     {"color": "#2980B9", "bg": "#EDE7F6",
                 "audio": "oval__this_is_a_oval__a_oval.mp3"},
}

MODES = {
    "tb":    {"count": 6,  "speed": "slow",   "label": "rain"},
    "lr":    {"count": 4,  "speed": "medium", "label": "lr"},
    "diag":  {"count": 5,  "speed": "medium", "label": "diag"},
    "float": {"count": 7,  "speed": "slow",   "label": "float"},
}

MUSIC_TRACKS = [
    "Carefree.mp3", "Wholesome.mp3", "Life of Riley.mp3",
    "Merry Go.mp3", "Pinball Spring.mp3", "Walking Along.mp3",
]


def pick_music(seed: int) -> str:
    return MUSIC_TRACKS[seed % len(MUSIC_TRACKS)]


def make_meta(shape: str, mode: str, out_path: Path):
    shape_cap = shape.capitalize()
    meta = {
        "title":            f"{shape_cap} Shape | {mode.upper()} | Shapes for Kids | Happy Bear Kids #shorts",
        "video_type":       "short_shape_float",
        "theme":            "shapes",
        "language":         "en",
        "duration_minutes": 1,
        "is_short":         True,
        "tags":             [
            "shapes for kids", shape, f"{shape} shape", "shape learning",
            "toddler learning", "preschool shapes", "happy bear kids",
            "educational", "shorts", "geometry for kids",
        ],
        "status": "public",
    }
    meta_path = out_path.parent / f"meta_{out_path.stem}.yaml"
    with open(meta_path, "w") as f:
        yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def render(shape: str, mode: str, date_str: str, force: bool) -> bool:
    data     = SHAPES[shape]
    mdata    = MODES[mode]
    out_name = f"short_float_{shape}_{mode}_{date_str}.mp4"
    out_path = QUEUE_DIR / out_name

    if out_path.exists() and not force:
        print(f"  [{shape}/{mode}] skip (exists)")
        return True

    seed = list(SHAPES.keys()).index(shape)
    props = {
        "shapeName":   shape,
        "shapeColor":  data["color"],
        "bgColor":     data["bg"],
        "mode":        mode,
        "count":       mdata["count"],
        "showLabel":   True,
        "audioFile":   data["audio"],
        "musicFile":   pick_music(seed),
        "speed":       mdata["speed"],
    }

    print(f"  [{shape:8} / {mode:5}]", end="  ", flush=True)
    cmd = [
        "npx", "remotion", "render",
        "src/index.ts", "ShapeFloatShort",
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
        make_meta(shape, mode, out_path)
        return True
    err = (result.stderr or result.stdout)[-200:].strip()
    print(f"✗  {err}")
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--shapes", nargs="+", default=list(SHAPES.keys()))
    parser.add_argument("--modes",  nargs="+", default=list(MODES.keys()))
    parser.add_argument("--force",  action="store_true")
    args = parser.parse_args()

    shapes   = [s for s in args.shapes if s in SHAPES]
    modes    = [m for m in args.modes  if m in MODES]
    date_str = datetime.now().strftime("%Y%m%d")
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)

    total = len(shapes) * len(modes)
    print(f"\nGenerating {total} ShapeFloat shorts ({len(shapes)} shapes × {len(modes)} modes)\n")

    ok = 0
    for shape in shapes:
        for mode in modes:
            if render(shape, mode, date_str, args.force):
                ok += 1

    print(f"\nDone: {ok}/{total} shape float shorts generated")


if __name__ == "__main__":
    main()
