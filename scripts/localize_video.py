#!/usr/bin/env python3
"""
Add YouTube localizations to already-published EN videos.

Translates title + description to ES, FR, PT, ID using Together.ai LLM,
then calls YouTube Data API videos.update with the 'localizations' part.

Note: YouTube localizations do NOT support per-language tags — tags stay global.

Usage:
    python3 scripts/localize_video.py --video-id VIDEO_ID_HERE
    python3 scripts/localize_video.py --meta output/queue/meta_myfile.yaml
    python3 scripts/localize_video.py --meta output/queue/meta_myfile.yaml --langs es,fr
    python3 scripts/localize_video.py --queue          # all meta in output/queue/ with youtube_id set
    python3 scripts/localize_video.py --queue --dry-run
"""

import argparse
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

TOGETHER_KEY_FILE = ROOT / "credentials" / "together_api_key.txt"
TOGETHER_CHAT_URL = "https://api.together.xyz/v1/chat/completions"
TOGETHER_TEXT_MODEL = "meta-llama/Llama-3.3-70B-Instruct-Turbo"

# BCP-47 codes and display names for YouTube localizations
LANG_MAP = {
    "es": "Spanish",
    "fr": "French",
    "pt": "Portuguese (Brazilian)",
    "id": "Indonesian (Bahasa)",
}
ALL_LANGS = list(LANG_MAP.keys())

QUEUE_DIR = ROOT / "output" / "queue"


# ── Together.ai text API ──────────────────────────────────────────────────────

def _together_key() -> str:
    return TOGETHER_KEY_FILE.read_text().strip()


def translate_field(text: str, target_lang: str, field: str, api_key: str) -> str:
    lang_name = LANG_MAP[target_lang]
    if field == "title":
        instruction = (
            f"Translate this YouTube video title for toddlers into {lang_name}. "
            "Keep it short (under 100 chars), fun, and child-friendly. "
            "Keep emojis as-is. Return only the translated title, no quotes, no explanation."
        )
    else:
        instruction = (
            f"Translate this YouTube video description for a toddler/baby channel into {lang_name}. "
            "Keep the same structure, tone, and emojis. Keep hashtags in English at the end. "
            "Keep channel handles (@ symbols) unchanged. "
            "Return only the translated description, no extra commentary."
        )

    payload = json.dumps({
        "model": TOGETHER_TEXT_MODEL,
        "messages": [
            {"role": "system", "content": instruction},
            {"role": "user",   "content": text},
        ],
        "temperature": 0.3,
        "max_tokens": 1024,
    }).encode()

    req = urllib.request.Request(
        TOGETHER_CHAT_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())

    return data["choices"][0]["message"]["content"].strip()


def translate_meta(title: str, description: str, langs: list[str], api_key: str) -> dict:
    """Return {lang_code: {title, description}} for all requested langs."""
    result = {}
    for lang in langs:
        print(f"  Translating → {lang} ({LANG_MAP[lang]})...")
        t_title = translate_field(title, lang, "title", api_key)
        t_desc  = translate_field(description, lang, "description", api_key)
        result[lang] = {"title": t_title, "description": t_desc}
        print(f"    Title: {t_title[:60]}...")
    return result


# ── YouTube API ───────────────────────────────────────────────────────────────

def _get_youtube_service():
    import pickle
    import datetime as _dt
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    SCOPES = [
        "https://www.googleapis.com/auth/youtube",
        "https://www.googleapis.com/auth/youtube.force-ssl",
    ]
    json_path   = ROOT / "credentials" / "youtube_token.json"
    pickle_path = ROOT / "credentials" / "token.pickle"

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
            "No EN token found. Run:\n  python3 scripts/reauth_youtube.py --channel en"
        )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    return build("youtube", "v3", credentials=creds)


def push_localizations(video_id: str, localizations: dict, dry_run: bool = False):
    """Upload localizations dict {lang: {title, description}} to YouTube."""
    if dry_run:
        print(f"  [dry-run] Would update video {video_id} with localizations:")
        for lang, vals in localizations.items():
            print(f"    {lang}: {vals['title'][:60]}...")
        return

    youtube = _get_youtube_service()
    body = {
        "id": video_id,
        "localizations": localizations,
    }
    response = youtube.videos().update(
        part="localizations",
        body=body,
    ).execute()
    print(f"  ✓ Updated video {video_id} — localizations set for: {list(localizations.keys())}")
    return response


