#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# MASTER RENDER ORCHESTRATOR — только длинные видео, один процесс за раз.
# 15GB RAM: никогда не запускать два рендера одновременно.
#
# ШАГ | ТИП               | СКРИПТ                              | КАНАЛЫ   | КОЛ-ВО
#  1  | number_learn       | generate_number_learn_long.py       | EN+AR+ID | 10×3=30
#  2  | color_learn        | generate_color_learn_long.py        | EN+AR+ID | 9×3=27
#  3  | shape_learn        | generate_shape_learn.py             | EN+AR+ID | 8×3=24
#  4  | dance (animals)    | generate_dance_long.py --themes animals    | EN | 1
#  5  | dance (fruits)     | generate_dance_long.py --themes fruits     | EN | 1
#  6  | dance (vegetables) | generate_dance_long.py --themes vegetables | EN | 1
#  7  | character_dialogue | generate_character_dialogue_long.py | EN+AR+ID | 4×3=12
#  8  | lullaby            | generate_lullaby.py                 | EN+AR+ID | 6×3=18
#  9  | nursery_ar         | generate_nursery_ar.py              | AR       | 3
# 10  | nursery_id         | generate_nursery_id.py              | ID       | 6
# 11  | thumbnails EN      | generate_ai_thumbs.py --queue en    | EN       | все
# 12  | thumbnails AR      | generate_ai_thumbs.py --queue ar    | AR       | все
# 13  | thumbnails ID      | generate_ai_thumbs.py --queue id    | ID       | все
#
# Шортсы — отдельно, после завершения всех длинных видео.
#
# Usage:
#   bash scripts/run_renders_sequential.sh            # полный прогон
#   bash scripts/run_renders_sequential.sh --from 4   # начать с шага 4
#   bash scripts/run_renders_sequential.sh --wait-for PID
# ═══════════════════════════════════════════════════════════════════════════════

set -e
cd /opt/kids_channel

WAIT_PID=""
FROM_STEP=1
while [[ $# -gt 0 ]]; do
    case "$1" in
        --wait-for) WAIT_PID="$2"; shift 2 ;;
        --from)     FROM_STEP="$2"; shift 2 ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

log()  { echo "[$(date '+%H:%M:%S')] $*" | tee -a logs/renders_sequential.log; }
skip() { log "SKIP step $1: $2"; }

mkdir -p logs

# ── Ожидание PID ──────────────────────────────────────────────────────────────
if [[ -n "$WAIT_PID" ]]; then
    log "Waiting for PID $WAIT_PID to finish..."
    while kill -0 "$WAIT_PID" 2>/dev/null; do sleep 30; done
    log "PID $WAIT_PID finished."
fi

# Helper: count MP4s in queue + uploaded (unique colors/numbers avoid double-count)
count_done() {
    local type="$1" lang="$2"
    local q_dir uploaded_glob
    case "$lang" in
        en)  q_dir="output/queue" ;;
        ar)  q_dir="output/queue_ar" ;;
        id)  q_dir="output/queue_id" ;;
    esac
    local q_count=$(ls ${q_dir}/${type}_*.mp4 2>/dev/null | wc -l)
    local u_count=$(ls uploaded/${type}_*_${lang}_*.mp4 2>/dev/null | sort -t_ -k5 -u | wc -l)
    echo $((q_count + u_count))
}

# ── Step 1: number_learn (10 × 3 = 30 видео) ─────────────────────────────────
if [[ $FROM_STEP -le 1 ]]; then
    if pgrep -f "generate_number_learn_long.py" > /dev/null; then
        log "[1/13] number_learn running — waiting..."
        while pgrep -f "generate_number_learn_long.py" > /dev/null; do sleep 30; done
    fi
    NL_EN=$(count_done "number_learn" "en")
    NL_AR=$(count_done "number_learn" "ar")
    NL_ID=$(count_done "number_learn" "id")
    NL=$((NL_EN + NL_AR + NL_ID))
    if [[ $NL -ge 30 ]]; then
        skip 1 "number_learn ($NL/30: EN=$NL_EN AR=$NL_AR ID=$NL_ID)"
    else
        log "[1/13] number_learn — $NL/30 done (EN=$NL_EN AR=$NL_AR ID=$NL_ID)..."
        python3 -u scripts/generate_number_learn_long.py >> logs/number_learn.log 2>&1
        log "[1/13] number_learn done."
    fi
    NLT=$(ls output/queue/thumb_number_learn_*.png output/queue_ar/thumb_number_learn_*.png output/queue_id/thumb_number_learn_*.png 2>/dev/null | wc -l)
    NLM=$(ls output/queue/number_learn_*.mp4 output/queue_ar/number_learn_*.mp4 output/queue_id/number_learn_*.mp4 2>/dev/null | wc -l)
    if [[ $NLT -lt $NLM ]]; then
        log "[1/13] number_learn thumbnails ($NLT/$NLM)..."
        python3 -u scripts/generate_number_learn_long.py --regen-meta >> logs/number_learn.log 2>&1
    fi
