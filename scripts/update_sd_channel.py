#!/usr/bin/env python3
"""Update Sacred Drift YouTube channel description and keywords via API."""
import json, sys, logging
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))

import yaml
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

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

def main():
    dry_run = '--dry-run' in sys.argv
    meta = yaml.safe_load((ROOT / 'sacred_drift/config/channel_metadata_sd.yaml').read_text())
    ch = meta['channel']

    description = ch['description'].strip()
    # YouTube keyword format: space-separated, multi-word phrases in quotes
    # API limit: 500 chars. Convert from comma-separated to YouTube format.
    keywords_raw = ch['keywords'].strip().replace('\n', ' ')
    kw_list = [k.strip() for k in keywords_raw.split(',') if k.strip()]
    formatted_kws = []
    total = 0
    for kw in kw_list:
        token = f'"{kw}"' if ' ' in kw else kw
        if total + len(token) + 1 > 500:
            break
        formatted_kws.append(token)
        total += len(token) + 1
    keywords = ' '.join(formatted_kws)

    print("=== Description preview ===")
    print(description[:300] + "...")
    print()
    print(f"=== Keywords ({len(keywords)} chars, limit 500) ===")
    print(keywords)

    if dry_run:
        log.info("[DRY RUN] Would update channel description and keywords.")
        return

    creds = load_creds()
    yt = build('youtube', 'v3', credentials=creds)

    # Fetch current brandingSettings
    resp = yt.channels().list(part='brandingSettings', mine=True).execute()
    if not resp.get('items'):
        log.error("No channel found for this token")
        return
    item = resp['items'][0]
    channel_id = item['id']

    # brandingSettings.channel holds description AND keywords for owned channels
    # Keep full branding object (including image/banner) — YouTube rejects if image is missing
    branding = item.get('brandingSettings', {})
    if 'channel' not in branding:
        branding['channel'] = {}
    # Preserve title/defaultLanguage/country, only set what we control
    branding['channel']['keywords']    = keywords
    branding['channel']['description'] = description

    log.info(f"Updating channel: {channel_id}")
    # YouTube API rejects description+keywords in the same call — do two calls
    # Call 1: description
    branding_desc = {'channel': {**branding['channel'], 'description': description},
                     'image': branding.get('image', {})}
    yt.channels().update(
        part='brandingSettings',
        body={'id': channel_id, 'brandingSettings': branding_desc}
    ).execute()
    log.info("✓ Description updated")

    # Call 2: keywords (re-fetch to pick up description update)
    resp2 = yt.channels().list(part='brandingSettings', mine=True).execute()
    branding2 = resp2['items'][0].get('brandingSettings', {})
    branding_kw = {'channel': {**branding2.get('channel', {}), 'keywords': keywords},
                   'image': branding2.get('image', {})}
    yt.channels().update(
        part='brandingSettings',
        body={'id': channel_id, 'brandingSettings': branding_kw}
    ).execute()
    log.info("✓ Keywords updated")
    log.info("✓ Channel fully updated!")
    log.info("Note: Channel NAME must be changed manually in YouTube Studio (API cannot change it)")

if __name__ == '__main__':
    main()
