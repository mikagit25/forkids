#!/usr/bin/env python3
"""
Generate CNR Shorts (50s vertical 1080×1920) from visual loop files.
Sources: output/_visual_loops/  (FLUX AI images, Ken Burns)
         output/_nature_loops/  (nature footage loops)
Music:   assets/music/classical/Music/  (Musopen PD/CC0)
         remotion/public/music/          (Suno AI tracks)
Output:  output/queue_id/  (made_for_kids: false, is_short: true)

--batch:          10 themes × 3 offsets = 30 Shorts (calming sleep / bedtime sounds / sleep ambience)
--keywords-batch: 9 keyword themes × 2 offsets = 18 Shorts targeting popular YouTube search queries:
                  soft piano music for relaxation | night rain sounds for sleeping |
                  relaxing music for studying | sleep meditation music |
                  relaxing music for stress relief | the best of chopin nocturnes

Usage:
    python3 scripts/make_visual_shorts.py --dry-run
    python3 scripts/make_visual_shorts.py --batch
    python3 scripts/make_visual_shorts.py --keywords-batch
    python3 scripts/make_visual_shorts.py --theme aurora_borealis
    python3 scripts/make_visual_shorts.py --kw-theme rain_night --offset 60
"""
import argparse
import base64
import io
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import requests
import yaml

ROOT              = Path(__file__).resolve().parent.parent
VISUAL_LOOPS_DIR  = ROOT / "output" / "_visual_loops"
NATURE_LOOPS_DIR  = ROOT / "output" / "_nature_loops"
QUEUE_CC          = ROOT / "output" / "queue_id"
MUSIC_DIR         = ROOT / "assets" / "music" / "classical" / "Music"
SUNO_DIR          = ROOT / "remotion" / "public" / "music"
TOGETHER_KEY_FILE = ROOT / "credentials" / "together_api_key.txt"
TOGETHER_URL      = "https://api.together.xyz/v1/images/generations"
TOGETHER_MODEL    = "black-forest-labs/FLUX.1-schnell"
DATE_STR          = datetime.now().strftime("%Y%m%d")

SHORT_DURATION = 50   # seconds — longer than 45 for better watch time signal
FADE_SECS      = 2

# 3 start offsets per theme to produce 3 distinct clips from each loop
BATCH_OFFSETS = [0, 60, 120]

# Classical music per theme (all Musopen PD/CC0)
THEME_MUSIC = {
    "aurora_borealis":   "Nocturne in E flat major, Op. 9 no. 2.mp3",        # Chopin
    "cherry_blossoms":   "Arabesque No. 1. Andantino con moto.mp3",           # Debussy
    "fireplace_cabin":   "Fantaisie, Op. 79 - Andantino.mp3",                 # Fauré
    "lavender_fields":   "Mozart - Serenade in G Major - I. Romance.mp3",     # Mozart
    "mountain_snow":     "Piano Sonata no. 14 in C#m 'Moonlight', Op. 27 no. 2 - I. Adagio sostenuto.mp3",
    "autumn_forest":     "Violin Concerto in D, Op. 61 - II. Larghetto.mp3",  # Beethoven
    "zen_garden":        "3 Fantaisies for Solo Flute, Op. 38 - Fantaisie no. 1.mp3",  # Telemann
    "deep_space":        "Nocturne in B flat minor, Op. 9 no. 1.mp3",         # Chopin
    "distant_waterfall": "Cello Suite no. 1 - Prelude in G, BWV 1007.mp3",    # Bach
    "rainforest_night":  "Swan Lake Op.20 - Act II Pt.1.mp3",                 # Tchaikovsky
}

# Composer label for meta
THEME_COMPOSER = {
    "aurora_borealis":   "Chopin",
    "cherry_blossoms":   "Debussy",
    "fireplace_cabin":   "Fauré",
    "lavender_fields":   "Mozart",
    "mountain_snow":     "Beethoven",
    "autumn_forest":     "Beethoven",
    "zen_garden":        "Telemann",
    "deep_space":        "Chopin",
    "distant_waterfall": "Bach",
    "rainforest_night":  "Tchaikovsky",
}

