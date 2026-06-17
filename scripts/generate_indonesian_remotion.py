#!/usr/bin/env python3
"""
Generate Indonesian Remotion videos: ColorLearn, ShapeFloat, ShapeDance.
Output goes to output/queue_id/.

Usage:
  python3 scripts/generate_indonesian_remotion.py
  python3 scripts/generate_indonesian_remotion.py --type colorlearn shapefloat
  python3 scripts/generate_indonesian_remotion.py --type shapefloat-notxt
"""
import argparse
import json
import subprocess
import yaml
from datetime import datetime
from pathlib import Path

ROOT     = Path(__file__).resolve().parent.parent
REMOTION = ROOT / "remotion"
QUEUE_ID = ROOT / "output" / "queue_id"

DATE_STR = datetime.now().strftime("%Y%m%d")

MUSIC_TRACKS = [
    "Carefree.mp3", "Wholesome.mp3", "Merry Go.mp3", "Pinball Spring.mp3",
    "Happy Happy Game Show.mp3", "Quirky Dog.mp3", "Life of Riley.mp3",
]

# Indonesian color names + taglines
COLORS_ID = {
    "red":    {"name": "Merah",      "tagline": "Merah! Dapatkah kamu menemukan sesuatu yang merah?"},
    "orange": {"name": "Oranye",     "tagline": "Oranye! Dapatkah kamu menemukan sesuatu yang oranye?"},
    "yellow": {"name": "Kuning",     "tagline": "Kuning! Dapatkah kamu menemukan sesuatu yang kuning?"},
    "green":  {"name": "Hijau",      "tagline": "Hijau! Dapatkah kamu menemukan sesuatu yang hijau?"},
    "blue":   {"name": "Biru",       "tagline": "Biru! Dapatkah kamu menemukan sesuatu yang biru?"},
    "purple": {"name": "Ungu",       "tagline": "Ungu! Dapatkah kamu menemukan sesuatu yang ungu?"},
    "pink":   {"name": "Merah Muda", "tagline": "Merah Muda! Dapatkah kamu menemukan sesuatu yang merah muda?"},
}

# Indonesian shape names
SHAPES_ID = {
    "circle":   "Lingkaran",
    "square":   "Kotak",
    "triangle": "Segitiga",
    "star":     "Bintang",
    "diamond":  "Belah Ketupat",
    "heart":    "Hati",
    "hexagon":  "Segi Enam",
    "oval":     "Oval",
}

COLORS = {
    "red":    {"hex": "#FF4444", "bg": "#FFF5F5",
               "fruits": ["fruits_cartoon/apple.png", "fruits_cartoon/strawberry.png",
                          "vegetables_cartoon/tomato.png", "vegetables_cartoon/pepper.png"]},
    "orange": {"hex": "#FF7F2A", "bg": "#FFF3E0",
               "fruits": ["fruits_cartoon/orange.png", "vegetables_cartoon/carrot.png",
                          "fruits_cartoon/peach.png", "vegetables_cartoon/pumpkin.png"]},
    "yellow": {"hex": "#F9A825", "bg": "#FFFDE7",
               "fruits": ["fruits_cartoon/banana.png", "vegetables_cartoon/corn.png",
                          "fruits_cartoon/pineapple.png", "fruits_cartoon/pear.png"]},
    "green":  {"hex": "#27AE60", "bg": "#F1F8E9",
               "fruits": ["vegetables_cartoon/broccoli.png", "fruits_cartoon/kiwi.png",
                          "vegetables_cartoon/cucumber.png", "fruits_cartoon/avocado.png"]},
    "blue":   {"hex": "#2980B9", "bg": "#E3F2FD",
               "fruits": ["fruits_cartoon/blueberry.png", "fruits_cartoon/dragonfruit.png"]},
    "purple": {"hex": "#8E44AD", "bg": "#F3E5F5",
               "fruits": ["fruits_cartoon/grape.png", "vegetables_cartoon/eggplant.png",
                          "fruits_cartoon/plum.png"]},
    "pink":   {"hex": "#E91E63", "bg": "#FCE4EC",
               "fruits": ["fruits_cartoon/strawberry.png", "fruits_cartoon/raspberry.png",
                          "fruits_cartoon/peach.png", "fruits_cartoon/dragonfruit.png"]},
}

