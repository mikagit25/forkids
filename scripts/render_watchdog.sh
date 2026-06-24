#!/bin/bash
# Watchdog for the sequential render pipeline.
# Runs every 30 min via cron. If the runner died and renders are incomplete,
# restarts it and sends a Telegram alert.
#
# Cron:
#   */30 * * * * bash /opt/kids_channel/scripts/render_watchdog.sh >> /opt/kids_channel/logs/watchdog.log 2>&1

set -euo pipefail
cd /opt/kids_channel

BOT_TOKEN="8657721269:AAEkhJ92vHR4K1CkA14nFcy0_bA95c38QZk"
CHAT_ID="209381269"
LOCK_FILE="/tmp/kids_render_watchdog.lock"
RUNNER_SCRIPT="scripts/run_renders_sequential.sh"
LOG_RENDER="logs/renders_sequential.log"

# ── Helpers ───────────────────────────────────────────────────────────────
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

tg() {
    local msg="$1"
    curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
        -H "Content-Type: application/json" \
        -d "{\"chat_id\":\"${CHAT_ID}\",\"text\":\"${msg}\",\"parse_mode\":\"HTML\"}" \
        --max-time 10 > /dev/null 2>&1 || true
}

# ── Prevent parallel watchdog runs ────────────────────────────────────────
if [ -f "$LOCK_FILE" ]; then
    LOCK_PID=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
    if [[ -n "$LOCK_PID" ]] && kill -0 "$LOCK_PID" 2>/dev/null; then
        log "Another watchdog instance running (PID $LOCK_PID). Exiting."
        exit 0
    fi
fi
echo $$ > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

# ── Count rendered files ───────────────────────────────────────────────────
count_mp4() {
    local total=0
    for pattern in "$@"; do
        total=$((total + $(ls $pattern 2>/dev/null | wc -l)))
    done
    echo $total
}

NL_EN=$(count_mp4 "output/queue/number_learn_*.mp4" "uploaded/number_learn_*_en_*.mp4")
NL_AR=$(count_mp4 "output/queue_ar/number_learn_*.mp4" "uploaded/number_learn_*_ar_*.mp4")
NL_ID=$(count_mp4 "output/queue_id/number_learn_*.mp4" "uploaded/number_learn_*_id_*.mp4")
CL_EN=$(count_mp4 "output/queue/color_learn_*.mp4" "uploaded/color_learn_*_en_*.mp4")
CL_AR=$(count_mp4 "output/queue_ar/color_learn_*.mp4" "uploaded/color_learn_*_ar_*.mp4")
CL_ID=$(count_mp4 "output/queue_id/color_learn_*.mp4" "uploaded/color_learn_*_id_*.mp4")
SL_EN=$(count_mp4 "output/queue/shape_learn_*.mp4" "uploaded/shape_learn_*_en_*.mp4")
SL_AR=$(count_mp4 "output/queue_ar/shape_learn_*.mp4" "uploaded/shape_learn_*_ar_*.mp4")
SL_ID=$(count_mp4 "output/queue_id/shape_learn_*.mp4" "uploaded/shape_learn_*_id_*.mp4")
CD_EN=$(count_mp4 "output/queue/character_dialogue_*.mp4" "uploaded/character_dialogue_*_en_*.mp4")
CD_AR=$(count_mp4 "output/queue_ar/character_dialogue_*.mp4" "uploaded/character_dialogue_*_ar_*.mp4")
CD_ID=$(count_mp4 "output/queue_id/character_dialogue_*.mp4" "uploaded/character_dialogue_*_id_*.mp4")
SM_EN=$(count_mp4 "output/queue/sm*.mp4")
SM_AR=$(count_mp4 "output/queue_ar/sm*.mp4")
SM_ID=$(count_mp4 "output/queue_id/sm*.mp4")
SR_EN=$(count_mp4 "output/queue/shape_roundelay_*.mp4")
SR_AR=$(count_mp4 "output/queue_ar/shape_roundelay_*.mp4")
SR_ID=$(count_mp4 "output/queue_id/shape_roundelay_*.mp4")
OCV_EN=$(count_mp4 "output/queue/ocd_vehicles_*.mp4")
NC_EN=$(count_mp4 "output/queue/nature_calm_*.mp4")
TB_EN=$(count_mp4 "output/queue/transform_*.mp4")
FG_EN=$(count_mp4 "output/queue/fruits_group_*.mp4")
F2_EN=$(count_mp4 "output/queue/fruits2s_*.mp4")
SL2_EN=$(count_mp4 "output/queue/shape_learn2_*.mp4")
SL2_AR=$(count_mp4 "output/queue_ar/shape_learn2_*.mp4")
SL2_ID=$(count_mp4 "output/queue_id/shape_learn2_*.mp4")

