#!/usr/bin/env python3
"""
Generate Classical Night Relax (@ClassicalNightRelax) sleep/focus program videos.

Pipeline:
  Phase A — Render shared loops (SleepClassicalLoop, ~4-5 min, no audio)
  Phase B — Assemble long videos (1h / 3h / 8h) via FFmpeg:
             concatenate tracks + loop visual to match total duration

Usage:
  python3 scripts/generate_sleep_classical.py --render-loops-only
  python3 scripts/generate_sleep_classical.py --program sleep_chopin_01
  python3 scripts/generate_sleep_classical.py --program focus_bach_01 --durations 1
  python3 scripts/generate_sleep_classical.py --list-programs
  python3 scripts/generate_sleep_classical.py --regen-meta --program sleep_chopin_01
"""
import argparse, base64, json, logging, re, subprocess, time, yaml
from datetime import datetime
from pathlib import Path

ROOT       = Path(__file__).resolve().parent.parent
REMOTION   = ROOT / "remotion"
PROGRAMS   = ROOT / "config" / "sleep_programs"
MUSIC_DIR  = ROOT / "assets" / "music" / "classical"
LICENSES   = ROOT / "assets" / "music" / "classical" / "licenses.yaml"
QUEUE_CC   = ROOT / "output" / "queue_id"    # Classical Night Relax queue (@ClassicalNightRelax)
QUEUE_EN   = ROOT / "output" / "queue"       # EN kids queue (for kids_sleep track)
LOOPS_DIR  = ROOT / "output" / "_sleep_loops"
TOGETHER_KEY_FILE = ROOT / "credentials" / "together_api_key.txt"
DATE_STR   = datetime.now().strftime("%Y%m%d")

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ── Ken Burns visual loops — AI image per program ─────────────────────────────
KB_N_IMAGES  = 6    # images per program (×30s clips = ~3 min loop)
KB_CLIP_DUR  = 30   # seconds per clip
KB_XFADE_DUR = 3    # crossfade between clips
KB_FADE_SECS = 2    # fade in at start
KB_FPS       = 25
KB_MOTIONS   = ["zoom_in", "pan_right", "zoom_out", "pan_left", "pan_up", "pan_down"]

# Cinematic prompts per program — used for both Ken Burns loop images and thumbnail
PROGRAM_KB_PROMPTS: dict[str, str] = {
    "sleep_chopin_01":          "candlelit grand piano in dark Parisian salon, moonlight through tall windows, romantic atmosphere, cinematic 4K",
    "sleep_chopin_02":          "Romantic era salon with soft candlelight, old gold picture frames, moonlit Parisian interior, warm amber glow",
    "sleep_swan_lake_01":       "moonlit lake at night, white swans gliding on still water, full moon reflection, misty forest background, ethereal blue",
    "sleep_swan_lake_02":       "swan lake at dusk, water surface reflecting stars, mist rising over dark water, dreamlike blue and silver tones",
    "sleep_debussy_01":         "impressionist lily pond at dawn, water reflections, soft morning mist, Monet-inspired, gentle pastel colors",
    "sleep_romantic_night_01":  "candlelit grand library at night, violin resting on velvet, moonlight through arched windows, warm amber fireplace glow",
    "sleep_flute_01":           "misty morning forest, golden rays through ancient trees, dew on leaves, peaceful woodland atmosphere at dawn",
    "sleep_baroque_01":         "baroque palace interior at night, ornate chandeliers, gold architecture, candlelight reflecting on marble floors",
    "sleep_grand_night_01":     "grand concert hall at night, ornate ceiling, dramatic spotlights over empty seats, majestic orchestral atmosphere",
    "focus_beethoven_01":       "dramatic storm clouds over hilltop, lightning in distance, powerful Romantic landscape, dark cinematic 4K",
    "focus_beethoven_02":       "Beethoven-era Vienna concert hall, dramatic lighting, symphony orchestra silhouettes, intense passionate atmosphere",
    "focus_mozart_01":          "Viennese baroque palace ballroom, crystal chandeliers, elegant 18th century interior, golden afternoon sunlight",
    "focus_drama_01":           "dramatic opera house interior, red velvet curtains, ornate gilded balconies, theatrical spotlight, deep shadows",
    "sleep_beethoven_cello_01": "cello leaning against window at dusk, autumn leaves outside, warm lamplight, cozy evening room ambiance",
    "focus_beethoven_cello_01": "cello and piano in sunlit studio, warm afternoon light on wooden floor, sheet music, serene focus atmosphere",
    "sleep_lullaby_01":         "cozy nursery at night, moonlight through curtains, soft mobile above crib, warm amber nightlight, peaceful",
}

