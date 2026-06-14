#!/usr/bin/env python3
"""
Generate voiceover audio for NumberLearnLong via edge-tts.

Sections per number:
  intro  — "Today we learn the number THREE!"
  obj1   — counting scene for object 1 (incl. review of prev numbers)
  obj2   — counting scene for object 2
  obj3   — counting scene for object 3
  song   — number chant
  outro  — "You can count to THREE! Bye!"

Usage:
  python3 scripts/generate_number_learn_audio.py
  python3 scripts/generate_number_learn_audio.py --number three
  python3 scripts/generate_number_learn_audio.py --lang ar
  python3 scripts/generate_number_learn_audio.py --force
"""
import argparse
import subprocess
import sys
import yaml
from pathlib import Path

ROOT      = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "config" / "number_learn_data.yaml"
OUT_DIR   = ROOT / "remotion" / "public" / "audio" / "number_learn"

EN_VOICE = "en-US-JennyNeural"
AR_VOICE = "ar-SA-ZariyahNeural"

EN_COUNT = ["one","two","three","four","five","six","seven","eight","nine","ten"]
AR_COUNT = ["واحد","اثنان","ثلاثة","أربعة","خمسة","ستة","سبعة","ثمانية","تسعة","عشرة"]


def load_data() -> list:
    with open(DATA_PATH) as f:
        return yaml.safe_load(f)["numbers"]


def counting_en(n: int) -> str:
    """Spoken counting sequence: 'one... two... three...'"""
    return ". . . ".join(EN_COUNT[:n]) + "!"


def counting_ar(n: int) -> str:
    return ". . . ".join(AR_COUNT[:n]) + "!"


# ── EN templates ──────────────────────────────────────────────────────────────

def en_intro(name: str, digit: str, prev_names: list[str]) -> str:
    review = ""
    if prev_names:
        review = f"We already know: {', '.join(prev_names)}. And now, "
    return (
        f"Hello friends! {review}Today we learn the number {name}! "
        f"{digit}! {name}! Can you say {name}? Let's count to {digit}!"
    )


def en_obj(name: str, digit: str, n: int,
           obj_name: str, obj_plural: str, intro: bool = False) -> str:
    count_seq = counting_en(n)
    extra = f"Can you count with me? " if intro else ""
    return (
        f"How many {obj_plural}? {extra}Count with me! "
        f"{count_seq} "
        f"{name}! {digit} {obj_plural}! "
        f"Great counting! You counted to {digit}!"
    )


def en_song(name: str, digit: str, n: int,
            obj1: str, obj2: str, obj3: str) -> str:
    count_seq = counting_en(n)
    return (
        f"{name}! {name}! Everything comes in {name}! "
        f"{digit} {obj1}! {digit} {obj2}! {digit} {obj3}! "
        f"Count with me! {count_seq} "
        f"{name}! I love the number {digit}!"
    )


def en_outro(name: str, digit: str, n: int,
             obj1: str, obj2: str, obj3: str) -> str:
    count_seq = counting_en(n)
    return (
        f"Amazing job! You can count to {digit}! "
        f"{count_seq} "
        f"{name} {obj1}! {name} {obj2}! {name} {obj3}! "
        f"You are a counting champion! "
        f"See you next time! Bye bye!"
    )


# ── AR templates ──────────────────────────────────────────────────────────────

def ar_intro(name_ar: str, digit: str, prev_names_ar: list[str]) -> str:
    review = ""
    if prev_names_ar:
        review = f"نعرف بالفعل: {' و'.join(prev_names_ar)}. والآن، "
    return (
        f"مرحباً أصدقاء! {review}اليوم نتعلم الرقم {name_ar}! "
        f"{digit}! {name_ar}! هل يمكنك قول {name_ar}؟ هيا نعد إلى {digit}!"
    )


def ar_obj(name_ar: str, digit: str, n: int,
           obj_ar: str, obj_plural_ar: str, intro: bool = False) -> str:
    count_seq = counting_ar(n)
    extra = "عد معي! " if intro else ""
    return (
        f"كم {obj_ar} لدينا؟ {extra}عد معي! "
        f"{count_seq} "
        f"{name_ar}! {digit} {obj_plural_ar}! "
        f"أحسنت! لقد عددت إلى {digit}!"
    )


def ar_song(name_ar: str, digit: str, n: int,
            obj1_ar: str, obj2_ar: str, obj3_ar: str) -> str:
    count_seq = counting_ar(n)
    return (
        f"{name_ar}! {name_ar}! كل شيء في {name_ar}! "
        f"{digit} {obj1_ar}! {digit} {obj2_ar}! {digit} {obj3_ar}! "
        f"عد معي! {count_seq} "
        f"{name_ar}! أحب الرقم {digit}!"
    )


