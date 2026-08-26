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
MEDITATION_DIR   = ROOT / "assets" / "audio" / "suno_meditation" / "Meditation"
TOGETHER_KEY_FILE = ROOT / "credentials" / "together_api_key.txt"
DATE_STR         = datetime.now().strftime("%Y%m%d")

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ── Clip / motion constants ────────────────────────────────────────────────────
CLIP_DURATION  = 30    # seconds per Ken Burns clip
XFADE_DURATION = 3     # seconds of crossfade between clips
FADE_SECS      = 2     # global fade in at start of loop
FPS            = 25
N_IMAGES       = 20    # images per theme (doubled for 3h variety)

# Ken Burns motion sequence (cycles through N_IMAGES)
MOTIONS = [
    "zoom_in",  "pan_right", "zoom_out",  "pan_left",
    "zoom_in",  "pan_up",    "zoom_out",  "pan_down",
    "zoom_in",  "pan_right", "zoom_out",  "pan_left",
    "pan_up",   "zoom_in",   "pan_down",  "zoom_out",
    "pan_right","zoom_in",   "pan_left",  "zoom_out",
]

# ── Theme catalogue ────────────────────────────────────────────────────────────
THEMES: dict[str, dict] = {

    "aurora_borealis": {
        "title": "Aurora Borealis 🌌 {duration} | Classical Music for Sleep | Calm Classics",
        "desc": (
            "Drift into peaceful sleep beneath the dancing northern lights. "
            "{duration} of stunning aurora borealis visuals paired with the most beloved classical piano music — "
            "Chopin Nocturnes and Beethoven's Moonlight Sonata, performed from public domain recordings.\n\n"
            "🎵 Music: Frédéric Chopin — Nocturnes Op. 9 | Ludwig van Beethoven — Moonlight Sonata "
            "| Ralph Vaughan Williams — Fantasia on a Theme by Thomas Tallis\n"
            "🎨 Visuals: AI-generated aurora borealis scenes\n"
            "📜 All recordings: Public Domain (Musopen.org)\n\n"
            "Whether you're looking for deep sleep music, calming classical music for the night, "
            "or simply a beautiful visual experience to wind down after a long day — this video was "
            "made for you. The soft piano melodies of Chopin have been used as sleep music for "
            "generations, and paired with the mesmerising movement of the northern lights, they "
            "create an atmosphere that quiets an anxious mind and slows the nervous system naturally.\n\n"
            "Many viewers use this as background music for deep sleep, leaving it on all night. "
            "The audio transitions smoothly and never startles — ideal classical music for sleeping "
            "without interruption. Others use it as study music, meditation music, or simply as "
            "relaxing background music while reading or unwinding.\n\n"
            "Why classical music helps you sleep:\n"
            "✦ Reduces heart rate and blood pressure within minutes\n"
            "✦ Lowers cortisol — the body's primary stress hormone\n"
            "✦ The predictable melodic structure signals safety to the brain\n"
            "✦ No lyrics — no cognitive engagement, allowing the mind to rest\n\n"
            "🔔 Subscribe for new classical music sleep programs every week → @ClassicalNightRelax\n\n"
            "#AuroraBorealis #NorthernLights #SleepMusic #ClassicalMusic #CalmClassics "
            "#ClassicalMusicForSleeping #DeepSleepMusic #RelaxingClassicalMusic "
            "#ChopinNocturnes #BeethovenMoonlightSonata #MeditationMusic #StudyMusic "
            "#InsomniaCure #ClassicalNightRelax #SleepingMusic #CalmingMusic"
        ),
        "tags": ["aurora borealis", "northern lights", "sleep music", "classical music",
                 "calm classics", "relaxing music", "chopin", "beethoven", "moonlight sonata",
                 "sleep aid", "study music", "meditation", "insomnia relief",
                 "sleep music for deep sleep", "classical music for sleeping",
                 "music to sleep", "relaxing sleep music", "deep sleep music"],
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
            # frame 10-19 (N_IMAGES=20)
            "aurora borealis reflected in frozen tundra lake, ice cracking patterns in foreground, green sky curtain, total wilderness, 16:9",
            "northern lights above Sami reindeer camp, tents glowing from inside, herd silhouetted, sub-zero magical night, 16:9",
            "aurora borealis green and white streaks above arctic fox on snow, wildlife and northern lights, stunning nature, 16:9",
            "northern lights seen from inside ice hotel, transparent ceiling, warm bed glow, green sky outside, magical stay, 16:9",
            "aurora borealis corona overhead, looking straight up, spiral of green light centered above, fisheye perspective, 16:9",
            "northern lights over Norwegian harbor, fishing boats reflected in calm fjord water, village lights, winter coast, 16:9",
            "aurora borealis purple and green above ancient Viking stone circle, mystical historical site, dark sky, 16:9",
            "midnight aurora train journey through Norway, light streaks outside snow-frosted window, warm interior light, travel magic, 16:9",
            "northern lights above frozen Baltic Sea, ice sheets stretching to horizon, faint pink and green, vast emptiness, 16:9",
            "aurora borealis double arc above snowy birch forest, moon also visible, blue and green contrast, perfect winter night, 16:9",
        ],
        "music_files": [
            "Nocturne in E flat major, Op. 9 no. 2.mp3",
            "Nocturne in B flat minor, Op. 9 no. 1.mp3",
            "Piano Sonata no. 14 in C#m 'Moonlight', Op. 27 no. 2 - I. Adagio sostenuto.mp3",
            "Fantasia on a Theme by Thomas Tallis.mp3",
            "Fantaisie, Op. 79 - Andantino.mp3",
            "Arabesque no. 1 (string quartet arr.).mp3",
            "Violin Concerto in D, Op. 61 - II. Larghetto.mp3",
            "Mozart - Serenade in G Major - I. Romance.mp3",
            "Mazurka in A flat major, B. 85.mp3",
            "Swan Lake Op.20 - Act IV Intro.mp3",
            "Cello Sonata No. 4, mov. 1 - Ben Larsen, Ava Nazar.mp3",
            "Adagio in G minor.mp3",
            "Ballade no. 1 in G minor, Op. 23.mp3",
            "Adagio for Organ & Strings in g minor.mp3",
            "Concerto for 2 Violins in D minor, BWV 1043  - II. Largo ma non tanto.mp3",
            "Piano Concerto No. 2 in C Minor, Op. 18 - II. Adagio sostenuto.mp3",
        ],
        "mood": "sleep",
        "video_type": "visual_theme",
    },

    "cherry_blossoms": {
        "title": "Cherry Blossoms 🌸 {duration} | Japanese Classical Music | Calm Classics",
        "desc": (
            "Float beneath a canopy of cherry blossoms with {duration} of serene, delicate classical music. "
            "Sakura petals drift across AI-illustrated spring scenes while Chopin's most gentle Nocturnes "
            "and Mozart's Serenade in G flow without interruption — the perfect companion for deep, "
            "untroubled sleep.\n\n"
            "🎵 Music: Frédéric Chopin — Nocturnes Op. 9 | W.A. Mozart — Serenade in G Major "
            "| Claude Debussy — Arabesque No. 1\n"
            "🎨 Visuals: AI-generated cherry blossom and sakura scenes\n"
            "📜 All recordings: Public Domain (Musopen.org)\n\n"
            "The Japanese concept of 'mono no aware' — the bittersweet beauty of passing things — "
            "runs through both the falling sakura petals and the soft, wistful quality of Chopin's "
            "piano writing. Together they create one of the most effective sleep music environments "
            "we know: visually calming, emotionally resolved, and completely free of jarring moments.\n\n"
            "This video works as classical music for sleeping because the pieces are carefully chosen "
            "for their soft dynamics and gentle tempo — nothing loud, nothing sudden. Perfect as "
            "music to fall asleep to, as relaxing study music, or as meditation background.\n\n"
            "✦ No ads mid-video — seamless listening all night\n"
            "✦ Soft audio levels — safe to leave on while sleeping\n"
            "✦ Looped visuals — screen-friendly for bedtime viewing\n\n"
            "🔔 Subscribe → @ClassicalNightRelax\n\n"
            "#CherryBlossoms #Sakura #SleepMusic #ClassicalMusic #CalmClassics "
            "#ClassicalMusicForSleeping #RelaxingClassicalMusic #ChopinNocturnes #Mozart "
            "#DeepSleepMusic #MeditationMusic #StudyMusic #JapaneseAmbiance #ClassicalNightRelax"
        ),
        "tags": ["cherry blossoms", "sakura", "japanese", "sleep music", "classical music",
                 "calm classics", "chopin nocturnes", "mozart", "spring ambiance",
                 "relaxing music", "meditation", "study music", "peaceful",
                 "sleep music for deep sleep", "classical music for sleeping",
                 "music to sleep", "relaxing sleep music"],
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
            # frame 10-19 (N_IMAGES=20)
            "cherry blossom petals falling on still Japanese garden stream, petals floating downstream, mossy stones, soft light, 16:9",
            "sakura tree at full bloom night with moonlight, glowing pink petals, temple silhouette, lantern light, ethereal, 16:9",
            "cherry blossom forest path at golden hour, sunlight turning petals gold, couple distant, romantic Japan spring, 16:9",
            "weeping cherry blossom tree (shidarezakura) by pond, branches touching water, pink cascade, dreamy atmosphere, 16:9",
            "sakura trees lining river canal in Tokyo, falling pink snow, people below small, spring overwhelm, 16:9",
            "close-up cherry blossom bee, pollen dusted, macro photography, flower and insect detail, spring life, 16:9",
            "Japanese castle Himeji surrounded by cherry blossoms, pink and white perfection, blue sky, iconic image, 16:9",
            "sakura petals landing on dark water surface, ripple circles from each petal, reflection of pink above, 16:9",
            "cherry blossom avenue at night with lanterns, pink blooms illuminated, magical tunnel of flowers, 16:9",
            "sakura hillside in Japan, hundreds of trees in full bloom, small village below, aerial spring perfection, 16:9",
        ],
        "music_files": [
            "Nocturne in E flat major, Op. 9 no. 2.mp3",
            "Mozart - Serenade in G Major - I. Romance.mp3",
            "Mozart - Serenade in G Major - II. Minuet.mp3",
            "Arabesque No. 1. Andantino con moto.mp3",
            "Nocturne in B flat minor, Op. 9 no. 1.mp3",
            "Mozart - Serenade in G Major - III. Rondo.mp3",
            "Mazurka in C sharp minor, Op. 6 no. 2.mp3",
            "Mazurka in A flat major, B. 85.mp3",
            "Fantaisie, Op. 79 - Andantino.mp3",
            "Violin Concerto in D, Op. 61 - II. Larghetto.mp3",
            "Cello Suite no. 1 - Prelude in G, BWV 1007.mp3",
            "Adagio in G minor.mp3",
            "Etude Op. 10, no. 6 in E flat minor - 'Lament'.mp3",
            "Adagio for Organ & Strings in g minor.mp3",
            "Concerto for 2 Violins in D minor, BWV 1043  - II. Largo ma non tanto.mp3",
        ],
        "mood": "sleep",
        "video_type": "visual_theme",
    },

    "mountain_snow": {
        "title": "Mountain Snow ⛰️ {duration} | Classical Music for Deep Sleep | Calm Classics",
        "desc": (
            "Rest beside majestic snow-capped mountains with {duration} of grand, sweeping classical music — "
            "the ideal deep sleep music for nights when your mind refuses to quiet down.\n\n"
            "🎵 Music: Ralph Vaughan Williams — Fantasia on a Theme by Thomas Tallis "
            "| Frédéric Chopin — Nocturnes Op. 9 | Ludwig van Beethoven — Moonlight Sonata\n"
            "🎨 Visuals: AI-generated alpine and mountain snow scenes\n"
            "📜 All recordings: Public Domain (Musopen.org)\n\n"
            "There is something about mountains that silences the noise inside us. "
            "The sheer scale — glaciers, frozen summits, the infinite dark sky — makes our "
            "daily worries feel appropriately small. Vaughan Williams' Fantasia on a Theme by "
            "Thomas Tallis, one of the most profoundly calming pieces ever written, fills that "
            "vast space perfectly. This is classical music for deep sleep in the truest sense: "
            "music that doesn't just accompany sleep but actively induces it.\n\n"
            "Researchers have consistently found that slow-tempo classical music — below 80 BPM — "
            "synchronises with the body's resting heart rate and guides the listener toward "
            "sleep. This video stays within that range throughout, making it reliable music "
            "to fall asleep to, even for those who struggle with insomnia.\n\n"
            "✦ Ideal for: deep sleep, insomnia relief, meditation, stress relief, relaxation\n"
            "✦ No sudden loud passages — safe to leave on all night at low volume\n"
            "✦ Works with headphones, speakers, or TV — the visual is calming either way\n\n"
            "🔔 Subscribe → @ClassicalNightRelax\n\n"
            "#MountainSnow #AlpineLandscape #SleepMusic #ClassicalMusic #CalmClassics "
            "#DeepSleepMusic #ClassicalMusicForSleeping #VaughanWilliams #ChopinNocturnes "
            "#RelaxingClassicalMusic #InsomniaCure #MeditationMusic #ClassicalNightRelax"
        ),
        "tags": ["mountain snow", "alpine", "winter landscape", "sleep music", "classical music",
                 "calm classics", "vaughan williams", "chopin", "deep sleep",
                 "relaxing music", "meditation", "stress relief", "nature",
                 "sleep music for deep sleep", "classical music for sleeping",
                 "deep sleep music", "relaxing sleep music"],
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
            # frame 10-19 (N_IMAGES=20)
            "mountain climber silhouette on summit ridge at sunset, vast snowy panorama below, achievement and solitude, 16:9",
            "Swiss Alps village covered in deep snow, church steeple, chalets with smoke, perfect winter postcard, 16:9",
            "glacier crevasses close-up, deep blue ice walls, scale shown by tiny rope, ancient ice interior, 16:9",
            "mountain ski resort at night, slope lights twinkling below dark peaks, stars above, magical cold night, 16:9",
            "frozen mountain lake perfectly reflecting surrounding peaks, cracks in ice, blue transparency, winter perfection, 16:9",
            "avalanche aftermath, massive snow debris field, morning light on devastation, mountains quiet after power, 16:9",
            "high altitude monastery in Himalayas, snow peaks behind ancient stone, prayer flags, silence and devotion, 16:9",
            "winter mountain sunrise, first orange light on snow cornices, purple shadows in valleys, dramatic alpenglow, 16:9",
            "mountain wolf in deep snow, breath visible, forest edge, intense gaze, winter wilderness predator, 16:9",
            "snowy Dolomites pink at sunset, Tre Cime silhouette, Italian Alps perfection, warm cold contrast, 16:9",
        ],
        "music_files": [
            "Fantasia on a Theme by Thomas Tallis.mp3",
            "Nocturne in B flat minor, Op. 9 no. 1.mp3",
            "Piano Sonata no. 14 in C#m 'Moonlight', Op. 27 no. 2 - I. Adagio sostenuto.mp3",
            "Nocturne in E flat major, Op. 9 no. 2.mp3",
            "Arabesque No. 1. Andantino con moto.mp3",
            "Mozart - Serenade in G Major - I. Romance.mp3",
            "Violin Concerto in D, Op. 61 - II. Larghetto.mp3",
            "Swan Lake Op.20 - Act II Pt.1.mp3",
            "Mazurka in A flat major, B. 85.mp3",
            "Symphony no. 5 in Cm, Op. 67 - II. Andante con moto.mp3",
            "Cello Suite no. 1 - Prelude in G, BWV 1007.mp3",
            "Adagio in G minor.mp3",
            "Sonata no. 17 in D minor 'The Tempest', Op. 31 no. 2 - II. Adagio.mp3",
            "Adagio for Organ & Strings in g minor.mp3",
            "Piano Concerto No. 2 in C Minor, Op. 18 - II. Adagio sostenuto.mp3",
            "Concerto for 2 Violins in D minor, BWV 1043  - II. Largo ma non tanto.mp3",
        ],
        "mood": "sleep",
        "video_type": "visual_theme",
    },

    "fireplace_cabin": {
        "title": "Cozy Fireplace 🔥 {duration} | Classical Music for Sleep | Calm Classics",
        "desc": (
            "Settle into the warmth of a winter cabin fireplace with {duration} of soft, "
            "soothing classical music. Glowing embers, candlelight, snow falling quietly outside — "
            "and Chopin's most intimate piano works accompanying every breath of warmth.\n\n"
            "🎵 Music: Frédéric Chopin — Nocturnes & Mazurkas | Claude Debussy — Arabesque No. 1\n"
            "🎨 Visuals: AI-generated cozy fireplace and cabin scenes\n"
            "📜 All recordings: Public Domain (Musopen.org)\n\n"
            "The fireplace has always been the original sleep aid — the soft crackle, the warmth, "
            "the contained living flame that asks nothing of you. Paired with Chopin's late-night "
            "piano writing — music he composed by candlelight, in rooms not unlike the ones you see "
            "here — this becomes one of the most natural and comfortable sleep environments you can "
            "create on a screen.\n\n"
            "This video works beautifully as relaxing classical music for evenings when you want "
            "warmth and calm without silence. Whether you're reading, journaling, or simply "
            "trying to let the day go, the combination of soft firelight and slow piano acts as "
            "a gentle signal to the body that it's time to rest. Many viewers use it as "
            "music to sleep to on winter nights — the visual warmth compensates for the "
            "cold outside.\n\n"
            "✦ Perfect for: sleep, cozy evenings, reading, winter ambiance, unwinding\n"
            "✦ Consistent volume — no sudden loud passages, safe for nighttime listening\n"
            "✦ Beautiful on any screen as a fireplace atmosphere substitute\n\n"
            "🔔 Subscribe → @ClassicalNightRelax\n\n"
            "#Fireplace #CozyVibes #SleepMusic #ClassicalMusic #CalmClassics "
            "#ClassicalMusicForSleeping #RelaxingClassicalMusic #ChopinNocturnes #Debussy "
            "#CozyCabin #WinterAmbiance #DeepSleepMusic #MusicToSleep #ClassicalNightRelax"
        ),
        "tags": ["fireplace", "cozy cabin", "winter ambiance", "sleep music", "classical music",
                 "calm classics", "chopin", "debussy", "cozy vibes",
                 "relaxing music", "reading ambiance", "hygge", "warm",
                 "sleep music for deep sleep", "classical music for sleeping",
                 "music to sleep", "relaxing sleep music"],
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
            # frame 10-19 (N_IMAGES=20)
            "log cabin kitchen at night, cast iron pot on fire, copper pots, handmade everything, warm lamp light, 16:9",
            "mountain hut exterior at dusk, smoke from chimney, lantern over door, pine forest, fresh snow fallen, 16:9",
            "fireplace embers at 2am, room in shadow, cat curled sleeping nearby, quiet domestic night, 16:9",
            "sauna cabin by frozen lake, steam from chimney, snow on roof, birch trees, Nordic winter ritual, 16:9",
            "wood-burning stove in artist studio, canvases around, books stacked, warm light, creative winter retreat, 16:9",
            "cabin living room morning after snowstorm, snow banked against windows, fire needed and ready, cozy siege, 16:9",
            "fireplace mantle with candles, clock, family photos soft background, ordinary domestic warmth, evening light, 16:9",
            "stone fireplace in medieval castle great hall, enormous logs burning, tapestries, historical grandeur, 16:9",
            "camping fire in forest clearing, sparks rising to stars, friends' silhouettes, tent glow, summer night magic, 16:9",
            "fire reflection in rain-wet cabin window, outside stormy, inside warm, contrast of safety and storm, 16:9",
        ],
        "music_files": [
            "Nocturne in E flat major, Op. 9 no. 2.mp3",
            "Nocturne in B flat minor, Op. 9 no. 1.mp3",
            "Arabesque No. 1. Andantino con moto.mp3",
            "Mazurka in A flat major, B. 85.mp3",
            "Fantaisie, Op. 79 - Andantino.mp3",
            "Mozart - Serenade in G Major - I. Romance.mp3",
            "Cello Suite no. 1 - Prelude in G, BWV 1007.mp3",
            "Violin Concerto in D, Op. 61 - II. Larghetto.mp3",
            "Swan Lake Op.20 - Act II Pt.1.mp3",
            "Symphony no. 5 in Cm, Op. 67 - II. Andante con moto.mp3",
            "Mazurka in C sharp minor, Op. 6 no. 2.mp3",
            "Adagio in G minor.mp3",
            "Etude Op. 10, no. 6 in E flat minor - 'Lament'.mp3",
            "Adagio for Organ & Strings in g minor.mp3",
            "Piano Concerto No. 2 in C Minor, Op. 18 - II. Adagio sostenuto.mp3",
        ],
        "mood": "sleep",
        "video_type": "visual_theme",
    },

    "zen_garden": {
        "title": "Zen Garden 🪨 {duration} | Classical Music for Focus | Calm Classics",
        "desc": (
            "Find stillness in the timeless beauty of a Japanese zen garden. "
            "{duration} of deeply meditative classical music paired with raked sand, stone lanterns, "
            "and bonsai — among the finest classical music for focus and concentration available.\n\n"
            "🎵 Music: Johann Sebastian Bach — Cello Suite No. 1, BWV 1007 "
            "| Claude Debussy — Arabesque No. 1 | W.A. Mozart — Serenade in G Major "
            "| Frédéric Chopin — Nocturne Op. 9 No. 2\n"
            "🎨 Visuals: AI-generated Japanese zen garden scenes\n"
            "📜 All recordings: Public Domain (Musopen.org)\n\n"
            "Bach's Cello Suite No. 1 is arguably the most studied piece in the classical "
            "repertoire — and not by accident. Its mathematical clarity and unhurried forward "
            "motion make it ideal classical music for studying: it occupies just enough of the "
            "listening brain to suppress distraction, without demanding conscious attention. "
            "Paired with the visual discipline of a zen garden — where every stone is placed "
            "with intention — the result is a focused calm that's difficult to find anywhere else.\n\n"
            "Students, writers, programmers, and designers regularly report that instrumental "
            "classical music for concentration outperforms silence for sustained creative work. "
            "This video is designed with exactly that in mind: no sudden changes in dynamics, "
            "no dramatic passages, just a continuous meditative flow that supports deep work "
            "or deep sleep equally well.\n\n"
            "✦ Ideal for: deep focus, study sessions, meditation, yoga, writing, coding\n"
            "✦ Also works as sleep music — the slow tempo suits both purposes\n"
            "✦ Loop-friendly: designed for extended listening without interruption\n\n"
            "🔔 Subscribe → @ClassicalNightRelax\n\n"
            "#ZenGarden #Japanese #FocusMusic #ClassicalMusic #CalmClassics "
            "#ClassicalMusicForStudying #ClassicalMusicForFocus #Bach #Debussy "
            "#MeditationMusic #StudyMusic #DeepFocusMusic #ClassicalNightRelax #YogaMusic"
        ),
        "tags": ["zen garden", "japanese garden", "focus music", "classical music",
                 "calm classics", "bach", "debussy", "meditation",
                 "study music", "yoga", "mindfulness", "peaceful",
                 "classical music for studying", "classical music for focus",
                 "sleep music for deep sleep", "relaxing sleep music"],
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
            # frame 10-19 (N_IMAGES=20)
            "Japanese temple meditation hall, monk silhouette, incense smoke rising, wooden floor, garden view outside, 16:9",
            "dry stone wall garden, Ryoanji style, only 15 stones in raked gravel, pure minimalism, Kyoto, 16:9",
            "zen garden bamboo fountain close-up, water flowing, dripping sound implied, stone bowl, moss, 16:9",
            "kare-sansui stone garden at dawn, mist above gravel, first light on stones, temple eaves framing, 16:9",
            "meditation cushion zafu on tatami, paper screen door open to garden, bird outside, simple practice space, 16:9",
            "zen garden gate torii wooden, moss on stones, path leading into forest, silent invitation, 16:9",
            "maple leaves fallen on zen garden sand, autumn disruption of order, accepted impermanence, wabi-sabi, 16:9",
            "night zen garden, lantern light on gravel patterns, moon shadows of stones, quiet after dark, 16:9",
            "modern zen garden rooftop Tokyo, city below, raked gravel and stones above, contrast of worlds, 16:9",
            "Japanese ink painting style garden scene, monochrome mist, bamboo, mountain, bridge, timeless aesthetic, 16:9",
        ],
        "music_files": [
            "Cello Suite no. 1 - Prelude in G, BWV 1007.mp3",
            "Arabesque No. 1. Andantino con moto.mp3",
            "Mozart - Serenade in G Major - I. Romance.mp3",
            "Nocturne in E flat major, Op. 9 no. 2.mp3",
            "Goldberg Variations, BWV 988 - 01 - Aria.mp3",
            "Mozart - Serenade in G Major - II. Minuet.mp3",
            "3 Fantaisies for Solo Flute, Op. 38 - Fantaisie no. 1.mp3",
            "Fantaisie, Op. 79 - Andantino.mp3",
            "Arabesque no. 1 (string quartet arr.).mp3",
            "Mazurka in E major, Op. 6 no. 3.mp3",
            "Sonata no. 17 in D minor 'The Tempest', Op. 31 no. 2 - II. Adagio.mp3",
            "Violin Partita no. 2, BWV 1004 - 5. Chaconne [Piano arrangement - K.H. Pillney].mp3",
            "Julia Florida.mp3",
            "Prelude and Fugue No. 4 in C-sharp minor - Complete Performance.mp3",
            "Prelude and Fugue No. 12 in F minor - Complete Performance.mp3",
            "Prelude and Fugue No. 24 in B minor - Complete Performance.mp3",
            "Concerto for 2 Violins in D minor, BWV 1043  - II. Largo ma non tanto.mp3",
        ],
        "mood": "focus",
        "video_type": "visual_theme",
    },

    "lavender_fields": {
        "title": "Lavender Fields 💜 {duration} | Classical Music for Sleep | Calm Classics",
        "desc": (
            "Close your eyes and picture endless rows of purple lavender running to the horizon "
            "under a warm Provence sunset. {duration} of the most quietly beautiful classical music — "
            "Chopin Nocturnes and Mozart's Serenade — as the perfect sleep companion.\n\n"
            "🎵 Music: Frédéric Chopin — Nocturnes Op. 9 | W.A. Mozart — Serenade in G Major "
            "| Claude Debussy — Arabesque No. 1\n"
            "🎨 Visuals: AI-generated Provence lavender field scenes\n"
            "📜 All recordings: Public Domain (Musopen.org)\n\n"
            "Lavender has been used as a natural sleep remedy for centuries — and there is real "
            "science behind it. The scent activates the parasympathetic nervous system, slowing "
            "heart rate and encouraging sleep. This video pairs that visual association with "
            "classical music for sleeping that works along the same principles: slow, predictable, "
            "emotionally warm, with no jarring transitions.\n\n"
            "The Chopin Nocturnes were written as 'night pieces' — music literally intended for "
            "the hours between dusk and dawn. They are among the most effective relaxing sleep "
            "music ever composed, and in the context of sun-drenched lavender fields they feel "
            "both intimate and expansive. This is music to fall asleep to that also rewards "
            "conscious listening — equally at home in a meditation session or as soft background "
            "music during an evening meal.\n\n"
            "✦ Perfect for: sleep, relaxation, stress relief, meditation, nature ambiance\n"
            "✦ Long-form — designed to play through the night without waking you\n"
            "✦ No ads, no interruptions, no sudden changes in volume\n\n"
            "🔔 Subscribe → @ClassicalNightRelax\n\n"
            "#LavenderFields #Provence #SleepMusic #ClassicalMusic #CalmClassics "
            "#ClassicalMusicForSleeping #ChopinNocturnes #Mozart #RelaxingClassicalMusic "
            "#NatureAmbiance #DeepSleepMusic #MusicToFallAsleepTo #ClassicalNightRelax"
        ),
        "tags": ["lavender fields", "provence", "france", "sleep music", "classical music",
                 "calm classics", "chopin", "mozart", "purple", "nature ambiance",
                 "relaxing music", "meditation", "spring", "flowers",
                 "sleep music for deep sleep", "classical music for sleeping",
                 "music to sleep", "relaxing sleep music"],
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
            # frame 10-19 (N_IMAGES=20)
            "lavender essential oil distillery in Provence, copper pot stills, steam, aromatic production, rustic, 16:9",
            "bee on lavender close-up macro, wings spread, pollen yellow, purple flower spike, summer detail, 16:9",
            "lavender field after rain, water drops on purple flowers, rainbow in background, Provence wet summer, 16:9",
            "lavender pressing harvest, farmer with bundle, sunset behind field, end of summer tradition, 16:9",
            "lavender fields from hot air balloon, purple rows far below, Alpes distant, summer morning flight, 16:9",
            "old stone provence house with lavender garden, blue shutters, roses climbing wall, summer perfection, 16:9",
            "lavender labyrinth garden, geometric pathways through purple blooms, aerial view, ornamental design, 16:9",
            "moonlit lavender field, blue-silver light on flowers, no wind, stillness, one owl hunting, 16:9",
            "lavender seeds in palm, close-up, small and grey-green, potential and harvest, minimal, 16:9",
            "lavender field edge meeting wildflower meadow, purple and yellow and white mixing, summer abundance, 16:9",
        ],
        "music_files": [
            "Nocturne in E flat major, Op. 9 no. 2.mp3",
            "Mozart - Serenade in G Major - I. Romance.mp3",
            "Nocturne in B flat minor, Op. 9 no. 1.mp3",
            "Arabesque No. 1. Andantino con moto.mp3",
            "Mozart - Serenade in G Major - II. Minuet.mp3",
            "Mozart - Serenade in G Major - III. Rondo.mp3",
            "Mazurka in A flat major, B. 85.mp3",
            "Fantaisie, Op. 79 - Andantino.mp3",
            "Violin Concerto in D, Op. 61 - II. Larghetto.mp3",
            "Swan Lake Op.20 - Act IV Intro.mp3",
            "Cello Suite no. 1 - Prelude in G, BWV 1007.mp3",
            "Adagio for Organ & Strings in g minor.mp3",
            "Piano Concerto No. 2 in C Minor, Op. 18 - II. Adagio sostenuto.mp3",
            "Concerto for 2 Violins in D minor, BWV 1043  - II. Largo ma non tanto.mp3",
        ],
        "mood": "sleep",
        "video_type": "visual_theme",
    },

    "deep_space": {
        "title": "Deep Space 🌌 {duration} | Classical Music for Sleep | Calm Classics",
        "desc": (
            "Float through the infinite cosmos with {duration} of transcendent, expansive classical music. "
            "Vivid nebulae, spiral galaxies, and glittering star fields — paired with orchestral "
            "masterpieces that feel as vast as the universe itself.\n\n"
            "🎵 Music: Ralph Vaughan Williams — Fantasia on a Theme by Thomas Tallis "
            "| Ludwig van Beethoven — Moonlight Sonata | Frédéric Chopin — Nocturne Op. 9 No. 1\n"
            "🎨 Visuals: AI-generated deep space and nebula imagery\n"
            "📜 All recordings: Public Domain (Musopen.org)\n\n"
            "There are few pieces of music that match the scale of looking at a nebula. "
            "Vaughan Williams' Fantasia on a Theme by Thomas Tallis is one of them — a vast, "
            "slow-moving string work that seems to expand outward like light from a distant star. "
            "Alongside Beethoven's Moonlight Sonata, it creates deep sleep music of a particularly "
            "meditative quality: music that asks you to let go of the human scale entirely and "
            "simply drift in something enormous and calm.\n\n"
            "This is one of our most requested videos from viewers who use classical music for "
            "insomnia. The slow harmonic rhythm and minimal melodic movement in these pieces "
            "prevents the brain from 'tracking' the music consciously, letting attention dissolve "
            "into sleep naturally. Some also use it as meditation music for visualisation — "
            "imagining floating through space is a well-established relaxation technique.\n\n"
            "✦ Deep sleep, meditation, insomnia relief, relaxation, stress relief\n"
            "✦ Particularly effective for overthinkers — the cosmic scale quiets rumination\n"
            "✦ Perfect at low volume in a darkened room\n\n"
            "🔔 Subscribe → @ClassicalNightRelax\n\n"
            "#DeepSpace #Nebula #SleepMusic #ClassicalMusic #CalmClassics "
            "#ClassicalMusicForSleeping #DeepSleepMusic #VaughanWilliams #BeethovenMoonlight "
            "#MeditationMusic #InsomniaCure #RelaxingClassicalMusic #ClassicalNightRelax"
        ),
        "tags": ["deep space", "nebula", "cosmos", "sleep music", "classical music",
                 "calm classics", "vaughan williams", "beethoven", "meditation",
                 "space ambiance", "stars", "galaxy", "relaxing",
                 "sleep music for deep sleep", "classical music for sleeping",
                 "deep sleep music", "space music for sleep"],
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
            # frame 10-19 (N_IMAGES=20)
            "pulsar star rotating, energy beams sweeping space, magnetic field lines visible, cosmic lighthouse, 16:9",
            "deep space ice giant planet with rings, blue and white stormy surface, ring system detail, Uranus style, 16:9",
            "star birth nursery nebula, dense gas clouds, proto-stars forming, golden and rust, epic scale, 16:9",
            "dark matter web simulation art, cosmic filaments connecting galaxy clusters, invisible universe made visible, 16:9",
            "astronaut spacewalk, Earth below, infinite black above, silence and awe, ISS glimpse, 16:9",
            "planet rise from moon surface, Earth-like world with clouds above stark grey moonscape, perspective shift, 16:9",
            "deep space time-lapse star trails, concentric circles around celestial pole, desert observatory below, 16:9",
            "cosmic collision two galaxies merging, tidal arms stretching, star formation explosion, 100 million year event, 16:9",
            "intergalactic void, vast emptiness between galaxy clusters, a few distant smudges, the true scale of nothing, 16:9",
            "neutron star surface simulation, extreme gravity curves, intense blue glow, atom-thick atmosphere, impossible, 16:9",
        ],
        "music_files": [
            "Fantasia on a Theme by Thomas Tallis.mp3",
            "Piano Sonata no. 14 in C#m 'Moonlight', Op. 27 no. 2 - I. Adagio sostenuto.mp3",
            "Nocturne in B flat minor, Op. 9 no. 1.mp3",
            "Violin Concerto in D, Op. 61 - II. Larghetto.mp3",
            "Symphony no. 5 in Cm, Op. 67 - II. Andante con moto.mp3",
            "Swan Lake Op.20 - Act II Pt.1.mp3",
            "Nocturne in E flat major, Op. 9 no. 2.mp3",
            "Arabesque No. 1. Andantino con moto.mp3",
            "Fantaisie, Op. 79 - Andantino.mp3",
            "Swan Lake Op.20 - Act IV Intro.mp3",
            "Adagio in G minor.mp3",
            "Sonata no. 17 in D minor 'The Tempest', Op. 31 no. 2 - II. Adagio.mp3",
            "Adagio for Organ & Strings in g minor.mp3",
            "Piano Concerto No. 2 in C Minor, Op. 18 - II. Adagio sostenuto.mp3",
            "Concerto for 2 Violins in D minor, BWV 1043  - II. Largo ma non tanto.mp3",
        ],
        "mood": "sleep",
        "video_type": "visual_theme",
    },

    "autumn_forest": {
        "title": "Autumn Forest 🍂 {duration} | Classical Music for Sleep | Calm Classics",
        "desc": (
            "Walk through a golden autumn forest with {duration} of warm, melancholic classical music — "
            "amber leaves, misty forest paths, and the particular stillness that only autumn "
            "afternoons carry. This is relaxing sleep music with soul.\n\n"
            "🎵 Music: Frédéric Chopin — Nocturnes Op. 9 "
            "| Pyotr Tchaikovsky — Swan Lake Act II\n"
            "🎨 Visuals: AI-generated autumn forest scenes\n"
            "📜 All recordings: Public Domain (Musopen.org)\n\n"
            "Autumn is the season of letting go — of leaves, of warmth, of the long days. "
            "The music in this video reflects exactly that. Chopin's Nocturnes have a quality "
            "of beautiful sadness that never tips into distress — they feel like memories of "
            "good things, which is precisely the emotional state most conducive to sleep. "
            "Tchaikovsky's Swan Lake adds orchestral warmth and sweep, turning the forest walk "
            "into something genuinely cinematic.\n\n"
            "As classical music for sleeping, this video works particularly well for those "
            "who find pure silence too empty, but need the music to stay out of the way. "
            "Chopin's slow-tempo piano writing sits at around 60 BPM — matching the resting "
            "heart rate — which is why classical music for deep sleep so often features his "
            "Nocturnes. The forest visuals add a layer of natural calm that makes the whole "
            "experience feel grounded rather than purely abstract.\n\n"
            "✦ Perfect for: sleep, autumn evenings, meditation, reading, relaxation\n"
            "✦ Warm, comforting mood — ideal for seasonal mood changes\n"
            "✦ No ads — seamless audio through the night\n\n"
            "🔔 Subscribe → @ClassicalNightRelax\n\n"
            "#AutumnForest #FallColors #SleepMusic #ClassicalMusic #CalmClassics "
            "#ClassicalMusicForSleeping #ChopinNocturnes #Tchaikovsky #AutumnVibes "
            "#DeepSleepMusic #RelaxingClassicalMusic #NatureSoundsForSleep #ClassicalNightRelax"
        ),
        "tags": ["autumn forest", "fall colors", "forest", "sleep music", "classical music",
                 "calm classics", "chopin", "tchaikovsky", "autumn ambiance",
                 "relaxing music", "nature", "meditation", "cozy",
                 "sleep music for deep sleep", "classical music for sleeping",
                 "nature sounds for sleep", "relaxing sleep music"],
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
            # frame 10-19 (N_IMAGES=20)
            "autumn forest floor, mushrooms on fallen log, leaf carpet, moisture and decay, close macro, 16:9",
            "red maple forest Japan, momiji, corridor of crimson, wooden bridge, perfect reflection, 16:9",
            "autumn forest waterfall, leaves floating past, brown orange yellow in water, seasonal rush, 16:9",
            "forest at peak color from above, patchwork quilt of red orange gold, one silver river thread, 16:9",
            "autumn birch grove, white trunks, yellow leaves backlit by sun, cathedral forest feeling, 16:9",
            "old man walking with stick in autumn forest, mist ahead, leaves falling, peaceful life moment, 16:9",
            "autumn leaves on glass surface, rain drops, backlit orange, abstract beauty, close-up, 16:9",
            "harvest moon rising above autumn forest, huge orange moon, silhouette treeline, blue twilight sky, 16:9",
            "apple orchard in autumn, heavy fruit, fallen apples, warm evening light, traditional farm, 16:9",
            "winter approaching autumn forest, last leaves clinging, frost on ground, transition scene, 16:9",
        ],
        "music_files": [
            "Nocturne in B flat minor, Op. 9 no. 1.mp3",
            "Nocturne in E flat major, Op. 9 no. 2.mp3",
            "Swan Lake Op.20 - Act II Pt.1.mp3",
            "Swan Lake Op.20 - Act II Concl.mp3",
            "Violin Concerto in D, Op. 61 - II. Larghetto.mp3",
            "Mazurka in A flat major, B. 85.mp3",
            "Mazurka in C sharp minor, Op. 6 no. 2.mp3",
            "Fantaisie, Op. 79 - Andantino.mp3",
            "Swan Lake Op.20 - Act III Pt.1.mp3",
            "Swan Lake Op.20 - Act IV Intro.mp3",
            "Symphony no. 5 in Cm, Op. 67 - II. Andante con moto.mp3",
            "Ballade no. 1 in G minor, Op. 23.mp3",
            "Etude Op. 10, no. 6 in E flat minor - 'Lament'.mp3",
            "Adagio for Organ & Strings in g minor.mp3",
            "Piano Concerto No. 2 in C Minor, Op. 18 - II. Adagio sostenuto.mp3",
            "Concerto for 2 Violins in D minor, BWV 1043  - II. Largo ma non tanto.mp3",
        ],
        "mood": "sleep",
        "video_type": "visual_theme",
    },

    # ── Keyword-targeted themes (popular YouTube search queries) ──────────────────

    "night_rain": {
        "title": "Night Rain & Piano 🌧️ {duration} | Soft Piano Music for Relaxation | Calm Classics",
        "desc": (
            "Lie back and let the night rain and soft piano carry you into deep, effortless sleep. "
            "{duration} of the most calming rain and classical piano atmosphere — Chopin Nocturnes, "
            "Debussy, Fauré and Bach, flowing gently beneath rain-washed images of windows, cobblestones "
            "and candlelit rooms.\n\n"
            "🎵 Music: Frédéric Chopin — Nocturnes | Claude Debussy — Arabesque No. 1 "
            "| Gabriel Fauré — Fantaisie Op. 79 | J.S. Bach — Cello Suite No. 1\n"
            "🎨 Visuals: AI-generated night rain, window and candlelight scenes\n"
            "📜 All recordings: Public Domain (Musopen.org)\n\n"
            "Rain sounds and piano music are among the most searched sleep aids on YouTube — and "
            "for good reason. The white-noise masking effect of rain suppresses distracting sounds, "
            "while slow-tempo piano music (under 70 BPM) synchronises with the resting heartbeat, "
            "guiding the nervous system toward sleep. Chopin composed most of his Nocturnes late at "
            "night, by candlelight — the same setting these visuals recreate. The result is one of "
            "the most natural sleep environments you can create on a screen.\n\n"
            "Whether you search for 'night rain sounds for sleeping', 'soft piano music for relaxation', "
            "or 'relaxing music for stress relief' — this video is built for exactly that.\n\n"
            "✦ Rain + piano: the perfect combination for sleep onset\n"
            "✦ Consistent soft volume — safe to leave on all night\n"
            "✦ No sudden loud passages or jarring transitions\n\n"
            "🔔 Subscribe → @ClassicalNightRelax\n\n"
            "#NightRainSoundsForSleeping #SoftPianoMusicForRelaxation #RainAndPiano "
            "#SleepMusic #ClassicalMusic #CalmClassics #RelaxingMusicForStressRelief "
            "#ChopinNocturnes #Debussy #SleepMeditationMusic #ClassicalNightRelax "
            "#RainSoundsForSleep #SoftMusicForRelaxation #DeepSleepMusic #PianoSleep"
        ),
        "tags": ["night rain sounds for sleeping", "soft piano music for relaxation",
                 "rain and piano", "sleep music", "classical music", "calm classics",
                 "relaxing music for stress relief", "chopin", "debussy", "sleep meditation music",
                 "soft music for relaxation", "rain sounds for sleep", "piano sleep music",
                 "deep sleep music", "classical music for sleeping", "rain sleep music",
                 "classical night relax", "piano relaxation", "bedtime music", "rain piano"],
        "thumb_prompt": (
            "rainy night window with candlelight inside, rain drops on glass, piano keys reflection, "
            "dark blue exterior wet cobblestones, warm amber interior glow, cinematic, no text"
        ),
        "flux_prompts": [
            "rainy night window interior, rain drops streaming on glass, candle flame reflection, cobblestone street wet below, soft piano implied, cinematic warmth, 16:9",
            "grand piano by large window in dark room, night rain outside, single lamp, sheet music, intimate practice, 16:9",
            "Paris street at night in heavy rain, golden reflections on wet pavement, umbrella person, cafe light, classic atmosphere, 16:9",
            "raindrops falling on dark lake surface, concentric ripples everywhere, night, ambient light from shore, meditative rain, 16:9",
            "rain on old cathedral stone, gargoyle with water streaming, lights below in wet plaza, gothic night atmosphere, 16:9",
            "cozy apartment window at night, city lights blurred through rain on glass, warm bedroom interior, rain vs warmth, 16:9",
            "train window with rain, countryside night blurred outside, warm carriage interior light, solitary journey, 16:9",
            "garden at night in gentle rain, lantern flickering, water on roses and leaves, intimate outdoor night, 16:9",
            "candlelit music room, cello leaning against chair, rain audible outside shuttered window, yellow warm light, 16:9",
            "rain-soaked old European alley at night, cobblestones gleaming, lone lamppost, deep shadows, romantic solitude, 16:9",
            # frame 10-19 (N_IMAGES=20)
            "heavy rain on forest canopy at night, leaves shining wet, streams forming, darkness and water, 16:9",
            "pianist's hands close-up on keys, rain on window behind, depth of field, focused practice in storm, 16:9",
            "rain falling into courtyard garden at night, stone fountain overflowing, plants bowing, enclosed peace, 16:9",
            "window condensation interior, handprint cleared, rain and streetlights outside, cold glass warm hands, 16:9",
            "lighthouse in storm rain, beam sweeping dark sea, waves crashing, isolated warmth of light, 16:9",
            "Japanese temple rain, stone lantern with water dripping, wet moss, grey sky, zen precipitation, 16:9",
            "bedroom with open window, curtain billowing in rain wind, cool air entering warm room, sensory threshold, 16:9",
            "river in rain at night, surface turbulent with drops, distant bridge lights blurred, urban rain, 16:9",
            "mountain cabin at night in rain, thunder implied, lightning flash distant, shelter and storm, 16:9",
            "dawn after rain, wet streets catching first light, birds returning, post-storm stillness and renewal, 16:9",
        ],
        "music_files": [
            "Nocturne in E flat major, Op. 9 no. 2.mp3",
            "Nocturne in B flat minor, Op. 9 no. 1.mp3",
            "Arabesque No. 1. Andantino con moto.mp3",
            "Cello Suite no. 1 - Prelude in G, BWV 1007.mp3",
            "Fantaisie, Op. 79 - Andantino.mp3",
            "Mozart - Serenade in G Major - I. Romance.mp3",
            "Mazurka in A flat major, B. 85.mp3",
            "Violin Concerto in D, Op. 61 - II. Larghetto.mp3",
            "Arabesque no. 1 (string quartet arr.).mp3",
            "Mazurka in C sharp minor, Op. 6 no. 2.mp3",
            "Swan Lake Op.20 - Act II Pt.1.mp3",
            "Adagio in G minor.mp3",
            "Etude Op. 10, no. 6 in E flat minor - 'Lament'.mp3",
            "Adagio for Organ & Strings in g minor.mp3",
            "Piano Concerto No. 2 in C Minor, Op. 18 - II. Adagio sostenuto.mp3",
            "Concerto for 2 Violins in D minor, BWV 1043  - II. Largo ma non tanto.mp3",
        ],
        "mood": "sleep",
        "video_type": "visual_theme",
    },

    "evening_piano": {
        "title": "Soft Piano Music for Relaxation 🎹 {duration} | Classical Piano | Calm Classics",
        "desc": (
            "{duration} of the most beautiful soft piano music for relaxation — Chopin Nocturnes, "
            "Beethoven's Moonlight Sonata, Debussy's Arabesque, Mozart Serenade, and Fauré. "
            "Filmed in candlelit concert halls, grand drawing rooms, and intimate music studios, "
            "this is the definitive soft piano music for stress relief and sleep.\n\n"
            "🎵 Music: Frédéric Chopin — Nocturnes Op. 9 & Mazurkas "
            "| Ludwig van Beethoven — Moonlight Sonata "
            "| Claude Debussy — Arabesque No. 1 "
            "| W.A. Mozart — Serenade in G Major "
            "| Gabriel Fauré — Fantaisie Op. 79\n"
            "🎨 Visuals: AI-generated grand piano and concert hall scenes\n"
            "📜 All recordings: Public Domain (Musopen.org)\n\n"
            "Soft piano music has a unique neurological effect: the slow sustain of each note, "
            "the predictable harmonic movement, and the absence of rhythm section instrumentation "
            "all combine to reduce cortisol, lower heart rate, and prepare the brain for sleep. "
            "This is why 'soft piano music for relaxation' is one of the most searched music "
            "queries worldwide — people instinctively reach for it when they need to decompress.\n\n"
            "This video brings together the greatest composers of soft piano music in Western "
            "history: Chopin (the undisputed master of the piano nocturne), Debussy (whose "
            "Arabesque is perhaps the most instantly calming piece ever written), Beethoven "
            "(whose Moonlight Sonata remains the gold standard of sleep music), and Mozart.\n\n"
            "✦ Perfect for: sleep, meditation, stress relief, reading, spa, yoga\n"
            "✦ No drums, no bass, no rhythm section — pure piano calm\n"
            "✦ Seamless transitions — no jolts, no abrupt changes\n\n"
            "🔔 Subscribe → @ClassicalNightRelax\n\n"
            "#SoftPianoMusicForRelaxation #SoftMusicForRelaxation #SleepMeditationMusic "
            "#ClassicalPiano #CalmClassics #RelaxingMusicForStressRelief "
            "#BestOfChopinNocturnes #BeethovenMoonlight #Debussy #Mozart "
            "#PianoSleep #ClassicalMusicForSleeping #ClassicalNightRelax "
            "#SleepMusic #PianoRelaxation #DeepSleepMusic #MeditationMusic"
        ),
        "tags": ["soft piano music for relaxation", "soft music for relaxation",
                 "sleep meditation music", "relaxing music for stress relief",
                 "best of chopin nocturnes", "classical piano", "calm classics",
                 "beethoven moonlight sonata", "debussy arabesque", "mozart",
                 "piano sleep music", "deep sleep music", "classical music for sleeping",
                 "piano relaxation", "chopin nocturnes", "classical night relax",
                 "meditation music", "stress relief music", "bedtime piano", "piano calm"],
        "thumb_prompt": (
            "grand concert piano in beautiful candlelit hall, single spotlight, dark wood and gold, "
            "soft atmosphere, classical elegance, evening piano recital, no text"
        ),
        "flux_prompts": [
            "grand Steinway piano in candlelit concert hall, single spotlight, dark wood panelling, gold chandelier glow, classical elegance, 16:9",
            "hands playing piano close-up, elegant fingers on ivory keys, soft light from left, movement and music implied, 16:9",
            "upright piano in old French drawing room, tall windows with evening light, vase of white flowers, Chopin era, 16:9",
            "piano in conservatory, glass ceiling with stars, ivy on columns, romantic night recital, botanical garden setting, 16:9",
            "grand piano on empty stage, single spotlight from above, all else in darkness, pure focus on instrument, 16:9",
            "piano keys close-up extreme, black and white abstract, light from left, texture of ivory, minimalist, 16:9",
            "piano in corner of library, books floor to ceiling, lamp lit, winter evening, intellectual cozy, 16:9",
            "concert pianist bowing after performance, empty gilded hall, echoes of applause implied, solitary art, 16:9",
            "old upright piano in abandoned mansion, faded grandeur, dust motes in light beam, keys yellowed, 16:9",
            "child's hands on piano keys for first time, small fingers, parent's hands guiding, warm home evening, 16:9",
            # frame 10-19 (N_IMAGES=20)
            "piano in beach house at sunset, window open to sea, last light on keys, salty air and music, 16:9",
            "sheet music on piano stand, Chopin nocturne pages, lamp illuminating notation, intimate practice, 16:9",
            "piano in Paris apartment, balcony door open, Eiffel Tower distant, evening city and music, 16:9",
            "antique fortepiano 1800s, period instrument, classical sitting room, candlelight, Mozart era, 16:9",
            "piano lid open, strings visible inside, hammer mechanism exposed, instrument anatomy, beautiful engineering, 16:9",
            "winter piano practice, frost on window, heating radiator, tea steam, student working alone, 16:9",
            "outdoor piano in autumn garden, leaves falling on keys, unusual installation, nature and culture, 16:9",
            "piano keyboard reflection in wine glass, candlelit restaurant, intimate dinner background music, 16:9",
            "jazz club after hours empty, piano in spotlight, cigarette smoke and memory, noir atmosphere, 16:9",
            "piano in monastery courtyard, stone arches, afternoon light, monk approaching, sacred and musical, 16:9",
        ],
        "music_files": [
            "Nocturne in E flat major, Op. 9 no. 2.mp3",
            "Nocturne in B flat minor, Op. 9 no. 1.mp3",
            "Piano Sonata no. 14 in C#m 'Moonlight', Op. 27 no. 2 - I. Adagio sostenuto.mp3",
            "Arabesque No. 1. Andantino con moto.mp3",
            "Mozart - Serenade in G Major - I. Romance.mp3",
            "Mozart - Serenade in G Major - II. Minuet.mp3",
            "Mozart - Serenade in G Major - III. Rondo.mp3",
            "Mazurka in A flat major, B. 85.mp3",
            "Mazurka in C sharp minor, Op. 6 no. 2.mp3",
            "Mazurka in E major, Op. 6 no. 3.mp3",
            "Fantaisie, Op. 79 - Andantino.mp3",
            "Cello Sonata No. 4, mov. 1 - Ben Larsen, Ava Nazar.mp3",
            "Adagio in G minor.mp3",
            "Etude Op. 10, no. 6 in E flat minor - 'Lament'.mp3",
            "Ballade no. 1 in G minor, Op. 23.mp3",
            "Adagio for Organ & Strings in g minor.mp3",
            "Piano Concerto No. 2 in C Minor, Op. 18 - II. Adagio sostenuto.mp3",
            "Julia Florida.mp3",
        ],
        "mood": "sleep",
        "video_type": "visual_theme",
    },

    # ── Nature Soundscape series (Suno AI ambient) ─────────────────────────────

    "distant_waterfall": {
        "title": "Distant Waterfall 🌊 {duration} | Nature Sounds for Sleep & Meditation | Calm Classics",
        "desc": (
            "{duration} of the most soothing waterfall sounds ever recorded — a distant cascade echoing "
            "through ancient stone, surrounded by birdsong and forest air. Let the gentle, unceasing flow "
            "carry away your stress and guide you into deep, restorative sleep.\n\n"
            "🌊 Nature sounds: AI-crafted waterfall ambience — distant cascade, mist, trickling streams\n"
            "🎨 Visuals: AI-generated waterfall and river landscapes\n"
            "🎵 Original ambient audio by Calm Classics (AI-generated, © 2026)\n\n"
            "Perfect for: sleep, meditation, white noise, stress relief, study, focus, yoga, spa\n\n"
            "Many viewers use waterfall sounds to:\n"
            "✦ Fall asleep faster and stay asleep longer\n"
            "✦ Mask unwanted background noise (traffic, neighbours)\n"
            "✦ Reach deeper meditation states\n"
            "✦ Focus during study or creative work\n"
            "✦ Relieve anxiety and calm an overactive mind\n\n"
            "Loop this video all night — the seamless audio never repeats awkwardly.\n\n"
            "Subscribe → @ClassicalNightRelax\n\n"
            "#WaterfallSounds #NatureSounds #SleepSounds #WhiteNoise #MeditationMusic "
            "#WaterSounds #RelaxingNature #SleepAid #StudyMusic #CalmClassics "
            "#AmbientMusic #StressRelief #DeepSleep #FocusMusic #NatureAmbience"
        ),
        "tags": ["waterfall sounds", "nature sounds", "sleep sounds", "white noise",
                 "meditation music", "water sounds", "relaxing nature", "sleep aid",
                 "study music", "calm classics", "ambient music", "stress relief",
                 "deep sleep", "focus music", "nature ambience", "waterfall white noise",
                 "rain sounds", "river sounds", "spa music", "yoga music"],
        "thumb_prompt": (
            "stunning tropical waterfall cascading into emerald pool, lush green jungle, "
            "mist rising from water, golden sunlight rays, peaceful and majestic, "
            "cinematic photography, no text"
        ),
        "flux_prompts": [
            "powerful tropical waterfall cascading 30 meters into emerald pool, lush jungle surrounding, mist rising, golden sunlight through canopy, paradise nature, 16:9",
            "serene mountain waterfall over mossy rocks, crystal clear stream, ancient ferns, dappled forest light, peaceful wilderness, 16:9",
            "aerial view waterfall flowing from cliff into blue lagoon, white water foam, jungle canopy, remote tropical island, 16:9",
            "waterfall at night with moonlight illuminating mist, long exposure photography, silvery cascade, dark forest, magical atmosphere, 16:9",
            "small gentle waterfall over smooth river stones, clear stream, forest floor, autumn leaves floating, intimate nature scene, 16:9",
            "Iceland waterfall in volcanic landscape, powerful cascade, black basalt rock, green moss, dramatic cloudy sky, 16:9",
            "waterfall reflection in still forest pool, mirror image of falling water, lily pads, dragonfly, perfect symmetry, 16:9",
            "close-up waterfall detail, water droplets spray, slow motion style, translucent white foam, soft focus background, 16:9",
            "misty morning waterfall in bamboo forest, fog drifting, Japanese garden aesthetic, stone steps beside, serene, 16:9",
            "secret waterfall behind curtain of water, cave entrance, glowing turquoise pool, magical hidden paradise, 16:9",
        ],
        "music_source": "meditation",
        "music_glob": "Sound Design Distant Waterfall*.mp3",
        "music_files": [],
        "mood": "sleep",
        "video_type": "visual_theme",
    },

    "rainforest_night": {
        "title": "Rainforest at Night 🌿 {duration} | Jungle Night Sounds for Sleep | Calm Classics",
        "desc": (
            "Drift into the living world of the rainforest after dark — crickets, distant frogs, "
            "rustling leaves, and the breathing of an ancient jungle ecosystem. {duration} of pure, "
            "immersive rainforest night sounds to help you sleep deeply and naturally.\n\n"
            "🌿 Nature sounds: AI-crafted tropical rainforest night ambience\n"
            "🎨 Visuals: AI-generated rainforest and jungle landscapes\n"
            "🎵 Original ambient audio by Calm Classics (AI-generated, © 2026)\n\n"
            "Perfect for: sleep, meditation, relaxation, ASMR, white noise, stress relief\n\n"
            "Why jungle night sounds work for sleep:\n"
            "✦ Natural rhythmic patterns prime the brain for sleep\n"
            "✦ Continuous sound masks sudden noise disturbances\n"
            "✦ Evolutionary connection — humans evolved sleeping to nature sounds\n"
            "✦ Reduces cortisol and activates the parasympathetic nervous system\n\n"
            "Subscribe → @ClassicalNightRelax\n\n"
            "#RainforestSounds #JungleSounds #NightSounds #SleepSounds #NatureSounds "
            "#TropicalAmbience #MeditationMusic #WhiteNoise #CalmClassics "
            "#AmbientMusic #DeepSleep #StressRelief #NatureAmbience #SleepAid"
        ),
        "tags": ["rainforest sounds", "jungle sounds", "night sounds", "sleep sounds",
                 "nature sounds", "tropical ambience", "meditation music", "white noise",
                 "calm classics", "ambient music", "deep sleep", "stress relief",
                 "nature ambience", "sleep aid", "insect sounds", "frog sounds",
                 "jungle night", "tropical forest", "rain forest", "ASMR nature"],
        "thumb_prompt": (
            "magical rainforest at night, bioluminescent plants glowing blue and green, "
            "mist between ancient trees, moonlight filtering through dense canopy, "
            "mystical jungle atmosphere, cinematic photography, no text"
        ),
        "flux_prompts": [
            "tropical rainforest at night, bioluminescent plants and fungi glowing electric blue, moonlight through dense canopy, ancient trees, mystical atmosphere, 16:9",
            "jungle waterfall at dusk, last light on lush green foliage, exotic birds silhouetted, fireflies beginning to glow, 16:9",
            "close-up rainforest floor at night, glowing mushrooms, wet leaves catching moonlight, insects on bark, macro jungle life, 16:9",
            "aerial view tropical rainforest, moonlit canopy stretching to horizon, mist in valleys, river glinting below, vast wilderness, 16:9",
            "rainforest stream at night, moonlight on water, fireflies above surface, frogs on rocks, tree roots, 16:9",
            "Amazon jungle interior, shafts of moonlight through enormous leaves, spider monkeys sleeping, bromeliads, ancient vines, 16:9",
            "tropical rain beginning to fall in jungle, large drops on giant leaves, steam rising, golden insects flying, 16:9",
            "rainforest sunrise mist, sun rays piercing canopy, howler monkeys in trees, parrots flying, spectacular morning light, 16:9",
            "jungle night sky through canopy gap, stars above ancient trees, southern cross visible, milky way, total wilderness, 16:9",
            "rainforest waterfall grotto at night, bioluminescent blue pool, ferns and moss lit green, hidden paradise, 16:9",
        ],
        "music_source": "meditation",
        "music_glob": "Sound Design Rainforest at Night*.mp3",
        "music_files": [],
        "mood": "sleep",
        "video_type": "visual_theme",
    },

    "mountain_lake_dawn": {
        "title": "Mountain Lake at Dawn 🏔️ {duration} | Nature Sounds for Sleep & Relaxation | Calm Classics",
        "desc": (
            "The stillness before sunrise — water so calm it mirrors the mountains perfectly. "
            "{duration} of serene mountain lake ambience at dawn: gentle lapping water, distant "
            "birdsong, the whisper of morning wind. Pure natural peace.\n\n"
            "🏔️ Nature sounds: AI-crafted mountain lake dawn ambience\n"
            "🎨 Visuals: AI-generated alpine lake and mountain landscapes\n"
            "🎵 Original ambient audio by Calm Classics (AI-generated, © 2026)\n\n"
            "Perfect for: sleep, morning meditation, yoga, study, relaxation, mindfulness\n\n"
            "✦ Reduce anxiety and mental chatter\n"
            "✦ Perfect background for morning meditation or journaling\n"
            "✦ Create a peaceful home office atmosphere\n"
            "✦ Use as gentle sleep induction — let the stillness slow your mind\n\n"
            "Subscribe → @ClassicalNightRelax\n\n"
            "#MountainLake #NatureSounds #DawnSounds #SleepSounds #MeditationMusic "
            "#AlpineAmbience #MorningMeditation #CalmClassics #AmbientMusic "
            "#WaterSounds #StressRelief #YogaMusic #MindfulnessMusic #Relaxation"
        ),
        "tags": ["mountain lake", "nature sounds", "dawn sounds", "sleep sounds",
                 "meditation music", "alpine ambience", "morning meditation",
                 "calm classics", "ambient music", "water sounds", "stress relief",
                 "yoga music", "mindfulness music", "relaxation", "lake sounds",
                 "bird sounds", "morning sounds", "peaceful nature", "alpine lake"],
        "thumb_prompt": (
            "perfect mirror reflection of snow-capped mountains in crystal clear alpine lake at dawn, "
            "pink and orange sunrise colors, mist on water surface, pine forest shoreline, "
            "breathtaking tranquil landscape, cinematic photography, no text"
        ),
        "flux_prompts": [
            "perfect mirror reflection of snow-capped mountain peaks in crystal alpine lake at dawn, pink sunrise colors, mist rising from water, pine forest shore, breathtaking tranquility, 16:9",
            "mountain lake at first light, lone wooden rowing boat, still water, golden horizon, single pine tree silhouette, utter silence implied, 16:9",
            "alpine lake surrounded by wildflowers, purple lupines and yellow buttercups, turquoise water, mountain backdrop, summer morning, 16:9",
            "mountain lake shoreline with smooth stones, crystal water revealing pebbles below, gentle ripples, mountains beyond, meditative, 16:9",
            "fog dissolving over mountain lake at sunrise, ghostly trees emerging, warm light breaking through, spiritual dawn atmosphere, 16:9",
            "mountain lake at golden hour, dramatic orange sky reflected, single eagle flying, vast alpine wilderness, cinematic, 16:9",
            "close-up mountain lake water surface, ripple circles, underwater pebbles, reflections of blue sky and clouds, calming detail, 16:9",
            "Norwegian fjord lake, dramatic cliffs dropping into still water, small village distant, misty mountain tops, peaceful grandeur, 16:9",
            "Dolomites alpine lake turquoise, jagged rocky peaks dramatic, clouds casting shadow, remote beauty, Italian Alps, 16:9",
            "mountain lake winter ice beginning to thaw, half frozen, spring light, reflections, geese arriving, seasonal renewal, 16:9",
        ],
        "music_source": "meditation",
        "music_glob": "Sound Design Mountain Lake at Dawn*.mp3",
        "music_files": [],
        "mood": "sleep",
        "video_type": "visual_theme",
    },

    "desert_night_wind": {
        "title": "Desert Night Wind 🌙 {duration} | Desert Sounds for Sleep | Calm Classics",
        "desc": (
            "The Sahara after midnight — a world of infinite silence broken only by warm desert wind "
            "moving across ancient dunes. {duration} of hypnotic desert night sounds: shifting sands, "
            "distant wind, the vast breathing of the world's greatest desert.\n\n"
            "🌙 Nature sounds: AI-crafted desert night ambience\n"
            "🎨 Visuals: AI-generated desert and dune landscapes\n"
            "🎵 Original ambient audio by Calm Classics (AI-generated, © 2026)\n\n"
            "Perfect for: deep sleep, meditation, insomnia relief, focus, relaxation\n\n"
            "Desert sounds are uniquely effective for sleep:\n"
            "✦ The low-frequency wind creates a natural brown noise effect\n"
            "✦ The sensation of vast empty space calms an anxious mind\n"
            "✦ Shifts brain into deep theta wave states associated with meditation\n\n"
            "Subscribe → @ClassicalNightRelax\n\n"
            "#DesertSounds #NightSounds #SleepSounds #BrownNoise #MeditationMusic "
            "#SaharaSounds #WindSounds #CalmClassics #AmbientMusic "
            "#DeepSleep #InsomniaCure #RelaxingNature #NatureAmbience #Meditation"
        ),
        "tags": ["desert sounds", "night sounds", "sleep sounds", "brown noise",
                 "meditation music", "sahara", "wind sounds", "calm classics",
                 "ambient music", "deep sleep", "insomnia", "relaxing nature",
                 "nature ambience", "meditation", "desert night", "sand dunes",
                 "desert wind", "desert ambience", "sleep aid", "white noise"],
        "thumb_prompt": (
            "vast Sahara desert sand dunes at night under spectacular Milky Way, "
            "warm golden sand reflecting starlight, single palm tree silhouette, "
            "infinite star field, magical desert night, cinematic photography, no text"
        ),
        "flux_prompts": [
            "vast Sahara desert sand dunes at night, Milky Way galaxy overhead, warm golden sand glowing under starlight, infinite wilderness, magic and solitude, 16:9",
            "desert dunes at twilight, last ember glow on horizon, first stars appearing, purple and orange sky, sand ripples, vast emptiness, 16:9",
            "Wadi Rum Jordan desert at night, ancient red rock formations, full moon rising, bright stars, dramatic alien landscape, 16:9",
            "desert campfire at night, embers glowing, camel sleeping nearby, dunes silhouetted against star field, Bedouin atmosphere, 16:9",
            "aerial view desert dunes at dusk, perfect wave patterns in sand, shadow and light contrast, abstract beauty, 16:9",
            "desert oasis at night, palm trees around small pool, reflection of stars in water, dry landscape surrounding, hidden paradise, 16:9",
            "sand dune crest at sunrise, perfect crescent line, golden and purple shadow side, lone footprint trail, minimalist beauty, 16:9",
            "desert rock canyon at night, narrow passage, stars framed above, ancient stone walls, mysterious and vast, 16:9",
            "Namib desert coastal dunes meeting ocean at night, fog rolling in, stars above, unique world's edge landscape, 16:9",
            "desert floor detail at golden hour, cracked earth, single desert flower, vast horizon, extreme minimalism, 16:9",
        ],
        "music_source": "meditation",
        "music_glob": "Sound Design Desert Night Wind*.mp3",
        "music_files": [],
        "mood": "sleep",
        "video_type": "visual_theme",
    },

    "winter_forest_silence": {
        "title": "Winter Forest ❄️ {duration} | Snow Sounds for Sleep & Relaxation | Calm Classics",
        "desc": (
            "Step into the sacred silence of a snow-covered forest. {duration} of pure winter "
            "forest ambience — the creak of frozen branches, a distant owl, the profound stillness "
            "that only snow can create. One of the most requested sleep sounds.\n\n"
            "❄️ Nature sounds: AI-crafted winter forest silence ambience\n"
            "🎨 Visuals: AI-generated winter forest and snow landscapes\n"
            "🎵 Original ambient audio by Calm Classics (AI-generated, © 2026)\n\n"
            "Perfect for: sleep, deep meditation, reading, relaxation, cozy evenings\n\n"
            "✦ Snow absorbs sound — mimicking this creates a profoundly calming effect\n"
            "✦ The subtle forest sounds prevent total silence (which can be disturbing)\n"
            "✦ Ideal for people who find rain sounds too stimulating\n"
            "✦ Works perfectly combined with a blanket and warm drink\n\n"
            "Subscribe → @ClassicalNightRelax\n\n"
            "#WinterForest #SnowSounds #NatureSounds #SleepSounds #ForestSounds "
            "#WinterAmbience #CozySounds #CalmClassics #AmbientMusic "
            "#DeepSleep #MeditationMusic #Relaxation #NatureAmbience #WhiteNoise"
        ),
        "tags": ["winter forest", "snow sounds", "nature sounds", "sleep sounds",
                 "forest sounds", "winter ambience", "cozy sounds", "calm classics",
                 "ambient music", "deep sleep", "meditation music", "relaxation",
                 "nature ambience", "white noise", "snowfall sounds", "winter sleep",
                 "forest ambience", "peaceful winter", "sleep aid", "frozen forest"],
        "thumb_prompt": (
            "magical snow-covered pine forest at night, snowflakes falling gently, "
            "moonlight illuminating white trees, deep blue shadows, ethereal winter silence, "
            "breathtaking winter scenery, cinematic photography, no text"
        ),
        "flux_prompts": [
            "magical snow-covered pine forest at night, large snowflakes falling, moonlight through trees casting blue shadows, pristine white silence, ethereal winter scene, 16:9",
            "winter forest path, footprints in deep snow, ancient trees bowed with weight, soft grey overcast sky, peaceful solitude, 16:9",
            "frozen stream in winter forest, ice formations on rocks, snow-covered banks, bare tree reflections in dark water, 16:9",
            "winter forest at sunrise, golden light hitting snow-laden branches, steam from warming snow, morning birds, magical awakening, 16:9",
            "owl perched on snow-covered pine branch at night, large eyes reflecting moonlight, silent predator, frozen forest, 16:9",
            "looking up through winter forest canopy, snow-dusted branches against grey sky, geometric bare tree patterns, calming abstraction, 16:9",
            "forest clearing in winter, perfect circle of snow, surrounded by dark pine trees, single deer tracks crossing, serene, 16:9",
            "heavy snowfall in forest, fat flakes blurring distant trees, close branches sharp, hypnotic depth, 16:9",
            "winter forest after ice storm, every branch coated in transparent ice, crystal world, dramatic low sun light, 16:9",
            "deep winter forest at dusk, last purple light through trees, first stars, snow blue-grey, absolute stillness, 16:9",
        ],
        "music_source": "meditation",
        "music_glob": "Sound Design Winter Forest Silence*.mp3",
        "music_files": [],
        "mood": "sleep",
        "video_type": "visual_theme",
    },

    "ambient_meditation_mix": {
        "title": "Ambient Meditation Mix 🎧 {duration} | Deep Relaxation & Sleep Sounds | Calm Classics",
        "desc": (
            "{duration} of carefully curated ambient meditation soundscapes — an ever-shifting "
            "journey through ice caves, distant waterfalls, cosmic drones, and ethereal tones. "
            "No single mood dominates; the mix breathes and evolves, keeping your mind just "
            "engaged enough to stay out of anxious thought while drifting toward sleep.\n\n"
            "🎧 Ambient mix: AI-crafted meditative soundscapes\n"
            "🎨 Visuals: AI-generated abstract and natural meditation environments\n"
            "🎵 Original ambient audio by Calm Classics (AI-generated, © 2026)\n\n"
            "What's in the mix:\n"
            "✦ Crystal ice cave resonance\n"
            "✦ Deep ambient drones and pads\n"
            "✦ Nature-infused textures\n"
            "✦ Soft tonal meditative layers\n\n"
            "Perfect for: sleep, deep meditation, float tank, yoga nidra, anxiety relief, study\n\n"
            "Subscribe → @ClassicalNightRelax\n\n"
            "#AmbientMusic #MeditationMusic #SleepSounds #DeepRelaxation #AmbientMix "
            "#IceCave #CalmClassics #SoundHealing #YogaNidra #DeepSleep "
            "#AnxietyRelief #AmbientMeditation #SleepAid #RelaxingMusic #MindfulMusic"
        ),
        "tags": ["ambient music", "meditation music", "sleep sounds", "deep relaxation",
                 "ambient mix", "ice cave sounds", "calm classics", "sound healing",
                 "yoga nidra", "deep sleep", "anxiety relief", "ambient meditation",
                 "sleep aid", "relaxing music", "mindful music", "drone music",
                 "space ambient", "crystal sounds", "meditation sounds", "sleep music"],
        "thumb_prompt": (
            "ethereal ice cave with blue glowing crystal formations, frozen stalactites, "
            "mysterious blue light reflecting on ice walls, magical and otherworldly, "
            "cinematic photography, no text"
        ),
        "flux_prompts": [
            "ethereal blue ice cave interior, frozen crystal stalactites, glowing turquoise light, ancient glacial formations, otherworldly and magical, 16:9",
            "abstract cosmic nebula-like ice formations, electric blue and white, deep space aesthetic but earthly, abstract art, 16:9",
            "glacial cave entrance at night, blue ice glow from inside, stars visible above frozen tundra, mysterious, 16:9",
            "underwater ice formations, pale blue light, frozen sculptures, abstract natural geometry, serene alien world, 16:9",
            "ice cave with frozen waterfall, blue stalactites, crystal floor, cold light, vast silent space, 16:9",
            "abstract meditation space, floating geometric light forms, deep blue and purple, infinite depth, minimalist, 16:9",
            "glacial lake inside ice cave, perfect reflection of blue ceiling, still water, absolute silence implied, 16:9",
            "ice crystal macro, intricate fractal patterns, cold blue tones, natural mathematical beauty, 16:9",
            "arctic night sky above frozen tundra, aurora borealis in soft blue and white, perfect silence, 16:9",
            "deep underground crystal cave, white and blue mineral formations, single shaft of light, meditative depth, 16:9",
        ],
        "music_source": "meditation",
        "music_glob": "Sound Design Glacier Ice Cave*.mp3",
        "music_files": [],
        "mood": "sleep",
        "video_type": "visual_theme",
    },
}


