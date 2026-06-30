#!/usr/bin/env python3
"""
Generate DanceSpriteLong pet videos — 33-video "Dancing Home Pets" series.
Sprite-based animation, no text → universal (EN + AR + ID).

10 pets × 3 video types:
  A = solo dance, no words → EN+AR+ID (same render, separate meta)
  B = 2 animals together, no words → EN+AR+ID (has_B animals only)
  C = educational with labels → EN-only (deferred — requires text overlay)

Usage:
  python3 scripts/generate_dance_pet.py                 # all A+B types
  python3 scripts/generate_dance_pet.py --animal cat    # one animal (A+B)
  python3 scripts/generate_dance_pet.py --type A        # all A-type
  python3 scripts/generate_dance_pet.py --dry-run
  python3 scripts/generate_dance_pet.py --regen-meta
"""
import argparse
import base64
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

# Sprite paths (relative to remotion/public/sprites/)
# animals_flux/ has rembg-processed transparent sprites
ANIMALS = {
    "cat":        {
        "name_en": "Cat",        "name_ar": "قطة",         "name_id": "Kucing",
        "sprite": "animals/cat_3d.png",
        "bg": "#E8EAF6", "accent": "#5C6BC0",
        "music": "Carefree.mp3",
        "partner": "dog",   "partner_sprite": "animals_flux/dog.png",
        "mood": "graceful and calm",
    },
    "dog":        {
        "name_en": "Dog",        "name_ar": "كلب",          "name_id": "Anjing",
        "sprite": "animals_flux/dog.png",
        "bg": "#FFF3E0", "accent": "#E67E22",
        "music": "Hyperfun.mp3",
        "partner": "cat",   "partner_sprite": "animals/cat_3d.png",
        "mood": "playful and energetic",
    },
    "rabbit":     {
        "name_en": "Rabbit",     "name_ar": "أرنب",         "name_id": "Kelinci",
        "sprite": "animals_flux/rabbit.png",
        "bg": "#F1F8E9", "accent": "#7CB342",
        "music": "Wholesome.mp3",
        "partner": "duck",  "partner_sprite": "animals_flux/duck.png",
        "mood": "bouncy and curious",
    },
    "fish":       {
        "name_en": "Fish",       "name_ar": "سمكة",         "name_id": "Ikan",
        "sprite": "animals_flux/frog.png",   # closest available
        "bg": "#E3F2FD", "accent": "#1E88E5",
        "music": "Gymnopedie No 1.mp3",
        "partner": None,
        "mood": "smooth and dreamy",
    },
    "turtle":     {
        "name_en": "Turtle",     "name_ar": "سلحفاة",       "name_id": "Kura-kura",
        "sprite": "animals_flux/frog.png",   # closest available
        "bg": "#E8F5E9", "accent": "#43A047",
        "music": "Crinoline Dreams.mp3",
        "partner": None,
        "mood": "very slow and wise",
    },
    "parrot":     {
        "name_en": "Parrot",     "name_ar": "ببغاء",        "name_id": "Beo",
        "sprite": "animals_flux/parrot.png",
        "bg": "#E8F5E9", "accent": "#E53935",
        "music": "Quirky Dog.mp3",
        "partner": "rabbit", "partner_sprite": "animals_flux/rabbit.png",
        "mood": "bright and energetic",
    },
    "hamster":    {
        "name_en": "Hamster",    "name_ar": "هامستر",       "name_id": "Hamster",
        "sprite": "animals_flux/pig.png",    # EN only — pig sprite, closest available
        "sprite_ar": "animals_flux/rabbit.png",  # AR/ID: use rabbit (no pig on Muslim channels)
        "bg": "#FFF8E1", "accent": "#F9A825",
        "music": "Monkeys Spinning Monkeys.mp3",
        "partner": None,
        "mood": "tiny and very fast",
    },
    "guinea_pig": {
        "name_en": "Guinea Pig", "name_ar": "أرنب صغير",   "name_id": "Kelinci Kecil",
        "sprite": "animals_flux/pig.png",    # EN only
        "sprite_ar": "animals_flux/rabbit.png",  # AR/ID: rabbit substitute
        "bg": "#FFF3E0", "accent": "#FF8F00",
        "music": "Life of Riley.mp3",
        "partner": None,
        "mood": "cute and waddling",
    },
    "duck":       {
        "name_en": "Duck",       "name_ar": "بطة",          "name_id": "Bebek",
        "sprite": "animals_flux/duck.png",
        "bg": "#E1F5FE", "accent": "#F39C12",
        "music": "Happy Happy Game Show.mp3",
        "partner": "rabbit", "partner_sprite": "animals_flux/rabbit.png",
        "mood": "cheerful and waddling",
    },
    "kitten":     {
        "name_en": "Kitten",     "name_ar": "قطة صغيرة",   "name_id": "Anak Kucing",
        "sprite": "animals/cat.png",
        "bg": "#FCE4EC", "accent": "#E91E63",
        "music": "Merry Go.mp3",
        "partner": None,
        "mood": "clumsy and playful",
    },
}