def ar_outro(name_ar: str, digit: str, n: int,
             obj1_ar: str, obj2_ar: str, obj3_ar: str) -> str:
    count_seq = counting_ar(n)
    return (
        f"عمل رائع! يمكنك العد إلى {digit}! "
        f"{count_seq} "
        f"{name_ar} {obj1_ar}! {name_ar} {obj2_ar}! {name_ar} {obj3_ar}! "
        f"أنت بطل العد! "
        f"إلى اللقاء! مع السلامة!"
    )


# ── TTS helper ────────────────────────────────────────────────────────────────

def tts(text: str, voice: str, out_path: Path, force: bool) -> bool:
    if out_path.exists() and not force:
        print(f"    skip {out_path.name}")
        return True
    out_path.parent.mkdir(parents=True, exist_ok=True)
    clean = text.replace("...", ". . .")
    cmd = ["edge-tts", "--voice", voice, "--text", clean, "--write-media", str(out_path)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0 and out_path.exists():
        print(f"    ✓ {out_path.name}  ({out_path.stat().st_size//1024}KB)")
        return True
    print(f"    ✗ FAILED {out_path.name}: {r.stderr[:80]}")
    return False


def generate_number(num_data: dict, all_numbers: list, lang: str, force: bool):
    key  = num_data["key"]
    n    = num_data["value"]
    objs = num_data["objects"]
    out  = OUT_DIR / lang
    out.mkdir(parents=True, exist_ok=True)

    # Previous number names for review
    prev_idx  = [d["key"] for d in all_numbers].index(key)
    prev_en   = [d["name_en"] for d in all_numbers[:prev_idx]]
    prev_ar   = [d["name_ar"] for d in all_numbers[:prev_idx]]

    print(f"\n  [{lang.upper()}] {key.upper()} = {num_data['name_en']} / {num_data['name_ar']}")

    if lang == "en":
        voice = EN_VOICE
        scripts = {
            "intro": en_intro(num_data["name_en"], num_data["digit"], prev_en[-3:]),
            "obj1":  en_obj(num_data["name_en"], num_data["digit"], n,
                            objs[0]["name_en"], objs[0]["plural_en"], intro=True),
            "obj2":  en_obj(num_data["name_en"], num_data["digit"], n,
                            objs[1]["name_en"], objs[1]["plural_en"]),
            "obj3":  en_obj(num_data["name_en"], num_data["digit"], n,
                            objs[2]["name_en"], objs[2]["plural_en"]),
            "song":  en_song(num_data["name_en"], num_data["digit"], n,
                             objs[0]["plural_en"], objs[1]["plural_en"], objs[2]["plural_en"]),
            "outro": en_outro(num_data["name_en"], num_data["digit"], n,
                              objs[0]["plural_en"], objs[1]["plural_en"], objs[2]["plural_en"]),
        }
    else:
        voice = AR_VOICE
        scripts = {
            "intro": ar_intro(num_data["name_ar"], num_data["digit"], prev_ar[-3:]),
            "obj1":  ar_obj(num_data["name_ar"], num_data["digit"], n,
                            objs[0]["name_ar"], objs[0]["plural_ar"], intro=True),
            "obj2":  ar_obj(num_data["name_ar"], num_data["digit"], n,
                            objs[1]["name_ar"], objs[1]["plural_ar"]),
            "obj3":  ar_obj(num_data["name_ar"], num_data["digit"], n,
                            objs[2]["name_ar"], objs[2]["plural_ar"]),
            "song":  ar_song(num_data["name_ar"], num_data["digit"], n,
                             objs[0]["plural_ar"], objs[1]["plural_ar"], objs[2]["plural_ar"]),
            "outro": ar_outro(num_data["name_ar"], num_data["digit"], n,
                              objs[0]["plural_ar"], objs[1]["plural_ar"], objs[2]["plural_ar"]),
        }

    ok = fail = 0
    for section, text in scripts.items():
        p = out / f"{key}_{section}.mp3"
        if tts(text, voice, p, force):
            ok += 1
        else:
            fail += 1
    return ok, fail


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--number", help="Single number key e.g. three")
    parser.add_argument("--lang",   choices=["en", "ar"])
    parser.add_argument("--force",  action="store_true")
    args = parser.parse_args()

    all_numbers = load_data()
    numbers = [n for n in all_numbers if not args.number or n["key"] == args.number]
    if args.number and not numbers:
        print(f"Number '{args.number}' not found.")
        sys.exit(1)

    langs = [args.lang] if args.lang else ["en", "ar"]
    ok = fail = 0
    for num in numbers:
        for lang in langs:
            o, f = generate_number(num, all_numbers, lang, args.force)
            ok += o; fail += f

    print(f"\nDone: {ok} generated, {fail} failed")


if __name__ == "__main__":
    main()
