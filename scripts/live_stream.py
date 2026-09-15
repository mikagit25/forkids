#!/usr/bin/env python3
"""
Live stream manager for Calm Classics (Classical Night Relax) YouTube channel.

Supports two daily stream slots — each slot has its own state, history, and playlist:
  eu  (default) — 20:00–06:00 UTC  → Europe prime time, saved as VOD
  us             — 07:00–14:00 UTC  → US night (00:00 EST / 21:00 PST), NOT saved

Content rotates independently per slot so each region gets fresh variety.

Commands:
  start        — pick content, create broadcast, start ffmpeg (idempotent)
  stop         — end broadcast, kill ffmpeg
  status       — show current state for a slot (or both)
  install-cron — add all 4 cron jobs (EU start/stop + US start/stop)

Usage:
  python3 scripts/live_stream.py start [--channel id] [--slot eu|us] [--mood any|sleep|focus|ambient]
  python3 scripts/live_stream.py stop  [--channel id] [--slot eu|us]
  python3 scripts/live_stream.py status [--channel id] [--slot eu|us|all]
  python3 scripts/live_stream.py install-cron [--channel id]
"""

import argparse
import json
import logging
import os
import signal
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT     = Path(__file__).resolve().parent.parent
LOGS_DIR = ROOT / "logs"

CHANNEL_TOKENS = {
    "id": ROOT / "credentials" / "youtube_token_id.json",
    "en": ROOT / "credentials" / "youtube_token.json",
    "ar": ROOT / "credentials" / "youtube_token_ar.json",
    "sd": ROOT / "credentials" / "youtube_token_ar.json",
}
CHANNEL_QUEUE = {
    "id": ROOT / "output" / "queue_id",
    "en": ROOT / "output" / "queue",
    "ar": ROOT / "output" / "queue_ar",
    "sd": ROOT / "sacred_drift" / "output" / "queue",
}

def _state_file(ch, slot):       return LOGS_DIR / f"live_state_{ch}_{slot}.json"
def _history_file(ch, slot):     return LOGS_DIR / f"live_history_{ch}_{slot}.json"
def _rtmp_file(ch):              return LOGS_DIR / f"live_rtmp_{ch}.json"      # shared RTMP key
def _playlist_file(ch, slot):    return LOGS_DIR / f"live_playlist_{ch}_{slot}.txt"
def _now_playing_file(ch, slot): return LOGS_DIR / f"live_now_playing_{ch}_{slot}.txt"
def _ffmpeg_log(ch, slot):       return LOGS_DIR / f"live_ffmpeg_{ch}_{slot}.log"
def _cron_log(ch):               return LOGS_DIR / f"live_cron_{ch}.log"

# Slot configuration: (cron_start, cron_stop, save_vod, default_mood)
SLOT_CONFIG = {
    "eu": {"start_cron": "0 20 * * *", "stop_cron": "0 6  * * *", "save_vod": True, "mood": "any"},
    "us": {"start_cron": "0 7  * * *", "stop_cron": "0 14 * * *", "save_vod": True, "mood": "any"},
}

# ── Content classification ─────────────────────────────────────────────────────

# Filename patterns that identify short-form content (excluded from streams)
SHORT_PATTERNS = ("_short_", "kw_short", "visual_short", "_t0s_", "_t60s_", "_t120s_")

# Minimum video duration to include in a stream playlist (seconds)
MIN_DURATION_SEC = 600  # 10 minutes

# Target stream length (the cron stop kills ffmpeg at the end)
STREAM_TARGET_HOURS = 10

# Max contribution from a single video in one playlist pass (avoid 16h video monopolising)
MAX_SINGLE_CONTRIBUTION_HOURS = 5

# ── Sacred Drift: 7-day themed stream rotation ────────────────────────────────
# Each day has a primary theme → different mix of content categories
SD_DAILY_THEMES = {
    0: "classical",   # Monday    — Classical Night
    1: "healing",     # Tuesday   — Deep Healing Journey
    2: "nature",      # Wednesday — Nature & Earth Sounds
    3: "focus",       # Thursday  — Focus & Study Session
    4: "sacred",      # Friday    — Sacred Sound Healing
    5: "jazz",        # Saturday  — Jazz & Soul Evening
    6: "cosmic",      # Sunday    — Cosmic Space Meditation
}

SD_THEME_DISPLAY = {
    "classical": ("Classical Night 🎻",                 "sleep"),
    "healing":   ("Deep Healing Journey ✨",             "healing"),
    "nature":    ("Nature & Earth Sounds 🌿",            "nature"),
    "focus":     ("Focus & Study Session 🎵",            "healing"),
    "sacred":    ("Sacred Sound Healing 🔔",             "healing"),
    "jazz":      ("Jazz & Soul Evening 🎷",              "sleep"),
    "cosmic":    ("Cosmic Space Meditation 🌌",          "healing"),
}

# Category detection keywords (checked against lowercase filename)
SD_CAT_KEYWORDS: dict[str, list[str]] = {
    "classical":  ["classical_sleep", "classical_focus"],
    "hz_freq":    ["111hz", "174hz", "285hz", "396hz", "432hz", "528hz",
                   "40hz", "741hz", "963hz", "binaural", "solfeggio",
                   "delta_wave", "theta_wave", "alpha_wave", "healing_meditation"],
    "chakra":     ["chakra", "crown_chakra", "heart_chakra", "root_chakra",
                   "sacral_chakra", "solar_plexus", "third_eye", "seven_centers",
                   "full_chakra", "complete_chakra"],
    "reiki":      ["reiki", "healing_reiki", "healing_energy", "healing_hum",
                   "healing_tone", "gong_bath", "sound_healing"],
    "tibetan":    ["tibetan", "crystal_bowl", "singing_bowl", "temple_bells",
                   "sound_bath"],
    "mantra":     ["mantra", "zen_mantra", "buddha", "om_", "sacred_sounds",
                   "chant", "zazen", "metta", "gratitude"],
    "cosmic":     ["cosmic", "space_medit", "full_moon", "moon_tide",
                   "crown_of_light", "starlit", "963hz"],
    "nature":     ["waterfall", "bamboo", "forest", "rain", "ocean",
                   "desert", "mountain", "morning_yoga", "birdsong",
                   "glacier", "ice_cave", "distant_waterfall", "bamboo_forest",
                   "desert_night", "block_"],
    "sleep":      ["deep_sleep", "baby_lullaby", "drone", "ambient_piano",
                   "amber_fireplace", "fireplace", "winter_fireplace",
                   "attic_window", "airy_cloud", "moon_tide", "velvet"],
    "comp":       ["comp_"],
    "jazz":       ["jazz", "lounge", "sunday_soul", "evening_sax",
                   "whiskey", "city_lights", "harbor_lights", "blue_hour",
                   "autumn_lounge", "velvet_waltz", "velvet_evening",
                   "velvet_nightfall", "velvet_bass"],
}

# Per-theme category weights: higher = more of this category in the stream
# Primary (1.0) fills ~40-50% of stream, secondary (0.5) ~25%, filler (0.2) ~15%
SD_THEME_WEIGHTS: dict[str, dict[str, float]] = {
    "classical": {"classical": 1.0, "sleep": 0.4, "comp": 0.3, "nature": 0.1},
    "healing":   {"hz_freq": 1.0, "chakra": 0.8, "reiki": 0.6,
                  "tibetan": 0.5, "mantra": 0.4, "comp": 0.3},
    "nature":    {"nature": 1.0, "sleep": 0.3, "comp": 0.2},
    "focus":     {"classical": 0.9, "hz_freq": 0.6, "comp": 0.4,
                  "chakra": 0.3, "sleep": 0.2},
    "sacred":    {"tibetan": 1.0, "mantra": 0.9, "reiki": 0.7,
                  "chakra": 0.6, "hz_freq": 0.4, "comp": 0.3},
    "jazz":      {"jazz": 1.0, "sleep": 0.5, "comp": 0.3, "nature": 0.2},
    "cosmic":    {"cosmic": 1.0, "chakra": 0.6, "hz_freq": 0.5,
                  "tibetan": 0.4, "comp": 0.3, "sleep": 0.2},
}

# Per-series max hours per stream (prevents glacier×48 monopolising the entire night)
# Series = base name with trailing _\d+ stripped
SD_SERIES_MAX_HOURS: dict[str, float] = {
    "glacier":   2.0,   # sound_design_glacier_ice_cave series
    "waterfall": 1.5,   # distant_waterfall series
    "bamboo":    1.5,   # bamboo_forest_wind series
    "desert":    1.5,   # desert_night_wind series
    "comp_":     1.0,   # each compilation is ~1h, use at most 1 per base
    "cosmic_drone": 1.5,
    "crown_chakra_963hz": 1.5,
}
# Default: meditation categories can repeat up to 3h (audio loop is intentional)
SD_DEFAULT_SERIES_MAX_HOURS = 3.0
SD_UNIQUE_SERIES_MAX_HOURS  = 99.0  # classical programs: no cap (each is unique)

