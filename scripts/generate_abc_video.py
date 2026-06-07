#!/usr/bin/env python3
"""
Generate a full A-Z ABC long video (~24 min) for kids.
Renders each of 26 letters as a ~55s segment using the ABC Manim scene,
concatenates them, and adds background music.

Usage:
  python3 scripts/generate_abc_video.py
  python3 scripts/generate_abc_video.py --quality m
"""
import argparse
import json
import random
import shutil
import subprocess
import sys
import tempfile
import yaml
from datetime import datetime
from pathlib import Path

ROOT        = Path(__file__).resolve().parent.parent
SCENE_FILE  = ROOT / "scripts" / "manim_abc_scene.py"
PARAMS_TMP  = Path("/tmp/manim_abc_params.json")
QUEUE_DIR   = ROOT / "output" / "queue"
AUDIO_DIR   = ROOT / "assets" / "audio" / "voiceover" / "en"
MUSIC_DIR   = ROOT / "assets" / "music" / "kevin"
SPRITES     = ROOT / "assets" / "sprites_new"

DANCE_TRACKS = [
    "Monkeys Spinning Monkeys.mp3", "Quirky Dog.mp3", "Merry Go.mp3",
    "Happy Happy Game Show.mp3", "Carefree.mp3", "Hyperfun.mp3",
    "Overworld.mp3", "Pinball Spring.mp3", "Sneaky Snitch.mp3", "Wholesome.mp3",
    "Life of Riley.mp3", "Walking Along.mp3", "Heartwarming.mp3",
]

# Same letter data as ABC shorts generator
LETTERS = {
    "A": {"word": "APPLE",      "audio": "a__apple__a_is_for_apple.mp3",
          "sprite": "fruits/apple.png",       "color": "#E53935", "bg": "#E8F5E9"},
    "B": {"word": "BANANA",     "audio": "b__banana__b_is_for_banana.mp3",
          "sprite": "fruits/banana.png",      "color": "#F9A825", "bg": "#FFF9C4"},
    "C": {"word": "CAT",        "audio": "c__cat__c_is_for_cat.mp3",
          "sprite": "animals/cat.png",        "color": "#F57C00", "bg": "#FFF3E0"},
    "D": {"word": "DOG",        "audio": "d__dog__d_is_for_dog.mp3",
          "sprite": "animals/dog.png",        "color": "#6D4C41", "bg": "#EFEBE9"},
    "E": {"word": "ELEPHANT",   "audio": "e__elephant__e_is_for_elephant.mp3",
          "sprite": "animals/elephant.png",   "color": "#546E7A", "bg": "#ECEFF1"},
    "F": {"word": "FROG",       "audio": "f__frog__f_is_for_frog.mp3",
          "sprite": "animals/frog.png",       "color": "#2E7D32", "bg": "#E8F5E9"},
    "G": {"word": "GIRAFFE",    "audio": "g__giraffe__g_is_for_giraffe.mp3",
          "sprite": None,                     "color": "#F9A825", "bg": "#FFFDE7"},
    "H": {"word": "HIPPO",      "audio": "h__hippo__h_is_for_hippo.mp3",
          "sprite": None,                     "color": "#7B1FA2", "bg": "#F3E5F5"},
    "I": {"word": "IGLOO",      "audio": "i__igloo__i_is_for_igloo.mp3",
          "sprite": None,                     "color": "#1565C0", "bg": "#E3F2FD"},
    "J": {"word": "JELLYFISH",  "audio": "j__jellyfish__j_is_for_jellyfish.mp3",
          "sprite": None,                     "color": "#C2185B", "bg": "#FCE4EC"},
    "K": {"word": "KOALA",      "audio": "k__koala__k_is_for_koala.mp3",
          "sprite": "animals/koala.png",      "color": "#546E7A", "bg": "#ECEFF1"},
    "L": {"word": "LION",       "audio": "l__lion__l_is_for_lion.mp3",
          "sprite": "animals/lion.png",       "color": "#E65100", "bg": "#FFF3E0"},
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
          "sprite": None,                     "color": "#F57F17", "bg": "#FFFDE7"},
    "T": {"word": "TIGER",      "audio": "t__tiger__t_is_for_tiger.mp3",
          "sprite": "animals/tiger.png",      "color": "#E65100", "bg": "#FFF3E0"},
    "U": {"word": "UMBRELLA",   "audio": "u__umbrella__u_is_for_umbrella.mp3",
          "sprite": None,                     "color": "#0277BD", "bg": "#E1F5FE"},
    "V": {"word": "VIOLIN",     "audio": "v__violin__v_is_for_violin.mp3",
          "sprite": None,                     "color": "#6A1B9A", "bg": "#EDE7F6"},
    "W": {"word": "WATERMELON", "audio": "w__watermelon__w_is_for_watermelon.mp3",
          "sprite": "fruits/watermelon.png",  "color": "#2E7D32", "bg": "#E8F5E9"},
    "X": {"word": "XYLOPHONE",  "audio": "x__xylophone__x_is_for_xylophone.mp3",
          "sprite": None,                     "color": "#C62828", "bg": "#FFEBEE"},
    "Y": {"word": "YAK",        "audio": "y__yak__y_is_for_yak.mp3",
          "sprite": None,                     "color": "#558B2F", "bg": "#F1F8E9"},
    "Z": {"word": "ZEBRA",      "audio": "z__zebra__z_is_for_zebra.mp3",
          "sprite": None,                     "color": "#212121", "bg": "#FAFAFA"},
}

