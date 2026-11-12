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

# ── Native title templates (research-based, no LLM needed for known styles) ──
_NATIVE_TITLES_FILE = ROOT / "sacred_drift" / "config" / "native_titles.yaml"
_NATIVE_TITLES: dict = {}
if _NATIVE_TITLES_FILE.exists():
    try:
        _NATIVE_TITLES = yaml.safe_load(_NATIVE_TITLES_FILE.read_text()) or {}
    except Exception:
        pass

import random as _rnd

def _native_duration(dur_en: str, lang: str) -> str:
    """Convert English duration like '3 Hours' / '1 Hour' / '8 Hours' to native string."""
    import re
    m = re.match(r'(\d+)\s+Hours?', dur_en.strip(), re.IGNORECASE)
    if not m:
        return dur_en  # unknown format — pass through as-is
    n = int(m.group(1))
    fmts = {
        "ru":       {1: "1 час",    3: "3 часа",    8: "8 часов"},
        "ar":       {1: "ساعة واحدة", 3: "3 ساعات", 8: "8 ساعات"},
        "ja":       {1: "1時間",    3: "3時間",      8: "8時間"},
        "ko":       {1: "1시간",    3: "3시간",      8: "8시간"},
        "zh-Hans":  {1: "1小时",    3: "3小时",      8: "8小时"},
        "de":       {1: "1 Stunde", 3: "3 Stunden",  8: "8 Stunden"},
        "it":       {1: "1 ora",    3: "3 ore",       8: "8 ore"},
        "es":       {1: "1 hora",   3: "3 horas",     8: "8 horas"},
        "fr":       {1: "1 heure",  3: "3 heures",    8: "8 heures"},
        "pt":       {1: "1 hora",   3: "3 horas",     8: "8 horas"},
        "id":       {1: "1 jam",    3: "3 jam",       8: "8 jam"},
    }
    lang_fmts = fmts.get(lang, {})
    if n in lang_fmts:
        return lang_fmts[n]
    # Generic fallback for other hour counts
    suffixes = {"ru": "часов", "de": "Stunden", "it": "ore", "es": "horas",
                "fr": "heures", "pt": "horas", "id": "jam",
                "ja": "時間", "ko": "시간", "zh-Hans": "小时",
                "ar": "ساعات"}
    s = suffixes.get(lang, "Hours")
    return f"{n} {s}"


def _native_title(style: str, lang: str, params: dict, duration: str) -> str | None:
    """Return a pre-researched native title for known style+lang combos.
    Falls back to None → LLM translation used instead."""
    lang_data = _NATIVE_TITLES.get(lang, {})
    # Map binaural/theta solfeggio sub-styles
    effective_style = style
    if style == "solfeggio" and params.get("binaural_beat_hz"):
        effective_style = "binaural"
    style_data = lang_data.get(effective_style)
    if not style_data:
        return None
    variants = style_data.get("long_variants", [])
    if not variants:
        return None
    template = _rnd.choice(variants)
    hz = params.get("hz", "")
    template = template.replace("{hz}", str(int(hz)) if hz else "")
    template = template.replace("{dur}", duration)
    return template


# ── LLM provider list — tried in order, skipped on permanent failure (403) ────
#
# Priority: Ollama (free, local, GPU when available) → Groq keys → Together.ai
#   → Pollinations.ai (free, no auth, always works as last resort)
#
# On 403 (invalid/expired key) → mark provider dead for this session, skip
# On 429 (rate limit) → wait and retry same provider
# On timeout/5xx → fall through to next provider

OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen3:1.7b"   # 1.4GB — fast on GPU; slow but functional on CPU

_GROQ_KEY_FILE = Path(__file__).resolve().parent.parent / "credentials" / "groq_api_keys.txt"
GROQ_KEYS = [k.strip() for k in _GROQ_KEY_FILE.read_text().splitlines() if k.strip()] if _GROQ_KEY_FILE.exists() else []

_TOGETHER_KEY_FILE = Path(__file__).resolve().parent.parent / "credentials" / "together_api_key.txt"
TOGETHER_KEY = _TOGETHER_KEY_FILE.read_text().strip() if _TOGETHER_KEY_FILE.exists() else ""

# Build provider list at import time
_PROVIDERS: list[dict] = []
_PROVIDERS.append({"name": "ollama",  "type": "ollama"})
for i, k in enumerate(GROQ_KEYS):
    _PROVIDERS.append({"name": f"groq[{i}]", "type": "openai_compat",
                        "url": "https://api.groq.com/openai/v1/chat/completions",
                        "model": "meta-llama/llama-4-maverick-17b-128e-instruct",
                        "key": k, "ratelimit_wait": 65})
