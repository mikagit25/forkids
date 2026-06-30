#!/usr/bin/env bash
# run_shorts.sh — Sequential generation of ALL shorts (EN + AR + ID)
# Run ONLY after long videos are complete (Remotion renders one at a time).
#
# Usage:
#   bash scripts/run_shorts.sh            # all steps
#   bash scripts/run_shorts.sh --from 5   # resume from step 5
#   bash scripts/run_shorts.sh --dry-run  # show steps, no render

set -euo pipefail
cd "$(dirname "$0")/.."

FROM_STEP=1
DRY_RUN=0
for arg in "$@"; do
    case "$arg" in
        --from) ;;
        --dry-run) DRY_RUN=1 ;;
        [0-9]*) FROM_STEP=$arg ;;
    esac
done
[[ "$*" =~ --from[[:space:]]+([0-9]+) ]] && FROM_STEP="${BASH_REMATCH[1]}"

log() { echo "[$(date +%H:%M:%S)] $*" | tee -a logs/run_shorts.log; }
skip() { log "SKIP step $1: $2"; }
run_py() {
    if [[ $DRY_RUN -eq 1 ]]; then
        log "DRY RUN: python3 $*"
    else
        python3 -u "$@" >> logs/run_shorts.log 2>&1
    fi
}

log "════════════════════════════════════════════════════════"
log "Shorts generation pipeline (FROM_STEP=$FROM_STEP)"
log "════════════════════════════════════════════════════════"

# ── Step 1: Vocab shorts (EN) — A-Z, 26 videos ──────────────────────────────
if [[ $FROM_STEP -le 1 ]]; then
    VOCAB_COUNT=$(ls output/queue/short_vocab_*.mp4 2>/dev/null | wc -l)
    if [[ $VOCAB_COUNT -ge 26 ]]; then
        skip 1 "vocab shorts ($VOCAB_COUNT/26 exist)"
    else
        log "[1/12] vocab shorts EN — A-Z = 26 videos..."
        run_py scripts/generate_vocab_shorts.py
        log "[1/12] vocab shorts EN done."
    fi
fi

# ── Step 2: Color learn shorts (EN) — 7 colors ──────────────────────────────
if [[ $FROM_STEP -le 2 ]]; then
    CL_COUNT=$(ls output/queue/short_colorlearn_*.mp4 2>/dev/null | wc -l)
    if [[ $CL_COUNT -ge 7 ]]; then
        skip 2 "color learn shorts EN ($CL_COUNT/7 exist)"
    else
        log "[2/12] color learn shorts EN — 7 colors..."
        run_py scripts/generate_color_learn_shorts.py
        log "[2/12] color learn shorts EN done."
    fi
fi

# ── Step 3: Shape float shorts (EN) — 8×4=32 videos ────────────────────────
if [[ $FROM_STEP -le 3 ]]; then
    SF_COUNT=$(ls output/queue/short_shape_float_*.mp4 2>/dev/null | wc -l)
    if [[ $SF_COUNT -ge 32 ]]; then
        skip 3 "shape float shorts EN ($SF_COUNT/32 exist)"
    else
        log "[3/12] shape float shorts EN — 8×4=32 videos..."
        run_py scripts/generate_shape_float_shorts.py
        log "[3/12] shape float shorts EN done."
    fi
fi

# ── Step 4: Shape dance shorts (EN) — 13 videos ─────────────────────────────
if [[ $FROM_STEP -le 4 ]]; then
    SD_COUNT=$(ls output/queue/short_shape_dance_*.mp4 2>/dev/null | wc -l)
    if [[ $SD_COUNT -ge 13 ]]; then
        skip 4 "shape dance shorts EN ($SD_COUNT/13 exist)"
    else
        log "[4/12] shape dance shorts EN — 13 videos..."
        run_py scripts/generate_shape_dance_shorts.py
        log "[4/12] shape dance shorts EN done."
    fi
fi

# ── Step 5: Animal dance shorts (EN) — 20 videos ────────────────────────────
if [[ $FROM_STEP -le 5 ]]; then
    AN_COUNT=$(ls output/queue/short_dance_*_2026*.mp4 2>/dev/null | grep -v ar | grep -v _id | wc -l)
    if [[ $AN_COUNT -ge 20 ]]; then
        skip 5 "animal dance shorts EN ($AN_COUNT/20 exist)"
    else
        log "[5/12] animal dance shorts EN — 20 videos..."
        run_py scripts/generate_animal_shorts.py
        log "[5/12] animal dance shorts EN done."
    fi
fi

# ── Step 6: Fruit dance shorts (EN) — 12 videos ─────────────────────────────
if [[ $FROM_STEP -le 6 ]]; then
    FR_COUNT=$(ls output/queue/short_dance_apple_*.mp4 output/queue/short_dance_banana_*.mp4 2>/dev/null | wc -l)
    if [[ $FR_COUNT -ge 2 ]]; then
        skip 6 "fruit dance shorts EN (exist)"
    else
        log "[6/12] fruit dance shorts EN — 12 videos..."
        run_py scripts/generate_fruit_shorts.py
        log "[6/12] fruit dance shorts EN done."
    fi
