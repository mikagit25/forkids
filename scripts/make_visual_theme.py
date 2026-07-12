#!/usr/bin/env python3
"""
Generate AI-illustrated visual theme sleep videos for Calm Classics.

Pipeline:
  1. Generate 10 FLUX images per theme (Together.ai, 2048×1152)
  2. Ken Burns motion (zoom/pan) on each image → 30s clip (FFmpeg)
  3. Crossfade concat → ~4.5 min seamless visual loop
  4. Stream-loop + classical music overlay → 1h / 3h / 8h video
  5. Write meta YAML + generate thumbnail → output/queue_id/

Usage:
  python3 scripts/make_visual_theme.py --theme aurora_borealis
  python3 scripts/make_visual_theme.py --theme aurora_borealis --durations 1 3 8
  python3 scripts/make_visual_theme.py --all --durations 1
  python3 scripts/make_visual_theme.py --list-themes
  python3 scripts/make_visual_theme.py --regen-images --theme zen_garden
  python3 scripts/make_visual_theme.py --regen-loop  --theme cherry_blossoms
  python3 scripts/make_visual_theme.py --dry-run --all
"""
import argparse
import base64
import logging
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

ROOT             = Path(__file__).resolve().parent.parent
QUEUE_ID         = ROOT / "output" / "queue_id"
VISUAL_LOOPS_DIR = ROOT / "output" / "_visual_loops"
ASSETS_DIR       = ROOT / "assets" / "visual_themes"
MUSIC_DIR        = ROOT / "assets" / "music" / "classical" / "Music"
TOGETHER_KEY_FILE = ROOT / "credentials" / "together_api_key.txt"
DATE_STR         = datetime.now().strftime("%Y%m%d")

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ── Clip / motion constants ────────────────────────────────────────────────────
CLIP_DURATION  = 30    # seconds per Ken Burns clip
XFADE_DURATION = 3     # seconds of crossfade between clips
FADE_SECS      = 2     # global fade in at start of loop
FPS            = 25
N_IMAGES       = 10    # images per theme

# Ken Burns motion sequence (cycles through N_IMAGES)
MOTIONS = ["zoom_in", "pan_right", "zoom_out", "pan_left",
           "zoom_in", "pan_up", "zoom_out", "pan_down",
           "zoom_in", "pan_right"]

