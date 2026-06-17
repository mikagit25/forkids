#!/bin/bash
cd /opt/kids_channel
LOG=logs/rerender_one_two.log

echo "[$(date +%H:%M:%S)] Re-rendering color_learn RED, BLUE, YELLOW, GREEN (wrong audio scheduling)..." | tee -a $LOG

# Re-render: these were rendered with wrong Remotion startFrom → Sequence fix applied 2026-06-17
python3 -u scripts/generate_color_learn_long.py --color red    --lang en --force >> $LOG 2>&1
python3 -u scripts/generate_color_learn_long.py --color red    --lang ar --force >> $LOG 2>&1
python3 -u scripts/generate_color_learn_long.py --color red    --lang id --force >> $LOG 2>&1
python3 -u scripts/generate_color_learn_long.py --color blue   --lang en --force >> $LOG 2>&1
python3 -u scripts/generate_color_learn_long.py --color blue   --lang ar --force >> $LOG 2>&1
python3 -u scripts/generate_color_learn_long.py --color blue   --lang id --force >> $LOG 2>&1
python3 -u scripts/generate_color_learn_long.py --color yellow --lang en --force >> $LOG 2>&1
python3 -u scripts/generate_color_learn_long.py --color yellow --lang ar --force >> $LOG 2>&1
python3 -u scripts/generate_color_learn_long.py --color yellow --lang id --force >> $LOG 2>&1
python3 -u scripts/generate_color_learn_long.py --color green  --lang en --force >> $LOG 2>&1
python3 -u scripts/generate_color_learn_long.py --color green  --lang ar --force >> $LOG 2>&1

echo "[$(date +%H:%M:%S)] color_learn red/blue/yellow/green done. Re-rendering ALL 10 numbers EN+AR (new SVG hands + Sequence audio fix)..." | tee -a $LOG

# Re-render ALL 10 numbers with new algorithm (SVG hands, finger audio, review section, correct Sequence scheduling)
python3 -u scripts/generate_number_learn_long.py --lang en --force >> $LOG 2>&1
python3 -u scripts/generate_number_learn_long.py --lang ar --force >> $LOG 2>&1

echo "[$(date +%H:%M:%S)] EN+AR numbers done. Setting bad published videos to private..." | tee -a $LOG

# Set all bad published videos to private (preserves ID/views, hides from viewers)
# Bad: numbers 1-4 EN (old algorithm), yellow_en (wrong startFrom audio)
python3 scripts/replace_youtube_videos.py --set-private NP_snqwXfPs oI7VeyoVvYw QNsQWQggwgo bAoaarnTyfs bB8lqfeQYSM >> $LOG 2>&1

echo "[$(date +%H:%M:%S)] Starting number_learn ID (all 10)..." | tee -a $LOG

# Generate number_learn for ID channel (all 10, new algorithm)
python3 -u scripts/generate_number_learn_long.py --lang id >> $LOG 2>&1

echo "[$(date +%H:%M:%S)] ALL DONE. Check logs/rerender_one_two.log for details." | tee -a $LOG
