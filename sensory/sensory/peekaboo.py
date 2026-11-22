"""Peek-a-boo: friends hide behind gift boxes, bushes and clouds and pop up exactly on the beat.

Every 2 bars one friend peeks out (rise on beat 1 with an elastic ease, dance, wave, hide on beats 7-8);
in chorus sections (B) everyone pops up together; in the break all hide and the hiding places wiggle
("where are they?"), then everybody jumps out on the next downbeat. Music: sensory.music (beat map) →
motion is on the beat by construction. Drawn at 960x540 and upscaled (cheap, soft shapes).
"""
from __future__ import annotations

import math
import random
import subprocess
from pathlib import Path

import cairo
import numpy as np

from .characters import CHARACTERS
from .easing import dance_pose, elastic_out, ease_in_out
from .render import beatmap_phase, compose, section_at

BG = [((255, 214, 230), (255, 160, 200)), ((200, 235, 255), (120, 190, 255)), ((215, 255, 215), (140, 220, 150)),
      ((255, 240, 200), (255, 200, 120)), ((230, 220, 255), (170, 150, 255))]
HIDERS = ["gift", "bush", "cloud"]
GIFT_COLS = [(0.95, 0.3, 0.4), (0.25, 0.6, 0.95), (1.0, 0.75, 0.2), (0.55, 0.35, 0.9)]


def _hider(ctx, kind, x, y, w, h, wiggle, col):
    ctx.save(); ctx.translate(x, y); ctx.rotate(math.radians(wiggle))
    if kind == "gift":
        ctx.set_source_rgb(*col)
        _rounded(ctx, -w / 2, -h / 2, w, h, w * 0.06); ctx.fill()
        ctx.set_source_rgb(1, 0.95, 0.5)
        ctx.rectangle(-w * 0.07, -h / 2, w * 0.14, h); ctx.fill()
        ctx.rectangle(-w / 2, -h * 0.12, w, h * 0.24); ctx.fill()
        for s in (-1, 1):                                       # bow
            ctx.save(); ctx.translate(0, -h / 2); ctx.scale(1, 0.6)
            ctx.arc(s * w * 0.12, -w * 0.08, w * 0.11, 0, 2 * math.pi); ctx.restore(); ctx.fill()
    elif kind == "bush":
        ctx.set_source_rgb(0.25, 0.7, 0.3)
        for dx, dy, r in ((-0.3, 0.1, 0.32), (0.0, -0.1, 0.38), (0.3, 0.1, 0.32), (-0.15, 0.25, 0.3), (0.15, 0.25, 0.3)):
            ctx.arc(dx * w, dy * h, r * w, 0, 2 * math.pi); ctx.fill()
        ctx.set_source_rgb(0.35, 0.82, 0.38)
        ctx.arc(-0.05 * w, -0.2 * h, 0.15 * w, 0, 2 * math.pi); ctx.fill()
        ctx.set_source_rgb(1, 0.45, 0.6)
        for dx, dy in ((-0.25, 0.0), (0.2, -0.15), (0.3, 0.2), (-0.1, 0.3)):
            ctx.arc(dx * w, dy * h, 0.035 * w, 0, 2 * math.pi); ctx.fill()
    else:  # cloud
        ctx.set_source_rgb(1, 1, 1)
        for dx, dy, r in ((-0.3, 0.12, 0.26), (-0.05, -0.08, 0.34), (0.25, 0.05, 0.3), (0.0, 0.2, 0.3)):
            ctx.arc(dx * w, dy * h, r * w, 0, 2 * math.pi); ctx.fill()
        ctx.set_source_rgb(0.2, 0.2, 0.3)
        for ex in (-0.12, 0.12):
            ctx.arc(ex * w, 0.05 * h, 0.03 * w, 0, 2 * math.pi); ctx.fill()
        ctx.set_line_width(w * 0.02); ctx.arc(0, 0.1 * h, 0.07 * w, 0.4, 2.74); ctx.stroke()
    ctx.restore()


def _rounded(ctx, x, y, w, h, r):
    ctx.new_sub_path()
    ctx.arc(x + w - r, y + r, r, -math.pi / 2, 0); ctx.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    ctx.arc(x + r, y + h - r, r, math.pi / 2, math.pi); ctx.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    ctx.close_path()


def _bg(w, h, inner, outer):
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt(((xx - w / 2) / (w * 0.7)) ** 2 + ((yy - h * 0.4) / (h * 0.9)) ** 2).clip(0, 1)[..., None]
    return np.array(inner, np.float32) * (1 - d) + np.array(outer, np.float32) * d


