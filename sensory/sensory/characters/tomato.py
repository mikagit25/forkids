"""Tommy Tomato — a plump red tomato with a cheerful star-shaped crown."""
from __future__ import annotations

import math

from ..style import glossy_fill, highlight, hex2rgb
from .base import Character


class Tomato(Character):
    color = hex2rgb("#e8281a")
    glow_color = hex2rgb("#ff5544")

    def body(self, ctx, r):
        ctx.arc(0, 0, r * 0.98, 0, 2 * math.pi)
        glossy_fill(ctx, 0, 0, r, self.color)
        # Subtle vertical ridges
        ctx.new_path()
        for angle in (-0.6, 0.6):
            x = r * math.sin(angle) * 0.7
            ctx.move_to(x, -r * 0.7)
            ctx.curve_to(x * 1.1, 0, x * 1.1, r * 0.5, x * 0.7, r * 0.85)
            ctx.set_source_rgba(0.6, 0.08, 0.05, 0.20)
            ctx.set_line_width(r * 0.04)
            ctx.stroke()
        highlight(ctx, -r * 0.38, -r * 0.42, r * 0.30, r * 0.14, -0.5, 0.65)

    def decorate(self, ctx, r):
        # Star-shaped green crown
        ctx.save()
        ctx.translate(0, -r * 0.93)
        ctx.set_source_rgb(0.18, 0.65, 0.20)
        for i in range(5):
            ctx.save()
            ctx.rotate(i * 2 * math.pi / 5 - 0.3)
            ctx.move_to(0, 0)
            ctx.curve_to(r * 0.08, -r * 0.28, r * 0.14, -r * 0.38, 0, -r * 0.46)
            ctx.curve_to(-r * 0.14, -r * 0.38, -r * 0.08, -r * 0.28, 0, 0)
            ctx.fill()
            ctx.restore()
        # Stem
        ctx.move_to(-r * 0.04, 0)
        ctx.line_to(r * 0.04, 0)
        ctx.line_to(r * 0.03, -r * 0.22)
        ctx.line_to(-r * 0.03, -r * 0.22)
        ctx.close_path()
        ctx.set_source_rgb(0.22, 0.55, 0.15)
        ctx.fill()
        ctx.restore()

    def face_pos(self, r):
        return 0.0, r * 0.1, r * 0.90
