#!/usr/bin/env python3
"""
Sacred Drift — one command, one finished video:

  1. original music       generate_ambient_audio.py (procedural, unique recipe per seed)
  2. audio-reactive video  render_sd_video.py (scene picked for the style; mandala often)
  3. thumbnail             frame from the video + big short text (thumb_text.py style)
  4. meta YAML             title, 200+ word description from the track's character, tags
  5. → sacred_drift/output/queue/  as  sd_comp_<category>_code_<date>_<seed>.{mp4,yaml,png}
     (the sd_comp_<category>_ prefix plugs into publish_queue.py's day-of-week theme rotation)

Usage:
  python3 scripts/make_sd_video.py --style solfeggio --hz 528 --minutes 60
  python3 scripts/make_sd_video.py --style bowls --variant slow --minutes 60
  python3 scripts/make_sd_video.py --style today --minutes 60            # style from the weekday theme
  python3 scripts/make_sd_video.py --style cosmic --minutes 3 --queue-dir /tmp/q   # quick test

Typical cost for 60 min on one core: music ~7 min + video ~60–110 min. Run it overnight.
"""
from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
import generate_ambient_audio as gaa  # noqa: E402
import sd_scenes  # noqa: E402

AUDIO_DIR = ROOT / "sacred_drift" / "audio" / "code_ambient"
QUEUE_DIR = ROOT / "sacred_drift" / "output" / "queue"

STYLE_CATEGORY = {"bowls": "tibetan_bowls", "cosmic": "cosmic_space", "sleep": "deep_sleep",
                  "solfeggio": "solfeggio", "rain": "rain_water", "morning": "morning_yoga"}
# publish_queue.py weekday themes → procedural style (mirrors SD_DOW_THEME in publish_queue.py)
WEEKDAY_STYLE = {0: "sleep", 1: "solfeggio", 2: "rain", 3: "bowls", 4: "morning", 5: "cosmic", 6: "cosmic"}

TAGS = {
    "bowls":     ["tibetan singing bowls", "singing bowls", "sound bath", "meditation music", "tibetan bowls",
                  "gong meditation", "deep meditation", "relaxing music", "mindfulness", "breathwork music"],
    "cosmic":    ["space music", "cosmic meditation", "ambient space music", "deep space ambient", "sleep music",
                  "meditation music", "relaxing music", "galaxy ambient", "calm music", "ambient"],
    "sleep":     ["deep sleep music", "sleep music", "dark ambient sleep", "fall asleep fast", "night music",
                  "relaxing sleep music", "calm music", "ambient drone", "bedtime music", "sleep sounds"],
    "solfeggio": ["solfeggio frequencies", "meditation music", "frequency music", "sound healing", "relaxing music",
                  "calm music", "pure tone", "meditation", "sacred geometry", "ambient"],
    "rain":      ["rain sounds", "rain meditation", "rain for sleep", "relaxing rain", "rain ambience",
                  "study music", "reading music", "calm music", "sleep music", "rainy night"],
    "morning":   ["morning meditation", "yoga music", "morning music", "calm morning", "positive ambient",
                  "relaxing music", "meditation music", "sunrise music", "yoga flow", "peaceful music"],
}
VISUAL_WORDS = {
    "lake": "A misty mountain lake at dawn; every bowl strike sends rings across the still water.",
    "mandala": "A slowly turning sacred-geometry mandala that breathes with the music, with a soft circular "
               "visualizer tracing the sound.",
    "cosmic": "A slow drift through nebulae and stars; stars shimmer with the high tones and a shooting star "
              "crosses the sky with the brightest notes.",
    "night": "A quiet moonlit sky with drifting clouds; the moon's halo glows softly with the music.",
    "window": "Rain on a window with warm lights blurred behind the glass; the drops run faster as the rain swells.",
    "sunrise": "Sunrise over layered hills, with light rays and morning mist that follow the music.",
}


