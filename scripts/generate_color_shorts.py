#!/usr/bin/env python3
"""
Generate color shorts (60s) — one per color per theme.
Each short: colored background + characters in that color's hue + color name.
Output: output/queue/short_color_{color}_{theme}_{date}.mp4
"""
import subprocess
import yaml
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent

COLORS = [
    {"name": "Red",    "key": "red",    "bg": "#FF4444", "emoji": "🔴"},
    {"name": "Orange", "key": "orange", "bg": "#FF7F2A", "emoji": "🟠"},
    {"name": "Yellow", "key": "yellow", "bg": "#FFD700", "emoji": "🟡"},
    {"name": "Green",  "key": "green",  "bg": "#27AE60", "emoji": "🟢"},
    {"name": "Blue",   "key": "blue",   "bg": "#2980B9", "emoji": "🔵"},
    {"name": "Purple", "key": "purple", "bg": "#8E44AD", "emoji": "🟣"},
    {"name": "Pink",   "key": "pink",   "bg": "#FF69B4", "emoji": "🩷"},
    {"name": "Brown",  "key": "brown",  "bg": "#8B4513", "emoji": "🟤"},
]

THEMES = {
    "animals": ["bear", "cat", "dog", "duck", "frog", "koala", "panda", "rabbit"],
    "fruits":  ["apple", "banana", "strawberry", "orange", "grapes", "lemon", "peach", "pear"],
    "vegetables": ["carrot", "broccoli", "corn", "tomato", "cucumber", "pepper", "potato", "mushroom"],
}

CHOREOS = ["solo_bounce", "solo_sway", "solo_spin", "solo_wave",
           "solo_jump", "solo_twist", "solo_nod", "solo_shimmy"]

TITLES = {
    ("red",    "animals"):    "🔴 Red Color with Animals | Learn Red | Happy Bear Kids #shorts",
    ("orange", "animals"):    "🟠 Orange Color with Animals | Learn Orange | Happy Bear Kids #shorts",
    ("yellow", "animals"):    "🟡 Yellow Color with Animals | Learn Yellow | Happy Bear Kids #shorts",
    ("green",  "animals"):    "🟢 Green Color with Animals | Learn Green | Happy Bear Kids #shorts",
    ("blue",   "animals"):    "🔵 Blue Color with Animals | Learn Blue | Happy Bear Kids #shorts",
    ("purple", "animals"):    "🟣 Purple Color with Animals | Learn Purple | Happy Bear Kids #shorts",
    ("pink",   "animals"):    "🩷 Pink Color with Animals | Learn Pink | Happy Bear Kids #shorts",
    ("brown",  "animals"):    "🟤 Brown Color with Animals | Learn Brown | Happy Bear Kids #shorts",
    ("red",    "fruits"):     "🔴 Red Color with Fruits | Learn Red | Happy Bear Kids #shorts",
    ("orange", "fruits"):     "🟠 Orange Color with Fruits | Learn Orange | Happy Bear Kids #shorts",
    ("yellow", "fruits"):     "🟡 Yellow Color with Fruits | Learn Yellow | Happy Bear Kids #shorts",
    ("green",  "fruits"):     "🟢 Green Color with Fruits | Learn Green | Happy Bear Kids #shorts",
    ("blue",   "fruits"):     "🔵 Blue Color with Fruits | Learn Blue | Happy Bear Kids #shorts",
    ("purple", "fruits"):     "🟣 Purple Color with Fruits | Learn Purple | Happy Bear Kids #shorts",
    ("pink",   "fruits"):     "🩷 Pink Color with Fruits | Learn Pink | Happy Bear Kids #shorts",
    ("brown",  "fruits"):     "🟤 Brown Color with Fruits | Learn Brown | Happy Bear Kids #shorts",
    ("red",    "vegetables"): "🔴 Red Color with Vegetables | Learn Red | Happy Bear Kids #shorts",
    ("orange", "vegetables"): "🟠 Orange Color with Vegetables | Learn Orange | Happy Bear Kids #shorts",
    ("yellow", "vegetables"): "🟡 Yellow Color with Vegetables | Learn Yellow | Happy Bear Kids #shorts",
    ("green",  "vegetables"): "🟢 Green Color with Vegetables | Learn Green | Happy Bear Kids #shorts",
    ("blue",   "vegetables"): "🔵 Blue Color with Vegetables | Learn Blue | Happy Bear Kids #shorts",
    ("purple", "vegetables"): "🟣 Purple Color with Vegetables | Learn Purple | Happy Bear Kids #shorts",
    ("pink",   "vegetables"): "🩷 Pink Color with Vegetables | Learn Pink | Happy Bear Kids #shorts",
    ("brown",  "vegetables"): "🟤 Brown Color with Vegetables | Learn Brown | Happy Bear Kids #shorts",
}


