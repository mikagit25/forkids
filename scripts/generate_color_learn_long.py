#!/usr/bin/env python3
"""
Generate "One Concept Deep" color learning videos via Remotion.
One 20-min video per color per language = 18 videos total.

Usage:
  python3 scripts/generate_color_learn_long.py --dry-run
  python3 scripts/generate_color_learn_long.py --color red
  python3 scripts/generate_color_learn_long.py --lang en
  python3 scripts/generate_color_learn_long.py           # all 18 videos
  python3 scripts/generate_color_learn_long.py --force   # re-render existing
"""
import argparse
import json
import subprocess
import sys
import yaml
from datetime import datetime
from pathlib import Path

ROOT         = Path(__file__).resolve().parent.parent
DATA_PATH    = ROOT / "config" / "color_learn_data.yaml"
QUEUE_DIR    = ROOT / "output" / "queue"
QUEUE_AR_DIR = ROOT / "output" / "queue_ar"
REMOTION     = ROOT / "remotion"

MUSIC_TRACKS = [
    "Happy Happy Game Show.mp3",
    "Carefree.mp3",
    "Pinball Spring.mp3",
    "Merry Go.mp3",
    "Wholesome.mp3",
    "Life of Riley.mp3",
    "Overworld.mp3",
    "Quirky Dog.mp3",
    "Hyperfun.mp3",
]

EN_TAGS_BASE = [
    "learn colors", "colors for kids", "color learning", "preschool", "toddler",
    "educational video", "happy bear kids", "one color deep", "kindergarten",
    "kids learning", "color recognition",
]
AR_TAGS_BASE = [
    "تعلم الألوان", "ألوان للأطفال", "تعليم أطفال", "رياض الأطفال", "هابي بير كيدز",
    "تعليمي", "تعلم الألوان بالعربية",
]


def load_data() -> list:
    with open(DATA_PATH) as f:
        return yaml.safe_load(f)["colors"]


def make_props(color: dict, lang: str, music_file: str) -> dict:
    rtl     = (lang == "ar")
    objects = [
        {
            "name":          obj["name_en"],
            "nameLocalized": obj["name_ar"] if rtl else obj["name_en"].capitalize(),
            "spritePath":    obj["sprite"],
        }
        for obj in color["objects"]
    ]
    return {
        "colorName": color["name_ar"] if rtl else color["name_en"],
        "colorHex":  color["hex"],
        "bgColor":   color["bg"],
        "rtl":       rtl,
        "lang":      lang,
        "colorKey":  color["key"],
        "musicFile": music_file,
        "objects":   objects,
    }


def make_meta(color: dict, lang: str, out_path: Path):
    rtl        = (lang == "ar")
    color_name = color["name_ar"] if rtl else color["name_en"]
    obj_names  = [o["name_ar"] if rtl else o["name_en"] for o in color["objects"]]
    tags_base  = AR_TAGS_BASE if rtl else EN_TAGS_BASE

    if lang == "en":
        title = (
            f"Learn the Color {color['name_en'].capitalize()} for Kids! "
            f"20 Minutes | Happy Bear Kids"
        )
        description = (
            f"🎨 Today we learn the color {color['name_en'].lower()}!\n\n"
            f"This 20-minute video uses the \"One Concept Deep\" method — "
            f"7-9 repetitions of one color to build lasting memory in toddlers.\n\n"
            f"We explore: {obj_names[0]}, {obj_names[1]}, and {obj_names[2]}!\n\n"
            f"Perfect for ages 1–4. Simple questions with 4-second think time "
            f"let your child answer before we reveal!\n\n"
            f"🌟 Educational Benefits:\n"
            f"• Long-term color memory through repetition\n"
            f"• Interactive dialogue — child participates!\n"
            f"• Positive reinforcement on every answer\n"
            f"• Great background video for play time\n\n"
            f"Subscribe for all 9 colors! → @HappyBearKids1\n\n"
            f"🎵 Music: Kevin MacLeod (incompetech.com)\n"
            f"Licensed under Creative Commons Attribution 4.0\n"
            f"http://creativecommons.org/licenses/by/4.0/\n\n"
            f"© Happy Bear Kids 2026"
        )
        tags = tags_base + [color["name_en"].lower(), f"learn {color['name_en'].lower()}"] + obj_names
    else:
        title = (
            f"تعلم اللون {color_name} | 20 دقيقة | هابي بير كيدز"
        )
        description = (
            f"🎨 اليوم نتعلم اللون {color_name}!\n\n"
            f"هذا الفيديو التعليمي يستخدم طريقة \"التعمق في مفهوم واحد\" — "
            f"7-9 تكرارات للون الواحد لبناء ذاكرة دائمة عند الأطفال.\n\n"
            f"نستكشف: {obj_names[0]} و{obj_names[1]} و{obj_names[2]}!\n\n"
            f"مثالي للأعمار 1–4 سنوات. أسئلة بسيطة مع وقت تفكير 4 ثوان "
            f"تتيح لطفلك الإجابة قبل الكشف!\n\n"
            f"🌟 فوائد تعليمية:\n"
            f"• ذاكرة طويلة الأمد للألوان عبر التكرار\n"
            f"• حوار تفاعلي — يشارك الطفل!\n"
            f"• تعزيز إيجابي مع كل إجابة\n"
            f"• رائع كفيديو خلفية أثناء اللعب\n\n"
            f"اشتركوا لمتابعة جميع الألوان التسعة! → @HappyBearKids1\n\n"
            f"🎵 الموسيقى: Kevin MacLeod (incompetech.com)\n"
            f"رخصة Creative Commons Attribution 4.0\n"
            f"http://creativecommons.org/licenses/by/4.0/\n\n"
            f"© هابي بير كيدز 2026"
        )
        tags = tags_base + [color_name] + obj_names

    meta = {
        "title":       title,
        "description": description,
        "tags":        tags[:40],
        "video_type":  "colors",
        "theme":       color["key"],
        "language":    lang,
        "status":      "public",
        "is_short":    False,
    }
    meta_path = out_path.parent / f"meta_{out_path.stem}.yaml"
    with open(meta_path, "w") as f:
        yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    print(f"    meta → {meta_path.name}")


