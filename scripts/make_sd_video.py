#!/usr/bin/env python3
"""
Sacred Drift — one command, one finished video:

  1. original music       generate_ambient_audio.py (procedural, unique recipe per seed)
  2. audio-reactive video  render_sd_video.py (scene picked for the style; mandala often)
  3. thumbnail             frame from the video + big short text (thumb_text.py style)
  4. meta YAML             title, 200+ word description from the track's character, tags
  5. → sacred_drift/output/queue/  as  sd_comp_<category>_code_<date>_<seed>.{mp4,yaml,png}
     (the sd_comp_<category>_ prefix plugs into publish_queue.py's day-of-week theme rotation)

Weekly programme (v2.3, from the trends analysis) — `--program today` picks the slot for the
day the video will be PUBLISHED (the nightly run after 12:00 UTC prepares tomorrow's video):
  Mon  thunderstorm for sleep          8 h  dark screen with lightning
  Tue  frequency 432/528/777/963/639   3 h  mandala
  Wed  Tibetan bowls for overthinking  3 h  lake / mandala
  Thu  theta binaural beats for study  3 h  mandala
  Fri  rain in a setting (tin roof…)   3 h  window / dark
  Sat  deep space sleep                3 h  cosmic
  Sun  Sacred Drift Sleep #NN         10 h  dark screen
Title formula: problem/benefit + instrument + duration (+ series number), one emoji, nothing
after the duration; no medical claims.

Usage:
  python3 scripts/make_sd_video.py --program today                      # nightly cron
  python3 scripts/make_sd_video.py --program mon --minutes 3 --queue-dir /tmp/q   # quick test
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
import math
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
                  "solfeggio": "solfeggio", "rain": "rain_water", "morning": "morning_yoga",
                  "storm": "rain_water"}
# SEO-friendly YouTube title bases — match what people actually search for
STYLE_TITLE = {
    "bowls":     "Tibetan Singing Bowls Meditation 🔔",
    "cosmic":    "Cosmic Space Meditation Music ✨",
    "sleep":     "Deep Sleep Music 😴",
    "solfeggio": None,   # built dynamically with Hz value
    "rain":      "Rain Sounds for Sleep & Relaxation 🌧",
    "morning":   "Morning Yoga & Meditation Music 🌅",
    "storm":     "Thunderstorm Sounds for Sleep 🌩",
}
BOWL_VARIANT_TITLE = {
    "slow": "Slow Tibetan Bowls Meditation 🔔",
    "deep": "Deep Tibetan Bowls & Gong 🔔",
}
SERIES_FILE = ROOT / "sacred_drift" / "series.json"
DAY_NAMES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
FREQ_ROTATION = [528, 432, 777, 963, 639, 396, 852, 417]


def program(dow: int, week: int) -> dict:
    """Weekly slot → what to make. `week` (ISO week number) rotates the variations so the same
    weekday never gets the same video twice in a row. Mirrors SD_DOW_THEME in publish_queue.py."""
    r = lambda xs: xs[week % len(xs)]                                       # noqa: E731
    if dow == 0:
        return {"style": "storm", "minutes": 480, "scene": "dark", "night_storm": True,
                "opts": {"setting": r(["window", "open", "window", "fireplace"]), "thunder": r(["heavy", "gentle"])}}
    if dow == 1:
        return {"style": "solfeggio", "minutes": 180, "scene": "mandala", "opts": {"hz": r(FREQ_ROTATION)}}
    if dow == 2:
        return {"style": "bowls", "minutes": 180, "scene": r(["lake", "mandala"]),
                "opts": {"variant": r(["slow", "deep", "slow", "ringing"])}}
    if dow == 3:
        return {"style": "solfeggio", "minutes": 180, "scene": "mandala",
                "opts": {"hz": r([432, 528, 639]), "binaural": r([6, 5, 7])}, "theta": True}
    if dow == 4:
        setting = r(["tin_roof", "tent", "car", "window", "fireplace"])
        return {"style": "storm", "minutes": 180, "scene": "window" if setting in ("window", "fireplace") else "dark",
                "opts": {"setting": setting, "thunder": r(["none", "gentle", "none"]),
                         "intensity": r(["steady", "light", "heavy"])}}
    if dow == 5:
        return {"style": "cosmic", "minutes": 180, "scene": "cosmic", "opts": {}}
    return {"style": "sleep", "minutes": 600, "scene": "dark", "opts": {}, "series": "Sacred Drift Sleep"}


def publish_date(now: datetime.datetime | None = None) -> datetime.date:
    """The cron starts at 23:30 UTC and the video goes out at 20:00 UTC the NEXT day, so a run
    after midday prepares tomorrow's slot; a morning run prepares today's."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    return (now + datetime.timedelta(days=1)).date() if now.hour >= 12 else now.date()


