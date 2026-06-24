#!/usr/bin/env python3
"""
generate_dance_item.py — Household item dance videos (25 min each, no text)
18 A-type videos × 3 channels (EN + AR + ID) = 54 videos total.

Groups: kitchen, toys, clothing, school, bathroom, home, music
Types per group: solo (A1) and group (A2), both text-free → universal
Finals: FIN1-FIN3 (25 min, 8 items), FIN4 (30 min, 21 items, big parade)

B-type videos (with learning dialogue) are deferred — require TTS + text overlay.

Usage:
  python3 scripts/generate_dance_item.py --list
  python3 scripts/generate_dance_item.py --generate-sprites [--force]
  python3 scripts/generate_dance_item.py --videos all [--dry-run] [--force]
  python3 scripts/generate_dance_item.py --videos kitchen_solo kitchen_group
  python3 scripts/generate_dance_item.py --group kitchen
  python3 scripts/generate_dance_item.py --regen-meta
"""
import argparse
import base64
import io
import json
import subprocess
import sys
import time
import yaml
from datetime import datetime
from pathlib import Path

ROOT     = Path(__file__).resolve().parent.parent
REMOTION = ROOT / "remotion"
QUEUE_EN = ROOT / "output" / "queue"
QUEUE_AR = ROOT / "output" / "queue_ar"
QUEUE_ID = ROOT / "output" / "queue_id"
SPRITES_DIR = ROOT / "assets" / "sprites_new" / "objects"
TOGETHER_KEY_FILE = ROOT / "credentials" / "together_api_key.txt"
TOGETHER_URL   = "https://api.together.xyz/v1/images/generations"
TOGETHER_MODEL = "black-forest-labs/FLUX.1-schnell"
DATE_STR = datetime.now().strftime("%Y%m%d")

_ALL_TRACKS = [
    "Carefree.mp3", "Crinoline Dreams.mp3", "Gymnopedie No 1.mp3",
    "Happy Happy Game Show.mp3", "Heartwarming.mp3", "Hyperfun.mp3",
    "Life of Riley.mp3", "Merry Go.mp3", "Monkeys Spinning Monkeys.mp3",
    "Overworld.mp3", "Pinball Spring.mp3", "Pixelland.mp3",
    "Quirky Dog.mp3", "Salty Ditty.mp3", "Sneaky Snitch.mp3",
    "Wholesome.mp3", "Fluffing a Duck.mp3", "Walking Along.mp3",
    "George Street Shuffle.mp3", "Circus of Freaks.mp3",
]

def alt_music(en_music: str, ep_idx: int, lang: str) -> str:
    if lang == "en":
        return en_music
    offset = 7 if lang == "ar" else 14
    pool = [t for t in _ALL_TRACKS if t != en_music]
    return pool[(ep_idx + offset) % len(pool)]

# ── Item definitions ──────────────────────────────────────────────────────────

