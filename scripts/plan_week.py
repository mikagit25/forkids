#!/usr/bin/env python3
"""
Generate a fresh weekly_plan.yaml based on upload history.

Rotates content types and themes to avoid repeating last week.
Produces 2 long videos + 4 shorts per day = 6 videos/day (new channel limit).

Run every Sunday before scheduler.py.

Usage:
    python3 plan_week.py              # auto-generate and save
    python3 plan_week.py --dry-run    # print plan without saving
    python3 plan_week.py --show       # show upload history
"""

import argparse
import re
import yaml
from datetime import datetime, timedelta
from pathlib import Path

ROOT      = Path(__file__).resolve().parent.parent
PLAN_PATH = ROOT / "config" / "weekly_plan.yaml"
UPLOADED  = ROOT / "uploaded"
QUEUE     = ROOT / "output" / "queue"

# ── Content rotation ──────────────────────────────────────────────────────────

# Long video types (full-length, 2 per day)
LONG_DANCE_THEMES  = ["animals", "fruits"]
LONG_EDU_TYPES     = ["abc", "numbers", "colors"]

# Shorts types (60s, 4 per day, vertical) — 7 types cycling across 6 days
SHORTS_ROTATION = [
    "short_letter", "short_number", "short_color", "short_shape",
    "short_dance", "short_vocabulary", "short_counting"
]

UPLOAD_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]

# Duration per type (minutes)
DURATIONS = {
    "dance":        30,
    "abc":          6,
    "numbers":      2,
    "colors":       2,
    "short_letter":     1,
    "short_number":     1,
    "short_color":      1,
    "short_shape":      1,
    "short_dance":      1,
    "short_vocabulary": 1,
    "short_counting":   1,
}

# Multiple title variants per type+theme — indexed by day number to avoid repeats
TITLES_VARIANTS = {
    ("dance", "animals"): [
        "Animals Dance Party 🐻 Happy Music for Kids",
        "Dancing Animals 🦁 Fun Cartoon Video for Toddlers",
        "Cute Animals Dancing 🐼 Happy Kids Music",
    ],
    ("dance", "fruits"): [
        "Fruits Dance Party 🍎 Fun Music for Children",
        "Dancing Fruits 🍌 Happy Music for Babies",
        "Cartoon Fruits Dancing 🍓 Kids Music Video",
    ],
    ("abc", "animals"): [
        "ABC Song A to Z 🔤 Learn the Alphabet with Animals",
        "Learn ABC with Cute Animals 🐻 Alphabet Song for Kids",
    ],
    ("abc", "fruits"): [
        "ABC Song 🍎 Learn the Alphabet with Fruits",
        "Learn Letters with Fruits 🍌 ABC for Toddlers",
    ],
    ("numbers", "animals"): [
        "Numbers 1 to 10 🔢 Count with Cute Animals for Kids",
        "Learn to Count 1-10 🐻 Numbers for Toddlers",
    ],
    ("numbers", "fruits"): [
        "Count 1 to 10 🔢 Learning Numbers with Fruits",
        "Numbers 1 to 10 🍎 Count with Fruits for Kids",
    ],
    ("colors", "animals"): [
        "Learn Colors 🎨 Red Blue Green Yellow for Kids",
        "Colors for Toddlers 🐻 Red Yellow Blue Green",
    ],
    ("colors", "fruits"): [
        "Colors for Kids 🎨 Learn with Cute Fruits",
        "Learn Colors with Fruits 🍎 Rainbow for Babies",
    ],
    ("short_letter", "animals"): [
        "Learn ABC Letters A B C D E 🔤 Alphabet for Babies #shorts",
        "Alphabet Song F G H I J 🔤 ABC for Toddlers #shorts",
        "Learn Letters K L M N O 🔤 Kids ABC #shorts",
        "ABC P Q R S T 🔤 Learn the Alphabet #shorts",
        "Letters U V W X Y Z 🔤 ABC Song #shorts",
        "A is for Apple 🍎 Learn ABC #shorts",
    ],
    ("short_number", "animals"): [
        "Count 1 to 5 🔢 Numbers for Babies #shorts",
        "Learn Numbers 1 2 3 4 5 🔢 Count with Animals #shorts",
        "1 2 3 Let's Count! 🔢 Numbers for Toddlers #shorts",
    ],
    ("short_number", "fruits"): [
        "Count with Fruits 🍎 1 2 3 4 5 #shorts",
        "Numbers 1 to 5 🍌 Count with Fruits #shorts",
    ],
    ("short_color", "animals"): [
        "Learn Colors 🎨 Red Blue Yellow Green #shorts",
        "Red Yellow Blue Green 🎨 Colors for Babies #shorts",
        "What Color Is It? 🌈 Colors for Kids #shorts",
    ],
    ("short_color", "fruits"): [
        "Colors with Fruits 🌈 Red Yellow Green #shorts",
        "Learn Colors 🍎 Orange Yellow Red Green #shorts",
    ],
    ("short_shape", "shapes"): [
        "Shapes for Kids ⭐ Circle Square Triangle #shorts",
        "Learn Shapes 🔷 Circle Square Star Heart #shorts",
        "Circle Square Triangle ⭐ Shapes for Babies #shorts",
    ],
    ("short_dance", "animals"): [
        "Dance with Animals 🐯 Fun Short for Kids #shorts",
        "Cute Animals Dancing 🐻 Happy Music #shorts",
        "Animal Dance Party 🦁 60 Seconds of Fun #shorts",
    ],
    ("short_dance", "fruits"): [
        "Dance with Fruits 🍌 Fun Short for Kids #shorts",
        "Fruits Dancing 🍎 Happy Music for Babies #shorts",
    ],
    ("short_vocabulary", "animals"): [
        "This is a Bear! 🐻 Learn Animals #shorts",
        "This is a Dog! 🐶 Animal Names for Kids #shorts",
        "This is an Elephant! 🐘 Learn Animals #shorts",
        "What Animal Is This? 🐸 Animal Names #shorts",
    ],
    ("short_counting", "animals"): [
        "Count 1 to 5 with Cats 🐱 Counting for Kids #shorts",
        "One Two Three! 🔢 Count with Animals #shorts",
        "Let's Count! 1 2 3 4 5 🔢 Kids Counting #shorts",
    ],
}


