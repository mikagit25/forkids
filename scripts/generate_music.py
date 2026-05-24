#!/usr/bin/env python3
"""
Generates royalty-free children's music loops using synthesis.
Produces WAV files ready for use in video generation.

Usage: python3 scripts/generate_music.py
"""

import wave
import struct
import math
import random
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MUSIC_DIR = ROOT / "assets" / "music"


def adsr(length: int, sr: int, attack=0.01, decay=0.05, sustain=0.7, release=0.1) -> np.ndarray:
    """ADSR envelope."""
    a = int(attack * sr)
    d = int(decay * sr)
    r = int(release * sr)
    s = max(0, length - a - d - r)
    env = np.concatenate([
        np.linspace(0, 1, a),
        np.linspace(1, sustain, d),
        np.full(s, sustain),
        np.linspace(sustain, 0, r),
    ])
    return env[:length]


def sine(freq: float, length: int, sr: int, phase=0.0) -> np.ndarray:
    t = np.arange(length) / sr
    return np.sin(2 * np.pi * freq * t + phase)


def xylophone(freq: float, length: int, sr: int) -> np.ndarray:
    """Bright xylophone-like tone: fundamental + harmonics, fast decay."""
    t = np.arange(length) / sr
    tone = (
        np.sin(2 * np.pi * freq * t) * 1.0 +
        np.sin(2 * np.pi * freq * 2 * t) * 0.5 +
        np.sin(2 * np.pi * freq * 3 * t) * 0.2 +
        np.sin(2 * np.pi * freq * 4 * t) * 0.1
    )
    env = np.exp(-t * 8)
    return tone * env


def piano(freq: float, length: int, sr: int) -> np.ndarray:
    """Soft piano-like tone."""
    t = np.arange(length) / sr
    tone = (
        np.sin(2 * np.pi * freq * t) * 1.0 +
        np.sin(2 * np.pi * freq * 2 * t) * 0.3 +
        np.sin(2 * np.pi * freq * 0.5 * t) * 0.15
    )
    env = adsr(length, sr, attack=0.005, decay=0.1, sustain=0.6, release=0.2)
    return tone * env


def bass_note(freq: float, length: int, sr: int) -> np.ndarray:
    """Warm bass."""
    t = np.arange(length) / sr
    tone = (
        np.sin(2 * np.pi * freq * t) * 1.0 +
        np.sin(2 * np.pi * freq * 2 * t) * 0.4 +
        np.sin(2 * np.pi * freq * 3 * t) * 0.1
    )
    env = adsr(length, sr, attack=0.01, decay=0.1, sustain=0.5, release=0.15)
    return tone * env


def kick(length: int, sr: int) -> np.ndarray:
    """Punchy kick drum."""
    t = np.arange(length) / sr
    freq = 120 * np.exp(-t * 30)
    tone = np.sin(2 * np.pi * np.cumsum(freq) / sr)
    env = np.exp(-t * 18)
    return tone * env


def snare(length: int, sr: int) -> np.ndarray:
    """Snappy snare."""
    t = np.arange(length) / sr
    noise = np.random.randn(length)
    tone = np.sin(2 * np.pi * 200 * t)
    env = np.exp(-t * 25)
    return (0.5 * tone + 0.5 * noise) * env


def hihat(length: int, sr: int, open_=False) -> np.ndarray:
    """Hi-hat."""
    t = np.arange(length) / sr
    noise = np.random.randn(length)
    # High-pass filter effect (just use high freq noise)
    decay = 6 if not open_ else 2
    env = np.exp(-t * decay)
    return noise * env * 0.4


def add_reverb(signal: np.ndarray, sr: int, delay=0.06, decay=0.35) -> np.ndarray:
    """Simple comb filter reverb."""
    delay_samples = int(delay * sr)
    out = signal.copy()
    for i in range(delay_samples, len(signal)):
        out[i] += out[i - delay_samples] * decay
    return out


def note_freq(note: str) -> float:
    """Note name to frequency. e.g. 'C4', 'G4', 'A5'"""
    notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    name = note[:-1]
    octave = int(note[-1])
    semitone = notes.index(name)
    midi = (octave + 1) * 12 + semitone
    return 440.0 * (2 ** ((midi - 69) / 12))


def mix(*signals, weights=None) -> np.ndarray:
    """Mix signals together."""
    if weights is None:
        weights = [1.0] * len(signals)
    length = max(len(s) for s in signals)
    out = np.zeros(length)
    for s, w in zip(signals, weights):
        out[:len(s)] += s * w
    return out


def save_wav(path: str, audio: np.ndarray, sr: int) -> None:
    audio = np.clip(audio, -1, 1)
    data = (audio * 32767).astype(np.int16)
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(data.tobytes())


# ── Track generators ───────────────────────────────────────────────────────────

