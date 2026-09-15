#!/bin/bash
# Regenerate all visual_theme videos that had broken audio (deleted from YouTube)
# autumn_forest 3h is already running separately (b9xbldvmw)
# All visual loops are cached — only audio rebuild + video assembly needed
# aurora_borealis: generate ONE 3h replacement (replaces all 3 deleted broken versions)

set -e
cd /opt/kids_channel

log() { echo "$(date '+%H:%M:%S') $*"; }

log "=== aurora_borealis 3h (replaces deleted 1h x2 + 3h) ==="
python3 scripts/make_visual_theme.py --theme aurora_borealis --durations 3
log "=== aurora_borealis DONE ==="

log "=== cherry_blossoms 3h ==="
python3 scripts/make_visual_theme.py --theme cherry_blossoms --durations 3
log "=== cherry_blossoms DONE ==="

log "=== fireplace_cabin 3h ==="
python3 scripts/make_visual_theme.py --theme fireplace_cabin --durations 3
log "=== fireplace_cabin DONE ==="

log "=== mountain_snow 1h ==="
python3 scripts/make_visual_theme.py --theme mountain_snow --durations 1
log "=== mountain_snow DONE ==="

log "=== zen_garden 3h ==="
python3 scripts/make_visual_theme.py --theme zen_garden --durations 3
log "=== zen_garden DONE ==="

log "=== Generating thumbnails for all new queue_id videos ==="
python3 scripts/generate_ai_thumbs.py --queue id --backend together
log "=== Thumbnails DONE ==="

log "ALL DONE — check output/queue_id/ for new videos"
