#!/usr/bin/env python3
"""
generate_special_mechanics.py — Special Mechanics Series (Episodes 7–14)
8 episodes × 3 channels = 24 videos. All no-text → universal (EN + AR + ID).

Episodes:
  7   Hide & Seek       (DanceSpriteLong — peek-a-boo rabbit/cat/dog)
  8   Shadows           (DanceShapeLong — bright shapes + dark shadow pairs)
  9   Bubbles           (StarsBubblesLong — 22 min bubble paradise)
  10  Reflections       (DanceShapeLong — mirrored pairs left/right)
  11  Silent Count      (DanceShapeLong — 10 circles sequential FADEIN)
  12  Birthday Party    (DanceShapeLong — rainbow celebration)
  13  Mirror Dance      (DanceSpriteLong — bear + cat with flipX mirror pairs)
  14  Sleep Time        (DanceShapeLong30 — 30 min nightMode stars + moon)

Usage:
  python3 scripts/generate_special_mechanics.py --list
  python3 scripts/generate_special_mechanics.py --videos all [--dry-run] [--force]
  python3 scripts/generate_special_mechanics.py --videos 7 9 12
  python3 scripts/generate_special_mechanics.py --regen-meta
"""
import argparse, base64, json, shutil, subprocess, sys, time, yaml
from datetime import datetime
from pathlib import Path

ROOT      = Path(__file__).resolve().parent.parent
REMOTION  = ROOT / "remotion"
QUEUE_EN  = ROOT / "output" / "queue"
QUEUE_AR  = ROOT / "output" / "queue_ar"
QUEUE_ID  = ROOT / "output" / "queue_id"
TOGETHER_KEY_FILE = ROOT / "credentials" / "together_api_key.txt"
TOGETHER_URL   = "https://api.together.xyz/v1/images/generations"
TOGETHER_MODEL = "black-forest-labs/FLUX.1-schnell"
DATE_STR  = datetime.now().strftime("%Y%m%d")

RAINBOW = ["#E53935","#FF9800","#FDD835","#43A047","#1E88E5","#9C27B0","#E91E63","#E53935"]

# Suno AI tracks — unique per episode+lang for distinct YT audio fingerprint
LANG_MUSIC = {
    "7":  {"en": "Spring Waltz v2.mp3",          "ar": "Afternoon in F v2.mp3",      "id": "Morning Trail.mp3"},
    "8":  {"en": "The Glass Forest v2.mp3",       "ar": "Rain Etude in C Minor v2.mp3","id": "Moonlight Waltz.mp3"},
    "9":  {"en": "Dreamy Arpeggios v2.mp3",       "ar": "Rainbow Lantern v2.mp3",     "id": "Rainbow Lantern.mp3"},
    "10": {"en": "Moonlight Waltz.mp3",           "ar": "Tide and Piano v2.mp3",      "id": "Tide and Piano.mp3"},
    "11": {"en": "Afternoon in F v2.mp3",         "ar": "Morning Trail v2.mp3",       "id": "Spring Waltz v2.mp3"},
    "12": {"en": "Rainbow Lantern v2.mp3",        "ar": "Rainbow Lantern.mp3",        "id": "Morning Trail v2.mp3"},
    "13": {"en": "Spring Waltz.mp3",              "ar": "The Golden Meadow v2.mp3",   "id": "Afternoon in F v2.mp3"},
    "14": {"en": "Moonlight on the Cradle v2.mp3","ar": "Dreamy Arpeggios v2.mp3",   "id": "Moonlight on the Piano v2.mp3"},
}

SERIES_EN = "Special Mechanics"
SERIES_AR = "ميكانيكا خاصة"
SERIES_ID = "Mekanika Khusus"

