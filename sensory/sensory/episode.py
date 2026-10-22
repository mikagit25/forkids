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
import subprocess
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


def thumbnail(path: Path, cast: list[str], text: str, seed: int, sleepy: bool = False):
    w, h = 1280, 720
    rnd = random.Random(seed)
    inner, outer = ((5, 10, 40), (40, 60, 140)) if sleepy else rnd.choice(THUMB_BG)
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt(((xx - w / 2) / (w * 0.6)) ** 2 + ((yy - h * 0.45) / (h * 0.75)) ** 2).clip(0, 1)[..., None]
    bg = (np.array(outer, np.float32) * (1 - d) + np.array(inner, np.float32) * d)
    picks = cast[:3]
    items = []
    for i, (name, x, r) in enumerate(zip(picks, (290, 640, 990), (165, 200, 165))):
        ch = CHARACTERS[name](seed=i + 1)
        pose = {"smile": 0.3, "tilt": (-8, 0, 8)[i], "sleepy": True} if sleepy else \
            {"smile": 1.3, "tilt": (-10, 0, 10)[i], "happy": i == 1}
        items.append((ch, x, 330 if i != 1 else 290, r, pose))
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


SUNO_DIR = ROOT / "assets" / "audio" / "suno"
SD_CODE_DIR = ROOT / "sacred_drift" / "audio" / "code_ambient"
AUDIO_EXT = (".mp3", ".wav", ".flac", ".m4a", ".ogg")


def used_sources() -> set[str]:
    if not LOG.exists():
        return set()
    out = set()
    for line in LOG.read_text().splitlines():
        try:
            out.add(json.loads(line).get("source", ""))
        except ValueError:
            pass
    return out


def pick_track(fmt: str, audio_dir: str | None, rnd: random.Random) -> Path | None:
    """A track from our collection that no earlier episode used. Sleep: lullaby/sleep tracks first
    (Suno), then procedural sleep music; dance: Suno songs (anything not a lullaby)."""
    dirs = [Path(audio_dir)] if audio_dir else ([SUNO_DIR, SD_CODE_DIR] if fmt == "sleep" else [SUNO_DIR])
    words = ("lullaby", "sleep", "night", "dream", "calm", "bedtime") if fmt == "sleep" else None
    used = used_sources()
    for d in dirs:
        if not d.exists():
            continue
        files = sorted(p for p in d.rglob("*") if p.suffix.lower() in AUDIO_EXT and str(p) not in used)
        if words and not audio_dir:
            files = [p for p in files if any(w in p.name.lower() for w in words)]
        elif fmt == "dance":
            files = [p for p in files if not any(w in p.name.lower() for w in ("lullaby", "sleep"))]
        if files:
            return rnd.choice(files)
    return None


def music_credit(src: Path | None) -> tuple[str, bool, str]:
    """(credit line, ai_generated, music_source) — channel rule: Suno → AI-generated credit."""
    if src is None:
        return ("🎵 Original music composed and synthesized by Happy Bear Kids — every note made in code, © 2026.",
                False, "procedural")
    if "suno" in str(src).lower():
        return ("🎵 Original music by Happy Bear Kids (AI-generated, © 2026)", True, "suno")
    return ("🎵 Original music composed and synthesized by Happy Bear Kids, © 2026.", False, "procedural")


def duration_words(minutes: float) -> str:
    if minutes >= 60:
        h = minutes / 60
        return f"{h:g} Hour" if h == 1 else f"{h:g} Hours"
    return f"{int(round(minutes))} Minutes"


def sleep_description(minutes: float, cast: list[str], credit: str) -> str:
    names = ", ".join(sorted({c.title() for c in cast}))
    return f"""🌙 Time for sleep! {names} close their eyes and float slowly among twinkling stars while calm, gentle music plays.

This {duration_words(minutes).lower()} bedtime video is made for babies and toddlers: a dark, peaceful night sky, soft slow movement and nothing sudden or loud. The sleepy fruit friends drift up and down like a soft breath, and every minute a new group of friends floats in to say goodnight.

How families use it:
• As part of a calm bedtime routine — dim the lights, lower the volume and let the music play
• For naps, quiet time or soothing a fussy baby
• As gentle background sound while your little one falls asleep

The picture stays dark and slow on purpose, so the screen can face away and the music can do the work. There is no talking and no text, so it works for children everywhere.

{credit}
🎨 Original characters and animation by Happy Bear Kids.

Subscribe for more sleepy lullabies, dance parties and counting videos every week! 🐻💛

#lullaby #babysleep #bedtimemusic #sleepmusicforbabies #sensoryvideo #happybearkids"""


