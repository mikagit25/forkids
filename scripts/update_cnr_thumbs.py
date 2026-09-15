#!/usr/bin/env python3
"""
Apply text overlay to CNR (Calm Classics) thumbnails and upload to YouTube.

Covers two cases:
  1. Already-published videos (uploaded/) — apply text, upload via YouTube API
  2. Pending queue_id videos (output/queue_id/) — apply text only, save in place

Usage:
    python3 scripts/update_cnr_thumbs.py --dry-run        # preview
    python3 scripts/update_cnr_thumbs.py                  # apply + upload
    python3 scripts/update_cnr_thumbs.py --queue-only     # only queue_id, no API calls
    python3 scripts/update_cnr_thumbs.py --uploaded-only  # only uploaded + YouTube
"""
import argparse
import importlib.util
import shutil
import sys
import tempfile
import time
from pathlib import Path

import yaml

ROOT      = Path(__file__).resolve().parent.parent
UPLOADED  = ROOT / "uploaded"
QUEUE_ID  = ROOT / "output" / "queue_id"

# Video types to process for CNR
CNR_TYPES = {"sleep_program", "focus_program", "visual_theme", "sleep_short"}


def load_thumb_text():
    spec = importlib.util.spec_from_file_location(
        "thumb_text", Path(__file__).resolve().parent / "thumb_text.py"
    )
    tt = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tt)
    return tt


def derive_text(meta: dict) -> str:
    """Derive overlay text from a meta YAML dict."""
    video_type = meta.get("video_type", "")
    program_id = meta.get("program_id", "")
    theme      = meta.get("theme", "")
    title      = meta.get("title", "")

    if video_type == "visual_theme" and theme:
        # aurora_borealis → "AURORA BOREALIS"
        label = theme.replace("_", " ").upper()
        return label

    if video_type in ("sleep_short",):
        # Short clips — just theme
        if theme:
            return theme.replace("_", " ").upper()
        return ""

    if program_id:
        # sleep_chopin_01 → "CHOPIN\nSLEEP MUSIC"
        pid = program_id
        suffix = ""
        if pid.startswith("sleep_"):
            pid = pid[6:]
            suffix = "SLEEP MUSIC"
        elif pid.startswith("focus_"):
            pid = pid[6:]
            suffix = "FOCUS MUSIC"
        # Strip trailing _NN
        parts = pid.rsplit("_", 1)
        if len(parts) == 2 and parts[1].isdigit():
            pid = parts[0]
        label = pid.replace("_", " ").upper()
        return f"{label}\n{suffix}" if suffix else label

    # Fallback: parse title
    if "Chopin" in title:      return "CHOPIN\nSLEEP MUSIC"
    if "Bach" in title:        return "BACH\nFOCUS MUSIC"
    if "Beethoven" in title:   return "BEETHOVEN\nFOCUS MUSIC"
    if "Mozart" in title:      return "MOZART\nFOCUS MUSIC"
    if "Debussy" in title:     return "DEBUSSY\nSLEEP MUSIC"
    if "Tchaikovsky" in title: return "TCHAIKOVSKY\nSLEEP MUSIC"
    return "CLASSICAL MUSIC"


def apply_text_to_thumb(thumb_path: Path, text: str, duration_hours: int,
                        tt, dry_run: bool) -> Path | None:
    """Apply text overlay; returns path to new file (temp) or None on failure."""
    if not thumb_path.exists():
        print(f"    ✗ Thumb not found: {thumb_path.name}")
        return None
    if dry_run:
        print(f"    [DRY RUN] overlay: '{text.replace(chr(10), ' | ')}', {duration_hours}h")
        return thumb_path  # fake — won't be used

    from PIL import Image
    try:
        img = Image.open(thumb_path).convert("RGB")
        img = tt.add_thumb_text(img, text, duration_hours=duration_hours or None)
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        img.save(tmp.name, "PNG")
        tmp.close()
        return Path(tmp.name)
    except Exception as e:
        print(f"    ✗ Text overlay failed: {e}")
        return None


