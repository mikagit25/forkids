#!/usr/bin/env python3
"""
sync_youtube_ids.py — fetch all published videos from a channel and match
youtube_id into local meta YAML files by title similarity.

After syncing, optionally runs localize_video.py --queue --channel <ch>.

Usage:
    python3 scripts/sync_youtube_ids.py --channel id            # Calm Classics
    python3 scripts/sync_youtube_ids.py --channel en            # EN kids
    python3 scripts/sync_youtube_ids.py --channel id --localize # sync + localize
    python3 scripts/sync_youtube_ids.py --channel id --dry-run  # show matches only
"""
import argparse
import json
import subprocess
import sys
import unicodedata
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

CHANNEL_CONFIG = {
    "en": {
        "json":      ROOT / "credentials" / "youtube_token.json",
        "pickle":    ROOT / "credentials" / "token.pickle",
        "queue_dir": ROOT / "output" / "queue",
        "reauth":    "--channel en",
    },
    "id": {
        "json":      ROOT / "credentials" / "youtube_token_id.json",
        "pickle":    ROOT / "credentials" / "token_id.pickle",
        "queue_dir": ROOT / "output" / "queue_id",
        "reauth":    "--channel id",
    },
}


def _normalize(s: str) -> str:
    s = unicodedata.normalize("NFC", s).lower().strip()
    for ch in "🌙✨🎵🔔▶":
        s = s.replace(ch, "")
    return " ".join(s.split())


def _get_youtube_service(channel: str):
    import pickle, datetime as _dt
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    SCOPES = [
        "https://www.googleapis.com/auth/youtube",
        "https://www.googleapis.com/auth/youtube.force-ssl",
    ]
    cfg = CHANNEL_CONFIG[channel]
    json_path   = cfg["json"]
    pickle_path = cfg["pickle"]

    creds = None
    if json_path.exists():
        try:
            with open(json_path) as f:
                t = json.load(f)
            if t.get("refresh_token"):
                creds = Credentials(
                    token=t.get("access_token"),
                    refresh_token=t["refresh_token"],
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=t["client_id"],
                    client_secret=t["client_secret"],
                    scopes=SCOPES,
                )
                expires_at = t.get("expires_at")
                if expires_at:
                    creds.expiry = _dt.datetime.utcfromtimestamp(float(expires_at))
        except Exception as e:
            print(f"  Warning: JSON token load failed: {e}")
            creds = None

    if creds is None and pickle_path.exists():
        with open(pickle_path, "rb") as f:
            creds = pickle.load(f)

    if not creds:
        raise RuntimeError(
            f"No token for channel '{channel}'. Run:\n"
            f"  python3 scripts/reauth_youtube.py {cfg['reauth']}"
        )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    return build("youtube", "v3", credentials=creds)


