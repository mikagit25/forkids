"""Use tracks from our existing collection (Suno songs, lullabies, procedural sleep music…).

analyze(path) → beat map in the same format as sensory.music (bpm, beats, sections), so any track
can drive the dance or sleep formats. Tempo is estimated from the onset envelope (autocorrelation,
60–180 BPM, biased to 90–130 for dance); sections are cut every 8 bars (intro 4, A/B alternating,
a 4-bar break every ~32 bars, outro 4) so the cast changes on phrase boundaries.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np

SR = 22050
HOP = 512


def decode(path: str | Path, sr=SR) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(path), "-ac", "1", "-ar", str(sr), "-f", "f32le",
                          "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def onset_envelope(y: np.ndarray) -> np.ndarray:
    win = np.hanning(2048).astype(np.float32)
    n = 1 + (len(y) - 2048) // HOP
    if n < 4:
        return np.zeros(4)
    idx = np.arange(2048)[None, :] + HOP * np.arange(n)[:, None]
    env = np.empty(n, np.float32); prev = None
    for k in range(0, n, 2048):                               # chunked → bounded memory for long tracks
        frames = y[idx[k:k + 2048]] * win
        mag = np.log1p(np.abs(np.fft.rfft(frames, axis=1)) * 10)
        d = np.diff(mag, axis=0, prepend=mag[:1] if prev is None else prev[None])
        env[k:k + len(frames)] = np.maximum(d, 0).sum(1)
        prev = mag[-1]
    env -= np.convolve(env, np.ones(16) / 16, "same")
    return np.maximum(env, 0)


def tempo(env: np.ndarray, lo=60, hi=180, prefer=(90, 130)) -> float:
    fps = SR / HOP
    seg = env[: int(fps * 120)]                               # first 2 minutes is plenty
    ac = np.correlate(seg, seg, "full")[len(seg) - 1:]
    best, best_bpm = -1.0, 100.0
    for bpm in np.arange(lo, hi, 0.5):
        lag = fps * 60 / bpm
        i = int(round(lag))
        if i >= len(ac):
            continue
        score = ac[i] + 0.5 * ac[min(len(ac) - 1, int(round(2 * lag)))]
        if prefer[0] <= bpm <= prefer[1]:
            score *= 1.15
        if score > best:
            best, best_bpm = score, bpm
    # octave check: a half-time pick (e.g. 61 BPM for a 123 BPM disco) → double it if the faster
    # pulse is nearly as strong and still in range
    if best_bpm * 2 <= hi:
        lag2 = int(round(fps * 60 / (best_bpm * 2)))
        lag1 = int(round(fps * 60 / best_bpm))
        if lag1 < len(ac) and ac[lag2] > 0.5 * ac[lag1]:
            best_bpm *= 2
    return float(best_bpm)


def analyze(path: str | Path, out_json: Path, bpm: float | None = None) -> dict:
    y = decode(path)
    dur = len(y) / SR
    env = onset_envelope(y)
    fps = SR / HOP
    fixed = bpm is not None
    bpm = bpm or tempo(env)
    beat = 60.0 / bpm
    # refine tempo (±1 BPM, 0.02 steps) and phase together: the grid that hits the most onsets
    # over the whole track wins — a 0.5 BPM error would drift a whole beat in a few minutes
    best = (-1.0, bpm, 0.0)
    if not fixed:
        cand = np.arange(bpm - 1.0, bpm + 1.0001, 0.02)
    else:
        cand = [bpm]
    for b_ in cand:
        lag = fps * 60.0 / b_
        for o in np.arange(0, lag, 0.5):
            sc = env[np.arange(o, len(env) - 1, lag).astype(int)].sum()
            if sc > best[0]:
                best = (sc, b_, o)
    bpm = float(round(best[1], 2)); beat = 60.0 / bpm
    t0 = float(best[2] / fps)
    t0 = (t0 + 0.9 * 2048 / SR) % beat                        # flux frames lead the hit by ~one window
    beats = [round(t0 + i * beat, 4) for i in range(int((dur - t0) / beat) + 1)]
    bar = 4 * beat
    nbars = int((dur - t0) / bar)
    secs, b = [{"name": "intro", "bars": min(4, nbars)}], min(4, nbars)
    k = 0
    while b + 8 <= nbars - 4:
        name = "break" if k % 4 == 3 else ("A" if k % 2 == 0 else "B")
        n = 4 if name == "break" else 8
        secs.append({"name": name, "bars": n}); b += n; k += 1
    if nbars - b > 0:
        secs.append({"name": "outro", "bars": nbars - b})
    start = 0.0
    out = []
    for s in secs:
        end = t0 + (sum(x["bars"] for x in out) + s["bars"]) * bar
        out.append({**s, "start": round(start, 4), "end": round(end, 4)}); start = end
    out[-1]["end"] = round(dur, 4)
    bmap = {"genre": "external", "bpm": bpm, "beat_s": beat, "bars": nbars, "beats": beats, "sections": out,
            "duration": round(dur, 3), "source": str(path)}
    out_json.write_text(json.dumps(bmap, indent=1))
    return bmap
