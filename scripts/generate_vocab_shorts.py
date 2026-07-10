#!/usr/bin/env python3
"""
Generate vocabulary ABC shorts using Remotion (React/Chromium renderer).
Produces 1080×1920 portrait shorts with clean web fonts and PNG sprites.
Output: output/queue/short_vocab_{letter}_{date}.mp4

Usage:
  python3 scripts/generate_vocab_shorts.py
  python3 scripts/generate_vocab_shorts.py --letters A B C
  python3 scripts/generate_vocab_shorts.py --force   # overwrite existing
"""
import argparse
import json
import subprocess
import sys
import yaml
from datetime import datetime
from pathlib import Path

ROOT        = Path(__file__).resolve().parent.parent
REMOTION    = ROOT / "remotion"
SCENE_ID    = "VocabularyShort"
QUEUE_DIR   = ROOT / "output" / "queue"
SPRITES     = ROOT / "assets" / "sprites_new"

MUSIC_TRACKS = [
    "Wholesome.mp3", "Carefree.mp3", "Heartwarming.mp3", "Gymnopedie No 1.mp3",
    "Fluffing a Duck.mp3", "Crinoline Dreams.mp3", "Walking Along.mp3",
]

LETTERS = {
    "A": {"word": "APPLE",      "audio": "a__apple__a_is_for_apple.mp3",
          "sprite": "fruits_cartoon/apple.png",    "color": "#E53935", "bg": "#E8F5E9"},
    "B": {"word": "BANANA",     "audio": "b__banana__b_is_for_banana.mp3",
          "sprite": "fruits_cartoon/banana.png",   "color": "#F9A825", "bg": "#FFF9C4"},
    "C": {"word": "CAT",        "audio": "c__cat__c_is_for_cat.mp3",
          "sprite": "animals_3d/cat.png",     "color": "#F57C00", "bg": "#FFF3E0"},
    "D": {"word": "DOG",        "audio": "d__dog__d_is_for_dog.mp3",
          "sprite": "animals/dog.png",        "color": "#6D4C41", "bg": "#EFEBE9"},
    "E": {"word": "ELEPHANT",   "audio": "e__elephant__e_is_for_elephant.mp3",
          "sprite": "animals_3d/elephant.png","color": "#546E7A", "bg": "#ECEFF1"},
    "F": {"word": "FROG",       "audio": "f__frog__f_is_for_frog.mp3",
          "sprite": "animals/frog.png",       "color": "#2E7D32", "bg": "#E8F5E9"},
    "G": {"word": "GIRAFFE",    "audio": "g__giraffe__g_is_for_giraffe.mp3",
          "sprite": None,                     "color": "#F9A825", "bg": "#FFFDE7"},
    "H": {"word": "HIPPO",      "audio": "h__hippo__h_is_for_hippo.mp3",
          "sprite": None,                     "color": "#7B1FA2", "bg": "#F3E5F5"},
    "I": {"word": "IGLOO",      "audio": "i__igloo__i_is_for_igloo.mp3",
          "sprite": None,                     "color": "#1565C0", "bg": "#E3F2FD"},
    "J": {"word": "JELLYFISH",  "audio": "j__jellyfish__j_is_for_jellyfish.mp3",
          "sprite": "objects/jellyfish_glow.png", "color": "#C2185B", "bg": "#FCE4EC"},
    "K": {"word": "KOALA",      "audio": "k__koala__k_is_for_koala.mp3",
          "sprite": "animals/koala.png",      "color": "#546E7A", "bg": "#ECEFF1"},
    "L": {"word": "LION",       "audio": "l__lion__l_is_for_lion.mp3",
          "sprite": "animals_3d/lion.png",    "color": "#E65100", "bg": "#FFF3E0"},
    "M": {"word": "MONKEY",     "audio": "m__monkey__m_is_for_monkey.mp3",
          "sprite": "animals/monkey.png",     "color": "#5D4037", "bg": "#EFEBE9"},
    "N": {"word": "NEST",       "audio": "n__nest__n_is_for_nest.mp3",
          "sprite": None,                     "color": "#4E342E", "bg": "#FFF8E1"},
    "O": {"word": "OWL",        "audio": "o__owl__o_is_for_owl.mp3",
          "sprite": "animals/owl.png",        "color": "#4527A0", "bg": "#EDE7F6"},
    "P": {"word": "PENGUIN",    "audio": "p__penguin__p_is_for_penguin.mp3",
          "sprite": "animals/penguin.png",    "color": "#1A237E", "bg": "#E8EAF6"},
    "Q": {"word": "QUEEN",      "audio": "q__queen__q_is_for_queen.mp3",
          "sprite": None,                     "color": "#6A1B9A", "bg": "#F3E5F5"},
    "R": {"word": "RABBIT",     "audio": "r__rabbit__r_is_for_rabbit.mp3",
          "sprite": "animals/rabbit.png",     "color": "#AD1457", "bg": "#FCE4EC"},
    "S": {"word": "STAR",       "audio": "s__star__s_is_for_star.mp3",
          "sprite": "objects/star_3d.png",   "color": "#F57F17", "bg": "#FFFDE7"},
    "T": {"word": "TIGER",      "audio": "t__tiger__t_is_for_tiger.mp3",
          "sprite": "animals/tiger.png",      "color": "#E65100", "bg": "#FFF3E0"},
    "U": {"word": "UMBRELLA",   "audio": "u__umbrella__u_is_for_umbrella.mp3",
          "sprite": None,                     "color": "#0277BD", "bg": "#E1F5FE"},
    "V": {"word": "VIOLIN",     "audio": "v__violin__v_is_for_violin.mp3",
          "sprite": None,                     "color": "#6A1B9A", "bg": "#EDE7F6"},
    "W": {"word": "WATERMELON", "audio": "w__watermelon__w_is_for_watermelon.mp3",
          "sprite": "fruits_cartoon/watermelon.png", "color": "#2E7D32", "bg": "#E8F5E9"},
    "X": {"word": "XYLOPHONE",  "audio": "x__xylophone__x_is_for_xylophone.mp3",
          "sprite": None,                     "color": "#C62828", "bg": "#FFEBEE"},
    "Y": {"word": "YAK",        "audio": "y__yak__y_is_for_yak.mp3",
          "sprite": None,                     "color": "#558B2F", "bg": "#F1F8E9"},
    "Z": {"word": "ZEBRA",      "audio": "z__zebra__z_is_for_zebra.mp3",
          "sprite": None,                     "color": "#212121", "bg": "#FAFAFA"},
}


