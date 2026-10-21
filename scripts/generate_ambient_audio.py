#!/usr/bin/env python3
"""
Sacred Drift — procedural ambient / meditation music generator (pure code, no AI, no samples).

Every track is synthesised from scratch (numpy/scipy): wavetable pads with slow chord
progressions and key changes, singing bowls, gongs, bells, drones, rain, "air" beds,
stereo hall reverb. A seed fully determines the track, so any file can be re-created and
its authorship proven (the parameters go to ambient_log.jsonl next to the audio).

Rendering is streamed in 30-second chunks (reverb tail and filter state carried over),
so memory stays flat from 1 minute to 8+ hours. Output goes straight to ffmpeg.

Styles:
  bowls      Tibetan singing bowls + soft pad + occasional deep gong
  cosmic     dark sus/lydian pads, distant "star" pings, wide reverb
  sleep      very dark, slow, low drone, sparse low bowls, quieter master
  solfeggio  pure tone at --hz (default 528) over a pad tuned to that tone
  rain       warm major pad + procedural rain (+ rare distant thunder)
  morning    bright major pad, pentatonic bells and soft plucks

Usage:
  python3 scripts/generate_ambient_audio.py --list-styles
  python3 scripts/generate_ambient_audio.py --style bowls --minutes 12 --count 4
  python3 scripts/generate_ambient_audio.py --style solfeggio --hz 432 --minutes 60
  python3 scripts/generate_ambient_audio.py --style sleep --minutes 480 --format flac   # 8 h
  python3 scripts/generate_ambient_audio.py --style cosmic --seconds 90 --out-dir /tmp  # preview
  python3 scripts/generate_ambient_audio.py --style solfeggio --hz 174 --register -12      # low, deep pad
  python3 scripts/generate_ambient_audio.py --style solfeggio --hz 432 --binaural 4         # theta beat, headphones
  python3 scripts/generate_ambient_audio.py --style rain --rain outside                     # open-air rain

Variety: every seed draws its own recipe — key, chord progression, chord length, pad timbre
(soft/dark/warm/hollow/glass), optional layers (gong, chimes, choir, waves, shimmer, plucks,
thunder…), reverb size and event pace. The recipe is logged, and a new track is re-rolled if it
matches one of the last 8 tracks of the same style (disable with --allow-repeat).

Files are named "<Title> (<seed>).mp3" with the category keywords generate_sd_compilation.py
looks for (tibetan / cosmic / sleep music / 528hz solfeggio / rain / yoga flow) and are
written to sacred_drift/audio/code_ambient/ by default.
"""
from __future__ import annotations

import argparse
import datetime
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt, sosfilt_zi

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "sacred_drift" / "audio" / "code_ambient"
SR = 44100
CHUNK_S = 30
VERSION = "1.1"

# ── basic music helpers ───────────────────────────────────────────────────────

CHORD_TYPES = {                       # voicings, semitones above chord root
    "m9":      [0, 7, 10, 14, 15],
    "maj9":    [0, 7, 11, 14, 16],
    "69":      [0, 7, 9, 14, 16],
    "sus2":    [0, 7, 12, 14, 19],
    "maj7#11": [0, 7, 11, 16, 18],
    "m11":     [0, 7, 10, 15, 17],
}
PROGRESSIONS = {                      # (offset from key root, chord type)
    "minor":  [[(0, "m9"), (-4, "maj9"), (3, "maj9"), (-2, "69")],
               [(0, "m9"), (5, "m9"), (-4, "maj9"), (-2, "69")],
               [(0, "m9"), (5, "69"), (0, "m11"), (-2, "maj9")]],
    "major":  [[(0, "maj9"), (5, "maj9"), (-3, "m9"), (7, "sus2")],
               [(0, "maj9"), (-3, "m9"), (5, "maj9"), (2, "m9")],
               [(0, "69"), (5, "maj7#11"), (0, "maj9"), (7, "sus2")]],
    "cosmic": [[(0, "sus2"), (-4, "maj7#11"), (-2, "sus2"), (3, "maj7#11")],
               [(0, "m11"), (-4, "maj7#11"), (0, "sus2"), (5, "sus2")]],
    "sleep":  [[(0, "m9"), (-4, "maj9")],
               [(0, "m11"), (5, "m9")],
               [(0, "sus2"), (-4, "maj9")]],
}
SCALES = {"minor_penta": [0, 3, 5, 7, 10], "major_penta": [0, 2, 4, 7, 9],
          "dorian": [0, 2, 3, 5, 7, 9, 10], "lydian": [0, 2, 4, 6, 7, 9, 11]}


class Tuning:
    """MIDI → Hz with an optional offset in semitones (solfeggio retunes the whole pad)."""
    def __init__(self, offset: float = 0.0):
        self.offset = offset

    def hz(self, m: float) -> float:
        return 440.0 * 2 ** ((m + self.offset - 69) / 12)


def _wavetable(harm_amps: list[float], size: int = 8192) -> np.ndarray:
    x = np.arange(size) / size
    w = sum(a * np.sin(2 * np.pi * (h + 1) * x) for h, a in enumerate(harm_amps))
    return (w / np.max(np.abs(w))).astype(np.float32)


TAB_DARK = _wavetable([1.0, 0.18, 0.05, 0.015])
TAB_WARM = _wavetable([1.0, 0.35, 0.14, 0.06, 0.02])
TAB_BRIGHT = _wavetable([1.0, 0.5, 0.28, 0.16, 0.09, 0.05, 0.03])
TAB_SOFT = _wavetable([1.0, 0.08])
TAB_HOLLOW = _wavetable([1.0, 0.0, 0.33, 0.0, 0.18, 0.0, 0.10])          # clarinet-like, odd harmonics
TAB_GLASS = _wavetable([1.0, 0.04, 0.42, 0.02, 0.22, 0.0, 0.11, 0.0, 0.05])
# pad timbre = crossfade between two tables driven by a slow "brightness" LFO
TIMBRES = {"soft": (TAB_SOFT, TAB_DARK), "dark": (TAB_DARK, TAB_WARM), "warm": (TAB_WARM, TAB_BRIGHT),
           "hollow": (TAB_SOFT, TAB_HOLLOW), "glass": (TAB_DARK, TAB_GLASS)}


