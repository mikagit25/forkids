#!/usr/bin/env python3
"""
Scenario Orchestrator — reads Google Sheets queue and dispatches video renders.

Sheet: https://docs.google.com/spreadsheets/d/1MAHh_LxESZCd0sWOx0qAjSWWIElR79oTfo-XiPbJc7o
Tab: Queue
Columns: id | type | lang | key | params | priority | status | youtube_id_en | youtube_id_ar | youtube_id_id | notes | created | updated

Statuses: pending → rendering → rendered → failed
lang values:
  en   — English only   → output/queue/
  ar   — Arabic only    → output/queue_ar/
  id   — Indonesian only → output/queue_id/
  both — EN + AR         → 2 renders (videos WITH voice/text)
  all  — EN + AR + ID    → 3 renders or 1 render → 3 queues (videos WITHOUT text/voice)

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

# Column indices (0-based)
COL = {
    'id': 0, 'type': 1, 'lang': 2, 'key': 3, 'doc_url': 4, 'params': 5,
    'priority': 6, 'status': 7, 'youtube_id_en': 8, 'youtube_id_ar': 9,
    'notes': 10, 'created': 11, 'updated': 12,
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
    procs = ['generate_number_learn_long.py', 'generate_color_learn_long.py',
             'generate_shape_learn.py', 'run_renders_sequential.sh', 'scenario_orchestrator.py']
    import psutil
    self_pid = os.getpid()
    for proc in psutil.process_iter(['pid', 'cmdline']):
        try:
            cmdline = ' '.join(proc.info['cmdline'] or [])
            if proc.info['pid'] == self_pid:
                continue
            for p in procs:
                if p in cmdline:
                    return True
        except Exception:
            pass
    return False


# ── Dispatchers ───────────────────────────────────────────────────────────────

LANG_QUEUE = {
    'en':   ROOT / 'output' / 'queue',
    'ar':   ROOT / 'output' / 'queue_ar',
    'id':   ROOT / 'output' / 'queue_id',
    'both': ROOT / 'output' / 'queue',   # EN+AR — videos WITH voice/text (2 renders)
    'all':  ROOT / 'output' / 'queue',   # EN+AR+ID — videos WITHOUT text (shape_learn: 1 render → 3 queues)
}

def expand_langs(lang: str) -> list[str]:
    """Expand lang shorthand to list of language codes."""
    if lang == 'both':
        return ['en', 'ar']
    if lang == 'all':
        return ['en', 'ar', 'id']
    return [lang]


def dispatch_color_learn(row: dict) -> bool:
    """Render color_learn video(s). lang=both → EN+AR, lang=all → EN+AR+ID."""
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
    """Render number_learn video(s). lang=both → EN+AR, lang=all → EN+AR+ID."""
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
    key = row['key']            # animals | fruits | vegetables
    p   = parse_params(row['params'])
    dur = p.get('duration', '30')
    script_map = {
        'animals':    'generate_dance_script.py',
        'fruits':     'generate_fruit_dance_script.py',
        'vegetables': 'generate_vegetable_dance_script.py',
    }
    gen_script = script_map.get(key)
    if not gen_script:
        log(f"  Unknown dance theme: {key}")
        return False

    date_str = datetime.now().strftime('%Y%m%d')
    out_mp4  = ROOT / 'output' / 'queue' / f'dance_{key}_{date_str}.mp4'
    script_yaml = ROOT / 'config' / 'scripts' / f'dance_{key}.yaml'

    steps = [
        [sys.executable, str(ROOT / 'scripts' / gen_script), '--duration', dur],
        [sys.executable, str(ROOT / 'scripts' / 'generate_video.py'),
         '--theme', key, '--duration', dur,
         '--script', str(script_yaml), '--output', str(out_mp4)],
    ]
    for cmd in steps:
        log(f"  Running: {' '.join(cmd)}")
        r = subprocess.run(cmd, capture_output=False, timeout=21600)
        if r.returncode != 0:
            log(f"  dance {key} step FAILED")
            return False
    return True


DISPATCHERS = {
    'color_learn':  dispatch_color_learn,
    'number_learn': dispatch_number_learn,
    'shape_learn':  dispatch_shape_learn,
    'dance':        dispatch_dance,
}


# ── Sheet I/O ─────────────────────────────────────────────────────────────────

def read_queue(svc) -> list[dict]:
    result = svc.values().get(
        spreadsheetId=SHEET_ID,
        range=f'{TAB}!A2:M200'
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
    else:
        update_status(svc, row['_row'], 'failed', f"Failed {now_iso()}")
        tg(f"❌ <b>Kids Channel</b>\nРендер провалился: <b>{row['key']}</b> ({vtype})\nПроверь: tail -f logs/orchestrator.log")
        log(f"  ✗ Failed — check logs.")


if __name__ == '__main__':
    main()
