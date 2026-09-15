#!/usr/bin/env python3
"""
Download meditation (and kids) audio tracks from Google Drive folder.

Authenticates via service account. The folder must be shared with:
  kids-channel-bot@kids-chanel-497308.iam.gserviceaccount.com

Usage:
  python3 scripts/sync_gdrive_meditation.py              # download all new files
  python3 scripts/sync_gdrive_meditation.py --list-only  # list without downloading
  python3 scripts/sync_gdrive_meditation.py --force      # re-download even if exists

Destinations:
  Meditation tracks  → assets/audio/suno_meditation/Meditation/
  Kids tracks        → assets/audio/mureka_kids/
  (Kids detection: filename contains 'kids', 'lullaby', 'baby', 'children', 'bedtime')

State file (tracks what's been downloaded by file ID):
  assets/audio/suno_meditation/.gdrive_state.json

Google Drive folder: 1A1VoXIR-00dgdjSvl16r8isvgjBD0Tn_
"""
import argparse, json, logging, sys
from pathlib import Path

ROOT       = Path(__file__).resolve().parent.parent
FOLDER_ID  = "1A1VoXIR-00dgdjSvl16r8isvgjBD0Tn_"
SA_FILE    = ROOT / "credentials" / "drive_service_account.json"
MEDIT_DIR  = ROOT / "assets" / "audio" / "suno_meditation" / "Meditation"
KIDS_DIR   = ROOT / "assets" / "audio" / "mureka_kids"
STATE_FILE = ROOT / "assets" / "audio" / "suno_meditation" / ".gdrive_state.json"
LOG_DIR    = ROOT / "logs"

AUDIO_MIME = {
    "audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav",
    "audio/flac", "audio/x-flac", "audio/mp4", "audio/m4a",
    "audio/ogg", "audio/aac",
}
AUDIO_EXT = {".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac"}

KIDS_KEYWORDS = {"kids", "lullaby", "baby", "children", "bedtime", "детск", "колыбел"}

log = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler()],
)


def _get_service():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    creds = service_account.Credentials.from_service_account_file(
        str(SA_FILE),
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )
    return build("drive", "v3", credentials=creds)


def _load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"downloaded": {}}


def _save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def _is_kids(name: str) -> bool:
    name_lower = name.lower()
    return any(kw in name_lower for kw in KIDS_KEYWORDS)


def _list_audio_files(svc, folder_id: str) -> list[dict]:
    """Recursively list all audio files in folder and subfolders."""
    results = []
    page_token = None
    while True:
        resp = svc.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            fields="nextPageToken, files(id, name, mimeType, size, modifiedTime)",
            pageToken=page_token,
            pageSize=100,
        ).execute()
        for f in resp.get("files", []):
            if f["mimeType"] == "application/vnd.google-apps.folder":
                results.extend(_list_audio_files(svc, f["id"]))
            elif (f["mimeType"] in AUDIO_MIME or
                  Path(f["name"]).suffix.lower() in AUDIO_EXT):
                results.append(f)
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return results


def _unique_dest(dest: Path) -> Path:
    """If dest exists, add numeric suffix: name (1).mp3, name (2).mp3 ..."""
    if not dest.exists():
        return dest
    stem, suffix = dest.stem, dest.suffix
    # Strip existing parenthesised counter if present
    import re
    base = re.sub(r"\s*\(\d+\)$", "", stem)
    i = 1
    while True:
        candidate = dest.parent / f"{base} ({i}){suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def _download_file(svc, file_id: str, dest: Path):
    from googleapiclient.http import MediaIoBaseDownload
    import io
    request = svc.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request, chunksize=4 * 1024 * 1024)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    dest.write_bytes(fh.getvalue())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--list-only", action="store_true")
    parser.add_argument("--force",     action="store_true", help="Re-download existing")
    parser.add_argument("--folder",    default=FOLDER_ID, help="Drive folder ID")
    args = parser.parse_args()

    MEDIT_DIR.mkdir(parents=True, exist_ok=True)
    KIDS_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    log.info("Connecting to Google Drive (service account)...")
    try:
        svc = _get_service()
    except Exception as e:
        log.error(f"Auth failed: {e}")
        log.error(f"Share the folder with: kids-channel-bot@kids-chanel-497308.iam.gserviceaccount.com")
        sys.exit(1)

    log.info(f"Listing files in folder {args.folder}...")
    files = _list_audio_files(svc, args.folder)
    log.info(f"Found {len(files)} audio file(s)")

    if not files:
        log.warning("No audio files found. Make sure the folder is shared with the service account.")
        log.warning("Share with: kids-channel-bot@kids-chanel-497308.iam.gserviceaccount.com")
        return

    state = _load_state()
    downloaded_ids = state.get("downloaded", {})

    new_count = kids_count = skip_count = 0
    for f in files:
        fid   = f["id"]
        name  = f["name"]
        size  = int(f.get("size", 0))
        kids  = _is_kids(name)
        dest_dir = KIDS_DIR if kids else MEDIT_DIR
        dest  = dest_dir / name

        tag = "[KIDS]" if kids else "[MEDIT]"
        size_mb = size / 1024 / 1024

        if args.list_only:
            status = "✓ cached" if fid in downloaded_ids else "↓ new"
            log.info(f"  {status} {tag} {name} ({size_mb:.1f} MB)")
            continue

        if fid in downloaded_ids and not args.force:
            log.info(f"  skip {tag} {name} (already downloaded)")
            skip_count += 1
            continue

        # Handle duplicate filenames — every Drive file gets its own copy
        dest = _unique_dest(dest)

        log.info(f"  ↓ {tag} {name} ({size_mb:.1f} MB)...")
        try:
            _download_file(svc, fid, dest)
            downloaded_ids[fid] = {"name": name, "dest": str(dest), "size": size}
            if kids:
                kids_count += 1
            else:
                new_count += 1
            log.info(f"    → {dest.relative_to(ROOT)}")
        except Exception as e:
            log.error(f"    FAILED: {e}")

    if not args.list_only:
        state["downloaded"] = downloaded_ids
        _save_state(state)
        log.info(f"\n=== DONE: {new_count} meditation, {kids_count} kids, {skip_count} skipped ===")
        if new_count:
            log.info(f"  Meditation → {MEDIT_DIR.relative_to(ROOT)}/")
        if kids_count:
            log.info(f"  Kids       → {KIDS_DIR.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
