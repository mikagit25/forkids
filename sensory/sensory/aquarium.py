"""Baby aquarium: calm underwater scene for babies — fish, jellyfish, an octopus and a whale drift slowly
past swaying seaweed and rising bubbles, under soft light rays.

Like sleep.py: one seamless visual loop (every motion period divides LOOP_S) rendered once at 15 fps, then
repeated under full-length, never-looped music. Rules kept: nothing faster than a slow drift, no flashes,
every element opacity >= 0.5, bubbles >= 14 px.
"""
from __future__ import annotations

import math
import random
import subprocess
import tempfile
from pathlib import Path

import cairo
import numpy as np

from .characters import CHARACTERS
from .render import compose

LOOP_S = 240.0
FISH_COLORS = [(1.0, 0.55, 0.15), (1.0, 0.85, 0.2), (0.35, 0.85, 1.0), (1.0, 0.45, 0.65), (0.55, 1.0, 0.5),
               (0.75, 0.55, 1.0), (1.0, 0.7, 0.35)]
JELLY_COLORS = [(1.0, 0.6, 0.85), (0.6, 0.8, 1.0), (0.85, 0.7, 1.0)]


def _background(w, h):
    y = np.linspace(0, 1, h)[:, None, None]
    top, bottom = np.array([30, 120, 170], np.float32), np.array([5, 25, 60], np.float32)
    bg = top * (1 - y) + bottom * y
    return np.repeat(bg, w, axis=1)


def _rays(w, h, t):
    """Soft diagonal light bands that sway very slowly (period 60 s / 80 s)."""
    xx = np.linspace(0, 1, w)[None, :]
    yy = np.linspace(0, 1, h)[:, None]
    s = 0.0
    for k, (f, p, ph) in enumerate(((5.0, 60.0, 0.0), (8.0, 80.0, 1.7), (3.0, 120.0, 3.1))):
        s = s + 0.5 + 0.5 * np.sin(2 * np.pi * (f * (xx + 0.35 * yy) + 0.15 * math.sin(2 * math.pi * t / p + ph)))
    fade = np.clip(1.0 - yy * 1.3, 0, 1)
    return (s / 3.0) ** 3 * fade * 38.0


def _seaweed(ctx, w, h, t, weeds):
    for x0, height, col, per, ph in weeds:
        ctx.set_source_rgba(*col, 0.85)
        ctx.set_line_width(h * 0.018)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.move_to(x0, h + 10)
        segs = 12
        for i in range(1, segs + 1):
            u = i / segs
            sway = math.sin(2 * math.pi * t / per + ph + u * 2.2) * 40 * u
            ctx.line_to(x0 + sway, h + 10 - height * u)
        ctx.stroke()


def _bubbles(ctx, w, h, t, bubbles):
    for x0, r, per, ph in bubbles:
        u = ((t / per) + ph) % 1.0
        y = h + 30 - u * (h + 60)
        x = x0 + 18 * math.sin(2 * math.pi * u * 3 + ph * 6)
        ctx.set_source_rgba(0.85, 0.95, 1.0, 0.55)
        ctx.set_line_width(2.5)
        ctx.arc(x, y, r, 0, 2 * math.pi)
        ctx.stroke()
        ctx.set_source_rgba(1, 1, 1, 0.75)
        ctx.arc(x - r * 0.35, y - r * 0.35, r * 0.22, 0, 2 * math.pi)
        ctx.fill()


