#!/bin/bash
# CNR Soundscape batch render — nature ambient themes from Suno AI
# Run sequentially to avoid OOM (15GB RAM server)
set -e
cd /opt/kids_channel
LOG=logs/soundscape_renders.log
exec >> "$LOG" 2>&1

run_theme() {
    local theme="$1"
    echo ""
    echo "--- $theme --- $(date)"
    python3 scripts/make_visual_theme.py --theme "$theme" --durations 1 3
    echo "--- $theme DONE --- $(date)"
}

echo "=============================="
echo "Soundscape batch start: $(date)"
echo "=============================="

run_theme rainforest_night
run_theme mountain_lake_dawn
run_theme desert_night_wind
run_theme winter_forest_silence
run_theme ambient_meditation_mix

echo ""
echo "=============================="
echo "ALL SOUNDSCAPES DONE: $(date)"
echo "=============================="
