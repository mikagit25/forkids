#!/bin/bash
# Generate A-Z vocabulary shorts for EN channel, sequentially.
# Run AFTER 8h renders complete (check: ps aux | grep ffmpeg)
cd "$(dirname "$0")/.."
LOG=logs/vocab_queue.log
mkdir -p logs
exec > >(tee -a "$LOG") 2>&1

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Vocab Queue A-Z START — $(date '+%Y-%m-%d %H:%M:%S')"
echo "════════════════════════════════════════════════════════════"

# Skip A B C — already generated in this session
python3 scripts/generate_vocab_shorts.py --letters D E F G H I J K L M N O P Q R S T U V W X Y Z

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  Vocab Queue A-Z DONE — $(date '+%Y-%m-%d %H:%M:%S')"
echo "════════════════════════════════════════════════════════════"
