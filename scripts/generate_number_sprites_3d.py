#!/usr/bin/env python3
"""
Generate Pixar 3D style sprites for NumberLearnLong via Together.ai FLUX.
Produces individual PNG files on white background for each object.

Usage:
  python3 scripts/generate_number_sprites_3d.py
  python3 scripts/generate_number_sprites_3d.py --object duck
  python3 scripts/generate_number_sprites_3d.py --force
"""
import argparse
import base64
import sys
import time
from pathlib import Path

import requests
import yaml

ROOT          = Path(__file__).resolve().parent.parent
DATA_PATH     = ROOT / "config" / "number_learn_data.yaml"
SPRITES_DIR   = ROOT / "remotion" / "public" / "sprites"
KEY_FILE      = ROOT / "credentials" / "together_api_key.txt"

TOGETHER_URL   = "https://api.together.xyz/v1/images/generations"
TOGETHER_MODEL = "black-forest-labs/FLUX.1-schnell"

# Prompts for each object key — Pixar 3D style, single character, white background
PROMPTS = {
    # animals
    "duck":        "A single cute 3D Pixar-style baby duck character with big round eyes, yellow fluffy body, orange beak, happy smile, standing pose, pure white background, children's educational illustration, no text, no shadows",
    # fruits
    "apple":       "A single cute 3D Pixar-style red apple character with big expressive eyes, round glossy body, green leaf on top, happy smile, pure white background, children's educational illustration, no text",
    "banana":      "A single cute 3D Pixar-style yellow banana character with big round eyes, curved chubby body, happy smiling face, pure white background, children's educational illustration, no text",
    "cherry":      "A single cute 3D Pixar-style red cherry pair character with big expressive eyes, round glossy red cherries on a green stem, happy face, pure white background, children's educational illustration, no text",
    # objects
    "balloon":     "A single cute 3D Pixar-style colorful red balloon character with big round eyes, shiny round body, happy smiling face, thin string, pure white background, children's educational illustration, no text",
    "butterfly":   "A single cute 3D Pixar-style colorful butterfly character with big expressive eyes, symmetrical colorful wings in pink and purple, happy face, pure white background, children's educational illustration, no text",
    "car":         "A single cute 3D Pixar-style red toy car character with big round headlight eyes, shiny rounded body, happy smiling face, pure white background, children's educational illustration, no text",
    "octopus":     "A single cute 3D Pixar-style purple octopus character with big round eyes, round head, eight curly tentacles, happy smiling face, pure white background, children's educational illustration, no text",
    "rainbow":     "A single cute 3D Pixar-style rainbow with big expressive eyes, glowing colorful arched stripes, happy smiling face, fluffy white clouds on each end, pure white background, children's educational illustration, no text",
    "shoe":        "A single cute 3D Pixar-style children's sneaker shoe character with big round eyes on the toe, colorful laces, happy face, pure white background, children's educational illustration, no text",
    "star":        "A single cute 3D Pixar-style golden star character with big expressive eyes, five chubby points, sparkly surface, happy smiling face with rosy cheeks, pure white background, children's educational illustration, no text",
    "sun":         "A single cute 3D Pixar-style yellow sun character with big round eyes, round glowing face, wavy golden rays, happy smiling face with rosy cheeks, pure white background, children's educational illustration, no text",
}

# Where to save: sprite_key → relative path from SPRITES_DIR
OUTPUT_PATHS = {
    "duck":       "animals/duck_3d.png",
    "apple":      "fruits/apple_3d.png",
    "banana":     "fruits/banana_3d.png",
    "cherry":     "fruits/cherry_3d.png",
    "balloon":    "objects/balloon_3d.png",
    "butterfly":  "objects/butterfly_3d.png",
    "car":        "objects/car_3d.png",
    "octopus":    "objects/octopus_3d.png",
    "rainbow":    "objects/rainbow_3d.png",
    "shoe":       "objects/shoe_3d.png",
    "star":       "objects/star_3d.png",
    "sun":        "objects/sun_3d.png",
}


def load_key() -> str:
    if not KEY_FILE.exists():
        sys.exit(f"Together.ai key not found: {KEY_FILE}")
    return KEY_FILE.read_text().strip()


def generate_sprite(prompt: str, key: str) -> bytes | None:
    try:
        r = requests.post(
            TOGETHER_URL,
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model":  TOGETHER_MODEL,
                "prompt": prompt,
                "width":  1024,
                "height": 1024,
                "steps":  4,
                "n":      1,
            },
            timeout=90,
        )
        if r.status_code != 200:
            print(f"    API error {r.status_code}: {r.text[:120]}")
            return None
        item = r.json()["data"][0]
        b64 = item.get("b64_json")
        if b64:
            return base64.b64decode(b64)
        url = item.get("url")
        if url:
            img_r = requests.get(url, timeout=30)
            if img_r.status_code == 200:
                return img_r.content
    except Exception as e:
        print(f"    Request failed: {e}")
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--object", help="Single object key (e.g. duck, apple)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    args = parser.parse_args()

    key = load_key()

    keys = [args.object] if args.object else list(PROMPTS.keys())

    print(f"Generating {len(keys)} 3D sprites via FLUX.1-schnell...")
    ok = fail = skip = 0

    for k in keys:
        if k not in PROMPTS:
            print(f"  Unknown key: {k}")
            continue

        out = SPRITES_DIR / OUTPUT_PATHS[k]
        if out.exists() and not args.force:
            print(f"  ✓ {k} already exists — skip (--force to overwrite)")
            skip += 1
            continue

        print(f"  Generating {k}...", end=" ", flush=True)
        data = generate_sprite(PROMPTS[k], key)
        if data:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(data)
            print(f"✓ saved {len(data)//1024}KB → {out.relative_to(ROOT)}")
            ok += 1
        else:
            print("FAILED")
            fail += 1

        if keys.index(k) < len(keys) - 1:
            time.sleep(1)

    print(f"\nDone: {ok} generated, {skip} skipped, {fail} failed")


if __name__ == "__main__":
    main()