def pick(rng, options):
    return options[int(rng.integers(len(options)))]


def wt(phase_cycles: np.ndarray, tab: np.ndarray) -> np.ndarray:
    idx = ((phase_cycles % 1.0) * len(tab)).astype(np.int64)
    return tab[idx]


# ── events: a sound with a start, a length and a function of local time ──────

@dataclass
class Event:
    start: float
    length: float
    fn: Callable[[np.ndarray], np.ndarray]     # tt (s from event start, float64) → mono float32
    pan: float = 0.0
    gain: float = 1.0
    wet: float = 1.0                           # reverb send multiplier

    @property
    def end(self):
        return self.start + self.length


@dataclass
class Score:
    events: list[Event]
    beds: list = field(default_factory=list)   # callables (c0, c1) -> (L, R) for continuous noise beds
    reverb_s: float = 5.5
    reverb_lp: float = 5000
    dry: float = 0.55
    wet: float = 0.75
    band: tuple = (35, 14000)
    target_lufs: float = -18.0
    params: dict = field(default_factory=dict)


def env_swell(tt, length):
    return (np.sin(np.pi * np.clip(tt / length, 0, 1)) ** 2).astype(np.float32)


def pad_voice(f, length, rng, tab_a=TAB_DARK, tab_b=TAB_WARM, detune=0.0025, bright_period=None):
    vib_r = rng.uniform(0.07, 0.18); vib_d = 0.0012; ph = rng.uniform(0, 1)
    br_p = bright_period or rng.uniform(25, 60); br_ph = rng.uniform(0, 6.28)

    def fn(tt):
        out = np.zeros(len(tt), np.float32)
        for d in (-detune, detune):
            fd = f * (1 + d)
            cyc = fd * tt + fd * vib_d * np.sin(2 * np.pi * vib_r * tt) / (2 * np.pi * vib_r) + ph
            b = (0.5 + 0.5 * np.sin(2 * np.pi * tt / br_p + br_ph)).astype(np.float32)
            out += (1 - b) * wt(cyc, tab_a) + b * wt(cyc, tab_b)
        return out * env_swell(tt, length)
    return fn


def bowl(f0, rng, length=24.0, partials=((1.0, 1.0, 9.0), (2.76, 0.5, 6.0), (5.40, 0.22, 3.5), (8.93, 0.10, 2.0))):
    beats = [rng.uniform(0.5, 1.4) for _ in partials]

    def fn(tt):
        s = np.zeros(len(tt))
        for (ratio, amp, dec), bt in zip(partials, beats):
            f = f0 * ratio
            s += amp * np.exp(-tt / dec) * (np.sin(2 * np.pi * f * tt) + 0.7 * np.sin(2 * np.pi * (f + bt) * tt))
        return (s * (1 - np.exp(-tt / 0.012))).astype(np.float32)     # soft mallet, no click
    return fn


def gong(f0, rng, length=30.0):
    ratios = [1.0, 1.47, 2.09, 2.76, 3.52, 4.21, 5.39]
    amps = [1.0, 0.7, 0.5, 0.35, 0.22, 0.14, 0.08]
    decs = [16, 12, 9, 7, 5, 4, 3]
    jitter = [rng.uniform(0.99, 1.01) for _ in ratios]

    def fn(tt):
        s = np.zeros(len(tt))
        for r, a, d, j in zip(ratios, amps, decs, jitter):
            s += a * np.exp(-tt / d) * np.sin(2 * np.pi * f0 * r * j * tt + 0.3 * np.sin(2 * np.pi * 0.4 * tt))
        swell = 1 - np.exp(-tt / 1.2)                     # soft mallet swell
        return (s * swell).astype(np.float32)
    return fn


def bell(f, length=6.0, decay=2.2):
    def fn(tt):
        s = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * f * 2.0 * tt) * np.exp(-tt / 0.8)
             + 0.12 * np.sin(2 * np.pi * f * 3.01 * tt) * np.exp(-tt / 0.4))
        return (s * np.exp(-tt / decay) * (1 - np.exp(-tt / 0.003))).astype(np.float32)
    return fn


def pluck(f, length=3.5):
    def fn(tt):
        s = np.sin(2 * np.pi * f * tt) + 0.25 * np.sin(2 * np.pi * 2 * f * tt) * np.exp(-tt / 0.3)
        return (s * np.exp(-tt / 0.9) * (1 - np.exp(-tt / 0.002))).astype(np.float32)
    return fn


def star(f, length=7.0):
    def fn(tt):
        s = np.sin(2 * np.pi * f * tt + 0.8 * np.sin(2 * np.pi * f * 1.5 * tt) * np.exp(-tt / 0.5))
        return (s * np.exp(-tt / 2.8) * (1 - np.exp(-tt / 0.02))).astype(np.float32)
    return fn


def choir(f, length, rng, vowel="oo"):
    """Soft wordless 'ooh/ah' voice: harmonics shaped by vowel formants, slow vibrato."""
    formants = {"oo": [(320, 110, 1.0), (800, 180, 0.30)],
                "oh": [(480, 130, 1.0), (880, 190, 0.45)],
                "ah": [(720, 150, 1.0), (1150, 200, 0.50), (2600, 320, 0.10)]}[vowel]
    hs = np.arange(1, 25)
    amps = sum(a * np.exp(-((hs * f - fc) / bw) ** 2) for fc, bw, a in formants) + 0.02 / hs
    amps[hs * f > 9000] = 0
    tab = _wavetable(list(amps), 4096)
    vib_r = rng.uniform(4.6, 5.4); ph = rng.uniform(0, 1)

    def fn(tt):
        depth = 0.004 * np.clip(tt / 3.0, 0, 1)                       # vibrato fades in like a singer
        cyc = f * tt + f * depth * np.sin(2 * np.pi * vib_r * tt) / (2 * np.pi * vib_r) + ph
        return wt(cyc, tab) * env_swell(tt, length)
    return fn


