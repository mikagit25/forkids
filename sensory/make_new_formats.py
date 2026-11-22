"""New Happy Bear Kids formats (pilots, Nov 2026) → output/queue (mp4 + thumb + meta, made_for_kids: true).

    python3 make_new_formats.py aquarium  [--minutes 30] [--seed N]   # baby aquarium, calm code-made lullabies
    python3 make_new_formats.py peekaboo  [--minutes 8]  [--seed N]   # peek-a-boo with baby animals, on the beat
    python3 make_new_formats.py lullabies [--minutes 30] [--seed N]   # public-domain nursery tunes, music box

Everything is drawn and synthesized in code (own characters, own recordings) → ai_generated: false.
Render one at a time (heavy job): bash ../history_channel/heavy.sh "<label>" bash -c "cd sensory && python3 ..."
"""
from __future__ import annotations

import argparse
import datetime
import json
import random
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sensory import music                                   # noqa: E402
from sensory.characters import FAMILIES                     # noqa: E402
from sensory.episode import duration_words, thumbnail, LOG  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "output" / "queue"
CREDIT = "🎵 Original music composed and synthesized by Happy Bear Kids — every note made in code, © 2026."
ART = "🎨 Original characters and animation by Happy Bear Kids."


def probe(p: Path) -> float:
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                 str(p)], capture_output=True, text=True).stdout.strip() or 0)


def lullaby_mix(out_wav: Path, seed: int, minutes: float) -> list[dict]:
    """Several different code-made lullabies (new key, tempo, motif each) joined with 4 s crossfades —
    the music never loops."""
    parts, total, k = [], 0.0, 0
    td = Path(tempfile.mkdtemp())
    while total < minutes * 60:
        w = td / f"l{k}.wav"
        bm = music.render(music.plan("lullaby", seed + 101 * k, 300), w)
        parts.append((w, bm)); total += bm["duration"] - 4; k += 1
    inputs, fc, last = [], [], "[0:a]"
    for i, (w, _) in enumerate(parts):
        inputs += ["-i", str(w)]
    for i in range(1, len(parts)):
        lab = f"[x{i}]"
        fc.append(f"{last}[{i}:a]acrossfade=d=4:c1=tri:c2=tri{lab}")
        last = lab
    cmd = ["ffmpeg", "-loglevel", "error", "-y", *inputs]
    if fc:
        cmd += ["-filter_complex", ";".join(fc), "-map", last]
    cmd += ["-t", f"{minutes * 60:.1f}", str(out_wav)]
    subprocess.run(cmd, check=True)
    return [{"key": b["key"], "bpm": b["bpm"], "seed": b["seed"]} for _, b in parts]


def write_meta(stem: str, q: Path, meta: dict, log: dict):
    base = {"language": "en", "is_short": False, "status": "public", "made_for_kids": True, "ai_generated": False,
            "music_source": "procedural"}
    base.update(meta)
    assert len(base["description"].split()) >= 200, len(base["description"].split())
    (q / f"meta_{stem}.yaml").write_text(yaml.dump(base, allow_unicode=True, sort_keys=False))
    with open(LOG, "a") as f:
        f.write(json.dumps({"stem": stem, **log}) + "\n")
    print(f"✅ {q / (stem + '.mp4')}\n   {base['title']}  ({len(base['description'].split())} words)")


# ── 1. baby aquarium ─────────────────────────────────────────────────────────

