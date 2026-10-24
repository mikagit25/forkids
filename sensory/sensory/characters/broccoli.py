"""Broc — a bright green broccoli with a fluffy crown and sturdy stalk."""
from __future__ import annotations

import math
import random

from ..style import glossy_fill, highlight, hex2rgb
from .base import Character


class Broccoli(Character):
    color = hex2rgb("#3db84a")
    glow_color = hex2rgb("#72e07a")

    def body(self, ctx, r):
        # Stalk
        ctx.rectangle(-r * 0.22, r * 0.12, r * 0.44, r * 0.82)
        ctx.set_source_rgb(0.28, 0.70, 0.22)
        ctx.fill()
        # Crown: big rounded dome made of overlapping circles
        rnd = random.Random(11)
        base_color = self.color
        for _ in range(18):
            bx = rnd.uniform(-r * 0.62, r * 0.62)
            by = rnd.uniform(-r * 0.88, -r * 0.08)
            br = r * rnd.uniform(0.28, 0.46)
            ctx.arc(bx, by, br, 0, 2 * math.pi)
            shade = rnd.uniform(0.85, 1.05)
            ctx.set_source_rgb(
                min(1.0, base_color[0] * shade),
                min(1.0, base_color[1] * shade),
                min(1.0, base_color[2] * shade),
            )
            ctx.fill()
        # Gloss on top
        highlight(ctx, -r * 0.25, -r * 0.68, r * 0.28, r * 0.12, -0.3, 0.55)

    def face_pos(self, r):
        return 0.0, -r * 0.28, r * 0.70