def chimes_cluster(rng, t, root, tun, gain):
    """Wind-chime burst: 3–7 quick high pentatonic bells."""
    out, tt = [], t
    for _ in range(int(rng.integers(3, 8))):
        m = root + 36 + int(pick(rng, SCALES["major_penta"])) + int(pick(rng, [0, 0, 12]))
        out.append(Event(tt, 5, bell(tun.hz(m), decay=1.4), rng.uniform(-0.9, 0.9), gain * rng.uniform(0.5, 1.0)))
        tt += rng.uniform(0.08, 0.45)
    return out


def shimmer_arp(rng, t, root, tun, scale, gain):
    """Slow ascending arpeggio of soft 'star' tones."""
    out = []
    notes = sorted(int(x) for x in rng.choice(scale, size=min(len(scale), int(rng.integers(4, 7))), replace=False))
    for i, n in enumerate(notes):
        out.append(Event(t + i * 0.42, 8, star(tun.hz(root + 24 + n)), -0.8 + 1.6 * i / max(1, len(notes) - 1),
                         gain, wet=1.3))
    return out


def drone(freqs, length, rng):
    lfo = [rng.uniform(0.03, 0.08) for _ in freqs]; ph = [rng.uniform(0, 6.28) for _ in freqs]

    def fn(tt):
        s = np.zeros(len(tt))
        for f, r, p in zip(freqs, lfo, ph):
            s += (0.75 + 0.25 * np.sin(2 * np.pi * r * tt + p)) * (np.sin(2 * np.pi * f * tt) + 0.2 * np.sin(4 * np.pi * f * tt))
        return (s * env_swell(tt, length)).astype(np.float32)
    return fn


def thunder(rng, length=9.0):
    noise = rng.standard_normal(int(length * SR)).astype(np.float32)
    sos = butter(2, [30, 220], btype="band", fs=SR, output="sos")
    rumble = sosfilt(sos, noise).astype(np.float32)

    def fn(tt):
        i = np.clip((tt * SR).astype(np.int64), 0, len(rumble) - 1)
        e = (1 - np.exp(-tt / 0.8)) * np.exp(-tt / 2.8) * (1 + 0.5 * np.sin(2 * np.pi * 0.7 * tt))
        return (rumble[i] * e).astype(np.float32)
    return fn


# ── continuous beds (stateful across chunks) ──────────────────────────────────

class NoiseBed:
    """Band-limited stereo noise with slow breathing; filter state carried across chunks."""
    def __init__(self, rng, lo, hi, level, breathe=0.03):
        self.rng, self.level, self.breathe = rng, level, breathe
        self.sos = butter(2, [lo, hi], btype="band", fs=SR, output="sos")
        self.zi = [sosfilt_zi(self.sos) * 0, sosfilt_zi(self.sos) * 0]

    def __call__(self, c0, c1):
        n = c1 - c0
        t = np.arange(c0, c1) / SR
        amp = self.level * (0.65 + 0.35 * np.sin(2 * np.pi * self.breathe * t))
        out = []
        for ch in (0, 1):
            y, self.zi[ch] = sosfilt(self.sos, self.rng.standard_normal(n), zi=self.zi[ch])
            out.append((y * amp).astype(np.float32))
        return out[0], out[1]


class WavesBed:
    """Distant sea: low-passed noise with slow irregular swells."""
    def __init__(self, rng, level=0.02):
        self.level = level
        self.noise = NoiseBed(rng, 60, 1100, 1.0, breathe=0.0)
        self.P = rng.uniform(8, 13); self.ph = rng.uniform(0, 6.28)

    def __call__(self, c0, c1):
        t = np.arange(c0, c1) / SR
        sw = 0.5 + 0.5 * np.sin(2 * np.pi * t / self.P + self.ph + 0.7 * np.sin(2 * np.pi * t / (self.P * 3.7)))
        env = (0.15 + 0.85 * sw ** 2.2) * self.level
        l, r = self.noise(c0, c1)
        return (l * env).astype(np.float32), (r * env).astype(np.float32)


class RainBed:
    """Procedural rain; intensity drifts slowly.

    mode='inside'  (default) rain heard from inside a room: muffled wash, dull soft taps on
                   glass/roof, occasional drip on the sill — no hiss.
    mode='outside' open-air rain: brighter wash and crisp droplets."""
    def __init__(self, rng, level=None, period=420, mode="inside"):
        self.rng, self.period, self.ph, self.mode = rng, period, rng.uniform(0, 6.28), mode
        self.inside = mode == "inside"
        self.level = level if level is not None else (0.032 if self.inside else 0.05)
        k = np.arange(int(0.03 * SR)) / SR
        if self.inside:
            self.wash = NoiseBed(rng, 120, 1600, 1.0, breathe=0.0)
            self.lp = butter(2, 1400, btype="low", fs=SR, output="sos")
            self.lp_zi = [sosfilt_zi(self.lp) * 0, sosfilt_zi(self.lp) * 0]
            self.kernels = [(np.sin(2 * np.pi * f * k) * np.exp(-k / 0.006)).astype(np.float32)
                            for f in (620, 820, 1050, 1300)]
            self.drip = (np.sin(2 * np.pi * 520 * k) * np.exp(-k / 0.012)).astype(np.float32)
            self.rate = 14
        else:
            self.wash = NoiseBed(rng, 500, 7000, 1.0, breathe=0.0)
            k = k[: int(0.012 * SR)]
            self.kernels = [(np.sin(2 * np.pi * f * k) * np.exp(-k / 0.0025)).astype(np.float32)
                            for f in (2600, 3400, 4300, 5200)]
            self.rate = 28

    def __call__(self, c0, c1):
        n = c1 - c0
        t = np.arange(c0, c1) / SR
        inten = 0.7 + 0.3 * np.sin(2 * np.pi * t / self.period + self.ph)
        wl, wr = self.wash(c0, c1)
        out = []
        for ch, w in enumerate((wl, wr)):
            drops = np.zeros(n, np.float32)
            cnt = self.rng.poisson(self.rate * n / SR)
            pos = self.rng.integers(0, n, cnt)
            drops[pos] = self.rng.uniform(0.1, 1.0, cnt) ** 2
            d = sum(fftconvolve(drops * (self.rng.random(n) < 0.25), kern, mode="same")
                    for kern in self.kernels)
            if self.inside:
                dr = np.zeros(n, np.float32)
                k = self.rng.poisson(n / SR / 3.5)                   # a drip every few seconds
                dr[self.rng.integers(0, n, k)] = self.rng.uniform(0.4, 1.0, k)
                d = 0.5 * d + 0.8 * fftconvolve(dr, self.drip, mode="same")
                mix = 0.7 * w + d
                mix, self.lp_zi[ch] = sosfilt(self.lp, mix, zi=self.lp_zi[ch])   # through the window
            else:
                mix = 0.6 * w + 0.9 * d
            out.append((mix * inten * self.level).astype(np.float32))
        return out[0], out[1]


