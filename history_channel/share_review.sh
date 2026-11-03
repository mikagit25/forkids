#!/bin/bash
# Push photo review sheets, manifest and newspaper research of one episode to GitHub for remote review.
#   bash share_review.sh 1918-flu
set -e
cd "$(dirname "$0")"
EP="episodes/$1"
source .venv/bin/activate
[ -f "$EP/manifest.json" ] && python run.py "$EP" review
git add "$EP/manifest.json" "$EP/review" "$EP/research" 2>/dev/null || true
git commit -m "history_channel: review + research for $1" || true
git push
echo "pushed review/research for $1"
