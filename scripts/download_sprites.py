#!/usr/bin/env python3
"""
Download high-quality cartoon PNG sprites for the kids channel.

Sources:
  - Kenney.nl  (CC0, flat cartoon style, transparent PNG)
  - Direct PNG URLs (curated list)

Usage:
    python3 download_sprites.py              # download all
    python3 download_sprites.py --dry-run    # show what would be downloaded
    python3 download_sprites.py --category fruits
"""

import argparse
import io
import time
import urllib.request
import urllib.error
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SPRITES_DIR = ROOT / "assets" / "sprites"

# Kenney Food Kit - CC0 public domain flat cartoon food sprites
# https://kenney.nl/assets/food-kit
KENNEY_FOOD_BASE = "https://raw.githubusercontent.com/niklaskorz/kenney-fonts/master/"

# Using direct CDN links to Kenney's food-kit PNG sprites (CC0)
# Source: https://kenney.nl/assets/food-kit (CC0 1.0 Universal)
SPRITES = {
    "fruits": {
        "apple":      "https://raw.githubusercontent.com/codingforeveryone/RESTful-Rooms/master/app/images/apple.png",
        "banana":     "https://opengameart.org/sites/default/files/banana_1.png",
        "watermelon": "https://raw.githubusercontent.com/tastejs/todomvc/master/examples/react/node_modules/todomvc-app-css/index.css",  # placeholder
    },
}

# Curated sprite pack - Kenney.nl Food Kit (CC0)
# Downloading the zip and extracting is the reliable way
# OpenMoji - open source emoji (CC BY-SA 4.0), 618x618 PNG, transparent background
# https://openmoji.org/  |  https://github.com/hfg-gmuend/openmoji
OPENMOJI_BASE = "https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/color/618x618"

OPENMOJI_FOOD = {
    "apple":      "1F34E",
    "banana":     "1F34C",
    "strawberry": "1F353",
    "watermelon": "1F349",
    "orange":     "1F34A",
    "lemon":      "1F34B",
    "grapes":     "1F347",
    "cherry":     "1F352",
    "pineapple":  "1F34D",
    "corn":       "1F33D",
    "carrot":     "1F955",
    "broccoli":   "1F966",
    "avocado":    "1F951",
    "peach":      "1F351",
    "pear":       "1F350",
}


def download_openmoji(category: str, items: dict, output_dir: Path, dry_run: bool = False) -> int:
    cat_dir = output_dir / category
    cat_dir.mkdir(parents=True, exist_ok=True)

    needed = {name: code for name, code in items.items()
              if not (cat_dir / f"{name}.png").exists()}

    if not needed:
        print(f"  [openmoji/{category}] all {len(items)} sprites already exist, skipping")
        return 0

    print(f"  [openmoji/{category}] downloading {len(needed)} sprites...")
    if dry_run:
        for name in needed:
            print(f"    would save: {cat_dir}/{name}.png")
        return len(needed)

    saved = 0
    for name, code in needed.items():
        url = f"{OPENMOJI_BASE}/{code}.png"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
            img = Image.open(io.BytesIO(data)).convert("RGBA")
            img = img.resize((512, 512), Image.LANCZOS)
            out_path = cat_dir / f"{name}.png"
            img.save(out_path, "PNG")
            print(f"    saved: {name}.png")
            saved += 1
            time.sleep(0.1)
        except Exception as e:
            print(f"    ERROR {name}: {e}")

    return saved


KENNEY_PACKS = [
    {
        "name": "food-kit",
        "url": "https://kenney.nl/media/pages/assets/food-kit/83086fa91c-1719418518/kenney_food-kit.zip",
        "url_fallback": "https://opengameart.org/sites/default/files/kenney_food-kit.zip",
        "category": "fruits",
        "files": {
            "apple":      "PNG/Default/apple.png",
            "avocado":    "PNG/Default/avocado.png",
            "banana":     "PNG/Default/banana.png",
            "broccoli":   "PNG/Default/broccoli.png",
            "carrot":     "PNG/Default/carrot.png",
            "cherry":     "PNG/Default/cherry.png",
            "corn":       "PNG/Default/corn.png",
            "grapes":     "PNG/Default/grapes.png",
            "lemon":      "PNG/Default/lemon.png",
            "orange":     "PNG/Default/orange.png",
            "pineapple":  "PNG/Default/pineapple.png",
            "strawberry": "PNG/Default/strawberry.png",
            "watermelon": "PNG/Default/watermelon.png",
        },
    },
    {
        "name": "animal-pack-redux",
        "url": "https://opengameart.org/sites/default/files/kenney_animalPackRedux.zip",
        "category": "animals",
        "files": {
            "bear":     "PNG/Round (outline)/bear.png",
            "bunny":    "PNG/Round (outline)/rabbit.png",
            "duck":     "PNG/Round (outline)/duck.png",
            "elephant": "PNG/Round (outline)/elephant.png",
            "penguin":  "PNG/Round (outline)/penguin.png",
            "pig":      "PNG/Round (outline)/pig.png",
            "parrot":   "PNG/Round (outline)/parrot.png",
            "dog":      "PNG/Round (outline)/dog.png",
            "frog":     "PNG/Round (outline)/frog.png",
            "owl":      "PNG/Round (outline)/owl.png",
            "panda":    "PNG/Round (outline)/panda.png",
            "monkey":   "PNG/Round (outline)/monkey.png",
            "giraffe":  "PNG/Round (outline)/giraffe.png",
        },
    },
]