def plan(bmap: dict, pool: list[str], seed: int) -> dict:
    rnd = random.Random(seed)
    sections = []
    for s in bmap["sections"]:
        hiders = rnd.sample(HIDERS * 2, 3)
        sections.append(dict(s, cast=rnd.sample(pool, 3), hiders=hiders, bg=rnd.randrange(len(BG)),
                             cols=[rnd.choice(GIFT_COLS) for _ in range(3)]))
    return {"sections": sections, "chars": {}, "bgs": {}}


def frame(t, bmap, P, w, h):
    sec = next((s for s in P["sections"] if s["start"] <= t < s["end"]), P["sections"][-1])
    name = sec["name"].rstrip("2")
    bg = P["bgs"].get(sec["bg"])
    if bg is None:
        bg = P["bgs"][sec["bg"]] = _bg(w, h, *BG[sec["bg"]])
    beat, ph = beatmap_phase(bmap, t)
    sec_beat = int(round((t - sec["start"]) / bmap["beat_s"] - ph))
    xs = (0.2 * w, 0.5 * w, 0.8 * w)
    base_y = h * 0.78
    hw, hh = w * 0.24, h * 0.36
    items = []
    for i in range(3):
        slot_beat = sec_beat % 8
        if name in ("B",):                                     # chorus: everyone out, dancing
            vis = 1.0 if sec_beat >= 1 or ph > 0.3 else elastic_out(ph / 0.3)
        elif name == "break" or name == "intro":
            vis = 0.0
        elif name == "outro":
            vis = max(0.0, 1.0 - (t - sec["start"]) / (sec["end"] - sec["start"]) * 1.5)
        else:                                                  # A: one friend per 2 bars, in turn
            who = (sec_beat // 8) % 3
            if i != who:
                vis = 0.0
            elif slot_beat == 0:
                vis = elastic_out(min(1.0, ph / 0.6))
            elif slot_beat < 6:
                vis = 1.0
            elif slot_beat == 6:
                vis = 1.0 - ease_in_out(ph)
            else:
                vis = 0.0
        if vis <= 0.01:
            continue
        cname = sec["cast"][i]
        ch = P["chars"].setdefault((cname, i), CHARACTERS[cname](seed=i + 1))
        pose = dance_pose(beat, ph, "bounce", amp=0.6) if vis >= 1.0 else {"smile": 1.3, "happy": True}
        r = h * 0.17                                           # hidden: whole friend behind the hiding place
        # sprite spans about (y - 1.65 r) .. (y + 0.13 r); hidden = sprite fully behind the hiding place,
        # A: peeks out with the lower half still hidden; B (chorus): stands on top of it
        htop = base_y - hh / 2
        bottom = htop + 1.75 * r + ((0.05 if name == "B" else 0.6) * r - 1.75 * r) * vis
        y = bottom - 0.13 * r
        items.append((ch, xs[i], y, r, pose))
    rgba = compose(items, w, h, t, rgba=True)
    out = rgba[..., :3] * 255 + bg * (1 - rgba[..., 3:4])
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    ctx = cairo.Context(s)
    for i in range(3):
        wig = 0.0
        if name == "break":
            wig = 6 * math.sin(2 * math.pi * ph) * (1 if (beat + i) % 2 else -1)
        _hider(ctx, sec["hiders"][i], xs[i], base_y, hw, hh, wig, sec["cols"][i])
    buf = np.ndarray((h, w, 4), np.uint8, s.get_data()).astype(np.float32) / 255.0
    a = buf[..., 3:4]
    out = buf[..., [2, 1, 0]] * 255 + out * (1 - a)
    return np.clip(out, 0, 255).astype(np.uint8)


def render_peekaboo(out: Path, wav: Path, bmap: dict, pool: list[str], seed: int, fps=25, w=960, h=540) -> dict:
    P = plan(bmap, pool, seed)
    dur = bmap["duration"] + 1.5
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{w}x{h}", "-r", str(fps), "-i", "-", "-i", str(wav), "-t", f"{dur:.2f}",
                          "-vf", "scale=1920:1080:flags=lanczos", "-c:a", "aac", "-b:a", "192k",
                          "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                          "-movflags", "+faststart", str(out)], stdin=subprocess.PIPE)
    for f in range(int(dur * fps)):
        p.stdin.write(frame(f / fps, bmap, P, w, h).tobytes())
    p.stdin.close()
    if p.wait():
        raise RuntimeError("ffmpeg failed")
    return {"cast": sorted({c for s in P["sections"] for c in s["cast"]})}
