#!/usr/bin/env python3
"""
generate_emotions_ocean.py — Series 3–6: Emotions + Ocean + Transport + Professions
All A-versions (no text → EN + AR + ID). ~25 episodes × 3 channels.

Series 3  Emotions (6)  — DanceSpriteLong with emotion sprites
Series 4  Ocean    (6)  — DanceSpriteLong/DanceShapeLong ocean creatures
Series 5  Transport (5) — DanceShapeLong / DanceSpriteLong (balloon)
Series 6  Professions(8)— DanceShapeLong with occupation-themed colors

Usage:
  python3 scripts/generate_emotions_ocean.py --list
  python3 scripts/generate_emotions_ocean.py --videos all [--dry-run] [--force]
  python3 scripts/generate_emotions_ocean.py --videos e_happy o_whale t_balloon
  python3 scripts/generate_emotions_ocean.py --series emotions
  python3 scripts/generate_emotions_ocean.py --regen-meta
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

# All available tracks — for picking per-language alternates (avoids YT duplicate fingerprinting)
# All available Suno instrumental tracks — for per-language alternates
_ALL_TRACKS = [
    "Afternoon in F v2.mp3", "Rain Etude in C Minor v2.mp3", "Spring Waltz v2.mp3",
    "Spring Waltz.mp3", "Morning Trail v2.mp3", "Morning Trail.mp3",
    "The Glass Forest v2.mp3", "Rainbow Lantern v2.mp3", "Rainbow Lantern.mp3",
    "Tide and Piano v2.mp3", "Tide and Piano.mp3", "Moonlight Waltz.mp3",
    "Dreamy Arpeggios v2.mp3", "Moonlight on the Cradle v2.mp3",
    "The Golden Meadow v2.mp3", "The Golden Meadow.mp3", "Moonlight on the Piano v2.mp3",
]

def alt_music(en_music: str, ep_idx: int, lang: str) -> str:
    """Return a track different from en_music. AR offset=7, ID offset=14 in the pool."""
    offset = 7 if lang == "ar" else 14
    pool = [t for t in _ALL_TRACKS if t != en_music]
    return pool[(ep_idx + offset) % len(pool)]

SERIES_EN = {"emotions": "Emotions with Roundy", "ocean": "Ocean World",
             "transport": "Let's Go! Transport", "professions": "People Who Help Us"}
SERIES_AR = {"emotions": "مشاعر مع روندي", "ocean": "عالم المحيط",
             "transport": "هيا نمشي! المواصلات", "professions": "الناس الذين يساعدوننا"}
SERIES_ID = {"emotions": "Emosi bersama Roundy", "ocean": "Dunia Laut",
             "transport": "Ayo Jalan! Transportasi", "professions": "Orang-orang yang Membantu Kita"}

VIDEOS = {
    # ── SERIES 3: EMOTIONS ────────────────────────────────────────────────────
    "e_happy": {
        "name_en": "Happy",  "name_ar": "سعيد",  "name_id": "Senang",
        "series": "emotions", "comp": "DanceSpriteLong", "dur_label": "25 min",
        "props": {
            "bgColor": "#1A1000", "bgColorEnd": "#0A0800",
            "accentColor": "#FFD700",
            "musicFile": "Afternoon in F v2.mp3", "volume": 0.20,
            "bgEffect": "sparkles",
            "sprites": [
                {"path": "emotions/happy_3d.png", "size": 380, "posX": 0.50, "posY": 0.44, "seed": 1},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 150,  "motion": "FADEIN",  "amplitude": 60, "wobble": True},
                {"startSec": 150,  "endSec": 500,  "motion": "BOB",     "period": 2.5,  "amplitude": 55, "wobble": True},
                {"startSec": 500,  "endSec": 850,  "motion": "BOUNCE",  "period": 2.0,  "amplitude": 100, "wobble": True},
                {"startSec": 850,  "endSec": 1200, "motion": "SWAY",    "period": 3.0,  "amplitude": 60, "wobble": True},
                {"startSec": 1200, "endSec": 1500, "motion": "BOB",     "period": 3.0,  "amplitude": 45, "wobble": True},
            ],
        },
    },
    "e_sad": {
        "name_en": "Sad",    "name_ar": "حزين",  "name_id": "Sedih",
        "series": "emotions", "comp": "DanceSpriteLong", "dur_label": "25 min",
        "props": {
            "bgColor": "#020510", "bgColorEnd": "#010408",
            "accentColor": "#64B5F6",
            "musicFile": "Rain Etude in C Minor v2.mp3", "volume": 0.14,
            "bgEffect": "none",
            "sprites": [
                {"path": "emotions/sad_3d.png", "size": 360, "posX": 0.50, "posY": 0.46, "seed": 1},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 200,  "motion": "FADEIN",  "amplitude": 30, "wobble": True},
                {"startSec": 200,  "endSec": 700,  "motion": "BOB",     "period": 6.0,  "amplitude": 18, "wobble": True},
                {"startSec": 700,  "endSec": 1200, "motion": "DRIFT",   "period": 14,   "amplitude": 70, "wobble": True},
                {"startSec": 1200, "endSec": 1500, "motion": "BOB",     "period": 7.0,  "amplitude": 15, "wobble": True},
            ],
        },
    },
    "e_surprised": {
        "name_en": "Surprised", "name_ar": "مندهش", "name_id": "Terkejut",
        "series": "emotions", "comp": "DanceSpriteLong", "dur_label": "25 min",
        "props": {
            "bgColor": "#0A0515", "bgColorEnd": "#050210",
            "accentColor": "#AB47BC",
            "musicFile": "Spring Waltz v2.mp3", "volume": 0.18,
            "bgEffect": "sparkles",
            "sprites": [
                {"path": "emotions/surprised_3d.png", "size": 370, "posX": 0.50, "posY": 0.44, "seed": 1},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 150,  "motion": "FADEIN",  "amplitude": 60, "wobble": True},
                {"startSec": 150,  "endSec": 500,  "motion": "BOUNCE",  "period": 2.0,  "amplitude": 120, "wobble": True},
                {"startSec": 500,  "endSec": 900,  "motion": "SWAY",    "period": 2.5,  "amplitude": 70, "wobble": True},
                {"startSec": 900,  "endSec": 1200, "motion": "BOUNCE",  "period": 2.5,  "amplitude": 90, "wobble": True},
                {"startSec": 1200, "endSec": 1500, "motion": "BOB",     "period": 4.0,  "amplitude": 40, "wobble": True},
            ],
        },
    },
    "e_angry": {
        "name_en": "Angry",  "name_ar": "غاضب",  "name_id": "Marah",
        "series": "emotions", "comp": "DanceSpriteLong", "dur_label": "25 min",
        "props": {
            "bgColor": "#120200", "bgColorEnd": "#0A0100",
            "accentColor": "#EF5350",
            "musicFile": "Morning Trail v2.mp3", "volume": 0.17,
            "bgEffect": "none",
            "sprites": [
                {"path": "emotions/angry_3d.png", "size": 370, "posX": 0.50, "posY": 0.44, "seed": 1},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 150,  "motion": "FADEIN",  "amplitude": 60, "wobble": True},
                {"startSec": 150,  "endSec": 500,  "motion": "BOUNCE",  "period": 1.8,  "amplitude": 80, "wobble": True},
                {"startSec": 500,  "endSec": 900,  "motion": "SWAY",    "period": 2.0,  "amplitude": 90, "wobble": True},
                {"startSec": 900,  "endSec": 1200, "motion": "BOUNCE",  "period": 2.2,  "amplitude": 70, "wobble": True},
                {"startSec": 1200, "endSec": 1500, "motion": "BOB",     "period": 5.0,  "amplitude": 30, "wobble": True},
            ],
        },
    },
    "e_scared": {
        "name_en": "Scared", "name_ar": "خائف",  "name_id": "Takut",
        "series": "emotions", "comp": "DanceSpriteLong", "dur_label": "25 min",
        "props": {
            "bgColor": "#010508", "bgColorEnd": "#010305",
            "accentColor": "#78909C",
            "musicFile": "The Glass Forest v2.mp3", "volume": 0.14,
            "bgEffect": "none",
            "sprites": [
                {"path": "emotions/scared_3d.png", "size": 360, "posX": 0.50, "posY": 0.44, "seed": 1},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 180,  "motion": "FADEIN",  "amplitude": 40, "wobble": True},
                {"startSec": 180,  "endSec": 600,  "motion": "PULSE",   "period": 2.5,  "amplitude": 18, "wobble": True},
                {"startSec": 600,  "endSec": 1100, "motion": "SWAY",    "period": 1.8,  "amplitude": 40, "wobble": True},
                {"startSec": 1100, "endSec": 1500, "motion": "BOB",     "period": 6.0,  "amplitude": 20, "wobble": True},
            ],
        },
    },
    "e_love": {
        "name_en": "Love",   "name_ar": "حب",    "name_id": "Cinta",
        "series": "emotions", "comp": "DanceSpriteLong", "dur_label": "25 min",
        "props": {
            "bgColor": "#120010", "bgColorEnd": "#0A000A",
            "accentColor": "#E91E63",
            "musicFile": "Rainbow Lantern v2.mp3", "volume": 0.16,
            "bgEffect": "sparkles",
            "sprites": [
                {"path": "emotions/love_3d.png",  "size": 340, "posX": 0.38, "posY": 0.44, "seed": 1},
                {"path": "emotions/happy_3d.png", "size": 220, "posX": 0.70, "posY": 0.50, "seed": 2},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 180,  "motion": "FADEIN",  "amplitude": 60, "wobble": True},
                {"startSec": 180,  "endSec": 600,  "motion": "BOB",     "period": 3.5,  "amplitude": 45, "wobble": True},
                {"startSec": 600,  "endSec": 1000, "motion": "ORBIT",   "period": 8.0,  "amplitude": 120, "wobble": True},
                {"startSec": 1000, "endSec": 1500, "motion": "BOB",     "period": 4.0,  "amplitude": 40, "wobble": True},
            ],
        },
    },

    # ── SERIES 4: OCEAN ──────────────────────────────────────────────────────
    "o_whale": {
        "name_en": "Whale",       "name_ar": "حوت",            "name_id": "Paus",
        "series": "ocean", "comp": "DanceSpriteLong", "dur_label": "25 min",
        "props": {
            "bgColor": "#010810", "bgColorEnd": "#010608",
            "accentColor": "#29B6F6",
            "musicFile": "Tide and Piano v2.mp3", "volume": 0.16,
            "bgEffect": "bubbles",
            "sprites": [
                {"path": "animals_3d/whale.png", "size": 480, "posX": 0.50, "posY": 0.46, "seed": 1},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 200,  "motion": "FADEIN",  "amplitude": 40, "wobble": True},
                {"startSec": 200,  "endSec": 700,  "motion": "WAVE",    "period": 6.0,  "amplitude": 50,  "waveDelay": 0, "wobble": True},
                {"startSec": 700,  "endSec": 1100, "motion": "BOB",     "period": 8.0,  "amplitude": 80, "wobble": True},
                {"startSec": 1100, "endSec": 1500, "motion": "DRIFT",   "period": 18,   "amplitude": 90, "wobble": True},
            ],
        },
    },
    "o_octopus": {
        "name_en": "Octopus",     "name_ar": "أخطبوط",         "name_id": "Gurita",
        "series": "ocean", "comp": "DanceSpriteLong", "dur_label": "25 min",
        "props": {
            "bgColor": "#020306", "bgColorEnd": "#010205",
            "accentColor": "#7E57C2",
            "musicFile": "Moonlight Waltz.mp3", "volume": 0.15,
            "bgEffect": "bubbles",
            "sprites": [
                {"path": "objects/octopus_3d.png", "size": 400, "posX": 0.50, "posY": 0.46, "seed": 1},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 180,  "motion": "FADEIN",  "amplitude": 50, "wobble": True},
                {"startSec": 180,  "endSec": 600,  "motion": "SWAY",    "period": 3.0,  "amplitude": 45, "wobble": True},
                {"startSec": 600,  "endSec": 1000, "motion": "PULSE",   "period": 4.0,  "amplitude": 15, "wobble": True},
                {"startSec": 1000, "endSec": 1500, "motion": "DRIFT",   "period": 12,   "amplitude": 80, "wobble": True},
            ],
        },
    },
    "o_fish": {
        "name_en": "Fish",        "name_ar": "سمكة",           "name_id": "Ikan",
        "series": "ocean", "comp": "DanceSpriteLong", "dur_label": "25 min",
        "props": {
            "bgColor": "#010A12", "bgColorEnd": "#010810",
            "accentColor": "#4FC3F7",
            "musicFile": "Dreamy Arpeggios v2.mp3", "volume": 0.15,
            "bgEffect": "bubbles",
            "sprites": [
                {"path": "animals_3d/fish.png", "size": 280, "posX": 0.25, "posY": 0.40, "seed": 1},
                {"path": "animals_3d/fish.png", "size": 200, "posX": 0.65, "posY": 0.50, "seed": 2},
                {"path": "animals_3d/fish.png", "size": 160, "posX": 0.80, "posY": 0.35, "seed": 3},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 180,  "motion": "FADEIN",  "amplitude": 60, "wobble": True},
                {"startSec": 180,  "endSec": 600,  "motion": "DRIFT",   "period": 8.0,  "amplitude": 100, "wobble": True},
                {"startSec": 600,  "endSec": 1100, "motion": "WAVE",    "period": 4.0,  "amplitude": 60,  "waveDelay": 0.8, "wobble": True},
                {"startSec": 1100, "endSec": 1500, "motion": "DRIFT",   "period": 10,   "amplitude": 120, "wobble": True},
            ],
        },
    },
    "o_dolphin": {
        "name_en": "Dolphin",     "name_ar": "دلفين",          "name_id": "Lumba-lumba",
        "series": "ocean", "comp": "DanceShapeLong", "dur_label": "25 min",
        "props": {
            "bgColor": "#011020",
            "musicFile": "Morning Trail v2.mp3", "volume": 0.18,
            "shapes": [
                {"shape": "oval",    "color": "#5C9ED9", "size": 280, "posX": 0.30, "posY": 0.42, "seed": 1},
                {"shape": "oval",    "color": "#4A8EC4", "size": 250, "posX": 0.65, "posY": 0.46, "seed": 2},
                {"shape": "diamond", "color": "#80C8F0", "size": 120, "posX": 0.48, "posY": 0.32, "seed": 3},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 150,  "motion": "FADEIN",  "amplitude": 60},
                {"startSec": 150,  "endSec": 600,  "motion": "BOUNCE",  "period": 2.5,  "amplitude": 130},
                {"startSec": 600,  "endSec": 1000, "motion": "ORBIT",   "period": 6.0,  "amplitude": 200},
                {"startSec": 1000, "endSec": 1300, "motion": "SWAY",    "period": 3.0,  "amplitude": 80},
                {"startSec": 1300, "endSec": 1500, "motion": "BOB",     "period": 5.0,  "amplitude": 40},
            ],
        },
    },
    "o_jellyfish": {
        "name_en": "Jellyfish",   "name_ar": "قنديل البحر",   "name_id": "Ubur-ubur",
        "series": "ocean", "comp": "DanceShapeLong", "dur_label": "25 min",
        "props": {
            "bgColor": "#010508",
            "musicFile": "Dreamy Arpeggios v2.mp3", "volume": 0.14,
            "shapes": [
                {"shape": "circle",  "color": "#80DEEA", "size": 240, "posX": 0.30, "posY": 0.36, "seed": 1, "colorOffset": 0.00},
                {"shape": "circle",  "color": "#CE93D8", "size": 210, "posX": 0.65, "posY": 0.34, "seed": 2, "colorOffset": 0.33},
                {"shape": "circle",  "color": "#A5D6A7", "size": 180, "posX": 0.50, "posY": 0.55, "seed": 3, "colorOffset": 0.67},
                {"shape": "diamond", "color": "#4FC3F7", "size": 110, "posX": 0.18, "posY": 0.62, "seed": 4, "colorOffset": 0.15},
                {"shape": "diamond", "color": "#BA68C8", "size": 100, "posX": 0.82, "posY": 0.60, "seed": 5, "colorOffset": 0.50},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 200,  "motion": "FADEIN", "amplitude": 40},
                {"startSec": 200,  "endSec": 800,  "motion": "PULSE",  "period": 5.0,  "amplitude": 12},
                {"startSec": 800,  "endSec": 1300, "motion": "DRIFT",  "period": 16,   "amplitude": 70},
                {"startSec": 1300, "endSec": 1500, "motion": "PULSE",  "period": 6.0,  "amplitude": 10},
            ],
        },
    },
    "o_starfish": {
        "name_en": "Starfish",    "name_ar": "نجمة البحر",    "name_id": "Bintang Laut",
        "series": "ocean", "comp": "DanceShapeLong", "dur_label": "25 min",
        "props": {
            "bgColor": "#040A08",
            "musicFile": "Moonlight on the Cradle v2.mp3", "volume": 0.14,
            "shapes": [
                {"shape": "star",   "color": "#FF7043", "size": 280, "posX": 0.50, "posY": 0.44, "seed": 1},
                {"shape": "star",   "color": "#FF8A65", "size": 160, "posX": 0.20, "posY": 0.60, "seed": 2},
                {"shape": "star",   "color": "#FFAB91", "size": 140, "posX": 0.78, "posY": 0.62, "seed": 3},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 300,  "motion": "FADEIN", "amplitude": 30},
                {"startSec": 300,  "endSec": 900,  "motion": "BOB",    "period": 10,   "amplitude": 15},
                {"startSec": 900,  "endSec": 1300, "motion": "DRIFT",  "period": 20,   "amplitude": 40},
                {"startSec": 1300, "endSec": 1500, "motion": "BOB",    "period": 12,   "amplitude": 12},
            ],
        },
    },

    # ── SERIES 5: TRANSPORT ──────────────────────────────────────────────────
    "t_airplane": {
        "name_en": "Airplane",    "name_ar": "طائرة",          "name_id": "Pesawat",
        "series": "transport", "comp": "DanceShapeLong", "dur_label": "25 min",
        "props": {
            "bgColor": "#040A18",
            "musicFile": "Morning Trail.mp3", "volume": 0.18,
            "shapes": [
                {"shape": "diamond", "color": "#E8EEF5", "size": 260, "posX": 0.50, "posY": 0.40, "seed": 1},
                {"shape": "diamond", "color": "#CFD8DC", "size": 180, "posX": 0.30, "posY": 0.44, "seed": 2},
                {"shape": "diamond", "color": "#CFD8DC", "size": 180, "posX": 0.70, "posY": 0.44, "seed": 3},
                {"shape": "circle",  "color": "#E3F2FD", "size": 130, "posX": 0.15, "posY": 0.28, "seed": 4},
                {"shape": "circle",  "color": "#E3F2FD", "size": 110, "posX": 0.82, "posY": 0.25, "seed": 5},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 120,  "motion": "FADEIN",  "amplitude": 60},
                {"startSec": 120,  "endSec": 600,  "motion": "ORBIT",   "period": 10,   "amplitude": 180},
                {"startSec": 600,  "endSec": 1100, "motion": "DRIFT",   "period": 8.0,  "amplitude": 120},
                {"startSec": 1100, "endSec": 1500, "motion": "WAVE",    "period": 6.0,  "amplitude": 50, "waveDelay": 0.5},
            ],
        },
    },
    "t_helicopter": {
        "name_en": "Helicopter",  "name_ar": "طائرة مروحية",  "name_id": "Helikopter",
        "series": "transport", "comp": "DanceShapeLong", "dur_label": "25 min",
        "props": {
            "bgColor": "#06100C",
            "musicFile": "Afternoon in F v2.mp3", "volume": 0.18,
            "shapes": [
                {"shape": "circle",  "color": "#FFB300", "size": 200, "posX": 0.50, "posY": 0.46, "seed": 1},
                {"shape": "diamond", "color": "#FDD835", "size": 160, "posX": 0.32, "posY": 0.30, "seed": 2},
                {"shape": "diamond", "color": "#FDD835", "size": 160, "posX": 0.68, "posY": 0.30, "seed": 3},
                {"shape": "diamond", "color": "#F9A825", "size": 110, "posX": 0.78, "posY": 0.54, "seed": 4},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 150,  "motion": "FADEIN",  "amplitude": 60},
                {"startSec": 150,  "endSec": 600,  "motion": "SPIN",    "period": 3.0,  "amplitude": 15},
                {"startSec": 600,  "endSec": 1100, "motion": "BOB",     "period": 4.0,  "amplitude": 70},
                {"startSec": 1100, "endSec": 1500, "motion": "DRIFT",   "period": 10,   "amplitude": 100},
            ],
        },
    },
    "t_ship": {
        "name_en": "Ship",        "name_ar": "سفينة",          "name_id": "Kapal",
        "series": "transport", "comp": "DanceShapeLong", "dur_label": "25 min",
        "props": {
            "bgColor": "#010812",
            "musicFile": "Tide and Piano.mp3", "volume": 0.16,
            "shapes": [
                {"shape": "hexagon", "color": "#37474F", "size": 280, "posX": 0.50, "posY": 0.56, "seed": 1},
                {"shape": "square",  "color": "#546E7A", "size": 140, "posX": 0.50, "posY": 0.36, "seed": 2},
                {"shape": "diamond", "color": "#29B6F6", "size": 160, "posX": 0.20, "posY": 0.70, "seed": 3},
                {"shape": "diamond", "color": "#4FC3F7", "size": 140, "posX": 0.80, "posY": 0.72, "seed": 4},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 200,  "motion": "FADEIN", "amplitude": 40},
                {"startSec": 200,  "endSec": 700,  "motion": "WAVE",   "period": 5.0,  "amplitude": 45, "waveDelay": 0.6},
                {"startSec": 700,  "endSec": 1200, "motion": "BOB",    "period": 7.0,  "amplitude": 50},
                {"startSec": 1200, "endSec": 1500, "motion": "SWAY",   "period": 6.0,  "amplitude": 40},
            ],
        },
    },
    "t_boat": {
        "name_en": "Boat",        "name_ar": "قارب",           "name_id": "Perahu",
        "series": "transport", "comp": "DanceShapeLong", "dur_label": "25 min",
        "props": {
            "bgColor": "#0A1408",
            "musicFile": "Spring Waltz.mp3", "volume": 0.18,
            "shapes": [
                {"shape": "oval",    "color": "#795548", "size": 200, "posX": 0.50, "posY": 0.58, "seed": 1},
                {"shape": "triangle","color": "#ECEFF1", "size": 180, "posX": 0.50, "posY": 0.36, "seed": 2},
                {"shape": "circle",  "color": "#4FC3F7", "size": 120, "posX": 0.28, "posY": 0.70, "seed": 3},
                {"shape": "circle",  "color": "#29B6F6", "size": 100, "posX": 0.72, "posY": 0.72, "seed": 4},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 180,  "motion": "FADEIN", "amplitude": 50},
                {"startSec": 180,  "endSec": 600,  "motion": "BOB",    "period": 4.0,  "amplitude": 40},
                {"startSec": 600,  "endSec": 1100, "motion": "WAVE",   "period": 4.5,  "amplitude": 50, "waveDelay": 0.7},
                {"startSec": 1100, "endSec": 1500, "motion": "DRIFT",  "period": 10,   "amplitude": 80},
            ],
        },
    },
    "t_balloon": {
        "name_en": "Hot Air Balloon", "name_ar": "بالون هوائي ساخن", "name_id": "Balon Udara",
        "series": "transport", "comp": "DanceSpriteLong", "dur_label": "25 min",
        "props": {
            "bgColor": "#060C18", "bgColorEnd": "#040810",
            "accentColor": "#FF7043",
            "musicFile": "Rainbow Lantern.mp3", "volume": 0.18,
            "bgEffect": "sparkles",
            "sprites": [
                {"path": "objects/balloon_3d.png", "size": 380, "posX": 0.50, "posY": 0.42, "seed": 1},
                {"path": "objects/cloud_3d.png",   "size": 220, "posX": 0.18, "posY": 0.30, "seed": 2},
                {"path": "objects/cloud_3d.png",   "size": 180, "posX": 0.80, "posY": 0.26, "seed": 3},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 200,  "motion": "FADEIN",  "amplitude": 60, "wobble": True},
                {"startSec": 200,  "endSec": 700,  "motion": "DRIFT",   "period": 12,   "amplitude": 90, "wobble": True},
                {"startSec": 700,  "endSec": 1200, "motion": "BOB",     "period": 6.0,  "amplitude": 55, "wobble": True},
                {"startSec": 1200, "endSec": 1500, "motion": "DRIFT",   "period": 10,   "amplitude": 80, "wobble": True},
            ],
        },
    },

    # ── SERIES 6: PROFESSIONS ────────────────────────────────────────────────
    "p_chef": {
        "name_en": "Chef",        "name_ar": "طباخ",           "name_id": "Koki",
        "series": "professions", "comp": "DanceSpriteLong", "dur_label": "25 min",
        "props": {
            "bgColor": "#150800", "bgColorEnd": "#0A0400",
            "accentColor": "#FFB74D",
            "musicFile": "Afternoon in F v2.mp3", "volume": 0.20,
            "bgEffect": "sparkles",
            "sprites": [
                {"path": "characters/bear_talking_3d.png", "size": 440, "posX": 0.50, "posY": 0.44, "seed": 1},
                {"path": "fruits/apple_3d.png",            "size": 210, "posX": 0.18, "posY": 0.50, "seed": 2},
                {"path": "fruits/orange_3d.png",           "size": 195, "posX": 0.82, "posY": 0.50, "seed": 3},
                {"path": "fruits/banana_3d.png",           "size": 185, "posX": 0.32, "posY": 0.72, "seed": 4},
                {"path": "objects/star_3d.png",            "size": 140, "posX": 0.68, "posY": 0.72, "seed": 5},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 150,  "motion": "FADEIN",  "amplitude": 60, "wobble": True},
                {"startSec": 150,  "endSec": 600,  "motion": "BOB",     "period": 3.0,  "amplitude": 45, "wobble": True},
                {"startSec": 600,  "endSec": 1000, "motion": "BOUNCE",  "period": 2.5,  "amplitude": 70, "wobble": True},
                {"startSec": 1000, "endSec": 1500, "motion": "SWAY",    "period": 4.0,  "amplitude": 50, "wobble": True},
            ],
        },
    },
    "p_doctor": {
        "name_en": "Doctor",      "name_ar": "طبيب",           "name_id": "Dokter",
        "series": "professions", "comp": "DanceSpriteLong", "dur_label": "25 min",
        "props": {
            "bgColor": "#040C15", "bgColorEnd": "#020810",
            "accentColor": "#29B6F6",
            "musicFile": "Morning Trail v2.mp3", "volume": 0.17,
            "bgEffect": "sparkles",
            "sprites": [
                {"path": "characters/bear_talking_3d.png", "size": 460, "posX": 0.50, "posY": 0.44, "seed": 1},
                {"path": "objects/star_3d.png",            "size": 165, "posX": 0.15, "posY": 0.30, "seed": 2},
                {"path": "objects/star_3d.png",            "size": 140, "posX": 0.85, "posY": 0.28, "seed": 3},
                {"path": "objects/sun_3d.png",             "size": 175, "posX": 0.18, "posY": 0.68, "seed": 4},
                {"path": "objects/star_3d.png",            "size": 130, "posX": 0.82, "posY": 0.66, "seed": 5},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 180,  "motion": "FADEIN", "amplitude": 50, "wobble": True},
                {"startSec": 180,  "endSec": 700,  "motion": "BOB",    "period": 4.0,  "amplitude": 35, "wobble": True},
                {"startSec": 700,  "endSec": 1200, "motion": "SWAY",   "period": 3.0,  "amplitude": 40, "wobble": True},
                {"startSec": 1200, "endSec": 1500, "motion": "DRIFT",  "period": 12,   "amplitude": 70, "wobble": True},
            ],
        },
    },
    "p_firefighter": {
        "name_en": "Firefighter", "name_ar": "رجل إطفاء",     "name_id": "Pemadam Kebakaran",
        "series": "professions", "comp": "DanceSpriteLong", "dur_label": "25 min",
        "props": {
            "bgColor": "#100200", "bgColorEnd": "#080100",
            "accentColor": "#FF5722",
            "musicFile": "The Golden Meadow v2.mp3", "volume": 0.18,
            "bgEffect": "sparkles",
            "sprites": [
                {"path": "characters/bear_celebrate_3d.png", "size": 460, "posX": 0.50, "posY": 0.44, "seed": 1},
                {"path": "objects/star_3d.png",              "size": 165, "posX": 0.15, "posY": 0.30, "seed": 2},
                {"path": "objects/sun_3d.png",               "size": 185, "posX": 0.82, "posY": 0.28, "seed": 3},
                {"path": "objects/star_3d.png",              "size": 140, "posX": 0.20, "posY": 0.68, "seed": 4},
                {"path": "objects/sun_3d.png",               "size": 150, "posX": 0.80, "posY": 0.68, "seed": 5},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 120,  "motion": "FADEIN",  "amplitude": 60, "wobble": True},
                {"startSec": 120,  "endSec": 500,  "motion": "BOUNCE",  "period": 2.0,  "amplitude": 90, "wobble": True},
                {"startSec": 500,  "endSec": 1000, "motion": "BOB",     "period": 2.5,  "amplitude": 50, "wobble": True},
                {"startSec": 1000, "endSec": 1500, "motion": "SWAY",    "period": 3.5,  "amplitude": 60, "wobble": True},
            ],
        },
    },
    "p_teacher": {
        "name_en": "Teacher",     "name_ar": "معلم",           "name_id": "Guru",
        "series": "professions", "comp": "DanceSpriteLong", "dur_label": "25 min",
        "props": {
            "bgColor": "#050A00", "bgColorEnd": "#030600",
            "accentColor": "#66BB6A",
            "musicFile": "Morning Trail.mp3", "volume": 0.17,
            "bgEffect": "sparkles",
            "sprites": [
                {"path": "characters/bear_wave_3d.png", "size": 460, "posX": 0.50, "posY": 0.44, "seed": 1},
                {"path": "objects/star_3d.png",         "size": 175, "posX": 0.15, "posY": 0.30, "seed": 2},
                {"path": "objects/star_3d.png",         "size": 150, "posX": 0.82, "posY": 0.32, "seed": 3},
                {"path": "objects/star_3d.png",         "size": 140, "posX": 0.22, "posY": 0.68, "seed": 4},
                {"path": "objects/rainbow_3d.png",      "size": 185, "posX": 0.78, "posY": 0.66, "seed": 5},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 180,  "motion": "FADEIN",  "amplitude": 50, "wobble": True},
                {"startSec": 180,  "endSec": 600,  "motion": "BOB",     "period": 4.5,  "amplitude": 30, "wobble": True},
                {"startSec": 600,  "endSec": 1100, "motion": "WAVE",    "period": 4.0,  "amplitude": 45, "waveDelay": 0.6, "wobble": True},
                {"startSec": 1100, "endSec": 1500, "motion": "DRIFT",   "period": 12,   "amplitude": 80, "wobble": True},
            ],
        },
    },
    "p_musician": {
        "name_en": "Musician",    "name_ar": "موسيقي",         "name_id": "Musisi",
        "series": "professions", "comp": "DanceSpriteLong", "dur_label": "25 min",
        "props": {
            "bgColor": "#05000F", "bgColorEnd": "#030008",
            "accentColor": "#CE93D8",
            "musicFile": "Moonlight on the Piano v2.mp3", "volume": 0.20,
            "bgEffect": "sparkles",
            "sprites": [
                {"path": "characters/bear_happy_3d.png", "size": 460, "posX": 0.50, "posY": 0.44, "seed": 1},
                {"path": "objects/orb_amber.png",        "size": 175, "posX": 0.18, "posY": 0.28, "seed": 2},
                {"path": "objects/orb_amber.png",        "size": 150, "posX": 0.80, "posY": 0.30, "seed": 3},
                {"path": "objects/star_3d.png",          "size": 140, "posX": 0.22, "posY": 0.68, "seed": 4},
                {"path": "objects/orb_amber.png",        "size": 165, "posX": 0.78, "posY": 0.66, "seed": 5},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 150,  "motion": "FADEIN",  "amplitude": 60, "wobble": True},
                {"startSec": 150,  "endSec": 600,  "motion": "ORBIT",   "period": 5.0,  "amplitude": 150, "wobble": True},
                {"startSec": 600,  "endSec": 1100, "motion": "BOUNCE",  "period": 2.5,  "amplitude": 80, "wobble": True},
                {"startSec": 1100, "endSec": 1500, "motion": "WAVE",    "period": 3.0,  "amplitude": 60, "waveDelay": 0.4, "wobble": True},
            ],
        },
    },
    "p_gardener": {
        "name_en": "Gardener",    "name_ar": "بستاني",         "name_id": "Tukang Kebun",
        "series": "professions", "comp": "DanceSpriteLong", "dur_label": "25 min",
        "props": {
            "bgColor": "#031008", "bgColorEnd": "#020A05",
            "accentColor": "#66BB6A",
            "musicFile": "The Golden Meadow.mp3", "volume": 0.17,
            "bgEffect": "sparkles",
            "sprites": [
                {"path": "characters/bear_happy_3d.png",  "size": 450, "posX": 0.50, "posY": 0.44, "seed": 1},
                {"path": "fruits/apple_3d.png",           "size": 175, "posX": 0.15, "posY": 0.30, "seed": 2},
                {"path": "vegetables/carrot_3d.png",      "size": 165, "posX": 0.82, "posY": 0.28, "seed": 3},
                {"path": "fruits/banana_3d.png",          "size": 155, "posX": 0.20, "posY": 0.68, "seed": 4},
                {"path": "vegetables/broccoli_3d.png",    "size": 160, "posX": 0.80, "posY": 0.66, "seed": 5},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 200,  "motion": "FADEIN",  "amplitude": 60, "wobble": True},
                {"startSec": 200,  "endSec": 650,  "motion": "BOB",     "period": 3.5,  "amplitude": 40, "wobble": True},
                {"startSec": 650,  "endSec": 1100, "motion": "WAVE",    "period": 4.0,  "amplitude": 55, "waveDelay": 0.5, "wobble": True},
                {"startSec": 1100, "endSec": 1500, "motion": "SWAY",    "period": 5.0,  "amplitude": 50, "wobble": True},
            ],
        },
    },
    "p_builder": {
        "name_en": "Builder",     "name_ar": "بنّاء",          "name_id": "Pembangun",
        "series": "professions", "comp": "DanceSpriteLong", "dur_label": "25 min",
        "props": {
            "bgColor": "#0A0800", "bgColorEnd": "#060500",
            "accentColor": "#FF8F00",
            "musicFile": "Spring Waltz v2.mp3", "volume": 0.18,
            "bgEffect": "sparkles",
            "sprites": [
                {"path": "characters/bear_celebrate_3d.png", "size": 460, "posX": 0.50, "posY": 0.44, "seed": 1},
                {"path": "objects/star_3d.png",              "size": 175, "posX": 0.15, "posY": 0.28, "seed": 2},
                {"path": "objects/sun_3d.png",               "size": 185, "posX": 0.82, "posY": 0.30, "seed": 3},
                {"path": "objects/star_3d.png",              "size": 150, "posX": 0.20, "posY": 0.68, "seed": 4},
                {"path": "objects/star_3d.png",              "size": 140, "posX": 0.80, "posY": 0.66, "seed": 5},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 200,  "motion": "FADEIN",  "amplitude": 50, "wobble": True},
                {"startSec": 200,  "endSec": 700,  "motion": "BOB",     "period": 4.0,  "amplitude": 40, "wobble": True},
                {"startSec": 700,  "endSec": 1200, "motion": "BOUNCE",  "period": 3.0,  "amplitude": 65, "wobble": True},
                {"startSec": 1200, "endSec": 1500, "motion": "SWAY",    "period": 5.0,  "amplitude": 45, "wobble": True},
            ],
        },
    },
    "p_captain": {
        "name_en": "Captain",     "name_ar": "قبطان",          "name_id": "Kapten",
        "series": "professions", "comp": "DanceSpriteLong", "dur_label": "25 min",
        "props": {
            "bgColor": "#020810", "bgColorEnd": "#010508",
            "accentColor": "#4FC3F7",
            "musicFile": "Tide and Piano v2.mp3", "volume": 0.16,
            "bgEffect": "sparkles",
            "sprites": [
                {"path": "characters/bear_wave_3d.png", "size": 460, "posX": 0.50, "posY": 0.44, "seed": 1},
                {"path": "objects/star_3d.png",         "size": 175, "posX": 0.18, "posY": 0.28, "seed": 2},
                {"path": "objects/star_3d.png",         "size": 150, "posX": 0.80, "posY": 0.26, "seed": 3},
                {"path": "objects/rainbow_3d.png",      "size": 207, "posX": 0.20, "posY": 0.68, "seed": 4},
                {"path": "objects/star_3d.png",         "size": 140, "posX": 0.78, "posY": 0.68, "seed": 5},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 180,  "motion": "FADEIN",  "amplitude": 50, "wobble": True},
                {"startSec": 180,  "endSec": 600,  "motion": "ORBIT",   "period": 8.0,  "amplitude": 160, "wobble": True},
                {"startSec": 600,  "endSec": 1100, "motion": "WAVE",    "period": 6.0,  "amplitude": 50, "waveDelay": 0.5, "wobble": True},
                {"startSec": 1100, "endSec": 1500, "motion": "DRIFT",   "period": 14,   "amplitude": 90, "wobble": True},
            ],
        },
    },
}

SERIES_KEYS = {
    "emotions":    [k for k, v in VIDEOS.items() if v["series"] == "emotions"],
    "ocean":       [k for k, v in VIDEOS.items() if v["series"] == "ocean"],
    "transport":   [k for k, v in VIDEOS.items() if v["series"] == "transport"],
    "professions": [k for k, v in VIDEOS.items() if v["series"] == "professions"],
}

PROMPTS = {
    "e_happy":      "cute 3D Pixar happy smiley character big eyes huge smile, bright yellow warm background, children's animation",
    "e_sad":        "cute 3D Pixar sad character droopy eyes frown, blue misty background, children's animation",
    "e_surprised":  "cute 3D Pixar surprised character wide eyes open mouth, purple sparkles background, children's animation",
    "e_angry":      "cute 3D Pixar angry character furrowed brows, red warm background, children's animation",
    "e_scared":     "cute 3D Pixar scared character big frightened eyes, dark spooky but cute background, children's animation",
    "e_love":       "cute 3D Pixar love character heart eyes rosy cheeks, pink sparkles romantic background, children's animation",
    "o_whale":      "adorable 3D Pixar blue whale swimming deep dark ocean with bubbles, children's animation",
    "o_octopus":    "cute 3D Pixar purple octopus curling tentacles in deep sea bioluminescent background, children's animation",
    "o_fish":       "three cute colorful 3D Pixar fish swimming in clear blue ocean, children's animation",
    "o_dolphin":    "playful 3D Pixar dolphins leaping out of sparkling blue ocean, children's animation",
    "o_jellyfish":  "glowing bioluminescent jellyfish floating dark deep ocean magical purple blue glow, children's animation",
    "o_starfish":   "cute orange 3D Pixar starfish resting on ocean floor with tiny companions, children's animation",
    "t_airplane":   "cute white 3D Pixar airplane flying through fluffy clouds in blue sky, children's animation",
    "t_helicopter": "cute yellow 3D Pixar helicopter hovering in sky spinning rotor, children's animation",
    "t_ship":       "big dark 3D Pixar ship sailing on ocean with waves majestic, children's animation",
    "t_boat":       "small cute 3D Pixar wooden sailing boat white sail on river, children's animation",
    "t_balloon":    "colorful hot air balloon floating in sky with clouds below, magical, Pixar 3D style",
    "p_chef":       "cute 3D Pixar chef tall white hat cooking colorful ingredients kitchen, children's animation",
    "p_doctor":     "friendly 3D Pixar doctor stethoscope white coat medical symbols, children's animation",
    "p_firefighter":"brave 3D Pixar firefighter red truck water hose battling tiny flames, children's animation",
    "p_teacher":    "friendly 3D Pixar teacher green chalkboard colorful stars letters, children's animation",
    "p_musician":   "happy 3D Pixar musician colorful floating music notes, children's animation",
    "p_gardener":   "cheerful 3D Pixar gardener fruits vegetables growing in garden, children's animation",
    "p_builder":    "cute 3D Pixar builder yellow hard hat stacking colorful building blocks, children's animation",
    "p_captain":    "brave 3D Pixar ship captain steering wheel stars guiding at night, children's animation",
}


def make_meta(video_id: str, lang: str) -> dict:
    v    = VIDEOS[video_id]
    ser  = v["series"]
    ch   = {"en": "@HappyBearKids1", "ar": "@happybearkidsar", "id": "@happybearkidsin"}
    name = v[f"name_{lang}"]
    dur  = v["dur_label"]
    if lang == "en":
        series_name = SERIES_EN[ser]
        title = f"{name} | {dur} Baby Animation | Happy Bear Kids"
        description = (
            f"✨ {name} — captivating visual animation for babies and toddlers!\n\n"
            f"No words, no text — pure visual experience designed to engage young minds. "
            f"Beautiful colors, smooth movements, and gentle music create a mesmerizing "
            f"experience perfect for babies from 0–3 years old.\n\n"
            f"Part of the {series_name} series — carefully designed educational content "
            f"that introduces concepts through visual storytelling without any language barriers.\n\n"
            f"🎯 Perfect for: visual stimulation, sensory development, background TV\n"
            f"👶 Age: 0–3 years | 📺 {dur} continuous\n"
            f"🌈 Universal — works for any culture or language\n\n"
            f"🔔 Subscribe → {ch['en']}\n"
            f"🎵 Original music by Happy Bear Kids (AI-generated, © 2026)\n\n"
            f"#{name.replace(' ','')} #{series_name.replace(' ','')} "
            f"#HappyBearKids #BabyAnimation #VisualStimulation #ToddlerTV"
            f"\n© Happy Bear Kids 2026"
        )
        tags = [name.lower(), series_name.lower(), "baby animation", "happy bear kids",
                "visual stimulation", "no talking", dur, "toddler tv"]
    elif lang == "ar":
        series_name = SERIES_AR[ser]
        title = f"{name} | {dur} رسوم أطفال | هابي بير كيدز"
        description = (
            f"✨ {name} — رسوم متحركة رائعة للرضع والأطفال الصغار!\n\n"
            f"بدون كلمات أو نصوص — تجربة بصرية خالصة مصممة لإشراك العقول الصغيرة. "
            f"ألوان جميلة وحركات سلسة وموسيقى هادئة تخلق تجربة آسرة للرضع.\n\n"
            f"جزء من سلسلة {series_name} — محتوى تعليمي مصمم بعناية يقدم المفاهيم "
            f"من خلال رواية بصرية بدون حواجز لغوية.\n\n"
            f"👶 العمر: 0–3 سنوات | 📺 {dur}\n\n"
            f"🔔 اشتركوا → {ch['ar']}\n"
            f"🎵 موسيقى أصلية من هابي بير كيدز\n\n"
            f"#{name.replace(' ','_')} #هابي_بير_كيدز #رسوم_أطفال #تحفيز_بصري"
            f"\n© هابي بير كيدز 2026"
        )
        tags = [name, series_name, "هابي بير كيدز", "رسوم أطفال", "تحفيز بصري", "بدون كلام"]
    else:
        series_name = SERIES_ID[ser]
        title = f"{name} | {dur} Animasi Bayi | Happy Bear Kids"
        description = (
            f"✨ {name} — animasi visual yang memukau untuk bayi dan balita!\n\n"
            f"Tanpa kata-kata atau teks — pengalaman visual murni yang dirancang untuk "
            f"melibatkan pikiran muda. Warna indah, gerakan halus, dan musik lembut menciptakan "
            f"pengalaman yang memikat untuk bayi usia 0–3 tahun.\n\n"
            f"Bagian dari seri {series_name} — konten edukatif yang dirancang dengan cermat "
            f"yang memperkenalkan konsep melalui cerita visual tanpa hambatan bahasa.\n\n"
            f"👶 Usia: 0–3 tahun | 📺 {dur}\n\n"
            f"🔔 Subscribe → {ch['id']}\n"
            f"🎵 Original music by Happy Bear Kids (AI-generated, © 2026)\n\n"
            f"#{name.replace(' ','')} #HappyBearKids #AnimasiBayi #StimulasiVisual"
            f"\n© Happy Bear Kids Indonesia 2026"
        )
        tags = [name.lower(), series_name.lower(), "animasi bayi", "happy bear kids",
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
    prompt = PROMPTS.get(video_id, "baby animation colorful characters") + f", YouTube thumbnail{notext}"
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


def render_video(video_id: str, lang: str, ep_idx: int, force: bool, dry_run: bool) -> Path | None:
    v    = VIDEOS[video_id]
    q    = {"en": QUEUE_EN, "ar": QUEUE_AR, "id": QUEUE_ID}[lang]
    stem = f"eo_{video_id}_{DATE_STR}" if lang == "en" else f"eo_{video_id}_{DATE_STR}_{lang}"
    out  = q / f"{stem}.mp4"
    if out.exists() and not force:
        print(f"  [{lang.upper()}] skip {out.name}"); return out
    en_music = v["props"]["musicFile"]
    music    = en_music if lang == "en" else alt_music(en_music, ep_idx, lang)
    props    = dict(v["props"], musicFile=music)
    print(f"\n  [{lang.upper()}] Rendering {video_id}: {v['name_en']} (music: {music})")
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


def distribute(video_id: str, ep_idx: int, force: bool, dry_run: bool,
               allowed_langs: list[str] | None = None):
    all_langs = [("en", QUEUE_EN), ("ar", QUEUE_AR), ("id", QUEUE_ID)]
    for lang, q in [(l, q) for l, q in all_langs if allowed_langs is None or l in allowed_langs]:
        stem  = f"eo_{video_id}_{DATE_STR}" if lang == "en" else f"eo_{video_id}_{DATE_STR}_{lang}"
        mp4   = q / f"{stem}.mp4"
        if not mp4.exists() or force:
            render_video(video_id, lang, ep_idx, force, dry_run)
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
    parser.add_argument("--videos",     nargs="*", help="Video IDs or 'all'")
    parser.add_argument("--series",     choices=list(SERIES_KEYS), help="Run one series")
    parser.add_argument("--dry-run",    action="store_true")
    parser.add_argument("--force",      action="store_true")
    parser.add_argument("--regen-meta", action="store_true")
    parser.add_argument("--queues",     nargs="+", choices=["en", "ar", "id"],
                        default=["en", "ar", "id"],
                        help="Which channel queues to render/distribute (default: all)")
    args = parser.parse_args()

    if args.list:
        for ser in ("emotions", "ocean", "transport", "professions"):
            print(f"\n  ── {SERIES_EN[ser]} ──")
            for vid in SERIES_KEYS[ser]:
                v = VIDEOS[vid]
                print(f"  {vid:20s}  {v['name_en']:22s}  {v['comp']:20s}  {v['dur_label']}")
        return

    if args.series:
        ids = SERIES_KEYS[args.series]
    elif args.videos:
        ids = list(VIDEOS) if args.videos == ["all"] else args.videos
    else:
        ids = list(VIDEOS)

    bad = [v for v in ids if v not in VIDEOS]
    if bad:
        print(f"Unknown video IDs: {bad}"); sys.exit(1)

    print(f"=== Emotions + Ocean + Transport + Professions — {len(ids)} videos ===\n")
    for ep_idx, vid in enumerate(ids):
        v = VIDEOS[vid]
        print(f"[{vid}] {v['name_en']}  ({v['series']})")
        distribute(vid, ep_idx, args.force, args.dry_run, args.queues)

    print("\n=== Done ===")


if __name__ == "__main__":
    main()