def render_video(color: dict, lang: str, force: bool = False, dry_run: bool = False) -> bool:
    key      = color["key"]
    date_str = datetime.now().strftime("%Y%m%d")
    fname    = f"color_learn_{key}_{lang}_{date_str}.mp4"
    # AR videos go to queue_ar/ so cron publishes them on the AR schedule
    dest_dir = QUEUE_AR_DIR if lang == "ar" else QUEUE_DIR
    out_path = dest_dir / fname

    if out_path.exists() and not force:
        size_mb = out_path.stat().st_size / 1024 / 1024
        print(f"  skip {fname} ({size_mb:.1f}MB)")
        return True

    # Pick music track
    color_idx   = [c["key"] for c in load_data()].index(key)
    music_file  = MUSIC_TRACKS[color_idx % len(MUSIC_TRACKS)]

    props       = make_props(color, lang, music_file)
    props_json  = json.dumps(props)

    print(f"\n  Rendering: {fname}")
    print(f"    Color: {color['name_en']} / {color['name_ar']} | lang={lang}")
    print(f"    Music: {music_file}")

    if dry_run:
        print(f"    [DRY RUN] props: {props_json[:120]}...")
        make_meta(color, lang, out_path)
        return True

    dest_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "npx", "remotion", "render",
        "src/index.ts", "ColorLearnLong",
        str(out_path),
        "--props", props_json,
        "--concurrency", "1",
        "--log", "error",
    ]

    print(f"    Running remotion render...")
    result = subprocess.run(
        cmd, cwd=str(REMOTION),
        capture_output=True, text=True,
        timeout=7200,  # 2h max per video
    )

    if result.returncode == 0 and out_path.exists():
        size_mb = out_path.stat().st_size / 1024 / 1024
        print(f"    ✓ {fname} ({size_mb:.1f}MB)")
        make_meta(color, lang, out_path)
        return True
    else:
        print(f"    ✗ FAILED: {result.stderr[-300:]}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Generate color learn long videos")
    parser.add_argument("--color",   help="Single color key (e.g. red)")
    parser.add_argument("--lang",    choices=["en", "ar"], help="Single language")
    parser.add_argument("--force",   action="store_true", help="Re-render existing")
    parser.add_argument("--dry-run", action="store_true", help="Show what would render")
    args = parser.parse_args()

    colors = load_data()
    if args.color:
        colors = [c for c in colors if c["key"] == args.color]
        if not colors:
            print(f"Color '{args.color}' not found.")
            sys.exit(1)

    langs = [args.lang] if args.lang else ["en", "ar"]

    print(f"\nColor Learn Long — {len(colors)} colors × {len(langs)} languages = {len(colors)*len(langs)} videos")

    ok = fail = 0
    for color in colors:
        for lang in langs:
            success = render_video(color, lang, force=args.force, dry_run=args.dry_run)
            if success:
                ok += 1
            else:
                fail += 1

    print(f"\nDone: {ok} rendered, {fail} failed")


if __name__ == "__main__":
    main()
