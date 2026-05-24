#!/usr/bin/env python3
"""
Kids YouTube Video Generator
Animated sprites (blinking, bouncing) synced to music beats.

Usage:
    python generate_video.py --theme animals --duration 30
    python generate_video.py --theme animals --duration 1 --output output/test.mp4
"""

import os
import sys
import random
import math
import argparse
import logging
import time
from pathlib import Path
from typing import List, Tuple, Optional, Dict
from datetime import datetime

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import librosa
import yaml
from moviepy.editor import VideoClip, AudioFileClip, concatenate_audioclips
from moviepy.audio.fx.audio_loop import audio_loop

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "settings.yaml"

(ROOT / "logs").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(ROOT / "logs" / "generator.log"),
    ],
)
log = logging.getLogger(__name__)

ANIM_FPS   = 30     # animation frames per second
CYCLE_LEN  = 60     # frames per character animation cycle

# ── Config ─────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


# ── Asset loaders ──────────────────────────────────────────────────────────────

def load_animated_sprites(theme: str) -> List[Tuple[str, List[Image.Image]]]:
    """
    Returns list of (name, frames) tuples.
    Animated characters come from assets/sprites/animated/ (any theme).
    Falls back to static sprites wrapped in single-frame lists.
    """
    anim_dir = ROOT / "assets" / "sprites" / "animated"
    static_dir = ROOT / "assets" / "sprites" / theme

    sprites = []

    if anim_dir.exists():
        for char_dir in sorted(anim_dir.iterdir()):
            if not char_dir.is_dir():
                continue
            frames = []
            for f in sorted(char_dir.glob("frame_*.png")):
                frames.append(Image.open(f).convert("RGBA"))
            if frames:
                sprites.append((char_dir.name, frames))

    if not sprites and static_dir.exists():
        for p in sorted(static_dir.glob("*.png")):
            img = Image.open(p).convert("RGBA")
            sprites.append((p.stem, [img]))

    if not sprites:
        raise FileNotFoundError(
            f"No sprites found. Run: python scripts/generate_animated_sprites.py"
        )

    log.info(f"Loaded {len(sprites)} characters (theme='{theme}')")
    return sprites


def build_audio(duration_sec: float) -> AudioFileClip:
    """Assemble a non-repeating audio track by chaining Kevin MacLeod tracks."""
    music_dirs = [
        ROOT / "assets" / "music" / "kevin",
        ROOT / "assets" / "music",
    ]
    tracks = []
    for d in music_dirs:
        if d.exists():
            tracks += list(d.glob("*.mp3")) + list(d.glob("*.wav"))
    tracks = list({str(p): p for p in tracks}.values())  # deduplicate
    if not tracks:
        raise FileNotFoundError("No music files. Run: python scripts/setup_assets.py")

    random.shuffle(tracks)
    clips = []
    remaining = duration_sec
    idx = 0
    while remaining > 0:
        t = tracks[idx % len(tracks)]
        ac = AudioFileClip(str(t))
        use = min(remaining, ac.duration)
        clips.append(ac.subclip(0, use))
        remaining -= use
        idx += 1
    combined = concatenate_audioclips(clips)
    log.info(f"Audio: {len(clips)} track(s), {duration_sec/60:.1f} min")
    return combined


def analyze_beats(audio: AudioFileClip) -> Tuple[float, np.ndarray]:
    """Detect BPM and beat timestamps from the first 60s of audio."""
    import tempfile, os
    tmp = tempfile.mktemp(suffix=".wav")
    try:
        audio.subclip(0, min(60, audio.duration)).write_audiofile(
            tmp, fps=22050, nbytes=2, buffersize=20000, logger=None
        )
        y, sr = librosa.load(tmp, sr=None)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    bpm = float(np.atleast_1d(tempo)[0])
    log.info(f"BPM: {bpm:.1f}, beats detected: {len(beat_times)}")
    return bpm, beat_times


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


# ── Background ─────────────────────────────────────────────────────────────────

