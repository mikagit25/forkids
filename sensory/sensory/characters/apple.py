"""Rosy Apple — a classic red-green apple with a dent on top."""
from __future__ import annotations

import cairo

from ..style import glossy_fill, highlight, hex2rgb
from .base import Character


class Apple(Character):
    color = hex2rgb("#4cd137")
    glow_color = hex2rgb("#7dff63")

    def body(self, ctx, r):
        ctx.move_to(0, -r * 0.72)
        ctx.curve_to(r * 0.5, -r * 1.05, r * 1.1, -r * 0.8, r * 1.0, -r * 0.05)
        ctx.curve_to(r * 0.95, r * 0.65, r * 0.55, r * 1.0, r * 0.25, r * 0.98)
        ctx.curve_to(r * 0.12, r * 0.95, -r * 0.12, r * 0.95, -r * 0.25, r * 0.98)
        ctx.curve_to(-r * 0.55, r * 1.0, -r * 0.95, r * 0.65, -r * 1.0, -r * 0.05)
        ctx.curve_to(-r * 1.1, -r * 0.8, -r * 0.5, -r * 1.05, 0, -r * 0.72)
        ctx.close_path()
        glossy_fill(ctx, 0, 0, r, self.color)
        ctx.new_path()
        highlight(ctx, -r * 0.45, -r * 0.45, r * 0.28, r * 0.16, -0.7, 0.6)

    def decorate(self, ctx, r):
        ctx.move_to(0, -r * 0.7); ctx.curve_to(0, -r * 0.9, r * 0.05, -r * 1.05, r * 0.1, -r * 1.15)
        ctx.set_source_rgb(0.45, 0.28, 0.12); ctx.set_line_width(r * 0.07); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.stroke()
        ctx.save(); ctx.translate(r * 0.08, -r * 1.0); ctx.rotate(-0.3)
        ctx.move_to(0, 0); ctx.curve_to(r * 0.15, -r * 0.14, r * 0.4, -r * 0.1, r * 0.48, 0)
        ctx.curve_to(r * 0.4, r * 0.1, r * 0.15, r * 0.13, 0, 0)
        ctx.set_source_rgb(0.2, 0.7, 0.25); ctx.fill(); ctx.restore()

    def face_pos(self, r):
        return 0.0, r * 0.12, r * 0.9
