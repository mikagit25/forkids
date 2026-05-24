#!/usr/bin/env python3
"""
Generate a fresh weekly_plan.yaml based on upload history.

Rotates content types and themes to avoid repeating last week.
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

# Ordered rotation — cycles through this list week by week
DANCE_THEMES  = ["animals", "fruits", "animals"]  # 3 dance slots per week
EDU_TYPES     = ["abc", "numbers", "colors"]       # rotate educational types

TITLES = {
    ("dance",   "animals"): "Animals Dance Party 🐻 Happy Music for Kids",
    ("dance",   "fruits"):  "Fruits Dance Party 🍎 Fun Music for Children",
    ("abc",     "animals"): "ABC Song A to Z 🔤 Learn the Alphabet with Animals",
    ("abc",     "fruits"):  "ABC Song 🍎 Learn the Alphabet with Fruits",
    ("numbers", "animals"): "Numbers 1 to 10 🔢 Count with Cute Animals",
    ("numbers", "fruits"):  "Count 1 to 10 🔢 Learning Numbers with Fruits",
    ("colors",  "animals"): "Learn Colors 🎨 Red Blue Green Yellow for Kids",
    ("colors",  "fruits"):  "Colors for Kids 🎨 Learn with Cute Fruits",
}

TAGS_BASE = {
    "dance":   ["dance", "kids music", "happy kids", "toddlers", "children"],
    "abc":     ["abc song", "alphabet", "kids learning", "phonics", "educational"],
    "numbers": ["counting", "numbers", "1 to 10", "math for kids", "educational"],
    "colors":  ["colors", "learn colors", "kids learning", "rainbow", "educational"],
}

UPLOAD_DAYS  = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
UPLOAD_TIME  = "09:00"

# Duration per type (minutes)
DURATIONS = {
    "dance":   30,
    "abc":     6,
    "numbers": 2,
    "colors":  2,
}


def parse_uploaded_files() -> list:
    """Return list of {type, theme, date} for uploaded files."""
    history = []
    for d in [UPLOADED, QUEUE]:
        if not d.exists():
            continue
        for p in sorted(d.glob("*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True):
            m = re.match(r"(dance|abc|numbers|colors)_(\w+)_(\d{8})", p.name)
            if m:
                history.append({
                    "type":  m.group(1),
                    "theme": m.group(2),
                    "date":  m.group(3),
                    "file":  p.name,
                })
    return history


def get_last_week_types(history: list) -> set:
    """Return set of (type, theme) combinations uploaded in the last 14 days."""
    cutoff = (datetime.now() - timedelta(days=14)).strftime("%Y%m%d")
    return {(h["type"], h["theme"]) for h in history if h["date"] >= cutoff}


def pick_edu_type(history: list) -> str:
    """Pick the educational type least recently used."""
    last_used = {}
    for h in history:
        t = h["type"]
        if t in EDU_TYPES and t not in last_used:
            last_used[t] = h["date"]
    # Pick type not in last_used, or oldest
    for t in EDU_TYPES:
        if t not in last_used:
            return t
    return min(EDU_TYPES, key=lambda t: last_used.get(t, "00000000"))


def build_plan(history: list) -> list:
    recent = get_last_week_types(history)
    edu_type = pick_edu_type(history)

    # 3 dance + 1 edu + (numbers or colors as second edu)
    second_edu = "numbers" if edu_type == "colors" else \
                 "colors"  if edu_type == "numbers" else "numbers"

    # Build slots: [type, theme, day]
    slots = []

    # Dance videos — alternate animal/fruit theme
    last_dance_theme = next(
        (h["theme"] for h in history if h["type"] == "dance"), "fruits"
    )
    dance_themes = ["animals", "fruits", "animals"] if last_dance_theme == "fruits" \
                   else ["fruits", "animals", "fruits"]

    day_iter = iter(UPLOAD_DAYS)
    for theme in dance_themes:
        slots.append(("dance", theme, next(day_iter)))

    slots.append((edu_type, "animals", next(day_iter)))
    slots.append((second_edu, "animals", next(day_iter)))

    # Build plan entries
    videos = []
    for video_type, theme, day in slots:
        title = TITLES.get((video_type, theme),
                           f"Happy Bear Kids — {theme.capitalize()} {video_type.capitalize()}")
        tags  = TAGS_BASE.get(video_type, []) + [theme, "kids", "children"]
        videos.append({
            "title":            title,
            "video_type":       video_type,
            "theme":            theme,
            "duration_minutes": DURATIONS[video_type],
            "upload_day":       day,
            "upload_time":      UPLOAD_TIME,
            "status":           "public",
            "tags":             tags,
        })

    return videos


def show_history(history: list):
    if not history:
        print("No upload history found.")
        return
    print(f"\nUpload history (last {min(len(history), 10)} files):")
    for h in history[:10]:
        print(f"  {h['date']}  {h['type']:<8}  {h['theme']:<10}  {h['file']}")


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

    plan = {
        "# generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "# video_type": "dance | abc | numbers | colors",
        "videos": videos,
    }

    # Print preview
    print(f"\nWeekly plan — {len(videos)} videos:")
    for v in videos:
        print(f"  {v['upload_day']:<12} {v['video_type']:<8} {v['theme']:<10}  {v['duration_minutes']}min  \"{v['title'][:50]}\"")

    if not args.dry_run:
        # Write plan using proper yaml (skip comment keys)
        out = {"videos": videos}
        with open(PLAN_PATH, "w") as f:
            f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write("# video_type: dance | abc | numbers | colors\n\n")
            yaml.dump(out, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
        print(f"\nSaved: {PLAN_PATH}")
    else:
        print("\n[DRY RUN] plan not saved")


if __name__ == "__main__":
    main()