def generate_happy_kids(output_path: str, bpm=120, bars=16) -> None:
    """Upbeat happy children's track — xylophone melody + bass + drums."""
    sr = 44100
    beat = 60 / bpm
    bar = beat * 4
    total = bar * bars
    N = int(sr * total)
    out = np.zeros(N)

    # C major pentatonic: C D E G A
    scale = {
        'C4': note_freq('C4'), 'D4': note_freq('D4'), 'E4': note_freq('E4'),
        'G4': note_freq('G4'), 'A4': note_freq('A4'),
        'C5': note_freq('C5'), 'D5': note_freq('D5'), 'E5': note_freq('E5'),
        'G5': note_freq('G5'),
    }

    # Melody pattern (repeats every 4 bars)
    melody = [
        ('C5',0), ('E5',0.5), ('G5',1), ('E5',1.5),
        ('D5',2), ('C5',2.5), ('E5',3), ('G5',3.5),
        ('A4',4), ('C5',4.5), ('E5',5), ('D5',5.5),
        ('C5',6), ('G4',6.5), ('A4',7), ('C5',7.5),
    ]

    for bar_i in range(bars):
        bar_t = bar_i * bar
        pattern_t = (bar_i % 4) * bar
        for note, beat_offset in melody:
            t_start = int((bar_t + beat_offset * beat) * sr)
            note_len = int(beat * 0.9 * sr)
            end = min(t_start + note_len, N)
            seg = xylophone(scale[note], end - t_start, sr)
            out[t_start:end] += seg * 0.45

    # Bass line (root notes)
    bass_notes = [note_freq('C3'), note_freq('G2'), note_freq('A2'), note_freq('F2')]
    for bar_i in range(bars):
        freq = bass_notes[bar_i % len(bass_notes)]
        for beat_i in range(4):
            t_start = int((bar_i * bar + beat_i * beat) * sr)
            note_len = int(beat * 0.7 * sr)
            end = min(t_start + note_len, N)
            seg = bass_note(freq, end - t_start, sr)
            out[t_start:end] += seg * 0.35

    # Chords (piano pad, every bar)
    chord_freqs = [
        [note_freq('C4'), note_freq('E4'), note_freq('G4')],   # C
        [note_freq('G3'), note_freq('B3'), note_freq('D4')],   # G
        [note_freq('A3'), note_freq('C4'), note_freq('E4')],   # Am
        [note_freq('F3'), note_freq('A3'), note_freq('C4')],   # F
    ]
    for bar_i in range(bars):
        chord = chord_freqs[bar_i % len(chord_freqs)]
        t_start = int(bar_i * bar * sr)
        chord_len = int(bar * 0.9 * sr)
        end = min(t_start + chord_len, N)
        for freq in chord:
            seg = piano(freq, end - t_start, sr)
            out[t_start:end] += seg * 0.12

    # Drums
    kick_len = int(0.15 * sr)
    snare_len = int(0.12 * sr)
    hh_len = int(0.05 * sr)
    kick_pat = [0, 2.5]          # beats 1 and "and of 2"
    snare_pat = [1, 3]           # beats 2 and 4
    hh_pat = [i * 0.5 for i in range(8)]  # every 8th note

    for bar_i in range(bars):
        bar_t = bar_i * bar
        for b in kick_pat:
            t = int((bar_t + b * beat) * sr)
            end = min(t + kick_len, N)
            out[t:end] += kick(end - t, sr) * 0.7
        for b in snare_pat:
            t = int((bar_t + b * beat) * sr)
            end = min(t + snare_len, N)
            out[t:end] += snare(end - t, sr) * 0.5
        for b in hh_pat:
            t = int((bar_t + b * beat) * sr)
            end = min(t + hh_len, N)
            out[t:end] += hihat(end - t, sr) * 0.3

    out = add_reverb(out, sr, delay=0.08, decay=0.25)
    out = out / max(abs(out.max()), 0.01) * 0.88
    save_wav(output_path, out, sr)


