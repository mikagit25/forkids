#!/usr/bin/env python3
"""
Generate FLUX AI background images for kids channel dance videos.
Output: remotion/public/backgrounds/

Each background is a 1280x720 JPG (16:9).
Used by DanceSpriteLong via bgImage prop.

Usage:
    python3 scripts/generate_kids_backgrounds.py
    python3 scripts/generate_kids_backgrounds.py --theme meadow_sunny
    python3 scripts/generate_kids_backgrounds.py --force   # regenerate existing
"""
import argparse
import base64
import time
from pathlib import Path

import requests

ROOT       = Path(__file__).resolve().parent.parent
OUT_DIR    = ROOT / "remotion" / "public" / "backgrounds"
KEY_FILE   = ROOT / "credentials" / "together_api_key.txt"
API_URL    = "https://api.together.xyz/v1/images/generations"
MODEL      = "black-forest-labs/FLUX.1-schnell"

BACKGROUNDS = {
    "meadow_sunny": {
        "prompt": (
            "sunny meadow landscape with wildflowers, green hills, blue sky with fluffy white clouds, "
            "butterflies, golden sunlight, soft bokeh, 3D animated kids cartoon style, "
            "bright vivid colors, no people, no animals, no text"
        ),
        "desc": "Sunny meadow with flowers",
    },
    "underwater_world": {
        "prompt": (
            "magical underwater ocean scene, clear blue water, coral reef, colorful sea plants, "
            "light rays streaming from surface, gentle bubbles, 3D animated kids cartoon style, "
            "bright vivid colors, soft glow, no text, no animals, wide landscape"
        ),
        "desc": "Magical underwater world",
    },
    "magical_forest": {
        "prompt": (
            "magical glowing forest at dusk, large friendly trees, fireflies glowing, "
            "soft purple and teal light through canopy, mushrooms with gentle glow, "
            "3D animated kids cartoon style, enchanting warm atmosphere, no text, no animals"
        ),
        "desc": "Magical glowing forest",
    },
    "rainbow_sky": {
        "prompt": (
            "bright rainbow arching across blue sky, white fluffy clouds, warm golden sunlight, "
            "sparkling light rays, cheerful colors pink yellow blue green, "
            "3D animated kids cartoon style, uplifting and joyful, no text, no animals"
        ),
        "desc": "Rainbow and clouds",
    },
    "space_adventure": {
        "prompt": (
            "colorful outer space scene, stars twinkling, colorful nebula in pink purple and blue, "
            "distant planets, sparkles of light, deep space background, "
            "3D animated kids cartoon style, vibrant dreamy atmosphere, no text, no animals"
        ),
        "desc": "Space with stars and nebula",
    },
    "candy_world": {
        "prompt": (
            "candy land landscape, colorful candy mountains, lollipop trees, gumdrops on ground, "
            "cotton candy clouds in pink and blue sky, sparkles everywhere, "
            "3D animated kids cartoon style, bright saturated colors, no text, no animals"
        ),
        "desc": "Candy-land fantasy",
    },
    "night_magic": {
        "prompt": (
            "magical night sky scene, large glowing moon, thousands of golden twinkling stars, "
            "soft purple-blue gradient sky, gentle aurora colors in background, "
            "3D animated kids cartoon style, dreamlike serene atmosphere, no text, no animals"
        ),
        "desc": "Magical night sky with stars",
    },
    "tropical_beach": {
        "prompt": (
            "tropical beach scene, turquoise water, white sandy beach, palm trees swaying, "
            "blue sky with puffy clouds, sun sparkling on water, "
            "3D animated kids cartoon style, bright cheerful summer colors, no text, no animals"
        ),
        "desc": "Tropical beach",
    },
}

# Map animals to the most fitting background theme
ANIMAL_BG_MAP = {
    "cat":       "magical_forest",
    "dog":       "meadow_sunny",
    "rabbit":    "meadow_sunny",
    "duck":      "tropical_beach",
    "guinea_pig":"rainbow_sky",
    "kitten":    "magical_forest",
    "parrot":    "tropical_beach",
    "hamster":   "candy_world",
    "turtle":    "underwater_world",
    "goldfish":  "underwater_world",
    # fruits/vegetables → cheerful backgrounds
    "apple":     "rainbow_sky",
    "banana":    "tropical_beach",
    "strawberry":"meadow_sunny",
    "watermelon":"tropical_beach",
    "orange":    "rainbow_sky",
    "pineapple": "tropical_beach",
    "carrot":    "meadow_sunny",
    "broccoli":  "magical_forest",
    "corn":      "meadow_sunny",
}


def get_api_key() -> str:
    if not KEY_FILE.exists():
        raise FileNotFoundError(f"Together API key not found: {KEY_FILE}")
    return KEY_FILE.read_text().strip()


def generate_background(theme: str, info: dict, api_key: str, force: bool = False) -> Path:
    out_path = OUT_DIR / f"{theme}.jpg"
    if out_path.exists() and not force:
        print(f"  ✓ {theme}.jpg already exists — skip")
        return out_path

    print(f"  Generating {theme} ({info['desc']})…")
    resp = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "python-requests/2.31.0",
        },
        json={
            "model": MODEL,
            "prompt": info["prompt"],
            "width": 1280, "height": 720,
            "steps": 4,
            "n": 1,
            "response_format": "b64_json",
        },
        timeout=90,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Together.ai error {resp.status_code}: {resp.text[:300]}")

    data = resp.json()
    b64 = data["data"][0]["b64_json"]
    img_bytes = base64.b64decode(b64)
    out_path.write_bytes(img_bytes)
    print(f"  ✓ Saved {out_path.name} ({len(img_bytes)//1024} KB)")
    return out_path


def get_bg_for(subject: str) -> str:
    """Return background filename (e.g. 'meadow_sunny.jpg') for a given animal/theme."""
    theme = ANIMAL_BG_MAP.get(subject, "rainbow_sky")
    return f"{theme}.jpg"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--theme", help="Generate one specific theme")
    parser.add_argument("--force", action="store_true", help="Regenerate even if file exists")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    api_key = get_api_key()

    themes_to_run = (
        {args.theme: BACKGROUNDS[args.theme]} if args.theme else BACKGROUNDS
    )

    print(f"Generating {len(themes_to_run)} background(s) → {OUT_DIR}\n")
    for theme, info in themes_to_run.items():
        try:
            generate_background(theme, info, api_key, force=args.force)
            time.sleep(1)
        except Exception as e:
            print(f"  ✗ {theme}: {e}")

    print("\nDone.")
    print(f"Use in DanceSpriteLong: bgImage='meadow_sunny.jpg', bgEffect='sparkles'")


if __name__ == "__main__":
    main()
