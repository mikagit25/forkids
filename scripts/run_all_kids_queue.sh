#!/bin/bash
# Master kids queue runner — sequential, safe for 15GB RAM server.
# Runs AFTER current dance_pet render (PID 214758) finishes.
#
# Order:
#   1. [ALREADY RUNNING] generate_dance_pet.py     (~15–20h total)
#   2. run_peekaboo.sh        — 12 PeekABooLong variants (~9–10h)
#   3. SensoryBlobLoop silent — 5-min render → FFmpeg 30+60 min (~30 min)
#   4. SensoryBlobLoop +sound — same with Dreamy Arpeggios v2.mp3 (~30 min)
#
# Usage: nohup bash scripts/run_all_kids_queue.sh > logs/all_kids_queue.log 2>&1 &
set -e
cd /opt/kids_channel
LOG=logs/all_kids_queue.log

# ── Helpers ───────────────────────────────────────────────────────────────────
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

wait_for_pid() {
    local pid=$1
    local label=$2
    if kill -0 "$pid" 2>/dev/null; then
        log "Waiting for $label (PID $pid) to finish..."
        while kill -0 "$pid" 2>/dev/null; do
            sleep 60
        done
        log "$label (PID $pid) finished."
    else
        log "$label (PID $pid) already done — continuing."
    fi
}

run_step() {
    local label=$1
    shift
    log "=== START: $label ==="
    "$@"
    log "=== DONE:  $label ==="
    echo ""
}

# ── Main ──────────────────────────────────────────────────────────────────────
log "=========================================="
log "Kids queue master runner START"
log "=========================================="

# Step 1: wait for dance_pet (launched earlier this session)
wait_for_pid 214758 "generate_dance_pet.py"

# Step 2: PeekABoo Long — 4 themes × 3 variants × shuffle seeds (12 videos → EN+AR)
run_step "PeekABooLong batch (12 variants)" bash scripts/run_peekaboo.sh

# Step 3: SensoryBlobLoop — silent version (30+60 min → EN+AR)
run_step "SensoryBlobLoop silent (30+60 min)" \
    python3 scripts/generate_sensory_blob.py --durations 30 60

# Step 4: SensoryBlobLoop — with music (30+60 min → EN+AR)
run_step "SensoryBlobLoop +sound (30+60 min)" \
    python3 scripts/generate_sensory_blob.py --durations 30 60 --sound

# Step 5: PeekABoo Shorts — 60s vertical clips from PeekABoo Long (EN+AR)
# FFmpeg only, no Remotion — safe to run after all Remotion renders done
run_step "PeekABoo Shorts EN+AR" \
    python3 scripts/generate_peekaboo_shorts.py

# Step 6: Generate AI thumbnails for any new shorts without thumbs
run_step "AI Thumbnails (EN+AR shorts)" \
    python3 scripts/generate_ai_thumbs.py --queue en --backend together
run_step "AI Thumbnails (AR)" \
    python3 scripts/generate_ai_thumbs.py --queue ar --backend together

log "=========================================="
log "ALL KIDS QUEUE DONE"
log "=========================================="
log "Check output/queue/ and output/queue_ar/ for results."
log "Cron will publish automatically on schedule."