THEME_META = {
    "aurora_borealis": {
        "title":        "🌌 Aurora Borealis | Chopin Sleep Music | Classical Night Relax #shorts",
        "desc_en":      (
            "Drift into peaceful sleep with the Northern Lights and Chopin's gentle Nocturne.\n\n"
            "✨ Sleep ambience for deep rest\n"
            "🎹 Frédéric Chopin — Nocturne in E flat major, Op. 9 no. 2\n"
            "🎧 Best with headphones at low volume\n\n"
            "Full sleep programs on our channel ▶ @ClassicalNightRelax\n\n"
            "#calmingsleep #sleepambience #chopinnocturne #classicalmusic #northernlights "
            "#sleepmusic #bedtimesounds #classicalnightrelax #shorts #relaxingmusic"
        ),
        "thumb_prompt": "stunning aurora borealis northern lights, green purple ribbons over dark night sky, peaceful sleep ambience, cinematic, no text",
        "tags": ["calming sleep", "sleep ambience", "aurora borealis", "Chopin", "nocturne",
                 "classical music shorts", "bedtime sounds", "sleep music", "northern lights",
                 "classical night relax", "relaxing music", "shorts"],
    },
    "cherry_blossoms": {
        "title":        "🌸 Cherry Blossoms | Debussy Sleep Ambience | Classical Night Relax #shorts",
        "desc_en":      (
            "Soft cherry blossoms falling gently to Debussy's dreamlike Arabesque. Perfect bedtime sounds.\n\n"
            "🌸 Relaxing nature ambience for sleep\n"
            "🎹 Claude Debussy — Arabesque No. 1\n"
            "🌙 Wind down before bed with calming classical music\n\n"
            "Full sleep programs ▶ @ClassicalNightRelax\n\n"
            "#calmingsleep #cherryblossom #debussy #bedtimesounds #sleepambience "
            "#classicalmusic #sleepmusic #relaxingmusic #classicalnightrelax #shorts"
        ),
        "thumb_prompt": "pink cherry blossom petals falling, soft spring light, pastel dreamy, sleep ambience peaceful, no text",
        "tags": ["calming sleep", "cherry blossoms", "Debussy", "arabesque", "sleep ambience",
                 "bedtime sounds", "classical music shorts", "relaxing music",
                 "classical night relax", "spring", "shorts"],
    },
    "fireplace_cabin": {
        "title":        "🔥 Fireplace Cabin | Fauré Classical Sleep Music | Classical Night Relax #shorts",
        "desc_en":      (
            "Cosy fireplace in a winter cabin with Fauré's warm Andantino. The perfect bedtime sounds.\n\n"
            "🔥 Calming sleep ambience — crackling fireplace\n"
            "🎹 Gabriel Fauré — Fantaisie, Op. 79 (Andantino)\n"
            "❄️ Wind down on cold nights with soothing classical music\n\n"
            "Full sleep programs ▶ @ClassicalNightRelax\n\n"
            "#calmingsleep #fireplace #cozy #faure #classicalmusic #sleepambience "
            "#bedtimesounds #relaxingmusic #classicalnightrelax #shorts"
        ),
        "thumb_prompt": "cozy fireplace cabin interior, warm glowing fire, winter snow outside window, classical music ambience, cinematic, no text",
        "tags": ["calming sleep", "fireplace", "cozy cabin", "Fauré", "sleep ambience",
                 "bedtime sounds", "classical music shorts", "relaxing music", "winter",
                 "classical night relax", "shorts"],
    },
    "lavender_fields": {
        "title":        "💜 Lavender Fields | Mozart Sleep Music | Classical Night Relax #shorts",
        "desc_en":      (
            "Endless purple lavender fields swaying in a gentle breeze with Mozart's Serenade. Sleep ambience.\n\n"
            "💜 Nature sleep ambience for deep rest\n"
            "🎹 Wolfgang Amadeus Mozart — Serenade in G Major (Romance)\n"
            "🌿 Let the lavender scent carry you to sleep\n\n"
            "Full sleep programs ▶ @ClassicalNightRelax\n\n"
            "#calmingsleep #lavender #mozart #sleepambience #bedtimesounds "
            "#classicalmusic #sleepmusic #relaxingmusic #classicalnightrelax #shorts"
        ),
        "thumb_prompt": "purple lavender fields in golden sunset light, peaceful Provence France, sleep ambience, cinematic photography, no text",
        "tags": ["calming sleep", "lavender", "Mozart", "serenade", "sleep ambience",
                 "bedtime sounds", "classical music shorts", "relaxing music",
                 "classical night relax", "nature", "shorts"],
    },
    "mountain_snow": {
        "title":        "⛰️ Snowy Mountains | Moonlight Sonata | Classical Night Relax #shorts",
        "desc_en":      (
            "Moonlit snowy peaks and Beethoven's Moonlight Sonata — the ultimate calming sleep soundtrack.\n\n"
            "🌙 Calming sleep ambience under mountain moonlight\n"
            "🎹 Ludwig van Beethoven — Piano Sonata 'Moonlight' (Adagio sostenuto)\n"
            "❄️ Pure silence and classical serenity\n\n"
            "Full sleep programs ▶ @ClassicalNightRelax\n\n"
            "#calmingsleep #moonlightsonata #beethoven #sleepambience #snowy "
            "#classicalmusic #bedtimesounds #relaxingmusic #classicalnightrelax #shorts"
        ),
        "thumb_prompt": "moonlit snowy mountain peaks at night, cold blue silence, classical sleep ambience, cinematic, no text",
        "tags": ["calming sleep", "Moonlight Sonata", "Beethoven", "snowy mountain", "sleep ambience",
                 "bedtime sounds", "classical music shorts", "relaxing music",
                 "classical night relax", "winter night", "shorts"],
    },
    "autumn_forest": {
        "title":        "🍂 Autumn Forest | Beethoven Violin | Classical Night Relax #shorts",
        "desc_en":      (
            "Golden autumn leaves falling through a quiet forest with Beethoven's Violin Concerto.\n\n"
            "🍂 Autumn sleep ambience and calming classical violin\n"
            "🎻 Ludwig van Beethoven — Violin Concerto in D (Larghetto)\n"
            "🌿 Perfect for bedtime sounds and winding down\n\n"
            "Full sleep programs ▶ @ClassicalNightRelax\n\n"
            "#calmingsleep #autumnforest #beethoven #violin #sleepambience "
            "#bedtimesounds #classicalmusic #relaxingmusic #classicalnightrelax #shorts"
        ),
        "thumb_prompt": "golden autumn forest with falling leaves, warm amber light through trees, peaceful sleep ambience, cinematic, no text",
        "tags": ["calming sleep", "autumn forest", "Beethoven", "violin concerto", "sleep ambience",
                 "bedtime sounds", "classical music shorts", "relaxing music",
                 "classical night relax", "fall", "shorts"],
    },
    "zen_garden": {
        "title":        "⛩️ Zen Garden | Flute Classical Music | Classical Night Relax #shorts",
        "desc_en":      (
            "A peaceful Japanese zen garden with raked sand and Telemann's meditative flute. Sleep ambience.\n\n"
            "🍃 Zen sleep ambience for deep calm\n"
            "🎵 Georg Philipp Telemann — Fantaisie for Solo Flute\n"
            "🌸 Meditative and calming bedtime sounds\n\n"
            "Full sleep programs ▶ @ClassicalNightRelax\n\n"
            "#calmingsleep #zengarden #telemann #flute #sleepambience "
            "#bedtimesounds #classicalmusic #meditation #classicalnightrelax #shorts"
        ),
        "thumb_prompt": "serene Japanese zen garden with raked sand patterns, stone lantern, cherry tree, peaceful sleep meditation, no text",
        "tags": ["calming sleep", "zen garden", "Telemann", "flute", "sleep ambience",
                 "bedtime sounds", "classical music shorts", "meditation", "japanese",
                 "classical night relax", "shorts"],
    },
    "deep_space": {
        "title":        "🌌 Deep Space | Chopin Nocturne | Classical Night Relax #shorts",
        "desc_en":      (
            "Float through stars and nebulae with Chopin's haunting Nocturne. Calming sleep ambience.\n\n"
            "✨ Space sleep ambience for deep rest\n"
            "🎹 Frédéric Chopin — Nocturne in B flat minor, Op. 9 no. 1\n"
            "🌙 Lose yourself in the cosmos with classical bedtime sounds\n\n"
            "Full sleep programs ▶ @ClassicalNightRelax\n\n"
            "#calmingsleep #deepspace #chopin #nocturne #sleepambience "
            "#bedtimesounds #classicalmusic #stars #classicalnightrelax #shorts"
        ),
        "thumb_prompt": "deep space nebula with stars and galaxies, dark purple blue cosmic, classical sleep ambience, cinematic, no text",
        "tags": ["calming sleep", "deep space", "Chopin", "nocturne", "sleep ambience",
                 "bedtime sounds", "classical music shorts", "relaxing music", "space",
                 "classical night relax", "shorts"],
    },
    "distant_waterfall": {
        "title":        "💧 Waterfall | Bach Cello Suite | Classical Night Relax #shorts",
        "desc_en":      (
            "A distant waterfall flowing through misty forest with Bach's meditative Cello Prelude.\n\n"
            "💧 Water sleep ambience and calming classical cello\n"
            "🎻 Johann Sebastian Bach — Cello Suite No. 1, Prelude in G\n"
            "🌿 Natural bedtime sounds for deep restful sleep\n\n"
            "Full sleep programs ▶ @ClassicalNightRelax\n\n"
            "#calmingsleep #waterfall #bach #cellosuite #sleepambience "
            "#bedtimesounds #classicalmusic #nature #classicalnightrelax #shorts"
        ),
        "thumb_prompt": "misty waterfall cascading through lush green forest, peaceful nature sleep ambience, cinematic photography, no text",
        "tags": ["calming sleep", "waterfall", "Bach", "cello suite", "sleep ambience",
                 "bedtime sounds", "classical music shorts", "nature sounds", "water",
                 "classical night relax", "shorts"],
    },
    "rainforest_night": {
        "title":        "🌿 Rainforest Night | Tchaikovsky Swan Lake | Classical Night Relax #shorts",
        "desc_en":      (
            "A moonlit tropical rainforest at night with Tchaikovsky's dreamlike Swan Lake. Sleep ambience.\n\n"
            "🌿 Tropical night sleep ambience\n"
            "🎻 Pyotr Ilyich Tchaikovsky — Swan Lake, Act II\n"
            "🌙 Enchanting bedtime sounds from the jungle night\n\n"
            "Full sleep programs ▶ @ClassicalNightRelax\n\n"
            "#calmingsleep #rainforest #tchaikovsky #swanlake #sleepambience "
            "#bedtimesounds #classicalmusic #tropicalnature #classicalnightrelax #shorts"
        ),
        "thumb_prompt": "moonlit tropical rainforest at night, bioluminescent plants, misty jungle, classical sleep ambience, cinematic, no text",
        "tags": ["calming sleep", "rainforest night", "Tchaikovsky", "Swan Lake", "sleep ambience",
                 "bedtime sounds", "classical music shorts", "tropical", "nature",
                 "classical night relax", "shorts"],
    },
}