# ── Together.ai image generation ───────────────────────────────────────────────

TOGETHER_URL   = "https://api.together.xyz/v1/images/generations"
TOGETHER_MODEL = "black-forest-labs/FLUX.1.1-pro"


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
            headers={"Authorization": f"Bearer {api_key}", "User-Agent": "python-requests/2.31.0"},
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

def build_music_track(music_files: list[str], target_secs: int, tmp_dir: Path,
                      music_dir: Optional[Path] = None,
                      music_glob: Optional[str] = None) -> Optional[Path]:
    """Concatenate music files in a loop until target_secs is reached."""
    base_dir = music_dir or MUSIC_DIR
    if music_glob:
        available = sorted(base_dir.glob(music_glob))
    else:
        available = [base_dir / f for f in music_files if (base_dir / f).exists()]
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
        # Normalize to 44100 Hz stereo before encoding — fixes mixed-format sources
        # (e.g. 22050 Hz mono files degrading the whole concat to 89 kbps output).
        # aresample=async=1 also fills tiny inter-track gaps that cause audible dropouts.
        "-af", "aresample=async=1:min_hard_comp=0.1:first_pts=0,aformat=sample_rates=44100:channel_layouts=stereo",
        "-c:a", "libmp3lame", "-b:a", "192k",
        str(audio_out),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if r.returncode != 0 or not audio_out.exists():
        log.error(f"  Music build failed: {r.stderr[-300:]}")
        return None
    return audio_out


