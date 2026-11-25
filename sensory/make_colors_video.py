#!/usr/bin/env python3
"""Learn Colors with Fruit & Animal Friends — sensory colour video for babies/toddlers (Happy Bear Kids EN, since 25.11.2026).

Built on the counting format (the channel's best, Studio analytics 25.11.2026): one colour per scene, the characters of that
colour dance in, the colour word appears big in its own colour and is spoken ("Let's find something red!" … "Red!"),
a soft glow of the colour behind them; finale: one friend of every colour, "All the colours of the rainbow!".
Background: black with a coloured glow per scene (our own look; black is fine, colours alternate).

    python3 make_colors_video.py [--genre march|bounce|calypso] [--seed N] [--queue-dir DIR]
"""
from __future__ import annotations

import argparse
import datetime
import random
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sensory import music as M                                   # noqa: E402
from sensory.characters import CHARACTERS                        # noqa: E402
from sensory.render import compose, beatmap_phase                # noqa: E402
from sensory.easing import dance_pose                            # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "output" / "queue"
FONT = ROOT / "assets" / "fonts" / "BebasNeue-Regular.ttf"
VOICE = ROOT / "assets" / "audio" / "voiceover" / "en" / "colors"
FPS, W, H = 30, 1920, 1080
BARS_PER_COLOR, BARS_FINALE = 8, 12
GENRES = ["march", "bounce", "march", "bounce", "calypso"]

# colour -> (RGB 0..1 for the word and glow, characters of that colour)
COLORS = {
    "red":    ((1.00, 0.18, 0.20), ["berry", "tomato"]),
    "orange": ((1.00, 0.55, 0.05), ["orange", "carrot", "pumpkin", "fox", "cat"]),
    "yellow": ((1.00, 0.90, 0.10), ["banana", "lemon", "corn", "lion"]),
    "green":  ((0.20, 0.85, 0.25), ["pear", "apple", "broccoli", "frog"]),
    "blue":   ((0.15, 0.45, 1.00), ["blueberry", "blue_whale"]),
    "purple": ((0.62, 0.25, 1.00), ["plum", "octopus"]),
    "pink":   ((1.00, 0.40, 0.75), ["butterfly"]),
    "brown":  ((0.72, 0.45, 0.22), ["bear", "monkey"]),
}
CORE = ["red", "orange", "yellow", "green", "blue", "purple"]


def glow_bg(rgb, strength=0.45):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - W / 2) / (W * 0.55)) ** 2 + ((yy - H * 0.58) / (H * 0.6)) ** 2)
    g = np.clip(1 - d, 0, 1) ** 1.6 * strength
    return (np.array(rgb, np.float32)[None, None, :] * g[..., None] * 255)


def draw_word(img: Image.Image, word: str, rgb, alpha: float, size=230):
    if alpha <= 0:
        return img
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(ov)
    font = ImageFont.truetype(str(FONT), size)
    text = word.upper()
    tw = dr.textlength(text, font=font)
    x, y = (W - tw) / 2, 30
    a = int(255 * alpha)
    for dx, dy in ((-7, 0), (7, 0), (0, -7), (0, 7), (5, 5), (-5, 5)):
        dr.text((x + dx, y + dy), text, font=font, fill=(255, 255, 255, a))
    dr.text((x, y), text, font=font, fill=(int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255), a))
    return Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB")