def make_vertical_short(loop_mp4: Path, start: int, out_mp4: Path,
                         music_mp3: Path | None, dry_run: bool) -> bool:
    vf = (
        f"scale=1080:-2:force_original_aspect_ratio=decrease,"
        f"pad=1080:1920:0:(oh-ih)/2:black,"
        f"fade=t=in:st=0:d={FADE_SECS},"
        f"fade=t=out:st={SHORT_DURATION - FADE_SECS}:d={FADE_SECS}"
    )
    af = (
        f"aresample=44100,aformat=channel_layouts=stereo,"
        f"afade=t=in:st=0:d={FADE_SECS},"
        f"afade=t=out:st={SHORT_DURATION - FADE_SECS}:d={FADE_SECS}"
    )

    if music_mp3 and music_mp3.exists():
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start), "-i", str(loop_mp4),
            "-ss", str(start), "-i", str(music_mp3),
            "-t", str(SHORT_DURATION),
            "-map", "0:v:0", "-map", "1:a:0",
            "-vf", vf, "-af", af,
            "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            str(out_mp4),
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start), "-i", str(loop_mp4),
            "-t", str(SHORT_DURATION),
            "-vf", vf,
            "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-an",
            "-movflags", "+faststart",
            str(out_mp4),
        ]

    print(f"  FFmpeg → {out_mp4.name}")
    if dry_run:
        print(f"  [DRY RUN] {' '.join(cmd[:6])} ...")
        return True

    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if r.returncode != 0 or not out_mp4.exists():
        print(f"  ✗ FFmpeg failed:\n{r.stderr[-400:]}")
        return False
    sz = out_mp4.stat().st_size // 1024 // 1024
    print(f"  ✓ {sz} MB")
    return True


