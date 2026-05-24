#!/usr/bin/env python3
"""
Kids YouTube Video Generator
Generates animated sprite videos synced to music beats.

Usage:
    python generate_video.py --theme fruits --duration 30
    python generate_video.py --theme animals --duration 5 --output output/test.mp4
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
from PIL import Image, ImageDraw
import librosa
import yaml
from moviepy.editor import VideoClip, AudioFileClip
from moviepy.audio.fx.audio_loop import audio_loop

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "settings.yaml"

# Ensure logs dir exists
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


# ── Config ─────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


# ── Asset loaders ──────────────────────────────────────────────────────────────

def load_sprites(theme: str) -> List[Image.Image]:
    sprites_dir = ROOT / "assets" / "sprites" / theme
    if not sprites_dir.exists():
        raise FileNotFoundError(f"No sprites dir: {sprites_dir}")
    sprites = []
    for p in sorted(sprites_dir.glob("*.png")):
        try:
            sprites.append(Image.open(p).convert("RGBA"))
        except Exception as e:
            log.warning(f"Skipping {p.name}: {e}")
    if not sprites:
        raise FileNotFoundError(f"No PNG files in {sprites_dir}")
    log.info(f"Loaded {len(sprites)} sprites for theme '{theme}'")
    return sprites


def pick_music() -> Path:
    music_dir = ROOT / "assets" / "music"
    tracks = list(music_dir.glob("*.mp3")) + list(music_dir.glob("*.wav"))
    if not tracks:
        raise FileNotFoundError(f"No music files in {music_dir}. Run: python scripts/setup_assets.py")
    return random.choice(tracks)


def analyze_beats(music_path: Path) -> Tuple[float, np.ndarray]:
    log.info(f"Analyzing beats: {music_path.name}")
    # Load only first 60s for speed — pattern repeats anyway
    y, sr = librosa.load(str(music_path), sr=None, duration=60)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    log.info(f"BPM: {float(tempo):.1f}, beats in sample: {len(beat_times)}")
    return float(tempo), beat_times


def load_watermark(config: dict) -> Optional[Image.Image]:
    wm_path = ROOT / config["video"]["watermark"]
    if not wm_path.exists():
        return None
    wm = Image.open(wm_path).convert("RGBA")
    wm.thumbnail((110, 110), Image.LANCZOS)
    return wm


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


# ── Sprite actor ───────────────────────────────────────────────────────────────

class SpriteActor:
    """One sprite on screen with its position and animation type."""

    ANIMATIONS = ["bounce", "sway", "pulse", "spin", "float"]

    def __init__(
        self,
        image: Image.Image,
        x: float,
        y: float,
        size: int,
        animation: Optional[str],
        appear_at: float,
        disappear_at: float,
        bpm: float,
    ):
        self.orig = image
        self.x = x
        self.y = y
        self.size = size
        self.animation = animation or random.choice(self.ANIMATIONS)
        self.appear_at = appear_at
        self.disappear_at = disappear_at
        self.beat_freq = bpm / 60.0
        self.phase = random.uniform(0, 2 * math.pi)
        # For float animation
        self.float_vx = random.choice([-1, 1]) * random.uniform(50, 110)
        self.float_vy = random.choice([-1, 1]) * random.uniform(20, 60)
        # Cache for resized base images
        self._base: Optional[Image.Image] = None

    def _get_base(self) -> Image.Image:
        if self._base is None:
            self._base = self.orig.resize((self.size, self.size), Image.LANCZOS)
        return self._base

    def render(self, canvas: Image.Image, t: float, W: int, H: int) -> None:
        """Composite this sprite onto canvas in-place."""
        rel = t - self.appear_at
        if rel < 0:
            return
        fade_out = self.disappear_at - t
        alpha = min(1.0, rel / 0.35, fade_out / 0.35)
        if alpha <= 0:
            return

        beat = rel * self.beat_freq + self.phase

        x, y = self.x, self.y
        scale = 1.0
        angle = 0.0

        if self.animation == "bounce":
            beat_phase = abs(math.sin(math.pi * beat))
            y -= beat_phase * 50
            scale = 1.0 - 0.08 * beat_phase          # squash at bottom

        elif self.animation == "sway":
            sway = math.sin(math.pi * beat)
            x += sway * 38
            angle = sway * 13

        elif self.animation == "pulse":
            scale = 1.0 + 0.20 * abs(math.sin(math.pi * beat))

        elif self.animation == "spin":
            angle = (rel * self.beat_freq * 180) % 360

        elif self.animation == "float":
            x = (self.x + self.float_vx * rel) % (W + self.size * 2) - self.size
            y = self.y + math.sin(rel * 0.9 + self.phase) * 55

        # Get base image (LANCZOS-cached)
        img = self._get_base()

        # Scale if needed (BILINEAR is fast enough for small changes)
        final_size = max(4, int(self.size * scale))
        if final_size != self.size:
            img = img.resize((final_size, final_size), Image.BILINEAR)

        # Rotate if needed
        if abs(angle) > 1.0:
            img = img.rotate(-angle % 360, expand=True, resample=Image.BILINEAR)

        # Apply alpha fade
        if alpha < 0.98:
            r, g, b, a = img.split()
            a = a.point(lambda p: int(p * alpha))
            img = Image.merge("RGBA", (r, g, b, a))

        # Paste (center-anchored)
        px = int(x - img.width / 2)
        py = int(y - img.height / 2)
        canvas.paste(img, (px, py), img)


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

        self.sprites = load_sprites(theme)
        self.music_path = pick_music()
        self.bpm, _ = analyze_beats(self.music_path)
        self.watermark = load_watermark(config)

        # Pre-build bg color sequence and sprite schedule
        self._bg_seq = self._build_bg_sequence()
        self.actors = self._build_schedule()

        log.info(f"Actors scheduled: {len(self.actors)}")

    def _build_bg_sequence(self) -> List[Tuple[Tuple[int, int, int], float]]:
        """Returns list of (rgb_color, start_time) for background segments."""
        seq = []
        t = 0.0
        while t < self.duration:
            color = hex_to_rgb(random.choice(self.bg_colors))
            seg_dur = random.uniform(self.group_interval[0], self.group_interval[1])
            seq.append((color, t))
            t += seg_dur
        return seq

    def _get_bg_color(self, t: float) -> Tuple[int, int, int]:
        # Find last bg color that started before t
        color = self._bg_seq[0][0]
        for c, start in self._bg_seq:
            if start <= t:
                color = c
            else:
                break
        return color

    def _get_positions(self, n: int) -> List[Tuple[float, float]]:
        """Spread N sprites across the screen with jitter."""
        margin = self.sprite_size * 0.7
        positions = []
        cols = math.ceil(math.sqrt(n))
        rows = math.ceil(n / cols)
        for i in range(n):
            col = i % cols
            row = i // cols
            x = margin + (col + 0.5) * (self.W - 2 * margin) / cols
            y = self.H * 0.15 + (row + 0.5) * (self.H * 0.65) / rows
            x += random.uniform(-55, 55)
            y += random.uniform(-25, 25)
            positions.append((x, y))
        return positions

    def _build_schedule(self) -> List[SpriteActor]:
        actors = []
        t = 0.0
        while t < self.duration:
            dur = random.uniform(self.group_interval[0], self.group_interval[1])
            group_end = min(t + dur, self.duration)
            n = self.n_on_screen
            chosen = random.choices(self.sprites, k=n)
            positions = self._get_positions(n)
            for sprite, pos in zip(chosen, positions):
                appear = t + random.uniform(0, 1.5)
                actors.append(SpriteActor(
                    image=sprite,
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
        """Generate one RGB frame at time t (called by moviepy)."""
        bg_color = self._get_bg_color(t)
        canvas = Image.new("RGBA", (self.W, self.H), bg_color + (255,))

        for actor in self.actors:
            if actor.appear_at - 0.5 <= t <= actor.disappear_at + 0.5:
                actor.render(canvas, t, self.W, self.H)

        if self.watermark:
            canvas.paste(self.watermark, (self.W - self.watermark.width - 18, 18), self.watermark)

        return np.array(canvas.convert("RGB"))

    def generate(self, output_path: str) -> str:
        log.info(f"Generating: theme={self.theme}, duration={self.duration/60:.1f}min, music={self.music_path.name}")
        start_t = time.time()

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Loop audio to fill duration
        audio_clip = AudioFileClip(str(self.music_path))
        looped_audio = audio_loop(audio_clip, duration=self.duration)

        # Build video
        video = VideoClip(self.make_frame, duration=self.duration)
        video = video.set_fps(self.fps).set_audio(looped_audio)

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
    parser.add_argument("--theme", default="fruits",
                        help="Sprite theme: fruits / vegetables / animals / shapes")
    parser.add_argument("--duration", type=float, default=30,
                        help="Duration in minutes (default: 30)")
    parser.add_argument("--output", default=None,
                        help="Output MP4 path (auto-generated if omitted)")
    args = parser.parse_args()

    config = load_config()
    duration_sec = args.duration * 60

    if args.output is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = str(ROOT / "output" / f"{args.theme}_{ts}.mp4")

    gen = VideoGenerator(config, args.theme, duration_sec)
    gen.generate(args.output)
    print(f"\n✓ Video saved: {args.output}")


if __name__ == "__main__":
    main()
