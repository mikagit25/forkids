#!/usr/bin/env python3
"""
Generate Sacred Drift meditation videos.

Pipeline per track:
  1. Pick audio from library
  2. Auto-detect visual theme from track title
  3. Generate 6 FLUX AI images (Together.ai)
  4. Ken Burns video loop matched to audio duration
  5. Mix audio + video via FFmpeg
  6. Write meta YAML + thumbnail to sacred_drift/output/queue/

Usage:
  python3 scripts/generate_sacred_drift.py --list
  python3 scripts/generate_sacred_drift.py --track "Crown Chakra Awakening"
  python3 scripts/generate_sacred_drift.py --all --limit 5
  python3 scripts/generate_sacred_drift.py --all          # process all ungenerated tracks
"""

import argparse, base64, json, logging, re, subprocess, sys, time, shutil, yaml
from datetime import datetime
from pathlib import Path

ROOT       = Path(__file__).resolve().parent.parent
AUDIO_DIR  = ROOT / 'assets/audio/suno_meditation/Meditation'
AUDIO_DIR2 = ROOT / 'sacred_drift/audio/uploads'   # new tracks uploaded via browser
QUEUE_DIR  = ROOT / 'sacred_drift/output/queue'
THUMB_DIR = ROOT / 'sacred_drift/thumbnails'
THEMES_DIR = ROOT / 'assets/visual_themes'
CONFIG    = ROOT / 'sacred_drift/config/channel_metadata_sd.yaml'
TOGETHER_KEY_FILE = ROOT / 'credentials/together_api_key.txt'
DATE_STR  = datetime.now().strftime('%Y%m%d')

# Keyword → local visual theme directory (fallback when Together.ai unavailable)
KEYWORD_TO_THEME = [
    ('crown chakra',    'aurora_borealis'),
    ('third eye',       'aurora_borealis'),
    ('full chakra',     'aurora_borealis'),
    ('chakra',          'aurora_borealis'),
    ('cosmic',          'deep_space'),
    ('space',           'deep_space'),
    ('deep sleep',      'fireplace_cabin'),
    ('sleep',           'evening_piano'),
    ('forest',          'rainforest_night'),
    ('bamboo',          'rainforest_night'),
    ('waterfall',       'distant_waterfall'),
    ('ocean',           'distant_waterfall'),
    ('rain',            'night_rain'),
    ('thunder',         'night_rain'),
    ('mountain',        'mountain_snow'),
    ('winter',          'mountain_snow'),
    ('fireplace',       'fireplace_cabin'),
    ('gong',            'zen_garden'),
    ('tibetan',         'zen_garden'),
    ('bowl',            'zen_garden'),
    ('zen',             'zen_garden'),
    ('buddhist',        'zen_garden'),
    ('temple',          'zen_garden'),
    ('monastery',       'zen_garden'),
    ('reiki',           'lavender_fields'),
    ('anxiety',         'lavender_fields'),
    ('stress',          'lavender_fields'),
    ('healing',         'lavender_fields'),
    ('heart chakra',    'lavender_fields'),
    ('yoga',            'cherry_blossoms'),
    ('morning',         'cherry_blossoms'),
    ('root chakra',     'autumn_forest'),
    ('sacral chakra',   'cherry_blossoms'),
    ('solar plexus',    'cherry_blossoms'),
    ('throat chakra',   'distant_waterfall'),
]

KB_N_IMAGES  = 6
KB_CLIP_DUR  = 30   # seconds per image
KB_XFADE_DUR = 3
KB_FADE_SECS = 2
KB_FPS       = 24

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')


# ── Visual prompt selection ───────────────────────────────────────────────────

