#!/usr/bin/env python3
"""
Generate Arabic 30-min dance scripts for animals, fruits, vegetables.
Text overlays use Arabic character names and "هيا نرقص!" instead of English.

Usage:
  python3 scripts/generate_arabic_dance_scripts.py            # generate scripts
  python3 scripts/generate_arabic_dance_scripts.py --render   # also render videos
"""
import argparse
import random
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from arabic_data import ANIMALS_AR, FRUITS_AR, VEGETABLES_AR, CHANNEL_NAME_AR

SCENE_DURATION = 38

SOLO_CHOREOS = [
    "solo_bounce", "solo_sway", "solo_spin", "solo_wave",
    "solo_jump",   "solo_twist", "solo_nod", "solo_shimmy",
]

BG_COLORS = [
    "#FFF9E6", "#E8F5E9", "#E3F2FD", "#FCE4EC",
    "#F3E5F5", "#E0F7FA", "#FFFDE7", "#F9FBE7",
    "#FFF3E0", "#E8EAF6", "#F1F8E9", "#FFF8E1",
    "#E0F2F1", "#FCE4EC", "#E8F5E9", "#EDE7F6",
    "#E1F5FE", "#F9FBE7", "#FFF9E6", "#E3F2FD",
]

THEMES = {
    "animals":    {"chars": list(ANIMALS_AR.keys()),    "names": ANIMALS_AR},
    "fruits":     {"chars": list(FRUITS_AR.keys()),     "names": FRUITS_AR},
    "vegetables": {"chars": list(VEGETABLES_AR.keys()), "names": VEGETABLES_AR},
}

AR_TAGLINE = "هيا نرقص!"


def generate_script(theme: str, duration_minutes: int = 30, seed: int = 42) -> dict:
    random.seed(seed)
    chars  = THEMES[theme]["chars"]
    names  = THEMES[theme]["names"]
    total_sec = duration_minutes * 60

    pool = []
    while len(pool) * SCENE_DURATION < total_sec + SCENE_DURATION:
        batch = chars.copy()
        random.shuffle(batch)
        pool.extend(batch)

    choreo_pool = SOLO_CHOREOS * (len(pool) // len(SOLO_CHOREOS) + 1)
    random.shuffle(choreo_pool)
    for i in range(1, len(choreo_pool)):
        if choreo_pool[i] == choreo_pool[i - 1]:
            for j in range(i + 1, len(choreo_pool)):
                if choreo_pool[j] != choreo_pool[i - 1]:
                    choreo_pool[i], choreo_pool[j] = choreo_pool[j], choreo_pool[i]
                    break

    scenes = []
    t = 0.0
    for idx, char in enumerate(pool):
        dur = min(SCENE_DURATION, total_sec - t)
        if dur < 10:
            break
        scenes.append({
            "start_sec": round(t, 1),
            "duration":  round(dur, 1),
            "choreo":    choreo_pool[idx % len(choreo_pool)],
            "n":         1,
            "chars":     [char],
            "entry":     "zoom_in",
            "bg_color":  BG_COLORS[idx % len(BG_COLORS)],
            "text":      names[char],    # Arabic name, e.g. "دب"
            "sub_text":  AR_TAGLINE,     # "هيا نرقص!"
        })
        t += dur

    return {
        "video_type":       "dance",
        "theme":            theme,
        "language":         "ar",
        "duration_minutes": duration_minutes,
        "style":            "tutitu",
        "scenes":           scenes,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--themes", nargs="+",
                        choices=["animals", "fruits", "vegetables"],
                        default=["animals", "fruits", "vegetables"])
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--render", action="store_true",
                        help="Also render videos immediately (slow: ~45 min each)")
    args = parser.parse_args()

    date_str = datetime.now().strftime("%Y%m%d")

    for theme in args.themes:
        script  = generate_script(theme, args.duration)
        out_yaml = ROOT / "config" / "scripts" / f"dance_{theme}_ar.yaml"
        with open(out_yaml, "w") as f:
            yaml.dump(script, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        print(f"Script → {out_yaml}  ({len(script['scenes'])} scenes)")

        if args.render:
            out_mp4 = ROOT / "output" / "queue_ar" / f"ar_dance_{theme}_{date_str}.mp4"
            # Remove old symlink if present
            if out_mp4.is_symlink() or out_mp4.exists():
                out_mp4.unlink()
            print(f"Rendering {out_mp4.name} …")
            result = subprocess.run([
                sys.executable,
                str(ROOT / "scripts" / "generate_video.py"),
                "--theme", theme,
                "--duration", str(args.duration),
                "--script", str(out_yaml),
                "--output", str(out_mp4),
            ], cwd=str(ROOT))
            if result.returncode == 0:
                print(f"  ✓ {out_mp4.name}")
                # Write meta sidecar
                theme_ar = {"animals": "الحيوانات", "fruits": "الفواكه",
                            "vegetables": "الخضروات"}[theme]
                meta = {
                    "title": f"رقص {theme_ar} | 30 دقيقة | {theme_ar} | {CHANNEL_NAME_AR}",
                    "description": (
                        f"استمتع بـ 30 دقيقة من الرقص مع {theme_ar}! 🎵\n"
                        f"فيديو تعليمي ومسلٍّ للأطفال مع {CHANNEL_NAME_AR}.\n"
                        f"تعلم أسماء {theme_ar} باللغة العربية مع الرقص والموسيقى.\n\n"
                        f"🌟 المميزات:\n"
                        f"• رسوم متحركة ملونة بأسماء عربية\n"
                        f"• موسيقى مرحة ومناسبة للأطفال\n"
                        f"• مناسب لجميع الأعمار\n\n"
                        f"🎵 الموسيقى: Kevin MacLeod (incompetech.com) CC BY 4.0\n"
                        f"© {CHANNEL_NAME_AR} 2026"
                    ),
                    "tags": ["رقص", "أطفال", theme_ar, "هابي بير كيدز",
                             "تعليم", "30 دقيقة", "موسيقى أطفال"],
                    "language": "ar",
                    "theme": theme,
                    "video_type": "dance",
                    "status": "public",
                }
                meta_path = out_mp4.parent / f"meta_{out_mp4.stem}.yaml"
                with open(meta_path, "w") as f:
                    yaml.dump(meta, f, allow_unicode=True, default_flow_style=False)
                print(f"  Meta → {meta_path.name}")
            else:
                print(f"  ✗ render failed (exit {result.returncode})")


if __name__ == "__main__":
    main()
