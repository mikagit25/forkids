#!/usr/bin/env python3
"""
Generate a 30-minute color learning video for kids.
Renders 8 color scenes (~60s each), cycles them to fill 30 minutes.
Adds background music at low volume.

Usage:
  python3 scripts/generate_color_video.py
  python3 scripts/generate_color_video.py --duration 30 --quality m
"""
import argparse
import random
import shutil
import subprocess
import sys
import tempfile
import yaml
from datetime import datetime
from pathlib import Path

ROOT      = Path(__file__).resolve().parent.parent
COLOR_GEN = ROOT / "scripts" / "manim_color_short.py"
QUEUE_DIR = ROOT / "output" / "queue"
MUSIC_DIR = ROOT / "assets" / "music" / "kevin"

DANCE_TRACKS = [
    "Monkeys Spinning Monkeys.mp3", "Quirky Dog.mp3", "Merry Go.mp3",
    "Happy Happy Game Show.mp3", "Carefree.mp3", "Hyperfun.mp3",
    "Overworld.mp3", "Pinball Spring.mp3", "Sneaky Snitch.mp3", "Wholesome.mp3",
    "Life of Riley.mp3", "Walking Along.mp3", "Heartwarming.mp3",
]

COLORS = ["red", "orange", "yellow", "green", "blue", "purple", "pink", "brown"]

TITLES = {
    "rainbow": "🌈 Learn Colors for Kids! 30 Minutes | Happy Bear Kids",
    "all":     "🎨 All Colors for Kids! 30 Minutes | Happy Bear Kids",
}

TAGS_BASE = [
    "colors for kids", "learn colors", "toddler learning", "preschool colors",
    "happy bear kids", "educational video", "kids learning", "color names",
    "color recognition", "30 minutes",
]


def pick_music() -> Path | None:
    tracks = DANCE_TRACKS.copy()
    random.shuffle(tracks)
    for name in tracks:
        p = MUSIC_DIR / name
        if p.exists() and p.stat().st_size > 1000:
            return p
    return None


def render_color(color: str, tmpdir: Path, quality: str) -> Path | None:
    out = tmpdir / f"color_{color}.mp4"
    cmd = [
        sys.executable, str(COLOR_GEN),
        "--color", color,
        "--output", str(out),
        "--quality", quality,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0 and out.exists():
        return out
    print(f"  [render fail] {color}: {result.stderr[-200:]}")
    return None


def concat_to_duration(segments: list[Path], target_sec: int, tmpdir: Path) -> Path | None:
    """Repeat segments cyclically until target duration, then cut."""
    # Build enough repetitions
    total_needed = target_sec + 120  # 2 min buffer
    playlist = []
    elapsed = 0
    idx = 0
    while elapsed < total_needed:
        seg = segments[idx % len(segments)]
        playlist.append(seg)
        # Rough duration guess (60s per segment)
        elapsed += 60
        idx += 1

    concat_list = tmpdir / "concat.txt"
    concat_list.write_text("\n".join(f"file '{p}'" for p in playlist))

    raw = tmpdir / "raw_concat.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-t", str(target_sec),
        "-c", "copy",
        str(raw),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not raw.exists():
        print(f"  [concat fail]: {r.stderr[-200:]}")
        return None
    return raw


def add_music(video: Path, music: Path, output: Path, target_sec: int) -> bool:
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video),
        "-stream_loop", "-1", "-i", str(music),
        "-filter_complex",
        "[1:a]volume=0.18[mus];[mus]apad=whole_dur=" + str(target_sec) + "[aout]",
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-t", str(target_sec),
        str(output),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode == 0 and output.exists()


def make_meta(out_path: Path, duration_min: int):
    meta = {
        "title":            "🎨 Learn Colors for Kids! " + str(duration_min) + " Minutes | Happy Bear Kids",
        "video_type":       "colors",
        "theme":            "colors",
        "duration_minutes": duration_min,
        "is_short":         False,
        "tags":             TAGS_BASE + COLORS,
        "status":           "public",
    }
    meta_path = out_path.parent / f"meta_{out_path.stem}.yaml"
    with open(meta_path, "w") as f:
        yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=int, default=30, help="Video duration in minutes")
    parser.add_argument("--quality",  default="m", choices=["l", "m", "h"])
    args = parser.parse_args()

    target_sec = args.duration * 60
    date_str   = datetime.now().strftime("%Y%m%d")
    out_name   = f"colors_all_{date_str}.mp4"
    out_path   = QUEUE_DIR / out_name

    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    tmpdir = Path(tempfile.mkdtemp(prefix="color_video_"))

    print(f"\nGenerating {args.duration}-min color video → {out_name}")
    print(f"Rendering {len(COLORS)} color segments...")

    segments = []
    for color in COLORS:
        print(f"  [{color}]", end="  ", flush=True)
        seg = render_color(color, tmpdir, args.quality)
        if seg:
            print("✓")
            segments.append(seg)
        else:
            print("✗ skipped")

    if not segments:
        print("No segments rendered. Aborting.")
        shutil.rmtree(tmpdir, ignore_errors=True)
        return

    print(f"\nConcatenating {len(segments)} segments → {target_sec}s...")
    raw = concat_to_duration(segments, target_sec, tmpdir)
    if not raw:
        shutil.rmtree(tmpdir, ignore_errors=True)
        return

    music = pick_music()
    if music:
        print(f"Adding music: {music.name}")
        ok = add_music(raw, music, out_path, target_sec)
        if not ok:
            shutil.copy2(raw, out_path)
    else:
        shutil.copy2(raw, out_path)

    shutil.rmtree(tmpdir, ignore_errors=True)

    if out_path.exists():
        size_mb = out_path.stat().st_size / 1024 / 1024
        print(f"\n✓ {out_name}  {size_mb:.1f}MB")
        make_meta(out_path, args.duration)
    else:
        print("\n✗ Output not created")


if __name__ == "__main__":
    main()