# ── Theme catalogue ────────────────────────────────────────────────────────────
THEMES: dict[str, dict] = {

    "aurora_borealis": {
        "title": "Aurora Borealis 🌌 {duration} | Classical Music for Sleep | Calm Classics",
        "desc": (
            "Drift into peaceful sleep beneath the dancing northern lights. "
            "{duration} of stunning aurora borealis visuals paired with timeless classical music. "
            "Let the vivid greens and purples of the aurora carry you into deep, restful sleep.\n\n"
            "🎵 Music: Frédéric Chopin — Nocturnes | Ludwig van Beethoven — Moonlight Sonata\n"
            "🎨 Visuals: AI-generated aurora borealis scenes\n"
            "📜 All recordings: Public Domain (Musopen.org)\n\n"
            "Perfect for: sleep, relaxation, meditation, stress relief, studying\n\n"
            "Subscribe for nightly classical music programs → @ClassicalNightRelax\n\n"
            "#AuroraBorealis #NorthernLights #SleepMusic #ClassicalMusic #CalmClassics "
            "#SleepingMusic #RelaxingMusic #MeditationMusic #StudyMusic #ClassicalNightRelax"
        ),
        "tags": ["aurora borealis", "northern lights", "sleep music", "classical music",
                 "calm classics", "relaxing music", "chopin", "beethoven", "moonlight sonata",
                 "sleep aid", "study music", "meditation", "insomnia relief"],
        "thumb_prompt": (
            "aurora borealis vivid green and purple northern lights dancing above snow-covered "
            "pine forest, frozen lake reflection, stars, breathtaking nature photography, "
            "cinematic, no text"
        ),
        "flux_prompts": [
            "aurora borealis vivid emerald green and deep purple northern lights dancing above snow-covered pine forest, frozen lake mirror reflection below, thousands of stars, long exposure night photography, ultra detailed, cinematic 16:9",
            "northern lights magenta and teal aurora curtains sweeping above arctic tundra, snowfields glittering, crisp winter night sky, moonlit, photorealistic landscape photography, 16:9",
            "aurora borealis yellow-green ribbons of light above Norwegian fjord, dark water reflection, distant mountains silhouetted, breathtaking, ultra sharp, 16:9",
            "northern lights triple color aurora green pink purple above Icelandic volcanic landscape, steam vents glowing, dramatic composition, astrophotography, 16:9",
            "aurora borealis seen from frozen lake surface perspective, ice patterns in foreground, towering green light pillars above pine trees, star trails, 16:9",
            "northern lights dancing above glass igloo hotel in Lapland, warm amber glow from interior, snow dusted trees, magical atmosphere, 16:9",
            "aurora borealis spiral vortex green and white above Arctic Ocean, sea ice in foreground, polar night, cinematic photography, 16:9",
            "northern lights curtains above lonely wooden cabin in snowy Finnish forest, warm window light, chimney smoke, peaceful winter solitude, 16:9",
            "aurora borealis faint pink and green light above Scandinavian mountain range, full moon illuminating snow peaks, vast dark sky, 16:9",
            "northern lights exploding green aurora above frozen waterfall, ice formations glittering, remote wilderness, dramatic angle, 16:9",
        ],
        "music_files": [
            "Nocturne in E flat major, Op. 9 no. 2.mp3",
            "Nocturne in B flat minor, Op. 9 no. 1.mp3",
            "Piano Sonata no. 14 in C#m 'Moonlight', Op. 27 no. 2 - I. Adagio sostenuto.mp3",
            "Fantasia on a Theme by Thomas Tallis.mp3",
        ],
        "mood": "sleep",
        "video_type": "visual_theme",
    },

    "cherry_blossoms": {
        "title": "Cherry Blossoms 🌸 {duration} | Japanese Classical Music | Calm Classics",
        "desc": (
            "Float beneath a canopy of cherry blossoms with {duration} of serene classical music. "
            "AI-illustrated sakura scenes in full bloom, paired with gentle piano and chamber pieces "
            "perfect for sleep, meditation, or quiet focus.\n\n"
            "🎵 Music: Frédéric Chopin — Nocturnes | W.A. Mozart — Serenade in G Major\n"
            "🎨 Visuals: AI-generated cherry blossom scenes\n"
            "📜 All recordings: Public Domain (Musopen.org)\n\n"
            "Perfect for: sleep, relaxation, study, meditation, spring ambiance\n\n"
            "Subscribe → @ClassicalNightRelax\n\n"
            "#CherryBlossoms #Sakura #SleepMusic #ClassicalMusic #CalmClassics "
            "#JapaneseAmbiance #RelaxingMusic #Chopin #Mozart #ClassicalNightRelax"
        ),
        "tags": ["cherry blossoms", "sakura", "japanese", "sleep music", "classical music",
                 "calm classics", "chopin nocturnes", "mozart", "spring ambiance",
                 "relaxing music", "meditation", "study music", "peaceful"],
        "thumb_prompt": (
            "Japanese cherry blossom sakura tree in full bloom, pink petals falling like snow, "
            "peaceful garden path, soft spring sunlight filtering through, dreamy atmosphere, "
            "cinematic photography, no text"
        ),
        "flux_prompts": [
            "Japanese cherry blossom avenue sakura trees in full pink bloom, petals floating like snow, soft spring morning light, people with parasols distant, dreamy depth of field, 16:9",
            "sakura cherry blossoms reflected in still Japanese garden pond, koi fish, stone lantern, temple pagoda distant, golden hour soft light, serene, 16:9",
            "cherry blossom tunnel hanami path at night, paper lanterns glowing warm orange, pink petals illuminated, magical atmosphere, Japan, 16:9",
            "sakura petals falling like pink snow over ancient stone steps, Japanese moss garden, wooden temple gate, spring mist, soft focus, 16:9",
            "aerial view of Japanese city neighborhood entirely covered in cherry blossom pink, rooftops barely visible, rivers of sakura trees, springtime from above, 16:9",
            "single cherry blossom branch close-up against soft sky, sunlight through translucent pink petals, macro photography, pastel bokeh background, 16:9",
            "Mount Fuji framed by blooming cherry blossom trees, pink foreground blue mountain white snow cap, classic Japan landscape, 16:9",
            "Japanese tea house surrounded by sakura trees in full bloom, wooden veranda, paper screen doors, stone garden, tranquil, 16:9",
            "cherry blossoms at dawn over ancient Japanese bridge, mist rising from river below, warm pink and gold tones, watercolor-like atmosphere, 16:9",
            "sakura petal close-up detail, dewdrops on pink petals, soft bokeh spring background, macro nature photography, delicate, 16:9",
        ],
        "music_files": [
            "Nocturne in E flat major, Op. 9 no. 2.mp3",
            "Mozart - Serenade in G Major - I. Romance.mp3",
            "Mozart - Serenade in G Major - II. Minuet.mp3",
            "Arabesque No. 1. Andantino con moto.mp3",
        ],
        "mood": "sleep",
        "video_type": "visual_theme",
    },

    "mountain_snow": {
        "title": "Mountain Snow ⛰️ {duration} | Classical Music for Deep Sleep | Calm Classics",
        "desc": (
            "Rest beside majestic snow-capped mountains with {duration} of grand classical music. "
            "Breathtaking alpine landscapes rendered in stunning detail, perfectly matched with "
            "orchestral masterpieces for the deepest, most restful sleep.\n\n"
            "🎵 Music: Ralph Vaughan Williams — Fantasia on a Theme by Thomas Tallis | Chopin Nocturnes\n"
            "🎨 Visuals: AI-generated alpine mountain scenes\n"
            "📜 All recordings: Public Domain (Musopen.org)\n\n"
            "Perfect for: deep sleep, relaxation, meditation, stress relief\n\n"
            "Subscribe → @ClassicalNightRelax\n\n"
            "#MountainSnow #AlpineLandscape #SleepMusic #ClassicalMusic #CalmClassics "
            "#VaughanWilliams #DeepSleep #RelaxingMusic #ClassicalNightRelax"
        ),
        "tags": ["mountain snow", "alpine", "winter landscape", "sleep music", "classical music",
                 "calm classics", "vaughan williams", "chopin", "deep sleep",
                 "relaxing music", "meditation", "stress relief", "nature"],
        "thumb_prompt": (
            "majestic snow-capped mountain peaks at sunrise, alpenglow pink and orange on glaciers, "
            "dark pine forest below, pristine alpine lake reflection, breathtaking, "
            "cinematic photography, no text"
        ),
        "flux_prompts": [
            "majestic snow-capped alpine mountain peaks at golden sunrise, alpenglow pink and orange on glaciers, dark pine forest reflection in clear mountain lake, breathtaking landscape, 16:9",
            "winter mountain range panorama, multiple peaks covered in fresh white snow, dramatic clouds parting to reveal blue sky, scale and grandeur, cinematic, 16:9",
            "lone mountain cabin in deep snow, warm amber light in window, pine trees bowed with snow, dramatic peaks behind, winter solitude, 16:9",
            "aerial view above clouds looking up at snow-capped mountain summit, cloud sea below, sunlit peak, above the storm, serene and vast, 16:9",
            "mountain valley in winter at night, full moon illuminating snow-covered slopes, frozen river below, stars above, silent wilderness, 16:9",
            "snowflakes falling in slow motion in mountain forest, trees frosted white, soft blue light, peaceful winter forest atmosphere, 16:9",
            "mountain waterfall partially frozen in winter, ice formations, snow-covered rocks, mist rising, dramatic lighting, 16:9",
            "alpine meadow under fresh snow, high peaks surrounding, blue sky with wispy clouds, utter silence and stillness implied, 16:9",
            "mountain pass at dusk, snow glowing lavender and pink in last light, vast empty landscape, single winding road disappearing, 16:9",
            "close-up fresh snow crystals on pine needles, macro photography, mountainside background soft bokeh, pristine winter detail, 16:9",
        ],
        "music_files": [
            "Fantasia on a Theme by Thomas Tallis.mp3",
            "Nocturne in B flat minor, Op. 9 no. 1.mp3",
            "Piano Sonata no. 14 in C#m 'Moonlight', Op. 27 no. 2 - I. Adagio sostenuto.mp3",
        ],
        "mood": "sleep",
        "video_type": "visual_theme",
    },

    "fireplace_cabin": {
        "title": "Cozy Fireplace 🔥 {duration} | Classical Music for Sleep | Calm Classics",
        "desc": (
            "Settle in by a warm, crackling fireplace for {duration} of soothing classical music. "
            "Cozy cabin interiors with glowing embers and soft candlelight — the perfect atmosphere "
            "for winding down, reading, or drifting off to sleep.\n\n"
            "🎵 Music: Frédéric Chopin — Nocturnes & Mazurkas | Debussy — Arabesque\n"
            "🎨 Visuals: AI-generated cozy fireplace cabin scenes\n"
            "📜 All recordings: Public Domain (Musopen.org)\n\n"
            "Perfect for: sleep, reading, cozy evenings, winter ambiance, relaxation\n\n"
            "Subscribe → @ClassicalNightRelax\n\n"
            "#Fireplace #CozyVibes #SleepMusic #ClassicalMusic #CalmClassics "
            "#CozyCabin #WinterAmbiance #Chopin #RelaxingMusic #ClassicalNightRelax"
        ),
        "tags": ["fireplace", "cozy cabin", "winter ambiance", "sleep music", "classical music",
                 "calm classics", "chopin", "debussy", "cozy vibes",
                 "relaxing music", "reading ambiance", "hygge", "warm"],
        "thumb_prompt": (
            "cozy fireplace in rustic log cabin, crackling fire with warm amber glow, "
            "armchair with blanket nearby, snow falling outside window, warm and inviting, "
            "cinematic photography, no text"
        ),
        "flux_prompts": [
            "cozy stone fireplace in rustic log cabin, crackling fire amber glow, armchair with wool blanket, books on shelf, snow falling outside window, warm hygge atmosphere, 16:9",
            "close-up fireplace flames dancing, embers glowing orange and red, occasional sparks, warm cinematic color grading, hypnotic fire, 16:9",
            "cabin living room at night, roaring fireplace, wooden beams, candles on mantle, frost on window, steaming mug on table, intimate and warm, 16:9",
            "fireplace and Christmas decorations in cozy interior, soft fairy lights, pine branches, warm amber tones, peaceful winter evening, 16:9",
            "mountain cabin bedroom with small corner fireplace glowing, soft bedside lamp, snow outside large window, peaceful sleeping atmosphere, 16:9",
            "library room with fireplace, leather armchair, floor-to-ceiling bookshelves, warm lamp light, rain on windows, scholarly coziness, 16:9",
            "evening fireplace view from outside through cabin window, warm amber glow inside, snow falling, pine trees silhouetted, inviting scene, 16:9",
            "fireplace embers dying down late at night, soft orange glow, room in shadow, peaceful quietude, long exposure, 16:9",
            "Swedish farmhouse interior, white walls, birch logs fire, minimalist hygge aesthetic, candles, wool throw, calm winter evening, 16:9",
            "close-up crackling log fire, flames licking, embers pulsing, warmth implied through warm color palette, hypnotic and calming, 16:9",
        ],
        "music_files": [
            "Nocturne in E flat major, Op. 9 no. 2.mp3",
            "Nocturne in B flat minor, Op. 9 no. 1.mp3",
            "Arabesque No. 1. Andantino con moto.mp3",
            "Mazurka in A flat major, B. 85.mp3",
        ],
        "mood": "sleep",
        "video_type": "visual_theme",
    },

    "zen_garden": {
        "title": "Zen Garden 🪨 {duration} | Classical Music for Focus | Calm Classics",
        "desc": (
            "Find stillness in the timeless beauty of a Japanese zen garden. "
            "{duration} of meditative classical music paired with raked sand, stone lanterns, "
            "and bonsai — ideal for deep focus, meditation, or peaceful sleep.\n\n"
            "🎵 Music: Johann Sebastian Bach — Cello Suite No. 1 | Debussy — Arabesque\n"
            "🎨 Visuals: AI-generated Japanese zen garden scenes\n"
            "📜 All recordings: Public Domain (Musopen.org)\n\n"
            "Perfect for: focus, meditation, yoga, sleep, study\n\n"
            "Subscribe → @ClassicalNightRelax\n\n"
            "#ZenGarden #Japanese #FocusMusic #ClassicalMusic #CalmClassics "
            "#Meditation #Bach #Debussy #StudyMusic #ClassicalNightRelax"
        ),
        "tags": ["zen garden", "japanese garden", "focus music", "classical music",
                 "calm classics", "bach", "debussy", "meditation",
                 "study music", "yoga", "mindfulness", "peaceful"],
        "thumb_prompt": (
            "Japanese zen garden with raked white sand patterns, large mossy stones, "
            "bamboo water fountain, stone lantern, soft morning mist, peaceful and serene, "
            "cinematic photography, no text"
        ),
        "flux_prompts": [
            "Japanese zen garden at dawn, perfectly raked white sand with spiral patterns around mossy stones, bamboo water fountain, morning mist, serene tranquility, 16:9",
            "stone lantern in Japanese garden, moss covered, filtered light through maple trees, autumn colors reflected in still pond, timeless peace, 16:9",
            "bonsai tree in ceramic pot against shoji screen window, soft light, traditional Japanese interior, tea ceremony setting, minimalist, 16:9",
            "bamboo grove pathway in Japanese garden, shafts of light between tall green bamboo, stone stepping stones, meditative quiet, 16:9",
            "koi pond in Zen garden, colorful fish beneath water lily pads, stone bridge, cherry blossom petals on water, 16:9",
            "sand meditation garden top-down view, perfect concentric raked circles, few select stones, mathematical precision, calming minimalism, 16:9",
            "Japanese maple tree with red autumn leaves above Zen garden pond, reflection, stone lantern, traditional wooden bench, 16:9",
            "moss covered stone garden path winding through ancient Japanese temple grounds, dawn mist, wooden torii gate distant, 16:9",
            "minimalist zen interior, tatami floor, single flower in vase, view into garden through open shoji door, evening light, 16:9",
            "Zen rock garden at sunset, long shadows across raked sand, few stones casting purple shadows, meditative emptiness, 16:9",
        ],
        "music_files": [
            "Cello Suite no. 1 - Prelude in G, BWV 1007.mp3",
            "Arabesque No. 1. Andantino con moto.mp3",
            "Mozart - Serenade in G Major - I. Romance.mp3",
            "Nocturne in E flat major, Op. 9 no. 2.mp3",
        ],
        "mood": "focus",
        "video_type": "visual_theme",
    },

    "lavender_fields": {
        "title": "Lavender Fields 💜 {duration} | Classical Music for Sleep | Calm Classics",
        "desc": (
            "Dream among endless rows of purple lavender stretching to the horizon. "
            "{duration} of soothing classical music paired with the most tranquil Provence landscapes — "
            "the perfect sleep companion.\n\n"
            "🎵 Music: Frédéric Chopin — Nocturnes | W.A. Mozart — Serenade in G Major\n"
            "🎨 Visuals: AI-generated lavender field scenes\n"
            "📜 All recordings: Public Domain (Musopen.org)\n\n"
            "Perfect for: sleep, relaxation, meditation, stress relief, nature ambiance\n\n"
            "Subscribe → @ClassicalNightRelax\n\n"
            "#LavenderFields #Provence #SleepMusic #ClassicalMusic #CalmClassics "
            "#RelaxingMusic #NatureAmbiance #Chopin #ClassicalNightRelax"
        ),
        "tags": ["lavender fields", "provence", "france", "sleep music", "classical music",
                 "calm classics", "chopin", "mozart", "purple", "nature ambiance",
                 "relaxing music", "meditation", "spring", "flowers"],
        "thumb_prompt": (
            "endless lavender fields in Provence France, purple rows to the horizon, "
            "old stone farmhouse in distance, golden sunset light, warm summer atmosphere, "
            "cinematic photography, no text"
        ),
        "flux_prompts": [
            "endless lavender fields Provence France stretching to rolling hills horizon, purple rows with path between, old stone farmhouse distant, golden hour sunset, warm summer light, 16:9",
            "lavender fields at dawn, mist over purple blooms, dew drops on flowers, soft pink light, quiet French countryside morning, 16:9",
            "aerial view lavender fields Valensole Plateau, purple and green stripes pattern, ancient village nestled among fields, summer, 16:9",
            "beekeeper among lavender in full bloom, thousands of bees, golden honey light, gentle summer afternoon, Provence, 16:9",
            "lavender bouquets drying in old Provençal barn, stone walls, wooden beams, sunlight through gaps, aromatic atmosphere, 16:9",
            "lavender field at twilight, purple silhouettes against deep blue sky, first stars appearing, cicadas implied, 16:9",
            "single lavender stem macro, purple flower spikes with dewdrop, soft bokeh field background, morning light, 16:9",
            "stone path through lavender garden, old French village beyond, butterflies on blooms, summer afternoon, 16:9",
            "lavender field meeting sunflower field, purple and yellow side by side, blue Provence sky, warm contrast, 16:9",
            "Provence lavender market, bundles of dried lavender, old woman vendor, stone square, summer day, 16:9",
        ],
        "music_files": [
            "Nocturne in E flat major, Op. 9 no. 2.mp3",
            "Mozart - Serenade in G Major - I. Romance.mp3",
            "Nocturne in B flat minor, Op. 9 no. 1.mp3",
            "Arabesque No. 1. Andantino con moto.mp3",
        ],
        "mood": "sleep",
        "video_type": "visual_theme",
    },

    "deep_space": {
        "title": "Deep Space 🌌 {duration} | Classical Music for Sleep | Calm Classics",
        "desc": (
            "Float through the infinite cosmos with {duration} of transcendent classical music. "
            "Stunning nebulae, star fields, and galaxies rendered in breathtaking detail — "
            "the perfect backdrop for deep sleep or profound meditation.\n\n"
            "🎵 Music: Ralph Vaughan Williams — Fantasia on a Theme by Thomas Tallis | Beethoven — Moonlight Sonata\n"
            "🎨 Visuals: AI-generated deep space imagery\n"
            "📜 All recordings: Public Domain (Musopen.org)\n\n"
            "Perfect for: deep sleep, meditation, relaxation, stress relief\n\n"
            "Subscribe → @ClassicalNightRelax\n\n"
            "#DeepSpace #Nebula #SleepMusic #ClassicalMusic #CalmClassics "
            "#Cosmos #VaughanWilliams #Beethoven #MeditationMusic #ClassicalNightRelax"
        ),
        "tags": ["deep space", "nebula", "cosmos", "sleep music", "classical music",
                 "calm classics", "vaughan williams", "beethoven", "meditation",
                 "space ambiance", "stars", "galaxy", "relaxing"],
        "thumb_prompt": (
            "deep space nebula with vivid purple and blue gas clouds, thousands of stars, "
            "distant galaxies, cosmic scale and grandeur, hubble-style photography, no text"
        ),
        "flux_prompts": [
            "deep space Orion nebula vivid purple blue teal gas clouds, thousands of bright stars embedded, cosmic scale, Hubble telescope style ultra detailed, 16:9",
            "spiral galaxy seen from above, arms of stars swirling, dust lanes, central bulge glowing, deep black space background, cinematic astronomy, 16:9",
            "star forming region in nebula, pillars of creation style, golden and rust dust columns backlit by young stars, dramatic scale, 16:9",
            "milky way galaxy arc above desert rock formations at night, shooting stars, planet rise, astrophotography masterpiece, 16:9",
            "deep space star field, thousands of colored stars from blue giant to red dwarf, depth and parallax implied, serene infinite vista, 16:9",
            "solar system planets aligned in space, Saturn rings prominent, Jupiter bands, deep star field, cosmic perspective, 16:9",
            "supernova remnant expanding in space, delicate purple and blue filaments of gas and light, perfectly detailed, 16:9",
            "twin stars binary system orbiting each other, plasma exchange arc between them, nebula background, dramatic space art, 16:9",
            "view from orbit above Earth at night, city lights below, aurora australis glowing green, stars above atmosphere, 16:9",
            "deep space black hole with accretion disk glowing, gravitational lensing effect, orange and white plasma ring, dramatic and awe-inspiring, 16:9",
        ],
        "music_files": [
            "Fantasia on a Theme by Thomas Tallis.mp3",
            "Piano Sonata no. 14 in C#m 'Moonlight', Op. 27 no. 2 - I. Adagio sostenuto.mp3",
            "Nocturne in B flat minor, Op. 9 no. 1.mp3",
        ],
        "mood": "sleep",
        "video_type": "visual_theme",
    },

    "autumn_forest": {
        "title": "Autumn Forest 🍂 {duration} | Classical Music for Sleep | Calm Classics",
        "desc": (
            "Walk through a golden autumn forest with {duration} of warm, soothing classical music. "
            "Amber and crimson leaves, misty forest paths, and the quiet magic of fall — "
            "a perfect companion for winding down and drifting into peaceful sleep.\n\n"
            "🎵 Music: Frédéric Chopin — Nocturnes | Pyotr Tchaikovsky — Swan Lake\n"
            "🎨 Visuals: AI-generated autumn forest scenes\n"
            "📜 All recordings: Public Domain (Musopen.org)\n\n"
            "Perfect for: sleep, relaxation, autumn ambiance, meditation, reading\n\n"
            "Subscribe → @ClassicalNightRelax\n\n"
            "#AutumnForest #FallColors #SleepMusic #ClassicalMusic #CalmClassics "
            "#AutumnVibes #Chopin #Tchaikovsky #RelaxingMusic #ClassicalNightRelax"
        ),
        "tags": ["autumn forest", "fall colors", "forest", "sleep music", "classical music",
                 "calm classics", "chopin", "tchaikovsky", "autumn ambiance",
                 "relaxing music", "nature", "meditation", "cozy"],
        "thumb_prompt": (
            "golden autumn forest with sunlight rays through amber and red maple leaves, "
            "misty forest path with fallen leaves, warm fall colors, magical atmosphere, "
            "cinematic photography, no text"
        ),
        "flux_prompts": [
            "golden autumn forest cathedral, sunlight rays through amber red maple canopy, fallen leaves on ground, mist in distance, magical light, 16:9",
            "autumn forest path covered in orange leaves, trees on both sides turning red and gold, misty morning light, peaceful solitude, 16:9",
            "forest stream in autumn, leaves floating on water, reflected colors of fall, stones mossy, gentle current, 16:9",
            "Japanese momiji maple forest at peak autumn color, red and orange canopy, temple steps covered in leaves, 16:9",
            "aerial view autumn forest, patchwork of red orange yellow green, winding river through, scale and beauty, 16:9",
            "single oak tree in field at golden hour, all leaves burning orange, long shadow, dramatic autumn sky, 16:9",
            "autumn forest at night, full moon through bare branches, last leaves clinging, frost beginning, 16:9",
            "beech forest in autumn, smooth grey trunks, golden yellow leaf carpet, shafts of afternoon light, 16:9",
            "autumn leaves macro close-up, veins visible, colors from yellow to deep red, moisture drops, 16:9",
            "misty autumn morning in deciduous forest, deer visible in distance, dew on spider webs between branches, ethereal atmosphere, 16:9",
        ],
        "music_files": [
            "Nocturne in B flat minor, Op. 9 no. 1.mp3",
            "Nocturne in E flat major, Op. 9 no. 2.mp3",
            "Swan Lake Op.20 - Act II Pt.1.mp3",
            "Swan Lake Op.20 - Act II Concl.mp3",
        ],
        "mood": "sleep",
        "video_type": "visual_theme",
    },
}


