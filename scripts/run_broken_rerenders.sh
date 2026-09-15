#!/usr/bin/env bash
# Re-render all quarantined broken-audio videos (except Debussy 3h + mountain_snow 1h
# which are handled by run_audio_fixes.sh already running).
#
# Run AFTER run_audio_fixes.sh completes.
# Usage: bash scripts/run_broken_rerenders.sh
set -e
cd /opt/kids_channel
LOG=logs/broken_rerenders_20260811.log
mkdir -p logs

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }

log "=== Broken video re-render batch started $(date) ==="

# ── 1. NO_AUDIO 3h visual themes ────────────────────────────────────────────
log "=== 1. Re-rendering NO_AUDIO 3h visual themes ==="
for theme in deep_space distant_waterfall rainforest_night; do
    log "  → $theme 3h"
    bash scripts/run_visual_themes.sh --single "$theme" \
        >> "$LOG" 2>&1 \
        && log "    OK: $theme" \
        || log "    FAILED: $theme"
done

# ── 2. swan_lake_02 8h ───────────────────────────────────────────────────────
# pad_from: sleep_grand_all_01 added to config to reach 8h
log "=== 2. Re-rendering swan_lake_02 8h (NO_AUDIO, padded from grand_all) ==="
python3 -u scripts/generate_sleep_classical.py \
    --program sleep_swan_lake_02 --durations 8 --force \
    >> "$LOG" 2>&1 \
    && log "  OK: swan_lake_02 8h" \
    || log "  FAILED: swan_lake_02 8h"

# ── 3. focus_classical_miniatures 1h + 3h (80kbps bad source fixed) ─────────
# Config only declares 1h; 3h forced via --durations flag (uses pad_from)
log "=== 3. Re-rendering focus_classical_miniatures (80kbps → 192kbps fix) ==="
python3 -u scripts/generate_sleep_classical.py \
    --program focus_classical_miniatures_01 --durations 1 --force \
    >> "$LOG" 2>&1 \
    && log "  OK: focus_classical_miniatures 1h" \
    || log "  FAILED: focus_classical_miniatures 1h"
python3 -u scripts/generate_sleep_classical.py \
    --program focus_classical_miniatures_01 --durations 3 --force \
    >> "$LOG" 2>&1 \
    && log "  OK: focus_classical_miniatures 3h" \
    || log "  FAILED: focus_classical_miniatures 3h"

# ── 4. sleep_beethoven_cello_01 1h (140kbps pre-fix pipeline) ───────────────
log "=== 4. Re-rendering sleep_beethoven_cello_01 1h (140kbps → 192kbps) ==="
python3 -u scripts/generate_sleep_classical.py \
    --program sleep_beethoven_cello_01 --durations 1 --force \
    >> "$LOG" 2>&1 \
    && log "  OK: sleep_beethoven_cello_01 1h" \
    || log "  FAILED: sleep_beethoven_cello_01 1h"

# ── 5. warm_waves shorts — REMOVED (make_sleep_short.py uses CSS Remotion loops,
#       not KB AI images → banned from CNR). Use visual_short from make_visual_shorts.py.

# ── 6. visual shorts: lavender_fields, rainforest_night, fireplace_cabin ────
log "=== 6. Re-rendering visual shorts (mono source → stereo fix) ==="
for theme in lavender_fields rainforest_night fireplace_cabin; do
    log "  → $theme visual shorts (3 offsets)"
    for offset in 0 60 120; do
        python3 scripts/make_visual_shorts.py --theme "$theme" --offset "$offset" --force \
            >> "$LOG" 2>&1 \
            && log "    OK: $theme t${offset}s" \
            || log "    FAILED: $theme t${offset}s"
    done
done

# ── 7. cherry_blossoms visual shorts (after loop is ready) ──────────────────
log "=== 7. Re-rendering cherry_blossoms visual shorts (3 offsets) ==="
for offset in 0 60 120; do
    python3 scripts/make_visual_shorts.py --theme cherry_blossoms --offset "$offset" --force \
        >> "$LOG" 2>&1 \
        && log "  OK: cherry_blossoms t${offset}s" \
        || log "  FAILED: cherry_blossoms t${offset}s"
done

log "=== Re-render batch complete $(date) ==="
log ""
log "Next steps:"
log "  1. Generate thumbnails: python3 scripts/generate_ai_thumbs.py --queue id"
log "  2. Upload via cron (20:00) or: python3 scripts/publish_queue.py --queue id --type long"
log "  3. Localize new videos: python3 scripts/localize_video.py --queue --channel id"