def get_title(video_type: str, theme: str, variant_idx: int) -> str:
    variants = TITLES_VARIANTS.get((video_type, theme))
    if variants:
        return variants[variant_idx % len(variants)]
    return f"Happy Bear Kids — {theme.capitalize()} {video_type.replace('_', ' ').capitalize()}"

TAGS_BASE = {
    "dance":        ["dance", "kids music", "happy kids", "toddlers", "children"],
    "abc":          ["abc song", "alphabet", "kids learning", "phonics", "educational"],
    "numbers":      ["counting", "numbers", "1 to 10", "math for kids", "educational"],
    "colors":       ["colors", "learn colors", "kids learning", "rainbow", "educational"],
    "short_letter": ["abc", "shorts", "alphabet", "kids", "toddlers"],
    "short_number": ["numbers", "counting", "shorts", "kids", "toddlers"],
    "short_color":  ["colors", "shorts", "kids", "learning", "rainbow"],
    "short_shape":  ["shapes", "shorts", "kids", "learning", "geometry"],
    "short_dance":       ["dance", "shorts", "kids", "fun", "animals"],
    "short_vocabulary":  ["vocabulary", "animals", "shorts", "kids", "learning"],
    "short_counting":    ["counting", "numbers", "shorts", "kids", "math"],
}

UPLOAD_TIMES_LONG   = ["09:00", "11:00"]
UPLOAD_TIMES_SHORTS = ["13:00", "15:00", "17:00", "19:00"]