# ── Together.ai image generation ───────────────────────────────────────────────

TOGETHER_URL   = "https://api.together.xyz/v1/images/generations"
TOGETHER_MODEL = "black-forest-labs/FLUX.1-schnell"


def generate_image(prompt: str, api_key: str,
                   width: int = 1344, height: int = 768) -> Optional[bytes]:
    """Generate image via Together.ai FLUX.1-schnell."""
    try:
        import requests as _req
    except ImportError:
        log.error("pip install requests")
        return None
    try:
        r = _req.post(
            TOGETHER_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": TOGETHER_MODEL, "prompt": prompt,
                  "width": width, "height": height, "steps": 4, "n": 1},
            timeout=120,
        )
        if r.status_code != 200:
            try:
                msg = r.json().get("error", {}).get("message", r.text[:200])
            except Exception:
                msg = r.text[:200]
            log.error(f"Together API {r.status_code}: {msg}")
            return None
        item = r.json()["data"][0]
        b64 = item.get("b64_json")
        if b64:
            return base64.b64decode(b64)
        url = item.get("url")
        if url:
            rr = _req.get(url, timeout=60)
            return rr.content if rr.status_code == 200 else None
    except Exception as e:
        log.error(f"generate_image error: {e}")
        return None


def ensure_images(theme: str, theme_cfg: dict, api_key: str,
                  force: bool = False, dry_run: bool = False) -> list[Path]:
    """Generate and cache theme images. Returns list of image paths."""
    img_dir = ASSETS_DIR / theme
    img_dir.mkdir(parents=True, exist_ok=True)

    prompts = theme_cfg["flux_prompts"]
    paths: list[Path] = []

    for i, prompt in enumerate(prompts):
        img_path = img_dir / f"frame_{i:02d}.png"
        paths.append(img_path)

        if img_path.exists() and not force:
            log.info(f"  [img {i:02d}] cached")
            continue

        if dry_run:
            log.info(f"  [img {i:02d}] [DRY RUN] would generate")
            paths[-1] = None
            continue

        log.info(f"  [img {i:02d}] generating...")
        retries = 3
        data = None
        for attempt in range(retries):
            data = generate_image(prompt, api_key)
            if data:
                break
            if attempt < retries - 1:
                wait = 2 ** attempt + 1
                log.info(f"  [img {i:02d}] retrying in {wait}s...")
                time.sleep(wait)

        if data:
            img_path.write_bytes(data)
            log.info(f"  [img {i:02d}] saved ({len(data)//1024}KB)")
        else:
            log.warning(f"  [img {i:02d}] FAILED — skipping")
            paths[-1] = None  # mark as missing

        time.sleep(1.0)  # rate limit courtesy

    return [p for p in paths if p is not None and p.exists()]


