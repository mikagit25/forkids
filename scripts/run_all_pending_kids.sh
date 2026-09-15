#!/usr/bin/env bash
# Sequential render of all pending kids EN/AR content.
# Run AFTER sleep_schubert_01 completes (shared RAM constraint).
# Usage: bash scripts/run_all_pending_kids.sh
set -e
cd /opt/kids_channel
LOG=logs/pending_kids_$(date +%Y%m%d_%H%M%S).log
mkdir -p logs

log() { echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }
run() {
    local id="$1"; shift
    log "=== START: $id ==="
    if python3 -u "$@" >> "$LOG" 2>&1; then
        log "  OK: $id"
    else
        log "  FAILED: $id (see $LOG)"
    fi
}

log "=== Pending kids render batch started $(date) ==="

# ── PeekABoo variants (Remotion renders — most valuable, fills EN+AR queue) ──
log "=== 1. PeekABoo renders ==="

# warm theme
run peekaboo_animals_warm    scripts/generate_peekaboo_long.py --variant animals      --theme warm     --cycle 360 --shuffle 1
run peekaboo_fruits_warm     scripts/generate_peekaboo_long.py --variant fruits_veggies --theme warm   --cycle 360 --shuffle 1
run peekaboo_mix_warm_s2     scripts/generate_peekaboo_long.py --variant mix           --theme warm    --cycle 360 --shuffle 2

# night theme
run peekaboo_mix_night       scripts/generate_peekaboo_long.py --variant mix           --theme night   --cycle 360 --shuffle 1
run peekaboo_animals_night   scripts/generate_peekaboo_long.py --variant animals       --theme night   --cycle 360 --shuffle 1
run peekaboo_fruits_night    scripts/generate_peekaboo_long.py --variant fruits_veggies --theme night  --cycle 360 --shuffle 1

# tropical theme
run peekaboo_mix_tropical    scripts/generate_peekaboo_long.py --variant mix           --theme tropical --cycle 360 --shuffle 1
run peekaboo_animals_tropical scripts/generate_peekaboo_long.py --variant animals      --theme tropical --cycle 360 --shuffle 1
run peekaboo_fruits_tropical scripts/generate_peekaboo_long.py --variant fruits_veggies --theme tropical --cycle 360 --shuffle 1

# candy theme
run peekaboo_mix_candy       scripts/generate_peekaboo_long.py --variant mix           --theme candy   --cycle 360 --shuffle 1
run peekaboo_animals_candy   scripts/generate_peekaboo_long.py --variant animals       --theme candy   --cycle 360 --shuffle 1
run peekaboo_fruits_candy    scripts/generate_peekaboo_long.py --variant fruits_veggies --theme candy  --cycle 360 --shuffle 1

# ── Shadow Puppet ────────────────────────────────────────────────────────────
log "=== 2. Shadow Puppet ==="
run shadow_puppet_animals  scripts/generate_shadow_puppet.py --themes animals
run shadow_puppet_fruits   scripts/generate_shadow_puppet.py --themes fruits
run shadow_puppet_mixed    scripts/generate_shadow_puppet.py --themes mixed

# ── Nature Calm ──────────────────────────────────────────────────────────────
log "=== 3. Nature Calm ==="
run nature_calm  scripts/generate_nature_calm.py

# ── Stars & Bubbles ──────────────────────────────────────────────────────────
log "=== 4. Stars & Bubbles ==="
run stars_bubbles  scripts/generate_stars_bubbles.py

# ── Ocean Creatures ──────────────────────────────────────────────────────────
log "=== 5. Ocean Creatures ==="
run ocean_ocean     scripts/generate_ocean_creatures.py --series ocean
run ocean_sky       scripts/generate_ocean_creatures.py --series sky
run ocean_vehicles  scripts/generate_ocean_creatures.py --series vehicles

# ── Nursery AR ───────────────────────────────────────────────────────────────
log "=== 6. Nursery AR ==="
run nursery_batta_batta  scripts/generate_nursery_ar.py --key batta_batta
run nursery_ya_matar     scripts/generate_nursery_ar.py --key ya_matar
run nursery_dajaja       scripts/generate_nursery_ar.py --key dajaja

# ── Thumbnails (all queues) ───────────────────────────────────────────────────
log "=== 7. Generate AI thumbnails ==="
python3 -u scripts/generate_ai_thumbs.py --queue en  --backend together --all-types >> "$LOG" 2>&1 && log "  OK: thumbs EN" || log "  FAILED: thumbs EN"
python3 -u scripts/generate_ai_thumbs.py --queue ar  --backend together --all-types >> "$LOG" 2>&1 && log "  OK: thumbs AR" || log "  FAILED: thumbs AR"
python3 -u scripts/generate_ai_thumbs.py --queue id  --backend together --all-types >> "$LOG" 2>&1 && log "  OK: thumbs ID" || log "  FAILED: thumbs ID"

log "=== All pending kids renders complete $(date) ==="
log "Log: $LOG"
log "Check queues: python3 scripts/publish_queue.py --dry-run --queue en --type long"
