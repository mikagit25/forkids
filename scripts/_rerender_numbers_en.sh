#!/bin/bash
# Re-render all 10 number_learn EN with corrected algorithm.
# Waits until color_learn (and any other render) is fully done.
cd /opt/kids_channel
LOG=logs/rerender_numbers_en.log
log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a $LOG; }

# Prevent duplicate runs
LOCK=/tmp/rerender_numbers_en.lock
if [ -f "$LOCK" ]; then
    log "Already running (lock exists). Exiting."; exit 0
fi
echo $$ > "$LOCK"
trap 'rm -f "$LOCK"' EXIT

log "Waiting for color_learn and remotion renders to finish..."
while kill -0 3667403 2>/dev/null || pgrep -x "remotion" > /dev/null 2>&1; do
    sleep 60
done
log "All renders done. Starting number_learn EN --force..."

python3 -u scripts/generate_number_learn_long.py --lang en --force >> $LOG 2>&1
EXIT=$?
log "Render exit=$EXIT"

if [[ $EXIT -eq 0 ]]; then
    python3 -u scripts/generate_number_learn_long.py --regen-meta >> $LOG 2>&1
    log "Done. number_learn_*_en_*.mp4 ready in output/queue/"
else
    log "ERROR — check $LOG"
fi