def render(out: Path, bmap: dict, plan: list[tuple[str, list[str]]], seed: int):
    beat_s = bmap["beat_s"]
    scene = beat_s * 4 * BARS_PER_COLOR
    finale = beat_s * 4 * BARS_FINALE
    total = scene * len(plan) + finale
    inst = {}
    k = 0
    for _, cast in plan:
        for n in cast:
            if n not in inst:
                k += 1
                inst[n] = CHARACTERS[n](seed=seed % 97 + k)
    bgs = [glow_bg(COLORS[c][0]) for c, _ in plan]
    rainbow = glow_bg((0.9, 0.9, 1.0), 0.25)
    cmd = ["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(int(total * FPS)):
        t = f / FPS
        if t < scene * len(plan):
            si = int(t / scene)
            ts = t - si * scene
            color, cast = plan[si]
            # characters walk in one by one (one per 2 bars), then all dance
            n_in = min(len(cast), 1 + int(ts / (beat_s * 8)))
            items = []
            sp = W / (n_in + 1)
            for i in range(n_in):
                b, ph = beatmap_phase(bmap, t, i * 0.25)
                pose = dance_pose(b, ph, "bounce" if i % 2 == 0 else "sway", 0.85)
                items.append((inst[cast[i]], sp * (i + 1), H * 0.62, min(230, int(sp * 0.36)), pose))
            fg = compose(items, W, H, t, rgba=True)
            fade = min(1.0, ts / (beat_s * 2), (scene - ts) / (beat_s * 2))
            bg = bgs[si] * fade
            frame = (fg[..., :3] * 255 + bg * (1 - fg[..., 3:4])).clip(0, 255).astype(np.uint8)
            img = draw_word(Image.fromarray(frame), color, COLORS[color][0], min(1.0, max(0.0, (ts - beat_s * 2) / beat_s)) *
                            min(1.0, (scene - ts) / (beat_s * 2)))
            frame = np.asarray(img)
        else:
            tf = t - scene * len(plan)
            items = []
            n = len(plan)
            for i, (color, cast) in enumerate(plan):
                b, ph = beatmap_phase(bmap, t, i * 0.15)
                items.append((inst[cast[0]], W * (i + 1) / (n + 1), H * 0.6, 150, dance_pose(b, ph, "bounce", 1.0)))
            fg = compose(items, W, H, t, rgba=True)
            frame = (fg[..., :3] * 255 + rainbow * (1 - fg[..., 3:4])).clip(0, 255).astype(np.uint8)
            img = Image.fromarray(frame)
            # rainbow word: each letter in the next colour
            ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            dr = ImageDraw.Draw(ov)
            font = ImageFont.truetype(str(FONT), 200)
            word = "RAINBOW"
            tw = dr.textlength(word, font=font)
            x = (W - tw) / 2
            a = int(255 * min(1.0, tf / beat_s, (finale - tf) / (beat_s * 2)))
            for j, ch in enumerate(word):
                rgb = COLORS[CORE[j % len(CORE)]][0]
                dr.text((x + 5, 45), ch, font=font, fill=(255, 255, 255, a))
                dr.text((x, 40), ch, font=font, fill=(int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255), a))
                x += dr.textlength(ch, font=font)
            frame = np.asarray(Image.alpha_composite(img.convert("RGBA"), ov).convert("RGB"))
        p.stdin.write(frame.tobytes())
    p.stdin.close()
    if p.wait():
        raise RuntimeError("ffmpeg failed")
    return total, scene


def mix_voice(music_wav: Path, plan, scene: float, beat_s: float, total: float, out_wav: Path):
    """Music + spoken colour words: 'Let's find something red!' at the start, 'Red!' when the word appears, twice."""
    cues = []
    for i, (color, _) in enumerate(plan):
        t0 = i * scene
        cues += [(VOICE / f"{color}_say.wav", t0 + beat_s * 0.5), (VOICE / f"{color}.wav", t0 + beat_s * 3),
                 (VOICE / f"{color}.wav", t0 + scene * 0.6)]
    cues.append((VOICE / "rainbow_say.wav", len(plan) * scene + beat_s))
    cmd = ["ffmpeg", "-loglevel", "error", "-y", "-i", str(music_wav)]
    for f, _ in cues:
        cmd += ["-i", str(f)]
    parts = [f"[0:a]volume=0.55[m]"]
    for k, (_, t) in enumerate(cues, start=1):
        parts.append(f"[{k}:a]aresample=44100,adelay={int(t * 1000)}|{int(t * 1000)},volume=1.6[v{k}]")
    parts.append("[m]" + "".join(f"[v{k}]" for k in range(1, len(cues) + 1)) +
                 f"amix=inputs={len(cues) + 1}:normalize=0,atrim=0:{total:.2f},loudnorm=I=-16:TP=-1.5[a]")
    cmd += ["-filter_complex", ";".join(parts), "-map", "[a]", "-ar", "44100", str(out_wav)]
    subprocess.run(cmd, check=True)


