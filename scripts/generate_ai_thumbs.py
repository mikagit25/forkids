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

STYLE_BASE = (
    "bright colorful children's illustration, cartoon style, "
    "bold outlines, cheerful expression, kids YouTube thumbnail, "
    "16:9 format 1280x720, no text"
)

STYLE_AR = (
    "رسوم متحركة للأطفال، ألوان زاهية، نمط كرتوني، "
    "ملصق قناة يوتيوب للأطفال، بدون نص"
)


def make_prompt(stem: str, meta: dict, is_ar: bool = False) -> str:
    """Build an image generation prompt from video metadata."""
    vtype  = meta.get("video_type", "")
    theme  = meta.get("theme", "animals")
    title  = meta.get("title", stem)

    # Strip channel suffix and clean title
    for s in ["| هابي بير كيدز", "| Happy Bear Kids", "هابي بير كيدز",
              "Happy Bear Kids", "#Shorts", "#shorts"]:
        title = title.replace(s, "")
    title = re.sub(r'[^\w\s؀-ۿ\-]', '', title).strip()

    # Detect character from stem
    name = re.sub(r'^ar_', '', re.sub(r'_\d{8}.*$', '', stem))
    character = ""
    for char in AR_NAMES:
        if char in name:
            character = char
            break

    # ── Build prompt by video type ────────────────────────────────────────────
    if "dance" in vtype or "dance" in name:
        if character:
            char_name = AR_NAMES.get(character, character) if is_ar else character.capitalize()
            if is_ar:
                prompt = (
                    f"كرتون {char_name} يرقص بسعادة، حركة راقصة ممتعة، "
                    f"خلفية ملونة مشرقة، {STYLE_AR}"
                )
            else:
                prompt = (
                    f"Cute cartoon {character} dancing happily, dynamic dance pose, "
                    f"bright colorful background with musical notes and stars, {STYLE_BASE}"
                )
        else:
            # Long 30-min dance video — crowd of characters
            theme_desc = {"animals": "animals", "fruits": "fruits",
                          "vegetables": "vegetables"}.get(theme, theme)
            if is_ar:
                prompt = (
                    f"مجموعة من الشخصيات الكرتونية ({theme_desc} بالعربية) "
                    f"يرقصون معاً، {STYLE_AR}"
                )
            else:
                prompt = (
                    f"Group of cute cartoon {theme_desc} characters dancing together joyfully, "
                    f"confetti and musical notes, 30 minute compilation badge, {STYLE_BASE}"
                )

    elif "counting" in vtype or "counting" in name:
        if is_ar:
            prompt = f"أرقام كرتونية كبيرة ملونة 1 2 3، حيوانات كرتونية تعد، {STYLE_AR}"
        else:
            prompt = (
                f"Big colorful cartoon numbers 1 2 3 floating, cute animals counting, "
                f"bright educational kids background, {STYLE_BASE}"
            )

    elif "color" in vtype or "color" in name:
        # Extract color
        color_match = re.search(
            r'(red|blue|green|yellow|orange|purple|pink|brown)', name)
        color = color_match.group(1) if color_match else "rainbow"
        if is_ar:
            colors_ar = {"red": "أحمر", "blue": "أزرق", "green": "أخضر",
                         "yellow": "أصفر", "orange": "برتقالي",
                         "purple": "بنفسجي", "pink": "وردي"}
            c_ar = colors_ar.get(color, color)
            prompt = (
                f"لون {c_ar}، دوائر وأشكال {c_ar} كبيرة وجميلة، "
                f"شخصيات كرتونية {c_ar}، {STYLE_AR}"
            )
        else:
            prompt = (
                f"Big bold {color} color theme, cartoon characters and objects in {color}, "
                f"educational color learning for kids, {STYLE_BASE}"
            )

    elif "shape" in vtype or "shape" in name or "float" in name:
        shape_match = re.search(
            r'(circle|square|triangle|star|heart|diamond|hexagon|oval)', name)
        shape = shape_match.group(1) if shape_match else "shapes"
        if is_ar:
            shapes_ar = {"circle": "دائرة", "square": "مربع", "triangle": "مثلث",
                         "star": "نجمة", "heart": "قلب", "diamond": "معين"}
            s_ar = shapes_ar.get(shape, "أشكال")
            prompt = f"شكل {s_ar} كرتوني كبير ملون، يرقص ويتحرك، {STYLE_AR}"
        else:
            prompt = (
                f"Cute cartoon {shape} shape character dancing and bouncing, "
                f"bright colors, educational shapes for kids, {STYLE_BASE}"
            )

    else:
        # Generic fallback
        if is_ar:
            prompt = f"شخصيات كرتونية للأطفال، {title[:40]}, {STYLE_AR}"
        else:
            prompt = f"Cute cartoon characters, {title[:60]}, {STYLE_BASE}"

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
    "short_", "ar_short_", "ar_counting_", "ar_color_",
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

        is_ar  = meta.get("language", "en") == "ar" or mp4.name.startswith("ar_")
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
    parser.add_argument("--queue",   choices=["en", "ar", "both", "none"], default="both")
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

    if args.queue in ("en", "both"):
        process_queue(QUEUE, key, args.force, args.dry_run, "EN", backend)

    if args.queue in ("ar", "both"):
        process_queue(QUEUE_AR, key, args.force, args.dry_run, "AR", backend)

    if args.uploaded:
        process_queue(UPLOADED, key, args.force, args.dry_run, "UPLOADED", backend)


if __name__ == "__main__":
    main()
