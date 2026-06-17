#!/bin/bash
# Restart pipeline after stopping flat-sprite renders.
# Order: color_learn (3d sprites) → rerender EN numbers → orchestrator step 3+
cd /opt/kids_channel
LOG=logs/restart_pipeline.log
log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }

mkdir -p logs

log "=== PIPELINE RESTART ==="

# ── Step A: color_learn full re-render with _3d sprites ───────────────────────
log "[A] Starting color_learn (all colors × EN+AR+ID, _3d sprites)..."
python3 -u scripts/generate_color_learn_long.py >> logs/color_learn.log 2>&1
log "[A] color_learn done."

# Re-rendered orange/yellow EN are already on YouTube (flat sprites).
# Move them to hold to prevent duplicate cron uploads — replace manually later.
log "[A] Moving already-uploaded EN colors to hold (avoid duplicate uploads)..."
for f in output/queue/color_learn_orange_en_*.mp4 output/queue/color_learn_yellow_en_*.mp4; do
    [ -f "$f" ] || continue
    stem=$(basename "$f" .mp4)
    mv "$f" output/hold/ 2>/dev/null
    mv "output/queue/meta_${stem}.yaml" output/hold/ 2>/dev/null || true
    mv "output/queue/thumb_${stem}.png" output/hold/ 2>/dev/null || true
    log "  → moved $stem to hold/"
done
# Same for green_id (already on YouTube)
for f in output/queue_id/color_learn_green_id_*.mp4; do
    [ -f "$f" ] || continue
    stem=$(basename "$f" .mp4)
    mv "$f" output/hold/ 2>/dev/null
    mv "output/queue_id/meta_${stem}.yaml" output/hold/ 2>/dev/null || true
    mv "output/queue_id/thumb_${stem}.png" output/hold/ 2>/dev/null || true
    log "  → moved $stem to hold/"
done

# ── Step B: re-render EN number_learn (audio bug fix) ────────────────────────
log "[B] Starting number_learn EN re-render (force)..."
python3 -u scripts/generate_number_learn_long.py --force --lang en >> logs/rerender_numbers_en.log 2>&1
log "[B] number_learn EN done."

# ── Step C: continue orchestrator from step 3 (shape_learn onward) ───────────
log "[C] Starting orchestrator from step 3 (shape_learn → lullaby → nursery → thumbs)..."
bash scripts/run_renders_sequential.sh --from 3 >> logs/renders_sequential.log 2>&1
log "[C] Orchestrator done."

log "=== ALL DONE ==="
