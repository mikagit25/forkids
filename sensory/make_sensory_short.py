"""Generate a 45-second 9:16 sensory short for the Happy Bear Kids EN channel.

Renders a solo fruit character on black in 1080×1920 — native vertical format,
no cropping. Music is code-made (sensory.music). Output goes to output/queue/.

Usage:
    cd /opt/kids_channel/sensory
    python3 make_sensory_short.py
    python3 make_sensory_short.py --genre disco --seed 42
    python3 make_sensory_short.py --queue-dir /tmp/sq   # test
"""
from __future__ import annotations

import argparse
import datetime
import json
import random
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sensory"))

from sensory import music
from sensory.characters import CHARACTERS
from sensory.render import compose
from sensory.easing import beat_phase, dance_pose
from sensory.render import beatmap_phase

QUEUE = ROOT / "output" / "queue"
FONT = ROOT / "assets" / "fonts" / "BebasNeue-Regular.ttf"

SHORT_SECS = 45
FPS = 30
W, H = 1080, 1920   # 9:16 vertical

GENRE_LABEL = {
    "disco":    "Disco Beat",
    "calypso":  "Island Vibes",
    "march":    "Toy Parade",
    "bounce":   "Bounce Party",
}

TITLE_TMPL = "Dancing Fruits — {label} 🍓 Sensory Video for Babies #Shorts"

DESCRIPTION_TMPL = """🍓 {character_name} dances to cheerful {style} music in this fun sensory short for babies and toddlers!

Bright colours on a dark background, smooth beat-locked movement and no talking — perfect for visual stimulation anywhere, any time.

Watch together, clap along and name the fruit! Keep screen time short for the youngest viewers.

🎵 Original music composed and synthesized by Happy Bear Kids — every note made in code, © 2026.
🎨 Original characters and animation by Happy Bear Kids.

Subscribe for full dance parties, counting videos and sleepy lullabies every week! 🐻💛

#sensoryvideo #babysensory #dancingfruit #toddlervideo #kidsmusic #happybearkids #shorts #babyvideo #infantstimulation #sensoryplay #visualstimulation #babydance #fruitdance #babymusic #toddlermusic"""


def render_short(out: Path, bmap: dict, character: str, seed: int):
    """Render a 45s vertical video: single character, solo centered in 1080×1920."""
    ch = CHARACTERS[character](seed=seed)
    # Center of the 1080×1920 frame, slightly above middle for visual balance
    cx, cy, r = W // 2, int(H * 0.48), int(min(W, H) * 0.30)

    cmd = ["ffmpeg", "-loglevel", "error", "-y",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p",
           "-movflags", "+faststart", str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    moves = ["bounce", "sway", "stretch"]
    move = moves[seed % len(moves)]
    energy = 0.8

    for f in range(int(SHORT_SECS * FPS)):
        t = f / FPS
        b, ph = beatmap_phase(bmap, t, 0.0)
        pose = dance_pose(b, ph, move, energy)
        frame = compose([(ch, cx, cy, r, pose)], W, H, t)
        p.stdin.write(frame.tobytes())

    p.stdin.close()
    if p.wait():
        raise RuntimeError("ffmpeg render failed")


def add_audio(video: Path, audio_wav: Path, out: Path):
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-y",
         "-i", str(video), "-i", str(audio_wav),
         "-t", str(SHORT_SECS), "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
         "-shortest", str(out)],
        check=True)


