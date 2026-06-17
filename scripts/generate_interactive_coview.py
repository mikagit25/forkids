#!/usr/bin/env python3
"""
Generate Interactive Co-Viewing videos.
Scenario: config/scenarios/interactive_coview_*.txt
Usage:
  python3 scripts/generate_interactive_coview.py --key KEY --lang both
"""
import argparse, json, shutil, subprocess, sys, yaml
from datetime import datetime
from pathlib import Path

ROOT     = Path(__file__).resolve().parent.parent
REMOTION = ROOT / "remotion"
QUEUE_EN = ROOT / "output" / "queue"
QUEUE_AR = ROOT / "output" / "queue_ar"
QUEUE_ID = ROOT / "output" / "queue_id"
DATE_STR = datetime.now().strftime("%Y%m%d")

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
        "tags": [name.lower(), "interactive_coview", "kids video", "happy bear kids",
                 "baby learning", "toddler", "educational"],
        "video_type": "interactive_coview",
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

    print(f"=== Interactive Co-Viewing: {args.key} ({', '.join(langs)}) ===")

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
    scenario_files = list(SCENARIO_DIR.glob(f"interactive_coview_{args.key}*.txt"))
    if scenario_files:
        print(f"  Scenario doc: {scenario_files[0].name}")

    is_no_text = True  # set False if this type has language-specific text

    if is_no_text:
        # Render once, copy to all queues
        out_mp4 = QUEUE_EN / f"interactive_coview_{args.key}_{DATE_STR}.mp4"
        if not out_mp4.exists() and not args.dry_run and not args.regen_meta:
            cmd = ["npx", "remotion", "render", "ShapeDanceLong",
                   f"--props={json.dumps(props)}", f"--output={str(out_mp4)}"]
            r = subprocess.run(cmd, cwd=str(REMOTION), timeout=86400)
            if r.returncode != 0:
                print(f"  FAILED")
                return
        if out_mp4.exists() and not args.dry_run:
            for lg in langs:
                if lg != 'en':
                    dest = queues[lg] / out_mp4.name
                    if not dest.exists():
                        shutil.copy2(str(out_mp4), str(dest))
        for lg in langs:
            q = queues[lg]
            mp4_name = out_mp4.name
            meta_path = q / f"meta_{Path(mp4_name).stem}.yaml"
            if not meta_path.exists() or args.regen_meta:
                meta = make_meta(args.key, lg, "Interactive Co-Viewing", "مشاهدة تفاعلية", "Menonton Bersama")
                if not args.dry_run:
                    with open(meta_path, 'w', encoding='utf-8') as f:
                        yaml.dump(meta, f, allow_unicode=True)
                print(f"  Meta ({lg}): {meta_path.name}")
    else:
        for lg in langs:
            q = queues[lg]
            out_mp4 = q / f"interactive_coview_{args.key}_{lg}_{DATE_STR}.mp4"
            if not out_mp4.exists() and not args.dry_run and not args.regen_meta:
                cmd = ["npx", "remotion", "render", "ShapeDanceLong",
                       f"--props={json.dumps(props)}", f"--output={str(out_mp4)}"]
                r = subprocess.run(cmd, cwd=str(REMOTION), timeout=86400)
            meta_path = q / f"meta_{out_mp4.stem}.yaml"
            if not meta_path.exists() or args.regen_meta:
                meta = make_meta(args.key, lg, "Interactive Co-Viewing", "مشاهدة تفاعلية", "Menonton Bersama")
                if not args.dry_run:
                    with open(meta_path, 'w', encoding='utf-8') as f:
                        yaml.dump(meta, f, allow_unicode=True)
                print(f"  Meta ({lg}): {meta_path.name}")

if __name__ == '__main__':
    main()
