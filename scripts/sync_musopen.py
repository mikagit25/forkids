#!/usr/bin/env python3
"""
Musopen auto-downloader with priority queue and daily limit tracking.

Strategy:
  1. PRIORITY list — specific pieces needed for blocked programs (focus_bach_01, sleep_lullaby_01)
  2. WISHLIST composers — broaden library for future programs
  3. Skips already-downloaded tracks (by musopen_id)
  4. Tracks daily download count in a state file (max 5/day free tier)
  5. Logs every download to logs/musopen_sync.log

Usage:
  python3 scripts/sync_musopen.py                  # auto daily run (respects limit)
  python3 scripts/sync_musopen.py --limit 3        # override daily limit
  python3 scripts/sync_musopen.py --list-only      # show what's available, no download
  python3 scripts/sync_musopen.py --composer Bach  # focus on one composer
  python3 scripts/sync_musopen.py --reset-daily    # reset today's counter

Cron (runs daily at 06:00):
  0 6 * * * cd /opt/kids_channel && python3 scripts/sync_musopen.py >> logs/musopen_sync.log 2>&1

API key: credentials/musopen_api_key.txt
  1. Register at https://musopen.org/accounts/register/
  2. Get key at https://musopen.org/accounts/apikey/
"""
import argparse, json, logging, re, sys, time, yaml
from datetime import date
from pathlib import Path

import requests

ROOT        = Path(__file__).resolve().parent.parent
MUSIC_DIR   = ROOT / "assets" / "music" / "classical" / "Music"
LICENSES    = ROOT / "assets" / "music" / "classical" / "licenses.yaml"
KEY_FILE    = ROOT / "credentials" / "musopen_api_key.txt"
STATE_FILE  = ROOT / "assets" / "music" / "classical" / ".sync_state.json"
LOG_DIR     = ROOT / "logs"
API_BASE    = "https://api.musopen.org"
DAILY_LIMIT = 5   # free tier: 5 downloads/day

log = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler()],
)

# ── Priority queue ────────────────────────────────────────────────────────────
# Specific pieces needed to unblock focus_bach_01 and sleep_lullaby_01.
# Format: (search_composer, search_keywords, target_id_in_licenses)
PRIORITY_PIECES = [
    # focus_bach_01
    ("Bach", "air g string suite 3 BWV 1068",          "bach_air_g_string"),
    ("Bach", "Goldberg variations aria BWV 988",        "bach_goldberg_aria"),
    ("Bach", "Jesu joy man desiring cantata BWV 147",   "bach_jesu_joy"),
    ("Bach", "prelude C major well-tempered BWV 846",   "bach_prelude_c_major"),
    ("Bach", "prelude C minor BWV 999",                 "bach_prelude_bwv_999"),
    ("Bach", "invention 1 C major BWV 772",             "bach_invention_1"),
    # sleep_lullaby_01
    ("Brahms", "wiegenlied lullaby op 49",              "brahms_lullaby"),
    ("Brahms", "intermezzo A major op 118",             "brahms_intermezzo_op118"),
    ("Schubert", "wiegenlied lullaby D 498",            "schubert_lullaby"),
    ("Satie", "gymnopédie gymnopedie 1",                "satie_gymnopedie_1"),
    ("Bach", "sleepers wake BWV 140",                   "bach_sleepers_wake"),
]

# ── Wishlist composers (after priority is done) ───────────────────────────────
WISHLIST_COMPOSERS = [
    "Brahms", "Schubert", "Satie", "Liszt", "Ravel",
    "Schumann", "Handel", "Vivaldi", "Bach",
]


# ─────────────────────────────────────────────────────────────────────────────
# State management (daily counter)
# ─────────────────────────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"date": "", "downloaded_today": 0, "total_downloaded": 0, "musopen_ids_downloaded": []}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def get_daily_remaining(state: dict, limit: int) -> int:
    today = str(date.today())
    if state.get("date") != today:
        state["date"] = today
        state["downloaded_today"] = 0
    return max(0, limit - state["downloaded_today"])


# ─────────────────────────────────────────────────────────────────────────────
# Licenses YAML
# ─────────────────────────────────────────────────────────────────────────────

def load_licenses() -> dict:
    if LICENSES.exists():
        data = yaml.safe_load(LICENSES.read_text()) or {}
    else:
        data = {}
    data.setdefault("recordings", [])
    return data


def save_licenses(data: dict):
    with open(LICENSES, "w") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def existing_musopen_ids(licenses_data: dict) -> set:
    return {r.get("musopen_id") for r in licenses_data["recordings"] if r.get("musopen_id")}


# ─────────────────────────────────────────────────────────────────────────────
# Musopen API
# ─────────────────────────────────────────────────────────────────────────────

def api_get(path: str, params: dict, api_key: str) -> dict | list | None:
    headers = {"Authorization": f"Token {api_key}"}
    try:
        r = requests.get(f"{API_BASE}{path}", params=params, headers=headers, timeout=30)
        if r.status_code == 401:
            log.error("API key invalid — check credentials/musopen_api_key.txt")
            sys.exit(1)
        if r.status_code == 429:
            log.warning("Rate limited — waiting 60s")
            time.sleep(60)
            return None
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        log.warning(f"API error: {e}")
        return None


