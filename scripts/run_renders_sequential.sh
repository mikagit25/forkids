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
# 14  | number_learn v2    | generate_number_learn_long.py --force | EN+AR+ID | 30 (новый алгоритм: муз., спрайты)
# 15  | thumbnails v2      | generate_ai_thumbs.py (EN+AR+ID)   | все      | новые превью для v2
# 16  | special_mechanics  | generate_special_mechanics.py       | EN+AR+ID | 8×3=24 (Hide&Seek/Shadows/Bubbles/Mirror/...)
# 17  | emotions_ocean     | generate_emotions_ocean.py          | EN+AR+ID | 25×3=75 (Emotions/Ocean/Transport/Professions)
# 18  | wiggle_party       | generate_wiggle_party.py            | EN+AR+ID | 5×3=15
# 19  | thumbnails final   | generate_ai_thumbs.py (EN+AR+ID)   | все      | финальный sweep
# 20  | shape_roundelay    | generate_shape_roundelay.py         | EN+AR+ID | 8×3=24
# 21  | ocd_vehicles       | generate_ocd_vehicles.py            | EN+AR+ID | 6×3=18
# 22  | construction_music | generate_construction_music.py      | EN+AR+ID | 6×3=18
# 23  | nature_calm        | generate_nature_calm.py             | EN+AR+ID | 6×3=18
# 24  | satisfying_3fmt    | generate_satisfying_3fmt.py         | EN+AR+ID | 8×3=24
# 25  | sensory_loop       | generate_sensory_loop.py            | EN+AR+ID | 14×3=42
# 26  | transform_block    | generate_transform_block.py         | EN+AR+ID | 20×3=60
# 27  | stars_bubbles      | generate_stars_bubbles.py           | EN+AR+ID | 1×3=3
# 28  | dance_fruits_group | generate_dance_fruits_group.py      | EN+AR+ID | 8×3=24
# 29  | dance_fruits_2stage| generate_dance_fruits_2stage.py     | EN+AR+ID | 14×3=42
# 30  | dance_pet          | generate_dance_pet.py               | EN+AR+ID | 10×2×3=60
# 31  | thumbnails final2  | generate_ai_thumbs.py (EN+AR+ID)   | все      | финальный sweep
# 32  | shape_learn_v2     | generate_shape_learn_v2.py          | EN+AR+ID | 8×3=24 (3D+DVD bounce+fly-in count)
# 33  | thumbnails final3  | generate_ai_thumbs.py (EN+AR+ID)   | все      | sweep после v2
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

# ── PAUSE FLAG: AR videos with on-screen text ─────────────────────────────────
# Set to 1 to skip generating AR versions of text-heavy content (color_learn,
# number_learn, character_dialogue, nursery_ar) until Arabic text is reviewed
# and corrected by a native speaker.
# Affects steps: 1 (number_learn AR), 2 (color_learn AR), 7 (character_dialogue AR), 9 (nursery_ar)
# Safe to keep: shape_learn AR, lullaby AR, dance AR (no on-screen text)
PAUSE_AR_TEXT=1
# ─────────────────────────────────────────────────────────────────────────────

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
    # PAUSE_AR_TEXT: count AR as "done" so script skips AR generation
    if [[ $PAUSE_AR_TEXT -eq 1 ]]; then NL_AR=10; fi
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
    # PAUSE_AR_TEXT: count AR as "done" so script skips AR generation
    if [[ $PAUSE_AR_TEXT -eq 1 ]]; then CL_AR=9; fi
    CL=$((CL_EN + CL_AR + CL_ID))
    if [[ $CL -ge 27 ]]; then
        skip 2 "color_learn ($CL/27: EN=$CL_EN AR=$CL_AR ID=$CL_ID)"
    else
        log "[2/13] color_learn — $CL/27 done (EN=$CL_EN AR=$CL_AR ID=$CL_ID)..."
        python3 -u scripts/generate_color_learn_long.py --force >> logs/color_learn.log 2>&1
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
    CD_EN=$(ls output/queue/character_dialogue_*.mp4 2>/dev/null | wc -l)
    CD_AR=$(ls output/queue_ar/character_dialogue_*.mp4 2>/dev/null | wc -l)
    CD_ID=$(ls output/queue_id/character_dialogue_*.mp4 2>/dev/null | wc -l)
    # PAUSE_AR_TEXT: count AR as "done" so script skips AR generation
    if [[ $PAUSE_AR_TEXT -eq 1 ]]; then CD_AR=4; fi
    CD=$((CD_EN + CD_AR + CD_ID))
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
    # PAUSE_AR_TEXT: skip entirely until Arabic text is reviewed
    if [[ $PAUSE_AR_TEXT -eq 1 ]]; then
        skip 9 "nursery_ar — PAUSE_AR_TEXT=1 (AR text under review)"
    else
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
    fi  # end PAUSE_AR_TEXT check
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
    log "[11/15] thumbnails EN..."
    python3 -u scripts/generate_ai_thumbs.py --queue en --backend together >> logs/thumbs_en.log 2>&1
    log "[11/15] thumbnails EN done."
