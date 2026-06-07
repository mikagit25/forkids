#!/usr/bin/env python3
"""
Generate a YAML script for a 30-min shapes dance video.
Usage: python3 generate_shapes_script.py --theme rainbow --duration 30 --seed 42
"""
import argparse
import random
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CHOREOS = [
    "bounce_row", "carousel", "size_pulse", "color_morph",
    "scatter_gather", "follow_path", "rain", "spin_zoom",
    "mirror_pair", "wave_grid",
    "pendulum", "orbit_layers", "popcorn", "heartbeat", "breathing", "snake_line",
]

SHAPES = ["circle", "square", "triangle", "hexagon", "star", "mixed",
          "ellipse", "diamond", "pentagon", "cross"]

PALETTES = {
    "rainbow": ["#FF4444", "#FF7F2A", "#FFD700", "#27AE60", "#2980B9", "#8E44AD", "#FF69B4"],
    "pastel":  ["#FFB3BA", "#FFDFBA", "#FFFFBA", "#BAFFC9", "#BAE1FF", "#E8BAFF", "#FFDAF0"],
    "warm":    ["#FF4444", "#FF7F2A", "#FFD700", "#FF69B4", "#FF6B35", "#FFA500", "#FF3D68"],
    "cool":    ["#2980B9", "#27AE60", "#8E44AD", "#00CED1", "#4169E1", "#20B2AA", "#5DADE2"],
    "neon":    ["#FF00FF", "#00FF41", "#00FFFF", "#FF4500", "#FFD700", "#FF1493", "#7FFF00"],
    "candy":   ["#FF6EB4", "#FF85A1", "#FFB347", "#FFEC6E", "#B5EAD7", "#C7CEEA", "#FF9AA2"],
    "ocean":   ["#006994", "#0099CC", "#00CED1", "#20B2AA", "#48CAE4", "#90E0EF", "#ADE8F4"],
    "earth":   ["#8B4513", "#D2691E", "#CD853F", "#DEB887", "#228B22", "#6B8E23", "#556B2F"],
    "sunset":  ["#FF4500", "#FF6347", "#FF7F50", "#FFD700", "#DA70D6", "#9400D3", "#FF1493"],
}

BG_COLORS = [
    "#FFF9E6", "#E8F5E9", "#E3F2FD", "#FCE4EC", "#F3E5F5",
    "#E0F7FA", "#FFFDE7", "#F9FBE7", "#FFF3E0", "#E8EAF6",
    "#F1F8E9", "#FFF8E1", "#E0F2F1", "#EDE7F6", "#E1F5FE",
]

TITLES = {
    "rainbow": "🌈 Rainbow Shapes Dance Party 30 Minutes | Happy Bear Kids",
    "pastel":  "🩷 Pastel Shapes for Babies 30 Minutes | Happy Bear Kids",
    "warm":    "🔥 Warm Colors Shapes Dance 30 Minutes | Happy Bear Kids",
    "cool":    "💙 Cool Shapes Dance Party 30 Minutes | Happy Bear Kids",
    "neon":    "✨ Neon Shapes Dance Party 30 Minutes | Happy Bear Kids",
    "candy":   "🍭 Candy Shapes Dance 30 Minutes | Happy Bear Kids",
    "ocean":   "🌊 Ocean Shapes Dance 30 Minutes | Happy Bear Kids",
    "earth":   "🌿 Earth Colors Shapes Dance 30 Minutes | Happy Bear Kids",
    "sunset":  "🌅 Sunset Shapes Dance Party 30 Minutes | Happy Bear Kids",
}

TAGS_BASE = ["shapes", "kids dance", "30 minutes", "baby dance", "toddler",
             "happy bear kids", "shapes for kids", "children songs", "colorful shapes"]

SCENE_DURATION = 40  # seconds per choreography scene


def generate(theme: str, duration_min: int, seed: int) -> dict:
    rng = random.Random(seed)
    colors = PALETTES[theme]
    total_sec = duration_min * 60
    n_scenes = total_sec // SCENE_DURATION

    # Build sequence: no same choreo twice in a row, rotate shapes
    choreo_pool = []
    while len(choreo_pool) < n_scenes + 5:
        c = rng.choice(CHOREOS)
        if not choreo_pool or choreo_pool[-1] != c:
            choreo_pool.append(c)

    shape_pool = []
    while len(shape_pool) < n_scenes + 5:
        s = rng.choice(SHAPES)
        if not shape_pool or shape_pool[-1] != s:
            shape_pool.append(s)

    scenes = []
    for i in range(n_scenes):
        choreo = choreo_pool[i]
        shape  = shape_pool[i]
        n      = rng.choice([3, 4, 5, 6, 7, 8])
        size   = rng.choice([0.55, 0.65, 0.75, 0.85])
        bg     = BG_COLORS[i % len(BG_COLORS)]

        # Some choreos work better with specific n values
        if choreo in ("mirror_pair",):
            n = rng.choice([2, 3, 4])
        elif choreo in ("wave_grid",):
            n = 15  # 3x5 grid
        elif choreo in ("size_pulse",):
            n = rng.choice([1, 3, 5])

        # Rotate color palette slice for variety
        offset = rng.randint(0, len(colors) - 1)
        scene_colors = colors[offset:] + colors[:offset]

        scenes.append({
            "choreo":     choreo,
            "shape":      shape,
            "n":          n,
            "colors":     scene_colors,
            "bg_color":   bg,
            "duration":   SCENE_DURATION,
            "size":       size,
        })

    tags = TAGS_BASE + [theme, "shapes dance"]

    return {
        "video_type":       "shape_dance",
        "title":            TITLES.get(theme, f"Shapes Dance Party | Happy Bear Kids"),
        "theme":            theme,
        "duration_minutes": duration_min,
        "tags":             tags,
        "seed":             seed,
        "scenes":           scenes,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--theme",    default="rainbow", choices=list(PALETTES) + ["all"])
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--seed",     type=int, default=42)
    parser.add_argument("--output",   default=None)
    args = parser.parse_args()

    script = generate(args.theme, args.duration, args.seed)
    out_name = args.output or f"config/scripts/shapes_{args.theme}.yaml"
    out = ROOT / out_name
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        yaml.dump(script, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print(f"Script → {out}  ({len(script['scenes'])} scenes × {SCENE_DURATION}s)")
    for s in script["scenes"][:5]:
        print(f"  {s['choreo']:<16} {s['shape']:<10} n={s['n']}  {s['bg_color']}")
    print("  ...")


if __name__ == "__main__":
    main()