TOTAL_DUR  = 55.0
AUDIO_TIMES = [1.0, 19.0, 37.5]


def pick_music() -> Path | None:
    tracks = DANCE_TRACKS.copy()
    random.shuffle(tracks)
    for name in tracks:
        p = MUSIC_DIR / name
        if p.exists() and p.stat().st_size > 1000:
            return p
    return None


def render_letter(letter: str, out: Path, quality: str) -> bool:
    data = LETTERS[letter]
    sprite_path = None
    if data["sprite"]:
        sp = SPRITES / data["sprite"]
        if sp.exists():
            sprite_path = str(sp)

    params = {
        "letter":         letter,
        "word":           data["word"],
        "letter_color":   data["color"],
        "bg_color":       data["bg"],
        "sprite_path":    sprite_path,
        "vertical":       False,  # landscape for long video
        "total_duration": TOTAL_DUR,
    }
    PARAMS_TMP.write_text(json.dumps(params))

    media_dir = out.parent / f"_manim_abc_{letter}_tmp"
    cmd = [
        "manim", f"-q{quality}",
        "--media_dir", str(media_dir),
        "--disable_caching",
        str(SCENE_FILE), "ABCScene",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"\n  [manim error {letter}] {result.stderr[-300:]}")
        shutil.rmtree(media_dir, ignore_errors=True)
        return False

    rendered = list(media_dir.rglob("ABCScene.mp4"))
    if not rendered:
        shutil.rmtree(media_dir, ignore_errors=True)
        return False
    shutil.copy2(rendered[0], out)
    shutil.rmtree(media_dir, ignore_errors=True)
    return True


def build_letter_audio(letter: str, tmpdir: Path) -> Path | None:
    data = LETTERS[letter]
    audio_file = AUDIO_DIR / data["audio"]
    if not audio_file.exists():
        return None

    out = tmpdir / f"voice_{letter}.wav"
    inputs = []
    filter_parts = []
    for j, t in enumerate(AUDIO_TIMES):
        delay_ms = int(t * 1000)
        inputs += ["-i", str(audio_file)]
        filter_parts.append(f"[{j}]adelay={delay_ms}|{delay_ms}[a{j}]")

    amix_in = "".join(f"[a{j}]" for j in range(3))
    filter_str = (
        ";".join(filter_parts)
        + f";{amix_in}amix=inputs=3:duration=longest,"
        + f"apad=whole_dur={TOTAL_DUR}[out]"
    )

    cmd = [
        "ffmpeg", "-y", *inputs,
        "-filter_complex", filter_str,
        "-map", "[out]",
        "-t", str(TOTAL_DUR),
        str(out),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not out.exists():
        return None
    return out


def combine_letter(video: Path, voice: Path | None, out: Path) -> bool:
    if voice is None:
        shutil.copy2(video, out)
        return True
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video), "-i", str(voice),
        "-map", "0:v", "-map", "1:a",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
        "-shortest", str(out),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode == 0 and out.exists()


