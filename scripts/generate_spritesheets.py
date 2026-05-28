#!/usr/bin/env python3
"""
Generate animated sprite sheets from static sprites using squash-and-stretch.
Each sprite gets 8 frames: normal, squash, stretch, lean-L, lean-R, tilt-L, tilt-R, big.
Output: assets/spritesheets/{theme}/{char}.png  (horizontal strip of 8 frames)
"""
from pathlib import Path
from PIL import Image, ImageFilter
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SPRITE_SIZE = 512   # output frame size (square)
N_FRAMES = 8


def load_sprite(path: Path, size: int = SPRITE_SIZE) -> Image.Image:
    img = Image.open(path).convert("RGBA")
    # Resize keeping aspect ratio, pad to square
    img.thumbnail((size, size), Image.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    x = (size - img.width) // 2
    y = (size - img.height) // 2
    canvas.paste(img, (x, y), img)
    return canvas


def squash(img: Image.Image, sx: float = 1.25, sy: float = 0.82) -> Image.Image:
    """Squash: wider + shorter (landing impact)."""
    W, H = img.size
    new_w = int(W * sx)
    new_h = int(H * sy)
    resized = img.resize((new_w, new_h), Image.LANCZOS)
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    x = (W - new_w) // 2
    y = H - new_h  # anchor to bottom
    canvas.paste(resized, (x, y), resized)
    return canvas


def stretch(img: Image.Image, sx: float = 0.82, sy: float = 1.22) -> Image.Image:
    """Stretch: narrower + taller (jumping up)."""
    W, H = img.size
    new_w = int(W * sx)
    new_h = int(H * sy)
    resized = img.resize((new_w, min(new_h, H)), Image.LANCZOS)
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    x = (W - new_w) // 2
    y = max(0, H - resized.height)
    canvas.paste(resized, (x, y), resized)
    return canvas


def lean(img: Image.Image, angle_deg: float) -> Image.Image:
    """Lean left or right by rotating and keeping bottom anchor."""
    W, H = img.size
    rotated = img.rotate(angle_deg, resample=Image.BICUBIC, expand=False)
    return rotated


def shear_x(img: Image.Image, shear: float) -> Image.Image:
    """Horizontal shear — makes character lean without rotating."""
    W, H = img.size
    arr = np.array(img, dtype=np.float32)
    result = np.zeros_like(arr)
    for y in range(H):
        shift = int((y - H // 2) * shear)
        if shift >= 0:
            result[y, shift:] = arr[y, :W - shift]
        else:
            result[y, :W + shift] = arr[y, -shift:]
    return Image.fromarray(result.astype(np.uint8), "RGBA")


def scale_center(img: Image.Image, sx: float, sy: float) -> Image.Image:
    """Scale from center."""
    W, H = img.size
    new_w = int(W * sx)
    new_h = int(H * sy)
    resized = img.resize((new_w, new_h), Image.LANCZOS)
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    x = (W - new_w) // 2
    y = (H - new_h) // 2
    canvas.paste(resized, (x, y), resized)
    return canvas


def make_frames(sprite: Image.Image) -> list[Image.Image]:
    """8 animation frames for squash-and-stretch dance."""
    return [
        sprite,                          # 0: normal
        squash(sprite, 1.22, 0.84),      # 1: squash (landing)
        stretch(sprite, 0.84, 1.18),     # 2: stretch (jumping)
        scale_center(sprite, 1.06, 1.06),# 3: big (anticipation)
        shear_x(sprite, -0.18),          # 4: lean left
        shear_x(sprite,  0.18),          # 5: lean right
        lean(sprite, -12),               # 6: tilt left
        lean(sprite,  12),               # 7: tilt right
    ]


def make_spritesheet(frames: list[Image.Image], frame_size: int) -> Image.Image:
    """Combine frames into a horizontal strip."""
    sheet = Image.new("RGBA", (frame_size * len(frames), frame_size), (0, 0, 0, 0))
    for i, frame in enumerate(frames):
        sheet.paste(frame, (i * frame_size, 0))
    return sheet


def process_theme(theme: str, sprite_dir: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    sprites = sorted(sprite_dir.glob("*.png"))
    if not sprites:
        print(f"  No sprites in {sprite_dir}")
        return

    print(f"\n{theme.upper()} ({len(sprites)} sprites):")
    for sp in sprites:
        sprite = load_sprite(sp, SPRITE_SIZE)
        frames = make_frames(sprite)
        sheet = make_spritesheet(frames, SPRITE_SIZE)
        out = out_dir / f"{sp.stem}.png"
        sheet.save(out, "PNG", optimize=False)
        print(f"  ✓ {sp.stem}  ({N_FRAMES} frames × {SPRITE_SIZE}px)")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--themes", nargs="+", default=["animals", "fruits", "vegetables"])
    args = parser.parse_args()

    sprites_src = ROOT / "assets" / "sprites_new"
    sheets_dir = ROOT / "assets" / "spritesheets"
    sheets_dir.mkdir(parents=True, exist_ok=True)

    for theme in args.themes:
        src = sprites_src / theme
        if not src.exists():
            print(f"Skipping {theme} — not found")
            continue
        process_theme(theme, src, sheets_dir / theme)

    print(f"\nDone! Spritesheets → {sheets_dir}")
    print(f"Format: horizontal strip of {N_FRAMES} frames × {SPRITE_SIZE}px each")
    print(f"Frame index: 0=normal 1=squash 2=stretch 3=big 4=lean-L 5=lean-R 6=tilt-L 7=tilt-R")


if __name__ == "__main__":
    main()
