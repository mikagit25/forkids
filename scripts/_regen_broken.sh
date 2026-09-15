#!/bin/bash
# Regenerate 6 broken natural-mode programs sequentially
# Run AFTER sleep_schubert_01 encoding completes
set -e
cd /opt/kids_channel

PROGRAMS=(
    "sleep_romantic_orchestral_01"
    "sleep_beethoven_complete_3h_01"
    "focus_bach_violin_partita_01"
    "focus_beethoven_concertos_01"
    "focus_beethoven_eroica_01"
    "focus_franck_violin_01"
)

for prog in "${PROGRAMS[@]}"; do
    echo "===== $(date -u '+%Y-%m-%d %H:%M:%S UTC') — Starting: $prog ====="
    python3 scripts/generate_sleep_classical.py --program "$prog" --natural
    echo "===== Done: $prog ====="
done

echo ""
echo "===== ALL DONE $(date -u '+%Y-%m-%d %H:%M:%S UTC') ====="
echo "Checking audio gaps on newly generated files..."

# Quick scan of new files
for prog in "sleep_schubert_01" "${PROGRAMS[@]}"; do
    f=$(ls /opt/kids_channel/output/queue_id/${prog}_natural_*.mp4 2>/dev/null | tail -1)
    if [ -z "$f" ]; then
        echo "  MISSING: $prog"
        continue
    fi
    total=$(ffprobe -v quiet -print_format json -show_streams "$f" 2>/dev/null | \
            python3 -c "import sys,json; s=json.load(sys.stdin)['streams']; v=[x for x in s if x.get('codec_type')=='video']; print(int(float(v[0]['duration'])))" 2>/dev/null || echo "?")
    gaps=$(ffmpeg -i "$f" -vn -af "silencedetect=noise=-50dB:duration=10" -f null /dev/null 2>&1 | \
           grep "silence_end" | awk '{sum+=$5} END{print int(sum)}')
    pct=$(python3 -c "print(f'{int($gaps)*100//int($total)}%')" 2>/dev/null || echo "?%")
    echo "  $pct silent | ${gaps}s / ${total}s | $(basename $f)"
done
