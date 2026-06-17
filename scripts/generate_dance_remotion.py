#!/usr/bin/env python3
"""
Generate dance shorts via Remotion DanceSpriteShort composition.
42 videos: 20 animals + 12 fruits + 10 vegetables.

Usage:
  python3 scripts/generate_dance_remotion.py
  python3 scripts/generate_dance_remotion.py --theme animals
  python3 scripts/generate_dance_remotion.py --only bear lion duck
  python3 scripts/generate_dance_remotion.py --lang ar
  python3 scripts/generate_dance_remotion.py --lang ar --theme animals
  python3 scripts/generate_dance_remotion.py --force
"""
import argparse
import json
import subprocess
import sys
import yaml
from datetime import datetime
from pathlib import Path

ROOT     = Path(__file__).resolve().parent.parent
REMOTION = ROOT / "remotion"
QUEUE    = ROOT / "output" / "queue"
QUEUE_AR = ROOT / "output" / "queue_ar"
QUEUE_ID = ROOT / "output" / "queue_id"

sys.path.insert(0, str(ROOT / "scripts"))
from arabic_data import ANIMALS_AR, FRUITS_AR, VEGETABLES_AR
from indonesian_data import ANIMALS_ID, FRUITS_ID, VEGETABLES_ID, dance_meta_id

DATE_STR = datetime.now().strftime("%Y%m%d")

MUSIC_TRACKS = [
    "Carefree.mp3", "Wholesome.mp3", "Merry Go.mp3", "Pinball Spring.mp3",
    "Happy Happy Game Show.mp3", "Quirky Dog.mp3", "Life of Riley.mp3",
]

# ── Sprite configuration per character ────────────────────────────────────────

ANIMALS = {
    "bear":     {"sprite": "animals/bear.png",     "accent": "#E67E22", "bg": "#FFF9E6"},
    "tiger":    {"sprite": "animals/tiger.png",    "accent": "#E74C3C", "bg": "#FFF3E0"},
    "frog":     {"sprite": "animals/frog.png",     "accent": "#27AE60", "bg": "#F1F8E9"},
    "penguin":  {"sprite": "animals/penguin.png",  "accent": "#2980B9", "bg": "#E3F2FD"},
    "lion":     {"sprite": "animals/lion.png",     "accent": "#F39C12", "bg": "#FFFDE7"},
    "panda":    {"sprite": "animals/panda.png",    "accent": "#34495E", "bg": "#FAFAFA"},
    "koala":    {"sprite": "animals/koala.png",    "accent": "#7F8C8D", "bg": "#F5F5F5"},
    "fox":      {"sprite": "animals/fox.png",      "accent": "#E67E22", "bg": "#FFF3E0"},
    "rabbit":   {"sprite": "animals/rabbit.png",   "accent": "#E91E63", "bg": "#FCE4EC"},
    "cow":      {"sprite": "animals/cow.png",      "accent": "#795548", "bg": "#EFEBE9"},
    "duck":     {"sprite": "animals/duck.png",     "accent": "#F9A825", "bg": "#FFFDE7"},
    "pig":      {"sprite": "animals/pig.png",      "accent": "#E91E63", "bg": "#FCE4EC"},
    "elephant": {"sprite": "animals/elephant.png", "accent": "#607D8B", "bg": "#ECEFF1"},
    "monkey":   {"sprite": "animals/monkey.png",   "accent": "#795548", "bg": "#FBE9E7"},
    "dog":      {"sprite": "animals/dog.png",      "accent": "#FF8F00", "bg": "#FFF8E1"},
    "cat":      {"sprite": "animals/cat.png",      "accent": "#8E44AD", "bg": "#F3E5F5"},
    "owl":      {"sprite": "animals/owl.png",      "accent": "#16A085", "bg": "#E0F7FA"},
    "unicorn":  {"sprite": "animals/unicorn.png",  "accent": "#9C27B0", "bg": "#F3E5F5"},
    "dino":     {"sprite": "animals/dino.png",     "accent": "#27AE60", "bg": "#E8F5E9"},
    "parrot":   {"sprite": "animals/parrot.png",   "accent": "#E53935", "bg": "#FFEBEE"},
}

