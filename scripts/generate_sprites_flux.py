#!/usr/bin/env python3
"""
Generate high-quality 3D cartoon sprites via Together.ai FLUX.1-schnell.

Pixar-style, white background, rembg background removal → PNG with transparency.
Output: assets/sprites_flux/{category}/{name}.png

Usage:
    python3 scripts/generate_sprites_flux.py --category animals
    python3 scripts/generate_sprites_flux.py --category fruits
    python3 scripts/generate_sprites_flux.py --category vegetables
    python3 scripts/generate_sprites_flux.py --category animals --names bear lion fox
    python3 scripts/generate_sprites_flux.py --category objects --names star moon sun cloud
    python3 scripts/generate_sprites_flux.py --list   # show all predefined objects
"""

import argparse
import base64
import io
import json
import sys
import time
from pathlib import Path

import requests
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
KEY_FILE = ROOT / "credentials" / "together_api_key.txt"

TOGETHER_URL = "https://api.together.xyz/v1/images/generations"
MODEL        = "black-forest-labs/FLUX.1-schnell"
SIZE         = 1024  # square sprites

# ── Predefined object lists ───────────────────────────────────────────────────

OBJECTS = {
    "animals": {
        "bear":     "cute brown bear cub",
        "tiger":    "cute baby tiger",
        "frog":     "cute green frog",
        "penguin":  "cute baby penguin",
        "lion":     "cute baby lion cub",
        "panda":    "cute panda bear",
        "koala":    "cute koala bear",
        "fox":      "cute red fox",
        "rabbit":   "cute white rabbit",
        "cow":      "cute spotted cow",
        "duck":     "cute yellow duck",
        "pig":      "cute pink pig",
        "elephant": "cute baby elephant",
        "monkey":   "cute little monkey",
        "dog":      "cute puppy dog",
        "cat":      "cute kitten cat",
        "owl":      "cute colorful owl",
        "unicorn":  "cute magical unicorn",
        "dino":     "cute friendly dinosaur",
        "parrot":   "cute colorful parrot",
    },
    "fruits": {
        "apple":        "shiny red apple",
        "banana":       "yellow banana",
        "strawberry":   "red strawberry",
        "orange":       "juicy orange",
        "grape":        "purple grapes",
        "watermelon":   "watermelon slice",
        "pineapple":    "tropical pineapple",
        "cherry":       "red cherries",
        "lemon":        "bright yellow lemon",
        "mango":        "tropical mango",
        "peach":        "peachy peach",
        "pear":         "green pear",
        "blueberry":    "blue blueberries",
        "raspberry":    "red raspberry",
        "kiwi":         "kiwi fruit",
        "coconut":      "tropical coconut",
        "plum":         "purple plum",
        "avocado":      "green avocado",
        "pomegranate":  "red pomegranate",
        "melon":        "yellow melon",
    },
    "vegetables": {
        "carrot":    "orange carrot",
        "broccoli":  "green broccoli",
        "corn":      "yellow corn",
        "tomato":    "red tomato",
        "potato":    "brown potato",
        "onion":     "purple onion",
        "pepper":    "red bell pepper",
        "cucumber":  "green cucumber",
        "eggplant":  "purple eggplant",
        "pumpkin":   "orange pumpkin",
    },
    "shapes": {
        "circle":    "perfect circle shape",
        "square":    "perfect square shape",
        "triangle":  "triangle shape",
        "star":      "five-pointed star shape",
        "heart":     "heart shape",
        "diamond":   "diamond shape",
        "hexagon":   "hexagon shape",
        "oval":      "oval shape",
    },
    "objects": {
        "sun":       "bright cartoon sun",
        "moon":      "crescent moon",
        "star":      "glowing star",
        "cloud":     "fluffy white cloud",
        "rainbow":   "colorful rainbow",
        "balloon":   "colorful balloon",
        "flower":    "colorful flower",
        "tree":      "cartoon tree",
        "house":     "cartoon house",
        "car":       "toy car",
        "bus":       "school bus",
        "train":     "toy train",
        "boat":      "cartoon boat",
        "plane":     "toy airplane",
        "rocket":    "cartoon rocket",
        "ball":      "colorful ball",
        "cake":      "birthday cake",
        "ice_cream": "ice cream cone",
        "cookie":    "chocolate chip cookie",
        "pizza":     "pizza slice",
    },
}

PROMPT_TEMPLATE = (
    "cute 3D cartoon character, {description}, Pixar style, "
    "bright vivid colors, smooth shading, white background, "
    "isolated object, studio lighting, high quality render, "
    "children illustration, no text, no letters"
)


def load_key() -> str:
    if not KEY_FILE.exists():
        print(f"ERROR: API key not found at {KEY_FILE}")
        sys.exit(1)
    return KEY_FILE.read_text().strip()


