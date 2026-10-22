"""Bobo Banana — a happy curved banana, standing up, with a brown tip."""
from __future__ import annotations

import cairo

from ..style import glossy_fill, highlight, hex2rgb
from .base import Character


class Banana(Character):
    color = hex2rgb("#ffd60a")
    glow_color = hex2rgb("#ffe45c")

    def path(self, ctx, r):
        ctx.move_to(-r * 0.15, -r * 1.05)
        ctx.curve_to(r * 0.55, -r * 0.7, r * 0.75, r * 0.3, r * 0.25, r * 1.0)
        ctx.curve_to(r * 0.05, r * 1.08, -r * 0.35, r * 1.05, -r * 0.55, r * 0.85)
        ctx.curve_to(-r * 0.25, r * 0.6, -r * 0.05, r * 0.1, -r * 0.3, -r * 0.95)
        ctx.close_path()

    def body(self, ctx, r):
        self.path(ctx, r)
        glossy_fill(ctx, r * 0.1, 0, r * 0.9, self.color)
        ctx.new_path()
        ctx.move_to(-r * 0.1, -r * 0.85); ctx.curve_to(r * 0.4, -r * 0.45, r * 0.5, r * 0.35, r * 0.15, r * 0.95)
        ctx.set_source_rgba(0.75, 0.55, 0.0, 0.35); ctx.set_line_width(r * 0.035); ctx.stroke()
        highlight(ctx, r * 0.05, -r * 0.55, r * 0.1, r * 0.3, -0.5, 0.55)

    def decorate(self, ctx, r):
        ctx.move_to(-r * 0.3, -r * 0.95); ctx.line_to(-r * 0.2, -r * 1.25)
        ctx.set_source_rgb(0.45, 0.32, 0.1); ctx.set_line_width(r * 0.12); ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.stroke()

    def face_pos(self, r):
        return r * 0.12, r * 0.1, r * 0.62
