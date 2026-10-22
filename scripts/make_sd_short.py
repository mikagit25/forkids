#!/usr/bin/env python3
"""
Sacred Drift — Shorts cutter: the strongest ~50 s of a procedural track → vertical 9:16 Short.

  1. find the best moment: a thunder strike / bowl strike lands ~6 s in (the hook), with the
     loudest, busiest stretch after it; tracks without strikes use the fullest-sounding window
  2. re-render the scene natively in portrait (540×960 → 1080×1920), audio-reactive as usual —
     not a crop of the 16:9 video
  3. burn in a short hook line at the top, fade in/out picture and sound
  4. title in the Shorts format from sd_title_rules ({Theme} — {Subtitle} 🎵 {Keywords} #Shorts),
     200+ word description pointing to the full-length video, tags
  5. → sacred_drift/output/queue/sd_short_<category>_code_<date>_<seed>.{mp4,png} + meta (is_short: true)

Usage:
  python3 scripts/make_sd_short.py --from-meta sacred_drift/output/queue/meta_sd_comp_….yaml
  python3 scripts/make_sd_short.py --audio "sacred_drift/audio/code_ambient/<track>.mp3"
  python3 scripts/make_sd_short.py --latest 2          # newest long code videos that have no Short yet

~1–2 min per Short.
"""
from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
import audio_reactive  # noqa: E402
import sd_scenes  # noqa: E402
import sd_title_rules  # noqa: E402
from render_sd_video import track_info  # noqa: E402

AUDIO_DIR = ROOT / "sacred_drift" / "audio" / "code_ambient"
QUEUE_DIR = ROOT / "sacred_drift" / "output" / "queue"
STYLE_CATEGORY = {"bowls": "tibetan_bowls", "cosmic": "cosmic_space", "sleep": "deep_sleep",
                  "solfeggio": "solfeggio", "rain": "rain_water", "morning": "morning_yoga", "storm": "rain_water"}
HOOK_AT = 6.0          # seconds into the Short where the strike lands
SUBTITLES = {          # unique-ish poetic subtitle per Short (picked by seed)
    "storm": ["Midnight Downpour", "Rolling Thunder", "Storm Over the Hills", "Night Rain", "Distant Lightning"],
    "rain": ["Window Rain", "Quiet Evening", "Soft Downpour"],
    "bowls": ["Temple Echoes", "One Breath", "Still Water", "Bronze and Silence"],
    "solfeggio": ["Pure Tone", "Inner Calm", "Clear Mind", "Soft Resonance"],
    "cosmic": ["Starlit Void", "Silent Orbit", "Nebula Drift"],
    "sleep": ["Soft Darkness", "Night Breath", "Slow Drift"],
    "morning": ["First Light", "Golden Hour", "New Day"],
}


def theme_and_keywords(style: str, params: dict) -> tuple[str, str]:
    """Display theme + search keywords — built from what people actually search for."""
    R = params.get("recipe", {})
    if style == "storm":
        th, s = R.get("thunder"), R.get("variant")
        place = {"tin_roof": "Rain on a Tin Roof", "tent": "Rain on a Tent", "car": "Rain on a Car Roof",
                 "fireplace": "Rain by the Fire"}.get(s)
        if place:
            return place, "Rain Sounds for Sleep"
        return ("Thunderstorm Sounds" if th in ("heavy", "gentle") else "Rain Sounds"), "Sleep Sounds"
    if style == "solfeggio":
        hz = f"{params.get('hz', 528):g}Hz"
        if 4 <= (params.get("binaural_beat_hz") or 0) <= 8:
            return "Theta Binaural Beats", "Study Music"
        return f"{hz} Frequency", "Sound Healing"
    if style == "bowls":
        return "Tibetan Singing Bowls", "Stress Relief"
    if style == "cosmic":
        return "Deep Space Ambient", "Sleep Music"
    if style == "sleep":
        return "Deep Sleep Music", "Fall Asleep Fast"
    if style == "rain":
        return "Rain Sounds", "Sleep Sounds"
    return "Morning Meditation", "Meditation Music"


def hook_text(style: str, params: dict) -> str:
    R = params.get("recipe", {})
    if style == "storm":
        s = R.get("variant")
        if s in ("tin_roof", "tent", "car"):
            return {"tin_roof": "RAIN ON A TIN ROOF", "tent": "RAIN ON YOUR TENT", "car": "RAIN ON THE CAR ROOF"}[s] + \
                "\nCLOSE YOUR EYES"
        return "CAN'T SLEEP?\nLISTEN TO THIS STORM" if R.get("thunder") != "none" else "RAIN FOR\nINSTANT CALM"
    if style == "solfeggio":
        if 4 <= (params.get("binaural_beat_hz") or 0) <= 8:
            return "THETA WAVES\nFOR DEEP FOCUS"
        return f"{params.get('hz', 528):g}HZ\nCLOSE YOUR EYES"
    return {"bowls": "STOP OVERTHINKING\nJUST BREATHE", "cosmic": "DRIFT INTO\nDEEP SPACE",
            "sleep": "FALL ASLEEP\nTO THIS", "rain": "RAIN FOR\nINSTANT CALM",
            "morning": "START YOUR DAY\nCALM"}.get(style, "BREATHE")