if TOGETHER_KEY:
    _PROVIDERS.append({"name": "together", "type": "openai_compat",
                        "url": "https://api.together.xyz/v1/chat/completions",
                        "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
                        "key": TOGETHER_KEY, "ratelimit_wait": 10})
# Pollinations.ai — free, no auth, OpenAI-compatible endpoint; has per-IP rate limits
_PROVIDERS.append({"name": "pollinations", "type": "openai_compat",
                    "url": "https://text.pollinations.ai/openai",
                    "model": "openai", "key": "", "ratelimit_wait": 20, "pre_delay": 3})

_dead_providers: set[str] = set()   # 403 → skip for rest of session


def _call_llm(system: str, user: str, max_tokens: int = 3000) -> str:
    """Try providers in order. Skip dead ones. Return first successful response."""
    import time as _t
    import urllib.parse as _up

    for prov in _PROVIDERS:
        name = prov["name"]
        if name in _dead_providers:
            continue

        # ── Ollama ────────────────────────────────────────────────────────────
        if prov["type"] == "ollama":
            try:
                payload = json.dumps({
                    "model": OLLAMA_MODEL,
                    "prompt": system + "\n\n" + user,
                    "stream": False, "think": False,
                    "options": {"temperature": 0.3, "num_predict": max_tokens},
                }).encode()
                req = urllib.request.Request(
                    OLLAMA_URL, data=payload,
                    headers={"Content-Type": "application/json"}, method="POST",
                )
                with urllib.request.urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read())
                result = data.get("response", "").strip()
                if result:
                    return result
            except (ConnectionRefusedError, TimeoutError):
                _dead_providers.add(name)
                print(f"    [{name}] not available (CPU-only or not running) — skipped for session")
            except Exception as e:
                print(f"    [{name}] {e.__class__.__name__} — trying next provider")
            continue

        # ── OpenAI-compatible (Groq, Together.ai, Pollinations) ───────────────
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        payload = json.dumps({
            "model": prov["model"],
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": max_tokens,
        }).encode()
        headers = {"Content-Type": "application/json"}
        if prov["key"]:
            headers["Authorization"] = f"Bearer {prov['key']}"
        req = urllib.request.Request(prov["url"], data=payload, headers=headers, method="POST")
        pre = prov.get("pre_delay", 0.5)
        for attempt in range(4):
            try:
                _t.sleep(pre)
                with urllib.request.urlopen(req, timeout=60) as resp:
                    data = json.loads(resp.read())
                return data["choices"][0]["message"]["content"].strip()
            except urllib.error.HTTPError as e:
                body = e.read().decode(errors="ignore")[:200]
                if e.code == 403 or e.code == 401:
                    _dead_providers.add(name)
                    print(f"    [{name}] 403/401 (key expired?) — provider disabled for this session")
                    break
                elif e.code in (429, 402):
                    w = prov.get("ratelimit_wait", 30) * (attempt + 1)
                    print(f"    [{name}] {e.code} rate-limit, waiting {w}s...")
                    _t.sleep(w)
                else:
                    print(f"    [{name}] HTTP {e.code}: {body[:80]} — trying next provider")
                    break
            except Exception as e:
                if attempt < 2:
                    print(f"    [{name}] {e.__class__.__name__} — retrying ({attempt+1}/3)...")
                    _t.sleep(prov.get("ratelimit_wait", 5))
                    continue
                print(f"    [{name}] {e.__class__.__name__} — trying next provider")
                break

    raise RuntimeError(f"All providers failed: {[p['name'] for p in _PROVIDERS]}")

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


