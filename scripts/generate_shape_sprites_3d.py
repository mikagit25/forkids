#!/usr/bin/env python3
"""
Generate 3D Pixar-style shape sprites via Together.ai FLUX.
Outputs: assets/sprites_new/shapes_3d/*.png + remotion/public/sprites/shapes_3d/*.png

Usage:
  python3 scripts/generate_shape_sprites_3d.py              # missing shapes only
  python3 scripts/generate_shape_sprites_3d.py --all        # regenerate all 8
  python3 scripts/generate_shape_sprites_3d.py --shapes star diamond heart
"""
import argparse
import base64
import io
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOGETHER_KEY_FILE = ROOT / "credentials" / "together_api_key.txt"
TOGETHER_URL = "https://api.together.xyz/v1/images/generations"
TOGETHER_MODEL = "black-forest-labs/FLUX.1-schnell"

OUT_ASSETS = ROOT / "assets" / "sprites_new" / "shapes_3d"
OUT_REMOTION = ROOT / "remotion" / "public" / "sprites" / "shapes_3d"

# Shape definitions: name → (color description, hex hint for prompt)
SHAPES = {
    "circle":   ("blue",           "shiny glossy cobalt blue sphere, slightly flattened disc shape"),
    "square":   ("red",            "shiny glossy scarlet red cube seen from front, perfectly square face, rounded edges"),
    "triangle": ("green",          "shiny glossy emerald green triangular prism, equilateral triangle face"),
    "star":     ("yellow",         "shiny glossy golden yellow 5-pointed star shape, chubby 3D star toy"),
    "diamond":  ("purple",         "shiny glossy violet purple 4-pointed diamond rhombus shape, gemstone-like"),
    "heart":    ("pink",           "shiny glossy hot pink heart shape, puffy 3D heart, rounded lobes"),
    "hexagon":  ("orange",         "shiny glossy orange 6-sided hexagon shape, flat hexagonal prism"),
    "oval":     ("teal",           "shiny glossy teal cyan oval ellipse shape, smooth rounded ellipsoid"),
}

PROMPT_TEMPLATE = (
    "A single isolated {name} shape, {desc}, children's educational toy, "
    "Pixar 3D render style, soft studio lighting, subtle drop shadow below, "
    "pure white background, no other objects, no text, no letters, "
    "high quality 3D render, clean edges, vibrant color"
)


def load_key() -> str:
    if not TOGETHER_KEY_FILE.exists():
        print(f"ERROR: {TOGETHER_KEY_FILE} not found", file=sys.stderr)
        sys.exit(1)
    return TOGETHER_KEY_FILE.read_text().strip()


def generate_sprite(shape: str, api_key: str, retries: int = 3) -> bytes:
    import requests

    color, desc = SHAPES[shape]
    prompt = PROMPT_TEMPLATE.format(name=shape, desc=desc)

    for attempt in range(retries):
        try:
            resp = requests.post(
                TOGETHER_URL,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": TOGETHER_MODEL,
                    "prompt": prompt,
                    "width": 1024,
                    "height": 1024,
                    "steps": 4,
                    "n": 1,
                    "response_format": "b64_json",
                },
                timeout=90,
            )
            resp.raise_for_status()
            data = resp.json()
            b64 = data["data"][0]["b64_json"]
            return base64.b64decode(b64)
        except Exception as e:
            print(f"  attempt {attempt+1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(5)
    raise RuntimeError(f"Failed to generate sprite for {shape}")


def save_sprite(name: str, img_bytes: bytes):
    from PIL import Image

    img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
    img = img.resize((512, 512), Image.LANCZOS)

    for out_dir in [OUT_ASSETS, OUT_REMOTION]:
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{name}.png"
        img.save(out_path, "PNG", optimize=True)
        size_kb = out_path.stat().st_size // 1024
        print(f"  saved → {out_path.relative_to(ROOT)} ({size_kb}KB)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="Regenerate all shapes")
    ap.add_argument("--shapes", nargs="+", choices=list(SHAPES), help="Specific shapes")
    args = ap.parse_args()

    api_key = load_key()
    print(f"API key loaded, model: {TOGETHER_MODEL}")

    # Determine which shapes to generate
    if args.shapes:
        targets = args.shapes
    elif args.all:
        targets = list(SHAPES)
    else:
        # Only missing shapes (check remotion path as authoritative)
        targets = [s for s in SHAPES if not (OUT_REMOTION / f"{s}.png").exists()]
        if not targets:
            print("All shapes already exist. Use --all to regenerate.")
            return

    print(f"Generating {len(targets)} shape(s): {', '.join(targets)}")

    for shape in targets:
        print(f"\n[{shape}] generating...")
        try:
            img_bytes = generate_sprite(shape, api_key)
            save_sprite(shape, img_bytes)
            print(f"[{shape}] ✓")
        except Exception as e:
            print(f"[{shape}] ERROR: {e}")
        time.sleep(1)  # rate limit

    print(f"\nDone. Sprites in: remotion/public/sprites/shapes_3d/")


if __name__ == "__main__":
    main()
