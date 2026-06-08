#!/usr/bin/env python3
"""
Generate Arabic Remotion videos: ColorLearn, ShapeFloat, ShapeDance.
Output goes to output/queue_ar/ (staging, not published until English queue empties).

Usage:
  python3 scripts/generate_arabic_remotion.py
  python3 scripts/generate_arabic_remotion.py --type colorlearn shapefloat
"""
import argparse
import json
import subprocess
import yaml
from datetime import datetime
from pathlib import Path

ROOT      = Path(__file__).resolve().parent.parent
REMOTION  = ROOT / "remotion"
QUEUE_AR  = ROOT / "output" / "queue_ar"

from arabic_data import (
    SHAPES_AR, COLORS_AR, COLOR_TAGLINES_AR,
    short_color_meta_ar, short_shape_meta_ar,
)

import sys; sys.path.insert(0, str(ROOT / "scripts"))

DATE_STR = datetime.now().strftime("%Y%m%d")

MUSIC_TRACKS = [
    "Carefree.mp3", "Wholesome.mp3", "Merry Go.mp3", "Pinball Spring.mp3",
    "Happy Happy Game Show.mp3", "Quirky Dog.mp3", "Life of Riley.mp3",
]

COLORS = {
    "red":    {"hex": "#FF4444", "bg": "#FFF5F5",
               "audio": "red__red__can_you_find_something_red.mp3",
               "fruits": ["fruits_cartoon/apple.png", "fruits_cartoon/strawberry.png",
                          "vegetables_cartoon/tomato.png", "vegetables_cartoon/pepper.png"]},
    "orange": {"hex": "#FF7F2A", "bg": "#FFF3E0",
               "audio": "orange__orange__can_you_find_something_orange.mp3",
               "fruits": ["fruits_cartoon/orange.png", "vegetables_cartoon/carrot.png",
                          "fruits_cartoon/peach.png", "vegetables_cartoon/pumpkin.png"]},
    "yellow": {"hex": "#F9A825", "bg": "#FFFDE7",
               "audio": "yellow__yellow__can_you_find_something_yellow.mp3",
               "fruits": ["fruits_cartoon/banana.png", "vegetables_cartoon/corn.png",
                          "fruits_cartoon/pineapple.png", "fruits_cartoon/pear.png"]},
    "green":  {"hex": "#27AE60", "bg": "#F1F8E9",
               "audio": "green__green__can_you_find_something_green.mp3",
               "fruits": ["vegetables_cartoon/broccoli.png", "fruits_cartoon/kiwi.png",
                          "vegetables_cartoon/cucumber.png", "fruits_cartoon/avocado.png"]},
    "blue":   {"hex": "#2980B9", "bg": "#E3F2FD",
               "audio": "blue__blue__can_you_find_something_blue.mp3",
               "fruits": ["fruits_cartoon/blueberry.png", "fruits_cartoon/dragonfruit.png"]},
    "purple": {"hex": "#8E44AD", "bg": "#F3E5F5",
               "audio": "purple__purple__can_you_find_something_purple.mp3",
               "fruits": ["fruits_cartoon/grape.png", "vegetables_cartoon/eggplant.png",
                          "fruits_cartoon/plum.png"]},
    "pink":   {"hex": "#E91E63", "bg": "#FCE4EC",
               "audio": "pink__pink__can_you_find_something_pink.mp3",
               "fruits": ["fruits_cartoon/strawberry.png", "fruits_cartoon/raspberry.png",
                          "fruits_cartoon/peach.png", "fruits_cartoon/dragonfruit.png"]},
}

SHAPES_CONFIG = {
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
    "hexagon":  {"color": "#16A085", "bg": "#E0F7FA", "audio": None},
    "oval":     {"color": "#5C6BC0", "bg": "#EDE7F6",
                 "audio": "oval__this_is_a_oval__a_oval.mp3"},
}

SHAPE_DANCE_COMBOS = {
    "circle_square_triangle": {
        "shapes": ["circle", "square", "triangle"],
        "colors": ["#E74C3C", "#27AE60", "#2980B9"],
        "bg": "#FFFFF0",
    },
    "star_circle_square": {
        "shapes": ["star", "circle", "square"],
        "colors": ["#F39C12", "#E74C3C", "#27AE60"],
        "bg": "#FFFDE7",
    },
    "heart_star_circle": {
        "shapes": ["heart", "star", "circle"],
        "colors": ["#E91E63", "#F39C12", "#2980B9"],
        "bg": "#FFF0F5",
    },
    "all_four": {
        "shapes": ["circle", "square", "triangle", "star"],
        "colors": ["#E74C3C", "#27AE60", "#2980B9", "#F39C12"],
        "bg": "#FAFAFA",
    },
}

FLOAT_MODES = ["tb", "lr", "diag", "float"]


def render(composition: str, out_path: Path, props: dict) -> bool:
    cmd = [
        "npx", "remotion", "render",
        "src/index.ts", composition,
        str(out_path),
        "--props", json.dumps(props),
        "--log", "error",
        "--video-image-format=jpeg",
        "--jpeg-quality=85",
        "--concurrency=4",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REMOTION))
    return result.returncode == 0 and out_path.exists()


def write_meta(meta: dict, out_path: Path):
    meta_path = out_path.parent / f"meta_{out_path.stem}.yaml"
    with open(meta_path, "w") as f:
        yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


