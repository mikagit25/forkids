#!/usr/bin/env python3
"""
Generate 60s shape dance shorts — one per choreography type.
Each short: 55s of one choreography, vertical 1080×1920, music overlay.

Usage:
  python3 generate_shapes_shorts.py
  python3 generate_shapes_shorts.py --choreos bounce_row carousel
"""
import argparse
import json
import random
import shutil
import subprocess
import tempfile
import yaml
from datetime import datetime
from pathlib import Path

ROOT       = Path(__file__).resolve().parent.parent
SCENE_FILE = ROOT / "scripts" / "manim_shapes_scene.py"
PARAMS_TMP = Path("/tmp/manim_shape_params.json")
QUEUE_DIR  = ROOT / "output" / "queue"
MUSIC_DIR  = ROOT / "assets" / "music" / "kevin"

DANCE_TRACKS = [
    "Monkeys Spinning Monkeys.mp3",
    "Quirky Dog.mp3",
    "Merry Go.mp3",
    "Happy Happy Game Show.mp3",
    "Carefree.mp3",
    "Hyperfun.mp3",
    "Overworld.mp3",
    "Pinball Spring.mp3",
    "Sneaky Snitch.mp3",
    "Wholesome.mp3",
]

ALL_CHOREOS = [
    "bounce_row", "carousel", "size_pulse", "color_morph",
    "scatter_gather", "follow_path", "rain", "spin_zoom",
    "mirror_pair", "wave_grid",
    "pendulum", "orbit_layers", "popcorn", "heartbeat", "breathing", "snake_line",
]

CHOREO_TITLES = {
    "bounce_row":     "🌈 Bouncing Shapes for Kids | Happy Bear Kids #shorts",
    "carousel":       "🌀 Spinning Shapes Carousel | Happy Bear Kids #shorts",
    "size_pulse":     "⬆️ Big and Small Shapes | Happy Bear Kids #shorts",
    "color_morph":    "🎨 Colorful Shapes Dance | Happy Bear Kids #shorts",
    "scatter_gather": "💥 Shapes Scatter and Gather | Happy Bear Kids #shorts",
    "follow_path":    "🎯 Follow the Shapes | Happy Bear Kids #shorts",
    "rain":           "🌧️ Shapes Rain Dance | Happy Bear Kids #shorts",
    "spin_zoom":      "🔄 Spinning Shapes Party | Happy Bear Kids #shorts",
    "mirror_pair":    "🪞 Mirror Shapes Dance | Happy Bear Kids #shorts",
    "wave_grid":      "🌊 Wave of Shapes | Happy Bear Kids #shorts",
    "pendulum":       "🎪 Pendulum Shapes Dance | Happy Bear Kids #shorts",
    "orbit_layers":   "⭕ Double Ring Shapes | Happy Bear Kids #shorts",
    "popcorn":        "🍿 Popcorn Shapes for Kids | Happy Bear Kids #shorts",
    "heartbeat":      "💓 Heartbeat Shapes Dance | Happy Bear Kids #shorts",
    "breathing":      "🌸 Breathing Shapes for Babies | Happy Bear Kids #shorts",
    "snake_line":     "🐍 Snake Shapes Dance | Happy Bear Kids #shorts",
}

TAGS_BASE = ["shapes", "kids", "shorts", "baby", "toddler",
             "happy bear kids", "shapes for kids", "colorful", "dance"]

PALETTES = {
    "rainbow": ["#FF4444", "#FF7F2A", "#FFD700", "#27AE60", "#2980B9", "#8E44AD", "#FF69B4"],
    "pastel":  ["#FFB3BA", "#FFDFBA", "#FFFFBA", "#BAFFC9", "#BAE1FF", "#E8BAFF", "#FFDAF0"],
    "warm":    ["#FF4444", "#FF7F2A", "#FFD700", "#FF69B4", "#FF6B35", "#FFA500"],
    "neon":    ["#FF00FF", "#00FF41", "#00FFFF", "#FF4500", "#FFD700", "#FF1493"],
    "candy":   ["#FF6EB4", "#FF85A1", "#FFB347", "#FFEC6E", "#B5EAD7", "#C7CEEA"],
    "ocean":   ["#006994", "#0099CC", "#00CED1", "#20B2AA", "#48CAE4", "#90E0EF"],
    "sunset":  ["#FF4500", "#FF6347", "#FF7F50", "#FFD700", "#DA70D6", "#FF1493"],
}

BG_COLORS = [
    "#FFF9E6", "#E8F5E9", "#E3F2FD", "#FCE4EC", "#F3E5F5",
    "#E0F7FA", "#FFFDE7", "#E8EAF6", "#FFF3E0", "#F1F8E9",
]