ITEMS = {
    # Kitchen
    "cup":        {"name_en": "Cup",        "name_ar": "كوب",          "name_id": "Cangkir",
                   "sprite": "objects/cup.png",
                   "flux": "cute 3D cartoon ceramic mug cup with steam rising from top happy smiling face",
                   "motion": "SWAY",   "period": 4.0, "amplitude": 38},
    "spoon":      {"name_en": "Spoon",      "name_ar": "ملعقة",        "name_id": "Sendok",
                   "sprite": "objects/spoon.png",
                   "flux": "cute 3D cartoon shiny silver spoon happy face in the bowl area metallic shine",
                   "motion": "SWAY",   "period": 2.8, "amplitude": 55},
    "plate":      {"name_en": "Plate",      "name_ar": "طبق",          "name_id": "Piring",
                   "sprite": "objects/plate.png",
                   "flux": "cute 3D cartoon round white plate dish colorful rim happy smiling face",
                   "motion": "SPIN",   "period": 4.0, "amplitude": 0},
    "kettle":     {"name_en": "Kettle",     "name_ar": "إبريق",        "name_id": "Teko",
                   "sprite": "objects/kettle.png",
                   "flux": "cute 3D cartoon teapot kettle steam cloud on top round belly happy face",
                   "motion": "SWAY",   "period": 5.5, "amplitude": 28},
    # Toys
    "ball":       {"name_en": "Ball",       "name_ar": "كرة",          "name_id": "Bola",
                   "sprite": "objects/ball.png",
                   "flux": "cute 3D cartoon colorful bouncy ball happy smiling face bright stripes",
                   "motion": "BOUNCE", "period": 1.6, "amplitude": 80},
    "cube":       {"name_en": "Cube",       "name_ar": "مكعب",         "name_id": "Kubus",
                   "sprite": "objects/cube.png",
                   "flux": "cute 3D cartoon wooden toy block cube colorful faces on each side happy expression",
                   "motion": "BOB",    "period": 2.2, "amplitude": 45},
    "pyramid":    {"name_en": "Pyramid",    "name_ar": "هرم",          "name_id": "Piramida",
                   "sprite": "objects/pyramid.png",
                   "flux": "cute 3D cartoon stacking rings pyramid toy colorful rings happy face on top",
                   "motion": "SPIN",   "period": 3.5, "amplitude": 0},
    "rattle":     {"name_en": "Rattle",     "name_ar": "خشخيشة",      "name_id": "Mainan Gemerincing",
                   "sprite": "objects/rattle.png",
                   "flux": "cute 3D cartoon baby rattle toy colorful beads handle happy face",
                   "motion": "BOB",    "period": 0.9, "amplitude": 38},
    # Clothing
    "shoe":       {"name_en": "Shoe",       "name_ar": "حذاء",         "name_id": "Sepatu",
                   "sprite": "objects/shoe.png",
                   "flux": "cute 3D cartoon colorful child shoe boot happy face on toe area",
                   "motion": "BOUNCE", "period": 2.2, "amplitude": 55},
    "hat":        {"name_en": "Hat",        "name_ar": "قبعة",         "name_id": "Topi",
                   "sprite": "objects/hat.png",
                   "flux": "cute 3D cartoon colorful winter beanie hat with pompom happy smiling face",
                   "motion": "DRIFT",  "period": 9.0, "amplitude": 180},
    "sock":       {"name_en": "Sock",       "name_ar": "جورب",         "name_id": "Kaos kaki",
                   "sprite": "objects/sock.png",
                   "flux": "cute 3D cartoon colorful striped sock happy face floating",
                   "motion": "BOB",    "period": 1.8, "amplitude": 65},
    "mitten":     {"name_en": "Mitten",     "name_ar": "قفاز",         "name_id": "Sarung tangan",
                   "sprite": "objects/mitten.png",
                   "flux": "cute 3D cartoon fluffy warm winter mitten happy smiling face",
                   "motion": "SWAY",   "period": 3.0, "amplitude": 50},
    # School
    "book":       {"name_en": "Book",       "name_ar": "كتاب",         "name_id": "Buku",
                   "sprite": "objects/book.png",
                   "flux": "cute 3D cartoon hardcover book slightly open showing colorful pages happy face on cover",
                   "motion": "BOB",    "period": 3.2, "amplitude": 40},
    "pencil":     {"name_en": "Pencil",     "name_ar": "قلم رصاص",    "name_id": "Pensil",
                   "sprite": "objects/pencil.png",
                   "flux": "cute 3D cartoon yellow pencil with pink eraser top happy face",
                   "motion": "SWAY",   "period": 2.5, "amplitude": 60},
    "ruler":      {"name_en": "Ruler",      "name_ar": "مسطرة",        "name_id": "Penggaris",
                   "sprite": "objects/ruler.png",
                   "flux": "cute 3D cartoon colorful measuring ruler with markings happy face",
                   "motion": "SWAY",   "period": 3.5, "amplitude": 45},
    "scissors":   {"name_en": "Scissors",   "name_ar": "مقص",          "name_id": "Gunting",
                   "sprite": "objects/scissors.png",
                   "flux": "cute 3D cartoon safety scissors colorful handles open slightly happy face",
                   "motion": "BOUNCE", "period": 1.4, "amplitude": 50},
    # Bathroom
    "toothbrush": {"name_en": "Toothbrush", "name_ar": "فرشاة أسنان", "name_id": "Sikat gigi",
                   "sprite": "objects/toothbrush.png",
                   "flux": "cute 3D cartoon colorful toothbrush with bristles happy smiling face",
                   "motion": "BOB",    "period": 0.7, "amplitude": 30},
    "soap":       {"name_en": "Soap",       "name_ar": "صابون",        "name_id": "Sabun",
                   "sprite": "objects/soap.png",
                   "flux": "cute 3D cartoon soap bar with foam bubbles happy slippery face",
                   "motion": "DRIFT",  "period": 7.0, "amplitude": 220},
    "towel":      {"name_en": "Towel",      "name_ar": "منشفة",        "name_id": "Handuk",
                   "sprite": "objects/towel.png",
                   "flux": "cute 3D cartoon fluffy colorful towel folded happy face",
                   "motion": "SWAY",   "period": 3.8, "amplitude": 42},
    "comb":       {"name_en": "Comb",       "name_ar": "مشط",          "name_id": "Sisir",
                   "sprite": "objects/comb.png",
                   "flux": "cute 3D cartoon colorful hair comb with teeth happy face",
                   "motion": "SWAY",   "period": 2.2, "amplitude": 55},
    # Home
    "key":        {"name_en": "Key",        "name_ar": "مفتاح",        "name_id": "Kunci",
                   "sprite": "objects/key.png",
                   "flux": "cute 3D cartoon golden ornate key bow as head happy face metallic shine",
                   "motion": "SWAY",   "period": 2.0, "amplitude": 65},
    "umbrella":   {"name_en": "Umbrella",   "name_ar": "مظلة",         "name_id": "Payung",
                   "sprite": "objects/umbrella.png",
                   "flux": "cute 3D cartoon colorful striped umbrella fully open happy face in center",
                   "motion": "SPIN",   "period": 5.0, "amplitude": 0},
    "lamp":       {"name_en": "Lamp",       "name_ar": "مصباح",        "name_id": "Lampu",
                   "sprite": "objects/lamp.png",
                   "flux": "cute 3D cartoon glowing table lamp warm light happy face on shade",
                   "motion": "PULSE",  "period": 2.5, "amplitude": 18},
    "phone":      {"name_en": "Phone",      "name_ar": "هاتف",         "name_id": "Telepon",
                   "sprite": "objects/phone.png",
                   "flux": "cute 3D cartoon colorful smartphone happy face on screen",
                   "motion": "BOUNCE", "period": 1.2, "amplitude": 45},
    # Music
    "drum":       {"name_en": "Drum",       "name_ar": "طبل",          "name_id": "Drum",
                   "sprite": "objects/drum.png",
                   "flux": "cute 3D cartoon red drum golden hoops drumsticks as arms happy face",
                   "motion": "BOUNCE", "period": 1.5, "amplitude": 35},
    "bell":       {"name_en": "Bell",       "name_ar": "جرس",          "name_id": "Lonceng",
                   "sprite": "objects/bell.png",
                   "flux": "cute 3D cartoon golden bell with clapper happy ringing face",
                   "motion": "SWAY",   "period": 1.8, "amplitude": 55},
    "flute":      {"name_en": "Flute",      "name_ar": "ناي",          "name_id": "Seruling",
                   "sprite": "objects/flute.png",
                   "flux": "cute 3D cartoon colorful recorder flute instrument happy face",
                   "motion": "SWAY",   "period": 3.0, "amplitude": 50},
    "xylophone":  {"name_en": "Xylophone",  "name_ar": "إكسيلوفون",   "name_id": "Xilofon",
                   "sprite": "objects/xylophone.png",
                   "flux": "cute 3D cartoon rainbow xylophone toy colorful keys small mallets happy face",
                   "motion": "BOB",    "period": 2.0, "amplitude": 35},
}