def main():
    ap = argparse.ArgumentParser(description="Sensory episode (dance or sleep) → EN kids queue")
    ap.add_argument("--format", choices=["dance", "sleep"], default="dance")
    ap.add_argument("--genre", choices=[g for g in music.GENRES if g != "lullaby"], default=None,
                    help="dance with code-made music in this genre (default when no track is given)")
    ap.add_argument("--audio", default=None, help="use this track from our collection")
    ap.add_argument("--audio-dir", default=None, help="pick an unused track from this folder")
    ap.add_argument("--collection", action="store_true",
                    help="dance: take a song from assets/audio/suno instead of code-made music")
    ap.add_argument("--minutes", type=float, default=None, help="dance: length (default 12); sleep: cap")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--queue-dir", default=str(QUEUE))
    ap.add_argument("--workers", type=int, default=None)
    a = ap.parse_args()
    seed = a.seed if a.seed is not None else int(datetime.datetime.now().timestamp()) % 100000
    rnd = random.Random(seed)
    q = Path(a.queue_dir); q.mkdir(parents=True, exist_ok=True)
    src = Path(a.audio) if a.audio else None
    if src is None and (a.format == "sleep" or a.audio_dir or a.collection):
        src = pick_track(a.format, a.audio_dir, rnd)
        if src is None:
            raise SystemExit("no unused track found — pass --audio or --audio-dir")
    credit, ai_gen, msrc = music_credit(src)
    today = f"{datetime.date.today():%Y%m%d}"

    if a.format == "sleep":
        from .sleep import render_sleep
        stem = f"sensory_sleep_{today}_{seed}"
        groups = render_sleep(q / f"{stem}.mp4", str(src), list(CHARACTERS), seed, minutes=a.minutes)
        dur = float(json.loads(subprocess_probe(q / f"{stem}.mp4")))
        minutes = dur / 60
        cast = [c for g in groups for c in g]
        thumbnail(q / f"thumb_{stem}.png", list(dict.fromkeys(cast)), "SLEEPY TIME", seed, sleepy=True)
        meta = {"title": f"Sleepy Fruit Friends 🌙 Calm Lullaby for Babies & Toddlers • {duration_words(round(minutes))}"[:100],
                "description": sleep_description(minutes, cast, credit),
                "tags": ["lullaby", "baby sleep music", "bedtime music", "sleep music for babies", "lullaby for babies",
                         "baby lullaby", "toddler sleep", "calm music for kids", "sensory video", "happy bear kids",
                         "relaxing music for babies", "night sky", "sleepy time"],
                "video_type": "sensory_sleep"}
        genre, extra = "sleep", {}
    else:
        if src is None:
            genre = a.genre or rnd.choice(["disco", "calypso", "march", "bounce"])
            stem = f"sensory_dance_{genre}_{today}_{seed}"
            wav = q / f"{stem}.wav"
            bmap = music.render(music.plan(genre, seed, (a.minutes or 12) * 60), wav)
        else:
            from .external import analyze
            genre = "collection"
            stem = f"sensory_dance_song_{today}_{seed}"
            wav = q / f"{stem}.wav"
            subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(src), "-ar", "44100", "-ac", "2", str(wav)],
                           check=True)
            bmap = analyze(wav, wav.with_suffix(".json"))
        print(f"♪ {genre} {bmap['bpm']:.0f} BPM, {bmap['duration'] / 60:.1f} min")
        scenes = render_episode(q / f"{stem}.mp4", str(wav), list(CHARACTERS), seed, workers=a.workers)
        minutes = bmap["duration"] / 60
        cast = [s.name for sc in scenes for s in sc.slots]
        thumbnail(q / f"thumb_{stem}.png", list(dict.fromkeys(cast)), "FRUIT DANCE PARTY", seed)
        word = GENRE_WORDS.get(genre, ("Party", "music"))
        meta = {"title": f"Dancing Fruit {word[0]} 🍓 Sensory Video for Babies & Toddlers • {duration_words(round(minutes))}"[:100],
                "description": description_for(genre if genre in GENRE_WORDS else "bounce", minutes, cast).replace(
                    "🎵 Original music composed and synthesized by Happy Bear Kids — every note made in code, © 2026.", credit),
                "tags": ["sensory video", "baby sensory", "dancing fruit", "toddler video", "kids music",
                         "fruit dance", "high contrast baby", "baby video", "dance party for kids", "happy bear kids",
                         "visual stimulation", "babies music", f"{word[1]} for kids"],
                "video_type": "sensory_dance"}
        extra = {"bpm": bmap["bpm"]}
        wav.unlink(missing_ok=True); wav.with_suffix(".json").unlink(missing_ok=True)
    meta.update({"language": "en", "is_short": False, "status": "public", "made_for_kids": True,
                 "ai_generated": ai_gen, "music_source": msrc, "music_file": str(src) if src else None,
                 "seed": seed, "genre": genre, "duration_sec": int(minutes * 60), **extra})
    (q / f"meta_{stem}.yaml").write_text(yaml.dump(meta, allow_unicode=True, sort_keys=False))
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a") as f:
        f.write(json.dumps({"stem": stem, "seed": seed, "format": a.format, "genre": genre,
                            "source": str(src) if src else None, "cast": sorted(set(cast))}) + "\n")
    print(f"✅ {q / (stem + '.mp4')}\n   {meta['title']}  ({len(meta['description'].split())} words)")


def subprocess_probe(path: Path) -> str:
    import subprocess as sp
    return sp.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                  capture_output=True, text=True).stdout.strip() or "0"


if __name__ == "__main__":
    main()