# ── Ken Burns clip generation ──────────────────────────────────────────────────

def _motion_vf(motion: str, duration: int = CLIP_DURATION) -> str:
    """Build FFmpeg vf string for Ken Burns motion."""
    total_frames = duration * FPS

    # Input images are 1344x768. Scale to 2688x1536 (2x) for zoom room.
    # zoompan crops to 1920x1080 from the scaled canvas.
    scale = "scale=2688:1536"

    if motion == "zoom_in":
        z = "min(zoom+0.0006,1.5)"
        x = "iw/2-(iw/zoom/2)"
        y = "ih/2-(ih/zoom/2)"
    elif motion == "zoom_out":
        z = "if(eq(on,0),1.5,max(zoom-0.0006,1.0))"
        x = "iw/2-(iw/zoom/2)"
        y = "ih/2-(ih/zoom/2)"
    elif motion == "pan_right":
        z = "1.4"
        x = f"min(on*(iw-iw/zoom)/{total_frames-1},iw-iw/zoom)"
        y = "ih/2-(ih/zoom/2)"
    elif motion == "pan_left":
        z = "1.4"
        x = f"max((iw-iw/zoom)-on*(iw-iw/zoom)/{total_frames-1},0)"
        y = "ih/2-(ih/zoom/2)"
    elif motion == "pan_up":
        z = "1.4"
        x = "iw/2-(iw/zoom/2)"
        y = f"max((ih-ih/zoom)-on*(ih-ih/zoom)/{total_frames-1},0)"
    elif motion == "pan_down":
        z = "1.4"
        x = "iw/2-(iw/zoom/2)"
        y = f"min(on*(ih-ih/zoom)/{total_frames-1},ih-ih/zoom)"
    else:
        z = "1.0"
        x = "0"
        y = "0"

    zp = f"zoompan=z='{z}':x='{x}':y='{y}':d={total_frames}:s=1920x1080:fps={FPS}"
    return f"{scale},{zp}"


