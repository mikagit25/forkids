#!/usr/bin/env python3
"""
Sacred Drift — audio analysis for audio-reactive video (like a music visualizer).

analyze(audio, fps) decodes the track once and returns per-video-frame features:
  env        overall loudness 0..1 (smoothed: fast attack, slow release) → glow / brightness pulse
  low/mid/high  band energies 0..1                                          → breathing, shimmer
  spectrum   [frames × 48] log-spaced bands 0..1                            → equalizer ring / bars
  onsets     frame indices of strikes (bowls, gongs, bells, drops)          → ripples, flashes
Works chunk by chunk, so an 8-hour track needs only the feature arrays in memory
(8 h at 24 fps ≈ 700k frames × 48 bands ≈ 130 MB float32).
"""
from __future__ import annotations

import subprocess

import numpy as np

SR = 22050
N_BANDS = 48


def _decode(path: str):
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", str(path), "-f", "f32le", "-ac", "1",
                          "-ar", str(SR), "-"], stdout=subprocess.PIPE)
    return p


def _smooth(x: np.ndarray, fps: float, attack: float, release: float) -> np.ndarray:
    """Envelope follower: rises within `attack` s, falls within `release` s."""
    a = 1 - np.exp(-1 / (fps * attack)); r = 1 - np.exp(-1 / (fps * release))
    y = np.empty_like(x); v = 0.0
    for i, s in enumerate(x):
        v += (a if s > v else r) * (s - v)
        y[i] = v
    return y


def _norm(x: np.ndarray, lo_pct=10, hi_pct=97) -> np.ndarray:
    lo, hi = np.percentile(x, lo_pct), np.percentile(x, hi_pct)
    return ((x - lo) / max(hi - lo, 1e-9)).clip(0, 1).astype(np.float32)


def analyze(path: str, fps: float = 24.0, min_gap_s: float = 1.2) -> dict:
    hop = SR / fps                                   # audio samples per video frame (may be fractional)
    win = 2048
    window = np.hanning(win).astype(np.float32)
    freqs = np.fft.rfftfreq(win, 1 / SR)
    edges = np.geomspace(40, 10000, N_BANDS + 1)
    band_idx = [np.where((freqs >= a) & (freqs < b))[0] for a, b in zip(edges[:-1], edges[1:])]
    band_idx = [ix if len(ix) else np.array([np.argmin(abs(freqs - a))]) for ix, a in zip(band_idx, edges[:-1])]
    low_m, mid_m, high_m = freqs < 250, (freqs >= 250) & (freqs < 2000), freqs >= 2000

    p = _decode(path)
    buf = np.zeros(0, np.float32)
    rms, low, mid, high, flux, spec = [], [], [], [], [], []
    prev = None
    frame = 0
    while True:
        raw = p.stdout.read(SR * 4 * 10)               # 10 s at a time
        if raw:
            buf = np.concatenate([buf, np.frombuffer(raw, np.float32)])
        while True:
            start = int(round(frame * hop))
            local = start - analyze._consumed
            if local + win > len(buf):
                break
            seg = buf[local:local + win] * window
            mag = np.abs(np.fft.rfft(seg)).astype(np.float32)
            rms.append(float(np.sqrt(np.mean(seg ** 2)) + 1e-9))
            low.append(float(mag[low_m].mean())); mid.append(float(mag[mid_m].mean())); high.append(float(mag[high_m].mean()))
            spec.append([float(mag[ix].mean()) for ix in band_idx])
            lm = np.log1p(mag[freqs > 300] * 10)
            flux.append(0.0 if prev is None else float(np.maximum(lm - prev, 0).sum()))
            prev = lm
            frame += 1
        drop = max(0, int(round(frame * hop)) - analyze._consumed - win)
        if drop:
            buf = buf[drop:]; analyze._consumed += drop
        if not raw:
            break
    p.wait()
    analyze._consumed = 0

    db = 20 * np.log10(np.array(rms))
    env = _smooth(_norm(db, 15, 98), fps, 0.08, 0.7)
    feats = {"fps": fps, "frames": len(db), "env": env}
    for name, arr in (("low", low), ("mid", mid), ("high", high)):
        feats[name] = _smooth(_norm(20 * np.log10(np.array(arr) + 1e-9), 15, 98), fps, 0.1, 0.8)
    S = 20 * np.log10(np.array(spec, np.float32) + 1e-9)
    S = (S - np.percentile(S, 20, axis=0)) / (np.percentile(S, 99, axis=0) - np.percentile(S, 20, axis=0) + 1e-9)
    feats["spectrum"] = S.clip(0, 1).astype(np.float32)

    # onsets: spectral-flux peaks above a rolling median threshold, at least min_gap_s apart
    f = np.array(flux, np.float32)
    k = int(fps * 1.5)
    pad = np.pad(f, (k, k), mode="edge")
    med = np.array([np.median(pad[i:i + 2 * k]) for i in range(len(f))]) if len(f) < 200_000 else \
        np.convolve(pad, np.ones(2 * k) / (2 * k), "valid")[: len(f)]
    thr = med + 3.0 * (np.median(np.abs(f - med)) + 1e-9) + 0.15 * f.max()
    onsets, last = [], -1e9
    for i in range(1, len(f) - 1):
        if f[i] > thr[i] and f[i] >= f[i - 1] and f[i] >= f[i + 1] and i - last >= min_gap_s * fps:
            onsets.append(i); last = i
    feats["onsets"] = np.array(onsets, np.int64)
    feats["onset_strength"] = (f[onsets] / (f[onsets].max() if len(onsets) else 1)).astype(np.float32) if onsets else np.zeros(0)
    return feats


analyze._consumed = 0


if __name__ == "__main__":
    import sys
    F = analyze(sys.argv[1])
    print(f"frames {F['frames']}  onsets {len(F['onsets'])} at s:",
          [round(i / F['fps'], 1) for i in F['onsets'][:30]])
    print("env mean", round(float(F['env'].mean()), 3), "low", round(float(F['low'].mean()), 3))
