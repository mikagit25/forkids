#!/usr/bin/env python3
"""
Publish videos from the output/queue/ directory to YouTube.

Reads meta_*.yaml sidecar files for full metadata (title, tags, upload_day,
upload_time). Falls back to weekly_plan.yaml matching if no sidecar found.

Usage:
    python3 publish_queue.py                  # upload 1 of any type
    python3 publish_queue.py --type short     # upload shorts only
    python3 publish_queue.py --type long      # upload long videos only
    python3 publish_queue.py --dry-run        # show what would be uploaded
    python3 publish_queue.py --limit 2        # upload at most N videos

Content split strategy (6 uploads/day within 10k quota):
    --type long  at 09:00 and 13:00  → 2 long videos/day
    --type short at 11:00, 15:00, 17:00, 19:00 → 4 shorts/day
"""

import argparse
import os
import shutil
import subprocess
import sys
import yaml
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUEUE_DIR    = ROOT / "output" / "queue"
QUEUE_AR_DIR = ROOT / "output" / "queue_ar"
QUEUE_ID_DIR = ROOT / "output" / "queue_id"   # Classical Night Relax (@ClassicalNightRelax)
QUEUE_SD_DIR = ROOT / "sacred_drift" / "output" / "queue"  # Sacred Drift (@SacredDrift)
UPLOADED_DIR = ROOT / "uploaded"
PLAN_PATH    = ROOT / "config" / "weekly_plan.yaml"

QUEUE_DIRS = {
    "en": QUEUE_DIR,
    "ar": QUEUE_AR_DIR,
    "id": QUEUE_ID_DIR,
    "sd": QUEUE_SD_DIR,
}

DAY_OFFSETS = {
    "monday": 0, "tuesday": 1, "wednesday": 2,
    "thursday": 3, "friday": 4, "saturday": 5,
}


def load_plan() -> list:
    if not PLAN_PATH.exists():
        return []
    with open(PLAN_PATH) as f:
        return yaml.safe_load(f).get("videos", [])


def load_sidecar(mp4_path: Path) -> dict | None:
    meta_path = mp4_path.parent / f"meta_{mp4_path.stem}.yaml"
    if meta_path.exists():
        with open(meta_path) as f:
            return yaml.safe_load(f)
    return None


def match_metadata(filename: str, plan: list) -> dict:
    """Fallback: find best matching plan entry for a queue file by type+theme."""
    parts = filename.replace(".mp4", "").split("_")
    video_type = parts[0] if parts else "dance"
    theme = parts[1] if len(parts) > 1 else "animals"

    for entry in plan:
        if (entry.get("video_type") == video_type and
                entry.get("theme", "animals") == theme):
            return entry

    return {
        "title": f"Happy Bear Kids — {theme.capitalize()} {video_type.capitalize()}",
        "status": "unlisted",
        "tags": ["kids", "children", theme, video_type],
        "video_type": video_type,
        "theme": theme,
    }


