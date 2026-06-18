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

NL_TOTAL=$((NL_EN + NL_AR + NL_ID))
CL_TOTAL=$((CL_EN + CL_AR + CL_ID))
SL_TOTAL=$((SL_EN + SL_AR + SL_ID))
GRAND_TOTAL=$((NL_TOTAL + CL_TOTAL + SL_TOTAL))
EXPECTED=81   # 30 number (10×3) + 27 color (9×3) + 24 shape (8×3)

log "Progress: number=$NL_TOTAL/30  color=$CL_TOTAL/27  shape=$SL_TOTAL/24  (total $GRAND_TOTAL/$EXPECTED)"
log "  EN: NL=$NL_EN CL=$CL_EN SL=$SL_EN  |  AR: NL=$NL_AR CL=$CL_AR SL=$SL_AR  |  ID: NL=$NL_ID CL=$CL_ID SL=$SL_ID"

# ── Check if already fully done ───────────────────────────────────────────
if [[ $GRAND_TOTAL -ge $EXPECTED ]]; then
    log "All $EXPECTED renders complete. Nothing to do."
    exit 0
fi

# ── Check if runner is alive ──────────────────────────────────────────────
RUNNER_PID=$(pgrep -f "$RUNNER_SCRIPT" 2>/dev/null | head -1 || true)
NL_PID=$(pgrep -f "generate_number_learn_long.py" 2>/dev/null | head -1 || true)
CL_PID=$(pgrep -f "generate_color_learn_long.py" 2>/dev/null | head -1 || true)
SL_PID=$(pgrep -f "generate_shape_learn.py" 2>/dev/null | head -1 || true)

ANY_RUNNING=""
[[ -n "$RUNNER_PID" ]] && ANY_RUNNING="runner(PID $RUNNER_PID)"
[[ -n "$NL_PID" ]]     && ANY_RUNNING="number_learn(PID $NL_PID)"
[[ -n "$CL_PID" ]]     && ANY_RUNNING="color_learn(PID $CL_PID)"
[[ -n "$SL_PID" ]]     && ANY_RUNNING="shape_learn(PID $SL_PID)"

if [[ -n "$ANY_RUNNING" ]]; then
    log "Pipeline is running: $ANY_RUNNING — OK."
    exit 0
fi

# ── Nothing running but renders incomplete → restart ──────────────────────
log "ALERT: Pipeline stopped with $GRAND_TOTAL/$EXPECTED renders done. Restarting..."

tg "🔄 <b>Kids Channel — Render Watchdog</b>
Pipeline остановился! Перезапускаю...

📊 Прогресс:
• numbers: ${NL_TOTAL}/30 (EN:${NL_EN} AR:${NL_AR} ID:${NL_ID})
• colors:  ${CL_TOTAL}/27 (EN:${CL_EN} AR:${CL_AR} ID:${CL_ID})
• shapes:  ${SL_TOTAL}/24 (EN:${SL_EN} AR:${SL_AR} ID:${SL_ID})

Итого: ${GRAND_TOTAL}/${EXPECTED}"

nohup bash "$RUNNER_SCRIPT" >> "$LOG_RENDER" 2>&1 &
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
