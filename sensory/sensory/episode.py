"""One command → a finished Happy Bear Kids sensory episode in the EN queue (step 8).

  music (code, new seed) → choreography (cast changes every section) → parallel render
  → thumbnail (3 characters big on a bright background + short text) → meta (made_for_kids: true)
  → output/queue/sensory_<format>_<genre>_<date>_<seed>.{mp4,png} + meta_….yaml

Usage (from the sensory/ folder):
  python3 -m sensory.episode --genre calypso --minutes 12
  python3 -m sensory.episode --minutes 2 --queue-dir out/q        # quick test, not the real queue
"""
from __future__ import annotations

import argparse
import datetime
import json
import random
from pathlib import Path

import numpy as np
import yaml
from PIL import Image, ImageDraw, ImageFont

from . import music
from .characters import CHARACTERS
from .render import compose, render_episode

ROOT = Path(__file__).resolve().parents[2]            # forkids/
QUEUE = ROOT / "output" / "queue"
FONT = ROOT / "assets" / "fonts" / "BebasNeue-Regular.ttf"
LOG = Path(__file__).resolve().parents[1] / "episodes" / "episode_log.jsonl"

GENRE_WORDS = {"disco": ("Disco", "disco dance"), "calypso": ("Island Beats", "steel drum music"),
               "march": ("Toy Parade", "marching music"), "bounce": ("Bounce Party", "dance music"),
               "lullaby": ("Sleepy Lullaby", "lullaby")}
THUMB_BG = [((70, 0, 120), (255, 40, 140)), ((0, 60, 140), (0, 200, 220)), ((120, 20, 0), (255, 170, 0)),
            ((10, 90, 30), (150, 230, 40)), ((40, 0, 90), (120, 80, 255))]


def title_for(genre: str, minutes: float, n: int) -> str:
    word = GENRE_WORDS[genre][0]
    dur = f"{int(minutes)} Minutes" if minutes < 60 else f"{int(minutes // 60)} Hour"
    return f"Dancing Fruit {word} 🍓 Sensory Video for Babies & Toddlers • {dur}"[:100]


def description_for(genre: str, minutes: float, cast: list[str]) -> str:
    names = ", ".join(sorted({c.replace('blueberry', 'blueberry').title() for c in cast}))
    word, style = GENRE_WORDS[genre]
    text = f"""🍓 Happy fruit friends dance to cheerful {style}! {names} bounce, wiggle and giggle on a calm black background — perfect visual stimulation for babies and toddlers.

This {int(minutes)}-minute sensory video uses bright, high-contrast colours on black, big friendly characters and smooth movements that follow the beat of the music. Every few bars the dancers change: solos, duets, trios, a wave, a conga line and a big party finale. There is no talking and no text, so little ones anywhere in the world can enjoy it.

Why parents use sensory videos:
• Bright colours on a dark background are easy for young eyes to see
• Gentle, rhythmic movement holds attention without being overwhelming
• Happy music for dancing, playtime, tummy time or a calm moment together

Tips: watch together, clap along on the beat and name the fruits and colours as they appear. Keep screen time short for the youngest viewers and enjoy the music as background play.

🎵 Original music composed and synthesized by Happy Bear Kids — every note made in code, © 2026.
🎨 Original characters and animation by Happy Bear Kids.

Subscribe for new dance parties, counting videos and sleepy lullabies every week! 🐻💛

#sensoryvideo #babysensory #dancingfruit #toddlervideos #kidsmusic #happybearkids"""
    return text


