"""Bluey Berry — a small, round, deep-blue berry with a star-shaped crown."""
from __future__ import annotations

import math

from ..style import glossy_fill, highlight, hex2rgb
from .base import Character


class Blueberry(Character):
    color = hex2rgb("#3a6bff")
    glow_color = hex2rgb("#6b8fff")

    def body(self, ctx, r):
        ctx.arc(0, 0, r, 0, 2 * math.pi)
        glossy_fill(ctx, 0, 0, r, self.color)
        ctx.new_path()
        highlight(ctx, -r * 0.4, -r * 0.45, r * 0.3, r * 0.16, -0.6, 0.6)

    def decorate(self, ctx, r):
        ctx.save(); ctx.translate(0, -r * 0.88)
        for k in range(5):
            a = k * 2 * math.pi / 5 - math.pi / 2
            ctx.move_to(0, 0); ctx.line_to(r * 0.16 * math.cos(a - 0.3), r * 0.1 * math.sin(a - 0.3))
            ctx.line_to(r * 0.22 * math.cos(a), r * 0.14 * math.sin(a))
            ctx.line_to(r * 0.16 * math.cos(a + 0.3), r * 0.1 * math.sin(a + 0.3)); ctx.close_path()
        ctx.set_source_rgb(0.15, 0.25, 0.6); ctx.fill(); ctx.restore()

    def face_pos(self, r):
        return 0.0, r * 0.08, r * 0.92