THEME_LOOP_SECS = {
    "moon_clouds": 240,
    "night_bear":  300,
    "warm_waves":  240,
    "rain_window": 240,
}

THEME_COMPOSITION = {
    "moon_clouds": "SleepClassicalLoop",
    "night_bear":  "SleepClassicalLoopNightBear",
    "warm_waves":  "SleepClassicalLoop",
    "rain_window": "SleepClassicalLoop",
}

HOURS_TO_LABEL = {1: "1 Hour", 3: "3 Hours", 8: "8 Hours"}

TITLES = {
    "sleep_chopin_01":          "Chopin Nocturnes for Sleep ✨ {dur} | Classical Night Relax",
    "sleep_chopin_02":          "Chopin Complete — Nocturnes, Mazurkas & Études 🌙 {dur} | Classical Night Relax",
    "sleep_debussy_01":         "Debussy for Sleep ✨ {dur} | Classical Night Relax",
    "sleep_swan_lake_01":       "Tchaikovsky Swan Lake for Sleep 🦢 {dur} | Classical Night Relax",
    "sleep_swan_lake_02":       "Swan Lake Act III & IV 🦢 {dur} | Tchaikovsky | Classical Night Relax",
    "sleep_romantic_night_01":  "Romantic Classics for Sleep 🌙 {dur} | Classical Night Relax",
    "sleep_flute_01":           "Flute & Piano for Sleep 🎵 {dur} | Classical Night Relax",
    "sleep_baroque_01":         "Baroque Classics for Sleep 🎻 {dur} | Classical Night Relax",
    "sleep_grand_night_01":     "Grand Night — Orchestral Classics for Sleep 🎻 {dur} | Classical Night Relax",
    "focus_bach_01":            "Bach for Focus & Study 🎵 {dur} | Classical Night Relax",
    "focus_beethoven_01":       "Beethoven for Focus & Study 🎵 {dur} | Classical Night Relax",
    "focus_beethoven_02":       "Beethoven Symphony No. 5 — Complete 🎻 {dur} | Classical Night Relax",
    "focus_mozart_01":          "Mozart for Focus & Study 🎵 {dur} | Classical Night Relax",
    "focus_drama_01":           "Dramatic Classics for Focus 🎻 {dur} | Classical Night Relax",
    "sleep_beethoven_cello_01": "Beethoven Cello Sonatas for Sleep 🎻 {dur} | Classical Night Relax",
    "focus_beethoven_cello_01": "Beethoven Cello Sonatas for Focus & Study 🎻 {dur} | Classical Night Relax",
    "sleep_lullaby_01":         "Classical Lullabies for Sleep 🌙 {dur} | Happy Bear Kids",
}

DESC_TEMPLATES = {
    "calm_classics": """\
Welcome to Classical Night Relax — beautiful classical music for sleep, focus and relaxation.

{program_desc}

🎵 Tracks in this program:
{track_list}

🌙 Perfect for:
• Deep sleep and bedtime relaxation
• Study and concentration sessions
• Meditation and mindfulness practice
• Working from home background music
• Unwinding after a long day

✨ All recordings are public domain performances sourced from Musopen (musopen.org).
Full attribution and license details in the description below.

🎼 Music attribution:
{attribution}

No ads during playback. New programs every week.
Subscribe ▶ @ClassicalNightRelax

© Classical Night Relax 2026 — All rights reserved
#ClassicalNightRelax #SleepMusic #ClassicalMusic #StudyMusic #{composer_tag}Sleep
""",
    "kids_sleep": """\
Welcome to Happy Bear Kids! 🌙 Gentle classical lullabies to help babies and toddlers sleep.

{program_desc}

🌙 Tracks in this program:
{track_list}

✨ Perfect for:
• Baby and toddler bedtime routines
• Nap time relaxation
• Calming an overtired baby
• Peaceful background for night feeds

🎼 Music: Public domain recordings from Musopen (musopen.org)
All composers passed away 200+ years ago — music is in the public domain.

{attribution}

New videos every week! Subscribe ▶ @HappyBearKids1
© Happy Bear Kids 2026
#HappyBearKids #LullabyMusic #BabyLullaby #SleepMusic #ClassicalLullaby
""",
}


