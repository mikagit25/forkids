"""Kids dance music, synthesized in code (no samples, no AI model → we own every note).

Every song is built from a seed: genre, key, tempo, chord progression, a catchy 2-bar motif that
repeats (toddlers love repetition) and a song form whose sections line up with the dance scenes:

    intro 4 · A 8 · A' 8 · B 8 · break 4 · A 8 · B' 8 · A 8 · outro 4   (bars; repeated to length)

Output: WAV + a JSON "beat map" (exact beat/bar/section times) — the animation reads it directly,
so the dancing is on the beat by construction, no beat detection needed.

Genres:
  disco      118–124 BPM  four-on-the-floor, octave bass, offbeat hats, marimba + bell lead
  calypso    100–108 BPM  steel drum lead, offbeat chord stabs, bouncy bass
  march      104–112 BPM  boom-chick, glockenspiel lead, toy-band feel
  bounce     122–128 BPM  electro-pop: plucky square lead (soft), claps on 2 and 4, rolling bass
  lullaby     64–72 BPM   music box + soft pad, no drums (sleep format)
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

SR = 44100
MAJOR = [0, 2, 4, 5, 7, 9, 11]
PENTA = [0, 2, 4, 7, 9]
PROGRESSIONS = [            # scale degrees (0 = I)
    [0, 4, 5, 3],           # I V vi IV
    [0, 3, 4, 0],           # I IV V I
    [0, 5, 3, 4],           # I vi IV V
    [0, 3, 0, 4],           # I IV I V
    [3, 4, 0, 0],           # IV V I I
]
FORM = [("intro", 4), ("A", 8), ("A2", 8), ("B", 8), ("break", 4), ("A", 8), ("B2", 8), ("A", 8), ("outro", 4)]
GENRES = {
    "disco":   dict(bpm=(118, 124), lead="marimba", lead2="bell", comp="piano", swing=0.0),
    "calypso": dict(bpm=(100, 108), lead="steel", lead2="marimba", comp="stab", swing=0.12),
    "march":   dict(bpm=(104, 112), lead="glock", lead2="marimba", comp="chick", swing=0.0),
    "bounce":  dict(bpm=(122, 128), lead="square", lead2="bell", comp="stab", swing=0.0),
    "lullaby": dict(bpm=(64, 72), lead="felt", lead2="flute", comp="pad", swing=0.0),
}


def hz(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


# ── instruments: (freq, dur, vel) → mono float32 ─────────────────────────────

def _t(dur):
    return np.arange(int(dur * SR)) / SR


def marimba(f, dur, vel=1.0):
    t = _t(min(dur, 1.2) + 0.4)
    y = (np.sin(2 * np.pi * f * t) * np.exp(-t / 0.35) + 0.35 * np.sin(2 * np.pi * f * 3.9 * t) * np.exp(-t / 0.06)
         + 0.12 * np.sin(2 * np.pi * f * 9.2 * t) * np.exp(-t / 0.02))
    return (y * vel * np.minimum(1, t / 0.002)).astype(np.float32)


def bell(f, dur, vel=1.0):
    t = _t(1.6)
    y = sum(a * np.sin(2 * np.pi * f * m * t) * np.exp(-t / d) for m, a, d in
            ((1, 1, 0.9), (2.76, 0.4, 0.4), (5.4, 0.2, 0.15), (8.9, 0.08, 0.06)))
    return (y * vel * 0.6).astype(np.float32)


def glock(f, dur, vel=1.0):
    t = _t(1.0)
    y = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.5) + 0.3 * np.sin(2 * np.pi * f * 2.0 * t) * np.exp(-t / 0.2)
    return (y * vel * 0.7).astype(np.float32)


def steel(f, dur, vel=1.0):
    t = _t(min(dur, 0.9) + 0.3)
    bend = 1 + 0.01 * np.exp(-t / 0.03)                       # tiny pitch drop at the strike
    ph = 2 * np.pi * f * np.cumsum(bend) / SR
    y = (np.sin(ph) + 0.5 * np.sin(2 * ph) * np.exp(-t / 0.2) + 0.35 * np.sin(3 * ph) * np.exp(-t / 0.12)
         + 0.2 * np.sin(4.2 * ph) * np.exp(-t / 0.05)) * np.exp(-t / 0.45)
    return (y * vel * 0.7).astype(np.float32)


def square(f, dur, vel=1.0):
    t = _t(dur + 0.05)
    y = np.zeros_like(t)
    for k in (1, 3, 5, 7, 9):                                # soft band-limited square
        y += np.sin(2 * np.pi * f * k * t) / k * (0.85 ** k)
    env = np.minimum(1, t / 0.005) * np.exp(-t / max(dur * 0.9, 0.08)) * np.clip((dur + 0.05 - t) / 0.05, 0, 1)
    return (y * env * vel * 0.5).astype(np.float32)


def musicbox(f, dur, vel=1.0):
    t = _t(2.2)
    y = np.sin(2 * np.pi * f * t) * np.exp(-t / 1.1) + 0.25 * np.sin(2 * np.pi * f * 4 * t) * np.exp(-t / 0.3)
    return (y * vel * 0.6).astype(np.float32)


def felt(f, dur, vel=1.0):
    """Felt piano / soft kalimba: slow-ish attack, almost no overtones → warm, not bell-like."""
    t = _t(2.0)
    y = np.sin(2 * np.pi * f * t) + 0.18 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / 0.25)
    env = np.minimum(1, t / 0.012) * np.exp(-t / 0.9)
    return (y * env * vel * 0.7).astype(np.float32)


def flute(f, dur, vel=1.0):
    """Soft breathy flute-like tone for gentle doubling."""
    t = _t(dur + 0.3)
    vib = 1 + 0.003 * np.sin(2 * np.pi * 5 * t) * np.minimum(1, t / 0.4)
    y = np.sin(2 * np.pi * f * np.cumsum(vib) / SR)
    env = np.minimum(1, t / 0.12) * np.clip((dur + 0.3 - t) / 0.3, 0, 1)
    return (y * env * vel * 0.4).astype(np.float32)


def piano(f, dur, vel=1.0):
    t = _t(min(dur, 0.8) + 0.2)
    y = sum(np.sin(2 * np.pi * f * k * t) / k ** 1.3 * np.exp(-t * k / 0.6) for k in range(1, 6))
    return (y * vel * 0.5 * np.minimum(1, t / 0.003)).astype(np.float32)


def pad(f, dur, vel=1.0):
    t = _t(dur + 0.6)
    y = sum(np.sin(2 * np.pi * f * (1 + d) * t) for d in (-0.003, 0, 0.003)) / 3
    env = np.minimum(1, t / 0.4) * np.clip((dur + 0.6 - t) / 0.6, 0, 1)
    return (y * env * vel * 0.35).astype(np.float32)


def bass(f, dur, vel=1.0):
    t = _t(dur + 0.03)
    y = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / 0.08) \
        + 0.15 * np.sin(2 * np.pi * 3 * f * t) * np.exp(-t / 0.04)
    env = np.minimum(1, t / 0.004) * np.exp(-t / max(dur, 0.12)) * np.clip((dur + 0.03 - t) / 0.03, 0, 1)
    return (y * env * vel).astype(np.float32)


def kick(vel=1.0):
    t = _t(0.35)
    f = 48 + 90 * np.exp(-t / 0.035)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.13) * vel).astype(np.float32)


_rng = np.random.default_rng(0)
_SOS_SN = butter(2, [1200, 6000], btype="band", fs=SR, output="sos")
_SOS_HH = butter(2, 7000, btype="high", fs=SR, output="sos")


def snare(vel=1.0):
    t = _t(0.22)
    n = sosfilt(_SOS_SN, _rng.standard_normal(len(t))) * np.exp(-t / 0.06)
    return ((0.7 * n + 0.4 * np.sin(2 * np.pi * 190 * t) * np.exp(-t / 0.05)) * vel).astype(np.float32)


def clap(vel=1.0):
    t = _t(0.25)
    n = sosfilt(_SOS_SN, _rng.standard_normal(len(t)))
    env = sum(np.exp(-np.clip(t - o, 0, None) / 0.008) * (t >= o) for o in (0, 0.011, 0.022)) + \
        0.6 * np.exp(-np.clip(t - 0.03, 0, None) / 0.07) * (t >= 0.03)
    return (n * env * 0.5 * vel).astype(np.float32)


def hat(vel=1.0, open_=False):
    t = _t(0.25 if open_ else 0.06)
    return (sosfilt(_SOS_HH, _rng.standard_normal(len(t))) * np.exp(-t / (0.08 if open_ else 0.015)) * vel
            ).astype(np.float32)


def shaker(vel=1.0):
    t = _t(0.08)
    return (sosfilt(_SOS_HH, _rng.standard_normal(len(t))) * np.sin(np.pi * t / 0.08) * vel * 0.5).astype(np.float32)


LEADS = {"marimba": marimba, "bell": bell, "glock": glock, "steel": steel, "square": square,
         "musicbox": musicbox, "piano": piano, "felt": felt, "flute": flute}


# ── song plan ────────────────────────────────────────────────────────────────

@dataclass
class Song:
    genre: str
    bpm: float
    key: int
    prog: list
    seed: int
    sections: list = field(default_factory=list)     # (name, start_bar, bars)
    bars: int = 0

    @property
    def beat_s(self):
        return 60.0 / self.bpm


def plan(genre: str, seed: int, seconds: float) -> Song:
    rng = np.random.default_rng(seed)
    G = GENRES[genre]
    bpm = float(rng.integers(G["bpm"][0], G["bpm"][1] + 1))
    key = int(rng.integers(55, 63))                           # G3..D4 → bright but not shrill
    prog = PROGRESSIONS[int(rng.integers(len(PROGRESSIONS)))]
    s = Song(genre, bpm, key, prog, seed)
    total_bars = int(math.ceil(seconds / (4 * 60 / bpm) / 4)) * 4      # whole 4-bar phrases
    bar = 0
    form = FORM if genre != "lullaby" else [("intro", 4), ("A", 8), ("A2", 8), ("B", 8), ("A", 8)]
    body = [x for x in form if x[0] not in ("intro", "outro")]
    s.sections.append(("intro", 0, 4)); bar = 4
    i = 0
    while bar + 4 < total_bars:
        name, n = body[i % len(body)]
        n = min(n, total_bars - 4 - bar)
        n -= n % 4                                            # sections always end on a phrase
        if n <= 0:
            break
        s.sections.append((name, bar, n)); bar += n; i += 1
    s.sections.append(("outro", bar, 4)); bar += 4
    s.bars = bar
    return s


def motif(rng, bars=2, steps_per_bar=8):
    """A catchy 2-bar phrase on the major pentatonic: (step, length_steps, scale_index)."""
    rhythm_bank = [[0, 2, 4, 6], [0, 2, 3, 4, 6], [0, 1, 2, 4, 6], [0, 3, 4, 6], [0, 2, 4, 5, 6]]
    notes, idx = [], int(rng.integers(2, 6))
    for b in range(bars):
        r = rhythm_bank[int(rng.integers(len(rhythm_bank)))]
        for j, st in enumerate(r):
            ln = (r[j + 1] if j + 1 < len(r) else steps_per_bar) - st
            idx = int(np.clip(idx + rng.choice([-2, -1, -1, 0, 1, 1, 2]), 0, 9))
            notes.append((b * steps_per_bar + st, ln, idx))
    notes[-1] = (notes[-1][0], notes[-1][1], 0 if rng.random() < 0.5 else 5)     # land on the tonic
    return notes


# ── render ───────────────────────────────────────────────────────────────────

def render(song: Song, out_wav: Path) -> dict:
    rng = np.random.default_rng(song.seed + 1)
    G = GENRES[song.genre]
    beat = song.beat_s; bar_s = 4 * beat; step = beat / 2
    n = int((song.bars * bar_s + 2.5) * SR)
    L = np.zeros(n, np.float32); R = np.zeros(n, np.float32)

    def add(sig, t, gain=1.0, pan=0.0):
        i = int(t * SR)
        if i >= n:
            return
        sig = sig[: n - i] * gain
        L[i:i + len(sig)] += sig * (1 - max(pan, 0)); R[i:i + len(sig)] += sig * (1 + min(pan, 0))

    def swing(t, st):
        return t + (G["swing"] * step if st % 2 == 1 else 0.0)

    motifs = {"A": motif(rng), "B": motif(rng)}
    lead, lead2 = LEADS[G["lead"]], LEADS[G["lead2"]]
    drums = song.genre != "lullaby"

    for name, b0, nb in song.sections:
        kind = name.rstrip("2")
        for b in range(b0, b0 + nb):
            t0 = b * bar_s
            deg = song.prog[(b - b0) % len(song.prog)]
            root = song.key - 12 + MAJOR[deg]
            chord = [song.key + MAJOR[(deg + k) % 7] + 12 * ((deg + k) // 7) for k in (0, 2, 4)]
            last_bar = b == b0 + nb - 1
            # drums
            if drums and (kind != "outro" or b == b0):
                for q in range(4):
                    tq = t0 + q * beat
                    if kind == "break":
                        if q in (1, 3):
                            add(clap(0.9), tq, 0.5)
                        continue
                    if song.genre in ("disco", "bounce") or q in (0, 2):
                        add(kick(), tq, 0.9)
                    if song.genre == "march" and q in (1, 3):
                        add(snare(0.8), tq, 0.4)
                    elif q in (1, 3):
                        add(clap() if song.genre in ("bounce", "calypso") else snare(), tq, 0.45)
                    if kind != "intro" or b >= b0 + 2:
                        for e in (0, 1):
                            st = q * 2 + e
                            if song.genre == "disco" and e == 1:
                                add(hat(0.6, open_=True), swing(tq + step, st), 0.18, 0.3)
                            elif song.genre == "calypso":
                                add(shaker(0.8), swing(tq + e * step, st), 0.25, -0.3)
                            else:
                                add(hat(0.5 + 0.3 * e), swing(tq + e * step, st), 0.16, 0.3)
                if last_bar and kind in ("A2", "B2", "B") and drums:            # fill into the next section
                    for k in range(4):
                        add(snare(0.5 + 0.12 * k), t0 + 3 * beat + k * beat / 4, 0.35)
            # bass
            if kind not in ("break",) or b == b0 + nb - 1:
                pattern = {"disco": [(0, 0), (1, 12), (2, 0), (3, 12), (4, 0), (5, 12), (6, 7), (7, 12)],
                           "calypso": [(0, 0), (3, 7), (4, 0), (6, 7)],
                           "march": [(0, 0), (4, 7)],
                           "bounce": [(0, 0), (2, 0), (3, 12), (4, 0), (6, 7), (7, 0)],
                           "lullaby": [(0, 0)]}[song.genre]
                for st, iv in pattern:
                    ln = step * (1.6 if song.genre != "lullaby" else 7)
                    add(bass(hz(root + iv), ln, 0.9), swing(t0 + st * step, st), 0.42)
            # comp (chords)
            for st in {"piano": [2, 6], "stab": [1, 3, 5, 7], "chick": [2, 6], "pad": [0]}[G["comp"]]:
                for m in chord:
                    if G["comp"] == "pad":
                        add(pad(hz(m), bar_s * 0.95), t0, 0.16, 0.0)
                    else:
                        add(piano(hz(m), step * 0.9, 0.8), swing(t0 + st * step, st), 0.11, -0.25)
            # lead melody: motif per 2 bars (A in A sections, B in B sections, rests in intro/break)
            if kind in ("A", "B"):
                mot = motifs[kind]
                rel = (b - b0) % 2
                variation = name.endswith("2") and (b - b0) >= nb - 2
                for st, ln, idx in mot:
                    if st // 8 != rel:
                        continue
                    if variation:
                        idx = min(idx + 2, 9)
                    m = song.key + (0 if song.genre == "lullaby" else 12) + PENTA[idx % 5] + 12 * (idx // 5)
                    tt = swing(t0 + (st % 8) * step, st)
                    add(lead(hz(m), ln * step, 0.9), tt, 0.32, 0.1)
                    if kind == "B" or name == "A2":                        # doubling (lullaby: same octave)
                        add(lead2(hz(m + (0 if song.genre == "lullaby" else 12)), ln * step, 0.5), tt, 0.10, -0.2)
            if kind == "intro" and b >= b0 + 2 and song.genre != "lullaby":                              # pickup sparkle
                add(bell(hz(song.key + 24), step), t0 + 3 * beat, 0.12)
    # small room reverb
    ir_t = _t(1.2)
    ir = (np.random.default_rng(3).standard_normal(len(ir_t)) * np.exp(-ir_t / 0.25)).astype(np.float32)
    ir /= np.sqrt((ir ** 2).sum())
    wl, wr = fftconvolve(L, ir)[:n], fftconvolve(R, ir[::-1].copy())[:n]
    L, R = L + 0.18 * wl, R + 0.18 * wr
    if song.genre == "lullaby":                               # warm and dark: nothing sparkly at bedtime
        sos = butter(2, 2800, btype="low", fs=SR, output="sos")
        L, R = sosfilt(sos, L).astype(np.float32), sosfilt(sos, R).astype(np.float32)
    end = int(song.bars * bar_s * SR)
    fade = np.ones(n, np.float32); fade[end:] = np.linspace(1, 0, n - end)
    st = np.stack([L * fade, R * fade], 1)
    st = np.tanh(st / (np.abs(st).max() + 1e-9) * 1.6) / np.tanh(1.6) * 0.89      # soft limit, peak ≈ −1 dB
    pcm = (st * 32767).astype("<i2").tobytes()
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "2", "-i", "-",
                    "-af", f"loudnorm=I={-20 if song.genre == 'lullaby' else -14}:TP=-1.0:LRA=9", "-ar", str(SR), str(out_wav)], input=pcm, check=True)
    beats = [round(i * beat, 4) for i in range(song.bars * 4 + 1)]
    bmap = {"genre": song.genre, "bpm": song.bpm, "key": song.key, "progression": song.prog, "seed": song.seed,
            "beat_s": beat, "bars": song.bars, "beats": beats,
            "sections": [{"name": nm, "start": round(b0 * bar_s, 4), "end": round((b0 + nb) * bar_s, 4),
                          "bars": nb} for nm, b0, nb in song.sections],
            "duration": round(song.bars * bar_s, 3),
            "license": "Original music synthesized in code — no samples, no AI model"}
    out_wav.with_suffix(".json").write_text(json.dumps(bmap, indent=1))
    return bmap


def main():
    ap = argparse.ArgumentParser(description="Kids dance music in code + beat map")
    ap.add_argument("--genre", choices=sorted(GENRES), default="disco")
    ap.add_argument("--seconds", type=float, default=60)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", default="audio")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    song = plan(a.genre, a.seed, a.seconds)
    p = out / f"{a.genre}_{a.seed}_{int(song.bpm)}bpm.wav"
    m = render(song, p)
    print(f"✅ {p}  {m['duration']:.0f}s  {m['bpm']:.0f} BPM  sections: "
          + " ".join(f"{s['name']}({s['bars']})" for s in m["sections"]))


if __name__ == "__main__":
    main()
