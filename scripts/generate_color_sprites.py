#!/usr/bin/env python3
"""
Generate missing sprite images for ColorLearnLong via Together.ai FLUX.1-schnell.
Saves to remotion/public/sprites/objects/

Usage:
  python3 scripts/generate_color_sprites.py
  python3 scripts/generate_color_sprites.py --force
"""
import sys
import time
import requests
from io import BytesIO
from pathlib import Path
from PIL import Image

ROOT      = Path(__file__).resolve().parent.parent
KEY_FILE  = ROOT / "credentials" / "together_api_key.txt"
OUT_DIR   = ROOT / "remotion" / "public" / "sprites" / "objects"
MODEL     = "black-forest-labs/FLUX.1-schnell"

SPRITES = [
    ("blueberry.png",     "cute cartoon blueberry cluster, bright blue-purple berries, white background, children's educational style, isolated, no text"),
    ("blue_butterfly.png","cute cartoon blue butterfly, bright blue wings, white background, children's educational style, isolated, no text"),
    ("blue_whale.png",    "cute cartoon blue whale, friendly smile, ocean blue color, white background, children's educational style, isolated, no text"),
    ("pumpkin.png",       "cute cartoon orange pumpkin, friendly face, bright orange color, white background, children's educational style, isolated, no text"),
    ("plum.png",          "cute cartoon purple plum fruit, shiny, bright purple color, white background, children's educational style, isolated, no text"),
    ("flamingo.png",      "cute cartoon pink flamingo bird, bright pink feathers, white background, children's educational style, isolated, no text"),
    ("cloud.png",         "cute cartoon white fluffy cloud, friendly smile, pure white color, light blue background, children's educational style, isolated, no text"),
    ("polar_bear.png",    "cute cartoon polar bear, white fur, friendly face, white background with light blue tint, children's educational style, isolated, no text"),
    ("crow.png",          "cute cartoon black crow bird, glossy black feathers, friendly smile, white background, children's educational style, isolated, no text"),
]


def load_key() -> str:
    return KEY_FILE.read_text().strip()


def generate_image(prompt: str, key: str) -> bytes | None:
    try:
        resp = requests.post(
            "https://api.together.xyz/v1/images/generations",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model":   MODEL,
                "prompt":  prompt,
                "width":   512,
                "height":  512,
                "steps":   4,
                "n":       1,
                "response_format": "b64_json",
            },
            timeout=60,
        )
        if resp.status_code == 200:
            import base64
            b64 = resp.json()["data"][0]["b64_json"]
            return base64.b64decode(b64)
        print(f"    API error {resp.status_code}: {resp.text[:200]}")
        return None
    except Exception as e:
        print(f"    Exception: {e}")
        return None


def resize_sprite(img_bytes: bytes, size: int = 512) -> bytes:
    img = Image.open(BytesIO(img_bytes)).convert("RGBA")
    img = img.resize((size, size), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    key = load_key()
    print(f"Together.ai key: {key[:15]}...")

    ok = fail = skip = 0
    for filename, prompt in SPRITES:
        out_path = OUT_DIR / filename
        if out_path.exists() and not args.force:
            size_kb = out_path.stat().st_size // 1024
            print(f"  skip {filename} ({size_kb}KB)")
            skip += 1
            continue

        print(f"  Generating {filename}...")
        img_bytes = generate_image(prompt, key)
        if img_bytes:
            final = resize_sprite(img_bytes)
            out_path.write_bytes(final)
            print(f"    ✓ saved {len(final)//1024}KB")
            ok += 1
        else:
            print(f"    ✗ FAILED")
            fail += 1
        time.sleep(4)

    print(f"\nDone: {ok} generated, {fail} failed, {skip} skipped")


if __name__ == "__main__":
    main()
