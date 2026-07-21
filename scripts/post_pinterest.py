#!/usr/bin/env python3
"""
Post video thumbnails to Pinterest as pins linking to YouTube.
Run after videos are published to YouTube.

Usage:
  # Post all uploaded videos not yet pinned (limit 50/run)
  python3 scripts/post_pinterest.py --all

  # Post a specific video by meta file
  python3 scripts/post_pinterest.py --meta uploaded/meta_nature_calm_forest_20260718.yaml

  # Dry run — show what would be posted
  python3 scripts/post_pinterest.py --all --dry-run

  # Re-post already pinned videos (force)
  python3 scripts/post_pinterest.py --all --force
"""
import argparse, base64, json, urllib.request, urllib.error, yaml, time, logging
from pathlib import Path

ROOT           = Path(__file__).resolve().parent.parent
UPLOADED_DIR   = ROOT / "uploaded"
TOKEN_FILE     = ROOT / "credentials" / "pinterest_token.json"

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

# Board IDs (created 2026-07-21)
BOARDS = {
    "dance":        "1134133187352883583",  # Baby Dance Videos 🐻
    "lullaby":      "1134133187352883584",  # Baby Lullabies 🌙
    "nature_calm":  "1134133187352883585",  # Nature Calm for Babies 🌿
    "song":         "1134133187352883586",  # Baby Songs & Nursery Rhymes 🎵
    "learn":        "1134133187352883587",  # Learn with Happy Bear 📚
    "ar":           "1134133187352883588",  # فيديوهات أطفال هابي بير كيدز 🐻
}

# Map video_type → board key
VIDEO_TYPE_TO_BOARD = {
    # Dance / movement
    "dance":                "dance",
    "dance_long":           "dance",
    "short_dance":          "dance",
    "emotions_ocean":       "dance",
    "special_mechanics":    "dance",
    "character_dialogue":   "dance",
    "emotional_values":     "dance",
    "ocean_creatures":      "dance",
    "shape_dance":          "dance",
    "shape_roundelay":      "dance",
    "construction_music":   "dance",
    # Lullabies / sleep
    "lullaby_long":         "lullaby",
    "sleep_lullaby":        "lullaby",
    "sleep_program":        "lullaby",
    "sleep_short":          "lullaby",
    "focus_program":        "lullaby",
    # Nature calm
    "nature_calm":          "nature_calm",
    "stars_bubbles":        "nature_calm",
    "bubble_series":        "nature_calm",
    # Songs
    "bubble_pop_song":      "song",
    "song_suno":            "song",
    "kids_song":            "song",
    "nursery_long":         "song",
    # Learn
    "color_learn":          "learn",
    "colors":               "learn",
    "number_learn":         "learn",
    "numbers":              "learn",
    "counting":             "learn",
    "shape_learn":          "learn",
    "shapes_long":          "learn",
    "short_shape":          "learn",
    "short_shape_float":    "learn",
    "short_color":          "learn",
    "short_number":         "learn",
    "short_vocab":          "learn",
    "short_letter":         "learn",
    "vocab_short":          "learn",
    "peekaboo_eggs":        "learn",
    "abc":                  "learn",
}

YOUTUBE_BASE = "https://youtu.be/"


def load_token() -> str:
    data = json.loads(TOKEN_FILE.read_text())
    return data["access_token"]


def refresh_token_if_needed(token_data: dict) -> str:
    """Refresh access token using refresh_token if expired."""
    cid    = token_data["client_id"]
    secret = token_data["client_secret"]
    rt     = token_data["refresh_token"]
    creds  = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    import urllib.parse
    data = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": rt,
    }).encode()
    req = urllib.request.Request(
        "https://api.pinterest.com/v5/oauth/token",
        data=data,
        headers={"Authorization": f"Basic {creds}",
                 "Content-Type": "application/x-www-form-urlencoded"},
    )
    r = urllib.request.urlopen(req)
    new = json.loads(r.read().decode())
    token_data["access_token"] = new["access_token"]
    TOKEN_FILE.write_text(json.dumps(token_data, indent=2))
    log.info("Token refreshed.")
    return new["access_token"]


def get_board_id(meta: dict) -> str | None:
    lang       = meta.get("language", "en")
    video_type = meta.get("video_type", "")
    if lang == "ar":
        return BOARDS["ar"]
    return BOARDS.get(VIDEO_TYPE_TO_BOARD.get(video_type, ""), None)


