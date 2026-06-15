#!/usr/bin/env python3
"""
Apply channel branding to YouTube channel via API.

Sets:
  - Channel description & keywords (channels.update)
  - Banner image                   (channelBanners.insert)
  - Profile picture (icon)         (cannot be set via API — must be done manually)

Usage:
    python3 scripts/setup_channel.py --channel en
    python3 scripts/setup_channel.py --channel ar
    python3 scripts/setup_channel.py --channel id
    python3 scripts/setup_channel.py --channel ar --description  # description only
    python3 scripts/setup_channel.py --channel ar --banner       # banner only
    python3 scripts/setup_channel.py --channel ar --show         # show current info
    python3 scripts/setup_channel.py --all                       # all 3 channels
"""

import argparse
import pickle
import subprocess
import sys
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CHANNEL_META = {
    "en": ROOT / "config" / "channel_metadata.yaml",
    "ar": ROOT / "config" / "channel_metadata_ar.yaml",
    "id": ROOT / "config" / "channel_metadata_id.yaml",
}

CHANNEL_CREDS = {
    "en": ROOT / "credentials" / "youtube_token.json",
    "ar": ROOT / "credentials" / "youtube_token_ar.json",
    "id": ROOT / "credentials" / "youtube_token_id.json",
}

CHANNEL_BANNER = {
    "en": ROOT / "output" / "channel" / "banner.png",
    "ar": ROOT / "output" / "channel" / "banner_ar.png",
    "id": ROOT / "output" / "channel" / "banner_id.png",
}

from googleapiclient.http import MediaFileUpload


def load_metadata(channel: str) -> dict:
    path = CHANNEL_META[channel]
    with open(path) as f:
        return yaml.safe_load(f)