fi

if [[ $FROM_STEP -le 12 ]]; then
    log "[12/15] thumbnails AR..."
    python3 -u scripts/generate_ai_thumbs.py --queue ar --backend together >> logs/thumbs_ar.log 2>&1
    log "[12/15] thumbnails AR done."
fi

if [[ $FROM_STEP -le 13 ]]; then
    log "[13/15] thumbnails ID..."
    python3 -u scripts/generate_ai_thumbs.py --queue id --backend together >> logs/thumbs_id.log 2>&1
    log "[13/15] thumbnails ID done."
fi

# ── Step 14: number_learn RE-RENDER (обновлённый алгоритм: новые спрайты, новая музыка) ──
# Перегенерирует все 30 number_learn видео поверх старых → публикуются как новые видео.
if [[ $FROM_STEP -le 14 ]]; then
    NL_RE=$(ls output/queue/number_learn_*.mp4 output/queue_ar/number_learn_*.mp4 output/queue_id/number_learn_*.mp4 2>/dev/null | wc -l)
    log "[14/15] number_learn RE-RENDER (updated algorithm) — $NL_RE old files will be replaced..."
    python3 -u scripts/generate_number_learn_long.py --force >> logs/number_learn_v2.log 2>&1
    log "[14/15] number_learn RE-RENDER done."
fi

# ── Step 15: thumbnails для переренденных number_learn ──────────────────────────
if [[ $FROM_STEP -le 15 ]]; then
    log "[15/15] thumbnails for re-rendered number_learn (EN+AR+ID)..."
    python3 -u scripts/generate_ai_thumbs.py --queue en --backend together >> logs/thumbs_en.log 2>&1
    python3 -u scripts/generate_ai_thumbs.py --queue ar --backend together >> logs/thumbs_ar.log 2>&1
    python3 -u scripts/generate_ai_thumbs.py --queue id --backend together >> logs/thumbs_id.log 2>&1
    log "[15/15] thumbnails done."
fi

# ── Step 16: special_mechanics (8 эпизодов × 3 канала = 24 видео) ─────────────
if [[ $FROM_STEP -le 16 ]]; then
    SM=$(ls output/queue/sm*.mp4 output/queue_ar/sm*.mp4 output/queue_id/sm*.mp4 2>/dev/null | wc -l)
    if [[ $SM -ge 24 ]]; then
        skip 16 "special_mechanics ($SM/24 MP4s exist)"
    else
        log "[16/19] special_mechanics — $SM/24 done..."
        python3 -u scripts/generate_special_mechanics.py --videos all >> logs/special_mechanics.log 2>&1
        log "[16/19] special_mechanics done."
    fi
fi

# ── Step 17: emotions_ocean (25 эпизодов × 3 канала = 75 видео) ───────────────
if [[ $FROM_STEP -le 17 ]]; then
    EO=$(ls output/queue/eo_*.mp4 output/queue_ar/eo_*.mp4 output/queue_id/eo_*.mp4 2>/dev/null | wc -l)
    if [[ $EO -ge 75 ]]; then
        skip 17 "emotions_ocean ($EO/75 MP4s exist)"
    else
        log "[17/19] emotions_ocean — $EO/75 done..."
        python3 -u scripts/generate_emotions_ocean.py --videos all >> logs/emotions_ocean.log 2>&1
        log "[17/19] emotions_ocean done."
    fi
