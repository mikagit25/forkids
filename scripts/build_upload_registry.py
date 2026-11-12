#!/usr/bin/env python3
"""
Build data/upload_registry.json from YouTube API.

Fetches all uploaded videos (including private) for each channel,
computes sha256 for any mp4 found locally, and writes the registry.

Usage:
    python3 scripts/build_upload_registry.py              # all channels
    python3 scripts/build_upload_registry.py --channel en # one channel
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CHANNELS = {
    "en": {
        "token":      ROOT / "credentials" / "youtube_token.json",
        "channel_id": "UCIOerrKr02oTAAk2_oOg0Xg",
        "queue":      ROOT / "output" / "queue",
        "uploaded":   ROOT / "uploaded",
    },
    "sd": {
        "token":      ROOT / "credentials" / "youtube_token_ar.json",
        "channel_id": "UCTAAc0Ih4PpwY9agi2tT8Gg",
        "queue":      ROOT / "sacred_drift" / "output" / "queue",
        "uploaded":   ROOT / "uploaded",
    },
}

REGISTRY_PATH = ROOT / "data" / "upload_registry.json"


def _yt_client(token_path: Path):
    import json as _j
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    raw = _j.loads(token_path.read_text())
    scopes = ["https://www.googleapis.com/auth/youtube",
              "https://www.googleapis.com/auth/youtube.upload",
              "https://www.googleapis.com/auth/youtube.force-ssl"]
    creds = Credentials(
        token=raw.get("access_token"),
        refresh_token=raw["refresh_token"],
        token_uri=raw.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=raw["client_id"],
        client_secret=raw["client_secret"],
        scopes=scopes,
    )
    if not creds.valid:
        creds.refresh(Request())
        raw["access_token"] = creds.token
        token_path.write_text(_j.dumps(raw, indent=2))
    return build("youtube", "v3", credentials=creds)


def _uploads_playlist(yt, channel_id: str) -> str:
    r = yt.channels().list(part="contentDetails", id=channel_id).execute()
    return r["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]


def _fetch_all_videos(yt, playlist_id: str) -> list[dict]:
    videos, token = [], None
    while True:
        r = yt.playlistItems().list(
            part="snippet,contentDetails", playlistId=playlist_id,
            maxResults=50, pageToken=token,
        ).execute()
        for item in r.get("items", []):
            sn = item["snippet"]
            videos.append({
                "video_id":    item["contentDetails"]["videoId"],
                "title":       sn["title"],
                "published_at": sn["publishedAt"],
                "privacy":     sn.get("status", {}).get("privacyStatus", "unknown"),
            })
        token = r.get("nextPageToken")
        if not token:
            break
    return videos


def _get_privacy(yt, video_ids: list[str]) -> dict[str, str]:
    """Fetch privacy status for a batch of video IDs."""
    result = {}
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        r = yt.videos().list(part="status", id=",".join(batch)).execute()
        for item in r.get("items", []):
            result[item["id"]] = item["status"]["privacyStatus"]
    return result


def sha256_file(path: Path) -> str | None:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def normalize_title(title: str) -> str:
    """Remove emojis, extra spaces, punctuation for fuzzy matching."""
    t = re.sub(r"[^\w\s]", " ", title)
    t = re.sub(r"\s+", " ", t).strip().lower()
    return t


def _find_local_mp4(stem_hint: str, search_dirs: list[Path]) -> Path | None:
    for d in search_dirs:
        if not d.exists():
            continue
        for f in d.glob("*.mp4"):
            if stem_hint.lower() in f.stem.lower() or f.stem.lower() in stem_hint.lower():
                return f
    return None


def build_registry(channels: list[str]) -> dict:
    registry_path = REGISTRY_PATH
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    existing = json.loads(registry_path.read_text()) if registry_path.exists() else {}

    for ch in channels:
        cfg = CHANNELS[ch]
        if not cfg["token"].exists():
            print(f"[{ch}] token not found, skipping")
            continue
        print(f"\n[{ch}] fetching from YouTube API...")
        yt = _yt_client(cfg["token"])
        playlist_id = _uploads_playlist(yt, cfg["channel_id"])
        videos = _fetch_all_videos(yt, playlist_id)
        print(f"[{ch}] {len(videos)} videos fetched")

        # Enrich with privacy status
        ids = [v["video_id"] for v in videos]
        privacy = _get_privacy(yt, ids)
        for v in videos:
            v["privacy"] = privacy.get(v["video_id"], "unknown")
            v["title_norm"] = normalize_title(v["title"])
            v["sha256"] = None

        # Try to find local sha256 for any file still on disk
        search_dirs = [cfg["queue"], cfg["uploaded"]]
        for v in videos:
            local = _find_local_mp4(v["video_id"], search_dirs)
            if local:
                v["sha256"] = sha256_file(local)

        existing[ch] = videos
        print(f"[{ch}] registry updated: {len(videos)} entries")

    registry_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False))
    print(f"\nRegistry saved: {registry_path}")
    return existing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", choices=list(CHANNELS), default=None,
                    help="Build for one channel only (default: all)")
    a = ap.parse_args()
    channels = [a.channel] if a.channel else list(CHANNELS)
    build_registry(channels)


if __name__ == "__main__":
    main()