# ── harmonic plan shared by all styles ───────────────────────────────────────

@dataclass
class Section:
    start: float
    length: float
    root: int            # key root (MIDI)
    chord: list[int]     # absolute MIDI notes


def plan_harmony(rng, dur, family, seg, key_root, modulate_every=(240, 420), info=None, lo=40):
    """Chord segments of length `seg`, changing progression/key every few minutes."""
    progs = PROGRESSIONS[family]
    first = int(rng.integers(len(progs)))
    prog = progs[first]
    if info is not None:
        info.update({"family": family, "progression": first, "chord_seconds": seg})
    out, t, k, next_mod = [], 0.0, 0, rng.uniform(*modulate_every)
    root = key_root
    while t < dur + seg:
        off, typ = prog[k % len(prog)]
        cr = root + off
        while cr < lo: cr += 12
        while cr > lo + 12: cr -= 12
        out.append(Section(t, seg, root, [cr + i for i in CHORD_TYPES[typ]]))
        t += seg; k += 1
        if t >= next_mod and k % len(prog) == 0:
            root += int(rng.choice([5, -5, 7, -7, 0, 2, -2]))
            while root < lo + 3: root += 12
            while root > lo + 15: root -= 12
            prog = progs[rng.integers(len(progs))]
            next_mod = t + rng.uniform(*modulate_every)
    return out


def root_at(sections, t):
    for s in sections:
        if s.start <= t < s.start + s.length:
            return s.root
    return sections[-1].root


def density(t, period, phase, lo=0.55):
    return lo + (1 - lo) * (0.5 + 0.5 * math.sin(2 * math.pi * t / period + phase))


def pad_events(sections, rng, tun, overlap, tabs, gain, detune=0.0025, bright_period=None):
    ev = []
    for s in sections:
        ln = s.length + 2 * overlap
        for m in s.chord:
            for pan in (-0.55, 0.55):
                ev.append(Event(s.start - overlap, ln,
                                pad_voice(tun.hz(m), ln, rng, tabs[0], tabs[1], detune, bright_period),
                                pan=pan * rng.uniform(0.7, 1.0), gain=gain))
    return ev


def scattered(rng, dur, start, gaps, make, d_period=None):
    """Place events at random gaps; gaps stretch when the slow density curve is low."""
    ev, t = [], start
    ph = rng.uniform(0, 6.28)
    while t < dur - 4:
        e = make(t)
        if e:
            ev.extend(e if isinstance(e, list) else [e])
        d = density(t, d_period, ph) if d_period else 1.0
        t += rng.uniform(*gaps) / d
    return ev


# ── styles ────────────────────────────────────────────────────────────────────

TITLES = {
    "bowls":     ("Tibetan Singing Bowls", ["Temple Dawn", "Amber Sanctuary", "Hidden Monastery", "Golden Stillness",
                                            "Stone Courtyard", "Lotus Pond", "Incense Hall", "Himalayan Dusk",
                                            "Prayer Flags", "Cedar Shrine", "Valley of Echoes", "Saffron Light"]),
    "cosmic":    ("Cosmic Space Meditation", ["Nebula Glow", "Silent Orbit", "Starlit Void", "Aurora Horizon",
                                              "Distant Galaxies", "Moonlit Voyage", "Celestial Light", "Deep Field",
                                              "Interstellar Calm", "Event Horizon", "Solar Wind", "Andromeda Night"]),
    "sleep":     ("Deep Sleep Music", ["Silk Night", "Midnight Lake", "Slow Breathing", "Soft Darkness",
                                               "Dream Haven", "Gentle Snowfall", "Starless Sky", "Night Breath",
                                               "Still Water", "Lantern Dim", "Late Hour", "Warm Blanket"]),
    "solfeggio": ("{hz}Hz Solfeggio Frequency", ["Inner Calm", "Pure Tone", "Clear Mind", "Gentle Resonance",
                                                 "Calm Center", "Soft Radiance", "Still Presence", "Open Heart",
                                                 "Crystal Air", "Deep Balance"]),
    "rain":      ("Gentle Rain Meditation", ["Window Rain", "Spring Shower", "Evening Drizzle", "Rooftop Rain",
                                             "Misty Garden", "Rain on Leaves", "Cabin Rain", "Monsoon Night",
                                             "Soft Downpour", "Garden After Rain"]),
    "morning":   ("Morning Sunrise Yoga Flow", ["First Light", "Golden Hour", "Dew Fields", "Open Sky",
                                                   "Gentle Awakening", "Soft Breeze", "Warm Horizon", "New Day",
                                                   "Sun Salutation", "Clear Morning"]),
}


def _recipe(rng, timbres, layers, reverb_base):
    """Per-seed sound recipe: pad timbre, which optional layers play, reverb size."""
    on = [name for name, prob in layers.items() if rng.random() < prob]
    return {"timbre": pick(rng, timbres), "layers": on,
            "reverb_s": round(reverb_base * rng.uniform(0.8, 1.25), 2),
            "pace": round(rng.uniform(0.8, 1.25), 2)}          # >1 = events further apart


