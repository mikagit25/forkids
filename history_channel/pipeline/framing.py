"""Framing check BEFORE the long render: how every photo will be cropped and moved.

    python run.py episodes/<ep> framing     -> episodes/<ep>/build/framing/sheet_NN.jpg

One tile per photo shot: the whole picture as it sits on the 16:9 canvas, a 10 % grid with labels
(the same fractions used by `frame`, `pan`, `detail` in episode.yaml), and the visible area at the
start (green) and at the end (red) of the shot. Read every sheet; whatever is outside the boxes is
never seen, whatever is inside must be worth seeing (no rafters, no headless bodies, no side tables).

Framing keys for an image in episode.yaml (all optional, fractions of the canvas 0..1):
    frame: [x, y]          point of interest; the camera drifts toward it (default centre)
    zoom: in | out | none  or [z0, z1]   (default: gentle in or out, max 1.10)
    pan: [[x0, y0], [x1, y1]]           explicit camera path (centre of view)
    detail: [x, y, zoom]   one extra close-up shot right after the wide one (or a list of them);
                           only for something meaningful: a face, a sign, a caption.
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw

from .render import Renderer, build_timeline, check_coverage, font, motion

TW, TH = 576, 324
COLS = 3


def _ts(t):
    return f"{int(t) // 60}:{int(t) % 60:02d}"


def framing_sheets(ep_dir: Path, episode: dict):
    manifest = json.loads((ep_dir / "manifest.json").read_text())
    timings = json.loads((ep_dir / "audio" / "timings.json").read_text())
    shots, marks, _, total = build_timeline(episode, manifest, timings)
    check_coverage(allow_short=True)

    scene_at = lambda t: next((sid for a, sid in reversed(marks) if a <= t + 0.01), marks[0][1])
    CW, CH = 1920, 1080
    R = Renderer(ep_dir, 960, 540, CW, CH, parallax=False)
    out = ep_dir / "build" / "framing"
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("sheet_*.jpg"):
        old.unlink()
    f1, f2 = font("SourceSans3.ttf", 18, 700), font("SourceSans3.ttf", 15, 500)

    tiles, seen = [], {}
    for sh in shots:
        if sh.kind != "photo":
            continue
        R.prepare(sh)
        img = cv2.cvtColor(cv2.resize(sh.canvas, (TW, TH), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB)
        im = Image.fromarray(img)
        d = ImageDraw.Draw(im, "RGBA")
        for i in range(1, 10):   # grid in canvas fractions
            x, y = TW * i / 10, TH * i / 10
            d.line([(x, 0), (x, TH)], fill=(255, 255, 255, 50))
            d.line([(0, y), (TW, y)], fill=(255, 255, 255, 50))
            d.text((x + 2, 2), f".{i}", font=f2, fill=(255, 255, 0, 200))
            d.text((2, y + 1), f".{i}", font=f2, fill=(255, 255, 0, 200))
        for p, col in ((0.0, (60, 230, 90, 255)), (1.0, (240, 60, 60, 255))):
            z, cx, cy, _ = motion(sh, p, CW, CH)
            w, h = CW / z, CH / z
            box = [(cx - w / 2) / CW * TW, (cy - h / 2) / CH * TH, (cx + w / 2) / CW * TW - 1, (cy + h / 2) / CH * TH - 1]
            d.rectangle(box, outline=col, width=3)
        sid = scene_at(sh.start)
        key = sh.item["id"]
        seen[key] = seen.get(key, 0) + 1
        tags = []
        if sh.detail:
            tags.append(f"DETAIL {sh.focus}")
        if sh.colorize:
            tags.append("COLOR")
        if seen[key] > 1:
            tags.append(f"REPEAT x{seen[key]}")
        if sh.item.get("rotate"):
            tags.append(f"rot {sh.item['rotate']}")
        tiles.append((im, f"{_ts(sh.start)}-{_ts(sh.end)}  {sid}", f"{key}  {' · '.join(tags)}",
                      bool(sh.end - sh.start > 10.5 or seen[key] > 1 and not sh.detail)))
        sh.canvas = sh.depth = sh.color = None

    rows_per = 5
    per = COLS * rows_per
    for pi in range(0, len(tiles), per):
        chunk = tiles[pi:pi + per]
        rows = (len(chunk) + COLS - 1) // COLS
        sheet = Image.new("RGB", (COLS * (TW + 10) + 10, rows * (TH + 56) + 10), (24, 24, 24))
        d = ImageDraw.Draw(sheet)
        for k, (im, l1, l2, bad) in enumerate(chunk):
            x, y = 10 + (k % COLS) * (TW + 10), 10 + (k // COLS) * (TH + 56)
            sheet.paste(im, (x, y))
            d.text((x, y + TH + 4), l1, font=f1, fill=(255, 120, 120) if bad else (240, 240, 240))
            d.text((x, y + TH + 28), l2, font=f2, fill=(255, 210, 120))
        sheet.save(out / f"sheet_{pi // per + 1:02d}.jpg", quality=85)
    print(f"framing: {len(tiles)} photo shots -> {out}/sheet_*.jpg  (green = start view, red = end view)")
