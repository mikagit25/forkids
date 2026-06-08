#!/usr/bin/env python3
"""
Generate dance shorts (60s) for each vegetable — one short per vegetable.
Output: output/queue/short_dance_{vegetable}_{date}.mp4
"""
import subprocess
import yaml
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent

VEGETABLES = [
    "carrot", "broccoli", "corn", "eggplant", "tomato",
    "cucumber", "potato", "mushroom", "onion", "pepper",
]

# Vegetables with new cartoon sprites (vegetables_cartoon/)
CARTOON_VEGETABLES = {
    "carrot", "broccoli", "corn", "eggplant", "tomato",
    "cucumber", "potato", "onion", "pepper",
}

VEGETABLE_NAMES = {
    "carrot": "Carrot", "broccoli": "Broccoli", "corn": "Corn",
    "eggplant": "Eggplant", "tomato": "Tomato", "cucumber": "Cucumber",
    "potato": "Potato", "mushroom": "Mushroom", "onion": "Onion",
    "pepper": "Pepper",
}

SOLO_CHOREOS = [
    "solo_bounce", "solo_sway", "solo_spin", "solo_wave",
    "solo_jump", "solo_twist", "solo_nod", "solo_shimmy",
]

BG_COLORS = [
    "#E8F5E9", "#F1F8E9", "#E0F2F1", "#F9FBE7",
    "#FFF9E6", "#E3F2FD", "#FCE4EC", "#F3E5F5",
    "#E0F7FA", "#FFFDE7",
]

TITLES = {
    "carrot":   "🥕 Dancing Carrot | Happy Bear Kids #shorts",
    "broccoli": "🥦 Dancing Broccoli | Happy Bear Kids #shorts",
    "corn":     "🌽 Dancing Corn | Happy Bear Kids #shorts",
    "eggplant": "🍆 Dancing Eggplant | Happy Bear Kids #shorts",
    "tomato":   "🍅 Dancing Tomato | Happy Bear Kids #shorts",
    "cucumber": "🥒 Dancing Cucumber | Happy Bear Kids #shorts",
    "potato":   "🥔 Dancing Potato | Happy Bear Kids #shorts",
    "mushroom": "🍄 Dancing Mushroom | Happy Bear Kids #shorts",
    "onion":    "🧅 Dancing Onion | Happy Bear Kids #shorts",
    "pepper":   "🫑 Dancing Pepper | Happy Bear Kids #shorts",
}


def make_short_script(veg: str, idx: int) -> Path:
    choreo = SOLO_CHOREOS[idx % len(SOLO_CHOREOS)]
    bg = BG_COLORS[idx % len(BG_COLORS)]
    name = VEGETABLE_NAMES.get(veg, veg.capitalize())

    theme = "vegetables_cartoon" if veg in CARTOON_VEGETABLES else "vegetables"
    script = {
        "video_type": "short_dance",
        "theme": theme,
        "duration_minutes": 1,
        "style": "tutitu",
        "scenes": [
            {
                "start_sec": 0.0,
                "duration": 60.0,
                "choreo": choreo,
                "n": 1,
                "chars": [veg],
                "entry": "zoom_in",
                "bg_color": bg,
                "text": name,
                "sub_text": "Let's dance!",
            }
        ],
    }

    out = ROOT / "config" / "scripts" / f"short_dance_{veg}.yaml"
    with open(out, "w") as f:
        yaml.dump(script, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    return out


def make_meta(veg: str, output_file: Path) -> Path:
    name = VEGETABLE_NAMES.get(veg, veg.capitalize())
    theme = "vegetables_cartoon" if veg in CARTOON_VEGETABLES else "vegetables"
    meta = {
        "title": TITLES[veg],
        "video_type": "short_dance",
        "theme": theme,
        "duration_minutes": 1,
        "is_short": True,
        "tags": [
            f"dancing {name.lower()}", "kids dance", "baby dance",
            "toddler dance", "children songs", "nursery rhymes",
            "happy bear kids", name.lower(), "vegetable dance",
            "kids music", "dance for kids", "vegetables for kids",
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
    parser.add_argument("--vegetables", nargs="+", default=VEGETABLES, help="Which vegetables to generate")
    parser.add_argument("--skip-existing", action="store_true", default=True)
    args = parser.parse_args()

    queue_dir = ROOT / "output" / "queue"
    queue_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime("%Y%m%d")
    total = len(args.vegetables)

    for idx, veg in enumerate(args.vegetables):
        out_file = queue_dir / f"short_dance_{veg}_{date_str}.mp4"

        if args.skip_existing and out_file.exists():
            print(f"[{idx+1}/{total}] SKIP {veg} (exists)")
            continue

        print(f"[{idx+1}/{total}] Generating: {veg}...", flush=True)
        script_path = make_short_script(veg, idx)
        meta_path = make_meta(veg, out_file)

        result = subprocess.run([
            "python3", str(ROOT / "scripts" / "generate_video.py"),
            "--theme", "vegetables",
            "--duration", "1",
            "--script", str(script_path),
            "--shorts",
            "--output", str(out_file),
        ], capture_output=True, text=True, cwd=str(ROOT))

        if result.returncode == 0:
            print(f"  ✓ {out_file.name}")
        else:
            print(f"  ✗ ERROR: {result.stderr[-300:]}")

    print("\nDone! Vegetable shorts in queue:")
    for f in sorted(queue_dir.glob("short_dance_*_*.mp4")):
        if any(v in f.name for v in VEGETABLES):
            size_mb = f.stat().st_size / 1024 / 1024
            print(f"  {f.name}  {size_mb:.1f}MB")


if __name__ == "__main__":
    main()
