#!/usr/bin/env python3
"""
Ocean Creatures Series — proper sprite-based videos replacing the old shape-only ocean/transport/profession videos.

Series 1: Ocean World (8 episodes — real ocean creature sprites)
Series 2: Sky & Nature (6 episodes — sun, moon, rainbow, butterfly, cloud, star)
Series 3: Vehicles (4 episodes — car, bus, rocket, balloon)

All use DanceSpriteLong composition. No text on screen → 3-channel distribution.

Usage:
  python3 scripts/generate_ocean_creatures.py --dry-run
  python3 scripts/generate_ocean_creatures.py --series ocean
  python3 scripts/generate_ocean_creatures.py --series sky
  python3 scripts/generate_ocean_creatures.py --series vehicles
  python3 scripts/generate_ocean_creatures.py --videos octopus whale
  python3 scripts/generate_ocean_creatures.py           # all series
"""
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml

ROOT      = Path(__file__).resolve().parent.parent
REMOTION  = ROOT / "remotion"
QUEUES    = {"en": ROOT / "output" / "queue",
             "ar": ROOT / "output" / "queue_ar",
             "id": ROOT / "output" / "queue_id"}
TOGETHER_KEY = (ROOT / "credentials" / "together_api_key.txt").read_text().strip()
DATE = datetime.now().strftime("%Y%m%d")

LANG_PHASE = {"en": 0.0, "ar": 0.33, "id": 0.67}

# ── Episode definitions ────────────────────────────────────────────────────────
# All use DanceSpriteLong. Sprites relative to remotion/public/sprites/.