def make_ken_burns_clip(img_path: Path, out_path: Path,
                        motion: str = "zoom_in",
                        duration: int = CLIP_DURATION) -> bool:
    """Create a Ken Burns motion clip from a static image."""
    vf = _motion_vf(motion, duration)
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(img_path),
        "-t", str(duration),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-pix_fmt", "yuv420p",
        "-an",
        str(out_path),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if r.returncode != 0 or not out_path.exists():
        log.error(f"  Ken Burns failed ({motion}): {r.stderr[-300:]}")
        return False
    return True


# ── Loop assembly with xfade ───────────────────────────────────────────────────

def concat_with_xfade(clip_paths: list[Path], out_path: Path,
                       xfade_dur: int = XFADE_DURATION,
                       clip_dur: int = CLIP_DURATION) -> bool:
    """
    Concatenate clips with xfade crossfade transitions.
    Total loop duration ≈ N * (clip_dur - xfade_dur) + xfade_dur
    """
    n = len(clip_paths)
    if n == 0:
        return False
    if n == 1:
        import shutil
        shutil.copy(clip_paths[0], out_path)
        return True

    inputs = []
    for p in clip_paths:
        inputs += ["-i", str(p)]

    # Build xfade filter chain
    step = clip_dur - xfade_dur  # 30 - 3 = 27 seconds between xfade starts
    filter_parts = []
    prev_label = "[0:v]"

    for i in range(1, n):
        offset = i * step
        cur_label = f"[0:v]" if i == 1 else f"[v{i-1:02d}]"
        next_label = f"[v{i:02d}]" if i < n - 1 else "[vout]"
        filter_parts.append(
            f"{cur_label}[{i}:v]xfade=transition=fade:duration={xfade_dur}:offset={offset}{next_label}"
        )

    # First clip fade in + xfade chain
    filter_parts_str = ";".join(filter_parts)

    # Add fade-in to first clip and fade-out at very end
    total_dur = n * clip_dur - (n - 1) * xfade_dur
    filter_complex = (
        f"[0:v]fade=t=in:st=0:d={FADE_SECS}[f0];"
        f"[f0][1:v]xfade=transition=fade:duration={xfade_dur}:offset={step}[v01]"
    )
    if n > 2:
        for i in range(2, n):
            offset = i * step
            prev = f"[v{i-1:02d}]"
            nxt  = f"[v{i:02d}]" if i < n - 1 else "[vpre]"
            filter_complex += f";{prev}[{i}:v]xfade=transition=fade:duration={xfade_dur}:offset={offset}{nxt}"
        filter_complex += f";[vpre]fade=t=out:st={total_dur-FADE_SECS}:d={FADE_SECS}[vout]"
    else:
        filter_complex += f";[v01]fade=t=out:st={total_dur-FADE_SECS}:d={FADE_SECS}[vout]"

    cmd = (
        ["ffmpeg", "-y"]
        + inputs
        + [
            "-filter_complex", filter_complex,
            "-map", "[vout]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-an",
            str(out_path),
        ]
    )
    log.info(f"  Concat {n} clips → {out_path.name} (~{total_dur}s)")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if r.returncode != 0 or not out_path.exists():
        log.error(f"  xfade concat failed: {r.stderr[-400:]}")
        return False
    return True


