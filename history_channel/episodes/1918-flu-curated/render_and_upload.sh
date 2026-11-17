#!/bin/bash
# 1918-flu-curated: wait until no other heavy render runs on the server (15 GB RAM, RULES.md),
# then render -> description/thumbnail -> upload as PRIVATE. Log: build/render_upload.log
cd /opt/kids_channel/history_channel || exit 1
source .venv/bin/activate
LOG=episodes/1918-flu-curated/build/render_upload.log
echo "[$(date -u +%F' '%T)] waiting for a free server" >> "$LOG"
busy() { pgrep -f "render_sd_video|make_sd_video|make_sd_short|remotion|sensory.episode|generate_sleep_classical|run_renders_sequential" >/dev/null; }
while busy; do sleep 60; done
echo "[$(date -u +%F' '%T)] render start" >> "$LOG"
python -u run.py episodes/1918-flu-curated render >> "$LOG" 2>&1 || { echo "RENDER FAILED" >> "$LOG"; exit 1; }
python -u run.py episodes/1918-flu-curated publish >> "$LOG" 2>&1 || { echo "PUBLISH FAILED" >> "$LOG"; exit 1; }
python -u run.py episodes/1918-flu-curated upload >> "$LOG" 2>&1 || { echo "UPLOAD FAILED" >> "$LOG"; exit 1; }
echo "[$(date -u +%F' '%T)] done" >> "$LOG"