def get_youtube_service(channel: str):
    import json as _json, datetime as _dt
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    SCOPES = [
        "https://www.googleapis.com/auth/youtube",
        "https://www.googleapis.com/auth/youtube.force-ssl",
    ]

    json_path = CHANNEL_CREDS[channel]
    if not json_path.exists():
        print(f"  No token for [{channel}]. Run: python3 scripts/reauth_youtube.py --channel {channel}")
        sys.exit(1)

    t = _json.loads(json_path.read_text())
    creds = Credentials(
        token=t.get("access_token"),
        refresh_token=t["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=t["client_id"],
        client_secret=t["client_secret"],
        scopes=SCOPES,
    )
    if t.get("expires_at"):
        creds.expiry = _dt.datetime.utcfromtimestamp(float(t["expires_at"]))
    if not creds.valid and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        t["access_token"] = creds.token
        t["expires_at"] = creds.expiry.timestamp() if creds.expiry else 0
        json_path.write_text(_json.dumps(t, indent=2))

    return build("youtube", "v3", credentials=creds)


def show_channel(youtube, channel: str):
    res = youtube.channels().list(
        part="snippet,brandingSettings,statistics", mine=True
    ).execute()
    for item in res.get("items", []):
        s  = item["snippet"]
        st = item["statistics"]
        bs = item.get("brandingSettings", {}).get("channel", {})
        print(f"\n{'='*60}")
        print(f"  Channel [{channel.upper()}]: {s['title']}")
        print(f"  ID:       {item['id']}")
        print(f"  Subs:     {st.get('subscriberCount', 'hidden')}")
        print(f"  Videos:   {st.get('videoCount', '?')}")
        print(f"  Country:  {bs.get('country', '—')}")
        print(f"  Keywords: {bs.get('keywords', '—')[:80]}")
        print(f"  Desc:     {s.get('description','—')[:120]}...")
        print(f"{'='*60}\n")


def update_description(youtube, meta: dict):
    ch   = meta["channel"]
    desc = ch["description"].strip()
    kw   = ch.get("keywords", "").replace("\n", " ").strip()

    print(f"  Updating description ({len(desc)} chars) and keywords…")

    ch_res = youtube.channels().list(part="id,snippet", mine=True).execute()
    ch_item = ch_res["items"][0]
    channel_id    = ch_item["id"]
    channel_title = ch_item["snippet"]["title"]

    youtube.channels().update(
        part="brandingSettings",
        body={
            "id": channel_id,
            "brandingSettings": {
                "channel": {
                    "title":       channel_title,
                    "description": desc[:1000],
                    "keywords":    kw[:500],
                    "country":     ch.get("country", "US"),
                }
            }
        }
    ).execute()
    print(f"  ✓ Description ({len(desc)} chars) & keywords updated.")


def upload_banner(youtube, channel: str):
    banner_path = CHANNEL_BANNER[channel]
    if not banner_path.exists():
        print(f"  Banner not found: {banner_path}")
        print(f"  Run: python3 scripts/generate_channel_art.py --channel {channel}")
        return

    print(f"  Uploading banner: {banner_path.name}  "
          f"({banner_path.stat().st_size // 1024} KB)")

    media = MediaFileUpload(str(banner_path), mimetype="image/png", resumable=True)
    res = youtube.channelBanners().insert(media_body=media).execute()
    banner_url = res.get("url", "")

    if not banner_url:
        print(f"  WARNING: banner upload returned no URL: {res}")
        return

    print(f"  Banner URL: {banner_url[:80]}")

    ch_res = youtube.channels().list(part="id,snippet", mine=True).execute()
    ch = ch_res["items"][0]
    channel_id    = ch["id"]
    channel_title = ch["snippet"]["title"]

    youtube.channels().update(
        part="brandingSettings",
        body={
            "id": channel_id,
            "brandingSettings": {
                "channel": {"title": channel_title},
                "image":   {"bannerExternalUrl": banner_url}
            }
        }
    ).execute()
    print(f"  ✓ Banner applied to channel: {channel_title} ({channel_id})")


def print_manual_steps(channel: str):
    handles = {"en": "@HappyBearKids1", "ar": "@happybearkidsar", "id": "@happybearkidsin"}
    print(f"""
  ─────────────────────────────────────────────────────
  MANUAL STEPS for [{channel.upper()}] (cannot be done via API):

  1. Profile picture:
     YouTube Studio → Customisation → Branding → Picture
     Upload: output/channel/icon.png  (800×800 px)

  2. Channel handle should be: {handles.get(channel, '')}
     YouTube Studio → Customisation → Basic Info

  3. Channel trailer:
     YouTube Studio → Customisation → Layout → Add Featured video

  4. Add sections: Latest Videos, Popular Videos
  ─────────────────────────────────────────────────────
""")


def setup_one_channel(channel: str, do_desc: bool, do_banner: bool, do_show: bool):
    print(f"\n{'='*55}")
    print(f"  Setting up channel: {channel.upper()}")
    print(f"{'='*55}")

    meta    = load_metadata(channel)
    youtube = get_youtube_service(channel)

    if do_show:
        show_channel(youtube, channel)

    if do_desc:
        update_description(youtube, meta)

    if do_banner:
        # Auto-generate banner if missing
        banner_path = CHANNEL_BANNER[channel]
        if not banner_path.exists():
            print(f"  Banner not found — generating via generate_channel_art.py…")
            subprocess.run([
                sys.executable, str(ROOT / "scripts" / "generate_channel_art.py"),
                "--channel", channel
            ], check=True)
        upload_banner(youtube, channel)

    print_manual_steps(channel)


def main():
    parser = argparse.ArgumentParser(description="Setup YouTube channel branding")
    parser.add_argument("--channel",     choices=["en", "ar", "id"], default=None,
                        help="Target channel (en/ar/id)")
    parser.add_argument("--all",         action="store_true", help="Apply to all 3 channels")
    parser.add_argument("--description", action="store_true", help="Update description & keywords only")
    parser.add_argument("--banner",      action="store_true", help="Upload and set banner only")
    parser.add_argument("--show",        action="store_true", help="Show current channel info")
    args = parser.parse_args()

    if not args.channel and not args.all:
        parser.print_help()
        return

    do_all    = not args.description and not args.banner and not args.show
    do_desc   = do_all or args.description
    do_banner = do_all or args.banner
    do_show   = args.show

    channels = ["en", "ar", "id"] if args.all else [args.channel]
    for ch in channels:
        setup_one_channel(ch, do_desc=do_desc, do_banner=do_banner, do_show=do_show)

    print("\n✓ Done.\n")


if __name__ == "__main__":
    main()
