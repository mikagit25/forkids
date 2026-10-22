#!/usr/bin/env python3
"""
Patch titles and descriptions of published Sacred Drift videos.

Fixes:
  1. Titles: round duration ("1 Hour 5 Min" → "1 Hour"), replace "—" with "•",
     remove "| Sacred Drift" suffix
  2. Descriptions (AI compilations only): update boilerplate wording,
     add "Music created with AI tools." disclosure, remove medical claims
  3. Category: 10 (Music) for all SD videos

Usage:
    python3 scripts/update_sd_titles.py --dry-run   # preview only
    python3 scripts/update_sd_titles.py             # live update
    python3 scripts/update_sd_titles.py --id VIDEO_ID  # single video
"""

import argparse, logging, re, sys, time
from pathlib import Path

import yaml
from googleapiclient.errors import HttpError

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from upload_youtube import get_youtube_service, load_config

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

UPLOADED_DIR = ROOT / "uploaded"

# ── Title transformation ──────────────────────────────────────────────────────

def _round_dur(m: re.Match) -> str:
    """Convert 'X Hour(s) Y Min' / 'X hour Y min(utes)' to '• N Hour(s)'."""
    h = int(m.group(1))
    if h < 1:
        h = 1
    return f"• {h} Hour" if h == 1 else f"• {h} Hours"

_DUR_PAT = re.compile(
    r'[—–\-]?\s*(\d+)\s+[Hh]our[s]?\s+\d+\s+[Mm]in(?:utes?)?\s*',
    re.IGNORECASE
)
_DUR_PAT2 = re.compile(
    r'[—–\-]?\s*(\d+)\s+[Hh]our[s]?\s+\d+\s+[Mm]inutes?\s*',
    re.IGNORECASE
)
# "1 hour 2 minutes" (lowercase, no leading dash)
_DUR_PAT3 = re.compile(
    r'[—–]?\s*(\d+)\s+hour[s]?\s+\d+\s+minute[s]?\s*',
    re.IGNORECASE
)

def fix_title(title: str) -> str:
    """Return corrected title, or same string if already correct."""
    t = title

    # 1. Round duration patterns (various forms)
    for pat in (_DUR_PAT, _DUR_PAT2, _DUR_PAT3):
        t = pat.sub(lambda m: f" {_round_dur(m)} ", t)

    # 2. Strip "| Sacred Drift" — at end OR before #shorts (keep space before hashtag)
    t = re.sub(r'\s*[\|]\s*Sacred Drift\s+(?=#shorts)', ' ', t, flags=re.IGNORECASE)
    t = re.sub(r'\s*[\|]\s*Sacred Drift\s*$', '', t, flags=re.IGNORECASE)

    # 3. Replace "—" separator before "•" duration if still present
    t = re.sub(r'\s+—\s+(•)', r' \1', t)

    # 4. "Rain & Water Meditation" → "Rain & Water Ambience" (mixed content)
    t = t.replace('Rain & Water Meditation', 'Rain & Water Ambience')

    # 5. "Heart Chakra Opening" → "Heart Chakra Meditation" (display name fix)
    t = t.replace('Heart Chakra Opening', 'Heart Chakra Meditation')

    # 6. "— N Hour" → "• N Hour" (em-dash separator before hour)
    t = re.sub(r'\s+—\s+(\d+ Hour)', r' • \1', t)

    # 7. Tidy multiple spaces
    t = re.sub(r' {2,}', ' ', t).strip()

    return t


# ── Description transformation ────────────────────────────────────────────────

def fix_description(desc: str, is_classical: bool) -> str:
    """Patch boilerplate in SD descriptions."""
    d = desc

    # Round "1 hour X min" in body text
    d = re.sub(
        r'(\d+) hour[s]? (\d+) min(?:utes?)?',
        lambda m: f"{m.group(1)} hour{'s' if int(m.group(1)) != 1 else ''}",
        d, flags=re.IGNORECASE
    )

    # "Ideal for" line — replace "healing" use and add study
    d = d.replace(
        "Ideal for: meditation, sleep, healing, relaxation",
        "Ideal for: meditation, sleep, relaxation, study"
    )

    # "healing frequencies, chakra" → "solfeggio frequencies, chakra"
    d = d.replace(
        "healing frequencies, chakra music and sacred soundscapes",
        "solfeggio frequencies, chakra music and sacred soundscapes"
    )

    # Add AI disclosure for non-classical content
    if not is_classical:
        if "Music created with AI tools" not in d:
            # Insert before last newlines / footer
            d = d.rstrip()
            d += "\n\n🎶 Music created with AI tools."

    return d


# ── Main ──────────────────────────────────────────────────────────────────────

def load_meta(path: Path) -> dict:
    return yaml.safe_load(path.read_text()) or {}


def update_video(yt, video_id: str, meta: dict, meta_path: Path, dry_run: bool):
    stem = meta_path.stem.replace("meta_", "")
    is_classical = "classical" in stem or "franck" in stem or "wagner" in stem

    old_title = meta.get("title", "")
    new_title  = fix_title(old_title)

    old_desc  = meta.get("description", "")
    new_desc  = fix_description(old_desc, is_classical)

    title_changed = new_title != old_title
    desc_changed  = new_desc  != old_desc

    if not title_changed and not desc_changed:
        log.info(f"  SKIP (no changes): {video_id} — {old_title[:60]}")
        return True

    log.info(f"\n  {'[DRY] ' if dry_run else ''}Video: {video_id}")
    if title_changed:
        log.info(f"    OLD: {old_title[:80]}")
        log.info(f"    NEW: {new_title[:80]}")
    if desc_changed:
        log.info(f"    DESC: patched ({'classical' if is_classical else 'AI'})")

    if dry_run:
        return True

    try:
        body = {
            "id": video_id,
            "snippet": {
                "title":       new_title[:100],
                "description": new_desc[:5000],
                "tags":        meta.get("tags", [])[:500],
                "categoryId":  "10",  # Music
            },
        }
        yt.videos().update(part="snippet", body=body).execute()
        log.info(f"    ✓ Updated on YouTube")
    except HttpError as e:
        if "quotaExceeded" in str(e):
            log.error("YouTube quota exceeded — stopping")
            return False
        log.error(f"    ✗ HTTP error: {e}")
        return True  # skip this one, continue

    # Update local meta
    meta["title"] = new_title
    meta["description"] = new_desc
    meta_path.write_text(yaml.dump(meta, allow_unicode=True, default_flow_style=False))
    log.info(f"    ✓ Meta saved")

    time.sleep(0.5)  # gentle rate limit
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--id", dest="video_id", help="Update single video ID")
    args = ap.parse_args()

    config = load_config()
    yt = get_youtube_service(config, channel="ar")  # Sacred Drift uses youtube_token_ar.json

    metas = sorted(UPLOADED_DIR.glob("meta_sd_*.yaml"))
    log.info(f"Found {len(metas)} uploaded SD meta files")

    ok = err = skip = 0
    for mp in metas:
        meta = load_meta(mp)
        vid = meta.get("youtube_id")
        if not vid:
            skip += 1
            continue
        if args.video_id and vid != args.video_id:
            continue
        result = update_video(yt, vid, meta, mp, args.dry_run)
        if result:
            ok += 1
        else:
            err += 1
            break  # quota exceeded — stop

    log.info(f"\nDone: {ok} updated, {err} errors, {skip} skipped (no youtube_id)")


if __name__ == "__main__":
    main()
