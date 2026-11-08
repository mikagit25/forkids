"""PngCharacter — renders an existing 3D PNG sprite as a sensory character.

The sprite already has a drawn face, so the animated face overlay is skipped.
Motion (bounce, tilt, squash) still works through the base draw() transform stack.
"""
from __future__ import annotations

import math
from pathlib import Path

import cairo
import numpy as np
from PIL import Image

from .base import Character
from ..style import hex2rgb


class PngCharacter(Character):
    """Base for characters drawn from a pre-made PNG sprite."""
    png_path: str = ""
    color = hex2rgb("#ffffff")
    glow_color = hex2rgb("#ffffff")

    def __init__(self, seed: int = 1):
        super().__init__(seed)
        self._surface: cairo.ImageSurface | None = None

    def _load(self):
        if self._surface is not None:
            return
        img = Image.open(self.png_path).convert("RGBA")
        arr = np.array(img, dtype=np.uint8)
        # Cairo ARGB32 (little-endian: B G R A in memory)
        argb = np.empty_like(arr)
        a = arr[:, :, 3].astype(np.float32) / 255.0
        argb[:, :, 0] = (arr[:, :, 2] * a).astype(np.uint8)   # B premult
        argb[:, :, 1] = (arr[:, :, 1] * a).astype(np.uint8)   # G premult
        argb[:, :, 2] = (arr[:, :, 0] * a).astype(np.uint8)   # R premult
        argb[:, :, 3] = arr[:, :, 3]                           # A
        h, w = arr.shape[:2]
        buf = bytearray(argb.tobytes())
        self._surface = cairo.ImageSurface.create_for_data(
            buf, cairo.FORMAT_ARGB32, w, h, w * 4
        )
        self._surf_w = w
        self._surf_h = h

    def body(self, ctx: cairo.Context, r: float):
        self._load()
        if self._surface is None:
            return
        iw, ih = self._surf_w, self._surf_h
        scale = 2 * r / max(iw, ih)
        ctx.save()
        ctx.translate(-iw * scale / 2, -ih * scale / 2 - r * 0.5)
        ctx.scale(scale, scale)
        ctx.set_source_surface(self._surface, 0, 0)
        ctx.paint()
        ctx.restore()

    def face_pos(self, r):
        # Push face far off-screen — PNG sprites have their own drawn face
        return 0.0, -r * 999, 0.0

    def draw(self, ctx, cx, cy, r, t=0.0, sx=1.0, sy=1.0, tilt=0.0, look=(0.0, 0.0),
             smile=1.0, happy=False, sleepy=False):
        """Override: skip face overlay entirely for PNG sprites."""
        ctx.save()
        ctx.translate(cx, cy + r)
        ctx.rotate(math.radians(tilt))
        ctx.scale(sx, sy)
        ctx.translate(0, -r)
        self.body(ctx, r)
        self.decorate(ctx, r)
        ctx.restore()


# ---------------------------------------------------------------------------
# Animal characters — one class per sprite
# ---------------------------------------------------------------------------

_SPRITES = Path(__file__).resolve().parents[3] / "assets" / "sprites_new" / "animals"


def _make(name: str, color: str, glow: str):
    return type(name.capitalize(), (PngCharacter,), {
        "png_path": str(_SPRITES / f"{name}_3d.png"),
        "color":      hex2rgb(color),
        "glow_color": hex2rgb(glow),
    })


Bear      = _make("bear",       "#8B5E3C", "#D4956A")
Cat       = _make("cat",        "#F4A460", "#FFD580")
Dog       = _make("dog",        "#C8A87A", "#EDD9A3")
Elephant  = _make("elephant",   "#9E9EA0", "#C8C8D0")
Fox       = _make("fox",        "#D2691E", "#FF8C42")
Frog      = _make("frog",       "#4CAF50", "#8BC34A")
Koala     = _make("koala",      "#9E9690", "#C8C0BC")
Lion      = _make("lion",       "#DAA520", "#FFD700")
Monkey    = _make("monkey",     "#8B4513", "#CD853F")
Owl       = _make("owl",        "#8B7355", "#D2B48C")
Panda     = _make("panda",      "#E8E8E8", "#FFFFFF")
Penguin   = _make("penguin",    "#2C3E50", "#5D6D7E")
Rabbit    = _make("rabbit",     "#F5F5F5", "#FFDEE9")
Tiger     = _make("tiger",      "#FF8C00", "#FFB347")

# Ocean characters (from objects/ sprites)
_OBJ = Path(__file__).resolve().parents[3] / "assets" / "sprites_new" / "objects"


def _make_obj(name: str, file: str, color: str, glow: str):
    return type(name, (PngCharacter,), {
        "png_path": str(_OBJ / file),
        "color":      hex2rgb(color),
        "glow_color": hex2rgb(glow),
    })


Octopus  = _make_obj("Octopus",  "octopus_3d.png",    "#9B59B6", "#D7BDE2")
Butterfly = _make_obj("Butterfly", "butterfly_3d.png", "#3498DB", "#AED6F1")
BlueWhale = _make("blue_whale", "#1A5276", "#2E86C1")  # from animals/
