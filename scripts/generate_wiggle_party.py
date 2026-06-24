#!/usr/bin/env python3
"""
generate_wiggle_party.py — Wiggle Party series (text-free, 3 separate renders per theme)

PIP/BWW style: 6-8 sprites on screen simultaneously, wobble effect always on,
large motion amplitudes. Universal content — no text, no voice.

Each theme renders 3 SEPARATE videos (EN/AR/ID) with DIFFERENT music and
slightly different background colour — avoids YouTube duplicate fingerprinting.

Themes:
  animals    — 8 animals, lively colours
  fruits     — 8 fruits, tropical feel
  vegetables — 8 vegetables, vivid palette
  mixed      — 4 animals + 4 fruits, rainbow chaos
  night      — 8 animals, dim palette, slow motion, bedtime

Usage:
  python3 scripts/generate_wiggle_party.py --list
  python3 scripts/generate_wiggle_party.py --themes all
  python3 scripts/generate_wiggle_party.py --themes animals fruits
  python3 scripts/generate_wiggle_party.py --force
  python3 scripts/generate_wiggle_party.py --regen-meta
"""
import argparse, base64, json, subprocess, sys, time
from datetime import datetime
from pathlib import Path

import requests
import yaml

ROOT         = Path(__file__).resolve().parent.parent
QUEUE_EN     = ROOT / "output" / "queue"
QUEUE_AR     = ROOT / "output" / "queue_ar"
QUEUE_ID     = ROOT / "output" / "queue_id"
TOGETHER_KEY = (ROOT / "credentials" / "together_api_key.txt").read_text().strip()
TOGETHER_URL = "https://api.together.xyz/v1/images/generations"

# ── Sprite grid layouts ────────────────────────────────────────────────────────
GRID_8 = [
    {"posX": 0.12, "posY": 0.28}, {"posX": 0.37, "posY": 0.22},
    {"posX": 0.63, "posY": 0.22}, {"posX": 0.88, "posY": 0.28},
    {"posX": 0.12, "posY": 0.68}, {"posX": 0.37, "posY": 0.74},
    {"posX": 0.63, "posY": 0.74}, {"posX": 0.88, "posY": 0.68},
]
GRID_6 = [
    {"posX": 0.18, "posY": 0.28}, {"posX": 0.50, "posY": 0.22}, {"posX": 0.82, "posY": 0.28},
    {"posX": 0.18, "posY": 0.68}, {"posX": 0.50, "posY": 0.74}, {"posX": 0.82, "posY": 0.68},
]

def make_sprites(paths, grid, size=220):
    return [
        {"path": p, "size": size, "posX": grid[i]["posX"], "posY": grid[i]["posY"], "seed": i + 1}
        for i, p in enumerate(paths)
    ]

def make_blocks(slow=False):
    amp = 55 if slow else 90
    per = 4.5 if slow else 3.0
    return [
        {"startSec":    0, "endSec":  180, "motion": "WAVE",   "period": per,       "amplitude": amp, "waveDelay": 0.35, "wobble": True},
        {"startSec":  180, "endSec":  360, "motion": "BOUNCE", "period": per,       "amplitude": amp, "wobble": True},
        {"startSec":  360, "endSec":  540, "motion": "SWAY",   "period": per,       "amplitude": amp, "wobble": True},
        {"startSec":  540, "endSec":  720, "motion": "DRIFT",  "period": per * 1.5, "amplitude": amp, "wobble": True},
        {"startSec":  720, "endSec":  900, "motion": "ORBIT",  "period": per,       "amplitude": amp, "orbitCenterX": 0.50, "orbitCenterY": 0.45, "wobble": True},
        {"startSec":  900, "endSec": 1080, "motion": "BOB",    "period": per,       "amplitude": amp, "wobble": True},
        {"startSec": 1080, "endSec": 1260, "motion": "MARCH",  "period": 12,        "amplitude": amp, "bobAmplitude": 35, "wobble": True},
        {"startSec": 1260, "endSec": 1440, "motion": "PULSE",  "period": per,       "amplitude": 30,  "wobble": True},
        {"startSec": 1440, "endSec": 1620, "motion": "WAVE",   "period": per,       "amplitude": amp, "waveDelay": 0.25, "wobble": True},
        {"startSec": 1620, "endSec": 1800, "motion": "BOUNCE", "period": per,       "amplitude": amp, "wobble": True},
    ]

