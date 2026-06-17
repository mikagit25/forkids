#!/usr/bin/env python3
"""
Generate frame-by-frame animation sprites for each character via FLUX.

Each character gets 5 poses:
  {name}_idle.png   — standing neutral
  {name}_smile.png  — big happy smile
  {name}_blink.png  — eyes closed (blinking)
  {name}_jump.png   — mid-air, arms raised
  {name}_wave.png   — waving one arm

Output: assets/sprites_flux/animals/{name}_{pose}.png
        (same folder as single-frame sprites)

Usage:
    python3 scripts/generate_sprite_frames_flux.py --name bear
    python3 scripts/generate_sprite_frames_flux.py --name bear panda fox
    python3 scripts/generate_sprite_frames_flux.py --all
    python3 scripts/generate_sprite_frames_flux.py --name bear --poses smile blink
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

ROOT     = Path(__file__).resolve().parent.parent
KEY_FILE = ROOT / "credentials" / "together_api_key.txt"
OUT_DIR  = ROOT / "assets" / "sprites_flux" / "animals"

TOGETHER_URL = "https://api.together.xyz/v1/images/generations"
MODEL        = "black-forest-labs/FLUX.1-schnell"
SIZE         = 1024

# ── Character base descriptions (for consistency across poses) ───────────────
CHARACTERS = {
    "bear":     "cute 3D cartoon brown bear cub, round fluffy ears, cream-colored belly",
    "tiger":    "cute 3D cartoon orange baby tiger with black stripes, big round eyes",
    "frog":     "cute 3D cartoon bright green frog, wide smile, big round eyes",
    "penguin":  "cute 3D cartoon black-and-white baby penguin, orange beak, round belly",
    "lion":     "cute 3D cartoon golden lion cub, fluffy mane, big friendly eyes",
    "panda":    "cute 3D cartoon black-and-white panda bear, black eye patches, chubby",
    "koala":    "cute 3D cartoon grey koala, large round ears, grey fluffy fur",
    "fox":      "cute 3D cartoon red fox, white-tipped tail, pointy ears",
    "rabbit":   "cute 3D cartoon white bunny rabbit, long floppy ears, pink nose",
    "cow":      "cute 3D cartoon black-and-white spotted cow, big gentle eyes, pink nose",
    "duck":     "cute 3D cartoon yellow baby duck, orange beak, fluffy feathers",
    "pig":      "cute 3D cartoon pink pig, curly tail, round snout",
    "elephant": "cute 3D cartoon grey baby elephant, big ears, long trunk curled up",
    "monkey":   "cute 3D cartoon brown monkey, big brown eyes, long tail",
    "dog":      "cute 3D cartoon golden puppy dog, floppy ears, wagging tail",
    "cat":      "cute 3D cartoon orange tabby kitten, striped fur, bright green eyes",
    "owl":      "cute 3D cartoon colorful owl, large round eyes, small beak, fluffy feathers",
    "unicorn":  "cute 3D cartoon white unicorn, rainbow mane and tail, golden horn",
    "dino":     "cute 3D cartoon friendly green dinosaur, short arms, big smile",
    "parrot":   "cute 3D cartoon colorful parrot, bright red-green-blue feathers",
}

# ── Pose suffixes added to base description ───────────────────────────────────
POSES = {
    "idle":  "standing upright, neutral friendly expression, arms relaxed at sides",
    "smile": "laughing with a huge happy smile, eyes squinting with joy, both hands on cheeks",
    "blink": "standing, eyes completely closed in a gentle blink, slight smile",
    "jump":  "jumping in the air, arms raised high above head, excited expression, legs bent",
    "wave":  "standing, waving one hand enthusiastically high in the air, big smile",
}

SUFFIX = (
    ", Pixar style, bright vivid colors, smooth shading, white background, "
    "isolated object, studio lighting, high quality render, children illustration, "
    "no text, no letters, no background"
)


def load_key() -> str:
    if not KEY_FILE.exists():
        print(f"ERROR: API key not found: {KEY_FILE}")
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
                print(f"  Rate limited — waiting {wait}s")
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
            return None
        except Exception as e:
            if attempt < retries - 1:
                print(f"  Error: {e} — retrying in 30s")
                time.sleep(30)
            else:
                print(f"  ERROR: {e}")
    return None


def remove_background(img_bytes: bytes) -> bytes:
    try:
        from rembg import remove
        return remove(img_bytes)
    except Exception as e:
        print(f"  WARNING: rembg failed ({e}), keeping white background")
        return img_bytes


def save_png(img_bytes: bytes, path: Path):
    img = Image.open(io.BytesIO(img_bytes))
    img = img.convert("RGBA")
    img.save(path, "PNG")


def generate_frames(name: str, poses: list[str], force: bool, dry_run: bool, key: str):
    if name not in CHARACTERS:
        print(f"  Unknown character: {name}. Add to CHARACTERS dict.")
        return

    base_desc = CHARACTERS[name]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    generated = 0

    for pose in poses:
        out_path = OUT_DIR / f"{name}_{pose}.png"
        if out_path.exists() and not force:
            print(f"  SKIP {name}_{pose} (exists)")
            continue

        prompt = f"{base_desc}, {POSES[pose]}{SUFFIX}"
        print(f"  [{pose}] {prompt[:90]}...")

        if dry_run:
            print(f"    [DRY RUN]")
            continue

        img_bytes = generate_flux(prompt, key)
        if not img_bytes:
            print(f"    FAILED")
            continue

        clean = remove_background(img_bytes)
        save_png(clean, out_path)
        size_kb = out_path.stat().st_size // 1024
        print(f"    ✓ {out_path.name} ({size_kb} KB)")
        generated += 1

        time.sleep(15)

    return generated


def main():
    parser = argparse.ArgumentParser(description="Generate frame-by-frame animation sprites via FLUX")
    parser.add_argument("--name",  nargs="+", help="Character name(s)")
    parser.add_argument("--all",   action="store_true", help="All characters")
    parser.add_argument("--poses", nargs="+", choices=list(POSES.keys()),
                        default=list(POSES.keys()), help="Which poses (default: all 5)")
    parser.add_argument("--force",   action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--list",    action="store_true", help="List characters")
    args = parser.parse_args()

    if args.list:
        for n, d in CHARACTERS.items():
            print(f"  {n}: {d[:60]}")
        return

    key = load_key()
    names = list(CHARACTERS.keys()) if args.all else (args.name or [])

    if not names:
        parser.print_help()
        return

    total_generated = 0
    for name in names:
        print(f"\n── {name.upper()} ({len(args.poses)} poses) ──")
        n = generate_frames(name, args.poses, args.force, args.dry_run, key)
        if n:
            total_generated += n

    print(f"\n✓ Total generated: {total_generated} frames → {OUT_DIR}")

    # Write/update sprite manifest JSON
    manifest_path = OUT_DIR.parent / "sprite_frames_manifest.json"
    manifest = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())

    for name in names:
        frames = {}
        for pose in POSES:
            p = OUT_DIR / f"{name}_{pose}.png"
            if p.exists():
                frames[pose] = f"animals_flux/{name}_{pose}.png"
        if frames:
            manifest[name] = frames

    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"✓ Manifest updated: {manifest_path.name}")


if __name__ == "__main__":
    main()