fi

# ── Step 18: wiggle_party (5 тем × 3 канала = 15 видео, text-free) ────────────
if [[ $FROM_STEP -le 18 ]]; then
    WP=$(ls output/queue/wiggle_*.mp4 2>/dev/null | wc -l)
    if [[ $WP -ge 5 ]]; then
        skip 18 "wiggle_party ($WP/5 EN MP4s exist)"
    else
        log "[18/19] wiggle_party — $WP/5 done (text-free, 1 render → 3 channels)..."
        python3 -u scripts/generate_wiggle_party.py --themes all >> logs/wiggle_party.log 2>&1
        log "[18/19] wiggle_party done."
    fi
fi

# ── Step 19: thumbnails финальные ─────────────────────────────────────────────
if [[ $FROM_STEP -le 19 ]]; then
    log "[19/19] final thumbnails sweep (EN+AR+ID)..."
    python3 -u scripts/generate_ai_thumbs.py --queue en --backend together >> logs/thumbs_en.log 2>&1
    python3 -u scripts/generate_ai_thumbs.py --queue ar --backend together >> logs/thumbs_ar.log 2>&1
    python3 -u scripts/generate_ai_thumbs.py --queue id --backend together >> logs/thumbs_id.log 2>&1
    log "[19/19] final thumbnails done."
fi

# ── Step 20: shape_roundelay (8 эпизодов × 3 канала = 24 видео) ──────────────
if [[ $FROM_STEP -le 20 ]]; then
    SR=$(ls output/queue/shape_roundelay_*.mp4 output/queue_ar/shape_roundelay_*.mp4 output/queue_id/shape_roundelay_*.mp4 2>/dev/null | wc -l)
    if [[ $SR -ge 24 ]]; then
        skip 20 "shape_roundelay ($SR/24 MP4s exist)"
    else
        log "[20/31] shape_roundelay — $SR/24 done..."
        python3 -u scripts/generate_shape_roundelay.py >> logs/shape_roundelay.log 2>&1
        log "[20/31] shape_roundelay done."
    fi
fi

# ── Step 21: ocd_vehicles (6 эпизодов × 3 канала = 18 видео) ─────────────────
if [[ $FROM_STEP -le 21 ]]; then
    OCV=$(ls output/queue/ocd_vehicles_*.mp4 output/queue_ar/ocd_vehicles_*.mp4 output/queue_id/ocd_vehicles_*.mp4 2>/dev/null | wc -l)
    if [[ $OCV -ge 18 ]]; then
        skip 21 "ocd_vehicles ($OCV/18 MP4s exist)"
    else
        log "[21/31] ocd_vehicles — $OCV/18 done..."
        python3 -u scripts/generate_ocd_vehicles.py >> logs/ocd_vehicles.log 2>&1
        log "[21/31] ocd_vehicles done."
    fi
fi

# ── Step 22: construction_music (6 эпизодов × 3 канала = 18 видео) ───────────
if [[ $FROM_STEP -le 22 ]]; then
    CM=$(ls output/queue/construction_music_*.mp4 output/queue_ar/construction_music_*.mp4 output/queue_id/construction_music_*.mp4 2>/dev/null | wc -l)
    if [[ $CM -ge 18 ]]; then
        skip 22 "construction_music ($CM/18 MP4s exist)"
    else
        log "[22/31] construction_music — $CM/18 done..."
        python3 -u scripts/generate_construction_music.py >> logs/construction_music.log 2>&1
        log "[22/31] construction_music done."
    fi
fi

