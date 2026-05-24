#!/usr/bin/env python3
"""
Generate a full episode scene script from a template.

Usage:
    python3 generate_script.py --duration 30 --theme fruits
    python3 generate_script.py --duration 5  --template config/scene_templates/default.yaml
    python3 generate_script.py --list-choreos

Output: config/scripts/episode_YYYYMMDD_HHMMSS.yaml
"""

import argparse
import random
import yaml
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent

CHOREO_DOCS = {
    "grid_bounce":   "2×2 grid, all bounce on the beat in wave sequence",
    "grid_sway":     "2×2 grid, chars sway left-right mirroring each other",
    "carousel":      "Chars rotate in an ellipse (perspective scale effect)",
    "parade":        "Chars march left → right across screen, looping",
    "line_h":        "Horizontal row, bounce ripples from left to right",
    "diagonal_in":   "Enter from screen corners → slide to grid, then bounce",
    "zigzag":        "Each char weaves along its own sine-wave path",
}


def load_template(path: Path) -> list:
    with open(path) as f:
        data = yaml.safe_load(f)
    return data["scenes"]


def load_chars(theme: str) -> list:
    """Return all available character names for the given theme."""
    ai_dir   = ROOT / "assets" / "sprites" / "ai_generated"
    theme_dir = ROOT / "assets" / "sprites" / theme

    chars = []
    if ai_dir.exists():
        chars = [p.stem for p in sorted(ai_dir.glob("*.png"))]
    elif theme_dir.exists():
        chars = [p.stem for p in sorted(theme_dir.glob("*.png"))]

    if not chars:
        raise FileNotFoundError(f"No characters found for theme '{theme}'")
    return chars


def assign_chars(scenes: list, all_chars: list) -> list:
    """
    Assign unique characters to each scene.
    Characters cycle through all available without repeats across adjacent scenes.
    """
    pool = all_chars.copy()
    random.shuffle(pool)
    pos = 0
    result = []

    for scene in scenes:
        n = scene.get("n", 4)
        # Use explicitly named chars if provided
        if "chars" in scene and scene["chars"]:
            result.append({**scene})
            continue

        chosen = []
        for _ in range(n):
            if pos >= len(pool):
                random.shuffle(pool)
                pos = 0
            # Avoid picking same as last scene's last char
            chosen.append(pool[pos])
            pos += 1
        result.append({**scene, "chars": chosen})

    return result


def fill_to_duration(scenes: list, target_sec: float) -> list:
    """Repeat scene template until target duration is covered."""
    total = sum(s["duration"] for s in scenes)
    if total >= target_sec:
        # Trim last scenes if needed
        out, acc = [], 0
        for s in scenes:
            if acc >= target_sec:
                break
            remaining = target_sec - acc
            if s["duration"] > remaining:
                s = {**s, "duration": remaining}
            out.append(s)
            acc += s["duration"]
        return out

    # Need to repeat
    filled = []
    acc = 0
    idx = 0
    while acc < target_sec:
        s = dict(scenes[idx % len(scenes)])
        remaining = target_sec - acc
        if s["duration"] > remaining:
            s["duration"] = remaining
        filled.append(s)
        acc += s["duration"]
        idx += 1
    return filled


def add_start_times(scenes: list) -> list:
    """Add start_sec field to each scene."""
    t = 0.0
    result = []
    for i, s in enumerate(scenes):
        result.append({**s, "id": i + 1, "start_sec": round(t, 2)})
        t += s["duration"]
    return result


def generate_script(
    duration_min: float,
    theme: str,
    template_path: Path,
    output_dir: Path,
) -> Path:
    all_chars = load_chars(theme)
    template_scenes = load_template(template_path)

    target_sec = duration_min * 60
    scenes = fill_to_duration(template_scenes, target_sec)
    scenes = assign_chars(scenes, all_chars)
    scenes = add_start_times(scenes)

    total_sec = sum(s["duration"] for s in scenes)

    script = {
        "title": f"Happy Bear Kids — {theme.capitalize()} Dance",
        "theme": theme,
        "duration_minutes": round(total_sec / 60, 1),
        "total_scenes": len(scenes),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "template": str(template_path.relative_to(ROOT)),
        "scenes": scenes,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = output_dir / f"episode_{ts}.yaml"
    with open(out_path, "w") as f:
        yaml.dump(script, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

    return out_path


def print_script_summary(path: Path):
    with open(path) as f:
        data = yaml.safe_load(f)

    print(f"\n{'='*60}")
    print(f"  {data['title']}")
    print(f"  Duration: {data['duration_minutes']} min  |  Scenes: {data['total_scenes']}")
    print(f"{'='*60}")
    for s in data["scenes"]:
        chars_str = ", ".join(s.get("chars", [])[:4])
        if len(s.get("chars", [])) > 4:
            chars_str += "…"
        print(f"  [{s['id']:02d}] {s['start_sec']:6.0f}s  {s['choreo']:<14}  {s['duration']:4.0f}s  n={s['n']}  [{chars_str}]")
    print(f"{'='*60}")
    print(f"  Saved: {path}\n")


def main():
    parser = argparse.ArgumentParser(description="Generate episode scene script")
    parser.add_argument("--duration", type=float, default=30,
                        help="Target duration in minutes (default: 30)")
    parser.add_argument("--theme", default="fruits",
                        help="Character theme (default: fruits)")
    parser.add_argument("--template", default=None,
                        help="Path to scene template YAML")
    parser.add_argument("--output-dir", default=None,
                        help="Output directory (default: config/scripts/)")
    parser.add_argument("--list-choreos", action="store_true",
                        help="List available choreography types and exit")
    args = parser.parse_args()

    if args.list_choreos:
        print("\nAvailable choreography types:")
        for name, desc in CHOREO_DOCS.items():
            print(f"  {name:<16} {desc}")
        print()
        return

    template_path = Path(args.template) if args.template else \
                    ROOT / "config" / "scene_templates" / "default.yaml"
    output_dir = Path(args.output_dir) if args.output_dir else \
                 ROOT / "config" / "scripts"

    out_path = generate_script(
        duration_min=args.duration,
        theme=args.theme,
        template_path=template_path,
        output_dir=output_dir,
    )
    print_script_summary(out_path)


if __name__ == "__main__":
    main()