def make_props_A(animal: str) -> dict:
    """DanceSpriteLong props for single-animal A-type video."""
    a = ANIMALS[animal]
    sprite = a["sprite"]
    bg     = a["bg"]
    acc    = a["accent"]
    music  = a["music"]

    # Per-animal block configs reflecting their character
    block_configs = {
        "cat": [
            {"startSec": 0,    "endSec": 300,  "motion": "BOB",   "period": 3.8, "amplitude": 35},
            {"startSec": 300,  "endSec": 600,  "motion": "SWAY",  "period": 4.5, "amplitude": 60},
            {"startSec": 600,  "endSec": 900,  "motion": "DRIFT", "period": 10,  "amplitude": 200},
            {"startSec": 900,  "endSec": 1200, "motion": "PULSE", "period": 5,   "amplitude": 10},
            {"startSec": 1200, "endSec": 1500, "motion": "DRIFT", "period": 12,  "amplitude": 180},
        ],
        "dog": [
            {"startSec": 0,    "endSec": 300,  "motion": "BOUNCE","period": 1.8, "amplitude": 75},
            {"startSec": 300,  "endSec": 600,  "motion": "MARCH", "period": 5,   "bobAmplitude": 25},
            {"startSec": 600,  "endSec": 900,  "motion": "BOB",   "period": 2.0, "amplitude": 55},
            {"startSec": 900,  "endSec": 1200, "motion": "DRIFT", "period": 7,   "amplitude": 220},
            {"startSec": 1200, "endSec": 1500, "motion": "BOUNCE","period": 1.8, "amplitude": 70},
        ],
        "rabbit": [
            {"startSec": 0,    "endSec": 300,  "motion": "BOUNCE","period": 1.5, "amplitude": 80},
            {"startSec": 300,  "endSec": 600,  "motion": "BOB",   "period": 1.5, "amplitude": 60},
            {"startSec": 600,  "endSec": 900,  "motion": "SWAY",  "period": 2.5, "amplitude": 50},
            {"startSec": 900,  "endSec": 1200, "motion": "DRIFT", "period": 8,   "amplitude": 200},
            {"startSec": 1200, "endSec": 1500, "motion": "BOUNCE","period": 1.5, "amplitude": 80},
        ],
        "fish": [
            {"startSec": 0,    "endSec": 300,  "motion": "SWAY",  "period": 4,   "amplitude": 70},
            {"startSec": 300,  "endSec": 600,  "motion": "DRIFT", "period": 12,  "amplitude": 240},
            {"startSec": 600,  "endSec": 900,  "motion": "SWAY",  "period": 5,   "amplitude": 80},
            {"startSec": 900,  "endSec": 1200, "motion": "DRIFT", "period": 14,  "amplitude": 260},
            {"startSec": 1200, "endSec": 1500, "motion": "PULSE", "period": 4,   "amplitude": 8},
        ],
        "turtle": [
            {"startSec": 0,    "endSec": 300,  "motion": "PULSE", "period": 7,   "amplitude": 8},
            {"startSec": 300,  "endSec": 600,  "motion": "DRIFT", "period": 18,  "amplitude": 100},
            {"startSec": 600,  "endSec": 900,  "motion": "SWAY",  "period": 8,   "amplitude": 35},
            {"startSec": 900,  "endSec": 1200, "motion": "DRIFT", "period": 20,  "amplitude": 80},
            {"startSec": 1200, "endSec": 1500, "motion": "PULSE", "period": 9,   "amplitude": 7},
        ],
        "parrot": [
            {"startSec": 0,    "endSec": 300,  "motion": "BOB",   "period": 1.5, "amplitude": 55},
            {"startSec": 300,  "endSec": 600,  "motion": "SPIN",  "period": 4},
            {"startSec": 600,  "endSec": 900,  "motion": "BOUNCE","period": 1.5, "amplitude": 65},
            {"startSec": 900,  "endSec": 1200, "motion": "DRIFT", "period": 6,   "amplitude": 200},
            {"startSec": 1200, "endSec": 1500, "motion": "BOB",   "period": 1.5, "amplitude": 55},
        ],
        "hamster": [
            {"startSec": 0,    "endSec": 300,  "motion": "BOUNCE","period": 1.0, "amplitude": 55},
            {"startSec": 300,  "endSec": 600,  "motion": "MARCH", "period": 3.5, "bobAmplitude": 30},
            {"startSec": 600,  "endSec": 900,  "motion": "BOB",   "period": 1.2, "amplitude": 50},
            {"startSec": 900,  "endSec": 1200, "motion": "DRIFT", "period": 5,   "amplitude": 180},
            {"startSec": 1200, "endSec": 1500, "motion": "BOUNCE","period": 1.0, "amplitude": 55},
        ],
        "guinea_pig": [
            {"startSec": 0,    "endSec": 300,  "motion": "SWAY",  "period": 2.5, "amplitude": 45},
            {"startSec": 300,  "endSec": 600,  "motion": "BOB",   "period": 2.0, "amplitude": 40},
            {"startSec": 600,  "endSec": 900,  "motion": "DRIFT", "period": 9,   "amplitude": 180},
            {"startSec": 900,  "endSec": 1200, "motion": "SWAY",  "period": 3,   "amplitude": 50},
            {"startSec": 1200, "endSec": 1500, "motion": "PULSE", "period": 3.5, "amplitude": 10},
        ],
        "duck": [
            {"startSec": 0,    "endSec": 300,  "motion": "BOB",   "period": 2.0, "amplitude": 45},
            {"startSec": 300,  "endSec": 600,  "motion": "SWAY",  "period": 2.5, "amplitude": 55},
            {"startSec": 600,  "endSec": 900,  "motion": "MARCH", "period": 7,   "bobAmplitude": 20},
            {"startSec": 900,  "endSec": 1200, "motion": "DRIFT", "period": 8,   "amplitude": 200},
            {"startSec": 1200, "endSec": 1500, "motion": "BOB",   "period": 2.0, "amplitude": 45},
        ],
        "kitten": [
            {"startSec": 0,    "endSec": 300,  "motion": "BOUNCE","period": 1.8, "amplitude": 70},
            {"startSec": 300,  "endSec": 600,  "motion": "SWAY",  "period": 2.0, "amplitude": 55},
            {"startSec": 600,  "endSec": 900,  "motion": "DRIFT", "period": 7,   "amplitude": 210},
            {"startSec": 900,  "endSec": 1200, "motion": "BOUNCE","period": 2.0, "amplitude": 65},
            {"startSec": 1200, "endSec": 1500, "motion": "SWAY",  "period": 2.0, "amplitude": 55},
        ],
    }

    return {
        "bgColor":    bg,
        "accentColor": acc,
        "musicFile":  music,
        "bgEffect":   "bubbles",
        "sprites": [
            {"path": sprite, "size": 460, "posX": 0.5, "posY": 0.42, "seed": 1},
        ],
        "blocks": block_configs.get(animal, block_configs["cat"]),
    }