VIDEOS = {
    "7": {
        "name_en": "Hide and Seek",
        "name_ar": "الغميضة",
        "name_id": "Petak Umpet",
        "comp": "DanceSpriteLong",
        "dur_label": "25 min",
        "props": {
            "bgColor": "#0A1A08",
            "bgColorEnd": "#05100A",
            "accentColor": "#66BB6A",
            "musicFile": "Spring Waltz v2.mp3",
            "volume": 0.18,
            "bgEffect": "sparkles",
            "sprites": [
                {"path": "animals/rabbit_3d.png", "size": 450, "posX": 0.50, "posY": 0.44, "seed": 1},
                {"path": "animals/cat_3d.png",    "size": 190, "posX": 0.20, "posY": 0.52, "seed": 2},
                {"path": "animals/dog_3d.png",    "size": 180, "posX": 0.80, "posY": 0.52, "seed": 3},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 120,  "motion": "FADEIN",  "amplitude": 60, "wobble": True},
                {"startSec": 120,  "endSec": 420,  "motion": "BOB",     "period": 3.0,  "amplitude": 40, "wobble": True},
                {"startSec": 420,  "endSec": 700,  "motion": "SWAY",    "period": 5.0,  "amplitude": 55, "wobble": True},
                {"startSec": 700,  "endSec": 1000, "motion": "BOUNCE",  "period": 2.5,  "amplitude": 80, "wobble": True},
                {"startSec": 1000, "endSec": 1300, "motion": "WAVE",    "period": 4.0,  "amplitude": 60, "waveDelay": 0.4, "wobble": True},
                {"startSec": 1300, "endSec": 1500, "motion": "BOB",     "period": 5.0,  "amplitude": 30, "wobble": True},
            ],
        },
    },
    "8": {
        "name_en": "Shadows",
        "name_ar": "الظلال",
        "name_id": "Bayangan",
        "comp": "DanceShapeLong",
        "dur_label": "25 min",
        "props": {
            "bgColor": "#F5EFE0",
            "musicFile": "The Glass Forest v2.mp3",
            "volume": 0.18,
            "shapes": [
                # Upper bright shapes (the objects)
                {"shape": "circle",  "color": "#FFD700", "size": 200, "posX": 0.25, "posY": 0.28, "seed": 1},
                {"shape": "star",    "color": "#4FC3F7", "size": 180, "posX": 0.50, "posY": 0.27, "seed": 2},
                {"shape": "hexagon", "color": "#FF9800", "size": 190, "posX": 0.75, "posY": 0.28, "seed": 3},
                # Lower dark shadow shapes (offset below each bright shape)
                {"shape": "circle",  "color": "#5D4037", "size": 200, "posX": 0.27, "posY": 0.68, "seed": 4},
                {"shape": "star",    "color": "#455A64", "size": 180, "posX": 0.52, "posY": 0.70, "seed": 5},
                {"shape": "hexagon", "color": "#4E342E", "size": 190, "posX": 0.77, "posY": 0.68, "seed": 6},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 120,  "motion": "FADEIN", "amplitude": 60, "wobble": True},
                {"startSec": 120,  "endSec": 600,  "motion": "SWAY",   "period": 4.0, "amplitude": 50, "wobble": True},
                {"startSec": 600,  "endSec": 1000, "motion": "BOB",    "period": 5.0, "amplitude": 30, "wobble": True},
                {"startSec": 1000, "endSec": 1500, "motion": "DRIFT",  "period": 12,  "amplitude": 110, "wobble": True},
            ],
        },
    },
    "9": {
        "name_en": "Bubbles",
        "name_ar": "فقاعات",
        "name_id": "Gelembung",
        "comp": "StarsBubblesLong",
        "dur_label": "22 min",
        "props": {
            "bgColor": "#030814",
            "musicFile": "Dreamy Arpeggios v2.mp3",
            "volume": 0.18,
            "seed": 99,
            "segments": [
                {"startSec": 0,    "endSec": 30,   "mode": "intro"},
                {"startSec": 30,   "endSec": 300,  "mode": "bubbles", "bubbleCount": 30},
                {"startSec": 300,  "endSec": 540,  "mode": "both",    "bubbleCount": 25, "starCount": 10},
                {"startSec": 540,  "endSec": 780,  "mode": "bubbles", "bubbleCount": 40},
                {"startSec": 780,  "endSec": 960,  "mode": "both",    "bubbleCount": 30, "starCount": 15, "shootRate": 4},
                {"startSec": 960,  "endSec": 1080, "mode": "calm",    "bubbleCount": 10, "starCount": 5},
                {"startSec": 1080, "endSec": 1260, "mode": "bubbles", "bubbleCount": 45},
                {"startSec": 1260, "endSec": 1320, "mode": "finale",  "bubbleCount": 50},
            ],
        },
    },
    "10": {
        "name_en": "Reflections",
        "name_ar": "انعكاسات",
        "name_id": "Pantulan",
        "comp": "DanceShapeLong",
        "dur_label": "25 min",
        "props": {
            "bgColor": "#020A10",
            "musicFile": "Moonlight Waltz.mp3",
            "volume": 0.18,
            "shapes": [
                # Left column
                {"shape": "star",    "color": "#4FC3F7", "size": 200, "posX": 0.22, "posY": 0.35, "seed": 1},
                {"shape": "circle",  "color": "#80DEEA", "size": 185, "posX": 0.22, "posY": 0.52, "seed": 3},
                {"shape": "diamond", "color": "#B0BEC5", "size": 175, "posX": 0.22, "posY": 0.68, "seed": 5},
                # Right column (mirror)
                {"shape": "star",    "color": "#4FC3F7", "size": 200, "posX": 0.78, "posY": 0.35, "seed": 2},
                {"shape": "circle",  "color": "#80DEEA", "size": 185, "posX": 0.78, "posY": 0.52, "seed": 4},
                {"shape": "diamond", "color": "#B0BEC5", "size": 175, "posX": 0.78, "posY": 0.68, "seed": 6},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 200,  "motion": "FADEIN", "amplitude": 60, "wobble": True},
                {"startSec": 200,  "endSec": 600,  "motion": "BOB",    "period": 4.0, "amplitude": 30, "wobble": True},
                {"startSec": 600,  "endSec": 1000, "motion": "SWAY",   "period": 5.0, "amplitude": 55, "wobble": True},
                {"startSec": 1000, "endSec": 1500, "motion": "DRIFT",  "period": 15,  "amplitude": 100, "wobble": True},
            ],
        },
    },
    "11": {
        "name_en": "Silent Count",
        "name_ar": "العد الصامت",
        "name_id": "Hitung Diam",
        "comp": "DanceShapeLong",
        "dur_label": "25 min",
        "props": {
            "bgColor": "#0A0A05",
            "musicFile": "Afternoon in F v2.mp3",
            "volume": 0.18,
            "shapes": [
                # Row 1: circles 1–5
                {"shape": "circle", "color": "#E53935", "size": 140, "posX": 0.12, "posY": 0.35, "seed": 1},
                {"shape": "circle", "color": "#FF9800", "size": 140, "posX": 0.28, "posY": 0.35, "seed": 2},
                {"shape": "circle", "color": "#FDD835", "size": 140, "posX": 0.50, "posY": 0.35, "seed": 3},
                {"shape": "circle", "color": "#43A047", "size": 140, "posX": 0.72, "posY": 0.35, "seed": 4},
                {"shape": "circle", "color": "#1E88E5", "size": 140, "posX": 0.88, "posY": 0.35, "seed": 5},
                # Row 2: circles 6–10
                {"shape": "circle", "color": "#9C27B0", "size": 140, "posX": 0.12, "posY": 0.58, "seed": 6},
                {"shape": "circle", "color": "#E91E63", "size": 140, "posX": 0.28, "posY": 0.58, "seed": 7},
                {"shape": "circle", "color": "#00BCD4", "size": 140, "posX": 0.50, "posY": 0.58, "seed": 8},
                {"shape": "circle", "color": "#8BC34A", "size": 140, "posX": 0.72, "posY": 0.58, "seed": 9},
                {"shape": "circle", "color": "#FF5722", "size": 140, "posX": 0.88, "posY": 0.58, "seed": 10},
                # 2 special stars at top
                {"shape": "star", "color": "#FFF176", "size": 155, "posX": 0.30, "posY": 0.18, "seed": 11},
                {"shape": "star", "color": "#FFF176", "size": 155, "posX": 0.70, "posY": 0.18, "seed": 12},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 600,  "motion": "FADEIN",  "amplitude": 60, "wobble": True},
                {"startSec": 600,  "endSec": 1000, "motion": "BOUNCE",  "period": 2.5, "amplitude": 70, "wobble": True},
                {"startSec": 1000, "endSec": 1300, "motion": "WAVE",    "period": 3.0, "amplitude": 60, "waveDelay": 0.45, "wobble": True},
                {"startSec": 1300, "endSec": 1500, "motion": "DRIFT",   "period": 10,  "amplitude": 90, "wobble": True},
            ],
        },
    },
    "12": {
        "name_en": "Birthday Party",
        "name_ar": "حفلة عيد الميلاد",
        "name_id": "Pesta Ulang Tahun",
        "comp": "DanceShapeLong",
        "dur_label": "25 min",
        "props": {
            "bgColor": "#0A0510",
            "musicFile": "Rainbow Lantern v2.mp3",
            "volume": 0.22,
            "shapes": [
                {"shape": "star",   "color": "#E53935", "size": 220, "posX": 0.50, "posY": 0.30, "seed": 1},
                {"shape": "circle", "color": "#FF9800", "size": 180, "posX": 0.25, "posY": 0.42, "seed": 2},
                {"shape": "circle", "color": "#FDD835", "size": 175, "posX": 0.75, "posY": 0.42, "seed": 3},
                {"shape": "star",   "color": "#43A047", "size": 165, "posX": 0.15, "posY": 0.60, "seed": 4},
                {"shape": "star",   "color": "#1E88E5", "size": 165, "posX": 0.85, "posY": 0.60, "seed": 5},
                {"shape": "circle", "color": "#9C27B0", "size": 155, "posX": 0.38, "posY": 0.62, "seed": 6},
                {"shape": "circle", "color": "#E91E63", "size": 155, "posX": 0.62, "posY": 0.62, "seed": 7},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 100,  "motion": "FADEIN",  "amplitude": 60, "wobble": True},
                {"startSec": 100,  "endSec": 450,  "motion": "BOUNCE",  "period": 2.0,  "amplitude": 90,
                 "colorPalette": RAINBOW, "colorCycleSec": 40, "wobble": True},
                {"startSec": 450,  "endSec": 750,  "motion": "PULSE",   "period": 3.0,  "amplitude": 20,
                 "colorPalette": RAINBOW, "colorCycleSec": 35, "wobble": True},
                {"startSec": 750,  "endSec": 1100, "motion": "MARCH",   "period": 3.5,
                 "colorPalette": RAINBOW, "colorCycleSec": 45, "wobble": True},
                {"startSec": 1100, "endSec": 1500, "motion": "BOUNCE",  "period": 2.5,  "amplitude": 80,
                 "colorPalette": RAINBOW, "colorCycleSec": 40, "wobble": True},
            ],
        },
    },
    "13": {
        "name_en": "Mirror Dance",
        "name_ar": "رقصة المرآة",
        "name_id": "Tari Cermin",
        "comp": "DanceSpriteLong",
        "dur_label": "25 min",
        "props": {
            "bgColor": "#050508",
            "bgColorEnd": "#020205",
            "accentColor": "#CE93D8",
            "musicFile": "Spring Waltz.mp3",
            "volume": 0.18,
            "bgEffect": "sparkles",
            "sprites": [
                {"path": "characters/bear_happy_3d.png", "size": 445, "posX": 0.25, "posY": 0.44, "seed": 1, "flipX": False},
                {"path": "characters/bear_happy_3d.png", "size": 445, "posX": 0.75, "posY": 0.44, "seed": 2, "flipX": True},
                {"path": "animals/cat_3d.png",           "size": 195, "posX": 0.40, "posY": 0.52, "seed": 3, "flipX": False},
                {"path": "animals/cat_3d.png",           "size": 185, "posX": 0.60, "posY": 0.52, "seed": 4, "flipX": True},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 200,  "motion": "FADEIN",  "amplitude": 60, "wobble": True},
                {"startSec": 200,  "endSec": 600,  "motion": "SWAY",    "period": 4.0,  "amplitude": 60, "wobble": True},
                {"startSec": 600,  "endSec": 900,  "motion": "BOB",     "period": 3.0,  "amplitude": 40, "wobble": True},
                {"startSec": 900,  "endSec": 1200, "motion": "BOUNCE",  "period": 2.5,  "amplitude": 85, "wobble": True},
                {"startSec": 1200, "endSec": 1500, "motion": "DRIFT",   "period": 12,   "amplitude": 100, "wobble": True},
            ],
        },
    },
    "14": {
        "name_en": "Sleep Time",
        "name_ar": "وقت النوم",
        "name_id": "Waktu Tidur",
        "comp": "DanceShapeLong30",
        "dur_label": "30 min",
        "props": {
            "bgColor": "#010208",
            "musicFile": "Moonlight on the Cradle v2.mp3",
            "volume": 0.14,
            "nightMode": True,
            "shapes": [
                # Moon (large circle at top center)
                {"shape": "circle", "color": "#FFFDE7", "size": 180, "posX": 0.50, "posY": 0.18, "seed": 1},
                # 7 stars scattered
                {"shape": "star",   "color": "#FFF9C4", "size": 140, "posX": 0.18, "posY": 0.32, "seed": 2},
                {"shape": "star",   "color": "#FFF176", "size": 120, "posX": 0.80, "posY": 0.30, "seed": 3},
                {"shape": "star",   "color": "#FFFDE7", "size": 130, "posX": 0.35, "posY": 0.48, "seed": 4},
                {"shape": "star",   "color": "#FFF9C4", "size": 115, "posX": 0.65, "posY": 0.50, "seed": 5},
                {"shape": "star",   "color": "#FFF176", "size": 140, "posX": 0.12, "posY": 0.62, "seed": 6},
                {"shape": "star",   "color": "#FFFDE7", "size": 125, "posX": 0.88, "posY": 0.63, "seed": 7},
                {"shape": "star",   "color": "#FFF9C4", "size": 130, "posX": 0.50, "posY": 0.68, "seed": 8},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 300,  "motion": "FADEIN", "amplitude": 40, "wobble": True},
                {"startSec": 300,  "endSec": 900,  "motion": "PULSE",  "period": 5.0, "amplitude": 8, "wobble": True},
                {"startSec": 900,  "endSec": 1500, "motion": "DRIFT",  "period": 15,  "amplitude": 60, "wobble": True},
                {"startSec": 1500, "endSec": 1800, "motion": "PULSE",  "period": 7.0, "amplitude": 5, "wobble": True},
            ],
        },
    },
}