# ── Theme definitions ──────────────────────────────────────────────────────────
# Each theme has per-channel music + bg variation → unique fingerprint per channel.
# Accent colour also differs subtly. Same sprites/motion — different audio+visual.
THEMES = {
    "animals": {
        "sprites": make_sprites([
            "animals/bear_3d.png", "animals/cat_3d.png", "animals/dog_3d.png",
            "animals/rabbit_3d.png", "animals/frog_3d.png", "animals/penguin_3d.png",
            "animals/elephant_3d.png", "animals/fox_3d.png",
        ], GRID_8),
        "blocks": make_blocks(),
        "channels": {
            "en": {"music": "Carefree.mp3",            "bgColor": "#FFF9C4", "accentColor": "#FFD54F"},
            "ar": {"music": "Wholesome.mp3",            "bgColor": "#FFF3E0", "accentColor": "#FFCC80"},
            "id": {"music": "Happy Happy Game Show.mp3","bgColor": "#F1F8E9", "accentColor": "#C5E1A5"},
        },
        "thumb_prompt": "8 cute 3D cartoon animals dancing together — bear cat dog rabbit frog penguin elephant fox, colorful party background, bright vivid colors, kids animation, joyful wiggly fun",
        "titles": {
            "en": "Animal Wiggle Party! 30 Minutes | Happy Bear Kids",
            "ar": "حفلة رقص الحيوانات! 30 دقيقة | هابي بير كيدز",
            "id": "Pesta Goyang Hewan! 30 Menit | Happy Bear Kids Indonesia",
        },
        "tags": ["animal dance", "wiggle party", "kids music", "30 minutes", "toddler fun",
                 "cartoon animals", "baby dance", "animals dancing", "nursery rhymes",
                 "happy bear kids", "children entertainment"],
    },
    "fruits": {
        "sprites": make_sprites([
            "fruits/apple_3d.png", "fruits/banana_3d.png", "fruits/strawberry_3d.png",
            "fruits/grapes_3d.png", "fruits/watermelon_3d.png", "fruits/orange_3d.png",
            "fruits/pineapple_3d.png", "fruits/cherry_3d.png",
        ], GRID_8),
        "blocks": make_blocks(),
        "channels": {
            "en": {"music": "Monkeys Spinning Monkeys.mp3", "bgColor": "#E8F5E9", "accentColor": "#A5D6A7"},
            "ar": {"music": "Merry Go.mp3",                 "bgColor": "#E0F2F1", "accentColor": "#80CBC4"},
            "id": {"music": "Hyperfun.mp3",                 "bgColor": "#FCE4EC", "accentColor": "#F48FB1"},
        },
        "thumb_prompt": "8 cute 3D cartoon fruits dancing — apple banana strawberry grapes watermelon orange pineapple cherry, tropical party, bright vivid colors, kids animation style",
        "titles": {
            "en": "Fruit Wiggle Party! 30 Minutes | Happy Bear Kids",
            "ar": "حفلة رقص الفواكه! 30 دقيقة | هابي بير كيدز",
            "id": "Pesta Goyang Buah! 30 Menit | Happy Bear Kids Indonesia",
        },
        "tags": ["fruit dance", "wiggle party", "kids music", "30 minutes", "toddler fun",
                 "cartoon fruits", "dancing fruits", "fruits for kids",
                 "happy bear kids", "children entertainment"],
    },
    "vegetables": {
        "sprites": make_sprites([
            "vegetables/carrot_3d.png", "vegetables/broccoli_3d.png", "vegetables/corn_3d.png",
            "vegetables/tomato_3d.png", "vegetables/cucumber_3d.png", "vegetables/potato_3d.png",
            "vegetables/mushroom_3d.png", "vegetables/pepper_3d.png",
        ], GRID_8),
        "blocks": make_blocks(),
        "channels": {
            "en": {"music": "Fluffing a Duck.mp3", "bgColor": "#F3E5F5", "accentColor": "#CE93D8"},
            "ar": {"music": "Quirky Dog.mp3",       "bgColor": "#EDE7F6", "accentColor": "#B39DDB"},
            "id": {"music": "Pinball Spring.mp3",   "bgColor": "#E8EAF6", "accentColor": "#9FA8DA"},
        },
        "thumb_prompt": "8 cute 3D cartoon vegetables dancing — carrot broccoli corn tomato cucumber potato mushroom pepper, colorful party, vivid colors, kids animation",
        "titles": {
            "en": "Vegetable Wiggle Party! 30 Minutes | Happy Bear Kids",
            "ar": "حفلة رقص الخضروات! 30 دقيقة | هابي بير كيدز",
            "id": "Pesta Goyang Sayuran! 30 Menit | Happy Bear Kids Indonesia",
        },
        "tags": ["vegetable dance", "wiggle party", "kids music", "30 minutes", "toddler fun",
                 "cartoon vegetables", "vegetables for kids", "happy bear kids"],
    },
    "mixed": {
        "sprites": make_sprites([
            "animals/bear_3d.png",  "animals/cat_3d.png",   "animals/frog_3d.png",   "animals/penguin_3d.png",
            "fruits/apple_3d.png",  "fruits/banana_3d.png", "fruits/strawberry_3d.png", "fruits/orange_3d.png",
        ], GRID_8),
        "blocks": make_blocks(),
        "channels": {
            "en": {"music": "Pixelland.mp3",          "bgColor": "#E3F2FD", "accentColor": "#90CAF9"},
            "ar": {"music": "Life of Riley.mp3",       "bgColor": "#E8F5E9", "accentColor": "#A5D6A7"},
            "id": {"music": "Walking Along.mp3",       "bgColor": "#FFF8E1", "accentColor": "#FFE082"},
        },
        "thumb_prompt": "8 cute 3D cartoon characters dancing — bear cat frog penguin plus apple banana strawberry orange, rainbow party, vivid colors, kids joyful animation",
        "titles": {
            "en": "Animal & Fruit Wiggle Party! 30 Minutes | Happy Bear Kids",
            "ar": "حفلة رقص الحيوانات والفواكه! 30 دقيقة | هابي بير كيدز",
            "id": "Pesta Goyang Hewan & Buah! 30 Menit | Happy Bear Kids Indonesia",
        },
        "tags": ["wiggle party", "kids music", "30 minutes", "toddler fun",
                 "cartoon characters", "baby dance", "happy bear kids"],
    },
    "night": {
        "sprites": make_sprites([
            "animals/bear_3d.png", "animals/owl_3d.png",    "animals/rabbit_3d.png",
            "animals/cat_3d.png",  "animals/fox_3d.png",    "animals/penguin_3d.png",
        ], GRID_6, size=260),
        "blocks": make_blocks(slow=True),
        "nightMode": True,
        "bgEffect": "none",
        "channels": {
            "en": {"music": "Gymnopedie No 1.mp3",  "bgColor": "#1A237E", "bgColorEnd": "#0D0D2B", "accentColor": "#5C6BC0"},
            "ar": {"music": "Crinoline Dreams.mp3",  "bgColor": "#1B1464", "bgColorEnd": "#0A0A20", "accentColor": "#4A4880"},
            "id": {"music": "Heartwarming.mp3",      "bgColor": "#1A1A3E", "bgColorEnd": "#080818", "accentColor": "#534FA0"},
        },
        "thumb_prompt": "6 cute cartoon animals sleeping dancing at night — bear owl rabbit cat fox penguin, dark blue starry background, soft glowing colors, bedtime relaxing kids animation",
        "titles": {
            "en": "Sleepy Animal Wiggle Night | 30 Minutes | Happy Bear Kids",
            "ar": "حيوانات ترقص ليلاً | 30 دقيقة | هابي بير كيدز",
            "id": "Hewan Bergoyang Malam Hari | 30 Menit | Happy Bear Kids Indonesia",
        },
        "tags": ["bedtime animals", "lullaby dance", "sleep music", "30 minutes", "toddler sleep",
                 "calm kids music", "baby sleep", "happy bear kids"],
    },
}

