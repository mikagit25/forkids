#!/usr/bin/env python3
"""
Generate PeekABooLong videos — ~18 min peek-a-boo with ALL 3D sprites.

Automatically collects every *_3d.png / flux sprite from remotion/public/sprites/,
shuffles them and renders ONE Remotion pass — no FFmpeg looping needed.

Default: 88 sprites × 12s/cycle (cycleDuration=360) = ~17.6 min unique content.
Fast preview: --cycle 120 (4s/cycle → ~5.9 min).

One render → EN queue + AR queue copy (no text, universal).

Usage:
    python3 scripts/generate_peekaboo_long.py
    python3 scripts/generate_peekaboo_long.py --variant animals
    python3 scripts/generate_peekaboo_long.py --cycle 120 --dry-run
    python3 scripts/generate_peekaboo_long.py --variant mix --shuffle 2  # 2nd shuffle seed
"""
import argparse
import base64
import json
import random
import subprocess
import shutil
from datetime import datetime
from pathlib import Path

import requests
import yaml

ROOT     = Path(__file__).resolve().parent.parent
REMOTION = ROOT / "remotion"
SPRITES  = REMOTION / "public" / "sprites"
QUEUE_EN = ROOT / "output" / "queue"
QUEUE_AR = ROOT / "output" / "queue_ar"
TOGETHER_KEY_FILE = ROOT / "credentials" / "together_api_key.txt"
TOGETHER_URL      = "https://api.together.xyz/v1/images/generations"
TOGETHER_MODEL    = "black-forest-labs/FLUX.1-schnell"
DATE_STR          = datetime.now().strftime("%Y%m%d")
FPS               = 30

# ── Color palette per sprite category ────────────────────────────────────────

CATEGORY_COLORS = {
    "animals":    ["#FF7043","#42A5F5","#EC407A","#5C6BC0","#FFA726","#7E57C2","#66BB6A","#26A69A","#8D6E63","#78909C"],
    "animals_flux":["#FF8F00","#43A047","#E91E63","#0288D1","#6D4C41","#00ACC1","#7B1FA2","#558B2F","#D84315","#37474F"],
    "animals_3d": ["#A1887F","#4CAF50","#9C27B0","#2196F3","#FF5722","#607D8B","#FF9800"],
    "fruits":     ["#E53935","#FDD835","#E91E63","#FB8C00","#388E3C","#C62828","#F9A825","#D81B60","#1565C0","#2E7D32"],
    "vegetables": ["#EF6C00","#F9A825","#E64A19","#388E3C","#C62828","#558B2F","#4E342E","#00695C","#1565C0","#6A1B9A"],
    "objects":    ["#0097A7","#7B1FA2","#1976D2","#388E3C","#F57C00","#C62828","#AD1457","#00838F","#4527A0","#2E7D32"],
    "characters": ["#A1887F","#FF8F00","#8D6E63","#6D4C41"],
}


def collect_sprites(variant: str, shuffle_seed: int) -> list[dict]:
    """
    Collect all 3D/flux sprites from remotion/public/sprites/ and assign
    box colours deterministically per category.
    """
    # Category → glob pattern → colour pool
    SOURCES = [
        ("animals",     SPRITES / "animals",     "*_3d.png"),
        ("animals_flux",SPRITES / "animals_flux","*.png"),
        ("animals_3d",  SPRITES / "animals_3d",  "*.png"),
        ("fruits",      SPRITES / "fruits",       "*_3d.png"),
        ("vegetables",  SPRITES / "vegetables",   "*_3d.png"),
        ("objects",     SPRITES / "objects",       "*_3d.png"),
        ("characters",  SPRITES / "characters",   "*.png"),
    ]

    # Filter by variant
    if variant == "animals":
        SOURCES = [s for s in SOURCES if s[0] in ("animals","animals_flux","animals_3d","characters")]
    elif variant == "fruits_veggies":
        SOURCES = [s for s in SOURCES if s[0] in ("fruits","vegetables","characters")]
    # "mix" = all sources (default)

    chars = []
    for cat, folder, pattern in SOURCES:
        if not folder.exists():
            continue
        colors = CATEGORY_COLORS.get(cat, ["#42A5F5"])
        files  = sorted(f for f in folder.glob(pattern) if ".bak" not in f.name)
        for i, f in enumerate(files):
            rel = f.relative_to(SPRITES).as_posix()
            chars.append({
                "sprite":   rel,
                "boxColor": colors[i % len(colors)],
            })

    # Shuffle for variety
    rng = random.Random(shuffle_seed)
    rng.shuffle(chars)
    return chars


# ── Thumbnail generation ──────────────────────────────────────────────────────

