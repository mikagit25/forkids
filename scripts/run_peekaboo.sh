#!/bin/bash
# PeekABoo Long batch render — 4 themes × 3 variants × shuffle seeds
# Each video: 88/53/29 sprites × 12s = 10–18 min unique, no repetition, EN+AR copy
# Usage: nohup bash scripts/run_peekaboo.sh &
set -e
cd /opt/kids_channel
LOG=logs/peekaboo.log
exec >> "$LOG" 2>&1

run() {
    local variant="$1"
    local theme="$2"
    local shuffle="$3"
    echo ""
    echo "--- peekaboo_${variant}_${theme}_s${shuffle} --- $(date)"
    python3 scripts/generate_peekaboo_long.py \
        --variant "$variant" --theme "$theme" --shuffle "$shuffle" --cycle 360
    echo "--- DONE --- $(date)"
}

echo "=============================="
echo "PeekABoo batch start: $(date)"
echo "=============================="

# === WARM (plain gradient) ===
run mix            warm 1
run animals        warm 1
run fruits_veggies warm 1
run mix            warm 2

# === NIGHT (dark purple + starry bg) ===
run mix            night 1
run animals        night 1
run fruits_veggies night 1

# === TROPICAL (cyan/teal bg) ===
run mix            tropical 1
run animals        tropical 1
run fruits_veggies tropical 1

# === CANDY (pink/lavender bg) ===
run mix            candy 1
run animals        candy 1

echo ""
echo "=============================="
echo "ALL PEEKABOO DONE: $(date)"
echo "=============================="