def write_meta(theme: str, out_mp4: Path, dry_run: bool):
    m = THEME_META[theme]
    composer = THEME_COMPOSER.get(theme, "")
    music_track = THEME_MUSIC.get(theme, "")
    meta = {
        "title":         m["title"],
        "description":   m["desc_en"],
        "video_type":    "sleep_short",
        "theme":         theme,
        "language":      "en",
        "is_short":      True,
        "status":        "public",
        "made_for_kids": False,
        "tags":          m["tags"],
        "composer":      composer,
        "music_track":   music_track,
        "ai_generated":  False,
    }
    meta_path = out_mp4.parent / f"meta_{out_mp4.stem}.yaml"
    if dry_run:
        print(f"  [DRY RUN] meta → {meta_path.name}")
        return
    meta_path.write_text(yaml.dump(meta, allow_unicode=True, sort_keys=False))
    print(f"  ✓ meta → {meta_path.name}")


def generate_thumbnail(theme: str, out_mp4: Path, dry_run: bool) -> bool:
    thumb_path = out_mp4.parent / f"thumb_{out_mp4.stem}.png"
    if thumb_path.exists():
        return True
    if dry_run:
        print(f"  [DRY RUN] thumb → {thumb_path.name}")
        return True
    if not TOGETHER_KEY_FILE.exists():
        print("  ✗ Together API key missing")
        return False

    m = THEME_META[theme]
    prompt = m["thumb_prompt"] + ", vertical portrait 9:16 format"
    try:
        api_key = TOGETHER_KEY_FILE.read_text().strip()
        resp = requests.post(
            TOGETHER_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "python-requests/2.31.0",
            },
            json={
                "model":           TOGETHER_MODEL,
                "prompt":          prompt,
                "width":           720,
                "height":          1280,
                "steps":           4,
                "n":               1,
                "response_format": "b64_json",
            },
            timeout=90,
        )
        resp.raise_for_status()
        from PIL import Image
        img_bytes = base64.b64decode(resp.json()["data"][0]["b64_json"])
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        img = img.resize((720, 1280), Image.LANCZOS)
        thumb_path.write_bytes(img_bytes)
        print(f"  ✓ thumb → {thumb_path.name}")
        return True
    except Exception as e:
        print(f"  ✗ thumb failed: {e}")
        return False


