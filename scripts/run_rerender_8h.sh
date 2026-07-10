#!/bin/bash
# Re-render corrupt 8h videos with fixed timeout + faster preset
cd "$(dirname "$0")/.."
LOG=logs/rerender_8h.log
mkdir -p logs
exec > >(tee -a "$LOG") 2>&1

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  8h Re-render START — $(date '+%Y-%m-%d %H:%M:%S')"
echo "════════════════════════════════════════════════════════════"

run() {
    local prog="$1"; shift
    echo ""
    echo "▶ [$prog] durations: $* — $(date '+%H:%M:%S')"
    python3 scripts/generate_sleep_classical.py --program "$prog" --durations "$@"
    echo "  ✓ [$prog] done — $(date '+%H:%M:%S')"
}

run sleep_swan_lake_01   8
run sleep_chopin_01      8
run sleep_grand_night_01 8

# ────────────────────────────────────────────────────────────
# New programs: sleep_swan_lake_02 + focus_beethoven_02
# ────────────────────────────────────────────────────────────
run sleep_swan_lake_02   1 3 8
run focus_beethoven_02   1 3

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  8h Re-render DONE — $(date '+%Y-%m-%d %H:%M:%S')"
echo "════════════════════════════════════════════════════════════"
