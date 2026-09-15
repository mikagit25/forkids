#!/usr/bin/env python3
"""
Adapt Calm Classics (CNR) queue videos for Sacred Drift channel.

Takes already-rendered MP4s from output/queue_id/ and creates
SD-branded meta + copies/symlinks them to sacred_drift/output/queue/.

Rules:
- Same MP4 file (symlinked, no re-encode)
- New thumbnail generated via Together.ai (different visual from CNR)
- New title: meditation angle, "| Sacred Drift" suffix
- New description: Sacred Drift style (healing, inner peace, etc.)
- All recordings are public domain (Musopen PD/CC0)

Usage:
  python3 scripts/adapt_cnr_to_sd.py --dry-run
  python3 scripts/adapt_cnr_to_sd.py
  python3 scripts/adapt_cnr_to_sd.py --only-type sleep_program
"""

import argparse, base64, json, logging, re, shutil, subprocess, yaml
from datetime import datetime
from pathlib import Path

ROOT      = Path(__file__).resolve().parent.parent
CNR_QUEUE = ROOT / 'output' / 'queue_id'
SD_QUEUE  = ROOT / 'sacred_drift' / 'output' / 'queue'
TOGETHER_KEY_FILE = ROOT / 'credentials' / 'together_api_key.txt'
DATE_STR  = datetime.now().strftime('%Y%m%d')

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')


# ── Title adaptation ──────────────────────────────────────────────────────────

