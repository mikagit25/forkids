#!/usr/bin/env bash
# Wait for replacement KB videos and backdate them to top of queue
# Runs until both sets of files appear, then exits.
set -e
cd /opt/kids_channel
LOG=logs/prioritize_replacements.log

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a $LOG; }

QUEUE=output/queue_id
EARLY_DATE="202607120000"  # Before all existing queue files

wait_and_prioritize() {
    local prog=$1
    local dur=$2
    local pattern="${QUEUE}/${prog}_${dur}_*.mp4"

    while true; do
        FILE=$(ls $pattern 2>/dev/null | head -1)
        if [[ -n "$FILE" ]]; then
            META=$(ls ${QUEUE}/meta_${prog}_${dur}_*.yaml 2>/dev/null | head -1)
            THUMB=$(ls ${QUEUE}/thumb_${prog}_${dur}_*.png 2>/dev/null | head -1)
            if [[ -n "$META" && -n "$THUMB" ]]; then
                log "  Prioritizing $prog $dur: $FILE"
                touch -t $EARLY_DATE "$FILE" "$META" "$THUMB"
                log "  → backdated to $EARLY_DATE ✓"
                return 0
            else
                log "  $prog $dur: mp4 exists but missing meta/thumb — waiting..."
            fi
        fi
        sleep 60
    done
}

log "=== Replacement prioritizer started ==="

log "Waiting for focus_beethoven_01..."
wait_and_prioritize focus_beethoven_01 1h &
wait_and_prioritize focus_beethoven_01 3h &

log "Waiting for sleep_debussy_01 (KB version)..."
wait_and_prioritize sleep_debussy_01 1h &
wait_and_prioritize sleep_debussy_01 3h &

wait
log "=== All replacements prioritized — check queue order with dry-run ==="
python3 scripts/publish_queue.py --dry-run --queue id --type long --limit 5 >> $LOG 2>&1