PROMPTS = {
    "7":  "cute cartoon rabbit cat and dog playing peek-a-boo behind trees, dark forest background, Pixar 3D style, children's animation",
    "8":  "colorful bright shapes with dark shadows underneath them, warm golden light, simple children's animation, Pixar 3D style",
    "9":  "magical glowing transparent bubbles floating in deep dark blue sky, iridescent light, dreamy, Pixar 3D style",
    "10": "colorful geometric stars circles diamonds with perfect mirror reflections, dark blue background, symmetrical, Pixar 3D style",
    "11": "ten colorful circles arranged in two rows with two glowing stars above, dark background, counting visual, Pixar 3D style",
    "12": "birthday party celebration with colorful balloons stars and rainbow confetti, festive, Pixar 3D style",
    "13": "cute bear and cat dancing with their perfect mirror reflections, purple sparkles background, Pixar 3D style",
    "14": "peaceful glowing moon and seven twinkling stars in deep dark sky, baby sleeping visual, serene, Pixar 3D style",
}


def make_meta(video_id: str, lang: str) -> dict:
    v    = VIDEOS[video_id]
    ch   = {"en": "@HappyBearKids1", "ar": "@happybearkidsar", "id": "@happybearkidsin"}
    name = v[f"name_{lang}"]
    dur  = v["dur_label"]
    if lang == "en":
        title = f"{name} | {dur} Baby Animation | Happy Bear Kids"
        description = (
            f"✨ {name} — captivating animation for babies and toddlers!\n\n"
            f"No words, no text — pure visual experience with beautiful shapes, "
            f"colors and gentle music designed for young viewers.\n\n"
            f"Part of our {SERIES_EN} series — exploring fascinating visual concepts "
            f"through animation that babies and toddlers find mesmerizing.\n\n"
            f"Every frame is crafted to capture and hold a young baby's attention, "
            f"with smooth movements, vibrant colors, and calming music.\n\n"
            f"🎯 Perfect for: visual stimulation, sensory development, background play\n"
            f"👶 Age: 0–3 years | 📺 {dur} continuous\n"
            f"🌈 No language barriers — universal for any culture\n\n"
            f"🔔 Subscribe → {ch['en']}\n"
            f"🎵 Original music by Happy Bear Kids (AI-generated, © 2026)\n\n"
            f"#{name.replace(' ','')} #HappyBearKids #BabyAnimation "
            f"#SpecialMechanics #VisualStimulation #ToddlerTV #BabySensory"
            f"\n© Happy Bear Kids 2026"
        )
        tags = [v["name_en"].lower(), "baby animation", "happy bear kids", "special mechanics",
                "visual stimulation", "no talking", dur, "toddler tv", "baby sensory"]
    elif lang == "ar":
        title = f"{name} | {dur} رسوم أطفال | هابي بير كيدز"
        description = (
            f"✨ {name} — رسوم متحركة رائعة للرضع والأطفال الصغار!\n\n"
            f"بدون كلمات أو نصوص — تجربة بصرية خالصة مع أشكال جميلة "
            f"وألوان مبهجة وموسيقى هادئة مصممة للمشاهدين الصغار.\n\n"
            f"جزء من سلسلة {SERIES_AR} — استكشاف مفاهيم بصرية رائعة "
            f"من خلال الرسوم المتحركة التي يجدها الرضع والأطفال آسرة.\n\n"
            f"كل لقطة مصممة لاستقطاب انتباه الرضع، مع حركات سلسة وألوان "
            f"زاهية وموسيقى مهدئة.\n\n"
            f"🎯 مثالي لـ: التحفيز البصري، التنمية الحسية، التشغيل في الخلفية\n"
            f"👶 العمر: 0–3 سنوات | 📺 {dur}\n\n"
            f"🔔 اشتركوا → {ch['ar']}\n"
            f"🎵 موسيقى أصلية من هابي بير كيدز\n\n"
            f"#{name.replace(' ','_')} #هابي_بير_كيدز #رسوم_أطفال "
            f"#تحفيز_بصري #ميكانيكا_خاصة\n© هابي بير كيدز 2026"
        )
        tags = [v["name_ar"], "هابي بير كيدز", "رسوم أطفال", "تحفيز بصري",
                "بدون كلام", "ميكانيكا خاصة"]
    else:
        title = f"{name} | {dur} Animasi Bayi | Happy Bear Kids"
        description = (
            f"✨ {name} — animasi memukau untuk bayi dan balita!\n\n"
            f"Tanpa kata-kata atau teks — pengalaman visual murni dengan bentuk indah, "
            f"warna cerah, dan musik lembut yang dirancang untuk penonton kecil.\n\n"
            f"Bagian dari seri {SERIES_ID} — menjelajahi konsep visual menakjubkan "
            f"melalui animasi yang memikat bayi dan balita.\n\n"
            f"Setiap frame dirancang untuk menarik perhatian bayi, dengan gerakan halus, "
            f"warna cerah, dan musik yang menenangkan.\n\n"
            f"🎯 Sempurna untuk: stimulasi visual, perkembangan sensorik, tayangan latar\n"
            f"👶 Usia: 0–3 tahun | 📺 {dur}\n\n"
            f"🔔 Subscribe → {ch['id']}\n"
            f"🎵 Original music by Happy Bear Kids (AI-generated, © 2026)\n\n"
            f"#{name.replace(' ','')} #HappyBearKids #AnimasiBayi "
            f"#StimulasiVisual #MekanikaKhusus\n© Happy Bear Kids Indonesia 2026"
        )
        tags = [v["name_id"].lower(), "animasi bayi", "happy bear kids", "mekanika khusus",
                "stimulasi visual", "tanpa suara", dur]
    return {"title": title, "description": description, "tags": tags,
            "video_type": "special_mechanics", "language": lang,
            "is_short": False, "status": "public"}