def _choir_events(sections, rng, tun, gain, every=2, vowel=None):
    ev = []
    vowel = vowel or pick(rng, ["oo", "oh", "ah"])
    for s in sections[::every]:
        ln = s.length * every + 8
        for m in sorted(s.chord)[2:5]:
            ev.append(Event(s.start - 4, ln, choir(tun.hz(m + 12), ln, rng, vowel), rng.uniform(-0.6, 0.6), gain))
    return ev


def style_bowls(rng, dur, o):
    tun = Tuning(); key = int(rng.integers(45, 52)); info = {}
    R = _recipe(rng, ["dark", "warm", "hollow", "soft"],
                {"gong": 0.75, "chimes": 0.4, "choir": 0.3, "waves": 0.15}, 6.0)
    secs = plan_harmony(rng, dur, "minor" if rng.random() < 0.7 else "major", int(pick(rng, [16, 20, 24])), key, info=info)
    ev = pad_events(secs, rng, tun, 5, TIMBRES[R["timbre"]], 0.013)
    scale = SCALES[pick(rng, ["minor_penta", "dorian"])]

    def mk_bowl(t):
        r = root_at(secs, t)
        m = r + 12 + int(pick(rng, scale)) + int(pick(rng, [0, 0, 12]))
        return Event(t, 26, bowl(tun.hz(m) * rng.uniform(0.998, 1.002), rng), rng.uniform(-0.55, 0.55), 0.10)
    ev += scattered(rng, dur, 2.5, (8 * R["pace"], 15 * R["pace"]), mk_bowl, d_period=rng.uniform(500, 900))
    if "gong" in R["layers"]:
        ev += scattered(rng, dur, rng.uniform(40, 90), (120, 260),
                        lambda t: Event(t, 32, gong(tun.hz(root_at(secs, t) - 12), rng), rng.uniform(-0.2, 0.2), 0.05))
    if "chimes" in R["layers"]:
        ev += scattered(rng, dur, rng.uniform(20, 60), (45, 110),
                        lambda t: chimes_cluster(rng, t, root_at(secs, t), tun, 0.012))
    if "choir" in R["layers"]:
        ev += _choir_events(secs, rng, tun, 0.006)
    beds = [NoiseBed(rng, 150, 900, 0.004)] + ([WavesBed(rng, 0.012)] if "waves" in R["layers"] else [])
    return Score(ev, beds, reverb_s=R["reverb_s"], reverb_lp=4800, params={"key": key, **info, "recipe": R})


def style_cosmic(rng, dur, o):
    tun = Tuning(); key = int(rng.integers(43, 50)); info = {}
    R = _recipe(rng, ["dark", "glass", "warm", "hollow"], {"shimmer": 0.5, "choir": 0.3, "drone": 0.85}, 8.5)
    secs = plan_harmony(rng, dur, "cosmic", int(pick(rng, [20, 24, 28])), key, (300, 540), info=info)
    ev = pad_events(secs, rng, tun, 7, TIMBRES[R["timbre"]], 0.012, detune=rng.uniform(0.003, 0.005), bright_period=70)
    if "drone" in R["layers"]:
        for s in secs[::2]:
            ln = 2 * s.length + 10
            ev.append(Event(s.start - 5, ln, drone([tun.hz(s.root - 12), tun.hz(s.root - 5)], ln, rng), 0, 0.05, wet=0.5))
    scale = SCALES[pick(rng, ["lydian", "major_penta", "dorian"])]
    ev += scattered(rng, dur, 6, (3 * R["pace"], 9 * R["pace"]),
                    lambda t: Event(t, 8, star(tun.hz(root_at(secs, t) + 36 + int(pick(rng, scale)) + int(pick(rng, [0, 12])))),
                                    rng.uniform(-0.9, 0.9), 0.022, wet=1.4),
                    d_period=rng.uniform(400, 800))
    if "shimmer" in R["layers"]:
        ev += scattered(rng, dur, rng.uniform(30, 70), (60, 140),
                        lambda t: shimmer_arp(rng, t, root_at(secs, t) + 12, tun, scale, 0.016))
    if "choir" in R["layers"]:
        ev += _choir_events(secs, rng, tun, 0.005, vowel="oo")
    return Score(ev, [NoiseBed(rng, 200, 2500, 0.0055, breathe=0.017)], reverb_s=R["reverb_s"], reverb_lp=6500,
                 dry=0.45, wet=0.9, params={"key": key, **info, "recipe": R})


def style_sleep(rng, dur, o):
    tun = Tuning(); key = int(rng.integers(43, 49)); info = {}
    R = _recipe(rng, ["soft", "dark", "hollow"], {"bowls": 0.6, "waves": 0.35, "choir": 0.25, "rain": 0.15}, 7.0)
    secs = plan_harmony(rng, dur, "sleep", int(pick(rng, [28, 32, 36])), key, (420, 720), info=info)
    ev = pad_events(secs, rng, tun, 9, TIMBRES[R["timbre"]], 0.012, detune=0.002)
    for s in secs:
        ln = s.length + 18
        ev.append(Event(s.start - 9, ln, drone([tun.hz(s.root - 12), tun.hz(s.root - 5)], ln, rng), 0, 0.045, wet=0.6))
    if "bowls" in R["layers"]:
        ev += scattered(rng, dur, 20, (40 * R["pace"], 75 * R["pace"]),
                        lambda t: Event(t, 28, bowl(tun.hz(root_at(secs, t) + int(pick(rng, [0, 7, 12]))), rng),
                                        rng.uniform(-0.4, 0.4), 0.05))
    if "choir" in R["layers"]:
        ev += _choir_events(secs, rng, tun, 0.004, every=1, vowel="oo")
    beds = [NoiseBed(rng, 80, 500, 0.004, breathe=0.08)]
    if "waves" in R["layers"]:
        beds.append(WavesBed(rng, 0.014))
    if "rain" in R["layers"]:
        beds.append(RainBed(rng, level=0.018, mode="inside"))
    return Score(ev, beds, reverb_s=R["reverb_s"], reverb_lp=3500, band=(30, 4200), target_lufs=-20.0,
                 params={"key": key, **info, "recipe": R})


