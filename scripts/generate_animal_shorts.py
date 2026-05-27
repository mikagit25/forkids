#!/usr/bin/env python3
"""
Generate dance shorts (60s) for each animal — one short per animal.
Output: output/queue/short_dance_{animal}_{date}.mp4
"""
import subprocess
import sys
import yaml
import random
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent

ANIMALS = [
    "bear", "tiger", "frog", "penguin", "lion",
    "panda", "koala", "fox", "rabbit", "cow",
    "duck", "pig", "elephant", "monkey", "dog",
    "cat", "owl", "unicorn", "dino", "parrot",
]

ANIMAL_NAMES = {
    "bear": "Bear", "tiger": "Tiger", "frog": "Frog",
    "penguin": "Penguin", "lion": "Lion", "panda": "Panda",
    "koala": "Koala", "fox": "Fox", "rabbit": "Rabbit",
    "cow": "Cow", "duck": "Duck", "pig": "Pig",
    "elephant": "Elephant", "monkey": "Monkey", "dog": "Dog",
    "cat": "Cat", "owl": "Owl", "unicorn": "Unicorn",
    "dino": "Dino", "parrot": "Parrot",
}

SOLO_CHOREOS = [
    "solo_bounce", "solo_sway", "solo_spin", "solo_wave",
    "solo_jump", "solo_twist", "solo_nod", "solo_shimmy",
]

BG_COLORS = [
    "#FFF9E6", "#E8F5E9", "#E3F2FD", "#FCE4EC",
    "#F3E5F5", "#E0F7FA", "#FFFDE7", "#F9FBE7",
    "#FFF3E0", "#E8EAF6", "#F1F8E9", "#FFF8E1",
    "#E0F2F1", "#FCE4EC", "#E8F5E9", "#EDE7F6",
    "#E1F5FE", "#F9FBE7", "#FFF9E6", "#E3F2FD",
]

TITLES = {
    "bear":     "🐻 Dancing Bear | Happy Bear Kids #shorts",
    "tiger":    "🐯 Dancing Tiger | Happy Bear Kids #shorts",
    "frog":     "🐸 Dancing Frog | Happy Bear Kids #shorts",
    "penguin":  "🐧 Dancing Penguin | Happy Bear Kids #shorts",
    "lion":     "🦁 Dancing Lion | Happy Bear Kids #shorts",
    "panda":    "🐼 Dancing Panda | Happy Bear Kids #shorts",
    "koala":    "🐨 Dancing Koala | Happy Bear Kids #shorts",
    "fox":      "🦊 Dancing Fox | Happy Bear Kids #shorts",
    "rabbit":   "🐰 Dancing Rabbit | Happy Bear Kids #shorts",
    "cow":      "🐮 Dancing Cow | Happy Bear Kids #shorts",
    "duck":     "🦆 Dancing Duck | Happy Bear Kids #shorts",
    "pig":      "🐷 Dancing Pig | Happy Bear Kids #shorts",
    "elephant": "🐘 Dancing Elephant | Happy Bear Kids #shorts",
    "monkey":   "🐒 Dancing Monkey | Happy Bear Kids #shorts",
    "dog":      "🐶 Dancing Dog | Happy Bear Kids #shorts",
    "cat":      "🐱 Dancing Cat | Happy Bear Kids #shorts",
    "owl":      "🦉 Dancing Owl | Happy Bear Kids #shorts",
    "unicorn":  "🦄 Dancing Unicorn | Happy Bear Kids #shorts",
    "dino":     "🦕 Dancing Dino | Happy Bear Kids #shorts",
    "parrot":   "🦜 Dancing Parrot | Happy Bear Kids #shorts",
}


def make_short_script(animal: str, idx: int) -> Path:
    """Generate a 60s script for one animal."""
    choreo = SOLO_CHOREOS[idx % len(SOLO_CHOREOS)]
    bg = BG_COLORS[idx % len(BG_COLORS)]
    name = ANIMAL_NAMES.get(animal, animal.capitalize())

    script = {
        "video_type": "short_dance",
        "theme": "animals",
        "duration_minutes": 1,
        "style": "tutitu",
        "scenes": [
            {
                "start_sec": 0.0,
                "duration": 60.0,
                "choreo": choreo,
                "n": 1,
                "chars": [animal],
                "entry": "zoom_in",
                "bg_color": bg,
                "text": name,
                "sub_text": "Let's dance!",
            }
        ],
    }

    out = ROOT / "config" / "scripts" / f"short_dance_{animal}.yaml"
    with open(out, "w") as f:
        yaml.dump(script, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    return out


def make_meta(animal: str, output_file: Path) -> Path:
    """Write meta sidecar for upload_youtube."""
    name = ANIMAL_NAMES.get(animal, animal.capitalize())
    meta = {
        "title": TITLES[animal],
        "video_type": "short_dance",
        "theme": "animals",
        "duration_minutes": 1,
        "is_short": True,
        "tags": [
            f"dancing {name.lower()}", "kids dance", "baby dance",
            "toddler dance", "children songs", "nursery rhymes",
            "happy bear kids", name.lower(), "animal dance",
            "kids music", "dance for kids", "cute animals",
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
    parser.add_argument("--animals", nargs="+", default=ANIMALS, help="Which animals to generate")
    parser.add_argument("--skip-existing", action="store_true", default=True)
    args = parser.parse_args()

    queue_dir = ROOT / "output" / "queue"
    queue_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime("%Y%m%d")
    total = len(args.animals)

    for idx, animal in enumerate(args.animals):
        out_file = queue_dir / f"short_dance_{animal}_{date_str}.mp4"

        if args.skip_existing and out_file.exists():
            print(f"[{idx+1}/{total}] SKIP {animal} (exists)")
            continue

        print(f"[{idx+1}/{total}] Generating: {animal}...", flush=True)
        script_path = make_short_script(animal, idx)
        meta_path = make_meta(animal, out_file)

        result = subprocess.run([
            "python3", str(ROOT / "scripts" / "generate_video.py"),
            "--theme", "animals",
            "--duration", "1",
            "--script", str(script_path),
            "--shorts",
            "--output", str(out_file),
        ], capture_output=True, text=True, cwd=str(ROOT))

        if result.returncode == 0:
            print(f"  ✓ {out_file.name}")
        else:
            print(f"  ✗ ERROR: {result.stderr[-200:]}")

    print("\nDone! Queue contents:")
    for f in sorted(queue_dir.glob("short_dance_*.mp4")):
        size_mb = f.stat().st_size / 1024 / 1024
        print(f"  {f.name}  {size_mb:.1f}MB")


if __name__ == "__main__":
    main()
