#!/usr/bin/env python3
"""
Generate Pixar 3D bear character sprites and emotion/concept sprites
for CharacterDialogueLong compositions via Together.ai FLUX.1-schnell.

Usage:
  python3 scripts/generate_bear_sprites.py
  python3 scripts/generate_bear_sprites.py --force
  python3 scripts/generate_bear_sprites.py --only bear
  python3 scripts/generate_bear_sprites.py --only emotions
"""
import argparse
import base64
import sys
import time
from pathlib import Path

import requests

ROOT        = Path(__file__).resolve().parent.parent
SPRITES_DIR = ROOT / "remotion" / "public" / "sprites"
KEY_FILE    = ROOT / "credentials" / "together_api_key.txt"

TOGETHER_URL   = "https://api.together.xyz/v1/images/generations"
TOGETHER_MODEL = "black-forest-labs/FLUX.1-schnell"

# ── Sprite definitions ────────────────────────────────────────────────────────
SPRITES: dict[str, tuple[str, str]] = {
    # (output_path, prompt)

    # Bear character variants
    "characters/bear_happy_3d.png": (
        "A single cute 3D Pixar-style brown teddy bear character, big round eyes, "
        "huge happy smile, fluffy round body, arms slightly raised in excitement, "
        "standing upright, warm friendly expression, pure white background, "
        "children's educational illustration, no text, no shadows"
    ),
    "characters/bear_talking_3d.png": (
        "A single cute 3D Pixar-style brown teddy bear character, big round eyes, "
        "mouth open in a wide friendly smile as if speaking, fluffy round body, "
        "one hand raised gesturing, standing upright, pure white background, "
        "children's educational illustration, no text, no shadows"
    ),
    "characters/bear_wave_3d.png": (
        "A single cute 3D Pixar-style brown teddy bear character, big round eyes, "
        "big happy smile, waving one paw up high as if saying hello or goodbye, "
        "fluffy round body, pure white background, children's educational illustration, "
        "no text, no shadows"
    ),
    "characters/bear_celebrate_3d.png": (
        "A single cute 3D Pixar-style brown teddy bear character, big round eyes, "
        "both arms raised up in celebration, huge excited smile, fluffy round body, "
        "jumping or leaping pose, pure white background, children's educational illustration, "
        "no text, no shadows"
    ),

    # Emotions sprites
    "emotions/happy_3d.png": (
        "A single cute 3D Pixar-style round face emoji character showing HAPPY emotion, "
        "bright yellow round face, huge beaming smile, rosy pink cheeks, "
        "sparkling happy eyes shaped like crescents, pure white background, "
        "children's educational illustration, no text, simple clean design"
    ),
    "emotions/sad_3d.png": (
        "A single cute 3D Pixar-style round face emoji character showing SAD emotion, "
        "soft blue round face, pouty frown, teardrop on cheek, droopy sad eyes, "
        "gentle melancholy expression, pure white background, "
        "children's educational illustration, no text, simple clean design"
    ),
    "emotions/angry_3d.png": (
        "A single cute 3D Pixar-style round face emoji character showing ANGRY emotion, "
        "red round face, eyebrows furrowed down in anger, grumpy frown, "
        "crossed arms if possible, steamy expression, pure white background, "
        "children's educational illustration, no text, simple clean design"
    ),
    "emotions/surprised_3d.png": (
        "A single cute 3D Pixar-style round face emoji character showing SURPRISED emotion, "
        "pale yellow round face, wide open round eyes, O-shaped mouth wide open in shock, "
        "hands on cheeks, astonished expression, pure white background, "
        "children's educational illustration, no text, simple clean design"
    ),
    "emotions/scared_3d.png": (
        "A single cute 3D Pixar-style round face emoji character showing SCARED emotion, "
        "pale purple round face, big wide frightened eyes, trembling expression, "
        "hands covering mouth, cowering slightly, pure white background, "
        "children's educational illustration, no text, simple clean design"
    ),
    "emotions/excited_3d.png": (
        "A single cute 3D Pixar-style round face emoji character showing EXCITED emotion, "
        "bright orange round face, huge wide excited smile, starry sparkling eyes, "
        "both hands raised in joy, energetic jumping pose, pure white background, "
        "children's educational illustration, no text, simple clean design"
    ),
    "emotions/sleepy_3d.png": (
        "A single cute 3D Pixar-style round face emoji character showing SLEEPY emotion, "
        "soft lavender round face, half-closed droopy eyes, little Zzzz speech bubble, "
        "yawning mouth, relaxed sleepy expression, pure white background, "
        "children's educational illustration, no text, simple clean design"
    ),
    "emotions/love_3d.png": (
        "A single cute 3D Pixar-style round face emoji character showing LOVE emotion, "
        "pink round face, heart-shaped eyes, blushing cheeks, sweet smile, "
        "small hearts floating around, pure white background, "
        "children's educational illustration, no text, simple clean design"
    ),

    # Concept sprites for special mechanics episodes
    "concepts/big_3d.png": (
        "A single cute 3D Pixar-style concept illustration of BIG — "
        "a large oversized star with a tiny star next to it showing size contrast, "
        "both have cute eyes, bright colors, pure white background, "
        "children's educational illustration, no text"
    ),
    "concepts/small_3d.png": (
        "A single cute 3D Pixar-style concept illustration of SMALL — "
        "a tiny cute star character with a big star next to it showing size contrast, "
        "both have cute eyes, bright colors, pure white background, "
        "children's educational illustration, no text"
    ),
    "concepts/fast_3d.png": (
        "A single cute 3D Pixar-style concept illustration of FAST — "
        "a cute car or animal character with speed lines showing fast movement, "
        "motion blur effect, bright colors, dynamic pose, pure white background, "
        "children's educational illustration, no text"
    ),
    "concepts/slow_3d.png": (
        "A single cute 3D Pixar-style concept illustration of SLOW — "
        "a cute turtle or snail character moving slowly, calm gentle expression, "
        "peaceful slow motion feel, bright colors, pure white background, "
        "children's educational illustration, no text"
    ),
    "concepts/up_3d.png": (
        "A single cute 3D Pixar-style concept illustration of UP — "
        "a cute balloon or bird character floating upward, arrow pointing up, "
        "cheerful expression, bright colors, pure white background, "
        "children's educational illustration, no text"
    ),
    "concepts/down_3d.png": (
        "A single cute 3D Pixar-style concept illustration of DOWN — "
        "a cute character gently sliding down, arrow pointing down, "
        "playful expression, bright colors, pure white background, "
        "children's educational illustration, no text"
    ),
    "concepts/hot_3d.png": (
        "A single cute 3D Pixar-style concept illustration of HOT — "
        "a cute sun or fire character radiating heat waves, "
        "warm red-orange colors, sweating expression, pure white background, "
        "children's educational illustration, no text"
    ),
    "concepts/cold_3d.png": (
        "A single cute 3D Pixar-style concept illustration of COLD — "
        "a cute snowflake or ice cube character with icicles, "
        "cool blue colors, shivering expression, pure white background, "
        "children's educational illustration, no text"
    ),
}

