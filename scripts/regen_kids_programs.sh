#!/bin/bash
# Re-run 5 kids sleep programs that failed due to old timeout (2160s → now fixed to max 10800s)
# Run AFTER bcv2pnetv batch task finishes

set -e
cd /opt/kids_channel

log() { echo "$(date '+%H:%M:%S') $*"; }

for prog in sleep_kids_mozart_3h_01 sleep_kids_beethoven_3h_01 sleep_kids_cello_3h_01 sleep_kids_lullaby_3h_01 sleep_kids_dreams_3h_01; do
    log "=== $prog ==="
    python3 scripts/generate_sleep_classical.py --programs "$prog" --durations 3
    log "=== $prog DONE ==="
done

log "=== Generating thumbnails for new EN queue videos ==="
python3 scripts/generate_ai_thumbs.py --queue en --backend together
log "ALL DONE"