def draw_background(W: int, H: int, color: Tuple[int, int, int], t: float) -> Image.Image:
    """Gradient background with slowly drifting stars/circles."""
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)

    # Gradient (top lighter, bottom darker)
    r, g, b = color
    for y in range(H):
        ratio = y / H
        cr = int(r + (r * 0.35) * (1 - ratio))
        cg = int(g + (g * 0.35) * (1 - ratio))
        cb = int(b + (b * 0.35) * (1 - ratio))
        draw.line([(0, y), (W, y)], fill=(min(cr,255), min(cg,255), min(cb,255)))

    # Floating decorative circles (static per-segment, drift slowly)
    rng = random.Random(int(color[0]*1000 + color[1]*100 + color[2]))
    for _ in range(18):
        cx = rng.randint(0, W)
        cy = rng.randint(0, H)
        radius = rng.randint(18, 65)
        drift = math.sin(t * 0.4 + rng.random() * math.tau) * 22
        bright = tuple(min(255, int(c * 1.25)) for c in color)
        alpha = rng.randint(25, 60)
        circle_img = Image.new("RGBA", (radius*2, radius*2), (0,0,0,0))
        cdraw = ImageDraw.Draw(circle_img)
        cdraw.ellipse([0, 0, radius*2, radius*2], fill=bright + (alpha,))
        img.paste(circle_img.convert("RGB"), (int(cx - radius), int(cy - radius + drift)),
                  circle_img)

    # Sparkle stars
    rng2 = random.Random(int(t * 3))
    for _ in range(6):
        sx = rng2.randint(50, W - 50)
        sy = rng2.randint(30, H - 30)
        star_r = rng2.randint(3, 8)
        star_alpha = rng2.randint(80, 180)
        star_img = Image.new("RGBA", (star_r*4, star_r*4), (0,0,0,0))
        sdraw = ImageDraw.Draw(star_img)
        sdraw.ellipse([star_r, star_r, star_r*3, star_r*3],
                      fill=(255, 255, 255, star_alpha))
        img.paste(star_img.convert("RGB"), (sx, sy), star_img)

    return img


# ── Sprite actor ───────────────────────────────────────────────────────────────