def make_meta(letter: str, word: str, out_path: Path):
    word_cap = word.capitalize()
    description = (
        f"🅰️ Letter {letter} — {letter} is for {word_cap}! 🐻\n\n"
        f"Join Happy Bear Kids and learn the letter {letter} with a fun and colourful animation! "
        f"In this short, we explore the letter {letter} and the word {word_cap}. "
        f"Perfect for toddlers and preschoolers learning the alphabet for the first time.\n\n"
        f"🌟 What you'll learn:\n"
        f"• The letter {letter} — uppercase and lowercase\n"
        f"• The word {word_cap} and how it starts with {letter}\n"
        f"• Letter sounds and phonics for beginners\n"
        f"• Alphabet recognition for preschool children\n\n"
        f"👶 Perfect for:\n"
        f"• Toddlers aged 2-5 learning their ABCs\n"
        f"• Preschool and kindergarten letter practice\n"
        f"• Parents looking for short, focused learning videos\n"
        f"• Early childhood educators in the classroom\n\n"
        f"🎵 Gentle background music keeps children engaged without overstimulation. "
        f"Each video is short and focused — just the right length for little attention spans!\n\n"
        f"Subscribe to Happy Bear Kids for the full A-Z alphabet series and many more fun learning videos. "
        f"New videos every week! 🐻\n\n"
        f"#HappyBearKids #ABCforkids #Letter{letter} #{word_cap} #AlphabetForKids "
        f"#LearnABC #Preschool #ToddlerLearning #KidsEducation #PhonicsForKids"
    )
    meta = {
        "title":            f"Letter {letter} | {letter} is for {word_cap} | ABC for Kids | Happy Bear Kids #shorts",
        "description":      description,
        "video_type":       "short_vocab",
        "theme":            "abc",
        "language":         "en",
        "duration_minutes": 1,
        "is_short":         True,
        "made_for_kids":    True,
        "tags":             [
            "abc", "alphabet", f"letter {letter.lower()}", word.lower(),
            f"{letter} is for {word_cap}", "kids learning", "abc for kids",
            "letters for toddlers", "preschool", "happy bear kids",
            "educational", "shorts", "phonics", "vocabulary",
        ],
        "status":           "public",
    }
    meta_path = out_path.parent / f"meta_{out_path.stem}.yaml"
    with open(meta_path, "w") as f:
        yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def render_letter(letter: str, date_str: str, force: bool) -> bool:
    data      = LETTERS[letter]
    out_name  = f"short_vocab_{letter.lower()}_{date_str}.mp4"
    out_path  = QUEUE_DIR / out_name

    if out_path.exists() and not force:
        print(f"  [{letter}] skip (exists)")
        return True

    sprite_exists = data["sprite"] and (SPRITES / data["sprite"]).exists()
    has_sprite    = "sprite" if sprite_exists else "shape "
    print(f"  [{letter}={data['word']:<10}] {has_sprite}", end="  ", flush=True)

    letter_idx = list(LETTERS.keys()).index(letter)
    props = {
        "letter":      letter,
        "word":        data["word"],
        "spritePath":  data["sprite"] if sprite_exists else None,
        "audioFile":   data["audio"],
        "letterColor": data["color"],
        "bgColor":     data["bg"],
        "musicFile":   MUSIC_TRACKS[letter_idx % len(MUSIC_TRACKS)],
    }

    cmd = [
        "npx", "remotion", "render",
        "src/index.ts",
        SCENE_ID,
        str(out_path),
        "--props", json.dumps(props),
        "--log", "error",
        "--video-image-format=jpeg",
        "--jpeg-quality=85",
        "--concurrency=4",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REMOTION))
    if result.returncode == 0 and out_path.exists():
        size_mb = out_path.stat().st_size / 1024 / 1024
        print(f"✓ {out_name}  {size_mb:.1f}MB")
        make_meta(letter, data["word"], out_path)
        return True
    else:
        err = (result.stderr or result.stdout)[-300:].strip()
        print(f"✗  {err}")
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--letters", nargs="+", default=list(LETTERS.keys()),
                        help="Letters to generate, e.g. A B C")
    parser.add_argument("--force", action="store_true", help="Overwrite existing")
    args = parser.parse_args()

    letters  = [l.upper() for l in args.letters if l.upper() in LETTERS]
    date_str = datetime.now().strftime("%Y%m%d")
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\nGenerating {len(letters)} vocabulary shorts (Remotion) → {QUEUE_DIR}\n")

    ok = 0
    for letter in letters:
        if render_letter(letter, date_str, args.force):
            ok += 1

    print(f"\nDone: {ok}/{len(letters)} vocabulary shorts generated")


if __name__ == "__main__":
    main()
