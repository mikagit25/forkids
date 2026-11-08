#!/usr/bin/env python3
"""
Duplicate check module — used by publish_queue.py before every upload.

check_duplicate(mp4_path, meta, channel) → (is_dup: bool, reason: str)

Also provides:
  dry_run_queue(channel)  — scan entire queue and report what would be rejected
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT / "data" / "upload_registry.json"
REJECTED_DIR  = ROOT / "output" / "rejected_duplicates"
TITLE_SIM_THRESHOLD = 0.82   # Jaccard similarity for fuzzy title match


def sha256_file(path: Path) -> str | None:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def normalize_title(title: str) -> str:
    t = re.sub(r"[^\w\s]", " ", title)
    t = re.sub(r"\s+", " ", t).strip().lower()
    return t


def title_similarity(a: str, b: str) -> float:
    """Jaccard similarity on word sets."""
    wa, wb = set(normalize_title(a).split()), set(normalize_title(b).split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def _load_registry(channel: str) -> list[dict]:
    if not REGISTRY_PATH.exists():
        return []
    try:
        return json.loads(REGISTRY_PATH.read_text()).get(channel, [])
    except Exception:
        return []


def _send_telegram(text: str):
    import urllib.request
    BOT_TOKEN = "8931668276:AAHU58_vHoswhBnpOhc4wH3w0jimATkC7m8"
    CHAT_ID   = "209381269"
    try:
        payload = json.dumps({"chat_id": CHAT_ID, "text": text}).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data=payload, headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=8)
    except Exception:
        pass


def reject_file(mp4_path: Path, reason: str, dry_run: bool = False) -> None:
    """Move mp4 + sidecar files to rejected_duplicates/ and notify Telegram."""
    if dry_run:
        print(f"  [DRY-RUN REJECT] {mp4_path.name}: {reason}")
        return
    REJECTED_DIR.mkdir(parents=True, exist_ok=True)
    for suffix in ["", f"meta_{mp4_path.stem}.yaml", f"thumb_{mp4_path.stem}.png"]:
        src = mp4_path.parent / (suffix if suffix else mp4_path.name)
        if src.exists():
            shutil.move(str(src), str(REJECTED_DIR / src.name))
    msg = f"🚫 Duplicate rejected\n{mp4_path.name}\nReason: {reason}"
    _send_telegram(msg)
    print(f"  → rejected: {reason} (moved to rejected_duplicates/)")


def check_duplicate(mp4_path: Path, meta: dict, channel: str,
                    dry_run: bool = False) -> tuple[bool, str]:
    """
    Returns (is_duplicate, reason).
    If is_duplicate and not dry_run, moves file to rejected_duplicates/.
    """
    registry = _load_registry(channel)
    if not registry:
        return False, ""

    title = meta.get("title", "")

    # 1. Exact / near-exact title match
    for entry in registry:
        sim = title_similarity(title, entry["title"])
        if sim >= TITLE_SIM_THRESHOLD:
            reason = (f"title too similar to already-uploaded video "
                      f"'{entry['title'][:60]}' (sim={sim:.2f}, id={entry['video_id']})")
            reject_file(mp4_path, reason, dry_run)
            return True, reason

    # 2. sha256 match (exact file duplicate)
    if mp4_path.exists():
        h = sha256_file(mp4_path)
        if h:
            for entry in registry:
                if entry.get("sha256") and entry["sha256"] == h:
                    reason = (f"identical file already uploaded as "
                              f"'{entry['title'][:60]}' (id={entry['video_id']})")
                    reject_file(mp4_path, reason, dry_run)
                    return True, reason

    return False, ""


def dry_run_queue(channel: str = "en"):
    """Scan the queue and report duplicates without moving anything."""
    import yaml
    QUEUE_DIRS = {
        "en": ROOT / "output" / "queue",
        "sd": ROOT / "sacred_drift" / "output" / "queue",
    }
    q = QUEUE_DIRS.get(channel, ROOT / "output" / "queue")
    if not q.exists():
        print(f"Queue not found: {q}")
        return

    print(f"\n=== Duplicate dry-run: {channel.upper()} queue ({q}) ===\n")
    rejected, ok = [], []
    for mp4 in sorted(q.glob("*.mp4")):
        meta_path = q / f"meta_{mp4.stem}.yaml"
        if not meta_path.exists():
            continue
        meta = yaml.safe_load(meta_path.read_text()) or {}
        is_dup, reason = check_duplicate(mp4, meta, channel, dry_run=True)
        if is_dup:
            rejected.append((mp4.name, reason))
        else:
            ok.append(mp4.name)

    print(f"Would PASS:   {len(ok)}")
    print(f"Would REJECT: {len(rejected)}")
    if rejected:
        print("\nFiles that would be rejected:")
        for name, reason in rejected:
            print(f"  ✗ {name}")
            print(f"    {reason}")
    else:
        print("\nNo duplicates found in queue.")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", default="en", choices=["en", "sd"])
    a = ap.parse_args()
    dry_run_queue(a.channel)