def adapt_title(cnr_title: str, vtype: str, dur_min: int) -> str:
    """Convert CNR-branded title to Sacred Drift meditation title."""
    title = cnr_title

    # Strip everything after the first | (CNR branding, type labels, etc.)
    if '|' in title:
        title = title[:title.index('|')].strip()

    # Strip #shorts
    title = re.sub(r'#\w+', '', title).strip()

    # Remove existing duration patterns (e.g. "1h 14min", "4h 4min", "39 min", "10min")
    title = re.sub(r'\b\d+h\s+\d+\s*min\b', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\b\d+\s*min\b', '', title, flags=re.IGNORECASE)
    title = re.sub(r'\b\d+h\b', '', title, flags=re.IGNORECASE)

    # Clean up trailing dashes, pipes, spaces and trailing emojis
    title = re.sub(r'[\s\-—|]+$', '', title).strip()
    title = re.sub(r'[\U0001F300-\U0001FFFF☀-⛿✀-➿]+$', '', title).strip()
    title = re.sub(r'[\s\-—]+$', '', title).strip()

    # Duration label for new title
    h, m = dur_min // 60, dur_min % 60
    if h > 1:
        dur_str = f"{h} Hours" + (f" {m} Min" if m else "")
    elif h == 1:
        dur_str = "1 Hour" + (f" {m} Min" if m else "")
    else:
        dur_str = f"{m} Min"

    # SD meditation angle
    if vtype == 'sleep_program':
        angle = 'Deep Sleep Meditation'
    elif vtype == 'focus_program':
        angle = 'Deep Focus & Flow'
    elif vtype == 'visual_theme':
        angle = 'Meditation Ambience'
    else:
        angle = 'Sacred Sound Session'

    return f"{title} — {angle} 🎶 {dur_str} | Sacred Drift"


# ── Description adaptation ────────────────────────────────────────────────────

COMPOSER_HOOKS = {
    'bach':      "Johann Sebastian Bach composed music of extraordinary mathematical beauty and spiritual depth. These works have accompanied meditation, prayer and contemplation for centuries.",
    'beethoven': "Ludwig van Beethoven's music transcends its era — expressing struggle, triumph and transcendence. Let these compositions guide you into states of deep focus and inner stillness.",
    'schubert':  "Franz Schubert's music carries a profound emotional honesty — tender, melancholic, luminous. Ideal for deep relaxation and emotional release.",
    'chopin':    "Frédéric Chopin's piano poetry speaks directly to the heart. These nocturnes and études create a meditative sanctuary of sound.",
    'debussy':   "Claude Debussy's impressionist soundscapes dissolve the boundary between music and nature. Perfect for deep meditation and sensory relaxation.",
    'mozart':    "Wolfgang Amadeus Mozart's music activates clarity, joy and inner harmony. Studies suggest his compositions uniquely support focused mental states.",
    'wagner':    "Richard Wagner's sweeping orchestral landscapes create immersive sonic environments for deep contemplation and inner journeys.",
    'tchaikovsky': "Pyotr Tchaikovsky's romantic orchestral voice — passionate, cinematic and deeply human — creates perfect conditions for emotional healing and rest.",
    'brahms':    "Johannes Brahms' music balances intellectual depth with warm emotional resonance — ideal for sustained focus and deep meditation.",
    'fauré':     "Gabriel Fauré's gentle, luminous harmonies create an atmosphere of serene contemplation and peaceful rest.",
    'franck':    "César Franck's deeply spiritual music carries a transcendent quality that has long supported prayer, meditation and inner peace.",
}

def get_composer_hook(title: str) -> str:
    title_lower = title.lower()
    for composer, hook in COMPOSER_HOOKS.items():
        if composer in title_lower:
            return hook
    return "This collection of classical recordings — all from public domain performances — creates a sanctuary of sound for deep rest, focus and contemplation."


def build_sd_description(cnr_meta: dict, dur_min: int, vtype: str) -> str:
    cnr_title = cnr_meta.get('title', '')
    composer_hook = get_composer_hook(cnr_title)

    h, m = dur_min // 60, dur_min % 60
    dur_str = f"{h} hour" + (f" {m} min" if m else "") if h else f"{m} minutes"
    if h > 1: dur_str = f"{h} hours" + (f" {m} min" if m else "")

    if vtype == 'sleep_program':
        use_case = "deep sleep, insomnia relief, night rest"
        instruction = "Let the music carry your mind into stillness. Allow each breath to slow. Surrender to rest."
        heading = "Deep Sleep"
    elif vtype == 'focus_program':
        use_case = "deep focus, studying, work, flow state"
        instruction = "Set your intention. Let the music become background to pure concentration. Allow thought to flow freely."
        heading = "Deep Focus"
    else:
        use_case = "meditation, relaxation, background ambience, healing"
        instruction = "Find a quiet place. Close your eyes. Let the music dissolve mental chatter and bring you home."
        heading = "Meditation"

    footer_cfg = yaml.safe_load((ROOT / 'sacred_drift/config/channel_metadata_sd.yaml').read_text())
    footer = footer_cfg.get('video_defaults', {}).get('description_footer', '')

    return f"""{heading} — {dur_str.title()} of Classical Sound for Inner Peace

{composer_hook}

✨ Best experienced with headphones at a comfortable volume.
🎧 Ideal for: {use_case}

How to use this session:
• Find a quiet, comfortable space
• {instruction}
• There is nothing to do — only to receive

────────────────────────────────────
🎵 All recordings are public domain (Musopen.org — PD/CC0 licensed).
No copyright claims. Safe for meditation, sleep and focus.
────────────────────────────────────

About Sacred Drift:
Sacred Drift is a sanctuary of sound — meditation music, healing frequencies and sacred soundscapes for those seeking deep rest, inner calm and spiritual connection.

🔮 Subscribe for new sessions every week: @SacredDrift

────────────────────────────────────
{footer}"""


# ── Tags ──────────────────────────────────────────────────────────────────────

def build_sd_tags(cnr_meta: dict, vtype: str) -> list:
    base_cfg = yaml.safe_load((ROOT / 'sacred_drift/config/channel_metadata_sd.yaml').read_text())
    base = base_cfg.get('video_defaults', {}).get('tags_base', [])

    type_tags = {
        'sleep_program': ['sleep music', 'classical sleep', 'deep sleep', 'classical for sleep', 'sleep meditation'],
        'focus_program': ['focus music', 'study music', 'classical focus', 'deep focus', 'concentration music'],
        'visual_theme':  ['meditation music', 'ambient classical', 'relaxing classical', 'background music'],
    }.get(vtype, [])

    all_tags = type_tags + base
    seen, result, total = set(), [], 0
    for t in all_tags:
        if t and t not in seen and len(t) <= 30 and len(result) < 30 and total + len(t) <= 500:
            seen.add(t); result.append(t); total += len(t)
    return result


# ── Thumbnail ─────────────────────────────────────────────────────────────────

THUMB_PROMPTS = {
    'bach':        "ancient cathedral interior, golden candlelight, stone arches, sacred geometry, dark mystical atmosphere, no text",
    'beethoven':   "dramatic stormy night, classical concert hall interior, golden light, powerful atmosphere, sacred space, no text",
    'schubert':    "misty forest at dawn, soft golden light filtering through ancient trees, peaceful ethereal atmosphere, no text",
    'chopin':      "moonlit piano in an elegant dark room, candles, velvet curtains, romantic mystical atmosphere, no text",
    'debussy':     "impressionist water garden at dusk, lily pads, soft purple and gold reflections, dreamy ethereal light, no text",
    'mozart':      "baroque garden at twilight, geometric fountains, golden sky, classical architecture, peaceful sacred space, no text",
    'wagner':      "dramatic mountain landscape at dusk, epic orchestral atmosphere, deep purple sky, sacred ancient forest, no text",
    'tchaikovsky': "winter palace garden at night, snow-covered trees, golden lights, romantic mystical atmosphere, no text",
    'brahms':      "old library with warm candlelight, leather-bound books, oak desk, autumn evening, sanctuary atmosphere, no text",
    'fauré':       "lavender field at golden hour, soft purple haze, ancient chapel in background, peaceful sacred light, no text",
    'franck':      "gothic cathedral interior, rose window light, incense smoke, spiritual sacred geometry, deep purple tones, no text",
    'default':     "ancient stone temple at sunset, sacred atmosphere, golden light rays, mystical peaceful energy, no text",
}

def get_thumb_prompt(title: str) -> str:
    title_lower = title.lower()
    for composer, prompt in THUMB_PROMPTS.items():
        if composer != 'default' and composer in title_lower:
            return f"Sacred Drift channel thumbnail, {prompt}, cinematic 4K quality, ultra detailed"
    return f"Sacred Drift channel thumbnail, {THUMB_PROMPTS['default']}, cinematic 4K quality, ultra detailed"


def generate_thumbnail(prompt: str, out_path: Path) -> bool:
    if not TOGETHER_KEY_FILE.exists():
        return False
    api_key = TOGETHER_KEY_FILE.read_text().strip()
    import urllib.request
    payload = json.dumps({
        "model": "black-forest-labs/FLUX.1.1-pro",
        "prompt": prompt, "width": 1280, "height": 720,
        "steps": 4, "n": 1, "response_format": "b64_json"
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
            return False
        out_path.write_bytes(base64.b64decode(b64))
        log.info(f"  Thumbnail: {out_path.name}")
        return True
    except Exception as e:
        log.error(f"  FLUX error: {e}")
        return False


# ── Duration helper ───────────────────────────────────────────────────────────

def get_duration_min(mp4: Path) -> int:
    r = subprocess.run(
        ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', str(mp4)],
        capture_output=True
    )
    try:
        return int(float(json.loads(r.stdout)['format']['duration']) / 60)
    except Exception:
        return 0


# ── Main processing ───────────────────────────────────────────────────────────

ELIGIBLE_TYPES = ('sleep_program', 'focus_program', 'visual_theme', 'nature_calm')
MIN_DURATION_MIN = 30   # skip very short videos

def process_cnr_video(meta_file: Path, dry_run: bool = False) -> bool:
    cnr_meta = yaml.safe_load(meta_file.read_text()) or {}

    if cnr_meta.get('youtube_id'):
        log.info(f"SKIP (already published): {meta_file.name}")
        return True

    vtype = cnr_meta.get('video_type', '')
    if vtype not in ELIGIBLE_TYPES:
        return False

    # Find MP4
    stem = meta_file.stem.replace('meta_', '')
    mp4 = meta_file.parent / f"{stem}.mp4"
    if not mp4.exists():
        log.debug(f"No MP4 for {stem}, skipping")
        return False

    dur_min = get_duration_min(mp4)
    if dur_min < MIN_DURATION_MIN:
        log.info(f"SKIP (too short {dur_min}min): {stem}")
        return False

    # Output paths in SD queue
    sd_stem    = f"sd_classical_{stem}"
    sd_mp4     = SD_QUEUE / f"{sd_stem}.mp4"
    sd_meta    = SD_QUEUE / f"meta_{sd_stem}.yaml"
    sd_thumb   = SD_QUEUE / f"thumb_{sd_stem}.png"

    if sd_mp4.exists():
        log.info(f"SKIP (already in SD queue): {sd_stem}")
        return True

    log.info(f"\n{'='*60}")
    log.info(f"Adapting: {stem}")
    log.info(f"Type: {vtype} | Duration: {dur_min}min")

    title = adapt_title(cnr_meta.get('title', ''), vtype, dur_min)
    log.info(f"Title: {title}")

    if dry_run:
        return True

    # 1. Symlink MP4 (avoid copying huge files)
    try:
        sd_mp4.symlink_to(mp4.resolve())
        log.info(f"  Linked: {mp4.name} → {sd_mp4.name}")
    except Exception as e:
        log.error(f"  Symlink failed: {e}")
        return False

    # 2. Generate SD-style thumbnail
    thumb_prompt = get_thumb_prompt(title)
    if not generate_thumbnail(thumb_prompt, sd_thumb):
        # Fallback: copy CNR thumbnail if exists
        cnr_thumb = meta_file.parent / f"thumb_{stem}.png"
        if cnr_thumb.exists():
            shutil.copy(str(cnr_thumb), str(sd_thumb))
            log.info(f"  Thumb fallback: copied from CNR")
        else:
            sd_thumb.write_bytes(b'')  # placeholder

    # 3. Build SD meta
    description = build_sd_description(cnr_meta, dur_min, vtype)
    tags = build_sd_tags(cnr_meta, vtype)

    sd_meta_doc = {
        'title':          title,
        'description':    description,
        'tags':           tags,
        'video_type':     'classical_meditation',
        'language':       'en',
        'is_short':       False,
        'status':         'public',
        'made_for_kids':  False,
        'ai_generated':   False,
        'music_source':   'Musopen PD/CC0',
        'source_channel': 'cnr',
        'source_file':    str(mp4),
        'duration_sec':   dur_min * 60,
    }
    sd_meta.write_text(yaml.dump(sd_meta_doc, allow_unicode=True, default_flow_style=False))
    log.info(f"  Meta: {sd_meta.name}")
    return True


def main():
    parser = argparse.ArgumentParser(description='Adapt CNR queue videos to Sacred Drift')
    parser.add_argument('--dry-run',    action='store_true')
    parser.add_argument('--only-type',  help='Filter by video_type (e.g. sleep_program)')
    parser.add_argument('--min-dur',    type=int, default=MIN_DURATION_MIN,
                        help='Minimum duration in minutes (default 30)')
    args = parser.parse_args()

    SD_QUEUE.mkdir(parents=True, exist_ok=True)

    meta_files = sorted(CNR_QUEUE.glob('meta_*.yaml'))
    log.info(f"Found {len(meta_files)} meta files in CNR queue")

    ok = fail = skip = 0
    for mf in meta_files:
        m = yaml.safe_load(mf.read_text()) or {}
        vtype = m.get('video_type', '')
        if args.only_type and vtype != args.only_type:
            skip += 1
            continue
        if vtype not in ELIGIBLE_TYPES:
            skip += 1
            continue
        if process_cnr_video(mf, dry_run=args.dry_run):
            ok += 1
        else:
            fail += 1

    log.info(f"\n{'='*60}")
    log.info(f"Done: {ok} adapted, {fail} failed, {skip} skipped")
    if args.dry_run:
        log.info("[DRY RUN — nothing was written]")


if __name__ == '__main__':
    main()
