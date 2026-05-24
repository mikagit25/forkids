#!/usr/bin/env python3
"""
Voiceover generator using gTTS (Google Text-to-Speech).

Generates MP3 files and caches them so each phrase is generated once.

Usage:
    python3 generate_voiceover.py --text "Apple" --lang en
    python3 generate_voiceover.py --pack abc --lang en
    python3 generate_voiceover.py --pack numbers --lang en
    python3 generate_voiceover.py --pack colors --lang en

Cache: assets/audio/voiceover/{lang}/{slug}.mp3
"""

import argparse
import re
import time
from pathlib import Path

from gtts import gTTS

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "assets" / "audio" / "voiceover"

# ── Content packs ─────────────────────────────────────────────────────────────

ABC_WORDS = {
    "A": "Apple",    "B": "Banana",   "C": "Cat",
    "D": "Dog",      "E": "Elephant", "F": "Frog",
    "G": "Giraffe",  "H": "Hippo",    "I": "Igloo",
    "J": "Jellyfish","K": "Koala",    "L": "Lion",
    "M": "Monkey",   "N": "Nest",     "O": "Owl",
    "P": "Penguin",  "Q": "Queen",    "R": "Rabbit",
    "S": "Star",     "T": "Tiger",    "U": "Umbrella",
    "V": "Violin",   "W": "Watermelon","X": "Xylophone",
    "Y": "Yak",      "Z": "Zebra",
}

NUMBERS = {str(i): str(i) for i in range(1, 21)}

COLORS = {
    "red": "Red",       "blue": "Blue",     "green": "Green",
    "yellow": "Yellow", "orange": "Orange", "purple": "Purple",
    "pink": "Pink",     "white": "White",   "black": "Black",
    "brown": "Brown",
}

PACKS = {
    "abc":     {letter: f"{letter}. {word}. {letter} is for {word}."
                for letter, word in ABC_WORDS.items()},
    "numbers": {k: f"{v}! {v}!" for k, v in NUMBERS.items()},
    "colors":  {k: f"{v}! Can you see {v.lower()}?" for k, v in COLORS.items()},
}

# Individual words (for sprites)
WORD_PHRASES = {**ABC_WORDS, **NUMBERS, **COLORS}


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9_]", "_", text.lower().strip()).strip("_")


def generate_phrase(text: str, lang: str = "en", slow: bool = False) -> Path:
    """Generate and cache a single phrase. Returns the MP3 path."""
    lang_dir = CACHE_DIR / lang
    lang_dir.mkdir(parents=True, exist_ok=True)

    slug = slugify(text)
    out_path = lang_dir / f"{slug}.mp3"

    if out_path.exists():
        return out_path

    tts = gTTS(text=text, lang=lang, slow=slow)
    tts.save(str(out_path))
    return out_path


def generate_pack(pack_name: str, lang: str = "en") -> dict:
    """Generate all phrases in a pack. Returns {key: mp3_path}."""
    if pack_name not in PACKS:
        raise ValueError(f"Unknown pack: {pack_name}. Available: {list(PACKS.keys())}")

    phrases = PACKS[pack_name]
    results = {}
    total = len(phrases)

    print(f"\nGenerating '{pack_name}' pack ({total} phrases, lang={lang})...")
    for i, (key, text) in enumerate(phrases.items(), 1):
        slug = slugify(text)
        lang_dir = CACHE_DIR / lang
        out_path = lang_dir / f"{slug}.mp3"
        if out_path.exists():
            print(f"  [{i:02d}/{total}] {key:12} ← cached")
        else:
            path = generate_phrase(text, lang=lang)
            print(f"  [{i:02d}/{total}] {key:12} → {path.name}")
            time.sleep(0.3)  # be polite to Google TTS
        results[key] = out_path

    print(f"Done. {total} phrases in {CACHE_DIR / lang}/\n")
    return results


def get_phrase_path(key: str, lang: str = "en") -> Path:
    """Return the cached MP3 path for a word/key. Generates if missing."""
    text = WORD_PHRASES.get(key, key)
    return generate_phrase(text, lang=lang)


def main():
    parser = argparse.ArgumentParser(description="Generate voiceover MP3s")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--text", help="Single phrase to generate")
    group.add_argument("--pack", choices=list(PACKS.keys()),
                       help="Generate an entire content pack")
    parser.add_argument("--lang", default="en", help="Language code (default: en)")
    parser.add_argument("--slow", action="store_true", help="Slower speech (for learning)")
    args = parser.parse_args()

    if args.text:
        path = generate_phrase(args.text, lang=args.lang, slow=args.slow)
        print(f"Saved: {path}")
    else:
        generate_pack(args.pack, lang=args.lang)


if __name__ == "__main__":
    main()
