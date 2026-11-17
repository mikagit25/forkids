#!/usr/bin/env python3
"""Our own piano performance of public-domain scores (Mutopia MIDI) -> audio for Sacred Drift.

No third-party recording is used: notes come from the score, sound from the Salamander Grand Piano samples
(Alexander Holm, CC BY 3.0 -> credit in the description). So there is no record label / Content ID owner of the
audio. Only scores with licence Public Domain or CC BY (Mutopia) - CC BY-SA scores are skipped.

Mutopia MIDI files are mechanical (one velocity, no pedal), so the script "performs" them:
  - melody (highest note of each onset) louder than inner voices, bass a little below melody
  - slow dynamic phrasing, gentle rubato (tempo breathes +-5 %), final ritardando
  - bass 12 ms and melody 6 ms ahead of the chord, small random timing/velocity jitter
  - sustain pedal re-taken at every new bass note (legato pedalling); no pedal for Bach/baroque
  - FluidSynth with hall reverb, loudness -18 LUFS (sleep: -20)

    python3 scripts/render_midi_piano.py --midi <file.mid> [--slow 1.08] [--mood sleep|calm] [--seed 3]
    python3 scripts/render_midi_piano.py --list            # usable scores (PD / CC BY)
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import subprocess
import tempfile
from pathlib import Path

import mido

ROOT = Path(__file__).resolve().parent.parent
MUSIC = ROOT / "assets/music/classical/Music"
INDEX = MUSIC / "_licenses_batch4.csv"
SF2 = ROOT / "assets/soundfonts/salamander/SalamanderGrandPiano-V3+20200602.sf2"
OUT = ROOT / "sacred_drift/audio/piano"
LOG = OUT / "piano_log.jsonl"
BAROQUE = ("BachJS", "HandelGF", "ScarlattiD", "CouperinF", "RameauJP", "TelemannGP", "VivaldiA", "PurcellH")


def scores():
    rows = list(csv.DictReader(open(INDEX, encoding="utf-8-sig")))
    return [r for r in rows if "ShareAlike" not in r["license"] and (MUSIC / f"{r['file_base']}.mid").exists()]


def notes_from_midi(path: Path):
    """Absolute-time notes [(start, end, pitch, vel)] in seconds, tempo map applied, drums dropped."""
    mid = mido.MidiFile(path)
    t, on, out = 0.0, {}, []
    for msg in mid:                       # merged tracks, msg.time already in seconds
        t += msg.time
        if msg.type not in ("note_on", "note_off") or getattr(msg, "channel", 0) == 9:
            continue
        key = (msg.channel, msg.note)
        if msg.type == "note_on" and msg.velocity > 0:
            if key in on:                 # re-strike without note_off: close the old note
                s, v = on.pop(key)
                out.append([s, t, msg.note, v])
            on[key] = (t, msg.velocity)
        elif key in on:
            s, v = on.pop(key)
            out.append([s, t, msg.note, v])
    for (ch, n), (s, v) in on.items():
        out.append([s, t, n, v])
    out.sort()
    return [x for x in out if x[1] - x[0] > 0.01]


def perform(notes, rnd: random.Random, slow=1.0, mood="calm", pedal=True):
    if not notes:
        return [], []
    end = max(n[1] for n in notes)
    # onset groups (chords) -> roles
    groups, cur = [], []
    for n in notes:
        if cur and n[0] - cur[0][0] > 0.03:
            groups.append(cur)
            cur = []
        cur.append(n)
    if cur:
        groups.append(cur)
    vels = [n[3] for n in notes]
    span = (max(vels) - min(vels)) or 1
    lo, hi = (26, 78) if mood == "sleep" else (30, 92)
    ph = [rnd.uniform(0, 6.28) for _ in range(3)]

    def dyn(t):      # slow phrasing curve, 0..1
        return 0.5 + 0.22 * math.sin(2 * math.pi * t / 11.0 + ph[0]) + 0.14 * math.sin(2 * math.pi * t / 23.0 + ph[1]) \
               + 0.08 * math.sin(2 * math.pi * t / 5.3 + ph[2])

    def warp(t):     # rubato + final ritardando, returns performed time
        A = 0.05 * 13.0 / (2 * math.pi)                       # +-5 % tempo, 13 s period
        x = t + A * math.sin(2 * math.pi * t / 13.0 + ph[1])
        tail = max(0.0, t - (end - 7.0))                       # last 7 s slow down to ~1.45x
        x += 0.45 * tail * tail / 14.0
        return x * slow

    out = []
    bass_onsets = []
    for g in groups:
        g.sort(key=lambda n: n[2])
        top, bottom = g[-1][2], g[0][2]
        for n in g:
            s, e, p, v = n
            role = "mel" if p == top and len(g) >= 1 else "bass" if (p == bottom and len(g) > 1) else "inner"
            if len(g) == 1 and p < 55:
                role = "bass"
            base = {"mel": 0.80, "bass": 0.62, "inner": 0.45}[role]
            orig = (v - min(vels)) / span                       # keep the editor's accents a little
            x = base * (0.65 + 0.55 * dyn(s)) + 0.12 * (orig - 0.5) + rnd.uniform(-0.035, 0.035)
            vel = int(round(lo + (hi - lo) * min(max(x, 0), 1)))
            lead = {"mel": -0.006, "bass": -0.012, "inner": 0.0}[role]
            ps = warp(s) + lead + rnd.gauss(0, 0.005)
            pe = warp(e) + (0.04 if not pedal else 0.0)          # slight legato overlap without pedal
            out.append((max(ps, 0.0), max(pe, ps + 0.03), p, vel))
        if pedal and bottom < 60:
            bass_onsets.append(warp(g[0][0]))
    ped = []
    if pedal:
        last = -9.0
        for b in bass_onsets:
            if b - last < 0.35:          # fast bass lines: keep the pedal, don't flutter
                continue
            ped.append((max(b - 0.015, 0), 0))      # up just before the new harmony
            ped.append((b + 0.07, 127))               # down right after it
            last = b
        ped.append((warp(end) + 0.5, 0))
    return out, ped


def write_midi(perf, ped, path: Path):
    tpq, bpm = 960, 120
    sec2tick = tpq * bpm / 60.0
    ev = [(s, 1, mido.Message("note_on", note=p, velocity=v)) for s, e, p, v in perf]
    ev += [(e, 0, mido.Message("note_off", note=p, velocity=0)) for s, e, p, v in perf]
    ev += [(t, 0 if val == 0 else 2, mido.Message("control_change", control=64, value=val)) for t, val in ped]
    ev.sort(key=lambda x: (x[0], x[1]))
    mf = mido.MidiFile(ticks_per_beat=tpq)
    tr = mido.MidiTrack()
    mf.tracks.append(tr)
    tr.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(bpm)))
    tr.append(mido.Message("program_change", program=0))
    last = 0
    for t, _, m in ev:
        tick = int(round(t * sec2tick))
        tr.append(m.copy(time=max(0, tick - last)))
        last = max(last, tick)
    mf.save(path)


def render(midi: Path, slow=1.0, mood="calm", seed=1, out_name=None, meta=None):
    rnd = random.Random(seed)
    meta = meta or {}
    pedal = meta.get("composer") not in BAROQUE
    perf, ped = perform(notes_from_midi(midi), rnd, slow, mood, pedal)
    OUT.mkdir(parents=True, exist_ok=True)
    name = out_name or f"{midi.stem}_s{seed}"
    with tempfile.TemporaryDirectory() as td:
        pm, wav = Path(td) / "perf.mid", Path(td) / "raw.wav"
        write_midi(perf, ped, pm)
        subprocess.run(["fluidsynth", "-ni", "-q", "-F", str(wav), "-r", "48000", "-g", "0.5",
                        "-o", "synth.reverb.active=1", "-o", "synth.reverb.room-size=0.82", "-o", "synth.reverb.damp=0.35",
                        "-o", "synth.reverb.width=0.9", "-o", "synth.reverb.level=0.55", "-o", "synth.chorus.active=0",
                        str(SF2), str(pm)], check=True, capture_output=True)
        target = -20 if mood == "sleep" else -18
        mp3 = OUT / f"{name}.mp3"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav),
                        "-af", f"apad=pad_dur=3,afade=t=in:d=0.05,loudnorm=I={target}:TP=-2:LRA=14,"
                               "aresample=44100", "-b:a", "256k", str(mp3)], check=True)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp3)],
                               capture_output=True, text=True).stdout or 0)
    rec = {"file": mp3.name, "midi": midi.name, "seed": seed, "slow": slow, "mood": mood, "pedal": pedal,
           "duration_sec": round(dur, 1), **{k: meta.get(k) for k in ("composer", "title", "license", "source")},
           "instrument": "Salamander Grand Piano (Alexander Holm, CC BY 3.0)", "performance": "procedural (render_midi_piano.py)"}
    with open(LOG, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"{mp3}  {dur / 60:.1f} min  pedal={pedal}")
    return mp3, rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--midi")
    ap.add_argument("--slow", type=float, default=1.0)
    ap.add_argument("--mood", default="calm", choices=["calm", "sleep"])
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    rows = scores()
    if a.list:
        for r in rows:
            print(f"{r['license'][:14]:14s} {r['composer']:13s} {r['title'][:60]:60s} {r['file_base']}")
        print(len(rows), "usable scores")
        return
    midi = Path(a.midi) if Path(a.midi).exists() else MUSIC / a.midi
    meta = next((r for r in rows if r["file_base"] == midi.stem), None)
    if meta is None:
        raise SystemExit(f"{midi.name}: not in the PD / CC BY list of {INDEX.name} - not used (licence unknown or BY-SA)")
    render(midi, a.slow, a.mood, a.seed, meta=meta)


if __name__ == "__main__":
    main()
