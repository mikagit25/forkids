#!/usr/bin/env python3
"""Cron (every 30 min): Archive Tales long episodes go to YouTube as soon as they are finished.

1. upload: an episode whose final render + publish step are done (build/<slug>.mp4, description.txt, thumbnail.jpg,
   subtitles.en.srt; description newer than the video) and that has no build/youtube_id.txt yet is uploaded PRIVATE,
   scheduled for the next free slot (every other day, 18:00 UTC — publish.next_slot). The owner turns it into a
   Premiere in YouTube Studio when it is its turn. At most one upload per run (shared API quota).
2. check: if a scheduled time has passed by more than 2 hours and the video is still private (no Premiere was set
   and YouTube did not publish it), it is made public — so a forgotten Premiere never leaves a slot empty.

Skips episodes that are still being worked on (a run.py process for that episode is alive) and the ones listed in
SKIP or marked with build/no_auto_upload.  Log: /opt/kids_channel/logs/archive_upload.log
    python auto_upload.py            # do it
    python auto_upload.py --dry-run  # only print what would happen
"""
import datetime as dt
import subprocess
import sys
from pathlib import Path

import yaml

from pipeline import publish, research

ROOT = Path(__file__).resolve().parent
SKIP = {"1918-flu"}            # auto-picked comparison version, never uploaded
DRY = "--dry-run" in sys.argv


def log(msg):
    print(f"[{dt.datetime.now(dt.timezone.utc):%Y-%m-%d %H:%M}] {msg}", flush=True)


def load(ep_dir):
    ep = yaml.safe_load((ep_dir / "episode.yaml").read_text())
    return {**yaml.safe_load((ROOT / "channel.yaml").read_text()), **ep}


def busy(slug):
    out = subprocess.run(["pgrep", "-af", f"run.py episodes/{slug}"], capture_output=True, text=True).stdout
    return any("python" in l and "pgrep" not in l for l in out.splitlines())


def ready(ep_dir, ep):
    b = ep_dir / "build"
    mp4 = b / f"{ep['slug']}.mp4"
    need = [mp4, b / "description.txt", b / "thumbnail.jpg", b / "subtitles.en.srt"]
    if ep_dir.name in SKIP or (b / "no_auto_upload").exists() or (b / "youtube_id.txt").exists():
        return False
    if not all(f.exists() for f in need):
        return False
    age = dt.datetime.now().timestamp() - mp4.stat().st_mtime
    return age > 300 and (b / "description.txt").stat().st_mtime >= mp4.stat().st_mtime and not busy(ep_dir.name)


def main():
    research.load_env()
    eps = sorted(p for p in (ROOT / "episodes").iterdir() if (p / "episode.yaml").exists())
    # 1. upload finished episodes (oldest render first)
    todo = [(p, load(p)) for p in eps]
    todo = sorted([(p, e) for p, e in todo if ready(p, e)], key=lambda t: (t[0] / "build" / f"{t[1]['slug']}.mp4").stat().st_mtime)
    if todo:
        p, e = todo[0]
        if DRY:
            log(f"would upload {p.name} -> slot {publish.next_slot(ROOT)}")
        else:
            log(f"uploading {p.name}")
            vid = publish.upload(p, e, client_secret=str(ROOT / "client_secret.json"))
            log(f"{p.name} -> https://youtu.be/{vid}  publishAt {(p / 'build' / 'publish_at.txt').read_text().strip()}")
    # 2. scheduled time passed but still private -> publish
    now = dt.datetime.now(dt.timezone.utc)
    late = []
    for p in eps:
        b = p / "build"
        if (b / "youtube_id.txt").exists() and (b / "publish_at.txt").exists():
            at = dt.datetime.fromisoformat((b / "publish_at.txt").read_text().strip().replace("Z", "+00:00"))
            if now - at > dt.timedelta(hours=2) and not (b / "published_ok").exists():
                late.append((p, (b / "youtube_id.txt").read_text().strip()))
    if not late:
        return
    yt = publish.youtube_client(load(late[0][0]), str(ROOT / "client_secret.json"))
    for p, vid in late:
        items = yt.videos().list(part="status", id=vid).execute().get("items", [])
        if not items:
            log(f"!! {p.name}: video {vid} not found on the channel")
            continue
        st = items[0]["status"]
        if st.get("privacyStatus") == "public":
            (p / "build" / "published_ok").write_text(now.isoformat() + "\n")
            continue
        if st.get("publishAt"):          # owner moved it to a later date / premiere is still ahead
            continue
        if DRY:
            log(f"would publish {p.name} ({vid}): still {st.get('privacyStatus')} after its slot")
            continue
        yt.videos().update(part="status", body={"id": vid, "status": {
            "privacyStatus": "public", "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": st.get("containsSyntheticMedia", False)}}).execute()
        (p / "build" / "published_ok").write_text(now.isoformat() + " (made public by auto_upload)\n")
        log(f"{p.name} ({vid}) was still {st.get('privacyStatus')} after its slot -> made public")


if __name__ == "__main__":
    main()
