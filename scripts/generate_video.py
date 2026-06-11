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
    """Synthesize bounce + squash-and-stretch frames from a single static sprite."""
    frames = []
    w, h = img.size
    for i in range(n_frames):
        t = i / n_frames
        bounce = abs(math.sin(math.pi * t))   # 0=ground, 1=peak

        # Stretch at peak, squash on landing (volume-preserving)
        sy = 0.84 + 0.31 * bounce             # 0.84 → 1.15 (tall at peak)
        sx = 1.17 - 0.27 * bounce             # 1.17 → 0.90 (narrow at peak)

        # Extra squash impulse on landing (t near 0 or 1)
        landing = max(0.0, 1.0 - abs(math.sin(math.pi * t)) / 0.18)
        sy -= 0.10 * landing
        sx += 0.08 * landing

        # Slight tilt — leans into the motion
        tilt = math.sin(2 * math.pi * t) * 10

        new_w = max(1, int(w * sx))
        new_h = max(1, int(h * sy))
        frame = img.resize((new_w, new_h), Image.LANCZOS)
        if abs(tilt) > 0.5:
            frame = frame.rotate(-tilt, expand=True, resample=Image.BILINEAR)

        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        ox = (w - frame.width) // 2
        oy = (h - frame.height) // 2
        canvas.paste(frame, (ox, oy), frame)
        frames.append(canvas)
    return frames


def _load_spritesheet(path: Path, frame_size: int = 512) -> List[Image.Image]:
    """Load a horizontal sprite sheet (N frames side by side) into a list of frames."""
    sheet = Image.open(path).convert("RGBA")
    n_frames = sheet.width // frame_size
    frames = []
    for i in range(n_frames):
        frame = sheet.crop((i * frame_size, 0, (i + 1) * frame_size, frame_size))
        frames.append(frame)
    return frames


def load_animated_sprites(theme: str, config: dict = None) -> List[Tuple[str, List[Image.Image]]]:
    """
    Returns list of (name, frames) tuples.
    Prefers spritesheets/ (8 semantic frames) over sprites_new/ (generates 30 bounce frames).
    """
    sheets_dir = ROOT / "assets" / "spritesheets"
    sprites_dir_name = (config or {}).get("animation", {}).get("sprites_dir", "assets/sprites_new")
    sprites_new = ROOT / sprites_dir_name
    sprites_old = ROOT / "assets" / "sprites"

    # 1. Try spritesheets/ first (pre-generated semantic frames)
    for theme_key in (theme, "animals", "fruits", "vegetables"):
        sheet_dir = sheets_dir / theme_key
        if not sheet_dir.exists():
            continue
        pngs = sorted(sheet_dir.glob("*.png"))
        if not pngs:
            continue
        sprites = []
        for p in pngs:
            frames = _load_spritesheet(p, frame_size=512)
            if frames:
                sprites.append((p.stem, frames))
        if sprites:
            log.info(f"Loaded {len(sprites)} spritesheets from {sheet_dir} (8 semantic frames)")
            return sprites

    # 2. Fall back to sprites_new / sprites (generate bounce frames)
    for sprites_root in (sprites_new, sprites_old):
        if not sprites_root.exists():
            continue
        candidate_dirs = []
        theme_dir = sprites_root / theme
        if theme_dir.exists():
            candidate_dirs.append(theme_dir)
        for fallback in ("animals", "fruits", "vegetables", "ai_generated"):
            d = sprites_root / fallback
            if d.exists() and d not in candidate_dirs:
                candidate_dirs.append(d)
        for d in candidate_dirs:
            pngs = sorted(d.glob("*.png"))
            if not pngs:
                continue
            sprites = []
            for p in pngs:
                img = Image.open(p).convert("RGBA")
                frames = _make_bounce_frames(img, n_frames=30)
                sprites.append((p.stem, frames))
            log.info(f"Loaded {len(sprites)} sprites from {d} (bounce frames)")
            return sprites

    raise FileNotFoundError(
        f"No sprites found for theme '{theme}'. Check assets/spritesheets/ or assets/sprites_new/"
    )


