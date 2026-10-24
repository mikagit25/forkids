"""Patch — a round orange pumpkin with deep ridges and a curly stem."""
from __future__ import annotations

import math

from ..style import glossy_fill, highlight, hex2rgb
from .base import Character


class Pumpkin(Character):
    color = hex2rgb("#f26a1b")
    glow_color = hex2rgb("#ffaa55")

    def body(self, ctx, r):
        # Five-lobe pumpkin: stack of arcs
        lobes = 5
        for i in range(lobes):
            angle = (i / lobes) * 2 * math.pi - math.pi / 2
            cx = math.cos(angle) * r * 0.28
            cy = math.sin(angle) * r * 0.22
            ctx.arc(cx, cy, r * 0.68, 0, 2 * math.pi)
        glossy_fill(ctx, 0, 0, r, self.color)
        # Deep ridge lines between lobes
        ctx.new_path()
        for i in range(lobes):
            angle = (i / lobes) * 2 * math.pi - math.pi / 2 + math.pi / lobes
            ctx.move_to(0, 0)
            ctx.line_to(math.cos(angle) * r * 0.96, math.sin(angle) * r * 0.96)
            ctx.set_source_rgba(0.5, 0.18, 0.0, 0.22)
            ctx.set_line_width(r * 0.05)
            ctx.stroke()
        highlight(ctx, -r * 0.32, -r * 0.44, r * 0.28, r * 0.12, -0.4, 0.60)

    def decorate(self, ctx, r):
        # Stem
        ctx.save()
        ctx.translate(0, -r * 0.88)
        ctx.move_to(-r * 0.06, 0)
        ctx.curve_to(-r * 0.08, -r * 0.22, r * 0.18, -r * 0.28, r * 0.16, -r * 0.44)
        ctx.curve_to(r * 0.12, -r * 0.28, r * 0.04, -r * 0.22, r * 0.06, 0)
        ctx.close_path()
        ctx.set_source_rgb(0.32, 0.52, 0.15)
        ctx.fill()
        # Curly tendril
        ctx.move_to(r * 0.12, -r * 0.22)
        ctx.curve_to(r * 0.38, -r * 0.42, r * 0.52, -r * 0.18, r * 0.38, -r * 0.04)
        ctx.set_source_rgb(0.28, 0.60, 0.18)
        ctx.set_line_width(r * 0.035)
        ctx.stroke()
        ctx.restore()

    def face_pos(self, r):
        return 0.0, r * 0.06, r * 0.82
