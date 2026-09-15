#!/usr/bin/env python3
"""
Compile short Sacred Drift sound-design video series into 1-hour blocks.

Glacier ice cave, waterfall, bamboo, desert wind etc. are generated as 5-6 min
episodes. The live stream filter (MIN_DURATION_SEC=600) accepts them individually,
but 48 glacier episodes would dominate an entire 8h stream. This script bundles
groups of ~12 episodes into 1h blocks with smooth xfade transitions.

Usage:
  python3 scripts/compile_sd_blocks.py               # compile all series
  python3 scripts/compile_sd_blocks.py --series glacier
  python3 scripts/compile_sd_blocks.py --dry-run
"""
import argparse, logging, re, subprocess, sys
from pathlib import Path

ROOT      = Path(__file__).resolve().parent.parent
SD_QUEUE  = ROOT / "sacred_drift" / "output" / "queue"
LOGS_DIR  = ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# Series to compile: series_key → (glob_pattern, target_block_hours, xfade_secs)
SERIES = {
    "glacier":   ("sd_sound_design_glacier_ice_cave_*.mp4",  1.0, 2),
    "waterfall": ("sd_sound_design_distant_waterfall_*.mp4", 1.0, 2),
    "bamboo":    ("sd_sound_design_bamboo_forest_wind_*.mp4",1.0, 2),
    "desert":    ("sd_sound_design_desert_night_wind_*.mp4", 1.0, 2),
    "cosmic":    ("sd_sound_design_cosmic_drone_*.mp4",      1.0, 3),
}


def get_duration(p: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(p)],
        capture_output=True, text=True, timeout=15
    )
    try:
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def episode_index(name: str) -> int:
    """Extract numeric index from filename for sorting."""
    m = re.search(r'_(\d+)(?:_\d{8})?\.mp4$', name)
    return int(m.group(1)) if m else 0


def concat_block(episodes: list[Path], out: Path, xfade: int) -> bool:
    """Concat episodes with xfade transitions into one block MP4."""
    if len(episodes) == 1:
        import shutil
        shutil.copy(episodes[0], out)
        return True

    n = len(episodes)
    inputs = []
    for ep in episodes:
        inputs += ["-i", str(ep)]

    # Build xfade filter chain
    durations = [get_duration(ep) for ep in episodes]
    fc_parts = []
    prev_out = "[0:v]"
    prev_a   = "[0:a]"
    offset = 0.0
    for i in range(1, n):
        offset += durations[i - 1] - xfade
        v_out = f"[v{i}]" if i < n - 1 else "[vout]"
        a_out = f"[a{i}]" if i < n - 1 else "[aout]"
        fc_parts.append(
            f"{prev_out}[{i}:v]xfade=transition=fade:duration={xfade}:offset={offset:.2f}{v_out}"
        )
        fc_parts.append(
            f"{prev_a}[{i}:a]acrossfade=d={xfade}:c1=tri:c2=tri{a_out}"
        )
        prev_out = v_out
        prev_a   = a_out

    fc = ";".join(fc_parts)
    cmd = (["ffmpeg", "-y"] + inputs +
           ["-filter_complex", fc,
            "-map", "[vout]", "-map", "[aout]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
            "-pix_fmt", "yuv420p", str(out)])
    log.info(f"  ffmpeg concat {len(episodes)} eps → {out.name}")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    if r.returncode != 0 or not out.exists():
        log.error(f"  concat failed: {r.stderr[-300:]}")
        return False
    return True


def compile_series(key: str, glob_pattern: str, target_hours: float,
                   xfade: int, dry_run: bool = False):
    """Find all episodes, group into target_hours blocks, compile each."""
    all_eps = sorted(SD_QUEUE.glob(glob_pattern), key=lambda p: episode_index(p.name))
    if not all_eps:
        log.warning(f"[{key}] No episodes found matching {glob_pattern}")
        return

    # How many episodes per block to reach target_hours
    total_dur = sum(get_duration(ep) for ep in all_eps[:6])  # sample first 6
    if total_dur == 0:
        log.warning(f"[{key}] Could not read durations")
        return
    avg_dur = total_dur / min(6, len(all_eps))
    eps_per_block = max(2, int(target_hours * 3600 / avg_dur))
    log.info(f"[{key}] {len(all_eps)} episodes, avg {avg_dur/60:.1f}min each → "
             f"{eps_per_block} eps/block (≈{eps_per_block*avg_dur/3600:.1f}h blocks)")

    # Group into blocks
    blocks = [all_eps[i:i + eps_per_block] for i in range(0, len(all_eps), eps_per_block)]
    log.info(f"[{key}] → {len(blocks)} blocks")

    for b_idx, block_eps in enumerate(blocks, start=1):
        out_name = f"sd_sound_design_{key}_block_{b_idx:02d}.mp4"
        out_path = SD_QUEUE / out_name
        if out_path.exists():
            log.info(f"[{key}] Block {b_idx}: already exists — skip (use --force to regen)")
            continue
        dur_h = sum(get_duration(ep) for ep in block_eps) / 3600
        log.info(f"[{key}] Block {b_idx}: {len(block_eps)} eps, ~{dur_h:.1f}h → {out_name}")
        if dry_run:
            continue
        ok = concat_block(block_eps, out_path, xfade)
        if ok:
            size_mb = out_path.stat().st_size / 1024 / 1024
            log.info(f"[{key}] Block {b_idx}: ✓ {size_mb:.0f}MB")
        else:
            log.error(f"[{key}] Block {b_idx}: FAILED")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--series", help="Compile only this series key (glacier/waterfall/bamboo/desert/cosmic)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Regenerate even if block already exists")
    args = parser.parse_args()

    targets = {args.series: SERIES[args.series]} if args.series and args.series in SERIES else SERIES
    if args.series and args.series not in SERIES:
        log.error(f"Unknown series: {args.series}. Valid: {list(SERIES.keys())}")
        sys.exit(1)

    for key, (pattern, target_h, xfade) in targets.items():
        compile_series(key, pattern, target_h, xfade, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