def short_scene(long_scene: str | None, style: str, seed: int) -> str:
    """A dark screen is right for sleeping, but a Short has to be seen: use a visible scene."""
    if long_scene and long_scene != "dark":
        return long_scene
    return {"storm": "window", "sleep": "night"}.get(style) or sd_scenes.pick_scene(style, seed)


def best_start(audio: Path, info: dict, seconds: float) -> float:
    F = audio_reactive.analyze(str(audio), 12)
    dur = F["frames"] / 12
    lo, hi = min(25.0, dur * 0.1), max(0.0, dur - seconds - 5)
    if hi <= lo:
        return 0.0
    strikes = ((info.get("params") or {}).get("recipe") or {}).get("strikes")
    if strikes:                                   # thunder: nearest (loudest) strike lands at HOOK_AT
        ok = [(d, t) for t, d in strikes if lo + HOOK_AT <= t <= hi + HOOK_AT]
        if ok:
            return min(ok)[1] - HOOK_AT
    env = F["env"]; cs = np.concatenate([[0], np.cumsum(env)])
    win = int(seconds * 12)
    onset_s = dict(zip((int(i) for i in F["onsets"]), (float(s) for s in F["onset_strength"])))
    best, best_t = -1.0, lo
    for t in np.arange(lo, hi, 1.0):
        i = int(t * 12)
        fill = (cs[min(i + win, len(env))] - cs[i]) / win
        hook = max((s for j, s in onset_s.items() if i + 12 * 3 <= j <= i + 12 * 10), default=0.0)
        score = fill + 0.8 * hook
        if score > best:
            best, best_t = score, float(t)
    if onset_s:                                   # align the strongest strike of that window to HOOK_AT
        i = int(best_t * 12)
        cand = [(s, j) for j, s in onset_s.items() if i + 36 <= j <= i + 120]
        if cand:
            best_t = max(lo, min(hi, max(cand)[1] / 12 - HOOK_AT))
    return best_t


def hook_overlay(text: str, path: Path, w=1080, h=1920):
    from PIL import Image, ImageDraw, ImageFilter
    import thumb_text as tt
    font, _ = tt._load_fonts(main_size=118, sub_size=40)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    lines = text.split("\n")
    y = int(h * 0.12)
    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0)); ds = ImageDraw.Draw(shadow)
    d = ImageDraw.Draw(img)
    for ln in lines:
        bw = d.textlength(ln, font=font)
        x = (w - bw) / 2
        ds.text((x + 4, y + 5), ln, font=font, fill=(0, 0, 0, 200))
        d.text((x, y), ln, font=font, fill=(255, 248, 230, 255))
        y += 130
    shadow = shadow.filter(ImageFilter.GaussianBlur(6))
    Image.alpha_composite(shadow, img).save(path)