# ── Long video assembly ────────────────────────────────────────────────────────

def build_music_track(music_files: list[str], target_secs: int, tmp_dir: Path) -> Optional[Path]:
    """Concatenate music files in a loop until target_secs is reached."""
    available = [MUSIC_DIR / f for f in music_files if (MUSIC_DIR / f).exists()]
    if not available:
        log.warning("  No music files found — video will be silent")
        return None

    concat_txt = tmp_dir / "music_concat.txt"
    audio_out  = tmp_dir / "audio_track.mp3"

    # Repeat track list until we exceed target duration
    total = 0
    lines = []
    while total < target_secs + 60:
        for f in available:
            # Estimate duration (we'll just repeat until long enough)
            lines.append(f"file '{f}'")
            total += 300  # rough estimate; ffmpeg stops at -t

    concat_txt.write_text("\n".join(lines))

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_txt),
        "-t", str(target_secs),
        "-c:a", "libmp3lame", "-b:a", "192k",
        str(audio_out),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if r.returncode != 0 or not audio_out.exists():
        log.error(f"  Music build failed: {r.stderr[-300:]}")
        return None
    return audio_out


def assemble_long_video(loop_mp4: Path, music_files: list[str],
                         duration_hours: int, out_mp4: Path) -> bool:
    """Stream-loop the visual loop + overlay music → output video."""
    target_secs = duration_hours * 3600
    preset = "slow" if duration_hours <= 1 else ("medium" if duration_hours <= 3 else "fast")

    tmp_dir = ROOT / "output" / "_tmp_visual_theme"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    audio_mp3 = build_music_track(music_files, target_secs, tmp_dir)

    if audio_mp3:
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", str(loop_mp4),
            "-i", str(audio_mp3),
            "-t", str(target_secs),
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "libx264", "-preset", preset, "-crf", "20",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            str(out_mp4),
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", str(loop_mp4),
            "-t", str(target_secs),
            "-c:v", "libx264", "-preset", preset, "-crf", "20",
            "-an",
            "-movflags", "+faststart",
            str(out_mp4),
        ]

    log.info(f"  Assembling {duration_hours}h → {out_mp4.name}")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=3600 * 3)
    if r.returncode != 0 or not out_mp4.exists():
        log.error(f"  Assembly failed: {r.stderr[-300:]}")
        return False

    size_mb = out_mp4.stat().st_size / 1024 / 1024
    log.info(f"  ✓ {size_mb:.0f}MB")
    return True


