#!/usr/bin/env python3
"""
Generate Sacred Drift fire ambient videos — fireplace, campfire, candle, fire closeup.

Pipeline:
  1. Search Pexels for fire footage (free CC0 license)
  2. Download best HD clip
  3. Extract clean 30s segment → create seamless loop with FFmpeg xfade
  4. Match with fire ambient audio from ai_instrumental/
  5. Loop to 1h, save to sacred_drift/output/queue/ with meta

Setup:
  1. Get free API key at https://www.pexels.com/api/
  2. echo "YOUR_KEY" > credentials/pexels_api_key.txt
  3. python3 scripts/generate_fire_ambient.py --all
     python3 scripts/generate_fire_ambient.py --type fireplace
     python3 scripts/generate_fire_ambient.py --all --dry-run
"""

import argparse, json, logging, shutil, subprocess, urllib.request, yaml
from datetime import datetime
from pathlib import Path

ROOT       = Path(__file__).resolve().parent.parent
QUEUE_DIR  = ROOT / 'sacred_drift/output/queue'
AUDIO_DIR  = ROOT / 'sacred_drift/audio/ai_instrumental'
LOOPS_DIR  = ROOT / 'output/_fire_loops'
PEXELS_KEY = ROOT / 'credentials/pexels_api_key.txt'
CONFIG     = ROOT / 'sacred_drift/config/channel_metadata_sd.yaml'
DATE_STR   = datetime.now().strftime('%Y%m%d')

TARGET_DUR  = 3600   # 1 hour output
LOOP_DUR    = 30     # seconds per seamless loop
FADE_DUR    = 3      # crossfade between loop iterations
SKIP_START  = 10     # skip first N seconds of Pexels clip (avoid intros/cuts)

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# ── Fire type definitions ──────────────────────────────────────────────────────
FIRE_TYPES = {
    'fireplace': {
        'query':        'cozy fireplace crackling wood burning',
        'display_name': 'Cozy Fireplace 🔥',
        'audio_kw':     ['amber fireplace', 'crackling fireplace', 'winter fireplace',
                         'candlelight hour', 'soft piano stillness'],
        'theme_desc':   'crackling wood fireplace, warm amber glow, cozy interior, close-up flames',
        'tags':         ['fireplace', 'crackling fire', 'cozy fireplace', 'fire sounds',
                         'fireplace ambience', 'relaxing fire', 'fire meditation'],
    },
    'campfire': {
        'query':        'campfire night outdoor burning wood',
        'display_name': 'Campfire Night 🏕️',
        'audio_kw':     ['sunset beach campfire', 'summer night', 'crackling fireplace',
                         'amber fireplace', 'attic window'],
        'theme_desc':   'outdoor campfire at night, sparks floating up, dark forest background',
        'tags':         ['campfire', 'campfire sounds', 'outdoor fire', 'bonfire',
                         'fire crackling', 'nature sounds', 'camping ambience'],
    },
    'candle': {
        'query':        'candle flame meditation close up burning',
        'display_name': 'Candlelight Meditation 🕯️',
        'audio_kw':     ['candlelight hour', 'soft piano stillness', 'quiet library',
                         'amber fireplace', 'soft forgiveness'],
        'theme_desc':   'single candle flame in darkness, soft golden glow, meditation atmosphere',
        'tags':         ['candle meditation', 'candlelight', 'candle flame', 'meditation candle',
                         'fire focus', 'candle ambience', 'mindfulness'],
    },
    'fire_closeup': {
        'query':        'fire flames close up burning abstract',
        'display_name': 'Sacred Fire — Close Up 🔥',
        'audio_kw':     ['deep drone sanctuary', 'deep ambient drone', 'velvet bass wash',
                         'crackling fireplace', 'amber fireplace'],
        'theme_desc':   'close up fire flames, abstract burning, deep red and orange tones',
        'tags':         ['fire flames', 'burning fire', 'abstract fire', 'fire meditation',
                         'fire therapy', 'fire sounds', 'flames'],
    },
}


# ── Pexels API ────────────────────────────────────────────────────────────────