# ── Meta file helpers ─────────────────────────────────────────────────────────

def load_meta(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def save_localized_langs(meta_path: Path, langs: list[str]):
    """Write 'localized_langs' list back to meta YAML so we don't re-translate."""
    meta = load_meta(meta_path)
    existing = set(meta.get("localized_langs", []))
    meta["localized_langs"] = sorted(existing | set(langs))
    with open(meta_path, "w") as f:
        yaml.dump(meta, f, allow_unicode=True, sort_keys=False, default_flow_style=False)


def find_queue_metas_with_id(queue_dir: Path) -> list[Path]:
    metas = []
    for p in sorted(queue_dir.glob("meta_*.yaml")):
        try:
            data = load_meta(p)
            if data.get("youtube_id"):
                metas.append(p)
        except Exception:
            pass
    return metas


# ── Main ──────────────────────────────────────────────────────────────────────

def process_one(video_id: str, title: str, description: str,
                langs: list[str], api_key: str,
                dry_run: bool, meta_path: Path = None):
    print(f"\nVideo: {video_id}")
    print(f"Title: {title[:70]}")

    localizations = translate_meta(title, description, langs, api_key)
    push_localizations(video_id, localizations, dry_run=dry_run)

    if meta_path and not dry_run:
        save_localized_langs(meta_path, langs)
        print(f"  ✓ Wrote localized_langs to {meta_path.name}")


def main():
    parser = argparse.ArgumentParser(description="Add YouTube localizations to EN videos")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--video-id", help="YouTube video ID to localize")
    group.add_argument("--meta",     help="Path to meta YAML (reads title/description/youtube_id)")
    group.add_argument("--queue",    action="store_true",
                       help="Process all meta files in output/queue/ that have youtube_id set")

    parser.add_argument("--langs", default=",".join(ALL_LANGS),
                        help=f"Comma-separated language codes. Default: {','.join(ALL_LANGS)}")
    parser.add_argument("--title",       help="Title override (only with --video-id)")
    parser.add_argument("--description", help="Description override (only with --video-id)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show translations without updating YouTube")
    args = parser.parse_args()

    langs = [l.strip() for l in args.langs.split(",") if l.strip() in LANG_MAP]
    if not langs:
        print(f"Error: no valid language codes. Choose from: {','.join(ALL_LANGS)}")
        sys.exit(1)

    if not TOGETHER_KEY_FILE.exists():
        print(f"Error: {TOGETHER_KEY_FILE} not found")
        sys.exit(1)
    api_key = _together_key()

    if args.video_id:
        title = args.title or "Happy Bear Kids Video"
        desc  = args.description or ""
        if not title or not desc:
            print("Error: --title and --description are required with --video-id")
            sys.exit(1)
        process_one(args.video_id, title, desc, langs, api_key, args.dry_run)

    elif args.meta:
        meta_path = Path(args.meta)
        meta = load_meta(meta_path)
        video_id = meta.get("youtube_id", "")
        if not video_id:
            print(f"Error: no youtube_id in {meta_path}")
            sys.exit(1)
        already = set(meta.get("localized_langs", []))
        todo = [l for l in langs if l not in already]
        if not todo:
            print(f"All requested langs already localized: {langs}")
            return
        process_one(video_id, meta["title"], meta["description"],
                    todo, api_key, args.dry_run, meta_path)

    else:  # --queue
        metas = find_queue_metas_with_id(QUEUE_DIR)
        print(f"Found {len(metas)} meta files with youtube_id in {QUEUE_DIR}")
        ok = err = skip = 0
        for meta_path in metas:
            meta = load_meta(meta_path)
            already = set(meta.get("localized_langs", []))
            todo = [l for l in langs if l not in already]
            if not todo:
                skip += 1
                continue
            try:
                process_one(meta["youtube_id"], meta["title"], meta["description"],
                            todo, api_key, args.dry_run, meta_path)
                ok += 1
            except Exception as e:
                print(f"  ERROR {meta_path.name}: {e}")
                err += 1

        print(f"\nDone: {ok} updated, {skip} already localized, {err} errors")


if __name__ == "__main__":
    main()
