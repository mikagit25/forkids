#!/usr/bin/env python3
"""
Download classical recordings from Musopen API.
Fills assets/music/classical/ and updates licenses.yaml.

Musopen API: https://musopen.org/sharedfiles/musopen-api.pdf
Requires API key: credentials/musopen_api_key.txt

Usage:
  python3 scripts/download_musopen.py --limit 50
  python3 scripts/download_musopen.py --composer chopin --limit 10
  python3 scripts/download_musopen.py --list-only    # show available, no download
"""
import argparse, logging, time, yaml
from pathlib import Path
import requests

ROOT        = Path(__file__).resolve().parent.parent
MUSIC_DIR   = ROOT / "assets" / "music" / "classical"
LICENSES    = ROOT / "assets" / "music" / "classical" / "licenses.yaml"
KEY_FILE    = ROOT / "credentials" / "musopen_api_key.txt"
API_BASE    = "https://api.musopen.org"

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Composers we want for our sleep/focus programs
TARGET_COMPOSERS = [
    "Chopin", "Debussy", "Satie", "Bach", "Mozart",
    "Brahms", "Schubert", "Beethoven", "Tchaikovsky",
]

# Only download recordings with these licenses
ALLOWED_LICENSES = {"Public Domain", "Attribution", "CC0"}


def load_licenses() -> dict:
    if LICENSES.exists():
        with open(LICENSES) as f:
            data = yaml.safe_load(f) or {}
    else:
        data = {}
    if "recordings" not in data:
        data["recordings"] = []
    return data


def save_licenses(data: dict):
    with open(LICENSES, "w") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def get_api_key() -> str | None:
    if KEY_FILE.exists():
        return KEY_FILE.read_text().strip()
    return None


def fetch_recordings(api_key: str, composer: str = None, page: int = 1, limit: int = 20) -> list:
    params = {"limit": limit, "page": page, "license": "public-domain"}
    if composer:
        params["composer"] = composer
    headers = {"Authorization": f"Token {api_key}"}
    r = requests.get(f"{API_BASE}/recordings/", params=params, headers=headers, timeout=30)
    if r.status_code == 401:
        log.error("Invalid API key — get one at https://musopen.org/accounts/register/")
        return []
    r.raise_for_status()
    return r.json().get("results", [])


def recording_to_license_entry(rec: dict) -> dict:
    piece = rec.get("work", {})
    composer = piece.get("composer", {})
    return {
        "id": f"musopen_{rec['id']}",
        "composer": composer.get("complete_name", "Unknown"),
        "piece": piece.get("title", "Unknown"),
        "performer": rec.get("ensemble", {}).get("name", "") or
                     ", ".join(p.get("name", "") for p in rec.get("performers", [])),
        "year": rec.get("year") or 0,
        "source": f"https://musopen.org/music/recordings/{rec['id']}/",
        "license": "pd",
        "duration_sec": rec.get("duration") or 0,
        "file": "",
        "programs": [],
        "notes": rec.get("license", ""),
        "musopen_id": rec["id"],
    }


def download_recording(rec: dict, api_key: str, dest_dir: Path) -> str | None:
    """Download MP3 from Musopen. Returns local filename or None."""
    url = rec.get("url") or rec.get("mp3_url")
    if not url:
        log.warning(f"  No download URL for recording {rec['id']}")
        return None

    musopen_id = rec["id"]
    piece_title = rec.get("work", {}).get("title", "unknown")
    safe_title = "".join(c if c.isalnum() or c in "-_" else "_" for c in piece_title)[:40]
    fname = f"musopen_{musopen_id}_{safe_title}.mp3"
    dest = dest_dir / fname

    if dest.exists():
        log.info(f"  Already downloaded: {fname}")
        return fname

    headers = {"Authorization": f"Token {api_key}"}
    r = requests.get(url, headers=headers, timeout=120, stream=True)
    if r.status_code == 403:
        log.warning(f"  Access denied for {musopen_id} — may need premium account")
        return None
    r.raise_for_status()

    with open(dest, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)

    size_mb = dest.stat().st_size / 1024 / 1024
    log.info(f"  ✓ {fname} ({size_mb:.1f}MB)")
    return fname


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit",     type=int, default=50)
    parser.add_argument("--composer",  default=None)
    parser.add_argument("--list-only", action="store_true")
    parser.add_argument("--api-key",   default=None)
    args = parser.parse_args()

    api_key = args.api_key or get_api_key()
    if not api_key:
        log.error(
            "No Musopen API key found.\n"
            "1. Register at https://musopen.org/accounts/register/\n"
            "2. Get API key at https://musopen.org/accounts/apikey/\n"
            f"3. Save to {KEY_FILE}"
        )
        return

    MUSIC_DIR.mkdir(parents=True, exist_ok=True)
    licenses_data = load_licenses()
    existing_ids = {r.get("musopen_id") for r in licenses_data["recordings"]}

    composers = [args.composer] if args.composer else TARGET_COMPOSERS
    downloaded = 0
    added_to_licenses = 0

    for composer in composers:
        if downloaded >= args.limit:
            break
        log.info(f"\nFetching: {composer}")
        page = 1
        while downloaded < args.limit:
            recs = fetch_recordings(api_key, composer=composer, page=page, limit=10)
            if not recs:
                break
            for rec in recs:
                if downloaded >= args.limit:
                    break
                if rec["id"] in existing_ids:
                    log.info(f"  Skip (already in licenses): {rec['id']}")
                    continue

                entry = recording_to_license_entry(rec)
                log.info(f"  [{rec['id']}] {entry['composer']} — {entry['piece'][:50]}")

                if not args.list_only:
                    fname = download_recording(rec, api_key, MUSIC_DIR)
                    if fname:
                        entry["file"] = fname
                        downloaded += 1
                    else:
                        entry["license"] = "rejected"
                else:
                    downloaded += 1

                licenses_data["recordings"].append(entry)
                existing_ids.add(rec["id"])
                added_to_licenses += 1
                time.sleep(0.5)  # be polite to API
            page += 1

    if not args.list_only:
        save_licenses(licenses_data)
        log.info(f"\nDone: {downloaded} downloaded, {added_to_licenses} added to licenses.yaml")
    else:
        log.info(f"\nList-only: {added_to_licenses} recordings found")
        save_licenses(licenses_data)


if __name__ == "__main__":
    main()
