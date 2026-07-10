#!/usr/bin/env python3
"""
Scenario Orchestrator — reads Google Sheets queue and dispatches video renders.

Sheet: https://docs.google.com/spreadsheets/d/1MAHh_LxESZCd0sWOx0qAjSWWIElR79oTfo-XiPbJc7o
Tab: Queue
Actual columns (A–M):
  id | type | lang | key | doc_url | params | priority | status |
  youtube_id_en | youtube_id_ar | notes | created | updated

Statuses: pending → rendering → rendered → failed
lang values:
  en   — English only              → output/queue/
  ar   — Arabic only               → output/queue_ar/
  id   — Classical Night Relax     → output/queue_id/  (ADULT channel, NOT kids)
  kids — EN + AR only              → expand_langs() returns ['en','ar'] (never queue_id)
  both — EN + AR + ID              → expand_langs() returns ['en','ar','id']
  all  — EN + AR + ID              → same as both (only for CNRelax-approved content)

NOTE: Scripts that generate no-text content handle all 3 queues internally —
      dispatch functions for those scripts do NOT pass --lang.

Cron: 0 * * * * cd /opt/kids_channel && python3 scripts/scenario_orchestrator.py >> logs/orchestrator.log 2>&1
"""

import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

# ── Google Sheets setup ───────────────────────────────────────────────────────
SHEET_ID  = '1MAHh_LxESZCd0sWOx0qAjSWWIElR79oTfo-XiPbJc7o'
KEY_FILE  = ROOT / 'credentials' / 'drive_service_account.json'
SCOPES    = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/documents.readonly',
    'https://www.googleapis.com/auth/drive.readonly',
]
TAB       = 'Queue'

# Column indices (0-based) — A through N (14 columns)
COL = {
    'id': 0, 'type': 1, 'lang': 2, 'key': 3, 'doc_url': 4, 'params': 5,
    'priority': 6, 'status': 7, 'youtube_id_en': 8, 'youtube_id_ar': 9,
    'youtube_id_id': 10, 'notes': 11, 'created': 12, 'updated': 13,
}

BOT_TOKEN = "8657721269:AAEkhJ92vHR4K1CkA14nFcy0_bA95c38QZk"
CHAT_ID   = "209381269"

# ── Helpers ───────────────────────────────────────────────────────────────────