def next_series_number(name: str, commit: bool) -> int:
    try:
        data = json.loads(SERIES_FILE.read_text())
    except (OSError, ValueError):
        data = {}
    n = int(data.get(name, 0)) + 1
    if commit:
        data[name] = n
        SERIES_FILE.parent.mkdir(parents=True, exist_ok=True)
        SERIES_FILE.write_text(json.dumps(data, indent=2))
    return n


def program_title(prog: dict, params: dict, week: int) -> str | None:
    """Trend formula: problem/benefit + instrument (+ setting) — duration is appended by build_meta."""
    style, R = prog["style"], params.get("recipe", {})
    r = lambda xs: xs[week % len(xs)]                                       # noqa: E731
    if prog.get("series"):
        return f"{prog['series']} #{prog['series_no']}: Dark Screen Deep Sleep Music 😴"
    if style == "storm" and prog.get("night_storm"):
        return ({"heavy": "Heavy Thunderstorm & Rain for Deep Sleep, Dark Screen 🌩",
                 "gentle": "Gentle Rain & Distant Thunder to Fall Asleep Fast, Dark Screen 🌧"}.get(R.get("thunder"))
                or "Rain Sounds for Deep Sleep, Dark Screen 🌧")
    if style == "storm":
        phrase = {"window": "Rain on the Window", "open": "Rain in the Open", "tin_roof": "Rain on a Tin Roof",
                  "tent": "Rain on a Tent", "car": "Rain on a Car Roof",
                  "fireplace": "Rain and Crackling Fire"}.get(R.get("variant"), "Rain Sounds")
        pre = {"light": "Light ", "heavy": "Heavy "}.get(R.get("intensity"), "")
        th = {"heavy": " with Thunder", "gentle": " with Distant Thunder"}.get(R.get("thunder"), "")
        tail = " (No Thunder)" if R.get("thunder") == "none" else ""
        return f"{pre}{phrase}{th} for Sleep & Study{tail} 🌧"
    if style == "solfeggio" and prog.get("theta"):
        return r(["Theta Binaural Beats for Study & Deep Focus 🧠", "Study Music with Theta Binaural Beats for Focus 🧠",
                  "Deep Focus: Theta Binaural Beats for Studying & Reading 🧠"])
    if style == "solfeggio":
        hz = f"{params.get('hz', 528):g}Hz"
        return r([f"Stop Overthinking: {hz} Frequency for a Calm Mind 🎶",
                  f"{hz} Solfeggio Frequency to Release Stress & Tension 🎶",
                  f"Quiet the Mind: {hz} Frequency Meditation Music 🎶",
                  f"{hz} Frequency to Let Go of Negative Energy 🎶"])
    if style == "bowls":
        return {"slow": "Slow Tibetan Singing Bowls to Calm an Overthinking Mind 🔔",
                "deep": "Deep Tibetan Bowls & Gong to Release Stress 🔔"}.get(
            R.get("variant"), "Tibetan Singing Bowls for Overthinking & Stress Relief 🔔")
    if style == "cosmic":
        return r(["Deep Space Sleep Music: Drift Through the Cosmos ✨", "Floating in Deep Space: Ambient Music for Sleep ✨",
                  "Deep Space Ambient for Sleep & Relaxation ✨"])
    return None

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
    "storm":     ["thunderstorm sounds", "rain and thunder", "thunderstorm for sleep", "rain sounds for sleeping",
                  "heavy rain", "rain sounds", "sleep sounds", "white noise rain", "storm sounds", "rain ambience",
                  "black screen rain", "dark screen sleep", "rain on tin roof", "rain on tent", "rain on car"],
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
    "dark": "A dark screen made for sleep: a near-black night sky with faint, slow clouds and a treeline — "
            "nothing bright to keep you awake. When thunder rolls, lightning softly lights the clouds from within.",
}


