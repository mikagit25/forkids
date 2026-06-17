#!/usr/bin/env python3
"""
Replace published YouTube videos: delete old → upload new.
Used to replace bad AR content (English videos published on Arabic channel,
or shape videos with English labels) with correct versions.

Usage:
  # List videos that will be replaced
  python3 scripts/replace_youtube_videos.py --list

  # Delete specific video IDs from YouTube (confirm before action)
  python3 scripts/replace_youtube_videos.py --delete ID1 ID2 ID3

  # Upload a new video immediately (bypasses cron queue)
  python3 scripts/replace_youtube_videos.py --upload output/queue_ar/shape_float_circle_tb_20260614.mp4

  # Full replace: delete old + upload new
  python3 scripts/replace_youtube_videos.py --delete ID1 --upload new_video.mp4
"""
import argparse
import json
import sys
import time
import yaml
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


def get_youtube():
    import json as _j
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    import google.auth.transport.requests

    json_path   = ROOT / "credentials" / "youtube_token.json"
    pickle_path = ROOT / "credentials" / "token.pickle"

    creds = None
    if json_path.exists():
        t = _j.load(open(json_path))
        creds = Credentials(
            token=t.get("access_token"),
            refresh_token=t.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=t.get("client_id"),
            client_secret=t.get("client_secret"),
        )
    elif pickle_path.exists():
        import pickle
        with open(pickle_path, "rb") as f:
            creds = pickle.load(f)

    if creds and (creds.expired or not creds.valid):
        creds.refresh(google.auth.transport.requests.Request())
    return build("youtube", "v3", credentials=creds)


def delete_video(youtube, video_id: str, dry_run: bool = False):
    print(f"  Deleting: https://youtu.be/{video_id} ...", end="  ")
    if dry_run:
        print("[DRY RUN]")
        return True
    try:
        youtube.videos().delete(id=video_id).execute()
        print("✓ deleted")
        return True
    except Exception as e:
        print(f"✗ {e}")
        return False


def upload_video(youtube, mp4_path: Path, dry_run: bool = False):
    from googleapiclient.http import MediaFileUpload
    meta_path = mp4_path.parent / f"meta_{mp4_path.stem}.yaml"
    thumb_path = mp4_path.parent / f"thumb_{mp4_path.stem}.png"

    meta = {}
    if meta_path.exists():
        meta = yaml.safe_load(open(meta_path)) or {}

    title       = meta.get("title", mp4_path.stem)
    description = meta.get("description", "")
    tags        = meta.get("tags", [])
    is_short    = meta.get("is_short", False)
    language    = meta.get("language", "en")

    print(f"\n  Uploading: {mp4_path.name}")
    print(f"  Title: {title[:70]}")
    print(f"  Lang:  {language} | Short: {is_short}")

    if dry_run:
        print("  [DRY RUN]")
        return None

    body = {
        "snippet": {
            "title":       title,
            "description": description,
            "tags":        tags[:40],
            "categoryId":  "22",
            "defaultLanguage": language,
        },
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": True},
    }

    media = MediaFileUpload(str(mp4_path), mimetype="video/mp4",
                            resumable=True, chunksize=4 * 1024 * 1024)
    req = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    video_id = None
    while True:
        status, response = req.next_chunk()
        if status:
            print(f"    {int(status.progress() * 100)}%", end="\r")
        if response:
            video_id = response["id"]
            print(f"\n  ✓ Uploaded: https://youtu.be/{video_id}")
            break

    if video_id and thumb_path.exists():
        from googleapiclient.http import MediaFileUpload as MFU
        try:
            m = MFU(str(thumb_path), mimetype="image/png", resumable=False)
            youtube.thumbnails().set(videoId=video_id, media_body=m).execute()
            print(f"  ✓ Thumbnail set")
        except Exception as e:
            print(f"  ⚠ Thumbnail failed: {e}")

    return video_id


