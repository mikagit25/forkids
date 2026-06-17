#!/usr/bin/env python3
"""
Generate AI thumbnails for queue videos using Gemini image generation.

Uses Gemini API (free tier, 1500 req/day) to generate high-quality
YouTube thumbnails (1280×720). Falls back to PIL generator if API fails.

Usage:
  python3 scripts/generate_ai_thumbs.py              # both queues, skip existing
  python3 scripts/generate_ai_thumbs.py --queue en
  python3 scripts/generate_ai_thumbs.py --queue ar
  python3 scripts/generate_ai_thumbs.py --force      # regenerate all
  python3 scripts/generate_ai_thumbs.py --dry-run    # show prompts only
  python3 scripts/generate_ai_thumbs.py --test bear  # test one character

API key: credentials/gemini_api_key.txt
Model:   gemini-2.0-flash-preview-image-generation (free tier)
"""
import argparse
import base64
import json
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

import yaml

ROOT      = Path(__file__).resolve().parent.parent
QUEUE     = ROOT / "output" / "queue"
QUEUE_AR  = ROOT / "output" / "queue_ar"
QUEUE_ID  = ROOT / "output" / "queue_id"
UPLOADED  = ROOT / "uploaded"
KEY_FILE        = ROOT / "credentials" / "gemini_api_key.txt"
TOGETHER_KEY_FILE = ROOT / "credentials" / "together_api_key.txt"

# Gemini (free 1500/day when billing enabled on account)
GEMINI_IMAGE_MODEL = "gemini-2.0-flash-preview-image-generation"
GEMINI_API_BASE    = "https://generativelanguage.googleapis.com/v1beta/models"

# Together.ai — FLUX.1-schnell, free $25 credit on signup, then ~$0.0003/image
TOGETHER_IMAGE_URL = "https://api.together.xyz/v1/images/generations"
TOGETHER_MODEL     = "black-forest-labs/FLUX.1-schnell"  # serverless, pay-per-use

# ── Prompt templates ──────────────────────────────────────────────────────────

# Character Arabic names for prompt context
AR_NAMES = {
    "bear": "دب", "tiger": "نمر", "frog": "ضفدع", "penguin": "بطريق",
    "lion": "أسد", "panda": "باندا", "koala": "كوالا", "fox": "ثعلب",
    "rabbit": "أرنب", "cow": "بقرة", "duck": "بطة", "pig": "خنزير",
    "elephant": "فيل", "monkey": "قرد", "dog": "كلب", "cat": "قطة",
    "owl": "بومة", "unicorn": "وحيد القرن", "dino": "ديناصور", "parrot": "ببغاء",
    "apple": "تفاحة", "banana": "موزة", "strawberry": "فراولة",
    "watermelon": "بطيخ", "orange": "برتقالة", "grapes": "عنب",
    "pineapple": "أناناس", "cherry": "كرز", "lemon": "ليمون",
    "carrot": "جزرة", "broccoli": "بروكلي", "corn": "ذرة", "tomato": "طماطم",
    "cucumber": "خيار", "pumpkin": "قرع", "mushroom": "فطر",
}

STYLE_EN = (
    "bright colorful children's illustration, cartoon style, "
    "bold outlines, cheerful expression, kids YouTube thumbnail, "
    "16:9 format 1280x720"
)

# AR channel: same style but absolutely no text — FLUX can't render Arabic (non-Latin)
STYLE_AR_NOTXT = (
    "bright colorful children's illustration, cartoon style, "
    "bold outlines, cheerful expression, kids YouTube thumbnail, "
    "16:9 format 1280x720, no text, no letters, no words, no numbers"
)

# ID channel: Indonesian uses Latin script → text allowed, same style as EN
# (STYLE_EN is reused for Indonesian)


