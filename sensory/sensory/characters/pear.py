"""Pippa Pear — a chubby lime-yellow pear with a curly stem."""
from __future__ import annotations

import cairo

from ..style import glossy_fill, highlight, hex2rgb
from .base import Character


class Pear(Character):
    color = hex2rgb("#c6e82a")
    glow_color = hex2rgb("#d8ff4a")

    def body(self, ctx, r):
        ctx.move_to(0, -r * 1.05)
        ctx.curve_to(r * 0.4, -r * 1.05, r * 0.45, -r * 0.55, r * 0.6, -r * 0.25)
        ctx.curve_to(r * 1.05, r * 0.15, r * 1.05, r * 1.0, 0, r * 1.0)
        ctx.curve_to(-r * 1.05, r * 1.0, -r * 1.05, r * 0.15, -r * 0.6, -r * 0.25)
        ctx.curve_to(-r * 0.45, -r * 0.55, -r * 0.4, -r * 1.05, 0, -r * 1.05)
        ctx.close_path()
        glossy_fill(ctx, 0, r * 0.15, r, self.color)
        ctx.new_path()
        highlight(ctx, -r * 0.32, -r * 0.45, r * 0.18, r * 0.3, 0.25, 0.6)

    def decorate(self, ctx, r):
        ctx.move_to(0, -r * 1.02); ctx.curve_to(-r * 0.05, -r * 1.25, r * 0.15, -r * 1.3, r * 0.1, -r * 1.42)
        ctx.set_source_rgb(0.45, 0.28, 0.12); ctx.set_line_width(r * 0.07); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.stroke()
        ctx.save(); ctx.translate(r * 0.06, -r * 1.22); ctx.rotate(-0.6)
        ctx.move_to(0, 0); ctx.curve_to(r * 0.15, -r * 0.12, r * 0.38, -r * 0.08, r * 0.45, 0)
        ctx.curve_to(r * 0.38, r * 0.1, r * 0.15, r * 0.12, 0, 0)
        ctx.set_source_rgb(0.25, 0.75, 0.3); ctx.fill(); ctx.restore()

    def face_pos(self, r):
        return 0.0, r * 0.35, r * 0.8
