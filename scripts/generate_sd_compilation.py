#!/usr/bin/env python3
"""
Generate Sacred Drift compilation videos — multiple tracks concatenated into
one 45-90 minute video, one per category.

Categories are auto-detected by keywords in filenames.

Usage:
  python3 scripts/generate_sd_compilation.py --list-categories
  python3 scripts/generate_sd_compilation.py --category chakra
  python3 scripts/generate_sd_compilation.py --all
  python3 scripts/generate_sd_compilation.py --all --dry-run
"""

import argparse, json, logging, re, shutil, subprocess, yaml
from datetime import datetime
from pathlib import Path

ROOT       = Path(__file__).resolve().parent.parent
AUDIO_DIR1 = ROOT / 'assets/audio/suno_meditation/Meditation'
AUDIO_DIR2 = ROOT / 'sacred_drift/audio/ai_instrumental'
AUDIO_DIR3 = ROOT / 'sacred_drift/audio/ai_chant'
THEMES_DIR = ROOT / 'assets/visual_themes'
QUEUE_DIR  = ROOT / 'sacred_drift/output/queue'
CONFIG     = ROOT / 'sacred_drift/config/channel_metadata_sd.yaml'
DATE_STR   = datetime.now().strftime('%Y%m%d')

CROSSFADE  = 3    # seconds between tracks
FADE_SECS  = 3    # fade in/out video
KB_FPS     = 24
KB_CLIP    = 30   # seconds per image

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# ── Categories ────────────────────────────────────────────────────────────────
# Each category: (display_name, [keywords], visual_theme, target_min_duration_sec)
CATEGORIES = {
    'chakra_journey': (
        'Full Chakra Journey 🌈',
        ['full chakra', 'chakra balance', 'seven centers', 'all chakra'],
        'aurora_borealis', 3600
    ),
    'crown_chakra': (
        'Crown Chakra Healing ✨',
        ['crown chakra'],
        'aurora_borealis', 3600
    ),
    'heart_chakra': (
        'Heart Chakra Opening 💚',
        ['heart chakra'],
        'lavender_fields', 3600
    ),
    'root_chakra': (
        'Root Chakra Grounding 🌿',
        ['root chakra', 'sacral chakra', 'solar plexus', 'throat chakra',
         'still grounding', 'schumann resonance', '417hz', '396hz'],
        'autumn_forest', 3600
    ),
    'third_eye': (
        'Third Eye Awakening 👁',
        ['third eye', 'theta waves', 'alpha waves', '852hz'],
        'aurora_borealis', 3600
    ),
    'solfeggio': (
        'Solfeggio Frequencies — Complete Session 🎶',
        ['111hz', '174hz', '285hz', '396hz', '417hz', '432hz', '528hz',
         '639hz', '741hz', '852hz', '963hz', '40hz', 'solfeggio', 'schumann',
         'frequency', 'cellular healing', 'tissue regeneration',
         'pain relief', 'release fear', 'natural harmony', 'detox cleansing',
         'morning clarity', 'deep sleep restoration', 'focus concentration'],
        'deep_space', 3600
    ),
    'deep_sleep': (
        'Deep Sleep Music 😴',
        ['deep sleep', 'sleep ambient', 'slow drone', 'lullaby',
         'sleep restoration', 'sleep music', 'deep ambient drone',
         'deep drone sanctuary', 'baby lullaby'],
        'evening_piano', 3600
    ),
    'forest_nature': (
        'Forest & Nature Sounds 🌲',
        ['forest', 'bamboo', 'birdsong', 'meadow', 'autumn forest',
         'spring garden', 'walking meditation', 'waterfall forest',
         'tropical rainforest', 'summer night crickets'],
        'rainforest_night', 3600
    ),
    'rain_water': (
        'Rain & Water Meditation 🌊',
        ['rain', 'ocean', 'river', 'mountain stream', 'waterfall',
         'crystal lake', 'hot springs', 'tropical sunset', 'thunderstorm',
         'tide', 'harbor', 'surf', 'underwater ocean'],
        'night_rain', 3600
    ),
    'tibetan_bowls': (
        'Tibetan & Crystal Bowls 🔔',
        ['tibetan', 'singing bowl', 'gong bath', 'temple bells',
         'sound bath', 'sound healing', 'crystal bowl', 'tibetan bowl'],
        'zen_garden', 3600
    ),
    'zen_mantra': (
        'Zen & Sacred Mantra 🧘',
        ['zen', 'buddhist', 'om mani', 'om mantra', 'om shanti', 'om chant',
         'sanskrit', 'so hum', 'gratitude chant', 'loving kindness', 'metta',
         'zazen', 'buddha garden', 'japanese zen', 'wind chimes zen',
         'zen temple', 'reiki healing chant', 'voice of truth'],
        'zen_garden', 3600
    ),
    'healing_reiki': (
        'Reiki & Healing Energy ✨',
        ['reiki', 'healing hum', 'healing tone', 'healing chant',
         'healing energy', 'om mantra natural voice'],
        'lavender_fields', 3600
    ),
    'cosmic_space': (
        'Cosmic Space Meditation 🌌',
        ['cosmic', 'space meditation', 'full moon', 'cosmic star', 'moon',
         'crown of light', 'starlit'],
        'deep_space', 3600
    ),
    'ambient_piano': (
        'Ambient Piano & Strings 🎹',
        ['piano', 'strings', 'cello', 'kalimba', 'pad', 'drone',
         'ambient', 'airy', 'velvet', 'twilight', 'afterglow',
         'candlelight', 'drift', 'fireplace', 'attic', 'quiet',
         'soft piano', 'soft forgiveness', 'tender ground', 'warmth returns',
         'where love', 'where the light', 'weight of the evening',
         'weightless', 'between two worlds', 'stay a while',
         'the long exhale', 'coming home', 'under the same sky',
         'soft static', 'slow cello', 'warm pad', 'slow falling snow',
         'wintering', 'train journey', 'slow train home'],
        'evening_piano', 3600
    ),
    'morning_yoga': (
        'Morning Yoga & Awakening 🌅',
        ['yoga', 'morning', 'breathing guide', 'breath meditation',
         '963hz morning', 'sunrise', 'yoga flow'],
        'cherry_blossoms', 3600
    ),
    'desert_mountain': (
        'Mountain & Desert Meditation 🏔️',
        ['mountain', 'desert', 'cave echo', 'mountain dawn',
         'mountain stream', 'native american', 'night forest',
         'snow blizzard', 'winter snow', 'winter snowfall',
         'winter fireplace', 'amber fireplace', 'crackling fireplace'],
        'mountain_snow', 3600
    ),
    'jazz_lounge': (
        'Jazz & Lounge — Late Night Sessions 🎷',
        ['jazz', 'sax', 'lounge', 'rainy cafe', 'rainy window',
         'evening sax', 'autumn lounge', 'city lights', 'blue hour',
         'small hours', 'sunday soul', 'slow sunday', 'whiskey',
         'velvet waltz', 'velvet evening', 'velvet nightfall',
         'velvet bass', 'blue', 'sunday'],
        'evening_piano', 3600
    ),
    # ── Merged compilations (combine weak categories into 1-hour sessions) ──────
    'complete_chakra': (
        'Complete Chakra Healing — All Energy Centers 🌈',
        ['chakra', 'third eye', 'theta waves', 'alpha waves'],
        'aurora_borealis', 3600
    ),
    'sacred_sounds': (
        'Sacred Sounds — Tibetan, Mantras & Healing 🔔',
        ['tibetan', 'singing bowl', 'gong bath', 'temple bells',
         'sound bath', 'sound healing', 'reiki', 'healing hum',
         'healing tone', 'healing chant',
         'zen', 'buddhist', 'om mani', 'om mantra', 'om shanti',
         'sanskrit', 'so hum', 'gratitude', 'loving kindness', 'metta',
         'zazen', 'buddha garden', 'japanese zen', 'wind chimes',
         'anxiety', 'stress'],
        'zen_garden', 3600
    ),
    'awakening_journey': (
        'Awakening Journey — Morning, Yoga & Cosmic 🌅',
        ['yoga', 'morning', 'breathing guide', 'breath meditation',
         'sunrise', 'cosmic', 'space meditation', 'full moon',
         'cosmic star', 'moon', 'deep sleep', 'sleep ambient',
         'slow drone', 'lullaby', 'sleep restoration', 'sleep music'],
        'cherry_blossoms', 3600
    ),
}