def search_recordings(api_key: str, composer: str = None,
                      page: int = 1, per_page: int = 20) -> list[dict]:
    params = {"limit": per_page, "page": page, "license": "public-domain"}
    if composer:
        params["composer"] = composer
    data = api_get("/recordings/", params, api_key)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("results", []) or data.get("recordings", [])
    return []


def keyword_score(piece_title: str, keywords: str) -> int:
    """Score how well a piece title matches our search keywords."""
    stopwords = {"in", "the", "a", "an", "no", "op", "and", "for", "of", "by", "to"}
    kw = set(re.sub(r"[^a-z0-9]", " ", keywords.lower()).split()) - stopwords
    tt = set(re.sub(r"[^a-z0-9]", " ", piece_title.lower()).split()) - stopwords
    return len(kw & tt)


def build_license_entry(rec: dict, filename: str = "") -> dict:
    work      = rec.get("work") or {}
    composer  = work.get("composer") or {}
    performer = (rec.get("ensemble") or {}).get("name", "") or \
                ", ".join(p.get("name", "") for p in (rec.get("performers") or []))
    return {
        "id":          f"musopen_{rec['id']}",
        "musopen_id":  rec["id"],
        "composer":    composer.get("complete_name") or composer.get("name") or "Unknown",
        "piece":       work.get("title", "Unknown"),
        "performer":   performer,
        "year":        rec.get("year") or 0,
        "source":      f"https://musopen.org/music/recordings/{rec['id']}/",
        "license":     "pd",
        "duration_sec": rec.get("duration") or 0,
        "file":        f"Music/{filename}" if filename else "",
        "programs":    [],
        "notes":       rec.get("license", ""),
    }


def download_mp3(rec: dict, api_key: str) -> str | None:
    """Download MP3. Returns filename (relative to Music/) or None."""
    url = rec.get("url") or rec.get("mp3_url") or rec.get("mp3")
    if not url:
        log.warning(f"  No download URL for {rec['id']}")
        return None

    work  = rec.get("work") or {}
    title = work.get("title", "unknown")
    safe  = re.sub(r"[^a-zA-Z0-9_\-]", "_", title)[:50].strip("_")
    fname = f"musopen_{rec['id']}_{safe}.mp3"
    dest  = MUSIC_DIR / fname

    if dest.exists() and dest.stat().st_size > 0:
        log.info(f"  Already exists: {fname}")
        return fname

    headers = {"Authorization": f"Token {api_key}"}
    try:
        r = requests.get(url, headers=headers, timeout=120, stream=True)
        if r.status_code == 403:
            log.warning(f"  Access denied (free tier limit?) for {rec['id']}")
            return None
        r.raise_for_status()
    except requests.RequestException as e:
        log.warning(f"  Download error: {e}")
        return None

    MUSIC_DIR.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)

    size_mb = dest.stat().st_size / 1024 / 1024
    if size_mb < 0.1:
        dest.unlink()
        log.warning(f"  File too small ({size_mb:.2f}MB) — likely error page, skipping")
        return None

    log.info(f"  ✓ {fname} ({size_mb:.1f} MB)")
    return fname


# ─────────────────────────────────────────────────────────────────────────────
# Priority search: find specific pieces
# ─────────────────────────────────────────────────────────────────────────────