# Per-language natural-language guidance for meditation/wellness content (used in descriptions)
_LANG_STYLE: dict[str, str] = {
    "ru": (
        "Write as a native Russian speaker would naturally search on YouTube. "
        "Standard chakra terms: корневая чакра, сакральная чакра, солнечное сплетение, "
        "сердечная чакра, горловая чакра, третий глаз, коронная чакра (NOT коронарная). "
        "Solfeggio: частоты Солфеджио. Binaural: бинауральные ритмы. "
        "Duration: use only whole hours — '• 1 час', '• 3 часа', '• 8 часов' (no minutes). "
    ),
    "ar": (
        "Use Modern Standard Arabic (فصحى). "
        "Duration: '• ساعة واحدة', '• 3 ساعات', '• 8 ساعات'. "
    ),
    "ja": (
        "Write naturally in Japanese for YouTube search. "
        "Duration: '• 1時間', '• 3時間'. "
    ),
    "ko": (
        "Write naturally in Korean for YouTube search. "
        "Duration: '• 1시간', '• 3시간'. "
    ),
    "zh-Hans": (
        "Write in Simplified Chinese naturally for YouTube search. "
        "Duration: '• 1小时', '• 3小时'. "
    ),
    "de": "Write naturally in German for YouTube. Duration format: '• 1 Stunde', '• 3 Stunden'. ",
    "it": "Write naturally in Italian for YouTube. Duration: '• 1 ora', '• 3 ore'. ",
    "es": "Write naturally in Spanish for YouTube. Duration: '• 1 hora', '• 3 horas'. ",
    "fr": "Write naturally in French for YouTube. Duration: '• 1 heure', '• 3 heures'. ",
    "pt": "Write naturally in Brazilian Portuguese for YouTube. Duration: '• 1 hora', '• 3 horas'. ",
    "id": "Write naturally in Indonesian for YouTube. Duration: '• 1 jam', '• 3 jam'. ",
}

# Duration label format per language — used when rewriting adult titles structurally
_LANG_DUR: dict[str, str] = {
    "ru":      "• 1 час  /  • 3 часа  /  • 8 часов",
    "ar":      "• ساعة واحدة  /  • 3 ساعات  /  • 8 ساعات",
    "ja":      "• 1時間  /  • 3時間  /  • 8時間",
    "ko":      "• 1시간  /  • 3시간  /  • 8시간",
    "zh-Hans": "• 1小时  /  • 3小时  /  • 8小时",
    "de":      "• 1 Stunde  /  • 3 Stunden  /  • 8 Stunden",
    "it":      "• 1 ora  /  • 3 ore  /  • 8 ore",
    "es":      "• 1 hora  /  • 3 horas  /  • 8 horas",
    "fr":      "• 1 heure  /  • 3 heures  /  • 8 heures",
    "pt":      "• 1 hora  /  • 3 horas  /  • 8 horas",
    "id":      "• 1 jam  /  • 3 jam  /  • 8 jam",
}

# Suffix patterns to strip from titles before translation (channel name in title)
_TITLE_STRIP_SUFFIXES = [
    " | Sacred Drift", " | Happy Bear Kids", " | Calm Classics",
    " | Classical Night Relax", " | @SacredDrift",
]


def _clean_title(text: str) -> str:
    """Remove channel-name suffixes from title — we don't put channel name in translated titles."""
    for s in _TITLE_STRIP_SUFFIXES:
        if text.endswith(s):
            text = text[: -len(s)].rstrip()
    return text


def translate_field(text: str, target_lang: str, field: str,
                    api_key: str = None, channel_type: str = "kids",
                    meta: dict = None) -> str:
    lang_name = LANG_MAP[target_lang]
    lang_code = LANG_CODES.get(target_lang, target_lang)
    is_arabic = target_lang == "ar"
    non_latin = target_lang in NON_LATIN_LANGS
    composer_hint = _composer_hint(target_lang) if non_latin else (
        "Do not translate instrument names (Cello, Piano, Violin) or composer names. "
    )
    lang_style = _LANG_STYLE.get(target_lang, "")

    # For adult titles: use pre-researched native search terms when style is known
    # This bypasses LLM entirely — native keywords are more accurate than translation
    if field == "title" and channel_type == "adult" and meta:
        style = meta.get("style") or meta.get("genre")
        params = meta.get("params", {})
        # Extract duration from the English title (everything after " • ")
        dur_en = text.rsplit(" • ", 1)[-1] if " • " in text else ""
        # Convert "3 Hours" → native format
        native_dur = _native_duration(dur_en, target_lang)
        if style and native_dur:
            native = _native_title(style, target_lang, params, native_dur)
            if native:
                return native

    # Strip channel name suffix from titles
    if field == "title":
        text = _clean_title(text)

    # Brand-name protection — always added for both field types
    brand_rule = (
        "IMPORTANT: Never translate brand names — keep exactly as-is in English: "
        "'Sacred Drift', 'Happy Bear Kids', 'Calm Classics'. "
        "Never translate channel handles: @SacredDrift, @HappyBearKids1. "
    )

    if field == "title":
        if channel_type == "adult":
            dur_fmt = _LANG_DUR.get(target_lang, "")
            extra = (
                f"IMPORTANT: Do NOT translate word-for-word. "
                f"Instead, REWRITE this YouTube title in {lang_name} for maximum search appeal. "
                f"Follow the same structure as the English original: "
                f"[benefit or problem phrase] + [instrument or sound] + [emoji] • [duration]. "
                f"Write exactly as a native {lang_name} YouTube creator would write it — "
                f"using the keywords people actually search for in {lang_name}. "
                + (f"Duration format: {dur_fmt}. " if dur_fmt else "")
                + "Keep emojis unchanged. Keep under 100 characters. "
                + brand_rule
                + composer_hint
                + "Return ONLY the title, nothing else."
            )
        else:
            extra = (
                "Keep under 100 chars. Keep emojis unchanged. "
                + brand_rule
                + lang_style
                + "Return only the translated title, nothing else."
            )
    else:
        if channel_type == "adult":
            extra = (
                "Keep the same structure and emojis. "
                + brand_rule
                + composer_hint
                + "Keep opus numbers (Op., No.) unchanged. "
                + "Keep all hashtags in English unchanged at the end. "
                + "Keep channel handles unchanged. "
                + lang_style
                + "Return only the translated text."
            )
        else:
            extra = (
                "Keep the same structure and emojis. "
                + brand_rule
                + "Keep hashtags in English unchanged at the end. "
                + "Keep channel handles unchanged. "
                + lang_style
                + "Return only the translated text."
            )

    instruction = f"You are a professional English (en) to {lang_name} ({lang_code}) translator specializing in meditation, relaxation and wellness content for YouTube. {extra}"
    result = _call_llm(instruction, text, max_tokens=3000 if field == "description" else 200)
    return _fix_composer_names(result, target_lang)