SOLFEGGIO_HZ = [111, 174, 285, 396, 417, 432, 528, 639, 741, 852, 963]


def style_solfeggio(rng, dur, o):
    hz = float(o.get("hz") or pick(rng, SOLFEGGIO_HZ))
    beat = o.get("binaural")
    R = _recipe(rng, ["soft", "dark", "warm", "hollow", "glass"], {"bells": 0.6, "choir": 0.3, "waves": 0.2}, 6.0)
    R["register"] = int(o["register"]) if o.get("register") is not None else int(pick(rng, [0, 0, -12]))  # -12 = deeper pad
    m = 69 + 12 * math.log2(hz / 440)
    lo = 40 if R["register"] == 0 else 34                    # deep variant: pad ~half an octave lower
    key = int(round(m)) % 12 + 24
    while key < lo: key += 12
    while key > lo + 12: key -= 12
    k = round((m - key) / 12)
    offset = m - (key + 12 * k)                               # retune so key root == hz / 2^k exactly
    tun = Tuning(offset); info = {}
    secs = plan_harmony(rng, dur, "minor" if rng.random() < 0.5 else "major", int(pick(rng, [20, 24, 28])), key,
                        (10**9, 10**9), info=info, lo=lo)
    ev = pad_events(secs, rng, tun, 6, TIMBRES[R["timbre"]], 0.010)
    tone_gain = rng.uniform(0.028, 0.045)

    def tone(f_hz):
        def fn(tt, f0=0.0):
            a = 0.8 + 0.2 * np.sin(2 * np.pi * 0.05 * (tt + f0))
            return (a * np.sin(2 * np.pi * f_hz * (tt + f0))).astype(np.float32)
        return fn
    seg, t = 120.0, -5.0
    while t < dur:
        ln = seg + 10
        if beat:                                              # binaural: hz in the left ear, hz+beat in the right
            for f_hz, pan in ((hz, -1.0), (hz + float(beat), 1.0)):
                g = tone(f_hz)
                ev.append(Event(t, ln, lambda tt, L=ln, f0=t, g=g: g(tt, f0) * env_swell(tt, L) ** 0.5,
                                pan=pan, gain=tone_gain, wet=0.15))
        else:
            g = tone(hz)
            ev.append(Event(t, ln, lambda tt, L=ln, f0=t, g=g: g(tt, f0) * env_swell(tt, L) ** 0.5,
                            pan=0.0, gain=tone_gain, wet=0.4))
        t += seg
    if "bells" in R["layers"]:
        ev += scattered(rng, dur, 15, (14 * R["pace"], 30 * R["pace"]),
                        lambda t: Event(t, 6, bell(tun.hz(key + 24 + int(pick(rng, SCALES["major_penta"])))),
                                        rng.uniform(-0.7, 0.7), 0.02))
    if "choir" in R["layers"]:
        ev += _choir_events(secs, rng, tun, 0.005)
    beds = [NoiseBed(rng, 150, 900, 0.003)] + ([WavesBed(rng, 0.01)] if "waves" in R["layers"] else [])
    return Score(ev, beds, reverb_s=R["reverb_s"], reverb_lp=5000,
                 params={"hz": hz, "binaural_beat_hz": beat, "key": key, "tuning_offset": round(offset, 4),
                         **info, "recipe": R})


def style_rain(rng, dur, o):
    tun = Tuning(); key = int(rng.integers(45, 52)); info = {}
    R = _recipe(rng, ["warm", "dark", "hollow", "soft"], {"plucks": 0.75, "choir": 0.2, "thunder": 0.5}, 4.5)
    R["rain"] = o.get("rain") or "inside"
    secs = plan_harmony(rng, dur, "major" if rng.random() < 0.75 else "minor", int(pick(rng, [20, 24])), key, info=info)
    ev = pad_events(secs, rng, tun, 6, TIMBRES[R["timbre"]], 0.011)
    if "plucks" in R["layers"]:
        def mk_pluck(t):
            r = root_at(secs, t); out = []
            notes = sorted(rng.choice(SCALES["major_penta"], size=int(rng.integers(2, 4)), replace=False))
            for i, n in enumerate(notes):
                out.append(Event(t + i * rng.uniform(0.5, 0.9), 4, pluck(tun.hz(r + 12 + int(n))), rng.uniform(-0.5, 0.5), 0.03))
            return out
        ev += scattered(rng, dur, 10, (12 * R["pace"], 26 * R["pace"]), mk_pluck, d_period=600)
    if "thunder" in R["layers"]:
        ev += scattered(rng, dur, rng.uniform(90, 200), (200, 420),
                        lambda t: Event(t, 9, thunder(rng), rng.uniform(-0.6, 0.6), 0.14, wet=0.8))
    if "choir" in R["layers"]:
        ev += _choir_events(secs, rng, tun, 0.004)
    return Score(ev, [RainBed(rng, mode=R["rain"])], reverb_s=R["reverb_s"], reverb_lp=5500,
                 params={"key": key, **info, "recipe": R})