def download_and_extract_kenney(pack: dict, output_dir: Path, dry_run: bool = False) -> int:
    """Download a Kenney zip pack and extract specific sprites."""
    import zipfile
    import tempfile
    import os

    cat_dir = output_dir / pack["category"]
    cat_dir.mkdir(parents=True, exist_ok=True)

    needed = {name: path for name, path in pack["files"].items()
              if not (cat_dir / f"{name}.png").exists()}

    if not needed:
        print(f"  [{pack['name']}] all {len(pack['files'])} sprites already exist, skipping")
        return 0

    print(f"  [{pack['name']}] downloading {len(needed)} sprites...")

    if dry_run:
        for name in needed:
            print(f"    would save: {cat_dir / name}.png")
        return len(needed)

    # Download zip to temp file
    tmp_path = Path(tempfile.mktemp(suffix=".zip"))
    urls = [pack["url"]] + ([pack["url_fallback"]] if "url_fallback" in pack else [])
    downloaded = False
    for url in urls:
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; kids-channel-bot/1.0)"}
            )
            print(f"  Downloading {url} ...")
            with urllib.request.urlopen(req, timeout=60) as resp:
                tmp_path.write_bytes(resp.read())
            print(f"  Downloaded {tmp_path.stat().st_size // 1024}KB")
            downloaded = True
            break
        except Exception as e:
            print(f"  WARN {url}: {e}")
    if not downloaded:
        print(f"  ERROR: all URLs failed for {pack['name']}")
        return 0

    saved = 0
    try:
        with zipfile.ZipFile(tmp_path) as zf:
            available = set(zf.namelist())
            for name, zip_path in needed.items():
                # Try different path variants inside zip
                candidates = [
                    zip_path,
                    zip_path.replace("PNG/Default/", "PNG/"),
                    zip_path.lower(),
                    Path(zip_path).name,
                ]
                matched = None
                for c in candidates:
                    if c in available:
                        matched = c
                        break
                    # fuzzy: find by filename
                    fname = Path(zip_path).name
                    hits = [z for z in available if z.endswith(fname)]
                    if hits:
                        matched = hits[0]
                        break

                if not matched:
                    # Last resort: search by stem
                    stem = Path(zip_path).stem.lower()
                    hits = [z for z in available if Path(z).stem.lower() == stem and z.endswith(".png")]
                    if hits:
                        matched = hits[0]

                if not matched:
                    print(f"    MISSING in zip: {zip_path}")
                    continue

                data = zf.read(matched)
                img = Image.open(io.BytesIO(data)).convert("RGBA")
                img = img.resize((512, 512), Image.LANCZOS)
                out_path = cat_dir / f"{name}.png"
                img.save(out_path, "PNG")
                print(f"    saved: {out_path.name}")
                saved += 1
    except Exception as e:
        print(f"  ERROR extracting {pack['name']}: {e}")
    finally:
        tmp_path.unlink(missing_ok=True)

    return saved


def show_summary(output_dir: Path):
    print(f"\n{'='*50}")
    print("  Sprites summary:")
    total = 0
    for cat_dir in sorted(output_dir.iterdir()):
        if not cat_dir.is_dir():
            continue
        files = list(cat_dir.glob("*.png"))
        print(f"  {cat_dir.name:<15} {len(files):3} sprites")
        total += len(files)
    print(f"  {'TOTAL':<15} {total:3} sprites")
    print(f"{'='*50}\n")


def main():
    parser = argparse.ArgumentParser(description="Download cartoon sprites")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be downloaded")
    parser.add_argument("--category", help="Only download specific category")
    args = parser.parse_args()

    print(f"\nSprite downloader — target: {SPRITES_DIR}")
    if args.dry_run:
        print("DRY RUN mode\n")

    total_saved = 0

    # OpenMoji food sprites (flat cartoon emoji style)
    if not args.category or args.category == "fruits":
        total_saved += download_openmoji("fruits", OPENMOJI_FOOD, SPRITES_DIR, dry_run=args.dry_run)

    # Kenney animal pack (round cartoon faces)
    packs = KENNEY_PACKS
    if args.category:
        packs = [p for p in KENNEY_PACKS if p["category"] == args.category]

    for pack in packs:
        total_saved += download_and_extract_kenney(pack, SPRITES_DIR, dry_run=args.dry_run)

    show_summary(SPRITES_DIR)
    print(f"Done. {total_saved} new sprites saved.")


if __name__ == "__main__":
    main()
