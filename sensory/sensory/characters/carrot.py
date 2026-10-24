"""Coco Carrot — a plump orange carrot with a feathery green top."""
from __future__ import annotations

import math

from ..style import glossy_fill, highlight, hex2rgb
from .base import Character


class Carrot(Character):
    color = hex2rgb("#ff7a1a")
    glow_color = hex2rgb("#ffaa55")

    def body(self, ctx, r):
        # Tapered carrot body: wide top, pointy bottom
        ctx.move_to(-r * 0.72, -r * 0.7)
        ctx.curve_to(-r * 0.78, r * 0.1, -r * 0.18, r * 0.9, 0, r * 1.05)
        ctx.curve_to(r * 0.18, r * 0.9, r * 0.78, r * 0.1, r * 0.72, -r * 0.7)
        ctx.close_path()
        glossy_fill(ctx, 0, 0, r, self.color)
        # Ridges
        ctx.new_path()
        for y_frac in (0.0, 0.3, 0.6):
            w = r * (0.70 - y_frac * 0.55)
            ctx.move_to(-w, r * y_frac)
            ctx.line_to(w, r * y_frac)
            ctx.set_source_rgba(0.75, 0.3, 0.0, 0.18)
            ctx.set_line_width(r * 0.035)
            ctx.stroke()
        highlight(ctx, -r * 0.3, -r * 0.5, r * 0.25, r * 0.12, -0.3, 0.6)

    def decorate(self, ctx, r):
        # Green feathery leaves
        for angle, length in ((-0.5, 0.7), (0.1, 0.85), (0.6, 0.7), (-0.9, 0.55)):
            ctx.save()
            ctx.translate(0, -r * 0.68)
            ctx.rotate(angle)
            ctx.move_to(0, 0)
            ctx.curve_to(r * 0.12, -r * length * 0.5, r * 0.08, -r * length * 0.9, 0, -r * length)
            ctx.curve_to(-r * 0.08, -r * length * 0.9, -r * 0.12, -r * length * 0.5, 0, 0)
            ctx.set_source_rgb(0.2, 0.72, 0.22)
            ctx.fill()
            ctx.restore()

    def face_pos(self, r):
        return 0.0, -r * 0.1, r * 0.72