def pexels_search(query: str, per_page: int = 10) -> list[dict]:
    if not PEXELS_KEY.exists():
        raise FileNotFoundError(
            f"Pexels API key not found: {PEXELS_KEY}\n"
            "Get a free key at https://www.pexels.com/api/ and save it:\n"
            "  echo 'YOUR_KEY' > credentials/pexels_api_key.txt"
        )
    api_key = PEXELS_KEY.read_text().strip()
    url = f"https://api.pexels.com/videos/search?query={urllib.parse.quote(query)}&per_page={per_page}&orientation=landscape"
    req = urllib.request.Request(url, headers={
        'Authorization': api_key,
        'User-Agent': 'Mozilla/5.0 (compatible; SacredDrift/1.0)',
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return data.get('videos', [])


def best_video_url(video: dict, min_width: int = 1280) -> tuple[str, int, int]:
    """Return (url, width, height) of best file at or above min_width."""
    files = video.get('video_files', [])
    # Prefer HD (1920 or 1280), landscape, mp4
    candidates = [
        f for f in files
        if f.get('file_type') == 'video/mp4'
        and f.get('width', 0) >= min_width
        and f.get('height', 0) > 0
        and f.get('width', 0) / f.get('height', 1) > 1.2  # landscape
    ]
    if not candidates:
        candidates = [f for f in files if f.get('file_type') == 'video/mp4']
    if not candidates:
        return '', 0, 0
    best = sorted(candidates, key=lambda f: f.get('width', 0))[-1]
    return best['link'], best['width'], best['height']


import urllib.parse

def download_video(url: str, out_path: Path) -> bool:
    log.info(f"  Downloading: {out_path.name}")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp, open(out_path, 'wb') as f:
            shutil.copyfileobj(resp, f)
        log.info(f"  Downloaded: {out_path.stat().st_size // 1024 // 1024}MB")
        return True
    except Exception as e:
        log.error(f"  Download failed: {e}")
        return False


# ── Video helpers ─────────────────────────────────────────────────────────────

def get_duration(path: Path) -> float:
    r = subprocess.run(
        ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', str(path)],
        capture_output=True
    )
    try:
        return float(json.loads(r.stdout)['format']['duration'])
    except Exception:
        return 0.0


def create_seamless_loop(src: Path, loop_path: Path, loop_dur: int = LOOP_DUR,
                         fade: int = FADE_DUR, skip: int = SKIP_START) -> bool:
    """
    Extract `loop_dur` seconds from `src` (starting at `skip`),
    then crossfade the end back to the beginning → seamless loop.
    """
    src_dur = get_duration(src)
    if src_dur < skip + loop_dur + fade:
        skip = max(0, src_dur // 4)  # fall back to 1/4 of clip

    offset = loop_dur - fade   # xfade start point

    # Resize to 1280x720 if needed, ensure even dimensions
    cmd = [
        'ffmpeg', '-y',
        '-ss', str(skip), '-t', str(loop_dur + fade),
        '-i', str(src),
        '-ss', str(skip), '-t', str(loop_dur + fade),
        '-i', str(src),
        '-filter_complex',
        (f'[0:v]scale=1280:720:force_original_aspect_ratio=decrease,'
         f'pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1[v0];'
         f'[1:v]scale=1280:720:force_original_aspect_ratio=decrease,'
         f'pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1[v1];'
         f'[v0][v1]xfade=transition=fade:duration={fade}:offset={offset}[vout]'),
        '-map', '[vout]',
        '-t', str(loop_dur),
        '-c:v', 'libx264', '-crf', '20', '-preset', 'fast',
        '-pix_fmt', 'yuv420p', '-an',
        str(loop_path)
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        log.error(f"  Seamless loop failed: {r.stderr[-300:]}")
        return False
    log.info(f"  Loop: {loop_path.name} ({loop_dur}s, {loop_path.stat().st_size//1024}KB)")
    return True


def find_audio(kw_list: list[str]) -> Path | None:
    """Find best matching audio file from ai_instrumental/ by keyword priority."""
    if not AUDIO_DIR.exists():
        return None
    for kw in kw_list:
        matches = [f for f in AUDIO_DIR.glob('*.mp3') if kw.lower() in f.name.lower()]
        if matches:
            # Prefer base file (no variant suffix) if available
            base = [m for m in matches if '(' not in m.name]
            return (base or matches)[0]
    return None


def build_long_video(loop_path: Path, audio_path: Path | None,
                     out_mp4: Path, target_dur: int = TARGET_DUR) -> bool:
    """Loop the seamless visual loop + add audio to fill target_dur seconds."""
    loop_dur = get_duration(loop_path)
    loops_needed = int(target_dur / loop_dur) + 2

    tmp = out_mp4.parent / '_fire_tmp'
    tmp.mkdir(exist_ok=True)
    concat_f = tmp / 'concat.txt'
    loop_mp4  = tmp / 'loop.mp4'

    try:
        # Write concat list
        concat_f.write_text(''.join(f"file '{loop_path.resolve()}'\n" for _ in range(loops_needed)))

        # Concatenate loops to cover duration
        r = subprocess.run([
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
            '-i', str(concat_f),
            '-t', str(target_dur + 2), '-c', 'copy', str(loop_mp4)
        ], capture_output=True, timeout=300)
        if r.returncode != 0:
            log.error(f"  Loop concat failed: {r.stderr.decode()[-200:]}")
            return False

        # Build audio: loop audio to fill duration
        if audio_path and audio_path.exists():
            audio_dur = get_duration(audio_path)
            audio_loops = int(target_dur / audio_dur) + 2
            concat_a = tmp / 'concat_audio.txt'
            concat_a.write_text(''.join(f"file '{audio_path.resolve()}'\n" for _ in range(audio_loops)))
            loop_audio = tmp / 'audio_loop.mp3'
            r = subprocess.run([
                'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
                '-i', str(concat_a),
                '-t', str(target_dur),
                '-ar', '44100', '-ac', '2', '-c:a', 'libmp3lame', '-b:a', '192k',
                str(loop_audio)
            ], capture_output=True, timeout=300)
            if r.returncode != 0:
                log.warning("  Audio loop failed — no audio in output")
                loop_audio = None
        else:
            loop_audio = None
            log.warning("  No matching audio found — video will be silent")

        # Mix video + audio
        fade_start = max(0, target_dur - 3)
        if loop_audio:
            cmd = [
                'ffmpeg', '-y',
                '-i', str(loop_mp4),
                '-i', str(loop_audio),
                '-map', '0:v:0', '-map', '1:a:0',
                '-vf',  f'fade=t=out:st={fade_start}:d=3',
                '-af',  f'afade=t=out:st={fade_start}:d=3',
                '-t', str(target_dur),
                '-c:v', 'libx264', '-crf', '20', '-preset', 'fast',
                '-c:a', 'aac', '-b:a', '192k', '-pix_fmt', 'yuv420p',
                str(out_mp4)
            ]
        else:
            cmd = [
                'ffmpeg', '-y', '-i', str(loop_mp4),
                '-map', '0:v:0',
                '-vf',  f'fade=t=out:st={fade_start}:d=3',
                '-t', str(target_dur),
                '-c:v', 'libx264', '-crf', '20', '-preset', 'fast',
                '-pix_fmt', 'yuv420p', '-an',
                str(out_mp4)
            ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
        if r.returncode != 0:
            log.error(f"  Final mix failed: {r.stderr[-300:]}")
            return False

        log.info(f"  Video: {out_mp4.name} ({out_mp4.stat().st_size//1024//1024}MB)")
        return True
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ── Thumbnail ─────────────────────────────────────────────────────────────────

def make_thumbnail(loop_path: Path, out_path: Path) -> bool:
    """Grab a frame from the middle of the loop for thumbnail."""
    dur = get_duration(loop_path)
    mid = dur / 2
    r = subprocess.run([
        'ffmpeg', '-y', '-ss', str(mid), '-i', str(loop_path),
        '-vframes', '1', '-s', '1280x720', str(out_path)
    ], capture_output=True, timeout=30)
    return r.returncode == 0 and out_path.exists()


# ── Meta ──────────────────────────────────────────────────────────────────────

def build_meta(fire_type: str, audio_name: str, dur_sec: int, meta_cfg: dict) -> dict:
    cfg = FIRE_TYPES[fire_type]
    name = cfg['display_name']
    hours = dur_sec // 3600
    mins  = (dur_sec % 3600) // 60
    dur_str = f"{hours} Hour" if mins == 0 else f"{hours} Hour {mins} Min"

    title = f"{name} — {dur_str} | Fire Ambience | Sacred Drift"

    footer = meta_cfg.get('video_defaults', {}).get('description_footer', '')

    description = f"""{name}

{dur_str} of continuous {cfg['theme_desc'].split(',')[0]} — perfect for deep relaxation, meditation, sleep and focus.

✨ Best experienced on a large screen or TV for full immersion.
🎧 Pair with headphones for the ultimate ambient experience.
🔥 Video loops seamlessly — ideal for background ambience.

━━━━━━━━━━━━━━━━━━━━━━━
About Sacred Drift:
Sacred Drift is a sanctuary of sound and vision — fire ambience, healing frequencies and sacred soundscapes for deep rest and inner peace.

Subscribe 🔮 @SacredDrift
━━━━━━━━━━━━━━━━━━━━━━━

🔥 Fire ambience — footage licensed under Pexels License (free to use)
🎵 Audio: {audio_name} (AI-generated, © Sacred Drift 2026)

{footer}"""

    base_tags = meta_cfg.get('video_defaults', {}).get('tags_base', [])
    all_tags = cfg['tags'] + base_tags
    seen, tags, total = set(), [], 0
    for t in all_tags:
        if t and t not in seen and len(t) <= 30 and len(tags) < 30 and total + len(t) <= 500:
            seen.add(t); tags.append(t); total += len(t)

    return {
        'title':          title,
        'description':    description,
        'tags':           tags,
        'video_type':     'fire_ambient',
        'language':       'en',
        'is_short':       False,
        'status':         'public',
        'made_for_kids':  False,
        'ai_generated':   False,
        'fire_type':      fire_type,
        'duration_sec':   dur_sec,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def process_fire_type(fire_type: str, meta_cfg: dict, dry_run: bool = False,
                      force: bool = False) -> bool:
    cfg = FIRE_TYPES[fire_type]
    log.info(f"\n{'='*60}")
    log.info(f"Fire type: {cfg['display_name']}")

    out_stem  = f"fire_{fire_type}_{DATE_STR}"
    out_mp4   = QUEUE_DIR / f"{out_stem}.mp4"
    out_meta  = QUEUE_DIR / f"meta_{out_stem}.yaml"
    out_thumb = QUEUE_DIR / f"thumb_{out_stem}.png"
    loop_path = LOOPS_DIR / f"loop_{fire_type}.mp4"

    if out_mp4.exists() and not force:
        log.info(f"  EXISTS — skip (--force to redo)")
        return True

    # 1. Find audio
    audio_path = find_audio(cfg['audio_kw'])
    audio_name = audio_path.stem if audio_path else 'Silent'
    log.info(f"  Audio: {audio_name}")

    if dry_run:
        log.info(f"  [DRY RUN] Would search Pexels: '{cfg['query']}'")
        log.info(f"  [DRY RUN] Would create {TARGET_DUR//3600}h video → {out_mp4.name}")
        return True

    LOOPS_DIR.mkdir(parents=True, exist_ok=True)
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)

    # 2. Download source video from Pexels (unless loop already cached)
    raw_path = LOOPS_DIR / f"raw_{fire_type}.mp4"
    if not loop_path.exists() or force:
        if not raw_path.exists() or force:
            log.info(f"  Searching Pexels: '{cfg['query']}'")
            try:
                videos = pexels_search(cfg['query'], per_page=15)
            except FileNotFoundError as e:
                log.error(str(e))
                return False
            except Exception as e:
                log.error(f"  Pexels search failed: {e}")
                return False

            if not videos:
                log.error(f"  No results for '{cfg['query']}'")
                return False

            # Pick the video with longest duration (more stable footage)
            videos.sort(key=lambda v: v.get('duration', 0), reverse=True)
            for vid in videos[:5]:
                url, w, h = best_video_url(vid)
                if url:
                    log.info(f"  Found: {vid.get('url','?')} ({w}×{h}, {vid.get('duration',0)}s)")
                    if download_video(url, raw_path):
                        break
            else:
                log.error("  Could not download any video from Pexels")
                return False

        # 3. Create seamless loop
        log.info(f"  Creating seamless {LOOP_DUR}s loop...")
        if not create_seamless_loop(raw_path, loop_path):
            return False

    # 4. Build 1-hour video
    log.info(f"  Building {TARGET_DUR//3600}h video...")
    if not build_long_video(loop_path, audio_path, out_mp4, TARGET_DUR):
        return False

    # 5. Thumbnail from loop
    make_thumbnail(loop_path, out_thumb)
    log.info(f"  Thumb: {out_thumb.name}")

    # 6. Meta
    meta_doc = build_meta(fire_type, audio_name, TARGET_DUR, meta_cfg)
    out_meta.write_text(yaml.dump(meta_doc, allow_unicode=True, default_flow_style=False))
    log.info(f"  Meta: {out_meta.name}")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--type',    choices=list(FIRE_TYPES.keys()), help='Single fire type')
    parser.add_argument('--all',     action='store_true', help='Generate all 4 fire types')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--force',   action='store_true', help='Re-generate even if exists')
    parser.add_argument('--list',    action='store_true', help='List fire types')
    args = parser.parse_args()

    if args.list:
        print("\nFire types:")
        for k, v in FIRE_TYPES.items():
            audio = find_audio(v['audio_kw'])
            print(f"  {k:<15} {v['display_name']:<35} audio: {audio.stem if audio else 'NOT FOUND'}")
        return

    if not PEXELS_KEY.exists() and not args.dry_run:
        print("\n⚠️  Pexels API key not found!")
        print("   1. Register free at: https://www.pexels.com/api/")
        print(f"  2. Save key: echo 'YOUR_KEY' > {PEXELS_KEY}")
        return

    meta_cfg = yaml.safe_load(CONFIG.read_text()) if CONFIG.exists() else {}
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)

    types_to_run = list(FIRE_TYPES.keys()) if args.all else ([args.type] if args.type else [])
    if not types_to_run:
        parser.print_help()
        return

    ok = fail = 0
    for ft in types_to_run:
        if process_fire_type(ft, meta_cfg, dry_run=args.dry_run, force=args.force):
            ok += 1
        else:
            fail += 1

    log.info(f"\nDone: {ok} OK, {fail} failed")


if __name__ == '__main__':
    main()