def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def tg(msg: str):
    import urllib.request, json
    try:
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data=json.dumps({"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}).encode(),
            headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')


def get_creds():
    from google.oauth2 import service_account
    return service_account.Credentials.from_service_account_file(str(KEY_FILE), scopes=SCOPES)


def get_sheets_service():
    from googleapiclient.discovery import build
    return build('sheets', 'v4', credentials=get_creds()).spreadsheets()


def extract_doc_id(url: str) -> str | None:
    """Extract Google Doc ID from URL."""
    m = re.search(r'/document/d/([a-zA-Z0-9_-]+)', url)
    return m.group(1) if m else None


def read_google_doc(doc_url: str) -> str:
    """Read plain text from a Google Doc via Docs API."""
    doc_id = extract_doc_id(doc_url)
    if not doc_id:
        return ''
    try:
        from googleapiclient.discovery import build
        svc = build('docs', 'v1', credentials=get_creds())
        doc = svc.documents().get(documentId=doc_id).execute()
        # Extract all text from the document body
        text_parts = []
        for block in doc.get('body', {}).get('content', []):
            for elem in block.get('paragraph', {}).get('elements', []):
                t = elem.get('textRun', {}).get('content', '')
                if t:
                    text_parts.append(t)
        return ''.join(text_parts)
    except Exception as e:
        log(f"  Could not read Google Doc: {e}")
        return ''


def parse_params(params_str: str) -> dict:
    """Parse 'key=val,key2=val2' string into dict. Handles objects list with |."""
    result = {}
    if not params_str:
        return result
    for part in params_str.split(','):
        part = part.strip()
        if '=' not in part:
            continue
        k, v = part.split('=', 1)
        result[k.strip()] = v.strip()
    return result


def any_render_running() -> bool:
    import psutil
    self_pid = os.getpid()
    for proc in psutil.process_iter(['pid', 'cmdline']):
        try:
            if proc.info['pid'] == self_pid:
                continue
            cmdline = ' '.join(proc.info['cmdline'] or [])
            # Any kids_channel generate script or sequential runner = render in progress
            if ('kids_channel' in cmdline or '/opt/kids_channel' in cmdline) and (
                'generate_' in cmdline or 'run_renders_sequential' in cmdline
            ):
                return True
            # Remotion render process
            if 'remotion render' in cmdline and 'kids_channel' in cmdline:
                return True
        except Exception:
            pass
    return False


# ── Dispatchers ───────────────────────────────────────────────────────────────

LANG_QUEUE = {
    'en':   ROOT / 'output' / 'queue',
    'ar':   ROOT / 'output' / 'queue_ar',
    'id':   ROOT / 'output' / 'queue_id',    # CNRelax only — adult sleep/focus
    'kids': ROOT / 'output' / 'queue',        # EN+AR kids only, NEVER CNRelax
    'both': ROOT / 'output' / 'queue',        # EN+AR — videos WITH voice/text (2 renders)
    'all':  ROOT / 'output' / 'queue',        # EN+AR+ID — ONLY for content valid on CNRelax
}

# CNRelax (queue_id) allowed content types — adult sleep/focus only
CNR_ALLOWED = {'sleep_program', 'focus_program', 'sleep_short', 'visual_theme', 'nature_calm'}

def expand_langs(lang: str) -> list[str]:
    """Expand lang shorthand to list of language codes.
    'kids' = EN+AR only (never CNRelax).
    'both'/'all' = EN+AR+ID — only for content approved for CNRelax.
    """
    if lang in ('both', 'all'):
        return ['en', 'ar', 'id']
    if lang == 'kids':
        return ['en', 'ar']
    return [lang]


def dispatch_color_learn(row: dict) -> bool:
    """Render color_learn video(s). lang=both/all → EN+AR+ID (3 renders)."""
    key   = row['key']          # e.g. "purple"
    lang  = row['lang']         # en | ar | id | both | all
    langs = expand_langs(lang)

    for lg in langs:
        cmd = [sys.executable, str(ROOT / 'scripts' / 'generate_color_learn_long.py'),
               '--colors', key, '--lang', lg]
        log(f"  Running: {' '.join(cmd)}")
        r = subprocess.run(cmd, capture_output=False, timeout=21600)
        if r.returncode != 0:
            log(f"  color_learn {key} {lg} FAILED (exit {r.returncode})")
            return False
    return True


def dispatch_number_learn(row: dict) -> bool:
    """Render number_learn video(s). lang=both/all → EN+AR+ID (3 renders)."""
    key   = row['key']          # e.g. "1" or "five"
    lang  = row['lang']
    langs = expand_langs(lang)

    for lg in langs:
        cmd = [sys.executable, str(ROOT / 'scripts' / 'generate_number_learn_long.py'),
               '--numbers', key, '--lang', lg]
        log(f"  Running: {' '.join(cmd)}")
        r = subprocess.run(cmd, capture_output=False, timeout=21600)
        if r.returncode != 0:
            log(f"  number_learn {key} {lg} FAILED")
            return False
    return True


def dispatch_shape_learn(row: dict) -> bool:
    """Render shape_learn. No text/voice → always publishes to all 3 channels (EN+AR+ID).
    lang=all or lang=both both trigger the 3-channel copy in generate_shape_learn.py."""
    key  = row['key']           # e.g. "pentagon"
    lang = row['lang']
    cmd  = [sys.executable, str(ROOT / 'scripts' / 'generate_shape_learn.py'),
            '--shapes', key]
    # lang=all or lang=both → omit --lang so the script copies to all 3 queues
    if lang not in ('both', 'all'):
        cmd += ['--lang', lang]
    log(f"  Running: {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=False, timeout=21600)
    return r.returncode == 0


def dispatch_dance(row: dict) -> bool:
    """Render 30-min dance video via generate_dance_long.py (auto meta + thumbnail)."""
    key   = row['key']   # animals | fruits | vegetables
    valid = ('animals', 'fruits', 'vegetables')
    if key not in valid:
        log(f"  Unknown dance theme: {key}. Valid: {valid}")
        return False
    cmd = [sys.executable, str(ROOT / 'scripts' / 'generate_dance_long.py'), '--themes', key]
    log(f"  Running: {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=False, timeout=21600)
    return r.returncode == 0


def dispatch_nursery_ar(row: dict) -> bool:
    """Render Arabic nursery rhyme. lang=ar → AR only; both/all → EN+AR+ID."""
    key  = row['key']
    lang = row['lang']
    cmd  = [sys.executable, str(ROOT / 'scripts' / 'generate_nursery_ar.py'),
            '--key', key, '--lang', lang]
    log(f"  Running: {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=False, timeout=21600)
    return r.returncode == 0


def dispatch_nursery_id(row: dict) -> bool:
    """Render Indonesian nursery rhyme."""
    key  = row['key']
    lang = row['lang']   # typically 'id' or 'all'
    cmd  = [sys.executable, str(ROOT / 'scripts' / 'generate_nursery_id.py'),
            '--key', key, '--lang', lang]
    log(f"  Running: {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=False, timeout=21600)
    return r.returncode == 0


def dispatch_sensory_loop(row: dict) -> bool:
    """Render sensory loop abstract animation videos. No text → all 3 channels."""
    key = row['key']
    cmd = [sys.executable, str(ROOT / 'scripts' / 'generate_sensory_loop.py'), '--key', key]
    log(f"  Running: {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=False, timeout=86400)
    return r.returncode == 0


def dispatch_stars_bubbles(row: dict) -> bool:
    """Render stars and bubbles abstract video. Kids channels only (EN+AR), NOT CNRelax."""
    cmd = [sys.executable, str(ROOT / 'scripts' / 'generate_stars_bubbles.py'), '--queues', 'en', 'ar']
    log(f"  Running: {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=False, timeout=21600)
    return r.returncode == 0


def dispatch_dance_shape(row: dict) -> bool:
    """Render dancing shapes series. No text → all 3 channels."""
    cmd = [sys.executable, str(ROOT / 'scripts' / 'generate_dance_shape.py')]
    log(f"  Running: {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=False, timeout=86400)
    return r.returncode == 0


def dispatch_dance_pet(row: dict) -> bool:
    """Render dancing home pets series. No text → all 3 channels."""
    key = row['key']
    cmd = [sys.executable, str(ROOT / 'scripts' / 'generate_dance_pet.py'), '--key', key]
    log(f"  Running: {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=False, timeout=86400)
    return r.returncode == 0


def dispatch_dance_item(row: dict) -> bool:
    """Render dancing household items series. No text → all 3 channels."""
    cmd = [sys.executable, str(ROOT / 'scripts' / 'generate_dance_item.py')]
    log(f"  Running: {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=False, timeout=86400)
    return r.returncode == 0


_LULLABY_EPISODES = {'sleepy_stars', 'ocean_night', 'moon_garden',
                     'sleepy_train', 'rain_window', 'forest_night'}

def dispatch_lullaby_long(row: dict) -> bool:
    """Render long-form lullaby sleep videos (1-2 hours). No text → all 3 channels.
    key = specific episode name OR meta-key (e.g. lullaby_nature) → run all."""
    key = row['key']
    cmd = [sys.executable, str(ROOT / 'scripts' / 'generate_lullaby.py')]
    if key in _LULLABY_EPISODES:
        cmd += ['--keys', key]
    # otherwise run all episodes (no --keys = process all)
    log(f"  Running: {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=False, timeout=86400)
    return r.returncode == 0


def dispatch_transform_block(row: dict) -> bool:
    """Render transform block SVG morphing videos."""
    key  = row['key']
    lang = row['lang']
    cmd  = [sys.executable, str(ROOT / 'scripts' / 'generate_transform_block.py'),
            '--key', key, '--lang', lang]
    log(f"  Running: {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=False, timeout=86400)
    return r.returncode == 0


def dispatch_dance_fruits_group(row: dict) -> bool:
    """Render group fruit/vegetable dance videos. No text → all 3 channels."""
    key = row['key']
    cmd = [sys.executable, str(ROOT / 'scripts' / 'generate_dance_fruits_group.py'), '--key', key]
    log(f"  Running: {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=False, timeout=86400)
    return r.returncode == 0


def dispatch_dance_fruits_2stage(row: dict) -> bool:
    """Render 2-stage fruit/vegetable dance. No text → all 3 channels."""
    key = row['key']
    cmd = [sys.executable, str(ROOT / 'scripts' / 'generate_dance_fruits_2stage.py'), '--key', key]
    log(f"  Running: {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=False, timeout=86400)
    return r.returncode == 0


def dispatch_learn_to_talk(row: dict) -> bool:
    """Render Learn to Talk speech development videos. All 3 channels."""
    key = row['key']
    cmd = [sys.executable, str(ROOT / 'scripts' / 'generate_learn_to_talk.py'), '--key', key]
    log(f"  Running: {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=False, timeout=86400)
    return r.returncode == 0


def dispatch_emotions_ocean(row: dict) -> bool:
    """Render emotions/ocean/transport/professions series. Kids channels only (EN+AR), NOT CNRelax.
    key='emotions_4series' → pilot mode: 1 video per series (4 pilots).
    key='e_happy' etc. → run that specific video only.
    """
    key = row['key']
    if key == 'emotions_4series':
        videos = ['e_happy', 'o_whale', 't_balloon', 'p_doctor']
    else:
        videos = [key]
    cmd = [sys.executable, str(ROOT / 'scripts' / 'generate_emotions_ocean.py'),
           '--videos'] + videos + ['--queues', 'en', 'ar']
    log(f"  Running: {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=False, timeout=86400)
    return r.returncode == 0


def dispatch_special_mechanics(row: dict) -> bool:
    """Render special mechanics game videos. Kids channels only (EN+AR), NOT CNRelax.
    key='special_mech_8series' → pilot: episode 7 (Hide & Seek).
    key='7' etc. → run that specific episode.
    """
    key = row['key']
    if key == 'special_mech_8series':
        videos = ['7']
    else:
        videos = [key]
    cmd = [sys.executable, str(ROOT / 'scripts' / 'generate_special_mechanics.py'),
           '--videos'] + videos + ['--queues', 'en', 'ar']
    log(f"  Running: {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=False, timeout=86400)
    return r.returncode == 0


def dispatch_shape_roundelay(row: dict) -> bool:
    """Render shape roundelay spinning/dancing shapes."""
    key  = row['key']
    lang = row['lang']
    cmd  = [sys.executable, str(ROOT / 'scripts' / 'generate_shape_roundelay.py'),
            '--key', key, '--lang', lang]
    log(f"  Running: {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=False, timeout=21600)
    return r.returncode == 0


def dispatch_ocd_vehicles(row: dict) -> bool:
    """Render One Concept Deep vehicles series — generates all 6 episodes."""
    cmd = [sys.executable, str(ROOT / 'scripts' / 'generate_ocd_vehicles.py')]
    log(f"  Running: {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=False, timeout=86400)
    return r.returncode == 0


def dispatch_construction_music(row: dict) -> bool:
    """Render construction + musical instruments series — generates all 6 episodes."""
    cmd = [sys.executable, str(ROOT / 'scripts' / 'generate_construction_music.py')]
    log(f"  Running: {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=False, timeout=86400)
    return r.returncode == 0


def dispatch_bubble_pop_song(row: dict) -> bool:
    """Render Bubble Pop song (Baby Shark formula) — 3 min + 20 min extended."""
    key  = row['key']
    lang = row['lang']
    cmd  = [sys.executable, str(ROOT / 'scripts' / 'generate_bubble_pop_song.py'),
            '--key', key, '--lang', lang]
    log(f"  Running: {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=False, timeout=21600)
    return r.returncode == 0


def dispatch_satisfying_3fmt(row: dict) -> bool:
    """Render satisfying/calming shape dance series — generates all 8 episodes."""
    cmd = [sys.executable, str(ROOT / 'scripts' / 'generate_satisfying_3fmt.py')]
    log(f"  Running: {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=False, timeout=86400)
    return r.returncode == 0


def dispatch_nature_calm(row: dict) -> bool:
    """Render calm nature shape series — generates all 6 episodes."""
    cmd = [sys.executable, str(ROOT / 'scripts' / 'generate_nature_calm.py')]
    log(f"  Running: {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=False, timeout=86400)
    return r.returncode == 0


def dispatch_interactive_coview(row: dict) -> bool:
    """Render interactive co-viewing scenarios (Category 3)."""
    key  = row['key']
    lang = row['lang']
    cmd  = [sys.executable, str(ROOT / 'scripts' / 'generate_interactive_coview.py'),
            '--key', key, '--lang', lang]
    log(f"  Running: {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=False, timeout=86400)
    return r.returncode == 0


def dispatch_emotional_values(row: dict) -> bool:
    """Render emotional values dance series — generates all 8 episodes."""
    cmd = [sys.executable, str(ROOT / 'scripts' / 'generate_emotional_values.py')]
    log(f"  Running: {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=False, timeout=86400)
    return r.returncode == 0


def dispatch_shorts_funnel(row: dict) -> bool:
    """Generate Shorts funnel clips from existing long videos (all queues)."""
    cmd = [sys.executable, str(ROOT / 'scripts' / 'generate_shorts_funnel.py'),
           '--queue', 'all', '--max-per-run', '5']
    log(f"  Running: {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=False, timeout=21600)
    return r.returncode == 0


def dispatch_wiggle_party(row: dict) -> bool:
    """Render Wiggle Party series — 3 separate renders per theme with different music."""
    key = row['key']  # e.g. 'animals', 'fruits', 'all'
    themes = list(__import__('scripts.generate_wiggle_party', fromlist=['THEMES']).THEMES.keys()) \
        if key == 'all' else key.split(',')
    cmd = [sys.executable, str(ROOT / 'scripts' / 'generate_wiggle_party.py'),
           '--themes'] + themes
    log(f"  Running: {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=False, timeout=86400)
    return r.returncode == 0


def dispatch_edu_entertain(row: dict) -> bool:
    """Render educational-entertainment scenarios (Category 1)."""
    key  = row['key']
    lang = row['lang']
    cmd  = [sys.executable, str(ROOT / 'scripts' / 'generate_edu_entertain.py'),
            '--key', key, '--lang', lang]
    log(f"  Running: {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=False, timeout=86400)
    return r.returncode == 0


def dispatch_character_dialogue(row: dict) -> bool:
    """Render CharacterDialogueLong — bear character speaks to child.
    Auto-generates sprites + TTS audio before rendering.
    key = episode key (e.g. emotions, colors_character, animals_character).
    lang = en | ar | id | both | all."""
    key   = row['key']
    lang  = row['lang']
    langs = expand_langs(lang)
    for lg in langs:
        cmd = [sys.executable, str(ROOT / 'scripts' / 'generate_character_dialogue_long.py'),
               '--episode', key, '--lang', lg]
        log(f"  Running: {' '.join(cmd)}")
        r = subprocess.run(cmd, capture_output=False, timeout=86400)
        if r.returncode != 0:
            log(f"  character_dialogue {key}/{lg} FAILED")
            return False
    return True


DISPATCHERS = {
    'color_learn':        dispatch_color_learn,
    'number_learn':       dispatch_number_learn,
    'shape_learn':        dispatch_shape_learn,
    'dance':              dispatch_dance,
    'nursery_ar':         dispatch_nursery_ar,
    'nursery_id':         dispatch_nursery_id,
    'sensory_loop':       dispatch_sensory_loop,
    'stars_bubbles':      dispatch_stars_bubbles,
    'dance_shape':        dispatch_dance_shape,
    'dance_pet':          dispatch_dance_pet,
    'dance_item':         dispatch_dance_item,
    'lullaby_long':       dispatch_lullaby_long,
    'transform_block':    dispatch_transform_block,
    'dance_fruits_group': dispatch_dance_fruits_group,
    'dance_fruits_2stage':dispatch_dance_fruits_2stage,
    'learn_to_talk':      dispatch_learn_to_talk,
    'emotions_ocean':     dispatch_emotions_ocean,
    'special_mechanics':  dispatch_special_mechanics,
    'shape_roundelay':    dispatch_shape_roundelay,
    'ocd_vehicles':       dispatch_ocd_vehicles,
    'construction_music': dispatch_construction_music,
    'bubble_pop_song':    dispatch_bubble_pop_song,
    'satisfying_3fmt':    dispatch_satisfying_3fmt,
    'nature_calm':        dispatch_nature_calm,
    'interactive_coview': dispatch_interactive_coview,
    'emotional_values':   dispatch_emotional_values,
    'shorts_funnel':      dispatch_shorts_funnel,
    'edu_entertain':      dispatch_edu_entertain,
    'character_dialogue': dispatch_character_dialogue,
    'wiggle_party':       dispatch_wiggle_party,
}


# ── Sheet I/O ─────────────────────────────────────────────────────────────────

def read_queue(svc) -> list[dict]:
    result = svc.values().get(
        spreadsheetId=SHEET_ID,
        range=f'{TAB}!A2:N200'
    ).execute()
    rows = result.get('values', [])
    out  = []
    for i, r in enumerate(rows):
        while len(r) < 13:
            r.append('')
        out.append({k: r[v] for k, v in COL.items()} | {'_row': i + 2})
    return out


def update_status(svc, row_num: int, status: str, notes: str = ''):
    updates = {
        COL['status']:  status,
        COL['updated']: now_iso(),
    }
    if notes:
        updates[COL['notes']] = notes

    for col_idx, value in updates.items():
        col_letter = chr(ord('A') + col_idx)
        svc.values().update(
            spreadsheetId=SHEET_ID,
            range=f'{TAB}!{col_letter}{row_num}',
            valueInputOption='RAW',
            body={'values': [[value]]}
        ).execute()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    try:
        import psutil  # noqa: F401
    except ImportError:
        log("Installing psutil...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'psutil', '-q',
                        '--break-system-packages'], check=True)

    log("=== Scenario Orchestrator ===")

    # Don't start if a render is already running
    if any_render_running():
        log("A render is already running — exiting.")
        return

    svc  = get_sheets_service()
    rows = read_queue(svc)

    # Filter pending, sort by priority (lower = higher priority)
    pending = [r for r in rows if r['status'].strip().lower() == 'pending']
    pending.sort(key=lambda r: (int(r['priority']) if r['priority'].isdigit() else 99))

    if not pending:
        log("No pending scenarios.")
        return

    row  = pending[0]
    vtype = row['type'].strip().lower()

    log(f"Processing: [{row['id']}] {vtype} / {row['key']} / lang={row['lang']} / priority={row['priority']}")

    # If there's a Google Doc link — read it and log for context
    if row.get('doc_url', '').strip():
        log(f"  Reading scenario doc: {row['doc_url'][:60]}…")
        doc_text = read_google_doc(row['doc_url'])
        if doc_text:
            log(f"  Doc content ({len(doc_text)} chars): {doc_text[:200].strip()}")
        else:
            log("  Doc is empty or not accessible — using params column only")

    dispatcher = DISPATCHERS.get(vtype)
    if not dispatcher:
        msg = f"Unknown type: {vtype}"
        log(f"  ERROR: {msg}")
        update_status(svc, row['_row'], 'failed', msg)
        return

    # Mark as rendering
    update_status(svc, row['_row'], 'rendering')
    tg(f"🎬 <b>Kids Channel</b>\nНачинаю рендер: <b>{row['key']}</b> ({vtype}, {row['lang']})\nПриоритет: {row['priority']}")

    try:
        success = dispatcher(row)
    except subprocess.TimeoutExpired:
        success = False
        log("  TIMEOUT after 6 hours")
    except Exception as e:
        success = False
        log(f"  Exception: {e}")

    if success:
        update_status(svc, row['_row'], 'rendered', f"Done {now_iso()}")
        tg(f"✅ <b>Kids Channel</b>\nРендер завершён: <b>{row['key']}</b> ({vtype})\nВидео в очереди на публикацию.")
        log(f"  ✓ Done — {row['key']} queued for publication.")
        # Thumbnail sweep — catches videos from scripts that don't generate thumbnails inline
        log("  Running thumbnail sweep for all queues...")
        thumbs_script = ROOT / 'scripts' / 'generate_ai_thumbs.py'
        for q in ('en', 'ar', 'id'):
            r = subprocess.run(
                [sys.executable, str(thumbs_script), '--queue', q, '--backend', 'together'],
                capture_output=False, timeout=3600,
            )
            if r.returncode != 0:
                log(f"  thumbs {q}: exit {r.returncode} (non-fatal)")
        log("  Thumbnail sweep done.")
    else:
        update_status(svc, row['_row'], 'failed', f"Failed {now_iso()}")
        tg(f"❌ <b>Kids Channel</b>\nРендер провалился: <b>{row['key']}</b> ({vtype})\nПроверь: tail -f logs/orchestrator.log")
        log(f"  ✗ Failed — check logs.")


if __name__ == '__main__':
    main()
