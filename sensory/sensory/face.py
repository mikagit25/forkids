"""Face: big glossy eyes (white + black pupil + two highlights), smile, cheeks, blinking."""
from __future__ import annotations

import math
import random

import cairo


def blink_amount(t: float, seed: int) -> float:
    """1 = open, ~0.1 = closed. Blinks every 3–6 s, 0.15 s long."""
    rnd = random.Random(seed)
    tb = rnd.uniform(0.5, 3.0)
    while tb < t + 1:
        if tb <= t < tb + 0.15:
            x = (t - tb) / 0.15
            return 1 - 0.9 * math.sin(math.pi * x)
        tb += rnd.uniform(3.0, 6.0)
    return 1.0


def happy_eye(ctx: cairo.Context, x, y, r):
    """Closed, smiling eye (^) — used for a giggle."""
    ctx.save()
    ctx.move_to(x - r * 0.8, y + r * 0.2)
    ctx.curve_to(x - r * 0.5, y - r * 0.75, x + r * 0.5, y - r * 0.75, x + r * 0.8, y + r * 0.2)
    ctx.set_source_rgb(0.06, 0.05, 0.08); ctx.set_line_width(r * 0.28)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND); ctx.stroke()
    ctx.restore()


def eye(ctx: cairo.Context, x, y, r, look=(0.0, 0.0), open_=1.0):
    ctx.save()
    ctx.translate(x, y); ctx.scale(1, max(open_, 0.1))
    ctx.arc(0, 0, r, 0, 2 * math.pi)
    ctx.set_source_rgb(1, 1, 1); ctx.fill_preserve()
    ctx.set_source_rgba(0, 0, 0, 0.25); ctx.set_line_width(r * 0.06); ctx.stroke()
    px, py = look[0] * r * 0.22, look[1] * r * 0.18 + r * 0.08
    ctx.arc(px, py, r * 0.62, 0, 2 * math.pi)
    ctx.set_source_rgb(0.06, 0.05, 0.08); ctx.fill()
    ctx.arc(px - r * 0.22, py - r * 0.24, r * 0.22, 0, 2 * math.pi)
    ctx.set_source_rgb(1, 1, 1); ctx.fill()
    ctx.arc(px + r * 0.2, py + r * 0.2, r * 0.09, 0, 2 * math.pi)
    ctx.fill()
    ctx.restore()


def face(ctx: cairo.Context, cx, cy, size, t=0.0, seed=1, look=(0.0, 0.0), smile=1.0, cheeks=(1.0, 0.45, 0.6),
         happy=False):
    """size ≈ body radius. Eyes sit slightly above centre, mouth below.
    smile: 0.3 = small closed-ish smile … 1.4 = big open laugh. happy: ^ ^ giggle eyes."""
    o = blink_amount(t, seed)
    er = size * 0.2
    dx = size * 0.3
    for sx in (-1, 1):
        if happy:
            happy_eye(ctx, cx + sx * dx, cy - size * 0.08, er)
        else:
            eye(ctx, cx + sx * dx, cy - size * 0.08, er, look, o)
    # cheeks
    for sx in (-1, 1):
        g = cairo.RadialGradient(cx + sx * dx * 1.45, cy + size * 0.2, 0, cx + sx * dx * 1.45, cy + size * 0.2, size * 0.16)
        g.add_color_stop_rgba(0, *cheeks, 0.9 if happy else 0.75); g.add_color_stop_rgba(1, *cheeks, 0)
        ctx.set_source(g)
        ctx.arc(cx + sx * dx * 1.45, cy + size * 0.2, size * 0.16, 0, 2 * math.pi); ctx.fill()
    # smile: open mouth with a tongue
    mw, mh = size * (0.22 + 0.04 * smile), size * 0.17 * smile
    my = cy + size * 0.2
    ctx.save()
    ctx.move_to(cx - mw, my)
    ctx.curve_to(cx - mw * 0.8, my + mh * 1.6, cx + mw * 0.8, my + mh * 1.6, cx + mw, my)
    ctx.close_path()
    ctx.set_source_rgb(0.32, 0.04, 0.10); ctx.fill_preserve()
    ctx.clip()
    ctx.arc(cx, my + mh * 1.35, mw * 0.55, 0, 2 * math.pi)
    ctx.set_source_rgb(1.0, 0.45, 0.55); ctx.fill()
    ctx.restore()
    ctx.move_to(cx - mw, my)
    ctx.curve_to(cx - mw * 0.8, my + mh * 1.6, cx + mw * 0.8, my + mh * 1.6, cx + mw, my)
    ctx.close_path()
    ctx.set_source_rgba(0.15, 0.02, 0.05, 0.9); ctx.set_line_width(size * 0.025)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND); ctx.stroke()
