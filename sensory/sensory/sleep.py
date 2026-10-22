"""Sleep format: sleepy fruit friends float slowly among twinkling stars to a calm track.

Visuals are a seamless loop (default 240 s: every motion period divides it) rendered once at
15 fps, then repeated under the full-length music with ffmpeg — a 1-hour sleep video costs the
same render time as 4 minutes. The music itself is never looped (use a full-length track).
Cast changes every 60 s with a slow shrink/grow; eyes closed (‿), small content smiles.
"""
from __future__ import annotations

import math
import random
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from .characters import CHARACTERS
from .render import compose
from .style import flatten

PERIODS = (8.0, 12.0, 10.0, 15.0, 20.0)                     # all divide 240


def _stars(rnd: random.Random, w, h, n=60):
    return [(rnd.uniform(0, w), rnd.uniform(0, h * 0.95), rnd.uniform(2.0, 4.5), rnd.choice((4.0, 6.0, 8.0, 12.0)),
             rnd.uniform(0, 6.28)) for _ in range(n)]


def _star_layer(stars, t, w, h):
    img = np.zeros((h, w, 3), np.float32)
    for x, y, r, p, ph in stars:
        b = 0.55 + 0.45 * (0.5 + 0.5 * math.sin(2 * math.pi * t / p + ph))   # never below ~0.55 (always visible)
        R = int(r * 4)
        x0, y0 = int(x) - R, int(y) - R
        if x0 < 0 or y0 < 0 or x0 + 2 * R >= w or y0 + 2 * R >= h:
            continue
        yy, xx = np.mgrid[-R:R, -R:R]
        g = np.exp(-(xx ** 2 + yy ** 2) / (2 * r * r)) * b
        img[y0:y0 + 2 * R, x0:x0 + 2 * R] += g[..., None] * np.array([255, 245, 210], np.float32) * 0.8
    return img


def groups(pool, seed, loop_s=240.0, per=60.0):
    rnd = random.Random(seed)
    out = []
    for g in range(int(loop_s // per)):
        cast = rnd.sample(pool, 3)
        out.append(cast)
    return out


def frame(t, w, h, P):
    per = P["per"]
    g = int(t // per) % len(P["groups"])
    local = t - (t // per) * per
    fade = min(1.0, local / 4.0, (per - local) / 4.0)          # 4 s grow / shrink
    fade = 0.5 - 0.5 * math.cos(math.pi * max(0.0, fade))
    items = []
    for i, name in enumerate(P["groups"][g]):
        ch = P["chars"].setdefault((name, g, i), CHARACTERS[name](seed=g * 10 + i + 1))
        per_i = PERIODS[(i + g) % len(PERIODS)]
        x = w * (0.25 + 0.25 * i) + 30 * math.sin(2 * math.pi * t / (per_i * 2) + i)
        y = h * 0.52 + 40 * math.sin(2 * math.pi * t / per_i + i * 1.7)
        tilt = 6 * math.sin(2 * math.pi * t / (per_i * 1.5) + i)
        r = (h / 1080) * 190 * fade * (1 + 0.03 * math.sin(2 * math.pi * t / per_i))
        if r < 3:
            continue
        items.append((ch, x, y, r, {"tilt": tilt, "sleepy": True, "smile": 0.3}))
    rgba = compose(items, w, h, t, rgba=True)
    bg = _star_layer(P["stars"], t, w, h)
    out = rgba[..., :3] * 255 + bg * (1 - rgba[..., 3:4])
    return np.clip(out * 0.85, 0, 255).astype(np.uint8)     # a little dimmer: bedtime


def render_sleep(out: Path, audio: str, pool: list[str], seed: int, loop_s=240.0, fps=15, w=1920, h=1080,
                 minutes: float | None = None):
    rnd = random.Random(seed)
    P = {"groups": groups(pool, seed, loop_s), "per": 60.0, "stars": _stars(rnd, w, h), "chars": {}}
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                audio], capture_output=True, text=True).stdout.strip())
    if minutes:
        dur = min(dur, minutes * 60)
    with tempfile.TemporaryDirectory() as td:
        loop = Path(td) / "loop.mp4"
        cmd = ["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
               "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
               str(loop)]
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for f in range(int(min(loop_s, dur) * fps)):
            p.stdin.write(frame(f / fps, w, h, P).tobytes())
        p.stdin.close()
        if p.wait():
            raise RuntimeError("ffmpeg failed")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-stream_loop", "-1", "-i", str(loop), "-i", audio,
                        "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                        "-af", f"afade=in:d=3,afade=out:st={max(0, dur - 6):.2f}:d=6", "-t", f"{dur:.2f}",
                        "-movflags", "+faststart", str(out)], check=True)
    return P["groups"]