def make_prompt(stem: str, meta: dict, is_ar: bool = False) -> str:
    """Build an English image generation prompt from video metadata.

    Always English — FLUX/Gemini don't render Arabic text well.
    is_ar=True → adds 'no text, no letters' suffix to keep images clean.
    Indonesian (id) uses Latin script, so text is allowed — same style as EN.
    """
    vtype  = meta.get("video_type", "")
    theme  = meta.get("theme", "animals")
    style  = STYLE_AR_NOTXT if is_ar else STYLE_EN

    # Normalise stem: strip ar_ prefix and date suffix
    name = re.sub(r'^ar_', '', re.sub(r'_\d{8}.*$', '', stem))

    # Detect specific character (bear, apple, circle, …) from filename
    character = ""
    for char in AR_NAMES:
        if char in name:
            character = char
            break

    # ── dance ─────────────────────────────────────────────────────────────────
    if "dance" in vtype or "dance" in name:
        if character:
            prompt = (
                f"Cute cartoon {character} dancing happily, dynamic dance pose, "
                f"bright colorful background with musical notes and stars, {style}"
            )
        else:
            theme_en = {"animals": "animals", "fruits": "fruits",
                        "vegetables": "vegetables", "shapes": "geometric shapes",
                        "mixed": "cartoon characters"}.get(theme, "cartoon characters")
            prompt = (
                f"Group of cute cartoon {theme_en} dancing together joyfully, "
                f"confetti and musical notes, bright pastel background, {style}"
            )

    # ── numbers / counting ────────────────────────────────────────────────────
    elif "counting" in vtype or "counting" in name or vtype == "numbers" or "number_learn" in name:
        num_match = re.search(
            r'number_learn_(one|two|three|four|five|six|seven|eight|nine|ten)', name)
        digit_map = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
                     "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10"}
        if num_match:
            digit = digit_map[num_match.group(1)]
            if is_ar:
                prompt = (
                    f"Cute cartoon animals around a big colorful star, "
                    f"confetti and sparkles, bright educational kids background, {style}"
                )
            else:
                prompt = (
                    f"Big bold cartoon number {digit}, cute cartoon animals around it, "
                    f"stars and confetti, bright educational kids background, {style}"
                )
        else:
            if is_ar:
                prompt = (
                    f"Cute cartoon animals playing with colorful balloons and stars, "
                    f"bright educational kids background, {style}"
                )
            else:
                prompt = (
                    f"Big colorful cartoon numbers 1 2 3 floating, cute animals counting, "
                    f"bright educational kids background, {style}"
                )

    # ── colors ────────────────────────────────────────────────────────────────
    elif "color" in vtype or "color_learn" in name or "color" in name:
        color_match = re.search(
            r'(red|blue|green|yellow|orange|purple|pink|brown|white|black)', name)
        color = color_match.group(1) if color_match else "rainbow"
        prompt = (
            f"Big bold {color} color theme, cute cartoon characters and objects in {color}, "
            f"educational color learning for kids, {style}"
        )

    # ── shapes ────────────────────────────────────────────────────────────────
    elif "shape" in vtype or "shape" in name or "float" in name:
        shape_match = re.search(
            r'(circle|square|triangle|star|heart|diamond|hexagon|oval|pentagon)', name)
        shape = shape_match.group(1) if shape_match else "circle"
        prompt = (
            f"Cute cartoon {shape} character with eyes and smile, dancing and bouncing, "
            f"bright vivid colors, educational shapes for kids, {style}"
        )

    # ── Indonesian nursery songs ──────────────────────────────────────────────
    elif vtype == "nursery_id" or "nursery_id" in name or "balonku" in name or "cicak" in name \
            or "naik_kereta" in name or "pelangi" in name or "dua_mata" in name or "kebunku" in name:
        song_visuals = {
            "balonku":     "colorful balloons floating up in a blue sky, cute cartoon bear holding balloons",
            "cicak":       "cute cartoon lizard walking on a wall, tropical leaves, friendly and cheerful",
            "naik_kereta": "cute cartoon train puffing steam, colorful carriages, happy animals riding",
            "pelangi":     "beautiful rainbow over green hills, cute cartoon animals under the rainbow",
            "dua_mata":    "cute cartoon bear pointing to its eyes and smiling, simple body parts lesson",
            "kebunku":     "colorful flower garden, cute cartoon butterfly and bee, cheerful garden scene",
        }
        song_key = next((k for k in song_visuals if k in name), None)
        visual = song_visuals.get(song_key,
                    "cute cartoon characters singing Indonesian nursery rhyme, colorful musical notes")
        prompt = f"{visual}, bright cheerful kids illustration, {style}"

    # ── Arabic nursery songs ───────────────────────────────────────────────────
    elif vtype == "nursery_ar" or "nursery_ar" in name or "batta_batta" in name \
            or "ya_matar" in name or "dajaja" in name:
        song_visuals = {
            "batta_batta": "cute cartoon duck splashing in a pond, cheerful water scene",
            "ya_matar":    "cartoon rain clouds and rainbow, colorful raindrops, happy animals in rain",
            "dajaja":      "cute cartoon hen with baby chicks, colorful farm scene, cheerful morning",
        }
        song_key = next((k for k in song_visuals if k in name), None)
        visual = song_visuals.get(song_key,
                    "cute cartoon animals singing cheerful Arabic nursery song, colorful musical notes")
        prompt = f"{visual}, bright cheerful kids illustration, {style}"

    # ── sensory loop / lullaby ────────────────────────────────────────────────
    elif vtype in ("sensory_loop", "lullaby_long") or "sensory" in name or "lullaby" in name:
        prompt = (
            f"Soothing pastel dreamscape, floating stars and soft glowing shapes, "
            f"gentle gradient colors, calming baby sleep video background, "
            f"no faces, no text, peaceful and magical, {style}"
        )

    # ── dancing shapes ────────────────────────────────────────────────────────
    elif vtype == "dance_shape" or "dance_shape" in name:
        prompt = (
            f"Cute cartoon geometric shapes dancing and bouncing, "
            f"colorful circle square triangle star with happy faces, "
            f"bright pastel background, {style}"
        )

    # ── dancing pets / items ──────────────────────────────────────────────────
    elif vtype in ("dance_pet", "dance_item") or "dance_pet" in name or "dance_item" in name:
        prompt = (
            f"Cute cartoon household pet dancing happily with musical notes, "
            f"bright colorful background, cheerful dance pose, {style}"
        )

    # ── stars and bubbles ─────────────────────────────────────────────────────
    elif vtype == "stars_bubbles" or "stars_bubble" in name:
        prompt = (
            f"Magical floating soap bubbles and twinkling stars, "
            f"bright colorful background, one big bubble about to pop, "
            f"sparkles and light trails, kids entertainment, {style}"
        )

    # ── generic fallback ──────────────────────────────────────────────────────
    else:
        prompt = (
            f"Cute cartoon characters for kids educational video, "
            f"bright colorful background, happy animals and objects, {style}"
        )

    return prompt


