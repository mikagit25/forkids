#!/usr/bin/env python3
"""
Generate Edu-Entertain videos.
Scenario: config/scenarios/edu_entertain_*.txt
Usage:
  python3 scripts/generate_edu_entertain.py --key KEY --lang both
"""
import argparse, json, subprocess, sys, yaml
from datetime import datetime
from pathlib import Path

ROOT     = Path(__file__).resolve().parent.parent
REMOTION = ROOT / "remotion"
QUEUE_EN = ROOT / "output" / "queue"
QUEUE_AR = ROOT / "output" / "queue_ar"
QUEUE_ID = ROOT / "output" / "queue_id"
DATE_STR = datetime.now().strftime("%Y%m%d")

_ALL_TRACKS = [
    "Carefree.mp3", "Crinoline Dreams.mp3", "Gymnopedie No 1.mp3",
    "Happy Happy Game Show.mp3", "Heartwarming.mp3", "Hyperfun.mp3",
    "Life of Riley.mp3", "Merry Go.mp3", "Monkeys Spinning Monkeys.mp3",
    "Overworld.mp3", "Pinball Spring.mp3", "Pixelland.mp3",
    "Quirky Dog.mp3", "Salty Ditty.mp3", "Sneaky Snitch.mp3",
    "Wholesome.mp3", "Fluffing a Duck.mp3", "Walking Along.mp3",
    "George Street Shuffle.mp3", "Circus of Freaks.mp3",
]

def alt_music(en_music: str, ep_idx: int, lang: str) -> str:
    if lang == "en":
        return en_music
    offset = 7 if lang == "ar" else 14
    pool = [t for t in _ALL_TRACKS if t != en_music]
    return pool[(ep_idx + offset) % len(pool)]

SCENARIO_DIR = ROOT / "config" / "scenarios"

def expand_langs(lang):
    return ['en', 'ar', 'id'] if lang in ('both', 'all') else [lang]

def make_meta(key, lang, name_en, name_ar, name_id):
    names = {'en': name_en, 'ar': name_ar, 'id': name_id}
    channels = {'en': '@HappyBearKids1', 'ar': '@happybearkidsar', 'id': '@happybearkidsin'}
    name = names[lang]
    return {
        "title": f"{name} | Happy Bear Kids",
        "description": (
            f"{name} — educational and entertaining video for babies and toddlers (0-3 years).\n\n"
            f"Safe, calming content with gentle music and colorful visuals.\n\n"
            f"Subscribe → {channels[lang]}\n"
            f"Music: Kevin MacLeod (incompetech.com) — CC Attribution 4.0\n"
            f"© Happy Bear Kids 2026"
        ),
        "tags": [name.lower(), "edu_entertain", "kids video", "happy bear kids",
                 "baby learning", "toddler", "educational"],
        "video_type": "edu_entertain",
        "language": lang,
        "is_short": False,
        "status": "public",
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--key',       required=True)
    parser.add_argument('--lang',      default='both')
    parser.add_argument('--dry-run',   action='store_true')
    parser.add_argument('--regen-meta',action='store_true')
    args = parser.parse_args()

    langs  = expand_langs(args.lang)
    queues = {'en': QUEUE_EN, 'ar': QUEUE_AR, 'id': QUEUE_ID}

    print(f"=== Edu-Entertain: {args.key} ({', '.join(langs)}) ===")

    # Default render props (ShapeDanceLong as placeholder)
    props = {
        "shapes": ["circle", "star", "square"],
        "colors": ["#FF4499", "#44AAFF", "#FFCC00"],
        "bgColor": "#0A1020",
        "bpm": 80,
        "showLabels": False,
        "musicFile": "Happy Happy Game Show.mp3",
    }

    # Check for scenario-specific doc
    scenario_files = list(SCENARIO_DIR.glob(f"edu_entertain_{args.key}*.txt"))
    if scenario_files:
        print(f"  Scenario doc: {scenario_files[0].name}")

    is_no_text = True  # set False if this type has language-specific text

    if is_no_text:
        # Render once, copy to all queues
        out_mp4 = QUEUE_EN / f"edu_entertain_{args.key}_{DATE_STR}.mp4"
        if not out_mp4.exists() and not args.dry_run and not args.regen_meta:
            cmd = ["npx", "remotion", "render", "ShapeDanceLong",
                   f"--props={json.dumps(props)}", f"--output={str(out_mp4)}"]
            r = subprocess.run(cmd, cwd=str(REMOTION), timeout=86400)
            if r.returncode != 0:
                print(f"  FAILED")
                return
        if out_mp4.exists() and not args.dry_run:
            en_music = props["musicFile"]
            for lg in langs:
                if lg != 'en':
                    dest = queues[lg] / out_mp4.name
                    if not dest.exists():
                        lang_music  = alt_music(en_music, 0, lg)
                        props_lang  = dict(props)
                        props_lang["musicFile"] = lang_music
                        cmd_lg = ["npx", "remotion", "render", "ShapeDanceLong",
                                  f"--props={json.dumps(props_lang)}", f"--output={str(dest)}"]
                        r = subprocess.run(cmd_lg, cwd=str(REMOTION), timeout=86400)
                        if r.returncode != 0:
                            print(f"  FAILED ({lg})")
        for lg in langs:
            q = queues[lg]
            mp4_name = out_mp4.name
            meta_path = q / f"meta_{Path(mp4_name).stem}.yaml"
            if not meta_path.exists() or args.regen_meta:
                meta = make_meta(args.key, lg, "Edu-Entertain", "ترفيه تعليمي", "Edu-Hibur")
                if not args.dry_run:
                    with open(meta_path, 'w', encoding='utf-8') as f:
                        yaml.dump(meta, f, allow_unicode=True)
                print(f"  Meta ({lg}): {meta_path.name}")
    else:
        for lg in langs:
            q = queues[lg]
            out_mp4 = q / f"edu_entertain_{args.key}_{lg}_{DATE_STR}.mp4"
            if not out_mp4.exists() and not args.dry_run and not args.regen_meta:
                cmd = ["npx", "remotion", "render", "ShapeDanceLong",
                       f"--props={json.dumps(props)}", f"--output={str(out_mp4)}"]
                r = subprocess.run(cmd, cwd=str(REMOTION), timeout=86400)
            meta_path = q / f"meta_{out_mp4.stem}.yaml"
            if not meta_path.exists() or args.regen_meta:
                meta = make_meta(args.key, lg, "Edu-Entertain", "ترفيه تعليمي", "Edu-Hibur")
                if not args.dry_run:
                    with open(meta_path, 'w', encoding='utf-8') as f:
                        yaml.dump(meta, f, allow_unicode=True)
                print(f"  Meta ({lg}): {meta_path.name}")

if __name__ == '__main__':
    main()