GROUPS = {
    "kitchen":  ["cup",        "spoon",      "plate",  "kettle"],
    "toys":     ["ball",       "cube",       "pyramid","rattle"],
    "clothing": ["shoe",       "hat",        "sock",   "mitten"],
    "school":   ["book",       "pencil",     "ruler",  "scissors"],
    "bathroom": ["toothbrush", "soap",       "towel",  "comb"],
    "home":     ["key",        "umbrella",   "lamp",   "phone"],
    "music":    ["drum",       "bell",       "flute",  "xylophone"],
}

GROUP_THEMES = {
    "kitchen":  {"bg": "#FFF8E1", "accent": "#BF360C", "music": "Carefree.mp3"},
    "toys":     {"bg": "#E8F5E9", "accent": "#1565C0", "music": "Quirky Dog.mp3"},
    "clothing": {"bg": "#FCE4EC", "accent": "#880E4F", "music": "Wholesome.mp3"},
    "school":   {"bg": "#E3F2FD", "accent": "#0D47A1", "music": "Happy Happy Game Show.mp3"},
    "bathroom": {"bg": "#E0F7FA", "accent": "#006064", "music": "Heartwarming.mp3"},
    "home":     {"bg": "#FFF3E0", "accent": "#E65100", "music": "Crinoline Dreams.mp3"},
    "music":    {"bg": "#F3E5F5", "accent": "#4A148C", "music": "Hyperfun.mp3"},
}

VIDEOS = {
    "kitchen_solo":   {"group": "kitchen",                 "type": "solo",   "comp": "DanceSpriteLong"},
    "kitchen_group":  {"group": "kitchen",                 "type": "group",  "comp": "DanceSpriteLong"},
    "toys_solo":      {"group": "toys",                    "type": "solo",   "comp": "DanceSpriteLong"},
    "toys_group":     {"group": "toys",                    "type": "group",  "comp": "DanceSpriteLong"},
    "clothing_solo":  {"group": "clothing",                "type": "solo",   "comp": "DanceSpriteLong"},
    "clothing_group": {"group": "clothing",                "type": "group",  "comp": "DanceSpriteLong"},
    "school_solo":    {"group": "school",                  "type": "solo",   "comp": "DanceSpriteLong"},
    "school_group":   {"group": "school",                  "type": "group",  "comp": "DanceSpriteLong"},
    "bathroom_solo":  {"group": "bathroom",                "type": "solo",   "comp": "DanceSpriteLong"},
    "bathroom_group": {"group": "bathroom",                "type": "group",  "comp": "DanceSpriteLong"},
    "home_solo":      {"group": "home",                    "type": "solo",   "comp": "DanceSpriteLong"},
    "home_group":     {"group": "home",                    "type": "group",  "comp": "DanceSpriteLong"},
    "music_solo":     {"group": "music",                   "type": "solo",   "comp": "DanceSpriteLong"},
    "music_group":    {"group": "music",                   "type": "group",  "comp": "DanceSpriteLong"},
    "final1":         {"groups": ["kitchen", "toys"],      "type": "final",  "comp": "DanceSpriteLong"},
    "final2":         {"groups": ["clothing", "bathroom"], "type": "final",  "comp": "DanceSpriteLong"},
    "final3":         {"groups": ["school", "music"],      "type": "final",  "comp": "DanceSpriteLong"},
    "final4":         {"groups": list(GROUPS.keys()),      "type": "parade", "comp": "DanceSpriteLong30"},
}