fi

# ── Step 2: color_learn (9 × 3 = 27 видео) ───────────────────────────────────
if [[ $FROM_STEP -le 2 ]]; then
    if pgrep -f "generate_color_learn_long.py" > /dev/null; then
        log "[2/13] color_learn running — waiting..."
        while pgrep -f "generate_color_learn_long.py" > /dev/null; do sleep 30; done
    fi
    CL_EN=$(count_done "color_learn" "en")
    CL_AR=$(count_done "color_learn" "ar")
    CL_ID=$(count_done "color_learn" "id")
    CL=$((CL_EN + CL_AR + CL_ID))
    if [[ $CL -ge 27 ]]; then
        skip 2 "color_learn ($CL/27: EN=$CL_EN AR=$CL_AR ID=$CL_ID)"
    else
        log "[2/13] color_learn — $CL/27 done (EN=$CL_EN AR=$CL_AR ID=$CL_ID)..."
        python3 -u scripts/generate_color_learn_long.py >> logs/color_learn.log 2>&1
        log "[2/13] color_learn done."
    fi
    CLT=$(ls output/queue/thumb_color_learn_*.png output/queue_ar/thumb_color_learn_*.png output/queue_id/thumb_color_learn_*.png 2>/dev/null | wc -l)
    CLM=$(ls output/queue/color_learn_*.mp4 output/queue_ar/color_learn_*.mp4 output/queue_id/color_learn_*.mp4 2>/dev/null | wc -l)
    if [[ $CLT -lt $CLM ]]; then
        log "[2/13] color_learn thumbnails ($CLT/$CLM)..."
        python3 -u scripts/generate_color_learn_long.py --regen-meta >> logs/color_learn.log 2>&1
    fi
fi

# ── Step 3: shape_learn (8 × 3 = 24 видео, без текста → EN+AR+ID) ────────────
if [[ $FROM_STEP -le 3 ]]; then
    SL_EN=$(count_done "shape_learn" "en")
    SL_AR=$(count_done "shape_learn" "ar")
    SL_ID=$(count_done "shape_learn" "id")
    SL=$((SL_EN + SL_AR + SL_ID))
    if [[ $SL -ge 24 ]]; then
        skip 3 "shape_learn ($SL/24: EN=$SL_EN AR=$SL_AR ID=$SL_ID)"
    else
        log "[3/13] shape_learn — $SL/24 done (EN=$SL_EN AR=$SL_AR ID=$SL_ID)..."
        python3 -u scripts/generate_shape_learn.py >> logs/shape_learn.log 2>&1
        log "[3/13] shape_learn done."
    fi
    SLT=$(ls output/queue/thumb_shape_learn_*.png output/queue_ar/thumb_shape_learn_*.png output/queue_id/thumb_shape_learn_*.png 2>/dev/null | wc -l)
    SLM=$(ls output/queue/shape_learn_*.mp4 output/queue_ar/shape_learn_*.mp4 output/queue_id/shape_learn_*.mp4 2>/dev/null | wc -l)
    if [[ $SLT -lt $SLM ]]; then
        log "[3/13] shape_learn thumbnails ($SLT/$SLM)..."
        python3 -u scripts/generate_shape_learn.py --regen-meta >> logs/shape_learn.log 2>&1
    fi
fi

# ── Step 4: dance animals (30-мин Manim, EN) ─────────────────────────────────
if [[ $FROM_STEP -le 4 ]]; then
    DA=$(ls output/queue/dance_animals_*.mp4 2>/dev/null | wc -l)
    if [[ $DA -ge 1 ]]; then
        skip 4 "dance_animals ($DA MP4 exists)"
    else
        log "[4/13] dance_animals — рендер ~45-60 мин..."
        python3 -u scripts/generate_dance_long.py --themes animals >> logs/dance_long.log 2>&1
        log "[4/13] dance_animals done."
    fi
fi

# ── Step 5: dance fruits (30-мин Manim, EN) ──────────────────────────────────
if [[ $FROM_STEP -le 5 ]]; then
    DF=$(ls output/queue/dance_fruits_*.mp4 2>/dev/null | wc -l)
    if [[ $DF -ge 1 ]]; then
        skip 5 "dance_fruits ($DF MP4 exists)"
    else
        log "[5/13] dance_fruits — рендер ~45-60 мин..."
        python3 -u scripts/generate_dance_long.py --themes fruits >> logs/dance_long.log 2>&1
        log "[5/13] dance_fruits done."
    fi
fi

# ── Step 6: dance vegetables (30-мин Manim, EN) ──────────────────────────────
if [[ $FROM_STEP -le 6 ]]; then
    DV=$(ls output/queue/dance_vegetables_*.mp4 2>/dev/null | wc -l)
    if [[ $DV -ge 1 ]]; then
        skip 6 "dance_vegetables ($DV MP4 exists)"
    else
        log "[6/13] dance_vegetables — рендер ~45-60 мин..."
        python3 -u scripts/generate_dance_long.py --themes vegetables >> logs/dance_long.log 2>&1
        log "[6/13] dance_vegetables done."
    fi
