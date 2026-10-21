#!/usr/bin/env python3
"""
Restore all archived SD sound design videos and give each a unique, SEO-friendly title.
Removes the ugly _N suffix and replaces with a poetic subtitle unique per video.
"""
import re, shutil
from pathlib import Path
from collections import defaultdict
import yaml

QUEUE   = Path("/opt/kids_channel/sacred_drift/output/queue")
ARCHIVE = Path("/opt/kids_channel/sacred_drift/output/queue_archived_sd_shorts")

# ── unique subtitles per theme ────────────────────────────────────────────────
SUBTITLES = {
    "glacier_ice_cave": [
        "Arctic Silence", "Frozen Depths", "Crystal Echoes", "Deep Freeze",
        "Polar Night", "Ice Cathedral", "Glacial Drift", "Subzero Stillness",
        "Permafrost Veil", "Blue Ice Chamber", "Crevasse Depths", "Eternal Winter",
        "Snowfield Zen", "Arctic Dawn", "Frozen Void", "Ice Crystal Halls",
        "Polar Solitude", "Midnight Glacier", "Tundra Silence", "Glacial Waters",
        "Winter Zenith", "Arctic Hollow", "Frozen Temple", "Ice Labyrinth",
        "Polar Fog", "Crystal Cave", "Arctic Wind", "Frozen Light",
        "Ice Monastery", "Polar Drift", "Glacial Tone", "Winter Stillness",
        "Arctic Dream", "Frozen Horizon", "Ice Sanctuary", "Polar Calm",
        "Glacial Breath", "Winter Abyss", "Arctic Resonance", "Frozen Flow",
        "Ice Meditation", "Polar Rest", "Glacial Peace", "Frost Veil",
        "Arctic Glow", "Ice Whispers", "Frozen Shore", "Polar Haze",
        "Crystal Silence", "Arctic Path", "Glacial Echo", "Ice Dawn",
        "Polar Song", "Frozen Mist", "Arctic Still", "Ice Harmony",
        "Polar Serenity", "Glacial Light", "Winter Calm", "Arctic Stone",
        "Frozen Pulse", "Ice Clarity", "Polar Depth", "Glacial Rest",
        "Winter Peace", "Arctic Tone",
    ],
    "distant_waterfall": [
        "Hidden Falls", "Mountain Cascade", "Mist and Stone", "Ancient Stream",
        "Forest Falls", "Sacred Waters", "Valley Cascade", "Misty Descent",
        "Rock and Water", "Eternal Falls", "Mountain Mist", "Jungle Cascade",
    ],
    "desert_night_wind": [
        "Sahara Night", "Dune Silence", "Desert Stars", "Midnight Sand",
        "Dry Wind", "Ancient Desert", "Nomad Rest", "Desert Void",
        "Oasis Night", "Desert Stillness",
    ],
    "cosmic_drone_meditation": [
        "Stellar Void", "Nebula Drift", "Dark Matter", "Cosmic Stillness",
        "Star Field", "Interstellar Rest",
    ],
    "bamboo_forest_wind": [
        "Morning Bamboo", "Wind Through Reeds", "Jade Forest",
        "Bamboo Zen", "Forest Wind", "Bamboo Temple",
    ],
    "monastery_bell_at_dawn": [
        "First Bell", "Dawn Call", "Temple Morning", "Bell Silence",
        "Sacred Dawn", "Morning Toll", "Monastery Mist", "Bell at Sunrise",
    ],
    "mountain_lake_at_dawn": [
        "Still Water", "Glass Lake", "Dawn Reflection", "Mist on Water",
        "Lakeside Calm", "First Light",
    ],
    "rainforest_at_night": [
        "Night Canopy", "Jungle Rain", "Forest Dark", "Night Birds",
        "Humid Stillness", "Rainforest Moon",
    ],
    "underwater_ocean_depths": [
        "Deep Blue", "Ocean Floor", "Silent Depths", "Abyssal Calm",
        "Coral Stillness", "Deep Current",
    ],
    "zen_garden_raked_gravel": [
        "Stone and Sand", "Raked Path", "Gravel Silence", "Garden Mind",
        "Zen Stone", "Still Garden",
    ],
    "shamanic_cave_drum": [
        "Earth Beat", "Cave Rhythm", "Drum Trance", "Shamanic Pulse",
    ],
    "winter_forest_silence": [
        "Snow Canopy", "Frozen Forest", "Winter Hush", "Snowfall Calm",
    ],
    "crown_chakra_963hz": ["Crown Activation", "Pure Frequency"],
    "gong_bath":           ["Resonant Bowl", "Gong Waves"],
    "rain_on_stone_temple":["Stone Temple Rain", "Monsoon Stillness"],
    "third_eye_852hz":     ["Third Eye Opening", "Indigo Frequency"],
    "fireplace_at_night":  ["Ember Glow", "Night Fire"],
    "glacier_block":       ["Ice Monolith"],
}