VIDEO_META = {
    "kitchen_solo":   ("Dancing Kitchen! ☕ Cups, Spoons & More | 25 Min Baby | Happy Bear Kids",
                       "kitchen items", "kitchen", "cup spoon plate kettle"),
    "kitchen_group":  ("Kitchen Dance Party! ☕ All Together | 25 Min Baby | Happy Bear Kids",
                       "kitchen items dancing together", "kitchen", "cup spoon plate kettle"),
    "toys_solo":      ("Dancing Toys! 🎾 Balls, Blocks & More | 25 Min Baby | Happy Bear Kids",
                       "toy characters", "toys", "ball cube pyramid rattle"),
    "toys_group":     ("Toy Dance Party! 🎾 All Together | 25 Min Baby | Happy Bear Kids",
                       "toys dancing together", "toys", "ball cube pyramid rattle"),
    "clothing_solo":  ("Dancing Clothes! 👟 Shoes, Hats & More | 25 Min Baby | Happy Bear Kids",
                       "clothing items", "clothing", "shoe hat sock mitten"),
    "clothing_group": ("Clothes Dance Party! 👟 All Together | 25 Min Baby | Happy Bear Kids",
                       "clothing items dancing", "clothing", "shoe hat sock mitten"),
    "school_solo":    ("Dancing School Supplies! 📚 Books & Pencils | 25 Min | Happy Bear Kids",
                       "school supplies", "school", "book pencil ruler scissors"),
    "school_group":   ("School Supply Dance Party! 📚 Together | 25 Min | Happy Bear Kids",
                       "school items dancing", "school", "book pencil ruler scissors"),
    "bathroom_solo":  ("Dancing Bathroom Buddies! 🪥 Toothbrush & More | 25 Min | Happy Bear Kids",
                       "bathroom items", "bathroom", "toothbrush soap towel comb"),
    "bathroom_group": ("Bathroom Dance Party! 🪥 All Together | 25 Min | Happy Bear Kids",
                       "bathroom items dancing", "bathroom", "toothbrush soap towel comb"),
    "home_solo":      ("Dancing Home Objects! 🔑 Keys & Umbrellas | 25 Min | Happy Bear Kids",
                       "home objects", "home", "key umbrella lamp phone"),
    "home_group":     ("Home Objects Dance Party! 🔑 Together | 25 Min | Happy Bear Kids",
                       "home objects dancing", "home", "key umbrella lamp phone"),
    "music_solo":     ("Dancing Instruments! 🥁 Drums, Bells & More | 25 Min | Happy Bear Kids",
                       "musical instruments", "music", "drum bell flute xylophone"),
    "music_group":    ("Instrument Orchestra! 🥁 All Play Together | 25 Min | Happy Bear Kids",
                       "instruments playing together", "music", "drum bell flute xylophone"),
    "final1":         ("Kitchen & Toys Super Dance! ☕🎾 8 Friends | 25 Min | Happy Bear Kids",
                       "kitchen and toy items", "kitchen toys", "cup spoon ball cube"),
    "final2":         ("Clothes & Bathroom Dance! 👟🪥 8 Friends | 25 Min | Happy Bear Kids",
                       "clothing and bathroom items", "clothing bathroom", "shoe hat toothbrush soap"),
    "final3":         ("School & Music Grand Show! 📚🥁 8 Friends | 25 Min | Happy Bear Kids",
                       "school and music items", "school music", "book pencil drum xylophone"),
    "final4":         ("The BIG Item Parade! 🎉 21 Friends | 30 Min Baby Animation | Happy Bear Kids",
                       "all household items", "all items", "cup ball shoe book drum"),
}


# ── Sprite generation ─────────────────────────────────────────────────────────

def generate_sprite(name: str, flux_desc: str, out_path: Path, key: str) -> bool:
    prompt = (
        f"cute 3D cartoon character, {flux_desc}, Pixar style, "
        f"bright vivid colors, smooth shading, white background, "
        f"isolated object, studio lighting, high quality render, "
        f"children illustration, no text, no letters"
    )
    import urllib.request
    try:
        payload = json.dumps({
            "model": TOGETHER_MODEL, "prompt": prompt,
            "width": 1024, "height": 1024, "steps": 4, "n": 1,
        }).encode()
        req = urllib.request.Request(
            TOGETHER_URL, data=payload,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read())
        img_bytes = base64.b64decode(data["data"][0]["b64_json"])
    except Exception as e:
        print(f"    ! FLUX failed: {e}")
        return False

    try:
        from rembg import remove
        from PIL import Image
        clean_bytes = remove(img_bytes)
        img = Image.open(io.BytesIO(clean_bytes))
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        img.save(out_path, "PNG")
        print(f"    ✓ (rembg) → {out_path.name}")
        return True
    except ImportError:
        out_path.write_bytes(img_bytes)
        print(f"    ✓ (no rembg) → {out_path.name}")
        return True
    except Exception as e:
        out_path.write_bytes(img_bytes)
        print(f"    ✓ (rembg err: {e}) → {out_path.name}")
        return True