def set_private(youtube, video_id: str, dry_run: bool = False):
    print(f"  Setting private: https://youtu.be/{video_id} ...", end="  ")
    if dry_run:
        print("[DRY RUN]")
        return True
    try:
        youtube.videos().update(
            part="status",
            body={"id": video_id, "status": {"privacyStatus": "private"}},
        ).execute()
        print("✓ private")
        return True
    except Exception as e:
        print(f"✗ {e}")
        return False


def cmd_list():
    """Show the bad AR videos that were published and need replacement."""
    BAD_VIDEOS = [
        # ar_counting_* — English counting videos on Arabic channel
        ("PsWOD7KfMwY", "ar_counting_rainbow_20260605", "English counting on AR channel"),
        ("xec9XgA9UwU", "ar_counting_pastel_20260605",  "English counting on AR channel"),
        ("SLL6-ZpAiYg", "ar_counting_warm_20260605",    "English counting on AR channel"),
        # ar_dance_shapes_* — Manim shape dance, possibly English text
        ("OVvK9oZJ0Bo", "ar_dance_mixed_blocks_20260528",  "Manim shape dance, English labels"),
        ("KkOcAPVAYZo", "ar_dance_shapes_rainbow_20260529","Manim shape dance, English labels"),
        ("_8fWoDe9YaA", "ar_dance_shapes_pastel_20260529", "Manim shape dance, English labels"),
        ("eD3-xUyMwow", "ar_dance_shapes_warm_20260529",   "Manim shape dance, English labels"),
        ("BgkWEMhfqes", "ar_dance_shapes_cool_20260529",   "Manim shape dance, English labels"),
        ("YKQlmmlOR-c", "ar_dance_shapes_neon_20260605",   "Manim shape dance, English labels"),
    ]
    print("\nPublished AR videos that may need replacement:\n")
    for vid_id, stem, reason in BAD_VIDEOS:
        print(f"  https://youtu.be/{vid_id}")
        print(f"    {stem}")
        print(f"    Reason: {reason}\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--list",    action="store_true",
                        help="List published bad AR videos")
    parser.add_argument("--delete",      nargs="+", metavar="VIDEO_ID",
                        help="Delete video(s) from YouTube")
    parser.add_argument("--set-private", nargs="+", metavar="VIDEO_ID",
                        help="Set video(s) to private (hides from viewers, preserves ID/views)")
    parser.add_argument("--upload",      nargs="+", metavar="MP4",
                        help="Upload new video(s) immediately")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.list:
        cmd_list()
        return

    if not args.delete and not args.upload and not args.set_private:
        parser.print_help()
        return

    youtube = get_youtube()

    if args.set_private:
        print(f"\nSetting {len(args.set_private)} video(s) to private:")
        for vid_id in args.set_private:
            set_private(youtube, vid_id, args.dry_run)
            time.sleep(1)

    if args.delete:
        print(f"\nDeleting {len(args.delete)} video(s) from YouTube:")
        if not args.dry_run:
            confirm = input("  Type 'yes' to confirm deletion: ").strip().lower()
            if confirm != "yes":
                print("  Aborted.")
                return
        for vid_id in args.delete:
            delete_video(youtube, vid_id, args.dry_run)
            time.sleep(1)

    if args.upload:
        print(f"\nUploading {len(args.upload)} video(s):")
        for mp4 in args.upload:
            p = Path(mp4)
            if not p.exists():
                print(f"  ✗ not found: {mp4}")
                continue
            vid_id = upload_video(youtube, p, args.dry_run)
            if vid_id:
                # Save youtube_id to meta
                meta_path = p.parent / f"meta_{p.stem}.yaml"
                if meta_path.exists():
                    m = yaml.safe_load(open(meta_path)) or {}
                    m["youtube_id"] = vid_id
                    with open(meta_path, "w") as f:
                        yaml.dump(m, f, allow_unicode=True, default_flow_style=False)
            time.sleep(2)


if __name__ == "__main__":
    main()
