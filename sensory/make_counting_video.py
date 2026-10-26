"""Generate a Counting 1-10 sensory video for Happy Bear Kids EN.

Each number gets its own scene: the fruit appears one-by-one, a big number
flashes on screen, then all fruits do a group dance at the end.

Format: landscape 1920×1080, ~4 min, code-made march/bounce music.
Output: output/queue/  (mp4 + meta + thumbnail)

Usage:
    cd /opt/kids_channel/sensory
    python3 make_counting_video.py
    python3 make_counting_video.py --seed 42 --genre march
    python3 make_counting_video.py --queue-dir /tmp/cq   # test
"""
from __future__ import annotations

import argparse
import datetime
import json
import math
import random
import subprocess
import sys
from pathlib import Path

import cairo
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sensory"))

from sensory import music as M
from sensory.characters import CHARACTERS, FAMILIES
from sensory.render import compose, beatmap_phase
from sensory.easing import dance_pose

QUEUE = ROOT / "output" / "queue"
FONT = ROOT / "assets" / "fonts" / "BebasNeue-Regular.ttf"

FPS = 30
W, H = 1920, 1080
BARS_PER_NUMBER = 8       # 8 bars per digit scene
BARS_FINALE     = 16      # group dance at the end
GENRES          = ["march", "bounce", "calypso"]

NUMBER_COLORS = [
    (1.0, 0.22, 0.22),   # 1 red
    (1.0, 0.58, 0.08),   # 2 orange
    (1.0, 0.90, 0.08),   # 3 yellow
    (0.18, 0.82, 0.25),  # 4 green
    (0.08, 0.72, 0.95),  # 5 cyan
    (0.20, 0.35, 1.00),  # 6 blue
    (0.68, 0.15, 1.00),  # 7 purple
    (1.00, 0.30, 0.75),  # 8 pink
    (0.95, 0.65, 0.10),  # 9 gold
    (0.95, 0.95, 0.95),  # 10 white
]


def _draw_number(frame: np.ndarray, number: int, alpha: float, r: float = 280):
    """Overlay a large digit on the frame (top-right area), RGBA blending."""
    img = Image.fromarray(frame)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(overlay)
    try:
        font = ImageFont.truetype(str(FONT), int(r))
    except OSError:
        font = ImageFont.load_default()
    text = str(number)
    tw = dr.textlength(text, font=font)
    x, y = W - tw - 60, 40
    col = NUMBER_COLORS[(number - 1) % len(NUMBER_COLORS)]
    a = int(alpha * 255)
    # Shadow
    for dx, dy in ((-6, 0), (6, 0), (0, -6), (0, 6)):
        dr.text((x + dx, y + dy), text, font=font, fill=(20, 10, 40, a))
    dr.text((x, y), text, font=font,
            fill=(int(col[0]*255), int(col[1]*255), int(col[2]*255), a))
    result = Image.alpha_composite(img.convert("RGBA"), overlay)
    return np.array(result.convert("RGB"))


