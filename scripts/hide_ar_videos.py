#!/usr/bin/env python3
"""Make all AR channel videos private — Sacred Drift rebrand.

Tracks progress in /tmp/hide_ar_progress.json to resume after quota reset.
"""
import json, sys, time, logging
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
PROGRESS_FILE = Path('/tmp/hide_ar_progress.json')

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

def load_creds():
    data = json.loads((ROOT / 'credentials/youtube_token_ar.json').read_text())
    creds = Credentials(
        token=data.get('access_token'),
        refresh_token=data.get('refresh_token'),
        token_uri=data.get('token_uri', 'https://oauth2.googleapis.com/token'),
        client_id=data.get('client_id'),
        client_secret=data.get('client_secret'),
    )
    creds.refresh(Request())
    return creds

def load_progress() -> dict:
    if PROGRESS_FILE.exists():
        return json.loads(PROGRESS_FILE.read_text())
    return {'hidden': [], 'skipped': []}

def save_progress(progress: dict):
    PROGRESS_FILE.write_text(json.dumps(progress, indent=2))

def main():
    dry_run = '--dry-run' in sys.argv
    reset   = '--reset' in sys.argv

    if reset and PROGRESS_FILE.exists():
        PROGRESS_FILE.unlink()
        log.info("Progress reset.")

    creds = load_creds()
    yt = build('youtube', 'v3', credentials=creds)
    progress = load_progress()
    done_ids = set(progress['hidden']) | set(progress['skipped'])

    # Get all channel video IDs (uses search quota — 100 units/call)
    video_ids = []
    page_token = None
    while True:
        kw = dict(part='id', forMine=True, type='video', maxResults=50)
        if page_token:
            kw['pageToken'] = page_token
        resp = yt.search().list(**kw).execute()
        for item in resp.get('items', []):
            video_ids.append(item['id']['videoId'])
        page_token = resp.get('nextPageToken')
        if not page_token:
            break

    log.info(f"Found {len(video_ids)} videos on AR channel")
    to_process = [v for v in video_ids if v not in done_ids]
    log.info(f"Remaining: {len(to_process)} (already done: {len(done_ids)})")

    hidden = 0
    for i in range(0, len(to_process), 50):
        batch = to_process[i:i+50]
        try:
            details = yt.videos().list(part='status,snippet', id=','.join(batch)).execute()
        except HttpError as e:
            if 'quotaExceeded' in str(e):
                log.error(f"Quota exceeded after hiding {hidden}. Resume tomorrow.")
                save_progress(progress)
                sys.exit(1)
            raise

        for item in details.get('items', []):
            vid_id = item['id']
            status = item['status']['privacyStatus']
            title  = item['snippet']['title'][:60]
            if status == 'private':
                log.info(f"  ALREADY PRIVATE: {vid_id} — {title}")
                progress['skipped'].append(vid_id)
                continue
            if dry_run:
                log.info(f"  [DRY RUN] Would hide: {vid_id} — {title}")
            else:
                try:
                    yt.videos().update(
                        part='status',
                        body={'id': vid_id, 'status': {'privacyStatus': 'private'}}
                    ).execute()
                    log.info(f"  ✓ HIDDEN: {vid_id} — {title}")
                    progress['hidden'].append(vid_id)
                    hidden += 1
                    save_progress(progress)
                    time.sleep(0.3)
                except HttpError as e:
                    if 'quotaExceeded' in str(e):
                        log.error(f"Quota exceeded after hiding {hidden}. Resume tomorrow.")
                        save_progress(progress)
                        sys.exit(1)
                    log.error(f"  Error on {vid_id}: {e}")

    log.info(f"Done. Hidden this run: {hidden} / {len(to_process)} remaining")
    log.info(f"Total hidden: {len(progress['hidden'])} | Skipped (already private): {len(progress['skipped'])}")

if __name__ == '__main__':
    main()
