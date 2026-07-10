#!/usr/bin/env python3
"""
Generate 30-min dance long videos for EN channel (Manim renderer).
Themes: animals, fruits, vegetables.
Handles render → meta → Together.ai thumbnail automatically.

Output: output/queue/dance_{theme}_{date}.mp4

Usage:
  python3 scripts/generate_dance_long.py
  python3 scripts/generate_dance_long.py --themes animals fruits
  python3 scripts/generate_dance_long.py --force
  python3 scripts/generate_dance_long.py --regen-meta
"""
import argparse
import base64
import json
import subprocess
import yaml
from datetime import datetime
from pathlib import Path

import requests

ROOT       = Path(__file__).resolve().parent.parent
QUEUE_DIR  = ROOT / "output" / "queue"
TOGETHER_KEY_FILE = ROOT / "credentials" / "together_api_key.txt"
TOGETHER_URL      = "https://api.together.xyz/v1/images/generations"

THEMES = {
    "animals": {
        "title":        "🐾 Animals Dance Party | 30 Minutes | Happy Bear Kids",
        "script":       "config/scripts/dance_animals.yaml",
        "thumb_prompt": "cute cartoon animals dancing party, bear tiger frog penguin lion panda, colorful background, kids animation style, vibrant colors, 1280x720",
        "tags": [
            "animal dance", "kids music", "30 minutes", "toddler", "happy bear kids",
            "children songs", "baby dance", "animals for kids", "dance party",
            "nursery rhymes", "educational", "animals", "cartoon animals",
        ],
    },
    "fruits": {
        "title":        "🍎 Fruit Dance Party | 30 Minutes | Happy Bear Kids",
        "script":       "config/scripts/dance_fruits.yaml",
        "thumb_prompt": "cute cartoon fruits dancing, apple banana strawberry watermelon orange pineapple, colorful background, kids animation style, vibrant 1280x720",
        "tags": [
            "fruit dance", "kids music", "30 minutes", "toddler", "happy bear kids",
            "children songs", "fruits for kids", "dancing fruits", "dance party",
            "nursery rhymes", "educational", "fruits", "cartoon fruits",
        ],
    },
    "vegetables": {
        "title":        "🥕 Vegetable Dance Party | 30 Minutes | Happy Bear Kids",
        "script":       "config/scripts/dance_vegetables.yaml",
        "thumb_prompt": "cute cartoon vegetables dancing, carrot broccoli tomato corn cucumber pepper, colorful background, kids animation style, vibrant 1280x720",
        "tags": [
            "vegetable dance", "kids music", "30 minutes", "toddler", "happy bear kids",
            "children songs", "vegetables for kids", "dancing vegetables", "dance party",
            "nursery rhymes", "educational", "vegetables", "cartoon vegetables",
        ],
    },
}

DESCRIPTION = """\
Welcome to Happy Bear Kids! 🐻

30 minutes of non-stop {theme_cap} dancing fun! All your favourite {theme} characters \
are here to get you and your family moving and grooving!

Our animations are designed in vivid colours to captivate babies and toddlers. Every \
character is uniquely designed and set to music carefully curated for the whole family to enjoy.

🌟 Key features:
• High contrast colours for visual stimulation
• Fun dance routines for every character
• Friendly, colourful characters
• Upbeat music throughout — no silence, no ads between songs
• Perfect background entertainment for little ones

👶 Great for:
• Babies — tummy time, visual tracking, sensory development
• Toddlers — dancing, movement, learning {theme} names
• Parents — entertains little ones while you get things done!
• Older children — singalong, movement and coordination

🎯 Educational value:
• {theme_cap} recognition and vocabulary
• Colour and shape awareness
• Rhythm and music appreciation
• Cause-and-effect understanding through animated characters

Each character dances in its own unique style, set to cheerful, upbeat music. \
No talking, no ads — just 30 uninterrupted minutes of pure dancing fun. \
Perfect for screen time that gets kids moving!

🎵 Music by Kevin MacLeod (incompetech.com)
Licensed under Creative Commons: By Attribution 4.0 License
http://creativecommons.org/licenses/by/4.0/

© Happy Bear Kids 2026 — All rights reserved
New videos every week! Subscribe ▶ @HappyBearKids1

#HappyBearKids #{theme_cap}Dance #KidsMusic #ToddlerDance #BabyDance #ChildrenSongs #30Minutes\
"""