def _fish(ctx, x, y, size, col, direction, t, ph):
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(direction, 1)
    wag = math.sin(2 * math.pi * t / 1.5 + ph) * 0.25           # gentle tail wag (1.5 s divides 240)
    # tail
    ctx.set_source_rgba(*[c * 0.85 for c in col], 0.95)
    ctx.move_to(-size * 0.8, 0)
    ctx.line_to(-size * 1.45, -size * (0.5 + wag))
    ctx.line_to(-size * 1.45, size * (0.5 - wag))
    ctx.close_path(); ctx.fill()
    # body with a soft highlight
    g = cairo.RadialGradient(-size * 0.1, -size * 0.25, size * 0.1, 0, 0, size)
    g.add_color_stop_rgba(0, min(1, col[0] + 0.3), min(1, col[1] + 0.3), min(1, col[2] + 0.3), 1)
    g.add_color_stop_rgba(1, *col, 1)
    ctx.set_source(g)
    ctx.save(); ctx.scale(1.0, 0.62); ctx.arc(0, 0, size, 0, 2 * math.pi); ctx.restore(); ctx.fill()
    # fin
    ctx.set_source_rgba(*[c * 0.8 for c in col], 0.9)
    ctx.move_to(-size * 0.1, -size * 0.55); ctx.line_to(size * 0.25, -size * 0.95); ctx.line_to(size * 0.4, -size * 0.5)
    ctx.close_path(); ctx.fill()
    # eye + smile
    ctx.set_source_rgb(1, 1, 1); ctx.arc(size * 0.45, -size * 0.12, size * 0.17, 0, 2 * math.pi); ctx.fill()
    ctx.set_source_rgb(0.1, 0.1, 0.15); ctx.arc(size * 0.5, -size * 0.1, size * 0.09, 0, 2 * math.pi); ctx.fill()
    ctx.set_source_rgb(1, 1, 1); ctx.arc(size * 0.53, -size * 0.14, size * 0.03, 0, 2 * math.pi); ctx.fill()
    ctx.set_source_rgba(0.2, 0.05, 0.1, 0.9); ctx.set_line_width(size * 0.05)
    ctx.arc(size * 0.62, size * 0.12, size * 0.12, 0.2, 2.0); ctx.stroke()
    ctx.restore()


def _jelly(ctx, x, y, size, col, t, ph):
    pulse = 1 + 0.08 * math.sin(2 * math.pi * t / 4.0 + ph)     # slow breathing (4 s divides 240)
    ctx.save(); ctx.translate(x, y)
    ctx.set_source_rgba(*col, 0.8)
    ctx.set_line_width(size * 0.07); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for k in range(5):
        x0 = (k - 2) * size * 0.28
        ctx.move_to(x0, 0)
        for i in range(1, 9):
            u = i / 8
            ctx.line_to(x0 + math.sin(2 * math.pi * t / 4.0 + ph + u * 4 + k) * size * 0.12, u * size * 1.6)
        ctx.stroke()
    g = cairo.RadialGradient(0, -size * 0.4, size * 0.1, 0, -size * 0.1, size * pulse)
    g.add_color_stop_rgba(0, 1, 1, 1, 0.95); g.add_color_stop_rgba(1, *col, 0.85)
    ctx.set_source(g)
    ctx.save(); ctx.scale(pulse, 1 / pulse)
    ctx.arc(0, 0, size, math.pi, 2 * math.pi); ctx.close_path(); ctx.fill()
    ctx.restore()
    ctx.set_source_rgb(0.15, 0.1, 0.2)
    for ex in (-0.3, 0.3):
        ctx.arc(ex * size, -size * 0.35, size * 0.08, 0, 2 * math.pi); ctx.fill()
    ctx.set_line_width(size * 0.05); ctx.arc(0, -size * 0.25, size * 0.15, 0.3, 2.84); ctx.stroke()
    ctx.restore()


def scene(seed: int, w=1920, h=1080) -> dict:
    rnd = random.Random(seed)
    periods = [40.0, 48.0, 60.0, 80.0, 120.0]                    # swim-across times, all divide 240
    fish = [dict(y=rnd.uniform(0.18, 0.8) * h, size=rnd.uniform(0.045, 0.075) * h, col=rnd.choice(FISH_COLORS),
                 per=rnd.choice(periods), ph=rnd.random(), dir=rnd.choice((1, -1))) for _ in range(9)]
    jellies = [dict(x=rnd.uniform(0.1, 0.9) * w, size=rnd.uniform(0.05, 0.07) * h, col=rnd.choice(JELLY_COLORS),
                    per=rnd.choice((60.0, 80.0, 120.0)), ph=rnd.random()) for _ in range(3)]
    weeds = [(rnd.uniform(0, w), rnd.uniform(0.18, 0.38) * h, rnd.choice(((0.2, 0.7, 0.35), (0.3, 0.8, 0.45),
                                                                          (0.55, 0.75, 0.25))),
              rnd.choice((8.0, 10.0, 12.0)), rnd.random() * 6) for _ in range(16)]
    bubbles = [(rnd.uniform(0, w), rnd.uniform(7, 14), rnd.choice((12.0, 15.0, 16.0, 20.0, 24.0)), rnd.random())
               for _ in range(26)]
    big = rnd.sample(["octopus", "blue_whale"], 2)
    return dict(fish=fish, jellies=jellies, weeds=weeds, bubbles=bubbles, big=big, chars={}, bg=_background(w, h))