# ── ColorLearn Arabic ─────────────────────────────────────────────────────────
def gen_colorlearn_ar(force: bool):
    print("\n[ColorLearn AR] 7 colors\n")
    ok = 0
    for i, (color_en, data) in enumerate(COLORS.items()):
        color_ar = COLORS_AR[color_en]["name"]
        tagline  = COLOR_TAGLINES_AR[color_en]
        out_name = f"ar_short_colorlearn_{color_en}_{DATE_STR}.mp4"
        out_path = QUEUE_AR / out_name
        if out_path.exists() and not force:
            print(f"  [{color_en}] skip"); continue

        props = {
            "colorName":    color_ar,
            "colorHex":     data["hex"],
            "bgColor":      data["bg"],
            "audioFile":    data["audio"],
            "musicFile":    MUSIC_TRACKS[i % len(MUSIC_TRACKS)],
            "taglineText":  tagline,
            "rtl":          True,
            "fruitSprites": data.get("fruits", []),
        }
        print(f"  [{color_en:8} → {color_ar}]", end="  ", flush=True)
        if render("ColorLearnShort", out_path, props):
            size = out_path.stat().st_size / 1024 / 1024
            print(f"✓  {size:.1f}MB")
            meta = short_color_meta_ar(color_en, color_ar)
            meta["video_type"] = "short_colorlearn"
            write_meta(meta, out_path)
            ok += 1
        else:
            print("✗")
    print(f"ColorLearn AR: {ok}/7")


# ── ShapeFloat Arabic ─────────────────────────────────────────────────────────
def gen_shapefloat_ar(force: bool):
    print("\n[ShapeFloat AR] 8 shapes × 4 modes\n")
    ok = 0
    for i, (shape_en, data) in enumerate(SHAPES_CONFIG.items()):
        shape_ar = SHAPES_AR.get(shape_en, shape_en)
        for j, mode in enumerate(FLOAT_MODES):
            out_name = f"ar_short_float_{shape_en}_{mode}_{DATE_STR}.mp4"
            out_path = QUEUE_AR / out_name
            if out_path.exists() and not force:
                print(f"  [{shape_en}/{mode}] skip"); continue

            count  = {"tb": 6, "lr": 4, "diag": 5, "float": 7}[mode]
            speed  = {"tb": "slow", "lr": "medium", "diag": "medium", "float": "slow"}[mode]
            music  = MUSIC_TRACKS[(i * 4 + j) % len(MUSIC_TRACKS)]
            props  = {
                "shapeName":   shape_en,
                "shapeColor":  data["color"],
                "bgColor":     data["bg"],
                "mode":        mode,
                "count":       count,
                "showLabel":   True,
                "audioFile":   data["audio"],
                "musicFile":   music,
                "speed":       speed,
                "customLabel": shape_ar,
                "rtl":         True,
            }
            print(f"  [{shape_en:8}/{mode:5}] → {shape_ar}", end="  ", flush=True)
            if render("ShapeFloatShort", out_path, props):
                size = out_path.stat().st_size / 1024 / 1024
                print(f"✓  {size:.1f}MB")
                meta = short_shape_meta_ar(shape_en, shape_ar)
                meta["video_type"] = "short_shape_float"
                write_meta(meta, out_path)
                ok += 1
            else:
                print("✗")
    print(f"ShapeFloat AR: {ok}/32")


# ── ShapeDance Arabic ─────────────────────────────────────────────────────────
def gen_shapedance_ar(force: bool):
    print("\n[ShapeDance AR] 4 combos\n")
    ok = 0
    for i, (combo, cfg) in enumerate(SHAPE_DANCE_COMBOS.items()):
        out_name = f"ar_short_sdance_{combo}_{DATE_STR}.mp4"
        out_path = QUEUE_AR / out_name
        if out_path.exists() and not force:
            print(f"  [{combo}] skip"); continue

        custom_labels = {s: SHAPES_AR.get(s, s) for s in cfg["shapes"]}
        labels_str = " + ".join(SHAPES_AR.get(s, s) for s in cfg["shapes"])
        props = {
            "shapes":       cfg["shapes"],
            "colors":       cfg["colors"],
            "bgColor":      cfg["bg"],
            "bpm":          110,
            "showLabels":   True,
            "audioFile":    None,
            "musicFile":    MUSIC_TRACKS[i % len(MUSIC_TRACKS)],
            "customLabels": custom_labels,
            "rtl":          True,
        }
        print(f"  [{combo}] → {labels_str}", end="  ", flush=True)
        if render("ShapeDanceShort", out_path, props):
            size = out_path.stat().st_size / 1024 / 1024
            print(f"✓  {size:.1f}MB")
            meta = {
                "title":       f"رقص الأشكال | {labels_str} | هابي بير كيدز #shorts",
                "description": f"شاهد {labels_str} يرقصون! ⭐ #أشكال #رقص #أطفال #shorts",
                "tags":        ["أشكال", "رقص", "أطفال", "هابي بير كيدز", "shorts"],
                "video_type":  "short_shape_dance",
                "language":    "ar", "is_short": True, "status": "public",
            }
            write_meta(meta, out_path)
            ok += 1
        else:
            print("✗")
    print(f"ShapeDance AR: {ok}/4")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", nargs="+",
                        choices=["colorlearn", "shapefloat", "shapedance", "all"],
                        default=["all"])
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    QUEUE_AR.mkdir(parents=True, exist_ok=True)
    types = set(args.type)
    if "all" in types:
        types = {"colorlearn", "shapefloat", "shapedance"}

    print(f"\nGenerating Arabic Remotion videos → {QUEUE_AR}\n")

    if "colorlearn" in types:
        gen_colorlearn_ar(args.force)
    if "shapedance" in types:
        gen_shapedance_ar(args.force)
    if "shapefloat" in types:
        gen_shapefloat_ar(args.force)


if __name__ == "__main__":
    main()
