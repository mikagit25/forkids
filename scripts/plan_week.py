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

# Shorts types (60s, 4 per day, vertical)
SHORTS_ROTATION = [
    "short_letter", "short_number", "short_color", "short_shape", "short_dance"
]

UPLOAD_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]

# Duration per type (minutes)
DURATIONS = {
    "dance":        30,
    "abc":          6,
    "numbers":      2,
    "colors":       2,
    "short_letter": 1,
    "short_number": 1,
    "short_color":  1,
    "short_shape":  1,
    "short_dance":  1,
}

TITLES = {
    ("dance",        "animals"): "Animals Dance Party 🐻 Happy Music for Kids",
    ("dance",        "fruits"):  "Fruits Dance Party 🍎 Fun Music for Children",
    ("abc",          "animals"): "ABC Song A to Z 🔤 Learn the Alphabet with Animals",
    ("abc",          "fruits"):  "ABC Song 🍎 Learn the Alphabet with Fruits",
    ("numbers",      "animals"): "Numbers 1 to 10 🔢 Count with Cute Animals for Kids",
    ("numbers",      "fruits"):  "Count 1 to 10 🔢 Learning Numbers with Fruits",
    ("colors",       "animals"): "Learn Colors 🎨 Red Blue Green Yellow for Kids",
    ("colors",       "fruits"):  "Colors for Kids 🎨 Learn with Cute Fruits",
    ("short_letter", "animals"): "Learn ABC Letters 🔤 Alphabet for Babies #shorts",
    ("short_letter", "fruits"):  "Learn Letters 🍎 ABC with Fruits #shorts",
    ("short_number", "animals"): "Count 1 to 5 🔢 Numbers for Babies #shorts",
    ("short_number", "fruits"):  "Count with Fruits 🍎 1 2 3 4 5 #shorts",
    ("short_color",  "animals"): "Learn Colors 🎨 Red Blue Yellow Green #shorts",
    ("short_color",  "fruits"):  "Colors with Fruits 🌈 Red Yellow Green #shorts",
    ("short_shape",  "shapes"):  "Shapes for Kids ⭐ Circle Square Triangle #shorts",
    ("short_dance",  "animals"): "Dance with Animals 🐯 Fun Short for Kids #shorts",
    ("short_dance",  "fruits"):  "Dance with Fruits 🍌 Fun Short for Kids #shorts",
}

TAGS_BASE = {
    "dance":        ["dance", "kids music", "happy kids", "toddlers", "children"],
    "abc":          ["abc song", "alphabet", "kids learning", "phonics", "educational"],
    "numbers":      ["counting", "numbers", "1 to 10", "math for kids", "educational"],
    "colors":       ["colors", "learn colors", "kids learning", "rainbow", "educational"],
    "short_letter": ["abc", "shorts", "alphabet", "kids", "toddlers"],
    "short_number": ["numbers", "counting", "shorts", "kids", "toddlers"],
    "short_color":  ["colors", "shorts", "kids", "learning", "rainbow"],
    "short_shape":  ["shapes", "shorts", "kids", "learning", "geometry"],
    "short_dance":  ["dance", "shorts", "kids", "fun", "animals"],
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


def make_entry(video_type: str, theme: str, day: str, time: str, is_shorts: bool = False) -> dict:
    title = TITLES.get(
        (video_type, theme),
        f"Happy Bear Kids — {theme.capitalize()} {video_type.replace('_', ' ').capitalize()}"
    )
    tags = TAGS_BASE.get(video_type, []) + [theme, "kids", "children"]
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
    dance_themes = ["animals", "fruits", "animals"] if last_dance_theme == "fruits" \
                   else ["fruits", "animals", "fruits"]

    edu_type = pick_edu_type(history)
    second_edu = "numbers" if edu_type == "colors" else \
                 "colors"  if edu_type == "numbers" else "numbers"

    shorts_set = pick_shorts_set(history)
    # Pad to 4 if needed
    while len(shorts_set) < 4:
        shorts_set.append("short_dance")

    # Alternate short themes
    shorts_themes = {
        "short_letter": "animals",
        "short_number": "animals",
        "short_color":  "animals",
        "short_shape":  "shapes",
        "short_dance":  "animals" if last_dance_theme == "fruits" else "fruits",
    }

    videos = []
    # 3 days of content (Mon/Tue/Wed), each day: 2 long + 4 shorts
    day_plans = [
        # (long_type1, long_theme1, long_type2, long_theme2)
        ("dance",   dance_themes[0], edu_type,   "animals"),
        ("dance",   dance_themes[1], second_edu, "animals"),
        ("dance",   dance_themes[2], "abc",      "animals"),
    ]

    days = UPLOAD_DAYS[:3]  # monday, tuesday, wednesday
    for i, day in enumerate(days):
        long1_type, long1_theme, long2_type, long2_theme = day_plans[i]

        # 2 long videos
        videos.append(make_entry(long1_type, long1_theme, day, UPLOAD_TIMES_LONG[0]))
        videos.append(make_entry(long2_type, long2_theme, day, UPLOAD_TIMES_LONG[1]))

        # 4 shorts (rotate the set each day)
        day_shorts = shorts_set[i % len(shorts_set):] + shorts_set[:i % len(shorts_set)]
        day_shorts = day_shorts[:4]
        for j, short_type in enumerate(day_shorts):
            theme = shorts_themes.get(short_type, "animals")
            videos.append(make_entry(short_type, theme, day,
                                     UPLOAD_TIMES_SHORTS[j], is_shorts=True))

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
