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
from moviepy.editor import VideoClip, AudioFileClip, concatenate_audioclips, CompositeAudioClip
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

def _make_bounce_frames(img: Image.Image, n_frames: int = 30) -> List[Image.Image]:
    """Synthesize bounce + squish animation frames from a single static sprite."""
    frames = []
    w, h = img.size
    for i in range(n_frames):
        t = i / n_frames
        # Bounce: goes up and comes back (sine arch)
        bounce = abs(math.sin(math.pi * t))
        # Squish on landing, stretch at peak
        sy = 1.0 + 0.12 * bounce          # taller at peak
        sx = 1.0 - 0.08 * bounce          # narrower at peak
        # Slight tilt left/right
        tilt = math.sin(2 * math.pi * t) * 8

        new_w = max(1, int(w * sx))
        new_h = max(1, int(h * sy))
        frame = img.resize((new_w, new_h), Image.LANCZOS)
        if abs(tilt) > 0.5:
            frame = frame.rotate(-tilt, expand=True, resample=Image.BILINEAR)

        # Paste onto same-size canvas so all frames have identical dimensions
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ox = (w - frame.width) // 2
        oy = (h - frame.height) // 2
        canvas.paste(frame, (ox, oy), frame)
        frames.append(canvas)
    return frames


def load_animated_sprites(theme: str) -> List[Tuple[str, List[Image.Image]]]:
    """
    Returns list of (name, frames) tuples.
    Priority: theme folder > animals > fruits > ai_generated (legacy).
    """
    sprites_root = ROOT / "assets" / "sprites"

    # Build candidate dirs in priority order
    candidate_dirs = []
    theme_dir = sprites_root / theme
    if theme_dir.exists():
        candidate_dirs.append(theme_dir)

    # If theme not found or not enough sprites, try other quality dirs
    for fallback in ("animals", "fruits", "ai_generated"):
        d = sprites_root / fallback
        if d.exists() and d not in candidate_dirs:
            candidate_dirs.append(d)

    sprites = []
    for d in candidate_dirs:
        for p in sorted(d.glob("*.png")):
            img = Image.open(p).convert("RGBA")
            frames = _make_bounce_frames(img, n_frames=30)
            sprites.append((p.stem, frames))
        if sprites:
            log.info(f"Using {len(sprites)} sprites from {d.name}/")
            break

    if not sprites:
        raise FileNotFoundError(
            f"No sprites found for theme '{theme}'. Run: python scripts/download_sprites.py"
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


# ── Choreography system ────────────────────────────────────────────────────────

# Grid positions (normalized 0..1) for static-base choreographies
GRID_LAYOUTS: Dict[int, List[Tuple[float, float]]] = {
    1: [(0.50, 0.52)],
    2: [(0.27, 0.52), (0.73, 0.52)],
    3: [(0.20, 0.62), (0.50, 0.36), (0.80, 0.62)],
    4: [(0.25, 0.34), (0.75, 0.34), (0.25, 0.66), (0.75, 0.66)],
    5: [(0.50, 0.28), (0.18, 0.54), (0.82, 0.54), (0.30, 0.76), (0.70, 0.76)],
}

SWAY_DIR = [1, -1, 1, -1, 1]  # adjacent chars mirror each other

# Each entry: (choreo_name, n_chars)
# Varied number of chars per scene keeps it visually fresh
CHOREO_SEQUENCE = [
    ("grid_bounce",   4),
    ("line_h",        4),
    ("carousel",      4),
    ("grid_sway",     4),
    ("parade",        3),
    ("diagonal_in",   4),
    ("zigzag",        4),
    ("grid_bounce",   3),
    ("line_h",        5),
    ("carousel",      3),
    ("parade",        4),
    ("grid_sway",     4),
    ("zigzag",        3),
    ("diagonal_in",   4),
    ("carousel",      5),
    ("line_h",        3),
]


# ── Sprite actor ───────────────────────────────────────────────────────────────

class SpriteActor:
    """
    Animated character with full choreography.
    Position is computed per-frame based on choreo type — characters actually
    move across the screen rather than bouncing in fixed spots.
    """

    def __init__(
        self,
        name: str,
        frames: List[Image.Image],
        choreo: str,
        slot: int,
        n_slots: int,
        appear_at: float,
        disappear_at: float,
        bpm: float,
        W: int,
        H: int,
        size: int,
    ):
        self.name = name
        self.frames = frames
        self.choreo = choreo
        self.slot = slot
        self.n_slots = n_slots
        self.appear_at = appear_at
        self.disappear_at = disappear_at
        self.beat_freq = bpm / 60.0
        self.W = W
        self.H = H
        self.size = size
        self.wave_delay = slot * 0.10   # wave effect: each char 100ms behind
        self.sway_dir = SWAY_DIR[slot % len(SWAY_DIR)]
        # Precompute grid anchor for static choreos
        layout = GRID_LAYOUTS.get(n_slots, GRID_LAYOUTS[4])
        gx, gy = layout[slot % len(layout)]
        self.grid_x = gx * W
        self.grid_y = gy * H
        self._cache: Dict[int, Image.Image] = {}

    def _get_frame(self, global_t: float) -> Image.Image:
        n = len(self.frames)
        frame_idx = int((global_t - self.appear_at) * ANIM_FPS) % n
        if frame_idx not in self._cache:
            self._cache[frame_idx] = self.frames[frame_idx].resize(
                (self.size, self.size), Image.LANCZOS
            )
        return self._cache[frame_idx]

    def _compute_transform(self, rel: float) -> Tuple[float, float, float, float]:
        """Return (x, y, scale, angle) for this moment in the choreography."""
        W, H = self.W, self.H
        beat = max(0.0, rel - self.wave_delay) * self.beat_freq
        bp = abs(math.sin(math.pi * beat))   # 0..1 peaks on each beat
        x, y, scale, angle = self.grid_x, self.grid_y, 1.0, 0.0

        # ── Static grid choreos ────────────────────────────────────────────
        if self.choreo == "grid_bounce":
            y = self.grid_y - bp * 62
            scale = 1.0 + 0.09 * bp
            if bp < 0.14:
                scale -= 0.06 * (1.0 - bp / 0.14)   # squish on landing

        elif self.choreo == "grid_sway":
            s = math.sin(math.pi * beat)
            x = self.grid_x + s * self.sway_dir * 44
            angle = s * self.sway_dir * 18

        elif self.choreo == "grid_combo":
            bp2 = abs(math.sin(math.pi * beat))
            y = self.grid_y - bp2 * 45
            angle = math.sin(math.pi * beat * 2) * self.sway_dir * 12
            scale = 1.0 + 0.06 * bp2

        # ── Carousel: rotate around center ellipse ─────────────────────────
        elif self.choreo == "carousel":
            cx, cy = W * 0.50, H * 0.48
            rx = W * 0.34
            ry = H * 0.28          # taller ellipse — more visible orbit
            base_a = self.slot * (math.tau / self.n_slots)
            theta = base_a + rel * 0.50   # slightly faster rotation
            x = cx + math.cos(theta) * rx
            y = cy + math.sin(theta) * ry
            # Perspective: larger at bottom, smaller at top
            persp = 0.65 + 0.45 * (math.sin(theta) + 1) / 2
            scale = persp * (1.0 + 0.07 * bp)
            angle = math.sin(theta) * 12   # more tilt as they orbit

        # ── Parade: march left → right, looping ────────────────────────────
        elif self.choreo == "parade":
            spacing = W * 0.28
            speed = W * 0.18   # faster march: ~230 px/s on 1280px screen
            base_x = -W * 0.20 + self.slot * spacing
            x = (base_x + rel * speed) % (W * 1.4) - W * 0.20
            y = H * 0.55 - bp * 50
            scale = 1.0 + 0.06 * bp
            angle = math.sin(math.pi * beat) * self.sway_dir * 14  # lean while marching

        # ── Horizontal line: wave bounce across the row ─────────────────────
        elif self.choreo == "line_h":
            margin = W * 0.10
            span = W - 2 * margin
            x = margin + (self.slot / max(self.n_slots - 1, 1)) * span \
                if self.n_slots > 1 else W * 0.5
            y = H * 0.54 - bp * 90   # bigger bounce height
            scale = 1.0 + 0.10 * bp
            angle = math.sin(math.pi * beat * 2) * self.sway_dir * 8

        # ── Diagonal entry: slide in from corners then bounce ───────────────
        elif self.choreo == "diagonal_in":
            corners = [
                (W * 0.02, H * 0.08), (W * 0.98, H * 0.08),
                (W * 0.02, H * 0.92), (W * 0.98, H * 0.92),
            ]
            cx_px, cy_px = corners[self.slot % len(corners)]
            arrive = 1.2   # seconds to slide to position
            frac = min(1.0, rel / arrive)
            ease = 1.0 - (1.0 - frac) ** 3   # cubic ease-out
            x = cx_px + (self.grid_x - cx_px) * ease
            y = cy_px + (self.grid_y - cy_px) * ease
            if frac >= 1.0:
                extra_beat = max(0.0, rel - arrive - self.wave_delay) * self.beat_freq
                bp2 = abs(math.sin(math.pi * extra_beat))
                y -= bp2 * 65
                scale = 1.0 + 0.08 * bp2

        # ── Zigzag: each char weaves across the whole screen ────────────────
        elif self.choreo == "zigzag":
            # Characters distributed vertically, each sweeps full screen width
            margin_y = H * 0.18
            span_y = H - 2 * margin_y
            base_y = margin_y + (self.slot / max(self.n_slots - 1, 1)) * span_y \
                     if self.n_slots > 1 else H * 0.5
            freq = self.beat_freq * 0.45
            phase = self.slot * math.pi * 0.75
            # Horizontal sweep: full screen width
            x = W * 0.5 + math.sin(rel * freq * math.pi + phase) * (W * 0.42)
            # Vertical oscillation around base_y
            y = base_y + math.cos(rel * freq * math.pi * 0.6 + phase) * (H * 0.12)
            scale = 1.0 + 0.08 * bp
            angle = math.sin(rel * freq * math.pi + phase) * 18  # tilt with direction

        return x, y, scale, angle

    def render(self, canvas: Image.Image, t: float, W: int, H: int,
               name_font=None) -> None:
        rel = t - self.appear_at
        if rel < 0:
            return
        fade_out = self.disappear_at - t
        alpha = min(1.0, rel / 0.35, fade_out / 0.35)
        if alpha <= 0:
            return

        x, y, scale, angle = self._compute_transform(rel)

        img = self._get_frame(t)

        final_size = max(4, int(self.size * scale))
        if final_size != self.size:
            img = img.resize((final_size, final_size), Image.BILINEAR)

        if abs(angle) > 0.5:
            img = img.rotate(-angle, expand=True, resample=Image.BILINEAR)

        if alpha < 0.98:
            r, g, b, a = img.split()
            a = a.point(lambda p: int(p * alpha))
            img = Image.merge("RGBA", (r, g, b, a))

        px = int(x - img.width / 2)
        py = int(y - img.height / 2)
        canvas.paste(img, (px, py), img)

        if name_font and rel < 3.0 and alpha > 0.3:
            badge_alpha = min(1.0, alpha) * min(1.0, (3.0 - rel) / 0.8)
            self._draw_badge(canvas, x, py - 10, badge_alpha, name_font)

    def _draw_badge(self, canvas, cx, top_y, alpha, font):
        label = self.name.capitalize()
        dummy = ImageDraw.Draw(canvas)
        try:
            bbox = dummy.textbbox((0, 0), label, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
        except Exception:
            tw, th = len(label) * 14, 20

        pad = 10
        bw, bh = tw + pad * 2, th + pad * 2
        bx = int(cx - bw / 2)
        by = int(top_y - bh - 8)

        badge = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
        bd = ImageDraw.Draw(badge)
        bd.rounded_rectangle([0, 0, bw - 1, bh - 1], radius=bh // 2,
                              fill=(255, 255, 255, int(200 * alpha)))
        bd.text((pad, pad), label, fill=(60, 40, 100, int(240 * alpha)),
                font=font)
        canvas.paste(badge, (bx, by), badge)


# ── Text overlay ──────────────────────────────────────────────────────────────

class TextOverlay:
    """Renders animated text (letter, word) over a scene."""

    def __init__(
        self,
        text: str,
        start_sec: float,
        end_sec: float,
        W: int,
        H: int,
        font_size: int = 160,
        sub_text: str = "",
        sub_font_size: int = 72,
        color: Tuple[int, int, int] = (255, 255, 255),
    ):
        self.text      = text
        self.sub_text  = sub_text
        self.start_sec = start_sec
        self.end_sec   = end_sec
        self.W, self.H = W, H
        self.color     = color
        self.font      = self._load_font(font_size)
        self.sub_font  = self._load_font(sub_font_size)

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

    def render(self, canvas: Image.Image, t: float) -> None:
        rel = t - self.start_sec
        remaining = self.end_sec - t
        if rel < 0 or remaining < 0:
            return

        # Fade in (0.4s) and fade out (0.5s)
        alpha = min(1.0, rel / 0.4, remaining / 0.5)
        if alpha <= 0:
            return

        draw = ImageDraw.Draw(canvas)

        # Bounce-in scale
        bounce = 1.0 + max(0.0, 0.3 - rel) * 0.8  # starts big, settles to 1.0

        def draw_text_centered(draw, text, font, y, color, alpha, scale=1.0):
            try:
                bbox = draw.textbbox((0, 0), text, font=font)
            except Exception:
                bbox = (0, 0, len(text) * 20, 40)
            tw = int((bbox[2] - bbox[0]) * scale)
            th = int((bbox[3] - bbox[1]) * scale)
            x = (self.W - tw) // 2
            # Draw shadow
            shadow_a = int(160 * alpha)
            draw.text((x + 4, y + 4), text, font=font,
                      fill=(0, 0, 0, shadow_a))
            # Draw main text
            r, g, b = color
            draw.text((x, y), text, font=font,
                      fill=(r, g, b, int(255 * alpha)))

        # Main letter/text - positioned in upper third
        draw_text_centered(draw, self.text, self.font,
                           int(self.H * 0.08), self.color, alpha, bounce)

        # Sub text (word) - below center
        if self.sub_text:
            draw_text_centered(draw, self.sub_text, self.sub_font,
                               int(self.H * 0.78), (255, 255, 200), alpha)


# ── Video generator ────────────────────────────────────────────────────────────

class VideoGenerator:
    def __init__(self, config: dict, theme: str, duration_sec: float,
                 script_scenes: Optional[list] = None):
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
        self.bpm, self._beat_times = analyze_beats(self.audio)

        self.font = self._load_font(32)
        self._bg_seq = self._build_bg_sequence()
        self.actors = self._build_schedule(script_scenes)
        self.overlays = self._build_overlays(script_scenes)
        self._vo_clips = self._build_voiceover(script_scenes)
        if self._vo_clips:
            from moviepy.editor import CompositeAudioClip
            self.audio = CompositeAudioClip([self.audio] + self._vo_clips)
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

    def _build_schedule(self, script_scenes: Optional[list] = None) -> List[SpriteActor]:
        """
        Build actor schedule either from a YAML script or from CHOREO_SEQUENCE auto-mode.
        """
        actors = []

        if script_scenes:
            # ── Script-driven mode ──────────────────────────────────────
            char_map = {name: frames for name, frames in self.char_sprites}
            for scene in script_scenes:
                t        = float(scene["start_sec"])
                dur      = float(scene["duration"])
                choreo   = scene["choreo"]
                n        = int(scene.get("n", 4))
                entry    = scene.get("entry", "cascade")
                names    = scene.get("chars", [])[:n]
                group_end = t + dur

                if not names:
                    continue  # skip if no chars assigned

                for slot, char_name in enumerate(names):
                    frames = char_map.get(char_name)
                    if frames is None:
                        # Fallback: pick any available char
                        frames = self.char_sprites[slot % len(self.char_sprites)][1]

                    if entry == "together":
                        appear = t
                    elif entry == "left_to_right":
                        appear = t + slot * 0.20
                    else:  # cascade (default)
                        appear = t + slot * 0.25

                    actors.append(SpriteActor(
                        name=char_name, frames=frames,
                        choreo=choreo, slot=slot, n_slots=n,
                        appear_at=appear, disappear_at=group_end,
                        bpm=self.bpm, W=self.W, H=self.H, size=self.sprite_size,
                    ))
        else:
            # ── Auto mode (CHOREO_SEQUENCE) ─────────────────────────────
            t = 0.0
            choreo_pos = 0
            char_pool = list(range(len(self.char_sprites)))
            random.shuffle(char_pool)
            pool_pos = 0

            while t < self.duration:
                choreo, n = CHOREO_SEQUENCE[choreo_pos % len(CHOREO_SEQUENCE)]
                choreo_pos += 1

                dur = random.uniform(self.group_interval[0], self.group_interval[1])
                if choreo in ("carousel", "parade", "zigzag"):
                    dur *= 1.5
                group_end = min(t + dur, self.duration)

                chosen_idx = []
                for _ in range(n):
                    if pool_pos >= len(char_pool):
                        random.shuffle(char_pool)
                        pool_pos = 0
                    chosen_idx.append(char_pool[pool_pos])
                    pool_pos += 1

                for slot, char_i in enumerate(chosen_idx):
                    name, frames = self.char_sprites[char_i]
                    appear = t + slot * 0.25
                    actors.append(SpriteActor(
                        name=name, frames=frames,
                        choreo=choreo, slot=slot, n_slots=n,
                        appear_at=appear, disappear_at=group_end,
                        bpm=self.bpm, W=self.W, H=self.H, size=self.sprite_size,
                    ))
                t = group_end

        return actors

    def _build_overlays(self, script_scenes: Optional[list]) -> List[TextOverlay]:
        """Build text overlays from scene text/label fields."""
        if not script_scenes:
            return []
        overlays = []
        for scene in script_scenes:
            text = scene.get("text", "")
            sub  = scene.get("sub_text", "")
            if not text:
                continue
            t     = float(scene["start_sec"])
            dur   = float(scene["duration"])
            overlays.append(TextOverlay(
                text=text, sub_text=sub,
                start_sec=t, end_sec=t + dur,
                W=self.W, H=self.H,
            ))
        return overlays

    def _build_voiceover(self, script_scenes: Optional[list]) -> list:
        """Build voiceover AudioFileClips from scene voiceover_key fields."""
        if not script_scenes:
            return []
        import sys as _sys
        _sys.path.insert(0, str(ROOT / "scripts"))
        from generate_voiceover import slugify, WORD_PHRASES, PACKS
        from moviepy.editor import AudioFileClip as AFC
        clips = []
        for scene in script_scenes:
            vo_key = scene.get("voiceover_key", "")
            if not vo_key:
                continue
            lang   = scene.get("voiceover_lang", "en")
            t      = float(scene["start_sec"])
            vo_dir = ROOT / "assets" / "audio" / "voiceover" / lang
            text   = WORD_PHRASES.get(vo_key) or PACKS.get("abc", {}).get(vo_key) or vo_key
            slug   = slugify(text)
            mp3_path = vo_dir / f"{slug}.mp3"
            if not mp3_path.exists():
                mp3_path = vo_dir / f"{slugify(vo_key)}.mp3"
            if mp3_path.exists():
                try:
                    clip = AFC(str(mp3_path)).set_start(t + 0.5)
                    clips.append(clip)
                except Exception as e:
                    log.warning(f"Voiceover {mp3_path}: {e}")
            else:
                log.warning(f"Voiceover not found: {mp3_path}")
        return clips

    def make_frame(self, t: float) -> np.ndarray:
        bg_color = self._get_bg_color(t)
        canvas = draw_background(self.W, self.H, bg_color, t).convert("RGBA")

        # Beat flash: brief white overlay on beat hits for energy
        if self._beat_times is not None and len(self._beat_times) > 0:
            dists = np.abs(self._beat_times - t)
            nearest = float(dists.min())
            if nearest < 0.06:
                flash_alpha = int(30 * (1.0 - nearest / 0.06))
                overlay = Image.new("RGBA", (self.W, self.H),
                                    (255, 255, 255, flash_alpha))
                canvas = Image.alpha_composite(canvas, overlay)

        for actor in self.actors:
            if actor.appear_at - 0.5 <= t <= actor.disappear_at + 0.5:
                actor.render(canvas, t, self.W, self.H, name_font=self.font)

        for overlay in self.overlays:
            overlay.render(canvas, t)

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
    parser.add_argument("--theme", default="fruits")
    parser.add_argument("--duration", type=float, default=30,
                        help="Duration in minutes")
    parser.add_argument("--output", default=None)
    parser.add_argument("--script", default=None,
                        help="Path to episode script YAML (from generate_script.py)")
    args = parser.parse_args()

    config = load_config()
    script_scenes = None

    if args.script:
        script_path = Path(args.script)
        if not script_path.is_absolute():
            script_path = ROOT / script_path
        with open(script_path) as f:
            script_data = yaml.safe_load(f)
        script_scenes = script_data["scenes"]
        duration_sec = sum(s["duration"] for s in script_scenes)
        theme = script_data.get("theme", args.theme)
        log.info(f"Loaded script: {script_path.name}  "
                 f"({len(script_scenes)} scenes, {duration_sec/60:.1f} min)")
    else:
        duration_sec = args.duration * 60
        theme = args.theme

    if args.output is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = str(ROOT / "output" / f"{theme}_{ts}.mp4")

    gen = VideoGenerator(config, theme, duration_sec, script_scenes=script_scenes)
    gen.generate(args.output)
    print(f"\n Video saved: {args.output}")


if __name__ == "__main__":
    main()