def aquarium(a, q, seed, today):
    from sensory.aquarium import render_aquarium
    stem = f"sensory_aquarium_{today}_{seed}"
    wav = q / f"{stem}.wav"
    songs = lullaby_mix(wav, seed, a.minutes or 30)
    info = render_aquarium(q / f"{stem}.mp4", str(wav), seed)
    wav.unlink(missing_ok=True)
    minutes = probe(q / f"{stem}.mp4") / 60
    thumbnail(q / f"thumb_{stem}.png", ["octopus", "blue_whale", "octopus"][:3], "BABY AQUARIUM", seed)
    words = duration_words(round(minutes))
    desc = f"""🐠 Welcome to the Happy Bear Kids baby aquarium! Colourful fish swim slowly from side to side, pink and blue jellyfish float up through the water, a friendly octopus and a smiling little whale glide past, and soft bubbles rise between swaying seaweed — all to calm, gentle music.

This {int(round(minutes))}-minute underwater video is made for babies and toddlers. Everything moves slowly and smoothly: no sudden movements, no flashing lights, no loud sounds and no talking. The deep blue colours and the soft light rays from the surface make it a peaceful view for quiet time.

How families use it:
• Calm-down time after a busy day, or before a nap
• Background for tummy time — little ones love to follow the fish with their eyes
• A gentle bedtime routine: dim the lights, lower the volume and let the music play
• Name the colours together: "Look, a yellow fish! Where is the pink jellyfish?"

Talking about what you see helps little ones learn new words: fish, bubble, whale, octopus, up, down, big, small.

The music is a set of soft lullabies with music box, felt piano and warm pads, made in code by Happy Bear Kids — the melody changes every few minutes and never loops.

{CREDIT}
{ART}

Subscribe for new calm videos, dance parties, peek-a-boo games and lullabies every week! 🐻💙

#babyaquarium #calmvideoforbabies #babysensory #underwater #lullaby #happybearkids"""
    write_meta(stem, q, {
        "title": f"Baby Aquarium 🐠 Calm Fish, Jellyfish & Little Whale for Babies • {words}"[:100],
        "description": desc,
        "tags": ["baby aquarium", "aquarium for babies", "calm video for babies", "fish video for babies",
                 "underwater for kids", "baby sensory", "jellyfish", "ocean animals for kids", "relaxing music for babies",
                 "baby sleep", "lullaby", "sensory video", "happy bear kids", "toddler calm down", "tummy time video"],
        "video_type": "sensory_aquarium", "seed": seed, "genre": "lullaby", "duration_sec": int(minutes * 60),
        "music_parts": songs}, {"seed": seed, "format": "aquarium", "genre": "lullaby", "source": None,
                                 "cast": sorted(set(info["big"]))})


# ── 2. peek-a-boo ────────────────────────────────────────────────────────────

def peekaboo(a, q, seed, today):
    from sensory.peekaboo import render_peekaboo
    genre = random.Random(seed).choice(["march", "bounce", "calypso"])
    stem = f"sensory_peekaboo_{genre}_{today}_{seed}"
    wav = q / f"{stem}.wav"
    bmap = music.render(music.plan(genre, seed, (a.minutes or 8) * 60), wav)
    info = render_peekaboo(q / f"{stem}.mp4", wav, bmap, FAMILIES["animals"], seed, fps=20)
    wav.unlink(missing_ok=True); wav.with_suffix(".json").unlink(missing_ok=True)
    minutes = probe(q / f"{stem}.mp4") / 60
    cast = info["cast"]
    thumbnail(q / f"thumb_{stem}.png", cast[:3], "PEEKABOO!", seed)
    words = duration_words(round(minutes))
    names = ", ".join(c.title() for c in cast)
    desc = f"""🙈 Peek-a-boo! Who is hiding behind the gift box? Who is behind the bush and the smiling cloud? Baby animals pop up exactly on the beat, wave hello, dance for a moment and hide again — and when the chorus comes, everybody jumps out together!

This {int(round(minutes))}-minute peek-a-boo video is made for babies and toddlers. Peek-a-boo is one of the first games babies love: it builds attention, anticipation and the idea that things are still there even when we can't see them (object permanence). Every surprise here is gentle and friendly — no scary sounds, no flashing lights and no talking.

Play along at home:
• Before each friend pops up, ask: "Who's hiding? Where is it?"
• When the friend appears, say "Peek-a-boo!" together and name the animal
• In the break, when everyone hides and the hiding places wiggle, count "one, two, three…" and cheer when they jump out
• Clap and bounce along to the beat

In this episode: {names}.

The music is a happy {genre} tune made in code by Happy Bear Kids, and every move is locked to its beat.

{CREDIT}
{ART}

Subscribe for more peek-a-boo games, dance parties, calm aquarium videos and lullabies every week! 🐻💛

#peekaboo #peekaboobaby #babysensory #babyanimals #toddlervideos #happybearkids"""
    write_meta(stem, q, {
        "title": f"Peekaboo with Baby Animals 🙈 Hide and Seek Dance for Babies & Toddlers • {words}"[:100],
        "description": desc,
        "tags": ["peekaboo", "peek a boo baby", "peekaboo song", "hide and seek for kids", "baby animals",
                 "baby sensory", "toddler video", "kids dance music", "object permanence", "baby games",
                 "animals for babies", "sensory video", "happy bear kids", "cute animals"],
        "video_type": "sensory_peekaboo", "seed": seed, "genre": genre, "bpm": bmap["bpm"],
        "duration_sec": int(minutes * 60)}, {"seed": seed, "format": "peekaboo", "genre": genre, "source": None,
                                             "cast": cast})


