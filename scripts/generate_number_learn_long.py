#!/usr/bin/env python3
"""
Generate "One Concept Deep" number learning videos via Remotion.
One 20-min video per number per language = 20 videos total (1-10 × EN+AR).

Usage:
  python3 scripts/generate_number_learn_long.py --dry-run
  python3 scripts/generate_number_learn_long.py --number three
  python3 scripts/generate_number_learn_long.py --lang en
  python3 scripts/generate_number_learn_long.py            # all 20 videos
  python3 scripts/generate_number_learn_long.py --force
"""
import argparse
import json
import subprocess
import sys
import yaml
from datetime import datetime
from pathlib import Path

ROOT         = Path(__file__).resolve().parent.parent
DATA_PATH    = ROOT / "config" / "number_learn_data.yaml"
QUEUE_DIR    = ROOT / "output" / "queue"
QUEUE_AR_DIR = ROOT / "output" / "queue_ar"
REMOTION     = ROOT / "remotion"

MUSIC_TRACKS = [
    "Pinball Spring.mp3", "Happy Happy Game Show.mp3", "Carefree.mp3",
    "Merry Go.mp3", "Wholesome.mp3", "Life of Riley.mp3",
    "Overworld.mp3", "Quirky Dog.mp3", "Hyperfun.mp3", "Walking Along.mp3",
]

EN_TAGS_BASE = [
    "learn numbers", "counting for kids", "number learning", "preschool", "toddler",
    "one two three", "educational video", "happy bear kids", "kindergarten",
    "count to ten", "number recognition", "math for kids",
]
AR_TAGS_BASE = [
    "تعلم الأرقام", "العد للأطفال", "أرقام للأطفال", "تعليم أطفال", "هابي بير كيدز",
    "رياض الأطفال", "عد من 1 إلى 10", "الرياضيات للأطفال",
]


def load_data() -> list:
    with open(DATA_PATH) as f:
        return yaml.safe_load(f)["numbers"]


def make_props(num: dict, lang: str, music_file: str) -> dict:
    rtl  = (lang == "ar")
    objs = [
        {
            "name":            o["name_en"],
            "nameLocalized":   o["name_ar"] if rtl else o["name_en"].capitalize(),
            "pluralLocalized": o["plural_ar"] if rtl else o["plural_en"].capitalize(),
            "spritePath":      o["sprite"],
        }
        for o in num["objects"]
    ]
    return {
        "numberValue":  num["value"],
        "numberName":   num["name_ar"] if rtl else num["name_en"],
        "numberDigit":  num["digit"],
        "accentColor":  num["accent"],
        "bgColor":      num["bg"],
        "rtl":          rtl,
        "lang":         lang,
        "numberKey":    num["key"],
        "musicFile":    music_file,
        "objects":      objs,
    }