def render_counting(out: Path, bmap: dict, cast_pool: list[str], seed: int):
    """Render the full counting video: 1 char per number, then finale."""
    rnd = random.Random(seed)
    chars_used = rnd.sample(cast_pool, min(10, len(cast_pool)))
    # Pad if pool smaller than 10
    while len(chars_used) < 10:
        chars_used.append(rnd.choice(cast_pool))

    beat_s = bmap["beat_s"]
    bars_per_beat = 4
    scene_dur = beat_s * bars_per_beat * BARS_PER_NUMBER
    finale_dur = beat_s * bars_per_beat * BARS_FINALE
    total_sec = scene_dur * 10 + finale_dur

    # Build character instances once
    instances = {n: CHARACTERS[n](seed=i + 1) for i, n in enumerate(cast_pool)}

    cmd = ["ffmpeg", "-loglevel", "error", "-y",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
           "-movflags", "+faststart", str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    for f in range(int(total_sec * FPS)):
        t = f / FPS

        if t < scene_dur * 10:
            # Counting scenes: show characters 1, 1+2, 1+2+3 …
            scene_idx = int(t / scene_dur)        # which number (0-based)
            t_in_scene = t - scene_idx * scene_dur
            n_shown = scene_idx + 1               # how many chars on screen

            items = []
            spacing = W / (n_shown + 1)
            for i in range(n_shown):
                name = chars_used[i]
                ch = instances[name]
                cx = spacing * (i + 1)
                cy = H * 0.52
                r = min(200, int(spacing * 0.38))
                b, ph = beatmap_phase(bmap, t, i * 0.25)
                move = "bounce" if i % 2 == 0 else "sway"
                pose = dance_pose(b, ph, move, 0.85)
                items.append((ch, cx, cy, r, pose))

            frame = compose(items, W, H, t)

            # Number overlay — fade in first 0.4s, fade out last 0.4s
            fade_in  = min(1.0, t_in_scene / (beat_s * 2))
            fade_out = min(1.0, (scene_dur - t_in_scene) / (beat_s * 2))
            alpha = fade_in * fade_out
            frame = _draw_number(frame, scene_idx + 1, alpha)
        else:
            # Finale: all 10 characters dance together
            t_fin = t - scene_dur * 10
            items = []
            for i, name in enumerate(chars_used):
                ch = instances[name]
                row, col = divmod(i, 5)
                cx = W * (col + 0.7) / 6
                cy = H * (0.32 + row * 0.42)
                r = 140
                b, ph = beatmap_phase(bmap, t_fin, i * 0.15)
                pose = dance_pose(b, ph, "bounce", 1.0)
                items.append((ch, cx, cy, r, pose))
            frame = compose(items, W, H, t_fin)

        p.stdin.write(frame.tobytes())

    p.stdin.close()
    if p.wait():
        raise RuntimeError("ffmpeg render failed")


def mux_audio(video: Path, audio_wav: Path, out: Path, total_sec: float):
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-y",
         "-i", str(video), "-i", str(audio_wav),
         "-t", str(total_sec), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-shortest", str(out)],
        check=True)


def make_thumbnail(path: Path, cast: list[str], seed: int):
    from sensory.episode import THUMB_BG
    w, h = 1280, 720
    rnd = random.Random(seed)
    inner, outer = rnd.choice(THUMB_BG)
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt(((xx - w / 2) / (w * 0.6)) ** 2 + ((yy - h * 0.45) / (h * 0.75)) ** 2).clip(0, 1)[..., None]
    bg = np.array(outer, np.float32) * (1 - d) + np.array(inner, np.float32) * d

    picks = cast[:3]
    items = []
    for i, (name, x, r) in enumerate(zip(picks, (290, 640, 990), (165, 200, 165))):
        ch = CHARACTERS[name](seed=i + 1)
        pose = {"smile": 1.3, "tilt": (-10, 0, 10)[i], "happy": i == 1}
        items.append((ch, x, 330 if i != 1 else 290, r, pose))
    fg = compose(items, w, h, 0.0, rgba=True)
    img = Image.fromarray((fg[..., :3] * 255 + bg * (1 - fg[..., 3:4])).clip(0, 255).astype(np.uint8))

    dr = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(str(FONT), 110)
    except OSError:
        font = ImageFont.load_default()
    text = "1 2 3 4 5..."
    tw = dr.textlength(text, font=font)
    x, y = (w - tw) / 2, h - 160
    for dx, dy in ((-5, 0), (5, 0), (0, -5), (0, 5)):
        dr.text((x + dx, y + dy), text, font=font, fill=(40, 10, 60))
    dr.text((x, y), text, font=font, fill=(255, 245, 120))
    img.save(path, "PNG", optimize=True)