def pin_video(token: str, meta: dict, thumb_path: Path, dry_run: bool) -> str | None:
    """Create a Pinterest pin. Returns pin_id or None on failure."""
    board_id = get_board_id(meta)
    if not board_id:
        log.warning(f"  No board for video_type={meta.get('video_type')} lang={meta.get('language')} — skipping")
        return None

    youtube_id = meta.get("youtube_id")
    if not youtube_id:
        log.warning("  No youtube_id — skipping")
        return None

    title = meta.get("title", "")[:100]
    desc  = meta.get("description", "")[:500].split("\n")[0]  # first line only
    link  = f"{YOUTUBE_BASE}{youtube_id}"

    if not thumb_path.exists():
        log.warning(f"  Thumbnail not found: {thumb_path.name} — skipping")
        return None

    if dry_run:
        log.info(f"  [DRY RUN] pin → board {board_id} | {title[:50]} | {link}")
        return "dry_run"

    # Step 1: upload image to Pinterest media
    with open(thumb_path, "rb") as f:
        img_bytes = f.read()

    # Pinterest requires multipart upload for images
    # Using media_source type = image_base64
    import base64 as b64mod
    img_b64 = b64mod.b64encode(img_bytes).decode()

    body = {
        "board_id": board_id,
        "title": title,
        "description": desc,
        "link": link,
        "media_source": {
            "source_type": "image_base64",
            "content_type": "image/png",
            "data": img_b64,
        },
    }
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        "https://api.pinterest.com/v5/pins",
        data=data,
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json"},
        method="POST",
    )
    try:
        r = urllib.request.urlopen(req)
        resp = json.loads(r.read().decode())
        pin_id = resp.get("id")
        log.info(f"  ✓ pin {pin_id} → https://pinterest.com/pin/{pin_id}/")
        return pin_id
    except urllib.error.HTTPError as e:
        body_err = e.read().decode()
        log.error(f"  ✗ Pinterest API error {e.code}: {body_err[:200]}")
        return None


def process_meta(meta_path: Path, token: str, dry_run: bool, force: bool) -> bool:
    meta = yaml.safe_load(meta_path.read_text()) or {}
    if not meta.get("youtube_id"):
        return False
    if meta.get("pinterest_pin_id") and not force:
        return False
    # Skip Calm Classics (id channel) — separate Pinterest account later
    if meta.get("language") == "id":
        return False

    stem       = meta_path.stem.replace("meta_", "")
    thumb_path = meta_path.parent / f"thumb_{stem}.png"

    log.info(f"  {meta.get('title', stem)[:60]}")
    pin_id = pin_video(token, meta, thumb_path, dry_run)
    if pin_id and pin_id != "dry_run":
        meta["pinterest_pin_id"] = pin_id
        with open(meta_path, "w") as f:
            yaml.dump(meta, f, allow_unicode=True, default_flow_style=False)
    return bool(pin_id)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all",      action="store_true", help="Post all uploaded videos not yet pinned")
    parser.add_argument("--meta",     help="Path to specific meta YAML file")
    parser.add_argument("--dry-run",  action="store_true")
    parser.add_argument("--force",    action="store_true", help="Re-post even if already pinned")
    parser.add_argument("--limit",    type=int, default=50, help="Max pins per run (default 50)")
    args = parser.parse_args()

    token_data = json.loads(TOKEN_FILE.read_text())
    token = token_data["access_token"]

    if args.meta:
        mp = Path(args.meta)
        process_meta(mp, token, args.dry_run, args.force)
        return

    if args.all:
        metas = sorted(UPLOADED_DIR.glob("meta_*.yaml"))
        pending = []
        for mp in metas:
            m = yaml.safe_load(mp.read_text()) or {}
            if not m.get("youtube_id"):
                continue
            if m.get("pinterest_pin_id") and not args.force:
                continue
            if m.get("language") == "id":
                continue
            pending.append(mp)

        print(f"\n=== Pinterest: {len(pending)} videos to pin (limit {args.limit}) ===\n")
        if len(pending) > args.limit:
            pending = pending[:args.limit]

        ok = 0
        for mp in pending:
            if process_meta(mp, token, args.dry_run, args.force):
                ok += 1
            time.sleep(1)  # avoid rate limiting
        print(f"\nDone: {ok}/{len(pending)} pinned")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