def upload_thumbnail(youtube_id: str, thumb_path: Path, dry_run: bool) -> bool:
    """Upload thumbnail to YouTube via thumbnails().set()."""
    if dry_run:
        print(f"    [DRY RUN] YouTube upload → {youtube_id}")
        return True
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from upload_youtube import get_youtube_service
        import pickle

        # Load channel config for ID channel
        from googleapiclient.http import MediaFileUpload
        ch_config = {"channel": "id"}
        yt = get_youtube_service(ch_config, channel="id")
        req = yt.thumbnails().set(
            videoId=youtube_id,
            media_body=MediaFileUpload(str(thumb_path), mimetype="image/png"),
        )
        req.execute()
        print(f"    ✓ Uploaded thumbnail → youtube.com/watch?v={youtube_id}")
        return True
    except Exception as e:
        print(f"    ✗ YouTube upload failed: {e}")
        return False


def process_dir(directory: Path, do_upload: bool, dry_run: bool, tt) -> tuple[int, int]:
    """Process all CNR meta files in directory. Returns (ok, failed)."""
    ok = failed = 0
    meta_files = sorted(directory.glob("meta_*.yaml"))

    for meta_path in meta_files:
        meta = yaml.safe_load(meta_path.read_text())
        if not meta:
            continue
        video_type  = meta.get("video_type", "")
        youtube_id  = meta.get("youtube_id", "")
        made_kids   = meta.get("made_for_kids", True)

        # duration_hours: prefer meta field, fall back to filename (_1h_, _3h_, _8h_)
        duration_h = meta.get("duration_hours", 0)
        if not duration_h:
            stem_lower = meta_path.stem
            for h in (8, 3, 2, 1):
                if f"_{h}h_" in stem_lower or stem_lower.endswith(f"_{h}h"):
                    duration_h = h
                    break

        # Only process CNR (adult) content
        if made_kids or video_type not in CNR_TYPES:
            continue

        # For uploaded/ we need youtube_id; for queue_id it's optional
        if do_upload and not youtube_id:
            continue

        # Find the thumbnail
        stem = meta_path.stem.replace("meta_", "", 1)
        thumb_path = directory / f"thumb_{stem}.png"

        text = derive_text(meta)
        if not text:
            continue

        print(f"  {stem[:55]:<55}  {text.replace(chr(10),' | ')}")

        new_thumb = apply_text_to_thumb(thumb_path, text, duration_h, tt, dry_run)
        if new_thumb is None:
            failed += 1
            continue

        if not dry_run:
            # Overwrite the existing thumbnail in place
            shutil.copy2(new_thumb, thumb_path)
            if new_thumb != thumb_path:
                new_thumb.unlink(missing_ok=True)

        if do_upload and youtube_id:
            target = thumb_path if dry_run else thumb_path
            if upload_thumbnail(youtube_id, target, dry_run):
                ok += 1
                if not dry_run:
                    time.sleep(1.5)  # be gentle with YouTube API
            else:
                failed += 1
        else:
            ok += 1

    return ok, failed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run",       action="store_true")
    parser.add_argument("--queue-only",    action="store_true", help="Only queue_id, no API")
    parser.add_argument("--uploaded-only", action="store_true", help="Only uploaded, API upload")
    args = parser.parse_args()

    tt = load_thumb_text()

    print("\n=== CNR Thumbnail Text Update ===\n")

    total_ok = total_fail = 0

    if not args.uploaded_only:
        print(f"── queue_id/ (pending, no API) ──")
        ok, fail = process_dir(QUEUE_ID, do_upload=False, dry_run=args.dry_run, tt=tt)
        print(f"  → {ok} updated, {fail} failed\n")
        total_ok += ok; total_fail += fail

    if not args.queue_only:
        print(f"── uploaded/ (published, YouTube API) ──")
        ok, fail = process_dir(UPLOADED, do_upload=True, dry_run=args.dry_run, tt=tt)
        print(f"  → {ok} uploaded to YouTube, {fail} failed\n")
        total_ok += ok; total_fail += fail

    print(f"=== Done: {total_ok} OK, {total_fail} failed ===")


if __name__ == "__main__":
    main()