# ── Keyword-targeted themes ───────────────────────────────────────────────────
# Each entry can override loop_dir and music_dir for non-standard sources.
KEYWORD_THEMES: dict[str, dict] = {
    # "night rain sounds for sleeping"
    "rain_night": {
        "loop_dir":   NATURE_LOOPS_DIR,
        "loop_file":  "nature_loop_rain_en_30.mp4",
        "music_dir":  SUNO_DIR,
        "music":      "Rain Etude in C Minor v2.mp3",
        "title":      "🌧️ Night Rain Sounds for Sleeping | Soft Piano Music | Classical Night Relax #shorts",
        "desc_en": (
            "Rain gently falls outside while soft piano carries you into deep sleep.\n\n"
            "🌧️ Night rain sounds for sleeping — pure relaxation\n"
            "🎹 Soft piano music for relaxation (original AI composition)\n"
            "🌙 Let the rain wash away the day's stress\n\n"
            "Full sleep programs ▶ @ClassicalNightRelax\n\n"
            "#nightrainsoundsforsleping #rainsoundssleep #softpianomusic "
            "#softpianoforrelaxation #sleepmusic #rainandpiano #calmingsleep "
            "#bedtimesounds #classicalnightrelax #shorts"
        ),
        "thumb_prompt": "rainy night window with soft candlelight inside, piano keys reflection in glass, cozy bedroom sleep ambience, cinematic, no text",
        "tags": ["night rain sounds for sleeping", "rain sounds for sleep", "soft piano music for relaxation",
                 "rain and piano", "calming sleep", "bedtime sounds", "sleep music",
                 "soft music for relaxation", "classical night relax", "shorts"],
        "composer": "",
        "ai_generated": True,
    },
    # "soft piano music for relaxation" / "soft music for relaxation"
    "piano_zen": {
        "loop_dir":  VISUAL_LOOPS_DIR,
        "loop_file": "visual_zen_garden_loop.mp4",
        "music_dir": SUNO_DIR,
        "music":     "Moonlight on the Piano v2.mp3",
        "title":     "⛩️ Soft Piano Music for Relaxation | Zen Garden | Classical Night Relax #shorts",
        "desc_en": (
            "Gentle piano drifts over a serene zen garden. Pure soft music for relaxation.\n\n"
            "🎹 Soft piano music for relaxation and inner calm\n"
            "⛩️ Zen garden meditation ambience\n"
            "🌸 Let the music melt away stress and tension\n\n"
            "Full sleep programs ▶ @ClassicalNightRelax\n\n"
            "#softpianoforrelaxation #softmusicforrelaxation #zengarden "
            "#pianorelaxation #calmingsleep #sleepmeditationmusic "
            "#relaxingmusicforstressrelief #classicalnightrelax #shorts"
        ),
        "thumb_prompt": "serene zen garden with soft moonlight, piano keys floating in mist, peaceful meditation, vertical, no text",
        "tags": ["soft piano music for relaxation", "soft music for relaxation", "zen garden",
                 "piano relaxation", "sleep meditation music", "relaxing music for stress relief",
                 "calming music", "classical night relax", "shorts"],
        "composer": "",
        "ai_generated": True,
    },
    # "soft music for relaxation"
    "piano_lavender": {
        "loop_dir":  VISUAL_LOOPS_DIR,
        "loop_file": "visual_lavender_fields_loop.mp4",
        "music_dir": SUNO_DIR,
        "music":     "Tide and Piano v2.mp3",
        "title":     "💜 Soft Music for Relaxation | Lavender Fields Piano | Classical Night Relax #shorts",
        "desc_en": (
            "Drift through purple lavender fields with the gentlest soft piano music for relaxation.\n\n"
            "💜 Soft music for relaxation — zero stress\n"
            "🎹 Piano and tide sounds, perfectly balanced\n"
            "🌿 Wind down, breathe deeply, let go\n\n"
            "Full sleep programs ▶ @ClassicalNightRelax\n\n"
            "#softmusicforrelaxation #softpianomusic #lavender "
            "#relaxingmusicforstressrelief #calmingsleep #pianosleep "
            "#classicalnightrelax #shorts"
        ),
        "thumb_prompt": "purple lavender fields in soft evening light, gentle piano keyboard in foreground, relaxation music, vertical cinematic, no text",
        "tags": ["soft music for relaxation", "soft piano music for relaxation", "lavender",
                 "relaxing music for stress relief", "calming sleep", "piano sleep",
                 "bedtime sounds", "classical night relax", "shorts"],
        "composer": "",
        "ai_generated": True,
    },
    # "sleep meditation music"
    "meditation_space": {
        "loop_dir":  VISUAL_LOOPS_DIR,
        "loop_file": "visual_deep_space_loop.mp4",
        "music_dir": SUNO_DIR,
        "music":     "The Glass Forest v2.mp3",
        "title":     "🌌 Sleep Meditation Music | Deep Space Journey | Classical Night Relax #shorts",
        "desc_en": (
            "Float through infinite space with this sleep meditation music. Breathe in, breathe out.\n\n"
            "🌌 Sleep meditation music for deep rest\n"
            "✨ Ambient soundscape for mindful relaxation\n"
            "🧘 Let the cosmos hold you as you drift to sleep\n\n"
            "Full sleep programs ▶ @ClassicalNightRelax\n\n"
            "#sleepmeditationmusic #deepspace #meditationmusic "
            "#calmingsleep #ambientmusic #relaxingmusicforstressrelief "
            "#mindfulrelaxation #classicalnightrelax #shorts"
        ),
        "thumb_prompt": "astronaut floating in colorful nebula, meditative peaceful deep space, sleep meditation, vertical cinematic, no text",
        "tags": ["sleep meditation music", "deep space", "meditation music", "calming sleep",
                 "ambient music", "relaxing music for stress relief", "mindful relaxation",
                 "classical night relax", "shorts"],
        "composer": "",
        "ai_generated": True,
    },
    # "relaxing music for stress relief"
    "stress_relief_forest": {
        "loop_dir":  VISUAL_LOOPS_DIR,
        "loop_file": "visual_autumn_forest_loop.mp4",
        "music_dir": SUNO_DIR,
        "music":     "Dreamy Arpeggios v2.mp3",
        "title":     "🍂 Relaxing Music for Stress Relief | Autumn Forest | Classical Night Relax #shorts",
        "desc_en": (
            "Autumn leaves fall gently to dreamy arpeggios — the perfect relaxing music for stress relief.\n\n"
            "🍂 Relaxing music for stress relief — instant calm\n"
            "🎵 Dreamy soft arpeggios for tension release\n"
            "🌿 Nature therapy in 50 seconds\n\n"
            "Full sleep programs ▶ @ClassicalNightRelax\n\n"
            "#relaxingmusicforstressrelief #stressrelief #autumnforest "
            "#softmusicforrelaxation #calmingsleep #sleepmeditationmusic "
            "#anxietyrelief #classicalnightrelax #shorts"
        ),
        "thumb_prompt": "golden autumn forest path, leaves floating down, dreamy soft light, stress relief nature scene, vertical, no text",
        "tags": ["relaxing music for stress relief", "stress relief", "autumn forest",
                 "soft music for relaxation", "calming sleep", "anxiety relief",
                 "nature therapy", "classical night relax", "shorts"],
        "composer": "",
        "ai_generated": True,
    },
    # "relaxing music for studying"
    "study_goldberg": {
        "loop_dir":   VISUAL_LOOPS_DIR,
        "loop_file":  "visual_deep_space_loop.mp4",
        "music_dir":  MUSIC_DIR,
        "music":      "Goldberg Variations, BWV 988 - 01 - Aria.mp3",
        "title":      "📚 Relaxing Music for Studying | Bach Goldberg Aria | Classical Night Relax #shorts",
        "desc_en": (
            "Bach's timeless Goldberg Aria over a deep space visual — relaxing music for studying.\n\n"
            "📚 Relaxing music for studying and deep focus\n"
            "🎹 J.S. Bach — Goldberg Variations, Aria (BWV 988)\n"
            "✨ Classical music proven to enhance concentration\n\n"
            "Full focus programs ▶ @ClassicalNightRelax\n\n"
            "#relaxingmusicforstudying #studymusic #bachgoldberg "
            "#classicalfocusmusic #deepfocus #concentrationmusic "
            "#classicalnightrelax #shorts"
        ),
        "thumb_prompt": "student study desk with open books, soft lamp light, deep space galaxy window behind, focus music ambience, vertical, no text",
        "tags": ["relaxing music for studying", "study music", "Bach Goldberg", "focus music",
                 "deep focus", "concentration music", "classical music for studying",
                 "classical night relax", "shorts"],
        "composer": "Bach",
        "ai_generated": False,
    },
    # "relaxing music for studying" variant
    "study_bach_snow": {
        "loop_dir":  VISUAL_LOOPS_DIR,
        "loop_file": "visual_mountain_snow_loop.mp4",
        "music_dir": MUSIC_DIR,
        "music":     "Cello Suite no. 1 - Prelude in G, BWV 1007.mp3",
        "title":     "❄️ Bach for Deep Focus | Relaxing Study Music | Classical Night Relax #shorts",
        "desc_en": (
            "Snowy mountain silence and Bach's Cello Suite Prelude — ideal relaxing music for studying.\n\n"
            "❄️ Relaxing music for studying — pure concentration\n"
            "🎻 J.S. Bach — Cello Suite No. 1, Prelude in G (BWV 1007)\n"
            "🏔️ Mountain silence + classical music = perfect focus\n\n"
            "Full focus programs ▶ @ClassicalNightRelax\n\n"
            "#relaxingmusicforstudying #bachcellosuite #studymusic "
            "#classicalfocusmusic #deepfocus #snowymountain "
            "#classicalnightrelax #shorts"
        ),
        "thumb_prompt": "snowy mountain peak at sunrise, soft warm light, classical music study ambience, vertical cinematic, no text",
        "tags": ["relaxing music for studying", "Bach cello suite", "study music", "deep focus",
                 "classical focus music", "snowy mountain", "concentration music",
                 "classical night relax", "shorts"],
        "composer": "Bach",
        "ai_generated": False,
    },
    # "the best of chopin nocturnes"
    "chopin_nocturne_aurora": {
        "loop_dir":  VISUAL_LOOPS_DIR,
        "loop_file": "visual_aurora_borealis_loop.mp4",
        "music_dir": MUSIC_DIR,
        "music":     "Nocturne in E flat major, Op. 9 no. 2.mp3",
        "title":     "🎹 Best of Chopin Nocturnes | Op. 9 No. 2 | Classical Night Relax #shorts",
        "desc_en": (
            "The most beloved Chopin nocturne over a shimmering Aurora Borealis. Pure piano magic.\n\n"
            "🎹 Best of Chopin Nocturnes — Op. 9 No. 2 in E♭ major\n"
            "🌌 Aurora Borealis — Northern Lights ambience\n"
            "🌙 Soft piano music for relaxation and sleep\n\n"
            "Full Chopin sleep programs ▶ @ClassicalNightRelax\n\n"
            "#bestofchopinnocturnes #chopinnocturne #nocturneop9 "
            "#softpianoforrelaxation #classicalpiano #calmingsleep "
            "#chopinpiano #classicalnightrelax #shorts"
        ),
        "thumb_prompt": "Chopin piano at night with aurora borealis sky, grand piano silhouette, best of chopin nocturnes, vertical cinematic, no text",
        "tags": ["best of chopin nocturnes", "Chopin nocturne", "Op. 9 No. 2", "soft piano music for relaxation",
                 "classical piano", "calming sleep", "Chopin piano", "sleep music",
                 "classical night relax", "shorts"],
        "composer": "Chopin",
        "ai_generated": False,
    },
    # "the best of chopin nocturnes" variant 2
    "chopin_nocturne_blossoms": {
        "loop_dir":  VISUAL_LOOPS_DIR,
        "loop_file": "visual_cherry_blossoms_loop.mp4",
        "music_dir": MUSIC_DIR,
        "music":     "Nocturne in B flat minor, Op. 9 no. 1.mp3",
        "title":     "🌸 Best of Chopin Nocturnes | Op. 9 No. 1 | Classical Night Relax #shorts",
        "desc_en": (
            "Chopin's hauntingly beautiful Nocturne Op. 9 No. 1 over falling cherry blossoms.\n\n"
            "🌸 Best of Chopin Nocturnes — Op. 9 No. 1 in B♭ minor\n"
            "🎹 Soft piano music for relaxation and deep sleep\n"
            "💮 Cherry blossom sleep ambience\n\n"
            "Full Chopin sleep programs ▶ @ClassicalNightRelax\n\n"
            "#bestofchopinnocturnes #chopinnocturne #nocturneop9 "
            "#softpianoforrelaxation #cherryblossom #calmingsleep "
            "#chopinpiano #classicalnightrelax #shorts"
        ),
        "thumb_prompt": "cherry blossom petals falling over a grand piano, Chopin nocturne night scene, soft classical music, vertical cinematic, no text",
        "tags": ["best of chopin nocturnes", "Chopin nocturne", "Op. 9 No. 1", "soft piano music for relaxation",
                 "cherry blossoms", "calming sleep", "Chopin piano", "sleep meditation music",
                 "classical night relax", "shorts"],
        "composer": "Chopin",
        "ai_generated": False,
    },
}

