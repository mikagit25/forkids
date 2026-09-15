#!/bin/bash
# Runs shader fire generation AFTER all current ffmpeg/generation processes finish
# Usage: bash scripts/run_shader_fire_queue.sh

LOG=/opt/kids_channel/logs/shader_fire.log
SCRIPT_DIR=/opt/kids_channel/scripts

echo "$(date) Waiting for existing generation processes to complete..." | tee -a "$LOG"

# Wait until no ffmpeg or generation scripts are running (poll every 30s)
while pgrep -f "generate_ambient_video\|generate_fire_ambient\|generate_sd_compilation\|ffmpeg" > /dev/null 2>&1; do
    echo "$(date)   still running — waiting 30s..." | tee -a "$LOG"
    sleep 30
done

echo "$(date) All processes done. Starting shader fire generation." | tee -a "$LOG"

# Render all 4 shader loops + build 1h videos
python3 "$SCRIPT_DIR/generate_fire_shader.py" --all --build >> "$LOG" 2>&1

echo "$(date) Shader fire generation complete." | tee -a "$LOG"
