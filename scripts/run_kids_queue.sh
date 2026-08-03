#!/bin/bash
set -e
cd /opt/kids_channel

echo "[$(date)] Waiting for nature_calm to finish..."
while pgrep -f "generate_nature_calm.py" > /dev/null; do
    sleep 30
done
echo "[$(date)] nature_calm done."

echo "[$(date)] Starting animal_groups (5 episodes)..."
python3 scripts/generate_animal_groups.py >> logs/animal_groups.log 2>&1
echo "[$(date)] animal_groups done."

echo "[$(date)] Starting lullaby_animals (4 episodes)..."
python3 scripts/generate_lullaby_animals.py >> logs/lullaby_animals.log 2>&1
echo "[$(date)] lullaby_animals done. All kids queue complete."