def find_best_match(api_key: str, composer: str, keywords: str,
                    skip_ids: set) -> dict | None:
    """Search for a specific piece and return the best-matching recording."""
    best_rec, best_score = None, 0
    for page in range(1, 4):
        recs = search_recordings(api_key, composer=composer, page=page, per_page=20)
        if not recs:
            break
        for rec in recs:
            if rec["id"] in skip_ids:
                continue
            work_title = (rec.get("work") or {}).get("title", "")
            score = keyword_score(work_title, keywords)
            if score > best_score:
                best_score, best_rec = score, rec
        time.sleep(0.3)
    if best_rec and best_score >= 2:
        work_title = (best_rec.get("work") or {}).get("title", "")
        log.info(f"  Best match (score={best_score}): [{best_rec['id']}] {work_title}")
        return best_rec
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Musopen auto-downloader with daily limit")
    parser.add_argument("--limit",        type=int, default=DAILY_LIMIT,
                        help=f"Max downloads today (default: {DAILY_LIMIT} = free tier)")
    parser.add_argument("--composer",     default=None, help="Focus on one composer")
    parser.add_argument("--list-only",    action="store_true", help="Show available, no download")
    parser.add_argument("--reset-daily",  action="store_true", help="Reset today's counter")
    parser.add_argument("--api-key",      default=None)
    args = parser.parse_args()

    api_key = args.api_key or (KEY_FILE.read_text().strip() if KEY_FILE.exists() else None)
    if not api_key:
        log.error(
            "No Musopen API key.\n"
            "  1. Register:  https://musopen.org/accounts/register/\n"
            "  2. Get key:   https://musopen.org/accounts/apikey/\n"
            f"  3. Save to:   {KEY_FILE}"
        )
        sys.exit(1)

    LOG_DIR.mkdir(exist_ok=True)
    licenses_data = load_licenses()
    skip_ids      = existing_musopen_ids(licenses_data)
    state         = load_state()

    if args.reset_daily:
        state["downloaded_today"] = 0
        save_state(state)
        log.info("Daily counter reset.")

    remaining = get_daily_remaining(state, args.limit)
    log.info(f"=== Musopen Sync === today={state.get('date') or 'new day'} "
             f"downloaded_today={state.get('downloaded_today', 0)} "
             f"remaining={remaining}/{args.limit}")

    if remaining <= 0 and not args.list_only:
        log.info(f"Daily limit reached ({args.limit}/day). Run tomorrow or use --reset-daily.")
        return

    downloaded = 0
    entries_added = []

    def do_download(rec: dict, target_id: str = None) -> bool:
        """Download one recording, update state. Returns True on success."""
        nonlocal downloaded
        work_title = (rec.get("work") or {}).get("title", "")
        composer_name = ((rec.get("work") or {}).get("composer") or {}).get("complete_name", "?")
        log.info(f"  [{rec['id']}] {composer_name} — {work_title}")

        if args.list_only:
            entries_added.append(build_license_entry(rec))
            downloaded += 1
            return True

        fname = download_mp3(rec, api_key)
        entry = build_license_entry(rec, fname or "")
        if target_id:
            entry["id"] = target_id  # use our canonical ID for program matching

        if fname:
            licenses_data["recordings"].append(entry)
            skip_ids.add(rec["id"])
            state["downloaded_today"] = state.get("downloaded_today", 0) + 1
            state["total_downloaded"] = state.get("total_downloaded", 0) + 1
            state.setdefault("musopen_ids_downloaded", []).append(rec["id"])
            save_state(state)
            save_licenses(licenses_data)
            downloaded += 1
            return True
        else:
            entry["license"] = "rejected"
            entry["file"] = ""
            licenses_data["recordings"].append(entry)
            skip_ids.add(rec["id"])
            save_licenses(licenses_data)
            return False

    # ── Phase 1: Priority pieces for blocked programs ────────────────────────
    if not args.composer:
        log.info("\n── Phase 1: Priority pieces (blocked programs) ──")
        # Check which priority pieces are still missing
        existing_target_ids = {r.get("id") for r in licenses_data["recordings"]}
        missing_priority = [
            (comp, kw, tid) for comp, kw, tid in PRIORITY_PIECES
            if tid not in existing_target_ids
        ]
        log.info(f"  {len(missing_priority)} priority pieces still missing")

        for comp, keywords, target_id in missing_priority:
            if get_daily_remaining(state, args.limit) <= 0:
                log.info("  Daily limit reached — stopping priority phase")
                break
            log.info(f"\n  Searching: {comp} / {keywords}")
            rec = find_best_match(api_key, comp, keywords, skip_ids)
            if rec:
                do_download(rec, target_id=target_id)
            else:
                log.warning(f"  No match found for: {keywords}")
            time.sleep(1)

    # ── Phase 2: Wishlist composers (broaden library) ───────────────────────
    composers = [args.composer] if args.composer else WISHLIST_COMPOSERS
    remaining_slots = get_daily_remaining(state, args.limit)

    if remaining_slots > 0:
        log.info(f"\n── Phase 2: Wishlist composers ({remaining_slots} slots left) ──")
        for composer in composers:
            if get_daily_remaining(state, args.limit) <= 0:
                break
            log.info(f"\n  Composer: {composer}")
            for page in range(1, 6):
                if get_daily_remaining(state, args.limit) <= 0:
                    break
                recs = search_recordings(api_key, composer=composer, page=page, per_page=20)
                if not recs:
                    break
                for rec in recs:
                    if get_daily_remaining(state, args.limit) <= 0:
                        break
                    if rec["id"] in skip_ids:
                        continue
                    do_download(rec)
                    time.sleep(0.5)
                time.sleep(1)

    # ── Summary ──────────────────────────────────────────────────────────────
    log.info(f"\n{'='*60}")
    log.info(f"Downloaded today: {state.get('downloaded_today', 0)} / {args.limit}")
    log.info(f"Total ever: {state.get('total_downloaded', 0)}")
    log.info(f"Library size: {len(licenses_data['recordings'])} recordings")

    # Show what's still missing for blocked programs
    existing_ids_set = {r.get("id") for r in licenses_data["recordings"]}
    still_missing = [(c, kw, tid) for c, kw, tid in PRIORITY_PIECES if tid not in existing_ids_set]
    if still_missing:
        log.info(f"\nStill missing for blocked programs ({len(still_missing)}):")
        for _, kw, tid in still_missing:
            log.info(f"  ✗ {tid}: {kw}")
    else:
        log.info("\n✓ All priority pieces downloaded! focus_bach_01 + sleep_lullaby_01 unblocked.")

    if args.list_only:
        log.info(f"\n[LIST ONLY] No files downloaded. {downloaded} recordings found.")


if __name__ == "__main__":
    main()