def calc_publish_at(upload_day: str, upload_time: str) -> str | None:
    """
    Calculate UTC ISO 8601 publishAt for the next occurrence of upload_day.

    The weekly plan runs Mon-Sat. We treat the current week as starting on
    the most recent Sunday and map Mon=+1 day, Tue=+2, ... Sat=+6.
    If the calculated time is already past, push to next week.
    """
    day_offset = DAY_OFFSETS.get(upload_day.lower())
    if day_offset is None:
        return None

    now = datetime.now(timezone.utc)
    # Find the most recent Sunday (weekday 6) at 00:00 UTC
    days_since_sunday = (now.weekday() + 1) % 7  # Mon=1..Sun=0
    last_sunday = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_since_sunday)

    # Parse time (HH:MM)
    h, m = int(upload_time[:2]), int(upload_time[3:5])
    publish_dt = last_sunday + timedelta(days=day_offset + 1, hours=h, minutes=m)

    # If already past, schedule for next week
    if publish_dt <= now:
        publish_dt += timedelta(weeks=1)

    return publish_dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def upload_video(mp4_path: Path, metadata: dict, schedule: bool = True,
                 dry_run: bool = False, channel: str = "en") -> bool:
    title       = metadata.get("title", mp4_path.stem)
    theme       = metadata.get("theme", "animals")
    video_type  = metadata.get("video_type", "dance")
    tags        = metadata.get("tags", [])
    tags_str    = ",".join(str(t) for t in tags) if tags else ""
    description = metadata.get("description", "")

    publish_at = None
    if schedule:
        upload_day  = metadata.get("upload_day", "")
        upload_time = metadata.get("upload_time", "09:00")
        if upload_day:
            publish_at = calc_publish_at(upload_day, upload_time)

    status_label = f"scheduled {publish_at}" if publish_at else metadata.get("status", "public")

    print(f"\n  File:   {mp4_path.name}")
    print(f"  Title:  {title}")
    print(f"  Status: {status_label}")

    if dry_run:
        print(f"  [DRY RUN] would upload")
        return True

    language = metadata.get("language", "en")

    made_for_kids = metadata.get("made_for_kids", channel not in ("id", "sd"))
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "upload_youtube.py"),
        "--file",         str(mp4_path),
        "--title",        title,
        "--video-type",   video_type,
        "--theme",        theme,
        "--status",       "private" if publish_at else metadata.get("status", "public"),
        "--language",     language,
        "--channel",      channel,
        "--made-for-kids", "true" if made_for_kids else "false",
    ]

    if tags_str:
        cmd += ["--tags", tags_str]

    if description:
        cmd += ["--description", description]

    thumb_path = mp4_path.parent / f"thumb_{mp4_path.stem}.png"
    if thumb_path.exists():
        cmd += ["--thumbnail", str(thumb_path)]
        print(f"  Thumb:  {thumb_path.name}")

    if publish_at:
        cmd += ["--publish-at", publish_at]

    # Tell upload_youtube.py where to write the video ID after upload
    meta_path = mp4_path.parent / f"meta_{mp4_path.stem}.yaml"
    if meta_path.exists():
        cmd += ["--meta-path", str(meta_path)]

    result = subprocess.run(cmd, capture_output=False)
    return result.returncode == 0


