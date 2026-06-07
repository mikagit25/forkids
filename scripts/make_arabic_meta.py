#!/usr/bin/env python3
"""
Generate Arabic meta YAML files for existing English videos.
For dance/counting/shapes videos — same MP4, only metadata changes.
Arabic videos go to output/queue_ar/ and wait there until English queue empties.

Usage:
  python3 scripts/make_arabic_meta.py           # process all videos in queue + uploaded
  python3 scripts/make_arabic_meta.py --dry-run  # preview only
"""
import argparse
import re
import sys
import yaml
from pathlib import Path

ROOT     = Path(__file__).resolve().parent.parent
QUEUE    = ROOT / "output" / "queue"
UPLOADED = ROOT / "uploaded"
QUEUE_AR = ROOT / "output" / "queue_ar"

sys.path.insert(0, str(ROOT / "scripts"))
from arabic_data import (
    ANIMALS_AR, FRUITS_AR, VEGETABLES_AR, SHAPES_AR, COLORS_AR,
    dance_meta_ar, counting_meta_ar, shapes_dance_meta_ar,
    short_dance_meta_ar, short_color_meta_ar, short_shape_meta_ar,
)

# ── Video type routing ────────────────────────────────────────────────────────

def subject_from_stem(stem: str, table: dict) -> tuple[str, str] | None:
    """Find English key and Arabic value matching any part of the filename."""
    for en, ar in table.items():
        if en in stem:
            return en, ar
    return None