def parse_uploaded_files() -> list:
    """Return list of {type, theme, date} for uploaded files."""
    history = []
    pattern = re.compile(r"(dance|abc|numbers|colors|short_\w+)_(\w+?)(?:_short)?_(\d{8})")
    for d in [UPLOADED, QUEUE]:
        if not d.exists():
            continue
        for p in sorted(d.glob("*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True):
            m = pattern.search(p.name)
            if m:
                history.append({
                    "type":  m.group(1),
                    "theme": m.group(2),
                    "date":  m.group(3),
                    "file":  p.name,
                })
    return history


def get_recent_types(history: list, days: int = 14) -> set:
    """Return set of (type, theme) used in the last N days."""
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
    return {(h["type"], h["theme"]) for h in history if h["date"] >= cutoff}


def pick_edu_type(history: list) -> str:
    """Pick the long educational type least recently used."""
    last_used = {}
    for h in history:
        t = h["type"]
        if t in LONG_EDU_TYPES and t not in last_used:
            last_used[t] = h["date"]
    for t in LONG_EDU_TYPES:
        if t not in last_used:
            return t
    return min(LONG_EDU_TYPES, key=lambda t: last_used.get(t, "00000000"))


def pick_shorts_set(history: list) -> list:
    """Pick 4 shorts types, cycling to avoid repeats."""
    last_used = {}
    for h in history:
        t = h["type"]
        if t in SHORTS_ROTATION and t not in last_used:
            last_used[t] = h["date"]

    # Sort by last used (oldest first), then pick 4
    sorted_types = sorted(SHORTS_ROTATION,
                          key=lambda t: last_used.get(t, "00000000"))
    return sorted_types[:4]


def make_entry(video_type: str, theme: str, day: str, time: str,
               variant_idx: int = 0, is_shorts: bool = False) -> dict:
    title = get_title(video_type, theme, variant_idx)
    tags  = TAGS_BASE.get(video_type, []) + [theme, "kids", "children"]
    entry = {
        "title":            title,
        "video_type":       video_type,
        "theme":            theme,
        "duration_minutes": DURATIONS[video_type],
        "upload_day":       day,
        "upload_time":      time,
        "status":           "public",
        "tags":             tags,
    }
    if is_shorts:
        entry["is_shorts"] = True
    return entry


def build_plan(history: list) -> list:
    last_dance_theme = next(
        (h["theme"] for h in history if h["type"] == "dance"), "fruits"
    )
    # 6 dance slots alternating themes
    dance_themes = []
    t = "animals" if last_dance_theme == "fruits" else "fruits"
    for _ in range(6):
        dance_themes.append(t)
        t = "fruits" if t == "animals" else "animals"

    edu_type   = pick_edu_type(history)
    # 6 edu slots — 2× each of the three types, with varying themes
    third_edu  = next(e for e in LONG_EDU_TYPES
                      if e != edu_type and e != (
                          "numbers" if edu_type == "colors" else
                          "colors"  if edu_type == "numbers" else "numbers"))
    second_edu = next(e for e in LONG_EDU_TYPES if e != edu_type and e != third_edu)

    # Edu plan for 6 days: each type appears exactly twice, themes alternate
    edu_plan = [
        (edu_type,   "animals"),
        (second_edu, "animals"),
        (third_edu,  "animals"),
        (edu_type,   "fruits"),
        (second_edu, "fruits"),
        (third_edu,  "fruits"),
    ]

    # Shorts: 7 types cycling across 6 days, 4 per day
    # Day 0: types 0,1,2,3 | Day 1: 1,2,3,4 | Day 2: 2,3,4,5 | etc.
    shorts_themes = {
        "short_letter":     "animals",
        "short_number":     "animals",
        "short_color":      "animals",
        "short_shape":      "shapes",
        "short_dance":      "animals" if last_dance_theme == "fruits" else "fruits",
        "short_vocabulary": "animals",
        "short_counting":   "animals",
    }

    # Variant counters per type to pick different titles each day
    variant_count = {}

    videos = []
    for i, day in enumerate(UPLOAD_DAYS):   # all 6 days Mon-Sat
        # Long video 1: dance
        d_theme = dance_themes[i]
        vc = variant_count.get(("dance", d_theme), 0)
        videos.append(make_entry("dance", d_theme, day, UPLOAD_TIMES_LONG[0], vc))
        variant_count[("dance", d_theme)] = vc + 1

        # Long video 2: educational (cycles through 6-slot plan)
        edu_t, edu_theme = edu_plan[i]
        vc2 = variant_count.get((edu_t, edu_theme), 0)
        videos.append(make_entry(edu_t, edu_theme, day, UPLOAD_TIMES_LONG[1], vc2))
        variant_count[(edu_t, edu_theme)] = vc2 + 1

        # 4 shorts — rotate through all 5 types across days
        day_shorts = [SHORTS_ROTATION[(i + j) % len(SHORTS_ROTATION)]
                      for j in range(4)]
        for j, short_type in enumerate(day_shorts):
            s_theme = shorts_themes.get(short_type, "animals")
            vc3 = variant_count.get((short_type, s_theme), 0)
            videos.append(make_entry(short_type, s_theme, day,
                                     UPLOAD_TIMES_SHORTS[j], vc3, is_shorts=True))
            variant_count[(short_type, s_theme)] = vc3 + 1

    return videos


def show_history(history: list):
    if not history:
        print("No upload history found.")
        return
    print(f"\nUpload history (last {min(len(history), 10)} files):")
    for h in history[:10]:
        print(f"  {h['date']}  {h['type']:<16}  {h['theme']:<10}  {h['file']}")


def main():
    parser = argparse.ArgumentParser(description="Generate weekly content plan")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--show", action="store_true", help="Show upload history")
    args = parser.parse_args()

    history = parse_uploaded_files()

    if args.show:
        show_history(history)
        return

    videos = build_plan(history)

    print(f"\nWeekly plan — {len(videos)} videos (2 long + 4 shorts per day):")
    for v in videos:
        shorts_tag = " [SHORT]" if v.get("is_shorts") else ""
        print(f"  {v['upload_day']:<12} {v['upload_time']}  "
              f"{v['video_type']:<16} {v['theme']:<10}  "
              f"{v['duration_minutes']}min{shorts_tag}  \"{v['title'][:50]}\"")

    if not args.dry_run:
        out = {"videos": videos}
        with open(PLAN_PATH, "w") as f:
            f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write("# 2 long videos + 4 shorts per day = 6 videos/day\n\n")
            yaml.dump(out, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
        print(f"\nSaved: {PLAN_PATH}")
    else:
        print("\n[DRY RUN] plan not saved")


if __name__ == "__main__":
    main()
