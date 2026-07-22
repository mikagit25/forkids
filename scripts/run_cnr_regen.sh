#!/usr/bin/env bash
# Regenerate all CNR programs with Ken Burns AI imagery.
# Runs sequentially to avoid OOM (15GB RAM server).
#
# Programs to generate:
#   1. sleep_debussy_01     — Debussy sleep (CSS warm_waves → KB lily pond)
#   2. sleep_grand_orchestral_01 — Swan Lake+Symphony5+Verdi+Tallis+Vivaldi (179 min, no repeat)
#   3. sleep_complete_romantic_01 — Beethoven Cello+Chopin+Debussy (101 min)
#   4. focus_baroque_chamber_01  — Bach+Vivaldi+Mozart+Beethoven Cello (91 min)
#
# focus_beethoven_01 is already regenerating (run separately).
set -e
cd /opt/kids_channel
LOG=logs/cnr_regen.log
mkdir -p logs

run() {
    local prog=$1
    local durs=${2:-"1 3"}
    local force=${3:-""}
    echo "[$(date '+%H:%M:%S')] === $prog ===" | tee -a $LOG
    python3 scripts/generate_sleep_classical.py --program "$prog" --durations $durs $force \
        >> $LOG 2>&1 \
        && echo "  OK: $prog" | tee -a $LOG \
        || echo "  FAILED: $prog (check $LOG)" | tee -a $LOG
}

echo "=== CNR regen started $(date) ===" | tee -a $LOG

# Re-render bad CSS programs with AI imagery
run sleep_debussy_01         "1 3" "--force"

# New expanded programs (no repeat in 3h)
run sleep_grand_orchestral_01  "1 3 8"
run sleep_complete_romantic_01 "1 3"
run focus_baroque_chamber_01   "1 3"

echo "=== CNR regen complete $(date) ===" | tee -a $LOG
echo "Generated files:"
ls output/queue_id/*.mp4 | grep -E "debussy|grand_orchestral|complete_romantic|baroque_chamber"
