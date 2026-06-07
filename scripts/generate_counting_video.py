#!/usr/bin/env python3
"""
Generate a 30-minute counting video for kids.
Multiple rounds: count each shape type 1-10, cycle through shapes.
Voiceover (number audio) + background music mixed together.

Usage:
  python3 generate_counting_video.py
  python3 generate_counting_video.py --duration 30 --theme rainbow --seed 42
  python3 generate_counting_video.py --theme all   # all themes
"""
import argparse
import json
import random
import shutil
import subprocess
import sys
import tempfile
import yaml
from datetime import datetime
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

PALETTES = {
    "rainbow": ["#FF4444", "#FF7F2A", "#FFD700", "#27AE60", "#2980B9", "#8E44AD"],
    "pastel":  ["#FFB3BA", "#FFDFBA", "#FFFFBA", "#BAFFC9", "#BAE1FF", "#E8BAFF"],
    "warm":    ["#FF4444", "#FF7F2A", "#FFD700", "#FF69B4", "#FF6B35", "#FFA500"],
    "neon":    ["#FF00FF", "#00FF41", "#00FFFF", "#FF4500", "#FFD700", "#FF1493"],
    "candy":   ["#FF6EB4", "#FF85A1", "#FFB347", "#FFEC6E", "#B5EAD7", "#C7CEEA"],
    "ocean":   ["#006994", "#0099CC", "#00CED1", "#20B2AA", "#48CAE4", "#90E0EF"],
    "cool":    ["#2980B9", "#27AE60", "#8E44AD", "#00CED1", "#4169E1", "#20B2AA"],
    "sunset":  ["#FF4500", "#FF6347", "#FF7F50", "#FFD700", "#DA70D6", "#FF1493"],
}

BG_COLORS = [
    "#FFF9E6", "#E8F5E9", "#E3F2FD", "#FCE4EC", "#F3E5F5",
    "#E0F7FA", "#FFFDE7", "#E8EAF6", "#FFF3E0", "#F1F8E9",
    "#F1F8E9", "#FFF8E1", "#E0F2F1", "#EDE7F6", "#E1F5FE",
]

TITLES = {
    "rainbow": "🌈 Count Shapes 1-10 | 30 Minutes | Happy Bear Kids",
    "pastel":  "🩷 Pastel Counting Shapes for Kids | 30 Minutes | Happy Bear Kids",
    "warm":    "🔥 Warm Counting Shapes | 30 Minutes | Happy Bear Kids",
    "neon":    "✨ Neon Counting Shapes | 30 Minutes | Happy Bear Kids",
    "candy":   "🍭 Candy Counting Shapes | 30 Minutes | Happy Bear Kids",
    "ocean":   "🌊 Ocean Counting Shapes | 30 Minutes | Happy Bear Kids",
    "cool":    "💙 Cool Counting Shapes | 30 Minutes | Happy Bear Kids",
    "sunset":  "🌅 Sunset Counting Shapes | 30 Minutes | Happy Bear Kids",
}

