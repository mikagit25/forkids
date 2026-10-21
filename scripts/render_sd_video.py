#!/usr/bin/env python3
"""
Sacred Drift — audio-reactive video: music track + procedural scene → finished MP4.

The audio is analysed once (audio_reactive.py) and every frame of the scene reacts to it:
  • whole picture breathes with loudness (soft brightness/glow pulse)
  • bowls / lake:      ripples spread on the water at every detected strike
  • solfeggio/mandala: geometry breathes with the bass, circular equalizer ring around it
  • cosmic:            stars twinkle with highs, a shooting star on strikes
  • rain / window:     drops slide faster in the downpour gusts, lights breathe
  • sleep / night:     moon halo pulses gently
  • morning / sunrise: light rays follow the music

Scene + seed come from the track's ambient_log.jsonl entry when available (same seed as the
music → picture and sound belong together), otherwise from --scene / --seed.

Usage:
  python3 scripts/render_sd_video.py --audio "sacred_drift/audio/code_ambient/Slow Tibetan … (707).mp3"
  python3 scripts/render_sd_video.py --audio track.mp3 --scene mandala --seconds 30 --out /tmp/demo.mp4

Speed: ~40–60 ms per frame at the default 960×540 render (upscaled to 1080p), i.e. roughly
1–1.5 h of rendering per hour of video on one core. Run overnight / after the daily music.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import audio_reactive  # noqa: E402
import sd_scenes  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "sacred_drift" / "output" / "queue"


def track_info(audio: Path) -> dict:
    log = audio.parent / "ambient_log.jsonl"
    if log.exists():
        for line in reversed(log.read_text().splitlines()):
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("file") == audio.name:
                return r
    return {}


def main():
    ap = argparse.ArgumentParser(description="Audio-reactive Sacred Drift video")
    ap.add_argument("--audio", required=True)
    ap.add_argument("--scene", choices=sorted(sd_scenes.SCENES), default=None)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--seconds", type=float, default=None, help="render only the first N seconds (preview)")
    ap.add_argument("--start", type=float, default=0.0, help="preview: start at this second of the track")
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--w", type=int, default=960, help="render width (upscaled to --out-w)")
    ap.add_argument("--h", type=int, default=540)
    ap.add_argument("--out-w", type=int, default=1920)
    ap.add_argument("--out-h", type=int, default=1080)
    ap.add_argument("--no-eq", action="store_true", help="no equalizer ring on the mandala")
    a = ap.parse_args()

    audio = Path(a.audio)
    info = track_info(audio)
    style = info.get("style")
    seed = a.seed if a.seed is not None else info.get("seed", 1)
    scene = a.scene or (sd_scenes.pick_scene(style, seed) if style else "lake")
    hz = (info.get("params") or {}).get("hz")
    out = Path(a.out) if a.out else QUEUE / (audio.stem + ".mp4")
    out.parent.mkdir(parents=True, exist_ok=True)

    print(f"🎧 analysing {audio.name} …")
    F = audio_reactive.analyze(str(audio), a.fps)
    f0 = int(a.start * a.fps)
    n = F["frames"] - f0 if not a.seconds else min(F["frames"] - f0, int(a.seconds * a.fps))
    onsets = set(int(i) for i in F["onsets"])
    strength = {int(i): float(s) for i, s in zip(F["onsets"], F["onset_strength"])}
    print(f"   {F['frames'] / a.fps / 60:.1f} min, {len(onsets)} strikes detected → scene={scene} seed={seed}"
          + (f" hz={hz}" if hz else ""))

    P = sd_scenes.params(scene, seed, hz)
    C: dict = {}
    rng = np.random.default_rng(seed + 17)
    ripples: list[list] = []          # [birth_frame, strength, x offset]
    meteors: list[list] = []          # [birth_frame, (x, y, angle, length)]
    rain_t = 0.0

    # replay strikes that happened before the preview start, so the first frames aren't empty
    for i in range(max(0, f0 - a.fps * 12), f0):
        if i in onsets:
            ripples.append([i, strength[i], rng.uniform(-0.05, 0.05) * a.w])

    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{a.w}x{a.h}",
           "-r", str(a.fps), "-i", "-", "-ss", f"{a.start:.3f}", "-i", str(audio), "-t", f"{n / a.fps:.3f}",
           "-vf", f"scale={a.out_w}:{a.out_h}:flags=bicubic", "-c:v", "libx264", "-preset", "medium",
           "-crf", "23", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    for k in range(n):
        i = f0 + k
        t = i / a.fps
        env = float(F["env"][i])
        if i in onsets:
            s = strength[i]
            ripples.append([i, s, rng.uniform(-0.05, 0.05) * a.w])
            ang = rng.uniform(math.radians(20), math.radians(40)) * (1 if rng.random() < 0.5 else -1)
            sx = rng.uniform(0.15, 0.85) * a.w
            meteors.append([i, (sx, rng.uniform(0.05, 0.35) * a.h, ang if ang > 0 else math.pi + ang, a.w * 0.25)])
        ripples = [r for r in ripples if (i - r[0]) / a.fps < 13]
        meteors = [m for m in meteors if (i - m[0]) / a.fps < 1.5]
        rain_t += (0.55 + 0.9 * env) / a.fps
        P["rx"] = {
            "env": env, "low": float(F["low"][i]), "mid": float(F["mid"][i]), "high": float(F["high"][i]),
            "spectrum": None if a.no_eq else F["spectrum"][i],
            "ripples": [((i - b) / a.fps, s, dx) for b, s, dx in ripples],
            "meteors": [((i - b) / a.fps, m) for b, m in meteors],
            "rain_t": rain_t,
        }
        img = sd_scenes.frame(scene, t, a.w, a.h, P, C)
        arr = np.asarray(img, np.float32) * (0.94 + 0.10 * env)       # whole picture breathes with the music
        proc.stdin.write(np.clip(arr, 0, 255).astype(np.uint8).tobytes())
        if k and k % (a.fps * 60) == 0:
            el = time.time() - t0
            print(f"   {k / a.fps / 60:5.1f}/{n / a.fps / 60:.1f} min  ({el / k * 1000:.0f} ms/frame, "
                  f"ETA {el / k * (n - k) / 60:.0f} min)")
    proc.stdin.close()
    if proc.wait() != 0:
        sys.exit("ffmpeg failed")
    print(f"✅ {out}  ({n / a.fps:.0f}s video, {time.time() - t0:.0f}s render)")


if __name__ == "__main__":
    main()
