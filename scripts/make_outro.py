#!/usr/bin/env python3
"""
Generate 25-second end-screen outro clips for CNR and Kids channels.

The outro contains:
  - Channel branding (name, tagline)
  - Two "card zone" rectangles — YouTube Studio overlays interactive cards here
  - Subscribe prompt
  - Fade in / fade out

Usage:
    python3 scripts/make_outro.py                  # generate all channel outros
    python3 scripts/make_outro.py --channel cnr    # CNR only
    python3 scripts/make_outro.py --channel kids   # Kids (EN+AR) only
    python3 scripts/make_outro.py --dry-run

Output:
    output/_outros/outro_cnr.mp4
    output/_outros/outro_kids.mp4    (same clip for EN+AR — no text → works both)

YouTube Studio integration:
    After video uploads, go to YouTube Studio → Content → select video
    → End screen → Add element → select "Video" → drag to match card zones
    Or: use End screen template (save once, apply to all future videos).
"""
import argparse
import io
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT      = Path(__file__).resolve().parent.parent
OUTRO_DIR = ROOT / "output" / "_outros"

W, H          = 1920, 1080
OUTRO_SECS    = 25
FADE_SECS     = 2
FPS           = 25

# ── Font paths ────────────────────────────────────────────────────────────────
FONT_SANS_BOLD   = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_SERIF_BOLD  = "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"
FONT_SERIF       = "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"
FONT_SANS        = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"

def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _draw_centered_text(draw: ImageDraw.Draw, text: str, font, y: int,
                         color: tuple, shadow_color: tuple | None = None):
    """Draw horizontally centered text with optional drop shadow."""
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    x = (W - tw) // 2
    if shadow_color:
        draw.text((x + 3, y + 3), text, font=font, fill=shadow_color)
    draw.text((x, y), text, font=font, fill=color)