# ── Meta + thumbnail ───────────────────────────────────────────────────────────

def write_meta(theme: str, theme_cfg: dict, out_mp4: Path, duration_hours: int):
    dur_label = f"{duration_hours} Hour" if duration_hours == 1 else f"{duration_hours} Hours"
    title = theme_cfg["title"].format(duration=dur_label)
    desc  = theme_cfg["desc"].format(duration=dur_label)

    meta = {
        "title":         title,
        "description":   desc,
        "video_type":    theme_cfg["video_type"],
        "theme":         theme,
        "language":      "en",
        "is_short":      False,
        "status":        "public",
        "made_for_kids": False,
        "tags":          theme_cfg["tags"],
    }
    meta_path = out_mp4.parent / f"meta_{out_mp4.stem}.yaml"
    with open(meta_path, "w") as f:
        yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    log.info(f"  Meta → {meta_path.name}")


def generate_thumbnail(theme: str, theme_cfg: dict, out_mp4: Path, api_key: str) -> bool:
    thumb_path = out_mp4.parent / f"thumb_{out_mp4.stem}.png"
    if thumb_path.exists() and thumb_path.stat().st_size > 0:
        return True

    prompt = theme_cfg["thumb_prompt"]
    data = generate_image(prompt, api_key, width=1280, height=720)
    if not data:
        return False

    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(data)).resize((1280, 720), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, "PNG")
        thumb_path.write_bytes(buf.getvalue())
        log.info(f"  Thumb → {thumb_path.name}")
        return True
    except Exception as e:
        # Pillow not available — save raw
        thumb_path.write_bytes(data)
        log.info(f"  Thumb (raw) → {thumb_path.name}")
        return True


