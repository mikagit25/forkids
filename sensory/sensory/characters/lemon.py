"""Lulu Lemon — an oval lemon with pointy ends, lying a little tilted."""
from __future__ import annotations

from ..style import glossy_fill, highlight, hex2rgb
from .base import Character


class Lemon(Character):
    color = hex2rgb("#fff04a")
    glow_color = hex2rgb("#fff47a")

    def body(self, ctx, r):
        ctx.move_to(-r * 1.08, 0)
        ctx.curve_to(-r * 0.95, -r * 0.95, r * 0.95, -r * 0.95, r * 1.08, 0)
        ctx.curve_to(r * 0.95, r * 0.95, -r * 0.95, r * 0.95, -r * 1.08, 0)
        ctx.close_path()
        glossy_fill(ctx, 0, 0, r, self.color)
        ctx.new_path()
        for sx in (-1, 1):
            ctx.arc(sx * r * 1.06, 0, r * 0.06, 0, 6.29); ctx.set_source_rgb(0.85, 0.8, 0.1); ctx.fill()
        highlight(ctx, -r * 0.35, -r * 0.4, r * 0.32, r * 0.13, -0.3, 0.6)

    def face_pos(self, r):
        return 0.0, r * 0.05, r * 0.82