def make_cnr_frame() -> Image.Image:
    """Create the CNR (Classical Night Relax) outro frame."""
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)

    # ── Background gradient (dark navy → deep purple) ─────────────────────────
    for y in range(H):
        t = y / H
        r = int(10  + t * 15)
        g = int(16  + t * 8)
        b = int(40  + t * 20)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # ── Subtle star pattern ───────────────────────────────────────────────────
    import random
    rng = random.Random(42)
    for _ in range(180):
        sx = rng.randint(0, W)
        sy = rng.randint(0, H // 2)
        sz = rng.randint(1, 3)
        alpha = rng.randint(100, 220)
        draw.ellipse([sx-sz, sy-sz, sx+sz, sy+sz], fill=(alpha, alpha, alpha))

    # ── Decorative thin horizontal line ──────────────────────────────────────
    line_y = 320
    draw.rectangle([160, line_y, W-160, line_y+1], fill=(180, 160, 220))

    # ── Channel name ─────────────────────────────────────────────────────────
    font_name = _font(FONT_SERIF_BOLD, 74)
    _draw_centered_text(draw, "Classical Night Relax", font_name, 200,
                        color=(230, 220, 255),
                        shadow_color=(60, 40, 100))

    # ── Tagline ───────────────────────────────────────────────────────────────
    font_tag = _font(FONT_SERIF, 32)
    _draw_centered_text(draw, "Classical music for sleep · focus · relaxation", font_tag, 340,
                        color=(180, 165, 210))

    # ── "WATCH NEXT" label ───────────────────────────────────────────────────
    font_label = _font(FONT_SANS_BOLD, 26)
    font_small = _font(FONT_SANS, 22)

    card_top     = 430
    card_h       = 310
    card_w       = 640
    gap          = 60
    left_x       = (W - 2 * card_w - gap) // 2
    right_x      = left_x + card_w + gap

    _draw_centered_text(draw, "WATCH NEXT", font_label, card_top - 44,
                        color=(200, 190, 240))

    # ── Card zone rectangles (YouTube will overlay interactive end cards here) ─
    for cx in (left_x, right_x):
        # Shadow
        draw.rectangle([cx+4, card_top+4, cx+card_w+4, card_top+card_h+4],
                       fill=(0, 0, 0, 60))
        # Card border
        draw.rectangle([cx, card_top, cx+card_w, card_top+card_h],
                       outline=(140, 120, 200), width=2)
        # Card fill (slightly lighter)
        draw.rectangle([cx+2, card_top+2, cx+card_w-2, card_top+card_h-2],
                       fill=(20, 25, 55))
        # Play icon (triangle)
        px = cx + card_w // 2
        py = card_top + card_h // 2
        r = 32
        triangle = [(px - r, py - r), (px + r, py), (px - r, py + r)]
        draw.polygon(triangle, fill=(160, 140, 210))
        # "Video" label below
        draw.text((cx + card_w//2 - 30, card_top + card_h - 42),
                  "next video", font=font_small, fill=(120, 110, 170))

    # ── Subscribe row ─────────────────────────────────────────────────────────
    sub_y = card_top + card_h + 40
    font_sub = _font(FONT_SANS_BOLD, 36)
    # Bell icon (simple circle)
    bell_x = (W - 500) // 2
    draw.ellipse([bell_x, sub_y + 4, bell_x + 36, sub_y + 40], fill=(230, 60, 60))
    draw.text((bell_x + 8, sub_y + 6), "▶", font=_font(FONT_SANS, 22), fill=(255, 255, 255))

    _draw_centered_text(draw, "Subscribe & never miss a sleep program",
                        font_sub, sub_y,
                        color=(255, 255, 255),
                        shadow_color=(40, 20, 80))

    # ── @handle ──────────────────────────────────────────────────────────────
    font_handle = _font(FONT_SANS, 28)
    _draw_centered_text(draw, "@ClassicalNightRelax", font_handle, sub_y + 56,
                        color=(150, 140, 200))

    return img


def make_kids_frame() -> Image.Image:
    """Create the Happy Bear Kids outro frame (text-free, works for EN+AR)."""
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)

    # ── Colorful gradient background ──────────────────────────────────────────
    for y in range(H):
        t = y / H
        r = int(255 - t * 60)
        g = int(200 - t * 40)
        b = int(50  + t * 100)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # ── Decorative stars ──────────────────────────────────────────────────────
    import random
    rng = random.Random(7)
    for _ in range(40):
        sx = rng.randint(80, W - 80)
        sy = rng.randint(60, 220)
        sz = rng.randint(8, 18)
        draw.ellipse([sx-sz, sy-sz, sx+sz, sy+sz], fill=(255, 255, 100))

    # ── Channel name ─────────────────────────────────────────────────────────
    font_name = _font(FONT_SANS_BOLD, 78)
    _draw_centered_text(draw, "Happy Bear Kids", font_name, 180,
                        color=(255, 255, 255),
                        shadow_color=(180, 100, 0))

    # ── Bear emoji row ───────────────────────────────────────────────────────
    font_bear = _font(FONT_SANS, 52)
    _draw_centered_text(draw, "🐻  🌈  ⭐  🐻", font_bear, 300, color=(255, 255, 255))

    # ── "WATCH NEXT" + card zones ─────────────────────────────────────────────
    font_label = _font(FONT_SANS_BOLD, 28)
    font_small = _font(FONT_SANS, 22)

    card_top = 420
    card_h   = 300
    card_w   = 640
    gap      = 60
    left_x   = (W - 2 * card_w - gap) // 2
    right_x  = left_x + card_w + gap

    _draw_centered_text(draw, "▶  WATCH NEXT  ◀", font_label, card_top - 48,
                        color=(255, 255, 255))

    for cx in (left_x, right_x):
        draw.rectangle([cx, card_top, cx+card_w, card_top+card_h],
                       fill=(255, 255, 255, 200), outline=(255, 200, 0), width=3)
        draw.rectangle([cx+2, card_top+2, cx+card_w-2, card_top+card_h-2],
                       fill=(255, 245, 200))
        px = cx + card_w // 2
        py = card_top + card_h // 2
        r = 36
        triangle = [(px - r, py - r), (px + r, py), (px - r, py + r)]
        draw.polygon(triangle, fill=(255, 140, 0))
        draw.text((cx + card_w//2 - 30, card_top + card_h - 40),
                  "next video", font=font_small, fill=(180, 100, 0))

    # ── Subscribe ─────────────────────────────────────────────────────────────
    sub_y = card_top + card_h + 40
    font_sub = _font(FONT_SANS_BOLD, 38)
    _draw_centered_text(draw, "🔔  Subscribe for more fun videos!",
                        font_sub, sub_y, color=(255, 255, 255),
                        shadow_color=(180, 80, 0))

    return img


def frame_to_video(img: Image.Image, out_mp4: Path, dry_run: bool) -> bool:
    """Convert a PIL frame to a 25-second fade-in/fade-out MP4."""
    out_mp4.parent.mkdir(parents=True, exist_ok=True)

    if dry_run:
        print(f"  [DRY RUN] → {out_mp4.name}")
        return True

    # Save frame as PNG to temp file
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        tmp_png = Path(f.name)
    img.save(str(tmp_png))

    vf = (
        f"fade=t=in:st=0:d={FADE_SECS},"
        f"fade=t=out:st={OUTRO_SECS - FADE_SECS}:d={FADE_SECS}"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(tmp_png),
        "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo",
        "-t", str(OUTRO_SECS),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-r", str(FPS),
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        str(out_mp4),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    tmp_png.unlink(missing_ok=True)

    if r.returncode != 0 or not out_mp4.exists():
        print(f"  ✗ FFmpeg failed: {r.stderr[-300:]}")
        return False
    sz = out_mp4.stat().st_size // 1024
    print(f"  ✓ {out_mp4.name} ({sz} KB)")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", choices=["cnr", "kids", "all"], default="all")
    parser.add_argument("--force",   action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print("\n=== Outro clips ===\n")
    OUTRO_DIR.mkdir(parents=True, exist_ok=True)

    channels = {"cnr", "kids"} if args.channel == "all" else {args.channel}

    if "cnr" in channels:
        out = OUTRO_DIR / "outro_cnr.mp4"
        if out.exists() and not args.force:
            print(f"  EXISTS: {out.name} (--force to regen)")
        else:
            print("  Building CNR outro frame...")
            frame = make_cnr_frame()
            frame_to_video(frame, out, args.dry_run)

    if "kids" in channels:
        out = OUTRO_DIR / "outro_kids.mp4"
        if out.exists() and not args.force:
            print(f"  EXISTS: {out.name} (--force to regen)")
        else:
            print("  Building Kids outro frame...")
            frame = make_kids_frame()
            frame_to_video(frame, out, args.dry_run)

    print(f"\nOutro clips: {OUTRO_DIR}")
    print("\nYouTube Studio → End screens workflow:")
    print("  1. Open any uploaded video → End screen → Add element")
    print("  2. Drag 'Video' card into the left card zone")
    print("  3. Drag 'Video' card into the right card zone")
    print("  4. Set to 'Best for viewer' or pick specific video")
    print("  5. Save as template → apply to all future uploads")


if __name__ == "__main__":
    main()
