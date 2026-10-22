"""Render a still: characters on black with glow → PNG (step 1 of the brief)."""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

from .characters import CHARACTERS
from .style import add_glow, flatten, over, surface, to_array


def render_still(cast: list[tuple[str, float, float, float]], w=1920, h=1080, t=0.0):
    """cast = [(name, cx, cy, r), ...] → RGB uint8 array."""
    import numpy as np
    canvas = np.zeros((h, w, 4), np.float32)
    for i, (name, cx, cy, r) in enumerate(cast):
        ch = CHARACTERS[name](seed=i + 1)
        s, ctx = surface(w, h)
        ch.draw(ctx, cx, cy, r, t)
        layer = to_array(s)
        canvas = over(canvas, add_glow(layer, ch.glow_color, radius=r * 0.12, strength=0.6))
        canvas = over(canvas, layer)
    return flatten(canvas)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    Image.fromarray(render_still([("berry", 960, 520, 300)])).save(out / "step1_berry.png")
    Image.fromarray(render_still([("pear", 480, 560, 220), ("berry", 960, 520, 250), ("plum", 1440, 560, 220)],
                                 t=0.0)).save(out / "step1_group.png")
    print("ok")


if __name__ == "__main__":
    main()
