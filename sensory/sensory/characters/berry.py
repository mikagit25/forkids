"""Bobbleberry — a round, glossy strawberry-pink berry with a leaf crown and golden seeds."""
from __future__ import annotations

import math
import random

import cairo

from ..style import glossy_fill, highlight, hex2rgb
from .base import Character


class Berry(Character):
    color = hex2rgb("#ff2d55")
    glow_color = hex2rgb("#ff4d6d")

    def path(self, ctx, r):
        # rounded heart-ish berry: wide top, soft point at the bottom
        ctx.move_to(0, -r * 0.92)
        ctx.curve_to(r * 0.75, -r * 1.05, r * 1.1, -r * 0.35, r * 0.95, r * 0.2)
        ctx.curve_to(r * 0.8, r * 0.7, r * 0.35, r * 1.0, 0, r * 1.02)
        ctx.curve_to(-r * 0.35, r * 1.0, -r * 0.8, r * 0.7, -r * 0.95, r * 0.2)
        ctx.curve_to(-r * 1.1, -r * 0.35, -r * 0.75, -r * 1.05, 0, -r * 0.92)
        ctx.close_path()

    def body(self, ctx, r):
        self.path(ctx, r)
        glossy_fill(ctx, 0, 0, r, self.color)
        ctx.new_path()
        rnd = random.Random(7)                        # seeds: fixed pattern, small glossy drops
        for row in range(5):
            y = -r * 0.45 + row * r * 0.3
            n = 5 - abs(row - 1)
            for k in range(n):
                x = (k - (n - 1) / 2) * r * 0.36 + rnd.uniform(-1, 1) * r * 0.04
                if abs(x) < r * 0.6 and -r * 0.3 < y < r * 0.6:
                    continue                          # keep the face area clean
                ctx.save(); ctx.translate(x, y); ctx.rotate(x / r * 0.5); ctx.scale(1, 1.6)
                ctx.arc(0, 0, r * 0.028, 0, 2 * math.pi); ctx.restore()
                ctx.set_source_rgb(1.0, 0.86, 0.35); ctx.fill()
        highlight(ctx, -r * 0.38, -r * 0.52, r * 0.34, r * 0.16, -0.55, 0.65)

    def decorate(self, ctx, r):
        for k in range(5):                            # leaf crown
            a = -math.pi / 2 + (k - 2) * 0.5
            ctx.save(); ctx.translate(0, -r * 0.9); ctx.rotate(a + math.pi / 2)
            ctx.move_to(0, 0)
            ctx.curve_to(r * 0.16, -r * 0.08, r * 0.14, -r * 0.34, 0, -r * 0.42)
            ctx.curve_to(-r * 0.14, -r * 0.34, -r * 0.16, -r * 0.08, 0, 0)
            g = cairo.LinearGradient(0, 0, 0, -r * 0.42)
            g.add_color_stop_rgb(0, 0.10, 0.55, 0.20); g.add_color_stop_rgb(1, 0.45, 0.92, 0.35)
            ctx.set_source(g); ctx.fill()
            ctx.restore()
        ctx.move_to(0, -r * 0.95); ctx.curve_to(r * 0.05, -r * 1.15, r * 0.12, -r * 1.25, r * 0.18, -r * 1.3)
        ctx.set_source_rgb(0.2, 0.6, 0.25); ctx.set_line_width(r * 0.05); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.stroke()

    def face_pos(self, r):
        return 0.0, r * 0.08, r * 0.95