def load_program(program_id: str) -> dict:
    path = PROGRAMS / f"{program_id}.yaml"
    if not path.exists():
        log.error(f"Program config not found: {path}")
        raise FileNotFoundError(path)
    with open(path) as f:
        return yaml.safe_load(f)


def load_licenses() -> dict:
    if not LICENSES.exists():
        return {"recordings": []}
    with open(LICENSES) as f:
        return yaml.safe_load(f) or {"recordings": []}


def _rec_to_path(rec: dict) -> Path | None:
    fname = rec.get("file", "")
    if not fname:
        return None
    p = MUSIC_DIR / fname
    return p if p.exists() else None


def _keyword_score(piece_query: str, rec: dict) -> int:
    """Rough overlap score between requested piece name and a registered entry."""
    q_words = set(re.sub(r"[^a-z0-9]", " ", piece_query.lower()).split())
    r_words = set(re.sub(r"[^a-z0-9]", " ", rec.get("piece", "").lower()).split())
    stopwords = {"in", "the", "a", "an", "no", "op", "and", "for", "of", "by"}
    q_words -= stopwords
    r_words -= stopwords
    return len(q_words & r_words)


def find_track_file(track_id: str, licenses_data: dict,
                    composer: str = "", piece: str = "") -> Path | None:
    """
    Find local MP3 by (in order of preference):
      1. Exact ID match
      2. ID prefix match (handles minor naming differences)
      3. Composer + piece keyword overlap
      4. Composer-only fallback (any track from same composer, warns)
    """
    recs = licenses_data.get("recordings", [])
    if not recs:
        return None

    # 1. Exact ID
    for rec in recs:
        if rec.get("id") == track_id or rec.get("id") == f"musopen_{track_id}":
            p = _rec_to_path(rec)
            if p:
                return p

    # 2. ID prefix (first 25 chars)
    prefix = re.sub(r"[^a-z0-9]", "_", track_id.lower())[:25]
    for rec in recs:
        if rec.get("id", "").startswith(prefix):
            p = _rec_to_path(rec)
            if p:
                log.info(f"    Fuzzy ID match: {track_id!r} → {rec['id']}")
                return p

    # 3. Composer + keyword match
    if composer and piece:
        c_low = composer.lower()
        best_score, best_rec = 0, None
        for rec in recs:
            if c_low not in rec.get("composer", "").lower():
                continue
            score = _keyword_score(piece, rec)
            if score > best_score:
                best_score, best_rec = score, rec
        if best_score >= 2 and best_rec:
            p = _rec_to_path(best_rec)
            if p:
                log.info(f"    Keyword match (score={best_score}): {track_id!r} → {best_rec['id']}")
                return p

    # 4. Composer-only fallback
    if composer:
        c_low = composer.lower()
        for rec in recs:
            if c_low in rec.get("composer", "").lower():
                p = _rec_to_path(rec)
                if p:
                    log.warning(f"    Composer fallback for {track_id!r} → {rec['id']}")
                    return p

    return None


def render_shared_loop(theme: str, phase_offset: float = 0.0, force: bool = False) -> Path:
    """Render a 4-5 min seamless loop with no audio. Returns path to MP4."""
    LOOPS_DIR.mkdir(parents=True, exist_ok=True)
    loop_secs  = THEME_LOOP_SECS[theme]
    composition = THEME_COMPOSITION[theme]
    out_mp4 = LOOPS_DIR / f"loop_{theme}_ph{int(phase_offset*100):02d}.mp4"

    if out_mp4.exists() and not force:
        log.info(f"  Loop exists: {out_mp4.name}")
        return out_mp4

    props = {
        "theme":       theme,
        "musicFile":   "",          # no audio in shared loop
        "loopSecs":    loop_secs,
        "phaseOffset": phase_offset,
    }
    cmd = [
        "npx", "remotion", "render", composition,
        f"--props={json.dumps(props)}",
        f"--output={out_mp4}",
        "--log=error",
    ]
    log.info(f"  Rendering loop: {theme} phase={phase_offset:.2f} ({loop_secs}s)…")
    r = subprocess.run(cmd, cwd=str(REMOTION), timeout=3600)
    if r.returncode != 0 or not out_mp4.exists():
        raise RuntimeError(f"Loop render failed: {theme}")
    log.info(f"  ✓ {out_mp4.name} ({out_mp4.stat().st_size / 1024 / 1024:.0f}MB)")
    return out_mp4


