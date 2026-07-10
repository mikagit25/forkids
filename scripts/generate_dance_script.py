#!/usr/bin/env python3
"""
Generate a 30-minute dance video script.
Style: TutiTuTV-inspired — one large animal per scene, light background,
animal name shown, smooth entry/exit, calm fun music.
"""
import yaml
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ALL_ANIMALS = [
    "bear", "tiger", "frog", "penguin", "lion",
    "panda", "koala", "fox", "rabbit", "cow",
    "duck", "pig", "elephant", "monkey", "dog",
    "cat", "owl", "unicorn", "dino", "parrot",
    "blue_whale", "crow", "flamingo", "polar_bear",
]

ANIMAL_NAMES = {
    "bear": "Bear",         "tiger": "Tiger",      "frog": "Frog",
    "penguin": "Penguin",   "lion": "Lion",         "panda": "Panda",
    "koala": "Koala",       "fox": "Fox",           "rabbit": "Rabbit",
    "cow": "Cow",           "duck": "Duck",         "pig": "Pig",
    "elephant": "Elephant", "monkey": "Monkey",     "dog": "Dog",
    "cat": "Cat",           "owl": "Owl",           "unicorn": "Unicorn",
    "dino": "Dino",         "parrot": "Parrot",
    "blue_whale": "Whale",  "crow": "Crow",         "flamingo": "Flamingo",
    "polar_bear": "Polar Bear",
}

# Light pastel backgrounds — one per animal slot
BG_COLORS = [
    "#FFF9E6", "#E8F5E9", "#E3F2FD", "#FCE4EC",
    "#F3E5F5", "#E0F7FA", "#FFFDE7", "#F9FBE7",
    "#FFF3E0", "#E8EAF6", "#F1F8E9", "#FFF8E1",
    "#E0F2F1", "#FCE4EC", "#E8F5E9", "#EDE7F6",
    "#E1F5FE", "#F9FBE7", "#FFF9E6", "#E3F2FD",
]

# Dance moves for single-character scenes
SOLO_CHOREOS = [
    "solo_bounce",   # classic up-down bounce
    "solo_sway",     # gentle left-right sway
    "solo_spin",     # slow rotation + bounce
    "solo_wave",     # body wave / pulse
    "solo_jump",     # big jump sequence
    "solo_twist",    # twisting hips
    "solo_nod",      # head-nod style
    "solo_shimmy",   # fast side vibration
]

SCENE_DURATION = 38   # seconds per animal


def generate_script(duration_minutes: int = 30, seed: int = None) -> dict:
    if seed is not None:
        random.seed(seed)

    total_sec = duration_minutes * 60
    scenes = []
    t = 0.0
    scene_idx = 0

    # Build full animal playlist — cycle through all, shuffle each round
    animals_pool = []
    while len(animals_pool) * SCENE_DURATION < total_sec + SCENE_DURATION:
        batch = ALL_ANIMALS.copy()
        random.shuffle(batch)
        animals_pool.extend(batch)

    choreo_pool = SOLO_CHOREOS * (len(animals_pool) // len(SOLO_CHOREOS) + 1)
    random.shuffle(choreo_pool)
    # No two same choreos in a row
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

        animal = animals_pool[scene_idx % len(animals_pool)]
        choreo = choreo_pool[scene_idx % len(choreo_pool)]
        bg = BG_COLORS[scene_idx % len(BG_COLORS)]
        name = ANIMAL_NAMES.get(animal, animal.capitalize())

        scenes.append({
            "start_sec": round(t, 1),
            "duration": round(dur, 1),
            "choreo": choreo,
            "n": 1,
            "chars": [animal],
            "entry": "zoom_in",      # animal zooms in from small
            "bg_color": bg,
            "text": name,            # shown large on screen
            "sub_text": "Let's dance!",
        })

        t += dur
        scene_idx += 1

    return {
        "video_type": "dance",
        "theme": "animals",
        "duration_minutes": duration_minutes,
        "style": "tutitu",
        "scenes": scenes,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--output", default="config/scripts/dance_animals.yaml")
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    script = generate_script(args.duration, args.seed)
    out = ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        yaml.dump(script, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print(f"Script → {out}")
    print(f"Scenes: {len(script['scenes'])} animals × {SCENE_DURATION}s = {args.duration} min")
    for s in script["scenes"]:
        mins = int(s['start_sec']) // 60
        secs = int(s['start_sec']) % 60
        print(f"  {mins:02d}:{secs:02d}  {s['chars'][0]:<10}  {s['choreo']}")


if __name__ == "__main__":
    main()