FRUITS = {
    "apple":      {"sprite": "fruits_cartoon/apple.png",      "accent": "#E53935", "bg": "#FFEBEE"},
    "banana":     {"sprite": "fruits_cartoon/banana.png",     "accent": "#F9A825", "bg": "#FFFDE7"},
    "strawberry": {"sprite": "fruits_cartoon/strawberry.png", "accent": "#E91E63", "bg": "#FCE4EC"},
    "watermelon": {"sprite": "fruits_cartoon/watermelon.png", "accent": "#27AE60", "bg": "#E8F5E9"},
    "orange":     {"sprite": "fruits_cartoon/orange.png",     "accent": "#FF7F2A", "bg": "#FFF3E0"},
    "grapes":     {"sprite": "fruits_cartoon/grape.png",      "accent": "#8E44AD", "bg": "#F3E5F5"},
    "pineapple":  {"sprite": "fruits_cartoon/pineapple.png",  "accent": "#F9A825", "bg": "#FFFDE7"},
    "cherry":     {"sprite": "fruits_cartoon/cherry.png",     "accent": "#C62828", "bg": "#FFEBEE"},
    "lemon":      {"sprite": "fruits_cartoon/lemon.png",      "accent": "#F9A825", "bg": "#FFFDE7"},
    "peach":      {"sprite": "fruits_cartoon/peach.png",      "accent": "#FF8A65", "bg": "#FBE9E7"},
    "pear":       {"sprite": "fruits_cartoon/pear.png",       "accent": "#7CB342", "bg": "#F1F8E9"},
    "melon":      {"sprite": "fruits_cartoon/melon.png",      "accent": "#27AE60", "bg": "#E8F5E9"},
}

VEGETABLES = {
    "carrot":   {"sprite": "vegetables_cartoon/carrot.png",   "accent": "#FF7F2A", "bg": "#FFF3E0"},
    "broccoli": {"sprite": "vegetables_cartoon/broccoli.png", "accent": "#27AE60", "bg": "#E8F5E9"},
    "corn":     {"sprite": "vegetables_cartoon/corn.png",     "accent": "#F9A825", "bg": "#FFFDE7"},
    "tomato":   {"sprite": "vegetables_cartoon/tomato.png",   "accent": "#E53935", "bg": "#FFEBEE"},
    "cucumber": {"sprite": "vegetables_cartoon/cucumber.png", "accent": "#27AE60", "bg": "#E8F5E9"},
    "eggplant": {"sprite": "vegetables_cartoon/eggplant.png", "accent": "#8E44AD", "bg": "#F3E5F5"},
    "onion":    {"sprite": "vegetables_cartoon/onion.png",    "accent": "#9C27B0", "bg": "#F3E5F5"},
    "pepper":   {"sprite": "vegetables_cartoon/pepper.png",   "accent": "#E53935", "bg": "#FFEBEE"},
    "potato":   {"sprite": "vegetables_cartoon/potato.png",   "accent": "#795548", "bg": "#EFEBE9"},
    "pumpkin":  {"sprite": "vegetables_cartoon/pumpkin.png",  "accent": "#E67E22", "bg": "#FFF3E0"},
}

# English voiceover (dance) audio map — file paths relative to remotion/public/audio/
AUDIO_EN = {
    # animals — matching existing voiceover files if present
    "bear":     None,
    "tiger":    None,
    "frog":     None,
    "penguin":  None,
    "lion":     None,
    "panda":    None,
    "koala":    None,
    "fox":      None,
    "rabbit":   None,
    "cow":      None,
    "duck":     None,
    "pig":      None,
    "elephant": None,
    "monkey":   None,
    "dog":      None,
    "cat":      None,
    "owl":      None,
    "unicorn":  None,
    "dino":     None,
    "parrot":   None,
    # fruits & vegetables — no dance voiceover yet
}