def _push_localizations_inline(video_id: str, localizations: dict, channel: str):
    """Push pre-translated localizations to YouTube immediately after upload."""
    import json as _json
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        cred_map = {
            "en": ROOT / "credentials" / "youtube_token.json",
            "ar": ROOT / "credentials" / "youtube_token_ar.json",
            "id": ROOT / "credentials" / "youtube_token_id.json",
            "sd": ROOT / "credentials" / "youtube_token_ar.json",
        }
        token_path = cred_map[channel]
        raw = token_path.read_text().strip() if token_path.exists() else ""
        if not raw:
            raise RuntimeError(
                f"YouTube token missing/empty: {token_path}\n"
                f"Run: python3 scripts/reauth_youtube.py --channel {channel}"
            )
        t = _json.loads(raw)
        scopes = ["https://www.googleapis.com/auth/youtube",
                  "https://www.googleapis.com/auth/youtube.force-ssl"]
        creds = Credentials(
            token=t.get("access_token"), refresh_token=t["refresh_token"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=t["client_id"], client_secret=t["client_secret"],
            scopes=scopes,
        )
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            t["access_token"] = creds.token
            import os as _os
            tmp = token_path.with_suffix(".tmp")
            tmp.write_text(_json.dumps(t, indent=2))
            _os.replace(str(tmp), str(token_path))
        yt = build("youtube", "v3", credentials=creds)

        # Fetch existing localizations
        resp = yt.videos().list(part="localizations", id=video_id).execute()
        if not resp.get("items"):
            print(f"  ⚠ Could not fetch video {video_id} for localizations")
            return
        existing = resp["items"][0].get("localizations", {})

        # Push one language at a time (pushing all at once fails for CJK/Arabic)
        # YouTube needs ~60s to process a freshly uploaded video before accepting localizations
        import time as _time
        pushed = 0
        retry_langs = {}
        for lang, data in localizations.items():
            existing[lang] = data
            try:
                yt.videos().update(
                    part="localizations",
                    body={"id": video_id, "localizations": existing}
                ).execute()
                pushed += 1
            except Exception as e:
                if "invalidVideoMetadata" in str(e) or "400" in str(e):
                    retry_langs[lang] = data
                else:
                    print(f"  ⚠ Could not push [{lang}]: {e}")
        if retry_langs:
            print(f"  ↺ {len(retry_langs)} langs got 400 — waiting 90s for YouTube to process video...")
            _time.sleep(90)
            for lang, data in retry_langs.items():
                existing[lang] = data
                try:
                    yt.videos().update(
                        part="localizations",
                        body={"id": video_id, "localizations": existing}
                    ).execute()
                    pushed += 1
                except Exception as e:
                    print(f"  ⚠ Could not push [{lang}] after retry: {e}")
        print(f"  → pushed {pushed}/{len(localizations)} localizations immediately")
    except Exception as e:
        print(f"  ⚠ Inline localization failed: {e} — skipping")


def _delete_youtube_video(video_id: str, channel: str = "id"):
    """Delete a YouTube video by ID using the channel credentials. Logs result."""
    import subprocess as _sp
    r = _sp.run(
        ["python3", str(ROOT / "scripts" / "delete_youtube_video.py"),
         "--channel", channel, video_id],
        capture_output=True, text=True,
    )
    if "Deleted:" in r.stdout:
        print(f"  ✓ Deleted replaced video {video_id} from YouTube")
    else:
        print(f"  ⚠ Could not delete {video_id}: {r.stdout.strip() or r.stderr.strip()[:100]}")


def _add_to_playlist(video_id: str, playlist_id: str, channel: str):
    """Add a video to a YouTube playlist using the channel credentials."""
    CREDS = {
        "en": ROOT / "credentials" / "youtube_token.json",
        "ar": ROOT / "credentials" / "youtube_token_ar.json",
        "id": ROOT / "credentials" / "youtube_token_id.json",
        "sd": ROOT / "credentials" / "youtube_token_ar.json",
    }
    cred_path = CREDS.get(channel)
    if not cred_path or not cred_path.exists():
        print(f"  ⚠ No credentials for channel={channel}, cannot add to playlist")
        return
    try:
        import google.oauth2.credentials
        import googleapiclient.discovery
        creds_data = yaml.safe_load(open(cred_path)) if cred_path.suffix == ".yaml" else __import__("json").loads(cred_path.read_text())
        creds = google.oauth2.credentials.Credentials(
            token=creds_data.get("token"),
            refresh_token=creds_data.get("refresh_token"),
            token_uri=creds_data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=creds_data.get("client_id"),
            client_secret=creds_data.get("client_secret"),
        )
        yt = googleapiclient.discovery.build("youtube", "v3", credentials=creds)
        yt.playlistItems().insert(
            part="snippet",
            body={"snippet": {"playlistId": playlist_id, "resourceId": {"kind": "youtube#video", "videoId": video_id}}},
        ).execute()
        print(f"  ✓ Added to playlist {playlist_id}")
    except Exception as e:
        print(f"  ⚠ Could not add to playlist {playlist_id}: {e}")


def _fix_ar_symlinks(old_path: Path, new_path: Path):
    """After an EN file moves to uploaded/, update any AR-queue symlinks that pointed to it."""
    for candidate in QUEUE_AR_DIR.glob("*.mp4"):
        try:
            if candidate.is_symlink() and Path(os.readlink(str(candidate))).resolve() == old_path.resolve():
                candidate.unlink()
                candidate.symlink_to(str(new_path))
        except Exception:
            pass


SHORT_PREFIXES = ("short_", "ar_short_", "sleep_short_", "funnel_", "visual_short_", "kw_short_")


def is_short(path: Path) -> bool:
    if path.name.startswith(SHORT_PREFIXES):
        return True
    # Fallback: check meta is_short field (covers any naming scheme)
    meta_path = path.parent / f"meta_{path.stem}.yaml"
    if meta_path.exists():
        try:
            m = yaml.safe_load(open(meta_path)) or {}
            return bool(m.get("is_short", False))
        except Exception:
            pass
    return False


def is_long(path: Path) -> bool:
    return not is_short(path)


def filter_queue(queue: list[Path], kind: str) -> list[Path]:
    if kind == "short":
        return [p for p in queue if is_short(p)]
    if kind == "long":
        return [p for p in queue if is_long(p)]
    # "any" — longs first (by mtime), then shorts (by mtime)
    longs  = [p for p in queue if is_long(p)]
    shorts = [p for p in queue if is_short(p)]
    return longs + shorts


def is_ready(mp4_path: Path) -> tuple[bool, str]:
    """Return (ready, reason). Video is ready only when meta+description+thumbnail exist."""
    meta_path  = mp4_path.parent / f"meta_{mp4_path.stem}.yaml"
    thumb_path = mp4_path.parent / f"thumb_{mp4_path.stem}.png"

    if not meta_path.exists():
        return False, "no meta file"
    if meta_path.stat().st_size == 0:
        return False, "meta file is 0 bytes"

    meta = yaml.safe_load(open(meta_path)) or {}
    if meta.get("upload_blocked"):
        return False, f"upload_blocked: {meta.get('upload_blocked')}"
    if not meta.get("title", "").strip():
        return False, "empty title"
    if not meta.get("description", "").strip():
        return False, "empty description"
    if not thumb_path.exists():
        return False, "no thumbnail"
    if thumb_path.stat().st_size == 0:
        return False, "thumbnail is 0 bytes"

    return True, "ok"


def main():
    parser = argparse.ArgumentParser(description="Publish queue to YouTube")
    parser.add_argument("--dry-run",     action="store_true")
    parser.add_argument("--limit",       type=int, default=1, help="Max videos to upload (default 1)")
    parser.add_argument("--type",          choices=["short", "long", "any"], default="any",
                        help="Filter: short=60s videos, long=30min videos, any=no filter")
    parser.add_argument("--fallback-type", choices=["short", "long", "any"], default=None,
                        help="If --type queue is empty, publish this type instead")
    parser.add_argument("--no-schedule", action="store_true", default=False,
                        help="Upload as public immediately (default: use upload_day/time from meta)")
    parser.add_argument("--queue", choices=["en", "ar", "id", "sd"], default="en",
                        help="Queue: en=Happy Bear Kids, ar=AR Kids, id=Classical Night Relax, sd=Sacred Drift")
    parser.add_argument("--file", help="Publish a specific MP4 file from the queue (by filename, bypasses ordering)")
    args = parser.parse_args()

    active_queue_dir = QUEUE_DIRS[args.queue]
    active_queue_dir.mkdir(parents=True, exist_ok=True)
    UPLOADED_DIR.mkdir(parents=True, exist_ok=True)

    if args.file:
        specific = active_queue_dir / args.file
        if not specific.exists():
            print(f"File not found: {specific}")
            return
        all_mp4s  = [specific]
        all_queue = [specific]
    else:
        def _sort_key(p: Path):
            name = p.name
            # SD queue: compilations (AI audio) first, then sound design, then classical
            if active_queue_dir == QUEUE_SD_DIR:
                if name.startswith("sd_comp_"):
                    priority = 0
                elif name.startswith("sd_sound_design_") or name.startswith("ambient_") or name.startswith("fire_"):
                    priority = 1
                elif name.startswith("sd_classical_"):
                    priority = 2
                else:
                    priority = 1
                return (priority, p.stat().st_mtime)
            return (0, p.stat().st_mtime)

        all_mp4s = sorted(
            [p for p in active_queue_dir.glob("*.mp4")
             if "test_" not in p.name and p.exists()],   # p.exists() skips broken symlinks
            key=_sort_key
        )
        all_queue = filter_queue(all_mp4s, args.type)

    # Split into ready (have meta+description+thumbnail) and not-ready
    ready_queue   = []
    not_ready     = []
    for p in all_queue:
        ok, reason = is_ready(p)
        if ok:
            ready_queue.append(p)
        else:
            not_ready.append((p, reason))

    shorts_count = len([p for p in all_mp4s if is_short(p)])
    longs_count  = len([p for p in all_mp4s if is_long(p)])
    print(f"\nPublish queue ({args.queue.upper()}) — {len(all_mp4s)} total ({longs_count} long, {shorts_count} short)")
    print(f"  Ready to publish: {len(ready_queue)}")
    if not_ready:
        print(f"  Waiting (missing meta/thumb): {len(not_ready)}")
        for p, reason in not_ready[:5]:
            print(f"    - {p.name}: {reason}")
        if len(not_ready) > 5:
            print(f"    ... and {len(not_ready)-5} more")

    if not ready_queue:
        if args.fallback_type:
            print(f"\nNo {args.type} videos ready — falling back to {args.fallback_type}")
            args.type = args.fallback_type
            all_queue   = filter_queue(all_mp4s, args.type)
            ready_queue = []
            not_ready   = []
            for p in all_queue:
                ok, reason = is_ready(p)
                if ok:
                    ready_queue.append(p)
                else:
                    not_ready.append((p, reason))
            if not ready_queue:
                print(f"No {args.type} videos ready either. Queue empty.")
                return
        else:
            print(f"\nNo videos ready to publish (type={args.type}). Check meta+thumbnail.")
            return

    plan  = load_plan()
    limit = args.limit if args.limit > 0 else len(ready_queue)

    print(f"\nUploading up to {limit} video(s) (type={args.type})")
    if args.dry_run:
        print("DRY RUN mode")

    uploaded = 0
    failed   = 0

    for mp4_path in ready_queue[:limit]:
        metadata = load_sidecar(mp4_path) or match_metadata(mp4_path.name, plan)
        success  = upload_video(
            mp4_path, metadata,
            schedule=not args.no_schedule,
            dry_run=args.dry_run,
            channel=args.queue,
        )

        if success:
            if not args.dry_run:
                # Check for AR symlinks before touching the MP4
                ar_symlinks = [
                    c for c in QUEUE_AR_DIR.glob("*.mp4")
                    if c.is_symlink() and Path(os.readlink(str(c))).resolve() == mp4_path.resolve()
                ]
                if ar_symlinks:
                    # AR still needs the file — move to uploaded/ and update symlinks
                    dest = UPLOADED_DIR / mp4_path.name
                    shutil.move(str(mp4_path), str(dest))
                    _fix_ar_symlinks(mp4_path, dest)
                    print(f"  → moved to uploaded/ (AR symlink exists)")
                else:
                    # No AR dependency — delete MP4 immediately to free disk space
                    mp4_size_mb = mp4_path.stat().st_size // (1024 * 1024)
                    mp4_path.unlink()
                    print(f"  → MP4 deleted ({mp4_size_mb}MB freed)")
                for suffix in [f"thumb_{mp4_path.stem}.png", f"meta_{mp4_path.stem}.yaml"]:
                    side = mp4_path.parent / suffix
                    if side.exists():
                        shutil.move(str(side), str(UPLOADED_DIR / suffix))
                # Push pre-translated localizations immediately, or fall back to background script
                meta_dest = UPLOADED_DIR / f"meta_{mp4_path.stem}.yaml"
                if meta_dest.exists():
                    try:
                        uploaded_meta = yaml.safe_load(open(meta_dest)) or {}
                        yt_id         = uploaded_meta.get("youtube_id", "")
                        pre_locs      = uploaded_meta.get("localizations", {})
                    except Exception:
                        yt_id    = ""
                        pre_locs = {}
                    if yt_id and pre_locs:
                        # Push pre-translated localizations immediately (one lang at a time)
                        _push_localizations_inline(yt_id, pre_locs, args.queue)
                    elif yt_id:
                        # No pre-translations — fall back to background localization
                        subprocess.Popen(
                            [sys.executable, "-u",
                             str(ROOT / "scripts" / "localize_all_videos.py"),
                             "--channel", args.queue, "--video-id", yt_id],
                            stdout=open(ROOT / "logs" / "localize_auto.log", "a"),
                            stderr=subprocess.STDOUT,
                        )
                        print(f"  → localization started in background ({yt_id})")
                    # Add to playlist if specified in meta
                    if yt_id:
                        playlist_id = uploaded_meta.get("playlist_id", "")
                        if playlist_id:
                            _add_to_playlist(yt_id, playlist_id, args.queue)
                # Auto-delete replaced video if meta has replace_id
                meta_dest = UPLOADED_DIR / f"meta_{mp4_path.stem}.yaml"
                if meta_dest.exists():
                    try:
                        m = yaml.safe_load(open(meta_dest)) or {}
                        old_id = m.get("replace_id")
                        if old_id:
                            _delete_youtube_video(old_id, channel=args.queue)
                    except Exception as e:
                        print(f"  ⚠ replace_id cleanup failed: {e}")
            uploaded += 1
        else:
            failed += 1

    print(f"\n{'='*50}")
    print(f"  Uploaded: {uploaded}   Failed: {failed}")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