# (keyword_in_filename, display_title, mood)  — first match wins
TITLE_MAP = [
    # Sleep — composer name first so viewers immediately know what they're hearing
    ("sleep_chopin",              "Chopin — Classical Music for Sleep",              "sleep"),
    ("sleep_baroque_romantics",   "Baroque & Romantic Classical Music for Sleep",    "sleep"),
    ("sleep_beethoven_complete",  "Beethoven — Classical Music for Sleep",           "sleep"),
    ("sleep_beethoven_symphony9", "Beethoven Symphony No. 9 — Classical Sleep Music","sleep"),
    ("sleep_beethoven",           "Beethoven — Classical Music for Sleep",           "sleep"),
    ("sleep_schubert_piano",      "Schubert Piano — Classical Music for Sleep",      "sleep"),
    ("sleep_schubert_chamber",    "Schubert Chamber — Classical Music for Sleep",    "sleep"),
    ("sleep_schubert_impromptus", "Schubert Impromptus — Classical Music for Sleep", "sleep"),
    ("sleep_schubert",            "Schubert — Classical Music for Sleep",            "sleep"),
    ("sleep_romantic_orchestral", "Romantic Orchestral — Classical Music for Sleep", "sleep"),
    ("sleep_complete_romantic",   "Complete Romantic — Classical Music for Sleep",   "sleep"),
    ("sleep_debussy",             "Debussy — Classical Music for Sleep",             "sleep"),
    ("sleep_grand_orchestral",    "Grand Orchestral — Classical Music for Sleep",    "sleep"),
    ("sleep_grand_night",         "Grand Night Classics — Classical Music for Sleep","sleep"),
    ("sleep_grand",               "Grand Classics — Classical Music for Sleep",      "sleep"),
    ("sleep_moonlight",           "Moonlight Classics — Classical Music for Sleep",  "sleep"),
    ("sleep_swan_lake",           "Tchaikovsky Swan Lake — Classical Music for Sleep","sleep"),
    ("sleep_flute",               "Flute Classics — Classical Music for Sleep",      "sleep"),
    ("sleep_lullaby",             "Classical Lullabies — Sleep Music",               "sleep"),
    # Focus — composer name + clear purpose
    ("focus_bach_goldberg_complete", "Bach Goldberg Variations — Classical Focus Music",   "focus"),
    ("focus_bach_goldberg",       "Bach Goldberg Variations — Classical Study Music",      "focus"),
    ("focus_bach_violin_partita", "Bach Violin Partita — Classical Focus Music",           "focus"),
    ("focus_bach",                "Bach — Classical Music for Focus & Study",              "focus"),
    ("focus_beethoven_concertos", "Beethoven Piano Concertos — Classical Focus Music",     "focus"),
    ("focus_beethoven_eroica",    "Beethoven Eroica — Classical Music for Focus",          "focus"),
    ("focus_beethoven_cello",     "Beethoven Cello Sonatas — Classical Focus Music",       "focus"),
    ("focus_beethoven_violin",    "Beethoven Violin Sonatas — Classical Focus Music",      "focus"),
    ("focus_beethoven_kreutzer",  "Beethoven Kreutzer Sonata — Classical Focus Music",     "focus"),
    ("focus_beethoven",           "Beethoven — Classical Music for Focus & Study",         "focus"),
    ("focus_franck_violin",       "Franck Violin Sonata — Classical Focus Music",          "focus"),
    ("focus_wagner_complete",     "Wagner Complete Works — Classical Music for Focus",     "focus"),
    ("focus_wagner_tannhaeuser",  "Wagner Tannhäuser — Classical Music for Focus",         "focus"),
    ("focus_wagner",              "Wagner — Classical Music for Focus & Study",            "focus"),
    ("focus_mozart",              "Mozart — Classical Music for Focus & Study",            "focus"),
    ("focus_baroque_chamber",     "Baroque Chamber — Classical Music for Study",           "focus"),
    ("focus_drama",               "Dramatic Classics — Classical Music for Focus",         "focus"),
    ("focus_classical",           "Classical Masterpieces — Music for Focus & Study",      "focus"),
    # Ambient visual themes — keep nature reference + classical music keyword
    ("visual_theme_autumn_forest",     "Autumn Forest — Ambient Classical Music",          "ambient"),
    ("visual_theme_cherry_blossoms",   "Cherry Blossoms — Ambient Classical Music",        "ambient"),
    ("visual_theme_aurora_borealis",   "Aurora Borealis — Ambient Classical Music",        "ambient"),
    ("visual_theme_deep_space",        "Deep Space — Ambient Classical Music",             "ambient"),
    ("visual_theme_distant_waterfall", "Waterfall — Relaxing Classical Music",             "ambient"),
    ("visual_theme_fireplace_cabin",   "Fireplace & Cabin — Cozy Classical Music",         "ambient"),
    ("visual_theme_lavender_fields",   "Lavender Fields — Relaxing Classical Music",       "ambient"),
    ("visual_theme_rainforest_night",  "Rainforest Night — Ambient Classical Music",       "ambient"),
    ("visual_theme_mountain_snow",     "Mountain Snow — Winter Classical Music",           "ambient"),
    ("visual_theme_evening_piano",     "Evening Piano — Classical Night Music",            "ambient"),
    ("visual_theme",                   "Ambient Classical Music for Relaxation",           "ambient"),
]

MOOD_EMOJI = {"sleep": "🌙", "focus": "🎵", "ambient": "🌿"}
LIVE_PREFIX  = "🔴 LIVE: "
CHAN_SUFFIX   = " | Classical Night Relax"

# Composer keywords extracted from program filename → display name
COMPOSER_DISPLAY = {
    "chopin":     "Frédéric Chopin",
    "bach":       "Johann Sebastian Bach",
    "beethoven":  "Ludwig van Beethoven",
    "schubert":   "Franz Schubert",
    "brahms":     "Johannes Brahms",
    "debussy":    "Claude Debussy",
    "mozart":     "Wolfgang Amadeus Mozart",
    "wagner":     "Richard Wagner",
    "tchaikovsky":"Pyotr Tchaikovsky",
    "vivaldi":    "Antonio Vivaldi",
    "handel":     "George Frideric Handel",
    "liszt":      "Franz Liszt",
    "franck":     "César Franck",
    "ravel":      "Maurice Ravel",
    "satie":      "Erik Satie",
    "haydn":      "Joseph Haydn",
    "mendelssohn":"Felix Mendelssohn",
    "romantic":   "Romantic Composers",
    "baroque":    "Baroque Masters",
}

HASHTAGS = {
    "sleep": ("#ClassicalMusicForSleep #SleepMusic #ClassicalNightRelax #RelaxingClassical"
              " #PianoSleep #ClassicalMusic #SleepAid #NocturneForSleep #ClassicalLive"
              " #DeepSleep #Chopin #Bach #Beethoven #Schubert #ClassicalPiano"),
    "focus": ("#ClassicalMusicForStudy #FocusMusic #ClassicalNightRelax #StudyMusic"
              " #ClassicalLive #ConcentrationMusic #ClassicalMusic #BachForStudy"
              " #ProductivityMusic #BeethovenForStudy #StudyWithMe #ClassicalFocus"),
    "ambient": ("#AmbientClassical #ClassicalNightRelax #RelaxingClassical #ClassicalLive"
                " #AmbientMusic #ClassicalMusic #NatureAndClassical #CalmMusic"
                " #RelaxingAmbient #ClassicalAmbient"),
}


# ── Sacred Drift constants ────────────────────────────────────────────────────

SD_TITLE_MAP = [
    # Category compilations (generated by generate_sd_compilation.py)
    ("sd_comp_rain_water",      "Rain & Water Meditation 🌊",          "nature"),
    ("sd_comp_forest_nature",   "Forest & Nature Sounds 🌲",           "nature"),
    ("sd_comp_morning_yoga",    "Morning Yoga & Awakening 🌅",         "nature"),
    ("sd_comp_desert_mountain", "Mountain & Desert Meditation 🏔️",    "nature"),
    ("sd_comp_deep_sleep",      "Deep Sleep Music 😴",                 "sleep"),
    ("sd_comp_ambient_piano",   "Ambient Piano & Strings 🎹",          "sleep"),
    ("sd_comp_solfeggio",       "Solfeggio Frequencies — Complete 🎶", "healing"),
    ("sd_comp_chakra_journey",  "Full Chakra Journey 🌈",              "healing"),
    ("sd_comp_crown_chakra",    "Crown Chakra Healing ✨",              "healing"),
    ("sd_comp_heart_chakra",    "Heart Chakra Opening 💚",             "healing"),
    ("sd_comp_root_chakra",     "Root Chakra Grounding 🌿",            "healing"),
    ("sd_comp_third_eye",       "Third Eye Awakening 👁",              "healing"),
    ("sd_comp_tibetan_bowls",   "Tibetan & Crystal Bowls 🔔",          "healing"),
    ("sd_comp_zen_mantra",      "Zen & Sacred Mantra 🧘",              "healing"),
    ("sd_comp_healing_reiki",   "Reiki & Healing Energy ✨",           "healing"),
    ("sd_comp_cosmic_space",    "Cosmic Space Meditation 🌌",          "healing"),
    # Individual tracks (keywords in filename)
    ("rain",        "Rain Meditation 🌧️",                "nature"),
    ("ocean",       "Ocean Waves Meditation 🌊",         "nature"),
    ("waterfall",   "Waterfall Meditation 💧",            "nature"),
    ("forest",      "Forest Sounds Meditation 🌲",       "nature"),
    ("bamboo",      "Bamboo Forest Meditation 🌿",        "nature"),
    ("mountain",    "Mountain Meditation 🏔️",           "nature"),
    ("morning",     "Morning Meditation 🌅",             "nature"),
    ("yoga",        "Yoga & Flow Meditation 🧘",         "nature"),
    ("sleep",       "Deep Sleep Meditation 😴",          "sleep"),
    ("lullaby",     "Sleep Lullaby Music 🌙",            "sleep"),
    ("drone",       "Ambient Drone Meditation 🎵",       "sleep"),
    ("piano",       "Ambient Piano Meditation 🎹",       "sleep"),
    ("chakra",      "Chakra Healing Meditation ✨",      "healing"),
    ("solfeggio",   "Solfeggio Frequencies 🎶",          "healing"),
    ("tibetan",     "Tibetan Bowls Sound Healing 🔔",    "healing"),
    ("gong",        "Gong Bath Sound Healing 🔔",        "healing"),
    ("reiki",       "Reiki Energy Healing ✨",           "healing"),
    ("zen",         "Zen Meditation 🧘",                 "healing"),
    ("mantra",      "Sacred Mantra Meditation 🕉️",     "healing"),
    ("cosmic",      "Cosmic Space Meditation 🌌",        "healing"),
    ("frequency",   "Healing Frequencies 🎶",            "healing"),
    ("anxiety",     "Anxiety Relief Meditation 🌿",      "healing"),
]

SD_MOOD_EMOJI = {"sleep": "😴", "healing": "✨", "nature": "🌿"}

SD_LIVE_PREFIX = "🔴 LIVE: "
SD_CHAN_SUFFIX  = " | Sacred Drift"

SD_HASHTAGS = {
    "sleep": (
        "#SleepMeditation #DeepSleepMusic #MeditationMusic #SacredDrift #RelaxingMusic"
        " #SleepSounds #MeditationSounds #HealingMusic #AmbientMusic #SleepAid"
        " #MindfulnessMeditation #SoundHealing #MeditationLive #DeltaWaves"
    ),
    "healing": (
        "#ChakraHealing #SolfeggiFrequencies #HealingFrequencies #SacredDrift #MeditationMusic"
        " #TibetanBowls #SoundBath #SoundHealing #MeditationLive #Mindfulness"
        " #ChakraMeditation #HealingVibes #528Hz #432Hz #SacredSound"
    ),
    "nature": (
        "#NatureSounds #RainMeditation #ForestSounds #SacredDrift #MeditationMusic"
        " #NatureMeditation #RelaxingNature #OceanWaves #RainSounds #MeditationLive"
        " #NatureHealing #MindfulnessNature #AmbientNature #NatureTherapy"
    ),
}