TITLE_EMOJI = {
    "bear": "🐻", "tiger": "🐯", "frog": "🐸", "penguin": "🐧", "lion": "🦁",
    "panda": "🐼", "koala": "🐨", "fox": "🦊", "rabbit": "🐰", "cow": "🐮",
    "duck": "🦆", "pig": "🐷", "elephant": "🐘", "monkey": "🐒", "dog": "🐶",
    "cat": "🐱", "owl": "🦉", "unicorn": "🦄", "dino": "🦕", "parrot": "🦜",
    "apple": "🍎", "banana": "🍌", "strawberry": "🍓", "watermelon": "🍉",
    "orange": "🍊", "grapes": "🍇", "pineapple": "🍍", "cherry": "🍒",
    "lemon": "🍋", "peach": "🍑", "pear": "🍐", "melon": "🍈",
    "carrot": "🥕", "broccoli": "🥦", "corn": "🌽", "tomato": "🍅",
    "cucumber": "🥒", "eggplant": "🍆", "onion": "🧅", "pepper": "🌶",
    "potato": "🥔", "pumpkin": "🎃",
}


def render(out_path: Path, props: dict) -> bool:
    cmd = [
        "npx", "remotion", "render",
        "src/index.ts", "DanceSpriteShort",
        str(out_path),
        "--props", json.dumps(props),
        "--log", "error",
        "--video-image-format=jpeg",
        "--jpeg-quality=85",
        "--concurrency=4",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REMOTION))
    return result.returncode == 0 and out_path.exists()


def write_meta(name: str, theme: str, out_path: Path):
    emoji = TITLE_EMOJI.get(name, "✨")
    display = name.capitalize()
    meta = {
        "title":       f"{emoji} Dancing {display} | Happy Bear Kids #shorts",
        "description": (
            f"Watch {display} dance and move! 🎵\n"
            f"Fun video for toddlers and kids.\n"
            f"#dancing{display.lower()} #kidsdance #happybearkids #shorts"
        ),
        "tags": [
            f"dancing {display.lower()}", "kids dance", "baby dance",
            "toddler dance", "children songs", "nursery rhymes",
            "happy bear kids", display.lower(), f"{theme} dance",
            "kids music", "dance for kids",
        ],
        "video_type":  "short_dance",
        "theme":       theme,
        "is_short":    True,
        "status":      "public",
    }
    meta_path = out_path.parent / f"meta_{out_path.stem}.yaml"
    with open(meta_path, "w") as f:
        yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


# ── Arabic audio paths (relative to remotion/public/audio/) ──────────────────
def _ar_audio(name: str) -> str | None:
    path = ROOT / "assets" / "audio" / "voiceover" / "ar" / f"ar_dance_{name}.mp3"
    return f"ar/ar_dance_{name}.mp3" if path.exists() else None

# Merged label dicts per language
_LABELS_AR: dict[str, str] = {**ANIMALS_AR, **FRUITS_AR, **VEGETABLES_AR}
_LABELS_ID: dict[str, str] = {**ANIMALS_ID, **FRUITS_ID, **VEGETABLES_ID}