GROUPS = {
    "bear":     [k for k in SPRITES if k.startswith("characters/")],
    "emotions": [k for k in SPRITES if k.startswith("emotions/")],
    "concepts": [k for k in SPRITES if k.startswith("concepts/")],
}


def load_key() -> str:
    if not KEY_FILE.exists():
        sys.exit(f"Together.ai key not found: {KEY_FILE}")
    return KEY_FILE.read_text().strip()


def flux_generate(prompt: str, key: str) -> bytes | None:
    try:
        r = requests.post(
            TOGETHER_URL,
            headers={"Authorization": f"Bearer {key}"},
            json={"model": TOGETHER_MODEL, "prompt": prompt,
                  "width": 1024, "height": 1024, "steps": 4, "n": 1},
            timeout=90,
        )
        if r.status_code != 200:
            print(f"    API {r.status_code}: {r.text[:120]}")
            return None
        item = r.json()["data"][0]
        b64 = item.get("b64_json")
        if b64:
            return base64.b64decode(b64)
        url = item.get("url")
        if url:
            ir = requests.get(url, timeout=30)
            return ir.content if ir.status_code == 200 else None
    except Exception as e:
        print(f"    Request failed: {e}")
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    parser.add_argument("--only", choices=list(GROUPS.keys()),
                        help=f"Only generate group: {', '.join(GROUPS.keys())}")
    args = parser.parse_args()

    key = load_key()

    keys_to_gen = list(GROUPS[args.only]) if args.only else list(SPRITES.keys())

    print(f"Generating {len(keys_to_gen)} character/concept sprites via FLUX.1-schnell...")
    ok = fail = skip = 0

    for rel_path in keys_to_gen:
        prompt = SPRITES[rel_path]
        out = SPRITES_DIR / rel_path
        if out.exists() and not args.force:
            print(f"  ✓ {rel_path} — skip (--force to overwrite)")
            skip += 1
            continue
        print(f"  Generating {rel_path}...", end=" ", flush=True)
        data = flux_generate(prompt, key)
        if data:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(data)
            print(f"✓ {len(data)//1024}KB")
            ok += 1
            time.sleep(0.5)
        else:
            print("FAILED")
            fail += 1

    print(f"\nDone: {ok} generated, {skip} skipped, {fail} failed")
    print(f"Sprites: {SPRITES_DIR}")


if __name__ == "__main__":
    main()