THUMB_PROMPTS = {
    "mix": (
        "colorful cardboard gift box with cute 3D cartoon bear popping out joyfully, "
        "confetti and sparkles everywhere, bright festive kids animation style, 1280x720, "
        "animals fruits vegetables characters surprise"
    ),
    "animals": (
        "colorful cardboard box with cute 3D cartoon animals popping out, bear cat dog rabbit penguin, "
        "confetti explosion, kids animation style, vibrant bright colors, 1280x720"
    ),
    "fruits_veggies": (
        "colorful cardboard box with 3D cartoon apple banana strawberry carrot popping out with confetti, "
        "kids animation style, bright playful colors, 1280x720"
    ),
}


def generate_thumbnail(variant: str, out_path: Path, dry_run: bool) -> bool:
    if out_path.exists():
        return True
    if dry_run:
        print(f"  [DRY RUN] Thumb → {out_path.name}")
        return True
    try:
        api_key = TOGETHER_KEY_FILE.read_text().strip()
        resp = requests.post(
            TOGETHER_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "python-requests/2.31.0",
            },
            json={
                "model": TOGETHER_MODEL,
                "prompt": THUMB_PROMPTS.get(variant, THUMB_PROMPTS["mix"]),
                "width": 1280, "height": 720,
                "steps": 4, "n": 1, "response_format": "b64_json",
            },
            timeout=90,
        )
        resp.raise_for_status()
        out_path.write_bytes(base64.b64decode(resp.json()["data"][0]["b64_json"]))
        print(f"  ✓ Thumb → {out_path.name}")
        return True
    except Exception as e:
        print(f"  ✗ Thumb failed: {e}")
        return False


# ── Meta YAML ────────────────────────────────────────────────────────────────

def make_meta(variant: str, lang: str, duration_min: int, n_chars: int, music: str) -> dict:
    variant_labels = {
        "mix":          {"en": "Animals, Fruits & Veggies", "ar": "حيوانات وفواكه وخضروات"},
        "animals":      {"en": "Animals",                   "ar": "الحيوانات"},
        "fruits_veggies":{"en": "Fruits & Vegetables",     "ar": "فواكه وخضروات"},
    }
    label = variant_labels.get(variant, variant_labels["mix"])

    titles = {
        "en": f"🎁 Peek-a-Boo {label['en']}! | {duration_min} Min | Happy Bear Kids",
        "ar": f"🎁 بيكا بو {label['ar']}! | {duration_min} دقيقة | هابي بير كيدز",
    }
    descs = {
        "en": (
            f"Who's hiding in the box? 🎁 Watch {n_chars} adorable 3D characters pop out one by one "
            f"in this {duration_min}-minute peek-a-boo adventure! Every reveal is different — "
            "animals, fruits, vegetables and more surprise your baby!\n\n"
            "🌟 Perfect for babies and toddlers 0–3 years\n"
            "🎉 No words — safe for all languages\n"
            "🎵 Fun cheerful music\n"
            "🎁 Every character gets their own colour box\n"
            "👶 Great for sensory development and attention\n\n"
            f"#peekaboo #babyanimals #toddlervideos #happybearkids #babytv "
            "#surprisebox #peekaboogame #babyplay #kidsvideos #learningforkids "
            "#animalsfortoddlers #infantvideos #sensoryplay"
        ),
        "ar": (
            f"من يختبئ في الصندوق؟ 🎁 شاهد {n_chars} شخصية ثلاثية الأبعاد رائعة تقفز واحدة تلو "
            f"الأخرى في مغامرة بيكا بو مدتها {duration_min} دقيقة!\n\n"
            "🌟 مثالي للرضع والأطفال 0-3 سنوات\n"
            "🎉 بدون كلام — مناسب لجميع اللغات\n"
            "🎵 موسيقى مرحة ومبهجة\n\n"
            "#بيكابو #حيوانات_للأطفال #هابي_بير_كيدز #برامج_اطفال"
        ),
    }
    tags = [
        "peek a boo", "peekaboo", "baby animals", "toddler videos", "happy bear kids",
        "surprise box", "baby tv", "peek a boo game", "animals for kids",
        "kids animation", "3d cartoon", "baby play", "educational baby",
        "peek-a-boo animals", "infant videos", "sensory play", "baby surprise",
        "learning for babies", "nursery videos",
    ]

    return {
        "title":         titles[lang],
        "description":   descs[lang],
        "tags":          tags,
        "video_type":    "peekaboo_long",
        "language":      lang,
        "is_short":      False,
        "status":        "public",
        "made_for_kids": True,
        "music_track":   music,
    }


# ── Render ────────────────────────────────────────────────────────────────────

