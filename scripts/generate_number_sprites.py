#!/usr/bin/env python3
"""
Generate missing sprite images for NumberLearnLong via Together.ai.
Saves to remotion/public/sprites/objects/

Usage:
  python3 scripts/generate_number_sprites.py
  python3 scripts/generate_number_sprites.py --force
"""
import sys
import time
import requests
from io import BytesIO
from pathlib import Path
from PIL import Image

ROOT     = Path(__file__).resolve().parent.parent
KEY_FILE = ROOT / "credentials" / "together_api_key.txt"
OUT_DIR  = ROOT / "remotion" / "public" / "sprites" / "objects"
MODEL    = "black-forest-labs/FLUX.1-schnell"

SPRITES = [
    ("star.png",      "cute cartoon yellow star shape, bright golden yellow, friendly smile, white background, children's educational style, isolated, no text, simple clean design"),
    ("sun.png",       "cute cartoon yellow sun with rays and friendly smile, bright yellow, white background, children's educational style, isolated, no text"),
    ("shoe.png",      "cute cartoon colorful shoe, bright red or blue color, friendly design, white background, children's educational style, isolated, no text"),
    ("car.png",       "cute cartoon toy car, bright red color, simple design, friendly face, white background, children's educational style, isolated, no text"),
    ("butterfly.png", "cute cartoon colorful butterfly, rainbow wings, bright colors, white background, children's educational style, isolated, no text"),
    ("balloon.png",   "cute cartoon red balloon with string, round shape, shiny, white background, children's educational style, isolated, no text"),
    ("octopus.png",   "cute cartoon purple octopus with 8 arms, friendly smile, bright colors, white background, children's educational style, isolated, no text"),
    ("rainbow.png",   "cute cartoon rainbow with 7 colorful arcs, white clouds on sides, bright colors, white background, children's educational style, isolated, no text"),
]


def load_key() -> str:
    return KEY_FILE.read_text().strip()


def generate_image(prompt: str, key: str) -> bytes | None:
    try:
        resp = requests.post(
            "https://api.together.xyz/v1/images/generations",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": MODEL,
                "prompt": prompt,
                "width": 512, "height": 512,
                "steps": 4, "n": 1,
                "response_format": "b64_json",
            },
            timeout=60,
        )
        if resp.status_code == 200:
            import base64
            return base64.b64decode(resp.json()["data"][0]["b64_json"])
        print(f"    API {resp.status_code}: {resp.text[:120]}")
        return None
    except Exception as e:
        print(f"    Error: {e}")
        return None


def resize(img_bytes: bytes, size: int = 512) -> bytes:
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
    print(f"Key: {key[:15]}...")

    ok = fail = skip = 0
    for fname, prompt in SPRITES:
        p = OUT_DIR / fname
        if p.exists() and not args.force:
            print(f"  skip {fname} ({p.stat().st_size//1024}KB)")
            skip += 1
            continue
        print(f"  Generating {fname}...")
        img = generate_image(prompt, key)
        if img:
            final = resize(img)
            p.write_bytes(final)
            print(f"    ✓ {len(final)//1024}KB")
            ok += 1
        else:
            print(f"    ✗ FAILED")
            fail += 1
        time.sleep(4)

    print(f"\nDone: {ok} generated, {fail} failed, {skip} skipped")


if __name__ == "__main__":
    main()