# Upbeat tracks suitable for kids dance videos (min ~90 BPM, fun feel)
DANCE_TRACKS = {
    "Monkeys Spinning Monkeys.mp3",  # 144 BPM — fun, upbeat
    "Happy Happy Game Show.mp3",     # 117 BPM — cheerful
    "Merry Go.mp3",                  # 129 BPM — playful carousel
    "Quirky Dog.mp3",                # 123 BPM — bouncy
    "Pinball Spring.mp3",            # 117 BPM — energetic
    "Hyperfun.mp3",                  # 99 BPM — light and fun
    "Carefree.mp3",                  # 96 BPM — warm and gentle
    "Wholesome.mp3",                 # gentle, cozy
    "Heartwarming.mp3",              # soft and sweet
    "Fluffing a Duck.mp3",           # 96 BPM — playful, fun
    "George Street Shuffle.mp3",     # 110 BPM — shuffling fun
    "Pixelland.mp3",                 # 120 BPM — game-like, upbeat
    "Overworld.mp3",                 # 120 BPM — adventure, fun
    "Circus of Freaks.mp3",          # 120 BPM — circus fun
}


def build_audio(duration_sec: float, dance_only: bool = True) -> AudioFileClip:
    """Assemble a non-repeating audio track by chaining upbeat kids music."""
    music_dirs = [
        ROOT / "assets" / "music" / "kevin",
        ROOT / "assets" / "music",
    ]
    all_tracks = []
    for d in music_dirs:
        if d.exists():
            all_tracks += list(d.glob("*.mp3")) + list(d.glob("*.wav"))
    all_tracks = list({str(p): p for p in all_tracks}.values())

    if dance_only:
        # Use only upbeat dance-friendly tracks
        tracks = [p for p in all_tracks if p.name in DANCE_TRACKS]
        if not tracks:
            tracks = all_tracks  # fallback to all if none match
    else:
        tracks = all_tracks

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
    """Light pastel background — TutiTuTV style: clean, bright, minimal."""
    img = Image.new("RGB", (W, H), color)
    draw = ImageDraw.Draw(img)

    # Very subtle gradient — just 8% darker at bottom (keeps it light)
    r, g, b = color
    for y in range(H):
        ratio = y / H * 0.08
        cr = max(0, int(r - r * ratio))
        cg = max(0, int(g - g * ratio))
        cb = max(0, int(b - b * ratio))
        draw.line([(0, y), (W, y)], fill=(cr, cg, cb))

    # Soft polka dots in corners — subtle, kid-friendly decoration
    rng = random.Random(int(color[0] * 100 + color[1]))
    dot_color = tuple(max(0, int(c * 0.88)) for c in color)  # slightly darker than bg
    for _ in range(12):
        cx = rng.randint(30, W - 30)
        cy = rng.randint(30, H - 30)
        r_dot = rng.randint(12, 30)
        draw.ellipse([cx - r_dot, cy - r_dot, cx + r_dot, cy + r_dot], fill=dot_color)

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
    ("line_h",        4),
    ("carousel",      5),
    ("grid_bounce",   4),
    ("parade",        4),
    ("twist",         4),
    ("grid_sway",     5),
    ("stomp",         4),
    ("diagonal_in",   4),
    ("spin_out",      4),
    ("zigzag",        4),
    ("robot",         4),
    ("wave_sync",     5),
    ("line_h",        5),
    ("carousel",      4),
    ("parade",        5),
    ("grid_combo",    4),
    ("twist",         5),
    ("stomp",         4),
    ("spin_out",      5),
    ("wave_sync",     4),
]