# ── Audio helpers ─────────────────────────────────────────────────────────────

def canonical_name(filename: str) -> str:
    name = Path(filename).stem
    name = re.sub(r'\s*\(\d+\)$', '', name).strip()
    name = re.sub(r'\bII+$', '', name).strip()
    name = re.sub(r'\s+\d+$', '', name).strip()
    return name


MIN_TRACK_DUR = 60   # tracks under 60s go to shorts only, skip in compilations

def get_all_tracks_grouped() -> list[Path]:
    """Return all tracks (including variants) sorted by canonical name.
    Variants of the same prompt are adjacent — they sound like one continuous piece."""
    sources = (list(AUDIO_DIR1.glob('*.mp3'))
               + (list(AUDIO_DIR2.glob('*.mp3')) if AUDIO_DIR2.exists() else [])
               + (list(AUDIO_DIR3.glob('*.mp3')) if AUDIO_DIR3.exists() else []))
    return sorted(sources, key=lambda p: (canonical_name(p.name).lower(), p.name.lower()))


def get_duration(path: Path) -> float:
    r = subprocess.run(
        ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', str(path)],
        capture_output=True
    )
    return float(json.loads(r.stdout)['format']['duration'])


def category_tracks(cat_key: str, all_tracks: list[Path]) -> list[Path]:
    _, keywords, _, _ = CATEGORIES[cat_key]
    result = []
    for t in all_tracks:
        name = canonical_name(t.name).lower()
        if any(kw in name for kw in keywords):
            dur = get_duration(t)
            if dur >= MIN_TRACK_DUR:   # skip very short tracks (for shorts only)
                result.append(t)
    return result


