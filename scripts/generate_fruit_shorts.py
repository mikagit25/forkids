#!/usr/bin/env python3
"""
Generate dance shorts (60s) for each fruit — one short per fruit.
Output: output/queue/short_dance_{fruit}_{date}.mp4
"""
import subprocess
import yaml
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent

FRUITS = [
    "apple", "banana", "strawberry", "grapes", "watermelon", "orange",
    "pineapple", "cherry", "peach", "lemon", "pear", "melon",
]

FRUIT_NAMES = {
    "apple": "Apple", "banana": "Banana", "strawberry": "Strawberry",
    "grapes": "Grapes", "watermelon": "Watermelon", "orange": "Orange",
    "pineapple": "Pineapple", "cherry": "Cherry", "peach": "Peach",
    "lemon": "Lemon", "pear": "Pear", "melon": "Melon",
}

SOLO_CHOREOS = [
    "solo_bounce", "solo_sway", "solo_spin", "solo_wave",
    "solo_jump", "solo_twist", "solo_nod", "solo_shimmy",
]

BG_COLORS = [
    "#FFF9E6", "#E8F5E9", "#E3F2FD", "#FCE4EC",
    "#F3E5F5", "#E0F7FA", "#FFFDE7", "#F9FBE7",
    "#FFF3E0", "#E8EAF6", "#F1F8E9", "#FFF8E1",
]

TITLES = {
    "apple":      "🍎 Dancing Apple | Happy Bear Kids #shorts",
    "banana":     "🍌 Dancing Banana | Happy Bear Kids #shorts",
    "strawberry": "🍓 Dancing Strawberry | Happy Bear Kids #shorts",
    "grapes":     "🍇 Dancing Grapes | Happy Bear Kids #shorts",
    "watermelon": "🍉 Dancing Watermelon | Happy Bear Kids #shorts",
    "orange":     "🍊 Dancing Orange | Happy Bear Kids #shorts",
    "pineapple":  "🍍 Dancing Pineapple | Happy Bear Kids #shorts",
    "cherry":     "🍒 Dancing Cherry | Happy Bear Kids #shorts",
    "peach":      "🍑 Dancing Peach | Happy Bear Kids #shorts",
    "lemon":      "🍋 Dancing Lemon | Happy Bear Kids #shorts",
    "pear":       "🍐 Dancing Pear | Happy Bear Kids #shorts",
    "melon":      "🍈 Dancing Melon | Happy Bear Kids #shorts",
}


def make_short_script(fruit: str, idx: int) -> Path:
    choreo = SOLO_CHOREOS[idx % len(SOLO_CHOREOS)]
    bg = BG_COLORS[idx % len(BG_COLORS)]
    name = FRUIT_NAMES.get(fruit, fruit.capitalize())

    script = {
        "video_type": "short_dance",
        "theme": "fruits",
        "duration_minutes": 1,
        "style": "tutitu",
        "scenes": [
            {
                "start_sec": 0.0,
                "duration": 60.0,
                "choreo": choreo,
                "n": 1,
                "chars": [fruit],
                "entry": "zoom_in",
                "bg_color": bg,
                "text": name,
                "sub_text": "Let's dance!",
            }
        ],
    }

    out = ROOT / "config" / "scripts" / f"short_dance_{fruit}.yaml"
    with open(out, "w") as f:
        yaml.dump(script, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    return out


def make_meta(fruit: str, output_file: Path) -> Path:
    name = FRUIT_NAMES.get(fruit, fruit.capitalize())
    meta = {
        "title": TITLES[fruit],
        "video_type": "short_dance",
        "theme": "fruits",
        "duration_minutes": 1,
        "is_short": True,
        "tags": [
            f"dancing {name.lower()}", "kids dance", "baby dance",
            "toddler dance", "children songs", "nursery rhymes",
            "happy bear kids", name.lower(), "fruit dance",
            "kids music", "dance for kids", "cute fruits",
        ],
        "status": "public",
    }
    meta_path = output_file.parent / f"meta_{output_file.stem}.yaml"
    with open(meta_path, "w") as f:
        yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    return meta_path


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--fruits", nargs="+", default=FRUITS, help="Which fruits to generate")
    parser.add_argument("--skip-existing", action="store_true", default=True)
    args = parser.parse_args()

    queue_dir = ROOT / "output" / "queue"
    queue_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime("%Y%m%d")
    total = len(args.fruits)

    for idx, fruit in enumerate(args.fruits):
        out_file = queue_dir / f"short_dance_{fruit}_{date_str}.mp4"

        if args.skip_existing and out_file.exists():
            print(f"[{idx+1}/{total}] SKIP {fruit} (exists)")
            continue

        print(f"[{idx+1}/{total}] Generating: {fruit}...", flush=True)
        script_path = make_short_script(fruit, idx)
        meta_path = make_meta(fruit, out_file)

        result = subprocess.run([
            "python3", str(ROOT / "scripts" / "generate_video.py"),
            "--theme", "fruits",
            "--duration", "1",
            "--script", str(script_path),
            "--shorts",
            "--output", str(out_file),
        ], capture_output=True, text=True, cwd=str(ROOT))

        if result.returncode == 0:
            print(f"  ✓ {out_file.name}")
        else:
            print(f"  ✗ ERROR: {result.stderr[-300:]}")

    print("\nDone! Fruit shorts in queue:")
    for f in sorted(queue_dir.glob("short_dance_*_*.mp4")):
        if any(fr in f.name for fr in FRUITS):
            size_mb = f.stat().st_size / 1024 / 1024
            print(f"  {f.name}  {size_mb:.1f}MB")


if __name__ == "__main__":
    main()
