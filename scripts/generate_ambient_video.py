#!/usr/bin/env python3
"""
Generate Sacred Drift ambient videos from Pexels stock footage.

Covers fire, water, nature and any future real-footage categories.
Pipeline: Pexels search → download → seamless 30s loop → 1h video + audio.

Usage:
  python3 scripts/generate_ambient_video.py --list
  python3 scripts/generate_ambient_video.py --type waterfall
  python3 scripts/generate_ambient_video.py --group water
  python3 scripts/generate_ambient_video.py --group fire
  python3 scripts/generate_ambient_video.py --all
  python3 scripts/generate_ambient_video.py --all --dry-run
"""

import argparse, json, logging, shutil, subprocess, urllib.parse, urllib.request, yaml
from datetime import datetime
from pathlib import Path

ROOT       = Path(__file__).resolve().parent.parent
QUEUE_DIR  = ROOT / 'sacred_drift/output/queue'
AUDIO_DIR  = ROOT / 'sacred_drift/audio/ai_instrumental'
LOOPS_DIR  = ROOT / 'output/_ambient_loops'
PEXELS_KEY = ROOT / 'credentials/pexels_api_key.txt'
CONFIG     = ROOT / 'sacred_drift/config/channel_metadata_sd.yaml'
DATE_STR   = datetime.now().strftime('%Y%m%d')

TARGET_DUR = 3600   # 1 hour
LOOP_DUR   = 30     # seamless loop length (seconds)
FADE_DUR   = 3      # xfade crossfade
SKIP_START = 8      # skip first N sec of downloaded clip

# Audio mix levels
# natural_vol: volume of natural sound from Pexels clip (0.0–1.0)
#   music is always at 1.0; natural is background
#   0.15 = barely audible texture, 0.30 = clearly audible but music leads
MUSIC_VOL    = 1.0   # AI music always at full
NAT_VOL_LOW  = 0.15  # fire, candle — subtle crackle texture
NAT_VOL_MID  = 0.22  # streams, rivers — gentle water presence
NAT_VOL_HIGH = 0.32  # ocean, rain — nature more prominent but music still leads

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')