KW_BATCH_OFFSETS = [0, 60]   # 9 themes × 2 offsets = 18 Shorts


def process(theme: str, offset: int, dry_run: bool, force: bool) -> bool:
    """Process one visual_loops theme (original batch)."""
    loop_path = VISUAL_LOOPS_DIR / f"visual_{theme}_loop.mp4"
    if not loop_path.exists():
        print(f"  ✗ Loop not found: {loop_path.name}")
        return False

    slug     = f"visual_short_{theme}_t{offset}s_{DATE_STR}"
    out_mp4  = QUEUE_CC / f"{slug}.mp4"

    if out_mp4.exists() and not force:
        print(f"  EXISTS: {out_mp4.name} — skip (--force to redo)")
        return True

    music_file = THEME_MUSIC.get(theme)
    music_mp3  = (MUSIC_DIR / music_file) if music_file else None
    if music_mp3 and not music_mp3.exists():
        print(f"  ✗ Music not found: {music_mp3.name}")
        music_mp3 = None
    elif music_mp3:
        print(f"  Music: {music_mp3.name}")

    ok = make_vertical_short(loop_path, offset, out_mp4, music_mp3, dry_run)
    if not ok:
        return False

    write_meta(theme, out_mp4, dry_run)
    generate_thumbnail(theme, out_mp4, dry_run)
    return True