def make_props_B(animal: str) -> dict:
    """DanceSpriteLong props for two-animal B-type video."""
    a = ANIMALS[animal]
    if not a.get("partner"):
        return make_props_A(animal)

    partner = a["partner"]
    pa = ANIMALS[partner]

    return {
        "bgColor":     a["bg"],
        "accentColor": a["accent"],
        "musicFile":   a["music"],
        "bgEffect":    "bubbles",
        "sprites": [
            {"path": a["sprite"],           "size": 380, "posX": 0.3, "posY": 0.42,
             "seed": 1, "orbitRadius": 0},
            {"path": a["partner_sprite"],   "size": 380, "posX": 0.7, "posY": 0.42,
             "seed": 2, "orbitRadius": 0},
        ],
        "blocks": [
            {"startSec": 0,    "endSec": 300,  "motion": "BOB",   "period": 2.5, "amplitude": 45},
            {"startSec": 300,  "endSec": 600,  "motion": "WAVE",  "period": 2.5, "amplitude": 45,
             "waveDelay": 0.5},
            {"startSec": 600,  "endSec": 900,  "motion": "ORBIT",
             "orbitCenterX": 0.5, "orbitCenterY": 0.42},
            {"startSec": 900,  "endSec": 1200, "motion": "DRIFT", "period": 8,  "amplitude": 160},
            {"startSec": 1200, "endSec": 1500, "motion": "WAVE",  "period": 2.5, "amplitude": 45,
             "waveDelay": -0.5},
        ],
    }


