"""Pluma — a round violet plum with a soft crease and one leaf."""
from __future__ import annotations

import math

from ..style import glossy_fill, highlight, hex2rgb
from .base import Character


class Plum(Character):
    color = hex2rgb("#8b3dff")
    glow_color = hex2rgb("#a66bff")

    def body(self, ctx, r):
        ctx.save(); ctx.scale(1.0, 0.95)
        ctx.arc(0, 0, r, 0, 2 * math.pi)
        ctx.restore()
        glossy_fill(ctx, 0, 0, r, self.color)
        ctx.new_path()
        ctx.move_to(r * 0.1, -r * 0.92)
        ctx.curve_to(r * 0.45, -r * 0.4, r * 0.5, r * 0.3, r * 0.3, r * 0.85)
        ctx.set_source_rgba(0.25, 0.05, 0.45, 0.35); ctx.set_line_width(r * 0.04); ctx.stroke()
        highlight(ctx, -r * 0.42, -r * 0.45, r * 0.3, r * 0.17, -0.6, 0.65)

    def decorate(self, ctx, r):
        ctx.save(); ctx.translate(r * 0.08, -r * 0.92); ctx.rotate(-0.9)
        ctx.move_to(0, 0); ctx.curve_to(r * 0.15, -r * 0.15, r * 0.42, -r * 0.1, r * 0.5, 0)
        ctx.curve_to(r * 0.42, r * 0.12, r * 0.15, r * 0.14, 0, 0)
        ctx.set_source_rgb(0.3, 0.8, 0.35); ctx.fill(); ctx.restore()

    def face_pos(self, r):
        return -r * 0.05, r * 0.08, r * 0.9
