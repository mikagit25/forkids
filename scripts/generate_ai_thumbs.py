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
    "bright colorful children's illustration, Pixar-style 3D cartoon, "
    "bold clean composition, cheerful expression, kids YouTube thumbnail, "
    "16:9 format 1280x720, no watermarks, no logos, no brand names, no copyright symbols"
)

# AR channel: same style but absolutely no text — FLUX can't render Arabic (non-Latin)
STYLE_AR_NOTXT = (
    "bright colorful children's illustration, Pixar-style 3D cartoon, "
    "bold clean composition, cheerful expression, kids YouTube thumbnail, "
    "16:9 format 1280x720, no text, no letters, no words, no numbers, "
    "no watermarks, no logos, no brand names, no copyright symbols"
)

# ID channel: Indonesian uses Latin script → text allowed, same style as EN
# (STYLE_EN is reused for Indonesian)

# Objects shown per number (first object used as main thumbnail subject)
_NUM_OBJECTS = {
    "1": ("apple",      "one cute smiling apple"),
    "2": ("banana",     "two cute smiling bananas"),
    "3": ("apple",      "three cute smiling apples in a row"),
    "4": ("balloon",    "four colorful balloons with cute faces"),
    "5": ("orange",     "five cute smiling oranges"),
    "6": ("balloon",    "six colorful balloons floating upward"),
    "7": ("apple",      "seven cute smiling apples arranged in a cluster"),
    "8": ("orange",     "eight cute smiling oranges in two rows of four"),
    "9": ("apple",      "nine cute smiling apples arranged in three rows of three"),
    "10": ("balloon",   "ten colorful balloons clustered together"),
}


