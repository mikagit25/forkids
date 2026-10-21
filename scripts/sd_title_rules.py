"""
Sacred Drift — title formatting rules (single source of truth).

SHORT VIDEOS (is_short=True, ≤ 3 min):
    Format : {Theme} — {Subtitle} 🎵 {Keywords} #Shorts
    Example: Glacier Ice Cave — Arctic Silence 🎵 Ambient Sounds #Shorts
    Rules  :
      - NO duration (YouTube shows it automatically on the card)
      - NO channel name (channel is visible under the video)
      - Theme: clean display name, no "Sound Design:" prefix, no _N suffix
      - Subtitle: unique poetic word/phrase per video
      - Keywords: 1-2 real search terms people type (not brand terms)
      - #Shorts: always at the end — helps YouTube classify the video

LONG VIDEOS (is_short=False, ≥ 1 hour):
    Format : {Theme} • {N Hours}
    Example: Tibetan Singing Bowls Meditation 🔔 • 1 Hour
    Rules  :
      - NO channel name suffix ("| Sacred Drift" etc.)
      - NO subtitle after the duration (keep it clean and searchable)
      - Duration rounded to nearest hour (1 Hour, 2 Hours — never "1 Hour 2 Min")
      - Emoji in theme name is fine, but only one
"""

import re

# Keywords per theme — what people actually search for
THEME_KEYWORDS = {
    "glacier_ice_cave":          "Ambient Sounds",
    "distant_waterfall":         "Nature Sounds",
    "desert_night_wind":         "Sleep Sounds",
    "cosmic_drone_meditation":   "Space Ambient",
    "bamboo_forest_wind":        "Nature Sounds",
    "monastery_bell_at_dawn":    "Zen Meditation",
    "mountain_lake_at_dawn":     "Nature Sounds",
    "rainforest_at_night":       "Rain ASMR",
    "underwater_ocean_depths":   "Ocean Sounds",
    "zen_garden_raked_gravel":   "Zen Meditation",
    "shamanic_cave_drum":        "Tribal Meditation",
    "winter_forest_silence":     "Sleep Sounds",
    "crown_chakra_963hz":        "Sound Healing",
    "gong_bath":                 "Sound Bath",
    "rain_on_stone_temple":      "Rain Sounds",
    "third_eye_852hz":           "Sound Healing",
    "fireplace_at_night":        "Relaxing Sounds",
    "glacier_block":             "Ambient Sounds",
    # fire ambient
    "campfire":                  "Fire Ambience",
    "candle":                    "Relaxing Sounds",
    "fireplace":                 "Relaxing Sounds",
    "fire_closeup":              "Fire Ambience",
    # procedural styles
    "tibetan_bowls":             "Meditation Music",
    "cosmic_space":              "Space Ambient",
    "deep_sleep":                "Sleep Music",
    "solfeggio":                 "Sound Healing",
    "rain_water":                "Rain Sounds",
    "morning_yoga":              "Meditation Music",
}

# Clean display names (no "Sound Design:" prefix, no technical suffixes)
THEME_DISPLAY = {
    "glacier_ice_cave":          "Glacier Ice Cave",
    "distant_waterfall":         "Distant Waterfall",
    "desert_night_wind":         "Desert Night Wind",
    "cosmic_drone_meditation":   "Cosmic Drone",
    "bamboo_forest_wind":        "Bamboo Forest Wind",
    "monastery_bell_at_dawn":    "Monastery Bell at Dawn",
    "mountain_lake_at_dawn":     "Mountain Lake at Dawn",
    "rainforest_at_night":       "Rainforest at Night",
    "underwater_ocean_depths":   "Underwater Ocean Depths",
    "zen_garden_raked_gravel":   "Zen Garden",
    "shamanic_cave_drum":        "Shamanic Cave Drum",
    "winter_forest_silence":     "Winter Forest Silence",
    "crown_chakra_963hz":        "Crown Chakra 963Hz",
    "gong_bath":                 "Gong Bath",
    "rain_on_stone_temple":      "Rain on Stone Temple",
    "third_eye_852hz":           "Third Eye 852Hz",
    "fireplace_at_night":        "Fireplace at Night",
    "glacier_block":             "Glacier Ice Block",
}


def format_short_title(theme: str, subtitle: str) -> str:
    """
    Format a YouTube Shorts title.
      theme    : bare theme key (e.g. 'glacier_ice_cave') OR a free-form display name
      subtitle : unique descriptor for this specific video (e.g. 'Arctic Silence')
    Returns: 'Theme — Subtitle 🎵 Keywords #Shorts'
    """
    display = THEME_DISPLAY.get(theme, _clean_display(theme))
    keywords = THEME_KEYWORDS.get(theme, "Meditation Sounds")
    return f"{display} — {subtitle} 🎵 {keywords} #Shorts"


def format_long_title(theme: str, duration_sec: int) -> str:
    """
    Format a long-form YouTube video title.
      theme        : bare theme key or free-form display name
      duration_sec : total duration in seconds (rounded to nearest hour)
    Returns: 'Theme • N Hours'  (or '• 1 Hour')
    """
    display = THEME_DISPLAY.get(theme, _clean_display(theme))
    hours = max(1, round(duration_sec / 3600))
    dur_label = "1 Hour" if hours == 1 else f"{hours} Hours"
    return f"{display} • {dur_label}"


def strip_channel_suffix(title: str) -> str:
    """Remove '| Channel Name' or '| Sacred Drift' from any title."""
    return re.sub(r'\s*\|\s*[\w\s]+$', '', title).strip()


def _clean_display(raw: str) -> str:
    """Fallback: convert snake_case or 'Sound Design X_10' to Title Case."""
    s = re.sub(r'^sound design[:\s]+', '', raw, flags=re.IGNORECASE)
    s = re.sub(r'_\d+$', '', s)
    return s.replace('_', ' ').title()