# ── Ambient type catalogue ────────────────────────────────────────────────────
# Each entry: query, display_name, group, audio_keywords[], description, tags[]
AMBIENT_TYPES = {

    # ── Fire — subtle crackle texture behind music ────────────────────────────
    'fireplace': {
        'group':      'fire',
        'query':      'cozy fireplace crackling wood burning indoor',
        'name':       'Cozy Fireplace 🔥',
        'desc':       'crackling wood fireplace, warm amber glow, cozy interior',
        'audio':      ['amber fireplace', 'crackling fireplace', 'winter fireplace', 'candlelight hour'],
        'natural_vol': NAT_VOL_LOW,   # subtle crackle — music leads
        'tags':       ['fireplace', 'crackling fire', 'cozy fireplace', 'fire sounds',
                       'fireplace ambience', 'relaxing fire', 'fire meditation'],
    },
    'campfire': {
        'group':      'fire',
        'query':      'campfire night outdoor burning wood sparks',
        'name':       'Campfire Night 🏕️',
        'desc':       'outdoor campfire at night, sparks floating up, dark forest background',
        'audio':      ['sunset beach campfire', 'summer night crickets', 'crackling fireplace'],
        'natural_vol': NAT_VOL_LOW,   # crackle + night sounds as texture
        'tags':       ['campfire', 'campfire sounds', 'outdoor fire', 'bonfire',
                       'fire crackling', 'nature sounds', 'camping ambience'],
    },
    'candle': {
        'group':      'fire',
        'query':      'single candle flame dark background meditation',
        'name':       'Candlelight Meditation 🕯️',
        'desc':       'single candle flame in darkness, soft golden glow, meditation atmosphere',
        'audio':      ['candlelight hour', 'soft piano stillness', 'quiet library meditation'],
        'natural_vol': 0.08,          # candle is nearly silent — very faint hiss only
        'tags':       ['candle meditation', 'candlelight', 'candle flame',
                       'meditation candle', 'candle ambience', 'mindfulness'],
    },
    'fire_closeup': {
        'group':      'fire',
        'query':      'fire flames close up burning abstract orange red',
        'name':       'Sacred Fire — Close Up 🔥',
        'desc':       'close-up fire flames, abstract burning, deep red and orange tones',
        'audio':      ['deep drone sanctuary', 'deep ambient drone', 'velvet bass wash'],
        'natural_vol': NAT_VOL_LOW,   # crackle as subtle texture under drone
        'tags':       ['fire flames', 'burning fire', 'abstract fire',
                       'fire meditation', 'fire therapy', 'flames'],
    },

    # ── Water — nature more prominent, music still leads ──────────────────────
    'waterfall': {
        'group':      'water',
        'query':      'waterfall nature beautiful forest flowing water close up',
        'name':       'Forest Waterfall 🌊',
        'desc':       'lush forest waterfall, white cascading water, green moss and ferns',
        'audio':      ['waterfall forest meditation', 'mountain waterfall echo meditation',
                       'forest relaxation sounds'],
        'natural_vol': NAT_VOL_MID,   # water sound clearly present, music leads
        'tags':       ['waterfall sounds', 'waterfall meditation', 'forest waterfall',
                       'nature sounds', 'water sounds', 'white noise', 'sleep sounds'],
    },
    'mountain_stream': {
        'group':      'water',
        'query':      'mountain stream creek flowing clear water rocks',
        'name':       'Mountain Stream 🏔️',
        'desc':       'crystal-clear mountain stream over rocks, sunlight through trees',
        'audio':      ['mountain stream meditation', 'crystal lake dawn meditation',
                       'river flow meditation'],
        'natural_vol': NAT_VOL_MID,   # gentle babbling under music
        'tags':       ['mountain stream', 'creek sounds', 'flowing water', 'nature meditation',
                       'stream sounds', 'water meditation', 'forest sounds'],
    },
    'ocean_waves': {
        'group':      'water',
        'query':      'ocean waves beach shore slow relaxing sunset',
        'name':       'Ocean Waves 🌊',
        'desc':       'gentle ocean waves on sandy beach, golden sunset light on water',
        'audio':      ['ocean waves meditation', 'ocean waves meditation ii',
                       'evening tide', 'ocean breath'],
        'natural_vol': NAT_VOL_HIGH,  # waves are part of the experience — more prominent
        'tags':       ['ocean waves', 'ocean sounds', 'beach sounds', 'wave sounds',
                       'ocean meditation', 'sea sounds', 'sleep sounds'],
    },
    'tropical_waterfall': {
        'group':      'water',
        'query':      'tropical jungle waterfall rainforest lush green water',
        'name':       'Tropical Waterfall 🌿',
        'desc':       'tropical jungle waterfall, lush green rainforest, misty spray',
        'audio':      ['tropical rainforest meditation', 'tropical sunset surf meditation',
                       'waterfall forest meditation'],
        'natural_vol': NAT_VOL_MID,   # jungle sounds enrich the atmosphere
        'tags':       ['tropical waterfall', 'jungle sounds', 'rainforest sounds',
                       'tropical nature', 'waterfall meditation', 'tropical meditation'],
    },
    'rain_forest': {
        'group':      'water',
        'query':      'rain falling forest nature peaceful rainfall drops',
        'name':       'Rain in the Forest 🌧️',
        'desc':       'gentle rainfall in a quiet forest, droplets on leaves, soft grey light',
        'audio':      ['gentle rain meditation', 'gentle rainfall', 'rain on rooftop meditation',
                       'zen temple rain meditation', 'autumn rain'],
        'natural_vol': NAT_VOL_HIGH,  # rain is atmospheric — justified to be more present
        'tags':       ['rain sounds', 'rain meditation', 'forest rain', 'rainfall',
                       'rain white noise', 'rain sleep sounds', 'rain nature'],
    },
    'river_flow': {
        'group':      'water',
        'query':      'calm river flowing water nature peaceful slow',
        'name':       'Flowing River 🏞️',
        'desc':       'wide calm river flowing through green valley, birds and rustling leaves',
        'audio':      ['river flow meditation', 'mountain stream meditation',
                       'ocean breath', 'evening tide'],
        'natural_vol': NAT_VOL_MID,   # gentle current texture
        'tags':       ['river sounds', 'flowing water', 'river meditation', 'nature sounds',
                       'water sounds relaxing', 'river white noise', 'peaceful river'],
    },
}


