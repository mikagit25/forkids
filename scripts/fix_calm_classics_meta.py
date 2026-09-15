#!/usr/bin/env python3
"""
One-off script: fix 'Calm Classics' → 'Classical Night Relax' in all published videos.
Updates YouTube title + description + tags via API, then patches local meta files.

Usage:
  python3 scripts/fix_calm_classics_meta.py --dry-run   # preview only
  python3 scripts/fix_calm_classics_meta.py             # apply
  python3 scripts/fix_calm_classics_meta.py --titles-only  # only fix titles (23 videos)
"""
import argparse, json, logging, re, time, yaml
from pathlib import Path
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

ROOT       = Path(__file__).resolve().parent.parent
UPLOADED   = ROOT / "uploaded"
CRED_PATH  = ROOT / "credentials" / "youtube_token_id.json"
DONE_LOG   = ROOT / "logs" / "fix_calm_classics_done.json"
QUOTA_COST = 50   # videos.update() = 50 units
DAILY_CAP  = 8000 # leave buffer; full quota is 10000

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def _fix_text(text: str) -> str:
    """Apply all Calm Classics → Classical Night Relax replacements."""
    # Titles: remove • No Ads, replace Calm Classics
    text = text.replace("• No Ads | Calm Classics", "| Classical Night Relax")
    text = text.replace("• No Ads | Classical Night Relax", "| Classical Night Relax")
    text = re.sub(r"\s*•\s*No Ads", "", text)
    text = text.replace("| Calm Classics", "| Classical Night Relax")
    text = text.replace("Calm Classics", "Classical Night Relax")
    # Lowercase form in descriptions/hashtags
    text = text.replace("calm classics", "classical night relax")
    text = text.replace("#CalmClassics", "#ClassicalNightRelax")
    return text


def _fix_tags(tags: list) -> list:
    return [_fix_text(t) for t in tags]


def _needs_fix(data: dict) -> bool:
    haystack = (
        data.get("title", "") + " " +
        data.get("description", "") + " " +
        " ".join(data.get("tags", []))
    )
    return "Calm Classics" in haystack or "calm classics" in haystack


def _get_youtube():
    creds_data = json.loads(CRED_PATH.read_text())
    creds = Credentials(
        token=creds_data.get("token"),
        refresh_token=creds_data.get("refresh_token"),
        token_uri=creds_data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=creds_data.get("client_id"),
        client_secret=creds_data.get("client_secret"),
        scopes=creds_data.get("scopes", ["https://www.googleapis.com/auth/youtube"]),
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        creds_data["token"] = creds.token
        CRED_PATH.write_text(json.dumps(creds_data, indent=2))
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def update_video(yt, video_id: str, title: str, description: str, tags: list, dry_run: bool) -> bool:
    if dry_run:
        log.info(f"  [DRY] Would update {video_id}: {title[:60]}")
        return True
    try:
        yt.videos().update(
            part="snippet",
            body={
                "id": video_id,
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": tags,
                    "categoryId": "10",  # Music
                },
            },
        ).execute()
        return True
    except Exception as e:
        log.error(f"  API error for {video_id}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--titles-only", action="store_true", help="Only update videos with Calm Classics in title")
    parser.add_argument("--limit", type=int, default=0, help="Stop after N updates (0=all)")
    args = parser.parse_args()

    done_ids = set()
    DONE_LOG.parent.mkdir(exist_ok=True)
    if DONE_LOG.exists():
        done_ids = set(json.loads(DONE_LOG.read_text()))

    meta_files = sorted(UPLOADED.glob("meta_*.yaml"))
    to_fix = []

    for f in meta_files:
        txt = f.read_text(encoding="utf-8")
        if "Calm Classics" not in txt and "calm classics" not in txt:
            continue
        try:
            data = yaml.safe_load(txt)
        except Exception:
            continue
        yt_id = data.get("youtube_id")
        if not yt_id or yt_id in done_ids:
            continue
        if not _needs_fix(data):
            continue
        if args.titles_only:
            title = data.get("title", "")
            if "Calm Classics" not in title and "• No Ads" not in title:
                continue
        to_fix.append((f, data, yt_id))

    log.info(f"Videos to fix: {len(to_fix)} (~{len(to_fix) * QUOTA_COST} quota units)")

    if not to_fix:
        log.info("Nothing to fix.")
        return

    yt = None if args.dry_run else _get_youtube()
    units_used = 0
    updated = 0

    for meta_path, data, yt_id in to_fix:
        if args.limit and updated >= args.limit:
            log.info(f"Reached --limit {args.limit}, stopping.")
            break
        if not args.dry_run and units_used + QUOTA_COST > DAILY_CAP:
            log.warning(f"Approaching quota cap ({units_used}/{DAILY_CAP} units), stopping.")
            break

        old_title = data.get("title", "")
        new_title = _fix_text(old_title)
        new_desc  = _fix_text(data.get("description", ""))
        new_tags  = _fix_tags(data.get("tags", []))

        changed = (new_title != old_title or new_desc != data.get("description","") or
                   new_tags != data.get("tags",[]))
        if not changed:
            continue

        log.info(f"\n[{updated+1}/{len(to_fix)}] {yt_id}")
        if new_title != old_title:
            log.info(f"  Title: {old_title[:70]}")
            log.info(f"    → {new_title[:70]}")

        ok = update_video(yt, yt_id, new_title, new_desc, new_tags, args.dry_run)
        if ok:
            units_used += QUOTA_COST
            updated += 1

            # Patch local meta file
            data["title"] = new_title
            data["description"] = new_desc
            data["tags"] = new_tags
            if not args.dry_run:
                meta_path.write_text(
                    yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False),
                    encoding="utf-8"
                )
                done_ids.add(yt_id)
                DONE_LOG.write_text(json.dumps(sorted(done_ids), indent=2))

            time.sleep(0.5)  # gentle rate limit
        else:
            log.warning(f"  Skipping {yt_id} due to API error")

    log.info(f"\nDone: {updated} updated, {units_used} quota units used.")
    if args.dry_run:
        log.info("(dry-run — no changes made)")


if __name__ == "__main__":
    main()