def _kb_motion_vf(motion: str) -> str:
    """FFmpeg Ken Burns zoompan filter string."""
    frames = KB_CLIP_DUR * KB_FPS
    scale  = "scale=2688:1536"
    if motion == "zoom_in":
        z, x, y = "min(zoom+0.0006,1.5)", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif motion == "zoom_out":
        z, x, y = "if(eq(on,0),1.5,max(zoom-0.0006,1.0))", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif motion == "pan_right":
        z, x, y = "1.4", f"min(on*(iw-iw/zoom)/{frames-1},iw-iw/zoom)", "ih/2-(ih/zoom/2)"
    elif motion == "pan_left":
        z, x, y = "1.4", f"max((iw-iw/zoom)-on*(iw-iw/zoom)/{frames-1},0)", "ih/2-(ih/zoom/2)"
    elif motion == "pan_up":
        z, x, y = "1.4", "iw/2-(iw/zoom/2)", f"max((ih-ih/zoom)-on*(ih-ih/zoom)/{frames-1},0)"
    else:  # pan_down
        z, x, y = "1.4", "iw/2-(iw/zoom/2)", f"min(on*(ih-ih/zoom)/{frames-1},ih-ih/zoom)"
    zp = f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s=1920x1080:fps={KB_FPS}"
    return f"{scale},{zp}"


def _kb_make_clip(img: Path, out: Path, motion: str) -> bool:
    r = subprocess.run(
        ["ffmpeg", "-y", "-loop", "1", "-i", str(img),
         "-t", str(KB_CLIP_DUR), "-vf", _kb_motion_vf(motion),
         "-c:v", "libx264", "-preset", "fast", "-crf", "22",
         "-pix_fmt", "yuv420p", "-an", str(out)],
        capture_output=True, text=True, timeout=300
    )
    return r.returncode == 0 and out.exists()


def _kb_concat(clips: list[Path], out: Path) -> bool:
    """Xfade-concatenate Ken Burns clips into a seamless visual loop."""
    n = len(clips)
    if n == 1:
        import shutil; shutil.copy(clips[0], out); return True

    inputs = []
    for p in clips:
        inputs += ["-i", str(p)]

    step  = KB_CLIP_DUR - KB_XFADE_DUR
    total = n * KB_CLIP_DUR - (n - 1) * KB_XFADE_DUR
    fc    = (f"[0:v]fade=t=in:st=0:d={KB_FADE_SECS}[f0];"
             f"[f0][1:v]xfade=transition=fade:duration={KB_XFADE_DUR}:offset={step}[v01]")
    for i in range(2, n):
        offset = i * step
        prev   = f"[v{i-1:02d}]"
        nxt    = f"[v{i:02d}]" if i < n - 1 else "[vpre]"
        fc    += f";{prev}[{i}:v]xfade=transition=fade:duration={KB_XFADE_DUR}:offset={offset}{nxt}"
    if n > 2:
        fc += f";[vpre]fade=t=out:st={total - KB_FADE_SECS}:d={KB_FADE_SECS}[vout]"
    else:
        fc += f";[v01]fade=t=out:st={total - KB_FADE_SECS}:d={KB_FADE_SECS}[vout]"

    r = subprocess.run(
        ["ffmpeg", "-y"] + inputs + [
            "-filter_complex", fc, "-map", "[vout]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-an", str(out)],
        capture_output=True, text=True, timeout=600
    )
    if r.returncode != 0 or not out.exists():
        log.error(f"  xfade concat failed: {r.stderr[-300:]}")
        return False
    return True