SHAPE_AUDIO = {
    "circle":    "circle__this_is_a_circle__a_circle.mp3",
    "square":    "square__this_is_a_square__a_square.mp3",
    "triangle":  "triangle__this_is_a_triangle__a_triangle.mp3",
    "star":      "star__this_is_a_star__a_star.mp3",
    "diamond":   "diamond__this_is_a_diamond__a_diamond.mp3",
    "ellipse":   "oval__this_is_a_oval__a_oval.mp3",
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
TAGS_BASE = ["counting", "numbers", "count to 10", "shapes for kids", "1 to 10",
             "kids counting", "educational", "toddler", "happy bear kids",
             "shapes", "baby learning", "count shapes"]


def round_duration(count: int) -> float:
    return INTRO_DUR + count * NUM_DUR + HOLD_DUR


def pick_music() -> Path | None:
    tracks = DANCE_TRACKS.copy()
    random.shuffle(tracks)
    for name in tracks:
        p = MUSIC_DIR / name
        if p.exists() and p.stat().st_size > 1000:
            return p
    return None


def render_round(shape_type: str, count: int, colors: list, bg: str,
                 out: Path, quality: str) -> bool:
    params = {
        "shape_type": shape_type,
        "count":      count,
        "colors":     colors,
        "bg_color":   bg,
        "intro_dur":  INTRO_DUR,
        "num_dur":    NUM_DUR,
        "hold_dur":   HOLD_DUR,
        "size":       0.60,
        "vertical":   False,
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
        shutil.rmtree(media_dir, ignore_errors=True)
        return False

    rendered = list(media_dir.rglob("CountingScene.mp4"))
    if not rendered:
        shutil.rmtree(media_dir, ignore_errors=True)
        return False
    shutil.copy2(rendered[0], out)
    shutil.rmtree(media_dir, ignore_errors=True)
    return True


def build_round_audio(shape_type: str, count: int, tmpdir: Path) -> Path | None:
    """Build voiceover audio for one round using ffmpeg adelay + amix."""
    tmpdir.mkdir(parents=True, exist_ok=True)
    pieces = []

    intro_name = SHAPE_AUDIO.get(shape_type)
    if intro_name:
        intro_path = AUDIO_DIR / intro_name
        if intro_path.exists():
            pieces.append((str(intro_path), 0))

    for i in range(1, count + 1):
        num_name = NUMBER_AUDIO.get(i)
        if num_name:
            num_path = AUDIO_DIR / num_name
            if num_path.exists():
                delay_ms = int((INTRO_DUR + (i - 1) * NUM_DUR) * 1000)
                pieces.append((str(num_path), delay_ms))

    if not pieces:
        return None

    total_dur = round_duration(count)
    out_audio = tmpdir / f"voice_{shape_type}_{count}.wav"

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
        "ffmpeg", "-y", *inputs,
        "-filter_complex", filter_str,
        "-map", "[out]",
        "-t", str(total_dur),
        str(out_audio),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not out_audio.exists():
        return None
    return out_audio


def attach_voice(video: Path, voice: Path, output: Path) -> bool:
    """Mux silent Manim video with voiceover audio."""
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video),
        "-i", str(voice),
        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
        "-shortest", str(output),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode == 0 and output.exists()


def concat_clips(clips: list, output: Path) -> bool:
    list_file = output.parent / "_concat_list.txt"
    list_file.write_text("".join(f"file '{c}'\n" for c in clips))
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(list_file),
        "-c", "copy", str(output),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    list_file.unlink(missing_ok=True)
    return r.returncode == 0


def add_music(video: Path, music: Path, output: Path) -> bool:
    """Mix background music at low volume with existing audio track."""
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video),
        "-stream_loop", "-1", "-i", str(music),
        "-filter_complex",
        "[0:a]volume=1.0[vo];[1:a]volume=0.20[mus];[vo][mus]amix=inputs=2:duration=first[aout]",
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest", str(output),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode == 0


def plan_rounds(duration_min: int, rng: random.Random) -> list:
    """Build a sequence of (shape_type, count) rounds to fill duration_min minutes."""
    target_sec = duration_min * 60
    total = 0.0
    rounds = []

    # Cycle: count 1-5 for each shape, then 6-10 for each shape
    shape_pool = ALL_SHAPES.copy()

    phase = 1  # 1 = count 1-5, 2 = count 6-10, repeat
    shape_idx = 0

    while total < target_sec - 5:
        shape = shape_pool[shape_idx % len(shape_pool)]
        count = rng.randint(1, 5) if phase == 1 else rng.randint(6, 10)
        dur = round_duration(count)
        if total + dur > target_sec + 30:  # allow 30s overshoot
            break
        rounds.append((shape, count))
        total += dur
        shape_idx += 1
        if shape_idx % len(shape_pool) == 0:
            phase = 3 - phase  # toggle 1↔2
            rng.shuffle(shape_pool)

    return rounds


