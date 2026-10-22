"""Visual grammar: pure black background, saturated glossy bodies, white highlight, soft glow."""
from __future__ import annotations

import cairo
import numpy as np
from scipy.ndimage import gaussian_filter

BG = (0, 0, 0)


def hex2rgb(h: str) -> tuple[float, float, float]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def mix(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def lighten(c, t):
    return mix(c, (1, 1, 1), t)


def darken(c, t):
    return mix(c, (0, 0, 0), t)


def glossy_fill(ctx: cairo.Context, cx, cy, r, color):
    """Radial gradient: bright spot up-left → saturated colour → darker rim (reads as 3D)."""
    g = cairo.RadialGradient(cx - r * 0.35, cy - r * 0.4, r * 0.05, cx, cy, r * 1.15)
    g.add_color_stop_rgb(0.0, *lighten(color, 0.45))
    g.add_color_stop_rgb(0.45, *color)
    g.add_color_stop_rgb(0.85, *darken(color, 0.25))
    g.add_color_stop_rgb(1.0, *darken(color, 0.45))
    ctx.set_source(g)
    ctx.fill_preserve()


def highlight(ctx: cairo.Context, cx, cy, rx, ry, angle=-0.5, alpha=0.6):
    """White glossy highlight ellipse that fades out at its lower edge."""
    ctx.save()
    ctx.translate(cx, cy); ctx.rotate(angle); ctx.scale(rx, ry)
    ctx.arc(0, 0, 1, 0, 2 * np.pi)
    ctx.restore()
    g = cairo.LinearGradient(cx, cy - ry, cx, cy + ry)
    g.add_color_stop_rgba(0, 1, 1, 1, alpha)
    g.add_color_stop_rgba(1, 1, 1, 1, 0.0)
    ctx.set_source(g)
    ctx.fill()


def surface(w, h):
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    ctx = cairo.Context(s)
    ctx.set_antialias(cairo.ANTIALIAS_BEST)
    return s, ctx


def to_array(s: cairo.ImageSurface) -> np.ndarray:
    """Cairo BGRA premultiplied → float RGBA (premultiplied) array h×w×4."""
    s.flush()
    a = np.ndarray((s.get_height(), s.get_stride() // 4, 4), np.uint8, s.get_data())[:, : s.get_width()]
    return a[..., [2, 1, 0, 3]].astype(np.float32) / 255


def add_glow(layer: np.ndarray, color, radius=28, strength=0.55) -> np.ndarray:
    """Soft coloured halo from the layer's alpha, placed under it (black background → additive)."""
    a = gaussian_filter(layer[..., 3], radius)
    glow = np.zeros_like(layer)
    glow[..., :3] = a[..., None] * np.array(color, np.float32) * strength
    glow[..., 3] = a * strength
    return glow


def over(dst: np.ndarray, src: np.ndarray) -> np.ndarray:
    """Premultiplied 'over'."""
    return src + dst * (1 - src[..., 3:4])


def flatten(rgba: np.ndarray, bg=BG) -> np.ndarray:
    out = rgba[..., :3] + np.array(bg, np.float32) * (1 - rgba[..., 3:4])
    return (np.clip(out, 0, 1) * 255).astype(np.uint8)