def generate_thumbnail(video_id: str, out_path: Path, lang: str) -> bool:
    if out_path.exists():
        return True
    try:
        key = TOGETHER_KEY_FILE.read_text().strip()
    except Exception:
        return False
    notext = "" if lang in ("en", "id") else ", no text, no letters, no words, no numbers"
    prompt = PROMPTS.get(video_id, "abstract baby animation") + f", YouTube thumbnail{notext}"
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("gat", ROOT / "scripts" / "generate_ai_thumbs.py")
        gat = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gat)
        img = gat.together_generate_image(prompt, key)
        if img:
            out_path.write_bytes(gat.resize_to_720p(img))
            print(f"    ✓ thumb → {out_path.name}")
            return True
        print(f"    ! thumb failed: API returned no image")
        return False
    except Exception as e:
        print(f"    ! thumb failed: {e}")
        return False


def render_video(video_id: str, lang: str, force: bool, dry_run: bool) -> Path | None:
    v       = VIDEOS[video_id]
    q       = {"en": QUEUE_EN, "ar": QUEUE_AR, "id": QUEUE_ID}[lang]
    stem    = f"sm{video_id}_{DATE_STR}" if lang == "en" else f"sm{video_id}_{DATE_STR}_{lang}"
    out     = q / f"{stem}.mp4"
    if out.exists() and not force:
        print(f"  [{lang.upper()}] skip {out.name}"); return out
    music   = LANG_MUSIC.get(video_id, {}).get(lang, v["props"]["musicFile"])
    props   = dict(v["props"], musicFile=music)
    print(f"\n  [{lang.upper()}] Rendering ep{video_id}: {v['name_en']} (music: {music})")
    if dry_run:
        print(f"    [DRY RUN] {v['comp']}"); return out
    q.mkdir(parents=True, exist_ok=True)
    cmd = ["npx", "remotion", "render", "src/index.ts", v["comp"],
           str(out), "--props", json.dumps(props),
           "--concurrency", "1", "--log", "error"]
    t0 = time.time()
    r  = subprocess.run(cmd, cwd=str(REMOTION), capture_output=True, text=True, timeout=21600)
    if r.returncode == 0 and out.exists():
        print(f"    ✓ {out.stat().st_size // 1024 // 1024} MB in {(time.time()-t0)/60:.0f} min")
        return out
    print(f"    ✗ FAILED: {r.stderr[-400:]}"); return None


