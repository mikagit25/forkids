"""Public-domain nursery melodies, arranged and synthesized in code (our own recording → no Content ID owner).

Every tune here is traditional or by a composer who died more than 100 years ago:
  Twinkle Twinkle Little Star — French "Ah! vous dirai-je, maman" (1761), words Jane Taylor (1806)
  Brahms' Lullaby (Wiegenlied, Op. 49 No. 4) — Johannes Brahms, 1868 (d. 1897)
  Frère Jacques — traditional French, 18th century
  Mary Had a Little Lamb — Sarah Josepha Hale (1830), tune Lowell Mason (d. 1872)
  London Bridge Is Falling Down — traditional English, 18th century
  Row, Row, Row Your Boat — traditional, first printed 1852

Melody format: list of (note, beats); note = semitones above the tonic (0 = do), None = rest.
"""
from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

from . import music as M

C, D, E, F, G, A, B = 0, 2, 4, 5, 7, 9, 11
G3, A3, B3 = -5, -3, -1
C5, D5 = 12, 14

TUNES = {
    "twinkle": dict(title="Twinkle Twinkle Little Star", beats_per_bar=4, chords="I IV I V", melody=[
        (C, 1), (C, 1), (G, 1), (G, 1), (A, 1), (A, 1), (G, 2), (F, 1), (F, 1), (E, 1), (E, 1), (D, 1), (D, 1), (C, 2),
        (G, 1), (G, 1), (F, 1), (F, 1), (E, 1), (E, 1), (D, 2), (G, 1), (G, 1), (F, 1), (F, 1), (E, 1), (E, 1), (D, 2),
        (C, 1), (C, 1), (G, 1), (G, 1), (A, 1), (A, 1), (G, 2), (F, 1), (F, 1), (E, 1), (E, 1), (D, 1), (D, 1), (C, 2)],
        harmony=["I", "I", "IV", "I", "IV", "I", "V", "I", "I", "IV", "I", "V", "I", "IV", "I", "V",
                 "I", "I", "IV", "I", "IV", "I", "V", "I"], harmony_beats=2),
    "brahms": dict(title="Brahms' Lullaby", beats_per_bar=3, melody=[
        (E, 0.5), (E, 0.5),
        (G, 2), (E, 0.5), (E, 0.5), (G, 2), (E, 0.5), (G, 0.5), (C5, 1), (B, 1.5), (A, 0.5), (A, 1), (G, 1),
        (D, 0.5), (E, 0.5), (F, 1), (D, 1), (D, 0.5), (E, 0.5), (F, 2), (D, 0.5), (F, 0.5), (B, 0.5), (A, 0.5),
        (G, 1), (B, 1), (C5, 2),
        (C, 0.5), (C, 0.5), (C5, 2), (A, 0.5), (F, 0.5), (G, 2), (E, 0.5), (C, 0.5), (F, 1), (G, 1), (A, 1), (G, 2),
        (C, 0.5), (C, 0.5), (C5, 2), (A, 0.5), (F, 0.5), (G, 2), (E, 0.5), (C, 0.5), (F, 0.5), (E, 0.5), (D, 1),
        (B3, 1), (C, 3)],
        harmony=["I", "I", "I", "V", "V", "V", "V", "I", "IV", "I", "IV", "I", "IV", "I", "V", "I"], harmony_beats=3,
        pickup=1.0),
    "frere": dict(title="Frère Jacques", beats_per_bar=4, melody=[
        (C, 1), (D, 1), (E, 1), (C, 1), (C, 1), (D, 1), (E, 1), (C, 1), (E, 1), (F, 1), (G, 2), (E, 1), (F, 1), (G, 2),
        (G, 0.5), (A, 0.5), (G, 0.5), (F, 0.5), (E, 1), (C, 1), (G, 0.5), (A, 0.5), (G, 0.5), (F, 0.5), (E, 1), (C, 1),
        (C, 1), (G3, 1), (C, 2), (C, 1), (G3, 1), (C, 2)],
        harmony=["I"] * 8, harmony_beats=4),
    "mary": dict(title="Mary Had a Little Lamb", beats_per_bar=4, melody=[
        (E, 1), (D, 1), (C, 1), (D, 1), (E, 1), (E, 1), (E, 2), (D, 1), (D, 1), (D, 2), (E, 1), (G, 1), (G, 2),
        (E, 1), (D, 1), (C, 1), (D, 1), (E, 1), (E, 1), (E, 1), (E, 1), (D, 1), (D, 1), (E, 1), (D, 1), (C, 4)],
        harmony=["I", "I", "V", "I", "I", "I", "V", "I"], harmony_beats=4),
    "london": dict(title="London Bridge Is Falling Down", beats_per_bar=4, melody=[
        (G, 1.5), (A, 0.5), (G, 1), (F, 1), (E, 1), (F, 1), (G, 2), (D, 1), (E, 1), (F, 2), (E, 1), (F, 1), (G, 2),
        (G, 1.5), (A, 0.5), (G, 1), (F, 1), (E, 1), (F, 1), (G, 2), (D, 2), (G, 2), (E, 1), (C, 3)],
        harmony=["I", "I", "V", "I", "I", "I", "V", "I"], harmony_beats=4),
    "rowboat": dict(title="Row, Row, Row Your Boat", beats_per_bar=6, melody=[
        (C, 3), (C, 3), (C, 2), (D, 1), (E, 3), (E, 2), (D, 1), (E, 2), (F, 1), (G, 6),
        (C5, 1), (C5, 1), (C5, 1), (G, 1), (G, 1), (G, 1), (E, 1), (E, 1), (E, 1), (C, 1), (C, 1), (C, 1),
        (G, 2), (F, 1), (E, 2), (D, 1), (C, 6)],
        harmony=["I", "I", "I", "V", "I", "I", "V", "I"], harmony_beats=6),
}