def assemble_long_video(loop_mp4: Path, music_files: list[str],
                         duration_hours: int, out_mp4: Path,
                         music_dir: Optional[Path] = None,
                         music_glob: Optional[str] = None) -> bool:
    """Stream-loop the visual loop + overlay music → output video."""
    target_secs = duration_hours * 3600
    preset = "slow" if duration_hours <= 1 else ("medium" if duration_hours <= 3 else "fast")

    tmp_dir = ROOT / "output" / "_tmp_visual_theme"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    audio_mp3 = build_music_track(music_files, target_secs, tmp_dir,
                                   music_dir=music_dir, music_glob=music_glob)

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

def append_outro(main_mp4: Path, outro_mp4: Path, out_mp4: Path) -> bool:
    """Concatenate main video + outro clip using FFmpeg concat demuxer."""
    import tempfile as _tf
    tmp_list = Path(_tf.mktemp(suffix=".txt"))
    tmp_list.write_text(
        f"file '{main_mp4.resolve()}'\nfile '{outro_mp4.resolve()}'\n"
    )
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(tmp_list),
        "-c", "copy",
        str(out_mp4),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
    tmp_list.unlink(missing_ok=True)
    if r.returncode != 0 or not out_mp4.exists():
        log.error(f"  outro concat failed: {r.stderr[-300:]}")
        return False
    log.info(f"  ✓ outro appended → {out_mp4.name}")
    return True


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