def translate_meta(title: str, description: str, langs: list[str],
                   api_key: str = None, channel_type: str = "kids",
                   meta: dict = None) -> dict:
    """Return {lang_code: {title, description}} for all requested langs."""
    result = {}
    for lang in langs:
        print(f"  Translating → {lang} ({LANG_MAP[lang]})...")
        t_title = translate_field(title, lang, "title", api_key, channel_type, meta=meta)
        t_desc  = translate_field(description, lang, "description", api_key, channel_type, meta=meta)
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


def _has_youtube_id(path: Path) -> bool:
    try:
        return bool(load_meta(path).get("youtube_id"))
    except Exception:
        return False


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

    meta_data = yaml.safe_load(meta_path.read_text()) if meta_path and meta_path.exists() else {}
    localizations = translate_meta(title, description, langs, channel_type=channel_type, meta=meta_data)
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
    parser.add_argument("--shorts-only", action="store_true",
                        help="With --queue: process only is_short=true videos")
    parser.add_argument("--force", action="store_true",
                        help="Re-translate even if langs already in localized_langs (re-runs with improved prompts)")
    args = parser.parse_args()

    channel = args.channel
    force   = args.force
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
        todo = langs if force else [l for l in langs if l not in already]
        if not todo:
            print(f"All requested langs already localized: {langs}")
            return
        process_one(video_id, meta["title"], meta["description"],
                    todo, channel, args.dry_run, meta_path)

    elif args.queue:
        queue_dir = CHANNEL_CONFIG[channel]["queue_dir"]
        uploaded_dir = ROOT / "uploaded"
        if channel == "sd":
            metas_queue    = find_queue_metas_with_id([queue_dir])
            metas_uploaded = [p for p in sorted(uploaded_dir.glob("meta_sd_*.yaml"))
                              if _has_youtube_id(p)]
        elif channel == "id":
            cnr_filter = lambda d: d.get("made_for_kids") is False
            metas_queue    = find_queue_metas_with_id([queue_dir])
            metas_uploaded = find_queue_metas_with_id([uploaded_dir], extra_filter=cnr_filter)
        else:
            metas_queue    = find_queue_metas_with_id([queue_dir])
            metas_uploaded = find_queue_metas_with_id([uploaded_dir])
        metas = metas_queue + metas_uploaded
        if args.shorts_only:
            metas = [p for p in metas if load_meta(p).get("is_short")]
        print(f"Found {len(metas)} meta files with youtube_id "
              f"({len(metas_queue)} in {queue_dir.name}, {len(metas_uploaded)} in uploaded/) [{channel}]")
        ok = err = skip = 0
        for meta_path in metas:
            meta = load_meta(meta_path)
            already = set(meta.get("localized_langs", []))
            todo = langs if force else [l for l in langs if l not in already]
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
                new_locs = translate_meta(title, description, todo, channel_type=channel_type, meta=meta)
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