def generate_bouncy_fun(output_path: str, bpm=128, bars=16) -> None:
    """Faster, bouncy track with more energy."""
    sr = 44100
    beat = 60 / bpm
    bar = beat * 4
    total = bar * bars
    N = int(sr * total)
    out = np.zeros(N)

    # G major: G A B D E
    freqs = {
        'G4': note_freq('G4'), 'A4': note_freq('A4'), 'B4': note_freq('B4'),
        'D5': note_freq('D5'), 'E5': note_freq('E5'), 'G5': note_freq('G5'),
        'G3': note_freq('G3'), 'D3': note_freq('D3'),
    }

    melody = [
        ('G4',0), ('B4',0.5), ('D5',1), ('B4',1.5),
        ('E5',2), ('D5',2.5), ('B4',3), ('G4',3.5),
        ('A4',4), ('G4',4.5), ('E5',5), ('D5',5.5),
        ('G5',6), ('E5',6.5), ('D5',7), ('B4',7.5),
    ]

    for bar_i in range(bars):
        bar_t = bar_i * bar
        for note, beat_off in melody:
            t_start = int((bar_t + beat_off * beat) * sr)
            nlen = int(beat * 0.85 * sr)
            end = min(t_start + nlen, N)
            seg = xylophone(freqs[note], end - t_start, sr)
            out[t_start:end] += seg * 0.4

    # Bass
    bass_seq = ['G3', 'D3', 'G3', 'D3']
    for bar_i in range(bars):
        freq = note_freq(bass_seq[bar_i % len(bass_seq)])
        for b in range(4):
            t_start = int((bar_i * bar + b * beat) * sr)
            nlen = int(beat * 0.6 * sr)
            end = min(t_start + nlen, N)
            seg = bass_note(freq, end - t_start, sr)
            out[t_start:end] += seg * 0.3

    # Drums (faster pattern)
    kick_len, snare_len, hh_len = int(0.12*sr), int(0.10*sr), int(0.04*sr)
    for bar_i in range(bars):
        bar_t = bar_i * bar
        for b in [0, 1.75, 2, 3.5]:
            t = int((bar_t + b * beat) * sr)
            end = min(t + kick_len, N)
            out[t:end] += kick(end - t, sr) * 0.75
        for b in [1, 3]:
            t = int((bar_t + b * beat) * sr)
            end = min(t + snare_len, N)
            out[t:end] += snare(end - t, sr) * 0.55
        for b in [i * 0.25 for i in range(16)]:
            t = int((bar_t + b * beat) * sr)
            end = min(t + hh_len, N)
            out[t:end] += hihat(end - t, sr, open_=(b % 1.0 == 0)) * 0.25

    out = add_reverb(out, sr, delay=0.05, decay=0.2)
    out = out / max(abs(out.max()), 0.01) * 0.88
    save_wav(output_path, out, sr)


def generate_gentle_wonder(output_path: str, bpm=100, bars=16) -> None:
    """Softer, dreamy track — good for calmer scenes."""
    sr = 44100
    beat = 60 / bpm
    bar = beat * 4
    total = bar * bars
    N = int(sr * total)
    out = np.zeros(N)

    # F major: F G A C D
    freqs = {
        'F4': note_freq('F4'), 'G4': note_freq('G4'), 'A4': note_freq('A4'),
        'C5': note_freq('C5'), 'D5': note_freq('D5'), 'F5': note_freq('F5'),
        'F3': note_freq('F3'), 'C3': note_freq('C3'),
    }
    melody = [
        ('F4',0), ('A4',1), ('C5',2), ('A4',3),
        ('D5',4), ('C5',5), ('A4',6), ('F4',7),
        ('G4',8), ('A4',9), ('C5',10), ('D5',11),
        ('C5',12), ('A4',13), ('F5',14), ('C5',15),
    ]

    for bar_i in range(bars):
        bar_t = bar_i * bar
        offset = (bar_i % 4) * 4
        for note, beat_off in melody:
            if beat_off >= offset * beat and beat_off < (offset + 4) * beat:
                t_start = int((bar_t + (beat_off - offset) * beat) * sr)
                nlen = int(beat * 1.2 * sr)
                end = min(t_start + nlen, N)
                seg = piano(freqs[note], end - t_start, sr)
                out[t_start:end] += seg * 0.5

    # Simple bass
    for bar_i in range(bars):
        freq = note_freq(['F3','C3','F3','C3'][bar_i % 4])
        t_start = int(bar_i * bar * sr)
        nlen = int(bar * 0.8 * sr)
        end = min(t_start + nlen, N)
        seg = bass_note(freq, end - t_start, sr)
        out[t_start:end] += seg * 0.25

    # Soft drums — just kick and light hh
    kick_len = int(0.12 * sr)
    hh_len = int(0.05 * sr)
    for bar_i in range(bars):
        bar_t = bar_i * bar
        for b in [0, 2]:
            t = int((bar_t + b * beat) * sr)
            end = min(t + kick_len, N)
            out[t:end] += kick(end - t, sr) * 0.5
        for b in [i * 0.5 for i in range(8)]:
            t = int((bar_t + b * beat) * sr)
            end = min(t + hh_len, N)
            out[t:end] += hihat(end - t, sr) * 0.15

    out = add_reverb(out, sr, delay=0.12, decay=0.4)
    out = out / max(abs(out.max()), 0.01) * 0.85
    save_wav(output_path, out, sr)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    MUSIC_DIR.mkdir(parents=True, exist_ok=True)

    tracks = [
        ("happy_loop_1.wav",   generate_happy_kids,    dict(bpm=120, bars=16)),
        ("happy_loop_2.wav",   generate_bouncy_fun,    dict(bpm=128, bars=16)),
        ("gentle_loop_1.wav",  generate_gentle_wonder, dict(bpm=100, bars=16)),
    ]

    print("Generating music tracks...")
    for filename, fn, kwargs in tracks:
        path = str(MUSIC_DIR / filename)
        print(f"  {filename} ...", end=" ", flush=True)
        fn(path, **kwargs)
        size = Path(path).stat().st_size // 1024
        print(f"done ({size} KB)")

    print(f"\n✓ {len(tracks)} tracks saved to {MUSIC_DIR}")


if __name__ == "__main__":
    main()