def render_kenburns_loop(program_id: str, force: bool = False) -> Path | None:
    """Generate FLUX AI images + Ken Burns loop for a program. Returns loop MP4 or None."""
    prompt = PROGRAM_KB_PROMPTS.get(program_id)
    if not prompt:
        return None
    if not TOGETHER_KEY_FILE.exists():
        log.warning("  No Together API key — falling back to CSS loop")
        return None

    loop_path = LOOPS_DIR / f"loop_kenburns_{program_id}.mp4"
    if loop_path.exists() and not force:
        log.info(f"  Ken Burns loop cached: {loop_path.name}")
        return loop_path

    api_key  = TOGETHER_KEY_FILE.read_text().strip()
    imgs_dir = LOOPS_DIR / f"imgs_{program_id}"
    imgs_dir.mkdir(parents=True, exist_ok=True)

    lighting_variants = ["moonlit", "candlelit", "dawn light", "golden hour", "dusk", "twilight"]

    # Step 1: Generate FLUX images
    images: list[Path] = []
    for i in range(KB_N_IMAGES):
        img_path = imgs_dir / f"img_{i:02d}.jpg"
        if img_path.exists() and not force:
            images.append(img_path)
            log.info(f"  Image cached: {img_path.name}")
            continue
        varied = f"{prompt}, {lighting_variants[i % len(lighting_variants)]} atmosphere"
        log.info(f"  Generating image {i+1}/{KB_N_IMAGES} via FLUX…")
        try:
            import requests as req
            resp = req.post(
                "https://api.together.xyz/v1/images/generations",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": "black-forest-labs/FLUX.1-schnell",
                      "prompt": varied, "width": 1344, "height": 768,
                      "steps": 4, "n": 1, "response_format": "b64_json"},
                timeout=90
            )
            resp.raise_for_status()
            img_path.write_bytes(base64.b64decode(resp.json()["data"][0]["b64_json"]))
            images.append(img_path)
            time.sleep(2)
        except Exception as e:
            log.warning(f"  Image {i+1} failed: {e}")

    if len(images) < 2:
        log.error(f"  Only {len(images)} images generated — skipping Ken Burns")
        return None

    # Step 2: Ken Burns clips
    clips_dir = LOOPS_DIR / f"clips_{program_id}"
    clips_dir.mkdir(exist_ok=True)
    clips: list[Path] = []
    for i, img in enumerate(images):
        clip = clips_dir / f"clip_{i:02d}.mp4"
        if clip.exists() and not force:
            clips.append(clip)
            continue
        motion = KB_MOTIONS[i % len(KB_MOTIONS)]
        log.info(f"  Ken Burns clip {i+1}/{len(images)}: {motion}")
        if _kb_make_clip(img, clip, motion):
            clips.append(clip)
        else:
            log.warning(f"  Clip {i+1} failed — skipping")

    if not clips:
        log.error("  No clips created — falling back to CSS loop")
        return None

    # Step 3: Xfade concat → loop
    log.info(f"  Concat {len(clips)} clips → {loop_path.name}")
    LOOPS_DIR.mkdir(parents=True, exist_ok=True)
    if _kb_concat(clips, loop_path):
        log.info(f"  ✓ Ken Burns loop: {loop_path.name} ({loop_path.stat().st_size / 1024**2:.0f}MB)")
        return loop_path

    log.error("  Loop concat failed — falling back to CSS loop")
    return None


def _get_mp3_duration(path: Path) -> float:
    """Return duration in seconds via ffprobe."""
    import json as _json
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", str(path)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        for s in _json.loads(r.stdout).get("streams", []):
            if s.get("duration"):
                return float(s["duration"])
    except Exception:
        pass
    return 0.0