# ── SEO-friendly base title per theme ─────────────────────────────────────────
BASE_TITLE = {
    "glacier_ice_cave":          "Glacier Ice Cave Meditation",
    "distant_waterfall":         "Distant Waterfall Meditation",
    "desert_night_wind":         "Desert Night Wind Meditation",
    "cosmic_drone_meditation":   "Cosmic Drone Meditation",
    "bamboo_forest_wind":        "Bamboo Forest Wind Meditation",
    "monastery_bell_at_dawn":    "Monastery Bell at Dawn",
    "mountain_lake_at_dawn":     "Mountain Lake at Dawn",
    "rainforest_at_night":       "Rainforest at Night",
    "underwater_ocean_depths":   "Underwater Ocean Depths",
    "zen_garden_raked_gravel":   "Zen Garden Meditation",
    "shamanic_cave_drum":        "Shamanic Cave Drum",
    "winter_forest_silence":     "Winter Forest Silence",
    "crown_chakra_963hz":        "Crown Chakra 963Hz",
    "gong_bath":                 "Gong Bath Meditation",
    "rain_on_stone_temple":      "Rain on Stone Temple",
    "third_eye_852hz":           "Third Eye 852Hz",
    "fireplace_at_night":        "Fireplace at Night",
    "glacier_block":             "Glacier Ice Block",
}

# ── collect all files from queue + archive ────────────────────────────────────
all_mp4 = defaultdict(list)
for f in sorted(list(QUEUE.glob("*.mp4")) + list(ARCHIVE.glob("*.mp4"))):
    n = f.name
    if n.startswith("sd_sound_design_") or n.startswith("sd_short_sound_design_"):
        stem = f.stem
        theme_key = re.sub(r'_\d{8}$', '', stem)
        theme_key = re.sub(r'_\d+$', '', theme_key)
        # strip prefix to get bare theme name
        bare = theme_key.replace("sd_short_sound_design_", "").replace("sd_sound_design_", "").lstrip("_")
        all_mp4[bare].append(f)

moved = 0
renamed = 0
skipped = 0

for bare_theme, files in sorted(all_mp4.items()):
    subtitles = SUBTITLES.get(bare_theme, [])
    base = BASE_TITLE.get(bare_theme, bare_theme.replace("_", " ").title())

    for idx, mp4 in enumerate(files):
        subtitle = subtitles[idx] if idx < len(subtitles) else f"Variation {idx+1}"
        stem = mp4.stem

        # duration label from meta
        meta_src = mp4.parent / f"meta_{stem}.yaml"
        if not meta_src.exists():
            print(f"  SKIP (no meta): {mp4.name}")
            skipped += 1
            continue

        meta = yaml.safe_load(meta_src.read_text())
        dur_sec = meta.get("duration_sec", 0)
        if dur_sec >= 3600:
            dur_label = f"{dur_sec//3600} Hour"
        elif dur_sec >= 60:
            dur_label = f"{dur_sec//60} Min"
        else:
            dur_label = f"{dur_sec} Sec"

        new_title = f"{base} — {subtitle} 🔮 {dur_label} | Sacred Drift"
        old_title = meta.get("title", "")

        meta["title"] = new_title
        meta["track_name"] = f"{base} — {subtitle}"

        # update localizations: just update title field in each lang
        for lang, loc in meta.get("localizations", {}).items():
            if "title" in loc:
                # keep language-translated base, append English subtitle
                old_loc_title = loc["title"]
                # replace the _N pattern
                loc["title"] = re.sub(r'_\d+\b', f' — {subtitle}', old_loc_title)
                if "_" + str(idx) not in old_loc_title and "_\d" not in old_loc_title:
                    # fallback: just append subtitle
                    loc["title"] = re.sub(r'\s*🔮.*', f' — {subtitle} 🔮 {dur_label} | Sacred Drift', old_loc_title)

        # move mp4 + meta + thumb to queue if in archive
        for ext_name, src_file in [
            (f"{stem}.mp4",       mp4),
            (f"meta_{stem}.yaml", meta_src),
            (f"thumb_{stem}.png", mp4.parent / f"thumb_{stem}.png"),
        ]:
            if src_file.parent == ARCHIVE:
                dst = QUEUE / ext_name
                if src_file.exists():
                    shutil.move(str(src_file), str(dst))
                    moved += 1
                    if ext_name.endswith(".yaml"):
                        src_file = dst  # write to new location

        # write updated meta (always to queue)
        meta_dst = QUEUE / f"meta_{stem}.yaml"
        meta_dst.write_text(yaml.dump(meta, allow_unicode=True,
                                       default_flow_style=False, sort_keys=False))
        renamed += 1
        print(f"  ✓ {new_title[:70]}")

print(f"\n移動: {moved} файлов из архива → queue")
print(f"Переименовано: {renamed} мета-файлов")
print(f"Пропущено: {skipped}")