# Map SD mood keywords to visual theme frames for thumbnail fallback
SD_THUMB_THEMES = {
    "sleep":   ["evening_piano", "fireplace_cabin", "night_rain"],
    "healing": ["aurora_borealis", "lavender_fields", "zen_garden"],
    "nature":  ["rainforest_night", "distant_waterfall", "mountain_snow"],
}


def _sd_classify(filename: str) -> tuple[str, str]:
    """Return (display_title, mood) for a Sacred Drift video filename."""
    stem = filename.lower()
    for keyword, title, mood in SD_TITLE_MAP:
        if keyword in stem:
            return title, mood
    return "🔮 Sacred Drift Meditation", "healing"


def _sd_build_description(playlist: list[Path], mood: str) -> str:
    titles = []
    for v in playlist[:8]:
        t, _ = _sd_classify(v.name)
        clean = t.split(" — ")[0].strip()
        if clean not in titles:
            titles.append(clean)
    programme = " • ".join(titles) if titles else "Sacred Sound Meditation"

    mood_intro = {
        "sleep": (
            "😴 Welcome to Sacred Drift — continuous meditation music to help you fall into"
            " deep, restful sleep and wake up refreshed."
        ),
        "healing": (
            "✨ Welcome to Sacred Drift — healing frequencies, chakra music and sacred"
            " soundscapes for energy alignment, stress relief and inner peace."
        ),
        "nature": (
            "🌿 Welcome to Sacred Drift — nature sounds and meditative music to ground you,"
            " calm your nervous system and reconnect with the earth."
        ),
    }.get(mood, "🔮 Welcome to Sacred Drift — sacred sound for rest, healing and inner peace.")

    mood_bullets = {
        "sleep": (
            "💤 Perfect for:\n"
            "• Falling asleep faster and staying asleep\n"
            "• Reducing anxiety and stress before bed\n"
            "• Delta wave and deep relaxation\n"
            "• Sleep meditation and lucid dreaming"
        ),
        "healing": (
            "⚡ Perfect for:\n"
            "• Chakra balancing and energy work\n"
            "• Solfeggio frequency healing sessions\n"
            "• Reiki, yoga and breathwork practice\n"
            "• Stress relief and emotional healing"
        ),
        "nature": (
            "🌊 Perfect for:\n"
            "• Grounding and nature meditation\n"
            "• Background music for yoga and stretching\n"
            "• Anxiety relief and nervous system calm\n"
            "• Focus and gentle relaxation"
        ),
    }.get(mood, "")

    return (
        f"{mood_intro}\n\n"
        f"🎧 Now playing: {programme}\n\n"
        f"{mood_bullets}\n\n"
        f"🎵 All music AI-generated (Suno / Mureka) — 100% original, royalty-free.\n"
        f"🔔 Subscribe and hit the bell to catch our daily meditation streams!\n\n"
        f"@SacredDrift\n\n"
        f"{SD_HASHTAGS.get(mood, SD_HASHTAGS['healing'])}"
    )