def build_audio_track(program: dict, licenses_data: dict, out_dir: Path,
                      target_secs: int = 0) -> Path | None:
    """
    Concatenate track MP3s into a single audio file covering at least target_secs.
    When found tracks are shorter than target_secs, the playlist is repeated.
    Returns path to combined MP3 or None if no tracks found.
    """
    tracks = program.get("tracks", [])
    if not tracks:
        return None

    found = []
    for t in tracks:
        f = find_track_file(t["id"], licenses_data,
                            composer=t.get("composer", ""),
                            piece=t.get("piece", ""))
        if f:
            dur = t.get("duration_sec") or _get_mp3_duration(f)
            found.append((str(f), dur))
        else:
            log.warning(f"  Track not found: {t['id']} ({t.get('piece','?')}) — skipped")

    if not found:
        log.warning("  No track files found — will generate visual-only (no audio)")
        return None

    # Loop the playlist until we cover target_secs
    total_dur = sum(d for _, d in found)
    if target_secs > 0 and total_dur < target_secs:
        reps = int(target_secs / total_dur) + 2
        log.info(f"  Audio {total_dur/60:.1f}min < {target_secs/3600:.0f}h target "
                 f"— repeating playlist ×{reps}")
        found = found * reps

    concat_list = out_dir / "concat_tracks.txt"
    with open(concat_list, "w") as f:
        for fp, _ in found:
            # Escape single quotes in path (ffmpeg concat uses single-quote delimiters)
            safe = str(fp).replace("'", "'\\''")
            f.write(f"file '{safe}'\n")

    audio_out = out_dir / "audio_combined.mp3"
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c:a", "libmp3lame", "-b:a", "192k",
    ]
    if target_secs > 0:
        cmd += ["-t", str(target_secs)]
    cmd.append(str(audio_out))

    # timeout scales with target: at least 1200s, or target/5 (e.g. 3h → 2160s, 8h → 5760s)
    audio_timeout = max(1200, target_secs // 5) if target_secs > 0 else 1200
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=audio_timeout)
    if r.returncode != 0 or not audio_out.exists():
        log.error(f"  Audio concat failed: {r.stderr[:300]}")
        return None
    size_mb = audio_out.stat().st_size / 1024 / 1024
    log.info(f"  ✓ Audio: {audio_out.name} ({size_mb:.1f}MB, "
             f"{len(found)} track instances)")
    return audio_out


def assemble_video(loop_mp4: Path, audio_mp3: Path | None,
                   target_hours: int, out_mp4: Path) -> bool:
    """Loop visual to fill target duration, overlay audio, write output."""
    target_secs = target_hours * 3600
    # Use faster preset for long videos: slow→fast saves hours on 8h renders.
    preset = "slow" if target_hours <= 1 else ("medium" if target_hours <= 3 else "fast")
    # Timeout scales: 1h→3600s, 3h→10800s, 8h→28800s plus 20% margin.
    video_timeout = int(target_secs * 1.2) + 3600

    if audio_mp3:
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", str(loop_mp4),   # infinite loop visual
            "-i", str(audio_mp3),
            "-t", str(target_secs),
            "-map", "0:v:0",            # video from loop
            "-map", "1:a:0",            # audio from music MP3, NOT from silent loop
            "-c:v", "libx264", "-preset", preset, "-crf", "20",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            str(out_mp4),
        ]
    else:
        # Visual only (no audio yet — placeholder)
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", str(loop_mp4),
            "-t", str(target_secs),
            "-c:v", "libx264", "-preset", preset, "-crf", "20",
            "-an",
            "-movflags", "+faststart",
            str(out_mp4),
        ]

    log.info(f"  Assembling {target_hours}h video (preset={preset}) → {out_mp4.name}…")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=video_timeout)
    if r.returncode != 0 or not out_mp4.exists():
        log.error(f"  Assembly failed: {r.stderr[:300]}")
        return False
    size_gb = out_mp4.stat().st_size / 1024 / 1024 / 1024
    log.info(f"  ✓ {out_mp4.name} ({size_gb:.2f}GB)")
    return True


def make_track_list(program: dict) -> str:
    lines = []
    for t in program.get("tracks", []):
        composer = t.get("composer", "")
        piece = t.get("piece", "")
        dur = t.get("duration_sec", 0)
        m, s = divmod(dur, 60)
        lines.append(f"• {composer} — {piece} ({m}:{s:02d})")
    return "\n".join(lines)


def make_attribution(program: dict) -> str:
    composers = set(t.get("composer", "") for t in program.get("tracks", []))
    parts = []
    for c in sorted(composers):
        parts.append(f"Music by {c}. Performed by public domain recording (Musopen.org). "
                     f"Licensed under Public Domain / CC0.")
    return "\n".join(parts)