# ── Step 23: nature_calm (6 эпизодов × 3 канала = 18 видео) ─────────────────
if [[ $FROM_STEP -le 23 ]]; then
    NC=$(ls output/queue/nature_calm_*.mp4 output/queue_ar/nature_calm_*.mp4 output/queue_id/nature_calm_*.mp4 2>/dev/null | wc -l)
    if [[ $NC -ge 18 ]]; then
        skip 23 "nature_calm ($NC/18 MP4s exist)"
    else
        log "[23/31] nature_calm — $NC/18 done..."
        python3 -u scripts/generate_nature_calm.py >> logs/nature_calm.log 2>&1
        log "[23/31] nature_calm done."
    fi
fi

# ── Step 24: satisfying_3fmt (8 эпизодов × 3 канала = 24 видео) ──────────────
if [[ $FROM_STEP -le 24 ]]; then
    SF=$(ls output/queue/satisfying_*.mp4 output/queue_ar/satisfying_*.mp4 output/queue_id/satisfying_*.mp4 2>/dev/null | wc -l)
    if [[ $SF -ge 24 ]]; then
        skip 24 "satisfying_3fmt ($SF/24 MP4s exist)"
    else
        log "[24/31] satisfying_3fmt — $SF/24 done..."
        python3 -u scripts/generate_satisfying_3fmt.py >> logs/satisfying_3fmt.log 2>&1
        log "[24/31] satisfying_3fmt done."
    fi
fi

# ── Step 25: sensory_loop (14 эпизодов × 3 канала = 42 видео) ────────────────
if [[ $FROM_STEP -le 25 ]]; then
    SL=$(ls output/queue/sensory_*.mp4 output/queue_ar/sensory_*.mp4 output/queue_id/sensory_*.mp4 2>/dev/null | wc -l)
    if [[ $SL -ge 42 ]]; then
        skip 25 "sensory_loop ($SL/42 MP4s exist)"
    else
        log "[25/31] sensory_loop — $SL/42 done..."
        python3 -u scripts/generate_sensory_loop.py >> logs/sensory_loop.log 2>&1
        log "[25/31] sensory_loop done."
    fi
fi

# ── Step 26: transform_block (20 видео × 3 канала = 60 видео) ─────────────────
if [[ $FROM_STEP -le 26 ]]; then
    TB=$(ls output/queue/transform_*.mp4 output/queue_ar/transform_*.mp4 output/queue_id/transform_*.mp4 2>/dev/null | wc -l)
    if [[ $TB -ge 60 ]]; then
        skip 26 "transform_block ($TB/60 MP4s exist)"
    else
        log "[26/31] transform_block — $TB/60 done..."
        python3 -u scripts/generate_transform_block.py >> logs/transform_block.log 2>&1
        log "[26/31] transform_block done."
    fi
fi

# ── Step 27: stars_bubbles (1 видео × 3 канала = 3 видео) ─────────────────────
if [[ $FROM_STEP -le 27 ]]; then
    SB=$(ls output/queue/stars_bubbles_*.mp4 output/queue_ar/stars_bubbles_*.mp4 output/queue_id/stars_bubbles_*.mp4 2>/dev/null | wc -l)
    if [[ $SB -ge 3 ]]; then
        skip 27 "stars_bubbles ($SB/3 MP4s exist)"
    else
        log "[27/31] stars_bubbles — $SB/3 done..."
        python3 -u scripts/generate_stars_bubbles.py >> logs/stars_bubbles.log 2>&1
        log "[27/31] stars_bubbles done."
    fi
fi

# ── Step 28: dance_fruits_group (8 видео × 3 канала = 24 видео) ──────────────
if [[ $FROM_STEP -le 28 ]]; then
    FG=$(ls output/queue/fruits_group_*.mp4 output/queue_ar/fruits_group_*.mp4 output/queue_id/fruits_group_*.mp4 2>/dev/null | wc -l)
    if [[ $FG -ge 24 ]]; then
        skip 28 "dance_fruits_group ($FG/24 MP4s exist)"
    else
        log "[28/31] dance_fruits_group — $FG/24 done..."
        python3 -u scripts/generate_dance_fruits_group.py --videos all >> logs/dance_fruits_group.log 2>&1
        log "[28/31] dance_fruits_group done."
    fi
fi