fi

# ── Step 7: Vegetable dance shorts (EN) — 10 videos ─────────────────────────
if [[ $FROM_STEP -le 7 ]]; then
    VG_COUNT=$(ls output/queue/short_dance_carrot_*.mp4 output/queue/short_dance_broccoli_*.mp4 2>/dev/null | wc -l)
    if [[ $VG_COUNT -ge 2 ]]; then
        skip 7 "vegetable dance shorts EN (exist)"
    else
        log "[7/12] vegetable dance shorts EN — 10 videos..."
        run_py scripts/generate_vegetable_shorts.py
        log "[7/12] vegetable dance shorts EN done."
    fi
fi

# ── Step 8: Counting shorts (EN) — 8 videos ─────────────────────────────────
if [[ $FROM_STEP -le 8 ]]; then
    CT_COUNT=$(ls output/queue/short_counting_*.mp4 2>/dev/null | wc -l)
    if [[ $CT_COUNT -ge 8 ]]; then
        skip 8 "counting shorts EN ($CT_COUNT/8 exist)"
    else
        log "[8/12] counting shorts EN — 8 videos..."
        run_py scripts/generate_counting_shorts.py
        log "[8/12] counting shorts EN done."
    fi
fi

# ── Step 9: Shape learn shorts (EN) — 16 videos ─────────────────────────────
if [[ $FROM_STEP -le 9 ]]; then
    SH_COUNT=$(ls output/queue/short_shapes_*.mp4 output/queue/short_shape_*.mp4 2>/dev/null | grep -v float | grep -v dance | wc -l)
    if [[ $SH_COUNT -ge 16 ]]; then
        skip 9 "shape learn shorts EN ($SH_COUNT/16 exist)"
    else
        log "[9/12] shape learn shorts EN — 16 videos..."
        run_py scripts/generate_shapes_shorts.py
        log "[9/12] shape learn shorts EN done."
    fi
fi

# ── Step 10: Shape float+dance shorts (AR + ID) — 32+4 per channel ──────────
# generate_shape_notxt.py --short: 8 shapes × 4 modes = 32 per channel
# generate_shape_notxt.py --dance: 4 combo dance shorts per channel
# NOTE: pig is not used in shapes, so no substitution needed here
if [[ $FROM_STEP -le 10 ]]; then
    AR_SH=$(ls output/queue_ar/shape_float_*.mp4 2>/dev/null | wc -l)
    ID_SH=$(ls output/queue_id/shape_float_*.mp4 2>/dev/null | wc -l)
    if [[ $AR_SH -ge 32 && $ID_SH -ge 32 ]]; then
        skip 10 "AR/ID shape shorts ($AR_SH AR, $ID_SH ID — all 32 exist)"
    else
        log "[10/12] shape float shorts AR+ID — 8×4=32 per channel..."
        run_py scripts/generate_shape_notxt.py --short
        log "[10/12] shape float shorts AR+ID done."
    fi
fi

# ── Step 11: Dance combo shorts (AR + ID) — 4 per channel ───────────────────
if [[ $FROM_STEP -le 11 ]]; then
    AR_DC=$(ls output/queue_ar/shape_dance_*.mp4 2>/dev/null | wc -l)
    if [[ $AR_DC -ge 4 ]]; then
        skip 11 "AR/ID dance combo shorts ($AR_DC exist)"
    else
        log "[11/12] dance combo shorts AR+ID — 4 per channel..."
        run_py scripts/generate_shape_notxt.py --dance
        log "[11/12] dance combo shorts AR+ID done."
    fi
fi

# ── Step 12: Thumbnails for all queues ───────────────────────────────────────
if [[ $FROM_STEP -le 12 ]]; then
    log "[12/12] generating thumbnails for all queues..."
    python3 -u scripts/generate_ai_thumbs.py --queue en --backend together >> logs/thumbs_en.log 2>&1
    python3 -u scripts/generate_ai_thumbs.py --queue ar --backend together >> logs/thumbs_ar.log 2>&1
    python3 -u scripts/generate_ai_thumbs.py --queue id --backend together >> logs/thumbs_id.log 2>&1
    log "[12/12] thumbnails done."
fi

log "════════════════════════════════════════════════════════"
log "ШОРТСЫ ГОТОВЫ"
EN_S=$(ls output/queue/short_*.mp4 2>/dev/null | wc -l)
AR_S=$(ls output/queue_ar/short_*.mp4 output/queue_ar/shape_float_*.mp4 output/queue_ar/shape_dance_*.mp4 2>/dev/null | wc -l)
ID_S=$(ls output/queue_id/short_*.mp4 output/queue_id/shape_float_*.mp4 output/queue_id/shape_dance_*.mp4 2>/dev/null | wc -l)
log "EN: $EN_S шортсов  AR: $AR_S шортсов  ID: $ID_S шортсов"
log "════════════════════════════════════════════════════════"