def write_meta(program: dict, hours: int, queue: Path, out_name: str):
    prog_id  = program["id"]
    track    = program.get("track", "calm_classics")
    dur_label = HOURS_TO_LABEL.get(hours, f"{hours} Hours")
    title_tpl = TITLES.get(prog_id, "Classical Music for Sleep ✨ {dur} | Classical Night Relax")
    title    = title_tpl.format(dur=dur_label)

    composer_names = set(t.get("composer", "").split()[0] for t in program.get("tracks", []))
    composer_tag   = "".join(sorted(composer_names))

    desc_tpl = DESC_TEMPLATES.get(track, DESC_TEMPLATES["calm_classics"])
    desc = desc_tpl.format(
        program_desc=f"{dur_label} of {', '.join(sorted(composer_names))} for {track.replace('_', ' ')}.",
        track_list=make_track_list(program),
        attribution=make_attribution(program),
        composer_tag=composer_tag,
    )

    tags = (program.get("tags", []) +
            [dur_label.lower(), f"{hours} hour music", "classical night relax",
             "classical music", "sleep music", "relaxation"])[:40]

    meta = {
        "title":          title,
        "description":    desc,
        "video_type":     program.get("video_type", "sleep_program"),
        "theme":          program["visual_theme"],
        "language":       "en",
        "is_short":       False,
        "status":         "public",
        "made_for_kids":  program.get("made_for_kids", False),
        "duration_hours": hours,
        "program_id":     prog_id,
        "tags":           tags,
    }

    stem = Path(out_name).stem
    meta_path = queue / f"meta_{stem}.yaml"
    with open(meta_path, "w") as f:
        yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    log.info(f"  Meta → {meta_path.name}")


def generate_thumbnail(out_mp4: Path, program: dict, hours: int) -> bool:
    thumb_path = out_mp4.parent / f"thumb_{out_mp4.stem}.png"
    if thumb_path.exists():
        return True

    prog_id = program.get("id", "")

    # Prefer a cached KB image (already generated for the loop)
    kb_img = LOOPS_DIR / f"imgs_{prog_id}" / "img_00.jpg"
    if kb_img.exists():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("gat", ROOT / "scripts" / "generate_ai_thumbs.py")
            gat  = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(gat)
            thumb_path.write_bytes(gat.resize_to_720p(kb_img.read_bytes()))
            log.info(f"  Thumb from KB image → {thumb_path.name}")
            return True
        except Exception as e:
            log.warning(f"  KB thumb resize failed: {e}")

    # Fall back: generate new FLUX image from prompt
    if not TOGETHER_KEY_FILE.exists():
        return False
    prompt = PROGRAM_KB_PROMPTS.get(prog_id)
    if not prompt:
        theme = program.get("visual_theme", "moon_clouds")
        prompt_map = {
            "moon_clouds": "peaceful moonlit night with classical music ambiance, sleep relaxation, dark blue",
            "night_bear":  "sleeping bear silhouette under moonlit sky with fireflies, cozy peaceful",
            "warm_waves":  "ocean waves at dusk with amber sunset glow, classical music relaxation",
            "rain_window": "rainy window with warm candle glow inside, classical music study, cozy",
        }
        prompt = prompt_map.get(theme, "peaceful classical music ambiance, sleep and relaxation")
    composers = set(t.get("composer", "").split()[0] for t in program.get("tracks", []))
    prompt += f", {', '.join(sorted(composers))}"

    try:
        import requests as req
        api_key = TOGETHER_KEY_FILE.read_text().strip()
        resp = req.post(
            "https://api.together.xyz/v1/images/generations",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": "black-forest-labs/FLUX.1-schnell",
                  "prompt": prompt, "width": 1280, "height": 720,
                  "steps": 4, "n": 1, "response_format": "b64_json"},
            timeout=60
        )
        resp.raise_for_status()
        thumb_path.write_bytes(base64.b64decode(resp.json()["data"][0]["b64_json"]))
        log.info(f"  Thumb → {thumb_path.name}")
        return True
    except Exception as e:
        log.warning(f"  Thumbnail skipped: {e}")
        return False


def cmd_render_loops_only(force: bool = False):
    """Render all 4 shared CSS loops without audio."""
    log.info("=== Rendering shared SleepClassicalLoop files ===")
    for theme in THEME_LOOP_SECS:
        render_shared_loop(theme, phase_offset=0.0, force=force)
    log.info("Done.")


def cmd_gen_visuals(force: bool = False):
    """Generate Ken Burns visual loops for all programs that have a prompt."""
    log.info("=== Generating Ken Burns visual loops ===")
    for prog_id in PROGRAM_KB_PROMPTS:
        log.info(f"\n--- {prog_id} ---")
        render_kenburns_loop(prog_id, force=force)
    log.info("\nDone — all Ken Burns loops generated.")


