#!/usr/bin/env python3
"""
Localize ALL uploaded videos on a channel — fetches video list directly from YouTube API.
Does not depend on youtube_id in meta files.

Usage:
  python3 scripts/localize_all_videos.py --channel en
  python3 scripts/localize_all_videos.py --channel id
  python3 scripts/localize_all_videos.py --channel en --dry-run
  python3 scripts/localize_all_videos.py --channel id --langs de,it,ja
"""
import argparse, json, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Primary: local Ollama (no rate limits, no API key)
OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "translategemma:4b"

# Fallback: Groq cloud (used only if Ollama unavailable)
GROQ_CHAT_URL  = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL     = "openai/gpt-oss-20b"
_GROQ_KEY_FILE = Path(__file__).resolve().parent.parent / "credentials" / "groq_api_keys.txt"
GROQ_KEYS = [k.strip() for k in _GROQ_KEY_FILE.read_text().splitlines() if k.strip()] if _GROQ_KEY_FILE.exists() else []
_groq_key_idx = 0

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
    "ar": "Arabic (Modern Standard)",
}

LANG_CODES = {
    "es": "es", "fr": "fr", "pt": "pt", "id": "id",
    "de": "de", "it": "it", "ja": "ja", "ru": "ru", "ko": "ko", "ar": "ar",
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

LANGS_BY_CHANNEL = {
    "en": ["es", "fr", "pt", "id"],
    "ar": [],  # AR channel publishes in Arabic; no outbound translations
    "id": ["de", "it", "ja", "ru", "es", "fr", "pt", "ko", "ar"],
}

CHANNEL_CONFIG = {
    "en": {
        "json":   ROOT / "credentials" / "youtube_token.json",
        "type":   "kids",
        "langs":  LANGS_BY_CHANNEL["en"],
    },
    "ar": {
        "json":   ROOT / "credentials" / "youtube_token_ar.json",
        "type":   "kids",
        "langs":  LANGS_BY_CHANNEL["ar"],
    },
    "id": {
        "json":   ROOT / "credentials" / "youtube_token_id.json",
        "type":   "adult",
        "langs":  LANGS_BY_CHANNEL["id"],
    },
}


def _get_youtube_service(channel: str):
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    SCOPES = [
        "https://www.googleapis.com/auth/youtube",
        "https://www.googleapis.com/auth/youtube.force-ssl",
    ]
    cfg = CHANNEL_CONFIG[channel]
    t = json.loads(cfg["json"].read_text())
    creds = Credentials(
        token=t.get("access_token"),
        refresh_token=t["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=t["client_id"],
        client_secret=t["client_secret"],
        scopes=SCOPES,
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        t["access_token"] = creds.token
        cfg["json"].write_text(json.dumps(t, indent=2))
    return build("youtube", "v3", credentials=creds)


def get_all_channel_videos(yt) -> list[dict]:
    """Return [{id, title, description}] for all uploaded videos."""
    ch = yt.channels().list(part="contentDetails", mine=True).execute()
    playlist_id = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    videos = []
    page_token = None
    while True:
        resp = yt.playlistItems().list(
            part="snippet", playlistId=playlist_id,
            maxResults=50, pageToken=page_token
        ).execute()
        for item in resp["items"]:
            vid_id = item["snippet"]["resourceId"]["videoId"]
            title = item["snippet"]["title"]
            desc = item["snippet"]["description"]
            videos.append({"id": vid_id, "title": title, "description": desc})
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return videos


def get_existing_localizations(yt, video_id: str) -> set[str]:
    """Return set of lang codes already set on this video."""
    resp = yt.videos().list(part="localizations", id=video_id).execute()
    if not resp["items"]:
        return set()
    return set(resp["items"][0].get("localizations", {}).keys())


def _next_groq_key() -> str:
    global _groq_key_idx
    key = GROQ_KEYS[_groq_key_idx % len(GROQ_KEYS)]
    _groq_key_idx += 1
    return key


def translate_field(text: str, target_lang: str, field: str,
                    api_key: str, channel_type: str) -> str:
    lang_name = LANG_MAP[target_lang]
    lang_code = LANG_CODES[target_lang]
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
                key_num = (attempt % len(GROQ_KEYS)) + 1
                if attempt > 0 and attempt % len(GROQ_KEYS) == 0:
                    print(f"    All keys rate-limited, waiting 65s for reset...")
                    time.sleep(65)
                else:
                    print(f"    Rate limit on key #{key_num}, rotating...")
                    time.sleep(2)
            else:
                raise RuntimeError(f"Groq HTTP {e.code}: {body}") from e
    raise RuntimeError("All Groq keys exhausted")


def push_localizations(yt, video_id: str, localizations: dict, dry_run: bool):
    """Push new localizations one language at a time (batching all in one call fails for CJK/Arabic)."""
    if dry_run:
        for lang, v in localizations.items():
            print(f"    [{lang}] {v['title'][:60]}")
        return

    # Fetch current state once
    resp = yt.videos().list(part="localizations", id=video_id).execute()
    if not resp["items"]:
        print(f"  ERROR: video {video_id} not found on channel")
        return
    existing = resp["items"][0].get("localizations", {})

    # Push one language at a time — pushing all at once causes 400 for CJK/RTL scripts
    for lang, data in localizations.items():
        existing[lang] = data
        yt.videos().update(
            part="localizations",
            body={"id": video_id, "localizations": existing}
        ).execute()
        print(f"    ✓ [{lang}] {data['title'][:50]}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--channel", choices=["en", "ar", "id"], required=True)
    parser.add_argument("--langs", default=None, help="Comma-separated lang codes")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0, help="Max videos to process (0=all)")
    parser.add_argument("--video-id", default=None, help="Localize only this one video ID")
    args = parser.parse_args()

    channel = args.channel
    cfg = CHANNEL_CONFIG[channel]
    langs = [l.strip() for l in args.langs.split(",")] if args.langs else cfg["langs"]
    langs = [l for l in langs if l in LANG_MAP]
    if not langs:
        print(f"No target langs configured for channel={channel} — nothing to do.")
        sys.exit(0)
    print(f"Channel: {channel} | Langs: {langs} | Dry-run: {args.dry_run}")
    print("Connecting to YouTube API...")
    yt = _get_youtube_service(channel)

    if args.video_id:
        resp = yt.videos().list(part="snippet", id=args.video_id).execute()
        if not resp.get("items"):
            print(f"ERROR: video {args.video_id} not found")
            return
        item = resp["items"][0]["snippet"]
        videos = [{"id": args.video_id, "title": item["title"], "description": item["description"]}]
    else:
        print("Fetching video list...")
        videos = get_all_channel_videos(yt)
    print(f"Found {len(videos)} videos to process")

    processed = skipped = errors = 0
    for i, video in enumerate(videos):
        if args.limit and processed >= args.limit:
            break
        vid_id = video["id"]
        title = video["title"]
        print(f"\n[{i+1}/{len(videos)}] {title[:60]}  ({vid_id})")

        # Check which langs are already set
        existing_langs = get_existing_localizations(yt, vid_id)
        todo = [l for l in langs if l not in existing_langs]
        if not todo:
            print(f"  ✓ Already localized: {sorted(existing_langs)}")
            skipped += 1
            continue

        print(f"  Missing: {todo} | Existing: {sorted(existing_langs)}")
        localizations = {}
        try:
            for lang in todo:
                print(f"  Translating → {lang} ({LANG_MAP[lang]})...")
                t_title = translate_field(title, lang, "title", None, cfg["type"])
                t_desc  = translate_field(video["description"], lang, "description", None, cfg["type"])
                localizations[lang] = {"title": t_title, "description": t_desc}
                print(f"    {t_title[:70]}")
                time.sleep(1)

            push_localizations(yt, vid_id, localizations, args.dry_run)
            if not args.dry_run:
                print(f"  ✓ Pushed {len(localizations)} langs")
            processed += 1
            time.sleep(2)
        except Exception as e:
            print(f"  ERROR: {e}")
            errors += 1

    print(f"\n=== DONE: {processed} localized, {skipped} skipped, {errors} errors ===")


if __name__ == "__main__":
    main()
