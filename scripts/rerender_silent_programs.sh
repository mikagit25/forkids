#!/usr/bin/env bash
# Re-render all silent CNR sleep/focus programs with audio fix
# Run AFTER rerender of swan_lake_01 1h, chopin_01 1h, beethoven_01 1h completes
set -e
cd /opt/kids_channel
LOG=logs/rerender_silent.log

run() {
    local prog=$1; shift
    local durs="$*"
    echo "[$(date '+%H:%M:%S')] $prog --durations $durs" | tee -a $LOG
    python3 scripts/generate_sleep_classical.py --program "$prog" --durations $durs --force \
        >> $LOG 2>&1 && echo "  OK" | tee -a $LOG \
        || echo "  FAILED" | tee -a $LOG
}

echo "=== Batch silent re-render started $(date) ===" | tee -a $LOG

# chopin_01: 3h + 8h  (1h done separately)
run sleep_chopin_01      3 8

# All other programs: both durations at once
run sleep_chopin_02      1 3
run sleep_debussy_01     1 3
run sleep_flute_01       1 3
run sleep_baroque_01     1 3
run sleep_romantic_night_01 1 3
run sleep_grand_night_01 3 8
run sleep_swan_lake_01   3 8  # (1h done separately)
run focus_beethoven_01   3    # (1h done separately)
run focus_drama_01       1 3
run focus_mozart_01      1 3

echo "=== Batch complete $(date) ===" | tee -a $LOG