QUEUES = {"en": QUEUE_EN, "ar": QUEUE_AR, "id": QUEUE_ID}

# ── Descriptions ───────────────────────────────────────────────────────────────
def make_desc(lang: str, title: str, theme_key: str) -> str:
    if lang == "en":
        return (
            f"🎉 {title}\n\n"
            f"Join the Wiggle Party — 30 minutes of non-stop dancing fun for babies and toddlers!\n\n"
            f"Eight adorable characters bounce, spin, sway and wiggle to cheerful music. "
            f"No text, no words — pure joyful movement for children of any language.\n\n"
            f"Perfect for: background play while toddlers dance along, motor skill development, "
            f"sensory stimulation with bright colours and lively motion.\n\n"
            f"🎵 Music: Kevin MacLeod (incompetech.com) — Creative Commons CC0\n\n"
            f"💛 Subscribe to Happy Bear Kids for new videos every day!\n\n"
            f"#HappyBearKids #WiggleParty #KidsDance #ToddlerDance #BabyDance "
            f"#ChildrenMusic #DanceParty #KidsEntertainment"
        )
    if lang == "ar":
        return (
            f"🎉 {title}\n\n"
            f"انضم إلى حفلة الرقص! ثلاثون دقيقة من المرح المتواصل للأطفال الصغار!\n\n"
            f"ثمانية شخصيات لطيفة ترقص وتقفز وتدور عبر الشاشة على موسيقى مبهجة. "
            f"لا نصوص، لا كلمات — مجرد متعة خالصة تناسب أطفال أي لغة!\n\n"
            f"مثالي لـ: التشغيل في الخلفية، تطوير المهارات الحركية، التحفيز الحسي.\n\n"
            f"🎵 الموسيقى: Kevin MacLeod — Creative Commons CC0\n\n"
            f"💛 اشترك في قناة هابي بير كيدز للمزيد من الفيديوهات!\n\n"
            f"#هابي_بير_كيدز #حفلة_رقص #اطفال #موسيقى_اطفال #رقص_اطفال"
        )
    # id
    return (
        f"🎉 {title}\n\n"
        f"Bergabunglah dalam Pesta Goyang! 30 menit kesenangan non-stop untuk bayi dan balita!\n\n"
        f"Delapan karakter lucu menari, melompat, berputar dan bergoyang mengikuti musik ceria. "
        f"Tanpa teks, tanpa kata — kesenangan murni untuk anak-anak dari bahasa apapun!\n\n"
        f"Sempurna untuk: diputar sambil balita ikut menari, pengembangan motorik, stimulasi sensorik.\n\n"
        f"🎵 Musik: Kevin MacLeod (incompetech.com) — Creative Commons CC0\n\n"
        f"💛 Subscribe Happy Bear Kids Indonesia untuk video baru setiap hari!\n\n"
        f"#HappyBearKids #PestaGoyang #AnakMenari #MusikAnak #Balita #Hiburan"
    )