# ── Pexels API ────────────────────────────────────────────────────────────────

def pexels_search(query: str, per_page: int = 15) -> list[dict]:
    if not PEXELS_KEY.exists():
        raise FileNotFoundError(
            f"Pexels API key not found. Save it:\n  echo 'KEY' > {PEXELS_KEY}")
    api_key = PEXELS_KEY.read_text().strip()
    url = (f"https://api.pexels.com/videos/search"
           f"?query={urllib.parse.quote(query)}&per_page={per_page}&orientation=landscape")
    req = urllib.request.Request(url, headers={
        'Authorization': api_key,
        'User-Agent': 'Mozilla/5.0 (compatible; SacredDrift/1.0)',
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read()).get('videos', [])


def best_video_url(video: dict, min_width: int = 1280) -> tuple[str, int, int]:
    files = video.get('video_files', [])
    candidates = [
        f for f in files
        if f.get('file_type') == 'video/mp4'
        and f.get('width', 0) >= min_width
        and f.get('width', 0) / max(f.get('height', 1), 1) > 1.2
    ]
    if not candidates:
        candidates = [f for f in files if f.get('file_type') == 'video/mp4']
    if not candidates:
        return '', 0, 0
    best = sorted(candidates, key=lambda f: f.get('width', 0))[-1]
    return best['link'], best['width'], best['height']


def download_video(url: str, out_path: Path) -> bool:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, timeout=180) as resp, open(out_path, 'wb') as f:
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
        capture_output=True)
    try:
        return float(json.loads(r.stdout)['format']['duration'])
    except Exception:
        return 0.0


def has_audio(path: Path) -> bool:
    r = subprocess.run(
        ['ffprobe', '-v', 'quiet', '-print_format', 'json',
         '-show_streams', '-select_streams', 'a', str(path)],
        capture_output=True)
    try:
        return len(json.loads(r.stdout).get('streams', [])) > 0
    except Exception:
        return False


def create_seamless_loop(src: Path, loop_path: Path) -> bool:
    src_dur = get_duration(src)
    skip = SKIP_START if src_dur > SKIP_START + LOOP_DUR + FADE_DUR else 0
    offset = LOOP_DUR - FADE_DUR
    src_has_audio = has_audio(src)

    # Video: seamless xfade between two reads of the same clip
    filter_complex = (
        f'[0:v]scale=1280:720:force_original_aspect_ratio=decrease,'
        f'pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1[v0];'
        f'[1:v]scale=1280:720:force_original_aspect_ratio=decrease,'
        f'pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1[v1];'
        f'[v0][v1]xfade=transition=fade:duration={FADE_DUR}:offset={offset}[vout]'
    )
    cmd = [
        'ffmpeg', '-y',
        '-ss', str(skip), '-t', str(LOOP_DUR + FADE_DUR), '-i', str(src),
        '-ss', str(skip), '-t', str(LOOP_DUR + FADE_DUR), '-i', str(src),
        '-filter_complex', filter_complex,
        '-map', '[vout]', '-t', str(LOOP_DUR),
        '-c:v', 'libx264', '-crf', '20', '-preset', 'fast', '-pix_fmt', 'yuv420p',
    ]
    if src_has_audio:
        # Keep natural audio from clip — simple trim; nature sounds cycle cleanly at low vol
        cmd += ['-map', '0:a:0', '-c:a', 'aac', '-b:a', '128k', '-ar', '44100']
    else:
        cmd += ['-an']
    cmd += [str(loop_path)]

    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        log.error(f"  Seamless loop failed: {r.stderr[-300:]}")
        return False
    label = "with natural audio" if src_has_audio else "video only"
    log.info(f"  Loop: {loop_path.name} ({LOOP_DUR}s, {label}, {loop_path.stat().st_size//1024}KB)")
    return True