def build_meta(rec: dict, style: str, params: dict, seconds: float, long_meta: dict | None) -> dict:
    theme, kw = theme_and_keywords(style, params)
    subs = SUBTITLES.get(style, ["Calm"])
    sub = subs[rec["seed"] % len(subs)]
    title = f"{theme} — {sub} 🎵 {kw} #Shorts"
    full = ""
    if long_meta:
        hours = int(long_meta.get("duration_sec", 0) // 3600)
        full = (f"🎧 The full {hours}-hour version is on the channel: “{long_meta.get('title', '')}”. "
                "Tap the channel name to find it and let it play all night.") if hours else ""
    desc = "\n\n".join(x for x in [
        f"{rec.get('description', '')}",
        f"This Short is a {int(seconds)}-second moment from a long Sacred Drift session. Put your phone down, "
        "breathe slowly and let the sound do the rest.",
        full,
        "About Sacred Drift:\nSacred Drift is a sanctuary of sound — rain and thunderstorms, singing bowls, "
        "frequencies, cosmic ambient and sleep music for deep rest, focus and calm. Every piece is composed and "
        "synthesized from scratch, with visuals that move with the sound. New long sessions every day.",
        "🎶 Original sound composed and synthesized by Sacred Drift (procedural synthesis, no samples, no AI "
        "model). Visuals generated by code and animated to the sound.",
        "This audio is intended for relaxation, focus and sleep and is not a medical treatment.",
        "Subscribe 🔮 @SacredDrift",
        f"#Shorts #{kw.replace(' ', '').lower()} #sacreddrift #relaxing #calm",
    ] if x)
    if len(desc.split()) < 200:
        desc += ("\n\nSave this Short and come back to the full session whenever you need a pause: for falling "
                 "asleep, for reading and study, or for a few quiet minutes in the middle of a busy day. Tell us in "
                 "the comments which sound you want next — rain on a tin roof, a tent, a car, or a storm by the "
                 "fire — the next sessions are shaped by your requests.")
    tags = list(dict.fromkeys([kw.lower(), theme.lower(), "shorts", "sacred drift", "relaxing sounds",
                               "sleep sounds", "meditation shorts", "calm"]))[:20]
    return {"title": title[:100], "description": desc, "tags": tags, "video_type": "meditation_short",
            "language": "en", "is_short": True, "status": "public", "made_for_kids": False,
            "ai_generated": False, "music_source": "procedural", "category": STYLE_CATEGORY.get(style, style),
            "seed": rec["seed"], "audio_file": rec["file"], "duration_sec": int(seconds),
            "source_video": (long_meta or {}).get("_stem")}


def make_short(audio: Path, seconds: float, qdir: Path, long_meta: dict | None = None,
               scene: str | None = None, date: datetime.date | None = None) -> Path:
    info = track_info(audio)
    if not info:
        sys.exit(f"no ambient_log entry for {audio.name} — Shorts need a procedural track")
    style, params, seed = info["style"], info.get("params", {}), info["seed"]
    scene = scene or short_scene((long_meta or {}).get("scene"), style, seed)
    start = best_start(audio, info, seconds)
    stem = f"sd_short_{STYLE_CATEGORY.get(style, style)}_code_{(date or datetime.date.today()):%Y%m%d}_{seed}"
    mp4, meta_p, thumb = qdir / f"{stem}.mp4", qdir / f"meta_{stem}.yaml", qdir / f"thumb_{stem}.png"
    print(f"✂️  {audio.name}: {start:.0f}s → +{seconds:.0f}s, scene {scene}")
    with tempfile.TemporaryDirectory() as td:
        raw, ov = Path(td) / "raw.mp4", Path(td) / "hook.png"
        subprocess.run([sys.executable, str(SCRIPTS / "render_sd_video.py"), "--audio", str(audio), "--scene", scene,
                        "--seed", str(seed), "--start", f"{start:.2f}", "--seconds", f"{seconds:.2f}",
                        "--w", "540", "--h", "960", "--out-w", "1080", "--out-h", "1920", "--fps", "24",
                        "--out", str(raw)], check=True)
        hook_overlay(hook_text(style, params), ov)
        fo = seconds - 1.0
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(raw), "-loop", "1", "-i", str(ov),
                        "-filter_complex",
                        f"[1:v]format=rgba,fade=in:st=0.4:d=0.8:alpha=1[t];[0:v][t]overlay=0:0:shortest=1,"
                        f"fade=in:st=0:d=0.5,fade=out:st={fo:.2f}:d=1.0[v];"
                        f"[0:a]afade=in:st=0:d=1.5,afade=out:st={seconds - 2.5:.2f}:d=2.5[a]",
                        "-map", "[v]", "-map", "[a]", "-t", f"{seconds:.2f}", "-c:v", "libx264", "-preset", "medium",
                        "-crf", "21", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
                        str(mp4)], check=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{HOOK_AT + 1:.1f}", "-i", str(mp4),
                    "-frames:v", "1", "-vf", "scale=720:1280", str(thumb)], check=True)
    meta = build_meta(info, style, params, seconds, long_meta)
    meta["short_start_s"] = round(start, 2)
    meta_p.write_text(yaml.dump(meta, allow_unicode=True, default_flow_style=False, sort_keys=False))
    print(f"✅ {mp4.name}\n   {meta['title']}  ({len(meta['description'].split())} words)")
    return mp4


def main():
    ap = argparse.ArgumentParser(description="Vertical Short from the best moment of a procedural track")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--audio"); src.add_argument("--from-meta")
    src.add_argument("--latest", type=int, help="make Shorts for the N newest long code videos without one")
    ap.add_argument("--seconds", type=float, default=50)
    ap.add_argument("--scene", choices=sorted(sd_scenes.SCENES), default=None)
    ap.add_argument("--queue-dir", default=str(QUEUE_DIR))
    ap.add_argument("--audio-dir", default=str(AUDIO_DIR))
    a = ap.parse_args()
    qdir = Path(a.queue_dir); qdir.mkdir(parents=True, exist_ok=True)
    adir = Path(a.audio_dir)

    jobs: list[tuple[Path, dict | None]] = []
    if a.audio:
        jobs.append((Path(a.audio), None))
    else:
        metas = [Path(a.from_meta)] if a.from_meta else \
            sorted(qdir.glob("meta_sd_comp_*_code_*.yaml"), key=lambda p: p.stat().st_mtime, reverse=True)
        for mp in metas:
            m = yaml.safe_load(mp.read_text()) or {}
            if not m.get("audio_file"):
                continue
            m["_stem"] = mp.stem[len("meta_"):]
            if a.latest and any(qdir.glob(f"sd_short_*_code_*_{m.get('seed')}.mp4")):
                continue
            jobs.append(((adir / m["audio_file"]), m))
            if a.latest and len(jobs) >= a.latest:
                break
    for audio, m in jobs:
        date = datetime.date.fromisoformat(m["publish_date"]) if m and m.get("publish_date") else None
        make_short(audio, a.seconds, qdir, m, a.scene, date)


if __name__ == "__main__":
    main()
