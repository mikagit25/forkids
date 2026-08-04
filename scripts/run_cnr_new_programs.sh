#!/bin/bash
# CNR New Programs batch render (2026-08-04)
# 5 programs × 2 durations = 10 videos → output/queue_id/
# Run sequentially — server has 15GB RAM, concurrent renders = OOM

set -e
cd /opt/kids_channel
LOG=logs/cnr_new_programs.log
exec >> "$LOG" 2>&1

echo "=============================="
echo "CNR new programs batch start: $(date)"
echo "=============================="

run_program() {
    local prog="$1"
    local durations="$2"
    echo ""
    echo "--- $prog ($durations) --- $(date)"
    python3 scripts/generate_sleep_classical.py --program "$prog" --durations $durations
    echo "--- $prog DONE --- $(date)"
}

run_program sleep_grand_all_01          "1 3"
run_program sleep_baroque_romantics_01  "1 3"
run_program focus_bach_goldberg_complete_01 "1 3"
run_program focus_beethoven_violin_01   "1 3"
run_program focus_bach_violin_partita_01 "1 3"

echo ""
echo "=============================="
echo "ALL DONE: $(date)"
echo "=============================="