# ── Step 29: dance_fruits_2stage (14 видео × 3 канала = 42 видео) ─────────────
if [[ $FROM_STEP -le 29 ]]; then
    F2=$(ls output/queue/fruits2s_*.mp4 output/queue_ar/fruits2s_*.mp4 output/queue_id/fruits2s_*.mp4 2>/dev/null | wc -l)
    if [[ $F2 -ge 42 ]]; then
        skip 29 "dance_fruits_2stage ($F2/42 MP4s exist)"
    else
        log "[29/31] dance_fruits_2stage — $F2/42 done..."
        python3 -u scripts/generate_dance_fruits_2stage.py --videos all >> logs/dance_fruits_2stage.log 2>&1
        log "[29/31] dance_fruits_2stage done."
    fi
fi

# ── Step 30: dance_pet (10 зверей × 2 вида × 3 канала = 60 видео) ────────────
if [[ $FROM_STEP -le 30 ]]; then
    DP=$(ls output/queue/pet_*.mp4 output/queue_ar/pet_*.mp4 output/queue_id/pet_*.mp4 2>/dev/null | wc -l)
    if [[ $DP -ge 60 ]]; then
        skip 30 "dance_pet ($DP/60 MP4s exist)"
    else
        log "[30/31] dance_pet — $DP/60 done..."
        for animal in cat dog rabbit fish turtle parrot hamster guinea_pig duck kitten; do
            python3 -u scripts/generate_dance_pet.py --animal "$animal" --type A >> logs/dance_pet.log 2>&1
            python3 -u scripts/generate_dance_pet.py --animal "$animal" --type B >> logs/dance_pet.log 2>&1
        done
        log "[30/31] dance_pet done."
    fi
fi

# ── Step 31: финальные thumbnails (полный sweep) ──────────────────────────────
if [[ $FROM_STEP -le 31 ]]; then
    log "[31/33] final thumbnails sweep (EN+AR+ID)..."
    python3 -u scripts/generate_ai_thumbs.py --queue en --backend together >> logs/thumbs_en.log 2>&1
    python3 -u scripts/generate_ai_thumbs.py --queue ar --backend together >> logs/thumbs_ar.log 2>&1
    python3 -u scripts/generate_ai_thumbs.py --queue id --backend together >> logs/thumbs_id.log 2>&1
    log "[31/33] final thumbnails done."
fi

# ── Step 32: shape_learn_v2 (8 фигур × 3 канала = 24 видео, 3D+DVD+fly-in) ───
if [[ $FROM_STEP -le 32 ]]; then
    SL2=$(ls output/queue/shape_learn2_*.mp4 output/queue_ar/shape_learn2_*.mp4 output/queue_id/shape_learn2_*.mp4 2>/dev/null | wc -l)
    if [[ $SL2 -ge 24 ]]; then
        skip 32 "shape_learn_v2 ($SL2/24 MP4s exist)"
    else
        log "[32/35] shape_learn_v2 — $SL2/24 done..."
        python3 -u scripts/generate_shape_learn_v2.py >> logs/shape_learn_v2.log 2>&1
        log "[32/35] shape_learn_v2 done."
    fi
fi

# ── Step 33: финальные thumbnails после v2 ────────────────────────────────────
if [[ $FROM_STEP -le 33 ]]; then
    log "[33/35] final thumbnails v2 sweep (EN+AR+ID)..."
    python3 -u scripts/generate_ai_thumbs.py --queue en --backend together >> logs/thumbs_en.log 2>&1
    python3 -u scripts/generate_ai_thumbs.py --queue ar --backend together >> logs/thumbs_ar.log 2>&1
    python3 -u scripts/generate_ai_thumbs.py --queue id --backend together >> logs/thumbs_id.log 2>&1
    log "[33/35] final thumbnails v2 done."
fi

