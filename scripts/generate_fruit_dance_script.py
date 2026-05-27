#!/usr/bin/env python3
"""
Generate a 30-minute fruit dance video script.
Style: TutiTuTV-inspired — one large fruit per scene, light background,
fruit name shown, smooth entry, calm fun music.
"""
import yaml
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ALL_FRUITS = [
    "apple", "banana", "strawberry", "grapes", "watermelon", "orange",
    "pineapple", "cherry", "peach", "lemon", "pear", "melon",
]

FRUIT_NAMES = {
    "apple": "Apple", "banana": "Banana", "strawberry": "Strawberry",
    "grapes": "Grapes", "watermelon": "Watermelon", "orange": "Orange",
    "pineapple": "Pineapple", "cherry": "Cherry", "peach": "Peach",
    "lemon": "Lemon", "pear": "Pear", "melon": "Melon",
}

BG_COLORS = [
    "#FFF9E6", "#E8F5E9", "#E3F2FD", "#FCE4EC",
    "#F3E5F5", "#E0F7FA", "#FFFDE7", "#F9FBE7",
    "#FFF3E0", "#E8EAF6", "#F1F8E9", "#FFF8E1",
]

SOLO_CHOREOS = [
    "solo_bounce", "solo_sway", "solo_spin", "solo_wave",
    "solo_jump", "solo_twist", "solo_nod", "solo_shimmy",
]

SCENE_DURATION = 38


def generate_script(duration_minutes: int = 30, seed: int = None) -> dict:
    if seed is not None:
        random.seed(seed)

    total_sec = duration_minutes * 60
    scenes = []
    t = 0.0
    scene_idx = 0

    fruits_pool = []
    while len(fruits_pool) * SCENE_DURATION < total_sec + SCENE_DURATION:
        batch = ALL_FRUITS.copy()
        random.shuffle(batch)
        fruits_pool.extend(batch)

    choreo_pool = SOLO_CHOREOS * (len(fruits_pool) // len(SOLO_CHOREOS) + 1)
    random.shuffle(choreo_pool)
    for i in range(1, len(choreo_pool)):
        if choreo_pool[i] == choreo_pool[i-1]:
            for j in range(i+1, len(choreo_pool)):
                if choreo_pool[j] != choreo_pool[i-1]:
                    choreo_pool[i], choreo_pool[j] = choreo_pool[j], choreo_pool[i]
                    break

    while t < total_sec:
        dur = min(SCENE_DURATION, total_sec - t)
        if dur < 10:
            break

        fruit = fruits_pool[scene_idx % len(fruits_pool)]
        choreo = choreo_pool[scene_idx % len(choreo_pool)]
        bg = BG_COLORS[scene_idx % len(BG_COLORS)]
        name = FRUIT_NAMES.get(fruit, fruit.capitalize())

        scenes.append({
            "start_sec": round(t, 1),
            "duration": round(dur, 1),
            "choreo": choreo,
            "n": 1,
            "chars": [fruit],
            "entry": "zoom_in",
            "bg_color": bg,
            "text": name,
            "sub_text": "Let's dance!",
        })

        t += dur
        scene_idx += 1

    return {
        "video_type": "dance",
        "theme": "fruits",
        "duration_minutes": duration_minutes,
        "style": "tutitu",
        "scenes": scenes,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--output", default="config/scripts/dance_fruits.yaml")
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    script = generate_script(args.duration, args.seed)
    out = ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        yaml.dump(script, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print(f"Script → {out}")
    print(f"Scenes: {len(script['scenes'])} fruits × {SCENE_DURATION}s = {args.duration} min")
    for s in script["scenes"]:
        mins = int(s['start_sec']) // 60
        secs = int(s['start_sec']) % 60
        print(f"  {mins:02d}:{secs:02d}  {s['chars'][0]:<12}  {s['choreo']}")


if __name__ == "__main__":
    main()