def generate_flux(prompt: str, key: str, retries: int = 3) -> bytes | None:
    for attempt in range(retries):
        try:
            resp = requests.post(
                TOGETHER_URL,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": MODEL, "prompt": prompt,
                      "width": SIZE, "height": SIZE, "steps": 4, "n": 1},
                timeout=60,
            )
            if resp.status_code == 429:
                wait = 30 * (attempt + 1)
                print(f"  Rate limited — waiting {wait}s (attempt {attempt+1}/{retries})")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            item = data["data"][0]
            if "b64_json" in item:
                return base64.b64decode(item["b64_json"])
            if "url" in item:
                r = requests.get(item["url"], timeout=30)
                r.raise_for_status()
                return r.content
            print("  ERROR: no image data in response")
            return None
        except Exception as e:
            if attempt < retries - 1:
                print(f"  ERROR: {e} — retrying in 30s")
                time.sleep(30)
            else:
                print(f"  ERROR: {e}")
                return None
    return None


def remove_background(img_bytes: bytes) -> bytes:
    try:
        from rembg import remove
        result = remove(img_bytes)
        return result
    except ImportError:
        print("  WARNING: rembg not installed, keeping white background")
        return img_bytes
    except Exception as e:
        print(f"  WARNING: rembg failed ({e}), keeping white background")
        return img_bytes


def save_sprite(img_bytes: bytes, out_path: Path):
    img = Image.open(io.BytesIO(img_bytes))
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    img.save(out_path, "PNG")


def generate_category(category: str, names: list[str] | None, force: bool, dry_run: bool):
    if category not in OBJECTS:
        print(f"Unknown category: {category}. Available: {', '.join(OBJECTS.keys())}")
        sys.exit(1)

    objects = OBJECTS[category]
    if names:
        objects = {k: v for k, v in objects.items() if k in names}
        missing = set(names) - set(OBJECTS[category].keys())
        if missing:
            print(f"  Unknown names in {category}: {', '.join(missing)}")
            print(f"  Will generate as custom objects")
            for name in missing:
                objects[name] = name.replace("_", " ")

    out_dir = ROOT / "assets" / "sprites_flux" / category
    out_dir.mkdir(parents=True, exist_ok=True)

    key = load_key()
    total = len(objects)
    generated = 0

    print(f"\nGenerating {total} sprites → {out_dir}")
    print(f"Model: {MODEL}  Size: {SIZE}×{SIZE}  Style: Pixar 3D")
    print("─" * 50)

    for idx, (name, description) in enumerate(objects.items(), 1):
        out_path = out_dir / f"{name}.png"

        if out_path.exists() and not force:
            print(f"[{idx}/{total}] SKIP {name} (exists)")
            continue

        prompt = PROMPT_TEMPLATE.format(description=description)
        print(f"[{idx}/{total}] {name}: {description}")

        if dry_run:
            print(f"  [DRY RUN] prompt: {prompt[:80]}...")
            continue

        img_bytes = generate_flux(prompt, key)
        if not img_bytes:
            print(f"  FAILED — skipping")
            continue

        print(f"  Removing background...")
        clean_bytes = remove_background(img_bytes)

        save_sprite(clean_bytes, out_path)
        size_kb = out_path.stat().st_size // 1024
        print(f"  ✓ saved ({size_kb} KB) → {out_path.name}")
        generated += 1

        if idx < total:
            time.sleep(15)  # Together.ai rate limit: ~4 req/min on free tier

    print(f"\n✓ Done: {generated}/{total} generated → {out_dir}")
    return generated


def list_objects():
    for category, items in OBJECTS.items():
        print(f"\n{category.upper()} ({len(items)}):")
        for name in items:
            print(f"  {name}")


def main():
    parser = argparse.ArgumentParser(description="Generate FLUX sprites for Kids Channel")
    parser.add_argument("--category", choices=list(OBJECTS.keys()),
                        help="Object category to generate")
    parser.add_argument("--names",    nargs="+", help="Specific object names (default: all)")
    parser.add_argument("--force",    action="store_true", help="Overwrite existing files")
    parser.add_argument("--dry-run",  action="store_true", help="Show prompts without generating")
    parser.add_argument("--list",     action="store_true", help="List all predefined objects")
    parser.add_argument("--all",      action="store_true", help="Generate all categories")
    args = parser.parse_args()

    if args.list:
        list_objects()
        return

    if args.all:
        for category in OBJECTS:
            generate_category(category, None, args.force, args.dry_run)
        return

    if not args.category:
        parser.print_help()
        return

    generate_category(args.category, args.names, args.force, args.dry_run)


if __name__ == "__main__":
    main()
