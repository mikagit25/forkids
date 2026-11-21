#!/bin/bash
# One heavy job at a time on this server (15 GB RAM): render, voice (TTS), framing, music, fetch of big batches.
#   bash heavy.sh <label> <command...>      -> waits for the lock, then runs; log in logs/heavy.log
# Also waits while Sacred Drift / kids renders run (they do not use this lock).
LOCK=/tmp/archive_tales_heavy.lock
LOG=/opt/kids_channel/logs/heavy.log
label=$1; shift
echo "[$(date -u +%F' '%T)] queued: $label" >> "$LOG"
exec 9>"$LOCK"
flock 9
while pgrep -f "[r]ender_sd_video|[m]ake_sd_video|[g]enerate_ambient|[r]emotion|[s]ensory.episode|[r]un_renders_sequential" >/dev/null; do sleep 60; done
echo "[$(date -u +%F' '%T)] start: $label" >> "$LOG"
cd /opt/kids_channel/history_channel && nice -n 5 "$@"
rc=$?
echo "[$(date -u +%F' '%T)] done: $label (exit $rc)" >> "$LOG"
exit $rc