DESCRIPTION_TMPL = """🔢 Count to 10 with colourful fruit friends! {names} pop onto the screen one by one as we count from 1 to 10 together — perfect for babies, toddlers and preschoolers learning their first numbers.

Each number brings a new dancing fruit friend! Watch as {first} arrives first, then more join until all 10 are dancing together in the big finale.

How to watch together:
• Point to each fruit as it appears and say the number out loud
• Clap along to the beat as you count
• Try counting backwards after: 10, 9, 8…!

Why counting videos help:
• Early number sense starts with hearing and seeing numbers repeated in a fun, low-pressure context
• Bright colours and fun characters make learning feel like play, not work
• The beat helps little ones feel rhythm and sequence naturally, building early maths intuition

🎵 Original music composed and synthesized by Happy Bear Kids — every note made in code, © 2026.
🎨 Original characters and animation by Happy Bear Kids.

Subscribe for more sensory dance parties, lullabies and learning videos every week! 🐻💛

#countingfor kids #babysensory #1to10 #learnnumbers #toddlerlearning #kidsmusic #happybearkids #sensoryvideo #numbersfor toddlers #educationalvideo #babyvideo #preschool #earlylearning #countingvideo"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--genre", choices=GENRES, default=None)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--family", choices=["fruits", "veggies", "all"], default="all")
    ap.add_argument("--queue-dir", default=str(QUEUE))
    a = ap.parse_args()

    seed = a.seed if a.seed is not None else int(datetime.datetime.now().timestamp()) % 100000
    rnd = random.Random(seed)
    genre = a.genre or rnd.choice(GENRES)
    q = Path(a.queue_dir)
    q.mkdir(parents=True, exist_ok=True)
    today = f"{datetime.date.today():%Y%m%d}"
    stem = f"sensory_counting_{genre}_{today}_{seed}"

    # Pool from chosen family
    import yaml
    from sensory.characters import FAMILIES
    pool = FAMILIES.get(a.family, FAMILIES["all"])

    # Music — enough bars for all 10 scenes + finale
    beat_s_approx = 60 / 108  # ~march tempo
    target_sec = beat_s_approx * 4 * (BARS_PER_NUMBER * 10 + BARS_FINALE) + 4
    wav = q / f"{stem}.wav"
    print(f"♪ generating {genre} music ({target_sec:.0f}s) …")
    bmap = M.render(M.plan(genre, seed, target_sec), wav)
    print(f"  {bmap['bpm']:.0f} BPM, {bmap['duration']:.0f}s")

    beat_s = bmap["beat_s"]
    scene_dur = beat_s * 4 * BARS_PER_NUMBER
    finale_dur = beat_s * 4 * BARS_FINALE
    total_sec = scene_dur * 10 + finale_dur

    cast_pool = list(pool)
    rnd.shuffle(cast_pool)

    tmp_vid = q / f"{stem}_noaudio.mp4"
    print(f"🎬 rendering counting video {W}×{H}, {total_sec:.0f}s …")
    render_counting(tmp_vid, bmap, cast_pool, seed)

    mp4 = q / f"{stem}.mp4"
    mux_audio(tmp_vid, wav, mp4, total_sec)
    tmp_vid.unlink(missing_ok=True)
    wav.unlink(missing_ok=True)
    wav.with_suffix(".json").unlink(missing_ok=True)

    chars_used = rnd.sample(cast_pool, min(10, len(cast_pool)))
    names = ", ".join(c.title() for c in chars_used[:5]) + " and friends"
    thumb = q / f"thumb_{stem}.png"
    make_thumbnail(thumb, chars_used, seed)

    minutes = total_sec / 60
    dur_str = f"{int(round(minutes))} Minutes"
    meta = {
        "title": f"Count 1 to 10 🔢 Sensory Counting Video for Babies & Toddlers • {dur_str}"[:100],
        "description": DESCRIPTION_TMPL.format(
            names=", ".join(c.title() for c in chars_used),
            first=chars_used[0].title(),
        ),
        "tags": ["counting for kids", "baby sensory", "learn to count", "1 to 10", "toddler learning",
                 "kids music", "sensory video", "happy bear kids", "numbers for toddlers",
                 "educational video", "baby video", "preschool numbers", "counting song",
                 "early learning"],
        "video_type": "sensory_counting",
        "language": "en",
        "is_short": False,
        "status": "public",
        "made_for_kids": True,
        "ai_generated": False,
        "music_source": "procedural",
        "seed": seed,
        "genre": genre,
        "duration_sec": int(total_sec),
    }
    (q / f"meta_{stem}.yaml").write_text(yaml.dump(meta, allow_unicode=True, sort_keys=False))
    print(f"✅ {mp4}")
    print(f"   {meta['title']}  ({len(meta['description'].split())} words)")


if __name__ == "__main__":
    main()
