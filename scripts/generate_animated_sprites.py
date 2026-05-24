#!/usr/bin/env python3
"""
Generate animated cartoon sprite frame sequences.
Each character = 60 frames (2s loop at 30fps): idle bob + blink.
Output: assets/sprites/animated/<name>/frame_000.png ... frame_059.png
"""

import math
from pathlib import Path
from PIL import Image, ImageDraw

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "assets" / "sprites" / "animated"

SIZE = 300       # canvas per frame
N_FRAMES = 60    # 2-second cycle at 30fps
BLINK_START = 45
BLINK_PEAK  = 50
BLINK_END   = 55


# ─── drawing helpers ──────────────────────────────────────────────────────────

def _circle(draw, cx, cy, r, fill, outline=None, lw=0):
    draw.ellipse([int(cx-r), int(cy-r), int(cx+r), int(cy+r)], fill=fill,
                 outline=outline, width=int(lw))

def _eyes(draw, cx, cy, radius, blink_t, eye_color=(255,255,255),
          pupil_color=(40,20,10), iris_color=(80,160,220)):
    """Draw a pair of eyes. blink_t 0=open, 1=fully closed."""
    for ex in [cx - radius*0.28, cx + radius*0.28]:
        ey = cy - radius*0.05
        er = radius * 0.17
        # white sclera
        _circle(draw, ex, ey, er, eye_color)
        # iris
        _circle(draw, ex, ey + er*0.08, er*0.65, iris_color)
        # pupil
        _circle(draw, ex, ey + er*0.10, er*0.38, pupil_color)
        # highlight
        _circle(draw, ex - er*0.25, ey - er*0.18, er*0.18, (255,255,255))
        # eyelid (blink)
        if blink_t > 0:
            lid_h = er * 2.1 * blink_t
            draw.rectangle([int(ex-er-1), int(ey-er-1), int(ex+er+1), int(ey-er+lid_h)],
                            fill=(0,0,0,0))
            # solid color lid matching body
            _circle(draw, ex, ey, er * (0.05 + 0.95*blink_t), (0,0,0,0))