def cmd_generate_program(program_id: str, durations: list[int] | None,
                         regen_meta: bool, dry_run: bool, force: bool):
    program = load_program(program_id)
    licenses_data = load_licenses()

    theme       = program["visual_theme"]
    track_type  = program.get("track", "calm_classics")
    queue       = QUEUE_EN if track_type == "kids_sleep" else QUEUE_CC
    hours_list  = durations or program.get("durations_hours", [1, 3, 8])

    log.info(f"=== Program: {program_id} | theme: {theme} | queue: {queue.name} ===")

    loop_mp4 = None
    audio_mp3 = None

    if not regen_meta and not dry_run:
        # Prefer AI image + Ken Burns loop; fall back to CSS Remotion animation
        loop_mp4 = render_kenburns_loop(program_id, force=force)
        if loop_mp4 is None:
            loop_mp4 = render_shared_loop(theme, force=force)

        # Build audio long enough for the longest requested duration
        max_hours = max(hours_list) if hours_list else 1
        tmp_dir = ROOT / "output" / f"_tmp_{program_id}"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        audio_mp3 = build_audio_track(program, licenses_data, tmp_dir,
                                      target_secs=max_hours * 3600)
    elif not regen_meta and dry_run:
        # In dry-run: just verify which tracks are found, skip rendering
        log.info("  [dry-run] Checking track availability:")
        for t in program.get("tracks", []):
            p = find_track_file(t["id"], licenses_data,
                                composer=t.get("composer", ""),
                                piece=t.get("piece", ""))
            status = f"✓ {p.name}" if p else "✗ NOT FOUND"
            log.info(f"    {t['id']}: {status}")

    queue.mkdir(parents=True, exist_ok=True)
    generated = 0

    for hours in hours_list:
        dur_label = HOURS_TO_LABEL.get(hours, f"{hours}h")
        out_name  = f"{program_id}_{hours}h_{DATE_STR}.mp4"
        out_mp4   = queue / out_name

        if not regen_meta and not dry_run and not out_mp4.exists():
            if loop_mp4 is None:
                log.error("No loop MP4 available — run --render-loops-only first")
                continue
            ok = assemble_video(loop_mp4, audio_mp3, hours, out_mp4)
            if not ok:
                continue

        if out_mp4.exists() or dry_run or regen_meta:
            write_meta(program, hours, queue, out_name)
            if not dry_run:
                generate_thumbnail(out_mp4 if out_mp4.exists() else queue / out_name,
                                   program, hours)
            generated += 1

    log.info(f"Done: {generated}/{len(hours_list)} for {program_id}")


def main():
    parser = argparse.ArgumentParser(description="Generate Classical Night Relax sleep programs")
    parser.add_argument("--render-loops-only", action="store_true",
                        help="Only render the 4 shared CSS loop MP4s (no audio, no assembly)")
    parser.add_argument("--gen-visuals", action="store_true",
                        help="Generate Ken Burns visual loops for all programs (FLUX images + FFmpeg)")
    parser.add_argument("--program",    help="Program ID (e.g. sleep_chopin_01)")
    parser.add_argument("--durations",  type=int, nargs="+",
                        help="Hours to generate (e.g. --durations 1 3). Default: from config")
    parser.add_argument("--list-programs", action="store_true", help="List available programs")
    parser.add_argument("--regen-meta", action="store_true", help="Regenerate meta+thumb only")
    parser.add_argument("--dry-run",    action="store_true")
    parser.add_argument("--force",      action="store_true", help="Re-render even if exists")
    args = parser.parse_args()

    if args.list_programs:
        print("Available programs:")
        for p in sorted(PROGRAMS.glob("*.yaml")):
            prog = yaml.safe_load(p.read_text())
            print(f"  {prog['id']:30s} track={prog.get('track','?')} theme={prog.get('visual_theme','?')}")
        return

    if args.render_loops_only:
        cmd_render_loops_only(force=args.force)
        return

    if args.gen_visuals:
        cmd_gen_visuals(force=args.force)
        return

    if args.program:
        cmd_generate_program(
            program_id=args.program,
            durations=args.durations,
            regen_meta=args.regen_meta,
            dry_run=args.dry_run,
            force=args.force,
        )
        return

    parser.print_help()


if __name__ == "__main__":
    main()