def get_visual_prompt(track_name: str, meta: dict) -> str:
    prompts = meta.get('visual_prompts', {})
    name_lower = track_name.lower()
    priority = [
        ('crown chakra',    'crown_chakra'),
        ('heart chakra',    'heart_chakra'),
        ('root chakra',     'root_chakra'),
        ('sacral chakra',   'sacral_chakra'),
        ('solar plexus',    'solar_plexus'),
        ('third eye',       'third_eye'),
        ('throat chakra',   'throat_chakra'),
        ('chakra',          'full_chakra'),
        ('deep sleep',      'deep_sleep'),
        ('sleep',           'sleep'),
        ('forest',          'forest'),
        ('ocean',           'ocean'),
        ('rain',            'rain'),
        ('mountain',        'mountain'),
        ('cosmic',          'cosmic'),
        ('space',           'space'),
        ('tibetan',         'tibetan'),
        ('gong',            'gong'),
        ('reiki',           'reiki'),
        ('buddhist',        'buddhist'),
        ('native american', 'native_american'),
        ('yoga',            'yoga'),
        ('anxiety',         'anxiety'),
        ('stress',          'anxiety'),
    ]
    for keyword, key in priority:
        if keyword in name_lower:
            return prompts.get(key, prompts.get('default', ''))
    return prompts.get('default', 'ethereal sacred space, golden light, cosmic peace, no text')


# ── FLUX image generation ─────────────────────────────────────────────────────