VIDEOS = {
    # ── Ocean World ───────────────────────────────────────────────────────────
    "octopus": {
        "series": "ocean", "name_en": "Octopus", "name_ar": "أخطبوط", "name_id": "Gurita",
        "dur_min": 25,
        "props": {
            "bgColor": "#010818", "bgColorEnd": "#010514",
            "accentColor": "#CE93D8",
            "musicFile": "Gymnopedie No 1.mp3", "volume": 0.15,
            "bgEffect": "bubbles",
            "sprites": [
                {"path": "objects/octopus_3d.png", "size": 380, "posX": 0.50, "posY": 0.44, "seed": 1},
                {"path": "objects/octopus.png",    "size": 200, "posX": 0.18, "posY": 0.62, "seed": 2},
                {"path": "objects/octopus.png",    "size": 180, "posX": 0.82, "posY": 0.60, "seed": 3},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 180,  "motion": "FADEIN",  "amplitude": 50},
                {"startSec": 180,  "endSec": 600,  "motion": "BOB",     "period": 3.5, "amplitude": 55},
                {"startSec": 600,  "endSec": 1000, "motion": "SWAY",    "period": 4.0, "amplitude": 60},
                {"startSec": 1000, "endSec": 1400, "motion": "BOUNCE",  "period": 2.5, "amplitude": 80},
                {"startSec": 1400, "endSec": 1500, "motion": "BOB",     "period": 4.0, "amplitude": 40},
            ],
        },
        "thumb_prompt": "cute Pixar-style 3D purple octopus character with big friendly eyes and eight curly tentacles, soft glowing deep ocean background with floating bubbles, magical underwater atmosphere",
    },
    "jellyfish": {
        "series": "ocean", "name_en": "Jellyfish", "name_ar": "قنديل البحر", "name_id": "Ubur-ubur",
        "dur_min": 25,
        "props": {
            "bgColor": "#000B18", "bgColorEnd": "#000810",
            "accentColor": "#80DEEA",
            "musicFile": "Gymnopedie No 1.mp3", "volume": 0.14,
            "bgEffect": "bubbles",
            "sprites": [
                {"path": "objects/jellyfish_glow.png", "size": 360, "posX": 0.50, "posY": 0.40, "seed": 1},
                {"path": "objects/jellyfish_glow.png", "size": 200, "posX": 0.20, "posY": 0.64, "seed": 2},
                {"path": "objects/jellyfish_glow.png", "size": 180, "posX": 0.80, "posY": 0.62, "seed": 3},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 200,  "motion": "FADEIN",  "amplitude": 45},
                {"startSec": 200,  "endSec": 700,  "motion": "DRIFT",   "period": 8.0, "amplitude": 70},
                {"startSec": 700,  "endSec": 1200, "motion": "BOB",     "period": 5.0, "amplitude": 50},
                {"startSec": 1200, "endSec": 1500, "motion": "DRIFT",   "period": 10,  "amplitude": 60},
            ],
        },
        "thumb_prompt": "beautiful glowing Pixar-style 3D jellyfish with trailing tentacles, deep dark ocean, bioluminescent purple and teal glow, magical underwater world, dreamy and calming",
    },
    "whale": {
        "series": "ocean", "name_en": "Blue Whale", "name_ar": "الحوت الأزرق", "name_id": "Paus Biru",
        "dur_min": 25,
        "props": {
            "bgColor": "#000A1A", "bgColorEnd": "#000612",
            "accentColor": "#4FC3F7",
            "musicFile": "Gymnopedie No 1.mp3", "volume": 0.15,
            "bgEffect": "sparkles",
            "sprites": [
                {"path": "objects/blue_whale.png",  "size": 420, "posX": 0.50, "posY": 0.42, "seed": 1},
                {"path": "animals_3d/whale.png",    "size": 220, "posX": 0.22, "posY": 0.66, "seed": 2},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 200,  "motion": "FADEIN",  "amplitude": 40},
                {"startSec": 200,  "endSec": 700,  "motion": "SWAY",    "period": 6.0, "amplitude": 45},
                {"startSec": 700,  "endSec": 1200, "motion": "BOB",     "period": 4.0, "amplitude": 35},
                {"startSec": 1200, "endSec": 1500, "motion": "DRIFT",   "period": 12,  "amplitude": 55},
            ],
        },
        "thumb_prompt": "majestic cute Pixar-style 3D blue whale with kind eyes gliding through deep ocean, soft rays of light from above, gentle water bubbles, peaceful and calming baby visual",
    },
    "deep_fish": {
        "series": "ocean", "name_en": "Deep Sea Fish", "name_ar": "سمكة أعماق البحار", "name_id": "Ikan Laut Dalam",
        "dur_min": 25,
        "props": {
            "bgColor": "#000A14", "bgColorEnd": "#000810",
            "accentColor": "#00BCD4",
            "musicFile": "Morning Trail v2.mp3", "volume": 0.15,
            "bgEffect": "bubbles",
            "sprites": [
                {"path": "objects/fish_deep.png",   "size": 340, "posX": 0.50, "posY": 0.44, "seed": 1},
                {"path": "animals_3d/fish.png",     "size": 200, "posX": 0.20, "posY": 0.62, "seed": 2},
                {"path": "animals_3d/fish.png",     "size": 180, "posX": 0.80, "posY": 0.60, "seed": 3},
                {"path": "animals_3d/fish.png",     "size": 140, "posX": 0.60, "posY": 0.70, "seed": 4},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 150,  "motion": "FADEIN",  "amplitude": 50},
                {"startSec": 150,  "endSec": 550,  "motion": "BOUNCE",  "period": 2.0, "amplitude": 70},
                {"startSec": 550,  "endSec": 1000, "motion": "SWAY",    "period": 3.0, "amplitude": 55},
                {"startSec": 1000, "endSec": 1350, "motion": "BOUNCE",  "period": 1.8, "amplitude": 80},
                {"startSec": 1350, "endSec": 1500, "motion": "BOB",     "period": 3.5, "amplitude": 40},
            ],
        },
        "thumb_prompt": "colorful cute Pixar-style 3D tropical fish with big eyes swimming in a glowing deep sea, bioluminescent underwater plants, magical ocean depth, vivid colors on dark background",
    },
    "penguin": {
        "series": "ocean", "name_en": "Penguin", "name_ar": "البطريق", "name_id": "Penguin",
        "dur_min": 25,
        "props": {
            "bgColor": "#010C18", "bgColorEnd": "#010810",
            "accentColor": "#E3F2FD",
            "musicFile": "Moonlight on the Piano v2.mp3", "volume": 0.16,
            "bgEffect": "sparkles",
            "sprites": [
                {"path": "animals/penguin_3d.png", "size": 360, "posX": 0.50, "posY": 0.44, "seed": 1},
                {"path": "animals/penguin_3d.png", "size": 200, "posX": 0.20, "posY": 0.64, "seed": 2},
                {"path": "animals/penguin_3d.png", "size": 170, "posX": 0.80, "posY": 0.62, "seed": 3},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 160,  "motion": "FADEIN",  "amplitude": 50},
                {"startSec": 160,  "endSec": 550,  "motion": "BOUNCE",  "period": 1.8, "amplitude": 90},
                {"startSec": 550,  "endSec": 1000, "motion": "BOB",     "period": 2.5, "amplitude": 60},
                {"startSec": 1000, "endSec": 1350, "motion": "SWAY",    "period": 3.0, "amplitude": 55},
                {"startSec": 1350, "endSec": 1500, "motion": "BOB",     "period": 3.0, "amplitude": 45},
            ],
        },
        "thumb_prompt": "cute adorable Pixar-style 3D penguin character with big round eyes and fluffy belly, icy arctic background with soft snow and glowing northern lights, playful and charming baby video",
    },
    # ── Sky & Nature ──────────────────────────────────────────────────────────
    "sun": {
        "series": "sky", "name_en": "Happy Sun", "name_ar": "الشمس السعيدة", "name_id": "Matahari Bahagia",
        "dur_min": 25,
        "props": {
            "bgColor": "#050800", "bgColorEnd": "#030500",
            "accentColor": "#FDD835",
            "musicFile": "Spring Waltz v2.mp3", "volume": 0.18,
            "bgEffect": "sparkles",
            "sprites": [
                {"path": "objects/sun_3d.png",      "size": 400, "posX": 0.50, "posY": 0.42, "seed": 1},
                {"path": "objects/cloud_3d.png",    "size": 200, "posX": 0.18, "posY": 0.28, "seed": 2},
                {"path": "objects/cloud_3d.png",    "size": 180, "posX": 0.82, "posY": 0.30, "seed": 3},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 160,  "motion": "FADEIN",  "amplitude": 50},
                {"startSec": 160,  "endSec": 600,  "motion": "BOB",     "period": 3.0, "amplitude": 45},
                {"startSec": 600,  "endSec": 1100, "motion": "ORBIT",   "period": 10,  "amplitude": 80},
                {"startSec": 1100, "endSec": 1500, "motion": "BOB",     "period": 3.5, "amplitude": 50},
            ],
        },
        "thumb_prompt": "cute happy Pixar-style 3D sun character with a big warm smile and golden rays, fluffy white clouds on bright blue sky, cheerful baby animation",
    },
    "rainbow": {
        "series": "sky", "name_en": "Rainbow", "name_ar": "قوس قزح", "name_id": "Pelangi",
        "dur_min": 25,
        "props": {
            "bgColor": "#020510", "bgColorEnd": "#010408",
            "accentColor": "#FF7043",
            "musicFile": "Rainbow Lantern v2.mp3", "volume": 0.17,
            "bgEffect": "sparkles",
            "sprites": [
                {"path": "objects/rainbow_3d.png",  "size": 440, "posX": 0.50, "posY": 0.38, "seed": 1},
                {"path": "objects/star_3d.png",     "size": 140, "posX": 0.15, "posY": 0.68, "seed": 2},
                {"path": "objects/star_3d.png",     "size": 120, "posX": 0.85, "posY": 0.70, "seed": 3},
                {"path": "objects/star_3d.png",     "size": 100, "posX": 0.50, "posY": 0.76, "seed": 4},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 180,  "motion": "FADEIN",  "amplitude": 50},
                {"startSec": 180,  "endSec": 650,  "motion": "BOB",     "period": 4.0, "amplitude": 40},
                {"startSec": 650,  "endSec": 1150, "motion": "SWAY",    "period": 5.0, "amplitude": 50},
                {"startSec": 1150, "endSec": 1500, "motion": "BOB",     "period": 4.5, "amplitude": 35},
            ],
        },
        "thumb_prompt": "beautiful vivid Pixar-style 3D rainbow arc with all colors glowing against a dark magical sky, golden stars below it, dreamy and enchanting baby visual",
    },
    "butterfly": {
        "series": "sky", "name_en": "Butterfly", "name_ar": "الفراشة", "name_id": "Kupu-kupu",
        "dur_min": 25,
        "props": {
            "bgColor": "#030A04", "bgColorEnd": "#020804",
            "accentColor": "#80CBC4",
            "musicFile": "Afternoon in F v2.mp3", "volume": 0.16,
            "bgEffect": "sparkles",
            "sprites": [
                {"path": "objects/butterfly_3d.png","size": 360, "posX": 0.50, "posY": 0.42, "seed": 1},
                {"path": "objects/blue_butterfly.png","size":200, "posX": 0.20, "posY": 0.62, "seed": 2},
                {"path": "objects/blue_butterfly.png","size":180, "posX": 0.78, "posY": 0.60, "seed": 3},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 150,  "motion": "FADEIN",  "amplitude": 50},
                {"startSec": 150,  "endSec": 600,  "motion": "SWAY",    "period": 3.0, "amplitude": 70},
                {"startSec": 600,  "endSec": 1100, "motion": "ORBIT",   "period": 7.0, "amplitude": 110},
                {"startSec": 1100, "endSec": 1500, "motion": "SWAY",    "period": 3.5, "amplitude": 65},
            ],
        },
        "thumb_prompt": "beautiful cute Pixar-style 3D butterfly with iridescent blue and purple wings, gently fluttering in a magical garden with soft green and teal glow, enchanting baby video",
    },
    "star": {
        "series": "sky", "name_en": "Twinkling Stars", "name_ar": "النجوم المتلألئة", "name_id": "Bintang Berkelip",
        "dur_min": 25,
        "props": {
            "bgColor": "#010308", "bgColorEnd": "#010206",
            "accentColor": "#FFF9C4",
            "musicFile": "Gymnopedie No 1.mp3", "volume": 0.14,
            "bgEffect": "sparkles",
            "sprites": [
                {"path": "objects/star_3d.png",      "size": 340, "posX": 0.50, "posY": 0.40, "seed": 1},
                {"path": "objects/star_silver.png",  "size": 200, "posX": 0.20, "posY": 0.26, "seed": 2},
                {"path": "objects/star.png",         "size": 180, "posX": 0.80, "posY": 0.28, "seed": 3},
                {"path": "objects/star_silver.png",  "size": 150, "posX": 0.14, "posY": 0.64, "seed": 4},
                {"path": "objects/star.png",         "size": 140, "posX": 0.86, "posY": 0.66, "seed": 5},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 180,  "motion": "FADEIN",  "amplitude": 40},
                {"startSec": 180,  "endSec": 700,  "motion": "BOB",     "period": 4.5, "amplitude": 45},
                {"startSec": 700,  "endSec": 1200, "motion": "ORBIT",   "period": 12,  "amplitude": 80},
                {"startSec": 1200, "endSec": 1500, "motion": "BOB",     "period": 5.0, "amplitude": 38},
            ],
        },
        "thumb_prompt": "magical glowing golden and silver stars twinkling in a deep dark blue night sky, one giant central star with smaller ones around it, soft sparkles, peaceful baby sleep visual",
    },
    # ── Vehicles ──────────────────────────────────────────────────────────────
    "car": {
        "series": "vehicles", "name_en": "Red Car", "name_ar": "السيارة الحمراء", "name_id": "Mobil Merah",
        "dur_min": 25,
        "props": {
            "bgColor": "#0A0200", "bgColorEnd": "#080100",
            "accentColor": "#EF5350",
            "musicFile": "Morning Trail.mp3", "volume": 0.17,
            "bgEffect": "sparkles",
            "sprites": [
                {"path": "objects/car_3d.png",      "size": 400, "posX": 0.50, "posY": 0.46, "seed": 1},
                {"path": "objects/car.png",         "size": 200, "posX": 0.18, "posY": 0.62, "seed": 2},
                {"path": "objects/car.png",         "size": 180, "posX": 0.82, "posY": 0.62, "seed": 3},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 150,  "motion": "FADEIN",  "amplitude": 50},
                {"startSec": 150,  "endSec": 550,  "motion": "BOUNCE",  "period": 1.8, "amplitude": 70},
                {"startSec": 550,  "endSec": 1000, "motion": "SWAY",    "period": 3.0, "amplitude": 60},
                {"startSec": 1000, "endSec": 1350, "motion": "BOUNCE",  "period": 2.0, "amplitude": 80},
                {"startSec": 1350, "endSec": 1500, "motion": "BOB",     "period": 3.0, "amplitude": 45},
            ],
        },
        "thumb_prompt": "cute shiny Pixar-style 3D red car with big headlight eyes and a friendly smile, bright colorful background, cheerful baby animation, cartoon vehicle for toddlers",
    },
    "balloon": {
        "series": "vehicles", "name_en": "Hot Air Balloon", "name_ar": "منطاد الهواء الساخن", "name_id": "Balon Udara",
        "dur_min": 25,
        "props": {
            "bgColor": "#020510", "bgColorEnd": "#010408",
            "accentColor": "#FF9800",
            "musicFile": "The Golden Meadow v2.mp3", "volume": 0.17,
            "bgEffect": "sparkles",
            "sprites": [
                {"path": "objects/balloon_3d.png",  "size": 380, "posX": 0.50, "posY": 0.40, "seed": 1},
                {"path": "objects/balloon.png",     "size": 200, "posX": 0.18, "posY": 0.32, "seed": 2},
                {"path": "objects/balloon.png",     "size": 180, "posX": 0.80, "posY": 0.34, "seed": 3},
                {"path": "objects/cloud_3d.png",    "size": 160, "posX": 0.50, "posY": 0.70, "seed": 4},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 180,  "motion": "FADEIN",  "amplitude": 50},
                {"startSec": 180,  "endSec": 650,  "motion": "BOB",     "period": 4.0, "amplitude": 60},
                {"startSec": 650,  "endSec": 1150, "motion": "DRIFT",   "period": 8.0, "amplitude": 80},
                {"startSec": 1150, "endSec": 1500, "motion": "BOB",     "period": 4.5, "amplitude": 55},
            ],
        },
        "thumb_prompt": "colorful cute Pixar-style 3D hot air balloon floating high in a magical night sky with glowing stars, vivid rainbow colors on the balloon, dreamy and cheerful baby visual",
    },
}

