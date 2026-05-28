#!/usr/bin/env python3
"""
Generate 30-min MIXED dance script — alternates between animals, fruits, vegetables.
Creates variety: different themes in one video, different choreographies.
"""
import yaml
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ALL_CHARS = {
    "animals":    ["bear", "tiger", "frog", "penguin", "lion", "panda", "koala", "fox",
                   "rabbit", "cow", "duck", "pig", "elephant", "monkey", "dog",
                   "cat", "owl", "unicorn", "dino", "parrot"],
    "fruits":     ["apple", "banana", "strawberry", "grapes", "watermelon", "orange",
                   "pineapple", "cherry", "peach", "lemon", "pear", "melon"],
    "vegetables": ["carrot", "broccoli", "corn", "eggplant", "tomato",
                   "cucumber", "potato", "mushroom", "onion", "pepper"],
}

NAMES = {
    **{k: k.capitalize() for k in ALL_CHARS["animals"]},
    **{k: k.capitalize() for k in ALL_CHARS["fruits"]},
    **{k: k.capitalize() for k in ALL_CHARS["vegetables"]},
}
NAMES["dino"] = "Dino"

# Varied pastel backgrounds — more variety than single-theme scripts
BG_COLORS = [
    "#FFF9E6", "#E8F5E9", "#E3F2FD", "#FCE4EC", "#F3E5F5",
    "#E0F7FA", "#FFFDE7", "#F9FBE7", "#FFF3E0", "#E8EAF6",
    "#F1F8E9", "#FFF8E1", "#E0F2F1", "#EDE7F6", "#E1F5FE",
]

SOLO_CHOREOS = [
    "solo_bounce", "solo_sway", "solo_spin", "solo_wave",
    "solo_jump", "solo_twist", "solo_nod", "solo_shimmy",
]

SCENE_DURATION = 38


def generate_mixed_script(duration_minutes: int = 30, mode: str = "interleave",
                          seed: int = None) -> dict:
    """
    mode='interleave': animals → fruit → vegetable → animal → ...
    mode='blocks':     all animals first, then fruits, then vegetables
    mode='random':     fully random mix
    """
    if seed is not None:
        random.seed(seed)

    total_sec = duration_minutes * 60

    # Build character pool based on mode
    if mode == "interleave":
        pool = []
        a = ALL_CHARS["animals"].copy()
        f = ALL_CHARS["fruits"].copy()
        v = ALL_CHARS["vegetables"].copy()
        random.shuffle(a); random.shuffle(f); random.shuffle(v)
        themes_cycle = []
        while len(pool) * SCENE_DURATION < total_sec + SCENE_DURATION:
            for char, theme in [(a[len(pool)//3 % len(a)], "animals"),
                                (f[len(pool)//3 % len(f)], "fruits"),
                                (v[len(pool)//3 % len(v)], "vegetables")]:
                pool.append((char, theme))
    elif mode == "blocks":
        pool = []
        for theme, chars in ALL_CHARS.items():
            shuffled = chars.copy()
            random.shuffle(shuffled)
            for c in shuffled:
                pool.append((c, theme))
        while len(pool) * SCENE_DURATION < total_sec + SCENE_DURATION:
            pool.extend(pool[:3])
    else:  # random
        all_flat = [(c, t) for t, chars in ALL_CHARS.items() for c in chars]
        random.shuffle(all_flat)
        pool = all_flat * 3

    choreo_pool = SOLO_CHOREOS * (len(pool) // len(SOLO_CHOREOS) + 2)
    random.shuffle(choreo_pool)
    for i in range(1, len(choreo_pool)):
        if choreo_pool[i] == choreo_pool[i-1]:
            for j in range(i+1, len(choreo_pool)):
                if choreo_pool[j] != choreo_pool[i-1]:
                    choreo_pool[i], choreo_pool[j] = choreo_pool[j], choreo_pool[i]
                    break

    scenes = []
    t = 0.0
    for i, (char, theme) in enumerate(pool):
        if t >= total_sec:
            break
        dur = min(SCENE_DURATION, total_sec - t)
        if dur < 10:
            break
        scenes.append({
            "start_sec": round(t, 1),
            "duration": round(dur, 1),
            "choreo": choreo_pool[i % len(choreo_pool)],
            "n": 1,
            "chars": [char],
            "entry": "zoom_in",
            "bg_color": BG_COLORS[i % len(BG_COLORS)],
            "text": NAMES.get(char, char.capitalize()),
            "sub_text": "Let's dance!",
        })
        t += dur

    return {
        "video_type": "dance",
        "theme": "mixed",
        "duration_minutes": duration_minutes,
        "style": "tutitu",
        "mode": mode,
        "scenes": scenes,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--mode", choices=["interleave", "blocks", "random"],
                        default="interleave")
    parser.add_argument("--output", default=None)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    script = generate_mixed_script(args.duration, args.mode, args.seed)
    name = args.output or f"config/scripts/dance_mixed_{args.mode}.yaml"
    out = ROOT / name
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        yaml.dump(script, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print(f"Script → {out}  ({len(script['scenes'])} scenes, mode={args.mode})")
    for s in script["scenes"]:
        mins, secs = divmod(int(s["start_sec"]), 60)
        print(f"  {mins:02d}:{secs:02d}  {s['chars'][0]:<12}  {s['choreo']}")


if __name__ == "__main__":
    main()
