"""Sunny Orange — round, bright orange with a dimpled peel and a little leaf."""
from __future__ import annotations

import math
import random

from ..style import glossy_fill, highlight, hex2rgb
from .base import Character


class Orange(Character):
    color = hex2rgb("#ff8a00")
    glow_color = hex2rgb("#ffa53a")

    def body(self, ctx, r):
        ctx.arc(0, 0, r, 0, 2 * math.pi)
        glossy_fill(ctx, 0, 0, r, self.color)
        ctx.new_path()
        rnd = random.Random(3)                                # peel dimples
        for _ in range(28):
            a, d = rnd.uniform(0, 2 * math.pi), r * math.sqrt(rnd.uniform(0.2, 0.9))
            x, y = d * math.cos(a), d * math.sin(a)
            if abs(x) < r * 0.6 and -r * 0.35 < y < r * 0.6:
                continue
            ctx.arc(x, y, r * 0.025, 0, 2 * math.pi)
            ctx.set_source_rgba(0.75, 0.35, 0.0, 0.35); ctx.fill()
        highlight(ctx, -r * 0.4, -r * 0.48, r * 0.32, r * 0.17, -0.6, 0.6)

    def decorate(self, ctx, r):
        ctx.arc(0, -r * 0.96, r * 0.07, 0, 2 * math.pi); ctx.set_source_rgb(0.35, 0.5, 0.15); ctx.fill()
        ctx.save(); ctx.translate(r * 0.04, -r * 0.98); ctx.rotate(-0.5)
        ctx.move_to(0, 0); ctx.curve_to(r * 0.15, -r * 0.16, r * 0.4, -r * 0.12, r * 0.48, 0)
        ctx.curve_to(r * 0.4, r * 0.1, r * 0.15, r * 0.12, 0, 0)
        ctx.set_source_rgb(0.25, 0.75, 0.3); ctx.fill(); ctx.restore()

    def face_pos(self, r):
        return 0.0, r * 0.08, r * 0.92