def thumb_text(style: str, params: dict) -> str:
    R = params.get("recipe", {})
    if style == "bowls":
        return {"slow": "SLOW BOWLS\nMEDITATION", "deep": "DEEP BOWLS\n& GONG"}.get(R.get("variant"), "SINGING\nBOWLS")
    if style == "solfeggio":
        hz = f"{params.get('hz', 528):g}HZ"
        return f"{hz}\nBINAURAL" if params.get("binaural_beat_hz") else f"{hz}\nSOLFEGGIO"
    if style == "rain":
        return {"inside": "SOFT RAIN\nINDOORS", "outside": "OPEN AIR\nRAIN"}.get(R.get("rain"), "RAIN\nMEDITATION")
    return {"cosmic": "COSMIC\nMEDITATION", "sleep": "DEEP SLEEP\nMUSIC", "morning": "MORNING\nYOGA"}[style]


def duration_label(minutes: float) -> str:
    if minutes >= 60:
        h = int(minutes // 60)
        return f"{h} Hour" if h == 1 else f"{h} Hours"
    return f"{int(round(minutes))} Minutes"


def duration_adj(minutes: float) -> str:
    return f"{int(minutes // 60)}-hour" if minutes >= 60 else f"{int(round(minutes))}-minute"


def build_meta(rec: dict, scene: str, minutes: float) -> dict:
    style, params = rec["style"], rec.get("params", {})
    dur = duration_label(minutes)
    title = f"{rec['title']} • {dur}"[:100]
    use_line = {
        "bowls": "Sit comfortably, let each strike fade completely before the next breath, and follow the echoes.",
        "cosmic": "Lie back, close your eyes and let the slow harmonies carry your attention outwards.",
        "sleep": "Start it as you go to bed; the music stays low and unchanging enough not to wake you.",
        "solfeggio": ("Use headphones so each ear hears its own tone — that is what creates the binaural beat."
                      if params.get("binaural_beat_hz") else
                      "Keep the volume low and let the steady tone settle into the background of your attention."),
        "rain": "Play it while you read, study or fall asleep — the rain rises and settles in slow waves.",
        "morning": "Use it for gentle yoga, stretching or a quiet first coffee before the day begins.",
    }[style]
    paragraphs = [
        rec.get("description", ""),
        f"{rec['title']} is a {duration_adj(minutes)} session of original, slowly evolving music. Nothing is looped: "
        f"the harmony, key and texture keep changing gently from beginning to end, so the session never "
        f"repeats itself. {VISUAL_WORDS[scene]}",
        "How to listen:\n"
        "• Headphones or soft speakers at a low, comfortable volume\n"
        f"• {use_line}\n"
        "• Let it play in the background — you don't need to watch, the sound is the session",
        "About Sacred Drift:\nSacred Drift is a sanctuary of sound — singing bowls, solfeggio tones, cosmic "
        "ambient, rain and sleep music for deep rest and inner calm. Every piece is composed and synthesized "
        "from scratch, with visuals that move with the music. New sessions every week.\n\nSubscribe 🔮 @SacredDrift",
        "🎶 Original music composed and synthesized by Sacred Drift (procedural synthesis, no samples, no AI "
        "model). Visuals generated by code and animated to the music.",
    ]
    if style == "solfeggio":
        paragraphs.append("This music is intended for relaxation and meditation and is not a medical treatment.")
    tags_h = {"bowls": "#singingbowls #soundbath #meditationmusic", "cosmic": "#spacemusic #ambient #meditation",
              "sleep": "#sleepmusic #deepsleep #ambient", "solfeggio": "#solfeggio #meditationmusic #frequency",
              "rain": "#rainsounds #rainforsleep #studymusic", "morning": "#morningmeditation #yogamusic #calm"}[style]
    paragraphs.append(f"{tags_h} #sacreddrift #relaxingmusic")
    description = "\n\n".join(p for p in paragraphs if p)
    if len(description.split()) < 200:                      # channel rule: at least 200 words
        description += ("\n\nThis session is part of a growing library of long-form music for meditation, sleep, "
                        "study and quiet moments. Save it to a playlist, come back whenever you need a pause, and "
                        "tell us in the comments where you listen — it helps shape the next sessions.")
    tags = list(dict.fromkeys(TAGS[style] + ["sacred drift", "relaxing music", "meditation", dur.lower()]))[:30]
    return {
        "title": title, "description": description, "tags": tags,
        "video_type": "meditation_compilation", "language": "en", "is_short": False, "status": "public",
        "made_for_kids": False, "ai_generated": False, "music_source": "procedural",
        "category": STYLE_CATEGORY[style], "scene": scene, "seed": rec["seed"],
        "duration_sec": int(minutes * 60), "audio_file": rec["file"], "stream_safe": True,
    }


def make_thumbnail(video: Path, out: Path, style: str, params: dict, minutes: float):
    from PIL import Image
    import thumb_text as tt
    frame = out.with_suffix(".frame.png")
    at = max(5.0, min(60.0, minutes * 60 * 0.3))
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{at:.1f}", "-i", str(video), "-frames:v", "1",
                    "-vf", "scale=1280:720", str(frame)], check=True)
    from PIL import ImageEnhance
    img = Image.open(frame).convert("RGB")
    # thumbnails compete in a bright feed: lift brightness/contrast/colour a little vs. the calm video
    img = ImageEnhance.Brightness(img).enhance(1.3)
    img = ImageEnhance.Contrast(img).enhance(1.15)
    img = ImageEnhance.Color(img).enhance(1.25)
    hours = int(minutes // 60) if minutes >= 60 else None
    img = tt.add_thumb_text(img, thumb_text(style, params), duration_hours=hours, channel_tag="Sacred Drift")
    img.save(out, "PNG", optimize=True)
    frame.unlink(missing_ok=True)


def main():
    ap = argparse.ArgumentParser(description="Music + reactive video + thumbnail + meta → Sacred Drift queue")
    ap.add_argument("--style", required=True, help="bowls|cosmic|sleep|solfeggio|rain|morning|today")
    ap.add_argument("--minutes", type=float, default=60)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--variant", default=None); ap.add_argument("--rain", default=None)
    ap.add_argument("--hz", type=float, default=None); ap.add_argument("--binaural", type=float, default=None)
    ap.add_argument("--scene", choices=sorted(sd_scenes.SCENES), default=None)
    ap.add_argument("--queue-dir", default=str(QUEUE_DIR))
    ap.add_argument("--audio-dir", default=str(AUDIO_DIR))
    a = ap.parse_args()

    style = WEEKDAY_STYLE[datetime.datetime.now(datetime.timezone.utc).weekday()] if a.style == "today" else a.style
    if style not in STYLE_CATEGORY:
        sys.exit(f"unknown style {style}")
    audio_dir = Path(a.audio_dir); audio_dir.mkdir(parents=True, exist_ok=True)
    qdir = Path(a.queue_dir); qdir.mkdir(parents=True, exist_ok=True)

    # 1. music
    cmd = [sys.executable, str(SCRIPTS / "generate_ambient_audio.py"), "--style", style, "--minutes", str(a.minutes),
           "--out-dir", str(audio_dir)]
    for flag, val in (("--seed", a.seed), ("--variant", a.variant), ("--rain", a.rain), ("--hz", a.hz),
                      ("--binaural", a.binaural)):
        if val is not None:
            cmd += [flag, str(val)]
    print("① music …"); subprocess.run(cmd, check=True)
    rec = json.loads((audio_dir / "ambient_log.jsonl").read_text().splitlines()[-1])
    audio = audio_dir / rec["file"]
    scene = a.scene or sd_scenes.pick_scene(style, rec["seed"])

    stem = f"sd_comp_{STYLE_CATEGORY[style]}_code_{datetime.date.today():%Y%m%d}_{rec['seed']}"
    mp4, meta_p, thumb = qdir / f"{stem}.mp4", qdir / f"meta_{stem}.yaml", qdir / f"thumb_{stem}.png"

    # 2. video
    print(f"② video ({scene}) …")
    subprocess.run([sys.executable, str(SCRIPTS / "render_sd_video.py"), "--audio", str(audio), "--scene", scene,
                    "--out", str(mp4)], check=True)
    # 3. thumbnail, 4. meta
    print("③ thumbnail …"); make_thumbnail(mp4, thumb, style, rec.get("params", {}), a.minutes)
    print("④ meta …")
    meta = build_meta(rec, scene, a.minutes)
    meta_p.write_text(yaml.dump(meta, allow_unicode=True, default_flow_style=False, sort_keys=False))
    print(f"✅ queued: {mp4.name}\n   title: {meta['title']}\n   words in description: {len(meta['description'].split())}")


if __name__ == "__main__":
    main()