ALL_SERIES = {"ocean", "sky", "vehicles"}
SERIES_NAMES = {
    "ocean":    {"en": "Ocean World",     "ar": "عالم المحيط",    "id": "Dunia Lautan"},
    "sky":      {"en": "Sky & Nature",    "ar": "السماء والطبيعة", "id": "Langit & Alam"},
    "vehicles": {"en": "On the Move",     "ar": "على الطريق",     "id": "Di Jalan Raya"},
}


# ── Titles ─────────────────────────────────────────────────────────────────────
def make_title(v: dict, lang: str) -> str:
    name = {"en": v["name_en"], "ar": v["name_ar"], "id": v["name_id"]}[lang]
    series_n = SERIES_NAMES[v["series"]][lang]
    dur = v["dur_min"]
    if lang == "en":
        return f"{name} — {series_n} | {dur} min Baby Visual | Happy Bear Kids"
    elif lang == "ar":
        return f"{name} — {series_n} | {dur} دقيقة | هابي بير كيدز"
    else:
        return f"{name} — {series_n} | {dur} Menit Bayi | Happy Bear Kids"


# ── Descriptions ───────────────────────────────────────────────────────────────
def make_desc(v: dict, lang: str) -> str:
    name_en = v["name_en"]
    series_en = SERIES_NAMES[v["series"]]["en"]
    title = make_title(v, lang)

    if lang == "en":
        return f"""{title}

25 minutes of beautiful, calming animation featuring {name_en.lower()} — designed for babies and toddlers aged 0–3 years. Smooth movements, vivid colors and soft music create the perfect gentle visual experience.

Part of the {series_en} series — carefully designed content that engages young minds through beautiful visuals without any language barriers.

🎯 Perfect for: visual stimulation, sensory development, calm background TV
👶 Age: 0–3 years | 📺 {v["dur_min"]} min continuous
🌈 Universal — works for any culture or language

🌟 Benefits for baby development:
• Visual tracking as the character moves gently and predictably
• Color recognition through vivid, high-contrast imagery
• Sensory stimulation and regulation
• Attention and focus through simple, predictable animation
• Emotional bonding through engaging and friendly character design

No text, no voices, no sudden changes — just pure visual joy for your little one.

🎵 Original music by Happy Bear Kids (AI-generated, © 2026)

© Happy Bear Kids 2026 — All rights reserved
New videos every week! Subscribe → @HappyBearKids1

#HappyBearKids #{name_en.replace(' ','')} #{series_en.replace(' ','')} #BabyVisual #ToddlerCalm #BabySensory #25Minutes #NoTalking #BabyAnimation #CalmBaby"""
    elif lang == "ar":
        name_ar = v["name_ar"]
        series_ar = SERIES_NAMES[v["series"]]["ar"]
        return f"""{title}

25 دقيقة من الرسوم المتحركة الجميلة والهادئة مع {name_ar} — مصممة للأطفال الرضع والصغار من عمر 0 إلى 3 سنوات.

🎯 مثالية لـ: التحفيز البصري، التطور الحسي، التلفزيون الهادئ في الخلفية
👶 العمر: 0–3 سنوات | 📺 {v["dur_min"]} دقيقة متواصلة
🌈 عالمية — مناسبة لجميع الثقافات واللغات

🌟 فوائد لتطور الطفل:
• تدريب التتبع البصري مع حركة الشخصية السلسة والمتوقعة
• التعرف على الألوان من خلال الصور الزاهية عالية التباين
• التحفيز الحسي والتنظيم
• الانتباه والتركيز من خلال الرسوم المتحركة البسيطة والمتوقعة

لا نص، لا أصوات، لا تغييرات مفاجئة — فقط متعة بصرية خالصة لطفلك الصغير.

© هابي بير كيدز 2026 — جميع الحقوق محفوظة
اشترك → @happybearkidsar

#هابي_بير_كيدز #{name_ar} #{series_ar} #فيديو_الرضع #هدوء_الأطفال #25_دقيقة #بدون_كلام"""
    else:
        name_id = v["name_id"]
        series_id = SERIES_NAMES[v["series"]]["id"]
        return f"""{title}

25 menit animasi yang indah dan menenangkan dengan {name_id.lower()} — dirancang untuk bayi dan balita usia 0–3 tahun.

🎯 Sempurna untuk: stimulasi visual, perkembangan sensori, TV latar lembut
👶 Usia: 0–3 tahun | 📺 {v["dur_min"]} menit terus menerus
🌈 Universal — cocok untuk semua budaya dan bahasa

🌟 Manfaat untuk perkembangan bayi:
• Latihan pelacakan visual dengan gerakan karakter yang lembut
• Pengenalan warna melalui gambar yang vivid dan kontras tinggi
• Stimulasi dan regulasi sensori
• Perhatian dan fokus melalui animasi yang sederhana

Tidak ada teks, tidak ada suara, tidak ada perubahan mendadak — hanya kesenangan visual murni untuk si kecil.

🎵 Original music by Happy Bear Kids (AI-generated, © 2026)

© Happy Bear Kids 2026 — Semua hak dilindungi
Berlangganan → @happybearkidsin

#HappyBearKids #{name_id.replace(' ','')} #{series_id.replace(' ','')} #VideoBalita #TenangBayi #25Menit"""


