#!/usr/bin/env python3
"""Thumbnail text overlay — CNR / Calm Classics style.

Design:
  - BebasNeue for main title (large, condensed, YouTube-style)
  - Montserrat for duration badge and channel tag
  - Bottom gradient (dark) — title stays fully readable over any image
  - Subtle vignette on left edge for extra depth
  - Gold accent color for duration badge
"""
from pathlib import Path
from typing import Optional

FONTS_DIR   = Path(__file__).resolve().parent.parent / "assets" / "fonts"
FONT_BEBAS  = str(FONTS_DIR / "BebasNeue-Regular.ttf")
FONT_MONT   = str(FONTS_DIR / "Montserrat-Variable.ttf")
FONT_FALLBACK = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"

# Gold / cream palette
GOLD    = (255, 210, 80)
CREAM   = (255, 248, 220)
WHITE   = (255, 255, 255)
SHADOW  = (0, 0, 0)


def _load_fonts(main_size: int = 96, sub_size: int = 46):
    from PIL import ImageFont
    try:
        font_main = ImageFont.truetype(FONT_BEBAS, main_size)
    except Exception:
        font_main = ImageFont.truetype(FONT_FALLBACK, main_size)
    try:
        font_sub = ImageFont.truetype(FONT_MONT, sub_size)
    except Exception:
        font_sub = ImageFont.truetype(FONT_FALLBACK, sub_size)
    return font_main, font_sub


def _draw_bottom_gradient(img, gradient_height: int = 280):
    """Add a dark-to-transparent gradient at the bottom of the image."""
    from PIL import Image as _PIL, ImageDraw
    import numpy as np

    arr = np.array(img.convert("RGBA"), dtype=np.float32)
    H, W = arr.shape[:2]

    # Gradient alpha: 0 at top of strip, 0.82 at bottom
    for row_offset in range(gradient_height):
        y = H - gradient_height + row_offset
        alpha = (row_offset / gradient_height) ** 1.4 * 0.82
        arr[y, :, :3] = arr[y, :, :3] * (1 - alpha)  # darken toward black

    return _PIL.fromarray(arr.astype(np.uint8)).convert("RGB")


def _draw_text_shadow(draw, pos, text, font, offset=3, blur_passes=2):
    """Draw text with multi-pass shadow for depth."""
    x, y = pos
    for dx in range(-offset, offset + 1):
        for dy in range(0, offset + 1):
            if dx == 0 and dy == 0:
                continue
            draw.text((x + dx, y + dy), text, font=font, fill=(0, 0, 0, 200))


def add_thumb_text(img, text: str, duration_hours: Optional[int] = None,
                   channel_tag: str = "Calm Classics"):
    """Overlay beautiful text on a PIL Image. Returns new image."""
    from PIL import Image as _PIL, ImageDraw, ImageFont
    import numpy as np

    W, H = img.size
    font_main, font_sub = _load_fonts(main_size=104, sub_size=44)

    lines = [l.strip() for l in text.upper().split("\n") if l.strip()]

    # 1. Bottom gradient
    img = _draw_bottom_gradient(img, gradient_height=int(H * 0.45))

    draw = ImageDraw.Draw(img, "RGBA")

    # 2. Main title lines — large BebasNeue, bottom-left aligned
    margin_x = 38
    line_h    = 108
    total_text_h = len(lines) * line_h
    y_start   = H - total_text_h - 70
    if duration_hours:
        y_start -= 56   # leave room for duration badge above

    for i, line in enumerate(lines):
        y = y_start + i * line_h
        # Shadow pass
        for dx, dy in [(-2, 2), (2, 2), (0, 3), (-3, 3), (3, 3)]:
            draw.text((margin_x + dx, y + dy), line, font=font_main,
                      fill=(0, 0, 0, 180))
        # Main text — white with slight warm tint on first line
        color = CREAM if i == 0 else WHITE
        draw.text((margin_x, y), line, font=font_main, fill=color)

    # 3. Duration badge — gold pill, bottom-right corner
    if duration_hours:
        badge_text = f"{duration_hours}H"
        bbox = draw.textbbox((0, 0), badge_text, font=font_sub)
        bw, bh = bbox[2] - bbox[0], bbox[3] - bbox[1]
        pad_x, pad_y = 18, 10
        bx = W - bw - pad_x * 2 - 28
        by = H - bh - pad_y * 2 - 28

        # Gold pill background
        draw.rounded_rectangle(
            [bx, by, bx + bw + pad_x * 2, by + bh + pad_y * 2],
            radius=8, fill=(200, 155, 20, 230)
        )
        draw.text((bx + pad_x, by + pad_y), badge_text, font=font_sub, fill=WHITE)

    # 4. Channel tag — small Montserrat, very bottom-left
    try:
        font_tag = ImageFont.truetype(FONT_MONT, 28)
    except Exception:
        font_tag = font_sub
    tag_y = H - 32
    draw.text((margin_x, tag_y), channel_tag.upper(), font=font_tag,
              fill=(200, 200, 200, 160))

    return img.convert("RGB")


def thumb_text_for_program(program: dict) -> str:
    """Derive short overlay text from a sleep_program YAML dict."""
    if program.get("thumb_text"):
        return program["thumb_text"]

    prog_id = program.get("id", "")
    composers = []
    for t in program.get("tracks", []):
        name = t.get("composer", "")
        if name:
            last = name.split()[-1].upper()
            if last not in composers:
                composers.append(last)

    if not composers:
        parts = prog_id.replace("focus_", "").replace("sleep_", "").split("_")
        composers = [parts[0].upper()] if parts else ["CLASSICAL"]

    composer_label = " · ".join(composers[:2])

    if prog_id.startswith("focus_"):
        return f"{composer_label}\nFOCUS MUSIC"
    elif prog_id.startswith("sleep_"):
        return f"{composer_label}\nSLEEP MUSIC"
    else:
        return composer_label