# ── Gemini API ────────────────────────────────────────────────────────────────

def load_key() -> str | None:
    if KEY_FILE.exists():
        return KEY_FILE.read_text().strip()
    return None


def load_together_key() -> str | None:
    if TOGETHER_KEY_FILE.exists():
        return TOGETHER_KEY_FILE.read_text().strip()
    return None


def together_generate_image(prompt: str, key: str) -> bytes | None:
    """Generate image via Together.ai FLUX.1-schnell."""
    try:
        import requests as _req
    except ImportError:
        print("    pip install requests  (needed for Together.ai)")
        return None
    try:
        r = _req.post(
            TOGETHER_IMAGE_URL,
            headers={"Authorization": f"Bearer {key}"},
            json={"model": TOGETHER_MODEL, "prompt": prompt,
                  "width": 1280, "height": 720, "steps": 4, "n": 1},
            timeout=90)
        if r.status_code != 200:
            try:
                msg = r.json().get("error", {}).get("message", r.text[:120])
            except Exception:
                msg = r.text[:120]
            print(f"    Together error {r.status_code}: {msg}")
            return None
        item = r.json()["data"][0]
        b64 = item.get("b64_json")
        if b64:
            return base64.b64decode(b64)
        url = item.get("url")
        if url:
            img_r = _req.get(url, timeout=30)
            if img_r.status_code == 200:
                return img_r.content
    except Exception as e:
        print(f"    Together request failed: {e}")
    return None


def gemini_generate_image(prompt: str, key: str,
                          retries: int = 3) -> bytes | None:
    """Call Gemini image generation. Returns raw PNG/JPEG bytes or None."""
    url = f"{GEMINI_API_BASE}/{GEMINI_IMAGE_MODEL}:generateContent?key={key}"
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]},
    }).encode()

    for attempt in range(retries):
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read())
                parts = data["candidates"][0]["content"]["parts"]
                for p in parts:
                    if "inlineData" in p:
                        return base64.b64decode(p["inlineData"]["data"])
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            err  = json.loads(body).get("error", {})
            code = err.get("code", e.code)
            msg  = err.get("message", "")

            if code == 429:  # rate limit — wait and retry
                wait = 2 ** attempt * 5
                print(f"    Rate limit, waiting {wait}s …")
                time.sleep(wait)
                continue
            elif code in (404, 400) and "not found" in msg.lower():
                print(f"    Model not available: {msg[:80]}")
                return None
            else:
                print(f"    API error {code}: {msg[:80]}")
                return None
        except Exception as e:
            print(f"    Request failed: {e}")
            if attempt < retries - 1:
                time.sleep(3)

    return None


