#!/bin/bash
# Sequential render runner — one process at a time.
# Order: number_learn → regen-meta (thumbs) → color_learn → regen-meta (thumbs)
# 3 channels: EN + AR + ID  (10×3=30 number, 9×3=27 color, 8×3=24 shape)
#
# Usage:
#   bash scripts/run_renders_sequential.sh             # normal run
#   bash scripts/run_renders_sequential.sh --wait-for PID  # wait for existing PID first

set -e
cd /opt/kids_channel

WAIT_PID=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --wait-for) WAIT_PID="$2"; shift 2 ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

log() { echo "[$(date '+%H:%M:%S')] $*"; }

# ── Step 0: Wait for an existing PID to finish ────────────────────────────
if [[ -n "$WAIT_PID" ]]; then
    log "Waiting for PID $WAIT_PID to finish before starting..."
    while kill -0 "$WAIT_PID" 2>/dev/null; do
        sleep 30
    done
    log "PID $WAIT_PID finished."
fi

# ── Step 1: number_learn (10 numbers × 3 langs = 30 videos) ──────────────
if pgrep -f "generate_number_learn_long.py" > /dev/null; then
    log "number_learn is running — waiting for it to finish..."
    while pgrep -f "generate_number_learn_long.py" > /dev/null; do
        sleep 30
    done
    log "number_learn finished."
else
    NL_TOTAL=$(ls output/queue/number_learn_*.mp4 output/queue_ar/number_learn_*.mp4 output/queue_id/number_learn_*.mp4 2>/dev/null | wc -l)
    if [[ $NL_TOTAL -ge 30 ]]; then
        log "number_learn complete ($NL_TOTAL/30 MP4s) — skipping render."
    else
        log "Starting number_learn ($NL_TOTAL/30 done)..."
        python3 -u scripts/generate_number_learn_long.py >> logs/number_learn.log 2>&1
        log "number_learn render done."
    fi
fi

# ── Step 2: regen meta+thumbnails for number_learn ───────────────────────
NL_THUMBS=$(ls output/queue/thumb_number_learn_*.png output/queue_ar/thumb_number_learn_*.png output/queue_id/thumb_number_learn_*.png 2>/dev/null | wc -l)
NL_MP4S=$(ls output/queue/number_learn_*.mp4 output/queue_ar/number_learn_*.mp4 output/queue_id/number_learn_*.mp4 2>/dev/null | wc -l)
if [[ $NL_THUMBS -lt $NL_MP4S ]]; then
    log "Generating thumbnails for number_learn ($NL_THUMBS/$NL_MP4S have thumbs)..."
    python3 -u scripts/generate_number_learn_long.py --regen-meta >> logs/number_learn.log 2>&1
    log "number_learn thumbnails done."
else
    log "number_learn thumbnails OK ($NL_THUMBS/$NL_MP4S)."
fi

# ── Step 3: color_learn (9 colors × 3 langs = 27 videos) ─────────────────
if pgrep -f "generate_color_learn_long.py" > /dev/null; then
    log "color_learn is running — waiting for it to finish..."
    while pgrep -f "generate_color_learn_long.py" > /dev/null; do
        sleep 30
    done
    log "color_learn finished."
else
    CL_TOTAL=$(ls output/queue/color_learn_*.mp4 output/queue_ar/color_learn_*.mp4 output/queue_id/color_learn_*.mp4 2>/dev/null | wc -l)
    if [[ $CL_TOTAL -ge 27 ]]; then
        log "color_learn complete ($CL_TOTAL/27 MP4s) — skipping render."
    else
        log "Starting color_learn ($CL_TOTAL/27 done)..."
        python3 -u scripts/generate_color_learn_long.py >> logs/color_learn.log 2>&1
        log "color_learn render done."
    fi
fi

# ── Step 4: regen meta+thumbnails for color_learn ────────────────────────
CL_THUMBS=$(ls output/queue/thumb_color_learn_*.png output/queue_ar/thumb_color_learn_*.png output/queue_id/thumb_color_learn_*.png 2>/dev/null | wc -l)
CL_MP4S=$(ls output/queue/color_learn_*.mp4 output/queue_ar/color_learn_*.mp4 output/queue_id/color_learn_*.mp4 2>/dev/null | wc -l)
if [[ $CL_THUMBS -lt $CL_MP4S ]]; then
    log "Generating thumbnails for color_learn ($CL_THUMBS/$CL_MP4S have thumbs)..."
    python3 -u scripts/generate_color_learn_long.py --regen-meta >> logs/color_learn.log 2>&1
    log "color_learn thumbnails done."
else
    log "color_learn thumbnails OK ($CL_THUMBS/$CL_MP4S)."
fi

# ── Step 5: shape_learn (8 shapes × 3 langs = 24 videos, no text) ────────
if pgrep -f "generate_shape_learn.py" > /dev/null; then
    log "shape_learn is running — waiting for it to finish..."
    while pgrep -f "generate_shape_learn.py" > /dev/null; do
        sleep 30
    done
    log "shape_learn finished."
else
    SL_TOTAL=$(ls output/queue/shape_learn_*.mp4 output/queue_ar/shape_learn_*.mp4 output/queue_id/shape_learn_*.mp4 2>/dev/null | wc -l)
    if [[ $SL_TOTAL -ge 24 ]]; then
        log "shape_learn complete ($SL_TOTAL/24 MP4s) — skipping render."
    else
        log "Starting shape_learn ($SL_TOTAL/24 done)..."
        python3 -u scripts/generate_shape_learn.py >> logs/shape_learn.log 2>&1
        log "shape_learn render done."
    fi
fi

# ── Step 6: regen meta+thumbnails for shape_learn ────────────────────────
SL_THUMBS=$(ls output/queue/thumb_shape_learn_*.png output/queue_ar/thumb_shape_learn_*.png output/queue_id/thumb_shape_learn_*.png 2>/dev/null | wc -l)
SL_MP4S=$(ls output/queue/shape_learn_*.mp4 output/queue_ar/shape_learn_*.mp4 output/queue_id/shape_learn_*.mp4 2>/dev/null | wc -l)
if [[ $SL_THUMBS -lt $SL_MP4S ]]; then
    log "Generating thumbnails for shape_learn ($SL_THUMBS/$SL_MP4S have thumbs)..."
    python3 -u scripts/generate_shape_learn.py --regen-meta >> logs/shape_learn.log 2>&1
    log "shape_learn thumbnails done."
else
    log "shape_learn thumbnails OK ($SL_THUMBS/$SL_MP4S)."
fi

# ── Summary ───────────────────────────────────────────────────────────────
log "=== All renders complete ==="
log "Queue EN:  $(ls output/queue/*.mp4 2>/dev/null | wc -l) videos"
log "Queue AR:  $(ls output/queue_ar/*.mp4 2>/dev/null | wc -l) videos"
log "Queue ID:  $(ls output/queue_id/*.mp4 2>/dev/null | wc -l) videos"
log "Thumbs:    $(ls output/queue/thumb_*.png output/queue_ar/thumb_*.png output/queue_id/thumb_*.png 2>/dev/null | wc -l) thumbnails"
