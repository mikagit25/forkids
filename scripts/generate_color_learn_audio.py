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
ID_VOICE = "id-ID-GadisNeural"


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


def en_review(color: str, obj1: str, obj2: str, obj3: str) -> str:
    return (
        f"Great job! Let's review! "
        f"What color is the {obj1}? "
        f"The {obj1} is {color}! {color}! "
        f"What color is the {obj2}? "
        f"The {obj2} is {color}! {color}! "
        f"What color is the {obj3}? "
        f"The {obj3} is {color}! {color}! "
        f"You are so smart! Can you say {color}? "
        f"{color}! {color}! {color}! "
        f"The {obj1} is {color}! Say it with me! {color}! "
        f"The {obj2} is {color}! Say it with me! {color}! "
        f"The {obj3} is {color}! Say it with me! {color}! "
        f"Wonderful! You know the color {color}! "
        f"{color}! {color}! Let's say it one more time! {color}! "
        f"You did it! You are a color champion!"
    )


# ── ID script templates ───────────────────────────────────────────────────────

def id_intro(color_id: str) -> str:
    return (
        f"Halo teman-teman! Hari ini kita belajar warna {color_id}! "
        f"{color_id}! Bisakah kamu bilang {color_id}? Ayo mulai!"
    )


def id_obj_cycle(color_id: str, obj_name: str) -> str:
    return (
        f"Lihat! Ini {obj_name}! "
        f"{obj_name} berwarna {color_id}! "
        f"Apa warna {obj_name}? "
        f"... "
        f"Betul! {color_id}! "
        f"{obj_name} berwarna {color_id}! "
        f"{color_id}! {color_id}! {color_id}! "
        f"Hebat sekali!"
    )


def id_song(color_id: str, obj1: str, obj2: str, obj3: str) -> str:
    return (
        f"{color_id}, {color_id}, semuanya {color_id}! "
        f"{obj1} {color_id}, {obj2} {color_id}, {obj3} {color_id}! "
        f"Bisakah kamu melihat warna {color_id}? "
        f"Aku melihat {color_id}! "
        f"{color_id}, {color_id}, {color_id}! "
        f"Aku suka warna {color_id}!"
    )


def id_outro(color_id: str, obj1: str, obj2: str, obj3: str) -> str:
    return (
        f"Luar biasa! Sekarang kamu tahu warna {color_id}! "
        f"{obj1} {color_id}! {obj2} {color_id}! {obj3} {color_id}! "
        f"Kamu sangat pintar! "
        f"Sampai jumpa lagi! Dadah!"
    )


def id_review(color_id: str, obj1: str, obj2: str, obj3: str) -> str:
    return (
        f"Kerja bagus! Ayo kita ulang! "
        f"Apa warna {obj1}? "
        f"{obj1} berwarna {color_id}! {color_id}! "
        f"Apa warna {obj2}? "
        f"{obj2} berwarna {color_id}! {color_id}! "
        f"Apa warna {obj3}? "
        f"{obj3} berwarna {color_id}! {color_id}! "
        f"Kamu sangat pintar! Bisakah kamu bilang {color_id}? "
        f"{color_id}! {color_id}! {color_id}! "
        f"{obj1} berwarna {color_id}! Bilang bersamaku! {color_id}! "
        f"{obj2} berwarna {color_id}! Bilang bersamaku! {color_id}! "
        f"{obj3} berwarna {color_id}! Bilang bersamaku! {color_id}! "
        f"Luar biasa! Kamu tahu warna {color_id}! "
        f"{color_id}! {color_id}! Ayo bilang sekali lagi! {color_id}! "
        f"Kamu berhasil! Kamu juara warna!"
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


def ar_review(color_ar: str, obj1_ar: str, obj2_ar: str, obj3_ar: str) -> str:
    return (
        f"عمل رائع! هيا نراجع! "
        f"ما لون {obj1_ar}؟ "
        f"{obj1_ar} لونه {color_ar}! {color_ar}! "
        f"ما لون {obj2_ar}؟ "
        f"{obj2_ar} لونه {color_ar}! {color_ar}! "
        f"ما لون {obj3_ar}؟ "
        f"{obj3_ar} لونه {color_ar}! {color_ar}! "
        f"أنت ذكي جداً! هل يمكنك قول {color_ar}؟ "
        f"{color_ar}! {color_ar}! {color_ar}! "
        f"{obj1_ar} لونه {color_ar}! قل معي! {color_ar}! "
        f"{obj2_ar} لونه {color_ar}! قل معي! {color_ar}! "
        f"{obj3_ar} لونه {color_ar}! قل معي! {color_ar}! "
        f"رائع! أنت تعرف اللون {color_ar}! "
        f"{color_ar}! {color_ar}! قلها مرة أخرى! {color_ar}! "
        f"أحسنت! أنت بطل الألوان!"
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

    color_id = color_data.get("name_id", color_en).capitalize()
    obj_id   = [o.get("name_id", o["name_en"]) for o in objs]

    if lang == "en":
        voice  = EN_VOICE
        scripts = {
            "intro":  en_intro(color_en),
            "obj1":   en_obj_cycle(color_en, obj_en[0], article(obj_en[0])),
            "obj2":   en_obj_cycle(color_en, obj_en[1], article(obj_en[1])),
            "obj3":   en_obj_cycle(color_en, obj_en[2], article(obj_en[2])),
            "song":   en_song(color_en, obj_en[0], obj_en[1], obj_en[2]),
            "review": en_review(color_en, obj_en[0], obj_en[1], obj_en[2]),
            "outro":  en_outro(color_en, obj_en[0], obj_en[1], obj_en[2]),
        }
    elif lang == "id":
        voice  = ID_VOICE
        scripts = {
            "intro":  id_intro(color_id),
            "obj1":   id_obj_cycle(color_id, obj_id[0]),
            "obj2":   id_obj_cycle(color_id, obj_id[1]),
            "obj3":   id_obj_cycle(color_id, obj_id[2]),
            "song":   id_song(color_id, obj_id[0], obj_id[1], obj_id[2]),
            "review": id_review(color_id, obj_id[0], obj_id[1], obj_id[2]),
            "outro":  id_outro(color_id, obj_id[0], obj_id[1], obj_id[2]),
        }
    else:
        voice  = AR_VOICE
        scripts = {
            "intro":  ar_intro(color_ar),
            "obj1":   ar_obj_cycle(color_ar, obj_ar[0]),
            "obj2":   ar_obj_cycle(color_ar, obj_ar[1]),
            "obj3":   ar_obj_cycle(color_ar, obj_ar[2]),
            "song":   ar_song(color_ar, obj_ar[0], obj_ar[1], obj_ar[2]),
            "review": ar_review(color_ar, obj_ar[0], obj_ar[1], obj_ar[2]),
            "outro":  ar_outro(color_ar, obj_ar[0], obj_ar[1], obj_ar[2]),
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
    parser.add_argument("--lang",  choices=["en", "ar", "id"], help="Single language")
    parser.add_argument("--force", action="store_true", help="Regenerate existing files")
    args = parser.parse_args()

    colors = load_data()
    if args.color:
        colors = [c for c in colors if c["key"] == args.color]
        if not colors:
            print(f"Color '{args.color}' not found in data.")
            sys.exit(1)

    langs = [args.lang] if args.lang else ["en", "ar", "id"]

    total_ok = total_fail = 0
    for color_data in colors:
        for lang in langs:
            ok, fail = generate_color(color_data, lang, force=args.force)
            total_ok   += ok
            total_fail += fail

    print(f"\nDone: {total_ok} generated, {total_fail} failed")


if __name__ == "__main__":
    main()