def thumb_text(style: str, params: dict) -> str:
    R = params.get("recipe", {})
    if style == "bowls":
        return {"slow": "SLOW BOWLS\nMEDITATION", "deep": "DEEP BOWLS\n& GONG"}.get(R.get("variant"), "SINGING\nBOWLS")
    if style == "solfeggio":
        hz = f"{params.get('hz', 528):g}HZ"
        if 4 <= (params.get("binaural_beat_hz") or 0) <= 8:
            return "THETA WAVES\nFOR STUDY"
        return f"{hz}\nBINAURAL" if params.get("binaural_beat_hz") else f"{hz}\nSOLFEGGIO"
    if style == "rain":
        return {"inside": "SOFT RAIN\nINDOORS", "outside": "OPEN AIR\nRAIN"}.get(R.get("rain"), "RAIN\nMEDITATION")
    if style == "storm":
        th = R.get("thunder")
        return {"tin_roof": "RAIN ON A\nTIN ROOF", "tent": "RAIN ON\nA TENT", "car": "RAIN ON\nA CAR ROOF",
                "fireplace": "STORM BY\nTHE FIRE" if th != "none" else "RAIN &\nFIREPLACE"}.get(
            R.get("variant"), {"heavy": "THUNDER\nSTORM", "gentle": "GENTLE\nTHUNDER"}.get(th, "RAIN\nNO THUNDER"))
    return {"cosmic": "COSMIC\nMEDITATION", "sleep": "DEEP SLEEP\nMUSIC", "morning": "MORNING\nYOGA"}[style]


