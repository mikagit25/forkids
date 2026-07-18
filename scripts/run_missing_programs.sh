#!/usr/bin/env bash
# Generate 4 missing Calm Classics programs (all music available in licenses.yaml).
# Runs sequentially after visual themes batch completes.
set -e
cd /opt/kids_channel
LOG=logs/missing_programs.log
mkdir -p logs

run() {
    local prog=$1; shift
    local durs="$*"
    echo "[$(date '+%H:%M:%S')] $prog --durations $durs" | tee -a $LOG
    python3 scripts/generate_sleep_classical.py --program "$prog" --durations $durs \
        >> $LOG 2>&1 && echo "  OK" | tee -a $LOG \
        || echo "  FAILED: $prog" | tee -a $LOG
}

echo "=== Missing programs batch started $(date) ===" | tee -a $LOG

# Swan Lake Act III & IV — sleep, moon_clouds, 1h+3h+8h
run sleep_swan_lake_02 1 3 8

# Beethoven Symphony No. 5 — focus, rain_window, 1h+3h
run focus_beethoven_02 1 3

# Beethoven Cello Sonatas — focus, rain_window, 1h+3h
run focus_beethoven_cello_01 1 3

# Beethoven Cello Sonatas — sleep, warm_waves, 1h+3h
run sleep_beethoven_cello_01 1 3

echo "=== Missing programs batch complete $(date) ===" | tee -a $LOG
echo "NOTE: focus_bach_01 and sleep_lullaby_01 are blocked — need Musopen API key at credentials/musopen_api_key.txt" | tee -a $LOG