def make_meta(theme: str, out_path: Path, duration_min: int):
    meta = {
        "title":            TITLES.get(theme, f"Count Shapes 1-10 | {duration_min} Minutes | Happy Bear Kids"),
        "video_type":       "counting",
        "theme":            "shapes",
        "duration_minutes": duration_min,
        "is_short":         False,
        "tags":             TAGS_BASE + [theme, "counting shapes", f"{duration_min} minutes"],
        "status":           "public",
    }
    meta_path = out_path.parent / f"meta_{out_path.stem}.yaml"
    with open(meta_path, "w") as f:
        yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def generate_video(theme: str, duration_min: int, seed: int, quality: str,
                   date_str: str) -> bool:
    rng = random.Random(seed)
    colors = PALETTES[theme]

    rounds = plan_rounds(duration_min, rng)
    print(f"\n  Theme={theme}  seed={seed}  {len(rounds)} rounds  "
          f"(est. {sum(round_duration(c) for _, c in rounds)/60:.1f} min)")

    out_name = f"counting_{theme}_{date_str}.mp4"
    out_path  = QUEUE_DIR / out_name

    tmpdir = Path(tempfile.mkdtemp(prefix=f"counting_{theme}_"))
    music  = pick_music()
    clips_with_audio = []

    for idx, (shape, count) in enumerate(rounds):
        bg = BG_COLORS[(idx * 3) % len(BG_COLORS)]
        # Rotate color palette for variety
        offset = rng.randint(0, len(colors) - 1)
        round_colors = colors[offset:] + colors[:offset]

        sys.stdout.write(f"    [{idx+1:3d}/{len(rounds)}] {shape:<10} 1-{count:<2}  ")
        sys.stdout.flush()

        raw = tmpdir / f"raw_{idx:03d}.mp4"
        if not render_round(shape, count, round_colors, bg, raw, quality):
            print("✗ render failed, skipping")
            continue

        # Build voiceover
        voice_dir = tmpdir / f"aud_{idx:03d}"
        voice = build_round_audio(shape, count, voice_dir)

        if voice:
            av = tmpdir / f"av_{idx:03d}.mp4"
            if attach_voice(raw, voice, av):
                clips_with_audio.append(av)
            else:
                clips_with_audio.append(raw)
        else:
            clips_with_audio.append(raw)

        print(f"✓")

    if not clips_with_audio:
        print("  No rounds rendered.")
        shutil.rmtree(tmpdir, ignore_errors=True)
        return False

    print(f"  Concatenating {len(clips_with_audio)} clips...")
    concat = tmpdir / "concat.mp4"
    if not concat_clips(clips_with_audio, concat):
        print("  ✗ concat failed")
        shutil.rmtree(tmpdir, ignore_errors=True)
        return False

    if music:
        print(f"  Adding music: {music.name}")
        final = tmpdir / "final.mp4"
        if add_music(concat, music, final):
            shutil.copy2(final, out_path)
        else:
            shutil.copy2(concat, out_path)
    else:
        shutil.copy2(concat, out_path)

    shutil.rmtree(tmpdir, ignore_errors=True)

    if out_path.exists():
        size_mb = out_path.stat().st_size / 1024 / 1024
        print(f"  ✓ {out_name}  {size_mb:.1f}MB")
        make_meta(theme, out_path, duration_min)
        return True
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--theme",    default="rainbow",
                        choices=list(PALETTES) + ["all"])
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--seed",     type=int, default=42)
    parser.add_argument("--quality",  default="m", choices=["l", "m", "h"])
    args = parser.parse_args()

    date_str = datetime.now().strftime("%Y%m%d")
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)

    themes = list(PALETTES.keys()) if args.theme == "all" else [args.theme]
    ok = 0
    for i, theme in enumerate(themes):
        print(f"\n[{i+1}/{len(themes)}] Generating counting video: {theme}")
        if generate_video(theme, args.duration, args.seed + i, args.quality, date_str):
            ok += 1

    print(f"\nDone: {ok}/{len(themes)} videos generated")


if __name__ == "__main__":
    main()