def find_audio(kw_list: list[str]) -> Path | None:
    if not AUDIO_DIR.exists():
        return None
    for kw in kw_list:
        matches = [f for f in AUDIO_DIR.glob('*.mp3') if kw.lower() in f.name.lower()]
        if matches:
            base = [m for m in matches if '(' not in m.name]
            return (base or matches)[0]
    return None


def build_long_video(loop_path: Path, audio_path: Path | None,
                     out_mp4: Path, natural_vol: float = 0.0,
                     target_dur: int = TARGET_DUR) -> bool:
    loop_dur = get_duration(loop_path)
    loops_needed = int(target_dur / loop_dur) + 2
    loop_has_audio = has_audio(loop_path)

    tmp = out_mp4.parent / '_ambient_tmp'
    tmp.mkdir(exist_ok=True)
    concat_f = tmp / 'concat_v.txt'
    loop_mp4  = tmp / 'loop.mp4'

    try:
        concat_f.write_text(''.join(f"file '{loop_path.resolve()}'\n" for _ in range(loops_needed)))
        r = subprocess.run([
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
            '-i', str(concat_f),
            '-t', str(target_dur + 2), '-c', 'copy', str(loop_mp4)
        ], capture_output=True, timeout=300)
        if r.returncode != 0:
            log.error(f"  Loop concat failed: {r.stderr[-200:]}")
            return False

        fade_start = max(0, target_dur - 3)

        if audio_path and audio_path.exists():
            audio_dur = get_duration(audio_path)
            audio_loops = int(target_dur / audio_dur) + 2
            concat_a = tmp / 'concat_a.txt'
            concat_a.write_text(''.join(f"file '{audio_path.resolve()}'\n" for _ in range(audio_loops)))
            loop_audio = tmp / 'audio_loop.mp3'
            subprocess.run([
                'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(concat_a),
                '-t', str(target_dur + 2), '-ar', '44100', '-ac', '2',
                '-c:a', 'libmp3lame', '-b:a', '192k', str(loop_audio)
            ], capture_output=True, timeout=300)

            if loop_has_audio and natural_vol > 0.0:
                # Mix: natural Pexels audio (at natural_vol) + AI music (at MUSIC_VOL=1.0)
                # [0] = loop_mp4 (video + natural audio), [1] = loop_audio (AI music)
                log.info(f"  Mixing natural audio (vol={natural_vol:.2f}) + AI music (vol={MUSIC_VOL:.1f})")
                fc = (
                    f'[0:v]fade=t=out:st={fade_start}:d=3[vout];'
                    f'[0:a]volume={natural_vol}[nat];'
                    f'[1:a]volume={MUSIC_VOL}[music];'
                    f'[nat][music]amix=inputs=2:duration=first:normalize=0[amixed];'
                    f'[amixed]afade=t=out:st={fade_start}:d=3[aout]'
                )
                cmd = [
                    'ffmpeg', '-y',
                    '-i', str(loop_mp4), '-i', str(loop_audio),
                    '-filter_complex', fc,
                    '-map', '[vout]', '-map', '[aout]',
                    '-t', str(target_dur),
                    '-c:v', 'libx264', '-crf', '20', '-preset', 'fast',
                    '-c:a', 'aac', '-b:a', '192k', '-pix_fmt', 'yuv420p', str(out_mp4)
                ]
            else:
                # No natural audio or vol=0 — AI music only
                cmd = [
                    'ffmpeg', '-y',
                    '-i', str(loop_mp4), '-i', str(loop_audio),
                    '-map', '0:v:0', '-map', '1:a:0',
                    '-vf', f'fade=t=out:st={fade_start}:d=3',
                    '-af', f'afade=t=out:st={fade_start}:d=3',
                    '-t', str(target_dur),
                    '-c:v', 'libx264', '-crf', '20', '-preset', 'fast',
                    '-c:a', 'aac', '-b:a', '192k', '-pix_fmt', 'yuv420p', str(out_mp4)
                ]
        else:
            log.warning("  No AI audio found — using natural sound only")
            if loop_has_audio:
                cmd = [
                    'ffmpeg', '-y', '-i', str(loop_mp4),
                    '-map', '0:v:0', '-map', '0:a:0',
                    '-vf', f'fade=t=out:st={fade_start}:d=3',
                    '-af', f'afade=t=out:st={fade_start}:d=3',
                    '-t', str(target_dur),
                    '-c:v', 'libx264', '-crf', '20', '-preset', 'fast',
                    '-c:a', 'aac', '-b:a', '192k', '-pix_fmt', 'yuv420p', str(out_mp4)
                ]
            else:
                log.warning("  No audio at all — silent video")
                cmd = [
                    'ffmpeg', '-y', '-i', str(loop_mp4), '-map', '0:v:0',
                    '-vf', f'fade=t=out:st={fade_start}:d=3',
                    '-t', str(target_dur),
                    '-c:v', 'libx264', '-crf', '20', '-preset', 'fast',
                    '-pix_fmt', 'yuv420p', '-an', str(out_mp4)
                ]

        r = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
        if r.returncode != 0:
            log.error(f"  Final mix failed: {r.stderr[-300:]}")
            return False

        log.info(f"  Video: {out_mp4.name} ({out_mp4.stat().st_size//1024//1024}MB)")
        return True
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def make_thumbnail(loop_path: Path, out_path: Path) -> bool:
    dur = get_duration(loop_path)
    r = subprocess.run([
        'ffmpeg', '-y', '-ss', str(dur / 2), '-i', str(loop_path),
        '-vframes', '1', '-s', '1280x720', str(out_path)
    ], capture_output=True, timeout=30)
    return r.returncode == 0 and out_path.exists()


