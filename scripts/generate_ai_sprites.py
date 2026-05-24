#!/usr/bin/env python3
"""
Generate Pixar-style cartoon character sprites via Pollinations.ai + rembg background removal.
Saves RGBA PNGs to assets/sprites/ai_generated/{character_name}.png

Usage:
    python3 generate_ai_sprites.py              # generate all missing
    python3 generate_ai_sprites.py --overwrite  # regenerate all
    python3 generate_ai_sprites.py --only bear bunny  # specific chars
    python3 generate_ai_sprites.py --parallel 3      # 3 concurrent downloads
"""

import time
import urllib.request
import urllib.parse
import argparse
import io
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from PIL import Image
from rembg import remove

ROOT = Path(__file__).parent.parent
OUT_DIR = ROOT / "assets" / "sprites" / "ai_generated"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CHARACTERS = [
    # Fruits
    ("strawberry",  "cute 3D cartoon strawberry character with big eyes smile arms legs dancing, Pixar style, white background"),
    ("apple",       "cute 3D cartoon red apple character with big eyes smile arms legs jumping happy, Pixar style, white background"),
    ("banana",      "cute 3D cartoon yellow banana character with eyes smile arms waving, Pixar style, white background"),
    ("lemon",       "cute 3D cartoon yellow lemon character with big eyes smile arms legs cheerful, Pixar style, white background"),
    ("orange",      "cute 3D cartoon orange fruit character with big eyes smile arms legs bouncing, Pixar style, white background"),
    ("watermelon",  "cute 3D cartoon watermelon slice character with big eyes smile arms legs, Pixar style, white background"),
    ("grapes",      "cute 3D cartoon purple grapes bunch character with big eyes smile arms, Pixar style, white background"),
    ("pineapple",   "cute 3D cartoon pineapple character with big eyes smile arms legs dancing, Pixar style, white background"),
    ("avocado",     "cute 3D cartoon avocado character with big eyes smile arms legs happy, Pixar style, white background"),
    ("cherry",      "cute 3D cartoon red cherries character pair with big eyes smile arms, Pixar style, white background"),
    # Vegetables
    ("carrot",      "cute 3D cartoon orange carrot character with big eyes smile arms legs jumping, Pixar style, white background"),
    ("broccoli",    "cute 3D cartoon green broccoli character with big eyes smile arms legs, Pixar style, white background"),
    ("corn",        "cute 3D cartoon yellow corn cob character with big eyes smile arms waving, Pixar style, white background"),
    # Animals
    ("bear",        "cute 3D cartoon brown bear cub character with big eyes smile standing waving, Pixar style, white background"),
    ("bunny",       "cute 3D cartoon white bunny rabbit character with big eyes smile dancing, Pixar style, white background"),
    ("cat",         "cute 3D cartoon orange cat character with big eyes smile arms legs happy, Pixar style, white background"),
    ("duck",        "cute 3D cartoon yellow duckling character with big eyes smile wings, Pixar style, white background"),
    ("elephant",    "cute 3D cartoon baby elephant character with big eyes smile trunk up happy, Pixar style, white background"),
    ("penguin",     "cute 3D cartoon penguin character with big eyes smile wings dancing, Pixar style, white background"),
    ("star",        "cute 3D cartoon golden star character with big eyes smile arms legs bouncing, Pixar style, white background"),
]

POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}?width=512&height=512&nologo=true&model=sana&seed={seed}"


def download_image(prompt: str, seed: int = 42, retries: int = 3) -> Image.Image:
    encoded = urllib.parse.quote(prompt)
    url = POLLINATIONS_URL.format(prompt=encoded, seed=seed)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
            return Image.open(io.BytesIO(data)).convert("RGBA")
        except Exception as e:
            if attempt < retries - 1:
                print(f"  [{prompt[:20]}] retry {attempt+1}...", flush=True)
                time.sleep(3)
            else:
                raise


def remove_background(img: Image.Image) -> Image.Image:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    result = remove(buf.getvalue())
    return Image.open(io.BytesIO(result)).convert("RGBA")


def generate_character(name: str, prompt: str, seed: int = 42, overwrite: bool = False) -> tuple:
    out_path = OUT_DIR / f"{name}.png"
    if out_path.exists() and not overwrite:
        return name, "skipped", None

    t0 = time.time()
    try:
        img = download_image(prompt, seed=seed)
        t1 = time.time()
        img = remove_background(img)
        t2 = time.time()

        img.thumbnail((512, 512), Image.LANCZOS)
        canvas = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
        offset = ((512 - img.width) // 2, (512 - img.height) // 2)
        canvas.paste(img, offset, img)
        canvas.save(out_path, "PNG")
        return name, "ok", f"{t1-t0:.1f}s dl, {t2-t1:.1f}s rembg"
    except Exception as e:
        return name, "error", str(e)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--overwrite", action="store_true", help="Re-generate existing sprites")
    parser.add_argument("--only", nargs="+", help="Generate only these characters by name")
    parser.add_argument("--parallel", type=int, default=1, help="Parallel download workers (default: 1)")
    args = parser.parse_args()

    targets = CHARACTERS
    if args.only:
        targets = [(n, p) for n, p in CHARACTERS if n in args.only]

    print(f"Generating {len(targets)} AI characters → {OUT_DIR}")
    print(f"Model: sana (Pollinations.ai, free) | workers={args.parallel}")
    print("=" * 60)

    ok = errors = skipped = 0

    if args.parallel > 1:
        futures = {}
        with ThreadPoolExecutor(max_workers=args.parallel) as ex:
            for i, (name, prompt) in enumerate(targets):
                f = ex.submit(generate_character, name, prompt, 100 + i, args.overwrite)
                futures[f] = name
            for f in as_completed(futures):
                name, status, info = f.result()
                if status == "ok":
                    print(f"  {name}: done ({info})")
                    ok += 1
                elif status == "skipped":
                    print(f"  {name}: skipped")
                    skipped += 1
                else:
                    print(f"  {name}: ERROR: {info}")
                    errors += 1
    else:
        for i, (name, prompt) in enumerate(targets):
            print(f"  generating {name}...", end="", flush=True)
            name2, status, info = generate_character(name, prompt, 100 + i, args.overwrite)
            if status == "ok":
                print(f" done ({info}) → {name}.png")
                ok += 1
            elif status == "skipped":
                print(f" skip (already exists)")
                skipped += 1
            else:
                print(f" ERROR: {info}")
                errors += 1
            time.sleep(1)

    print("=" * 60)
    print(f"Done: {ok} generated, {skipped} skipped, {errors} errors")
    print(f"Total sprites: {len(list(OUT_DIR.glob('*.png')))}")


if __name__ == "__main__":
    main()
