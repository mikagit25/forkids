#!/usr/bin/env python3
"""
Render a 30-min shapes dance video from a YAML script using Manim + ffmpeg.

Pipeline:
  YAML script → render each scene with Manim → ffmpeg concat → add music → output MP4

Usage:
  python3 manim_shapes_video.py --script config/scripts/shapes_rainbow.yaml
  python3 manim_shapes_video.py --theme rainbow   # auto-generates script first
  python3 manim_shapes_video.py --theme pastel --duration 30 --seed 7
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

ROOT       = Path(__file__).resolve().parent.parent
SCENE_FILE = ROOT / "scripts" / "manim_shapes_scene.py"
PARAMS_TMP = Path("/tmp/manim_shape_params.json")

DANCE_TRACKS = [
    "Monkeys Spinning Monkeys.mp3",
    "Pixelland.mp3",
    "Carefree.mp3",
    "Happy Happy Game Show.mp3",
    "Sneaky Snitch.mp3",
    "Hyperfun.mp3",
    "Quirky Dog.mp3",
    "Merry Go.mp3",
    "Overworld.mp3",
    "Pinball Spring.mp3",
    "Wholesome.mp3",
    "Life of Riley.mp3",
    "Walking Along.mp3",
    "Heartwarming.mp3",
]
MUSIC_DIR = ROOT / "assets" / "music" / "kevin"


def pick_music() -> Path | None:
    for name in random.sample(DANCE_TRACKS, len(DANCE_TRACKS)):
        p = MUSIC_DIR / name
        if p.exists() and p.stat().st_size > 1000:
            return p
    return None


def render_scene(scene_params: dict, out_mp4: Path, quality: str = "m") -> bool:
    """Write params JSON, call manim, return True on success."""
    PARAMS_TMP.write_text(json.dumps(scene_params))

    media_dir = out_mp4.parent / "_manim_tmp"
    cmd = [
        "manim",
        f"-q{quality}",
        "--media_dir", str(media_dir),
        "--disable_caching",
        str(SCENE_FILE),
        "ShapeScene",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"    [manim error] {result.stderr[-800:]}")
        return False

    rendered = list(media_dir.rglob("ShapeScene.mp4"))
    if not rendered:
        print("    [error] No ShapeScene.mp4 found")
        return False

    shutil.copy2(rendered[0], out_mp4)
    shutil.rmtree(media_dir, ignore_errors=True)
    return True


def concat_videos(clips: list[Path], output: Path) -> bool:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for c in clips:
            f.write(f"file '{c.resolve()}'\n")
        concat_list = f.name

    result = subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_list,
        "-c", "copy",
        str(output),
    ], capture_output=True, text=True)
    Path(concat_list).unlink(missing_ok=True)
    return result.returncode == 0


def add_music(video: Path, music: Path, output: Path) -> bool:
    result = subprocess.run([
        "ffmpeg", "-y",
        "-i", str(video),
        "-stream_loop", "-1", "-i", str(music),
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        "-map", "0:v:0", "-map", "1:a:0",
        str(output),
    ], capture_output=True, text=True)
    return result.returncode == 0


def make_meta(script: dict, output_file: Path):
    import yaml as _yaml
    meta = {
        "title":            script.get("title", "Shapes Dance Party | Happy Bear Kids"),
        "video_type":       "shape_dance",
        "theme":            script.get("theme", "rainbow"),
        "duration_minutes": script.get("duration_minutes", 30),
        "is_short":         False,
        "tags":             script.get("tags", []),
        "status":           "public",
    }
    meta_path = output_file.parent / f"meta_{output_file.stem}.yaml"
    with open(meta_path, "w") as f:
        _yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    return meta_path


def render_video(script: dict, output: Path, quality: str = "m") -> bool:
    scenes  = script["scenes"]
    n       = len(scenes)
    tmpdir  = Path(tempfile.mkdtemp(prefix="shapes_"))

    print(f"\nRendering {n} scenes → {output.name}")
    clips   = []
    failed  = 0

    for i, scene in enumerate(scenes):
        clip_path = tmpdir / f"scene_{i:03d}.mp4"
        params = {
            "choreo":     scene["choreo"],
            "shape_type": scene["shape"],
            "n":          scene["n"],
            "colors":     scene["colors"],
            "bg_color":   scene["bg_color"],
            "duration":   scene["duration"],
            "size":       scene.get("size", 0.65),
            "seed":       i,
        }
        print(f"  [{i+1:2d}/{n}] {scene['choreo']:<16} {scene['shape']:<10} n={scene['n']}",
              end="  ", flush=True)

        ok = render_scene(params, clip_path, quality)
        if ok:
            clips.append(clip_path)
            size_kb = clip_path.stat().st_size // 1024
            print(f"✓ {size_kb}KB")
        else:
            failed += 1
            print("✗ FAILED")

    if not clips:
        print("No clips rendered — abort")
        shutil.rmtree(tmpdir, ignore_errors=True)
        return False

    print(f"\nConcatenating {len(clips)} clips...", flush=True)
    raw = tmpdir / "raw.mp4"
    if not concat_videos(clips, raw):
        print("ffmpeg concat failed")
        shutil.rmtree(tmpdir, ignore_errors=True)
        return False

    music = pick_music()
    if music:
        print(f"Adding music: {music.name}")
        if not add_music(raw, music, output):
            print("Music mix failed — copying raw video")
            shutil.copy2(raw, output)
    else:
        print("No music found — copying raw video")
        shutil.copy2(raw, output)

    shutil.rmtree(tmpdir, ignore_errors=True)

    size_mb = output.stat().st_size / 1024 / 1024
    print(f"\n✓ {output.name}  {size_mb:.0f}MB  ({len(clips)}/{n} scenes, {failed} failed)")
    if failed:
        print(f"  WARNING: {failed} scenes failed")
    return True


def main():
    parser = argparse.ArgumentParser(description="Render shapes dance video")
    parser.add_argument("--script",   default=None, help="Path to YAML script")
    parser.add_argument("--theme",    default="rainbow",
                        choices=["rainbow", "pastel", "warm", "cool", "neon"])
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--seed",     type=int, default=42)
    parser.add_argument("--output",   default=None)
    parser.add_argument("--quality",  default="m",
                        choices=["l", "m", "h"], help="l=480p m=720p h=1080p")
    parser.add_argument("--dry-run",  action="store_true",
                        help="Show scene list without rendering")
    args = parser.parse_args()

    # Load or generate script
    if args.script:
        script_path = ROOT / args.script
        with open(script_path) as f:
            script = yaml.safe_load(f)
    else:
        from generate_shapes_script import generate
        script = generate(args.theme, args.duration, args.seed)
        # Save it
        out_name = ROOT / f"config/scripts/shapes_{args.theme}.yaml"
        out_name.parent.mkdir(parents=True, exist_ok=True)
        with open(out_name, "w") as f:
            yaml.dump(script, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        print(f"Script saved → {out_name}")

    if args.dry_run:
        print(f"\nDRY RUN — {len(script['scenes'])} scenes:")
        for i, s in enumerate(script["scenes"]):
            print(f"  {i+1:2d}. {s['choreo']:<16} {s['shape']:<10} n={s['n']}")
        return

    date_str = datetime.now().strftime("%Y%m%d")
    theme    = script.get("theme", args.theme)
    out_path = Path(args.output) if args.output else \
               ROOT / "output" / "queue" / f"dance_shapes_{theme}_{date_str}.mp4"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    ok = render_video(script, out_path, args.quality)
    if ok:
        make_meta(script, out_path)
        print(f"Meta → meta_{out_path.stem}.yaml")


if __name__ == "__main__":
    main()
