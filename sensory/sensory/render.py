"""Rendering: stills (step 1) and beat-locked clips (step 2+) → PNG / MP4 via ffmpeg pipe."""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

from .characters import CHARACTERS
from .easing import beat_phase, dance_pose
from .style import add_glow, flatten, over, surface, to_array


def compose(items, w=1920, h=1080, t=0.0, rgba=False) -> np.ndarray:
    """items = [(character, cx, cy, r, pose), ...] → RGB uint8 frame."""
    canvas = np.zeros((h, w, 4), np.float32)
    for ch, cx, cy, r, pose in items:
        x, y = cx + pose.get("dx", 0), cy + pose.get("dy", 0)
        half = int(r * 1.9)                                   # box: body + crown + squash + glow margin
        x0, y0 = int(x) - half, int(y) - int(r * 2.0)
        bw, bh = half * 2, int(r * 3.9)
        s, ctx = surface(bw, bh)
        ch.draw(ctx, x - x0, y - y0, r, t, pose.get("sx", 1), pose.get("sy", 1), pose.get("tilt", 0),
                pose.get("look", (0, 0)), pose.get("smile", 1.0), pose.get("happy", False),
                pose.get("sleepy", False))
        layer = to_array(s)
        layer = over(add_glow(layer, ch.glow_color, radius=r * 0.12, strength=0.6), layer)
        # paste the box into the frame (clipped at the edges)
        cx0, cy0, cx1, cy1 = max(x0, 0), max(y0, 0), min(x0 + bw, w), min(y0 + bh, h)
        if cx1 > cx0 and cy1 > cy0:
            sub = layer[cy0 - y0:cy1 - y0, cx0 - x0:cx1 - x0]
            canvas[cy0:cy1, cx0:cx1] = over(canvas[cy0:cy1, cx0:cx1], sub)
    return canvas if rgba else flatten(canvas)


def render_still(cast, w=1920, h=1080, t=0.0):
    items = [(CHARACTERS[n](seed=i + 1), cx, cy, r, {}) for i, (n, cx, cy, r) in enumerate(cast)]
    return compose(items, w, h, t)


