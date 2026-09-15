#!/usr/bin/env python3
"""
Pre-translate all ready queue videos BEFORE uploading to YouTube.

Reads meta_*.yaml in the queue directory, translates title+description
to all target languages using Ollama (qwen3:8b, think:false) with Groq fallback,
and saves translations back into the meta YAML as a 'localizations' field.

publish_queue.py reads this field and pushes localizations immediately after upload.

Usage:
    python3 scripts/prepare_queue.py --queue id    # CC channel
    python3 scripts/prepare_queue.py --queue en    # EN kids channel
    python3 scripts/prepare_queue.py --queue ar    # AR channel
    python3 scripts/prepare_queue.py --queue id --force  # Re-translate even if already done
    python3 scripts/prepare_queue.py --queue id --dry-run
"""

import argparse
import json
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

QUEUE_DIRS = {
    "en": ROOT / "output" / "queue",
    "ar": ROOT / "output" / "queue_ar",
    "id": ROOT / "output" / "queue_id",
    "sd": ROOT / "sacred_drift" / "output" / "queue",
}

OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "translategemma:4b"

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL    = "openai/gpt-oss-20b"
_GROQ_KEY_FILE = Path(__file__).resolve().parent.parent / "credentials" / "groq_api_keys.txt"
GROQ_KEYS = [k.strip() for k in _GROQ_KEY_FILE.read_text().splitlines() if k.strip()] if _GROQ_KEY_FILE.exists() else []
_groq_idx = 0

LANG_MAP = {
    "es":      "Spanish",
    "fr":      "French",
    "pt":      "Portuguese (Brazilian)",
    "id":      "Indonesian (Bahasa)",
    "de":      "German",
    "it":      "Italian",
    "ja":      "Japanese",
    "ru":      "Russian",
    "ko":      "Korean",
    "zh-Hans": "Chinese (Simplified)",
    "ar":      "Arabic (Modern Standard)",
}

LANGS_BY_CHANNEL = {
    "en": ["es", "fr", "pt", "id"],
    "ar": [],
    "id": ["de", "it", "ja", "ru", "es", "fr", "pt", "ko", "ar"],
    # Sacred Drift — all 11 global markets
    "sd": ["es", "fr", "pt", "id", "de", "it", "ja", "ru", "ko", "zh-Hans", "ar"],
}

CHANNEL_TYPE = {
    "en": "kids",
    "ar": "kids",
    "id": "adult",
    "sd": "adult",
}


def _next_groq_key() -> str:
    global _groq_idx
    key = GROQ_KEYS[_groq_idx % len(GROQ_KEYS)]
    _groq_idx += 1
    return key


LANG_CODES = {
    "es": "es", "fr": "fr", "pt": "pt", "id": "id",
    "de": "de", "it": "it", "ja": "ja", "ru": "ru", "ko": "ko",
    "zh-Hans": "zh-CN", "ar": "ar",
}

# Standard transliterations for classical composers in non-Latin scripts
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
    """Post-process: replace Latin composer names with proper transliterations."""
    for english, native in COMPOSER_NAMES.get(lang, {}).items():
        text = text.replace(english, native)
    if lang == "ru":
        text = text.replace("Чопин", "Шопен").replace("Шопин", "Шопен")
    return text


def _composer_hint(lang: str) -> str:
    """Build composer transliteration hint for prompt."""
    names = COMPOSER_NAMES.get(lang, {})
    if not names:
        return ""
    examples = ", ".join(f"{v} ({k})" for k, v in list(names.items())[:8])
    return f"Use standard transliterations for composer names: {examples}. "