def frame(t, w, h, S):
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    ctx = cairo.Context(s)
    _seaweed(ctx, w, h, t, S["weeds"])
    for j in S["jellies"]:
        u = ((t / j["per"]) + j["ph"]) % 1.0
        _jelly(ctx, j["x"] + 40 * math.sin(2 * math.pi * u), h * (1.05 - u * 1.2), j["size"], j["col"], t, j["ph"] * 6)
    for f in S["fish"]:
        u = ((t / f["per"]) + f["ph"]) % 1.0
        x = -0.12 * w + u * 1.24 * w if f["dir"] > 0 else 1.12 * w - u * 1.24 * w
        y = f["y"] + 25 * math.sin(2 * math.pi * t / 8.0 + f["ph"] * 6)
        _fish(ctx, x, y, f["size"], f["col"], f["dir"], t, f["ph"] * 6)
    _bubbles(ctx, w, h, t, S["bubbles"])
    buf = np.ndarray((h, w, 4), np.uint8, s.get_data()).astype(np.float32) / 255.0   # BGRA premultiplied
    fg = buf[..., [2, 1, 0]] * 255; a = buf[..., 3:4]
    out = S["bg"] + _rays(w, h, t)[..., None]
    out = fg + out * (1 - a)
    # the two big friends glide slowly through (whale one way, octopus the other), 120 s per crossing
    items = []
    for i, name in enumerate(S["big"]):
        ch = S["chars"].setdefault(name, CHARACTERS[name](seed=i + 1))
        u = ((t / 120.0) + i * 0.5) % 1.0
        x = (-0.2 + u * 1.4) * w if i == 0 else (1.2 - u * 1.4) * w
        y = h * (0.42 + 0.18 * i) + 30 * math.sin(2 * math.pi * t / 12.0 + i)
        items.append((ch, x, y + h * 0.04, h * 0.21, {"tilt": 4 * math.sin(2 * math.pi * t / 10.0 + i), "smile": 0.8}))
    rgba = compose(items, w, h, t, rgba=True)
    out = rgba[..., :3] * 255 + out * (1 - rgba[..., 3:4])
    return np.clip(out, 0, 255).astype(np.uint8)


def render_aquarium(out: Path, audio: str, seed: int, fps=15, w=960, h=540) -> dict:
    """Drawn at 960x540 (0.3 s/frame instead of 1.1 s) and upscaled to 1080p: a slow, soft scene loses nothing."""
    S = scene(seed, w, h)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                audio], capture_output=True, text=True).stdout.strip())
    with tempfile.TemporaryDirectory() as td:
        loop = Path(td) / "loop.mp4"
        p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                              "-s", f"{w}x{h}", "-r", str(fps), "-i", "-", "-vf", "scale=1920:1080:flags=lanczos", "-c:v", "libx264", "-preset", "medium",
                              "-crf", "20", "-pix_fmt", "yuv420p", str(loop)], stdin=subprocess.PIPE)
        for f in range(int(min(LOOP_S, dur) * fps)):
            p.stdin.write(frame(f / fps, w, h, S).tobytes())
        p.stdin.close()
        if p.wait():
            raise RuntimeError("ffmpeg failed")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-stream_loop", "-1", "-i", str(loop), "-i", audio,
                        "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                        "-af", f"afade=in:d=3,afade=out:st={max(0, dur - 6):.2f}:d=6", "-t", f"{dur:.2f}",
                        "-movflags", "+faststart", str(out)], check=True)
    return {"big": S["big"], "fish": len(S["fish"]), "jellies": len(S["jellies"]), "duration": dur}
