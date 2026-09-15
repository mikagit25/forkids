#!/bin/bash
# Repair broken sleep/focus videos: rebuild audio without aresample async,
# then remux (copy video stream, replace audio — no video re-encoding).
set -e
cd /opt/kids_channel

declare -A PROG_FILES=(
  ["sleep_schubert_01"]="output/queue_id/sleep_schubert_01_natural_20260908.mp4"
  ["sleep_romantic_orchestral_01"]="output/queue_id/sleep_romantic_orchestral_01_natural_20260908.mp4"
  ["sleep_beethoven_complete_3h_01"]="output/queue_id/sleep_beethoven_complete_3h_01_natural_20260908.mp4"
  ["focus_bach_violin_partita_01"]="output/queue_id/focus_bach_violin_partita_01_natural_20260908.mp4"
  ["focus_beethoven_concertos_01"]="output/queue_id/focus_beethoven_concertos_01_natural_20260909.mp4"
  ["focus_beethoven_eroica_01"]="output/queue_id/focus_beethoven_eroica_01_natural_20260909.mp4"
  ["focus_franck_violin_01"]="output/queue_id/focus_franck_violin_01_natural_20260909.mp4"
)

for prog in "${!PROG_FILES[@]}"; do
  video="${PROG_FILES[$prog]}"
  tmpdir="output/_tmp_${prog}"
  concat="$tmpdir/concat_tracks.txt"
  audio_fixed="$tmpdir/audio_fixed.mp3"
  video_tmp="${video%.mp4}_fixing.mp4"

  echo ""
  echo "===== $(date -u '+%H:%M:%S UTC') — Repairing: $prog ====="

  if [ ! -f "$video" ]; then
    echo "  SKIP: video file not found: $video"
    continue
  fi
  if [ ! -f "$concat" ]; then
    echo "  SKIP: concat_tracks.txt not found in $tmpdir"
    continue
  fi

  echo "  Step 1: Rebuild clean audio (no aresample async)..."
  ffmpeg -y -f concat -safe 0 -i "$concat" \
    -ar 44100 -ac 2 \
    -c:a libmp3lame -b:a 192k \
    "$audio_fixed" 2>&1 | tail -3

  audio_dur=$(ffprobe -v error -show_entries format=duration \
    -of default=nw=1 "$audio_fixed" 2>/dev/null | cut -d= -f2 | xargs printf "%.0f")
  echo "  Audio rebuilt: ~${audio_dur}s (ffprobe header estimate)"

  echo "  Step 2: Remux — copy video, replace audio (no re-encode)..."
  ffmpeg -y \
    -i "$video" \
    -i "$audio_fixed" \
    -map 0:v:0 -map 1:a:0 \
    -c:v copy -c:a aac -b:a 192k \
    -shortest \
    "$video_tmp" 2>&1 | tail -3

  actual_dur=$(ffprobe -v error -show_entries format=duration \
    -of default=nw=1 "$video_tmp" 2>/dev/null | cut -d= -f2 | xargs printf "%.0f")
  size=$(du -sh "$video_tmp" 2>/dev/null | cut -f1)
  echo "  Output: ${actual_dur}s / ${size} → $(basename $video_tmp)"

  echo "  Step 3: Quick silence check..."
  gaps=$(ffmpeg -i "$video_tmp" -vn -af "silencedetect=noise=-50dB:duration=10" -f null /dev/null 2>&1 | \
         grep "silence_duration:" | awk -F'silence_duration: ' '{sum+=$2} END{printf "%.0f", sum}')
  gaps=${gaps:-0}
  pct=0
  [ "${actual_dur:-0}" -gt 0 ] && pct=$((gaps * 100 / actual_dur))
  echo "  Silence: ${pct}% (${gaps}s / ${actual_dur}s)"

  if [ "$pct" -le 15 ]; then
    echo "  ✓ CLEAN — replacing original file"
    mv "$video_tmp" "$video"
    # Regenerate meta with corrected duration
    echo "  Regenerating meta..."
    python3 scripts/generate_sleep_classical.py --program "$prog" --natural --regen-meta 2>&1 | \
      grep -E "Meta →|Done:|Natural duration"
  else
    echo "  ✗ STILL BROKEN (${pct}% silent) — keeping original, manual inspection needed"
    rm -f "$video_tmp"
  fi
done

echo ""
echo "===== REPAIR COMPLETE $(date -u '+%Y-%m-%d %H:%M:%S UTC') ====="
echo "Final queue_id long files:"
for f in output/queue_id/*.mp4; do
  [[ "$f" == *"visual_short"* ]] && continue
  [[ "$f" == *"kw_short"* ]] && continue
  size=$(du -sh "$f" 2>/dev/null | cut -f1)
  echo "  $size  $(basename $f)"
done
