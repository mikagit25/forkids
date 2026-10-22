"""Character: draws itself at (cx, cy) with a size, squash/stretch, tilt and face."""
from __future__ import annotations

import math

import cairo

from .. import face as F


class Character:
    color = (1, 0, 0)
    glow_color = (1, 0.3, 0.3)

    def __init__(self, seed: int = 1):
        self.seed = seed

    def body(self, ctx: cairo.Context, r: float):
        """Draw the body path + fill around (0, 0) with radius r. Override."""
        raise NotImplementedError

    def decorate(self, ctx: cairo.Context, r: float):
        """Leaves, stems, seeds… drawn after the body. Override."""

    def face_pos(self, r):
        return 0.0, r * 0.05, r

    def draw(self, ctx: cairo.Context, cx, cy, r, t=0.0, sx=1.0, sy=1.0, tilt=0.0, look=(0.0, 0.0),
             smile=1.0, happy=False):
        ctx.save()
        ctx.translate(cx, cy + r)           # squash around the bottom: feet stay on the beat line
        ctx.rotate(math.radians(tilt))
        ctx.scale(sx, sy)
        ctx.translate(0, -r)
        self.body(ctx, r)
        self.decorate(ctx, r)
        fx, fy, fs = self.face_pos(r)
        F.face(ctx, fx, fy, fs, t, self.seed, look, smile=smile, happy=happy)
        ctx.restore()