# ── Meta ──────────────────────────────────────────────────────────────────────

def build_meta(atype: str, audio_name: str, dur_sec: int, meta_cfg: dict) -> dict:
    cfg = AMBIENT_TYPES[atype]
    h = dur_sec // 3600
    m = (dur_sec % 3600) // 60
    dur_str = f"{h} Hour" if m == 0 else f"{h} Hour {m} Min"
    title = f"{cfg['name']} — {dur_str} | Ambient Sounds | Sacred Drift"

    footer = meta_cfg.get('video_defaults', {}).get('description_footer', '')
    description = f"""{cfg['name']}

{dur_str} of continuous {cfg['desc']} — perfect for deep relaxation, meditation, sleep and focus.

✨ Best experienced on a large screen or TV for full immersion.
🎧 Pair with headphones for the ultimate ambient experience.
🔁 Video loops seamlessly — ideal for background ambience all night.

━━━━━━━━━━━━━━━━━━━━━━━
About Sacred Drift:
Sacred Drift is a sanctuary of sound and vision — ambient nature, fire, water and healing soundscapes for deep rest and inner peace.

Subscribe 🔮 @SacredDrift
━━━━━━━━━━━━━━━━━━━━━━━

📹 Footage licensed under Pexels License (free to use, no attribution required)
🎵 Audio: {audio_name} (AI-generated, © Sacred Drift 2026)

{footer}"""

    base_tags = meta_cfg.get('video_defaults', {}).get('tags_base', [])
    all_tags  = cfg['tags'] + base_tags
    seen, tags, total = set(), [], 0
    for t in all_tags:
        if t and t not in seen and len(t) <= 30 and len(tags) < 30 and total + len(t) <= 500:
            seen.add(t); tags.append(t); total += len(t)

    return {
        'title':         title,
        'description':   description,
        'tags':          tags,
        'video_type':    'ambient_video',
        'ambient_type':  atype,
        'ambient_group': cfg['group'],
        'language':      'en',
        'is_short':      False,
        'status':        'public',
        'made_for_kids': False,
        'ai_generated':  False,
        'duration_sec':  dur_sec,
    }


# ── Core process ──────────────────────────────────────────────────────────────