def make_meta(theme: str, out_path: Path):
    cfg = THEMES[theme]
    desc = DESCRIPTION.format(theme=theme, theme_cap=theme.capitalize())
    meta = {
        "title":            cfg["title"],
        "video_type":       "dance",
        "theme":            theme,
        "language":         "en",
        "duration_minutes": 30,
        "is_short":         False,
        "description":      desc,
        "tags":             cfg["tags"],
        "status":           "public",
    }
    meta_path = out_path.parent / f"meta_{out_path.stem}.yaml"
    with open(meta_path, "w") as f:
        yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    print(f"  meta → {meta_path.name}")
    return meta_path


def generate_thumbnail(theme: str, out_path: Path) -> bool:
    thumb_path = out_path.parent / f"thumb_{out_path.stem}.png"
    if thumb_path.exists():
        print(f"  thumb already exists: {thumb_path.name}")
        return True
    if not TOGETHER_KEY_FILE.exists():
        print("  WARNING: no Together.ai key, thumbnail skipped")
        return False
    api_key = TOGETHER_KEY_FILE.read_text().strip()
    prompt  = THEMES[theme]["thumb_prompt"]
    print(f"  Generating thumbnail ({theme})...", end="  ", flush=True)
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("gat", ROOT / "scripts" / "generate_ai_thumbs.py")
        gat = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gat)
        img = gat.together_generate_image(prompt, api_key)
        if img:
            thumb_path.write_bytes(gat.resize_to_720p(img))
            size_kb = thumb_path.stat().st_size // 1024
            print(f"thumb → {thumb_path.name} ({size_kb}KB)")
            return True
        print(f"thumb failed: API returned no image")
        return False
    except Exception as e:
        print(f"thumbnail error: {e}")
        return False


def render(theme: str, date_str: str, force: bool) -> bool:
    cfg      = THEMES[theme]
    out_name = f"dance_{theme}_{date_str}.mp4"
    out_path = QUEUE_DIR / out_name

    if out_path.exists() and not force:
        size_mb = out_path.stat().st_size / 1024 / 1024
        print(f"  skip {out_name} ({size_mb:.1f}MB exists)")
        make_meta(theme, out_path)
        generate_thumbnail(theme, out_path)
        return True

    script_path = ROOT / cfg["script"]
    cmd = [
        "python3", str(ROOT / "scripts" / "generate_video.py"),
        "--theme", theme,
        "--duration", "30",
        "--output", str(out_path),
    ]
    if script_path.exists():
        cmd += ["--script", str(script_path)]

    print(f"  [{theme}] Rendering 30-min dance (~45-60 min)...", flush=True)
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))

    if result.returncode == 0 and out_path.exists():
        size_mb = out_path.stat().st_size / 1024 / 1024
        print(f"  ✓ {out_name}  {size_mb:.1f}MB")
        make_meta(theme, out_path)
        generate_thumbnail(theme, out_path)
        return True

    err = (result.stderr or result.stdout)[-300:].strip()
    print(f"  ✗ {err}")
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--themes", nargs="+", default=list(THEMES.keys()),
                        choices=list(THEMES.keys()))
    parser.add_argument("--force",     action="store_true", help="Overwrite existing")
    parser.add_argument("--regen-meta", action="store_true",
                        help="Regenerate meta+thumbnail for existing MP4s only")
    args = parser.parse_args()

    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")

    if args.regen_meta:
        for theme in THEMES:
            for mp4 in sorted(QUEUE_DIR.glob(f"dance_{theme}_*.mp4")):
                print(f"  regen: {mp4.name}")
                make_meta(theme, mp4)
                generate_thumbnail(theme, mp4)
        return

    print(f"\nGenerating {len(args.themes)} dance long videos → {QUEUE_DIR}\n")
    ok = 0
    for theme in args.themes:
        if render(theme, date_str, args.force):
            ok += 1

    print(f"\nDone: {ok}/{len(args.themes)} dance long videos generated")


if __name__ == "__main__":
    main()