SHAPES_CONFIG = {
    "circle":   {"color": "#2980B9", "bg": "#E3F2FD"},
    "square":   {"color": "#27AE60", "bg": "#E8F5E9"},
    "triangle": {"color": "#E67E22", "bg": "#FFF3E0"},
    "star":     {"color": "#F39C12", "bg": "#FFFDE7"},
    "diamond":  {"color": "#8E44AD", "bg": "#F3E5F5"},
    "heart":    {"color": "#E74C3C", "bg": "#FFEBEE"},
    "hexagon":  {"color": "#16A085", "bg": "#E0F7FA"},
    "oval":     {"color": "#5C6BC0", "bg": "#EDE7F6"},
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


# ── ColorLearn Indonesian ──────────────────────────────────────────────────────
def gen_colorlearn_id(force: bool):
    print("\n[ColorLearn ID] 7 warna → queue_id/\n")
    ok = 0
    for i, (color_en, data) in enumerate(COLORS.items()):
        color_id = COLORS_ID[color_en]["name"]
        tagline  = COLORS_ID[color_en]["tagline"]
        out_name = f"id_short_colorlearn_{color_en}_{DATE_STR}.mp4"
        out_path = QUEUE_ID / out_name
        if out_path.exists() and not force:
            print(f"  [{color_en}] skip"); continue

        props = {
            "colorName":    color_id,
            "colorHex":     data["hex"],
            "bgColor":      data["bg"],
            "audioFile":    None,   # Indonesian TTS not set up yet
            "musicFile":    MUSIC_TRACKS[i % len(MUSIC_TRACKS)],
            "taglineText":  tagline,
            "rtl":          False,
            "fruitSprites": data.get("fruits", []),
        }
        print(f"  [{color_en:8} → {color_id}]", end="  ", flush=True)
        if render("ColorLearnShort", out_path, props):
            size = out_path.stat().st_size / 1024 / 1024
            print(f"✓  {size:.1f}MB")
            meta = {
                "title": f"Belajar Warna {color_id} | Happy Bear Kids #Shorts",
                "description": (
                    f"Belajar warna {color_id.lower()} bersama Happy Bear Kids! "
                    f"Video edukasi warna yang menyenangkan untuk bayi dan balita.\n\n"
                    f"#{color_id.replace(' ','')} #BelajarWarna #HappyBearKids #AnakCerdas"
                ),
                "tags": [color_en, color_id.lower(), "belajar warna", "warna", "anak",
                         "bayi", "happy bear kids", "edukasi", "balita"],
                "video_type": "short_colorlearn",
                "language":   "id",
                "is_short":   True,
                "status":     "public",
            }
            write_meta(meta, out_path)
            ok += 1
        else:
            print("✗")
    print(f"ColorLearn ID: {ok}/7")


# ── ShapeFloat — with Indonesian labels ───────────────────────────────────────
def gen_shapefloat_id(force: bool):
    print("\n[ShapeFloat ID with labels] 8 bentuk × 4 mode → queue_id/\n")
    ok = 0
    for i, (shape_en, data) in enumerate(SHAPES_CONFIG.items()):
        shape_id = SHAPES_ID.get(shape_en, shape_en.capitalize())
        for j, mode in enumerate(FLOAT_MODES):
            out_name = f"id_short_float_{shape_en}_{mode}_{DATE_STR}.mp4"
            out_path = QUEUE_ID / out_name
            if out_path.exists() and not force:
                print(f"  [{shape_en}/{mode}] skip"); continue

            count = {"tb": 6, "lr": 4, "diag": 5, "float": 7}[mode]
            speed = {"tb": "slow", "lr": "medium", "diag": "medium", "float": "slow"}[mode]
            props = {
                "shapeName":   shape_en,
                "shapeColor":  data["color"],
                "bgColor":     data["bg"],
                "mode":        mode,
                "count":       count,
                "showLabel":   True,
                "audioFile":   None,   # Indonesian TTS not set up yet
                "musicFile":   MUSIC_TRACKS[(i * 4 + j) % len(MUSIC_TRACKS)],
                "speed":       speed,
                "customLabel": shape_id,
                "rtl":         False,
            }
            print(f"  [{shape_en:8}/{mode:5}]", end="  ", flush=True)
            if render("ShapeFloatShort", out_path, props):
                size = out_path.stat().st_size / 1024 / 1024
                print(f"✓  {size:.1f}MB")
                meta = {
                    "title": f"Belajar Bentuk {shape_id} | Happy Bear Kids #Shorts",
                    "description": (
                        f"Belajar bentuk {shape_id.lower()} bersama Happy Bear Kids! "
                        f"Animasi bentuk yang menyenangkan untuk bayi dan balita.\n\n"
                        f"#{shape_id.replace(' ','')} #BelajarBentuk #HappyBearKids #AnakCerdas"
                    ),
                    "tags": [shape_en, shape_id.lower(), "belajar bentuk", "bentuk", "anak",
                             "bayi", "happy bear kids", "edukasi"],
                    "video_type": "short_shape_float",
                    "language":   "id",
                    "is_short":   True,
                    "status":     "public",
                }
                write_meta(meta, out_path)
                ok += 1
            else:
                print("✗")
    print(f"ShapeFloat ID (labels): {ok}/32")


# ── ShapeDance — with Indonesian labels ───────────────────────────────────────
def gen_shapedance_id(force: bool):
    print("\n[ShapeDance ID with labels] 4 combo → queue_id/\n")
    ok = 0
    for i, (combo, cfg) in enumerate(SHAPE_DANCE_COMBOS.items()):
        out_name = f"id_short_sdance_{combo}_{DATE_STR}.mp4"
        out_path = QUEUE_ID / out_name
        if out_path.exists() and not force:
            print(f"  [{combo}] skip"); continue

        labels_id  = " + ".join(SHAPES_ID.get(s, s) for s in cfg["shapes"])
        custom_labels = {s: SHAPES_ID.get(s, s) for s in cfg["shapes"]}
        props = {
            "shapes":       cfg["shapes"],
            "colors":       cfg["colors"],
            "bgColor":      cfg["bg"],
            "bpm":          110,
            "showLabels":   True,
            "audioFile":    None,
            "musicFile":    MUSIC_TRACKS[i % len(MUSIC_TRACKS)],
            "customLabels": custom_labels,
            "rtl":          False,
        }
        print(f"  [{combo}] {labels_id}", end="  ", flush=True)
        if render("ShapeDanceShort", out_path, props):
            size = out_path.stat().st_size / 1024 / 1024
            print(f"✓  {size:.1f}MB")
            meta = {
                "title": f"Tarian Bentuk | {labels_id} | Happy Bear Kids #Shorts",
                "description": (
                    f"Lihat {labels_id} menari bersama! "
                    f"Animasi bentuk yang menyenangkan untuk anak-anak.\n\n"
                    f"#Bentuk #Menari #HappyBearKids #AnakCerdas"
                ),
                "tags": cfg["shapes"] + [SHAPES_ID.get(s, s).lower() for s in cfg["shapes"]]
                        + ["bentuk", "menari", "anak", "bayi", "happy bear kids"],
                "video_type": "short_shape_dance",
                "language":   "id",
                "is_short":   True,
                "status":     "public",
            }
            write_meta(meta, out_path)
            ok += 1
        else:
            print("✗")
    print(f"ShapeDance ID (labels): {ok}/4")


def main():
    parser = argparse.ArgumentParser(
        description="Generate Indonesian Remotion shorts (ColorLearn, ShapeFloat, ShapeDance)")
    parser.add_argument("--type", nargs="+",
                        choices=["colorlearn", "shapefloat", "shapedance", "all"],
                        default=["all"])
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    QUEUE_ID.mkdir(parents=True, exist_ok=True)
    types = set(args.type)
    if "all" in types:
        types = {"colorlearn", "shapefloat", "shapedance"}

    print(f"\nGenerating Indonesian Remotion videos → {QUEUE_ID}\n")

    if "colorlearn" in types:
        gen_colorlearn_id(args.force)
    if "shapefloat" in types:
        gen_shapefloat_id(args.force)
    if "shapedance" in types:
        gen_shapedance_id(args.force)


if __name__ == "__main__":
    main()