def make_prompt(stem: str, meta: dict, is_ar: bool = False) -> str:
    """Build an English image generation prompt from video metadata.

    Always English — FLUX/Gemini don't render Arabic text well.
    is_ar=True → adds 'no text, no letters' suffix to keep images clean.
    Indonesian (id) uses Latin script, so text is allowed — same style as EN.
    """
    vtype  = meta.get("video_type", "")
    theme  = meta.get("theme", "animals")
    style  = STYLE_AR_NOTXT if is_ar else STYLE_EN

    # Normalise stem: strip lang suffix and date
    name = re.sub(r'_(en|ar|id)$', '', re.sub(r'_\d{8}.*$', '', stem))
    name = re.sub(r'^(ar|id)_', '', name)

    # Detect specific character/object from filename
    character = ""
    for char in AR_NAMES:
        if char in name:
            character = char
            break

    # ── numbers / counting ────────────────────────────────────────────────────
    if "counting" in vtype or "counting" in name or vtype == "numbers" or "number_learn" in name:
        num_match = re.search(
            r'number_learn_(one|two|three|four|five|six|seven|eight|nine|ten)', name)
        digit_map = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
                     "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10"}
        if num_match:
            digit = digit_map[num_match.group(1)]
            obj_name, obj_desc = _NUM_OBJECTS.get(digit, ("apple", f"{digit} cute apples"))
            if is_ar:
                # No digit (FLUX can't render Arabic numerals cleanly)
                prompt = (
                    f"{obj_desc} with big round eyes and happy smiles, "
                    f"grouped together in a cheerful cluster, "
                    f"all faces clearly visible and unobstructed, "
                    f"bright warm gradient background, small colorful confetti around them, "
                    f"clean open composition, educational toddler video, {style}"
                )
            else:
                prompt = (
                    f"Giant bold bubble-letter number {digit} in vivid yellow with dark outline "
                    f"centered at the top of the image, "
                    f"{obj_desc} with big round eyes and happy smiles "
                    f"arranged in a neat row at the bottom, "
                    f"objects placed well below the number not overlapping it, "
                    f"all characters' faces clearly visible and unobstructed, "
                    f"bright cheerful background, small colorful confetti falling, "
                    f"clean composition with clear separation between number and objects, "
                    f"{style}"
                )
        else:
            if is_ar:
                prompt = (
                    f"Cute smiling cartoon apple and balloon characters in a cheerful group, "
                    f"all faces clearly visible, bright educational background, "
                    f"small confetti and sparkles, {style}"
                )
            else:
                prompt = (
                    f"Three giant bold bubble-letter numbers 1 2 3 in vivid colors at the top, "
                    f"cute smiling cartoon animals standing below them in a row, "
                    f"characters' faces unobstructed, bright cheerful background, "
                    f"small colorful confetti falling, {style}"
                )

    # ── colors ────────────────────────────────────────────────────────────────
    elif "color" in vtype or "color_learn" in name or "color" in name:
        color_match = re.search(
            r'(red|blue|green|yellow|orange|purple|pink|brown|white|black)', name)
        color = color_match.group(1) if color_match else "rainbow"
        if color == "rainbow":
            prompt = (
                f"Vibrant rainbow arc over a cheerful scene, cute cartoon bear character "
                f"standing below it with arms raised, colorful objects in every color, "
                f"bright saturated background, educational color learning for kids, {style}"
            )
        else:
            prompt = (
                f"Scene bathed in vivid {color} light, cute Pixar-style cartoon bear character "
                f"surrounded by large {color} objects like fruits and balloons, "
                f"bold {color} gradient background, character's face clearly visible, "
                f"educational color learning for toddlers, {style}"
            )

    # ── shapes ────────────────────────────────────────────────────────────────
    elif "shape" in vtype or "shape" in name or "float" in name:
        shape_match = re.search(
            r'(circle|square|triangle|star|heart|diamond|hexagon|oval|pentagon)', name)
        shape = shape_match.group(1) if shape_match else "circle"
        color_map = {
            "circle": "bright red", "square": "vivid blue", "triangle": "lime green",
            "star": "golden yellow", "heart": "hot pink", "diamond": "cyan",
            "hexagon": "deep purple", "oval": "orange", "pentagon": "teal",
        }
        shape_color = color_map.get(shape, "vivid")
        prompt = (
            f"Giant {shape_color} cartoon {shape} character with big cute eyes and wide happy smile "
            f"taking up most of the image, bold and eye-catching, "
            f"several smaller {shape} shapes with happy faces scattered in the background, "
            f"the main {shape}'s face is fully clear and unobstructed, "
            f"bright vivid background in contrasting color, educational shapes for kids, {style}"
        )

    # ── dance ─────────────────────────────────────────────────────────────────
    elif "dance" in vtype or "dance" in name:
        theme_en = {"animals": "animals", "fruits": "fruits",
                    "vegetables": "vegetables", "shapes": "geometric shapes",
                    "mixed": "cartoon characters"}.get(theme, "cartoon characters")
        if character:
            prompt = (
                f"Cute Pixar-style 3D {character} character in an energetic joyful dance pose, "
                f"arms raised, big smile, facing the viewer, "
                f"bright colorful background with musical notes and colorful confetti, "
                f"character face clearly visible and prominent, no shapes overlapping the face, "
                f"vibrant and eye-catching, {style}"
            )
        else:
            prompt = (
                f"Group of three cute Pixar-style 3D cartoon {theme_en} characters "
                f"dancing together joyfully, each with big smiles and raised arms, "
                f"all faces clearly visible and unobstructed, "
                f"colorful confetti and musical notes in the background, "
                f"bright vivid background, energetic and fun, {style}"
            )

    # ── character dialogue (Roundy the bear) ─────────────────────────────────
    elif vtype == "character_dialogue" or "character_dialogue" in name:
        topic_map = {
            "emotions":  ("happy bear showing emotions", "colorful emotion face icons around it"),
            "colors":    ("bear surrounded by colorful paint splashes", "rainbow colors everywhere"),
            "numbers":   ("bear pointing at floating numbers", "colorful number bubbles"),
            "animals":   ("bear surrounded by cute animal friends", "jungle scene"),
        }
        topic = next((k for k in topic_map if k in name), None)
        desc, detail = topic_map.get(topic, ("cute cartoon bear character talking to child",
                                             "speech bubble, friendly educational scene"))
        prompt = (
            f"Cute Pixar-style 3D bear character with big expressive eyes and warm smile, "
            f"{desc}, {detail}, "
            f"bear's face is the clear main focus of the image, "
            f"bright friendly background, engaging and inviting for toddlers, {style}"
        )

    # ── ABC / vocabulary shorts ───────────────────────────────────────────────
    elif vtype == "short_vocab" or "short_vocab" in name or "vocab" in name:
        letter_match = re.search(r'short_vocab_([a-z])', name)
        if letter_match:
            letter = letter_match.group(1).upper()
            prompt = (
                f"Giant bold bubble letter {letter} in vivid color taking up the left half, "
                f"cute cartoon object starting with {letter} on the right side with big eyes, "
                f"letter and object clearly separated, bright cheerful background, "
                f"ABC learning for toddlers, {style}"
            )
        else:
            prompt = (
                f"Colorful alphabet letters A B C in giant bubble style, "
                f"cute cartoon characters around them, bright educational background, {style}"
            )

    # ── Indonesian nursery songs ──────────────────────────────────────────────
    elif vtype == "nursery_id" or "nursery_id" in name or "balonku" in name or "cicak" in name \
            or "naik_kereta" in name or "pelangi" in name or "dua_mata" in name or "kebunku" in name:
        song_visuals = {
            "balonku":     "three colorful balloons with happy faces floating in blue sky, "
                           "cute cartoon bear holding balloon strings below",
            "cicak":       "cute cartoon gecko character with big eyes clinging to a wall, "
                           "bright tropical green leaves behind it",
            "naik_kereta": "cute cartoon steam train with smiling face, colorful carriages, "
                           "happy animal passengers waving from windows",
            "pelangi":     "beautiful vivid rainbow arching across blue sky, "
                           "cute cartoon animals standing under it with arms raised joyfully",
            "dua_mata":    "cute cartoon bear character pointing to its big round eyes with a smile, "
                           "simple bright background",
            "kebunku":     "colorful garden with giant sunflowers and flowers, "
                           "cute cartoon butterfly with big eyes landing on a flower",
        }
        song_key = next((k for k in song_visuals if k in name), None)
        visual = song_visuals.get(song_key,
                    "cute cartoon characters singing together, colorful musical notes floating around")
        prompt = f"{visual}, bright cheerful kids illustration, {style}"

    # ── Arabic nursery songs ───────────────────────────────────────────────────
    elif vtype == "nursery_ar" or "nursery_ar" in name or "batta_batta" in name \
            or "ya_matar" in name or "dajaja" in name:
        song_visuals = {
            "batta_batta": "cute Pixar-style cartoon duck with big eyes splashing happily in a pond, "
                           "water droplets sparkling around it",
            "ya_matar":    "cartoon rain clouds with smiling faces and bright rainbow, "
                           "colorful raindrops falling, happy animals dancing in the rain",
            "dajaja":      "cute cartoon mother hen with fluffy yellow baby chicks around her, "
                           "cheerful sunny farm background",
        }
        song_key = next((k for k in song_visuals if k in name), None)
        visual = song_visuals.get(song_key,
                    "cute cartoon animals in a cheerful singing pose, colorful musical notes")
        prompt = f"{visual}, bright cheerful kids illustration, {style}"

    # ── lullaby / sensory ─────────────────────────────────────────────────────
    elif vtype in ("sensory_loop", "lullaby_long") or "sensory" in name or "lullaby" in name:
        prompt = (
            f"Dreamy night sky with glowing crescent moon and soft twinkling stars, "
            f"gentle pastel clouds in purple and blue tones, "
            f"floating soft glowing orbs and sparkles, "
            f"peaceful and magical baby sleep atmosphere, "
            f"16:9 format 1280x720, no text, no letters, no words, no numbers, "
            f"no faces, no watermarks, no logos, no brand names"
        )

    # ── dancing shapes ────────────────────────────────────────────────────────
    elif vtype == "dance_shape" or "dance_shape" in name:
        prompt = (
            f"Four cute cartoon geometric shape characters — a circle, square, triangle, and star — "
            f"each with big eyes and wide smiles, dancing together in a joyful pose, "
            f"all faces clearly visible and unobstructed, "
            f"bright vivid pastel background with colorful confetti, {style}"
        )

    # ── stars and bubbles ─────────────────────────────────────────────────────
    elif vtype == "stars_bubbles" or "stars_bubble" in name:
        prompt = (
            f"Dozens of transparent soap bubbles floating in a magical glowing scene, "
            f"one giant bubble in the center reflecting rainbow light, "
            f"soft twinkling stars in the background, "
            f"sparkles and light trails, dreamy and mesmerizing for babies, "
            f"16:9 format 1280x720, no text, no letters, no words, no numbers, "
            f"no watermarks, no logos, no brand names"
        )

    # ── generic fallback ──────────────────────────────────────────────────────
    else:
        if character:
            prompt = (
                f"Cute Pixar-style 3D {character} character with big eyes and happy smile, "
                f"face clearly visible and prominent, bright colorful background, "
                f"educational kids video, {style}"
            )
        else:
            prompt = (
                f"Three cute Pixar-style cartoon animal characters with big smiles "
                f"waving at the viewer, all faces clearly visible, "
                f"bright vivid colorful background, educational kids video, {style}"
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
    parser.add_argument("--shorts", action="store_true",
                        help="Process shorts (short_* files) instead of long videos")
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

    long_only = not args.shorts

    if args.queue in ("en", "both", "all"):
        process_queue(QUEUE, key, args.force, args.dry_run, "EN", backend, long_only=long_only)

    if args.queue in ("ar", "both", "all"):
        process_queue(QUEUE_AR, key, args.force, args.dry_run, "AR", backend, long_only=long_only)

    if args.queue in ("id", "all"):
        process_queue(QUEUE_ID, key, args.force, args.dry_run, "ID", backend, long_only=long_only)

    if args.uploaded:
        process_queue(UPLOADED, key, args.force, args.dry_run, "UPLOADED", backend, long_only=long_only)


if __name__ == "__main__":
    main()