def duration_label(minutes: float) -> str:
    if minutes >= 60:
        h = int(minutes // 60)
        return f"{h} Hour" if h == 1 else f"{h} Hours"
    return f"{int(round(minutes))} Minutes"


def duration_adj(minutes: float) -> str:
    return f"{int(minutes // 60)}-hour" if minutes >= 60 else f"{int(round(minutes))}-minute"


def _seo_title(style: str, params: dict) -> str:
    """Return clean, search-friendly title base (no subtitles)."""
    R = params.get("recipe", {})
    if style == "bowls":
        return BOWL_VARIANT_TITLE.get(R.get("variant"), STYLE_TITLE["bowls"])
    if style == "solfeggio":
        hz = f"{params.get('hz', 528):g}Hz"
        return (f"{hz} Binaural Beats Meditation 🎶"
                if params.get("binaural_beat_hz")
                else f"{hz} Solfeggio Frequency Meditation 🎶")
    if style == "rain":
        return {"inside": "Soft Rain Sounds for Sleep & Study 🌧",
                "outside": "Open Air Rain Meditation 🌧"}.get(R.get("rain"), STYLE_TITLE["rain"])
    if style == "storm":
        return gaa.storm_title(R) + " 🌧"
    return STYLE_TITLE[style]


def build_meta(rec: dict, scene: str, minutes: float, title_base: str | None = None,
               no_ads: bool = False) -> dict:
    style, params = rec["style"], rec.get("params", {})
    dur = duration_label(minutes)
    base = title_base or _seo_title(style, params)
    if no_ads:          # only honest while the channel is NOT monetized — turn off once YPP is on
        head, _, last = base.rstrip().rpartition(" ")
        base = f"{head} (No Mid-Roll Ads) {last}" if head and not last.isascii() else f"{base} (No Mid-Roll Ads)"
    title = f"{base} • {dur}"
    if len(title) > 100:
        title = f"{_seo_title(style, params)} • {dur}"[:100]
    use_line = {
        "bowls": "Sit comfortably, let each strike fade completely before the next breath, and follow the echoes.",
        "cosmic": "Lie back, close your eyes and let the slow harmonies carry your attention outwards.",
        "sleep": "Start it as you go to bed; the music stays low and unchanging enough not to wake you.",
        "solfeggio": ("Use headphones so each ear hears its own tone — that is what creates the binaural beat."
                      if params.get("binaural_beat_hz") else
                      "Keep the volume low and let the steady tone settle into the background of your attention."),
        "rain": "Play it while you read, study or fall asleep — the rain rises and settles in slow waves.",
        "morning": "Use it for gentle yoga, stretching or a quiet first coffee before the day begins.",
        "storm": "Start it as you go to bed and turn the screen away — the rain stays steady all night and the "
                 "thunder never jumps out loudly.",
    }[style]
    paragraphs = [
        rec.get("description", ""),
        (f"{rec['title']} is a {duration_adj(minutes)} rain and thunder soundscape, synthesized from scratch. "
         f"Nothing is looped: every raindrop, gust and roll of thunder is generated anew, so the storm never "
         f"repeats itself. {VISUAL_WORDS[scene]}" if style == "storm" else
         f"{rec['title']} is a {duration_adj(minutes)} session of original, slowly evolving music. Nothing is looped: "
         f"the harmony, key and texture keep changing gently from beginning to end, so the session never "
         f"repeats itself. {VISUAL_WORDS[scene]}"),
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
    if style in ("solfeggio", "bowls", "storm", "sleep"):
        paragraphs.append("This audio is intended for relaxation, focus and sleep and is not a medical treatment.")
    tags_h = {"storm": "#thunderstorm #rainsounds #sleepsounds","bowls": "#singingbowls #soundbath #meditationmusic", "cosmic": "#spacemusic #ambient #meditation",
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


def dark_still(params: dict, seed: int):
    """Thumbnail for dark-screen videos: a near-black frame would vanish in the feed, so draw a still
    instead — lightning-lit storm clouds for storms, a moonlit night sky for sleep."""
    if params.get("recipe", {}).get("strikes") is not None or params.get("recipe", {}).get("thunder"):
        P = sd_scenes.params("dark", seed)
        P["strikes"] = [(10.0 + 0.4 + 3 * 0.15, 0.15)]                     # a near strike lit at t=10 s
        img = sd_scenes.frame("dark", 10.03, 1280, 720, P, {})
        _, fx = sd_scenes.strike_flash(10.03, P["strikes"])
        return lightning_bolt(img, fx * 1280, seed)
    return sd_scenes.frame("night", 3.0, 1280, 720, sd_scenes.params("night", seed), {})


def lightning_bolt(img, x0: float, seed: int):
    """Jagged lightning bolt with a soft glow, from the top of the frame down towards the horizon."""
    import random as _r
    from PIL import ImageDraw, ImageFilter
    rnd = _r.Random(seed)
    w, h = img.size
    pts, x, y = [(x0, 0)], x0, 0
    while y < h * 0.78:
        y += rnd.uniform(25, 60); x += rnd.uniform(-45, 45); pts.append((x, y))
    branch = pts[len(pts) // 3:len(pts) // 3 + 1]
    bx, by = branch[0]
    for _ in range(4):
        by += rnd.uniform(25, 50); bx += rnd.uniform(10, 50) * (1 if x0 < w / 2 else -1); branch.append((bx, by))
    glow = img.copy(); d = ImageDraw.Draw(glow)
    d.line(pts, fill=(170, 185, 255), width=16); d.line(branch, fill=(170, 185, 255), width=9)
    glow = glow.filter(ImageFilter.GaussianBlur(14))
    from PIL import Image as _I
    img = _I.blend(img, glow, 0.6)
    d = ImageDraw.Draw(img)
    d.line(pts, fill=(245, 248, 255), width=4); d.line(branch, fill=(235, 240, 255), width=2)
    return img




def make_thumbnail(video: Path, out: Path, style: str, params: dict, minutes: float, scene: str = "", seed: int = 1):
    from PIL import Image
    import thumb_text as tt
    frame = out.with_suffix(".frame.png")
    if scene == "dark":
        dark_still(params, seed).save(frame)
    else:
        at = max(5.0, min(60.0, minutes * 60 * 0.3))
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{at:.1f}", "-i", str(video), "-frames:v", "1",
                        "-vf", "scale=1280:720", str(frame)], check=True)
    from PIL import ImageEnhance
    img = Image.open(frame).convert("RGB")
    # thumbnails compete in a bright feed: lift brightness/contrast/colour a little vs. the calm video
    img = ImageEnhance.Brightness(img).enhance(2.2 if scene == "dark" else 1.3)
    img = ImageEnhance.Contrast(img).enhance(1.15)
    img = ImageEnhance.Color(img).enhance(1.25)
    hours = int(minutes // 60) if minutes >= 60 else None
    img = tt.add_thumb_text(img, thumb_text(style, params), duration_hours=hours, channel_tag="Sacred Drift")
    img.save(out, "PNG", optimize=True)
    frame.unlink(missing_ok=True)


def main():
    ap = argparse.ArgumentParser(description="Music + reactive video + thumbnail + meta → Sacred Drift queue")
    ap.add_argument("--program", choices=["today"] + DAY_NAMES, default=None,
                    help="weekly slot (today = the day this video will be published)")
    ap.add_argument("--for-date", default=None, help="program: publish date YYYY-MM-DD (default: auto)")
    ap.add_argument("--style", default=None, help="bowls|cosmic|sleep|solfeggio|rain|morning|storm (today = --program today)")
    ap.add_argument("--minutes", type=float, default=None, help="default 60, or the programme length")
    ap.add_argument("--setting", default=None); ap.add_argument("--thunder", default=None)
    ap.add_argument("--intensity", default=None)
    ap.add_argument("--with-short", action="store_true",
                    help="also cut a vertical Short from the best moment (make_sd_short.py)")
    ap.add_argument("--no-ads-title", action="store_true",
                    help="add '(No Mid-Roll Ads)' to the title — only while the channel is not monetized")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--variant", default=None); ap.add_argument("--rain", default=None)
    ap.add_argument("--hz", type=float, default=None); ap.add_argument("--binaural", type=float, default=None)
    ap.add_argument("--scene", choices=sorted(sd_scenes.SCENES), default=None)
    ap.add_argument("--queue-dir", default=str(QUEUE_DIR))
    ap.add_argument("--audio-dir", default=str(AUDIO_DIR))
    a = ap.parse_args()

    if a.style == "today":
        a.program, a.style = "today", None
    pdate = datetime.date.fromisoformat(a.for_date) if a.for_date else publish_date()
    week = pdate.isocalendar()[1]
    prog = None
    if a.program:
        dow = pdate.weekday() if a.program == "today" else DAY_NAMES.index(a.program)
        if a.program != "today" and not a.for_date:                       # next date with that weekday
            pdate = pdate + datetime.timedelta(days=(dow - pdate.weekday()) % 7)
            week = pdate.isocalendar()[1]
        prog = program(dow, week)
        print(f"📅 programme for {pdate:%a %Y-%m-%d}: {prog['style']} {prog['minutes'] / 60:g} h, scene {prog['scene']}, "
              f"{prog['opts']}")
        style = prog["style"]
        for k, v in prog["opts"].items():
            if getattr(a, k, None) is None:
                setattr(a, k, v)
        a.scene = a.scene or prog["scene"]
        a.minutes = a.minutes or prog["minutes"]
        if prog.get("series"):
            prog["series_no"] = next_series_number(prog["series"], commit=False)
    else:
        style = a.style
    a.minutes = a.minutes or 60
    if style not in STYLE_CATEGORY:
        sys.exit(f"unknown style {style}")
    audio_dir = Path(a.audio_dir); audio_dir.mkdir(parents=True, exist_ok=True)
    qdir = Path(a.queue_dir); qdir.mkdir(parents=True, exist_ok=True)

    # 1. music
    cmd = [sys.executable, str(SCRIPTS / "generate_ambient_audio.py"), "--style", style, "--minutes", str(a.minutes),
           "--out-dir", str(audio_dir)]
    for flag, val in (("--seed", a.seed), ("--variant", a.variant), ("--rain", a.rain), ("--hz", a.hz),
                      ("--binaural", a.binaural), ("--setting", a.setting), ("--thunder", a.thunder),
                      ("--intensity", a.intensity)):
        if val is not None:
            cmd += [flag, str(val)]
    print("① music …"); subprocess.run(cmd, check=True)
    rec = json.loads((audio_dir / "ambient_log.jsonl").read_text().splitlines()[-1])
    audio = audio_dir / rec["file"]
    scene = a.scene or sd_scenes.pick_scene(style, rec["seed"])

    stem = f"sd_comp_{STYLE_CATEGORY[style]}_code_{pdate:%Y%m%d}_{rec['seed']}"
    mp4, meta_p, thumb = qdir / f"{stem}.mp4", qdir / f"meta_{stem}.yaml", qdir / f"thumb_{stem}.png"

    # 2. video
    print(f"② video ({scene}) …")
    subprocess.run([sys.executable, str(SCRIPTS / "render_sd_video.py"), "--audio", str(audio), "--scene", scene,
                    "--out", str(mp4)], check=True)
    # 3. thumbnail, 4. meta
    print("③ thumbnail …"); make_thumbnail(mp4, thumb, style, rec.get("params", {}), a.minutes, scene, rec["seed"])
    print("④ meta …")
    title_base = program_title({**prog, "scene": scene, "minutes": a.minutes}, rec.get("params", {}), week) \
        if prog else None
    meta = build_meta(rec, scene, a.minutes, title_base, a.no_ads_title)
    if prog:
        meta["publish_dow"] = pdate.weekday()             # publish_queue.py puts it first on that weekday
        meta["publish_date"] = pdate.isoformat()
        meta["program"] = DAY_NAMES[pdate.weekday()] if a.program == "today" else a.program
        if prog.get("series"):
            meta["series"] = prog["series"]; meta["series_no"] = next_series_number(prog["series"], commit=True)
    meta_p.write_text(yaml.dump(meta, allow_unicode=True, default_flow_style=False, sort_keys=False))
    print(f"✅ queued: {mp4.name}\n   title: {meta['title']}\n   words in description: {len(meta['description'].split())}")
    if a.with_short:
        print("⑤ short …")
        subprocess.run([sys.executable, str(SCRIPTS / "make_sd_short.py"), "--from-meta", str(meta_p),
                        "--queue-dir", str(qdir), "--audio-dir", str(audio_dir)], check=True)


if __name__ == "__main__":
    main()
