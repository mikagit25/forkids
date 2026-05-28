#!/usr/bin/env python3
"""
Compile individual dance shorts into long compilation videos using ffmpeg concat.
Fast — no re-rendering, uses already-generated MP4s.
Output: output/queue/compilation_{theme}_{date}.mp4
"""
import subprocess
import tempfile
import yaml
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent

ANIMALS = [
    "bear", "tiger", "frog", "penguin", "lion", "panda", "koala", "fox",
    "rabbit", "cow", "duck", "pig", "elephant", "monkey", "dog",
    "cat", "owl", "unicorn", "dino", "parrot",
]
FRUITS = [
    "apple", "banana", "strawberry", "grapes", "watermelon", "orange",
    "pineapple", "cherry", "peach", "lemon", "pear", "melon",
]
VEGETABLES = [
    "carrot", "broccoli", "corn", "eggplant", "tomato",
    "cucumber", "potato", "mushroom", "onion", "pepper",
]

COMPILATIONS = [
    {
        "name": "animals",
        "chars": ANIMALS,
        "title": "🐻 Animals Dance Party 20 Minutes | All Animals Dancing | Happy Bear Kids",
        "tags": ["animals dance", "kids dance", "20 minutes", "animal party",
                 "baby dance", "toddler dance", "happy bear kids", "dance compilation",
                 "kids music", "cute animals dancing", "children songs"],
    },
    {
        "name": "fruits",
        "chars": FRUITS,
        "title": "🍎 Fruits Dance Party 12 Minutes | All Fruits Dancing | Happy Bear Kids",
        "tags": ["fruits dance", "kids dance", "fruit party", "dancing fruits",
                 "baby dance", "toddler dance", "happy bear kids", "dance compilation",
                 "kids music", "fruits for kids", "children songs"],
    },
    {
        "name": "vegetables",
        "chars": VEGETABLES,
        "title": "🥕 Vegetables Dance Party 10 Minutes | All Vegetables Dancing | Happy Bear Kids",
        "tags": ["vegetables dance", "kids dance", "vegetable party", "dancing vegetables",
                 "baby dance", "toddler dance", "happy bear kids", "dance compilation",
                 "kids music", "vegetables for kids", "children songs"],
    },
    {
        "name": "all_dance",
        "chars": ANIMALS + FRUITS + VEGETABLES,
        "title": "🎉 Big Dance Party 42 Minutes | Animals Fruits Vegetables | Happy Bear Kids",
        "tags": ["dance party", "kids dance", "42 minutes", "animals fruits vegetables",
                 "baby dance", "toddler dance", "happy bear kids", "big compilation",
                 "kids music", "dance for kids", "children songs"],
    },
]


def find_short(char: str, queue_dir: Path) -> Path | None:
    """Find the most recent short_dance_{char}_*.mp4 in queue or uploaded."""
    for d in [queue_dir, queue_dir.parent.parent / "uploaded"]:
        candidates = sorted(d.glob(f"short_dance_{char}_*.mp4"), reverse=True)
        if candidates:
            return candidates[0]
    return None


def make_meta(comp: dict, output_file: Path, duration_min: int) -> Path:
    meta = {
        "title": comp["title"],
        "video_type": "dance",
        "theme": comp["name"],
        "duration_minutes": duration_min,
        "is_short": False,
        "tags": comp["tags"],
        "status": "public",
    }
    meta_path = output_file.parent / f"meta_{output_file.stem}.yaml"
    with open(meta_path, "w") as f:
        yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    return meta_path


def compile_videos(files: list[Path], output: Path) -> bool:
    """Concatenate MP4 files using ffmpeg concat demuxer."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tf:
        for f in files:
            tf.write(f"file '{f.resolve()}'\n")
        concat_list = tf.name

    result = subprocess.run([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_list,
        "-c", "copy",
        str(output),
    ], capture_output=True, text=True)

    Path(concat_list).unlink(missing_ok=True)
    return result.returncode == 0


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--compilations", nargs="+",
                        default=[c["name"] for c in COMPILATIONS],
                        help="Which compilations to build")
    parser.add_argument("--skip-existing", action="store_true", default=True)
    args = parser.parse_args()

    queue_dir = ROOT / "output" / "queue"
    date_str = datetime.now().strftime("%Y%m%d")

    for comp in COMPILATIONS:
        if comp["name"] not in args.compilations:
            continue

        out_file = queue_dir / f"compilation_{comp['name']}_{date_str}.mp4"
        if args.skip_existing and out_file.exists():
            print(f"SKIP {comp['name']} (exists)")
            continue

        print(f"Building: {comp['name']}...", flush=True)

        found = []
        missing = []
        for char in comp["chars"]:
            p = find_short(char, queue_dir)
            if p:
                found.append(p)
            else:
                missing.append(char)

        if missing:
            print(f"  WARNING: missing shorts for: {', '.join(missing)}")

        if not found:
            print(f"  ERROR: no shorts found, skipping")
            continue

        total_sec = len(found) * 60
        duration_min = round(total_sec / 60)

        print(f"  Concatenating {len(found)} clips ({duration_min} min)...")
        ok = compile_videos(found, out_file)

        if ok:
            size_mb = out_file.stat().st_size / 1024 / 1024
            make_meta(comp, out_file, duration_min)
            print(f"  ✓ {out_file.name}  {size_mb:.0f}MB  ({duration_min} min)")
        else:
            print(f"  ✗ ffmpeg failed")

    print("\nDone! Compilations in queue:")
    for f in sorted(queue_dir.glob("compilation_*.mp4")):
        size_mb = f.stat().st_size / 1024 / 1024
        print(f"  {f.name}  {size_mb:.0f}MB")


if __name__ == "__main__":
    main()