# Human-readable style names shown briefly on screen
CHOREO_LABELS = {
    "grid_bounce":  "Let's Jump!",
    "line_h":       "Dance Line!",
    "carousel":     "Round & Round!",
    "grid_sway":    "Wiggle Time!",
    "parade":       "March March!",
    "diagonal_in":  "Surprise!",
    "zigzag":       "Zig Zag!",
    "grid_combo":   "Party Mix!",
    "twist":        "Twist!",
    "stomp":        "Stomp It!",
    "spin_out":     "Spin!",
    "robot":        "Robot Dance!",
    "wave_sync":    "Wave Dance!",
    "solo_bounce":  "Bounce!",
    "solo_sway":    "Wiggle!",
    "solo_spin":    "Spin!",
    "solo_wave":    "Wave!",
    "solo_jump":    "Jump!",
    "solo_twist":   "Twist!",
    "solo_nod":     "Nod!",
    "solo_shimmy":  "Shimmy!",
}


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

    # Spritesheet frame indices (from generate_spritesheets.py):
    # 0=normal  1=squash  2=stretch  3=big  4=lean-L  5=lean-R  6=tilt-L  7=tilt-R
    _FRAME_NORMAL  = 0
    _FRAME_SQUASH  = 1
    _FRAME_STRETCH = 2
    _FRAME_BIG     = 3
    _FRAME_LEAN_L  = 4
    _FRAME_LEAN_R  = 5
    _FRAME_TILT_L  = 6
    _FRAME_TILT_R  = 7

    def _get_semantic_frame(self, rel: float) -> int:
        """Choose which spritesheet frame fits the current choreography state."""
        beat = max(0.0, rel - self.wave_delay) * self.beat_freq
        bp   = abs(math.sin(math.pi * beat))   # 0..1 pulse
        s    = math.sin(math.pi * beat)         # -1..1 signed

        choreo = self.choreo
        if choreo == "solo_bounce" or choreo == "grid_bounce" or choreo == "stomp":
            if bp > 0.7:
                return self._FRAME_STRETCH  # rising / at peak
            elif bp < 0.15:
                return self._FRAME_SQUASH   # landing
            return self._FRAME_NORMAL

        elif choreo in ("solo_sway", "grid_sway", "solo_shimmy"):
            if s < -0.3:
                return self._FRAME_LEAN_L
            elif s > 0.3:
                return self._FRAME_LEAN_R
            return self._FRAME_NORMAL

        elif choreo in ("solo_jump", "line_h"):
            if bp > 0.6:
                return self._FRAME_STRETCH
            elif bp < 0.2:
                return self._FRAME_SQUASH
            return self._FRAME_NORMAL

        elif choreo in ("solo_twist", "twist"):
            if s < -0.3:
                return self._FRAME_TILT_L
            elif s > 0.3:
                return self._FRAME_TILT_R
            return self._FRAME_NORMAL

        elif choreo in ("solo_spin", "spin_out"):
            phase = (rel * self.beat_freq * 2) % 1.0
            if phase < 0.25:
                return self._FRAME_TILT_L
            elif phase < 0.5:
                return self._FRAME_TILT_R
            elif phase < 0.75:
                return self._FRAME_LEAN_L
            return self._FRAME_LEAN_R

        elif choreo == "solo_nod":
            return self._FRAME_SQUASH if bp > 0.5 else self._FRAME_NORMAL

        elif choreo == "solo_wave" or choreo == "wave_sync":
            return self._FRAME_BIG if bp > 0.6 else self._FRAME_NORMAL

        elif choreo == "robot":
            beat_t  = max(0, rel - self.wave_delay) * self.beat_freq
            snap    = int(beat_t) % 4
            return [self._FRAME_NORMAL, self._FRAME_LEAN_R,
                    self._FRAME_BIG,    self._FRAME_LEAN_L][snap]

        return self._FRAME_NORMAL

    def _get_frame(self, global_t: float) -> Image.Image:
        n = len(self.frames)
        # 8-frame spritesheets: pick semantically correct frame for the choreo
        if n == 8:
            rel = global_t - self.appear_at
            frame_idx = self._get_semantic_frame(rel)
        else:
            frame_idx = int((global_t - self.appear_at) * ANIM_FPS) % n
        frame_idx = max(0, min(frame_idx, n - 1))
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
            margin_y = H * 0.18
            span_y = H - 2 * margin_y
            base_y = margin_y + (self.slot / max(self.n_slots - 1, 1)) * span_y \
                     if self.n_slots > 1 else H * 0.5
            freq = self.beat_freq * 0.45
            phase = self.slot * math.pi * 0.75
            x = W * 0.5 + math.sin(rel * freq * math.pi + phase) * (W * 0.42)
            y = base_y + math.cos(rel * freq * math.pi * 0.6 + phase) * (H * 0.12)
            scale = 1.0 + 0.08 * bp
            angle = math.sin(rel * freq * math.pi + phase) * 18

        # ── Twist: hips sway hard left-right, big rotation ───────────────────
        elif self.choreo == "twist":
            layout = GRID_LAYOUTS.get(self.n_slots, GRID_LAYOUTS[4])
            gx, gy = layout[self.slot % len(layout)]
            x = gx * W
            s = math.sin(math.pi * 2 * self.beat_freq * max(0, rel - self.wave_delay))
            y = gy * H - abs(s) * 40
            angle = s * 35          # big hip rotation
            scale = 1.0 + 0.06 * abs(s)

        # ── Stomp: heavy bounce with squash on landing ────────────────────────
        elif self.choreo == "stomp":
            layout = GRID_LAYOUTS.get(self.n_slots, GRID_LAYOUTS[4])
            gx, gy = layout[self.slot % len(layout)]
            x = gx * W
            beat_t = max(0, rel - self.wave_delay) * self.beat_freq
            phase_t = beat_t % 1.0
            # Fast drop, slow rise
            if phase_t < 0.25:
                rise = 1.0 - (phase_t / 0.25)
            else:
                rise = (phase_t - 0.25) / 0.75
            y = gy * H - rise * 90
            # Squash on land (bottom), stretch at peak
            scale = 1.0 + 0.15 * rise - 0.10 * (1.0 - rise)
            angle = 0.0

        # ── Spin out: characters spin continuously + orbit ────────────────────
        elif self.choreo == "spin_out":
            cx, cy = W * 0.5, H * 0.5
            rx = W * 0.30
            ry = H * 0.22
            base_a = self.slot * (math.tau / self.n_slots)
            theta = base_a + rel * 0.70
            x = cx + math.cos(theta) * rx
            y = cy + math.sin(theta) * ry
            angle = rel * 180 % 360   # full spin
            persp = 0.70 + 0.40 * (math.sin(theta) + 1) / 2
            scale = persp * (1.0 + 0.05 * bp)

        # ── Robot: stiff jerky mechanical movement ────────────────────────────
        elif self.choreo == "robot":
            layout = GRID_LAYOUTS.get(self.n_slots, GRID_LAYOUTS[4])
            gx, gy = layout[self.slot % len(layout)]
            beat_t = max(0, rel - self.wave_delay) * self.beat_freq
            # Snap to beat: quantize movement
            beat_int = int(beat_t)
            snap = beat_int % 4
            x_offsets = [0, 30, 0, -30]
            y_offsets = [-40, 0, -40, 0]
            x = gx * W + x_offsets[snap]
            y = gy * H + y_offsets[snap]
            angle = [0, 15, 0, -15][snap]
            scale = [1.05, 0.95, 1.05, 0.95][snap]

        # ── Wave sync: flowing wave across all characters ─────────────────────
        elif self.choreo == "wave_sync":
            margin = W * 0.10
            span = W - 2 * margin
            x = margin + (self.slot / max(self.n_slots - 1, 1)) * span \
                if self.n_slots > 1 else W * 0.5
            wave_phase = rel * self.beat_freq * math.pi - self.slot * 0.6
            y = H * 0.55 - abs(math.sin(wave_phase)) * 110
            scale = 1.0 + 0.12 * abs(math.sin(wave_phase))
            angle = math.sin(wave_phase) * 12

        # ══ SOLO choreographies (1 large character, TutiTuTV style) ═══════════

        elif self.choreo == "solo_bounce":
            x = W * 0.5
            y = H * 0.52 - bp * 80
            scale = 1.0 + 0.10 * bp
            if bp < 0.15:
                scale -= 0.08 * (1.0 - bp / 0.15)  # squash on land
            angle = math.sin(math.pi * beat * 2) * 6

        elif self.choreo == "solo_sway":
            s = math.sin(math.pi * beat)
            x = W * 0.5 + s * 60
            y = H * 0.52 - abs(s) * 20
            angle = s * 22
            scale = 1.0 + 0.05 * abs(s)

        elif self.choreo == "solo_spin":
            x = W * 0.5
            y = H * 0.52 - bp * 40
            angle = rel * 90 % 360
            scale = 1.0 + 0.08 * bp

        elif self.choreo == "solo_wave":
            x = W * 0.5 + math.sin(rel * self.beat_freq * math.pi * 0.7) * 30
            pulse = abs(math.sin(math.pi * beat))
            y = H * 0.52 - pulse * 60
            scale = 1.0 + 0.14 * pulse
            angle = math.sin(math.pi * beat) * 10

        elif self.choreo == "solo_jump":
            beat_t = max(0, rel) * self.beat_freq
            phase_t = beat_t % 1.0
            # Quick jump: fast up, slow float down
            if phase_t < 0.35:
                h = math.sin(math.pi * phase_t / 0.35)
            else:
                h = math.sin(math.pi * 0.35 / 0.35) * (1.0 - (phase_t - 0.35) / 0.65)
            h = max(0.0, h)
            x = W * 0.5
            y = H * 0.52 - h * 130
            scale = 1.0 + 0.12 * h
            angle = math.sin(phase_t * math.pi * 2) * 8

        elif self.choreo == "solo_twist":
            s = math.sin(math.pi * 2 * self.beat_freq * rel)
            x = W * 0.5
            y = H * 0.52 - abs(s) * 30
            angle = s * 40
            scale = 1.0 + 0.07 * abs(s)

        elif self.choreo == "solo_nod":
            # Forward nod: scale Y squish + slight drop
            nod = abs(math.sin(math.pi * beat))
            x = W * 0.5
            y = H * 0.52 + nod * 25
            scale = 1.0 - 0.08 * nod
            angle = 0.0

        elif self.choreo == "solo_shimmy":
            # Fast side vibration — double beat frequency
            fast = abs(math.sin(math.pi * beat * 2))
            s = math.sin(math.pi * beat * 2)
            x = W * 0.5 + s * 35
            y = H * 0.52 - fast * 25
            angle = s * 12
            scale = 1.0 + 0.05 * fast

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

        # Drop shadow: drawn at grid_y (ground), squashes as character rises
        ground_y = self.grid_y
        height_above = max(0.0, ground_y - y)
        if height_above > 2:
            rise_norm = min(1.0, height_above / (self.size * 0.6))
            sw = max(4, int(final_size * 0.62 * (1.0 - rise_norm * 0.35)))
            sh = max(2, int(sw * 0.22))
            sh_alpha = int(80 * alpha * (1.0 - rise_norm * 0.55))
            shadow = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
            sd = ImageDraw.Draw(shadow)
            for row in range(sh):
                fade = 1.0 - (row / max(sh - 1, 1)) ** 0.5
                a_row = int(sh_alpha * fade * 0.9)
                sd.line([(0, row), (sw, row)], fill=(0, 0, 0, a_row))
            sx_pos = int(x - sw / 2)
            sy_pos = int(ground_y + final_size * 0.08)
            if 0 <= sx_pos < W and 0 <= sy_pos < H:
                canvas.paste(shadow, (sx_pos, sy_pos), shadow)

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

    @staticmethod
    def _has_arabic(text: str) -> bool:
        return any('؀' <= c <= 'ۿ' for c in text)

    @staticmethod
    def _shape_arabic(text: str) -> str:
        try:
            import arabic_reshaper
            from bidi.algorithm import get_display
            return get_display(arabic_reshaper.reshape(text))
        except ImportError:
            return text

    def _load_font(self, size: int):
        candidates = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        ]
        ar_font = str(Path(__file__).resolve().parent.parent /
                      "remotion/public/fonts/NotoSansArabic-Bold.ttf")
        if self._has_arabic(self.text) or self._has_arabic(self.sub_text):
            candidates = [ar_font] + candidates
        for path in candidates:
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
        main_text = self._shape_arabic(self.text) if self._has_arabic(self.text) else self.text
        draw_text_centered(draw, main_text, self.font,
                           int(self.H * 0.08), self.color, alpha, bounce)

        # Sub text (word) - below center
        if self.sub_text:
            sub = self._shape_arabic(self.sub_text) if self._has_arabic(self.sub_text) else self.sub_text
            draw_text_centered(draw, sub, self.sub_font,
                               int(self.H * 0.78), (255, 255, 200), alpha)