# ── Step 34-41: re-render ALL lullaby themes with fixed transparent sprites ────
# Sprites were fixed (black/white bg removed → contour transparency).
# Runs once: if hold/lullaby_rect_sprites/DONE exists, skips (already re-rendered).
if [[ $FROM_STEP -le 34 ]]; then
    HOLD_LUL="output/hold/lullaby_rect_sprites"
    if [[ -f "$HOLD_LUL/DONE" ]]; then
        LUL_Q=$(ls output/queue/lullaby_*.mp4 output/queue_ar/lullaby_*.mp4 output/queue_id/lullaby_*.mp4 2>/dev/null | wc -l)
        skip 34 "lullaby transparent re-render already done ($LUL_Q videos in queue)"
    else
        mkdir -p "$HOLD_LUL"
        # Move all existing lullaby files to hold (may have rectangular sprite glows)
        for q in output/queue output/queue_ar output/queue_id; do
            for f in "$q"/lullaby_*.mp4 "$q"/meta_lullaby_*.yaml "$q"/thumb_lullaby_*.png; do
                [[ -f "$f" ]] && mv "$f" "$HOLD_LUL/" 2>/dev/null && true
            done
        done
        # Delete all cached loop files → force Remotion re-render with transparent sprites
        rm -f output/tmp_lullaby/loop_*.mp4
        log "[34/42] Moved old lullaby files to hold. Re-rendering all 6 themes with transparent sprites + classical music..."
        python3 -u scripts/generate_lullaby.py >> logs/lullaby_v2.log 2>&1
        touch "$HOLD_LUL/DONE"
        log "[34/42] All lullaby themes re-rendered."
    fi
fi

# ── Step 35: thumbnails for re-rendered lullaby files ─────────────────────────
if [[ $FROM_STEP -le 35 ]]; then
    log "[35/42] thumbnails for lullaby re-render (all queues)..."
    python3 -u scripts/generate_ai_thumbs.py --queue en --backend together >> logs/thumbs_en.log 2>&1
    python3 -u scripts/generate_ai_thumbs.py --queue ar --backend together >> logs/thumbs_ar.log 2>&1
    python3 -u scripts/generate_ai_thumbs.py --queue id --backend together >> logs/thumbs_id.log 2>&1
    log "[35/42] thumbnails done."
fi

# Steps 36-41 consolidated into step 34 (moved all old files + re-rendered all themes at once)

# ── Step 42: final thumbnails sweep after all lullaby videos ──────────────────
if [[ $FROM_STEP -le 42 ]]; then
    log "[42/44] final thumbnails — all lullaby videos..."
    python3 -u scripts/generate_ai_thumbs.py --queue en --backend together >> logs/thumbs_en.log 2>&1
    python3 -u scripts/generate_ai_thumbs.py --queue ar --backend together >> logs/thumbs_ar.log 2>&1
    python3 -u scripts/generate_ai_thumbs.py --queue id --backend together >> logs/thumbs_id.log 2>&1
    log "[42/44] final thumbnails done."
fi

# ── Step 43: Mozart calm videos (3 × 60 min, EN only, stars/garden/ocean) ─────
if [[ $FROM_STEP -le 43 ]]; then
    MOZ_TOTAL=$(ls output/queue/mozart_*.mp4 2>/dev/null | wc -l)
    if [[ $MOZ_TOTAL -ge 3 ]]; then
        skip 43 "Mozart calm videos ($MOZ_TOTAL videos already generated)"
    else
        log "[43/46] Mozart calm videos — romance/minuet/rondo (3 × 60 min, EN)..."
        python3 -u scripts/generate_mozart_calm.py >> logs/mozart_calm.log 2>&1
        log "[43/46] Mozart calm done."
    fi
fi

# ── Step 44: thumbnails for Mozart calm videos ────────────────────────────────
if [[ $FROM_STEP -le 44 ]]; then
    log "[44/46] thumbnails — Mozart calm (EN queue)..."
    python3 -u scripts/generate_ai_thumbs.py --queue en --backend together >> logs/thumbs_en.log 2>&1
    log "[44/46] Mozart thumbnails done."
fi

