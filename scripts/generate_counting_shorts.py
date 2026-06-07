#!/usr/bin/env python3
"""
Generate 60s counting shorts — one per shape type.
Each short: count 1-5 with shape A, then count 1-5 with shape B.
Voiceover audio synced via ffmpeg; background music mixed in at lower volume.

Usage:
  python3 generate_counting_shorts.py
  python3 generate_counting_shorts.py --shapes circle star
"""
import argparse
import json
import math
import random
import shutil
import subprocess
import tempfile
import yaml
from pathlib import Path

ROOT        = Path(__file__).resolve().parent.parent
SCENE_FILE  = ROOT / "scripts" / "manim_counting_scene.py"
PARAMS_TMP  = Path("/tmp/manim_counting_params.json")
QUEUE_DIR   = ROOT / "output" / "queue"
AUDIO_DIR   = ROOT / "assets" / "audio" / "voiceover" / "en"
MUSIC_DIR   = ROOT / "assets" / "music" / "kevin"

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

ALL_SHAPES = ["circle", "square", "triangle", "star",
              "diamond", "ellipse", "hexagon", "pentagon"]

# Pairs of shapes for each short (shape A count 1-5, shape B count 1-5)
SHAPE_PAIRS = [
    ("circle",   "star"),
    ("square",   "triangle"),
    ("hexagon",  "diamond"),
    ("ellipse",  "pentagon"),
    ("circle",   "square"),
    ("star",     "triangle"),
    ("diamond",  "circle"),
    ("pentagon", "hexagon"),
]

TITLES = {
    ("circle",   "star"):     "⭕ Count Circles and Stars 1-5 | Happy Bear Kids #shorts",
    ("square",   "triangle"): "🔷 Count Squares and Triangles 1-5 | Happy Bear Kids #shorts",
    ("hexagon",  "diamond"):  "⬡ Count Hexagons and Diamonds 1-5 | Happy Bear Kids #shorts",
    ("ellipse",  "pentagon"): "🥚 Count Ovals and Pentagons 1-5 | Happy Bear Kids #shorts",
    ("circle",   "square"):   "⭕ Count Circles and Squares 1-5 | Happy Bear Kids #shorts",
    ("star",     "triangle"): "⭐ Count Stars and Triangles 1-5 | Happy Bear Kids #shorts",
    ("diamond",  "circle"):   "💎 Count Diamonds and Circles 1-5 | Happy Bear Kids #shorts",
    ("pentagon", "hexagon"):  "⬠ Count Pentagons and Hexagons 1-5 | Happy Bear Kids #shorts",
}

PALETTES = {
    "rainbow": ["#FF4444", "#FF7F2A", "#FFD700", "#27AE60", "#2980B9"],
    "pastel":  ["#FFB3BA", "#FFDFBA", "#FFFFBA", "#BAFFC9", "#BAE1FF"],
    "neon":    ["#FF00FF", "#00FF41", "#00FFFF", "#FF4500", "#FFD700"],
    "candy":   ["#FF6EB4", "#FF85A1", "#FFB347", "#FFEC6E", "#B5EAD7"],
    "warm":    ["#FF4444", "#FF7F2A", "#FFD700", "#FF69B4", "#FF6B35"],
    "cool":    ["#2980B9", "#27AE60", "#8E44AD", "#00CED1", "#4169E1"],
    "ocean":   ["#006994", "#0099CC", "#00CED1", "#20B2AA", "#48CAE4"],
    "sunset":  ["#FF4500", "#FF6347", "#FF7F50", "#FFD700", "#DA70D6"],
}

BG_COLORS = [
    "#FFF9E6", "#E8F5E9", "#E3F2FD", "#FCE4EC", "#F3E5F5",
    "#E0F7FA", "#FFFDE7", "#E8EAF6", "#FFF3E0", "#F1F8E9",
]

SHAPE_AUDIO = {
    "circle":    "circle__this_is_a_circle__a_circle.mp3",
    "square":    "square__this_is_a_square__a_square.mp3",
    "triangle":  "triangle__this_is_a_triangle__a_triangle.mp3",
    "star":      "star__this_is_a_star__a_star.mp3",
    "heart":     "heart__this_is_a_heart__a_heart.mp3",
    "diamond":   "diamond__this_is_a_diamond__a_diamond.mp3",
    "ellipse":   "oval__this_is_a_oval__a_oval.mp3",
    "rectangle": "rectangle__this_is_a_rectangle__a_rectangle.mp3",
    "hexagon":   None,
    "pentagon":  None,
}

NUMBER_AUDIO = {
    1:  "one__one__let_s_count__one.mp3",
    2:  "two__two__let_s_count__two.mp3",
    3:  "three__three__let_s_count__three.mp3",
    4:  "four__four__let_s_count__four.mp3",
    5:  "five__five__let_s_count__five.mp3",
    6:  "six__six__let_s_count__six.mp3",
    7:  "seven__seven__let_s_count__seven.mp3",
    8:  "eight__eight__let_s_count__eight.mp3",
    9:  "nine__nine__let_s_count__nine.mp3",
    10: "ten__ten__let_s_count__ten.mp3",
}

