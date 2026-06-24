#!/usr/bin/env python3
"""
generate_dance_fruits_2stage.py — Two-stage fruit & vegetable dance series.
Stage A (no text): 14 videos × 30 min → DanceSpriteLong30 → EN + AR + ID
Stage B (text + TTS): DEFERRED — requires text overlay composition.

Stage A videos (no text, universal):
  A-01  apple       bounce + roll
  A-02  banana      swing + pendulum
  A-03  orange      wobble + slow roll
  A-04  strawberry  tip-tap + bounce
  A-05  carrot      wave + whip
  A-06  watermelon  heavy bounce + roll
  A-07  grapes      cluster sway + orbit
  A-08  pineapple   march + crown wave
  A-09  tomato      wobble + squish
  A-10  corn        pendulum + kernel wave
  A-11  lemon       spin + sharp bounce
  A-12  cherry      pair swing + bob
  A-13  fruits together (apple banana orange strawberry watermelon)
  A-14  vegetables together (carrot tomato corn broccoli)

Usage:
  python3 scripts/generate_dance_fruits_2stage.py --list
  python3 scripts/generate_dance_fruits_2stage.py --videos all [--dry-run] [--force]
  python3 scripts/generate_dance_fruits_2stage.py --videos A-01 A-02
  python3 scripts/generate_dance_fruits_2stage.py --regen-meta
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

BG     = "#0A1628"
ACCENT = "#FFFFFF"

# Sprite paths (relative to remotion/public/sprites/)
S = {
    "apple":      "fruits/apple.png",
    "banana":     "fruits/banana.png",
    "orange":     "fruits/orange.png",
    "strawberry": "fruits/strawberry.png",
    "watermelon": "fruits/watermelon.png",
    "grapes":     "fruits/grapes.png",
    "pineapple":  "fruits/pineapple.png",
    "lemon":      "fruits/lemon.png",
    "cherry":     "fruits/cherry.png",
    "carrot":     "vegetables/carrot.png",
    "tomato":     "vegetables/tomato.png",
    "corn":       "vegetables/corn.png",
    "broccoli":   "vegetables/broccoli.png",
}


# ── Props builders ─────────────────────────────────────────────────────────────

def _sp(name: str, posX: float, posY: float, size: int, seed: int) -> dict:
    return {"path": S[name], "size": size, "posX": posX, "posY": posY, "seed": seed}


def solo_blocks(m1: str, p1: float, a1: int,
                m2: str, p2: float, a2: int,
                m3: str, p3: float, a3: int,
                m4: str, p4: float, a4: int) -> list:
    """Standard 6-block structure for a 30-min solo video."""
    return [
        {"startSec": 0,    "endSec": 90,   "motion": "FADEIN"},
        {"startSec": 90,   "endSec": 390,  "motion": m1, "period": p1, "amplitude": a1},
        {"startSec": 390,  "endSec": 690,  "motion": m2, "period": p2, "amplitude": a2},
        {"startSec": 690,  "endSec": 990,  "motion": m3, "period": p3, "amplitude": a3},
        {"startSec": 990,  "endSec": 1380, "motion": m4, "period": p4, "amplitude": a4},
        {"startSec": 1380, "endSec": 1620, "motion": "PULSE",  "period": 4.0, "amplitude": 12},
        {"startSec": 1620, "endSec": 1800, "motion": "DRIFT",  "period": 14,  "amplitude": 240},
    ]


PROPS: dict[str, dict] = {}

# A-01 Apple: bounce + roll + sway
PROPS["A-01"] = {
    "bgColor": BG, "accentColor": ACCENT, "musicFile": "Carefree.mp3", "bgEffect": "bubbles",
    "sprites": [_sp("apple", 0.5, 0.45, 500, 1)],
    "blocks": solo_blocks(
        "BOUNCE", 1.8, 80,
        "SWAY",   3.5, 65,
        "BOUNCE", 1.5, 90,
        "DRIFT",  12,  280,
    ),
}

# A-02 Banana: sway (pendulum) + spin + drift
PROPS["A-02"] = {
    "bgColor": BG, "accentColor": ACCENT, "musicFile": "Wholesome.mp3", "bgEffect": "bubbles",
    "sprites": [_sp("banana", 0.5, 0.45, 480, 1)],
    "blocks": solo_blocks(
        "SWAY",  3.0, 70,
        "SPIN",  5.0, 0,
        "SWAY",  4.0, 60,
        "DRIFT", 12,  270,
    ),
}

# A-03 Orange: slow bob + wobble (sway) + drift
PROPS["A-03"] = {
    "bgColor": BG, "accentColor": ACCENT, "musicFile": "Heartwarming.mp3", "bgEffect": "bubbles",
    "sprites": [_sp("orange", 0.5, 0.45, 500, 1)],
    "blocks": solo_blocks(
        "BOB",   4.0, 40,
        "SWAY",  5.0, 50,
        "BOB",   3.5, 45,
        "DRIFT", 14,  250,
    ),
}

# A-04 Strawberry: bounce (tip-tap) + bob + pulse
PROPS["A-04"] = {
    "bgColor": BG, "accentColor": ACCENT, "musicFile": "Quirky Dog.mp3", "bgEffect": "bubbles",
    "sprites": [_sp("strawberry", 0.5, 0.45, 480, 1)],
    "blocks": solo_blocks(
        "BOUNCE", 1.6, 75,
        "BOB",    2.0, 55,
        "BOUNCE", 1.4, 80,
        "DRIFT",  11,  260,
    ),
}

# A-05 Carrot: sway (wave whip) + spin + drift
PROPS["A-05"] = {
    "bgColor": BG, "accentColor": ACCENT, "musicFile": "Crinoline Dreams.mp3", "bgEffect": "bubbles",
    "sprites": [_sp("carrot", 0.5, 0.45, 480, 1)],
    "blocks": solo_blocks(
        "SWAY",  2.5, 70,
        "SPIN",  4.0, 0,
        "SWAY",  3.0, 65,
        "DRIFT", 12,  260,
    ),
}

# A-06 Watermelon: heavy slow bounce + sway + drift
PROPS["A-06"] = {
    "bgColor": BG, "accentColor": ACCENT, "musicFile": "Gymnopedie No 1.mp3", "bgEffect": "bubbles",
    "sprites": [_sp("watermelon", 0.5, 0.45, 520, 1)],
    "blocks": solo_blocks(
        "BOB",   5.0, 35,
        "SWAY",  6.0, 45,
        "BOUNCE",3.0, 50,
        "DRIFT", 16,  220,
    ),
}

# A-07 Grapes: cluster bob + orbit sway + drift
PROPS["A-07"] = {
    "bgColor": BG, "accentColor": ACCENT, "musicFile": "Life of Riley.mp3", "bgEffect": "bubbles",
    "sprites": [_sp("grapes", 0.5, 0.45, 480, 1)],
    "blocks": solo_blocks(
        "BOB",   2.5, 55,
        "PULSE", 3.0, 14,
        "SWAY",  3.5, 60,
        "DRIFT", 12,  260,
    ),
}

# A-08 Pineapple: march + bob + sway + drift
PROPS["A-08"] = {
    "bgColor": BG, "accentColor": ACCENT, "musicFile": "Merry Go.mp3", "bgEffect": "bubbles",
    "sprites": [_sp("pineapple", 0.5, 0.45, 480, 1)],
    "blocks": [
        {"startSec": 0,    "endSec": 90,   "motion": "FADEIN"},
        {"startSec": 90,   "endSec": 390,  "motion": "MARCH",  "period": 8,   "bobAmplitude": 25},
        {"startSec": 390,  "endSec": 690,  "motion": "BOB",    "period": 2.5, "amplitude": 55},
        {"startSec": 690,  "endSec": 990,  "motion": "SWAY",   "period": 3.5, "amplitude": 60},
        {"startSec": 990,  "endSec": 1380, "motion": "MARCH",  "period": 9,   "bobAmplitude": 20},
        {"startSec": 1380, "endSec": 1620, "motion": "PULSE",  "period": 3.5, "amplitude": 12},
        {"startSec": 1620, "endSec": 1800, "motion": "DRIFT",  "period": 13,  "amplitude": 250},
    ],
}

# A-09 Tomato: bob (wobble) + sway + drift
PROPS["A-09"] = {
    "bgColor": BG, "accentColor": ACCENT, "musicFile": "Carefree.mp3", "bgEffect": "bubbles",
    "sprites": [_sp("tomato", 0.5, 0.45, 490, 1)],
    "blocks": solo_blocks(
        "BOB",   3.0, 50,
        "SWAY",  4.0, 55,
        "PULSE", 2.5, 13,
        "DRIFT", 13,  255,
    ),
}

# A-10 Corn: sway (pendulum) + wave motion + drift
PROPS["A-10"] = {
    "bgColor": BG, "accentColor": ACCENT, "musicFile": "Wholesome.mp3", "bgEffect": "bubbles",
    "sprites": [_sp("corn", 0.5, 0.45, 480, 1)],
    "blocks": solo_blocks(
        "SWAY",  3.0, 65,
        "BOB",   2.5, 50,
        "SWAY",  4.0, 60,
        "DRIFT", 12,  250,
    ),
}

# A-11 Lemon: spin + sharp bounce + sway
PROPS["A-11"] = {
    "bgColor": BG, "accentColor": ACCENT, "musicFile": "Quirky Dog.mp3", "bgEffect": "bubbles",
    "sprites": [_sp("lemon", 0.5, 0.45, 480, 1)],
    "blocks": solo_blocks(
        "SPIN",  3.5, 0,
        "BOUNCE",1.4, 80,
        "SPIN",  4.0, 0,
        "DRIFT", 11,  260,
    ),
}

# A-12 Cherry: pair swing (sway) + bob + drift
PROPS["A-12"] = {
    "bgColor": BG, "accentColor": ACCENT, "musicFile": "Heartwarming.mp3", "bgEffect": "bubbles",
    "sprites": [_sp("cherry", 0.5, 0.45, 480, 1)],
    "blocks": solo_blocks(
        "SWAY",  2.0, 65,
        "BOB",   2.0, 55,
        "SWAY",  2.5, 70,
        "DRIFT", 12,  255,
    ),
}

# A-13 Fruits together (5 items)
PROPS["A-13"] = {
    "bgColor": BG, "accentColor": ACCENT, "musicFile": "Happy Happy Game Show.mp3",
    "bgEffect": "bubbles",
    "sprites": [
        _sp("apple",      0.10, 0.45, 260, 1),
        _sp("banana",     0.28, 0.45, 260, 2),
        _sp("orange",     0.50, 0.45, 260, 3),
        _sp("strawberry", 0.72, 0.45, 260, 4),
        _sp("watermelon", 0.90, 0.45, 260, 5),
    ],
    "blocks": [
        {"startSec": 0,    "endSec": 180,  "motion": "FADEIN"},
        {"startSec": 180,  "endSec": 480,  "motion": "WAVE",   "period": 2.5,
         "amplitude": 55,  "waveDelay": 0.30},
        {"startSec": 480,  "endSec": 880,  "motion": "ORBIT",
         "orbitCenterX": 0.5, "orbitCenterY": 0.45},
        {"startSec": 880,  "endSec": 1280, "motion": "BOUNCE", "period": 2.0,  "amplitude": 55},
        {"startSec": 1280, "endSec": 1580, "motion": "SWAY",   "period": 5.0,  "amplitude": 48},
        {"startSec": 1580, "endSec": 1800, "motion": "DRIFT",  "period": 13,   "amplitude": 230},
    ],
}

# A-14 Vegetables together (4 items)
PROPS["A-14"] = {
    "bgColor": BG, "accentColor": ACCENT, "musicFile": "Carefree.mp3", "bgEffect": "bubbles",
    "sprites": [
        _sp("carrot",   0.2, 0.45, 310, 1),
        _sp("tomato",   0.4, 0.45, 310, 2),
        _sp("corn",     0.6, 0.45, 310, 3),
        _sp("broccoli", 0.8, 0.45, 310, 4),
    ],
    "blocks": [
        {"startSec": 0,    "endSec": 150,  "motion": "FADEIN"},
        {"startSec": 150,  "endSec": 450,  "motion": "WAVE",   "period": 2.8,
         "amplitude": 52,  "waveDelay": 0.35},
        {"startSec": 450,  "endSec": 800,  "motion": "ORBIT",
         "orbitCenterX": 0.5, "orbitCenterY": 0.45},
        {"startSec": 800,  "endSec": 1200, "motion": "BOUNCE", "period": 2.2,  "amplitude": 50},
        {"startSec": 1200, "endSec": 1550, "motion": "SWAY",   "period": 5.5,  "amplitude": 45},
        {"startSec": 1550, "endSec": 1800, "motion": "DRIFT",  "period": 12,   "amplitude": 230},
    ],
}


# ── Video table ────────────────────────────────────────────────────────────────

ITEM_NAMES = {
    "A-01": ("Apple",      "تفاحة",    "Apel"),
    "A-02": ("Banana",     "موزة",     "Pisang"),
    "A-03": ("Orange",     "برتقالة", "Jeruk"),
    "A-04": ("Strawberry", "فراولة",  "Stroberi"),
    "A-05": ("Carrot",     "جزرة",    "Wortel"),
    "A-06": ("Watermelon", "بطيخة",   "Semangka"),
    "A-07": ("Grapes",     "عنب",     "Anggur"),
    "A-08": ("Pineapple",  "أناناس",  "Nanas"),
    "A-09": ("Tomato",     "طماطم",   "Tomat"),
    "A-10": ("Corn",       "ذرة",     "Jagung"),
    "A-11": ("Lemon",      "ليمون",   "Lemon"),
    "A-12": ("Cherry",     "كرز",     "Ceri"),
    "A-13": ("Fruits Dance Party", "رقصة الفواكه", "Pesta Buah"),
    "A-14": ("Veggie Dance Party", "رقصة الخضروات", "Pesta Sayur"),
}

VIDEOS = {vid: {"props": PROPS[vid], "names": ITEM_NAMES[vid], "comp": "DanceSpriteLong30"}
          for vid in PROPS}


# ── Meta generation ────────────────────────────────────────────────────────────

def make_meta(video_id: str, lang: str) -> dict:
    ch = {"en": "@HappyBearKids1", "ar": "@happybearkidsar", "id": "@happybearkidsin"}
    name_en, name_ar, name_id = ITEM_NAMES[video_id]
    series_en = "Dancing Fruits & Vegetables"
    series_ar = "رقصة الفواكه والخضروات"
    series_id = "Tarian Buah & Sayur"

    if lang == "en":
        title = f"Dancing {name_en}! 🎵 30 Min Baby Animation | Happy Bear Kids"
        description = (
            f"✨ Watch a beautiful animated {name_en.lower()} dance and move for 30 minutes!\n\n"
            f"No words, no text — pure visual delight. "
            f"A single colorful character dancing to gentle music. "
            f"Perfect for babies and toddlers to watch quietly.\n\n"
            f"🎯 Perfect for:\n"
            f"• Background video during play time\n"
            f"• Visual stimulation for babies 0–3\n"
            f"• Calming colorful screen time\n"
            f"• Nap time wind-down\n\n"
            f"🍎 Part of the {series_en} series — introducing one item at a time!\n\n"
            f"🔔 Subscribe → {ch['en']} for more baby animations every day!\n\n"
            f"🎵 Music: Kevin MacLeod (incompetech.com)\n"
            f"Licensed under Creative Commons Attribution 4.0 (CC BY 4.0)\n\n"
            f"#Dancing{name_en.replace(' ', '')} #HappyBearKids #BabyAnimation #ToddlerTV "
            f"#FruitDance #NoTalking #VisualBaby #BabyBackground #KevinMacLeod #BabyTV"
        )
    elif lang == "ar":
        title = f"رقصة {name_ar}! 🎵 30 دقيقة رسوم أطفال | هابي بير كيدز"
        description = (
            f"✨ شاهد {name_ar} الرسوم المتحركة الجميلة ترقص لمدة 30 دقيقة!\n\n"
            f"بدون كلمات أو نصوص — بهجة بصرية خالصة. "
            f"شخصية ملونة واحدة ترقص على موسيقى هادئة.\n\n"
            f"🎯 مثالي لـ:\n"
            f"• فيديو خلفية أثناء وقت اللعب\n"
            f"• تحفيز بصري للأطفال 0–3 سنوات\n"
            f"• وقت شاشة هادئ وملون\n"
            f"• الاسترخاء قبل قيلولة الطفل\n\n"
            f"🍎 جزء من سلسلة {series_ar}!\n\n"
            f"🔔 اشتركوا → {ch['ar']} للمزيد من رسوم الأطفال كل يوم!\n\n"
            f"🎵 الموسيقى: Kevin MacLeod — Creative Commons Attribution 4.0\n\n"
            f"#رسوم_أطفال #هابي_بير_كيدز #رقصة_فواكه #بدون_كلام "
            f"#فيديو_للرضع #تحفيز_بصري #رسوم_متحركة"
        )
    else:  # id
        title = f"Tarian {name_id}! 🎵 30 Menit Animasi Bayi | Happy Bear Kids"
        description = (
            f"✨ Saksikan {name_id.lower()} animasi yang indah menari selama 30 menit!\n\n"
            f"Tanpa kata-kata, tanpa teks — hiburan visual murni. "
            f"Satu karakter warna-warni menari mengikuti musik lembut.\n\n"
            f"🎯 Sempurna untuk:\n"
            f"• Video latar saat waktu bermain\n"
            f"• Stimulasi visual untuk bayi 0–3 tahun\n"
            f"• Waktu layar yang menenangkan\n"
            f"• Bersiap tidur siang\n\n"
            f"🍎 Bagian dari seri {series_id}!\n\n"
            f"🔔 Subscribe → {ch['id']} untuk animasi bayi setiap hari!\n\n"
            f"🎵 Musik: Kevin MacLeod — Creative Commons Attribution 4.0\n\n"
            f"#AnimasiAnak #HappyBearKids #TarianBuah #TanpaSuara "
            f"#VideoUntukBayi #StimulasiBayi #AnimasiLucu"
        )

    return {
        "title":       title,
        "description": description,
        "tags": ["fruit dance", "baby animation", "happy bear kids", "30 minutes",
                 "single fruit", "no talking", "visual baby", "baby background",
                 "toddler tv", name_en.lower()],
        "video_type": "dance_fruits_2stage_a",
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

    name_en = ITEM_NAMES[video_id][0]
    notext = "" if lang == "en" else ", no text, no letters, no words, no numbers"
    prompt = (
        f"cute 3D cartoon {name_en.lower()} character dancing, Pixar style, "
        f"dark blue background, bright colors, children's YouTube thumbnail, "
        f"single fruit character{notext}"
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
    v        = VIDEOS[video_id]
    slug     = f"fruits2s_{video_id.lower().replace('-', '')}_{DATE_STR}.mp4"
    out_path = QUEUE_EN / slug

    if out_path.exists() and not force:
        sz = out_path.stat().st_size / 1024 / 1024
        print(f"  skip {slug} ({sz:.0f}MB)")
        return out_path

    props = v["props"]
    comp  = v["comp"]
    n     = len(props["sprites"])

    print(f"\n  Rendering {video_id}: {ITEM_NAMES[video_id][0]} → {slug}")
    if dry_run:
        print(f"    [DRY RUN] {comp}  sprites={n}")
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

def publish_to_all_channels(mp4_path: Path, video_id: str, ep_idx: int, dry_run: bool):
    v        = VIDEOS[video_id]
    props_en = v["props"]
    en_music = props_en["musicFile"]
    comp     = v["comp"]
    stem     = mp4_path.stem

    for lang, queue in [("en", QUEUE_EN), ("ar", QUEUE_AR), ("id", QUEUE_ID)]:
        queue.mkdir(parents=True, exist_ok=True)
        if lang == "en":
            target      = mp4_path
            target_stem = stem
        else:
            target_stem = f"{stem}_{lang}"
            target      = queue / f"{target_stem}.mp4"
            if not target.exists() and not dry_run:
                lang_music = alt_music(en_music, ep_idx, lang)
                props_lang = dict(props_en)
                props_lang["musicFile"] = lang_music
                print(f"  Rendering ({lang}) {target.name}")
                cmd = [
                    "npx", "remotion", "render",
                    "src/index.ts", comp,
                    str(target),
                    "--props", json.dumps(props_lang),
                    "--concurrency", "1",
                    "--log", "error",
                ]
                start  = time.time()
                result = subprocess.run(cmd, cwd=str(REMOTION),
                                        capture_output=True, text=True, timeout=21600)
                if result.returncode == 0 and target.exists():
                    elapsed = (time.time() - start) / 60
                    sz      = target.stat().st_size / 1024 / 1024
                    print(f"    ✓ {sz:.0f}MB in {elapsed:.0f}min")
                else:
                    print(f"    ✗ FAILED ({lang}): {result.stderr[-400:]}")
                    continue

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
    parser = argparse.ArgumentParser(description="Generate 2-stage fruit/veg dance videos (Stage A)")
    parser.add_argument("--list",      action="store_true")
    parser.add_argument("--videos",    nargs="*",
                        help="Video IDs (A-01..A-14) or 'all'")
    parser.add_argument("--dry-run",   action="store_true")
    parser.add_argument("--force",     action="store_true")
    parser.add_argument("--regen-meta", action="store_true")
    args = parser.parse_args()

    if args.list:
        print("2-Stage Fruit Dance Videos (Stage A — no text):")
        for vid in VIDEOS:
            n    = len(VIDEOS[vid]["props"]["sprites"])
            name = ITEM_NAMES[vid][0]
            print(f"  {vid}  {name:20s}  {n} sprite(s)  30 min  DanceSpriteLong30")
        return

    video_ids = (list(VIDEOS) if not args.videos or args.videos == ["all"]
                 else args.videos)
    invalid = [v for v in video_ids if v not in VIDEOS]
    if invalid:
        print(f"Unknown IDs: {', '.join(invalid)}. Available: {', '.join(VIDEOS)}")
        sys.exit(1)

    print(f"=== Dance Fruits 2-Stage A — {len(video_ids)} videos ===\n")

    all_video_ids = list(VIDEOS.keys())
    for video_id in video_ids:
        ep_idx = all_video_ids.index(video_id)
        print(f"[{video_id}] {ITEM_NAMES[video_id][0]}")

        slug = f"fruits2s_{video_id.lower().replace('-', '')}_{DATE_STR}.mp4"
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