class SpriteActor:
    """Animated character on screen — multi-frame with motion."""

    ANIMATIONS = ["bounce", "sway", "pulse", "float"]

    def __init__(
        self,
        name: str,
        frames: List[Image.Image],
        x: float,
        y: float,
        size: int,
        animation: Optional[str],
        appear_at: float,
        disappear_at: float,
        bpm: float,
    ):
        self.name = name
        self.frames = frames
        self.x = x
        self.y = y
        self.size = size
        self.animation = animation or random.choice(self.ANIMATIONS)
        self.appear_at = appear_at
        self.disappear_at = disappear_at
        self.beat_freq = bpm / 60.0
        self.phase = random.uniform(0, math.tau)
        self.float_vx = random.choice([-1, 1]) * random.uniform(50, 110)
        # Cache resized frames
        self._cache: Dict[int, Image.Image] = {}

    def _get_frame(self, global_t: float) -> Image.Image:
        """Pick and cache-resize the right animation frame."""
        n = len(self.frames)
        frame_idx = int((global_t - self.appear_at) * ANIM_FPS) % n
        if frame_idx not in self._cache:
            self._cache[frame_idx] = self.frames[frame_idx].resize(
                (self.size, self.size), Image.LANCZOS
            )
        return self._cache[frame_idx]

    def render(self, canvas: Image.Image, t: float, W: int, H: int,
               name_font=None) -> None:
        rel = t - self.appear_at
        if rel < 0:
            return
        fade_out = self.disappear_at - t
        alpha = min(1.0, rel / 0.4, fade_out / 0.4)
        if alpha <= 0:
            return

        beat = rel * self.beat_freq + self.phase
        x, y = self.x, self.y
        scale = 1.0
        angle = 0.0

        if self.animation == "bounce":
            bp = abs(math.sin(math.pi * beat))
            y -= bp * 55
            scale = 1.0 - 0.07 * bp

        elif self.animation == "sway":
            sway = math.sin(math.pi * beat)
            x += sway * 42
            angle = sway * 14

        elif self.animation == "pulse":
            scale = 1.0 + 0.22 * abs(math.sin(math.pi * beat))

        elif self.animation == "float":
            x = (self.x + self.float_vx * rel) % (W + self.size * 2) - self.size
            y = self.y + math.sin(rel * 0.85 + self.phase) * 55

        img = self._get_frame(t)

        # Scale
        final_size = max(4, int(self.size * scale))
        if final_size != self.size:
            img = img.resize((final_size, final_size), Image.BILINEAR)

        # Rotate
        if abs(angle) > 1.0:
            img = img.rotate(-angle % 360, expand=True, resample=Image.BILINEAR)

        # Alpha fade
        if alpha < 0.98:
            r, g, b, a = img.split()
            a = a.point(lambda p: int(p * alpha))
            img = Image.merge("RGBA", (r, g, b, a))

        # Paste
        px = int(x - img.width / 2)
        py = int(y - img.height / 2)
        canvas.paste(img, (px, py), img)

        # Name badge (only first 3 seconds of appearance)
        if name_font and rel < 3.0 and alpha > 0.3:
            badge_alpha = min(1.0, alpha) * min(1.0, (3.0 - rel) / 0.8)
            self._draw_badge(canvas, x, py - 10, badge_alpha, name_font)

    def _draw_badge(self, canvas, cx, top_y, alpha, font):
        label = self.name.capitalize()
        # Estimate text size
        dummy = ImageDraw.Draw(canvas)
        try:
            bbox = dummy.textbbox((0, 0), label, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
        except Exception:
            tw, th = len(label) * 14, 20

        pad = 10
        bw, bh = tw + pad*2, th + pad*2
        bx = int(cx - bw/2)
        by = int(top_y - bh - 8)

        badge = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
        bd = ImageDraw.Draw(badge)
        bd.rounded_rectangle([0, 0, bw-1, bh-1], radius=bh//2,
                               fill=(255, 255, 255, int(200 * alpha)))
        bd.text((pad, pad), label, fill=(60, 40, 100, int(240 * alpha)),
                font=font)
        canvas.paste(badge, (bx, by), badge)


# ── Video generator ────────────────────────────────────────────────────────────

class VideoGenerator:
    def __init__(self, config: dict, theme: str, duration_sec: float):
        self.cfg = config
        self.theme = theme
        self.duration = duration_sec
        self.W, self.H = config["video"]["resolution"]
        self.fps = config["video"]["fps"]
        self.sprite_size = config["animation"]["sprite_size"]
        self.n_on_screen = config["animation"]["sprites_on_screen"]
        self.bg_colors = config["video"]["background_colors"]
        self.group_interval = config["animation"]["group_change_interval"]

        self.char_sprites = load_animated_sprites(theme)
        self.audio = build_audio(duration_sec)
        self.bpm, _ = analyze_beats(self.audio)

        # Try to load a font for name badges
        self.font = self._load_font(32)

        self._bg_seq = self._build_bg_sequence()
        self.actors = self._build_schedule()
        log.info(f"Actors scheduled: {len(self.actors)}")

    def _load_font(self, size: int):
        for path in [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        ]:
            if Path(path).exists():
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    pass
        return ImageFont.load_default()

    def _build_bg_sequence(self):
        seq = []
        t = 0.0
        while t < self.duration:
            color = hex_to_rgb(random.choice(self.bg_colors))
            dur = random.uniform(self.group_interval[0], self.group_interval[1])
            seq.append((color, t))
            t += dur
        return seq

    def _get_bg_color(self, t: float) -> Tuple[int, int, int]:
        color = self._bg_seq[0][0]
        for c, start in self._bg_seq:
            if start <= t:
                color = c
            else:
                break
        return color

    def _get_positions(self, n: int):
        margin = self.sprite_size * 0.7
        positions = []
        cols = math.ceil(math.sqrt(n))
        rows = math.ceil(n / cols)
        for i in range(n):
            col = i % cols
            row = i // cols
            x = margin + (col + 0.5) * (self.W - 2 * margin) / cols
            y = self.H * 0.18 + (row + 0.5) * (self.H * 0.62) / rows
            x += random.uniform(-60, 60)
            y += random.uniform(-30, 30)
            positions.append((x, y))
        return positions

    def _build_schedule(self) -> List[SpriteActor]:
        actors = []
        t = 0.0
        while t < self.duration:
            dur = random.uniform(self.group_interval[0], self.group_interval[1])
            group_end = min(t + dur, self.duration)
            n = self.n_on_screen
            chosen = random.choices(self.char_sprites, k=n)
            positions = self._get_positions(n)
            for (name, frames), pos in zip(chosen, positions):
                appear = t + random.uniform(0, 1.5)
                actors.append(SpriteActor(
                    name=name,
                    frames=frames,
                    x=pos[0], y=pos[1],
                    size=self.sprite_size,
                    animation=None,
                    appear_at=appear,
                    disappear_at=group_end,
                    bpm=self.bpm,
                ))
            t = group_end
        return actors

    def make_frame(self, t: float) -> np.ndarray:
        bg_color = self._get_bg_color(t)
        canvas = draw_background(self.W, self.H, bg_color, t).convert("RGBA")

        for actor in self.actors:
            if actor.appear_at - 0.5 <= t <= actor.disappear_at + 0.5:
                actor.render(canvas, t, self.W, self.H, name_font=self.font)

        return np.array(canvas.convert("RGB"))

    def generate(self, output_path: str) -> str:
        log.info(
            f"Generating: theme={self.theme}, "
            f"duration={self.duration/60:.1f}min, "
            f"chars={len(self.char_sprites)}"
        )
        start_t = time.time()
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        video = VideoClip(self.make_frame, duration=self.duration)
        video = video.set_fps(self.fps).set_audio(self.audio)

        video.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            fps=self.fps,
            preset="fast",
            ffmpeg_params=["-pix_fmt", "yuv420p", "-crf", "23"],
            verbose=False,
            logger="bar",
        )

        elapsed = time.time() - start_t
        size_mb = Path(output_path).stat().st_size / 1_000_000
        log.info(f"Done in {elapsed:.0f}s → {output_path} ({size_mb:.1f} MB)")
        return output_path


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate kids YouTube video")
    parser.add_argument("--theme", default="animals")
    parser.add_argument("--duration", type=float, default=30,
                        help="Duration in minutes")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    config = load_config()
    if args.output is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = str(ROOT / "output" / f"{args.theme}_{ts}.mp4")

    gen = VideoGenerator(config, args.theme, args.duration * 60)
    gen.generate(args.output)
    print(f"\n✓ Video saved: {args.output}")


if __name__ == "__main__":
    main()