# ── Video generator ────────────────────────────────────────────────────────────

class VideoGenerator:
    def __init__(self, config: dict, theme: str, duration_sec: float,
                 script_scenes: Optional[list] = None,
                 shorts: bool = False):
        self.cfg = config
        self.theme = theme
        self.duration = duration_sec
        self.shorts = shorts
        if shorts:
            self.W, self.H = 720, 1280   # 9:16 vertical for YouTube Shorts
        else:
            self.W, self.H = config["video"]["resolution"]
        self.fps = config["video"]["fps"]
        self.sprite_size = config["animation"]["sprite_size"] if not shorts else 200
        self.n_on_screen = config["animation"]["sprites_on_screen"]
        self.bg_colors = config["video"]["background_colors"]
        self.group_interval = config["animation"]["group_change_interval"]

        self.char_sprites = load_animated_sprites(theme, config)
        self.audio = build_audio(duration_sec)
        self.bpm, self._beat_times = analyze_beats(self.audio)

        self.font = self._load_font(32)
        self._bg_seq = self._build_bg_sequence()
        self._scene_colors = self._build_scene_colors(script_scenes)
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

    def _build_scene_colors(self, script_scenes: Optional[list]) -> List[Tuple[float, float, Tuple[int,int,int]]]:
        """Build list of (start, end, rgb) from scenes that have bg_color."""
        if not script_scenes:
            return []
        result = []
        for scene in script_scenes:
            if "bg_color" not in scene:
                continue
            start = float(scene["start_sec"])
            end   = start + float(scene["duration"])
            rgb   = hex_to_rgb(scene["bg_color"])
            result.append((start, end, rgb))
        return result

    def _get_bg_color(self, t: float) -> Tuple[int, int, int]:
        # Per-scene color takes priority over random sequence
        for start, end, rgb in self._scene_colors:
            if start <= t < end:
                return rgb
        # Fall back to random sequence
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

                    if entry in ("together", "zoom_in"):
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

            # Search all packs first (gives full phrase text like "A. Apple. A is for Apple.")
            text = None
            for pack in PACKS.values():
                if vo_key in pack:
                    text = pack[vo_key]
                    break
            if not text:
                text = WORD_PHRASES.get(vo_key, vo_key)

            slug = slugify(text)
            mp3_path = vo_dir / f"{slug}.mp3"
            if not mp3_path.exists():
                # fallback: just the key itself
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
    parser.add_argument("--shorts", action="store_true",
                        help="Generate vertical 9:16 YouTube Short (720x1280)")
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
        suffix = "_short" if args.shorts else ""
        args.output = str(ROOT / "output" / f"{theme}{suffix}_{ts}.mp4")

    gen = VideoGenerator(config, theme, duration_sec,
                         script_scenes=script_scenes, shorts=args.shorts)
    gen.generate(args.output)
    print(f"\n Video saved: {args.output}")


if __name__ == "__main__":
    main()