DEG = {"I": (0, 4, 7), "IV": (5, 9, 12), "V": (7, 11, 14), "vi": (9, 12, 16)}
# one "verse" = the tune once; each tune is played several times, each time with a different voice
VOICES = [("musicbox", None), ("felt", "flute"), ("musicbox", "felt"), ("flute", None)]


def tune_beats(tune: dict) -> float:
    return sum(b for _, b in tune["melody"])


def render_medley(order: list[str], out_wav: Path, seed: int, bpm: float = 76, repeats: int = 3, key: int = 60,
                  target_min: float | None = None) -> dict:
    """Play the tunes in `order`, each `repeats` times with changing instruments, soft pad chords and a bass
    note per chord; 1 bar of rest between verses. If target_min is set the whole medley repeats until the
    length is reached (with new voicings — never a copied loop). Returns a map of (title, start, end)."""
    rng = np.random.default_rng(seed)
    beat = 60.0 / bpm
    plan, t = [], 1.5
    cycle = 0
    while True:
        for name in order:
            tune = TUNES[name]
            start = t
            for r in range(repeats):
                v = VOICES[(r + cycle + len(plan)) % len(VOICES)]
                plan.append((name, t, v))
                t += tune_beats(tune) * beat + tune["beats_per_bar"] * beat
            plan_title = (tune["title"], round(start, 2), round(t, 2))
            plan.append(("__mark__", plan_title, None))
        cycle += 1
        if not target_min or t >= target_min * 60:
            break
    n = int((t + 4) * M.SR)
    L = np.zeros(n, np.float32); R = np.zeros(n, np.float32); W = np.zeros(n, np.float32)

    def add(sig, at, gain, pan=0.0, send=0.5):
        i = int(at * M.SR)
        if i >= n:
            return
        sig = sig[: n - i] * gain
        L[i:i + len(sig)] += sig * (1 - max(pan, 0)); R[i:i + len(sig)] += sig * (1 + min(pan, 0))
        W[i:i + len(sig)] += sig * send

    marks = []
    for name, at, v in plan:
        if name == "__mark__":
            marks.append(at)
            continue
        tune = TUNES[name]
        tt = at
        for note, b in tune["melody"]:
            if note is not None:
                f = M.hz(key + note)
                add(M.LEADS[v[0]](f, b * beat * 0.95, 0.9), tt, 0.34, 0.08)
                if v[1]:
                    add(M.LEADS[v[1]](f * (2 if v[1] == "musicbox" else 1), b * beat * 0.95, 0.5), tt, 0.10, -0.15)
            tt += b * beat
        hb = tune["harmony_beats"] * beat
        hstart = at + tune.get("pickup", 0) * beat
        for k, deg in enumerate(tune["harmony"]):
            if hstart + k * hb >= tt:
                break
            for iv in DEG[deg]:
                add(M.pad(M.hz(key - 12 + iv), hb * 0.97), hstart + k * hb, 0.07, 0.0, 0.6)
            add(M.bass(M.hz(key - 24 + DEG[deg][0]), hb * 0.8, 0.7), hstart + k * hb, 0.16, 0.0, 0.0)
    irl, irr = M.hall_ir(rng, 2.6, 3200, (beat * 0.75, 0.35, 4))
    L = L + 0.5 * fftconvolve(W, irl)[:n]
    R = R + 0.5 * fftconvolve(W, irr)[:n]
    sos = butter(2, 3000, btype="low", fs=M.SR, output="sos")
    L, R = sosfilt(sos, L), sosfilt(sos, R)
    st = np.stack([L, R], 1)
    st = st / (np.abs(st).max() + 1e-9) * 0.89
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "s16le", "-ar", str(M.SR), "-ac", "2", "-i", "-",
                    "-af", "loudnorm=I=-20:TP=-1.0:LRA=9", "-ar", str(M.SR), str(out_wav)],
                   input=(st * 32767).astype("<i2").tobytes(), check=True)
    info = {"bpm": bpm, "duration": round(t + 3, 2), "songs": marks, "seed": seed,
            "license": "Public-domain melodies; arrangement and recording synthesized in code by Happy Bear Kids"}
    out_wav.with_suffix(".json").write_text(json.dumps(info, indent=1))
    return info