def style_morning(rng, dur, o):
    tun = Tuning(); key = int(rng.integers(48, 55)); info = {}
    R = _recipe(rng, ["warm", "glass", "dark"], {"plucks": 0.5, "chimes": 0.35, "choir": 0.2}, 4.8)
    secs = plan_harmony(rng, dur, "major", int(pick(rng, [16, 20])), key, info=info)
    ev = pad_events(secs, rng, tun, 4, TIMBRES[R["timbre"]], 0.011)
    pen = SCALES["major_penta"]

    def mk_phrase(t):
        r = root_at(secs, t); out = []; idx = int(rng.integers(len(pen)))
        for i in range(int(rng.integers(3, 6))):
            m = r + 24 + pen[idx % len(pen)] + 12 * (idx // len(pen))
            out.append(Event(t + i * float(pick(rng, [0.6, 0.9, 1.2])), 6, bell(tun.hz(m), decay=1.8),
                             rng.uniform(-0.7, 0.7), 0.03))
            idx = max(0, idx + int(pick(rng, [-1, 1, 2])))
        return out
    ev += scattered(rng, dur, 6, (9 * R["pace"], 18 * R["pace"]), mk_phrase, d_period=500)
    if "plucks" in R["layers"]:
        ev += scattered(rng, dur, 12, (10, 22),
                        lambda t: Event(t, 4, pluck(tun.hz(root_at(secs, t) + 12 + int(pick(rng, pen)))),
                                        rng.uniform(-0.5, 0.5), 0.025))
    if "chimes" in R["layers"]:
        ev += scattered(rng, dur, 30, (50, 120), lambda t: chimes_cluster(rng, t, root_at(secs, t) - 12, tun, 0.01))
    if "choir" in R["layers"]:
        ev += _choir_events(secs, rng, tun, 0.004, vowel="ah")
    return Score(ev, [NoiseBed(rng, 300, 3000, 0.003, breathe=0.05)], reverb_s=R["reverb_s"], reverb_lp=7000,
                 params={"key": key, **info, "recipe": R})


STYLES = {"bowls": style_bowls, "cosmic": style_cosmic, "sleep": style_sleep,
          "solfeggio": style_solfeggio, "rain": style_rain, "morning": style_morning}


# ── renderer ──────────────────────────────────────────────────────────────────

def make_ir(rng, secs, lp):
    n = int(secs * SR); t = np.arange(n) / SR
    env = np.exp(-t / (secs / 3.4))
    sos = butter(1, lp, btype="low", fs=SR, output="sos")
    irs = []
    for pre in (0.020, 0.027):
        ir = sosfilt(sos, rng.standard_normal(n)) * env
        ir[: int(pre * SR)] = 0
        irs.append((ir / np.sqrt((ir ** 2).sum())).astype(np.float32))
    return irs


def measure_lufs(L, R) -> float:
    """Integrated loudness of a stereo buffer via ffmpeg ebur128 (used for gain calibration)."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        path = f.name
    try:
        from scipy.io import wavfile
        st = np.stack([L, R], 1)
        wavfile.write(path, SR, np.clip(st, -1, 1).astype(np.float32))
        r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128", "-f", "null", "-"],
                           capture_output=True, text=True)
        vals = [float(line.split("I:")[1].split("LUFS")[0]) for line in r.stderr.splitlines()
                if " I:" in line and "LUFS" in line]
        return vals[-1] if vals else -30.0
    finally:
        os.unlink(path)


def render(score: Score, dur: float, out_path: Path, fmt: str, seed: int, log=print) -> dict:
    N = int(dur * SR); C = CHUNK_S * SR
    rng_ir = np.random.default_rng(seed + 991)
    irL, irR = make_ir(rng_ir, score.reverb_s, score.reverb_lp)
    tails = [np.zeros(len(irL) - 1, np.float32), np.zeros(len(irR) - 1, np.float32)]
    sos_m = butter(2, list(score.band), btype="band", fs=SR, output="sos")
    zi_m = [sosfilt_zi(sos_m) * 0, sosfilt_zi(sos_m) * 0]
    events = sorted(score.events, key=lambda e: e.start)
    active: list[Event] = []; ei = 0
    fade_in, fade_out = 6.0, min(10.0, dur / 4)

    codec = {"mp3": ["-c:a", "libmp3lame", "-b:a", "320k"], "flac": ["-c:a", "flac"],
             "wav": ["-c:a", "pcm_s16le"]}[fmt]
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", str(SR), "-ac", "2",
                             "-i", "-", *codec, str(out_path)], stdin=subprocess.PIPE)
    calib_s = min(dur, 150.0)
    pending: list[tuple[np.ndarray, np.ndarray]] = []
    gain = None
    peak = 0.0
    t0 = time.time()

    def emit(L, R):
        nonlocal peak
        x = np.stack([L, R], 1) * gain
        x = np.tanh(x * 1.15) / 1.15            # soft clip: unity gain for quiet signal, ceiling ≈ -1.2 dBFS
        peak = max(peak, float(np.abs(x).max()))
        proc.stdin.write((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())

    for c0 in range(0, N, C):
        c1 = min(N, c0 + C); n = c1 - c0
        t_lo, t_hi = c0 / SR, c1 / SR
        while ei < len(events) and events[ei].start < t_hi:
            active.append(events[ei]); ei += 1
        dry = [np.zeros(n, np.float32), np.zeros(n, np.float32)]
        send = [np.zeros(n, np.float32), np.zeros(n, np.float32)]
        still = []
        for e in active:
            s = int(e.start * SR); en = int(e.end * SR)
            a, b = max(s, c0), min(en, c1)
            if b > a:
                sig = e.fn((np.arange(a, b) - s) / SR) * e.gain
                ang = (e.pan + 1) * math.pi / 4
                for ch, g in ((0, math.cos(ang)), (1, math.sin(ang))):
                    dry[ch][a - c0:b - c0] += sig * g
                    send[ch][a - c0:b - c0] += sig * (g * e.wet)
            if en > c1:
                still.append(e)
        active = still
        for bed in score.beds:
            l, r = bed(c0, c1)
            dry[0] += l; dry[1] += r; send[0] += l; send[1] += r
        out = []
        for ch, ir in ((0, irL), (1, irR)):
            w = fftconvolve(send[ch], ir).astype(np.float32)
            w[: len(tails[ch])] += tails[ch]
            tails[ch] = w[n:].copy()
            if len(tails[ch]) < len(ir) - 1:
                tails[ch] = np.pad(tails[ch], (0, len(ir) - 1 - len(tails[ch])))
            mix = score.dry * dry[ch] + score.wet * w[:n]
            y, zi_m[ch] = sosfilt(sos_m, mix, zi=zi_m[ch])
            t = np.arange(c0, c1) / SR
            y *= np.minimum(1, np.minimum(t / fade_in, (dur - t) / fade_out)).clip(0, 1)
            out.append(y.astype(np.float32))

        if gain is None:
            pending.append((out[0], out[1]))
            if c1 >= calib_s * SR or c1 == N:
                L = np.concatenate([p[0] for p in pending]); R = np.concatenate([p[1] for p in pending])
                skip = int(min(fade_in + 2, len(L) / SR / 3) * SR)          # ignore the fade-in when measuring
                lufs = measure_lufs(L[skip:], R[skip:])
                gain = 10 ** ((score.target_lufs - lufs) / 20)
                for l, r in pending:
                    emit(l, r)
                pending = []
        else:
            emit(out[0], out[1])
        if c1 % (C * 20) == 0:
            el = time.time() - t0
            log(f"    {c1 / SR / 60:5.1f}/{dur / 60:.1f} min  ({el / (c1 / SR) * 60:.1f} s per audio minute)")

    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg encoding failed")
    return {"render_seconds": round(time.time() - t0, 1), "peak_dbfs": round(20 * math.log10(max(peak, 1e-9)), 2),
            "gain_db": round(20 * math.log10(gain), 2)}


# ── CLI ───────────────────────────────────────────────────────────────────────

def track_title(style, rng, params: dict) -> str:
    base, names = TITLES[style]
    hz = params.get("hz")
    if style == "solfeggio" and params.get("binaural_beat_hz"):
        base = "{hz}Hz Solfeggio Binaural Beats " + f"{params['binaural_beat_hz']:g}Hz"
    return f"{base.format(hz=f'{hz:g}' if hz else '528')} — {names[int(rng.integers(len(names)))]}"


def signature(style: str, title: str, params: dict) -> tuple:
    """What makes two tracks of the same style sound alike: key, progression, timbre, layers."""
    r = params.get("recipe", {})
    return (style, (params.get("key") or 0) % 12, params.get("progression"), r.get("timbre"),
            tuple(sorted(r.get("layers", []))), params.get("hz"), title.split(" — ")[-1])


def recent_tracks(log_path: Path, style: str, n: int = 8) -> list[dict]:
    if not log_path.exists():
        return []
    rows = []
    for line in log_path.read_text().splitlines()[-400:]:
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("style") == style:
            rows.append(r)
    return rows[-n:]


def main():
    ap = argparse.ArgumentParser(description="Procedural ambient music for Sacred Drift")
    ap.add_argument("--style", choices=sorted(STYLES))
    ap.add_argument("--minutes", type=float, default=None)
    ap.add_argument("--seconds", type=float, default=None)
    ap.add_argument("--count", type=int, default=1, help="number of tracks")
    ap.add_argument("--seed", type=int, default=None, help="first seed (default: from clock)")
    ap.add_argument("--hz", type=float, default=None,
                    help="solfeggio tone in Hz (any value; default: random from 111…963)")
    ap.add_argument("--binaural", type=float, default=None,
                    help="solfeggio: binaural beat in Hz (e.g. 4 = theta, 2 = delta) — headphones")
    ap.add_argument("--register", type=int, choices=[0, -12], default=None,
                    help="solfeggio: -12 = deeper pad an octave lower (default: random)")
    ap.add_argument("--rain", choices=["inside", "outside"], default=None,
                    help="rain style: heard from inside a room (default) or open air")
    ap.add_argument("--allow-repeat", action="store_true",
                    help="skip the check against recently generated tracks of the same style")
    ap.add_argument("--format", choices=["mp3", "flac", "wav"], default="mp3")
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT))
    ap.add_argument("--list-styles", action="store_true")
    a = ap.parse_args()

    if a.list_styles or not a.style:
        for k in STYLES:
            print(f"  {k:10} {TITLES[k][0].format(hz='528')}")
        return
    dur = a.seconds if a.seconds else (a.minutes or 10) * 60
    out_dir = Path(a.out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    seed_next = a.seed if a.seed is not None else int(time.time()) % 1_000_000
    log_path = out_dir / "ambient_log.jsonl"
    opts = {"hz": a.hz, "binaural": a.binaural, "register": a.register, "rain": a.rain}
    recent = [] if a.allow_repeat else recent_tracks(log_path, a.style)
    recent_sigs = {json.dumps(r["signature"]) for r in recent if r.get("signature")}
    recent_names = {r["title"].split(" — ")[-1] for r in recent if r.get("title")}

    for i in range(a.count):
        for attempt in range(40):                       # re-roll until it differs from recent tracks
            seed = seed_next; seed_next += 1
            rng = np.random.default_rng(seed)
            score = STYLES[a.style](rng, dur, opts)
            title = track_title(a.style, rng, score.params)
            sig = signature(a.style, title, score.params)
            name = title.split(" — ")[-1]
            if a.allow_repeat or (json.dumps(list(sig)) not in recent_sigs and name not in recent_names):
                break
        out = out_dir / f"{title} ({seed}).{a.format}"
        R = score.params.get("recipe", {})
        print(f"🎵 [{i + 1}/{a.count}] {out.name}  ({dur / 60:.1f} min)\n"
              f"    timbre={R.get('timbre')} layers={R.get('layers')} key={score.params.get('key')} "
              f"reverb={R.get('reverb_s')}s" + (f" hz={score.params.get('hz')}" if score.params.get("hz") else ""))
        stats = render(score, dur, out, a.format, seed)
        rec = {"file": out.name, "title": title, "style": a.style, "seed": seed, "duration_s": dur,
               "generator": "generate_ambient_audio.py", "version": VERSION, "params": score.params,
               "signature": list(sig), "target_lufs": score.target_lufs, **stats,
               "created": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
               "license": "Original procedural synthesis by Sacred Drift — no samples, no AI model"}
        with open(log_path, "a") as f:
            f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
        recent_sigs.add(json.dumps(list(sig))); recent_names.add(title.split(" — ")[-1])
        print(f"   ✅ {stats['render_seconds']}s render, peak {stats['peak_dbfs']} dBFS → {out}")


if __name__ == "__main__":
    main()
