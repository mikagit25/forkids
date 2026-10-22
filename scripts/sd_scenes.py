#!/usr/bin/env python3
"""
Sacred Drift — procedural animated scenes (pure code: numpy + PIL), one family per music style.

Each scene is a function of (t seconds, width, height, params-from-seed), so the same code
gives a still preview, a seamless loop, or a long video. Params are drawn from a seed, so every
video gets its own palette / layout / time of day.

Scenes:
  lake       misty mountain lake, stone cairn, ripples on water        → bowls
  cosmic     nebula, star field with parallax, slow drift               → cosmic
  night      moonlit sky, slow clouds, treeline                         → sleep
  mandala    rotating sacred-geometry rings, hue from the Hz            → solfeggio
  window     rain on a window, bokeh lights behind the glass            → rain
  sunrise    sun on the horizon, layered hills, light rays, mist        → morning

Preview:
  python3 scripts/sd_scenes.py --preview /tmp/scenes --seed 3
"""
from __future__ import annotations

import argparse
import bisect
import random
import colorsys
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import zoom


# ── helpers ───────────────────────────────────────────────────────────────────

def lerp(a, b, t):
    return a + (b - a) * t


def grad(h, w, stops):
    """Vertical gradient; stops = [(pos 0..1, (r,g,b)), ...]."""
    y = np.linspace(0, 1, h)[:, None]
    out = np.zeros((h, 1, 3), np.float32)
    for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
        m = (y >= p0) & (y <= p1)
        k = ((y - p0) / max(p1 - p0, 1e-6)).clip(0, 1)
        out += m[..., None] * lerp(np.array(c0, np.float32), np.array(c1, np.float32), k[..., None])
    return np.repeat(out, w, axis=1)


def fbm(h, w, rng, octaves=5, base=4, persistence=0.55):
    """Fractal value noise in [0,1] (cheap: upsampled random grids)."""
    acc = np.zeros((h, w), np.float32); amp, tot = 1.0, 0.0
    for o in range(octaves):
        gh, gw = base * 2 ** o + 1, int(base * 2 ** o * w / h) + 1
        g = rng.random((gh, gw)).astype(np.float32)
        up = zoom(g, (h / gh, w / gw), order=3)[:h, :w]
        acc[: up.shape[0], : up.shape[1]] += amp * up
        tot += amp; amp *= persistence
    acc /= tot
    return (acc - acc.min()) / (acc.max() - acc.min() + 1e-6)


def ridge(w, rng, base, amp, octaves=6):
    x = np.arange(w, dtype=np.float32); y = np.zeros(w, np.float32); f, a = 1 / 700, amp
    for _ in range(octaves):
        y += np.sin(x * f * 2 * np.pi + rng.random() * 6.28) * a
        f *= 2.05; a *= 0.48
    return base - y


LOOP = 240.0   # seconds: every motion is periodic over this (or a divisor), so loops are seamless


def pan(layer: np.ndarray, t: float, w: int, period: float = LOOP, phase: float = 0.0) -> np.ndarray:
    """Window of width w sliding smoothly back and forth over an oversize layer (no wrap seam)."""
    span = layer.shape[1] - w
    off = int(span * 0.5 * (1 - math.cos(2 * math.pi * t / period + phase)))
    return layer[:, off:off + w]


def oversize(make, h, w, factor=1.4):
    a = make(h, int(w * factor))
    return a


def glow(img: np.ndarray, cx, cy, r, color, strength):
    h, w, _ = img.shape
    yy, xx = np.ogrid[:h, :w]
    d2 = ((xx - cx) ** 2 + (yy - cy) ** 2) / (r * r)
    img += np.exp(-d2)[..., None].astype(np.float32) * np.array(color, np.float32) * strength


def rx(P, key, default=0.0):
    """Audio-reactive value for this frame (set by render_sd_video.py); default when rendering without audio."""
    return P.get("rx", {}).get(key, default)


