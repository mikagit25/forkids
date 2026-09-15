#!/usr/bin/env python3
"""
Generate 55-second vertical Shorts for Sacred Drift.

Pipeline per track:
  1. Pick a meditation track from library
  2. Select matching local visual theme image
  3. Build vertical 1080×1920 Ken Burns clip (zoom + center crop from landscape)
  4. Mix with 55s audio excerpt (starting at 30s into track)
  5. Write meta YAML + thumbnail to sacred_drift/output/queue/

Usage:
  python3 scripts/generate_sacred_drift_short.py --all
  python3 scripts/generate_sacred_drift_short.py --all --limit 10
  python3 scripts/generate_sacred_drift_short.py --track "Crown Chakra"
"""

import argparse, json, logging, re, shutil, subprocess, yaml
from datetime import datetime
from pathlib import Path

ROOT       = Path(__file__).resolve().parent.parent
AUDIO_DIR  = ROOT / 'assets/audio/suno_meditation/Meditation'
AUDIO_DIR2 = ROOT / 'sacred_drift/audio/uploads'   # new tracks uploaded via browser
THEMES_DIR = ROOT / 'assets/visual_themes'
QUEUE_DIR  = ROOT / 'sacred_drift/output/queue'
CONFIG     = ROOT / 'sacred_drift/config/channel_metadata_sd.yaml'
DATE_STR   = datetime.now().strftime('%Y%m%d')

SHORT_DUR  = 55    # seconds
START_SEC  = 30    # skip intro silence
FADE_SECS  = 2

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# Same keyword→theme mapping as the long video generator
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


def get_theme(track_name: str) -> str:
    name_lower = track_name.lower()
    for keyword, theme in KEYWORD_TO_THEME:
        if keyword in name_lower:
            return theme
    return 'zen_garden'


