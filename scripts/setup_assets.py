#!/usr/bin/env python3
"""
Create sample sprites and test music for first run.
Run once: python scripts/setup_assets.py

Sprites: colorful circles with cute faces (placeholder until real PNG sets added).
Music: simple 120 BPM beat loop (placeholder until real MP3 added).
Logo: simple watermark.
"""

import math
import random
import struct
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SPRITES_DIR = ROOT / "assets" / "sprites"
MUSIC_DIR   = ROOT / "assets" / "music"


# ── Sprite generation ──────────────────────────────────────────────────────────

def make_sprite(color_rgb: tuple, size: int = 300) -> Image.Image:
    """Create a round smiley sprite with transparent background."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    pad = size // 10
    r, g, b = color_rgb

    # Body (circle)
    draw.ellipse([pad, pad, size - pad, size - pad], fill=(r, g, b, 255))

    # Highlight (top-left glow)
    hl_size = size // 4
    hl_img = Image.new("RGBA", (hl_size, hl_size), (0, 0, 0, 0))
    hl_draw = ImageDraw.Draw(hl_img)
    hl_draw.ellipse([0, 0, hl_size, hl_size], fill=(255, 255, 255, 80))
    img.paste(hl_img, (pad + size // 8, pad + size // 8), hl_img)

    # Eyes
    cx, cy = size // 2, size // 2
    eye_r = size // 11
    eye_y = cy - size // 9
    draw.ellipse(
        [cx - size // 5 - eye_r, eye_y - eye_r,
         cx - size // 5 + eye_r, eye_y + eye_r],
        fill=(40, 30, 30, 255),
    )
    draw.ellipse(
        [cx + size // 5 - eye_r, eye_y - eye_r,
         cx + size // 5 + eye_r, eye_y + eye_r],
        fill=(40, 30, 30, 255),
    )
    # Pupils (white glint)
    g_r = max(2, eye_r // 3)
    draw.ellipse(
        [cx - size // 5 - eye_r // 3 - g_r, eye_y - eye_r // 3 - g_r,
         cx - size // 5 - eye_r // 3 + g_r, eye_y - eye_r // 3 + g_r],
        fill=(255, 255, 255, 200),
    )

    # Smile
    smile_w = size // 4
    smile_y = cy + size // 12
    draw.arc(
        [cx - smile_w, smile_y, cx + smile_w, smile_y + size // 5],
        start=10, end=170,
        fill=(40, 30, 30, 255),
        width=max(2, size // 22),
    )

    # Cheeks
    cheek_r = size // 9
    draw.ellipse(
        [cx - size // 3 - cheek_r, cy + size // 20 - cheek_r,
         cx - size // 3 + cheek_r, cy + size // 20 + cheek_r],
        fill=(r + 30, g - 20, b - 20, 100) if r < 220 else (255, 160, 160, 100),
    )
    draw.ellipse(
        [cx + size // 3 - cheek_r, cy + size // 20 - cheek_r,
         cx + size // 3 + cheek_r, cy + size // 20 + cheek_r],
        fill=(r + 30, g - 20, b - 20, 100) if r < 220 else (255, 160, 160, 100),
    )

    return img


THEMES = {
    "fruits": [
        ("apple",       (220,  55,  55)),
        ("banana",      (255, 220,   0)),
        ("grape",       (150,  50, 200)),
        ("orange",      (255, 145,   0)),
        ("strawberry",  (255,  80,  80)),
        ("watermelon",  ( 60, 195, 100)),
        ("cherry",      (175,  25,  55)),
        ("lemon",       (245, 245,  45)),
        ("peach",       (255, 180, 120)),
        ("kiwi",        ( 90, 160,  60)),
    ],
    "vegetables": [
        ("carrot",      (255, 130,   0)),
        ("broccoli",    ( 50, 175,  50)),
        ("tomato",      (220,  60,  60)),
        ("corn",        (255, 230,   0)),
        ("eggplant",    (120,  45, 160)),
        ("pumpkin",     (230, 110,  25)),
        ("pea",         (120, 200,  80)),
        ("radish",      (220,  80, 100)),
    ],
    "animals": [
        ("cat",         (210, 170, 130)),
        ("dog",         (200, 160, 100)),
        ("rabbit",      (230, 220, 215)),
        ("bear",        (155, 115,  75)),
        ("elephant",    (155, 155, 175)),
        ("giraffe",     (240, 200,  70)),
        ("penguin",     ( 65,  65,  85)),
        ("duck",        (255, 220,  45)),
        ("fox",         (220, 120,  50)),
        ("koala",       (175, 175, 185)),
    ],
    "shapes": [
        ("star",        (255, 220,   0)),
        ("heart",       (255,  80, 100)),
        ("circle",      (100, 185, 255)),
        ("square",      (255, 150,  80)),
        ("triangle",    (100, 220, 150)),
        ("diamond",     (200, 100, 255)),
    ],
}


def create_sprites():
    for theme, sprites in THEMES.items():
        theme_dir = SPRITES_DIR / theme
        theme_dir.mkdir(parents=True, exist_ok=True)
        for name, color in sprites:
            path = theme_dir / f"{name}.png"
            if path.exists():
                continue
            img = make_sprite(color)
            img.save(path)
            print(f"  {path.relative_to(ROOT)}")
    print(f"Sprites: {sum(len(v) for v in THEMES.values())} files created.")


# ── Logo / watermark ───────────────────────────────────────────────────────────

def create_logo():
    logo_path = ROOT / "assets" / "logo.png"
    if logo_path.exists():
        return
    size = 120
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Yellow circle
    draw.ellipse([4, 4, size - 4, size - 4], fill=(255, 215, 0, 210))
    # Bear ears
    ear_r = 18
    draw.ellipse([8, 4, 8 + ear_r * 2, 4 + ear_r * 2], fill=(200, 160, 80, 210))
    draw.ellipse([size - 8 - ear_r * 2, 4, size - 8, 4 + ear_r * 2], fill=(200, 160, 80, 210))
    # Eyes
    cx, cy = size // 2, size // 2 - 5
    draw.ellipse([cx - 20, cy - 8, cx - 10, cy + 2], fill=(40, 30, 30, 255))
    draw.ellipse([cx + 10, cy - 8, cx + 20, cy + 2], fill=(40, 30, 30, 255))
    # Smile
    draw.arc([cx - 16, cy + 4, cx + 16, cy + 22], 10, 170, fill=(40, 30, 30, 255), width=3)
    img.save(logo_path)
    print(f"  {logo_path.relative_to(ROOT)}")


# ── Test music ─────────────────────────────────────────────────────────────────

def create_test_music():
    """Generate a simple 8-second WAV loop at 120 BPM."""
    music_path = MUSIC_DIR / "happy_loop_1.wav"
    MUSIC_DIR.mkdir(parents=True, exist_ok=True)

    if music_path.exists():
        return

    sr = 44100
    bpm = 120
    beat = 60 / bpm          # 0.5 s
    bar = beat * 4            # 2 s
    total = bar * 4           # 8 s loop
    N = int(sr * total)
    t = np.linspace(0, total, N, endpoint=False)

    audio = np.zeros(N, dtype=np.float32)

    # Kick drum — beats 1 & 3
    for b in range(int(total / beat)):
        if b % 4 in (0, 2):
            s = int(b * beat * sr)
            e = min(s + int(0.12 * sr), N)
            kt = np.linspace(0, 0.12, e - s)
            audio[s:e] += 0.8 * np.sin(2 * math.pi * 75 * kt) * np.exp(-kt * 28)

    # Hi-hat — every half-beat
    for b in range(int(total / (beat / 2))):
        s = int(b * beat / 2 * sr)
        e = min(s + int(0.04 * sr), N)
        n = e - s
        audio[s:e] += 0.22 * (2 * np.random.rand(n) - 1) * np.exp(-np.linspace(0, 1, n) * 40)

    # Snare — beats 2 & 4
    for b in range(int(total / beat)):
        if b % 4 in (1, 3):
            s = int(b * beat * sr)
            e = min(s + int(0.08 * sr), N)
            n = e - s
            st = np.linspace(0, 0.08, n)
            audio[s:e] += 0.5 * (
                0.6 * np.sin(2 * math.pi * 200 * st) +
                0.4 * (2 * np.random.rand(n) - 1)
            ) * np.exp(-st * 25)

    # Simple melody (C major pentatonic)
    notes = [261.63, 329.63, 392.00, 523.25, 392.00, 329.63]  # C E G C5 G E
    for i, note in enumerate(notes * 2):
        s = int(i * beat * sr)
        e = min(s + int(beat * sr), N)
        mt = np.linspace(0, beat, e - s)
        env = (1 - mt / beat) ** 2 * 0.35
        audio[s:e] += env * np.sin(2 * math.pi * note * mt)

    # Bass line
    bass_notes = [130.81, 130.81, 146.83, 164.81]   # C G D E
    for i, note in enumerate(bass_notes * int(total / bar)):
        s = int(i * bar / len(bass_notes) * sr)
        e = min(s + int(bar / len(bass_notes) * sr), N)
        bt = np.linspace(0, bar / len(bass_notes), e - s)
        env = np.exp(-bt * 3) * 0.4
        audio[s:e] += env * np.sin(2 * math.pi * note * bt)

    # Normalize and write
    audio = audio / max(abs(audio.max()), 0.01) * 0.88
    audio_i16 = (audio * 32767).astype(np.int16)

    with wave.open(str(music_path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(audio_i16.tobytes())

    print(f"  {music_path.relative_to(ROOT)}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("Setting up assets...\n")
    print("Sprites:")
    create_sprites()
    print("\nLogo:")
    create_logo()
    print("\nMusic:")
    create_test_music()
    print("\nDone! To generate your first test video:")
    print("  python scripts/generate_video.py --theme fruits --duration 1 --output output/test.mp4")


if __name__ == "__main__":
    main()