fi

# ── Step 7: character_dialogue (4 эпизода × 3 языка = 12 видео) ──────────────
if [[ $FROM_STEP -le 7 ]]; then
    CD=$(ls output/queue/character_dialogue_*.mp4 output/queue_ar/character_dialogue_*.mp4 output/queue_id/character_dialogue_*.mp4 2>/dev/null | wc -l)
    if [[ $CD -ge 12 ]]; then
        skip 7 "character_dialogue ($CD/12 MP4s exist)"
    else
        log "[7/13] character_dialogue — $CD/12 done..."
        python3 -u scripts/generate_character_dialogue_long.py >> logs/character_dialogue.log 2>&1
        log "[7/13] character_dialogue done."
    fi
fi

# ── Step 8: lullaby (6 видео × 3 языка = 18, без текста → EN+AR+ID) ─────────
if [[ $FROM_STEP -le 8 ]]; then
    LL=$(ls output/queue/lullaby_*.mp4 output/queue_ar/lullaby_*.mp4 output/queue_id/lullaby_*.mp4 2>/dev/null | wc -l)
    if [[ $LL -ge 18 ]]; then
        skip 8 "lullaby ($LL/18 MP4s exist)"
    else
        log "[8/13] lullaby — $LL/18 done..."
        python3 -u scripts/generate_lullaby.py >> logs/lullaby.log 2>&1
        log "[8/13] lullaby done."
    fi
fi

# ── Step 9: nursery_ar (3 песни → AR queue) ───────────────────────────────────
if [[ $FROM_STEP -le 9 ]]; then
    NAR=$(ls output/queue_ar/nursery_*.mp4 2>/dev/null | wc -l)
    if [[ $NAR -ge 3 ]]; then
        skip 9 "nursery_ar ($NAR/3 MP4s exist)"
    else
        log "[9/13] nursery_ar — $NAR/3 done..."
        for key in batta_batta ya_matar dajaja; do
            python3 -u scripts/generate_nursery_ar.py --key $key --lang ar >> logs/nursery_ar.log 2>&1
        done
        log "[9/13] nursery_ar done."
    fi
fi

# ── Step 10: nursery_id (6 песен → ID queue) ──────────────────────────────────
if [[ $FROM_STEP -le 10 ]]; then
    NID=$(ls output/queue_id/nursery_*.mp4 2>/dev/null | wc -l)
    if [[ $NID -ge 6 ]]; then
        skip 10 "nursery_id ($NID/6 MP4s exist)"
    else
        log "[10/13] nursery_id — $NID/6 done..."
        for key in balonku cicak naik_kereta pelangi dua_mata kebunku; do
            python3 -u scripts/generate_nursery_id.py --key $key --lang id >> logs/nursery_id.log 2>&1
        done
        log "[10/13] nursery_id done."
    fi
fi

# ── Step 11-13: Thumbnails для всех очередей ──────────────────────────────────
if [[ $FROM_STEP -le 11 ]]; then
    log "[11/13] thumbnails EN..."
    python3 -u scripts/generate_ai_thumbs.py --queue en --backend together >> logs/thumbs_en.log 2>&1
    log "[11/13] thumbnails EN done."
fi

if [[ $FROM_STEP -le 12 ]]; then
    log "[12/13] thumbnails AR..."
    python3 -u scripts/generate_ai_thumbs.py --queue ar --backend together >> logs/thumbs_ar.log 2>&1
    log "[12/13] thumbnails AR done."
fi

if [[ $FROM_STEP -le 13 ]]; then
    log "[13/13] thumbnails ID..."
    python3 -u scripts/generate_ai_thumbs.py --queue id --backend together >> logs/thumbs_id.log 2>&1
    log "[13/13] thumbnails ID done."
fi

# ── Итог ──────────────────────────────────────────────────────────────────────
log "════════════════════════════════════════════════════════"
log "ВСЕ ДЛИННЫЕ ВИДЕО ГОТОВЫ"
log "EN queue:  $(ls output/queue/*.mp4 2>/dev/null | wc -l) видео,  $(ls output/queue/thumb_*.png 2>/dev/null | wc -l) thumbs"
log "AR queue:  $(ls output/queue_ar/*.mp4 2>/dev/null | wc -l) видео,  $(ls output/queue_ar/thumb_*.png 2>/dev/null | wc -l) thumbs"
log "ID queue:  $(ls output/queue_id/*.mp4 2>/dev/null | wc -l) видео,  $(ls output/queue_id/thumb_*.png 2>/dev/null | wc -l) thumbs"
log "════════════════════════════════════════════════════════"
log "Для шортсов (после завершения длинных): bash scripts/run_shorts.sh"