THUMB_FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"

def _add_thumb_text(img, text: str, duration_hours: Optional[int] = None):
    """Overlay bold text on thumbnail image — delegates to shared thumb_text.py."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("tt", Path(__file__).resolve().parent / "thumb_text.py")
    tt = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tt)
    return tt.add_thumb_text(img, text, duration_hours=duration_hours)


def generate_thumbnail(theme: str, theme_cfg: dict, out_mp4: Path, api_key: str,
                       duration_hours: Optional[int] = None) -> bool:
    thumb_path = out_mp4.parent / f"thumb_{out_mp4.stem}.png"
    if thumb_path.exists() and thumb_path.stat().st_size > 0:
        return True

    prompt = theme_cfg["thumb_prompt"]
    data = generate_image(prompt, api_key, width=1280, height=704)
    if not data:
        return False

    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(data)).resize((1280, 720), Image.LANCZOS).convert("RGB")
        # Derive display title from theme config title (strip emoji + duration placeholder)
        import re as _re
        raw_title = theme_cfg.get("title", theme.replace("_", " ").title())
        thumb_label = _re.sub(r"\s*\{duration\}.*", "", raw_title).strip()
        thumb_label = _re.sub(r"^[^\w]+", "", thumb_label).strip()  # strip leading emoji
        img = _add_thumb_text(img, thumb_label, duration_hours=duration_hours)
        buf = io.BytesIO()
        img.save(buf, "PNG")
        thumb_path.write_bytes(buf.getvalue())
        log.info(f"  Thumb → {thumb_path.name}")
        return True
    except Exception as e:
        log.warning(f"  Thumb error: {e} — saving raw")
        thumb_path.write_bytes(data)
        return True


# ── Main processing ────────────────────────────────────────────────────────────

def process_theme(theme: str, durations: list[int], api_key: str,
                  force: bool = False, regen_images: bool = False,
                  regen_loop: bool = False, dry_run: bool = False,
                  with_outro: str | None = None) -> int:
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

        mdir  = MEDITATION_DIR if theme_cfg.get("music_source") == "meditation" else None
        mglob = theme_cfg.get("music_glob")
        assembled = assemble_long_video(loop_path, theme_cfg.get("music_files", []), dur, out_mp4,
                                        music_dir=mdir, music_glob=mglob)
        if assembled:
            # Optional: append outro clip
            if with_outro:
                outro_mp4 = Path(with_outro)
                if outro_mp4.exists():
                    out_with_outro = QUEUE_ID / f"visual_theme_{theme}_{dur}h_{DATE_STR}_outro.mp4"
                    if append_outro(out_mp4, outro_mp4, out_with_outro):
                        out_mp4.unlink()
                        out_with_outro.rename(out_mp4)
                else:
                    log.warning(f"  --with-outro: file not found: {outro_mp4}")
            write_meta(theme, theme_cfg, out_mp4, dur)
            generate_thumbnail(theme, theme_cfg, out_mp4, api_key, duration_hours=dur)
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
    parser.add_argument("--with-outro",  metavar="OUTRO_MP4",
                        help="Append outro clip to each assembled video (e.g. output/_outros/outro_cnr.mp4)")
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
            with_outro=getattr(args, "with_outro", None),
        )
        total_done += done

    log.info(f"\nDone: {total_done} video(s)")


if __name__ == "__main__":
    main()
