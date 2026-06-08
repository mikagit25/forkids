#!/usr/bin/env python3
"""
Generate ColorLearn shorts using Remotion.
One 55s short per color: big circle + color name + 4 shapes + "Can you find...?" voiceover.
Output: output/queue/short_colorlearn_{color}_{date}.mp4

Usage:
  python3 scripts/generate_color_learn_shorts.py
  python3 scripts/generate_color_learn_shorts.py --colors red blue green
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

COLORS = {
    "red":    {"hex": "#FF4444", "bg": "#FFF5F5",
               "audio": "red__red__can_you_find_something_red.mp3",
               "fruits": ["fruits_cartoon/apple.png",
                          "fruits_cartoon/strawberry.png",
                          "vegetables_cartoon/tomato.png",
                          "vegetables_cartoon/pepper.png"]},
    "orange": {"hex": "#FF7F2A", "bg": "#FFF3E0",
               "audio": "orange__orange__can_you_find_something_orange.mp3",
               "fruits": ["fruits_cartoon/orange.png",
                          "vegetables_cartoon/carrot.png",
                          "fruits_cartoon/peach.png",
                          "vegetables_cartoon/pumpkin.png"]},
    "yellow": {"hex": "#F9A825", "bg": "#FFFDE7",
               "audio": "yellow__yellow__can_you_find_something_yellow.mp3",
               "fruits": ["fruits_cartoon/banana.png",
                          "vegetables_cartoon/corn.png",
                          "fruits_cartoon/pineapple.png",
                          "fruits_cartoon/pear.png"]},
    "green":  {"hex": "#27AE60", "bg": "#F1F8E9",
               "audio": "green__green__can_you_find_something_green.mp3",
               "fruits": ["vegetables_cartoon/broccoli.png",
                          "fruits_cartoon/kiwi.png",
                          "vegetables_cartoon/cucumber.png",
                          "fruits_cartoon/avocado.png"]},
    "blue":   {"hex": "#2980B9", "bg": "#E3F2FD",
               "audio": "blue__blue__can_you_find_something_blue.mp3",
               "fruits": ["fruits_cartoon/blueberry.png",
                          "fruits_cartoon/dragonfruit.png"]},
    "purple": {"hex": "#8E44AD", "bg": "#F3E5F5",
               "audio": "purple__purple__can_you_find_something_purple.mp3",
               "fruits": ["fruits_cartoon/grape.png",
                          "vegetables_cartoon/eggplant.png",
                          "fruits_cartoon/plum.png"]},
    "pink":   {"hex": "#E91E63", "bg": "#FCE4EC",
               "audio": "pink__pink__can_you_find_something_pink.mp3",
               "fruits": ["fruits_cartoon/strawberry.png",
                          "fruits_cartoon/raspberry.png",
                          "fruits_cartoon/peach.png",
                          "fruits_cartoon/dragonfruit.png"]},
}

MUSIC_TRACKS = [
    "Happy Happy Game Show.mp3", "Carefree.mp3", "Wholesome.mp3",
    "Merry Go.mp3", "Overworld.mp3", "Life of Riley.mp3", "Quirky Dog.mp3",
]


def make_meta(color: str, out_path: Path):
    color_cap = color.capitalize()
    meta = {
        "title":            f"Color {color_cap} | Learn Colors for Kids | Happy Bear Kids #shorts",
        "video_type":       "short_color_learn",
        "theme":            "colors",
        "duration_minutes": 1,
        "is_short":         True,
        "tags":             [
            "colors for kids", "learn colors", color, f"color {color}",
            "color recognition", "toddler learning", "preschool",
            "happy bear kids", "educational", "shorts",
        ],
        "status": "public",
    }
    meta_path = out_path.parent / f"meta_{out_path.stem}.yaml"
    with open(meta_path, "w") as f:
        yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def render(color: str, date_str: str, force: bool, idx: int) -> bool:
    data     = COLORS[color]
    out_name = f"short_colorlearn_{color}_{date_str}.mp4"
    out_path = QUEUE_DIR / out_name

    if out_path.exists() and not force:
        print(f"  [{color}] skip (exists)")
        return True

    music = MUSIC_TRACKS[idx % len(MUSIC_TRACKS)]
    props = {
        "colorName":    color.upper(),
        "colorHex":     data["hex"],
        "bgColor":      data["bg"],
        "audioFile":    data["audio"],
        "musicFile":    music,
        "fruitSprites": data.get("fruits", []),
    }

    print(f"  [{color:8}]", end="  ", flush=True)
    cmd = [
        "npx", "remotion", "render",
        "src/index.ts", "ColorLearnShort",
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
        make_meta(color, out_path)
        return True
    err = (result.stderr or result.stdout)[-200:].strip()
    print(f"✗  {err}")
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--colors", nargs="+", default=list(COLORS.keys()))
    parser.add_argument("--force",  action="store_true")
    args = parser.parse_args()

    colors   = [c for c in args.colors if c in COLORS]
    date_str = datetime.now().strftime("%Y%m%d")
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\nGenerating {len(colors)} ColorLearn shorts\n")

    ok = 0
    for idx, color in enumerate(colors):
        if render(color, date_str, args.force, idx):
            ok += 1

    print(f"\nDone: {ok}/{len(colors)} color learn shorts generated")


if __name__ == "__main__":
    main()
