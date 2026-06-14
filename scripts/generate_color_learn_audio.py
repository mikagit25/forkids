#!/usr/bin/env python3
"""
Generate voiceover audio for ColorLearnLong videos via edge-tts.

Output: remotion/public/audio/color_learn/{lang}/{color}_{section}.mp3

Sections per color:
  intro     — "Today we learn RED!"
  obj1      — full cycle: intro + question + answer for object 1
  obj2      — same for object 2
  obj3      — same for object 3
  song      — color chant
  outro     — "Great job! You know RED!"

Usage:
  python3 scripts/generate_color_learn_audio.py              # all colors, both langs
  python3 scripts/generate_color_learn_audio.py --color red  # one color
  python3 scripts/generate_color_learn_audio.py --lang en    # one language
  python3 scripts/generate_color_learn_audio.py --force      # regenerate existing
"""

import argparse
import asyncio
import re
import subprocess
import sys
import yaml
from pathlib import Path

ROOT      = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "config" / "color_learn_data.yaml"
OUT_DIR   = ROOT / "remotion" / "public" / "audio" / "color_learn"

EN_VOICE = "en-US-JennyNeural"
AR_VOICE = "ar-SA-ZariyahNeural"


def load_data() -> list:
    with open(DATA_PATH) as f:
        return yaml.safe_load(f)["colors"]


# ── EN script templates ───────────────────────────────────────────────────────

def en_intro(color: str) -> str:
    return (
        f"Hello friends! Today we are going to learn the color {color}! "
        f"{color}! Can you say {color}? Let's go!"
    )


def en_obj_cycle(color: str, obj_name: str, article: str = "a") -> str:
    """Full 45-second dialogue cycle for one object."""
    return (
        f"Look! {article.capitalize()} {obj_name}! "
        f"The {obj_name} is {color}! "
        f"What color is the {obj_name}? "
        f"... "
        f"That's right! {color}! "
        f"The {obj_name} is {color}! "
        f"{color}! {color}! {color}! "
        f"Great job!"
    )


def en_song(color: str, obj1: str, obj2: str, obj3: str) -> str:
    return (
        f"{color}, {color}, everything is {color}! "
        f"{color} {obj1}, {color} {obj2}, {color} {obj3}! "
        f"Can you see the {color}? "
        f"I see {color}! "
        f"{color}, {color}, {color}! "
        f"I love the color {color}!"
    )


def en_outro(color: str, obj1: str, obj2: str, obj3: str) -> str:
    return (
        f"Amazing job! Now you know the color {color}! "
        f"{color} {obj1}! {color} {obj2}! {color} {obj3}! "
        f"You are so smart! "
        f"See you next time! Bye bye!"
    )


# ── AR script templates ───────────────────────────────────────────────────────

def ar_intro(color_ar: str) -> str:
    return (
        f"مرحباً أصدقاء! اليوم سنتعلم اللون {color_ar}! "
        f"{color_ar}! هل يمكنك قول {color_ar}؟ هيا بنا!"
    )


def ar_obj_cycle(color_ar: str, obj_ar: str) -> str:
    return (
        f"انظر! هذا {obj_ar}! "
        f"{obj_ar} لونه {color_ar}! "
        f"ما لون {obj_ar}؟ "
        f"... "
        f"أحسنت! {color_ar}! "
        f"{obj_ar} لونه {color_ar}! "
        f"{color_ar}! {color_ar}! {color_ar}! "
        f"عمل رائع!"
    )


def ar_song(color_ar: str, obj1_ar: str, obj2_ar: str, obj3_ar: str) -> str:
    return (
        f"{color_ar}، {color_ar}، كل شيء {color_ar}! "
        f"{obj1_ar} {color_ar}، {obj2_ar} {color_ar}، {obj3_ar} {color_ar}! "
        f"هل ترى اللون {color_ar}؟ "
        f"أرى {color_ar}! "
        f"{color_ar}، {color_ar}، {color_ar}! "
        f"أحب اللون {color_ar}!"
    )