def generate_missing_sprites(force: bool = False, dry_run: bool = False):
    SPRITES_DIR.mkdir(parents=True, exist_ok=True)
    try:
        key = TOGETHER_KEY_FILE.read_text().strip()
    except Exception:
        print("ERROR: Together.ai key not found at credentials/together_api_key.txt")
        sys.exit(1)

    missing = [(n, d["sprite"], d["flux"]) for n, d in ITEMS.items()
               if not (SPRITES_DIR / Path(d["sprite"]).name).exists() or force]

    if not missing:
        print("All item sprites exist — nothing to generate.")
        return

    print(f"\nGenerating {len(missing)} sprites → {SPRITES_DIR}")
    print("─" * 50)
    for idx, (name, sprite_path, flux_desc) in enumerate(missing, 1):
        fname    = Path(sprite_path).name
        out_path = SPRITES_DIR / fname
        print(f"[{idx}/{len(missing)}] {name}: {flux_desc[:60]}...")
        if dry_run:
            print(f"    [DRY RUN] would generate {fname}")
            continue
        ok = generate_sprite(name, flux_desc, out_path, key)
        if ok and idx < len(missing):
            time.sleep(15)
    print(f"\n✓ Sprite generation complete")


# ── Props builders ─────────────────────────────────────────────────────────────

def _sp(item_name: str, posX: float, posY: float, size: int, seed: int) -> dict:
    return {"path": ITEMS[item_name]["sprite"], "size": size,
            "posX": posX, "posY": posY, "seed": seed}


def make_props_solo(group: str) -> dict:
    """Radial layout: item[0] large center, others smaller around.
    Blocks cycle through each item's characteristic motion type."""
    items  = GROUPS[group]
    theme  = GROUP_THEMES[group]
    sprites = [
        _sp(items[0], 0.50, 0.38, 360, 1),  # center, featured
        _sp(items[1], 0.20, 0.62, 220, 2),  # lower-left
        _sp(items[2], 0.50, 0.76, 220, 3),  # bottom-center
        _sp(items[3], 0.80, 0.62, 220, 4),  # lower-right
    ]

    def m(k):
        return ITEMS[k]["motion"], ITEMS[k]["period"], ITEMS[k]["amplitude"]

    m0, p0, a0 = m(items[0])
    m1, p1, a1 = m(items[1])
    m2, p2, a2 = m(items[2])
    m3, p3, a3 = m(items[3])

    blocks = [
        {"startSec": 0,    "endSec": 90,   "motion": "FADEIN"},
        {"startSec": 90,   "endSec": 390,  "motion": m0, "period": p0, "amplitude": a0},
        {"startSec": 390,  "endSec": 690,  "motion": m1, "period": p1, "amplitude": a1},
        {"startSec": 690,  "endSec": 990,  "motion": m2, "period": p2, "amplitude": a2},
        {"startSec": 990,  "endSec": 1290, "motion": m3, "period": p3, "amplitude": a3},
        {"startSec": 1290, "endSec": 1500, "motion": "WAVE", "period": 2.5,
         "amplitude": 45, "waveDelay": 0.4},
    ]
    return {"bgColor": theme["bg"], "accentColor": theme["accent"],
            "musicFile": theme["music"], "bgEffect": "bubbles",
            "sprites": sprites, "blocks": blocks}


def make_props_group(group: str) -> dict:
    """Equal row of 4 sprites; synchronized group motions."""
    items  = GROUPS[group]
    theme  = GROUP_THEMES[group]
    sprites = [_sp(items[i], xs, 0.45, 295, i + 1)
               for i, xs in enumerate([0.2, 0.4, 0.6, 0.8])]

    blocks = [
        {"startSec": 0,    "endSec": 150,  "motion": "FADEIN"},
        {"startSec": 150,  "endSec": 450,  "motion": "WAVE",   "period": 2.5,
         "amplitude": 50,  "waveDelay": 0.5},
        {"startSec": 450,  "endSec": 750,  "motion": "ORBIT",
         "orbitCenterX": 0.5, "orbitCenterY": 0.45},
        {"startSec": 750,  "endSec": 1050, "motion": "MARCH",  "period": 8,    "bobAmplitude": 22},
        {"startSec": 1050, "endSec": 1350, "motion": "BOUNCE", "period": 2.0,  "amplitude": 55},
        {"startSec": 1350, "endSec": 1500, "motion": "DRIFT",  "period": 10,   "amplitude": 140},
    ]
    return {"bgColor": theme["bg"], "accentColor": theme["accent"],
            "musicFile": theme["music"], "bgEffect": "bubbles",
            "sprites": sprites, "blocks": blocks}


