"""Documentary underscore synthesized from scratch with numpy (no samples, no AI models).

Slow string-like pads following a minor or major progression, sparse low piano notes, a soft
low hit on every chapter card, and a synthetic hall reverb. Same seed -> same music, so a
track can always be reproduced (proof of authorship, no Content ID risk).
"""
from __future__ import annotations

import numpy as np
from scipy.signal import oaconvolve

from .tts import SR

MOODS = {
    #            key root (MIDI), mode,  progressions (scale degrees, 0-based), chord seconds, piano density
    "somber":  (50, "minor", [[0, 5, 2, 6], [0, 3, 5, 4], [0, 5, 3, 4], [0, 6, 5, 4]], 9.0, 0.35),
    "tense":   (45, "minor", [[0, 1, 0, 5], [0, 5, 1, 4], [0, 0, 5, 1]], 7.0, 0.55),
    "hopeful": (48, "major", [[0, 4, 5, 3], [0, 5, 3, 4], [3, 4, 0, 5]], 8.0, 0.4),
}
SCALES = {"minor": [0, 2, 3, 5, 7, 8, 10], "major": [0, 2, 4, 5, 7, 9, 11]}


def _hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def _chord(root, mode, degree, rng):
    sc = SCALES[mode]
    notes = []
    for k in (0, 2, 4):
        i = degree + k
        notes.append(root + sc[i % 7] + 12 * (i // 7))
    bass = notes[0] - 12
    voicing = [bass, notes[0], notes[1] + 12, notes[2] + 12]
    if rng.random() < 0.4:  # occasional added 9th for colour
        voicing.append(notes[0] + 14)
    return voicing


def _pad_voice(f, n, rng, bright=6):
    t = np.arange(n) / SR
    out = np.zeros(n, np.float32)
    for det in (-0.004, 0.0, 0.0045):  # three slightly detuned "players" = ensemble width
        vib = 1 + 0.0025 * np.sin(2 * np.pi * rng.uniform(4.2, 5.4) * t + rng.uniform(0, 6.28))
        phase = 2 * np.pi * f * (1 + det) * np.cumsum(vib) / SR  # integrate frequency -> no pitch drift
        ph = rng.uniform(0, 6.28)
        for h in range(1, bright + 1):
            out += (np.sin(h * phase + ph * h) / h ** 1.6).astype(np.float32)
    return out / 3


def _envelope(n, attack, release):
    e = np.ones(n, np.float32)
    a, r = int(attack * SR), int(release * SR)
    e[:a] = np.linspace(0, 1, a) ** 1.5
    e[-r:] *= np.linspace(1, 0, r) ** 1.2
    return e


def _piano(f, dur, rng):
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n, np.float32)
    for h, amp in ((1, 1.0), (2, 0.45), (3, 0.2), (4, 0.12), (6, 0.05)):
        inharm = 1 + 0.0004 * h * h
        out += amp * np.sin(2 * np.pi * f * h * inharm * t) * np.exp(-t * (1.1 + 0.9 * h))
    out[: int(0.004 * SR)] *= np.linspace(0, 1, int(0.004 * SR))
    return out


def _hit(rng):
    """Soft low 'boom' for chapter cards (pitched-down sine thump + filtered noise)."""
    n = int(4.0 * SR)
    t = np.arange(n) / SR
    f = 52 * np.exp(-t * 0.6) + 30
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.3)
    noise = np.convolve(rng.standard_normal(n), np.ones(60) / 60, mode="same") * np.exp(-t * 4)
    return (0.9 * body + 0.25 * noise).astype(np.float32)


def _reverb_ir(seconds, rng):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    ir = rng.standard_normal(n) * np.exp(-t * 6.9 / seconds)
    ir = np.convolve(ir, np.ones(8) / 8, mode="same")  # darker tail
    ir[0] = 1.0
    return (ir / np.sqrt(np.sum(ir ** 2))).astype(np.float32)


def underscore(total: float, seed: int = 1, mood: str = "somber", hits: list[float] | None = None) -> np.ndarray:
    root, mode, progs, chord_len, density = MOODS.get(mood, MOODS["somber"])
    rng = np.random.default_rng(seed)
    n_total = int((total + 6) * SR)
    pad = np.zeros(n_total, np.float32)
    keys = np.zeros(n_total, np.float32)
    prog = progs[rng.integers(len(progs))]
    t, i = 0.0, 0
    while t < total + 2:
        if i and i % 8 == 0:
            prog = progs[rng.integers(len(progs))]
        deg = prog[i % len(prog)]
        voicing = _chord(root, mode, deg, rng)
        dur = chord_len * rng.choice([1.0, 1.0, 1.5])
        n = int((dur + 3.0) * SR)  # overlap = smooth chord crossfade
        s = int(t * SR)
        seg = np.zeros(n, np.float32)
        for k, m in enumerate(voicing):
            seg += _pad_voice(_hz(m), n, rng, bright=4 if k == 0 else 6) * (0.9 if k == 0 else 0.55)
        seg *= _envelope(n, 2.8, 3.5)
        e = min(s + n, n_total)
        pad[s:e] += seg[: e - s]
        # sparse low piano: one or two chord tones per chord
        for _ in range(rng.binomial(2, density)):
            pt = t + rng.uniform(0.5, dur - 0.5)
            m = rng.choice(voicing[1:3]) - 12 * rng.integers(0, 2)
            note = _piano(_hz(m), 6.0, rng)
            ps = int(pt * SR)
            pe = min(ps + len(note), n_total)
            keys[ps:pe] += 0.5 * note[: pe - ps]
        t += dur
        i += 1
    dry = 0.55 * pad / (np.max(np.abs(pad)) or 1) + 0.45 * keys / (np.max(np.abs(keys)) or 1)
    if hits:
        h = _hit(rng)
        for ht in hits:
            s = int(ht * SR)
            e = min(s + len(h), n_total)
            dry[s:e] += 0.8 * h[: e - s]
    wet = oaconvolve(dry, _reverb_ir(3.2, rng))[:n_total]
    out = 0.45 * dry + 0.75 * wet
    out = out[: int(total * SR)]
    out /= np.max(np.abs(out)) or 1
    fade = np.ones_like(out)
    fade[: 3 * SR] = np.linspace(0, 1, 3 * SR)
    fade[-5 * SR:] = np.linspace(1, 0, 5 * SR)
    return (out * fade * 0.8).astype(np.float32)