NL_TOTAL=$((NL_EN + NL_AR + NL_ID))
CL_TOTAL=$((CL_EN + CL_AR + CL_ID))
SL_TOTAL=$((SL_EN + SL_AR + SL_ID))
CD_TOTAL=$((CD_EN + CD_AR + CD_ID))
SM_TOTAL=$((SM_EN + SM_AR + SM_ID))
SR_TOTAL=$((SR_EN + SR_AR + SR_ID))
SL2_TOTAL=$((SL2_EN + SL2_AR + SL2_ID))
NEW_TOTAL=$((OCV_EN + NC_EN + TB_EN + FG_EN + F2_EN))
GRAND_TOTAL=$((NL_TOTAL + CL_TOTAL + SL_TOTAL + CD_TOTAL + SM_TOTAL + SR_TOTAL + SL2_TOTAL + NEW_TOTAL))
# 30 number + 27 color + 24 shape_v1 + 12 character_dialogue + 24 special_mechanics
# + 24 shape_roundelay + 24 shape_learn_v2 + new series (tracked partially)
EXPECTED=165  # raised: +24 for shape_learn_v2

log "Progress: NL=$NL_TOTAL/30 CL=$CL_TOTAL/27 SL=$SL_TOTAL/24 CD=$CD_TOTAL/12 SM=$SM_TOTAL/24 SR=$SR_TOTAL/24 SL2=$SL2_TOTAL/24 (total $GRAND_TOTAL/$EXPECTED)"
log "  New: ocd=${OCV_EN} nature=${NC_EN} transform=${TB_EN} fruits_grp=${FG_EN} fruits_2s=${F2_EN}"

# ── Check if already fully done ───────────────────────────────────────────
if [[ $GRAND_TOTAL -ge $EXPECTED ]]; then
    log "All tracked $EXPECTED renders complete. Nothing to do."
    exit 0
fi

# ── Check if runner is alive ──────────────────────────────────────────────
RUNNER_PID=$(pgrep -f "$RUNNER_SCRIPT" 2>/dev/null | head -1 || true)
ANY_RENDER=$(pgrep -f "remotion render" 2>/dev/null | head -1 || true)

ANY_RUNNING=""
[[ -n "$RUNNER_PID" ]] && ANY_RUNNING="runner(PID $RUNNER_PID)"
[[ -n "$ANY_RENDER" ]] && ANY_RUNNING="remotion_render(PID $ANY_RENDER)"

if [[ -n "$ANY_RUNNING" ]]; then
    log "Pipeline is running: $ANY_RUNNING — OK."
    exit 0
fi

# ── Find first incomplete step to restart from ────────────────────────────
# The orchestrator skips already-done steps, so starting from step 7 is always safe.
# We optimize by finding the first step that still has work.
FROM_STEP=7
if [[ $CD_TOTAL -ge 12 ]]; then
    FROM_STEP=16
    [[ $SM_TOTAL -ge 24 ]] && FROM_STEP=20
    [[ $SM_TOTAL -ge 24 && $SR_TOTAL -ge 24 ]] && FROM_STEP=21
    [[ $SM_TOTAL -ge 24 && $SR_TOTAL -ge 24 && $SL2_TOTAL -ge 24 ]] && FROM_STEP=33
fi

# ── Nothing running but renders incomplete → restart ──────────────────────
log "ALERT: Pipeline stopped with $GRAND_TOTAL/$EXPECTED renders done. Restarting from step $FROM_STEP..."

tg "🔄 <b>Kids Channel — Render Watchdog</b>
Pipeline остановился! Перезапускаю с шага $FROM_STEP...

📊 Прогресс:
• numbers: ${NL_TOTAL}/30
• colors:  ${CL_TOTAL}/27
• shapes:  ${SL_TOTAL}/24
• dialogues: ${CD_TOTAL}/12
• special_mechanics: ${SM_TOTAL}/24
• shape_roundelay: ${SR_TOTAL}/24

Итого: ${GRAND_TOTAL}/${EXPECTED}"

nohup bash "$RUNNER_SCRIPT" --from "$FROM_STEP" >> "$LOG_RENDER" 2>&1 &
NEW_PID=$!
log "Restarted runner with PID $NEW_PID"

sleep 5
if kill -0 "$NEW_PID" 2>/dev/null; then
    tg "✅ <b>Kids Channel — Render Watchdog</b>
Перезапуск успешен (PID ${NEW_PID}).
Слежу каждые 30 минут."
    log "Runner PID $NEW_PID alive — restart successful."
else
    tg "❌ <b>Kids Channel — Render Watchdog</b>
Перезапуск ПРОВАЛИЛСЯ (PID ${NEW_PID}).
Нужна ручная проверка: tail -f /opt/kids_channel/logs/renders_sequential.log"
    log "ERROR: Runner PID $NEW_PID died immediately after restart."
    exit 1
fi