def thumbnail(path: Path, plan, seed: int):
    from sensory.episode import THUMB_BG
    w, h = 1280, 720
    inner, outer = random.Random(seed).choice(THUMB_BG)
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt(((xx - w / 2) / (w * 0.6)) ** 2 + ((yy - h * 0.45) / (h * 0.75)) ** 2).clip(0, 1)[..., None]
    bg = np.array(outer, np.float32) * (1 - d) + np.array(inner, np.float32) * d
    picks = [plan[0][1][0], plan[2][1][0], plan[4][1][0]]
    items = []
    for i, (name, x, r) in enumerate(zip(picks, (290, 640, 990), (165, 200, 165))):
        items.append((CHARACTERS[name](seed=i + 1), x, 330 if i != 1 else 290, r,
                      {"smile": 1.3, "tilt": (-10, 0, 10)[i], "happy": i == 1}))
    fg = compose(items, w, h, 0.0, rgba=True)
    img = Image.fromarray((fg[..., :3] * 255 + bg * (1 - fg[..., 3:4])).clip(0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(img)
    font = ImageFont.truetype(str(FONT), 120)
    words = [plan[0][0].upper(), plan[2][0].upper(), plan[4][0].upper()]
    total = sum(dr.textlength(wd, font=font) for wd in words) + 60 * (len(words) - 1)
    x = (w - total) / 2
    for wd, (c, _) in zip(words, (plan[0], plan[2], plan[4])):
        rgb = tuple(int(v * 255) for v in COLORS[c][0])
        for dx, dy in ((-5, 0), (5, 0), (0, -5), (0, 5)):
            dr.text((x + dx, h - 165 + dy), wd, font=font, fill=(255, 255, 255))
        dr.text((x, h - 165), wd, font=font, fill=rgb)
        x += dr.textlength(wd, font=font) + 60
    img.save(path, "PNG", optimize=True)


DESC = """🌈 Learn your colours with dancing friends! {intro} Every colour gets its own little dance party: the friends of that colour bounce onto the screen, the colour word appears in big bright letters and a friendly voice says it out loud — {colours}.

At the end, one friend of every colour dances together for a big rainbow finale.

How to watch together:
• Say each colour out loud with the video, then point to something of the same colour in your room
• Ask "which one is {first}?" and let your little one point
• Clap along to the beat and copy the bounces

Why colour videos help:
• Toddlers learn colour words best when they hear the word and see the colour at the same time, again and again
• Big, bright characters on a calm dark background are easy for young eyes to follow
• Music with a steady beat helps attention, rhythm and early language

This video has no fast flashing and no scary moments — just happy characters, clear colours and a gentle voice.

🎵 Original music composed and synthesized by Happy Bear Kids — every note made in code, © 2026.
🎨 Original characters and animation by Happy Bear Kids.

Subscribe for more counting, colours, lullabies and sensory dance videos every week! 🐻💛

#learncolors #colorsfortoddlers #babysensory #toddlerlearning #kidsmusic #happybearkids #sensoryvideo #preschool #earlylearning #colorsong"""


def main():
    import yaml
    ap = argparse.ArgumentParser()
    ap.add_argument("--genre", choices=sorted(set(GENRES)))
    ap.add_argument("--seed", type=int)
    ap.add_argument("--queue-dir", default=str(QUEUE))
    a = ap.parse_args()
    seed = a.seed if a.seed is not None else int(datetime.datetime.now().timestamp()) % 100000
    rnd = random.Random(seed)
    genre = a.genre or rnd.choice(GENRES)
    colours = CORE[:]
    extra = rnd.choice(["pink", "brown"])
    colours.insert(rnd.randrange(3, len(colours) + 1), extra)
    plan = []
    for c in colours:
        cast = COLORS[c][1][:]
        rnd.shuffle(cast)
        plan.append((c, cast[:3]))
    q = Path(a.queue_dir)
    q.mkdir(parents=True, exist_ok=True)
    stem = f"sensory_colors_{genre}_{datetime.date.today():%Y%m%d}_{seed}"
    beat_guess = 60 / 108
    target = beat_guess * 4 * (BARS_PER_COLOR * len(plan) + BARS_FINALE) + 4
    music_wav = q / f"{stem}_music.wav"
    print(f"♪ {genre} music {target:.0f}s …")
    bmap = M.render(M.plan(genre, seed, target), music_wav)
    vid = q / f"{stem}_noaudio.mp4"
    print(f"🎬 rendering {len(plan)} colours …")
    total, scene = render(vid, bmap, plan, seed)
    mix = q / f"{stem}_mix.wav"
    mix_voice(music_wav, plan, scene, bmap["beat_s"], total, mix)
    mp4 = q / f"{stem}.mp4"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(vid), "-i", str(mix), "-t", f"{total:.2f}", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", str(mp4)], check=True)
    for f in (vid, mix, music_wav, music_wav.with_suffix(".json")):
        f.unlink(missing_ok=True)
    thumbnail(q / f"thumb_{stem}.png", plan, seed)
    names = [n.replace("_", " ").title() for _, cast in plan for n in cast[:1]]
    cl = [c for c, _ in plan]
    title = f"Learn Colors with {names[0]} & {names[2]} 🌈 {cl[0].title()}, {cl[2].title()}, {cl[4].title()} for Babies & Toddlers • {int(round(total / 60))} Minutes"
    meta = {
        "title": title[:100],
        "description": DESC.format(intro=f"{names[0]}, {names[1]}, {names[2]} and friends are here to help.",
                                   colours=", ".join(cl[:-1]) + " and " + cl[-1], first=cl[0]),
        "tags": ["learn colors", "colors for toddlers", "colours for babies", "baby sensory", "toddler learning",
                 "learn colours", "kids music", "sensory video", "happy bear kids", "color song", "preschool colors",
                 "educational video", "baby video", "early learning"],
        "video_type": "sensory_colors", "language": "en", "is_short": False, "status": "public", "made_for_kids": True,
        "ai_generated": False, "music_source": "procedural", "voice": "Kokoro af_heart (synthetic)", "seed": seed,
        "genre": genre, "colours": cl, "duration_sec": int(total),
    }
    (q / f"meta_{stem}.yaml").write_text(yaml.dump(meta, allow_unicode=True, sort_keys=False))
    print(f"✅ {mp4}\n   {meta['title']}  ({len(meta['description'].split())} words)")


if __name__ == "__main__":
    main()