SHAPES = ["circle", "square", "triangle", "hexagon", "star", "mixed",
          "ellipse", "diamond", "pentagon"]


def pick_music() -> Path | None:
    tracks = DANCE_TRACKS.copy()
    random.shuffle(tracks)
    for name in tracks:
        p = MUSIC_DIR / name
        if p.exists() and p.stat().st_size > 1000:
            return p
    return None


def render_scene(params: dict, out: Path, quality: str = "m") -> bool:
    PARAMS_TMP.write_text(json.dumps(params))
    media_dir = out.parent / "_manim_tmp"
    cmd = [
        "manim", f"-q{quality}",
        "--media_dir", str(media_dir),
        "--disable_caching",
        str(SCENE_FILE), "ShapeScene",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  [manim error] {result.stderr[-500:]}")
        return False
    rendered = list(media_dir.rglob("ShapeScene.mp4"))
    if not rendered:
        return False
    shutil.copy2(rendered[0], out)
    shutil.rmtree(media_dir, ignore_errors=True)
    return True


def add_music(video: Path, music: Path, output: Path) -> bool:
    result = subprocess.run([
        "ffmpeg", "-y",
        "-i", str(video),
        "-stream_loop", "-1", "-i", str(music),
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        "-map", "0:v:0", "-map", "1:a:0",
        str(output),
    ], capture_output=True, text=True)
    return result.returncode == 0


def make_meta(choreo: str, out_path: Path, colors_name: str):
    meta = {
        "title":            CHOREO_TITLES.get(choreo, f"Shapes Dance | Happy Bear Kids #shorts"),
        "video_type":       "short_shape_dance",
        "theme":            "shapes",
        "language":         "en",
        "duration_minutes": 1,
        "is_short":         True,
        "tags":             TAGS_BASE + [choreo.replace("_", " "), colors_name],
        "status":           "public",
    }
    meta_path = out_path.parent / f"meta_{out_path.stem}.yaml"
    with open(meta_path, "w") as f:
        yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def generate_short(choreo: str, date_str: str, quality: str = "m") -> bool:
    rng = random.Random(choreo)
    palette_name = rng.choice(list(PALETTES.keys()))
    colors  = PALETTES[palette_name]
    shape   = rng.choice(SHAPES)
    bg      = rng.choice(BG_COLORS)
    n       = rng.choice([4, 5, 6])
    size    = rng.choice([0.55, 0.65, 0.75])

    if choreo == "mirror_pair":
        n = rng.choice([2, 3, 4])
    elif choreo == "wave_grid":
        n = 12   # 4×3 portrait grid

    params = {
        "choreo":     choreo,
        "shape_type": shape,
        "n":          n,
        "colors":     colors,
        "bg_color":   bg,
        "duration":   55,
        "size":       size,
        "seed":       abs(hash(choreo)) % 9999,
        "vertical":   True,
    }

    out_name = f"short_shapes_{choreo}_{date_str}.mp4"
    out_path = QUEUE_DIR / out_name

    print(f"  [{choreo:<16}] {shape:<10} {palette_name:<8} n={n}", end="  ", flush=True)

    tmpdir = Path(tempfile.mkdtemp(prefix=f"shapes_short_{choreo}_"))
    raw = tmpdir / "raw.mp4"

    ok = render_scene(params, raw, quality)
    if not ok:
        print("✗ render failed")
        shutil.rmtree(tmpdir, ignore_errors=True)
        return False

    music = pick_music()
    if music:
        ok2 = add_music(raw, music, out_path)
        if not ok2:
            shutil.copy2(raw, out_path)
    else:
        shutil.copy2(raw, out_path)

    shutil.rmtree(tmpdir, ignore_errors=True)

    size_mb = out_path.stat().st_size / 1024 / 1024
    print(f"✓ {out_name}  {size_mb:.1f}MB")
    make_meta(choreo, out_path, palette_name)
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--choreos", nargs="+", default=ALL_CHOREOS)
    parser.add_argument("--quality", default="m", choices=["l", "m", "h"])
    args = parser.parse_args()

    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")

    print(f"\nGenerating {len(args.choreos)} shape shorts → {QUEUE_DIR}\n")
    ok = 0
    for choreo in args.choreos:
        if choreo not in ALL_CHOREOS:
            print(f"  Unknown choreo: {choreo}")
            continue
        if generate_short(choreo, date_str, args.quality):
            ok += 1

    print(f"\nDone: {ok}/{len(args.choreos)} shorts generated")


if __name__ == "__main__":
    main()