# ── Main processing ────────────────────────────────────────────────────────────

def process_theme(theme: str, durations: list[int], api_key: str,
                  force: bool = False, regen_images: bool = False,
                  regen_loop: bool = False, dry_run: bool = False) -> int:
    theme_cfg = THEMES[theme]
    log.info(f"\n{'='*60}")
    log.info(f"Theme: {theme.upper()}  durations={durations}h")

    VISUAL_LOOPS_DIR.mkdir(parents=True, exist_ok=True)
    QUEUE_ID.mkdir(parents=True, exist_ok=True)

    # Step 1: Generate / load images
    log.info("Step 1: Images")
    img_paths = ensure_images(theme, theme_cfg, api_key,
                              force=regen_images or force, dry_run=dry_run)
    if dry_run:
        n_cached = len([p for p in (ASSETS_DIR / theme).glob("frame_*.png")
                        if p.exists()]) if (ASSETS_DIR / theme).exists() else 0
        log.info(f"  [DRY RUN] {n_cached} cached images, "
                 f"would generate {N_IMAGES - n_cached} more, "
                 f"then make loop + {durations}h video(s)")
        return len(durations)
    if not img_paths:
        log.error(f"  No images generated for {theme} — skipping")
        return 0

    # Step 2: Ken Burns clips
    log.info("Step 2: Ken Burns clips")
    tmp_dir = ROOT / "output" / f"_tmp_{theme}"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    clip_paths: list[Path] = []
    for i, img_path in enumerate(img_paths):
        motion = MOTIONS[i % len(MOTIONS)]
        clip_path = tmp_dir / f"clip_{i:02d}.mp4"
        if clip_path.exists() and not (regen_loop or force):
            log.info(f"  [clip {i:02d}] cached")
        else:
            log.info(f"  [clip {i:02d}] {motion}")
            if not make_ken_burns_clip(img_path, clip_path, motion=motion):
                log.warning(f"  [clip {i:02d}] FAILED — skipping")
                continue
        clip_paths.append(clip_path)

    if not clip_paths:
        log.error(f"  No clips generated for {theme}")
        return 0

    # Step 3: Concat with xfade → visual loop
    log.info("Step 3: Visual loop")
    loop_path = VISUAL_LOOPS_DIR / f"visual_{theme}_loop.mp4"
    if loop_path.exists() and not (regen_loop or force):
        log.info(f"  Loop cached: {loop_path.name}")
    else:
        if not concat_with_xfade(clip_paths, loop_path):
            return 0
        size_mb = loop_path.stat().st_size / 1024 / 1024
        log.info(f"  Loop ✓ {size_mb:.1f}MB")

    # Step 4: Assemble long videos
    log.info("Step 4: Long videos")
    done = 0
    for dur in durations:
        out_name = f"visual_theme_{theme}_{dur}h_{DATE_STR}.mp4"
        out_mp4  = QUEUE_ID / out_name

        if out_mp4.exists() and not force:
            log.info(f"  EXISTS {out_name} (--force to redo)")
            write_meta(theme, theme_cfg, out_mp4, dur)
            done += 1
            continue

        if assemble_long_video(loop_path, theme_cfg["music_files"], dur, out_mp4):
            write_meta(theme, theme_cfg, out_mp4, dur)
            generate_thumbnail(theme, theme_cfg, out_mp4, api_key)
            done += 1

    return done


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate AI visual theme sleep videos for CNR")
    parser.add_argument("--theme",       choices=list(THEMES.keys()), help="Single theme")
    parser.add_argument("--all",         action="store_true", help="All themes")
    parser.add_argument("--durations",   type=int, nargs="+", default=[1],
                        help="Hours to generate (e.g. --durations 1 3 8)")
    parser.add_argument("--force",       action="store_true", help="Overwrite all existing files")
    parser.add_argument("--regen-images", action="store_true", help="Re-generate images only")
    parser.add_argument("--regen-loop",  action="store_true", help="Re-generate visual loop only")
    parser.add_argument("--dry-run",     action="store_true")
    parser.add_argument("--list-themes", action="store_true", help="List available themes")
    args = parser.parse_args()

    if args.list_themes:
        print("\nAvailable themes:")
        for name, cfg in THEMES.items():
            print(f"  {name:<20} mood={cfg['mood']}")
        return

    if not TOGETHER_KEY_FILE.exists() or TOGETHER_KEY_FILE.stat().st_size == 0:
        log.error(f"Together.ai API key missing: {TOGETHER_KEY_FILE}")
        return
    api_key = TOGETHER_KEY_FILE.read_text().strip()

    themes = list(THEMES.keys()) if args.all else ([args.theme] if args.theme else [])
    if not themes:
        parser.print_help()
        return

    total_done = 0
    for theme in themes:
        done = process_theme(
            theme, args.durations, api_key,
            force=args.force,
            regen_images=args.regen_images,
            regen_loop=args.regen_loop,
            dry_run=args.dry_run,
        )
        total_done += done

    log.info(f"\nDone: {total_done} video(s)")


if __name__ == "__main__":
    main()