def render_clip(out: Path, seconds: float, bpm: float, cast, fps=30, w=1920, h=1080, audio: str | None = None):
    """cast = [(name, cx, cy, r, move, beat_offset), ...]"""
    chars = [CHARACTERS[c[0]](seed=i + 1) for i, c in enumerate(cast)]
    cmd = ["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
           "-r", str(fps), "-i", "-"]
    if audio:
        cmd += ["-i", audio, "-shortest", "-c:a", "aac", "-b:a", "192k"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(int(seconds * fps)):
        t = f / fps
        items = []
        for ch, (name, cx, cy, r, move, off) in zip(chars, cast):
            b, ph = beat_phase(t, bpm, off)
            items.append((ch, cx, cy, r, dance_pose(b, ph, move)))
        p.stdin.write(compose(items, w, h, t).tobytes())
    p.stdin.close()
    if p.wait():
        raise RuntimeError("ffmpeg failed")


def beatmap_phase(bmap: dict, t: float, offset: float = 0.0) -> tuple[int, float]:
    """Beat index + phase from the music's beat map (exact, also for tempo changes)."""
    import bisect
    beats = bmap["beats"]
    tt = t - offset * bmap["beat_s"]
    i = max(0, bisect.bisect_right(beats, tt) - 1)
    if i >= len(beats) - 1:
        return i, 0.0
    return i, (tt - beats[i]) / (beats[i + 1] - beats[i])


SECTION_ENERGY = {"intro": 0.55, "A": 1.0, "A2": 1.05, "B": 1.2, "B2": 1.2, "break": 0.45, "outro": 0.6}


def section_at(bmap: dict, t: float) -> str:
    for s in bmap["sections"]:
        if s["start"] <= t < s["end"]:
            return s["name"]
    return "outro"


def render_to_music(out: Path, audio: str, cast, seconds: float | None = None, fps=30, w=1920, h=1080):
    """Dance to a sensory.music track: beats from its JSON beat map, energy from the song section."""
    import json
    bmap = json.loads(Path(audio).with_suffix(".json").read_text())
    seconds = seconds or bmap["duration"] + 1.5
    chars = [CHARACTERS[c[0]](seed=i + 1) for i, c in enumerate(cast)]
    cmd = ["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
           "-r", str(fps), "-i", "-", "-i", audio, "-t", f"{seconds:.2f}", "-c:a", "aac", "-b:a", "192k",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
           str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    energy = 0.5
    for f in range(int(seconds * fps)):
        t = f / fps
        target = SECTION_ENERGY.get(section_at(bmap, t), 1.0)
        energy += (target - energy) * 0.08                    # smooth change between sections
        items = []
        for ch, (name, cx, cy, r, move, off) in zip(chars, cast):
            b, ph = beatmap_phase(bmap, t, off)
            items.append((ch, cx, cy, r, dance_pose(b, ph, move, energy)))
        p.stdin.write(compose(items, w, h, t).tobytes())
    p.stdin.close()
    if p.wait():
        raise RuntimeError("ffmpeg failed")


def _high_contrast(frame: np.ndarray) -> np.ndarray:
    """Convert frame to grayscale + boost contrast for newborn high-contrast mode."""
    gray = (frame[..., 0] * 0.299 + frame[..., 1] * 0.587 + frame[..., 2] * 0.114).astype(np.float32) / 255
    # stretch: darks → black, lights → white
    lo, hi = np.percentile(gray[gray > 0.02], [2, 98]) if gray.max() > 0.02 else (0.0, 1.0)
    gray = np.clip((gray - lo) / max(hi - lo, 0.01), 0, 1)
    rgb = (gray[..., None] * 255).astype(np.uint8)
    return np.concatenate([rgb, rgb, rgb], axis=2)


def _render_range(args):
    """Worker: frames [f0, f1) of an episode → video-only mp4."""
    import json
    audio, scenes, f0, f1, fps, w, h, path, high_contrast = args
    from .timeline import energy_at, frame_items
    bmap = json.loads(Path(audio).with_suffix(".json").read_text())
    cmd = ["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
           "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
           str(path)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    ph = lambda t, off: beatmap_phase(bmap, t, off)        # noqa: E731
    for f in range(f0, f1):
        t = f / fps
        frame = compose(frame_items(scenes, bmap, t, ph, energy_at(bmap, t), w, h), w, h, t)
        if high_contrast:
            frame = _high_contrast(frame)
        p.stdin.write(frame.tobytes())
    p.stdin.close()
    if p.wait():
        raise RuntimeError("ffmpeg failed")
    return path


def render_episode(out: Path, audio: str, pool: list[str], seed: int, fps=30, w=1920, h=1080,
                   workers: int | None = None, seconds: float | None = None,
                   high_contrast: bool = False):
    """Song + character pool → finished mp4. Frames are split across CPU cores, then concatenated."""
    import json
    import os
    import tempfile
    from multiprocessing import Pool
    from .timeline import build
    bmap = json.loads(Path(audio).with_suffix(".json").read_text())
    scenes = build(bmap, pool, seed)
    total = int((seconds or bmap["duration"] + 1.0) * fps)
    workers = workers or os.cpu_count() or 1
    with tempfile.TemporaryDirectory() as td:
        bounds = [total * i // workers for i in range(workers + 1)]
        jobs = [(audio, scenes, bounds[i], bounds[i + 1], fps, w, h, Path(td) / f"part{i}.mp4", high_contrast)
                for i in range(workers)]
        with Pool(workers) as pool_:
            parts = pool_.map(_render_range, jobs)
        lst = Path(td) / "list.txt"
        lst.write_text("".join(f"file '{p}'\n" for p in parts))
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                        "-i", audio, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                        "-t", f"{total / fps:.3f}", "-movflags", "+faststart", str(out)], check=True)
    return scenes


def click_track(path: Path, seconds: float, bpm: float, sr=44100):
    """Metronome so the sync can be checked by ear: accent on every 4th beat."""
    n = int(seconds * sr); y = np.zeros(n, np.float32)
    k = np.arange(int(0.05 * sr)) / sr
    for i in range(int(seconds * bpm / 60) + 1):
        s = int(i * 60 / bpm * sr)
        f = 1500 if i % 4 == 0 else 1000
        c = np.sin(2 * np.pi * f * k) * np.exp(-k / 0.01) * (0.6 if i % 4 == 0 else 0.35)
        y[s:s + len(c)] += c[: max(0, min(len(c), n - s))]
    pcm = (np.clip(y, -1, 1) * 32767).astype("<i2").tobytes()
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "s16le", "-ar", str(sr), "-ac", "1", "-i", "-",
                    str(path)], input=pcm, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", type=int, default=2)
    ap.add_argument("--out", default="out")
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    if a.step == 1:
        Image.fromarray(render_still([("berry", 960, 520, 300)])).save(out / "step1_berry.png")
        Image.fromarray(render_still([("pear", 480, 560, 220), ("berry", 960, 520, 250),
                                      ("plum", 1440, 560, 220)])).save(out / "step1_group.png")
    elif a.step == 4:
        import time
        from . import music
        from .characters import CHARACTERS
        song = music.plan("calypso", 7, 120)
        wav = out / "step4_calypso.wav"; music.render(song, wav)
        t0 = time.time()
        scenes = render_episode(out / "step4_mini.mp4", str(wav), list(CHARACTERS), seed=7)
        for sc in scenes:
            print(f"  {sc.start:6.1f}s {sc.section:6} {sc.template:6} {[s.name for s in sc.slots]}")
        print(f"  render {time.time() - t0:.0f}s")
    elif a.step == 3:
        from . import music
        song = music.plan("disco", 3, 30)
        wav = out / "step3_disco.wav"; music.render(song, wav)
        render_to_music(out / "step3_dance.mp4", str(wav), [("pear", 480, 560, 220, "sway", 0.0),
                                                              ("berry", 960, 520, 250, "bounce", 0.0),
                                                              ("plum", 1440, 560, 220, "stretch", 0.5)])
    else:
        click = out / "click120.wav"; click_track(click, 8, 120)
        render_clip(out / "step2_berry.mp4", 8, 120, [("berry", 960, 520, 300, "bounce", 0.0)], audio=str(click))
        render_clip(out / "step2_group.mp4", 8, 120, [("pear", 480, 560, 220, "sway", 0.0),
                                                      ("berry", 960, 520, 250, "bounce", 0.0),
                                                      ("plum", 1440, 560, 220, "stretch", 0.5)], audio=str(click))
    print("ok")


if __name__ == "__main__":
    main()