# ── Audio concat ─────────────────────────────────────────────────────────────

def concat_audio(tracks: list[Path], out_mp3: Path, target_dur: float) -> float:
    """Concatenate tracks (with crossfade) until target_dur is reached.
    If unique tracks < target, cycles round-robin so same track is never adjacent."""
    selected, total = [], 0.0
    pool = list(tracks)
    idx  = 0
    while total < target_dur:
        t = pool[idx % len(pool)]
        d = get_duration(t)
        selected.append((t, d))
        total += d
        idx += 1
        if idx > len(pool) * 20:
            break

    if not selected:
        return 0.0

    cycled = idx > len(pool)
    log.info(f"  Concatenating {len(selected)} tracks → {total/60:.0f} min"
             + (f" (×{idx // len(pool) + 1} round-robins, {len(pool)} unique tracks)" if cycled else ""))

    if len(selected) == 1:
        shutil.copy(str(selected[0][0]), str(out_mp3))
        return selected[0][1]

    # Build ffmpeg concat with crossfade between tracks
    # Use filter_complex for proper crossfade
    inputs = []
    for t, _ in selected:
        inputs += ['-i', str(t)]

    # Build filter: [0][1]acrossfade=d=3[a01]; [a01][2]acrossfade=d=3[a012]; ...
    n = len(selected)
    if n == 2:
        filt = f'[0:a][1:a]acrossfade=d={CROSSFADE}[out]'
        maps = ['-map', '[out]']
    else:
        parts = []
        prev = '[0:a]'
        for i in range(1, n):
            label = f'[cf{i}]' if i < n - 1 else '[out]'
            parts.append(f'{prev}[{i}:a]acrossfade=d={CROSSFADE}{label}')
            prev = label
        filt = '; '.join(parts)
        maps = ['-map', '[out]']

    cmd = ['ffmpeg', '-y'] + inputs + [
        '-filter_complex', filt
    ] + maps + [
        '-ar', '44100', '-ac', '2',
        '-c:a', 'libmp3lame', '-b:a', '192k',
        str(out_mp3)
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        log.error(f"Audio concat failed: {r.stderr[-400:]}")
        return 0.0

    actual_dur = get_duration(out_mp3)
    log.info(f"  Audio: {out_mp3.name} ({actual_dur/60:.1f} min, {out_mp3.stat().st_size//1024//1024}MB)")
    return actual_dur


# ── Video build (Ken Burns loop) ─────────────────────────────────────────────

MOTIONS = ['zoom_in', 'pan_right', 'zoom_out', 'pan_left', 'pan_up', 'pan_down']


def ken_burns_filter(motion: str, w=1280, h=704) -> str:
    n = KB_CLIP * KB_FPS
    if motion == 'zoom_in':
        return (f"scale=8000:-1,zoompan=z='min(zoom+0.0015,1.5)':x='iw/2-(iw/zoom/2)'"
                f":y='ih/2-(ih/zoom/2)':d={n}:s={w}x{h}:fps={KB_FPS}")
    if motion == 'zoom_out':
        return (f"scale=8000:-1,zoompan=z='if(lte(zoom,1.0),1.5,max(1.0,zoom-0.0015))'"
                f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s={w}x{h}:fps={KB_FPS}")
    if motion == 'pan_right':
        return (f"scale={w*2}:{h},zoompan=z=1:x='min(x+1,iw-{w})':y=0:d={n}:s={w}x{h}:fps={KB_FPS}")
    if motion == 'pan_left':
        return (f"scale={w*2}:{h},zoompan=z=1:x='max(0,iw-{w}-on)':y=0:d={n}:s={w}x{h}:fps={KB_FPS}")
    if motion == 'pan_up':
        return (f"scale={w}:{h*2},zoompan=z=1:x=0:y='min(y+1,ih-{h})':d={n}:s={w}x{h}:fps={KB_FPS}")
    return (f"scale={w}:{h*2},zoompan=z=1:x=0:y='max(0,ih-{h}-on)':d={n}:s={w}x{h}:fps={KB_FPS}")


def build_video(theme: str, audio_mp3: Path, out_mp4: Path, duration: float) -> bool:
    theme_dir = THEMES_DIR / theme
    frames = sorted(theme_dir.glob('frame_*.png'))
    if not frames:
        frames = sorted(theme_dir.glob('*.png'))
    if not frames:
        log.error(f"No frames in {theme_dir}")
        return False

    tmp = out_mp4.parent / '_comp_tmp'
    tmp.mkdir(exist_ok=True)
    clips = []

    try:
        # Build 6 KB clips (one per image, cycling motions)
        n_images = min(6, len(frames))
        step = max(1, len(frames) // n_images)
        images = [frames[i * step] for i in range(n_images)]

        for i, img in enumerate(images):
            motion = MOTIONS[i % len(MOTIONS)]
            clip = tmp / f'clip_{i:02d}.mp4'
            vf = ken_burns_filter(motion)
            fade_in  = f"fade=t=in:st=0:d={FADE_SECS}:alpha=0"
            fade_out = f"fade=t=out:st={KB_CLIP - FADE_SECS}:d={FADE_SECS}:alpha=0"
            cmd = [
                'ffmpeg', '-y', '-loop', '1', '-i', str(img),
                '-vf', f"{vf},{fade_in},{fade_out}",
                '-t', str(KB_CLIP), '-c:v', 'libx264', '-crf', '20',
                '-preset', 'fast', '-pix_fmt', 'yuv420p', str(clip)
            ]
            r = subprocess.run(cmd, capture_output=True, timeout=120)
            if r.returncode != 0:
                log.error(f"KB clip {i} failed: {r.stderr.decode()[-200:]}")
                return False
            clips.append(clip)

        # Loop clips to cover audio_dur
        loop_dur  = n_images * KB_CLIP
        loops_needed = int(duration / loop_dur) + 2
        concat_f = tmp / 'concat.txt'
        with open(concat_f, 'w') as f:
            for _ in range(loops_needed):
                for c in clips:
                    f.write(f"file '{c.resolve()}'\n")

        loop_mp4 = tmp / 'loop.mp4'
        cmd = ['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(concat_f),
               '-t', str(duration + 2), '-c', 'copy', str(loop_mp4)]
        r = subprocess.run(cmd, capture_output=True, timeout=120)
        if r.returncode != 0:
            log.error(f"Concat failed: {r.stderr.decode()[-200:]}")
            return False

        # Mix video + audio
        fade_out_start = max(0, duration - FADE_SECS)
        cmd = [
            'ffmpeg', '-y',
            '-i', str(loop_mp4),
            '-i', str(audio_mp3),
            '-map', '0:v:0', '-map', '1:a:0',
            '-vf', f"fade=t=out:st={fade_out_start}:d={FADE_SECS}",
            '-af', f"afade=t=out:st={fade_out_start}:d={FADE_SECS}",
            '-t', str(duration),
            '-c:v', 'libx264', '-crf', '20', '-preset', 'fast',
            '-c:a', 'aac', '-b:a', '192k',
            '-pix_fmt', 'yuv420p', str(out_mp4)
        ]
        r = subprocess.run(cmd, capture_output=True, timeout=7200)
        if r.returncode != 0:
            log.error(f"Mix failed: {r.stderr.decode()[-400:]}")
            return False

        log.info(f"  Video: {out_mp4.name} ({out_mp4.stat().st_size//1024//1024}MB)")
        return True
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ── Meta ─────────────────────────────────────────────────────────────────────

def build_meta(cat_key: str, tracks: list[Path], duration: float, meta_cfg: dict) -> dict:
    display_name, keywords, _, _ = CATEGORIES[cat_key]
    mins  = int(duration / 60)
    hours = mins // 60
    rem   = mins % 60
    dur_str = f"{hours} Hour {rem} Min" if hours else f"{mins} Minutes"

    title = f"{display_name} — {dur_str} | Sacred Drift"

    # Deduplicate tracklist — variants of the same prompt play back-to-back in the video
    # but we list each unique track name only once in the description
    seen_names, unique_names = set(), []
    for t in tracks:
        cn = canonical_name(t.name)
        if cn not in seen_names:
            seen_names.add(cn)
            unique_names.append(cn)
    tracklist = '\n'.join(f"  {i:02d}. {n}" for i, n in enumerate(unique_names, 1))

    footer = meta_cfg.get('video_defaults', {}).get('description_footer', '')

    description = f"""{display_name}

A {dur_str.lower()} deep meditation session — {len(unique_names)} carefully selected tracks for continuous, uninterrupted practice.

✨ Best with headphones at comfortable volume.
🎧 Ideal for: meditation, sleep, healing, relaxation

━━━━━━━━━━━━━━━━━━━━━━━
About Sacred Drift:
Sacred Drift is a sanctuary of sound — healing frequencies, chakra music and sacred soundscapes for deep rest and inner peace. New sessions every week.

Subscribe 🔮 @SacredDrift
━━━━━━━━━━━━━━━━━━━━━━━

🎵 Tracks in this compilation:
{tracklist}

{footer}"""

    base_tags = meta_cfg.get('video_defaults', {}).get('tags_base', [])
    cat_tags  = {
        'chakra_journey':  ['chakra music', 'chakra meditation', 'chakra healing'],
        'crown_chakra':    ['crown chakra', 'chakra healing', '963hz'],
        'heart_chakra':    ['heart chakra', 'chakra healing', '639hz'],
        'root_chakra':     ['root chakra', 'grounding meditation', 'chakra healing'],
        'third_eye':       ['third eye', 'theta waves', 'pineal gland'],
        'solfeggio':       ['solfeggio frequencies', '432hz', '528hz', '741hz'],
        'deep_sleep':      ['sleep music', 'deep sleep', 'insomnia relief'],
        'forest_nature':   ['forest sounds', 'nature sounds', 'nature meditation'],
        'rain_water':      ['rain sounds', 'ocean waves', 'water sounds'],
        'tibetan_bowls':   ['tibetan bowls', 'singing bowls', 'gong bath'],
        'zen_mantra':      ['zen music', 'mantra meditation', 'om meditation'],
        'healing_reiki':   ['reiki music', 'sound healing', 'healing frequencies'],
        'cosmic_space':    ['space meditation', 'cosmic music', 'deep space'],
        'ambient_piano':   ['ambient music', 'piano meditation', 'relaxing piano'],
        'morning_yoga':    ['yoga music', 'morning meditation', 'yoga flow'],
        'desert_mountain': ['mountain meditation', 'desert sounds', 'nature sounds'],
        'jazz_lounge':     ['jazz meditation', 'lounge music', 'late night jazz',
                            'smooth jazz', 'relaxing jazz', 'jazz sleep'],
    }.get(cat_key, [])

    all_tags = cat_tags + base_tags
    seen, tags, total = set(), [], 0
    for t in all_tags:
        if t and t not in seen and len(t) <= 30 and len(tags) < 30 and total + len(t) <= 500:
            seen.add(t); tags.append(t); total += len(t)

    return {
        'title':          title,
        'description':    description,
        'tags':           tags,
        'video_type':     'meditation_compilation',
        'language':       'en',
        'is_short':       False,
        'status':         'public',
        'made_for_kids':  False,
        'ai_generated':   True,
        'category':       cat_key,
        'track_count':    len(tracks),
        'duration_sec':   int(duration),
    }


def make_thumbnail(theme: str, out_path: Path):
    theme_dir = THEMES_DIR / theme
    frames = sorted(theme_dir.glob('frame_*.png'))
    if not frames:
        return
    src = frames[len(frames) // 2]
    try:
        from PIL import Image
        img = Image.open(src).convert('RGB').resize((1280, 720), Image.LANCZOS)
        img.save(str(out_path), 'PNG', optimize=True)
    except Exception:
        shutil.copy(str(src), str(out_path))


# ── Main ─────────────────────────────────────────────────────────────────────

def process_category(cat_key: str, all_tracks: list[Path], meta_cfg: dict,
                     dry_run: bool = False, force: bool = False) -> bool:
    display_name, keywords, theme, target_dur = CATEGORIES[cat_key]

    tracks = category_tracks(cat_key, all_tracks)
    if not tracks:
        log.warning(f"[{cat_key}] No tracks found")
        return False

    out_stem  = f"sd_comp_{cat_key}_{DATE_STR}"
    out_mp4   = QUEUE_DIR / f"{out_stem}.mp4"
    out_meta  = QUEUE_DIR / f"meta_{out_stem}.yaml"
    out_thumb = QUEUE_DIR / f"thumb_{out_stem}.png"
    tmp_mp3   = QUEUE_DIR / f"_tmp_{cat_key}.mp3"

    if out_mp4.exists() and not force:
        log.info(f"[{cat_key}] EXISTS — skip (--force to redo)")
        return True

    log.info(f"\n{'='*60}")
    log.info(f"Compilation: {display_name}")
    log.info(f"  Tracks: {len(tracks)} | Theme: {theme} | Target: {target_dur/60:.0f}min")
    for t in tracks[:5]:
        log.info(f"    {canonical_name(t.name)}")
    if len(tracks) > 5:
        log.info(f"    ... +{len(tracks)-5} more")

    if dry_run:
        total = sum(get_duration(t) for t in tracks)
        log.info(f"  [DRY RUN] Would compile {len(tracks)} tracks → {min(total, target_dur)/60:.0f}min video")
        return True

    try:
        # 1. Concat audio
        duration = concat_audio(tracks, tmp_mp3, target_dur)
        if duration < 60:
            log.error(f"Audio too short: {duration}s")
            return False

        # 2. Build video
        log.info(f"Building video ({duration/60:.0f}min)...")
        if not build_video(theme, tmp_mp3, out_mp4, duration):
            return False

        # 3. Thumbnail
        make_thumbnail(theme, out_thumb)
        log.info(f"  Thumb: {out_thumb.name}")

        # 4. Meta
        meta_doc = build_meta(cat_key, tracks, duration, meta_cfg)
        out_meta.write_text(yaml.dump(meta_doc, allow_unicode=True, default_flow_style=False))
        log.info(f"  Meta: {out_meta.name}")

        return True
    finally:
        tmp_mp3.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--list-categories', action='store_true')
    parser.add_argument('--category', help='Category key (e.g. chakra_journey)')
    parser.add_argument('--all',      action='store_true')
    parser.add_argument('--dry-run',  action='store_true')
    parser.add_argument('--force',    action='store_true')
    args = parser.parse_args()

    meta_cfg   = yaml.safe_load(CONFIG.read_text())
    all_tracks = get_all_tracks_grouped()
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)

    if args.list_categories:
        print(f"\nCategories ({len(CATEGORIES)} total):\n")
        print(f"  {'Key':<20} {'Name':<45} {'Tracks':>6}  {'~Min':>5}")
        print(f"  {'-'*20} {'-'*45} {'-'*6}  {'-'*5}")
        for key, (name, kws, theme, dur) in CATEGORIES.items():
            tracks = category_tracks(key, all_tracks)
            total  = sum(get_duration(t) for t in tracks)
            print(f"  {key:<20} {name:<45} {len(tracks):>6}  {min(total,dur)/60:>5.0f}")
        print(f"\nTotal unique tracks: {len(all_tracks)}")
        return

    if args.category:
        if args.category not in CATEGORIES:
            log.error(f"Unknown category: {args.category}. Use --list-categories")
            return
        to_process = [args.category]
    elif args.all:
        to_process = list(CATEGORIES.keys())
    else:
        parser.print_help()
        return

    ok = fail = 0
    for cat_key in to_process:
        if process_category(cat_key, all_tracks, meta_cfg,
                            dry_run=args.dry_run, force=args.force):
            ok += 1
        else:
            fail += 1

    log.info(f"\n{'='*60}")
    log.info(f"Done: {ok} OK, {fail} failed")


if __name__ == '__main__':
    main()