def make_meta(num: dict, lang: str, out_path: Path):
    rtl        = (lang == "ar")
    num_name   = num["name_ar"] if rtl else num["name_en"]
    digit      = num["digit"]
    obj_names  = [o["name_ar"] if rtl else o["name_en"] for o in num["objects"]]
    tags_base  = AR_TAGS_BASE if rtl else EN_TAGS_BASE

    if lang == "en":
        title = (
            f"Learn Number {digit} — {num['name_en'].capitalize()} for Kids! "
            f"20 Minutes | Happy Bear Kids"
        )
        description = (
            f"🔢 Today we learn the number {digit} — {num['name_en'].capitalize()}!\n\n"
            f"This 20-minute video uses the \"One Concept Deep\" method — "
            f"every scene focuses only on {digit}, with 7+ repetitions to build counting memory.\n\n"
            f"We count: {obj_names[0]}, {obj_names[1]}, and {obj_names[2]}!\n\n"
            f"🌟 Educational Benefits:\n"
            f"• One-second pauses between counts — child counts along!\n"
            f"• Objects appear one by one with number badges\n"
            f"• Finger counting activity included\n"
            f"• Positive reinforcement every cycle\n"
            f"• Great background video for play time\n\n"
            f"Part of the complete 1–10 series! Subscribe → @HappyBearKids1\n\n"
            f"🎵 Music: Kevin MacLeod (incompetech.com)\n"
            f"Licensed under Creative Commons Attribution 4.0\n"
            f"http://creativecommons.org/licenses/by/4.0/\n\n"
            f"© Happy Bear Kids 2026"
        )
        tags = tags_base + [digit, num["name_en"].lower(),
                            f"number {digit}", f"count to {digit}"] + obj_names
    else:
        title = f"تعلم الرقم {digit} — {num_name} | 20 دقيقة | هابي بير كيدز"
        description = (
            f"🔢 اليوم نتعلم الرقم {digit} — {num_name}!\n\n"
            f"هذا الفيديو التعليمي يستخدم طريقة \"التعمق في مفهوم واحد\" — "
            f"كل مشهد يركز على {digit} فقط، مع 7+ تكرارات لبناء ذاكرة العد.\n\n"
            f"نعد: {obj_names[0]} و{obj_names[1]} و{obj_names[2]}!\n\n"
            f"🌟 فوائد تعليمية:\n"
            f"• توقفات لمدة ثانية بين الأعداد — الطفل يعد معنا!\n"
            f"• تظهر الأشياء واحداً تلو الآخر مع شارة الرقم\n"
            f"• نشاط العد بالأصابع مضمّن\n"
            f"• تعزيز إيجابي في كل دورة\n"
            f"• رائع كفيديو خلفية أثناء اللعب\n\n"
            f"جزء من سلسلة 1–10 الكاملة! اشتركوا → @HappyBearKids1\n\n"
            f"🎵 الموسيقى: Kevin MacLeod (incompetech.com)\n"
            f"رخصة Creative Commons Attribution 4.0\n"
            f"http://creativecommons.org/licenses/by/4.0/\n\n"
            f"© هابي بير كيدز 2026"
        )
        tags = tags_base + [digit, num_name,
                            f"رقم {digit}", f"العد إلى {digit}"] + obj_names

    meta = {
        "title":       title,
        "description": description,
        "tags":        tags[:40],
        "video_type":  "numbers",
        "theme":       num["key"],
        "language":    lang,
        "status":      "public",
        "is_short":    False,
    }
    meta_path = out_path.parent / f"meta_{out_path.stem}.yaml"
    with open(meta_path, "w") as f:
        yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    print(f"    meta → {meta_path.name}")


def render_video(num: dict, lang: str, force: bool, dry_run: bool) -> bool:
    key      = num["key"]
    date_str = datetime.now().strftime("%Y%m%d")
    fname    = f"number_learn_{key}_{lang}_{date_str}.mp4"
    dest_dir = QUEUE_AR_DIR if lang == "ar" else QUEUE_DIR
    out_path = dest_dir / fname

    if out_path.exists() and not force:
        print(f"  skip {fname} ({out_path.stat().st_size/1024/1024:.1f}MB)")
        return True

    all_nums   = load_data()
    num_idx    = [n["key"] for n in all_nums].index(key)
    music_file = MUSIC_TRACKS[num_idx % len(MUSIC_TRACKS)]
    props      = make_props(num, lang, music_file)
    props_json = json.dumps(props)

    print(f"\n  Rendering: {fname}")
    print(f"    Number: {num['name_en']} / {num['name_ar']} ({num['digit']}) | lang={lang}")
    print(f"    Music: {music_file}")

    if dry_run:
        print(f"    [DRY RUN] {props_json[:100]}...")
        make_meta(num, lang, out_path)
        return True

    dest_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "npx", "remotion", "render",
        "src/index.ts", "NumberLearnLong",
        str(out_path),
        "--props", props_json,
        "--concurrency", "1",
        "--log", "error",
    ]

    print(f"    Running remotion render...")
    result = subprocess.run(
        cmd, cwd=str(REMOTION),
        capture_output=True, text=True,
        timeout=7200,
    )

    if result.returncode == 0 and out_path.exists():
        size_mb = out_path.stat().st_size / 1024 / 1024
        print(f"    ✓ {fname} ({size_mb:.1f}MB)")
        make_meta(num, lang, out_path)
        return True
    else:
        print(f"    ✗ FAILED: {result.stderr[-300:]}")
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--number",  help="Single number key e.g. three")
    parser.add_argument("--lang",    choices=["en", "ar"])
    parser.add_argument("--force",   action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    numbers = load_data()
    if args.number:
        numbers = [n for n in numbers if n["key"] == args.number]
        if not numbers:
            print(f"Number '{args.number}' not found.")
            sys.exit(1)

    langs = [args.lang] if args.lang else ["en", "ar"]
    print(f"\nNumber Learn Long — {len(numbers)} numbers × {len(langs)} languages = {len(numbers)*len(langs)} videos")

    ok = fail = 0
    for num in numbers:
        for lang in langs:
            if render_video(num, lang, args.force, args.dry_run):
                ok += 1
            else:
                fail += 1

    print(f"\nDone: {ok} rendered, {fail} failed")


if __name__ == "__main__":
    main()