# ── Render ─────────────────────────────────────────────────────────────────────
def render_video(key: str, v: dict, lang: str, dry_run: bool) -> Path | None:
    queue = QUEUES[lang]
    lang_sfx = "" if lang == "en" else f"_{lang}"
    out = queue / f"{key}{lang_sfx}_{DATE}.mp4"

    if out.exists():
        print(f"  [{lang.upper()}] already exists: {out.name}")
        return out

    dur_frames = v["dur_min"] * 60 * 30  # 30fps
    props = dict(v["props"])
    props["phaseOffset"] = LANG_PHASE[lang]

    cmd = [
        "npx", "remotion", "render",
        "src/index.ts", "DanceSpriteLong",
        str(out),
        "--props", json.dumps(props),
        "--frames", f"0-{dur_frames - 1}",
        "--concurrency", "1",
    ]

    print(f"  [{lang.upper()}] Rendering {out.name} ...")
    if dry_run:
        print(f"    [DRY RUN] {' '.join(cmd[:6])} ...")
        return out

    result = subprocess.run(cmd, cwd=REMOTION, capture_output=False)
    if result.returncode != 0:
        print(f"  [{lang.upper()}] RENDER FAILED")
        return None
    return out


# ── Thumbnail ──────────────────────────────────────────────────────────────────
def gen_thumb(key: str, v: dict, lang: str, out_path: Path, dry_run: bool) -> bool:
    if out_path.exists():
        print(f"  [{lang.upper()}] thumb exists")
        return True
    prompt = v["thumb_prompt"]
    if lang == "ar":
        prompt += ", no text, no letters, no words, no numbers, no watermarks"
    else:
        prompt += ", Pixar 3D style, vibrant colors, 16:9 format 1280x720"

    print(f"  [{lang.upper()}] generating thumb...")
    if dry_run:
        print(f"    [DRY RUN] {prompt[:80]}")
        return True

    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("gat", ROOT / "scripts" / "generate_ai_thumbs.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        img = mod.together_generate_image(prompt, TOGETHER_KEY)
        if img:
            out_path.write_bytes(mod.resize_to_720p(img))
            print(f"    ✓ thumb saved")
            return True
        print(f"    ✗ thumb: API returned no image")
        return False
    except Exception as e:
        print(f"    ✗ thumb failed: {e}")
        return False


# ── Meta ───────────────────────────────────────────────────────────────────────
def write_meta(key: str, v: dict, lang: str, queue: Path, dry_run: bool) -> None:
    lang_sfx = "" if lang == "en" else f"_{lang}"
    meta_path = queue / f"meta_{key}{lang_sfx}_{DATE}.yaml"
    if meta_path.exists():
        return
    meta = {
        "title":       make_title(v, lang),
        "description": make_desc(v, lang),
        "tags": [v["name_en"].lower(), v["series"], "baby visual", "happy bear kids",
                 "toddler", "baby sensory", "no talking", f"{v['dur_min']} minutes",
                 "calming baby", SERIES_NAMES[v["series"]]["en"].lower()],
        "video_type":  v["series"] if v["series"] in ("ocean", "sky") else "dance",
        "language":    lang,
        "duration_minutes": v["dur_min"],
        "is_short":    False,
        "status":      "public",
    }
    if dry_run:
        print(f"  [{lang.upper()}] [DRY RUN] meta: {meta['title'][:60]}")
        return
    meta_path.write_text(yaml.dump(meta, allow_unicode=True, sort_keys=False))
    print(f"  [{lang.upper()}] meta written")


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run",   action="store_true")
    parser.add_argument("--series",    choices=list(ALL_SERIES) + ["all"], default="all")
    parser.add_argument("--videos",    nargs="+", help="Specific video keys")
    parser.add_argument("--regen-meta",action="store_true", help="Only regenerate meta+thumb")
    args = parser.parse_args()

    if args.videos:
        targets = {k: v for k, v in VIDEOS.items() if k in args.videos}
    elif args.series == "all":
        targets = VIDEOS
    else:
        targets = {k: v for k, v in VIDEOS.items() if v["series"] == args.series}

    print(f"Processing {len(targets)} video(s) across 3 channels...")

    for key, v in targets.items():
        print(f"\n{'='*60}")
        print(f"[{v['series'].upper()}] {key}: {v['name_en']}")

        for lang in ("en", "ar", "id"):
            queue = QUEUES[lang]
            lang_sfx = "" if lang == "en" else f"_{lang}"
            mp4_path   = queue / f"{key}{lang_sfx}_{DATE}.mp4"
            thumb_path = queue / f"thumb_{key}{lang_sfx}_{DATE}.png"

            if not args.regen_meta:
                mp4 = render_video(key, v, lang, args.dry_run)
                if not mp4 and not args.dry_run:
                    print(f"  [{lang.upper()}] skipping meta/thumb — render failed")
                    continue

            write_meta(key, v, lang, queue, args.dry_run)
            gen_thumb(key, v, lang, thumb_path, args.dry_run)
            time.sleep(0.5)

    print("\nDone!")


if __name__ == "__main__":
    main()