def get_theme_image(track_name: str) -> Path | None:
    """Return a middle frame from the best matching visual theme."""
    theme = get_theme(track_name)
    theme_dir = THEMES_DIR / theme
    frames = sorted(theme_dir.glob('frame_*.png'))
    if not frames:
        frames = sorted(theme_dir.glob('*.png'))
    if not frames:
        return None
    return frames[len(frames) // 2]  # middle frame


def canonical_name(filename: str) -> str:
    name = Path(filename).stem
    name = re.sub(r'\s*\(\d+\)$', '', name).strip()
    name = re.sub(r'\s+II+$', '', name).strip()
    name = re.sub(r'\s+\d+$', '', name).strip()
    return name


def get_audio_duration(audio_path: Path) -> float:
    r = subprocess.run(
        ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', str(audio_path)],
        capture_output=True
    )
    return float(json.loads(r.stdout)['format']['duration'])


def build_vertical_short(image: Path, audio: Path, out_mp4: Path,
                          start: float = START_SEC) -> bool:
    """
    Scale landscape image to fill 1080×1920 (zoom into center, Ken Burns slow zoom-in).
    Mix with 55s audio excerpt starting at `start` seconds.
    """
    # Scale image so height=1920, then center-crop to 1080 wide.
    # Add slow zoom-in (1.0→1.15 over 55s) via zoompan.
    # Source is ~1344×768; scaled to height 1920: width = 1344*1920/768 = 3360
    # After crop to 1080: we have a portrait view of the center.
    fps = 24
    n   = SHORT_DUR * fps  # total frames = 1320

    vf = (
        # Scale to fill height 1920 (width will be much wider due to landscape AR)
        f"scale=-2:1920,"
        # Slow zoom-in: start at z=1.0 (full height), end at z=1.15 (zoomed 15%)
        # iw is the scaled width; we want a 1080px wide window, centered, that slowly zooms
        f"zoompan=z='min(1+on*0.00011364,1.15)'"
        f":x='iw/2-(iw/zoom/2)-(iw/2-540)'"
        f":y='ih/2-(ih/zoom/2)'"
        f":d={n}:s=1080x1920:fps={fps},"
        # Fades
        f"fade=t=in:st=0:d={FADE_SECS},"
        f"fade=t=out:st={SHORT_DUR - FADE_SECS}:d={FADE_SECS}"
    )
    af = (
        f"aresample=44100,aformat=channel_layouts=stereo,"
        f"afade=t=in:st=0:d={FADE_SECS},"
        f"afade=t=out:st={SHORT_DUR - FADE_SECS}:d={FADE_SECS}"
    )

    cmd = [
        'ffmpeg', '-y',
        '-loop', '1', '-i', str(image),
        '-ss', str(start), '-i', str(audio),
        '-t', str(SHORT_DUR),
        '-map', '0:v:0', '-map', '1:a:0',
        '-vf', vf, '-af', af,
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '22',
        '-c:a', 'aac', '-b:a', '192k',
        '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart',
        str(out_mp4),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        log.error(f"ffmpeg failed: {r.stderr[-300:]}")
        return False
    return True


def build_title(track_name: str) -> str:
    return f"{track_name} 🔮 {SHORT_DUR}s | Sacred Drift #shorts"


def build_description(track_name: str) -> str:
    n = track_name.lower()
    if 'chakra' in n:
        hook = "✨ A moment of chakra alignment. Close your eyes and breathe."
    elif 'sleep' in n:
        hook = "🌙 Drift into peaceful rest. A 55-second reset for your mind."
    elif 'anxiety' in n or 'stress' in n:
        hook = "🌿 Release tension in 55 seconds. Breathe in, let go."
    elif 'healing' in n or 'reiki' in n:
        hook = "💫 55 seconds of healing sound. Let it wash through you."
    elif 'forest' in n or 'nature' in n:
        hook = "🌲 Step into the forest for 55 seconds. Pure stillness."
    elif 'ocean' in n or 'water' in n:
        hook = "🌊 55 seconds of ocean calm. Breathe and be still."
    else:
        hook = "🔮 55 seconds of sacred sound. Stop. Breathe. Drift."

    return f"""{hook}

Part of the Sacred Drift meditation library — healing frequencies, chakra music and sacred soundscapes for deep rest and inner peace.

Subscribe for daily meditation sessions 🔮 @SacredDrift

#Meditation #SacredDrift #HealingFrequencies #MeditationShorts #Shorts"""


def build_tags(track_name: str, meta: dict) -> list:
    base = meta.get('video_defaults', {}).get('tags_base', [])
    n = track_name.lower()
    extra = ['meditation shorts', 'shorts', 'sacred drift', 'healing sound']
    if 'chakra' in n: extra += ['chakra shorts', 'chakra healing']
    if 'sleep' in n:  extra += ['sleep shorts', 'sleep music']
    if 'forest' in n: extra += ['nature shorts', 'forest sounds']
    if 'ocean' in n:  extra += ['ocean shorts', 'ocean sounds']
    all_tags = extra + base
    seen, result, total = set(), [], 0
    for t in all_tags:
        if t and t not in seen and len(t) <= 30 and len(result) < 30 and total + len(t) <= 500:
            seen.add(t); result.append(t); total += len(t)
    return result


def already_generated(track_name: str) -> bool:
    safe = re.sub(r'[^\w\s-]', '', track_name).strip().replace(' ', '_').lower()
    return any(QUEUE_DIR.glob(f'*short*{safe}*.mp4'))


def get_unique_tracks() -> list[Path]:
    seen, tracks = set(), []
    sources = list(AUDIO_DIR.glob('*.mp3')) + list(AUDIO_DIR2.glob('*.mp3'))
    for mp3 in sorted(sources, key=lambda p: p.name):
        key = canonical_name(mp3.name)
        if key not in seen:
            seen.add(key); tracks.append(mp3)
    return tracks


def process_track(audio_path: Path, meta: dict) -> bool:
    track_name = canonical_name(audio_path.name)
    safe_name  = re.sub(r'[^\w\s-]', '', track_name).strip().replace(' ', '_').lower()
    out_stem   = f"sd_short_{safe_name}_{DATE_STR}"
    out_mp4    = QUEUE_DIR / f"{out_stem}.mp4"
    out_meta   = QUEUE_DIR / f"meta_{out_stem}.yaml"
    out_thumb  = QUEUE_DIR / f"thumb_{out_stem}.png"

    if out_mp4.exists():
        log.info(f"SKIP (exists): {track_name}")
        return True

    duration = get_audio_duration(audio_path)
    if duration < START_SEC + SHORT_DUR:
        log.warning(f"Track too short ({duration:.0f}s): {track_name}")
        return False

    image = get_theme_image(track_name)
    if not image:
        log.error(f"No theme image for: {track_name}")
        return False

    log.info(f"\n{'='*55}")
    log.info(f"Short: {track_name}")
    log.info(f"Audio: {audio_path.name} (start={START_SEC}s, dur={SHORT_DUR}s)")
    log.info(f"Image: {image.parent.name}/{image.name}")

    if not build_vertical_short(image, audio_path, out_mp4):
        return False

    log.info(f"Video: {out_mp4.name} ({out_mp4.stat().st_size // 1024}KB)")

    # Thumbnail: vertical crop + resize of the same image
    try:
        from PIL import Image
        img = Image.open(image).convert('RGB')
        # Center-crop to portrait (scale h to 1280, crop w to 720)
        w, h = img.size
        new_w = int(w * 1280 / h)
        img = img.resize((new_w, 1280), Image.LANCZOS)
        left = (new_w - 720) // 2
        img = img.crop((left, 0, left + 720, 1280))
        img.save(str(out_thumb), 'PNG', optimize=True)
        log.info(f"Thumb: {out_thumb.name}")
    except Exception as e:
        log.warning(f"Thumb failed ({e}), copying source")
        shutil.copy(str(image), str(out_thumb))

    # Meta
    meta_doc = {
        'title':         build_title(track_name),
        'description':   build_description(track_name),
        'tags':          build_tags(track_name, meta),
        'video_type':    'meditation_short',
        'language':      'en',
        'is_short':      True,
        'status':        'public',
        'made_for_kids': False,
        'ai_generated':  True,
        'track_name':    track_name,
    }
    out_meta.write_text(yaml.dump(meta_doc, allow_unicode=True, default_flow_style=False))
    log.info(f"Meta: {out_meta.name}")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--all',   action='store_true')
    parser.add_argument('--track', help='Partial track name')
    parser.add_argument('--limit', type=int, default=0)
    parser.add_argument('--list',  action='store_true')
    args = parser.parse_args()

    meta = yaml.safe_load(CONFIG.read_text())
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    tracks = get_unique_tracks()

    if args.list:
        print(f"\n{len(tracks)} tracks available for shorts:\n")
        for i, t in enumerate(tracks, 1):
            done = '✓' if already_generated(canonical_name(t.name)) else ' '
            dur  = get_audio_duration(t)
            ok   = '✓' if dur >= START_SEC + SHORT_DUR else '✗ too short'
            print(f"  {done} {i:3d}. {canonical_name(t.name):<45} {dur/60:.1f}min  {ok}")
        return

    if args.track:
        matches = [t for t in tracks if args.track.lower() in t.name.lower()]
        if not matches:
            log.error(f"No track matching: {args.track}")
            return
        to_process = matches[:1]
    elif args.all:
        to_process = [t for t in tracks
                      if not already_generated(canonical_name(t.name))
                      and get_audio_duration(t) >= START_SEC + SHORT_DUR]
        if args.limit:
            to_process = to_process[:args.limit]
        log.info(f"{len(to_process)} shorts to generate")
    else:
        parser.print_help()
        return

    ok = fail = 0
    for audio in to_process:
        if process_track(audio, meta):
            ok += 1
        else:
            fail += 1
    log.info(f"\nDone: {ok} OK, {fail} failed")


if __name__ == '__main__':
    main()
