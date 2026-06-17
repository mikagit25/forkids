#!/usr/bin/env python3
"""
Generate voiceover audio for NumberLearnLong via edge-tts.
Conversational style — child cannot read, everything must be spoken.

Sections per number:
  intro   — "Hello! Today we learn TWO! Two! Can you say TWO?"
  review  — "We already know ONE! And now — TWO!" (N=1: extra intro time)
  obj1    — counting scene, conversational, repeated (~40s of speech)
  obj2    — same for object 2
  obj3    — same for object 3
  fingers — "Show me TWO fingers! Hold up TWO fingers! ONE... TWO!"
  song    — number chant, all 3 objects
  outro   — "You can count to TWO! Bye bye!"

Usage:
  python3 scripts/generate_number_learn_audio.py
  python3 scripts/generate_number_learn_audio.py --number one
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
ID_VOICE = "id-ID-GadisNeural"

EN_COUNT = ["one","two","three","four","five","six","seven","eight","nine","ten"]
AR_COUNT = ["واحد","اثنان","ثلاثة","أربعة","خمسة","ستة","سبعة","ثمانية","تسعة","عشرة"]
ID_COUNT = ["satu","dua","tiga","empat","lima","enam","tujuh","delapan","sembilan","sepuluh"]


def load_data() -> list:
    with open(DATA_PATH) as f:
        return yaml.safe_load(f)["numbers"]


# ── EN templates ──────────────────────────────────────────────────────────────

def en_intro(name: str, digit: str) -> str:
    return (
        f"Hello friends! Hello! "
        f"Today we are going to learn the number {digit}! "
        f"{name}! The number {name}! "
        f"Can you say {name}? Say it with me! {name}! {name}! "
        f"Yes! The number {digit}! {name}! "
        f"Let's learn the number {name} together! "
        f"{digit}! {name}! Let's go!"
    )


def en_review(name: str, digit: str, prev_names: list) -> str:
    if not prev_names:
        # N=1 — no previous numbers, use extra intro animation time
        return (
            f"ONE! The number ONE! "
            f"ONE is the very first number! "
            f"Can you say ONE? ONE! ONE! "
            f"ONE! There is only ONE! Just ONE! "
            f"ONE is special! ONE! "
            f"Let's learn everything about ONE! ONE!"
        )
    prev = prev_names[-1]
    all_prev = ", ".join(prev_names[-4:])
    return (
        f"We already know: {all_prev}! "
        f"Good job! We know {prev}! "
        f"And now we learn the next number — {name}! "
        f"{name}! {name} comes after {prev}! "
        f"Can you say {name}? {name}! "
        f"Today is {name}! The number {digit}! Let's go!"
    )


def en_obj(name: str, digit: str, n: int, obj_name: str, obj_plural: str) -> str:
    """Conversational counting scene — fills ~40 seconds of speech."""
    counts = EN_COUNT[:n]
    count_slow = "... ".join(counts)    # "one... two... three"
    count_fast = ", ".join(counts)      # "one, two, three"

    if n == 1:
        return (
            f"Look! A {obj_name}! {obj_name}! "
            f"This is ONE {obj_name}! "
            f"Can you see the {obj_name}? {obj_name}! "
            f"How many {obj_plural}? ONE! Just ONE! "
            f"ONE {obj_name}! Let's count! ONE! "
            f"ONE {obj_name}! {name}! "
            f"Say it with me! ONE! {obj_name.upper()}! "
            f"That's right! ONE {obj_name}! ONE! "
            f"Great job! ONE! ONE {obj_name}! "
            f"ONE! You are so smart! ONE {obj_name}!"
        )
    else:
        return (
            f"Look! {obj_plural.capitalize()}! "
            f"Let's count {obj_plural} together! Ready? "
            f"{count_slow}! "
            f"{name}! {digit} {obj_plural}! "
            f"How many {obj_plural}? {name}! {digit}! "
            f"Can you count with me? "
            f"{count_slow}! "
            f"{name} {obj_plural}! Wonderful! "
            f"Let's count one more time! "
            f"{count_fast}! "
            f"{name}! {digit} {obj_plural}! "
            f"You did it! {name}! {name} {obj_plural}! "
            f"Amazing counting! {name}!"
        )


def en_fingers(name: str, digit: str, n: int) -> str:
    counts = EN_COUNT[:n]
    count_slow = "... ".join(counts)
    fw = "finger" if n == 1 else "fingers"
    if n == 1:
        return (
            f"Now let's use our fingers! "
            f"Show me ONE finger! Hold up ONE finger! "
            f"ONE! Can you do it? ONE finger! "
            f"Look — ONE finger! ONE! "
            f"Show me your finger! ONE! "
            f"ONE finger! That's right! ONE! "
            f"Great job! ONE finger! ONE!"
        )
    else:
        return (
            f"Now let's use our fingers! "
            f"Show me {digit} {fw}! "
            f"Let's count our {fw} together! "
            f"{count_slow}! "
            f"{digit} {fw}! {name}! "
            f"Can you do it? Hold up {digit} {fw}! "
            f"{count_slow}! "
            f"{name} {fw}! Look at you! "
            f"{digit} {fw}! {name}! You are so clever!"
        )


def en_song(name: str, digit: str, n: int, obj1: str, obj2: str, obj3: str) -> str:
    counts = EN_COUNT[:n]
    count_fast = ", ".join(counts)
    return (
        f"{name}! {name}! The number {name}! "
        f"Everything comes in {name}! "
        f"{digit} {obj1}! {digit} {obj2}! {digit} {obj3}! "
        f"Count with me! {count_fast}! "
        f"{name}! {name}! I love the number {digit}! "
        f"{count_fast}! "
        f"{name} {obj1}! {name} {obj2}! {name} {obj3}! "
        f"Count! {count_fast}! "
        f"{name}! The number {name}! {name}!"
    )


def en_outro(name: str, digit: str, n: int, obj1: str, obj2: str, obj3: str) -> str:
    counts = EN_COUNT[:n]
    count_slow = "... ".join(counts)
    return (
        f"Amazing job today! You learned the number {digit}! "
        f"{name}! The number {name}! "
        f"Let's count one last time! {count_slow}! "
        f"{name}! "
        f"{digit} {obj1}! {digit} {obj2}! {digit} {obj3}! "
        f"You are a wonderful counter! "
        f"The number {digit}! {name}! "
        f"See you next time! Bye bye! {name}!"
    )


# ── AR templates ──────────────────────────────────────────────────────────────

def ar_intro(name: str, digit: str) -> str:
    return (
        f"مرحباً أصدقاء! مرحباً! "
        f"اليوم سنتعلم الرقم {digit}! "
        f"{name}! الرقم {name}! "
        f"هل يمكنك قول {name}؟ قل معي! {name}! {name}! "
        f"نعم! الرقم {digit}! {name}! "
        f"هيا نتعلم الرقم {name} معاً! "
        f"{digit}! {name}! هيا بنا!"
    )


def ar_review(name: str, digit: str, prev_names: list) -> str:
    if not prev_names:
        return (
            f"واحد! الرقم واحد! "
            f"واحد هو أول رقم! "
            f"هل يمكنك قول واحد؟ واحد! واحد! "
            f"واحد! هناك واحد فقط! "
            f"واحد مميز! واحد! "
            f"هيا نتعلم كل شيء عن واحد! واحد!"
        )
    prev = prev_names[-1]
    all_prev = " و".join(prev_names[-4:])
    return (
        f"نعرف بالفعل: {all_prev}! "
        f"أحسنت! نعرف {prev}! "
        f"والآن نتعلم الرقم التالي — {name}! "
        f"{name}! {name} يأتي بعد {prev}! "
        f"هل يمكنك قول {name}؟ {name}! "
        f"اليوم هو {name}! الرقم {digit}! هيا بنا!"
    )


def ar_obj(name: str, digit: str, n: int, obj_name: str, obj_plural: str) -> str:
    counts = AR_COUNT[:n]
    count_slow = "... ".join(counts)
    count_fast = ", ".join(counts)
    if n == 1:
        return (
            f"انظر! {obj_name}! {obj_name}! "
            f"هذه {obj_name} واحدة! "
            f"هل يمكنك رؤية {obj_name}؟ {obj_name}! "
            f"كم {obj_plural}؟ واحد! واحد فقط! "
            f"{obj_name} واحدة! هيا نعد! واحد! "
            f"واحد {obj_name}! {name}! "
            f"قل معي! واحد! {obj_name}! "
            f"صحيح! واحد {obj_name}! واحد! "
            f"أحسنت! واحد! واحد {obj_name}! "
            f"واحد! أنت رائع! واحد {obj_name}!"
        )
    else:
        return (
            f"انظر! {obj_plural}! "
            f"هيا نعد {obj_plural} معاً! مستعد؟ "
            f"{count_slow}! "
            f"{name}! {digit} {obj_plural}! "
            f"كم {obj_plural}؟ {name}! {digit}! "
            f"هل يمكنك العد معي؟ "
            f"{count_slow}! "
            f"{name} {obj_plural}! رائع! "
            f"هيا نعد مرة أخرى! "
            f"{count_fast}! "
            f"{name}! {digit} {obj_plural}! "
            f"فعلتها! {name}! {name} {obj_plural}! "
            f"عد رائع! {name}!"
        )


def ar_fingers(name: str, digit: str, n: int) -> str:
    counts = AR_COUNT[:n]
    count_slow = "... ".join(counts)
    fw = "إصبع" if n == 1 else "أصابع"
    if n == 1:
        return (
            f"الآن هيا نستخدم أصابعنا! "
            f"أرني إصبعاً واحداً! ارفع إصبعاً واحداً! "
            f"واحد! هل يمكنك فعل ذلك؟ إصبع واحد! "
            f"انظر — إصبع واحد! واحد! "
            f"أرني إصبعك! واحد! "
            f"إصبع واحد! صحيح! واحد! "
            f"أحسنت! إصبع واحد! واحد!"
        )
    else:
        return (
            f"الآن هيا نستخدم أصابعنا! "
            f"أرني {digit} {fw}! "
            f"هيا نعد {fw} معاً! "
            f"{count_slow}! "
            f"{digit} {fw}! {name}! "
            f"هل يمكنك فعل ذلك؟ ارفع {digit} {fw}! "
            f"{count_slow}! "
            f"{name} {fw}! انظر إليك! "
            f"{digit} {fw}! {name}! أنت ذكي جداً!"
        )


def ar_song(name: str, digit: str, n: int, obj1: str, obj2: str, obj3: str) -> str:
    counts = AR_COUNT[:n]
    count_fast = ", ".join(counts)
    return (
        f"{name}! {name}! الرقم {name}! "
        f"كل شيء يأتي في {name}! "
        f"{digit} {obj1}! {digit} {obj2}! {digit} {obj3}! "
        f"عد معي! {count_fast}! "
        f"{name}! {name}! أحب الرقم {digit}! "
        f"{count_fast}! "
        f"{name} {obj1}! {name} {obj2}! {name} {obj3}! "
        f"عد! {count_fast}! "
        f"{name}! الرقم {name}! {name}!"
    )


def ar_outro(name: str, digit: str, n: int, obj1: str, obj2: str, obj3: str) -> str:
    counts = AR_COUNT[:n]
    count_slow = "... ".join(counts)
    return (
        f"عمل رائع اليوم! تعلمت الرقم {digit}! "
        f"{name}! الرقم {name}! "
        f"هيا نعد مرة أخيرة! {count_slow}! "
        f"{name}! "
        f"{digit} {obj1}! {digit} {obj2}! {digit} {obj3}! "
        f"أنت عداد رائع! "
        f"الرقم {digit}! {name}! "
        f"أراكم في المرة القادمة! مع السلامة! {name}!"
    )


# ── ID templates ──────────────────────────────────────────────────────────────

def id_intro(name: str, digit: str) -> str:
    return (
        f"Halo teman-teman! Halo! "
        f"Hari ini kita akan belajar angka {digit}! "
        f"{name}! Angka {name}! "
        f"Bisakah kamu bilang {name}? Bilang bersamaku! {name}! {name}! "
        f"Ya! Angka {digit}! {name}! "
        f"Ayo belajar angka {name} bersama! "
        f"{digit}! {name}! Ayo!"
    )


def id_review(name: str, digit: str, prev_names: list) -> str:
    if not prev_names:
        return (
            f"Satu! Angka satu! "
            f"Satu adalah angka pertama! "
            f"Bisakah kamu bilang satu? Satu! Satu! "
            f"Satu! Hanya ada satu! "
            f"Satu itu istimewa! Satu! "
            f"Ayo belajar semua tentang satu! Satu!"
        )
    prev = prev_names[-1]
    all_prev = ", ".join(prev_names[-4:])
    return (
        f"Kita sudah tahu: {all_prev}! "
        f"Bagus! Kita tahu {prev}! "
        f"Dan sekarang kita belajar angka berikutnya — {name}! "
        f"{name}! {name} datang setelah {prev}! "
        f"Bisakah kamu bilang {name}? {name}! "
        f"Hari ini adalah {name}! Angka {digit}! Ayo!"
    )


def id_obj(name: str, digit: str, n: int, obj_name: str, obj_plural: str) -> str:
    counts = ID_COUNT[:n]
    count_slow = "... ".join(counts)
    count_fast = ", ".join(counts)
    if n == 1:
        return (
            f"Lihat! {obj_name.capitalize()}! {obj_name.capitalize()}! "
            f"Ini SATU {obj_name}! "
            f"Bisakah kamu melihat {obj_name}? {obj_name.capitalize()}! "
            f"Ada berapa {obj_plural}? Satu! Hanya satu! "
            f"Satu {obj_name}! Ayo hitung! Satu! "
            f"Satu {obj_name}! {name}! "
            f"Bilang bersamaku! Satu! {obj_name.upper()}! "
            f"Benar! Satu {obj_name}! Satu! "
            f"Bagus sekali! Satu! Satu {obj_name}! "
            f"Satu! Kamu hebat! Satu {obj_name}!"
        )
    else:
        return (
            f"Lihat! {obj_plural.capitalize()}! "
            f"Ayo hitung {obj_plural} bersama! Siap? "
            f"{count_slow}! "
            f"{name}! {digit} {obj_plural}! "
            f"Ada berapa {obj_plural}? {name}! {digit}! "
            f"Bisakah kamu hitung bersamaku? "
            f"{count_slow}! "
            f"{name} {obj_plural}! Luar biasa! "
            f"Ayo hitung sekali lagi! "
            f"{count_fast}! "
            f"{name}! {digit} {obj_plural}! "
            f"Kamu berhasil! {name}! {name} {obj_plural}! "
            f"Hitungan yang bagus! {name}!"
        )


def id_fingers(name: str, digit: str, n: int) -> str:
    counts = ID_COUNT[:n]
    count_slow = "... ".join(counts)
    fw = "jari" if n == 1 else "jari"
    if n == 1:
        return (
            f"Sekarang ayo gunakan jari kita! "
            f"Tunjukkan SATU jari! Angkat satu jari! "
            f"Satu! Bisakah kamu melakukannya? Satu jari! "
            f"Lihat — satu jari! Satu! "
            f"Tunjukkan jarimu! Satu! "
            f"Satu jari! Betul! Satu! "
            f"Kerja bagus! Satu jari! Satu!"
        )
    else:
        return (
            f"Sekarang ayo gunakan jari kita! "
            f"Tunjukkan {digit} {fw}! "
            f"Ayo hitung {fw} bersama! "
            f"{count_slow}! "
            f"{digit} {fw}! {name}! "
            f"Bisakah kamu melakukannya? Angkat {digit} {fw}! "
            f"{count_slow}! "
            f"{name} {fw}! Lihat kamu! "
            f"{digit} {fw}! {name}! Kamu sangat pintar!"
        )


def id_song(name: str, digit: str, n: int, obj1: str, obj2: str, obj3: str) -> str:
    counts = ID_COUNT[:n]
    count_fast = ", ".join(counts)
    return (
        f"{name}! {name}! Angka {name}! "
        f"Semuanya ada {name}! "
        f"{digit} {obj1}! {digit} {obj2}! {digit} {obj3}! "
        f"Hitung bersamaku! {count_fast}! "
        f"{name}! {name}! Aku suka angka {digit}! "
        f"{count_fast}! "
        f"{name} {obj1}! {name} {obj2}! {name} {obj3}! "
        f"Hitung! {count_fast}! "
        f"{name}! Angka {name}! {name}!"
    )


def id_outro(name: str, digit: str, n: int, obj1: str, obj2: str, obj3: str) -> str:
    counts = ID_COUNT[:n]
    count_slow = "... ".join(counts)
    return (
        f"Kerja bagus hari ini! Kamu belajar angka {digit}! "
        f"{name}! Angka {name}! "
        f"Ayo hitung sekali terakhir! {count_slow}! "
        f"{name}! "
        f"{digit} {obj1}! {digit} {obj2}! {digit} {obj3}! "
        f"Kamu penghitung yang luar biasa! "
        f"Angka {digit}! {name}! "
        f"Sampai jumpa lagi! Dadah! {name}!"
    )


# ── TTS helper ────────────────────────────────────────────────────────────────

def tts(text: str, voice: str, out_path: Path, force: bool) -> bool:
    if out_path.exists() and not force:
        print(f"    skip {out_path.name}")
        return True
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # edge-tts speaks "..." as ellipsis pause naturally
    cmd = ["edge-tts", "--voice", voice, "--text", text, "--write-media", str(out_path)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0 and out_path.exists():
        kb = out_path.stat().st_size // 1024
        print(f"    ✓ {out_path.name}  ({kb}KB)")
        return True
    print(f"    ✗ FAILED {out_path.name}: {r.stderr[:100]}")
    return False


def generate_number(num_data: dict, all_numbers: list, lang: str, force: bool):
    key   = num_data["key"]
    n     = num_data["value"]
    digit = num_data["digit"]
    objs  = num_data["objects"]
    out   = OUT_DIR / lang
    out.mkdir(parents=True, exist_ok=True)

    prev_idx  = [d["key"] for d in all_numbers].index(key)
    prev_en   = [d["name_en"] for d in all_numbers[:prev_idx]]
    prev_ar   = [d["name_ar"] for d in all_numbers[:prev_idx]]
    prev_id   = [d.get("name_id", d["name_en"]).capitalize() for d in all_numbers[:prev_idx]]

    name_id = num_data.get("name_id", num_data["name_en"]).capitalize()

    print(f"\n  [{lang.upper()}] {key.upper()}: {num_data['name_en']} / {num_data['name_ar']} / {name_id}")

    if lang == "en":
        voice = EN_VOICE
        name  = num_data["name_en"]
        scripts = {
            "intro":   en_intro(name, digit),
            "review":  en_review(name, digit, prev_en),
            "obj1":    en_obj(name, digit, n, objs[0]["name_en"], objs[0]["plural_en"]),
            "obj2":    en_obj(name, digit, n, objs[1]["name_en"], objs[1]["plural_en"]),
            "obj3":    en_obj(name, digit, n, objs[2]["name_en"], objs[2]["plural_en"]),
            "fingers": en_fingers(name, digit, n),
            "song":    en_song(name, digit, n,
                               objs[0]["plural_en"], objs[1]["plural_en"], objs[2]["plural_en"]),
            "outro":   en_outro(name, digit, n,
                                objs[0]["plural_en"], objs[1]["plural_en"], objs[2]["plural_en"]),
        }
    elif lang == "id":
        voice = ID_VOICE
        name  = name_id
        scripts = {
            "intro":   id_intro(name, digit),
            "review":  id_review(name, digit, prev_id),
            "obj1":    id_obj(name, digit, n,
                              objs[0].get("name_id", objs[0]["name_en"]),
                              objs[0].get("plural_id", objs[0]["name_en"])),
            "obj2":    id_obj(name, digit, n,
                              objs[1].get("name_id", objs[1]["name_en"]),
                              objs[1].get("plural_id", objs[1]["name_en"])),
            "obj3":    id_obj(name, digit, n,
                              objs[2].get("name_id", objs[2]["name_en"]),
                              objs[2].get("plural_id", objs[2]["name_en"])),
            "fingers": id_fingers(name, digit, n),
            "song":    id_song(name, digit, n,
                               objs[0].get("plural_id", objs[0]["name_en"]),
                               objs[1].get("plural_id", objs[1]["name_en"]),
                               objs[2].get("plural_id", objs[2]["name_en"])),
            "outro":   id_outro(name, digit, n,
                                objs[0].get("plural_id", objs[0]["name_en"]),
                                objs[1].get("plural_id", objs[1]["name_en"]),
                                objs[2].get("plural_id", objs[2]["name_en"])),
        }
    else:  # ar
        voice = AR_VOICE
        name  = num_data["name_ar"]
        scripts = {
            "intro":   ar_intro(name, digit),
            "review":  ar_review(name, digit, prev_ar),
            "obj1":    ar_obj(name, digit, n, objs[0]["name_ar"], objs[0]["plural_ar"]),
            "obj2":    ar_obj(name, digit, n, objs[1]["name_ar"], objs[1]["plural_ar"]),
            "obj3":    ar_obj(name, digit, n, objs[2]["name_ar"], objs[2]["plural_ar"]),
            "fingers": ar_fingers(name, digit, n),
            "song":    ar_song(name, digit, n,
                               objs[0]["plural_ar"], objs[1]["plural_ar"], objs[2]["plural_ar"]),
            "outro":   ar_outro(name, digit, n,
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
    parser.add_argument("--number", help="Single number key e.g. one, two, three")
    parser.add_argument("--lang",   choices=["en", "ar", "id"])
    parser.add_argument("--force",  action="store_true", help="Overwrite existing files")
    args = parser.parse_args()

    all_numbers = load_data()
    numbers = [n for n in all_numbers if not args.number or n["key"] == args.number]
    if args.number and not numbers:
        print(f"Number '{args.number}' not found.")
        sys.exit(1)

    langs = [args.lang] if args.lang else ["en", "ar", "id"]
    ok = fail = 0
    for num in numbers:
        for lang in langs:
            o, f = generate_number(num, all_numbers, lang, args.force)
            ok += o; fail += f

    print(f"\nDone: {ok} generated, {fail} failed")


if __name__ == "__main__":
    main()