# ── Step 45: classical visualizer — 7 pieces × 3 channels = 21 videos ─────────
# Pieces: Vaughan Williams + Mozart (×3) + Beethoven 5 + Verdi Traviata + Telemann Flute
# THEME ROTATION: each 60-min video cycles through 4 visual themes (15 min each).
# 12 shared Remotion loops (4 themes × 3 channels) are rendered once, reused for all pieces.
if [[ $FROM_STEP -le 45 ]]; then
    CV_TOTAL=$(ls output/queue/classical_*_en_*.mp4 \
                  output/queue_ar/classical_*_ar_*.mp4 \
                  output/queue_id/classical_*_id_*.mp4 2>/dev/null | wc -l)
    if [[ $CV_TOTAL -ge 21 ]]; then
        skip 45 "classical visualizer ($CV_TOTAL / 21 videos already generated)"
    else
        log "[45/48] classical visualizer — 7 pieces × 3 channels = 21 videos (60 min each, theme rotation)..."
        python3 -u scripts/generate_classical_visualizer.py >> logs/classical_visualizer.log 2>&1
        log "[45/48] classical visualizer done."
    fi
fi

# ── Step 46: thumbnails for classical visualizer ───────────────────────────────
if [[ $FROM_STEP -le 46 ]]; then
    log "[46/48] thumbnails — classical visualizer (all queues)..."
    python3 -u scripts/generate_ai_thumbs.py --queue en --backend together >> logs/thumbs_en.log 2>&1
    python3 -u scripts/generate_ai_thumbs.py --queue ar --backend together >> logs/thumbs_ar.log 2>&1
    python3 -u scripts/generate_ai_thumbs.py --queue id --backend together >> logs/thumbs_id.log 2>&1
    log "[46/48] classical visualizer thumbnails done."
fi

# ── Step 47: shape_roundelay v2 — N shapes per episode, thumbnail = video ─────
# Episode N has exactly N shape types. Titles: "1 Shape Roundelay", "2 Shapes", ...
if [[ $FROM_STEP -le 47 ]]; then
    SR2_TOTAL=$(ls output/queue/shape_roundelay_*_$(date +%Y%m%d).mp4 \
                   output/queue_ar/shape_roundelay_*_$(date +%Y%m%d).mp4 \
                   output/queue_id/shape_roundelay_*_$(date +%Y%m%d).mp4 2>/dev/null | wc -l)
    if [[ $SR2_TOTAL -ge 24 ]]; then
        skip 47 "shape_roundelay v2 ($SR2_TOTAL / 24 videos already generated)"
    else
        log "[47/48] shape_roundelay v2 — 8 eps × 3 channels = 24 videos (N shapes = episode N)..."
        python3 -u scripts/generate_shape_roundelay.py >> logs/shape_roundelay.log 2>&1
        log "[47/48] shape_roundelay v2 done."
    fi
fi

# ── Step 48: final thumbnails sweep ───────────────────────────────────────────
if [[ $FROM_STEP -le 48 ]]; then
    log "[48/48] final thumbnails sweep (all queues)..."
    python3 -u scripts/generate_ai_thumbs.py --queue en --backend together >> logs/thumbs_en.log 2>&1
    python3 -u scripts/generate_ai_thumbs.py --queue ar --backend together >> logs/thumbs_ar.log 2>&1
    python3 -u scripts/generate_ai_thumbs.py --queue id --backend together >> logs/thumbs_id.log 2>&1
    log "[48/48] final thumbnails done."
fi

# ── Итог ──────────────────────────────────────────────────────────────────────
log "════════════════════════════════════════════════════════"
log "ВСЕ ДЛИННЫЕ ВИДЕО ГОТОВЫ"
log "EN queue:  $(ls output/queue/*.mp4 2>/dev/null | wc -l) видео,  $(ls output/queue/thumb_*.png 2>/dev/null | wc -l) thumbs"
log "AR queue:  $(ls output/queue_ar/*.mp4 2>/dev/null | wc -l) видео,  $(ls output/queue_ar/thumb_*.png 2>/dev/null | wc -l) thumbs"
log "ID queue:  $(ls output/queue_id/*.mp4 2>/dev/null | wc -l) видео,  $(ls output/queue_id/thumb_*.png 2>/dev/null | wc -l) thumbs"
log "════════════════════════════════════════════════════════"
log "Для шортсов (после завершения длинных): bash scripts/run_shorts.sh"
