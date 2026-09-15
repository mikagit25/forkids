#!/usr/bin/env python3
"""
Live stream watchdog — runs every minute via cron.

Checks both EU and US slots for:
  1. ffmpeg process dead
  2. YouTube stream inactive/bad health (audio or video missing)
  3. Excessive "frames duplicated" in ffmpeg log (audio sync failure)

On any issue: kills old ffmpeg, starts fresh one, sends Telegram alert.
Prevents restart loops: max 1 restart per slot per 10 minutes.
"""
import fcntl
import json
import logging
import os
import re
import signal
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT     = Path(__file__).resolve().parent.parent
LOGS_DIR = ROOT / "logs"

sys.path.insert(0, str(ROOT / "scripts"))

BOT_TOKEN = "8931668276:AAHU58_vHoswhBnpOhc4wH3w0jimATkC7m8"
CHAT_ID   = "209381269"

WATCHDOG_STATE  = LOGS_DIR / "live_watchdog_state.json"
WATCHDOG_LOCK   = LOGS_DIR / "live_watchdog.lock"
WATCHDOG_LOG    = LOGS_DIR / "live_watchdog.log"
MIN_RESTART_GAP = 600   # seconds — don't restart same slot more than once per 10 min
DUP_THRESHOLD   = 2     # "frames duplicated" lines in new log content = audio broken
                        # ffmpeg prints at 1000/10000/100000 frames, so 2 lines = ~5 min of silent audio


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("watchdog")


# ── Telegram ──────────────────────────────────────────────────────────────────

def tg(msg: str):
    try:
        payload = json.dumps({"chat_id": CHAT_ID, "text": msg,
                              "parse_mode": "HTML"}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        log.warning(f"Telegram failed: {e}")


# ── State helpers ─────────────────────────────────────────────────────────────

def _load_wd_state() -> dict:
    try:
        if WATCHDOG_STATE.exists():
            return json.loads(WATCHDOG_STATE.read_text())
    except Exception:
        pass
    return {}


def _save_wd_state(state: dict):
    WATCHDOG_STATE.parent.mkdir(exist_ok=True)
    tmp = WATCHDOG_STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2))
    os.replace(str(tmp), str(WATCHDOG_STATE))


def _load_stream_state(channel: str, slot: str) -> dict:
    sf = LOGS_DIR / f"live_state_{channel}_{slot}.json"
    try:
        if sf.exists():
            text = sf.read_text().strip()
            if text:
                return json.loads(text)
    except Exception:
        pass
    return {}


def _save_stream_state(channel: str, slot: str, state: dict):
    sf = LOGS_DIR / f"live_state_{channel}_{slot}.json"
    tmp = sf.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2))
    os.replace(str(tmp), str(sf))


# ── YouTube API ───────────────────────────────────────────────────────────────