MUSIC_TRACKS = [
    "Monkeys Spinning Monkeys.mp3",
    "Happy Happy Game Show.mp3",
    "Carefree.mp3",
    "Wholesome.mp3",
    "Heartwarming.mp3",
    "Merry Go.mp3",
    "Pinball Spring.mp3",
]

# ── Background images available per theme ─────────────────────────────────────

THEME_BACKGROUNDS = {
    "warm":     None,                       # no bgImage — plain gradient
    "night":    "night_magic.jpg",          # dark starry sky (from generate_kids_backgrounds.py)
    "tropical": "tropical_beach.jpg",
    "candy":    "candy_world.jpg",
}

THEME_MUSIC = {
    "warm":     None,    # use shuffle-based selection
    "night":    "Heartwarming.mp3",
    "tropical": "Carefree.mp3",
    "candy":    "Pinball Spring.mp3",
}


def render(characters: list, cycle_dur: int, music: str, theme: str,
           out_path: Path, dry_run: bool) -> bool:
    n        = len(characters)
    n_frames = n * cycle_dur
    dur_min  = round(n_frames / FPS / 60, 1)

    props: dict = {
        "characters":    characters,
        "cycleDuration": cycle_dur,
        "musicFile":     music,
        "musicVolume":   0.20,
    }
    if theme and theme != "warm":
        props["boxTheme"] = theme
        bg = THEME_BACKGROUNDS.get(theme)
        if bg:
            bg_path = REMOTION / "public" / "backgrounds" / bg
            if bg_path.exists():
                props["bgImage"] = bg
                props["bgDim"]   = 0.22
    else:
        props["bgColor"]    = "#FFF9C4"
        props["bgColorEnd"] = "#E1F5FE"

    cmd = [
        "npx", "remotion", "render",
        "src/index.ts", "PeekABooLong",
        str(out_path),
        "--props", json.dumps(props),
        "--frames", f"0-{n_frames - 1}",
        "--concurrency", "1",
        "--log", "error",
    ]
    print(f"  Rendering {n} chars × {cycle_dur}f = {n_frames}f ({dur_min} min) → {out_path.name}")
    if dry_run:
        print(f"  [DRY RUN] {' '.join(cmd[:6])} ...")
        return True
    res = subprocess.run(cmd, cwd=str(REMOTION), capture_output=True, text=True, timeout=7200)
    if res.returncode != 0:
        print(f"  ✗ Render failed:\n{res.stderr[-600:]}")
        return False
    sz = out_path.stat().st_size // 1024 // 1024
    print(f"  ✓ Rendered ({sz} MB)")
    return True


# ── Thumbnail prompts extended by theme ───────────────────────────────────────

THUMB_PROMPTS_THEMED = {
    ("mix",          "warm"):     THUMB_PROMPTS["mix"],
    ("animals",      "warm"):     THUMB_PROMPTS["animals"],
    ("fruits_veggies","warm"):    THUMB_PROMPTS["fruits_veggies"],
    ("mix",          "night"):    (
        "dark starry night sky, glowing gift box with cute 3D cartoon animals popping out, "
        "gold sparkles, magical night kids animation, 1280x720"
    ),
    ("animals",      "night"):    (
        "magical night sky, glowing box, cute 3D cartoon animals popping out with gold confetti, "
        "dark purple background, kids animation, 1280x720"
    ),
    ("fruits_veggies","night"):   (
        "starry night, glowing box with 3D cartoon fruits and vegetables popping out, "
        "gold sparkle confetti, magical dark sky, kids animation, 1280x720"
    ),
    ("mix",          "tropical"): (
        "tropical beach paradise, colorful gift box with cute 3D cartoon animals fruits veggies popping out, "
        "bright confetti, sunny kids animation, 1280x720"
    ),
    ("animals",      "tropical"): (
        "tropical beach, vibrant box with cute 3D cartoon animals popping out joyfully, "
        "confetti explosion, bright summer colors, kids animation, 1280x720"
    ),
    ("fruits_veggies","tropical"):(
        "tropical beach, colorful box with 3D cartoon fruits and vegetables popping out, "
        "confetti, bright vivid colors, kids animation, 1280x720"
    ),
    ("mix",          "candy"):    (
        "candy land pink pastel world, cute gift box with 3D cartoon animals fruits veggies popping out, "
        "sparkle confetti, sweet kids animation, 1280x720"
    ),
    ("animals",      "candy"):    (
        "candy land, pastel pink gift box with cute 3D cartoon animals popping out, "
        "colorful confetti, sweet kids animation, 1280x720"
    ),
    ("fruits_veggies","candy"):   (
        "candy world, pastel gift box with 3D cartoon fruits and vegetables popping out, "
        "sparkle confetti, sweet pastel colors, kids animation, 1280x720"
    ),
}