def make_props_final(group_names: list, parade: bool = False) -> dict:
    all_items = []
    for g in group_names:
        all_items.extend(GROUPS[g])
    theme = GROUP_THEMES[group_names[0]]

    if parade:
        # 4 rows × 7 columns = 28 items (all groups × 4 items each)
        rows = [all_items[i:i + 7] for i in range(0, len(all_items), 7)]
        ys = [0.14, 0.38, 0.62, 0.86]
        xs = [0.07, 0.21, 0.35, 0.50, 0.64, 0.78, 0.92]
        sprites = []
        seed = 1
        for ri, row in enumerate(rows):
            for ci, item in enumerate(row):
                sprites.append(_sp(item, xs[ci], ys[ri], 158, seed))
                seed += 1
        blocks = [
            {"startSec": 0,    "endSec": 180,  "motion": "FADEIN"},
            {"startSec": 180,  "endSec": 600,  "motion": "MARCH",  "period": 12,  "bobAmplitude": 20},
            {"startSec": 600,  "endSec": 1000, "motion": "WAVE",   "period": 3,
             "amplitude": 50,  "waveDelay": 0.2},
            {"startSec": 1000, "endSec": 1400, "motion": "BOUNCE", "period": 2.2, "amplitude": 45},
            {"startSec": 1400, "endSec": 1700, "motion": "ORBIT",
             "orbitCenterX": 0.5, "orbitCenterY": 0.5},
            {"startSec": 1700, "endSec": 1800, "motion": "FADEOUT"},
        ]
        return {"bgColor": "#FFF9F0", "accentColor": "#FF6F00",
                "musicFile": "Monkeys Spinning Monkeys.mp3", "bgEffect": "bubbles",
                "sprites": sprites, "blocks": blocks}
    else:
        # 8 items in 2 rows × 4
        top = all_items[:4]
        bot = all_items[4:]
        xs = [0.15, 0.38, 0.62, 0.85]
        sprites = (
            [_sp(top[i], xs[i], 0.28, 230, i + 1)     for i in range(4)] +
            [_sp(bot[i], xs[i], 0.68, 230, i + 5)     for i in range(len(bot))]
        )
        blocks = [
            {"startSec": 0,    "endSec": 150,  "motion": "FADEIN"},
            {"startSec": 150,  "endSec": 500,  "motion": "WAVE",   "period": 2.8,
             "amplitude": 48,  "waveDelay": 0.35},
            {"startSec": 500,  "endSec": 800,  "motion": "ORBIT",
             "orbitCenterX": 0.5, "orbitCenterY": 0.5},
            {"startSec": 800,  "endSec": 1100, "motion": "MARCH",  "period": 10,  "bobAmplitude": 20},
            {"startSec": 1100, "endSec": 1350, "motion": "BOUNCE", "period": 2.0, "amplitude": 45},
            {"startSec": 1350, "endSec": 1500, "motion": "DRIFT",  "period": 9,   "amplitude": 120},
        ]
        return {"bgColor": theme["bg"], "accentColor": theme["accent"],
                "musicFile": "Merry Go.mp3", "bgEffect": "bubbles",
                "sprites": sprites, "blocks": blocks}


def make_props(video_id: str) -> dict:
    v = VIDEOS[video_id]
    if v["type"] == "solo":
        return make_props_solo(v["group"])
    if v["type"] == "group":
        return make_props_group(v["group"])
    if v["type"] == "final":
        return make_props_final(v["groups"])
    return make_props_final(v["groups"], parade=True)


# ── Meta generation ────────────────────────────────────────────────────────────