def _get_youtube(channel: str):
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    token_files = {
        "id": ROOT / "credentials" / "youtube_token_id.json",
        "en": ROOT / "credentials" / "youtube_token.json",
        "ar": ROOT / "credentials" / "youtube_token_ar.json",
    }
    token_path = token_files[channel]
    raw = token_path.read_text().strip()
    t = json.loads(raw)
    creds = Credentials(
        token=t.get("access_token"),
        refresh_token=t["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=t["client_id"], client_secret=t["client_secret"],
        scopes=["https://www.googleapis.com/auth/youtube.force-ssl"],
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return build("youtube", "v3", credentials=creds)


def check_youtube_health(channel: str, stream_id: str, broadcast_id: str) -> tuple[str, str]:
    """
    Returns (stream_status, health_status).
    stream_status: active | inactive | error | ready
    health_status: good | ok | bad | noData | revoked | unknown
    """
    try:
        yt = _get_youtube(channel)

        # 1. Stream ingestion status
        sr = yt.liveStreams().list(part="status", id=stream_id).execute()
        if not sr.get("items"):
            return "unknown", "noData"
        stream_status = sr["items"][0]["status"].get("streamStatus", "unknown")
        health_raw    = sr["items"][0]["status"].get("healthStatus", {})
        health_status = health_raw.get("status", "unknown")

        return stream_status, health_status

    except Exception as e:
        log.warning(f"YouTube health check failed: {e}")
        return "unknown", "unknown"


def check_broadcast_live(channel: str, broadcast_id: str) -> bool:
    """Return True if broadcast is still in 'live' state on YouTube."""
    try:
        yt = _get_youtube(channel)
        r = yt.liveBroadcasts().list(part="status", id=broadcast_id).execute()
        if r.get("items"):
            status = r["items"][0]["status"]["lifeCycleStatus"]
            return status == "live"
    except Exception as e:
        log.warning(f"Broadcast status check failed: {e}")
    return False


# ── ffmpeg helpers ────────────────────────────────────────────────────────────

def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def count_new_dup_lines(log_path: Path, last_size: int) -> tuple[int, int]:
    """Count 'frames duplicated' warnings added since last check. Returns (count, new_size)."""
    try:
        current_size = log_path.stat().st_size if log_path.exists() else 0
        if current_size <= last_size:
            return 0, current_size
        with open(log_path, "rb") as f:
            f.seek(last_size)
            new_data = f.read().decode("utf-8", errors="replace")
        count = new_data.count("frames duplicated")
        return count, current_size
    except Exception:
        return 0, last_size


def get_rtmp_url(pid: int) -> str | None:
    try:
        args = open(f"/proc/{pid}/cmdline", "rb").read().decode("utf-8", errors="replace")
        parts = args.split("\x00")
        return next((p for p in parts if p.startswith("rtmp://")), None)
    except Exception:
        return None


def kill_ffmpeg(pid: int):
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            pgid = os.getpgid(pid)
            os.killpg(pgid, sig)
        except Exception:
            try:
                os.kill(pid, sig)
            except Exception:
                pass
        time.sleep(1)


def start_ffmpeg(channel: str, slot: str, rtmp_url: str) -> int:
    """Start ffmpeg with the current playlist. Returns new PID."""
    from live_stream import _start_ffmpeg, _validate_playlist_file, LOGS_DIR as LS_LOGS

    playlist_file    = LS_LOGS / f"live_playlist_{channel}_{slot}.txt"
    now_playing_file = LS_LOGS / f"live_now_playing_{channel}_{slot}.txt"
    log_path         = LS_LOGS / f"live_ffmpeg_{channel}_{slot}.log"

    removed = _validate_playlist_file(playlist_file)
    if removed:
        log.warning(f"Playlist cleaned before watchdog restart: {removed} invalid file(s) removed")

    # Check the playlist has at least one entry after cleaning
    if not playlist_file.exists():
        raise RuntimeError("Playlist file missing")
    entries = [l for l in playlist_file.read_text().splitlines()
               if l.strip().startswith("file '")]
    if not entries:
        raise RuntimeError("Playlist is empty after validation — cannot restart stream")

    return _start_ffmpeg(playlist_file, rtmp_url, now_playing_file, log_path)


# ── Core watchdog logic ───────────────────────────────────────────────────────

SLOT_CONFIG = {
    "eu": {"start_hour": 20, "stop_hour": 6},
    "us": {"start_hour": 7,  "stop_hour": 14},
}


def is_slot_active(slot: str) -> bool:
    """Return True during the slot's scheduled window (UTC)."""
    now = datetime.now(timezone.utc)
    cfg = SLOT_CONFIG[slot]
    h = now.hour
    start, stop = cfg["start_hour"], cfg["stop_hour"]
    if start > stop:   # overnight: EU 20→6
        return h >= start or h < stop
    return start <= h < stop


def check_slot(channel: str, slot: str, wd_state: dict) -> dict:
    """Check one slot, restart ffmpeg if needed. Returns updated wd_state."""
    slot_key = f"{channel}_{slot}"
    stream_state = _load_stream_state(channel, slot)

    if not stream_state:
        return wd_state   # no active stream in this slot

    if not is_slot_active(slot):
        return wd_state   # outside scheduled window

    pid          = stream_state.get("ffmpeg_pid")
    stream_id    = stream_state.get("stream_id", "")
    broadcast_id = stream_state.get("broadcast_id", "")
    ffmpeg_log   = LOGS_DIR / f"live_ffmpeg_{channel}_{slot}.log"

    # Check restart cooldown
    last_restart = wd_state.get(f"{slot_key}_last_restart", 0)
    now_ts = time.time()
    if now_ts - last_restart < MIN_RESTART_GAP:
        return wd_state   # too soon to restart again

    # ── Check 1: ffmpeg process alive ────────────────────────────────────────
    ffmpeg_ok = pid and pid_alive(pid)

    # ── Check 2: audio frames duplicated in log ───────────────────────────────
    last_log_size = wd_state.get(f"{slot_key}_log_size", 0)
    dup_count, new_log_size = count_new_dup_lines(ffmpeg_log, last_log_size)
    wd_state[f"{slot_key}_log_size"] = new_log_size
    audio_broken = dup_count >= DUP_THRESHOLD

    # ── Decision (no YouTube API — avoid quota burn) ──────────────────────────
    restart_reason = None
    if not ffmpeg_ok:
        restart_reason = f"ffmpeg PID {pid} died"
    elif audio_broken:
        restart_reason = f"{dup_count} duplicated-frame warnings (audio sync failure)"

    if not restart_reason:
        log.info(f"[{slot_key}] OK — ffmpeg:{pid} dup_warnings:{dup_count}")
        return wd_state

    log.warning(f"[{slot_key}] ISSUE: {restart_reason} — restarting ffmpeg")

    # Get RTMP URL (from old process or state)
    rtmp_url = None
    if pid and pid_alive(pid):
        rtmp_url = get_rtmp_url(pid)
    if not rtmp_url:
        # Reconstruct from stream key in state — extract from old cmdline cache
        rtmp_url = wd_state.get(f"{slot_key}_rtmp_url")

    if not rtmp_url:
        log.error(f"[{slot_key}] Cannot restart — RTMP URL unknown")
        tg(f"⚠️ <b>CNR Live [{slot.upper()}]</b> — {restart_reason}\n"
           f"Cannot auto-restart: RTMP URL unknown. Manual intervention needed.")
        return wd_state

    # Kill old ffmpeg
    if pid:
        kill_ffmpeg(pid)

    # Start new ffmpeg
    try:
        new_pid = start_ffmpeg(channel, slot, rtmp_url)
        log.info(f"[{slot_key}] Restarted ffmpeg → PID {new_pid}")

        # Update stream state
        stream_state["ffmpeg_pid"] = new_pid
        _save_stream_state(channel, slot, stream_state)

        wd_state[f"{slot_key}_last_restart"] = now_ts
        wd_state[f"{slot_key}_rtmp_url"]     = rtmp_url
        # Skip old log content — new ffmpeg appends to same file, track current end
        wd_state[f"{slot_key}_log_size"]     = new_log_size

        tg(f"🔄 <b>CNR Live [{slot.upper()}]</b> auto-restarted\n"
           f"Reason: {restart_reason}\n"
           f"New ffmpeg PID: {new_pid}")

    except Exception as e:
        log.error(f"[{slot_key}] Restart failed: {e}")
        tg(f"❌ <b>CNR Live [{slot.upper()}]</b> restart FAILED\n"
           f"Reason was: {restart_reason}\nError: {e}")

    return wd_state


def main():
    LOGS_DIR.mkdir(exist_ok=True)

    # Exclusive lock: if previous cron instance is still running, exit immediately.
    # Without this, concurrent watchdog runs each restart ffmpeg → zombie duplicates.
    lock_fd = open(WATCHDOG_LOCK, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        log.info("Another watchdog instance is running — exiting.")
        lock_fd.close()
        return

    wd_state = _load_wd_state()

    # Cache RTMP URLs from running processes proactively
    for slot in ("eu", "us"):
        slot_key = f"id_{slot}"
        ss = _load_stream_state("id", slot)
        pid = ss.get("ffmpeg_pid")
        if pid and pid_alive(pid):
            rtmp = get_rtmp_url(pid)
            if rtmp:
                wd_state[f"{slot_key}_rtmp_url"] = rtmp

    for slot in ("eu", "us"):
        wd_state = check_slot("id", slot, wd_state)

    _save_wd_state(wd_state)


if __name__ == "__main__":
    main()