def resize_to_720p(img_bytes: bytes) -> bytes:
    """Resize image to 1280×720 using PIL."""
    from PIL import Image
    import io
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    img = img.resize((1280, 720), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


# ── Queue processor ───────────────────────────────────────────────────────────

SHORT_PREFIXES = (
    "short_", "ar_short_",
)


def is_short(name: str) -> bool:
    return any(name.startswith(p) for p in SHORT_PREFIXES)


def process_queue(queue_dir: Path, key: str, force: bool,
                  dry_run: bool, label: str, backend: str = "gemini",
                  long_only: bool = True):
    mp4s = sorted([
        p for p in queue_dir.glob("*.mp4")
        if "test_" not in p.name and p.exists() and not p.is_symlink()
    ])
    if long_only:
        mp4s = [p for p in mp4s if not is_short(p.name)]
    if not mp4s:
        print(f"  [{label}] Queue empty")
        return

    ok = skip = err = api_fail = consec_fail = 0

    for i, mp4 in enumerate(mp4s):
        thumb_path = queue_dir / f"thumb_{mp4.stem}.png"
        if thumb_path.exists() and not force:
            skip += 1
            continue

        meta_path = queue_dir / f"meta_{mp4.stem}.yaml"
        meta = {}
        if meta_path.exists():
            with open(meta_path) as f:
                meta = yaml.safe_load(f) or {}

        lang   = meta.get("language", "en")
        is_ar  = lang == "ar" or mp4.name.startswith("ar_")
        # Indonesian uses Latin script → text allowed, same style as EN (is_ar=False)
        prompt = make_prompt(mp4.stem, meta, is_ar=is_ar)

        print(f"  [{label}] {i+1}/{len(mp4s)} {mp4.name}")
        print(f"    Prompt: {prompt[:100]}")

        if dry_run:
            ok += 1
            continue

        if backend == "together":
            img_bytes = together_generate_image(prompt, key)
        else:
            img_bytes = gemini_generate_image(prompt, key)
        if img_bytes:
            try:
                final = resize_to_720p(img_bytes)
                thumb_path.write_bytes(final)
                print(f"    ✓ saved {len(final)//1024}KB")
                ok += 1
                consec_fail = 0
            except Exception as e:
                print(f"    PIL resize error: {e}")
                err += 1
        else:
            api_fail += 1
            consec_fail += 1
            if consec_fail >= 5:
                wait = 60
                print(f"    5 consecutive failures — waiting {wait}s before retry …")
                time.sleep(wait)
                consec_fail = 0
            elif consec_fail >= 10:
                print(f"\n  API persistently unavailable — stopping.")
                break
            continue  # skip sleep on failure, retry sooner

        # Rate limit: ~10 RPM
        time.sleep(6)

    print(f"\n  [{label}] Done: {ok} generated, {skip} skipped, "
          f"{err} errors, {api_fail} API failures")


def main():
    parser = argparse.ArgumentParser(
        description="Generate AI thumbnails via Gemini or Together.ai")
    parser.add_argument("--queue",   choices=["en", "ar", "id", "all", "both", "none"], default="both")
    parser.add_argument("--force",   action="store_true")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show prompts without calling API")
    parser.add_argument("--test",    metavar="CHARACTER",
                        help="Test one character (e.g. --test bear)")
    parser.add_argument("--backend",  choices=["gemini", "together", "auto"],
                        default="auto", help="Force specific backend (default: auto)")
    parser.add_argument("--uploaded", action="store_true",
                        help="Also process uploaded/ directory (for already-published videos)")
    args = parser.parse_args()

    gemini_key   = load_key()
    together_key = load_together_key()

    if not gemini_key and not together_key:
        print("No API keys found. Add one of:")
        print(f"  Gemini (free):  {KEY_FILE}")
        print(f"  Together.ai:    {TOGETHER_KEY_FILE}")
        sys.exit(1)

    # Pick backend
    if args.backend == "together":
        if not together_key:
            print(f"Together.ai key not found: {TOGETHER_KEY_FILE}")
            sys.exit(1)
        key, backend = together_key, "together"
    elif args.backend == "gemini":
        if not gemini_key:
            print(f"Gemini key not found: {KEY_FILE}")
            sys.exit(1)
        key, backend = gemini_key, "gemini"
    else:
        # auto: prefer Gemini, fall back to Together
        key    = gemini_key or together_key
        backend = "gemini" if gemini_key else "together"
    print(f"Backend: {backend}  key: {key[:14]}…")

    if args.test:
        # Quick single test
        stem = f"short_dance_{args.test}_20260101"
        meta = {"video_type": "short_dance", "theme": "animals", "language": "en"}
        prompt = make_prompt(stem, meta, is_ar=False)
        print(f"Prompt: {prompt}")
        if not args.dry_run:
            if backend == "together":
                img = together_generate_image(prompt, key)
            else:
                img = gemini_generate_image(prompt, key)
            if img:
                out = ROOT / f"output/test_ai_thumb_{args.test}.png"
                out.write_bytes(resize_to_720p(img))
                print(f"Saved: {out}")
            else:
                print("Generation failed — model may need billing enabled")
        return

    if args.queue in ("en", "both", "all"):
        process_queue(QUEUE, key, args.force, args.dry_run, "EN", backend)

    if args.queue in ("ar", "both", "all"):
        process_queue(QUEUE_AR, key, args.force, args.dry_run, "AR", backend)

    if args.queue in ("id", "all"):
        process_queue(QUEUE_ID, key, args.force, args.dry_run, "ID", backend)

    if args.uploaded:
        process_queue(UPLOADED, key, args.force, args.dry_run, "UPLOADED", backend)


if __name__ == "__main__":
    main()