def make_meta(video_id: str, lang: str) -> dict:
    ch = {"en": "@HappyBearKids1", "ar": "@happybearkidsar", "id": "@happybearkidsin"}
    title_en, desc_hint, theme_hint, item_hint = VIDEO_META[video_id]
    v      = VIDEOS[video_id]
    is_30m = v["comp"] == "DanceSpriteLong30"
    dur_en, dur_ar, dur_id = (
        ("30 minutes", "30 دقيقة", "30 menit") if is_30m
        else ("25 minutes", "25 دقيقة", "25 menit")
    )

    series_en = "Dancing Household Items"
    series_ar = "الأشياء المنزلية الراقصة"
    series_id = "Benda Rumah Menari"

    if lang == "en":
        title = title_en
        description = (
            f"✨ Watch cute animated {desc_hint} come to life and dance for {dur_en}!\n\n"
            f"No words, no text — just adorable animated objects moving to cheerful music. "
            f"Perfect for babies and toddlers of any language!\n\n"
            f"🎯 Great for:\n"
            f"• Background video during play time\n"
            f"• Visual stimulation for babies 0–3\n"
            f"• Calming screen time\n"
            f"• Toddler nap time wind-down\n\n"
            f"🏠 Part of the {series_en} series — fun everyday objects dancing!\n"
            f"✅ Features: {item_hint} — and more!\n\n"
            f"🔔 Subscribe → {ch['en']} for more baby animations every day!\n\n"
            f"🎵 Music: Kevin MacLeod (incompetech.com)\n"
            f"Licensed under Creative Commons Attribution 4.0 (CC BY 4.0)\n\n"
            f"#DancingObjects #HappyBearKids #BabyAnimation #ToddlerTV "
            f"#HouseholdItems #NoTalking #VisualBaby #BabyBackground "
            f"#{theme_hint.replace(' ', '').title()}Dance #CuteAnimation "
            f"#KevinMacLeod #BabyTV #KidsAnimation #ChildrenTV"
        )
    elif lang == "ar":
        title = (title_en
                 .replace("Dancing", "رقصة")
                 .replace("Dance Party!", "حفلة رقص!")
                 .replace("Super Dance!", "رقصة!")
                 .replace("Grand Show!", "عرض!")
                 .replace("BIG Item Parade!", "موكب الأشياء الكبير!")
                 .replace("Baby", "للرضع")
                 .replace("Happy Bear Kids", "هابي بير كيدز"))
        description = (
            f"✨ شاهد {desc_hint} رسوم متحركة لطيفة ترقص لمدة {dur_ar}!\n\n"
            f"بدون كلمات أو نصوص — فقط أشياء رسوم متحركة جميلة تتحرك على موسيقى مرحة. "
            f"مثالي للرضع والأطفال الصغار من أي لغة!\n\n"
            f"🎯 رائع لـ:\n"
            f"• فيديو خلفية أثناء وقت اللعب\n"
            f"• تحفيز بصري للأطفال من 0–3 سنوات\n"
            f"• وقت شاشة هادئ ومريح\n"
            f"• الاسترخاء قبل قيلولة الطفل\n\n"
            f"🏠 جزء من سلسلة {series_ar} — أشياء يومية ممتعة ترقص!\n\n"
            f"🔔 اشتركوا → {ch['ar']} للمزيد من رسوم الأطفال كل يوم!\n\n"
            f"🎵 الموسيقى: Kevin MacLeod (incompetech.com)\n"
            f"رخصة المشاع الإبداعي Attribution 4.0\n\n"
            f"#رسوم_أطفال #هابي_بير_كيدز #أشياء_راقصة #بدون_كلام "
            f"#فيديو_للرضع #تحفيز_بصري #موسيقى_أطفال #رسوم_متحركة"
        )
    else:  # id
        title = (title_en
                 .replace("Dancing", "Tarian")
                 .replace("Dance Party!", "Pesta Tari!")
                 .replace("Super Dance!", "Tari Bersama!")
                 .replace("Grand Show!", "Pertunjukan!")
                 .replace("BIG Item Parade!", "Parade Benda Besar!")
                 .replace("Baby", "Bayi")
                 .replace("Happy Bear Kids", "Happy Bear Kids"))
        description = (
            f"✨ Saksikan {desc_hint} animasi lucu menari selama {dur_id}!\n\n"
            f"Tanpa kata-kata, tanpa teks — hanya benda animasi menggemaskan bergerak mengikuti "
            f"musik ceria. Cocok untuk bayi dan balita dari bahasa manapun!\n\n"
            f"🎯 Sempurna untuk:\n"
            f"• Video latar saat waktu bermain\n"
            f"• Stimulasi visual untuk bayi 0–3 tahun\n"
            f"• Waktu layar yang menenangkan\n"
            f"• Bersiap tidur siang\n\n"
            f"🏠 Bagian dari seri {series_id} — benda sehari-hari yang menari!\n\n"
            f"🔔 Subscribe → {ch['id']} untuk animasi bayi setiap hari!\n\n"
            f"🎵 Musik: Kevin MacLeod (incompetech.com)\n"
            f"Lisensi Creative Commons Attribution 4.0\n\n"
            f"#AnimasiAnak #HappyBearKids #BendaMenari #TanpaSuara "
            f"#VideoUntukBayi #StimulasiBayi #AnimasiLucu #TelevisiBayi"
        )

    vtype = "dance_item_final" if "final" in video_id else f"dance_item_{v.get('group', 'final')}"
    return {
        "title":       title,
        "description": description,
        "tags": ["dance", "item dance", "household items", "baby animation",
                 "happy bear kids", dur_en, "cute animation", "no talking",
                 "visual baby", "baby background", "toddler tv",
                 theme_hint, item_hint],
        "video_type": vtype,
        "language":   lang,
        "is_short":   False,
        "status":     "public",
    }


# ── Thumbnail generation ───────────────────────────────────────────────────────

def generate_thumbnail(video_id: str, out_path: Path, lang: str = "en") -> bool:
    if out_path.exists():
        return True
    try:
        key = TOGETHER_KEY_FILE.read_text().strip()
    except Exception:
        return False

    _, desc_hint, theme_hint, _ = VIDEO_META[video_id]
    no_text = "" if lang == "en" else ", no text, no letters, no words, no numbers"
    prompt = (
        f"cute 3D cartoon {desc_hint} dancing together, Pixar style, "
        f"bright cheerful colors, children's YouTube thumbnail, "
        f"colorful background, fun and energetic{no_text}"
    )
    import urllib.request
    try:
        payload = json.dumps({
            "model": TOGETHER_MODEL, "prompt": prompt,
            "width": 1280, "height": 720, "steps": 4, "n": 1,
        }).encode()
        req = urllib.request.Request(
            TOGETHER_URL, data=payload,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read())
        out_path.write_bytes(base64.b64decode(data["data"][0]["b64_json"]))
        print(f"    ✓ thumb → {out_path.name}")
        return True
    except Exception as e:
        print(f"    ! thumb failed: {e}")
        return False


# ── Render ─────────────────────────────────────────────────────────────────────

def render_video(video_id: str, force: bool, dry_run: bool) -> Path | None:
    slug     = f"item_{video_id}_{DATE_STR}.mp4"
    out_path = QUEUE_EN / slug

    if out_path.exists() and not force:
        sz = out_path.stat().st_size / 1024 / 1024
        print(f"  skip {slug} ({sz:.0f}MB)")
        return out_path

    props = make_props(video_id)
    comp  = VIDEOS[video_id]["comp"]

    print(f"\n  Rendering {video_id} → {slug}")
    if dry_run:
        print(f"    [DRY RUN] {comp}  sprites={len(props['sprites'])}")
        return out_path

    QUEUE_EN.mkdir(parents=True, exist_ok=True)
    cmd = [
        "npx", "remotion", "render",
        "src/index.ts", comp,
        str(out_path),
        "--props", json.dumps(props),
        "--concurrency", "1",
        "--log", "error",
    ]
    start  = time.time()
    result = subprocess.run(cmd, cwd=str(REMOTION),
                            capture_output=True, text=True, timeout=21600)
    if result.returncode == 0 and out_path.exists():
        elapsed = (time.time() - start) / 60
        sz      = out_path.stat().st_size / 1024 / 1024
        print(f"    ✓ {sz:.0f}MB in {elapsed:.0f}min")
        return out_path
    else:
        print(f"    ✗ FAILED: {result.stderr[-400:]}")
        return None