def _smile(draw, cx, cy, radius, open_=False):
    w = radius * 0.36
    h = radius * 0.14
    y = cy + radius * 0.30
    bbox = [int(cx-w), int(y-h), int(cx+w), int(y+h)]
    draw.arc(bbox, 10, 170, fill=(180,60,60), width=max(2, int(radius)//20))
    if open_:
        # tongue
        _circle(draw, cx, y+h*0.2, h*0.55, (220,80,100))


def _cheeks(draw, cx, cy, radius):
    for bx in [cx - radius*0.38, cx + radius*0.38]:
        _circle(draw, bx, cy + radius*0.22, radius*0.12,
                (255, 160, 160, 100))


def _outline_circle(draw, cx, cy, r, color, lw=4):
    draw.ellipse([int(cx-r-lw), int(cy-r-lw), int(cx+r+lw), int(cy+r+lw)],
                 outline=color, width=int(lw), fill=None)


# ─── character factories ──────────────────────────────────────────────────────

def _base_frame(size, body_color, dark_color, frame_i):
    """Blank canvas with background transparent and positioned body."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img, "RGBA")

    # idle bob: ±4px over 60 frames
    bob = math.sin(frame_i / N_FRAMES * math.tau) * 4
    cx = size / 2
    cy = size / 2 + bob
    r  = size * 0.38

    # shadow
    draw.ellipse([int(cx - r*0.7), int(cy + r*0.78), int(cx + r*0.7), int(cy + r*1.0)],
                 fill=(0, 0, 0, 40))
    # body
    _circle(draw, cx, cy, r, body_color)
    _outline_circle(draw, cx, cy, r, dark_color, lw=max(3, size//60))

    return img, draw, cx, cy, r


def _blink_t(frame_i):
    if frame_i < BLINK_START:
        return 0.0
    elif frame_i < BLINK_PEAK:
        return (frame_i - BLINK_START) / (BLINK_PEAK - BLINK_START)
    elif frame_i < BLINK_END:
        return 1.0 - (frame_i - BLINK_PEAK) / (BLINK_END - BLINK_PEAK)
    return 0.0


def make_cat(size=SIZE):
    frames = []
    body_c = (255, 160, 80)
    dark_c = (200, 110, 40)
    for i in range(N_FRAMES):
        img, draw, cx, cy, r = _base_frame(size, body_c, dark_c, i)
        # ears
        for ex, ew in [(cx - r*0.52, -1), (cx + r*0.52, 1)]:
            pts = [(ex, cy - r*0.75),
                   (ex - ew*r*0.22, cy - r*1.22),
                   (ex + ew*r*0.22, cy - r*1.22)]
            draw.polygon(pts, fill=body_c, outline=dark_c)
            # inner ear
            inner = [(p[0]*0.6+cx*0.4, p[1]*0.7+cy*0.3) for p in pts]
            draw.polygon(inner, fill=(255, 200, 200))
        # face
        _eyes(draw, cx, cy, r, _blink_t(i))
        # nose
        _circle(draw, cx, cy + r*0.18, r*0.065, (220, 80, 120))
        # whiskers
        for wx, wy, ang in [(-1, 0.05, -10), (-1, 0.13, -5),
                             (1, 0.05, 10),  (1, 0.13, 5)]:
            x0 = cx + wx * r*0.08
            x1 = cx + wx * r*0.6
            y0 = cy + r*wy
            y1 = cy + r*(wy + wx*math.tan(math.radians(ang))*0.3)
            draw.line([(x0,y0),(x1,y1)], fill=(100,60,20,180), width=2)
        _smile(draw, cx, cy, r)
        _cheeks(draw, cx, cy, r)
        frames.append(img)
    return frames


def make_rabbit(size=SIZE):
    frames = []
    body_c = (230, 230, 250)
    dark_c = (180, 180, 210)
    for i in range(N_FRAMES):
        img, draw, cx, cy, r = _base_frame(size, body_c, dark_c, i)
        # long ears
        for ex, tilt in [(cx - r*0.3, -0.12), (cx + r*0.3, 0.12)]:
            ey_top = cy - r*1.5
            ear_w  = r*0.18
            pts = [(ex - ear_w + tilt*r, cy - r*0.7),
                   (ex - ear_w*0.4 + tilt*r, ey_top),
                   (ex + ear_w*0.4 + tilt*r, ey_top),
                   (ex + ear_w + tilt*r, cy - r*0.7)]
            draw.polygon(pts, fill=body_c, outline=dark_c)
            inner = [(p[0]*0.8+cx*0.2, p[1]*0.85+cy*0.15) for p in pts]
            draw.polygon(inner, fill=(255, 180, 200))
        _eyes(draw, cx, cy, r, _blink_t(i),
              iris_color=(100, 80, 200))
        _circle(draw, cx, cy + r*0.18, r*0.07, (255, 140, 160))
        _smile(draw, cx, cy, r)
        _cheeks(draw, cx, cy, r)
        frames.append(img)
    return frames


def make_bear(size=SIZE):
    frames = []
    body_c = (160, 110, 70)
    dark_c = (110, 70, 35)
    snout_c = (210, 170, 130)
    for i in range(N_FRAMES):
        img, draw, cx, cy, r = _base_frame(size, body_c, dark_c, i)
        # ears
        for ex in [cx - r*0.62, cx + r*0.62]:
            _circle(draw, ex, cy - r*0.68, r*0.22, body_c)
            _outline_circle(draw, ex, cy - r*0.68, r*0.22, dark_c, 3)
            _circle(draw, ex, cy - r*0.68, r*0.12, snout_c)
        # snout
        _circle(draw, cx, cy + r*0.18, r*0.32, snout_c)
        _circle(draw, cx, cy + r*0.12, r*0.09, (80, 40, 20))
        _eyes(draw, cx, cy, r, _blink_t(i), iris_color=(80, 130, 60))
        _smile(draw, cx, cy, r)
        _cheeks(draw, cx, cy, r)
        frames.append(img)
    return frames


def make_duck(size=SIZE):
    frames = []
    body_c = (255, 230, 80)
    dark_c = (200, 165, 30)
    for i in range(N_FRAMES):
        img, draw, cx, cy, r = _base_frame(size, body_c, dark_c, i)
        # bill
        bx, by = cx, cy + r*0.25
        pts = [(bx - r*0.22, by - r*0.04),
               (bx + r*0.22, by - r*0.04),
               (bx + r*0.18, by + r*0.14),
               (bx - r*0.18, by + r*0.14)]
        draw.polygon(pts, fill=(255, 160, 30), outline=(200, 110, 10))
        _eyes(draw, cx, cy, r, _blink_t(i), iris_color=(60, 140, 200))
        _cheeks(draw, cx, cy, r)
        frames.append(img)
    return frames


def make_elephant(size=SIZE):
    frames = []
    body_c = (170, 170, 200)
    dark_c = (120, 120, 155)
    for i in range(N_FRAMES):
        img, draw, cx, cy, r = _base_frame(size, body_c, dark_c, i)
        # big ears
        for ex, sign in [(cx - r*0.82, -1), (cx + r*0.82, 1)]:
            draw.ellipse([int(ex - r*0.38), int(cy - r*0.45),
                          int(ex + r*0.38), int(cy + r*0.45)],
                         fill=(200, 160, 160), outline=dark_c, width=3)
        # trunk (swings with bob)
        bob2 = math.sin(i / N_FRAMES * math.tau * 2) * r * 0.04
        trunk_pts = [(cx - r*0.1, cy + r*0.25),
                     (cx + r*0.1, cy + r*0.25),
                     (cx + r*0.12 + bob2, cy + r*0.72),
                     (cx - r*0.05 + bob2, cy + r*0.72)]
        draw.polygon(trunk_pts, fill=body_c, outline=dark_c)
        _circle(draw, cx + bob2*0.8, cy + r*0.74, r*0.08, body_c, dark_c, 3)
        _eyes(draw, cx, cy, r, _blink_t(i), iris_color=(80, 140, 100))
        _smile(draw, cx, cy, r)
        _cheeks(draw, cx, cy, r)
        frames.append(img)
    return frames


def make_frog(size=SIZE):
    frames = []
    body_c = (80, 195, 80)
    dark_c = (40, 140, 40)
    for i in range(N_FRAMES):
        img, draw, cx, cy, r = _base_frame(size, body_c, dark_c, i)
        # eyes on top of head
        for ex in [cx - r*0.28, cx + r*0.28]:
            ey = cy - r*0.72
            _circle(draw, ex, ey, r*0.22, (255,255,255))
            _outline_circle(draw, ex, ey, r*0.22, dark_c, 3)
            # iris / pupil
            if _blink_t(i) < 0.5:
                _circle(draw, ex, ey, r*0.14, (60, 180, 60))
                _circle(draw, ex, ey+r*0.02, r*0.08, (20,20,20))
                _circle(draw, ex-r*0.06, ey-r*0.06, r*0.04, (255,255,255))
            else:
                draw.ellipse([int(ex-r*0.14), int(ey-r*0.03),
                               int(ex+r*0.14), int(ey+r*0.03)],
                              fill=(20,20,20))
        # wide smile
        sm_w = r*0.42
        draw.arc([int(cx-sm_w), int(cy+r*0.08), int(cx+sm_w), int(cy+r*0.42)],
                 5, 175, fill=(30,100,30), width=max(2, size//50))  # type: ignore
        _cheeks(draw, cx, cy, r)
        frames.append(img)
    return frames


def make_panda(size=SIZE):
    frames = []
    body_c = (250, 250, 250)
    dark_c = (180, 180, 180)
    black  = (30, 30, 30)
    for i in range(N_FRAMES):
        img, draw, cx, cy, r = _base_frame(size, body_c, dark_c, i)
        # ears
        for ex in [cx - r*0.62, cx + r*0.62]:
            _circle(draw, ex, cy - r*0.65, r*0.22, black)
        # eye patches
        for ex in [cx - r*0.28, cx + r*0.28]:
            _circle(draw, ex, cy - r*0.05, r*0.24, black)
        _eyes(draw, cx, cy, r, _blink_t(i),
              eye_color=(245,245,245), iris_color=(80,80,200))
        # nose
        _circle(draw, cx, cy + r*0.19, r*0.07, black)
        _smile(draw, cx, cy, r)
        _cheeks(draw, cx, cy, r)
        frames.append(img)
    return frames


def make_lion(size=SIZE):
    frames = []
    body_c = (235, 185, 80)
    dark_c = (190, 135, 40)
    mane_c = (180, 100, 30)
    for i in range(N_FRAMES):
        img, draw, cx, cy, r = _base_frame(size, body_c, dark_c, i)
        # mane (drawn before body overwrites)
        img2, draw2 = img, draw
        _circle(draw2, cx, cy, r * 1.22, mane_c)
        # body on top
        _circle(draw2, cx, cy, r, body_c)
        _outline_circle(draw2, cx, cy, r, dark_c, max(3, SIZE//60))
        # ears
        for ex in [cx - r*0.55, cx + r*0.55]:
            _circle(draw2, ex, cy - r*0.6, r*0.18, body_c)
            _circle(draw2, ex, cy - r*0.6, r*0.09, (220, 160, 140))
        _eyes(draw2, cx, cy, r, _blink_t(i), iris_color=(140, 100, 30))
        _circle(draw2, cx, cy + r*0.18, r*0.09, (160, 80, 40))
        _smile(draw2, cx, cy, r, open_=True)
        _cheeks(draw2, cx, cy, r)
        frames.append(img)
    return frames


def make_monkey(size=SIZE):
    frames = []
    body_c = (160, 110, 60)
    dark_c = (110, 70, 25)
    face_c = (230, 185, 140)
    for i in range(N_FRAMES):
        img, draw, cx, cy, r = _base_frame(size, body_c, dark_c, i)
        # ears
        for ex in [cx - r*0.8, cx + r*0.8]:
            _circle(draw, ex, cy, r*0.25, body_c, dark_c, 3)
            _circle(draw, ex, cy, r*0.14, face_c)
        # face disk
        _circle(draw, cx, cy + r*0.08, r*0.62, face_c)
        _eyes(draw, cx, cy, r, _blink_t(i), iris_color=(80, 60, 200))
        _circle(draw, cx, cy + r*0.24, r*0.13, face_c)
        draw.ellipse([int(cx-r*0.07), int(cy+r*0.20), int(cx+r*0.07), int(cy+r*0.28)],
                     fill=(100, 50, 20))
        _smile(draw, cx, cy, r)
        _cheeks(draw, cx, cy, r)
        frames.append(img)
    return frames


def make_chick(size=SIZE):
    frames = []
    body_c = (255, 225, 60)
    dark_c = (200, 165, 20)
    for i in range(N_FRAMES):
        img, draw, cx, cy, r = _base_frame(size, body_c, dark_c, i)
        # wing flap syncs with bob
        wing_angle = math.sin(i / N_FRAMES * math.tau) * 15
        for sign in [-1, 1]:
            wx = cx + sign * r * 0.72
            wy = cy + r * 0.05
            angle_rad = math.radians(wing_angle * sign)
            tip_x = wx + sign * r * 0.28 * math.cos(angle_rad)
            tip_y = wy - r * 0.22 * abs(math.sin(angle_rad)) - r*0.10
            pts = [(wx - sign*r*0.05, wy - r*0.15),
                   (wx + sign*r*0.05, wy + r*0.15),
                   (tip_x, tip_y)]
            draw.polygon(pts, fill=body_c, outline=dark_c)
        # beak
        pts = [(cx - r*0.1, cy + r*0.18),
               (cx + r*0.1, cy + r*0.18),
               (cx, cy + r*0.34)]
        draw.polygon(pts, fill=(255, 140, 30), outline=(200, 100, 10))
        _eyes(draw, cx, cy, r, _blink_t(i), iris_color=(60, 60, 60))
        _cheeks(draw, cx, cy, r)
        frames.append(img)
    return frames


# ─── generate all + save ──────────────────────────────────────────────────────

CHARACTERS = {
    "cat":      make_cat,
    "rabbit":   make_rabbit,
    "bear":     make_bear,
    "duck":     make_duck,
    "elephant": make_elephant,
    "frog":     make_frog,
    "panda":    make_panda,
    "lion":     make_lion,
    "monkey":   make_monkey,
    "chick":    make_chick,
}


def generate_all(size=SIZE, overwrite=False):
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, factory in CHARACTERS.items():
        out = OUT_DIR / name
        if not overwrite and out.exists() and len(list(out.glob("*.png"))) >= N_FRAMES:
            print(f"  skip  {name} (already exists)")
            continue
        out.mkdir(exist_ok=True)
        print(f"  gen   {name} ({N_FRAMES} frames)...", end="", flush=True)
        frames = factory(size)
        for fi, frame in enumerate(frames):
            frame.save(out / f"frame_{fi:03d}.png")
        print(" ok")
    print(f"\n✓ {len(CHARACTERS)} characters → {OUT_DIR}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", type=int, default=SIZE)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--char", default=None, help="generate only this character")
    args = parser.parse_args()

    if args.char:
        factory = CHARACTERS.get(args.char)
        if not factory:
            print(f"Unknown character: {args.char}")
        else:
            out = OUT_DIR / args.char
            out.mkdir(parents=True, exist_ok=True)
            frames = factory(args.size)
            for fi, frame in enumerate(frames):
                frame.save(out / f"frame_{fi:03d}.png")
            print(f"✓ {args.char}: {len(frames)} frames → {out}")
    else:
        generate_all(args.size, args.overwrite)