def write_meta_ar(name: str, name_ar: str, theme: str, out_path: Path):
    emoji = TITLE_EMOJI.get(name, "✨")
    theme_ar = {"animals": "الحيوانات", "fruits": "الفواكه",
                "vegetables": "الخضروات"}.get(theme, theme)
    meta = {
        "title":       f"{emoji} رقص {name_ar} | هابي بير كيدز #shorts",
        "description": (
            f"شاهد {name_ar} يرقص! 🎵 فيديو ممتع للأطفال.\n"
            f"#{name_ar} #رقص #أطفال #{theme_ar} #هابي_بير_كيدز #shorts"
        ),
        "tags": [
            name_ar, "رقص", "أطفال", "فيديو قصير", "هابي بير كيدز",
            theme_ar, "تعليم", "مسلٍّ", "shorts",
        ],
        "video_type":  "short_dance",
        "theme":       theme,
        "language":    "ar",
        "is_short":    True,
        "status":      "public",
    }
    meta_path = out_path.parent / f"meta_{out_path.stem}.yaml"
    with open(meta_path, "w") as f:
        yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def write_meta_id(name: str, name_id: str, theme: str, out_path: Path):
    meta = dance_meta_id(name, name_id, theme)
    meta_path = out_path.parent / f"meta_{out_path.stem}.yaml"
    with open(meta_path, "w") as f:
        yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def gen_theme(characters: dict, theme: str, only: set, force: bool, lang: str = "en"):
    queue = {"ar": QUEUE_AR, "id": QUEUE_ID}.get(lang, QUEUE)
    ok = 0
    for i, (name, cfg) in enumerate(characters.items()):
        if only and name not in only:
            continue

        if lang == "ar":
            suffix = f"_{DATE_STR}_ar_remotion"
        elif lang == "id":
            suffix = f"_{DATE_STR}_id_remotion"
        else:
            suffix = f"_{DATE_STR}_remotion"
        out_name = f"short_dance_{name}{suffix}.mp4"
        out_path = queue / out_name
        if out_path.exists() and not force:
            print(f"  [{name}] skip"); continue

        name_ar = _LABELS_AR.get(name, name)
        name_id = _LABELS_ID.get(name, name.capitalize())
        custom_label = {"ar": name_ar, "id": name_id}.get(lang)
        props = {
            "spritePath":    cfg["sprite"],
            "characterName": name.capitalize(),
            "customLabel":   custom_label,
            "audioFile":     _ar_audio(name) if lang == "ar" else AUDIO_EN.get(name),
            "musicFile":     MUSIC_TRACKS[i % len(MUSIC_TRACKS)],
            "bgColor":       cfg["bg"],
            "accentColor":   cfg["accent"],
            "language":      lang if lang in ("ar", "en") else "en",
        }
        label = custom_label or name
        print(f"  [{name:12} → {label}]", end="  ", flush=True)
        if render(out_path, props):
            size = out_path.stat().st_size / 1024 / 1024
            print(f"✓  {size:.1f}MB")
            if lang == "ar":
                write_meta_ar(name, name_ar, theme, out_path)
            elif lang == "id":
                write_meta_id(name, name_id, theme, out_path)
            else:
                write_meta(name, theme, out_path)
            ok += 1
        else:
            print("✗")
    return ok


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--theme", nargs="+",
                        choices=["animals", "fruits", "vegetables", "all"],
                        default=["all"])
    parser.add_argument("--only", nargs="+", help="Render specific characters")
    parser.add_argument("--lang", choices=["en", "ar", "id"], default="en",
                        help="Output language (en=queue/, ar=queue_ar/, id=queue_id/)")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    queue = {"ar": QUEUE_AR, "id": QUEUE_ID}.get(args.lang, QUEUE)
    queue.mkdir(parents=True, exist_ok=True)

    themes = set(args.theme)
    if "all" in themes:
        themes = {"animals", "fruits", "vegetables"}
    only = set(args.only) if args.only else set()

    total_ok = 0
    lang_label = {"ar": "Arabic → queue_ar/", "id": "Indonesian → queue_id/"}.get(
        args.lang, "English → queue/"
    )
    print(f"\nGenerating dance shorts via Remotion [{lang_label}]\n")

    if "animals" in themes:
        print(f"[Animals] {len(ANIMALS)} characters\n")
        total_ok += gen_theme(ANIMALS, "animals", only, args.force, args.lang)

    if "fruits" in themes:
        print(f"\n[Fruits] {len(FRUITS)} characters\n")
        total_ok += gen_theme(FRUITS, "fruits", only, args.force, args.lang)

    if "vegetables" in themes:
        print(f"\n[Vegetables] {len(VEGETABLES)} characters\n")
        total_ok += gen_theme(VEGETABLES, "vegetables", only, args.force, args.lang)

    total = sum([
        len(ANIMALS) if "animals" in themes else 0,
        len(FRUITS)  if "fruits"  in themes else 0,
        len(VEGETABLES) if "vegetables" in themes else 0,
    ])
    print(f"\nDone: {total_ok}/{total}")


if __name__ == "__main__":
    main()