def process_type(atype: str, meta_cfg: dict, dry_run: bool = False,
                 force: bool = False) -> bool:
    cfg = AMBIENT_TYPES[atype]
    log.info(f"\n{'='*60}")
    log.info(f"{cfg['group'].upper()} — {cfg['name']}")

    out_stem  = f"ambient_{atype}_{DATE_STR}"
    out_mp4   = QUEUE_DIR / f"{out_stem}.mp4"
    out_meta  = QUEUE_DIR / f"meta_{out_stem}.yaml"
    out_thumb = QUEUE_DIR / f"thumb_{out_stem}.png"
    loop_path = LOOPS_DIR / f"loop_{atype}.mp4"
    raw_path  = LOOPS_DIR / f"raw_{atype}.mp4"

    if out_mp4.exists() and not force:
        log.info("  EXISTS — skip (--force to redo)")
        return True

    audio_path = find_audio(cfg['audio'])
    audio_name = audio_path.stem if audio_path else 'Silent'
    log.info(f"  Audio: {audio_name}")

    if dry_run:
        log.info(f"  [DRY RUN] Pexels: '{cfg['query']}'")
        log.info(f"  [DRY RUN] → {out_mp4.name}")
        return True

    LOOPS_DIR.mkdir(parents=True, exist_ok=True)
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)

    # Download source if loop not cached
    if not loop_path.exists() or force:
        if not raw_path.exists() or force:
            log.info(f"  Searching Pexels: '{cfg['query']}'")
            try:
                videos = pexels_search(cfg['query'])
            except Exception as e:
                log.error(f"  Pexels error: {e}")
                return False
            if not videos:
                log.error("  No results")
                return False

            # Prefer longer clips (more stable footage)
            videos.sort(key=lambda v: v.get('duration', 0), reverse=True)
            downloaded = False
            for vid in videos[:5]:
                url, w, h = best_video_url(vid)
                if url:
                    dur = vid.get('duration', 0)
                    log.info(f"  Found: {w}×{h} {dur}s — {vid.get('url','')}")
                    if download_video(url, raw_path):
                        downloaded = True
                        break
            if not downloaded:
                log.error("  Could not download any clip")
                return False

        log.info(f"  Creating seamless {LOOP_DUR}s loop...")
        if not create_seamless_loop(raw_path, loop_path):
            return False

    log.info(f"  Building {TARGET_DUR//3600}h video...")
    if not build_long_video(loop_path, audio_path, out_mp4,
                            natural_vol=cfg.get('natural_vol', 0.0),
                            target_dur=TARGET_DUR):
        return False

    make_thumbnail(loop_path, out_thumb)
    meta_doc = build_meta(atype, audio_name, TARGET_DUR, meta_cfg)
    out_meta.write_text(yaml.dump(meta_doc, allow_unicode=True, default_flow_style=False))
    log.info(f"  Meta: {out_meta.name}")
    return True


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--list',    action='store_true')
    parser.add_argument('--type',    choices=list(AMBIENT_TYPES.keys()))
    parser.add_argument('--group',   choices=['fire', 'water'], help='Generate all types in group')
    parser.add_argument('--all',     action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--force',   action='store_true')
    args = parser.parse_args()

    if args.list:
        print(f"\n{'Type':<22} {'Group':<8} {'Name':<38} Audio")
        print('-' * 90)
        for k, v in AMBIENT_TYPES.items():
            audio = find_audio(v['audio'])
            loop  = '✓' if (LOOPS_DIR / f"loop_{k}.mp4").exists() else ' '
            print(f"  [{loop}] {k:<20} {v['group']:<8} {v['name']:<38} {audio.stem if audio else 'NOT FOUND'}")
        return

    meta_cfg = yaml.safe_load(CONFIG.read_text()) if CONFIG.exists() else {}

    if args.type:
        types = [args.type]
    elif args.group:
        types = [k for k, v in AMBIENT_TYPES.items() if v['group'] == args.group]
    elif args.all:
        types = list(AMBIENT_TYPES.keys())
    else:
        parser.print_help()
        return

    ok = fail = 0
    for t in types:
        if process_type(t, meta_cfg, dry_run=args.dry_run, force=args.force):
            ok += 1
        else:
            fail += 1

    log.info(f"\nDone: {ok} OK, {fail} failed")


if __name__ == '__main__':
    main()
