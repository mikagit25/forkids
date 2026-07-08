#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
# CLASSICAL PROGRAMS QUEUE — строго последовательно, один ffmpeg за раз.
# Принцип как в run_renders_sequential.sh: один процесс → ждём → следующий.
# Сервер 15GB RAM / 4 CPU: никогда не запускать два рендера одновременно.
#
# Запуск: bash scripts/run_classical_queue.sh
# Лог:    logs/classical_queue.log
# Статус: tail -f logs/classical_queue.log
# ═══════════════════════════════════════════════════════════════════════════════

cd "$(dirname "$0")/.."
LOG=logs/classical_queue.log
mkdir -p logs
exec > >(tee -a "$LOG") 2>&1

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Classical Queue START — $(date '+%Y-%m-%d %H:%M:%S')"
echo "════════════════════════════════════════════════════════════"

run() {
    local prog="$1"; shift
    echo ""
    echo "▶ [$prog] durations: $* — $(date '+%H:%M:%S')"
    python3 scripts/generate_sleep_classical.py --program "$prog" --durations "$@"
    echo "  ✓ [$prog] done — $(date '+%H:%M:%S')"
}

# ────────────────────────────────────────────────────────────
# Блок 1 — Доделать текущие программы (1h уже есть, нужен 3h)
# ────────────────────────────────────────────────────────────
run focus_beethoven_01         3          # 1h готов, генерируем 3h

# ────────────────────────────────────────────────────────────
# Блок 2 — Новые программы: сначала все 1h (быстро в очередь)
# ────────────────────────────────────────────────────────────
run sleep_romantic_night_01    1
run focus_drama_01             1
run sleep_flute_01             1
run focus_mozart_01            1
run sleep_debussy_01           1
run sleep_chopin_02            1
run sleep_baroque_01           1

# ────────────────────────────────────────────────────────────
# Блок 3 — 3h версии (более длинный контент)
# ────────────────────────────────────────────────────────────
run sleep_romantic_night_01    3
run focus_drama_01             3
run sleep_flute_01             3
run focus_mozart_01            3
run sleep_debussy_01           3
run sleep_chopin_02            3
run sleep_baroque_01           3

# ────────────────────────────────────────────────────────────
# Блок 4 — 3h+8h для основных программ
# ────────────────────────────────────────────────────────────
run sleep_swan_lake_01         3
run sleep_swan_lake_01         8
run sleep_chopin_01            3
run sleep_chopin_01            8
run sleep_grand_night_01       3
run sleep_grand_night_01       8

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Classical Queue DONE — $(date '+%Y-%m-%d %H:%M:%S')"
echo "════════════════════════════════════════════════════════════"