def make_meta(animal: str, vtype: str, lang: str) -> dict:
    a  = ANIMALS[animal]
    ch = {"en": "@HappyBearKids1", "ar": "@happybearkidsar", "id": "@happybearkidsin"}
    names = {"en": a["name_en"], "ar": a["name_ar"], "id": a["name_id"]}
    name  = names[lang]

    if vtype == "A":
        titles = {
            "en": f"Dancing {a['name_en']}! 🐾 25 Min Baby Animation | Happy Bear Kids",
            "ar": f"رقصة {a['name_ar']}! 🐾 25 دقيقة رسوم للرضع | هابي بير كيدز",
            "id": f"{a['name_id']} Menari! 🐾 25 Menit Animasi Bayi | Happy Bear Kids",
        }
        descs = {
            "en": (
                f"🐾 Watch adorable animated {a['name_en']} dance for 25 minutes!\n\n"
                f"Pure visual delight — no words, no text — just a cute {a['name_en'].lower()} "
                f"moving to gentle music. {a['mood'].capitalize()}!\n\n"
                f"✨ Perfect for:\n• Background video during play time\n"
                f"• Calming screen time for babies 0-3\n• Nap time wind-down\n\n"
                f"Part of the Dancing Home Pets series — 10 cute animals!\n"
                f"🔔 Subscribe → {ch['en']}\n\n"
                f"🎵 Music: Kevin MacLeod (incompetech.com) "
                f"Licensed under Creative Commons Attribution 4.0\n\n"
                f"#Dancing{a['name_en']} #HappyBearKids #BabyAnimation #CutePet "
                f"#PetDance #BabyTV #NoTalking #VisualBaby"
            ),
            "ar": (
                f"🐾 شاهد {a['name_ar']} الرسوم المتحركة الرائع يرقص لمدة 25 دقيقة!\n\n"
                f"بهجة بصرية خالصة — بدون كلمات أو نصوص — فقط {a['name_ar']} لطيف "
                f"يتحرك على موسيقى هادئة. مثالي للرضع من أي لغة!\n\n"
                f"✨ مثالي لـ:\n• فيديو خلفية أثناء وقت اللعب\n"
                f"• وقت شاشة هادئ للرضع 0-3\n• الاسترخاء قبل القيلولة\n\n"
                f"جزء من سلسلة حيوانات المنزل الراقصة — 10 حيوانات لطيفة!\n"
                f"🔔 اشتركوا → {ch['ar']}\n\n"
                f"🎵 الموسيقى: Kevin MacLeod — رخصة Creative Commons Attribution 4.0\n\n"
                f"#رقصة_{name.replace(' ', '_')} #هابي_بير_كيدز #رسوم_أطفال "
                f"#حيوانات_أليفة #بدون_كلام #فيديو_للرضع"
            ),
            "id": (
                f"🐾 Saksikan {a['name_id']} animasi yang menggemaskan menari selama 25 menit!\n\n"
                f"Hiburan visual murni — tanpa kata-kata — hanya {a['name_id'].lower()} lucu "
                f"bergerak mengikuti musik lembut. Cocok untuk bayi dari bahasa manapun!\n\n"
                f"✨ Sempurna untuk:\n• Video latar saat waktu bermain\n"
                f"• Waktu layar yang menenangkan untuk bayi 0-3\n• Bersiap tidur siang\n\n"
                f"Bagian dari seri Hewan Peliharaan Menari — 10 hewan lucu!\n"
                f"🔔 Subscribe → {ch['id']}\n\n"
                f"🎵 Musik: Kevin MacLeod — Creative Commons Attribution 4.0\n\n"
                f"#Tari{a['name_id'].replace(' ', '')} #HappyBearKids #AnimasiAnak "
                f"#HewanPeliharaan #TanpaSuara #VideoUntukBayi"
            ),
        }
    else:  # B type
        partner    = a.get("partner", "friend")
        pa         = ANIMALS.get(partner, {})
        partner_en = pa.get("name_en", "Friend")
        partner_ar = pa.get("name_ar", "صديق")
        partner_id = pa.get("name_id", "Teman")
        titles = {
            "en": f"{a['name_en']} & {partner_en}! 🐾 Pet Friends | 25 Min | Happy Bear Kids",
            "ar": f"{a['name_ar']} و{partner_ar}! 🐾 أصدقاء أليفون | هابي بير كيدز",
            "id": f"{a['name_id']} & {partner_id}! 🐾 Sahabat Hewan | Happy Bear Kids",
        }
        descs = {
            "en": (
                f"🐾 Watch {a['name_en']} meet and play with {partner_en}! 25 minutes of friendship!\n\n"
                f"Two adorable animated pets — no words needed, emotions tell the story.\n"
                f"Pure visual fun for babies of any language!\n\n"
                f"🔔 Subscribe → {ch['en']}\n\n"
                f"🎵 Music: Kevin MacLeod — Creative Commons Attribution 4.0\n\n"
                f"#PetFriends #HappyBearKids #BabyAnimation #CutePets "
                f"#Dancing{a['name_en']} #Dancing{partner_en} #NoTalking"
            ),
            "ar": (
                f"🐾 شاهد {a['name_ar']} و{partner_ar} يلعبان معاً! 25 دقيقة من الصداقة!\n\n"
                f"حيوانان أليفان رسوم متحركة لطيفان — بدون كلمات.\n\n"
                f"🔔 اشتركوا → {ch['ar']}\n\n"
                f"🎵 Kevin MacLeod — Creative Commons Attribution 4.0\n\n"
                f"#أصدقاء_أليفون #هابي_بير_كيدز #رسوم_أطفال #بدون_كلام"
            ),
            "id": (
                f"🐾 Saksikan {a['name_id']} dan {partner_id} bermain bersama! 25 menit persahabatan!\n\n"
                f"Dua hewan peliharaan animasi — tanpa kata-kata.\n\n"
                f"🔔 Subscribe → {ch['id']}\n\n"
                f"🎵 Kevin MacLeod — Creative Commons Attribution 4.0\n\n"
                f"#HewanBersahabat #HappyBearKids #AnimasiAnak #TanpaSuara"
            ),
        }

    return {
        "title":       titles[lang],
        "description": descs[lang],
        "tags": [
            animal, a["name_en"].lower(), "pet dance", "baby animation",
            "happy bear kids", "25 minutes", "cute pet", "no talking",
            "visual baby", "baby background video", "toddler tv",
        ],
        "video_type": f"dance_pet_{vtype.lower()}",
        "language":   lang,
        "is_short":   False,
        "status":     "public",
    }