INTRO_DUR = 4.0
NUM_DUR   = 3.5
HOLD_DUR  = 2.5


def pick_music() -> Path | None:
    tracks = DANCE_TRACKS.copy()
    random.shuffle(tracks)
    for name in tracks:
        p = MUSIC_DIR / name
        if p.exists() and p.stat().st_size > 1000:
            return p
    return None


def render_round(shape_type: str, count: int, colors: list, bg: str,
                 out: Path, quality: str = "m") -> bool:
    """Render one counting round (visual only, no audio) via Manim."""
    params = {
        "shape_type": shape_type,
        "count":      count,
        "colors":     colors,
        "bg_color":   bg,
        "intro_dur":  INTRO_DUR,
        "num_dur":    NUM_DUR,
        "hold_dur":   HOLD_DUR,
        "size":       0.55,
        "vertical":   True,
    }
    PARAMS_TMP.write_text(json.dumps(params))

    media_dir = out.parent / "_manim_cnt_tmp"
    cmd = [
        "manim", f"-q{quality}",
        "--media_dir", str(media_dir),
        "--disable_caching",
        str(SCENE_FILE), "CountingScene",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"\n  [manim error] {result.stderr[-400:]}")
        return False

    rendered = list(media_dir.rglob("CountingScene.mp4"))
    if not rendered:
        return False
    shutil.copy2(rendered[0], out)
    shutil.rmtree(media_dir, ignore_errors=True)
    return True


def round_duration(count: int) -> float:
    return INTRO_DUR + count * NUM_DUR + HOLD_DUR


def build_round_audio(shape_type: str, count: int, tmpdir: Path) -> Path | None:
    """Build voiceover audio for one round using ffmpeg adelay + amix."""
    pieces = []  # list of (path, delay_ms)

    # Shape intro audio at t=0
    intro_name = SHAPE_AUDIO.get(shape_type)
    if intro_name:
        intro_path = AUDIO_DIR / intro_name
        if intro_path.exists():
            pieces.append((str(intro_path), 0))

    # Number audios
    for i in range(1, count + 1):
        num_name = NUMBER_AUDIO.get(i)
        if num_name:
            num_path = AUDIO_DIR / num_name
            if num_path.exists():
                delay_ms = int((INTRO_DUR + (i - 1) * NUM_DUR) * 1000)
                pieces.append((str(num_path), delay_ms))

    if not pieces:
        return None

    out_audio = tmpdir / "round_voice.wav"
    total_dur = round_duration(count)

    inputs = []
    filter_parts = []
    for j, (fpath, delay_ms) in enumerate(pieces):
        inputs += ["-i", fpath]
        filter_parts.append(f"[{j}]adelay={delay_ms}|{delay_ms}[a{j}]")

    amix_in = "".join(f"[a{j}]" for j in range(len(pieces)))
    filter_str = (
        ";".join(filter_parts)
        + f";{amix_in}amix=inputs={len(pieces)}:duration=longest,"
        + f"apad=whole_dur={total_dur}[out]"
    )

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_str,
        "-map", "[out]",
        "-t", str(total_dur),
        str(out_audio),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not out_audio.exists():
        return None
    return out_audio


def attach_audio(video: Path, voice: Path | None, music: Path | None,
                 output: Path) -> bool:
    """Combine silent video with voiceover + background music."""
    if voice is None and music is None:
        shutil.copy2(video, output)
        return True

    inputs = ["-i", str(video)]
    filter_parts = []
    audio_src = None

    if voice and music:
        inputs += ["-stream_loop", "-1", "-i", str(music), "-i", str(voice)]
        # music (input 1) at 25%, voice (input 2) full
        filter_parts = [
            "[1:a]volume=0.25[mus]",
            "[2:a][mus]amix=inputs=2:duration=first[aout]",
        ]
        audio_src = "[aout]"
    elif music:
        inputs += ["-stream_loop", "-1", "-i", str(music)]
        filter_parts = ["[1:a]volume=0.35[aout]"]
        audio_src = "[aout]"
    else:
        inputs += ["-i", str(voice)]
        audio_src = "1:a"

    if filter_parts:
        cmd = [
            "ffmpeg", "-y", *inputs,
            "-filter_complex", ";".join(filter_parts),
            "-map", "0:v", "-map", audio_src,
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest", str(output),
        ]
    else:
        cmd = [
            "ffmpeg", "-y", *inputs,
            "-map", "0:v", "-map", audio_src,
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest", str(output),
        ]

    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode == 0


def concat_clips(clips: list, output: Path) -> bool:
    """Concatenate video clips (each may have or lack audio)."""
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        for c in clips:
            f.write(f"file '{c}'\n")
        list_file = f.name

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", list_file,
        "-c", "copy", str(output),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    Path(list_file).unlink(missing_ok=True)
    return r.returncode == 0


