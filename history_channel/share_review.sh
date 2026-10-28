#!/bin/bash
# Push the photo review sheets + manifest of one episode to GitHub, so they can be checked remotely.
#   bash share_review.sh 1918-flu
set -e
cd "$(dirname "$0")"
EP="episodes/$1"
[ -f "$EP/manifest.json" ] || { echo "no $EP/manifest.json - run fetch first"; exit 1; }
source .venv/bin/activate
python run.py "$EP" review
git add "$EP/manifest.json" "$EP/review"
git commit -m "history_channel: photo review for $1" || true
git push
echo "pushed review sheets for $1"