def generate_thumbnail(animal: str, vtype: str, out_path: Path) -> bool:
    if out_path.exists():
        return True
    try:
        key = TOGETHER_KEY_FILE.read_text().strip()
    except Exception:
        return False

    a = ANIMALS[animal]
    suffix = "" if vtype == "A" else f" and {ANIMALS.get(a.get('partner',''), {}).get('name_en', 'friend').lower()}"
    prompt = (
        f"cute animated {a['name_en'].lower()}{suffix}, Pixar 3D style, "
        f"dancing and jumping, cheerful background, children's YouTube thumbnail, "
        f"bright colors, no text, no letters, no words, 1280x720"
    )
    try:
        import urllib.request
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


def render_video(animal: str, vtype: str, force: bool, dry_run: bool) -> Path | None:
    slug     = f"pet_{animal}_{vtype.lower()}_{DATE_STR}.mp4"
    out_path = QUEUE_EN / slug

    if out_path.exists() and not force:
        sz = out_path.stat().st_size / 1024 / 1024
        print(f"  skip {slug} ({sz:.0f}MB)")
        return out_path

    props = make_props_A(animal) if vtype == "A" else make_props_B(animal)

    print(f"\n  Rendering {animal} [{vtype}] → {slug}")
    if dry_run:
        print(f"    [DRY RUN] DanceSpriteLong")
        return out_path

    QUEUE_EN.mkdir(parents=True, exist_ok=True)
    cmd = [
        "npx", "remotion", "render",
        "src/index.ts", "DanceSpriteLong",
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
        sz = out_path.stat().st_size / 1024 / 1024
        print(f"    ✓ {sz:.0f}MB in {elapsed:.0f}min")
        return out_path
    else:
        print(f"    ✗ FAILED: {result.stderr[-400:]}")
        return None


def publish_to_all_channels(en_mp4: Path, animal: str, vtype: str, ep_idx: int, dry_run: bool):
    a        = ANIMALS[animal]
    en_music = a["music"]
    stem     = en_mp4.stem

    for lang, queue in [("en", QUEUE_EN), ("ar", QUEUE_AR), ("id", QUEUE_ID)]:
        queue.mkdir(parents=True, exist_ok=True)
        target_stem = stem if lang == "en" else f"{stem}_{lang}"
        target      = queue / f"{target_stem}.mp4"

        if lang != "en" and not target.exists() and not dry_run:
            lang_music = alt_music(en_music, ep_idx, lang)
            props = make_props_A(animal) if vtype == "A" else make_props_B(animal)
            props["musicFile"] = lang_music
            # AR/ID: swap pig sprite for halal substitute
            if lang in ("ar", "id") and "sprite_ar" in a:
                props["sprites"][0]["path"] = a["sprite_ar"]
            print(f"\n    Rendering {animal} [{vtype}] ({lang.upper()}) → {target.name}")
            cmd = [
                "npx", "remotion", "render",
                "src/index.ts", "DanceSpriteLong",
                str(target),
                "--props", json.dumps(props),
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
            meta = make_meta(animal, vtype, lang)
            if not dry_run:
                with open(meta_path, "w") as f:
                    yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
                print(f"    meta {lang.upper()} → {meta_path.name}")
            else:
                print(f"    [DRY RUN] meta {lang.upper()}")

        if not thumb_path.exists() and not dry_run:
            time.sleep(0.5)
            generate_thumbnail(animal, vtype, thumb_path)


def main():
    parser = argparse.ArgumentParser(description="Generate DanceSpriteLong pet videos")
    parser.add_argument("--animal",    default=None, choices=list(ANIMALS),
                        help="Specific animal (default: all)")
    parser.add_argument("--type",      default=None, choices=["A", "B"],
                        help="Video type A=solo B=pair (default: both)")
    parser.add_argument("--dry-run",   action="store_true")
    parser.add_argument("--force",     action="store_true")
    parser.add_argument("--regen-meta", action="store_true")
    args = parser.parse_args()

    animals = [args.animal] if args.animal else list(ANIMALS)
    vtypes  = [args.type]   if args.type   else ["A", "B"]

    all_tasks = [
        (an, vt) for an in ANIMALS for vt in ["A", "B"]
        if vt == "A" or ANIMALS[an].get("partner")
    ]
    tasks = [
        (an, vt) for an in animals for vt in vtypes
        if vt == "A" or ANIMALS[an].get("partner")
    ]

    print(f"=== Dance Pet — {len(tasks)} videos ===\n")

    for animal, vtype in tasks:
        a      = ANIMALS[animal]
        ep_idx = all_tasks.index((animal, vtype))
        print(f"[{animal.upper()}-{vtype}] {a['name_en']}")

        slug = f"pet_{animal}_{vtype.lower()}_{DATE_STR}.mp4"
        mp4  = QUEUE_EN / slug

        if args.regen_meta:
            if mp4.exists():
                publish_to_all_channels(mp4, animal, vtype, ep_idx, args.dry_run)
            else:
                print(f"  ! No MP4 at {mp4}")
            continue

        mp4 = render_video(animal, vtype, args.force, args.dry_run)
        if mp4 and (mp4.exists() or args.dry_run):
            publish_to_all_channels(mp4, animal, vtype, ep_idx, args.dry_run)

    print("\n=== Done ===")


if __name__ == "__main__":
    main()