def distribute(video_id: str, force: bool, dry_run: bool,
               allowed_langs: list[str] | None = None):
    all_langs = [("en", QUEUE_EN), ("ar", QUEUE_AR), ("id", QUEUE_ID)]
    for lang, q in [(l, q) for l, q in all_langs if allowed_langs is None or l in allowed_langs]:
        stem  = f"sm{video_id}_{DATE_STR}" if lang == "en" else f"sm{video_id}_{DATE_STR}_{lang}"
        mp4   = q / f"{stem}.mp4"
        # Render separately per language (different music → unique YT fingerprint)
        if not mp4.exists() or force:
            render_video(video_id, lang, force, dry_run)
        q.mkdir(parents=True, exist_ok=True)
        mpath = q / f"meta_{stem}.yaml"
        if not mpath.exists():
            if dry_run:
                print(f"    [DRY RUN] meta {lang.upper()}")
            else:
                with open(mpath, "w", encoding="utf-8") as f:
                    yaml.dump(make_meta(video_id, lang), f, allow_unicode=True,
                              default_flow_style=False, sort_keys=False)
                print(f"    meta {lang.upper()} → {mpath.name}")
        tp = q / f"thumb_{stem}.png"
        if not tp.exists() and not dry_run:
            time.sleep(0.5); generate_thumbnail(video_id, tp, lang)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--list",       action="store_true")
    parser.add_argument("--videos",     nargs="*")
    parser.add_argument("--dry-run",    action="store_true")
    parser.add_argument("--force",      action="store_true")
    parser.add_argument("--regen-meta", action="store_true")
    parser.add_argument("--queues",     nargs="+", choices=["en", "ar", "id"],
                        default=["en", "ar", "id"],
                        help="Which channel queues to render/distribute (default: all)")
    args = parser.parse_args()

    if args.list:
        for vid, v in VIDEOS.items():
            print(f"  ep{vid}  {v['name_en']:30s}  {v['comp']:20s}  {v['dur_label']}")
        return

    ids = list(VIDEOS) if not args.videos or args.videos == ["all"] else args.videos
    bad = [v for v in ids if v not in VIDEOS]
    if bad:
        print(f"Unknown episode IDs: {bad}"); sys.exit(1)

    print(f"=== Special Mechanics — {len(ids)} episodes ===\n")
    for vid in ids:
        print(f"[ep{vid}] {VIDEOS[vid]['name_en']}")
        distribute(vid, args.force, args.dry_run, args.queues)

    print("\n=== Done ===")


if __name__ == "__main__":
    main()
