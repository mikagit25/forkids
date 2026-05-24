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

NUMBER_WORDS = {
    "1": "One",      "2": "Two",       "3": "Three",
    "4": "Four",     "5": "Five",      "6": "Six",
    "7": "Seven",    "8": "Eight",     "9": "Nine",
    "10": "Ten",     "11": "Eleven",   "12": "Twelve",
    "13": "Thirteen","14": "Fourteen", "15": "Fifteen",
    "16": "Sixteen", "17": "Seventeen","18": "Eighteen",
    "19": "Nineteen","20": "Twenty",
}

COLORS = {
    "red":    ("Red",    "#FF4444"),
    "orange": ("Orange", "#FF922B"),
    "yellow": ("Yellow", "#FFD93D"),
    "green":  ("Green",  "#6BCB77"),
    "blue":   ("Blue",   "#4D96FF"),
    "purple": ("Purple", "#A29BFE"),
    "pink":   ("Pink",   "#FD79A8"),
    "brown":  ("Brown",  "#A0522D"),
}

SHAPES = {
    "circle":    "Circle",
    "square":    "Square",
    "triangle":  "Triangle",
    "rectangle": "Rectangle",
    "oval":      "Oval",
    "star":      "Star",
    "heart":     "Heart",
    "diamond":   "Diamond",
}

# Vocabulary: object → display name
VOCABULARY = {
    "apple":      "Apple",
    "banana":     "Banana",
    "cat":        "Cat",
    "dog":        "Dog",
    "elephant":   "Elephant",
    "frog":       "Frog",
    "giraffe":    "Giraffe",
    "hippo":      "Hippo",
    "lion":       "Lion",
    "monkey":     "Monkey",
    "penguin":    "Penguin",
    "rabbit":     "Rabbit",
    "tiger":      "Tiger",
    "zebra":      "Zebra",
    "bird":       "Bird",
    "fish":       "Fish",
    "bear":       "Bear",
    "owl":        "Owl",
}

PACKS = {
    "abc": {letter: f"{letter}. {word}. {letter} is for {word}."
            for letter, word in ABC_WORDS.items()},
    "numbers": {k: f"{word}! {word}! Let's count! {word}!"
                for k, word in NUMBER_WORDS.items()},
    "colors":  {k: f"{name}! {name}! Can you find something {name.lower()}?"
                for k, (name, _) in COLORS.items()},
    "shapes":  {k: f"{name}! This is a {name.lower()}! A {name.lower()}!"
                for k, name in SHAPES.items()},
    "vocabulary": {k: f"This is a {name.lower()}! {name}! {name}!"
                   for k, name in VOCABULARY.items()},
    "counting": {
        "1_apple":  "One apple! One!",
        "2_apples": "Two apples! One, two!",
        "3_apples": "Three apples! One, two, three!",
        "4_apples": "Four apples! One, two, three, four!",
        "5_apples": "Five apples! One, two, three, four, five!",
        "1_cat":    "One cat! One!",
        "2_cats":   "Two cats! One, two!",
        "3_cats":   "Three cats! One, two, three!",
        "4_cats":   "Four cats! One, two, three, four!",
        "5_cats":   "Five cats! One, two, three, four, five!",
        "1_star":   "One star! One!",
        "2_stars":  "Two stars! One, two!",
        "3_stars":  "Three stars! One, two, three!",
        "4_stars":  "Four stars! One, two, three, four!",
        "5_stars":  "Five stars! One, two, three, four, five!",
    },
    "colors_objects": {
        "red_apple":     "The apple is red! Red apple!",
        "yellow_banana": "The banana is yellow! Yellow banana!",
        "orange_orange": "The orange is orange! Orange orange!",
        "green_frog":    "The frog is green! Green frog!",
        "blue_sky":      "The sky is blue! Blue blue blue!",
        "purple_grape":  "The grape is purple! Purple grape!",
        "pink_pig":      "The pig is pink! Pink pig!",
        "brown_bear":    "The bear is brown! Brown bear!",
    },
    "shapes_colors": {
        "green_circle":    "A green circle! Green and round!",
        "blue_square":     "A blue square! Blue with four sides!",
        "red_triangle":    "A red triangle! Red with three sides!",
        "yellow_rectangle":"A yellow rectangle! Long and yellow!",
        "purple_oval":     "A purple oval! Round like an egg!",
        "orange_star":     "An orange star! Shiny orange star!",
        "pink_heart":      "A pink heart! Love, love, love!",
        "teal_diamond":    "A teal diamond! Sparkly diamond!",
    },
}

# Flat lookup: key → display text (for get_phrase_path)
NUMBERS = {k: v for k, v in NUMBER_WORDS.items()}  # "1" → "One"

# Individual words (for sprites / scene lookup)
WORD_PHRASES = {
    **ABC_WORDS,
    **NUMBER_WORDS,
    **{k: v[0] for k, v in COLORS.items()},
    **SHAPES,
    **VOCABULARY,
}


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
    group.add_argument("--pack", choices=list(PACKS.keys()) + ["all"],
                       help="Generate an entire content pack (or 'all' for all packs)")
    parser.add_argument("--lang", default="en", help="Language code (default: en)")
    parser.add_argument("--slow", action="store_true", help="Slower speech (for learning)")
    args = parser.parse_args()

    if args.text:
        path = generate_phrase(args.text, lang=args.lang, slow=args.slow)
        print(f"Saved: {path}")
    elif args.pack == "all":
        for pack_name in PACKS:
            generate_pack(pack_name, lang=args.lang)
    else:
        generate_pack(args.pack, lang=args.lang)


if __name__ == "__main__":
    main()