def make_short_script(color: dict, theme: str, idx: int) -> Path:
    chars = THEMES[theme]
    choreo = CHOREOS[idx % len(CHOREOS)]

    scenes = []
    # 4 × 15s: intro color (15s), then 3 animal/fruit scenes each 15s
    for i in range(4):
        char = chars[i % len(chars)]
        scenes.append({
            "start_sec": round(i * 15.0, 1),
            "duration": 15.0,
            "choreo": choreo,
            "n": 1,
            "chars": [char],
            "entry": "zoom_in",
            "bg_color": color["bg"],
            "text": color["name"],
            "sub_text": f"{color['name']}!",
            "voiceover_key": color["key"],
        })

    script = {
        "video_type": "short_color",
        "theme": theme,
        "duration_minutes": 1,
        "style": "tutitu",
        "scenes": scenes,
    }

    slug = f"short_color_{color['key']}_{theme}"
    out = ROOT / "config" / "scripts" / f"{slug}.yaml"
    with open(out, "w") as f:
        yaml.dump(script, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    return out


def make_meta(color: dict, theme: str, output_file: Path) -> Path:
    title = TITLES.get((color["key"], theme),
                       f"{color['emoji']} {color['name']} Color | Happy Bear Kids #shorts")
    meta = {
        "title": title,
        "video_type": "short_color",
        "theme": theme,
        "duration_minutes": 1,
        "is_short": True,
        "tags": [
            f"learn {color['name'].lower()}", f"{color['name'].lower()} color",
            "colors for kids", "learn colors", "kids learning",
            "toddler colors", "baby colors", "happy bear kids",
            f"{color['name'].lower()}", "educational for kids",
            "preschool colors", theme, "nursery rhymes",
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
    parser.add_argument("--themes", nargs="+", default=list(THEMES.keys()))
    parser.add_argument("--colors", nargs="+", default=[c["key"] for c in COLORS])
    parser.add_argument("--skip-existing", action="store_true", default=True)
    args = parser.parse_args()

    queue_dir = ROOT / "output" / "queue"
    queue_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")

    selected_colors = [c for c in COLORS if c["key"] in args.colors]
    total = len(selected_colors) * len(args.themes)
    idx = 0

    for theme in args.themes:
        for color in selected_colors:
            idx += 1
            slug = f"short_color_{color['key']}_{theme}"
            out_file = queue_dir / f"{slug}_{date_str}.mp4"

            if args.skip_existing and out_file.exists():
                print(f"[{idx}/{total}] SKIP {color['name']}/{theme} (exists)")
                continue

            print(f"[{idx}/{total}] {color['name']} + {theme}...", flush=True)
            script_path = make_short_script(color, theme, idx)
            make_meta(color, theme, out_file)

            result = subprocess.run([
                "python3", str(ROOT / "scripts" / "generate_video.py"),
                "--theme", theme,
                "--duration", "1",
                "--script", str(script_path),
                "--shorts",
                "--output", str(out_file),
            ], capture_output=True, text=True, cwd=str(ROOT))

            if result.returncode == 0:
                print(f"  ✓ {out_file.name}")
            else:
                print(f"  ✗ ERROR: {result.stderr[-200:]}")

    print(f"\nDone! Color shorts in queue:")
    for f in sorted(queue_dir.glob("short_color_*_*.mp4")):
        if f.stat().st_size > 100_000:
            print(f"  {f.name}  {f.stat().st_size/1024/1024:.1f}MB")


if __name__ == "__main__":
    main()
