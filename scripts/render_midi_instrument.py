#!/usr/bin/env python3
"""Render a public-domain MIDI score on another instrument (or as written, for orchestral scores) with FluidSynth
and the FluidR3_GM soundfont (MIT licence) — our own performance, no existing recording is used.

    python3 scripts/render_midi_instrument.py --midi <file_base or path> --instrument harp [--seconds 60] [--out x.mp3]
    instruments: harp, guitar, celesta, musicbox, strings, flute, vibes, organ, harpsichord, orchestra (keep programs)

Every note keeps its timing; velocities are softened a little (calm), all channels are moved to the chosen instrument
(drums dropped). A short room reverb + -18 LUFS loudness normalisation is applied with ffmpeg.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

import mido

ROOT = Path(__file__).resolve().parent.parent
MUSIC = ROOT / "assets/music/classical/Music"
SF2 = "/usr/share/sounds/sf2/FluidR3_GM.sf2"
OUT = ROOT / "sacred_drift/audio/instrument_renders"
GM = {"harp": 46, "guitar": 24, "celesta": 8, "musicbox": 10, "strings": 48, "flute": 73, "vibes": 11,
      "organ": 19, "harpsichord": 6, "orchestra": None}


def retarget(src: Path, dst: Path, instrument: str, soft: float = 0.85, slow: float = 1.0):
    mid = mido.MidiFile(src)
    prog = GM[instrument]
    for tr in mid.tracks:
        keep = []
        for msg in tr:
            if hasattr(msg, "channel") and msg.channel == 9:          # drums out
                msg = mido.MetaMessage("text", text="", time=msg.time) if not msg.is_meta else msg
            if prog is not None and msg.type == "program_change":
                msg = msg.copy(program=prog)
            if msg.type == "note_on" and msg.velocity > 0:
                msg = msg.copy(velocity=max(18, min(110, int(msg.velocity * soft))))
            if msg.type == "set_tempo" and slow != 1.0:
                msg = msg.copy(tempo=int(msg.tempo * slow))
            keep.append(msg)
        tr[:] = keep
    if prog is not None:                         # a program change at the start of every channel used
        chans = sorted({m.channel for tr in mid.tracks for m in tr if hasattr(m, "channel") and m.channel != 9})
        mid.tracks[0][0:0] = [mido.Message("program_change", channel=c, program=prog, time=0) for c in chans]
    mid.save(dst)


def render(midi: Path, instrument: str, out: Path, seconds: float | None = None, slow: float = 1.0):
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        m2 = Path(td) / "x.mid"
        wav = Path(td) / "x.wav"
        retarget(midi, m2, instrument, slow=slow)
        subprocess.run(["fluidsynth", "-ni", "-g", "0.7", "-r", "44100", "-F", str(wav), SF2, str(m2)],
                       check=True, capture_output=True)
        af = "aecho=0.8:0.5:60|110:0.25|0.15,loudnorm=I=-18:TP=-2,afade=t=out:st=0:d=0"
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav)]
        if seconds:
            cmd += ["-t", str(seconds)]
        cmd += ["-af", af.replace(",afade=t=out:st=0:d=0", ""), "-c:a", "libmp3lame", "-b:a", "256k", str(out)]
        subprocess.run(cmd, check=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--midi", required=True)
    ap.add_argument("--instrument", default="harp", choices=sorted(GM))
    ap.add_argument("--seconds", type=float)
    ap.add_argument("--slow", type=float, default=1.0)
    ap.add_argument("--out")
    a = ap.parse_args()
    midi = Path(a.midi) if a.midi.endswith(".mid") else MUSIC / f"{a.midi}.mid"
    out = Path(a.out) if a.out else OUT / f"{midi.stem}_{a.instrument}.mp3"
    print(render(midi, a.instrument, out, a.seconds, a.slow))


if __name__ == "__main__":
    main()