def make_ar_meta(mp4: Path) -> tuple[dict, str] | None:
    """Return (meta_dict, ar_stem) or None if unrecognised."""
    stem = mp4.stem

    # ── Long videos ──────────────────────────────────────────────────────────
    if re.match(r"dance_(animals|fruits|vegetables)", stem):
        theme = re.search(r"dance_(animals|fruits|vegetables)", stem).group(1)
        table = {"animals": ANIMALS_AR, "fruits": FRUITS_AR,
                 "vegetables": VEGETABLES_AR}[theme]
        name_ar = {"animals": "الحيوانات", "fruits": "الفواكه",
                   "vegetables": "الخضروات"}[theme]
        theme_ar = {"animals": "animals", "fruits": "fruits",
                    "vegetables": "vegetables"}[theme]
        meta = {
            "title":       f"رقص {name_ar} | 30 دقيقة | {'' if 'v2' not in stem else 'الجزء الثاني '}{name_ar} | هابي بير كيدز",
            "description": (
                f"استمتع بـ 30 دقيقة من الرقص مع {name_ar}! 🎵\n"
                f"فيديو تعليمي ومسلٍّ للأطفال.\n\n"
                f"#رقص #أطفال #{name_ar} #هابي_بير_كيدز"
            ),
            "tags": ["رقص", "أطفال", name_ar, "هابي بير كيدز",
                     "تعليم", "30 دقيقة"],
            "video_type": "dance", "theme": theme_ar,
            "language": "ar", "status": "public",
            "source_mp4": str(mp4),
        }
        return meta, f"ar_{stem}"

    if re.match(r"dance_shapes", stem):
        theme_m = re.search(r"dance_shapes_(\w+)", stem)
        theme = theme_m.group(1) if theme_m else "rainbow"
        meta = shapes_dance_meta_ar(theme)
        meta.update({"video_type": "dance", "theme": "shapes",
                     "source_mp4": str(mp4)})
        return meta, f"ar_{stem}"

    if re.match(r"counting_", stem):
        theme_m = re.search(r"counting_(\w+)_\d{8}", stem)
        theme = theme_m.group(1) if theme_m else "rainbow"
        meta = counting_meta_ar(theme)
        meta.update({"video_type": "counting", "theme": "shapes",
                     "source_mp4": str(mp4)})
        return meta, f"ar_{stem}"

    if stem.startswith("dance_mixed"):
        meta = {
            "title":       f"رقص مختلط | أشكال وحيوانات | هابي بير كيدز",
            "description": "رقص مبهج مع مجموعة متنوعة! 🎵 #رقص #أطفال",
            "tags":        ["رقص", "أطفال", "مختلط", "هابي بير كيدز"],
            "video_type":  "dance", "theme": "animals",
            "language":    "ar", "status": "public",
            "source_mp4":  str(mp4),
        }
        return meta, f"ar_{stem}"

    # ── Shorts — dance ────────────────────────────────────────────────────────
    m = re.match(r"short_dance_(\w+)_\d{8}", stem)
    if m:
        subject_en = m.group(1)
        all_subjects = {**ANIMALS_AR, **FRUITS_AR, **VEGETABLES_AR}
        subject_ar = all_subjects.get(subject_en, subject_en)
        meta = short_dance_meta_ar(subject_en, subject_ar)
        meta.update({"video_type": "short_dance", "source_mp4": str(mp4)})
        return meta, f"ar_{stem}"

    # ── Shorts — color (existing short_color_red_animals type) ───────────────
    m = re.match(r"short_color_(\w+)_(\w+)_\d{8}", stem)
    if m:
        color_en = m.group(1)
        color_ar = COLORS_AR.get(color_en, {}).get("name", color_en)
        meta = short_color_meta_ar(color_en, color_ar)
        meta.update({"video_type": "short_color", "source_mp4": str(mp4)})
        return meta, f"ar_{stem}"

    # ── Shorts — shapes (existing short_shapes_* Manim type) ─────────────────
    m = re.match(r"short_shapes_(\w+)_\d{8}", stem)
    if m:
        anim = m.group(1).replace("_", " ")
        meta = {
            "title":       f"رقص الأشكال — {anim} | هابي بير كيدز #shorts",
            "description": "شاهد الأشكال ترقص! ⭐ #أشكال #أطفال #shorts",
            "tags":        ["أشكال", "رقص", "أطفال", "هابي بير كيدز", "shorts"],
            "video_type":  "short_shapes", "language": "ar",
            "is_short": True, "status": "public", "source_mp4": str(mp4),
        }
        return meta, f"ar_{stem}"

    # ── Shorts — counting ─────────────────────────────────────────────────────
    m = re.match(r"short_counting_(\w+)_\d{8}", stem)
    if m:
        shapes = m.group(1).replace("_", " و")
        meta = {
            "title":       f"عد الأشكال | {shapes} | هابي بير كيدز #shorts",
            "description": "تعلم العد مع الأشكال! 🔢 #عد #أطفال #shorts",
            "tags":        ["عد", "أشكال", "أطفال", "تعليم", "هابي بير كيدز", "shorts"],
            "video_type":  "short_counting", "language": "ar",
            "is_short": True, "status": "public", "source_mp4": str(mp4),
        }
        return meta, f"ar_{stem}"

    # ── Shorts — color_learn (new Remotion type) ──────────────────────────────
    m = re.match(r"short_colorlearn_(\w+)_\d{8}", stem)
    if m:
        color_en = m.group(1)
        color_ar = COLORS_AR.get(color_en, {}).get("name", color_en)
        meta = short_color_meta_ar(color_en, color_ar)
        meta.update({"video_type": "short_colorlearn", "source_mp4": str(mp4)})
        return meta, f"ar_{stem}"

    # ── Shorts — shape_float / shape_dance (Remotion) ─────────────────────────
    m = re.match(r"short_(float|sdance)_(\w+)_\d{8}", stem)
    if m:
        shape_en = m.group(2).split("_")[0]
        shape_ar = SHAPES_AR.get(shape_en, shape_en)
        meta = short_shape_meta_ar(shape_en, shape_ar)
        meta.update({"video_type": f"short_{m.group(1)}", "source_mp4": str(mp4)})
        return meta, f"ar_{stem}"

    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--source", choices=["queue", "uploaded", "both"],
                        default="both")
    args = parser.parse_args()

    QUEUE_AR.mkdir(parents=True, exist_ok=True)

    sources = []
    if args.source in ("queue", "both"):
        sources += list(QUEUE.glob("*.mp4"))
    if args.source in ("uploaded", "both"):
        sources += list(UPLOADED.glob("*.mp4"))

    sources = [p for p in sources if "test_" not in p.name
               and not p.name.startswith("ar_")
               and "abc" not in p.name
               and "vocab" not in p.name]

    ok = skip = 0
    for mp4 in sorted(sources):
        result = make_ar_meta(mp4)
        if not result:
            continue
        meta, ar_stem = result
        meta_path = QUEUE_AR / f"meta_{ar_stem}.yaml"
        # Symlink to the actual mp4 (avoid copying GBs of data)
        link_path = QUEUE_AR / f"{ar_stem}.mp4"

        if meta_path.exists():
            skip += 1
            continue

        print(f"  {'[DRY]' if args.dry_run else '     '} {ar_stem}.mp4")
        if not args.dry_run:
            meta_path.write_text(
                yaml.dump(meta, allow_unicode=True,
                          default_flow_style=False, sort_keys=False)
            )
            if not link_path.exists():
                link_path.symlink_to(mp4.resolve())
        ok += 1

    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Done: {ok} Arabic meta files created, {skip} skipped")
    if not args.dry_run:
        total = len(list(QUEUE_AR.glob("meta_*.yaml")))
        print(f"Arabic staging queue: {total} videos ready in output/queue_ar/")


if __name__ == "__main__":
    main()