def make_thumbnail(path: Path, character: str, label: str, seed: int):
    w, h = 1080, 1920
    rnd = random.Random(seed)
    THUMB_BG = [
        ((70, 0, 120), (255, 40, 140)),
        ((0, 60, 140), (0, 200, 220)),
        ((120, 20, 0), (255, 170, 0)),
        ((10, 90, 30), (150, 230, 40)),
    ]
    inner, outer = rnd.choice(THUMB_BG)
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt(((xx - w / 2) / (w * 0.6)) ** 2 + ((yy - h * 0.45) / (h * 0.75)) ** 2).clip(0, 1)[..., None]
    bg = (np.array(outer, np.float32) * (1 - d) + np.array(inner, np.float32) * d)

    ch = CHARACTERS[character](seed=1)
    r = int(min(w, h) * 0.30)
    items = [(ch, w // 2, int(h * 0.42), r, {"smile": 1.3, "tilt": 5, "happy": True})]
    fg = compose(items, w, h, 0.0, rgba=True)
    img = Image.fromarray((fg[..., :3] * 255 + bg * (1 - fg[..., 3:4])).clip(0, 255).astype(np.uint8))

    dr = ImageDraw.Draw(img)
    try:
        font_big = ImageFont.truetype(str(FONT), 100)
        font_sm = ImageFont.truetype(str(FONT), 60)
    except OSError:
        font_big = font_sm = ImageFont.load_default()

    # Top tag
    tag = "HAPPY BEAR KIDS"
    tw = dr.textlength(tag, font=font_sm)
    x = (w - tw) / 2
    dr.text((x, 60), tag, font=font_sm, fill=(255, 245, 120))

    # Bottom label
    text = label.upper()
    tw = dr.textlength(text, font=font_big)
    x = (w - tw) / 2
    y = h - 220
    for dx, dy in ((-4, 0), (4, 0), (0, -4), (0, 4)):
        dr.text((x + dx, y + dy), text, font=font_big, fill=(40, 10, 60))
    dr.text((x, y), text, font=font_big, fill=(255, 245, 120))

    # #Shorts badge
    badge = "#SHORTS"
    tw = dr.textlength(badge, font=font_sm)
    x = (w - tw) / 2
    dr.text((x, h - 130), badge, font=font_sm, fill=(255, 100, 150))

    img.save(path, "PNG", optimize=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--genre", choices=list(GENRE_LABEL), default=None)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--queue-dir", default=str(QUEUE))
    a = ap.parse_args()

    seed = a.seed if a.seed is not None else int(datetime.datetime.now().timestamp()) % 100000
    rnd = random.Random(seed)
    genre = a.genre or rnd.choice(list(GENRE_LABEL))
    q = Path(a.queue_dir)
    q.mkdir(parents=True, exist_ok=True)
    today = f"{datetime.date.today():%Y%m%d}"
    stem = f"sensory_short_{genre}_{today}_{seed}"

    # Generate 45s of music (plan truncated to SHORT_SECS)
    wav = q / f"{stem}.wav"
    print(f"♪ generating {genre} music …")
    bmap = music.render(music.plan(genre, seed, SHORT_SECS + 4), wav)
    print(f"  {bmap['bpm']:.0f} BPM")

    # Pick character
    character = rnd.choice(list(CHARACTERS))

    # Render video (no audio)
    tmp_vid = q / f"{stem}_noaudio.mp4"
    print(f"🎬 rendering {character} ({W}×{H}, {SHORT_SECS}s) …")
    render_short(tmp_vid, bmap, character, seed)

    # Mux audio
    mp4 = q / f"{stem}.mp4"
    add_audio(tmp_vid, wav, mp4)
    tmp_vid.unlink(missing_ok=True)
    wav.unlink(missing_ok=True)
    wav.with_suffix(".json").unlink(missing_ok=True)

    # Thumbnail
    label = GENRE_LABEL[genre]
    thumb = q / f"thumb_{stem}.png"
    make_thumbnail(thumb, character, label, seed)

    # Meta
    import yaml
    char_name = character.replace("blueberry", "blueberry").title()
    style_map = {"disco": "disco", "calypso": "steel drum", "march": "marching", "bounce": "dance"}
    meta = {
        "title": TITLE_TMPL.format(label=label)[:100],
        "description": DESCRIPTION_TMPL.format(
            character_name=char_name,
            style=style_map.get(genre, "dance"),
        ),
        "tags": ["sensory video", "baby sensory", "dancing fruit", "toddler video", "kids music",
                 "fruit dance", "high contrast baby", "baby video", "sensory short", "happy bear kids",
                 "visual stimulation", "babies music", "sensory play", "#shorts"],
        "video_type": "sensory_short",
        "language": "en",
        "is_short": True,
        "status": "public",
        "made_for_kids": True,
        "ai_generated": False,
        "music_source": "procedural",
        "seed": seed,
        "genre": genre,
        "duration_sec": SHORT_SECS,
    }
    (q / f"meta_{stem}.yaml").write_text(yaml.dump(meta, allow_unicode=True, sort_keys=False))

    print(f"✅ {mp4}")
    print(f"   {meta['title']}")


if __name__ == "__main__":
    main()