def _make_sd_thumbnail(base_img: Path, title: str, mood: str,
                       duration_label: str = "LIVE") -> Path:
    """
    Sacred Drift live thumbnail: dark mystical background, gold/purple palette.
    Layout: LIVE badge top-right, large title center, Sacred Drift branding bottom.
    """
    from PIL import Image, ImageDraw, ImageFont, ImageFilter

    SD_THUMB_TMP = ROOT / "logs" / "thumb_sd_tmp"
    SD_THUMB_TMP.mkdir(parents=True, exist_ok=True)
    out_path = SD_THUMB_TMP / f"thumb_{hash(title) & 0xFFFFFF:06x}_{duration_label}.png"

    img = Image.open(base_img).convert("RGB").resize((1280, 720), Image.LANCZOS)
    # Darken the base image for readability
    dark = Image.new("RGB", img.size, (0, 0, 0))
    img  = Image.blend(img, dark, alpha=0.45)
    draw = ImageDraw.Draw(img)
    W, H = img.size

    def load_font(path: str, size: int):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            return ImageFont.truetype(
                "/usr/share/fonts/truetype/noto/NotoSerifDisplay-Regular.ttf", size)

    font_title   = load_font(FONT_BOLD,   80)
    font_sub     = load_font(FONT_MEDIUM, 38)
    font_channel = load_font(FONT_LIGHT,  28)
    font_badge   = load_font(FONT_BOLD,   40)

    # Bottom gradient
    grad_h = 200
    gradient = Image.new("RGBA", (W, grad_h))
    for y in range(grad_h):
        alpha = int(200 * (y / grad_h) ** 0.5)
        for x in range(W):
            gradient.putpixel((x, y), (10, 0, 30, alpha))
    img.paste(Image.new("RGB", (W, grad_h), (10, 0, 30)), (0, H - grad_h), gradient)

    def shadow(text, font, x, y, fill, anchor="mm"):
        draw.text((x + 3, y + 3), text, font=font, fill=(0, 0, 0, 180), anchor=anchor)
        draw.text((x, y), text, font=font, fill=fill, anchor=anchor)

    # LIVE / duration badge — top right, red pill
    badge_color = (200, 30, 30) if duration_label == "LIVE" else (140, 100, 10)
    bx, by = W - 20, 16
    bbox = draw.textbbox((bx, by), duration_label, font=font_badge, anchor="ra")
    pad  = 14
    draw.rounded_rectangle([bbox[0]-pad, bbox[1]-6, bbox[2]+pad, bbox[3]+8],
                            radius=8, fill=badge_color)
    draw.text((bx, by + (bbox[3]-bbox[1])//2 + 6), duration_label,
              font=font_badge, fill="white", anchor="rm")

    # Title (strip leading emoji for cleaner render, keep text)
    clean_title = title.replace(SD_LIVE_PREFIX, "").replace(SD_CHAN_SUFFIX, "").strip()
    # Split if too long
    if draw.textlength(clean_title, font=font_title) > W - 80:
        parts = clean_title.split(" — ", 1)
        shadow(parts[0], font_title, W // 2, H - 200, fill=(255, 220, 100))
        if len(parts) > 1:
            shadow(parts[1], font_sub, W // 2, H - 128, fill=(200, 180, 255))
    else:
        shadow(clean_title, font_title, W // 2, H - 170, fill=(255, 220, 100))

    # Mood subtitle
    mood_sub = {"sleep": "✦ Deep Sleep Meditation ✦",
                "healing": "✦ Healing Frequencies & Sacred Sound ✦",
                "nature": "✦ Nature & Earth Meditation ✦"}.get(mood, "✦ Sacred Sound Meditation ✦")
    shadow(mood_sub, font_sub, W // 2, H - 90, fill=(180, 160, 220))

    # Channel branding bottom
    draw.text((W // 2, H - 22), "Sacred Drift", font=font_channel,
              fill=(140, 120, 180), anchor="ms")

    img.save(out_path, "PNG", optimize=True)
    return out_path


def _sd_find_thumbnail(primary: Path, queue_dir: Path, mood: str) -> Path | None:
    """Find thumbnail for Sacred Drift stream — prefer queue-side thumb, fall back to theme frame."""
    # 1. Exact video-specific thumb in queue
    stem_prefix = primary.stem.rsplit("_", 1)[0]  # strip date suffix
    for thumb in sorted(queue_dir.glob(f"thumb_{stem_prefix}*.png")):
        return thumb

    # 2. Any thumb in queue matching the mood category
    for comp_key in SD_THUMB_THEMES.get(mood, []):
        for thumb in sorted(queue_dir.glob(f"thumb_sd_comp_{comp_key}*.png")):
            return thumb

    # 3. Fall back to visual theme frames
    themes = SD_THUMB_THEMES.get(mood, ["zen_garden"])
    import random
    theme = random.choice(themes)
    theme_dir = ROOT / "assets" / "visual_themes" / theme
    frames = sorted(theme_dir.glob("frame_*.png"))
    if frames:
        return frames[len(frames) // 2]

    return None


def _extract_composers(playlist: list[Path]) -> list[str]:
    """Extract unique composer display names from playlist filenames, preserving order."""
    seen, composers = set(), []
    for v in playlist:
        stem = v.stem.lower()
        for key, display in COMPOSER_DISPLAY.items():
            if key in stem and display not in seen:
                seen.add(display)
                composers.append(display)
                break
    return composers


def _build_description(playlist: list[Path], mood: str) -> str:
    """Generate a specific, SEO-rich description based on actual playlist content."""
    composers = _extract_composers(playlist)
    composer_list = " • ".join(composers) if composers else "Classical Masters"

    mood_intro = {
        "sleep": (
            "🌙 Welcome to Classical Night Relax — uninterrupted classical music to help you fall "
            "asleep and stay asleep through the night."
        ),
        "focus": (
            "🎵 Welcome to Classical Night Relax — classical music carefully curated for deep "
            "focus, concentration, and productive work."
        ),
        "ambient": (
            "🌿 Welcome to Classical Night Relax — beautiful classical music paired with stunning "
            "visual atmospheres for perfect relaxation."
        ),
    }.get(mood, "🎵 Welcome to Classical Night Relax — the finest classical music, streaming daily.")

    programme_line = f"🎼 Tonight's programme: {composer_list}"

    mood_bullets = {
        "sleep": (
            "💤 Perfect for:\n"
            "• Falling asleep faster and staying asleep\n"
            "• Stress relief and deep relaxation\n"
            "• Meditation and mindfulness\n"
            "• Yoga and breathing exercises\n"
            "• Late-night studying"
        ),
        "focus": (
            "⚡ Perfect for:\n"
            "• Deep work and study sessions\n"
            "• Coding, writing, and creative work\n"
            "• Any task requiring sustained concentration\n"
            "• Background music for peak productivity"
        ),
        "ambient": (
            "✨ Perfect for:\n"
            "• Relaxation and unwinding\n"
            "• Background music for reading\n"
            "• Meditation and mindfulness\n"
            "• Creating a peaceful home atmosphere"
        ),
    }.get(mood, "")

    return (
        f"{mood_intro}\n\n"
        f"{programme_line}\n\n"
        f"{mood_bullets}\n\n"
        f"🎵 All recordings sourced from Musopen.org — public domain, copyright-free classical music.\n"
        f"🔔 Subscribe and click the bell to never miss our daily classical streams!\n\n"
        f"{HASHTAGS.get(mood, HASHTAGS['ambient'])}"
    )

log = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler()],
    )


def _load_json(path: Path, default):
    if path.exists():
        try:
            text = path.read_text().strip()
            if text:
                return json.loads(text)
        except Exception:
            pass
    return default


def _save_json(path: Path, data):
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def _classify(filename: str) -> tuple[str, str]:
    """Return (emoji + display_title, mood) for a video filename."""
    stem = filename.lower()
    for keyword, title, mood in TITLE_MAP:
        if keyword in stem:
            return f"{MOOD_EMOJI[mood]} {title}", mood
    return "🎵 Classical Music", "ambient"


def _is_short(filename: str) -> bool:
    return any(p in filename for p in SHORT_PATTERNS)


def _get_duration(path: Path) -> float:
    """Return video duration in seconds via ffprobe."""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=30,
        )
        return float(r.stdout.strip())
    except Exception:
        return 3600.0


def _is_file_complete(path: Path) -> bool:
    """Return True if the MP4 is fully written (moov atom present, ffprobe succeeds)."""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=15,
        )
        return r.returncode == 0 and r.stdout.strip() not in ("", "N/A")
    except Exception:
        return False


def _list_long_videos(queue_dir: Path) -> list[Path]:
    """All fully-written long-form MP4s in queue_dir, sorted newest first."""
    videos = []
    for p in queue_dir.glob("*.mp4"):
        if _is_short(p.name):
            continue
        if not _is_file_complete(p):
            log.info(f"  skip (still writing): {p.name}")
            continue
        dur = _get_duration(p)
        if dur >= MIN_DURATION_SEC:
            videos.append((p, dur))
    videos.sort(key=lambda x: x[0].stat().st_mtime, reverse=True)
    return [p for p, _ in videos]


# ── Playlist building ─────────────────────────────────────────────────────────

def _pick_playlist(queue_dir: Path, history: list, target_hours: float,
                   mood_filter: str = "any") -> list[Path]:
    """
    Build a diverse playlist filling ~target_hours.
    Rotates through composers/themes, avoiding content used in recent streams.
    Each video contributes at most MAX_SINGLE_CONTRIBUTION_HOURS to avoid monopoly.
    If the playlist is still short after one pass, repeats it.
    """
    all_videos = _list_long_videos(queue_dir)
    if not all_videos:
        return []

    # Filter by mood if requested
    if mood_filter != "any":
        filtered = [v for v in all_videos if _classify(v.name)[1] == mood_filter]
        if filtered:
            all_videos = filtered

    # Videos used in the last 14 streams (avoid immediate repeats)
    recent_names: set[str] = set()
    for h in history[-14:]:
        for p in h.get("playlist", []):
            recent_names.add(Path(p).name)

    # Sort: prefer not-recently-used, then diverse moods
    def _score(v: Path) -> int:
        return 0 if v.name in recent_names else 10

    candidates = sorted(all_videos, key=_score, reverse=True)

    target_secs = target_hours * 3600
    max_single  = MAX_SINGLE_CONTRIBUTION_HOURS * 3600

    playlist: list[Path] = []
    total_secs = 0.0
    used_moods: set[str] = set()

    # First pass: pick diverse candidates, cap contribution per video
    for v in candidates:
        _, mood = _classify(v.name)
        dur = _get_duration(v)
        contribution = min(dur, max_single)
        # Prefer mood variety in first 4 slots
        if len(playlist) < 4 and mood in used_moods and len(used_moods) < 2:
            continue
        playlist.append(v)
        total_secs += contribution
        used_moods.add(mood)
        if total_secs >= target_secs:
            break

    # Second pass: if still short, add remaining candidates
    if total_secs < target_secs:
        added = set(v.name for v in playlist)
        for v in candidates:
            if v.name in added:
                continue
            dur = _get_duration(v)
            playlist.append(v)
            total_secs += min(dur, max_single)
            if total_secs >= target_secs:
                break

    # Still short (few videos)? Repeat the playlist until filled
    if playlist and total_secs < target_secs:
        base = list(playlist)
        idx  = 0
        while total_secs < target_secs and idx < 500:
            v = base[idx % len(base)]
            playlist.append(v)
            total_secs += _get_duration(v)
            idx += 1

    return playlist


def _sd_get_category(filename: str) -> str:
    """Classify a Sacred Drift filename into one of SD_CAT_KEYWORDS categories."""
    stem = filename.lower().replace("-", "_")
    for cat, keywords in SD_CAT_KEYWORDS.items():
        for kw in keywords:
            if kw in stem:
                return cat
    return "sleep"  # default


def _sd_series_base(filename: str) -> str:
    """Extract series base name (strip date suffix and trailing _N index)."""
    stem = Path(filename).stem
    # strip _YYYYMMDD date
    stem = re.sub(r'_20\d{6}$', '', stem)
    # strip trailing _N (episode number)
    stem = re.sub(r'_\d+$', '', stem)
    return stem


def _sd_series_cap(series_base: str) -> float:
    """Return max hours a series may contribute to one stream."""
    base_lower = series_base.lower()
    for key, cap in SD_SERIES_MAX_HOURS.items():
        if key in base_lower:
            return cap
    # Classical programs are unique content — no cap needed
    if "classical" in base_lower:
        return SD_UNIQUE_SERIES_MAX_HOURS
    return SD_DEFAULT_SERIES_MAX_HOURS


def _sd_pick_playlist(queue_dir: Path, history: list, target_hours: float,
                      theme_override: str = "auto") -> tuple[list[Path], str]:
    """
    Build a Sacred Drift themed playlist for today's day-of-week rotation.

    Rules:
    - Theme determines category priorities (SD_THEME_WEIGHTS)
    - Per-series cap prevents any one series from monopolising the stream
    - Meditation audio repeats are acceptable but visual variant is preferred
      (glacier/waterfall/bamboo series already have different visuals per episode)
    - On forced repeat fill: shuffle playlist so order differs from previous run
    - Returns (playlist, theme_name)
    """
    import random as _random
    all_videos = _list_long_videos(queue_dir)
    if not all_videos:
        return [], "any"

    # Determine today's theme
    if theme_override == "auto":
        theme = SD_DAILY_THEMES[datetime.now(timezone.utc).weekday()]
    else:
        theme = theme_override if theme_override in SD_THEME_WEIGHTS else "healing"

    weights = SD_THEME_WEIGHTS[theme]
    theme_display = SD_THEME_DISPLAY[theme][0]
    log.info(f"  [SD] Today's theme: {theme} — {theme_display}")

    # Score each video
    recent_names: set[str] = set()
    for h in history[-14:]:
        for p in h.get("playlist", []):
            recent_names.add(Path(p).name)

    def _score(v: Path) -> float:
        cat = _sd_get_category(v.name)
        w = weights.get(cat, 0.05)
        freshness = 0.0 if v.name in recent_names else 3.0
        return w + freshness + _random.uniform(0, 0.1)  # small random tiebreak

    candidates = sorted(all_videos, key=_score, reverse=True)

    target_secs = target_hours * 3600
    series_used: dict[str, float] = {}   # base_name → hours used
    playlist: list[Path] = []
    total_secs = 0.0

    # Pass 1: fill with theme-scored candidates, respecting series caps
    for v in candidates:
        dur     = _get_duration(v)
        base    = _sd_series_base(v.name)
        cap     = _sd_series_cap(base) * 3600
        used_so_far = series_used.get(base, 0.0)
        if used_so_far >= cap:
            continue  # this series has hit its cap
        contribution = min(dur, cap - used_so_far)
        playlist.append(v)
        total_secs += contribution
        series_used[base] = used_so_far + contribution
        if total_secs >= target_secs:
            break

    # Pass 2: if still short, re-allow capped series with their remaining quota
    if total_secs < target_secs:
        added = {v.name for v in playlist}
        for v in candidates:
            if v.name in added:
                continue
            dur = _get_duration(v)
            playlist.append(v)
            total_secs += dur
            if total_secs >= target_secs:
                break

    # Pass 3: forced repeat fill (meditation content) — shuffle so it sounds different
    if playlist and total_secs < target_secs:
        cat_for_theme = list(weights.keys())[0]  # primary category
        # Prefer repeating meditation/nature content (no vocals)
        repeat_pool = [v for v in playlist
                       if _sd_get_category(v.name) in ("hz_freq", "chakra", "nature", "sleep", "reiki", "tibetan")]
        if not repeat_pool:
            repeat_pool = list(playlist)
        _random.shuffle(repeat_pool)
        idx = 0
        while total_secs < target_secs and idx < 500:
            v = repeat_pool[idx % len(repeat_pool)]
            playlist.append(v)
            total_secs += _get_duration(v)
            idx += 1
        log.info(f"  [SD] Repeat fill: added {idx} clips from meditation pool")

    log.info(f"  [SD] Playlist: {len(playlist)} videos, ~{total_secs/3600:.1f}h | theme={theme}")
    cat_counts: dict[str, int] = {}
    for v in playlist:
        c = _sd_get_category(v.name)
        cat_counts[c] = cat_counts.get(c, 0) + 1
    for cat, cnt in sorted(cat_counts.items(), key=lambda x: -x[1]):
        log.info(f"    {cat:15s}: {cnt} videos")

    return playlist, theme


def _build_concat_file(playlist: list[Path], out: Path):
    """Write ffmpeg concat demuxer playlist file."""
    lines = []
    for p in playlist:
        escaped = str(p).replace("'", r"'\''")
        lines.append(f"file '{escaped}'")
    out.write_text("\n".join(lines) + "\n")


MAX_SILENCE_RATIO = 0.15   # reject files where >15% of audio is silent gaps (>10s each)
_AUDIO_CACHE: dict[str, bool] = {}   # path → audio_ok (in-process cache)


def _has_audio_gaps(path: Path) -> bool:
    """Return True if the file has excessive silent gaps (>15% of duration above 10s each)."""
    key = str(path)
    if key in _AUDIO_CACHE:
        return not _AUDIO_CACHE[key]
    try:
        dur_result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1", str(path)],
            capture_output=True, text=True, timeout=15,
        )
        total = float(dur_result.stdout.split("=")[-1].strip())
        if total < 300:   # skip short files — silence check not meaningful
            _AUDIO_CACHE[key] = True
            return False
        silence_result = subprocess.run(
            ["ffmpeg", "-i", str(path), "-vn",
             "-af", "silencedetect=noise=-50dB:duration=10",
             "-f", "null", "/dev/null"],
            capture_output=True, text=True, timeout=120,
        )
        gap_secs = 0.0
        for line in silence_result.stderr.splitlines():
            if "silence_duration:" in line:
                gap_secs += float(line.split("silence_duration:")[-1].strip())
        ratio = gap_secs / total if total > 0 else 0
        ok = ratio <= MAX_SILENCE_RATIO
        _AUDIO_CACHE[key] = ok
        if not ok:
            log.warning(f"Audio gap check: {path.name} — {gap_secs:.0f}s silent / {total:.0f}s total ({ratio:.0%})")
        return not ok
    except Exception as e:
        log.warning(f"Audio gap check failed for {path.name}: {e}")
        return False


def _validate_playlist_file(playlist_path: Path) -> int:
    """
    Read the concat playlist, remove any entries whose file is:
      - missing
      - corrupt (ffprobe fails)
      - has excessive silent audio gaps (>15% of duration)
    Returns number of entries removed.
    """
    if not playlist_path.exists():
        return 0

    lines = playlist_path.read_text().splitlines()
    good: list[str] = []
    removed = 0
    for line in lines:
        line = line.strip()
        if not line or not line.startswith("file '"):
            good.append(line)
            continue
        path_str = line[6:].rstrip("'")
        p = Path(path_str)
        if not p.exists():
            log.warning(f"Playlist: removing missing file: {p.name}")
            removed += 1
            continue
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1", str(p)],
            capture_output=True, text=True, timeout=15,
        )
        if probe.returncode != 0 or "error" in probe.stderr.lower():
            log.warning(f"Playlist: removing corrupt file: {p.name}")
            removed += 1
            continue
        if _has_audio_gaps(p):
            log.warning(f"Playlist: removing file with audio gaps: {p.name}")
            removed += 1
            continue
        good.append(line)

    if removed:
        playlist_path.write_text("\n".join(good) + "\n")
        log.info(f"Playlist cleaned: removed {removed} invalid file(s), {len(good)} remain")

    return removed


# ── YouTube API ───────────────────────────────────────────────────────────────

def _get_youtube(channel: str):
    import json as _json
    import os
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    token_path = CHANNEL_TOKENS[channel]
    raw = token_path.read_text().strip() if token_path.exists() else ""
    if not raw:
        raise RuntimeError(
            f"YouTube token file is missing or empty: {token_path}\n"
            f"Run: python3 scripts/reauth_youtube.py --channel {channel}"
        )
    t = _json.loads(raw)
    scopes = [
        "https://www.googleapis.com/auth/youtube",
        "https://www.googleapis.com/auth/youtube.force-ssl",
    ]
    creds = Credentials(
        token=t.get("access_token"),
        refresh_token=t["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=t["client_id"],
        client_secret=t["client_secret"],
        scopes=scopes,
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        t["access_token"] = creds.token
        # Atomic write: temp file + rename so a full disk can't zero out the token
        tmp = token_path.with_suffix(".tmp")
        tmp.write_text(_json.dumps(t, indent=2))
        os.replace(str(tmp), str(token_path))
    return build("youtube", "v3", credentials=creds)


def _get_or_create_rtmp_stream(yt, channel: str) -> tuple[str, str]:
    """
    Return (stream_id, full_rtmp_url).
    Reuses the saved reusable RTMP stream if it still exists; otherwise creates one.
    """
    rf = _rtmp_file(channel)
    cached = _load_json(rf, {})

    if cached.get("stream_id") and cached.get("rtmp_url"):
        try:
            resp = yt.liveStreams().list(
                part="id,cdn,status",
                id=cached["stream_id"],
            ).execute()
            if resp.get("items"):
                log.info(f"Reusing RTMP stream: {cached['stream_id']}")
                return cached["stream_id"], cached["rtmp_url"]
        except Exception as e:
            log.warning(f"Cached stream check failed ({e}), creating new stream...")

    log.info("Creating new reusable RTMP stream...")
    stream = yt.liveStreams().insert(
        part="snippet,cdn,contentDetails",
        body={
            "snippet": {"title": "Classical Night Relax — Live"},
            "cdn": {
                "frameRate": "30fps",
                "ingestionType": "rtmp",
                "resolution": "1080p",
            },
            "contentDetails": {"isReusable": True},
        },
    ).execute()

    stream_id = stream["id"]
    info      = stream["cdn"]["ingestionInfo"]
    rtmp_url  = info["ingestionAddress"] + "/" + info["streamName"]
    _save_json(rf, {"stream_id": stream_id, "rtmp_url": rtmp_url})
    log.info(f"RTMP stream created: {stream_id}")
    return stream_id, rtmp_url


def _create_broadcast(yt, title: str, description: str, save_vod: bool = True) -> str:
    """
    Create a YouTube live broadcast with auto-start/stop.
    save_vod=False → recordFromStart:false, stream goes live but no VOD is created.
    Returns broadcast_id.
    """
    start_time = (
        datetime.now(timezone.utc) + timedelta(minutes=2)
    ).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    broadcast = yt.liveBroadcasts().insert(
        part="snippet,status,contentDetails",
        body={
            "snippet": {
                "title": title[:100],
                "description": description,
                "scheduledStartTime": start_time,
                "categoryId": "10",   # Music
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False,
            },
            "contentDetails": {
                "enableAutoStart":  False,     # we transition manually via API
                "enableAutoStop":   True,      # complete when ffmpeg disconnects
                "enableDvr":        save_vod,
                "recordFromStart":  save_vod,
                "latencyPreference": "normal",
                "monitorStream": {"enableMonitorStream": True, "broadcastStreamDelayMs": 0},
            },
        },
    ).execute()
    return broadcast["id"]


# ── Thumbnail matching ────────────────────────────────────────────────────────

FONT_BOLD    = "/usr/share/fonts/truetype/custom/BebasNeue-Regular.ttf"
FONT_MEDIUM  = "/usr/share/fonts/truetype/custom/Montserrat-Bold.ttf"
FONT_LIGHT   = "/usr/share/fonts/truetype/custom/Montserrat-Regular.ttf"
CNR_THUMB_TMP = ROOT / "logs" / "thumb_live_tmp"


def _extract_composer_and_type(title: str, mood: str) -> tuple[str, str]:
    """Extract composer surname and music type label from stream title."""
    # Strip LIVE prefix and channel suffix
    clean = title.replace("🔴 LIVE:", "").strip()
    clean = clean.split("|")[0].strip()

    composer_map = {
        "beethoven": "BEETHOVEN", "bach": "BACH", "chopin": "CHOPIN",
        "mozart": "MOZART", "schubert": "SCHUBERT", "brahms": "BRAHMS",
        "debussy": "DEBUSSY", "tchaikovsky": "TCHAIKOVSKY",
        "wagner": "WAGNER", "vivaldi": "VIVALDI", "handel": "HANDEL",
        "schumann": "SCHUMANN", "liszt": "LISZT", "verdi": "VERDI",
        "franck": "FRANCK", "albinoni": "ALBINONI",
        "autumn forest": "AUTUMN FOREST", "cherry blossom": "CHERRY BLOSSOM",
        "fireplace": "FIREPLACE", "rainforest": "RAINFOREST",
    }
    composer = "CLASSICAL"
    for key, label in composer_map.items():
        if key in clean.lower():
            composer = label
            break

    type_map = {"sleep": "♪ Sleep Music ♪", "focus": "♪ Focus Music ♪", "ambient": "♪ Ambient Music ♪"}
    music_type = type_map.get(mood, "♪ Classical Music ♪")

    return composer, music_type


def _make_cnr_thumbnail(base_photo: Path, title: str, mood: str,
                        duration_label: str = "LIVE") -> Path:
    """
    Overlay text on a CNR base photo in top-channel style:
      top-right: duration badge (LIVE / 4H / 8H)
      center: COMPOSER NAME (large)
      center-sub: ♪ Sleep Music ♪
      bottom strip: Classical Night Relax
    Returns path to the generated thumbnail (in logs/thumb_live_tmp/).
    """
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    import textwrap

    CNR_THUMB_TMP.mkdir(parents=True, exist_ok=True)
    out_path = CNR_THUMB_TMP / f"thumb_{hash(title) & 0xFFFFFF:06x}_{duration_label}.png"

    img = Image.open(base_photo).convert("RGB").resize((1280, 720), Image.LANCZOS)
    draw = ImageDraw.Draw(img)
    W, H = img.size

    composer, music_type = _extract_composer_and_type(title, mood)

    def load_font(path: str, size: int):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            return ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSerifDisplay-Regular.ttf", size)

    font_composer = load_font(FONT_BOLD, 110)
    font_type     = load_font(FONT_MEDIUM, 46)
    font_channel  = load_font(FONT_LIGHT, 30)
    font_badge    = load_font(FONT_BOLD, 44)

    # ── Bottom gradient ──────────────────────────────────────────────────────
    grad_h = 220
    gradient = Image.new("RGBA", (W, grad_h))
    for y in range(grad_h):
        alpha = int(210 * (y / grad_h) ** 0.6)
        for x in range(W):
            gradient.putpixel((x, y), (0, 0, 0, alpha))
    img.paste(Image.new("RGB", (W, grad_h), (0, 0, 0)),
              (0, H - grad_h), gradient)

    # ── Top shadow for badge ─────────────────────────────────────────────────
    top_grad = Image.new("RGBA", (W, 90))
    for y in range(90):
        alpha = int(160 * (1 - y / 90))
        for x in range(W):
            top_grad.putpixel((x, y), (0, 0, 0, alpha))
    img.paste(Image.new("RGB", (W, 90), (0, 0, 0)), (0, 0), top_grad)

    def draw_text_shadow(text, font, x, y, fill, shadow=(0, 0, 0), offset=3, anchor="mm"):
        draw.text((x + offset, y + offset), text, font=font, fill=(*shadow, 180), anchor=anchor)
        draw.text((x, y), text, font=font, fill=fill, anchor=anchor)

    # ── Duration badge top-right ─────────────────────────────────────────────
    badge_text = duration_label
    badge_color = (220, 30, 30) if duration_label == "LIVE" else (180, 140, 20)
    bx, by = W - 24, 18
    bbox = draw.textbbox((bx, by), badge_text, font=font_badge, anchor="ra")
    pad = 12
    draw.rounded_rectangle([bbox[0]-pad, bbox[1]-6, bbox[2]+pad, bbox[3]+6],
                            radius=8, fill=badge_color)
    draw.text((bx, by + (bbox[3]-bbox[1])//2 + 6), badge_text,
              font=font_badge, fill="white", anchor="rm")

    # ── Composer name (large, center) ────────────────────────────────────────
    cy = H - 160
    draw_text_shadow(composer, font_composer, W // 2, cy, fill=(255, 255, 255), offset=4)

    # ── Music type subtitle ──────────────────────────────────────────────────
    draw_text_shadow(music_type, font_type, W // 2, cy + 72, fill=(200, 200, 200), offset=2)

    # ── Channel name bottom ──────────────────────────────────────────────────
    draw.text((W // 2, H - 22), "Classical Night Relax",
              font=font_channel, fill=(160, 160, 160), anchor="ms")

    img.save(out_path, "PNG", optimize=True)
    return out_path


def _is_cnr_thumb(p: Path) -> bool:
    """True only for CNR-appropriate thumbnails: new-style _natural_, visual_theme, or nature_calm.
    All new CNR thumbnails have _natural_ or visual_theme in the filename.
    Old 8h/1h kids thumbnails and shorts frames don't have these keywords."""
    name = p.name
    # Require at least one positive CNR indicator
    if not any(kw in name for kw in ("_natural_", "visual_theme", "nature_calm")):
        return False
    # Reject short-clip thumbnails — not suitable as stream thumbnails
    if any(kw in name for kw in ("kw_short", "sleep_short", "visual_short", "shadow_")):
        return False
    return True


CNR_THUMB_POOL = ROOT / "assets" / "thumbnails" / "cnr"

# Mood → preferred filenames in CNR_THUMB_POOL (no extension, partial match)
_CNR_MOOD_THUMBS = {
    "sleep":   ["swans_foggy_lake", "swans_moonlit", "moonlit_hills", "moonlit_forest", "jellyfish_blue"],
    "focus":   ["rainy_window_candle", "mountain_sunset", "mountain_snow"],
    "ambient": ["autumn_forest", "rainforest_night", "cherry_blossoms", "fireplace_cabin", "evening_piano"],
}


def _find_thumbnail(primary: Path, queue_dir: Path) -> Path | None:
    """
    Find the best matching thumbnail for the primary stream video.
    1. Exact match alongside the video in queue_dir (video-specific thumb)
    2. Mood-based pick from assets/thumbnails/cnr/ pool (guaranteed adult/photo)
    3. Any file in cnr pool
    Never falls back to queue_dir glob — avoids picking kids/cartoon thumbs.
    """
    import re
    prefix = re.sub(r'_(natural|\d+h)_\d{8}$', '', primary.stem)

    # 1. Video-specific thumb in queue_dir
    for thumb in sorted(queue_dir.glob(f"thumb_{prefix}*_natural_*.png")):
        if _is_cnr_thumb(thumb):
            return thumb

    # 2. Mood-based pick from CNR pool
    _, mood = _classify(primary.name)
    for kw in _CNR_MOOD_THUMBS.get(mood, []):
        for thumb in sorted(CNR_THUMB_POOL.glob(f"{kw}*.png")):
            return thumb

    # 3. Any CNR pool thumb (round-robin by name for variety)
    pool = sorted(CNR_THUMB_POOL.glob("*.png"))
    if pool:
        # Pick based on video filename hash for consistent but varied selection
        idx = hash(primary.stem) % len(pool)
        return pool[idx]

    return None


def _post_process_vod(yt, broadcast_id: str, state: dict, queue_dir: Path,
                      channel: str = "id"):
    """
    After stream ends: clean the title (remove 🔴 LIVE: prefix) and upload a proper thumbnail.
    Called with a brief delay after transition to allow YouTube to process the VOD.
    """
    import time
    time.sleep(15)   # give YouTube time to process the completed broadcast

    is_sd = (channel == "sd")
    live_prefix = SD_LIVE_PREFIX if is_sd else LIVE_PREFIX

    # 1. Clean title
    raw_title   = state.get("stream_title", "")
    clean_title = raw_title.replace(live_prefix, "").strip()
    try:
        resp = yt.videos().list(part="snippet", id=broadcast_id).execute()
        if resp.get("items"):
            snippet = resp["items"][0]["snippet"]
            snippet["title"] = clean_title
            yt.videos().update(
                part="snippet",
                body={"id": broadcast_id, "snippet": snippet},
            ).execute()
            log.info(f"VOD title → {clean_title}")
    except Exception as e:
        log.warning(f"Could not update VOD title: {e}")

    # 2. Upload thumbnail (with text overlay)
    playlist = state.get("playlist", [])
    primary  = Path(playlist[0]) if playlist else None
    mood     = state.get("mood", "healing" if is_sd else "ambient")
    if primary:
        thumb = _sd_find_thumbnail(primary, queue_dir, mood) if is_sd else _find_thumbnail(primary, queue_dir)
    else:
        thumb = None
    if thumb and thumb.exists():
        try:
            from googleapiclient.http import MediaFileUpload
            dur_hours = state.get("duration_hours", "")
            dur_badge = f"{int(float(dur_hours))}H" if dur_hours else ""
            if is_sd:
                thumb_with_text = _make_sd_thumbnail(thumb, clean_title, mood, dur_badge or "VOD")
            else:
                thumb_with_text = _make_cnr_thumbnail(thumb, clean_title, mood, dur_badge or "VOD")
            yt.thumbnails().set(
                videoId=broadcast_id,
                media_body=MediaFileUpload(str(thumb_with_text), mimetype="image/png"),
            ).execute()
            log.info(f"VOD thumbnail → {thumb.name} (with text overlay)")
        except Exception as e:
            log.warning(f"Could not set thumbnail: {e}")
    else:
        log.info("No matching thumbnail found — YouTube keeps auto-generated frame")

    # 3. Localize VOD title + description (background subprocess — takes ~3-5 min)
    description = state.get("description", "")
    if description and broadcast_id:
        localize_script = ROOT / "scripts" / "localize_video.py"
        localize_log    = ROOT / "logs" / f"live_localize_{channel}.log"
        cmd = [
            sys.executable, str(localize_script),
            "--video-id",    broadcast_id,
            "--title",       clean_title,
            "--description", description,
            "--channel",     channel if channel in ("id", "sd") else "id",
        ]
        try:
            localize_log.parent.mkdir(exist_ok=True)
            with open(localize_log, "a") as lf:
                subprocess.Popen(
                    cmd, stdout=lf, stderr=lf,
                    start_new_session=True,
                )
            log.info(f"Localization started in background → {localize_log.name}")
        except Exception as e:
            log.warning(f"Could not start localization: {e}")
    else:
        log.info("No description in state — skipping localization")


FONT_TITLE   = "/usr/share/fonts/truetype/noto/NotoSerifDisplay-Regular.ttf"
FONT_CHANNEL = "/usr/share/fonts/truetype/noto/NotoSerif-Regular.ttf"
CHANNEL_BRAND = "Classical Night Relax"


def _escape_drawtext(text: str) -> str:
    """Escape special characters for ffmpeg drawtext filter."""
    return text.replace("\\", "\\\\").replace("'", "\\'").replace(":", "\\:").replace("%", "\\%")


def _drawtext_vf(now_playing_path: Path) -> str:
    """
    Build ffmpeg -vf string for a two-line overlay:
      Line 1 (large): current program title — read from file, refreshed every 60s
      Line 2 (small): channel brand name (static)
    Positioned in the lower third, centred, with semi-transparent black box.
    """
    np = str(now_playing_path).replace("'", "\\'").replace(":", "\\:")
    brand = _escape_drawtext(CHANNEL_BRAND)

    title_dt = (
        f"drawtext="
        f"fontfile={FONT_TITLE}:"
        f"textfile={np}:"
        f"reload=1800:"            # reload every 1800 frames = 60s at 30fps
        f"x=(w-text_w)/2:"
        f"y=h*0.87:"
        f"fontsize=42:"
        f"fontcolor=white@0.95:"
        f"box=1:boxcolor=black@0.50:boxborderw=18:"
        f"shadowcolor=black@0.60:shadowx=2:shadowy=2"
    )
    brand_dt = (
        f"drawtext="
        f"fontfile={FONT_CHANNEL}:"
        f"text='{brand}':"
        f"x=(w-text_w)/2:"
        f"y=h*0.87+60:"
        f"fontsize=26:"
        f"fontcolor=white@0.70:"
        f"shadowcolor=black@0.40:shadowx=1:shadowy=1"
    )
    return f"{title_dt},{brand_dt}"


def _start_now_playing_watcher(playlist: list[Path], durations: list[float],
                                now_playing_path: Path, log_path: Path) -> int:
    """
    Launch a background process that updates now_playing_path as the stream
    progresses through the playlist (recalculates every 30 seconds).
    Returns watcher PID.
    """
    import json as _json

    titles = []
    for v in playlist:
        title, _ = _classify(v.name)
        # Strip emoji prefix for display (keep text clean on screen)
        clean = title.lstrip("🌙🎵🌿✨🍂🌸🌊🔥💜❄️🦢 ").strip()
        titles.append(clean)

    watcher_data = _json.dumps({
        "titles":    titles,
        "durations": durations,
        "start_time": __import__("time").time(),
        "now_playing_path": str(now_playing_path),
    })

    # Inline watcher script — no external file dependency
    script = (
        "import time, json, sys; "
        "d = json.loads(sys.argv[1]); "
        "titles = d['titles']; durations = d['durations']; "
        "start = d['start_time']; npp = d['now_playing_path']; "
        "prev = None\n"
        "while True:\n"
        "    elapsed = time.time() - start; cum = 0; cur = titles[-1]\n"
        "    for t, dur in zip(titles, durations):\n"
        "        if elapsed < cum + dur: cur = t; break\n"
        "        cum += dur\n"
        "    if cur != prev:\n"
        "        open(npp, 'w').write(cur); prev = cur\n"
        "    time.sleep(30)\n"
    )

    proc = subprocess.Popen(
        ["python3", "-c", script, watcher_data],
        stdout=open(log_path, "ab"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    return proc.pid


# ── ffmpeg ────────────────────────────────────────────────────────────────────

def _start_ffmpeg(playlist_file: Path, rtmp_url: str,
                  now_playing_path: Path, log_path: Path) -> int:
    """Launch ffmpeg streaming process with on-screen track name overlay. Returns PID."""
    vf = _drawtext_vf(now_playing_path)
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "warning",
        "-fflags", "+genpts",          # regenerate timestamps at concat seams
        "-re",
        "-f", "concat", "-safe", "0",
        "-i", str(playlist_file),
        # Explicit stream mapping — required when -vf is used to keep audio
        "-map", "0:v:0",
        "-map", "0:a:0",
        # Overlay: programme title + channel brand
        "-vf", vf,
        # Video
        "-c:v", "libx264", "-preset", "ultrafast",
        "-b:v", "2500k", "-maxrate", "2500k", "-bufsize", "5000k",
        "-pix_fmt", "yuv420p",
        "-g", "60", "-r", "30",
        # Audio — async=1000 absorbs timestamp gaps between concat files
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-ac", "2",
        "-f", "flv", rtmp_url,
    ]
    log_fh = open(log_path, "ab")
    proc = subprocess.Popen(
        cmd,
        stdout=log_fh,
        stderr=subprocess.STDOUT,
        start_new_session=True,   # survive after this script exits
    )
    return proc.pid


# ── Commands ──────────────────────────────────────────────────────────────────

def _kill_ffmpeg(pid: int):
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            try:
                pgid = os.getpgid(pid)
                os.killpg(pgid, sig)
            except Exception:
                os.kill(pid, sig)
            log.info(f"ffmpeg PID {pid} terminated")
            return
        except ProcessLookupError:
            log.info("ffmpeg was already stopped")
            return
        except Exception as e:
            log.warning(f"Kill attempt ({sig}): {e}")


def _transition_to_live(yt, broadcast_id: str, stream_id: str, max_wait: int = 120) -> None:
    """Wait for RTMP stream to become active, then transition broadcast ready→testing→live."""
    import time as _time
    deadline = _time.time() + max_wait
    while _time.time() < deadline:
        try:
            r = yt.liveStreams().list(part="status", id=stream_id).execute()
            if r.get("items") and r["items"][0]["status"]["streamStatus"] == "active":
                break
        except Exception:
            pass
        _time.sleep(5)
    else:
        log.warning("Stream did not become active in time — attempting transition anyway")

    for status in ("testing", "live"):
        for attempt in range(3):
            try:
                r = yt.liveBroadcasts().transition(
                    broadcastStatus=status, id=broadcast_id, part="id,status"
                ).execute()
                log.info(f"Broadcast {broadcast_id} → {r['status']['lifeCycleStatus']}")
                _time.sleep(5)
                break
            except Exception as e:
                err = str(e)
                if "invalidTransition" in err:
                    # Already in this state or can skip — continue to next
                    log.info(f"Transition to {status} skipped (already past): {e}")
                    break
                log.warning(f"Transition to {status} attempt {attempt+1}: {e}")
                _time.sleep(5)


def cmd_start(args):
    channel   = args.channel
    slot      = args.slot
    queue_dir = CHANNEL_QUEUE.get(channel)
    if not queue_dir:
        log.error(f"Unknown channel: {channel}")
        sys.exit(1)

    slot_cfg = SLOT_CONFIG[slot]
    save_vod = slot_cfg["save_vod"]
    LOGS_DIR.mkdir(exist_ok=True)

    # Idempotency: skip if ffmpeg already running for this slot
    sf = _state_file(channel, slot)
    state = _load_json(sf, {})
    if state.get("ffmpeg_pid"):
        pid = state["ffmpeg_pid"]
        try:
            os.kill(pid, 0)
            log.info(f"[{slot}] Stream already running (PID {pid}). Nothing to do.")
            return
        except ProcessLookupError:
            log.warning(f"[{slot}] Stale state — cleaning up")
            sf.unlink(missing_ok=True)
            state = {}

    # Select content (separate history per slot → independent rotation)
    history  = _load_json(_history_file(channel, slot), [])
    mood     = args.mood if args.mood != "auto" else slot_cfg["mood"]
    is_sd    = (channel == "sd")
    log.info(f"[{slot}] Building playlist (channel={channel}, target={STREAM_TARGET_HOURS}h, save_vod={save_vod})...")

    if is_sd:
        theme_arg = mood if mood in SD_THEME_WEIGHTS else "auto"
        playlist, active_theme = _sd_pick_playlist(queue_dir, history, STREAM_TARGET_HOURS, theme_arg)
        theme_display, primary_mood = SD_THEME_DISPLAY[active_theme]
        stream_title = f"{SD_LIVE_PREFIX}{theme_display}{SD_CHAN_SUFFIX}"
        description  = _sd_build_description(playlist, primary_mood)
    else:
        playlist = _pick_playlist(queue_dir, history, STREAM_TARGET_HOURS, mood)
    if not playlist:
        log.error("No long-form videos in queue.")
        sys.exit(1)

    if not is_sd:
        primary_title, primary_mood = _classify(playlist[0].name)
        stream_title = f"{LIVE_PREFIX}{primary_title}{CHAN_SUFFIX}"
        description  = _build_description(playlist, primary_mood)

    durations = [_get_duration(v) for v in playlist]
    total_h   = sum(durations) / 3600
    log.info(f"Title: {stream_title}")
    log.info(f"Playlist: {len(playlist)} videos, ~{total_h:.1f}h")
    for v, d in zip(playlist, durations):
        log.info(f"  [{d/3600:.1f}h] {v.name}")

    # Write concat playlist
    pf = _playlist_file(channel, slot)
    _build_concat_file(playlist, pf)

    # Write initial now-playing text (first program title, stripped of emoji)
    np_file = _now_playing_file(channel, slot)
    first_title = primary_title
    np_file.write_text(first_title.lstrip("🌙🎵🌿✨🍂🌸🌊🔥💜❄️🦢😴🔮🌈👁🔔🧘🌌🎹🏔️🌅💚 ").strip())

    # YouTube API
    log.info("Connecting to YouTube API...")
    yt = _get_youtube(channel)

    # Reuse pre-scheduled broadcast if available (created 1h before by cmd_schedule)
    sched_file = _scheduled_file(channel, slot)
    sched = _load_json(sched_file, {})
    if sched.get("broadcast_id"):
        try:
            r = yt.liveBroadcasts().list(part="status", id=sched["broadcast_id"]).execute()
            if r.get("items") and r["items"][0]["status"]["lifeCycleStatus"] in ("ready", "created"):
                broadcast_id = sched["broadcast_id"]
                stream_id    = sched["stream_id"]
                rtmp_data    = _load_json(_rtmp_file(channel), {})
                rtmp_url     = rtmp_data.get("rtmp_url", "")
                log.info(f"Reusing pre-scheduled broadcast {broadcast_id}")
                sched_file.unlink(missing_ok=True)
            else:
                raise ValueError("scheduled broadcast no longer ready")
        except Exception as e:
            log.warning(f"Cannot reuse scheduled broadcast: {e} — creating new one")
            sched_file.unlink(missing_ok=True)
            sched = {}

    if not sched.get("broadcast_id"):
        stream_id, rtmp_url = _get_or_create_rtmp_stream(yt, channel)
        broadcast_id = _create_broadcast(yt, stream_title, description, save_vod=save_vod)
        yt.liveBroadcasts().bind(
            id=broadcast_id, part="id,contentDetails", streamId=stream_id,
        ).execute()
        log.info(f"Broadcast {broadcast_id} → stream {stream_id} (save_vod={save_vod})")

        # Set thumbnail immediately so live preview shows the correct image
        if is_sd:
            thumb = _sd_find_thumbnail(playlist[0], CHANNEL_QUEUE[channel], primary_mood)
        else:
            thumb = _find_thumbnail(playlist[0], CHANNEL_QUEUE[channel])
        if thumb and thumb.exists():
            try:
                from googleapiclient.http import MediaFileUpload
                if is_sd:
                    thumb_with_text = _make_sd_thumbnail(thumb, stream_title, primary_mood, "LIVE")
                else:
                    thumb_with_text = _make_cnr_thumbnail(thumb, stream_title, primary_mood, "LIVE")
                yt.thumbnails().set(
                    videoId=broadcast_id,
                    media_body=MediaFileUpload(str(thumb_with_text), mimetype="image/png"),
                ).execute()
                log.info(f"Thumbnail set: {thumb.name} (with text overlay)")
            except Exception as e:
                log.warning(f"Could not set thumbnail at start: {e}")
        else:
            log.warning("No thumbnail found — YouTube will use auto-generated frame")

    # Validate playlist: remove any files that are missing or corrupt
    removed = _validate_playlist_file(pf)
    if removed:
        log.warning(f"Playlist cleaned before start: {removed} invalid file(s) removed")
        # Reload playlist from the cleaned file
        playlist = [Path(l[6:].rstrip("'")) for l in pf.read_text().splitlines()
                    if l.strip().startswith("file '")]
        durations = [_get_duration(v) for v in playlist]
    if not playlist:
        log.error("Playlist is empty after validation — cannot start stream")
        return

    # Start now-playing watcher (updates on-screen title as playlist progresses)
    watcher_pid = _start_now_playing_watcher(playlist, durations, np_file, _ffmpeg_log(channel, slot))
    log.info(f"Now-playing watcher PID {watcher_pid}")

    # Start ffmpeg with on-screen overlay
    pid = _start_ffmpeg(pf, rtmp_url, np_file, _ffmpeg_log(channel, slot))
    log.info(f"ffmpeg PID {pid} — transitioning broadcast to live...")

    # Wait for stream to be ingesting, then manually transition to live
    _transition_to_live(yt, broadcast_id, stream_id)

    _save_json(sf, {
        "channel":       channel,
        "slot":          slot,
        "save_vod":      save_vod,
        "broadcast_id":  broadcast_id,
        "stream_id":     stream_id,
        "ffmpeg_pid":    pid,
        "watcher_pid":   watcher_pid,
        "started_at":    datetime.now(timezone.utc).isoformat(),
        "stream_title":  stream_title,
        "description":   description,
        "mood":          primary_mood,
        "playlist":      [str(p) for p in playlist],
        "durations":     durations,
    })
    log.info(f"State → {sf}")


def cmd_stop(args):
    channel = args.channel
    slot    = args.slot
    sf      = _state_file(channel, slot)
    state   = _load_json(sf, {})

    if not state:
        log.info(f"[{slot}] No active stream.")
        return

    broadcast_id = state.get("broadcast_id")
    save_vod     = state.get("save_vod", True)

    # 1. Transition broadcast to complete (enableAutoStop also handles this, but be explicit)
    if broadcast_id:
        try:
            yt = _get_youtube(channel)
            yt.liveBroadcasts().transition(
                broadcastStatus="complete",
                id=broadcast_id,
                part="id,status",
            ).execute()
            if save_vod:
                log.info(f"Broadcast {broadcast_id} → complete  ✓ VOD will appear shortly")
            else:
                log.info(f"Broadcast {broadcast_id} → complete  (no VOD — recordFromStart=false)")
        except Exception as e:
            log.warning(f"Transition failed: {e}")

    # 2. Kill ffmpeg + now-playing watcher
    for pid_key in ("ffmpeg_pid", "watcher_pid"):
        pid = state.get(pid_key)
        if pid:
            _kill_ffmpeg(pid)

    # 3. Post-process VOD: clean title + upload thumbnail
    if broadcast_id and save_vod:
        try:
            queue_dir = CHANNEL_QUEUE[channel]
            _post_process_vod(yt, broadcast_id, state, queue_dir, channel)
        except Exception as e:
            log.warning(f"VOD post-processing failed: {e}")

    # 4. History (per slot)
    history = _load_json(_history_file(channel, slot), [])
    history.append({
        "slot":         slot,
        "save_vod":     save_vod,
        "broadcast_id": broadcast_id,
        "started_at":   state.get("started_at"),
        "stopped_at":   datetime.now(timezone.utc).isoformat(),
        "stream_title": state.get("stream_title"),
        "mood":         state.get("mood"),
        "playlist":     state.get("playlist", []),
    })
    _save_json(_history_file(channel, slot), history[-60:])

    sf.unlink(missing_ok=True)
    log.info(f"[{slot}] Stream stopped.")


def cmd_status(args):
    channel = args.channel
    slots   = list(SLOT_CONFIG.keys()) if args.slot == "all" else [args.slot]

    for slot in slots:
        state = _load_json(_state_file(channel, slot), {})
        print(f"\n═══ Slot: {slot.upper()} ({SLOT_CONFIG[slot]['start_cron']} → {SLOT_CONFIG[slot]['stop_cron']} UTC) ═══")
        if not state:
            print("  No active stream.")
        else:
            pid   = state.get("ffmpeg_pid", 0)
            alive = False
            try:
                os.kill(pid, 0); alive = True
            except (ProcessLookupError, ValueError):
                pass
            sv = "✓ saved as VOD" if state.get("save_vod") else "✗ not saved (ephemeral)"
            print(f"  Broadcast:  {state.get('broadcast_id')}  [{sv}]")
            print(f"  ffmpeg:     PID {pid} ({'✓ running' if alive else '✗ DEAD'})")
            print(f"  Started:    {state.get('started_at','?')[:19]} UTC")
            print(f"  Title:      {state.get('stream_title','?')[:80]}")
            playlist = state.get("playlist", [])
            print(f"  Playlist:   {len(playlist)} videos")
            for p in playlist[:4]:
                print(f"    • {Path(p).name}")
            if len(playlist) > 4:
                print(f"    … and {len(playlist)-4} more")

        history = _load_json(_history_file(channel, slot), [])
        if history:
            print(f"  History ({len(history)} total, last 3):")
            for h in history[-3:]:
                dt = h.get("stopped_at", h.get("started_at","?"))[:10]
                sv = "VOD" if h.get("save_vod") else "ephemeral"
                print(f"    {dt}  [{sv}]  {h.get('stream_title','?')[:60]}")


def _scheduled_file(channel: str, slot: str) -> Path:
    return LOGS_DIR / f"live_scheduled_{channel}_{slot}.json"


def cmd_schedule(args):
    """
    Pre-create the YouTube broadcast 1h before stream time so viewers see 'upcoming'.
    Saves broadcast_id to live_scheduled_<ch>_<slot>.json.
    cmd_start reuses this broadcast instead of creating a new one.
    """
    channel   = args.channel
    slot      = args.slot
    queue_dir = CHANNEL_QUEUE.get(channel)
    slot_cfg  = SLOT_CONFIG[slot]
    save_vod  = slot_cfg["save_vod"]

    sf = _scheduled_file(channel, slot)
    existing = _load_json(sf, {})
    if existing.get("broadcast_id"):
        # Verify it still exists on YouTube
        try:
            yt = _get_youtube(channel)
            r = yt.liveBroadcasts().list(
                part="status", id=existing["broadcast_id"],
            ).execute()
            if r.get("items"):
                status = r["items"][0]["status"]["lifeCycleStatus"]
                if status in ("ready", "created"):
                    log.info(f"[{slot}] Scheduled broadcast already exists: {existing['broadcast_id']} ({status})")
                    return
        except Exception:
            pass
        sf.unlink(missing_ok=True)

    # Compute next slot start time (today or tomorrow)
    start_hour = int(slot_cfg["start_cron"].split()[1])   # e.g. 20 for EU, 7 for US
    now = datetime.now(timezone.utc)
    next_start = now.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    if next_start <= now:
        elapsed_sec = (now - next_start).total_seconds()
        if elapsed_sec < 4 * 3600:
            # We're running late but still within the stream window — start in 2 min
            next_start = now + timedelta(minutes=2)
        else:
            next_start += timedelta(days=1)
    start_iso = next_start.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    history  = _load_json(_history_file(channel, slot), [])
    is_sd    = (channel == "sd")
    if is_sd:
        playlist, active_theme = _sd_pick_playlist(queue_dir, history, STREAM_TARGET_HOURS, "auto")
        theme_display, primary_mood = SD_THEME_DISPLAY[active_theme]
        stream_title = f"{SD_LIVE_PREFIX}{theme_display}{SD_CHAN_SUFFIX}"
        description  = _sd_build_description(playlist, primary_mood)
    else:
        mood     = slot_cfg["mood"]
        playlist = _pick_playlist(queue_dir, history, STREAM_TARGET_HOURS, mood)
        primary_title, primary_mood = _classify(playlist[0].name)
        stream_title = f"{LIVE_PREFIX}{primary_title}{CHAN_SUFFIX}"
        description  = _build_description(playlist, primary_mood)
    if not playlist:
        log.error("No videos in queue — cannot schedule")
        return

    log.info(f"[{slot}] Scheduling broadcast for {start_iso}: {stream_title[:60]}")
    yt = _get_youtube(channel)

    # Create broadcast with correct future start time
    broadcast = yt.liveBroadcasts().insert(
        part="snippet,status,contentDetails",
        body={
            "snippet": {
                "title": stream_title[:100],
                "description": description,
                "scheduledStartTime": start_iso,
                "categoryId": "10",
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False,
            },
            "contentDetails": {
                "enableAutoStart":   False,    # we transition manually at start time
                "enableAutoStop":    True,
                "enableDvr":         save_vod,
                "recordFromStart":   save_vod,
                "latencyPreference": "normal",
                "monitorStream":     {"enableMonitorStream": True, "broadcastStreamDelayMs": 0},
            },
        },
    ).execute()
    broadcast_id = broadcast["id"]

    stream_id, _ = _get_or_create_rtmp_stream(yt, channel)
    yt.liveBroadcasts().bind(
        id=broadcast_id, part="id,contentDetails", streamId=stream_id,
    ).execute()

    # Set thumbnail now so it shows in upcoming section
    if is_sd:
        thumb = _sd_find_thumbnail(playlist[0], queue_dir, primary_mood)
    else:
        thumb = _find_thumbnail(playlist[0], queue_dir)
    if thumb and thumb.exists():
        try:
            from googleapiclient.http import MediaFileUpload
            if is_sd:
                thumb_with_text = _make_sd_thumbnail(thumb, stream_title, primary_mood, "LIVE")
            else:
                thumb_with_text = _make_cnr_thumbnail(thumb, stream_title, primary_mood, "LIVE")
            yt.thumbnails().set(
                videoId=broadcast_id,
                media_body=MediaFileUpload(str(thumb_with_text), mimetype="image/png"),
            ).execute()
            log.info(f"Thumbnail set: {thumb.name} (with text overlay)")
        except Exception as e:
            log.warning(f"Thumbnail failed: {e}")

    _save_json(sf, {
        "broadcast_id":  broadcast_id,
        "stream_id":     stream_id,
        "stream_title":  stream_title,
        "description":   description,
        "scheduled_for": start_iso,
        "playlist":      [str(p) for p in playlist],
        "mood":          primary_mood,
    })
    log.info(f"[{slot}] Scheduled broadcast {broadcast_id} → {start_iso}")
    log.info(f"[{slot}] Saved to {sf.name}")


def cmd_install_cron(args):
    """Install all 4 cron jobs: EU start/stop + US start/stop."""
    channel = args.channel
    script  = str(ROOT / "scripts" / "live_stream.py")
    clog    = str(_cron_log(channel))

    # Schedule crons fire 1 hour before stream start so "upcoming" shows on YouTube
    SCHEDULE_OFFSET = {
        "eu": "0 19 * * *",   # 1h before 20:00 UTC
        "us": "0 6  * * *",   # 1h before 07:00 UTC (same minute as EU stop — sequential, fine)
    }
    new_jobs = []
    for slot, cfg in SLOT_CONFIG.items():
        new_jobs.append(
            f"{SCHEDULE_OFFSET[slot]}  cd {ROOT} && python3 {script} schedule"
            f" --channel {channel} --slot {slot} >> {clog} 2>&1"
        )
        new_jobs.append(
            f"{cfg['start_cron']}  cd {ROOT} && python3 {script} start"
            f" --channel {channel} --slot {slot} >> {clog} 2>&1"
        )
        new_jobs.append(
            f"{cfg['stop_cron']}  cd {ROOT} && python3 {script} stop"
            f"  --channel {channel} --slot {slot} >> {clog} 2>&1"
        )

    try:
        current = subprocess.check_output(
            ["crontab", "-l"], text=True, stderr=subprocess.DEVNULL
        )
    except subprocess.CalledProcessError:
        current = ""

    # Remove old live_stream.py jobs for this channel
    lines = [ln for ln in current.splitlines()
             if not ("live_stream.py" in ln and f"--channel {channel}" in ln)]
    lines += new_jobs
    new_crontab = "\n".join(lines) + "\n"

    result = subprocess.run(["crontab", "-"], input=new_crontab, text=True)
    if result.returncode == 0:
        log.info(f"Installed {len(new_jobs)} cron jobs:")
        for j in new_jobs:
            log.info(f"  {j}")
    else:
        log.error("crontab update failed — edit manually with 'crontab -e'")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    _setup_logging()
    parser = argparse.ArgumentParser(description="Calm Classics live stream manager")
    sub    = parser.add_subparsers(dest="command", required=True)

    for cmd_name in ("start", "stop", "status", "schedule", "install-cron"):
        p = sub.add_parser(cmd_name)
        p.add_argument("--channel", default="id", choices=list(CHANNEL_TOKENS.keys()))
        if cmd_name in ("start", "stop", "schedule"):
            p.add_argument("--slot", default="eu", choices=list(SLOT_CONFIG.keys()),
                           help="eu = Europe 20:00–06:00 UTC | us = Americas 07:00–14:00 UTC")
        elif cmd_name == "status":
            p.add_argument("--slot", default="all", choices=list(SLOT_CONFIG.keys()) + ["all"])
        if cmd_name == "start":
            p.add_argument("--mood", default="auto",
                           choices=["auto", "sleep", "focus", "ambient", "healing", "nature", "any"],
                           help="Content mood. 'auto' uses slot default. SD moods: sleep/healing/nature")

    args = parser.parse_args()
    {"start": cmd_start, "stop": cmd_stop, "status": cmd_status,
     "schedule": cmd_schedule, "install-cron": cmd_install_cron}[args.command](args)


if __name__ == "__main__":
    main()
