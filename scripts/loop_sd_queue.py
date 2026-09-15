#!/usr/bin/env python3
"""
Loop all short Sacred Drift queue videos to 1 hour (3600s).
Uses FFmpeg concat + copy — fast, no re-encode.

Usage:
  python3 scripts/loop_sd_queue.py --dry-run
  python3 scripts/loop_sd_queue.py
  python3 scripts/loop_sd_queue.py --target 1800  # 30 min instead of 1h
"""
import argparse, logging, subprocess, json, yaml, shutil
from pathlib import Path

ROOT      = Path(__file__).resolve().parent.parent
QUEUE_DIR = ROOT / 'sacred_drift/output/queue'
TARGET    = 3600   # default: 1 hour

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')


def get_duration(path: Path) -> float:
    r = subprocess.run(
        ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', str(path)],
        capture_output=True
    )
    try:
        return float(json.loads(r.stdout)['format']['duration'])
    except Exception:
        return 0.0


def fmt_dur(sec: float) -> str:
    h, m = int(sec) // 3600, (int(sec) % 3600) // 60
    return f"{h}h" if not m else (f"{h}h {m}min" if h else f"{m}min")


def build_title(old_title: str, new_dur: float) -> str:
    """Replace duration string in title."""
    import re
    dur_str = "1 Hour" if new_dur >= 3500 else fmt_dur(new_dur)
    # Replace patterns like "3min", "5min", "2min", "Xh Ymin", "Xh"
    new = re.sub(r'\d+h\s*\d*min|\d+h|\d+\s*min', dur_str, old_title)
    if new == old_title:
        # Pattern not found — append before " | Sacred Drift"
        new = old_title.replace(' | Sacred Drift', f' — {dur_str} | Sacred Drift')
    return new


def loop_video(mp4: Path, target: float, dry_run: bool) -> bool:
    dur = get_duration(mp4)
    if dur >= target * 0.9:
        log.info(f"SKIP (already {dur/60:.0f}min): {mp4.name}")
        return True

    loops = int(target / dur) + 2
    tmp_list = mp4.parent / f'_loop_list_{mp4.stem}.txt'
    tmp_out  = mp4.parent / f'_looped_{mp4.name}'

    log.info(f"  {mp4.name}: {dur/60:.1f}min → loop ×{loops} → {target/60:.0f}min")
    if dry_run:
        return True

    with open(tmp_list, 'w') as f:
        for _ in range(loops):
            f.write(f"file '{mp4.resolve()}'\n")

    cmd = [
        'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
        '-i', str(tmp_list),
        '-t', str(target),
        '-c', 'copy',
        str(tmp_out)
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    tmp_list.unlink(missing_ok=True)

    if r.returncode != 0:
        log.error(f"  ffmpeg failed: {r.stderr[-300:]}")
        tmp_out.unlink(missing_ok=True)
        return False

    shutil.move(str(tmp_out), str(mp4))
    new_dur = get_duration(mp4)
    log.info(f"  Done: {new_dur/60:.1f}min ({mp4.stat().st_size // 1024 // 1024}MB)")
    return True


def update_meta(meta_path: Path, new_dur: float, dry_run: bool):
    m = yaml.safe_load(meta_path.read_text()) or {}
    old_title = m.get('title', '')
    new_title = build_title(old_title, new_dur)
    m['title'] = new_title
    m['duration_sec'] = int(new_dur)
    if dry_run:
        log.info(f"  [DRY] title: {old_title!r} → {new_title!r}")
        return
    log.info(f"  title: {old_title!r} → {new_title!r}")
    meta_path.write_text(yaml.dump(m, allow_unicode=True, default_flow_style=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--target', type=int, default=TARGET, help='Target duration in seconds')
    args = parser.parse_args()

    mp4s = sorted(QUEUE_DIR.glob('sd_*.mp4'))
    long_mp4s = [p for p in mp4s if not p.stem.startswith('sd_comp_') and '_short_' not in p.stem]

    log.info(f"Found {len(long_mp4s)} long videos in queue")

    ok = skip = fail = 0
    for mp4 in long_mp4s:
        dur = get_duration(mp4)
        if dur >= args.target * 0.9:
            skip += 1
            continue

        log.info(f"\n{'─'*50}")
        log.info(f"{mp4.name}: {dur/60:.1f}min")
        if loop_video(mp4, args.target, args.dry_run):
            new_dur = get_duration(mp4) if not args.dry_run else args.target
            meta = QUEUE_DIR / f'meta_{mp4.stem}.yaml'
            if meta.exists():
                update_meta(meta, new_dur, args.dry_run)
            ok += 1
        else:
            fail += 1

    log.info(f"\n{'='*50}")
    log.info(f"Done: {ok} looped, {skip} skipped (already long), {fail} failed")


if __name__ == '__main__':
    main()