def to_img(a):
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def vignette(a, k=0.35):
    h, w, _ = a.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    v = 1 - k * (((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    return a * v.clip(0.5, 1)[..., None]


def hsv(hh, s, v):
    return tuple(int(255 * c) for c in colorsys.hsv_to_rgb(hh % 1, s, v))


# ── parameters per scene (seeded) ─────────────────────────────────────────────

PALETTES = {
    "lake":    [((24, 22, 54), (126, 92, 140), (236, 170, 150)),   # dawn violet → peach
                ((10, 20, 44), (40, 70, 110), (150, 170, 190)),    # blue hour
                ((30, 24, 30), (120, 80, 70), (230, 180, 120))],   # amber dusk
    "night":   [((4, 8, 24), (16, 30, 62)), ((6, 6, 18), (28, 22, 54)), ((2, 10, 20), (12, 40, 52))],
    "sunrise": [((40, 60, 110), (240, 150, 110), (255, 220, 160)), ((60, 90, 140), (250, 190, 140), (255, 236, 190)),
                ((50, 40, 90), (230, 120, 120), (255, 200, 150))],
}


def params(scene: str, seed: int, hz: float | None = None) -> dict:
    rng = np.random.default_rng(seed)
    P = {"seed": seed, "rng_seed": int(rng.integers(1 << 30))}
    if scene in PALETTES:
        P["palette"] = PALETTES[scene][int(rng.integers(len(PALETTES[scene])))]
    if scene == "cosmic":
        h1 = rng.uniform(0.52, 0.86); P["hues"] = (h1, 0.52 + (h1 - 0.52 + rng.uniform(0.08, 0.2)) % 0.34)
    if scene == "mandala":
        if hz:
            P["hue"] = 0.75 * math.log2(hz / 111) / math.log2(963 / 111)    # low Hz = red/amber → high Hz = violet
        else:
            P["hue"] = float(rng.uniform(0.45, 0.85))                         # no tone: calm teal → violet range
        P["folds"] = int(rng.choice([6, 8, 12]))
        P["style"] = str(rng.choice(["flower", "petals", "polygon"]))
        P["rings"] = int(rng.integers(4, 7))
    if scene == "window":
        P["warm"] = bool(rng.random() < 0.6)
    return P


# ── scenes: frame(t, w, h, P, cache) → PIL.Image ──────────────────────────────

def scene_lake(t, w, h, P, C):
    if "bg" not in C:
        rng = np.random.default_rng(P["rng_seed"])
        top, mid, low = P["palette"]
        hz = int(h * 0.62)
        sky = grad(hz, w, [(0, top), (0.65, mid), (1, low)])
        glow(sky, w * rng.uniform(0.55, 0.8), hz * 0.92, h * 0.35, low, 0.35)
        yy = np.arange(hz)[:, None]
        for i, (base, amp, shade) in enumerate([(hz - h * 0.20, h * 0.06, 0.55), (hz - h * 0.12, h * 0.07, 0.38),
                                                (hz - h * 0.05, h * 0.04, 0.24)]):
            r = ridge(w, rng, base, amp)
            m = (yy >= r[None, :]).astype(np.float32)[..., None]
            col = np.array(mid, np.float32) * shade + np.array(top, np.float32) * (1 - shade) * 0.5
            sky = sky * (1 - m) + col * m
        water = sky[::-1][: h - hz] * 0.55 + np.array(top, np.float32) * 0.25
        C["bg"] = np.concatenate([sky, water], 0)
        m = fbm(h // 2, int(w * 1.4) // 2, rng, 4, 3)
        C["mist"] = zoom(m, (h / m.shape[0], int(w * 1.4) / m.shape[1]), order=1)[:h, :int(w * 1.4)]
        C["hz"] = hz
        # stone cairn (foreground silhouette, left third)
        cx, base = w * (rng.uniform(0.16, 0.28) if rng.random() < 0.6 else rng.uniform(0.72, 0.84)), h * 0.93
        stones, y = [], base
        for k in range(int(rng.integers(4, 7))):
            sw = w * (0.075 - k * 0.011) * rng.uniform(0.9, 1.1); sh = sw * rng.uniform(0.42, 0.55)
            stones.append((cx + rng.uniform(-4, 4), y - sh / 2, sw / 2, sh / 2)); y -= sh * 0.92
        C["stones"], C["ripple_c"] = stones, (cx, base - h * 0.01)
    a = C["bg"].copy()
    hz = C["hz"]
    # drifting mist band over the far shore
    mist = pan(C["mist"], t, w)
    band = np.exp(-((np.arange(h)[:, None] - hz) / (h * 0.06)) ** 2)
    a = lerp(a, np.array([200, 190, 210], np.float32), (mist * band * (0.40 + 0.25 * rx(P, "low")))[..., None])
    im = to_img(vignette(a, 0.3))
    d = ImageDraw.Draw(im, "RGBA")
    # ripples spreading on the water (in video: one ring per bowl strike)
    cx, cy = C["ripple_c"]
    rings = P["rx"]["ripples"] if "rx" in P else [((t % 7.0), 1.0, 0.0), ((t + 3.5) % 7.0, 1.0, 0.0)]
    for age, strength, dx in rings:                                   # (seconds since strike, 0..1, x offset)
        life = 7.0 + 4.0 * strength
        for k, lag in enumerate((0.0, 0.6, 1.2)):                     # each strike sends out 3 rings
            a2 = age - lag
            if a2 <= 0 or a2 > life:
                continue
            r = 18 + a2 * w * 0.028
            al = int((60 + 110 * strength) * (1 - a2 / life) * (1 - 0.3 * k))
            d.ellipse([cx + dx - r, cy - r * 0.18, cx + dx + r, cy + r * 0.18], outline=(232, 226, 245, al), width=2)
    for (sx, sy, srx, sry) in C["stones"]:
        d.ellipse([sx - srx, sy - sry, sx + srx, sy + sry], fill=(18, 16, 24, 255))
    return im


def scene_cosmic(t, w, h, P, C):
    if "neb" not in C:
        rng = np.random.default_rng(P["rng_seed"])
        W2 = int(w * 1.3) // 2
        n1, n2 = fbm(h // 2, W2, rng, 6, 3), fbm(h // 2, W2, rng, 6, 4)
        c1 = np.array(hsv(P["hues"][0], 0.55, 0.8), np.float32); c2 = np.array(hsv(P["hues"][1], 0.5, 0.7), np.float32)
        neb = (n1 ** 3)[..., None] * c1 * 0.9 + (n2 ** 4)[..., None] * c2 * 0.8
        C["neb"] = zoom(neb, (h / neb.shape[0], W2 * 2 / neb.shape[1], 1), order=1)
        C["stars"] = [(rng.random(800) * w, rng.random(800) * h, rng.random(800) ** 4, rng.random(800)) for _ in range(3)]
    shift = t * (w / LOOP)                                         # stars wrap exactly once per loop
    a = np.zeros((h, w, 3), np.float32) + np.array([4, 6, 16], np.float32)
    a += pan(C["neb"], t, w) * (0.85 + 0.3 * rx(P, "env", 0.5))
    im = to_img(a)
    d = ImageDraw.Draw(im, "RGBA")
    for layer, (xs, ys, br, ph) in enumerate(C["stars"]):
        speed = layer + 1                                          # integer → still periodic over LOOP
        amp_tw = 0.25 + 0.35 * rx(P, "high")
        tw = (1 - amp_tw) + amp_tw * np.sin(2 * np.pi * t * np.round(LOOP * (0.12 + ph * 0.3)) / LOOP + ph * 6.28)
        for x, y, b, k in zip((xs + shift * speed) % w, ys, br * tw, ph):
            r = 0.6 + layer * 0.6 + b * 1.6
            al = int(90 + 165 * b)
            d.ellipse([x - r, y - r, x + r, y + r], fill=(235, 235, 255, al))
    for age, (mx, my, ang, ln) in P.get("rx", {}).get("meteors", []):   # shooting star on each strike
        if 0 <= age < 1.4:
            k = age / 1.4
            hx, hy = mx + math.cos(ang) * ln * k, my + math.sin(ang) * ln * k
            tx, ty = hx - math.cos(ang) * ln * 0.35, hy - math.sin(ang) * ln * 0.35
            d.line([tx, ty, hx, hy], fill=(255, 250, 235, int(220 * (1 - k))), width=2)
    return im.filter(ImageFilter.GaussianBlur(0.4))


def scene_night(t, w, h, P, C):
    if "bg" not in C:
        rng = np.random.default_rng(P["rng_seed"])
        top, low = P["palette"]
        a = grad(h, w, [(0, top), (1, low)])
        my = rng.uniform(0.2, 0.32) if w >= h else rng.uniform(0.36, 0.44)   # portrait: below the Shorts hook text
        C["moon"] = (w * rng.uniform(0.6, 0.8), h * my, min(w, h) * 0.055)
        mx, my, mr = C["moon"]
        C["bg"] = a
        W2 = int(w * 1.4)
        cl = fbm(h // 2, W2 // 4, rng, 5, 2)                         # stretched 4x sideways, 2x down: wide clouds
        C["clouds"] = zoom(cl, (h / cl.shape[0], W2 / cl.shape[1]), order=1)[:h, :W2]
        C["stars"] = (rng.random(260) * w, rng.random(260) * h * 0.6, rng.random(260))
        C["trees"] = ridge(w, rng, h * 0.9, h * 0.03, 7) - (rng.random(w) ** 8) * h * 0.04
    a = C["bg"].copy()
    mx, my, mr = C["moon"]
    glow(a, mx, my, mr * 5, (150, 160, 200), 0.30 + 0.25 * rx(P, "env", 0.2))
    im = to_img(a)
    d = ImageDraw.Draw(im, "RGBA")
    xs, ys, ph = C["stars"]
    for x, y, p in zip(xs, ys, ph):
        al = int(80 + 120 * (0.5 + 0.5 * math.sin(t * (0.5 + p) + p * 6.28)))
        d.ellipse([x - 1, y - 1, x + 1, y + 1], fill=(220, 225, 255, al))
    mx, my, mr = C["moon"]
    d.ellipse([mx - mr, my - mr, mx + mr, my + mr], fill=(240, 236, 220, 255))
    a = np.asarray(im).astype(np.float32)
    cl = pan(C["clouds"], t, w)
    dens = ((cl - 0.45) / 0.3).clip(0, 1) * np.linspace(1, 0.2, h)[:, None]
    a = lerp(a, np.array([60, 66, 96], np.float32), (dens * 0.75)[..., None])
    yy = np.arange(h)[:, None]
    m = (yy >= C["trees"][None, :])[..., None]
    a = np.where(m, np.array([4, 6, 12], np.float32), a)
    return to_img(vignette(a, 0.4))


def scene_mandala(t, w, h, P, C):
    hue, folds, style, rings = P["hue"], P["folds"], P.get("style", "flower"), P.get("rings", 5)
    S = min(w, h)                                         # size from the short side → works in 9:16 Shorts too
    base = np.zeros((h, w, 3), np.float32) + np.array(hsv(hue, 0.6, 0.08), np.float32)
    glow(base, w / 2, h / 2, S * 0.5, hsv(hue, 0.5, 0.5),
         0.6 * (1 + 0.15 * math.sin(2 * math.pi * t / 8)) * (0.75 + 0.6 * rx(P, "env", 0.4)))
    im = to_img(base)
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, cy = w / 2, h / 2
    breathe = 1 + 0.03 * math.sin(2 * math.pi * t / 8) + 0.07 * rx(P, "low")
    spec = P.get("rx", {}).get("spectrum")
    if spec is not None:                                              # circular equalizer around the mandala
        R0 = S * 0.43 * breathe
        bands = np.concatenate([spec, spec[::-1]])                    # mirrored → symmetric ring
        n = len(bands)
        for k, v in enumerate(bands):
            ang = 2 * math.pi * k / n - math.pi / 2 + t * 0.01
            L = S * (0.012 + 0.07 * float(v) ** 1.5)
            x0, y0 = cx + R0 * math.cos(ang), cy + R0 * math.sin(ang)
            x1, y1 = cx + (R0 + L) * math.cos(ang), cy + (R0 + L) * math.sin(ang)
            d.line([x0, y0, x1, y1], fill=hsv(hue + 0.05 * float(v), 0.5, 1.0) + (int(90 + 140 * float(v)),),
                   width=max(2, int(S / 300)))
    for ring in range(1, rings + 1):
        R = S * 0.27 * ring / rings * breathe              # outer circles (R*1.55) stay inside the frame
        rot = t * (0.02 if ring % 2 else -0.015) * (1 + ring * 0.3)
        col = hsv(hue + ring * 0.03, 0.55, 1.0) + (int(160 - ring * 14),)
        n = folds * (1 if ring < 3 else 2)
        pts = []
        for k in range(n):
            ang = rot + 2 * math.pi * k / n
            x, y = cx + R * math.cos(ang), cy + R * math.sin(ang)
            pts.append((x, y))
            if style == "flower":
                rr = R * 0.55
                d.ellipse([x - rr, y - rr, x + rr, y + rr], outline=col, width=2)
            elif style == "petals":                                    # lens-shaped petals pointing outwards
                a2 = ang + math.pi / 2; L = R * 0.35
                petal = [(cx + (R - L) * math.cos(ang), cy + (R - L) * math.sin(ang)),
                         (x + L * 0.35 * math.cos(a2), y + L * 0.35 * math.sin(a2)),
                         (cx + (R + L * 0.6) * math.cos(ang), cy + (R + L * 0.6) * math.sin(ang)),
                         (x - L * 0.35 * math.cos(a2), y - L * 0.35 * math.sin(a2))]
                d.polygon(petal, outline=col)
        if style == "polygon":
            d.polygon(pts, outline=col)
            d.polygon(pts[::2] if len(pts) % 2 == 0 else pts, outline=col)
        d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=col, width=1)
    g = layer.filter(ImageFilter.GaussianBlur(6))
    im = Image.alpha_composite(im.convert("RGBA"), g)
    im = Image.alpha_composite(im, layer)
    return im.convert("RGB")


def scene_window(t, w, h, P, C):
    if "bokeh" not in C:
        rng = np.random.default_rng(P["rng_seed"])
        bg = Image.new("RGB", (w, h), (14, 16, 24) if P["warm"] else (10, 16, 26))
        d = ImageDraw.Draw(bg, "RGBA")
        for _ in range(70):
            x, y, r = rng.random() * w, rng.random() * h * 0.85, rng.uniform(10, 46)
            col = (hsv(rng.uniform(0.05, 0.13), 0.6, 1) if P["warm"] else hsv(rng.uniform(0.5, 0.62), 0.4, 1))
            d.ellipse([x - r, y - r, x + r, y + r], fill=col + (int(rng.uniform(40, 120)),))
        C["bokeh"] = np.asarray(bg.filter(ImageFilter.GaussianBlur(14))).astype(np.float32)
        n = 120
        C["drops"] = dict(x=rng.random(n) * w, y0=rng.random(n) * h, sp=rng.uniform(6, 30, n) * (rng.random(n) < 0.3),
                          r=rng.uniform(3, 10, n) * h / 720)
    a = C["bokeh"] * (0.82 + 0.22 * rx(P, "low", 0.4))
    a = a + np.linspace(14, 0, h)[:, None, None]                     # fogged glass at the top
    im = to_img(a)
    d = ImageDraw.Draw(im, "RGBA")
    D = C["drops"]
    for x, y0, sp, r in zip(D["x"], D["y0"], D["sp"], D["r"]):
        y = (y0 + sp * rx(P, "rain_t", t)) % (h + 60) - 30
        ry = r * (1.25 if sp > 0 else 1.0)
        if sp > 0:                                                    # faint wet trail above a sliding drop
            d.line([x, y - r * 9, x, y - r], fill=(160, 170, 190, 22), width=max(1, int(r * 0.5)))
        d.ellipse([x - r, y - ry, x + r, y + ry], fill=(10, 12, 18, 90))                     # refraction (darker)
        d.ellipse([x - r * 0.8, y - ry * 0.8, x + r * 0.8, y + ry * 0.8], fill=(70, 74, 90, 60))
        d.ellipse([x - r * 0.45, y - ry * 0.7, x - r * 0.05, y - ry * 0.3], fill=(235, 240, 255, 150))  # highlight
        d.arc([x - r, y - ry, x + r, y + ry], 20, 160, fill=(200, 210, 230, 90), width=1)      # lit lower rim
    return im.filter(ImageFilter.GaussianBlur(0.6))


def scene_sunrise(t, w, h, P, C):
    if "bg" not in C:
        rng = np.random.default_rng(P["rng_seed"])
        top, mid, low = P["palette"]
        a = grad(h, w, [(0, top), (0.55, mid), (0.72, low), (1, low)])
        C["sun"] = (w * rng.uniform(0.35, 0.65), h * 0.62, h * 0.06)
        sx, sy, sr = C["sun"]
        glow(a, sx, sy, h * 0.45, (255, 210, 150), 0.45)
        yy = np.arange(h)[:, None]
        layers = []
        for i, (base, amp) in enumerate([(h * 0.66, h * 0.05), (h * 0.74, h * 0.06), (h * 0.84, h * 0.05), (h * 0.94, h * 0.04)]):
            r = ridge(w, rng, base, amp)
            depth = i / 3
            col = lerp(np.array(mid, np.float32) * 0.9, np.array([40, 34, 50], np.float32), depth)
            layers.append(((yy >= r[None, :])[..., None], col))
        C["bg"], C["layers"] = a, layers
        m = fbm(h // 2, int(w * 1.4) // 2, rng, 4, 3)
        C["mist"] = zoom(m, (h / m.shape[0], int(w * 1.4) / m.shape[1]), order=1)[:h, :int(w * 1.4)]
        C["rays"] = rng.random(36)
    a = C["bg"].copy()
    sx, sy, sr = C["sun"]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    ang = np.arctan2(yy - sy, xx - sx)
    idx = ((ang + np.pi) / (2 * np.pi) * len(C["rays"])).astype(int) % len(C["rays"])
    rays = C["rays"][idx] * (0.45 + 0.25 * math.sin(2 * math.pi * t / LOOP * 6) + 0.5 * rx(P, "env", 0.4))
    fall = np.exp(-np.hypot(xx - sx, yy - sy) / (h * 0.7)) * (yy < sy)
    a += (rays * fall * 40)[..., None] * np.array([1.0, 0.85, 0.6], np.float32)
    im = to_img(a)
    d = ImageDraw.Draw(im)
    d.ellipse([sx - sr, sy - sr, sx + sr, sy + sr], fill=(255, 240, 210))
    a = np.asarray(im).astype(np.float32)
    for i, (m, col) in enumerate(C["layers"]):
        a = np.where(m, col, a)
        mist = pan(C["mist"], t, w, phase=i * 1.3)
        band = m[..., 0] * np.exp(-((yy - (h * (0.66 + i * 0.09))) / (h * 0.05)) ** 2)
        a = lerp(a, np.array([250, 225, 210], np.float32), (mist * band * 0.35)[..., None])
    return to_img(vignette(a, 0.25))


def strike_flash(t: float, strikes) -> tuple[float, float]:
    """Lightning brightness at time t. strikes = [(thunder_time_s, distance 0..1), ...].
    Light arrives before the sound (≈3 s per km → we use 0.4 + 3·distance s), near strikes
    flicker 2–3 times, far ones are one soft glow. Returns (brightness 0..1, x position 0..1)."""
    if not strikes:
        return 0.0, 0.5
    i = bisect.bisect_right(strikes, (t + 3.5, 9.0))
    best, bx = 0.0, 0.5
    for ts, dist in strikes[max(0, i - 3): i]:
        tl = ts - (0.4 + 3.0 * dist)                 # flash time
        dt = t - tl
        if dt < 0 or dt > 2.5:
            continue
        r = random.Random(int(ts * 100))
        if dist < 0.5:                               # near: bright, flickering
            v = sum(a * math.exp(-(dt - o) / 0.09) for o, a in ((0, 1.0), (0.13, 0.55), (0.34 + r.random() * 0.2, 0.8))
                    if dt >= o)
            v *= 1.0 - 0.6 * dist
        else:                                        # far: one soft glow behind the clouds
            v = 0.45 * (1 - dist * 0.5) * math.exp(-max(dt - 0.15, 0) / 0.45) * min(1, dt / 0.15)
        if v > best:
            best, bx = v, r.uniform(0.15, 0.85)
    return min(best, 1.3), bx


def scene_dark(t, w, h, P, C):
    """Dark screen for 8–10 h sleep videos: near-black sky, faint slow clouds, black treeline;
    lightning lights the clouds from within on every thunder strike. Cheap to render."""
    if "bg" not in C:
        rng = np.random.default_rng(P["rng_seed"])
        C["bg"] = grad(h, w, [(0, (7, 9, 18)), (0.7, (3, 4, 10)), (1, (2, 2, 6))])
        W2 = int(w * 1.5)
        cl = fbm(h // 2, W2 // 4, rng, 5, 2)
        C["clouds"] = zoom(cl, (h / cl.shape[0], W2 / cl.shape[1]), order=1)[:h, :W2].astype(np.float32)
        C["trees"] = ridge(w, rng, h * 0.92, h * 0.025, 7) - (rng.random(w) ** 8) * h * 0.035
        C["mask"] = (np.arange(h)[:, None] >= C["trees"][None, :])[..., None]
        C["dither"] = (rng.random((h, w, 1)).astype(np.float32) - 0.5) * 1.6   # static: no banding, costs no bitrate
        C["xx"] = np.linspace(0, 1, w, dtype=np.float32)[None, :]
        C["yy"] = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    cl = pan(C["clouds"], t, w, period=LOOP * 2)
    dens = ((cl - 0.35) / 0.4).clip(0, 1) * (1.0 - 0.6 * C["yy"])
    env = rx(P, "env", 0.3)
    a = C["bg"] + (dens * (5 + 3 * env))[..., None] * np.array([0.8, 0.9, 1.3], np.float32)
    fl, fx = strike_flash(t, P.get("strikes"))
    if fl > 0.01:
        spot = np.exp(-((C["xx"] - fx) ** 2) / 0.05 - (C["yy"] - 0.25) ** 2 / 0.12)
        lit = (0.25 + 0.75 * dens) * (0.35 + 0.65 * spot) * fl
        a = a + lit[..., None] * np.array([150, 160, 200], np.float32)
    a = np.where(C["mask"], np.array([1, 1, 3], np.float32), a + C["dither"])
    return to_img(a)


SCENES = {"lake": scene_lake, "cosmic": scene_cosmic, "night": scene_night,
          "mandala": scene_mandala, "window": scene_window, "sunrise": scene_sunrise, "dark": scene_dark}
STYLE_SCENE = {"bowls": "lake", "cosmic": "cosmic", "sleep": "night",
               "solfeggio": "mandala", "rain": "window", "morning": "sunrise", "storm": "dark"}
# scenes that fit each style, with weights — the mandala (audience favourite) also suits bowls/cosmic/morning
STYLE_SCENES = {"bowls": [("lake", 0.5), ("mandala", 0.5)], "cosmic": [("cosmic", 0.6), ("mandala", 0.4)],
                "sleep": [("night", 1.0)], "solfeggio": [("mandala", 1.0)], "rain": [("window", 1.0)],
                "morning": [("sunrise", 0.65), ("mandala", 0.35)], "storm": [("dark", 0.6), ("window", 0.4)]}
FAST_SCENES = {"dark"}       # rendered small + 12 fps + fast encode → practical for 8–10 h videos


def pick_scene(style: str, seed: int) -> str:
    opts = STYLE_SCENES.get(style, [("lake", 1.0)])
    r = np.random.default_rng(seed + 4242).random()
    acc = 0.0
    for name, w in opts:
        acc += w
        if r < acc:
            return name
    return opts[-1][0]


def frame(scene, t, w, h, P, cache):
    return SCENES[scene](t, w, h, P, cache)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", required=True)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--w", type=int, default=1280)
    ap.add_argument("--h", type=int, default=720)
    a = ap.parse_args()
    out = Path(a.preview); out.mkdir(parents=True, exist_ok=True)
    for sc in SCENES:
        frame(sc, 3.0, a.w, a.h, params(sc, a.seed), {}).save(out / f"{sc}_{a.seed}.png")
        print(sc)
