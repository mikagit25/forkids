#!/usr/bin/env python3
"""
Add YouTube localizations to already-published videos (EN kids or Calm Classics).

Translates title + description to ES, FR, PT, ID using Together.ai LLM,
then calls YouTube Data API videos.update with the 'localizations' part.

Note: YouTube localizations do NOT support per-language tags — tags stay global.

Usage:
    python3 scripts/localize_video.py --video-id VIDEO_ID_HERE
    python3 scripts/localize_video.py --video-id VIDEO_ID_HERE --channel id
    python3 scripts/localize_video.py --meta output/queue/meta_myfile.yaml
    python3 scripts/localize_video.py --meta output/queue_id/meta_myfile.yaml --channel id
    python3 scripts/localize_video.py --meta output/queue/meta_myfile.yaml --langs es,fr
    python3 scripts/localize_video.py --queue             # EN kids channel
    python3 scripts/localize_video.py --queue --channel id  # Calm Classics
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

# Primary: local Ollama (no rate limits, no API key)
OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "translategemma:4b"

# Fallback: Groq cloud
GROQ_CHAT_URL  = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL     = "openai/gpt-oss-20b"
_GROQ_KEY_FILE = Path(__file__).resolve().parent.parent / "credentials" / "groq_api_keys.txt"
GROQ_KEYS = [k.strip() for k in _GROQ_KEY_FILE.read_text().splitlines() if k.strip()] if _GROQ_KEY_FILE.exists() else []
_groq_idx = 0

# BCP-47 codes and display names for YouTube localizations
LANG_MAP = {
    "es": "Spanish",
    "fr": "French",
    "pt": "Portuguese (Brazilian)",
    "id": "Indonesian (Bahasa)",
    "de": "German",
    "it": "Italian",
    "ja": "Japanese",
    "ru": "Russian",
    "ko": "Korean",
    "zh-Hans": "Chinese (Simplified)",
    "ar": "Arabic (Modern Standard)",
}
ALL_LANGS = list(LANG_MAP.keys())

# Default language sets per channel type
LANGS_BY_CHANNEL = {
    "en": ["es", "fr", "pt", "id"],
    "id": ["de", "it", "ja", "ru", "es", "fr", "pt", "ko", "ar"],
    # Sacred Drift — all 11 global markets
    "sd": ["es", "fr", "pt", "id", "de", "it", "ja", "ru", "ko", "zh-Hans", "ar"],
}

# Per-channel config: token paths and queue directory
CHANNEL_CONFIG = {
    "en": {
        "json":       ROOT / "credentials" / "youtube_token.json",
        "pickle":     ROOT / "credentials" / "token.pickle",
        "queue_dir":  ROOT / "output" / "queue",
        "type":       "kids",
        "reauth":     "--channel en",
        "default_langs": LANGS_BY_CHANNEL["en"],
    },
    "id": {
        "json":       ROOT / "credentials" / "youtube_token_id.json",
        "pickle":     ROOT / "credentials" / "token_id.pickle",
        "queue_dir":  ROOT / "output" / "queue_id",
        "type":       "adult",
        "reauth":     "--channel id",
        "default_langs": LANGS_BY_CHANNEL["id"],
    },
    "sd": {
        "json":       ROOT / "credentials" / "youtube_token_ar.json",
        "pickle":     ROOT / "credentials" / "token_ar.pickle",
        "queue_dir":  ROOT / "sacred_drift" / "output" / "queue",
        "type":       "adult",
        "reauth":     "--channel ar",
        "default_langs": LANGS_BY_CHANNEL["sd"],
    },
}


# ── Groq text API (with key rotation) ────────────────────────────────────────

def _next_groq_key() -> str:
    global _groq_idx
    key = GROQ_KEYS[_groq_idx % len(GROQ_KEYS)]
    _groq_idx += 1
    return key


LANG_CODES = {
    "es": "es", "fr": "fr", "pt": "pt", "id": "id",
    "de": "de", "it": "it", "ja": "ja", "ru": "ru", "ko": "ko",
    "zh-Hans": "zh", "ar": "ar",
}

COMPOSER_NAMES: dict[str, dict[str, str]] = {
    "ru": {
        "Chopin": "Шопен", "Bach": "Бах", "Beethoven": "Бетховен",
        "Mozart": "Моцарт", "Schubert": "Шуберт", "Tchaikovsky": "Чайковский",
        "Vivaldi": "Вивальди", "Wagner": "Вагнер", "Debussy": "Дебюсси",
        "Handel": "Гендель", "Brahms": "Брамс", "Liszt": "Лист",
        "Franck": "Франк", "Haydn": "Гайдн", "Mendelssohn": "Мендельсон",
        "Rachmaninoff": "Рахманинов", "Satie": "Сати", "Ravel": "Равель",
    },
    "ja": {
        "Chopin": "ショパン", "Bach": "バッハ", "Beethoven": "ベートーヴェン",
        "Mozart": "モーツァルト", "Schubert": "シューベルト", "Tchaikovsky": "チャイコフスキー",
        "Vivaldi": "ヴィヴァルディ", "Wagner": "ワーグナー", "Debussy": "ドビュッシー",
        "Handel": "ヘンデル", "Brahms": "ブラームス", "Liszt": "リスト",
        "Franck": "フランク", "Haydn": "ハイドン", "Mendelssohn": "メンデルスゾーン",
        "Rachmaninoff": "ラフマニノフ", "Satie": "サティ", "Ravel": "ラヴェル",
    },
    "ko": {
        "Chopin": "쇼팽", "Bach": "바흐", "Beethoven": "베토벤",
        "Mozart": "모차르트", "Schubert": "슈베르트", "Tchaikovsky": "차이콥스키",
        "Vivaldi": "비발디", "Wagner": "바그너", "Debussy": "드뷔시",
        "Handel": "헨델", "Brahms": "브람스", "Liszt": "리스트",
        "Franck": "프랑크", "Haydn": "하이든", "Mendelssohn": "멘델스존",
        "Rachmaninoff": "라흐마니노프", "Satie": "사티", "Ravel": "라벨",
    },
    "ar": {
        "Chopin": "شوبان", "Bach": "باخ", "Beethoven": "بيتهوفن",
        "Mozart": "موتسارت", "Schubert": "شوبيرت", "Tchaikovsky": "تشايكوفسكي",
        "Vivaldi": "فيفالدي", "Wagner": "فاغنر", "Debussy": "ديبوسي",
        "Handel": "هاندل", "Brahms": "برامز", "Liszt": "ليست",
        "Franck": "فرانك", "Haydn": "هايدن", "Mendelssohn": "مندلسون",
        "Rachmaninoff": "راخمانينوف", "Satie": "ساتي", "Ravel": "رافيل",
    },
}

NON_LATIN_LANGS = {"ru", "ja", "ko", "ar"}


def _fix_composer_names(text: str, lang: str) -> str:
    for english, native in COMPOSER_NAMES.get(lang, {}).items():
        text = text.replace(english, native)
    if lang == "ru":
        text = text.replace("Чопин", "Шопен").replace("Шопин", "Шопен")
    return text


def _composer_hint(lang: str) -> str:
    names = COMPOSER_NAMES.get(lang, {})
    if not names:
        return ""
    examples = ", ".join(f"{v} ({k})" for k, v in list(names.items())[:8])
    return f"Use standard transliterations for composer names: {examples}. "


def translate_field(text: str, target_lang: str, field: str,
                    api_key: str = None, channel_type: str = "kids") -> str:
    lang_name = LANG_MAP[target_lang]
    lang_code = LANG_CODES.get(target_lang, target_lang)
    is_arabic = target_lang == "ar"
    non_latin = target_lang in NON_LATIN_LANGS
    composer_hint = _composer_hint(target_lang) if non_latin else (
        "Do not translate instrument names (Cello, Piano, Violin) or composer names. "
    )

    if field == "title":
        if channel_type == "adult":
            extra = (
                "Keep under 100 chars. Keep emojis unchanged. "
                + composer_hint
                + ("Use Modern Standard Arabic (فصحى). " if is_arabic else "")
                + "Return only the translated title."
            )
        else:
            extra = (
                "Keep under 100 chars. Keep emojis unchanged. "
                + ("Use Modern Standard Arabic (فصحى). " if is_arabic else "")
                + "Return only the translated title."
            )
    else:
        if channel_type == "adult":
            extra = (
                "Keep the same structure and emojis. "
                + composer_hint
                + "Keep opus numbers (Op., No.) unchanged. "
                + "Keep all hashtags in English unchanged at the end. "
                + "Keep channel handles (e.g. @ClassicalNightRelax) unchanged. "
                + ("Use Modern Standard Arabic (فصحى). " if is_arabic else "")
                + "Return only the translated text."
            )
        else:
            extra = (
                "Keep the same structure and emojis. "
                "Keep hashtags in English unchanged at the end. "
                "Keep channel handles unchanged. "
                + ("Use Modern Standard Arabic (فصحى). " if is_arabic else "")
                + "Return only the translated text."
            )

    prompt = (
        f"You are a professional English (en) to {lang_name} ({lang_code}) translator. {extra}"
        f"\n\n\n{text}"
    )
    instruction = prompt.rsplit("\n\n\n", 1)[0]

    # Try Ollama first (translategemma:4b — specialized translation model, 55 languages)
    try:
        payload = json.dumps({
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 1000},
        }).encode()
        req = urllib.request.Request(
            OLLAMA_URL, data=payload,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read())
        return _fix_composer_names(data["response"].strip(), target_lang)
    except Exception as ollama_err:
        print(f"    Ollama unavailable ({ollama_err}), falling back to Groq...")

    # Fallback: Groq cloud
    groq_messages = [
        {"role": "system", "content": instruction},
        {"role": "user",   "content": text},
    ]
    for attempt in range(len(GROQ_KEYS) * 2):
        groq_key = _next_groq_key()
        payload = json.dumps({
            "model": GROQ_MODEL,
            "messages": groq_messages,
            "temperature": 0.3,
            "max_tokens": 2500,
        }).encode()
        req = urllib.request.Request(
            GROQ_CHAT_URL,
            data=payload,
            headers={
                "Authorization": f"Bearer {groq_key}",
                "Content-Type": "application/json",
                "User-Agent": "python-requests/2.31.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
            return _fix_composer_names(data["choices"][0]["message"]["content"].strip(), target_lang)
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="ignore")[:200]
            if e.code == 429:
                if attempt > 0 and attempt % len(GROQ_KEYS) == 0:
                    import time as _t; _t.sleep(65)
                else:
                    import time as _t; _t.sleep(2)
            else:
                raise RuntimeError(f"Groq HTTP {e.code}: {body}") from e
    raise RuntimeError("All Groq keys exhausted")


def translate_meta(title: str, description: str, langs: list[str],
                   api_key: str = None, channel_type: str = "kids") -> dict:
    """Return {lang_code: {title, description}} for all requested langs."""
    result = {}
    for lang in langs:
        print(f"  Translating → {lang} ({LANG_MAP[lang]})...")
        t_title = translate_field(title, lang, "title", api_key, channel_type)
        t_desc  = translate_field(description, lang, "description", api_key, channel_type)
        result[lang] = {"title": t_title, "description": t_desc}
        print(f"    Title: {t_title[:60]}...")
    return result


# ── YouTube API ───────────────────────────────────────────────────────────────

def _get_youtube_service(channel: str = "en"):
    import pickle
    import datetime as _dt
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    SCOPES = [
        "https://www.googleapis.com/auth/youtube",
        "https://www.googleapis.com/auth/youtube.force-ssl",
    ]
    cfg         = CHANNEL_CONFIG[channel]
    json_path   = cfg["json"]
    pickle_path = cfg["pickle"]

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
            print(f"  Warning: JSON token load failed [{channel}]: {e}")
            creds = None

    if creds is None and pickle_path.exists():
        with open(pickle_path, "rb") as f:
            creds = pickle.load(f)

    if not creds:
        raise RuntimeError(
            f"No token for channel '{channel}'. Run:\n"
            f"  python3 scripts/reauth_youtube.py {cfg['reauth']}"
        )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    return build("youtube", "v3", credentials=creds)


def push_localizations(video_id: str, localizations: dict,
                       channel: str = "en", dry_run: bool = False):
    """Merge new localizations into existing ones and push to YouTube."""
    if dry_run:
        print(f"  [dry-run] Would update video {video_id} [{channel}] with localizations:")
        for lang, vals in localizations.items():
            print(f"    {lang}: {vals['title'][:60]}...")
        return

    youtube = _get_youtube_service(channel)
    # Fetch existing localizations first — YouTube requires all of them in the body
    existing_resp = youtube.videos().list(part="localizations", id=video_id).execute()
    existing = {}
    if existing_resp.get("items"):
        existing = existing_resp["items"][0].get("localizations", {})
    existing.update(localizations)

    youtube.videos().update(
        part="localizations",
        body={"id": video_id, "localizations": existing},
    ).execute()
    print(f"  ✓ Updated video {video_id} — localizations: {list(localizations.keys())}")


# ── Meta file helpers ─────────────────────────────────────────────────────────

def load_meta(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def save_localized_langs(meta_path: Path, langs: list[str]):
    """Append langs to 'localized_langs' in meta YAML to skip on next run."""
    meta = load_meta(meta_path)
    existing = set(meta.get("localized_langs", []))
    meta["localized_langs"] = sorted(existing | set(langs))
    with open(meta_path, "w") as f:
        yaml.dump(meta, f, allow_unicode=True, sort_keys=False, default_flow_style=False)


def find_queue_metas_with_id(dirs, extra_filter=None) -> list[Path]:
    """Scan one or more directories for meta_*.yaml files that have youtube_id set.

    extra_filter: optional callable(data) -> bool for additional filtering.
    """
    if isinstance(dirs, Path):
        dirs = [dirs]
    metas = []
    for d in dirs:
        if not d.exists():
            continue
        for p in sorted(d.glob("meta_*.yaml")):
            try:
                data = load_meta(p)
                if data.get("youtube_id"):
                    if extra_filter is None or extra_filter(data):
                        metas.append(p)
            except Exception:
                pass
    return metas


# ── Main ──────────────────────────────────────────────────────────────────────

def process_one(video_id: str, title: str, description: str,
                langs: list[str], channel: str,
                dry_run: bool, meta_path: Path = None):
    channel_type = CHANNEL_CONFIG[channel]["type"]
    print(f"\nVideo: {video_id}  [{channel} / {channel_type}]")
    print(f"Title: {title[:70]}")

    localizations = translate_meta(title, description, langs, channel_type=channel_type)
    push_localizations(video_id, localizations, channel=channel, dry_run=dry_run)

    if meta_path and not dry_run:
        save_localized_langs(meta_path, langs)
        print(f"  ✓ Wrote localized_langs to {meta_path.name}")


def main():
    parser = argparse.ArgumentParser(
        description="Add YouTube localizations to published videos (EN kids or Calm Classics)"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--video-id", help="YouTube video ID to localize")
    group.add_argument("--meta",     help="Path to meta YAML (reads title/description/youtube_id)")
    group.add_argument("--queue",    action="store_true",
                       help="Process all meta files in channel queue with youtube_id set")
    group.add_argument("--pre-translate", action="store_true",
                       help="Translate meta files in queue BEFORE upload — saves localizations into meta YAML (no YouTube API needed)")

    parser.add_argument("--channel", choices=list(CHANNEL_CONFIG.keys()), default="en",
                        help="Channel: en=Happy Bear Kids, id=Calm Classics (default: en)")
    parser.add_argument("--langs", default=None,
                        help="Comma-separated BCP-47 codes. Default: per-channel (kids=es,fr,pt,id; CC=de,it,ja,ru,es,fr,pt,ko)")
    parser.add_argument("--title",       help="Title override (only with --video-id)")
    parser.add_argument("--description", help="Description override (only with --video-id)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show translations without updating YouTube")
    args = parser.parse_args()

    channel = args.channel
    default_langs = CHANNEL_CONFIG[channel]["default_langs"]
    raw_langs = args.langs if args.langs else ",".join(default_langs)
    langs = [l.strip() for l in raw_langs.split(",") if l.strip() in LANG_MAP]
    if not langs:
        print(f"Error: no valid language codes. Choose from: {','.join(ALL_LANGS)}")
        sys.exit(1)

    if args.video_id:
        title = args.title or ""
        desc  = args.description or ""
        if not title or not desc:
            print("Error: --title and --description are required with --video-id")
            sys.exit(1)
        process_one(args.video_id, title, desc, langs, channel, args.dry_run)

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
                    todo, channel, args.dry_run, meta_path)

    elif args.queue:
        queue_dir = CHANNEL_CONFIG[channel]["queue_dir"]
        uploaded_dir = ROOT / "uploaded"
        # For id/CNR channel, uploaded/ contains ALL channels mixed together.
        # Only take made_for_kids=False entries, which are exclusively CNR videos.
        cnr_filter = (lambda d: d.get("made_for_kids") is False) if channel in ("id", "sd") else None
        metas_queue    = find_queue_metas_with_id([queue_dir])
        metas_uploaded = find_queue_metas_with_id([uploaded_dir], extra_filter=cnr_filter)
        metas = metas_queue + metas_uploaded
        print(f"Found {len(metas)} meta files with youtube_id "
              f"({len(metas_queue)} in {queue_dir.name}, {len(metas_uploaded)} in uploaded/) [{channel}]")
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
                            todo, channel, args.dry_run, meta_path)
                ok += 1
            except Exception as e:
                print(f"  ERROR {meta_path.name}: {e}")
                err += 1

        print(f"\nDone: {ok} updated, {skip} already localized, {err} errors")

    else:  # --pre-translate
        queue_dir    = CHANNEL_CONFIG[channel]["queue_dir"]
        channel_type = CHANNEL_CONFIG[channel]["type"]
        metas = sorted(queue_dir.glob("meta_*.yaml"))
        print(f"Pre-translating {len(metas)} meta files in {queue_dir.name} [{channel}] → {langs}")
        ok = skip = err = 0
        for meta_path in metas:
            try:
                meta = load_meta(meta_path)
            except Exception as e:
                print(f"  SKIP {meta_path.name}: {e}")
                skip += 1
                continue

            # Skip if already has localizations for all requested langs
            existing_locs = meta.get("localizations", {})
            todo = [l for l in langs if l not in existing_locs]
            if not todo:
                skip += 1
                continue

            title       = meta.get("title", "").strip()
            description = meta.get("description", "").strip()
            if not title or not description:
                skip += 1
                continue

            print(f"\n  {meta_path.name}")
            print(f"  Title: {title[:70]}")

            if args.dry_run:
                print(f"  [dry-run] would translate → {todo}")
                ok += 1
                continue

            try:
                new_locs = translate_meta(title, description, todo, channel_type=channel_type)
                existing_locs.update(new_locs)
                meta["localizations"] = existing_locs
                with open(meta_path, "w", encoding="utf-8") as f:
                    yaml.dump(meta, f, allow_unicode=True, default_flow_style=False,
                              sort_keys=False)
                print(f"  ✓ saved {len(existing_locs)} langs to meta")
                ok += 1
            except Exception as e:
                print(f"  ERROR: {e}")
                err += 1

        print(f"\nPre-translate done: {ok} translated, {skip} skipped, {err} errors")


if __name__ == "__main__":
    main()