def generate_thumbnail_themed(variant: str, theme: str, out_path: Path, dry_run: bool) -> bool:
    if out_path.exists():
        return True
    if dry_run:
        print(f"  [DRY RUN] Thumb → {out_path.name}")
        return True
    try:
        api_key = TOGETHER_KEY_FILE.read_text().strip()
        prompt  = THUMB_PROMPTS_THEMED.get((variant, theme), THUMB_PROMPTS["mix"])
        resp = requests.post(
            TOGETHER_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "python-requests/2.31.0",
            },
            json={
                "model": TOGETHER_MODEL,
                "prompt": prompt,
                "width": 1280, "height": 720,
                "steps": 4, "n": 1, "response_format": "b64_json",
            },
            timeout=90,
        )
        resp.raise_for_status()
        out_path.write_bytes(base64.b64decode(resp.json()["data"][0]["b64_json"]))
        print(f"  ✓ Thumb → {out_path.name}")
        return True
    except Exception as e:
        print(f"  ✗ Thumb failed: {e}")
        return False


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=["mix","animals","fruits_veggies"], default="mix",
                        help="Sprite set to include")
    parser.add_argument("--cycle",   type=int, default=360,
                        help="Frames per reveal cycle (360=12s, 120=4s)")
    parser.add_argument("--shuffle", type=int, default=1,
                        help="Random seed for character order")
    parser.add_argument("--theme",   choices=["warm","night","tropical","candy"], default="warm",
                        help="Visual theme: warm (default) | night | tropical | candy")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force",   action="store_true")
    args = parser.parse_args()

    variant   = args.variant
    cycle_dur = args.cycle
    shuffle   = args.shuffle
    theme     = args.theme
    dry_run   = args.dry_run

    characters = collect_sprites(variant, shuffle)
    n          = len(characters)
    dur_s      = n * cycle_dur / FPS
    dur_min    = round(dur_s / 60, 1)

    # Music: theme overrides shuffle-based selection
    music = THEME_MUSIC.get(theme) or MUSIC_TRACKS[(shuffle - 1) % len(MUSIC_TRACKS)]

    theme_sfx = "" if theme == "warm" else f"_{theme}"
    slug   = f"peekaboo_{variant}{theme_sfx}_s{shuffle}_{DATE_STR}"
    vid_en = QUEUE_EN / f"{slug}.mp4"
    vid_ar = QUEUE_AR / f"{slug}.mp4"

    print(f"\n=== PeekABooLong ===")
    print(f"  Variant:  {variant}  ({n} sprites)")
    print(f"  Theme:    {theme}")
    print(f"  Cycle:    {cycle_dur}f = {cycle_dur/FPS:.1f}s")
    print(f"  Duration: {n} × {cycle_dur/FPS:.1f}s = {dur_min} min  (no looping)")
    print(f"  Music:    {music}")
    print(f"  Shuffle:  #{shuffle}\n")

    # Render
    if not vid_en.exists() or args.force:
        ok = render(characters, cycle_dur, music, theme, vid_en, dry_run)
        if not ok:
            return
    else:
        print(f"  ✓ EN video exists: {vid_en.name}")

    # Copy to AR queue
    if not vid_ar.exists() or args.force:
        if dry_run:
            print(f"  [DRY RUN] Copy → queue_ar/{vid_en.name}")
        elif vid_en.exists():
            shutil.copy2(vid_en, vid_ar)
            print(f"  ✓ Copied → queue_ar/{vid_en.name}")

    # Thumbnails
    thumb_en = QUEUE_EN / f"thumb_{slug}.png"
    thumb_ar = QUEUE_AR / f"thumb_{slug}.png"
    generate_thumbnail_themed(variant, theme, thumb_en, dry_run)
    if thumb_en.exists() and not thumb_ar.exists() and not dry_run:
        shutil.copy2(thumb_en, thumb_ar)
        print(f"  ✓ Thumb copied → queue_ar")

    # Meta YAML
    for lang, queue in [("en", QUEUE_EN), ("ar", QUEUE_AR)]:
        meta_path = queue / f"meta_{slug}.yaml"
        if not meta_path.exists() or args.force:
            meta = make_meta(variant, lang, int(dur_min), n, music)
            if not dry_run:
                meta_path.write_text(yaml.dump(meta, allow_unicode=True, sort_keys=False))
                print(f"  ✓ Meta {lang.upper()} → {meta_path.name}")
            else:
                print(f"  [DRY RUN] meta {lang.upper()}")

    print(f"\nDone — {dur_min} min, {n} unique characters, no repetition.")


if __name__ == "__main__":
    main()