def ar_outro(color_ar: str, obj1_ar: str, obj2_ar: str, obj3_ar: str) -> str:
    return (
        f"عمل رائع! الآن تعرف اللون {color_ar}! "
        f"{obj1_ar} {color_ar}! {obj2_ar} {color_ar}! {obj3_ar} {color_ar}! "
        f"أنت ذكي جداً! "
        f"إلى اللقاء! مع السلامة!"
    )


# ── Articles helper ───────────────────────────────────────────────────────────

VOWELS = "aeiou"

def article(word: str) -> str:
    return "an" if word[0].lower() in VOWELS else "a"


# ── edge-tts generation ───────────────────────────────────────────────────────

def tts_generate(text: str, voice: str, out_path: Path, force: bool = False) -> bool:
    if out_path.exists() and not force:
        print(f"    skip (exists): {out_path.name}")
        return True
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Replace ellipsis "..." with explicit pause using a short silence
    text_clean = text.replace("...", ". . .")
    cmd = ["edge-tts", "--voice", voice, "--text", text_clean, "--write-media", str(out_path)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0 and out_path.exists():
        size = out_path.stat().st_size
        print(f"    ✓ {out_path.name}  ({size//1024}KB)")
        return True
    print(f"    ✗ FAILED: {out_path.name}: {result.stderr[:100]}")
    return False


def generate_color(color_data: dict, lang: str, force: bool = False):
    key      = color_data["key"]
    color_en = color_data["name_en"]
    color_ar = color_data["name_ar"]
    objs     = color_data["objects"]

    out_dir = OUT_DIR / lang
    out_dir.mkdir(parents=True, exist_ok=True)

    obj_en = [o["name_en"] for o in objs]
    obj_ar = [o["name_ar"] for o in objs]

    print(f"\n  [{lang.upper()}] {key.upper()} ({color_en} / {color_ar})")

    if lang == "en":
        voice  = EN_VOICE
        scripts = {
            "intro": en_intro(color_en),
            "obj1":  en_obj_cycle(color_en, obj_en[0], article(obj_en[0])),
            "obj2":  en_obj_cycle(color_en, obj_en[1], article(obj_en[1])),
            "obj3":  en_obj_cycle(color_en, obj_en[2], article(obj_en[2])),
            "song":  en_song(color_en, obj_en[0], obj_en[1], obj_en[2]),
            "outro": en_outro(color_en, obj_en[0], obj_en[1], obj_en[2]),
        }
    else:
        voice  = AR_VOICE
        scripts = {
            "intro": ar_intro(color_ar),
            "obj1":  ar_obj_cycle(color_ar, obj_ar[0]),
            "obj2":  ar_obj_cycle(color_ar, obj_ar[1]),
            "obj3":  ar_obj_cycle(color_ar, obj_ar[2]),
            "song":  ar_song(color_ar, obj_ar[0], obj_ar[1], obj_ar[2]),
            "outro": ar_outro(color_ar, obj_ar[0], obj_ar[1], obj_ar[2]),
        }

    ok = fail = 0
    for section, text in scripts.items():
        out_path = out_dir / f"{key}_{section}.mp3"
        if tts_generate(text, voice, out_path, force):
            ok += 1
        else:
            fail += 1

    return ok, fail


def main():
    parser = argparse.ArgumentParser(description="Generate color learn audio via edge-tts")
    parser.add_argument("--color", help="Single color key (e.g. red)")
    parser.add_argument("--lang",  choices=["en", "ar"], help="Single language")
    parser.add_argument("--force", action="store_true", help="Regenerate existing files")
    args = parser.parse_args()

    colors = load_data()
    if args.color:
        colors = [c for c in colors if c["key"] == args.color]
        if not colors:
            print(f"Color '{args.color}' not found in data.")
            sys.exit(1)

    langs = [args.lang] if args.lang else ["en", "ar"]

    total_ok = total_fail = 0
    for color_data in colors:
        for lang in langs:
            ok, fail = generate_color(color_data, lang, force=args.force)
            total_ok   += ok
            total_fail += fail

    print(f"\nDone: {total_ok} generated, {total_fail} failed")


if __name__ == "__main__":
    main()