def process_kw(kw_key: str, offset: int, dry_run: bool, force: bool) -> bool:
    """Process one keyword-targeted theme."""
    kw = KEYWORD_THEMES[kw_key]
    loop_dir  = kw.get("loop_dir", VISUAL_LOOPS_DIR)
    loop_path = loop_dir / kw["loop_file"]
    if not loop_path.exists():
        print(f"  ✗ Loop not found: {loop_path}")
        return False

    slug    = f"kw_short_{kw_key}_t{offset}s_{DATE_STR}"
    out_mp4 = QUEUE_CC / f"{slug}.mp4"

    if out_mp4.exists() and not force:
        print(f"  EXISTS: {out_mp4.name} — skip")
        return True

    music_dir  = kw.get("music_dir", MUSIC_DIR)
    music_file = kw.get("music", "")
    music_mp3  = (music_dir / music_file) if music_file else None
    if music_mp3 and not music_mp3.exists():
        print(f"  ✗ Music not found: {music_mp3.name}")
        music_mp3 = None
    elif music_mp3:
        print(f"  Music: {music_mp3.name}")

    ok = make_vertical_short(loop_path, offset, out_mp4, music_mp3, dry_run)
    if not ok:
        return False

    # Write meta directly from kw dict
    meta = {
        "title":         kw["title"],
        "description":   kw["desc_en"],
        "video_type":    "sleep_short",
        "theme":         kw_key,
        "language":      "en",
        "is_short":      True,
        "status":        "public",
        "made_for_kids": False,
        "tags":          kw["tags"],
        "composer":      kw.get("composer", ""),
        "music_track":   music_file,
        "ai_generated":  kw.get("ai_generated", False),
    }
    meta_path = QUEUE_CC / f"meta_{slug}.yaml"
    if dry_run:
        print(f"  [DRY RUN] meta → {meta_path.name}")
    else:
        meta_path.write_text(yaml.dump(meta, allow_unicode=True, sort_keys=False))
        print(f"  ✓ meta → {meta_path.name}")

    # Thumbnail
    thumb_path = QUEUE_CC / f"thumb_{slug}.png"
    if not thumb_path.exists() and not dry_run and TOGETHER_KEY_FILE.exists():
        prompt = kw["thumb_prompt"]
        try:
            api_key = TOGETHER_KEY_FILE.read_text().strip()
            resp = requests.post(
                TOGETHER_URL,
                headers={"Authorization": f"Bearer {api_key}",
                         "Content-Type": "application/json",
                         "User-Agent": "python-requests/2.31.0"},
                json={"model": TOGETHER_MODEL, "prompt": prompt,
                      "width": 720, "height": 1280, "steps": 4, "n": 1,
                      "response_format": "b64_json"},
                timeout=90,
            )
            resp.raise_for_status()
            img_bytes = base64.b64decode(resp.json()["data"][0]["b64_json"])
            thumb_path.write_bytes(img_bytes)
            print(f"  ✓ thumb → {thumb_path.name}")
        except Exception as e:
            print(f"  ✗ thumb failed: {e}")
    elif dry_run:
        print(f"  [DRY RUN] thumb → {thumb_path.name}")

    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch",          action="store_true",
                        help="All 10 visual themes × 3 offsets = 30 Shorts")
    parser.add_argument("--keywords-batch", action="store_true",
                        help="9 keyword themes × 2 offsets = 18 Shorts (popular search queries)")
    parser.add_argument("--theme",          choices=list(THEME_META.keys()),
                        help="Single visual theme")
    parser.add_argument("--kw-theme",       choices=list(KEYWORD_THEMES.keys()),
                        help="Single keyword theme")
    parser.add_argument("--offset",         type=int, default=0,
                        help="Start offset in seconds (default 0)")
    parser.add_argument("--dry-run",        action="store_true")
    parser.add_argument("--force",          action="store_true")
    args = parser.parse_args()

    if not any([args.batch, getattr(args, "keywords_batch", False),
                args.theme, args.kw_theme]):
        parser.print_help()
        return

    QUEUE_CC.mkdir(parents=True, exist_ok=True)
    done = 0

    # ── Original visual batch ──
    if args.batch or args.theme:
        themes  = list(THEME_META.keys()) if args.batch else [args.theme]
        offsets = BATCH_OFFSETS if args.batch else [args.offset]
        total   = len(themes) * len(offsets)
        print(f"\n=== Visual CNR Shorts ({total} planned) ===\n")
        for theme in themes:
            for offset in offsets:
                print(f"\n── {theme}  offset={offset}s ──")
                if process(theme, offset, args.dry_run, args.force):
                    done += 1
        print(f"\n=== Done: {done}/{total} ===")

    # ── Keyword batch ──
    kw_batch = getattr(args, "keywords_batch", False)
    if kw_batch or args.kw_theme:
        kw_keys = list(KEYWORD_THEMES.keys()) if kw_batch else [args.kw_theme]
        offsets = KW_BATCH_OFFSETS if kw_batch else [args.offset]
        total   = len(kw_keys) * len(offsets)
        print(f"\n=== Keyword CNR Shorts ({total} planned) ===\n")
        for kw_key in kw_keys:
            for offset in offsets:
                print(f"\n── {kw_key}  offset={offset}s ──")
                if process_kw(kw_key, offset, args.dry_run, args.force):
                    done += 1
        print(f"\n=== Done: {done}/{total} ===")


if __name__ == "__main__":
    main()