# ── Publish ────────────────────────────────────────────────────────────────────

def publish_to_all_channels(en_mp4: Path, video_id: str, ep_idx: int, dry_run: bool):
    props_en  = make_props(video_id)
    en_music  = props_en["musicFile"]
    comp      = VIDEOS[video_id]["comp"]
    stem      = en_mp4.stem

    for lang, queue in [("en", QUEUE_EN), ("ar", QUEUE_AR), ("id", QUEUE_ID)]:
        queue.mkdir(parents=True, exist_ok=True)
        target_stem = stem if lang == "en" else f"{stem}_{lang}"
        target      = queue / f"{target_stem}.mp4"

        if lang != "en" and not target.exists() and not dry_run:
            lang_music        = alt_music(en_music, ep_idx, lang)
            props_lang        = dict(props_en)
            props_lang["musicFile"] = lang_music
            print(f"\n    Rendering {video_id} ({lang.upper()}) → {target.name}")
            cmd = [
                "npx", "remotion", "render",
                "src/index.ts", comp,
                str(target),
                "--props", json.dumps(props_lang),
                "--concurrency", "1",
                "--log", "error",
            ]
            r = subprocess.run(cmd, cwd=str(REMOTION),
                               capture_output=True, text=True, timeout=21600)
            if r.returncode != 0 or not target.exists():
                print(f"    ✗ FAILED ({lang}): {r.stderr[-300:]}")
                continue
            print(f"    ✓ {target.stat().st_size/1024/1024:.0f}MB")

        meta_path  = queue / f"meta_{target_stem}.yaml"
        thumb_path = queue / f"thumb_{target_stem}.png"

        if not meta_path.exists():
            meta = make_meta(video_id, lang)
            if not dry_run:
                with open(meta_path, "w") as f:
                    yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
                print(f"    meta {lang.upper()} → {meta_path.name}")
            else:
                print(f"    [DRY RUN] meta {lang.upper()}")

        if not thumb_path.exists() and not dry_run:
            time.sleep(0.5)
            generate_thumbnail(video_id, thumb_path, lang)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate DanceSpriteLong household item videos")
    parser.add_argument("--list",             action="store_true",
                        help="List all video IDs")
    parser.add_argument("--generate-sprites", action="store_true",
                        help="Generate missing item sprites via Together.ai FLUX")
    parser.add_argument("--videos",           nargs="*",
                        help="Video IDs to generate. Use 'all' for all.")
    parser.add_argument("--group",            default=None, choices=list(GROUPS),
                        help="Generate all videos for one group (both solo and group types)")
    parser.add_argument("--dry-run",          action="store_true")
    parser.add_argument("--force",            action="store_true")
    parser.add_argument("--regen-meta",       action="store_true")
    args = parser.parse_args()

    if args.list:
        print("Dance Item Videos:")
        for vid, cfg in VIDEOS.items():
            dur = "30min" if cfg["comp"] == "DanceSpriteLong30" else "25min"
            n   = len(GROUPS.get(cfg.get("group", ""), []))
            print(f"  {vid:20s}  {cfg['type']:7s}  {dur}  {cfg['comp']}")
        return

    if args.generate_sprites:
        generate_missing_sprites(force=args.force, dry_run=args.dry_run)
        return

    if args.group:
        video_ids = [vid for vid, cfg in VIDEOS.items()
                     if cfg.get("group") == args.group
                     or args.group in cfg.get("groups", [])]
    elif args.videos:
        video_ids = list(VIDEOS) if args.videos == ["all"] else args.videos
    else:
        video_ids = list(VIDEOS)

    invalid = [v for v in video_ids if v not in VIDEOS]
    if invalid:
        print(f"Unknown IDs: {', '.join(invalid)}")
        print(f"Available: {', '.join(VIDEOS)}")
        sys.exit(1)

    all_video_ids = list(VIDEOS.keys())
    print(f"=== Dance Item — {len(video_ids)} videos ===\n")

    for video_id in video_ids:
        v      = VIDEOS[video_id]
        ep_idx = all_video_ids.index(video_id)
        print(f"[{video_id.upper()}] {v['type']} → {v['comp']}")

        slug = f"item_{video_id}_{DATE_STR}.mp4"
        mp4  = QUEUE_EN / slug

        if args.regen_meta:
            if mp4.exists():
                publish_to_all_channels(mp4, video_id, ep_idx, args.dry_run)
            else:
                print(f"  ! No MP4 at {mp4}")
            continue

        mp4 = render_video(video_id, args.force, args.dry_run)
        if mp4 and (mp4.exists() or args.dry_run):
            publish_to_all_channels(mp4, video_id, ep_idx, args.dry_run)

    print("\n=== Done ===")


if __name__ == "__main__":
    main()
