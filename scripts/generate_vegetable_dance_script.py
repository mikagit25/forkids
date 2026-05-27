#!/usr/bin/env python3
"""Generate a 30-minute vegetable dance video script."""
import yaml
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ALL_VEGETABLES = [
    "carrot", "broccoli", "corn", "eggplant", "tomato",
    "cucumber", "potato", "mushroom", "onion", "pepper",
]

VEGETABLE_NAMES = {
    "carrot": "Carrot", "broccoli": "Broccoli", "corn": "Corn",
    "eggplant": "Eggplant", "tomato": "Tomato", "cucumber": "Cucumber",
    "potato": "Potato", "mushroom": "Mushroom", "onion": "Onion",
    "pepper": "Pepper",
}

BG_COLORS = [
    "#E8F5E9", "#F1F8E9", "#E0F2F1", "#F9FBE7",
    "#FFF9E6", "#E3F2FD", "#FCE4EC", "#F3E5F5",
    "#E0F7FA", "#FFFDE7",
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

    veg_pool = []
    while len(veg_pool) * SCENE_DURATION < total_sec + SCENE_DURATION:
        batch = ALL_VEGETABLES.copy()
        random.shuffle(batch)
        veg_pool.extend(batch)

    choreo_pool = SOLO_CHOREOS * (len(veg_pool) // len(SOLO_CHOREOS) + 1)
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

        veg = veg_pool[scene_idx % len(veg_pool)]
        choreo = choreo_pool[scene_idx % len(choreo_pool)]
        bg = BG_COLORS[scene_idx % len(BG_COLORS)]
        name = VEGETABLE_NAMES.get(veg, veg.capitalize())

        scenes.append({
            "start_sec": round(t, 1),
            "duration": round(dur, 1),
            "choreo": choreo,
            "n": 1,
            "chars": [veg],
            "entry": "zoom_in",
            "bg_color": bg,
            "text": name,
            "sub_text": "Let's dance!",
        })

        t += dur
        scene_idx += 1

    return {
        "video_type": "dance",
        "theme": "vegetables",
        "duration_minutes": duration_minutes,
        "style": "tutitu",
        "scenes": scenes,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=int, default=30)
    parser.add_argument("--output", default="config/scripts/dance_vegetables.yaml")
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    script = generate_script(args.duration, args.seed)
    out = ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        yaml.dump(script, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print(f"Script → {out}")
    print(f"Scenes: {len(script['scenes'])} vegetables × {SCENE_DURATION}s = {args.duration} min")
    for s in script["scenes"]:
        mins = int(s['start_sec']) // 60
        secs = int(s['start_sec']) % 60
        print(f"  {mins:02d}:{secs:02d}  {s['chars'][0]:<12}  {s['choreo']}")


if __name__ == "__main__":
    main()
