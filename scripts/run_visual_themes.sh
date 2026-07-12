#!/usr/bin/env bash
# Sequential generation of all 8 AI visual theme videos for Calm Classics.
# Generates 1h + 3h versions per theme (8 themes × 2 durations = 16 videos).
# Runs sequentially to avoid OOM on 15GB RAM server.
#
# Usage:
#   bash scripts/run_visual_themes.sh            # all themes, 1h+3h
#   bash scripts/run_visual_themes.sh --single aurora_borealis
set -e
cd /opt/kids_channel
LOG=logs/visual_themes.log
mkdir -p logs

run() {
    local theme=$1
    echo "[$(date '+%H:%M:%S')] Theme: $theme" | tee -a $LOG
    python3 scripts/make_visual_theme.py --theme "$theme" --durations 1 3 \
        >> $LOG 2>&1 \
        && echo "  OK: $theme" | tee -a $LOG \
        || echo "  FAILED: $theme" | tee -a $LOG
}

if [[ "$1" == "--single" && -n "$2" ]]; then
    echo "=== Single theme: $2 $(date) ===" | tee -a $LOG
    run "$2"
    echo "=== Done $(date) ===" | tee -a $LOG
    exit 0
fi

echo "=== Visual themes batch started $(date) ===" | tee -a $LOG

# Sleep themes (ordered by expected viewer appeal)
run aurora_borealis
run cherry_blossoms
run fireplace_cabin
run lavender_fields
run autumn_forest
run mountain_snow
run deep_space
run zen_garden

echo "=== Visual themes batch complete $(date) ===" | tee -a $LOG
