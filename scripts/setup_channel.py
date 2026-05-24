#!/usr/bin/env python3
"""
Apply channel branding to YouTube channel via API.

Sets:
  - Channel description & keywords (channels.update)
  - Banner image                   (channelBanners.insert)
  - Profile picture (icon)         (cannot be set via API — must be done manually)

Usage:
    python3 setup_channel.py --all
    python3 setup_channel.py --description
    python3 setup_channel.py --banner
    python3 setup_channel.py --show        # show current channel info
"""

import argparse
import pickle
import sys
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT / "scripts"))
from upload_youtube import get_youtube_service, load_config

from googleapiclient.http import MediaFileUpload

METADATA_PATH = ROOT / "config" / "channel_metadata.yaml"
BANNER_PATH   = ROOT / "output" / "channel" / "banner.png"
ICON_PATH     = ROOT / "output" / "channel" / "icon.png"


def load_metadata() -> dict:
    with open(METADATA_PATH) as f:
        return yaml.safe_load(f)


def show_channel(youtube):
    res = youtube.channels().list(
        part="snippet,brandingSettings,statistics", mine=True
    ).execute()
    for item in res.get("items", []):
        s  = item["snippet"]
        st = item["statistics"]
        bs = item.get("brandingSettings", {}).get("channel", {})
        print(f"\n{'='*60}")
        print(f"  Channel:  {s['title']}")
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
    kw   = ch["keywords"].replace("\n", " ").strip()

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
                    "description": desc,
                    "keywords":    kw,
                    "country":     ch.get("country", "US"),
                }
            }
        }
    ).execute()
    print(f"  ✓ Description ({len(desc)} chars) & keywords updated.")


def upload_banner(youtube):
    if not BANNER_PATH.exists():
        print(f"  Banner not found: {BANNER_PATH}")
        print("  Run: python3 scripts/generate_channel_art.py")
        return

    print(f"  Uploading banner: {BANNER_PATH.name}  "
          f"({BANNER_PATH.stat().st_size // 1024} KB)")

    # Step 1: upload banner image
    media = MediaFileUpload(str(BANNER_PATH), mimetype="image/png", resumable=True)
    res = youtube.channelBanners().insert(media_body=media).execute()
    banner_url = res.get("url", "")

    if not banner_url:
        print(f"  WARNING: banner upload returned no URL: {res}")
        return

    print(f"  Banner URL: {banner_url[:80]}")

    # Step 2: apply banner to channel (title required in body)
    ch_res = youtube.channels().list(part="id,snippet", mine=True).execute()
    ch = ch_res["items"][0]
    channel_id = ch["id"]
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


def _my_channel_id(youtube) -> str:
    res = youtube.channels().list(part="id", mine=True).execute()
    items = res.get("items", [])
    if not items:
        raise RuntimeError("No channel found for this account.")
    return items[0]["id"]


def print_manual_steps():
    print("""
  ─────────────────────────────────────────────────────
  MANUAL STEPS (cannot be done via API):

  1. Profile picture (icon):
     YouTube Studio → Customisation → Branding
     Upload: output/channel/icon.png  (800×800 px)

  2. Channel handle:
     YouTube Studio → Customisation → Basic Info
     Set handle to: @HappyBearKids

  3. Channel trailer:
     YouTube Studio → Customisation → Layout
     Add Featured video (first uploaded video)

  4. Sections layout:
     Add sections: Latest Videos, Popular Videos
  ─────────────────────────────────────────────────────
""")


def main():
    parser = argparse.ArgumentParser(description="Setup YouTube channel branding")
    parser.add_argument("--all",         action="store_true", help="Apply everything via API")
    parser.add_argument("--description", action="store_true", help="Update description & keywords")
    parser.add_argument("--banner",      action="store_true", help="Upload and set banner")
    parser.add_argument("--show",        action="store_true", help="Show current channel info")
    args = parser.parse_args()

    config   = load_config()
    meta     = load_metadata()
    youtube  = get_youtube_service(config)

    if args.show or not any([args.all, args.description, args.banner]):
        show_channel(youtube)
        print_manual_steps()
        return

    if args.all or args.description:
        update_description(youtube, meta)

    if args.all or args.banner:
        upload_banner(youtube)

    show_channel(youtube)
    print_manual_steps()


if __name__ == "__main__":
    main()