def translate_field(text: str, target_lang: str, field: str, channel_type: str) -> str:
    lang_name = LANG_MAP[target_lang]
    lang_code = LANG_CODES[target_lang]
    is_arabic  = target_lang == "ar"
    non_latin  = target_lang in NON_LATIN_LANGS
    composer_hint = _composer_hint(target_lang) if non_latin else (
        "Do not translate instrument names (Cello, Piano, Violin) or composer names. "
    )

    if field == "title":
        if channel_type == "adult":
            extra = (
                "Keep under 100 chars. Keep emojis unchanged. "
                + composer_hint
                + "Keep hashtag words unchanged. "
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
    except Exception as e:
        print(f"    Ollama unavailable ({type(e).__name__}), using Groq...")

    # Groq fallback — extract instruction from combined prompt
    instruction = prompt.rsplit("\n\n\n", 1)[0]
    messages = [
        {"role": "system", "content": instruction},
        {"role": "user",   "content": text},
    ]
    for attempt in range(len(GROQ_KEYS) * 2):
        key = _next_groq_key()
        payload = json.dumps({
            "model": GROQ_MODEL,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 2500,
        }).encode()
        req = urllib.request.Request(
            GROQ_CHAT_URL, data=payload,
            headers={
                "Authorization": f"Bearer {key}",
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
            body = e.read().decode(errors="ignore")[:100]
            if e.code == 429:
                if attempt > 0 and attempt % len(GROQ_KEYS) == 0:
                    print(f"    All Groq keys rate-limited, waiting 65s...")
                    time.sleep(65)
                else:
                    print(f"    Groq key rotated...")
                    time.sleep(2)
            else:
                raise RuntimeError(f"Groq HTTP {e.code}: {body}") from e
    raise RuntimeError("All Groq keys exhausted")


def spellcheck_english(title: str, description: str) -> tuple[str, str]:
    """Fix spelling and grammar of English source text using LLM before translating."""
    prompt = (
        "You are a professional English copy editor. "
        "Fix any spelling mistakes, grammar errors, and punctuation in the text below. "
        "Keep ALL emojis, hashtags, URLs, channel handles (@...), numbers, and formatting unchanged. "
        "Do NOT change the meaning, style, or structure. Return only the corrected text.\n\n"
    )
    def fix(text: str) -> str:
        full_prompt = prompt + text
        try:
            payload = json.dumps({
                "model": OLLAMA_MODEL,
                "prompt": full_prompt,
                "stream": False,
                "options": {"temperature": 0.0, "num_predict": 2000},
            }).encode()
            req = urllib.request.Request(
                OLLAMA_URL, data=payload,
                headers={"Content-Type": "application/json"}, method="POST",
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read())["response"].strip()
                return result if result else text
        except Exception:
            return text  # if Ollama unavailable, keep original

    fixed_title = fix(title)
    fixed_desc  = fix(description)
    if fixed_title != title:
        print(f"    spellcheck title: {title!r} → {fixed_title!r}")
    return fixed_title, fixed_desc


def _translate_one(lang: str, title: str, description: str,
                   channel_type: str, dry_run: bool) -> tuple[str, dict | None]:
    """Translate a single language — runs in a thread."""
    if dry_run:
        return lang, {"title": f"[{lang}] {title}", "description": f"[{lang}] {description[:50]}..."}
    try:
        t_title = translate_field(title, lang, "title", channel_type)
        t_desc  = translate_field(description, lang, "description", channel_type)
        return lang, {"title": t_title, "description": t_desc}
    except RuntimeError as e:
        print(f"    ⚠ {lang} failed: {e}")
        return lang, None


def prepare_video(meta_path: Path, langs: list[str], channel_type: str,
                  force: bool, dry_run: bool) -> bool:
    meta = yaml.safe_load(meta_path.read_text()) or {}
    title       = meta.get("title", "").strip()
    description = meta.get("description", "").strip()
    if not title or not description:
        print(f"  SKIP {meta_path.name}: empty title or description")
        return False

    existing_locs = meta.get("localizations", {})
    todo = [l for l in langs if force or l not in existing_locs]
    if not todo:
        print(f"  SKIP {meta_path.name}: all langs ready {sorted(existing_locs.keys())}")
        return False

    # Spellcheck English source before translating
    if not dry_run:
        title, description = spellcheck_english(title, description)
        if title != meta.get("title", "").strip() or description != meta.get("description", "").strip():
            meta["title"]       = title
            meta["description"] = description

    print(f"  Translating {len(todo)} langs simultaneously: {todo}")
    new_locs = dict(existing_locs)

    # Parallel translation — all languages at once
    max_workers = min(len(todo), 6)  # cap at 6 to avoid Ollama queue overload
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_translate_one, lang, title, description, channel_type, dry_run): lang
            for lang in todo
        }
        for future in as_completed(futures):
            lang, result = future.result()
            if result is not None:
                new_locs[lang] = result
                print(f"    ✓ {lang:8s} {result['title'][:55]}")
            # failed langs stay out of new_locs → retry on next run

    if not dry_run:
        meta["localizations"] = new_locs
        meta_path.write_text(yaml.dump(meta, allow_unicode=True, sort_keys=False))
        done = len(new_locs) - len(existing_locs)
        print(f"  ✓ Saved {done} new localizations ({len(new_locs)} total) → {meta_path.name}")

    return True


def main():
    parser = argparse.ArgumentParser(description="Pre-translate queue videos before upload")
    parser.add_argument("--queue",   choices=["en", "ar", "id", "sd"], required=True)
    parser.add_argument("--force",   action="store_true", help="Re-translate even if already done")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit",   type=int, default=0, help="Max videos to process (0=all)")
    args = parser.parse_args()

    queue_dir    = QUEUE_DIRS[args.queue]
    langs        = LANGS_BY_CHANNEL[args.queue]
    channel_type = CHANNEL_TYPE[args.queue]

    if not langs:
        print(f"No target langs configured for queue={args.queue}")
        return

    meta_files = sorted(queue_dir.glob("meta_*.yaml"), key=lambda p: p.stat().st_mtime)
    print(f"Queue: {args.queue} | Langs: {langs} | Videos: {len(meta_files)}")
    if args.dry_run:
        print("DRY RUN mode")

    processed = 0
    for meta_path in meta_files:
        if args.limit and processed >= args.limit:
            break
        print(f"\n{meta_path.name}:")
        if prepare_video(meta_path, langs, channel_type, args.force, args.dry_run):
            processed += 1

    print(f"\n=== Done: {processed} videos prepared ===")


if __name__ == "__main__":
    main()