def generate_flux_image(prompt: str, out_path: Path) -> bool:
    key_file = TOGETHER_KEY_FILE
    if not key_file.exists():
        log.error("Together.ai key not found")
        return False
    api_key = key_file.read_text().strip()

    import urllib.request
    payload = json.dumps({
        "model": "black-forest-labs/FLUX.1.1-pro",
        "prompt": prompt,
        "width": 1280, "height": 704,
        "steps": 4, "n": 1,
        "response_format": "b64_json"
    }).encode()

    req = urllib.request.Request(
        'https://api.together.xyz/v1/images/generations',
        data=payload,
        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
        method='POST'
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
        b64 = data['data'][0].get('b64_json', '')
        if not b64:
            log.error("Empty image response")
            return False
        out_path.write_bytes(base64.b64decode(b64))
        log.info(f"  Image saved: {out_path.name}")
        return True
    except Exception as e:
        log.error(f"  FLUX error: {e}")
        return False


# ── Local image fallback ──────────────────────────────────────────────────────

def get_fallback_theme(track_name: str) -> str:
    """Return best matching local visual_themes directory name."""
    name_lower = track_name.lower()
    for keyword, theme in KEYWORD_TO_THEME:
        if keyword in name_lower:
            return theme
    return 'zen_garden'  # default


def get_fallback_images(track_name: str, n: int = KB_N_IMAGES) -> list[Path]:
    """Pick n evenly-spaced frames from the matching local visual theme."""
    theme = get_fallback_theme(track_name)
    theme_dir = THEMES_DIR / theme
    frames = sorted(theme_dir.glob('frame_*.png'))
    if not frames:
        # try any PNG
        frames = sorted(theme_dir.glob('*.png'))
    if not frames:
        log.warning(f"No frames found in {theme_dir}")
        return []
    # pick n evenly-spaced
    step = max(1, len(frames) // n)
    picked = [frames[i * step] for i in range(n)][:n]
    return picked


# ── Ken Burns video from images ───────────────────────────────────────────────

MOTIONS = ['zoom_in', 'pan_right', 'zoom_out', 'pan_left', 'pan_up', 'pan_down']

def ken_burns_filter(motion: str, w: int = 1280, h: int = 704) -> str:
    dur = KB_CLIP_DUR
    fps = KB_FPS
    n   = dur * fps
    if motion == 'zoom_in':
        return (f"scale=8000:-1,zoompan=z='min(zoom+0.0015,1.5)':x='iw/2-(iw/zoom/2)'"
                f":y='ih/2-(ih/zoom/2)':d={n}:s={w}x{h}:fps={fps}")
    if motion == 'zoom_out':
        return (f"scale=8000:-1,zoompan=z='if(lte(zoom,1.0),1.5,max(1.0,zoom-0.0015))'"
                f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s={w}x{h}:fps={fps}")
    if motion == 'pan_right':
        return (f"scale={w*2}:{h},zoompan=z=1:x='min(x+1,iw-{w})':y=0:d={n}:s={w}x{h}:fps={fps}")
    if motion == 'pan_left':
        return (f"scale={w*2}:{h},zoompan=z=1:x='max(0,iw-{w}-on)':y=0:d={n}:s={w}x{h}:fps={fps}")
    if motion == 'pan_up':
        return (f"scale={w}:{h*2},zoompan=z=1:x=0:y='min(y+1,ih-{h})':d={n}:s={w}x{h}:fps={fps}")
    # pan_down
    return (f"scale={w}:{h*2},zoompan=z=1:x=0:y='max(0,ih-{h}-on)':d={n}:s={w}x{h}:fps={fps}")


def build_ken_burns_video(images: list[Path], out_path: Path, audio_dur: float) -> bool:
    tmp_clips = []
    try:
        # Build one clip per image
        for i, img in enumerate(images):
            motion = MOTIONS[i % len(MOTIONS)]
            clip = out_path.parent / f'_kb_clip_{i}.mp4'
            vf = ken_burns_filter(motion)
            fade_in  = f"fade=t=in:st=0:d={KB_FADE_SECS}:alpha=0"
            fade_out = f"fade=t=out:st={KB_CLIP_DUR - KB_FADE_SECS}:d={KB_FADE_SECS}:alpha=0"
            cmd = [
                'ffmpeg', '-y', '-loop', '1', '-i', str(img),
                '-vf', f"{vf},{fade_in},{fade_out}",
                '-t', str(KB_CLIP_DUR), '-c:v', 'libx264', '-crf', '20',
                '-preset', 'fast', '-pix_fmt', 'yuv420p', str(clip)
            ]
            r = subprocess.run(cmd, capture_output=True)
            if r.returncode != 0:
                log.error(f"Clip {i} failed: {r.stderr.decode()[-300:]}")
                return False
            tmp_clips.append(clip)

        # Loop clips to cover audio_dur + crossfade
        loop_dur = KB_N_IMAGES * KB_CLIP_DUR
        loops_needed = int(audio_dur / loop_dur) + 2

        # Build concat list
        concat_file = out_path.parent / '_kb_concat.txt'
        with open(concat_file, 'w') as f:
            for _ in range(loops_needed):
                for clip in tmp_clips:
                    f.write(f"file '{clip.resolve()}'\n")

        # Concat + trim to audio_dur
        loop_video = out_path.parent / '_kb_loop.mp4'
        cmd = [
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(concat_file),
            '-t', str(audio_dur + 1), '-c', 'copy', str(loop_video)
        ]
        r = subprocess.run(cmd, capture_output=True)
        if r.returncode != 0:
            log.error(f"Concat failed: {r.stderr.decode()[-300:]}")
            return False

        shutil.move(str(loop_video), str(out_path))
        return True
    finally:
        for c in tmp_clips:
            c.unlink(missing_ok=True)
        for f in [out_path.parent / '_kb_concat.txt']:
            f.unlink(missing_ok=True)


# ── Audio processing ──────────────────────────────────────────────────────────

def get_audio_duration(audio_path: Path) -> float:
    r = subprocess.run(
        ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', str(audio_path)],
        capture_output=True
    )
    data = json.loads(r.stdout)
    return float(data['format']['duration'])


def mix_video_audio(video_path: Path, audio_path: Path, out_path: Path, duration: float) -> bool:
    fade_out_start = max(0, duration - 3)
    cmd = [
        'ffmpeg', '-y',
        '-i', str(video_path),
        '-i', str(audio_path),
        '-map', '0:v:0', '-map', '1:a:0',
        '-vf', f"fade=t=out:st={fade_out_start}:d=3",
        '-af', f"afade=t=out:st={fade_out_start}:d=3",
        '-t', str(duration),
        '-c:v', 'libx264', '-crf', '20', '-preset', 'fast',
        '-c:a', 'aac', '-b:a', '192k',
        '-pix_fmt', 'yuv420p',
        str(out_path)
    ]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        log.error(f"Mix failed: {r.stderr.decode()[-400:]}")
        return False
    return True


# ── Meta YAML ────────────────────────────────────────────────────────────────

def build_title(track_name: str, duration: float) -> str:
    mins = int(duration / 60)
    hours = mins // 60
    rem_mins = mins % 60
    if hours > 0:
        dur_str = f"{hours}h {rem_mins:02d}min" if rem_mins else f"{hours}h"
    else:
        dur_str = f"{mins}min"
    return f"{track_name} 🔮 {dur_str} | Sacred Drift"


def _build_timestamps(duration: float) -> str:
    if duration < 300:  # under 5 min — no timestamps
        return ""
    def fmt(s): return f"{int(s/60):02d}:{int(s)%60:02d}"
    points = [(0, "Opening — settling in")]
    if duration > 600:
        points.append((120, "Settling in"))
    points.append((duration * 0.25, "Deepening"))
    points.append((duration * 0.50, "Deep immersion"))
    points.append((duration * 0.75, "Integration"))
    points.append((max(duration - 120, duration * 0.85), "Closing"))
    points.sort(key=lambda x: x[0])
    lines = "Timestamps:\n" + "\n".join(f"{fmt(s)} {label}" for s, label in points)
    return lines + "\n"


def build_description(track_name: str, duration: float, meta: dict) -> str:
    mins = int(duration / 60)
    hours = mins // 60
    rem_mins = mins % 60
    dur_str = f"{hours} hour {rem_mins} min" if hours else f"{mins} minutes"

    name_lower = track_name.lower()
    if 'chakra' in name_lower:
        hook = f"Allow this {dur_str} session to gently activate and balance your energy centers. Let the healing frequencies wash through each chakra, releasing blockages and restoring flow."
        benefit = "chakra balancing, energy healing, spiritual alignment"
    elif 'sleep' in name_lower or 'drone' in name_lower:
        hook = f"Drift into deep, restorative sleep with this {dur_str} ambient soundscape. Designed to slow the mind, release the day, and guide you into peaceful rest."
        benefit = "deep sleep, insomnia relief, rest and recovery"
    elif 'meditation' in name_lower or 'mindful' in name_lower:
        hook = f"Settle into stillness with this {dur_str} meditation session. Allow thoughts to dissolve as you arrive in the present moment — calm, clear, and at peace."
        benefit = "meditation, mindfulness, inner peace, stress relief"
    elif 'healing' in name_lower or 'reiki' in name_lower or 'gong' in name_lower:
        hook = f"Let this {dur_str} healing session restore balance in body, mind and spirit. Sound has been used for millennia as a tool for deep healing — open yourself to its power."
        benefit = "sound healing, energy healing, restoration"
    elif 'anxiety' in name_lower or 'stress' in name_lower:
        hook = f"Release tension and quiet anxious thoughts with this gentle {dur_str} soundscape. Each breath becomes easier, each moment more peaceful."
        benefit = "anxiety relief, stress relief, calming"
    elif 'yoga' in name_lower or 'morning' in name_lower:
        hook = f"Begin your practice with intention. This {dur_str} session supports movement, breath and presence — the perfect companion for yoga, stretching or morning ritual."
        benefit = "yoga music, morning routine, mindful movement"
    else:
        hook = f"Surrender to stillness with this {dur_str} sacred soundscape. Close your eyes, breathe deeply, and let Sacred Drift carry you to a place of profound inner quiet."
        benefit = "relaxation, inner peace, meditation, stress relief"

    footer = meta.get('video_defaults', {}).get('description_footer', '')

    return f"""{track_name}

{hook}

✨ Best experienced with headphones at a comfortable volume.
🌙 Ideal for: {benefit}

How to use this session:
• Find a quiet, comfortable space
• Close your eyes and take three deep breaths
• Let your body relax completely
• Allow the music to guide you inward
• Stay as long as you need

────────────────────────────
About Sacred Drift:
Sacred Drift is a sanctuary of sound — meditation music, healing frequencies and sacred soundscapes for those seeking deep rest, inner calm and spiritual connection. New sessions released every week.

Subscribe and turn on notifications so you never miss a session. 🔮

────────────────────────────
{_build_timestamps(duration)}{footer}"""


def build_tags(track_name: str, meta: dict) -> list:
    base = meta.get('video_defaults', {}).get('tags_base', [])
    name_words = [w.lower() for w in re.split(r'[\s\-_]+', track_name) if len(w) > 3]
    extra = []
    n = track_name.lower()
    if 'chakra' in n: extra += ['chakra healing', 'chakra meditation', 'chakra balancing', 'energy healing']
    if 'sleep' in n: extra += ['sleep music', 'deep sleep', 'insomnia relief', 'sleep fast']
    if 'meditation' in n: extra += ['guided meditation', 'mindfulness', 'zen music', 'calm music']
    if 'healing' in n or 'reiki' in n: extra += ['sound healing', 'reiki music', 'healing music']
    if 'gong' in n or 'tibetan' in n or 'bowl' in n: extra += ['tibetan bowls', 'singing bowls', 'gong bath']
    if 'binaural' in n: extra += ['binaural beats', 'theta waves', 'delta waves', 'alpha waves']
    if '432' in n: extra += ['432hz', '432hz music', 'healing frequencies']
    if '528' in n: extra += ['528hz', 'love frequency', 'dna repair frequency']
    if 'forest' in n: extra += ['forest sounds', 'nature sounds', 'forest meditation']
    if 'ocean' in n: extra += ['ocean waves', 'ocean sounds', 'waves meditation']
    all_tags = extra + base
    seen, result, total = set(), [], 0
    for t in all_tags:
        if t and t not in seen and len(t) <= 30 and len(result) < 30 and total + len(t) <= 500:
            seen.add(t)
            result.append(t)
            total += len(t)
    return result


# ── Track deduplication ───────────────────────────────────────────────────────

def canonical_name(filename: str) -> str:
    """Strip duplicates like (1), (2), II — keep base name."""
    name = Path(filename).stem
    name = re.sub(r'\s*\(\d+\)$', '', name).strip()
    name = re.sub(r'\s+II+$', '', name).strip()
    name = re.sub(r'\s+\d+$', '', name).strip()
    return name


def get_unique_tracks() -> list[Path]:
    seen, tracks = set(), []
    sources = list(AUDIO_DIR.glob('*.mp3')) + list(AUDIO_DIR2.glob('*.mp3'))
    for mp3 in sorted(sources, key=lambda p: p.name):
        key = canonical_name(mp3.name)
        if key not in seen:
            seen.add(key)
            tracks.append(mp3)
    return tracks


def already_generated(track_name: str) -> bool:
    safe = re.sub(r'[^\w\s-]', '', track_name).strip().replace(' ', '_').lower()
    return any(QUEUE_DIR.glob(f'*{safe}*.mp4'))


# ── Main ──────────────────────────────────────────────────────────────────────

def process_track(audio_path: Path, meta: dict, tmp_dir: Path) -> bool:
    track_name = canonical_name(audio_path.name)
    safe_name  = re.sub(r'[^\w\s-]', '', track_name).strip().replace(' ', '_').lower()
    out_stem   = f"sd_{safe_name}_{DATE_STR}"
    out_mp4    = QUEUE_DIR / f"{out_stem}.mp4"
    out_meta   = QUEUE_DIR / f"meta_{out_stem}.yaml"
    out_thumb  = QUEUE_DIR / f"thumb_{out_stem}.png"

    if out_mp4.exists():
        log.info(f"SKIP (exists): {track_name}")
        return True

    log.info(f"\n{'='*60}")
    log.info(f"Processing: {track_name}")
    log.info(f"Audio: {audio_path.name}")

    # 1. Audio duration — loop short tracks to LOOP_TO_SEC (1 hour)
    raw_duration = get_audio_duration(audio_path)
    log.info(f"Raw duration: {raw_duration:.0f}s ({raw_duration/60:.1f} min)")

    if raw_duration < LOOP_TO_SEC:
        looped_mp3 = tmp_dir / '_looped.mp3'
        log.info(f"Looping audio to {LOOP_TO_SEC/60:.0f} min...")
        duration = loop_audio_to_duration(audio_path, looped_mp3, LOOP_TO_SEC)
        if duration < 60:
            log.error("Loop audio failed")
            return False
        active_audio = looped_mp3
        log.info(f"Looped: {duration:.0f}s ({duration/60:.1f} min)")
    else:
        duration = raw_duration
        active_audio = audio_path

    # 2. Visual prompt
    prompt = get_visual_prompt(track_name, meta)
    log.info(f"Prompt: {prompt[:80]}...")

    # 3. Generate FLUX images (fallback to local theme images if API unavailable)
    images = []
    flux_failed = False
    for i in range(KB_N_IMAGES):
        if flux_failed:
            break
        img_path = tmp_dir / f"img_{i:02d}.jpg"
        variation = f"{prompt}, variation {i+1}, ultra detailed, cinematic lighting"
        ok = generate_flux_image(variation, img_path)
        if ok:
            images.append(img_path)
            time.sleep(1)
        else:
            flux_failed = True
            log.warning("Together.ai unavailable — using local visual theme images")
            fallback = get_fallback_images(track_name)
            if not fallback:
                log.error("No fallback images found")
                return False
            images = fallback
            log.info(f"  Using theme: {get_fallback_theme(track_name)} ({len(images)} frames)")

    # 4. Ken Burns video loop
    loop_video = tmp_dir / '_loop.mp4'
    log.info("Building Ken Burns video loop...")
    if not build_ken_burns_video(images, loop_video, duration):
        return False

    # 5. Mix video + audio
    log.info("Mixing video + audio...")
    if not mix_video_audio(loop_video, active_audio, out_mp4, duration):
        return False
    log.info(f"Video: {out_mp4} ({out_mp4.stat().st_size // 1024 // 1024}MB)")

    # 6. Thumbnail = first image resized to 1280×720
    try:
        from PIL import Image
        img = Image.open(images[0]).convert('RGB')
        img = img.resize((1280, 720), Image.LANCZOS)
        img.save(str(out_thumb), 'PNG', optimize=True)
        log.info(f"Thumbnail: {out_thumb.name}")
    except Exception as e:
        log.warning(f"PIL resize failed ({e}), copying image as-is")
        shutil.copy(str(images[0]), str(out_thumb))

    # 7. Meta YAML
    title       = build_title(track_name, duration)
    description = build_description(track_name, duration, meta)
    tags        = build_tags(track_name, meta)
    meta_doc = {
        'title':        title,
        'description':  description,
        'tags':         tags,
        'video_type':   'meditation',
        'language':     'en',
        'is_short':     True,   # individual tracks go in short slot (1/day); compilations are long
        'status':       'public',
        'made_for_kids': False,
        'ai_generated': True,
        'track_name':   track_name,
        'audio_file':   str(audio_path),
        'duration_sec': int(duration),
    }
    out_meta.write_text(yaml.dump(meta_doc, allow_unicode=True, default_flow_style=False))
    log.info(f"Meta: {out_meta.name}")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--track',  help='Track name (partial match)')
    parser.add_argument('--all',    action='store_true', help='Process all ungenerated tracks')
    parser.add_argument('--list',   action='store_true', help='List available tracks')
    parser.add_argument('--limit',  type=int, default=0, help='Max tracks to process')
    args = parser.parse_args()

    meta = yaml.safe_load(CONFIG.read_text())
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    THUMB_DIR.mkdir(parents=True, exist_ok=True)

    tracks = get_unique_tracks()

    if args.list:
        print(f"\n{len(tracks)} unique tracks in library:\n")
        for i, t in enumerate(tracks, 1):
            dur = get_audio_duration(t)
            done = '✓' if already_generated(canonical_name(t.name)) else ' '
            print(f"  {done} {i:3d}. {canonical_name(t.name):<45} {dur/60:.1f}min")
        return

    if args.track:
        matches = [t for t in tracks if args.track.lower() in t.name.lower()]
        if not matches:
            log.error(f"No track matching: {args.track}")
            sys.exit(1)
        to_process = matches[:1]
    elif args.all:
        to_process = [t for t in tracks if not already_generated(canonical_name(t.name))]
        if args.limit:
            to_process = to_process[:args.limit]
        log.info(f"{len(to_process)} tracks to generate")
    else:
        parser.print_help()
        return

    tmp_dir = QUEUE_DIR / '_tmp_sd'
    tmp_dir.mkdir(exist_ok=True)
    try:
        ok = fail = 0
        for audio in to_process:
            if process_track(audio, meta, tmp_dir):
                ok += 1
            else:
                fail += 1
        log.info(f"\nDone: {ok} OK, {fail} failed")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == '__main__':
    main()
