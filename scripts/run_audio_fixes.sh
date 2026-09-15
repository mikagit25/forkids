#!/usr/bin/env bash
# Sequential runner for all broken-audio video replacements.
# Run AFTER visual_themes batch completes (to avoid OOM).
#
# Usage:
#   bash scripts/run_audio_fixes.sh
#   bash scripts/run_audio_fixes.sh --debussy-only
set -e
cd /opt/kids_channel
LOG=logs/audio_fixes_20260811.log
mkdir -p logs

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }

# ── 1. Debussy 3h ─────────────────────────────────────────────────────────────
run_debussy_3h() {
    log "=== Debussy 3h re-render (91min unique, fixed audio) ==="
    python3 -u scripts/generate_sleep_classical.py \
        --program sleep_debussy_01 --durations 3 --force \
        >> "$LOG" 2>&1 \
        && log "  OK: sleep_debussy_01 3h" \
        || log "  FAILED: sleep_debussy_01 3h"

    # Add replace_id to meta so publish_queue auto-deletes old video after upload
    python3 -c "
import yaml
from pathlib import Path
from glob import glob
metas = sorted(glob('output/queue_id/meta_sleep_debussy_01_3h_*.yaml'))
if metas:
    meta = Path(metas[-1])
    d = yaml.safe_load(meta.read_text())
    d['replace_id'] = 'xGKnjNFHiSY'  # Jul23 3h (with localizations)
    with open(meta, 'w') as f:
        yaml.dump(d, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    print(f'  replace_id=xGKnjNFHiSY set on {meta.name}')
" 2>&1 | tee -a "$LOG"
}

# ── 2. Mountain Snow 1h ────────────────────────────────────────────────────────
run_mountain_snow() {
    log "=== Mountain Snow 1h re-render (track-boundary gap fixed) ==="
    bash scripts/run_visual_themes.sh --single mountain_snow \
        >> "$LOG" 2>&1 \
        && log "  OK: mountain_snow" \
        || log "  FAILED: mountain_snow"

    python3 -c "
import yaml
from pathlib import Path
from glob import glob
metas = sorted(glob('output/queue_id/meta_visual_theme_mountain_snow_1h_*.yaml'))
if metas:
    meta = Path(metas[-1])
    d = yaml.safe_load(meta.read_text())
    d['replace_id'] = 'hw1IO2roixw'  # Jul14 (gap at 14:47)
    with open(meta, 'w') as f:
        yaml.dump(d, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    print(f'  replace_id=hw1IO2roixw set on {meta.name}')
" 2>&1 | tee -a "$LOG"
}

# ── 3. Delete duplicate Debussy Jul12 videos (no localizations) ───────────────
delete_duplicates() {
    log "=== Deleting duplicate broken videos ==="
    # Debussy 1h Jul12 (FH_gxkPskQM) — no localizations, replaced by Jul23 which
    # will itself be replaced by new upload via replace_id
    python3 scripts/delete_youtube_video.py --channel id FH_gxkPskQM \
        2>&1 | tee -a "$LOG"
    # Debussy 3h Jul12 (G0FIe0KliHk) — has localizations but is 89kbps broken
    python3 scripts/delete_youtube_video.py --channel id G0FIe0KliHk \
        2>&1 | tee -a "$LOG"
    # warm_waves Jul12 short (dnOnhOiuC_Y) — no localizations, EN credentials
    python3 scripts/delete_youtube_video.py --channel en dnOnhOiuC_Y \
        2>&1 | tee -a "$LOG"
    log "  Duplicates deleted"
}

# ── Main ──────────────────────────────────────────────────────────────────────
if [[ "$1" == "--debussy-only" ]]; then
    run_debussy_3h
    exit 0
fi

log "=== Audio fix batch started $(date) ==="
run_debussy_3h
run_mountain_snow
delete_duplicates
log "=== Audio fix batch complete $(date) ==="
log ""
log "Next steps:"
log "  1. Generate thumbnails: python3 scripts/generate_ai_thumbs.py --queue id"
log "  2. Upload via cron (20:00) or: python3 scripts/publish_queue.py --queue id --type long"
log "  3. After uploads: check YouTube Studio that old broken videos were auto-deleted"
log "  4. Localize new videos: python3 scripts/localize_video.py --queue --channel id"