def make_meta(pair: tuple, out_path: Path, palette_name: str):
    meta = {
        "title":            TITLES.get(pair, f"Count Shapes 1-5 | Happy Bear Kids #shorts"),
        "video_type":       "short_counting",
        "theme":            "shapes",
        "duration_minutes": 1,
        "is_short":         True,
        "tags":             ["counting", "numbers", "shapes", "kids", "shorts",
                             "baby", "toddler", "happy bear kids", "1 2 3",
                             "count shapes", "educational", pair[0], pair[1]],
        "status":           "public",
    }
    meta_path = out_path.parent / f"meta_{out_path.stem}.yaml"
    with open(meta_path, "w") as f:
        yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def generate_counting_short(pair: tuple, date_str: str, quality: str = "m") -> bool:
    shape_a, shape_b = pair
    rng = random.Random(f"{shape_a}_{shape_b}")
    palette_name = rng.choice(list(PALETTES.keys()))
    colors = PALETTES[palette_name]
    bg_a = rng.choice(BG_COLORS)
    bg_b = rng.choice([b for b in BG_COLORS if b != bg_a])

    out_name = f"short_counting_{shape_a}_{shape_b}_{date_str}.mp4"
    out_path  = QUEUE_DIR / out_name

    print(f"  [{shape_a}+{shape_b:<10}] {palette_name}", end="  ", flush=True)

    tmpdir = Path(tempfile.mkdtemp(prefix=f"counting_{shape_a}_{shape_b}_"))

    # Render round A
    raw_a = tmpdir / "raw_a.mp4"
    if not render_round(shape_a, 5, colors, bg_a, raw_a, quality):
        print("✗ render A failed")
        shutil.rmtree(tmpdir, ignore_errors=True)
        return False

    # Render round B
    raw_b = tmpdir / "raw_b.mp4"
    # Shift color palette for variety
    colors_b = colors[2:] + colors[:2]
    if not render_round(shape_b, 5, colors_b, bg_b, raw_b, quality):
        print("✗ render B failed")
        shutil.rmtree(tmpdir, ignore_errors=True)
        return False

    # Build voiceover audio for each round
    (tmpdir / "a").mkdir(exist_ok=True)
    voice_a = build_round_audio(shape_a, 5, tmpdir / "a")
    (tmpdir / "b").mkdir(exist_ok=True)
    voice_b = build_round_audio(shape_b, 5, tmpdir / "b")

    music = pick_music()

    # Attach audio to each round
    av_a = tmpdir / "av_a.mp4"
    av_b = tmpdir / "av_b.mp4"
    attach_audio(raw_a, voice_a, None, av_a)  # music added after concat
    attach_audio(raw_b, voice_b, None, av_b)

    # Concat A + B
    concat = tmpdir / "concat.mp4"
    if not concat_clips([av_a, av_b], concat):
        print("✗ concat failed")
        shutil.rmtree(tmpdir, ignore_errors=True)
        return False

    # Add background music to final concat
    if music:
        final = tmpdir / "final.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-i", str(concat),
            "-stream_loop", "-1", "-i", str(music),
            "-filter_complex",
            "[0:a]volume=1.0[vo];[1:a]volume=0.22[mus];[vo][mus]amix=inputs=2:duration=first[aout]",
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest", str(final),
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            shutil.copy2(final, out_path)
        else:
            shutil.copy2(concat, out_path)
    else:
        shutil.copy2(concat, out_path)

    shutil.rmtree(tmpdir, ignore_errors=True)

    if out_path.exists():
        size_mb = out_path.stat().st_size / 1024 / 1024
        print(f"✓ {out_name}  {size_mb:.1f}MB")
        make_meta(pair, out_path, palette_name)
        return True
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--shapes", nargs="+", default=None,
                        help="Shape types to generate (e.g. circle star). "
                             "Generates one short per pair.")
    parser.add_argument("--quality", default="m", choices=["l", "m", "h"])
    args = parser.parse_args()

    from datetime import datetime
    date_str = datetime.now().strftime("%Y%m%d")
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)

    if args.shapes:
        # Build pairs from provided shapes
        shapes = args.shapes
        pairs = []
        for i in range(0, len(shapes) - 1, 2):
            pairs.append((shapes[i], shapes[i + 1]))
        if len(shapes) % 2 == 1:
            pairs.append((shapes[-1], shapes[0]))
    else:
        pairs = SHAPE_PAIRS

    print(f"\nGenerating {len(pairs)} counting shorts → {QUEUE_DIR}\n")
    ok = 0
    for pair in pairs:
        if generate_counting_short(pair, date_str, args.quality):
            ok += 1

    print(f"\nDone: {ok}/{len(pairs)} shorts generated")


if __name__ == "__main__":
    main()
