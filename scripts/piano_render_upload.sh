#!/bin/bash
# Sacred Drift piano test: wait for a free server (one heavy render at a time), render the video + thumbnail,
# then upload to Sacred Drift as PRIVATE with a scheduled publish time (default Fri 20.11.2026 20:00 UTC — a day
# without a regular long video). Log: sacred_drift/output/piano/render_upload.log
#   bash scripts/piano_render_upload.sh [program] [seed] [publish_at]
cd /opt/kids_channel || exit 1
P=${1:-1}; S=${2:-101}; AT=${3:-2026-11-20T20:00:00Z}
STEM=sd_piano_sleep_p${P}_s${S}; D=sacred_drift/output/piano; LOG=$D/render_upload.log
echo "[$(date -u +%F' '%T)] waiting for a free server" >> "$LOG"
busy() { pgrep -f "render_sd_video|make_sd_video|make_sd_short|remotion|sensory.episode|generate_sleep_classical|run_renders_sequential|run.py episodes" >/dev/null; }
while busy; do sleep 60; done
echo "[$(date -u +%F' '%T)] render start" >> "$LOG"
nice -n 5 python3 -u scripts/make_sd_piano.py --program "$P" --seed "$S" >> "$LOG" 2>&1 || { echo "RENDER FAILED" >> "$LOG"; exit 1; }
python3 - "$D/meta_$STEM.yaml" "$D/desc_$STEM.txt" <<'E' > "$D/args_$STEM.txt"
import sys, yaml
m = yaml.safe_load(open(sys.argv[1]))
open(sys.argv[2], "w").write(m["description"])
print(m["title"]); print(",".join(m["tags"]))
E
TITLE=$(sed -n 1p "$D/args_$STEM.txt"); TAGS=$(sed -n 2p "$D/args_$STEM.txt")
python3 -u scripts/upload_youtube.py --file "$D/$STEM.mp4" --title "$TITLE" --description-file "$D/desc_$STEM.txt" \
  --tags "$TAGS" --status private --publish-at "$AT" --channel sd --made-for-kids false --language en \
  --video-type meditation_compilation --thumbnail "$D/thumb_$STEM.png" --meta-path "$D/meta_$STEM.yaml" >> "$LOG" 2>&1 \
  || { echo "UPLOAD FAILED" >> "$LOG"; exit 1; }
echo "[$(date -u +%F' '%T)] done (scheduled $AT)" >> "$LOG"