def fetch_channel_videos(channel: str) -> list[dict]:
    """Return all videos on channel as [{id, title, published_at}]."""
    yt = _get_youtube_service(channel)

    # Get uploads playlist ID (UU... = UC... with UC→UU)
    ch_resp = yt.channels().list(mine=True, part="contentDetails").execute()
    uploads_playlist = ch_resp["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    print(f"  Uploads playlist: {uploads_playlist}")

    videos = []
    page_token = None
    while True:
        kwargs = dict(
            playlistId=uploads_playlist,
            part="snippet",
            maxResults=50,
        )
        if page_token:
            kwargs["pageToken"] = page_token
        resp = yt.playlistItems().list(**kwargs).execute()
        for item in resp.get("items", []):
            sn = item["snippet"]
            vid_id = sn["resourceId"]["videoId"]
            title  = sn.get("title", "")
            pub    = sn.get("publishedAt", "")
            videos.append({"id": vid_id, "title": title, "published_at": pub})
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    print(f"  Found {len(videos)} videos on channel")
    return videos


def load_metas(queue_dir: Path) -> list[tuple[Path, dict]]:
    result = []
    for p in sorted(queue_dir.glob("meta_*.yaml")):
        try:
            with open(p) as f:
                data = yaml.safe_load(f) or {}
            result.append((p, data))
        except Exception:
            pass
    return result


def _title_key(title: str) -> str:
    """Extract the unique theme part of a title (before first '|')."""
    part = title.split("|")[0]
    return _normalize(part)


# Words that appear in Indonesian kids video titles — used to skip non-CC content
_INDONESIAN_MARKERS = {
    "indonesia", "bayi", "menit", "belajar", "tarian", "tari", "bentuk",
    "warna", "hewan", "angka", "goyang", "sayuran", "buah", "sensori",
    "animasi", "pesta", "rondo", "bayangan", "gelembung",
}


def _is_indonesian(title: str) -> bool:
    words = set(title.lower().split())
    return bool(words & _INDONESIAN_MARKERS)


def _keywords(title: str) -> set[str]:
    """Extract meaningful keywords from a title (skip stopwords and numbers)."""
    stopwords = {
        "for", "the", "a", "an", "and", "or", "of", "in", "to", "at",
        "is", "it", "on", "with", "by", "from", "sleep", "music", "hour",
        "hours", "classical", "night", "relax", "calm", "classics", "study",
        "1", "2", "3", "4", "5", "6", "7", "8", "focus",
    }
    words = set(_title_key(title).split())
    return words - stopwords


def _duration_label(title: str) -> str:
    """Extract duration marker from title: 1h/3h/8h/short."""
    t = title.lower()
    if "8 hour" in t: return "8h"
    if "3 hour" in t: return "3h"
    if "2 hour" in t: return "2h"
    if "1 hour" in t: return "1h"
    if "short" in t or "30 min" in t: return "short"
    return ""


def match_video_to_meta(video: dict, metas: list[tuple[Path, dict]],
                        skip_indonesian: bool = False) -> tuple[Path, dict] | None:
    """Find best meta match for a YouTube video by title."""
    if skip_indonesian and _is_indonesian(video["title"]):
        return None

    vid_norm = _normalize(video["title"])
    vid_key  = _title_key(video["title"])
    vid_kw   = _keywords(video["title"])
    vid_dur  = _duration_label(video["title"])

    # 1. Exact full-title match
    for path, meta in metas:
        if _normalize(meta.get("title", "")) == vid_norm:
            return path, meta

    # 2. Theme-key exact match (before first "|")
    for path, meta in metas:
        if _title_key(meta.get("title", "")) == vid_key and vid_key:
            return path, meta

    # 3. Theme-key substring match (one contained in other, same duration)
    # Bug fix: use explicit length comparison to avoid min/max returning same
    # string when lengths are equal, which caused trivially True substring checks.
    best = None
    best_score = 0
    for path, meta in metas:
        meta_key = _title_key(meta.get("title", ""))
        if not meta_key or not vid_key:
            continue
        # Duration must match
        if vid_dur and _duration_label(meta.get("title", "")) != vid_dur:
            continue
        if len(vid_key) <= len(meta_key):
            shorter, longer = vid_key, meta_key
        else:
            shorter, longer = meta_key, vid_key
        if shorter != longer and shorter in longer:
            score = len(shorter) / len(longer)
            if score > best_score and score > 0.80:
                best_score = score
                best = (path, meta)

    if best:
        return best

    # 4. Keyword overlap (must share >= 2 meaningful words + same duration)
    best = None
    best_score = 0
    for path, meta in metas:
        if vid_dur and _duration_label(meta.get("title", "")) != vid_dur:
            continue
        meta_kw = _keywords(meta.get("title", ""))
        if not meta_kw or not vid_kw:
            continue
        overlap = vid_kw & meta_kw
        score = len(overlap) / max(len(vid_kw), len(meta_kw))
        if len(overlap) >= 2 and score > best_score and score > 0.50:
            best_score = score
            best = (path, meta)

    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", choices=["en", "id"], default="id")
    ap.add_argument("--localize", action="store_true",
                    help="Run localize_video.py --queue after syncing")
    ap.add_argument("--dry-run", action="store_true",
                    help="Show matches without writing to meta files")
    args = ap.parse_args()

    queue_dir = CHANNEL_CONFIG[args.channel]["queue_dir"]
    print(f"\n=== Sync YouTube IDs: channel={args.channel} ===")

    print("\n1. Fetching videos from YouTube...")
    try:
        videos = fetch_channel_videos(args.channel)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    print("\n2. Loading local meta files...")
    metas = load_metas(queue_dir)
    # Only consider metas without youtube_id
    unmatched_metas = [(p, m) for p, m in metas if not m.get("youtube_id")]
    already_matched = [(p, m) for p, m in metas if m.get("youtube_id")]
    print(f"  {len(metas)} meta files total, {len(already_matched)} already have youtube_id, "
          f"{len(unmatched_metas)} need matching")

    # For Calm Classics (id): skip Indonesian-titled videos (old channel content)
    skip_indonesian = (args.channel == "id")

    print("\n3. Matching videos to meta files...")
    matched = 0
    unmatched_videos = []

    for video in videos:
        result = match_video_to_meta(video, unmatched_metas, skip_indonesian=skip_indonesian)
        if result:
            meta_path, meta = result
            print(f"  ✓ MATCH: [{video['id']}] {video['title'][:50]}")
            print(f"         → {meta_path.name}")
            if not args.dry_run:
                meta["youtube_id"] = video["id"]
                with open(meta_path, "w") as f:
                    yaml.dump(meta, f, allow_unicode=True, sort_keys=False,
                              default_flow_style=False)
            # Remove from unmatched pool
            unmatched_metas = [(p, m) for p, m in unmatched_metas if p != meta_path]
            matched += 1
        else:
            unmatched_videos.append(video)

    print(f"\n  Matched: {matched} videos → meta files")

    if unmatched_videos:
        print(f"\n  No meta match for {len(unmatched_videos)} YouTube videos:")
        for v in unmatched_videos:
            print(f"    [{v['id']}] {v['title'][:70]}")

    if unmatched_metas:
        print(f"\n  No YouTube match for {len(unmatched_metas)} local meta files:")
        for p, m in unmatched_metas:
            print(f"    {p.name}  title={m.get('title','?')[:50]}")

    if args.dry_run:
        print("\n[dry-run] No files written.")
        return

    if matched == 0:
        print("\nNothing matched — check token and channel.")
        return

    print(f"\n✓ Synced {matched} youtube_ids into meta files.")

    if args.localize:
        print(f"\n4. Running localization for channel={args.channel}...")
        result = subprocess.run(
            ["python3", "scripts/localize_video.py", "--queue", "--channel", args.channel],
            cwd=str(ROOT),
        )
        if result.returncode != 0:
            print("  Localization completed with errors.")
        else:
            print("  Localization done.")


if __name__ == "__main__":
    main()