def concat_segments(segments: list[Path], tmpdir: Path) -> Path | None:
    concat_list = tmpdir / "concat.txt"
    concat_list.write_text("\n".join(f"file '{p}'" for p in segments))
    out = tmpdir / "full_concat.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(out),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return out if r.returncode == 0 and out.exists() else None


def add_music(video: Path, music: Path, output: Path) -> bool:
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video),
        "-stream_loop", "-1", "-i", str(music),
        "-filter_complex",
        "[0:a]volume=1.0[vo];[1:a]volume=0.15[mus];[vo][mus]amix=inputs=2:duration=first[aout]",
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest", str(output),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode == 0 and output.exists()


def make_meta(out_path: Path):
    duration_min = round(len(LETTERS) * TOTAL_DUR / 60)
    meta = {
        "title":            "ABC Alphabet for Kids | A to Z | Learn Letters | Happy Bear Kids",
        "video_type":       "abc",
        "theme":            "abc",
        "duration_minutes": duration_min,
        "is_short":         False,
        "tags":             [
            "abc", "alphabet", "learn letters", "abc for kids", "a to z",
            "alphabet song", "preschool", "kindergarten", "phonics",
            "kids learning", "happy bear kids", "educational", "letter names",
        ],
        "status":           "public",
    }
    meta_path = out_path.parent / f"meta_{out_path.stem}.yaml"
    with open(meta_path, "w") as f:
        yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--letters",  nargs="+", default=list(LETTERS.keys()),
                        help="Letters to include, e.g. A B C")
    parser.add_argument("--quality", default="m", choices=["l", "m", "h"])
    args = parser.parse_args()

    letters = [l.upper() for l in args.letters if l.upper() in LETTERS]
    date_str = datetime.now().strftime("%Y%m%d")
    out_name = f"abc_az_{date_str}.mp4"
    out_path  = QUEUE_DIR / out_name

    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    tmpdir = Path(tempfile.mkdtemp(prefix="abc_video_"))

    print(f"\nGenerating ABC A-Z video ({len(letters)} letters) → {out_name}\n")

    segments = []
    for letter in letters:
        data = LETTERS[letter]
        has_sprite = bool(data["sprite"] and (SPRITES / data["sprite"]).exists())
        print(f"  [{letter}={data['word']:<10}] {'sprite' if has_sprite else 'shape ':6}", end="  ", flush=True)

        raw = tmpdir / f"raw_{letter}.mp4"
        if not render_letter(letter, raw, args.quality):
            print("✗ render failed")
            continue

        voice_out = tmpdir / f"seg_{letter}.mp4"
        voice = build_letter_audio(letter, tmpdir)
        if combine_letter(raw, voice, voice_out):
            segments.append(voice_out)
            print(f"✓")
        else:
            segments.append(raw)
            print(f"✓ (no audio)")

    if not segments:
        print("No segments. Aborting.")
        shutil.rmtree(tmpdir, ignore_errors=True)
        return

    print(f"\nConcatenating {len(segments)} letter segments...")
    full = concat_segments(segments, tmpdir)
    if not full:
        print("Concat failed.")
        shutil.rmtree(tmpdir, ignore_errors=True)
        return

    music = pick_music()
    if music:
        print(f"Adding music: {music.name}")
        if not add_music(full, music, out_path):
            shutil.copy2(full, out_path)
    else:
        shutil.copy2(full, out_path)

    shutil.rmtree(tmpdir, ignore_errors=True)

    if out_path.exists():
        size_mb = out_path.stat().st_size / 1024 / 1024
        dur_min  = len(segments) * TOTAL_DUR / 60
        print(f"\n✓ {out_name}  {size_mb:.1f}MB  (~{dur_min:.0f} min)")
        make_meta(out_path)
    else:
        print("\n✗ Output not created")


if __name__ == "__main__":
    main()