def thumbnail(path: Path, cast: list[str], text: str, seed: int):
    w, h = 1280, 720
    rnd = random.Random(seed)
    inner, outer = rnd.choice(THUMB_BG)
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt(((xx - w / 2) / (w * 0.6)) ** 2 + ((yy - h * 0.45) / (h * 0.75)) ** 2).clip(0, 1)[..., None]
    bg = (np.array(outer, np.float32) * (1 - d) + np.array(inner, np.float32) * d)
    picks = cast[:3]
    items = []
    for i, (name, x, r) in enumerate(zip(picks, (290, 640, 990), (165, 200, 165))):
        ch = CHARACTERS[name](seed=i + 1)
        items.append((ch, x, 330 if i != 1 else 290, r, {"smile": 1.3, "tilt": (-10, 0, 10)[i], "happy": i == 1}))
    fg = compose(items, w, h, 0.0, rgba=True)                              # premultiplied RGBA
    img = Image.fromarray((fg[..., :3] * 255 + bg * (1 - fg[..., 3:4])).clip(0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(str(FONT), 120)
    except OSError:
        font = ImageFont.load_default()
    tw = dr.textlength(text, font=font)
    x, y = (w - tw) / 2, h - 165
    for dx, dy in ((-5, 0), (5, 0), (0, -5), (0, 5), (4, 4), (-4, 4), (4, -4), (-4, -4)):
        dr.text((x + dx, y + dy), text, font=font, fill=(40, 10, 60))
    dr.text((x, y), text, font=font, fill=(255, 245, 120))
    img.save(path, "PNG", optimize=True)


def main():
    ap = argparse.ArgumentParser(description="Sensory dance episode → EN kids queue")
    ap.add_argument("--genre", choices=[g for g in music.GENRES if g != "lullaby"], default=None)
    ap.add_argument("--minutes", type=float, default=12)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--queue-dir", default=str(QUEUE))
    ap.add_argument("--workers", type=int, default=None)
    a = ap.parse_args()
    seed = a.seed if a.seed is not None else int(datetime.datetime.now().timestamp()) % 100000
    rnd = random.Random(seed)
    genre = a.genre or rnd.choice(["disco", "calypso", "march", "bounce"])
    q = Path(a.queue_dir); q.mkdir(parents=True, exist_ok=True)
    stem = f"sensory_dance_{genre}_{datetime.date.today():%Y%m%d}_{seed}"
    wav = q / f"{stem}.wav"
    song = music.plan(genre, seed, a.minutes * 60)
    bmap = music.render(song, wav)
    print(f"♪ {genre} {bmap['bpm']:.0f} BPM, {bmap['duration'] / 60:.1f} min")
    scenes = render_episode(q / f"{stem}.mp4", str(wav), list(CHARACTERS), seed, workers=a.workers)
    cast = [s.name for sc in scenes for s in sc.slots]
    thumbnail(q / f"thumb_{stem}.png", list(dict.fromkeys(cast)), "FRUIT DANCE PARTY", seed)
    meta = {"title": title_for(genre, a.minutes, len(scenes)), "description": description_for(genre, a.minutes, cast),
            "tags": ["sensory video", "baby sensory", "dancing fruit", "toddler video", "kids music",
                     "fruit dance", "high contrast baby", "baby video", "dance party for kids", "happy bear kids",
                     "visual stimulation", "babies music", f"{GENRE_WORDS[genre][1]} for kids"],
            "video_type": "sensory_dance", "language": "en", "is_short": False, "status": "public",
            "made_for_kids": True, "ai_generated": False, "music_source": "procedural",
            "seed": seed, "genre": genre, "bpm": bmap["bpm"], "duration_sec": int(bmap["duration"])}
    (q / f"meta_{stem}.yaml").write_text(yaml.dump(meta, allow_unicode=True, sort_keys=False))
    wav.unlink(missing_ok=True); wav.with_suffix(".json").unlink(missing_ok=True)
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a") as f:
        f.write(json.dumps({"stem": stem, "seed": seed, "genre": genre, "key": bmap["key"],
                            "progression": bmap["progression"], "cast": sorted(set(cast))}) + "\n")
    print(f"✅ {q / (stem + '.mp4')}\n   {meta['title']}  ({len(meta['description'].split())} words)")


if __name__ == "__main__":
    main()