# ── Thumbnail ──────────────────────────────────────────────────────────────────
def generate_thumb(prompt: str, out_path: Path) -> bool:
    try:
        resp = requests.post(
            TOGETHER_URL,
            headers={"Authorization": f"Bearer {TOGETHER_KEY}", "Content-Type": "application/json"},
            json={"model": "black-forest-labs/FLUX.1-schnell", "prompt": prompt,
                  "width": 1280, "height": 720, "steps": 4, "n": 1},
            timeout=60,
        )
        resp.raise_for_status()
        out_path.write_bytes(base64.b64decode(resp.json()["data"][0]["b64_json"]))
        return True
    except Exception as e:
        print(f"  Thumb error: {e}")
        return False

# ── Render ─────────────────────────────────────────────────────────────────────
def render_channel(theme_key: str, t: dict, lang: str, ch: dict, out_mp4: Path, dry_run: bool) -> bool:
    props = {
        "sprites":   t["sprites"],
        "blocks":    t["blocks"],
        "bgColor":   ch["bgColor"],
        "musicFile": ch["music"],
        "volume":    0.22,
        "wobble":    True,
        "bgEffect":  t.get("bgEffect", "bubbles"),
        "nightMode": t.get("nightMode", False),
        "accentColor": ch.get("accentColor", "#FFFFFF"),
    }
    if "bgColorEnd" in ch:
        props["bgColorEnd"] = ch["bgColorEnd"]

    cmd = [
        "npx", "remotion", "render",
        "src/index.ts", "DanceSpriteLong30",
        str(out_mp4),
        "--props", json.dumps(props),
        "--concurrency", "2",
    ]
    print(f"  [{lang.upper()}] Rendering → {out_mp4.name}  (music: {ch['music']})")
    if dry_run:
        print(f"  [dry-run] would run: {' '.join(cmd[:5])} ...")
        return True
    result = subprocess.run(cmd, cwd=ROOT / "remotion", capture_output=False)
    return result.returncode == 0

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--themes", nargs="+", default=list(THEMES.keys()))
    parser.add_argument("--langs",  nargs="+", default=["en", "ar", "id"])
    parser.add_argument("--force",      action="store_true")
    parser.add_argument("--dry-run",    action="store_true")
    parser.add_argument("--regen-meta", action="store_true")
    parser.add_argument("--list",       action="store_true")
    args = parser.parse_args()

    if "all" in args.themes:
        args.themes = list(THEMES.keys())

    if args.list:
        print(f"{'Theme':15s}  {'EN music':30s}  {'AR music':30s}  {'ID music'}")
        for key, t in THEMES.items():
            ch = t["channels"]
            print(f"  {key:13s}  {ch['en']['music']:30s}  {ch['ar']['music']:30s}  {ch['id']['music']}")
        return

    date = datetime.now().strftime("%Y%m%d")
    ok = 0

    for theme_key in args.themes:
        if theme_key not in THEMES:
            print(f"Unknown theme: {theme_key}"); continue
        t = THEMES[theme_key]
        print(f"\n{'='*60}\n[{theme_key}] Processing...\n{'='*60}")

        for lang in args.langs:
            ch   = t["channels"][lang]
            q    = QUEUES[lang]
            lang_suffix = f"_{lang}" if lang != "en" else ""
            mp4  = q / f"wiggle_{theme_key}{lang_suffix}_{date}.mp4"

            # ── Render ──────────────────────────────────────────────────────
            if not args.regen_meta:
                if mp4.exists() and not args.force:
                    print(f"  [{lang.upper()}] MP4 exists, skipping render")
                else:
                    if not render_channel(theme_key, t, lang, ch, mp4, args.dry_run):
                        print(f"  [{lang.upper()}] RENDER FAILED — skipping meta/thumb")
                        continue

            # ── Meta ────────────────────────────────────────────────────────
            title    = t["titles"][lang]
            meta_path = q / f"meta_wiggle_{theme_key}{lang_suffix}_{date}.yaml"
            meta = {
                "title":       title,
                "description": make_desc(lang, title, theme_key),
                "tags":        t["tags"],
                "video_type":  "dance",
                "language":    lang,
                "is_short":    False,
                "status":      "public",
            }
            with open(meta_path, "w", encoding="utf-8") as f:
                yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
            print(f"  [{lang.upper()}] Meta → {meta_path.name}")

            # ── Thumbnail ───────────────────────────────────────────────────
            prompt = t["thumb_prompt"]
            if lang == "ar":
                prompt += ", no text, no letters, no words, no numbers"
            thumb = q / f"thumb_wiggle_{theme_key}{lang_suffix}_{date}.png"
            if not thumb.exists() or args.force or args.regen_meta:
                print(f"  [{lang.upper()}] Generating thumbnail...")
                if not args.dry_run:
                    generate_thumb(prompt, thumb)
                    time.sleep(5)

        ok += 1

    print(f"\nDone: {ok}/{len(args.themes)} wiggle themes, {ok * len(args.langs) * 3} files total.")

if __name__ == "__main__":
    main()
