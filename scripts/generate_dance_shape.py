#!/usr/bin/env python3
"""
Generate DanceShapeLong videos — 12-video "Dancing Shapes" series.
Pure geometric animation, no text, no sprites → universal (EN + AR + ID).

Series:
  1  One Circle     (25 min) — BOB → SWAY → SPIN → PULSE → DRIFT
  2  Three Circles  (25 min) — Sync BOB → WAVE → Multi-rhythm → ORBIT → DRIFT
  3  Five Wave      (25 min) — WAVE → reverse → competing → vertical → PULSE
  4  Squares March  (25 min) — MARCH → SPIN → Sync SPIN → WAVE → ORBIT
  5  Triangles      (25 min) — SWAY → SPIN → BOUNCE → ORBIT → WAVE
  6  Mixed Three    (25 min) — BOB intro → Sync BOB → DRIFT → Each own → ORBIT
  7  Aquarium       (30 min) — FADEIN → DRIFT → FADEOUT
  8  Stars          (25 min) — PULSE → SPIN → BOB fall → ORBIT → DRIFT
  9  Hearts         (25 min) — PULSE breathing → SWAY → BOUNCE float → SWAY → ORBIT
  10 Color Circles  (30 min) — Color BOB → Color WAVE → PULSE → Rainbow → BOB
  11 Big+Small      (25 min) — BOB different → ORBIT small → SWAY → DRIFT → PULSE
  12 Night Mode     (30 min) — PULSE breath → DRIFT slow → FADEIN → SPIN slow → DRIFT

Usage:
  python3 scripts/generate_dance_shape.py               # all 12
  python3 scripts/generate_dance_shape.py --videos 1 2  # specific videos
  python3 scripts/generate_dance_shape.py --dry-run
  python3 scripts/generate_dance_shape.py --force       # re-render existing
  python3 scripts/generate_dance_shape.py --regen-meta  # regenerate meta+thumb only
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
TOGETHER_URL      = "https://api.together.xyz/v1/images/generations"
TOGETHER_MODEL    = "black-forest-labs/FLUX.1-schnell"

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

# Palettes
VIBRANT = ["#E53935", "#FF9800", "#FDD835", "#43A047", "#1E88E5", "#8E24AA", "#F06292"]
PASTEL  = ["#FFCDD2", "#FFE0B2", "#FFF9C4", "#DCEDC8", "#BBDEFB", "#E1BEE7", "#FCE4EC"]
NIGHT   = ["#7B9EC7", "#8FB3D4", "#A3C4E0", "#BAD4EA", "#D0E4F2", "#E5F1F9", "#C5D8E8"]
RAINBOW = ["#E53935", "#FF9800", "#FDD835", "#43A047", "#1E88E5", "#8E24AA"]


def make_config(video_num: int) -> tuple[dict, str, int]:
    """Return (props_dict, composition_id, duration_sec)."""

    if video_num == 1:
        props = {
            "bgColor": "#0A1628",
            "musicFile": "Carefree.mp3",
            "shapes": [
                {"shape": "circle", "color": "#E53935", "size": 400,
                 "posX": 0.5, "posY": 0.42, "seed": 1},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 300,  "motion": "BOB",   "period": 3,  "amplitude": 45,
                 "colorPalette": ["#E53935", "#FF7043"], "colorCycleSec": 90},
                {"startSec": 300,  "endSec": 600,  "motion": "SWAY",  "period": 4,  "amplitude": 55,
                 "colorPalette": ["#FF7043", "#FF9800"], "colorCycleSec": 90},
                {"startSec": 600,  "endSec": 900,  "motion": "SPIN",  "period": 7,
                 "colorPalette": ["#FF9800", "#FDD835"], "colorCycleSec": 90},
                {"startSec": 900,  "endSec": 1200, "motion": "PULSE", "period": 4.5, "amplitude": 14,
                 "colorPalette": ["#FDD835", "#43A047"], "colorCycleSec": 90},
                {"startSec": 1200, "endSec": 1500, "motion": "DRIFT", "period": 9,  "amplitude": 300,
                 "colorPalette": ["#43A047", "#1E88E5", "#8E24AA"], "colorCycleSec": 80},
            ],
        }
        return props, "DanceShapeLong", 1500

    if video_num == 2:
        props = {
            "bgColor": "#0A1628",
            "musicFile": "Pinball Spring.mp3",
            "shapes": [
                {"shape": "circle", "color": "#E53935", "size": 260,
                 "posX": 0.25, "posY": 0.42, "seed": 1,
                 "orbitRadius": 0},
                {"shape": "circle", "color": "#1E88E5", "size": 260,
                 "posX": 0.5,  "posY": 0.42, "seed": 2,
                 "orbitRadius": 280, "orbitPeriodSec": 10, "orbitCcw": False},
                {"shape": "circle", "color": "#FDD835", "size": 260,
                 "posX": 0.75, "posY": 0.42, "seed": 3,
                 "orbitRadius": 280, "orbitPeriodSec": 10, "orbitCcw": True},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 300,  "motion": "BOB",   "period": 2.5, "amplitude": 40},
                {"startSec": 300,  "endSec": 600,  "motion": "WAVE",  "period": 2.5, "amplitude": 40,
                 "waveDelay": 0.4},
                {"startSec": 600,  "endSec": 900,  "motion": "BOB",   "period": 2.0, "amplitude": 40,
                 "colorPalette": VIBRANT, "colorCycleSec": 70},
                {"startSec": 900,  "endSec": 1200, "motion": "ORBIT",
                 "orbitCenterX": 0.5, "orbitCenterY": 0.42},
                {"startSec": 1200, "endSec": 1500, "motion": "DRIFT", "period": 8,  "amplitude": 200,
                 "colorPalette": VIBRANT, "colorCycleSec": 60},
            ],
        }
        return props, "DanceShapeLong", 1500

    if video_num == 3:
        colors5 = ["#E53935", "#FF9800", "#FDD835", "#43A047", "#1E88E5"]
        props = {
            "bgColor": "#0A1628",
            "musicFile": "Wholesome.mp3",
            "shapes": [
                {"shape": "circle", "color": c, "size": 200,
                 "posX": 0.1 + i * 0.2, "posY": 0.42,
                 "seed": i + 1, "colorOffset": i * 0.18}
                for i, c in enumerate(colors5)
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 300,  "motion": "WAVE",  "period": 2.5, "amplitude": 50,
                 "waveDelay": 0.4},
                {"startSec": 300,  "endSec": 600,  "motion": "WAVE",  "period": 2.5, "amplitude": 50,
                 "waveDelay": -0.4},
                {"startSec": 600,  "endSec": 900,  "motion": "WAVE",  "period": 2.0, "amplitude": 50,
                 "waveDelay": 0.5,
                 "colorPalette": VIBRANT, "colorCycleSec": 50},
                {"startSec": 900,  "endSec": 1200, "motion": "BOB",   "period": 2.5, "amplitude": 50,
                 "colorPalette": RAINBOW, "colorCycleSec": 40},
                {"startSec": 1200, "endSec": 1500, "motion": "PULSE", "period": 3.5, "amplitude": 15,
                 "colorPalette": VIBRANT, "colorCycleSec": 30},
            ],
        }
        return props, "DanceShapeLong", 1500

    if video_num == 4:
        sq_colors = ["#E53935", "#1E88E5", "#43A047", "#FF9800"]
        props = {
            "bgColor": "#0D1B2A",
            "musicFile": "Quirky Dog.mp3",
            "shapes": [
                {"shape": "square", "color": c, "size": 220,
                 "posX": 0.15 + i * 0.24, "posY": 0.42,
                 "seed": i + 1,
                 "orbitRadius": [0, 180, 220, 260][i],
                 "orbitPeriodSec": 9 + i * 1.5,
                 "orbitCcw": i % 2 == 1}
                for i, c in enumerate(sq_colors)
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 300,  "motion": "MARCH", "period": 8,
                 "bobAmplitude": 22},
                {"startSec": 300,  "endSec": 600,  "motion": "SPIN",  "period": 5,
                 "colorPalette": VIBRANT, "colorCycleSec": 60},
                {"startSec": 600,  "endSec": 900,  "motion": "SPIN",  "period": 6},
                {"startSec": 900,  "endSec": 1200, "motion": "WAVE",  "period": 2.5, "amplitude": 45,
                 "waveDelay": 0.5},
                {"startSec": 1200, "endSec": 1500, "motion": "ORBIT",
                 "orbitCenterX": 0.5, "orbitCenterY": 0.42},
            ],
        }
        return props, "DanceShapeLong", 1500

    if video_num == 5:
        tri_colors = ["#E53935", "#009688", "#F9A825"]
        props = {
            "bgColor": "#0A1628",
            "musicFile": "Merry Go.mp3",
            "shapes": [
                {"shape": "triangle", "color": c, "size": 240,
                 "posX": 0.25 + i * 0.25, "posY": 0.42,
                 "seed": i + 1,
                 "orbitRadius": [0, 220, 220][i],
                 "orbitPeriodSec": 8,
                 "orbitCcw": i % 2 == 0}
                for i, c in enumerate(tri_colors)
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 300,  "motion": "SWAY",   "period": 3.5, "amplitude": 50},
                {"startSec": 300,  "endSec": 600,  "motion": "SPIN",   "period": 5,
                 "colorPalette": ["#E53935", "#FF9800", "#FDD835"], "colorCycleSec": 80},
                {"startSec": 600,  "endSec": 900,  "motion": "BOUNCE", "period": 2.0, "amplitude": 70},
                {"startSec": 900,  "endSec": 1200, "motion": "ORBIT",
                 "orbitCenterX": 0.5, "orbitCenterY": 0.42},
                {"startSec": 1200, "endSec": 1500, "motion": "WAVE",   "period": 2.5, "amplitude": 45,
                 "waveDelay": 0.4},
            ],
        }
        return props, "DanceShapeLong", 1500

    if video_num == 6:
        props = {
            "bgColor": "#0A1628",
            "musicFile": "Life of Riley.mp3",
            "shapes": [
                {"shape": "circle",   "color": "#E53935", "size": 240,
                 "posX": 0.25, "posY": 0.42, "seed": 1, "orbitRadius": 0},
                {"shape": "square",   "color": "#1E88E5", "size": 240,
                 "posX": 0.5,  "posY": 0.42, "seed": 2,
                 "orbitRadius": 260, "orbitPeriodSec": 9},
                {"shape": "triangle", "color": "#43A047", "size": 240,
                 "posX": 0.75, "posY": 0.42, "seed": 3,
                 "orbitRadius": 260, "orbitPeriodSec": 9, "orbitCcw": True},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 300,  "motion": "BOB",   "period": 2.5, "amplitude": 40},
                {"startSec": 300,  "endSec": 600,  "motion": "BOB",   "period": 2.5, "amplitude": 40,
                 "colorPalette": VIBRANT, "colorCycleSec": 50},
                {"startSec": 600,  "endSec": 900,  "motion": "DRIFT", "period": 7,  "amplitude": 220},
                {"startSec": 900,  "endSec": 1200, "motion": "SWAY",  "period": 3.5, "amplitude": 55},
                {"startSec": 1200, "endSec": 1500, "motion": "ORBIT",
                 "orbitCenterX": 0.5, "orbitCenterY": 0.42},
            ],
        }
        return props, "DanceShapeLong", 1500

    if video_num == 7:
        # Aquarium — 30 min, 12 shapes
        aq = [
            ("circle",   "#E53935", 200, 0.17, 0.28, 0.00),
            ("square",   "#1E88E5", 180, 0.50, 0.22, 0.08),
            ("triangle", "#43A047", 190, 0.83, 0.28, 0.16),
            ("star",     "#F9A825", 180, 0.17, 0.60, 0.24),
            ("heart",    "#E91E63", 180, 0.50, 0.58, 0.32),
            ("diamond",  "#9C27B0", 180, 0.83, 0.60, 0.40),
            ("circle",   "#FF9800", 160, 0.33, 0.78, 0.48),
            ("square",   "#00BCD4", 160, 0.67, 0.78, 0.56),
            ("hexagon",  "#8BC34A", 170, 0.08, 0.45, 0.64),
            ("oval",     "#FF5722", 160, 0.92, 0.45, 0.72),
            ("triangle", "#3F51B5", 150, 0.33, 0.35, 0.80),
            ("star",     "#FFEB3B", 150, 0.67, 0.35, 0.88),
        ]
        props = {
            "bgColor": "#040D1A",
            "musicFile": "Gymnopedie No 1.mp3",
            "volume": 0.15,
            "shapes": [
                {"shape": s, "color": c, "size": sz, "posX": px, "posY": py,
                 "seed": i + 1, "colorOffset": co}
                for i, (s, c, sz, px, py, co) in enumerate(aq)
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 600,  "motion": "FADEIN",  "amplitude": 80,
                 "colorPalette": VIBRANT, "colorCycleSec": 60},
                {"startSec": 600,  "endSec": 1200, "motion": "DRIFT",   "period": 12, "amplitude": 140,
                 "colorPalette": VIBRANT, "colorCycleSec": 60},
                {"startSec": 1200, "endSec": 1800, "motion": "FADEOUT", "amplitude": 80,
                 "colorPalette": VIBRANT, "colorCycleSec": 60},
            ],
        }
        return props, "DanceShapeLong30", 1800

    if video_num == 8:
        props = {
            "bgColor": "#050A1A",
            "musicFile": "Heartwarming.mp3",
            "shapes": [
                {"shape": "star", "color": "#FDD835", "size": 420,
                 "posX": 0.5,  "posY": 0.42, "seed": 1, "orbitRadius": 0},
                {"shape": "star", "color": "#FF9800", "size": 180,
                 "posX": 0.5,  "posY": 0.22, "seed": 2,
                 "orbitRadius": 240, "orbitPeriodSec": 8},
                {"shape": "star", "color": "#E53935", "size": 160,
                 "posX": 0.5,  "posY": 0.62, "seed": 3,
                 "orbitRadius": 240, "orbitPeriodSec": 8, "orbitCcw": True},
                {"shape": "star", "color": "#FDD835", "size": 140,
                 "posX": 0.3,  "posY": 0.42, "seed": 4,
                 "orbitRadius": 320, "orbitPeriodSec": 12},
                {"shape": "star", "color": "#FF9800", "size": 140,
                 "posX": 0.7,  "posY": 0.42, "seed": 5,
                 "orbitRadius": 320, "orbitPeriodSec": 12, "orbitCcw": True},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 300,  "motion": "PULSE", "period": 5,  "amplitude": 12},
                {"startSec": 300,  "endSec": 600,  "motion": "SPIN",  "period": 8,
                 "colorPalette": ["#FDD835", "#FF9800", "#E53935", "#FF5722"],
                 "colorCycleSec": 80},
                {"startSec": 600,  "endSec": 900,  "motion": "BOB",   "period": 3,  "amplitude": 40,
                 "colorPalette": ["#FDD835", "#FFEB3B", "#FF9800"], "colorCycleSec": 70},
                {"startSec": 900,  "endSec": 1200, "motion": "ORBIT",
                 "orbitCenterX": 0.5, "orbitCenterY": 0.42},
                {"startSec": 1200, "endSec": 1500, "motion": "DRIFT", "period": 11, "amplitude": 200,
                 "colorPalette": NIGHT, "colorCycleSec": 50},
            ],
        }
        return props, "DanceShapeLong", 1500

    if video_num == 9:
        props = {
            "bgColor": "#1A0A0F",
            "musicFile": "Crinoline Dreams.mp3",
            "shapes": [
                {"shape": "heart", "color": "#E91E63", "size": 380,
                 "posX": 0.5,  "posY": 0.38, "seed": 1, "orbitRadius": 0},
                {"shape": "heart", "color": "#F06292", "size": 260,
                 "posX": 0.28, "posY": 0.45, "seed": 2,
                 "orbitRadius": 260, "orbitPeriodSec": 10},
                {"shape": "heart", "color": "#AD1457", "size": 240,
                 "posX": 0.72, "posY": 0.45, "seed": 3,
                 "orbitRadius": 260, "orbitPeriodSec": 10, "orbitCcw": True},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 300,  "motion": "PULSE",  "period": 5,  "amplitude": 13},
                {"startSec": 300,  "endSec": 600,  "motion": "SWAY",   "period": 3.5, "amplitude": 55,
                 "colorPalette": ["#E91E63", "#F06292", "#AD1457", "#E53935"],
                 "colorCycleSec": 80},
                {"startSec": 600,  "endSec": 900,  "motion": "BOUNCE", "period": 2.0, "amplitude": 60},
                {"startSec": 900,  "endSec": 1200, "motion": "SWAY",   "period": 2.5, "amplitude": 60},
                {"startSec": 1200, "endSec": 1500, "motion": "ORBIT",
                 "orbitCenterX": 0.5, "orbitCenterY": 0.42},
            ],
        }
        return props, "DanceShapeLong", 1500

    if video_num == 10:
        # Six color circles — 30 min
        grid = [
            (0.17, 0.28), (0.50, 0.28), (0.83, 0.28),
            (0.17, 0.62), (0.50, 0.62), (0.83, 0.62),
        ]
        base_colors = ["#E53935", "#FF9800", "#FDD835", "#43A047", "#1E88E5", "#8E24AA"]
        props = {
            "bgColor": "#0A1628",
            "musicFile": "Hyperfun.mp3",
            "shapes": [
                {"shape": "circle", "color": c, "size": 240,
                 "posX": px, "posY": py, "seed": i + 1, "colorOffset": i * 0.17}
                for i, ((px, py), c) in enumerate(zip(grid, base_colors))
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 300,  "motion": "BOB",   "period": 2.5, "amplitude": 35,
                 "colorPalette": VIBRANT, "colorCycleSec": 50},
                {"startSec": 300,  "endSec": 600,  "motion": "WAVE",  "period": 2.5, "amplitude": 35,
                 "waveDelay": 0.35,
                 "colorPalette": RAINBOW, "colorCycleSec": 40},
                {"startSec": 600,  "endSec": 900,  "motion": "PULSE", "period": 4,   "amplitude": 14,
                 "colorPalette": VIBRANT, "colorCycleSec": 60},
                {"startSec": 900,  "endSec": 1200, "motion": "BOB",   "period": 2.5, "amplitude": 35,
                 "colorPalette": RAINBOW, "colorCycleSec": 30},
                {"startSec": 1200, "endSec": 1500, "motion": "WAVE",  "period": 2.0, "amplitude": 35,
                 "waveDelay": 0.5,
                 "colorPalette": VIBRANT, "colorCycleSec": 25},
                {"startSec": 1500, "endSec": 1800, "motion": "BOB",   "period": 2.5, "amplitude": 30,
                 "colorPalette": RAINBOW, "colorCycleSec": 20},
            ],
        }
        return props, "DanceShapeLong30", 1800

    if video_num == 11:
        props = {
            "bgColor": "#0A1628",
            "musicFile": "Walking Along.mp3",
            "shapes": [
                {"shape": "circle", "color": "#1E88E5", "size": 460,
                 "posX": 0.5, "posY": 0.42, "seed": 1, "orbitRadius": 0},
                {"shape": "circle", "color": "#FDD835", "size": 140,
                 "posX": 0.5, "posY": 0.22, "seed": 2,
                 "orbitRadius": 220, "orbitPeriodSec": 6},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 300,  "motion": "BOB",   "period": 3,  "amplitude": 40},
                {"startSec": 300,  "endSec": 600,  "motion": "ORBIT",
                 "orbitCenterX": 0.5, "orbitCenterY": 0.42},
                {"startSec": 600,  "endSec": 900,  "motion": "SWAY",  "period": 3.5, "amplitude": 55,
                 "colorPalette": ["#1E88E5", "#43A047", "#E53935"], "colorCycleSec": 80},
                {"startSec": 900,  "endSec": 1200, "motion": "DRIFT", "period": 8,  "amplitude": 200},
                {"startSec": 1200, "endSec": 1500, "motion": "PULSE", "period": 4,  "amplitude": 14},
            ],
        }
        return props, "DanceShapeLong", 1500

    if video_num == 12:
        props = {
            "bgColor": "#050A1A",
            "musicFile": "Gymnopedie No 1.mp3",
            "volume": 0.12,
            "nightMode": True,
            "shapes": [
                {"shape": "circle",  "color": "#7B9EC7", "size": 300,
                 "posX": 0.5,  "posY": 0.35, "seed": 1, "orbitRadius": 0, "colorOffset": 0.0},
                {"shape": "oval",    "color": "#8FB3D4", "size": 220,
                 "posX": 0.3,  "posY": 0.55, "seed": 2, "orbitRadius": 0, "colorOffset": 0.25},
                {"shape": "circle",  "color": "#A3C4E0", "size": 180,
                 "posX": 0.7,  "posY": 0.55, "seed": 3, "orbitRadius": 0, "colorOffset": 0.5},
                {"shape": "hexagon", "color": "#BAD4EA", "size": 200,
                 "posX": 0.15, "posY": 0.35, "seed": 4, "orbitRadius": 0, "colorOffset": 0.75},
                {"shape": "star",    "color": "#D0E4F2", "size": 160,
                 "posX": 0.85, "posY": 0.35, "seed": 5, "orbitRadius": 0, "colorOffset": 0.9},
            ],
            "blocks": [
                {"startSec": 0,    "endSec": 480,  "motion": "PULSE",  "period": 8,  "amplitude": 10,
                 "colorPalette": NIGHT, "colorCycleSec": 120},
                {"startSec": 480,  "endSec": 960,  "motion": "DRIFT",  "period": 14, "amplitude": 80,
                 "colorPalette": NIGHT, "colorCycleSec": 120},
                {"startSec": 960,  "endSec": 1320, "motion": "FADEIN", "amplitude": 60,
                 "colorPalette": NIGHT, "colorCycleSec": 120},
                {"startSec": 1320, "endSec": 1680, "motion": "SPIN",   "period": 20,
                 "colorPalette": NIGHT, "colorCycleSec": 120},
                {"startSec": 1680, "endSec": 1800, "motion": "DRIFT",  "period": 18, "amplitude": 40,
                 "colorPalette": NIGHT, "colorCycleSec": 120},
            ],
        }
        return props, "DanceShapeLong30", 1800

    raise ValueError(f"Unknown video number: {video_num}")


VIDEO_META = {
    1:  {"title": "One Circle",       "duration": 1500, "fg": "single glowing circle"},
    2:  {"title": "Three Circles",    "duration": 1500, "fg": "three colorful circles"},
    3:  {"title": "Wave of Five",     "duration": 1500, "fg": "five circles in a wave"},
    4:  {"title": "Squares March",    "duration": 1500, "fg": "four marching squares"},
    5:  {"title": "Triangles Dance",  "duration": 1500, "fg": "three dancing triangles"},
    6:  {"title": "Shapes Together",  "duration": 1500, "fg": "circle square triangle together"},
    7:  {"title": "Shape Aquarium",   "duration": 1800, "fg": "many colorful shapes floating"},
    8:  {"title": "Dancing Stars",    "duration": 1500, "fg": "glowing stars orbiting"},
    9:  {"title": "Dancing Hearts",   "duration": 1500, "fg": "pink hearts dancing"},
    10: {"title": "Rainbow Circles",  "duration": 1800, "fg": "six colorful circles changing"},
    11: {"title": "Big and Small",    "duration": 1500, "fg": "large and small circles"},
    12: {"title": "Night Shapes",     "duration": 1800, "fg": "pastel shapes on dark background"},
}


def make_meta_en(video_num: int) -> dict:
    m = VIDEO_META[video_num]
    dur_min = m["duration"] // 60
    fg = m["fg"]
    title = m["title"]
    description = (
        f"✨ {title} — {dur_min} Minutes of Dancing Shapes for Babies & Toddlers!\n\n"
        f"Pure visual magic — {fg} moving to gentle music. "
        f"No words, no text — just beautiful shapes in motion. Perfect for any language!\n\n"
        f"🎯 Perfect for:\n"
        f"• Background video during play time\n"
        f"• Calming screen time that stimulates visual development\n"
        f"• Nap time wind-down\n"
        f"• Building shape and color recognition naturally\n\n"
        f"🌈 What your baby sees:\n"
        f"• Smooth, predictable motion patterns — babies love it!\n"
        f"• Beautiful color transitions — never harsh or sudden\n"
        f"• Rhythmic movement synced to gentle music\n"
        f"• No flashing or sudden changes — safe for young eyes\n\n"
        f"Part of our 12-video Dancing Shapes series. "
        f"Each video focuses on different shapes, movements, and moods.\n\n"
        f"🔔 Subscribe → @HappyBearKids1 for weekly educational videos!\n\n"
        f"🎵 Music: Kevin MacLeod (incompetech.com) "
        f"Licensed under Creative Commons Attribution 4.0 "
        f"http://creativecommons.org/licenses/by/4.0/\n\n"
        f"#ShapesForBabies #DancingShapes #BabyVisualStimulation #ToddlerTV "
        f"#HappyBearKids #CalmBabyVideo #ShapeAnimation #EducationalVideo "
        f"#BabyLearning #VisualStimulation #{title.replace(' ', '')}"
    )
    return {
        "title": f"{title} 🔷 Shape Dance for Babies | {dur_min} Min | Happy Bear Kids",
        "description": description,
        "tags": [
            "dancing shapes", "shapes for babies", "baby visual stimulation",
            "shape animation", "calm baby video", "happy bear kids",
            "toddler tv", f"{dur_min} minutes", title.lower(),
            "no talking", "visual learning", "baby background video",
            "colorful shapes", "geometric shapes", "baby tv",
        ],
        "video_type": "dance_shape",
        "language": "en",
        "is_short": False,
        "status": "public",
    }


def make_meta_ar(video_num: int) -> dict:
    m = VIDEO_META[video_num]
    dur_min = m["duration"] // 60
    title = m["title"]
    description = (
        f"✨ {title} — {dur_min} دقيقة من الأشكال الراقصة للرضع والأطفال!\n\n"
        f"سحر بصري خالص — أشكال ملونة ترقص وتتحرك على موسيقى هادئة. "
        f"بدون كلمات أو نصوص — فقط أشكال جميلة في حركة. مناسبة لجميع اللغات!\n\n"
        f"🎯 مثالية لـ:\n"
        f"• فيديو خلفية أثناء وقت اللعب\n"
        f"• وقت الشاشة الهادئ الذي يحفز التطور البصري\n"
        f"• الاسترخاء قبل القيلولة\n"
        f"• بناء التعرف على الأشكال والألوان بشكل طبيعي\n\n"
        f"جزء من سلسلة أشكال الرقص — 12 فيديو ساحر للأشكال.\n\n"
        f"🔔 اشتركوا → @happybearkidsar لفيديوهات تعليمية أسبوعية!\n\n"
        f"🎵 الموسيقى: Kevin MacLeod — رخصة Creative Commons Attribution 4.0\n\n"
        f"#أشكال_للأطفال #رقص_الأشكال #تحفيز_بصري #هابي_بير_كيدز "
        f"#فيديو_هادئ #رسوم_أشكال #تعليم_أطفال #ألوان_للأطفال"
    )
    return {
        "title": f"{title} 🔷 أشكال راقصة للرضع | {dur_min} دقيقة | هابي بير كيدز",
        "description": description,
        "tags": [
            "رقص الأشكال", "أشكال للأطفال", "تحفيز بصري", "هابي بير كيدز",
            "فيديو هادئ للأطفال", "رسوم الأشكال", "تعليم أطفال",
            f"{dur_min} دقيقة", title, "بدون كلام", "تعلم بصري",
        ],
        "video_type": "dance_shape",
        "language": "ar",
        "is_short": False,
        "status": "public",
    }


def make_meta_id(video_num: int) -> dict:
    m = VIDEO_META[video_num]
    dur_min = m["duration"] // 60
    title = m["title"]
    description = (
        f"✨ {title} — {dur_min} Menit Bentuk Menari untuk Bayi & Balita!\n\n"
        f"Keajaiban visual murni — bentuk berwarna menari mengikuti musik lembut. "
        f"Tanpa kata-kata atau teks — hanya bentuk indah yang bergerak. Cocok untuk semua bahasa!\n\n"
        f"🎯 Sempurna untuk:\n"
        f"• Video latar saat waktu bermain\n"
        f"• Waktu layar yang menenangkan dan merangsang perkembangan visual\n"
        f"• Bersiap tidur siang\n"
        f"• Membangun pengenalan bentuk dan warna secara alami\n\n"
        f"Bagian dari Seri Bentuk Menari — 12 video hipnotis.\n\n"
        f"🔔 Subscribe → @happybearkidsin untuk video edukasi mingguan!\n\n"
        f"🎵 Musik: Kevin MacLeod — Creative Commons Attribution 4.0\n\n"
        f"#BentukMenari #BentukUntukBayi #StimulasiVisualBayi #HappyBearKids "
        f"#VideoTenangBayi #AnimasiBentuk #BelajarAnak #WarnaUntukAnak"
    )
    return {
        "title": f"{title} 🔷 Bentuk Menari untuk Bayi | {dur_min} Menit | Happy Bear Kids",
        "description": description,
        "tags": [
            "bentuk menari", "bentuk untuk bayi", "stimulasi visual bayi",
            "animasi bentuk", "video tenang bayi", "happy bear kids",
            f"{dur_min} menit", title.lower(), "tanpa suara", "belajar visual",
        ],
        "video_type": "dance_shape",
        "language": "id",
        "is_short": False,
        "status": "public",
    }


def generate_thumbnail(video_num: int, out_path: Path) -> bool:
    if out_path.exists():
        return True
    try:
        key = TOGETHER_KEY_FILE.read_text().strip()
    except Exception:
        print(f"    ! No Together.ai key")
        return False

    m = VIDEO_META[video_num]
    fg = m["fg"]
    prompt = (
        f"children's YouTube thumbnail, {fg}, "
        f"vivid neon colors on dark background, glowing geometric shapes, "
        f"smooth colorful animation, no text, no letters, no words, 1280x720"
    )

    try:
        import urllib.request
        payload = json.dumps({
            "model": TOGETHER_MODEL,
            "prompt": prompt,
            "width": 1280, "height": 720, "steps": 4, "n": 1,
        }).encode()
        req = urllib.request.Request(
            TOGETHER_URL,
            data=payload,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read())
        b64 = data["data"][0]["b64_json"]
        out_path.write_bytes(base64.b64decode(b64))
        print(f"    ✓ thumb → {out_path.name}")
        return True
    except Exception as e:
        print(f"    ! thumb failed: {e}")
        return False


def render_video(video_num: int, force: bool, dry_run: bool) -> Path | None:
    m        = VIDEO_META[video_num]
    slug     = f"dance_shape_{video_num:02d}_{DATE_STR}.mp4"
    out_path = QUEUE_EN / slug

    if out_path.exists() and not force:
        sz = out_path.stat().st_size / 1024 / 1024
        print(f"  skip {slug} ({sz:.0f}MB)")
        return out_path

    props, composition_id, duration_sec = make_config(video_num)

    print(f"\n  Rendering Video {video_num}: {m['title']} ({duration_sec//60} min) ...")
    if dry_run:
        print(f"    [DRY RUN] composition={composition_id}")
        return out_path

    QUEUE_EN.mkdir(parents=True, exist_ok=True)
    cmd = [
        "npx", "remotion", "render",
        "src/index.ts", composition_id,
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


def publish_to_all_channels(en_mp4: Path, video_num: int, force: bool, dry_run: bool):
    props_en, composition_id, duration_sec = make_config(video_num)
    en_music = props_en["musicFile"]
    stem     = en_mp4.stem

    for lang, queue in [("en", QUEUE_EN), ("ar", QUEUE_AR), ("id", QUEUE_ID)]:
        queue.mkdir(parents=True, exist_ok=True)
        target_stem = stem if lang == "en" else f"{stem}_{lang}"
        target      = queue / f"{target_stem}.mp4"

        if lang != "en" and not target.exists() and not dry_run:
            lang_music = alt_music(en_music, video_num - 1, lang)
            props_lang = dict(props_en)
            props_lang["musicFile"] = lang_music
            print(f"\n    Rendering Video {video_num} ({lang.upper()}) → {target.name}")
            cmd = [
                "npx", "remotion", "render",
                "src/index.ts", composition_id,
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
            fn_map = {"en": make_meta_en, "ar": make_meta_ar, "id": make_meta_id}
            meta = fn_map[lang](video_num)
            if not dry_run:
                with open(meta_path, "w") as f:
                    yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
                print(f"    meta {lang.upper()} → {meta_path.name}")
            else:
                print(f"    [DRY RUN] meta {lang.upper()} → {meta_path.name}")

        if not thumb_path.exists() and not dry_run:
            time.sleep(0.5)
            generate_thumbnail(video_num, thumb_path)


def main():
    parser = argparse.ArgumentParser(
        description="Generate DanceShapeLong videos (12-video Dancing Shapes series)"
    )
    parser.add_argument("--videos",    nargs="+", type=int, default=list(range(1, 13)),
                        help="Video numbers 1-12 (default: all)")
    parser.add_argument("--dry-run",   action="store_true")
    parser.add_argument("--force",     action="store_true", help="Re-render existing")
    parser.add_argument("--regen-meta", action="store_true",
                        help="Regenerate meta+thumb only (skip render)")
    args = parser.parse_args()

    print(f"=== Dancing Shapes — {len(args.videos)} videos ===\n")

    for vnum in args.videos:
        if vnum not in VIDEO_META:
            print(f"Unknown video number {vnum} (valid: 1-12)")
            continue

        m = VIDEO_META[vnum]
        print(f"[Video {vnum}] {m['title']} ({m['duration']//60} min)")

        slug = f"dance_shape_{vnum:02d}_{DATE_STR}.mp4"
        mp4  = QUEUE_EN / slug

        if args.regen_meta:
            if mp4.exists():
                publish_to_all_channels(mp4, vnum, args.force, args.dry_run)
            else:
                print(f"  ! No MP4 at {mp4}")
            continue

        mp4 = render_video(vnum, args.force, args.dry_run)
        if mp4 and (mp4.exists() or args.dry_run):
            publish_to_all_channels(mp4, vnum, args.force, args.dry_run)

    print("\n=== Done ===")


if __name__ == "__main__":
    main()
