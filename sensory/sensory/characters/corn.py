"""Corny — a golden ear of corn with a big smile and green leafy husk."""
from __future__ import annotations

import math
import random

from ..style import glossy_fill, highlight, hex2rgb
from .base import Character


class Corn(Character):
    color = hex2rgb("#f7c81e")
    glow_color = hex2rgb("#ffe066")

    def body(self, ctx, r):
        # Rounded cylinder (cob)
        ctx.move_to(-r * 0.52, -r * 0.78)
        ctx.curve_to(-r * 0.62, -r * 0.5, -r * 0.62, r * 0.6, -r * 0.42, r * 0.88)
        ctx.curve_to(-r * 0.18, r * 1.0, r * 0.18, r * 1.0, r * 0.42, r * 0.88)
        ctx.curve_to(r * 0.62, r * 0.6, r * 0.62, -r * 0.5, r * 0.52, -r * 0.78)
        ctx.close_path()
        glossy_fill(ctx, 0, 0, r, self.color)
        # Kernel grid
        rnd = random.Random(7)
        ctx.new_path()
        for row in range(7):
            for col in range(4):
                kx = (col - 1.5) * r * 0.22 + rnd.uniform(-0.015, 0.015) * r
                ky = (row - 3) * r * 0.24 + rnd.uniform(-0.015, 0.015) * r
                ctx.move_to(kx + r * 0.08, ky)
                ctx.arc(kx, ky, r * 0.08, 0, 2 * math.pi)
        ctx.set_source_rgba(0.88, 0.7, 0.05, 0.35)
        ctx.fill()
        highlight(ctx, -r * 0.28, -r * 0.55, r * 0.22, r * 0.10, -0.4, 0.65)

    def decorate(self, ctx, r):
        # Green husk leaves on sides
        for sx in (-1, 1):
            ctx.save()
            ctx.translate(sx * r * 0.44, -r * 0.3)
            ctx.rotate(sx * 0.55)
            ctx.move_to(0, 0)
            ctx.curve_to(sx * r * 0.5, -r * 0.3, sx * r * 0.7, -r * 0.7, sx * r * 0.45, -r * 1.0)
            ctx.curve_to(sx * r * 0.2, -r * 0.8, sx * r * 0.15, -r * 0.4, 0, 0)
            ctx.set_source_rgb(0.2, 0.68, 0.25)
            ctx.fill()
            ctx.restore()

    def face_pos(self, r):
        return 0.0, 0.0, r * 0.75