# ── 3. public-domain nursery tunes ───────────────────────────────────────────

def lullabies(a, q, seed, today):
    from sensory.melodies import TUNES, render_medley
    from sensory.sleep import render_sleep
    rnd = random.Random(seed)
    order = ["twinkle", "brahms", "mary", "frere", "rowboat", "london"]
    stem = f"sensory_lullabies_{today}_{seed}"
    wav = q / f"{stem}.wav"
    info = render_medley(order, wav, seed, bpm=rnd.choice([70, 72, 76]), repeats=3, target_min=a.minutes or 30)
    pool = FAMILIES["animals"]
    groups = render_sleep(q / f"{stem}.mp4", str(wav), list(pool), seed, scale=1.6)
    wav.unlink(missing_ok=True); wav.with_suffix(".json").unlink(missing_ok=True)
    minutes = probe(q / f"{stem}.mp4") / 60
    cast = [c for g in groups for c in g]
    thumbnail(q / f"thumb_{stem}.png", list(dict.fromkeys(cast)), "MUSIC BOX LULLABIES", seed, sleepy=True)
    words = duration_words(round(minutes))
    chapters = []
    for title, start, _ in info["songs"]:
        s = 0 if not chapters else int(start)
        chapters.append(f"{s // 60}:{s % 60:02d} {title}")
    desc = f"""🌙 Gentle music box lullabies for babies: Twinkle Twinkle Little Star, Brahms' Lullaby, Mary Had a Little Lamb, Frère Jacques, Row Row Row Your Boat and London Bridge — slow, soft and warm, while sleepy baby animals float among twinkling stars.

This {int(round(minutes))}-minute bedtime video is made for babies and toddlers. Each tune is played three times in a row, on a music box, a soft felt piano and a gentle flute, over warm, quiet chords. Then the whole set comes back twice more, each time in a new key and a little slower, so the music grows calmer and calmer towards sleep. The picture stays dark and slow, with nothing sudden or bright, so it can be part of a calm bedtime routine.

Songs:
{chr(10).join(chapters)}

How families use it:
• Dim the lights, lower the volume and let the music play as your little one falls asleep
• Hum or sing along — these are the tunes grandparents sang too
• For naps, car rides and quiet time

All six melodies are traditional nursery songs or classical lullabies in the public domain. The arrangement and the recording are our own: every note is synthesized in code by Happy Bear Kids.

{CREDIT}
{ART}

Subscribe for more lullabies, calm aquarium videos, peek-a-boo games and dance parties every week! 🐻💛

#lullaby #lullabiesforbabies #musicbox #twinkletwinkle #brahmslullaby #babysleep #happybearkids"""
    write_meta(stem, q, {
        "title": f"Music Box Lullabies 🌙 Twinkle Twinkle, Brahms' Lullaby & More for Babies • {words}"[:100],
        "description": desc,
        "tags": ["lullaby", "lullabies for babies", "music box lullaby", "twinkle twinkle little star", "brahms lullaby",
                 "baby sleep music", "bedtime music", "nursery rhymes instrumental", "mary had a little lamb",
                 "frere jacques", "row row row your boat", "london bridge", "sleep music for babies", "happy bear kids"],
        "video_type": "sensory_lullabies", "seed": seed, "genre": "lullaby", "duration_sec": int(minutes * 60),
        "songs": [s[0] for s in info["songs"]],
        "music_note": "Public-domain melodies; arrangement and recording synthesized in code"},
        {"seed": seed, "format": "lullabies", "genre": "lullaby", "source": None, "cast": sorted(set(cast))})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("format", choices=["aquarium", "peekaboo", "lullabies"])
    ap.add_argument("--minutes", type=float, default=None)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--queue-dir", default=str(QUEUE))
    a = ap.parse_args()
    seed = a.seed if a.seed is not None else int(datetime.datetime.now().timestamp()) % 100000
    q = Path(a.queue_dir); q.mkdir(parents=True, exist_ok=True)
    today = f"{datetime.date.today():%Y%m%d}"
    {"aquarium": aquarium, "peekaboo": peekaboo, "lullabies": lullabies}[a.format](a, q, seed, today)


if __name__ == "__main__":
    main()
