#!/usr/bin/env python3
"""
Generate 45-second vertical Shorts from SleepClassicalLoop shared loop files.
Format: 1080×1920, center-cropped with black bars, fade in/out.
Output goes to queue_id (Classical Night Relax) as video_type: sleep_short.

Usage:
  python3 scripts/make_sleep_short.py --all
  python3 scripts/make_sleep_short.py --theme moon_clouds
  python3 scripts/make_sleep_short.py --theme rain_window --start 60
"""
import argparse, logging, subprocess, yaml
from datetime import datetime
from pathlib import Path

ROOT       = Path(__file__).resolve().parent.parent
LOOPS_DIR  = ROOT / "output" / "_sleep_loops"
QUEUE_CC   = ROOT / "output" / "queue_id"
TOGETHER_KEY_FILE = ROOT / "credentials" / "together_api_key.txt"
DATE_STR   = datetime.now().strftime("%Y%m%d")

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

SHORT_DURATION = 45  # seconds
FADE_SECS      = 2   # fade in + fade out duration

THEME_META = {
    "moon_clouds": {
        "title":   "🌙 Peaceful Night Sky | Classical Music Shorts | Classical Night Relax #shorts",
        "desc":    "45 seconds of peaceful classical music under a moonlit night sky. Perfect for a moment of calm. Subscribe for full sleep programs ▶ @ClassicalNightRelax\n\n#ClassicalMusic #SleepMusic #ClassicalNightRelax #Shorts #RelaxationMusic",
        "thumb_prompt": "peaceful night sky with full moon and stars, classical music relaxation, dark blue, cinematic, no text",
        "tags":    ["sleep music shorts", "classical music", "classical night relax", "night sky", "moon", "relaxation shorts", "shorts"],
    },
    "night_bear":  {
        "title":   "🐻 Sleeping Bear & Fireflies | Classical Lullaby Shorts | Classical Night Relax #shorts",
        "desc":    "A sleeping bear under a starlit sky with gentle fireflies. Soothing classical lullaby. Subscribe for full sleep programs ▶ @ClassicalNightRelax\n\n#LullabyShorts #ClassicalMusic #SleepingBear #ClassicalNightRelax #Shorts",
        "thumb_prompt": "sleeping bear silhouette with fireflies under moonlit night, classical lullaby, peaceful, dark forest, no text",
        "tags":    ["lullaby shorts", "sleeping bear", "fireflies", "classical lullaby", "classical night relax", "shorts"],
    },
    "warm_waves":  {
        "title":   "🌊 Ocean Waves at Dusk | Classical Music Shorts | Classical Night Relax #shorts",
        "desc":    "Warm ocean waves at sunset with classical music. 45 seconds of pure relaxation. Subscribe ▶ @ClassicalNightRelax\n\n#OceanShorts #ClassicalMusic #RelaxationShorts #ClassicalNightRelax #Shorts",
        "thumb_prompt": "ocean waves at dusk with warm amber sunset glow, classical music, peaceful, cinematic, no text",
        "tags":    ["ocean shorts", "waves", "sunset", "classical music", "classical night relax", "relaxation shorts", "shorts"],
    },
    "rain_window": {
        "title":   "🌧️ Rainy Window & Classical Music Shorts | Classical Night Relax #shorts",
        "desc":    "Rain on a window with warm candlelight inside. Perfect study or sleep ambiance. Subscribe ▶ @ClassicalNightRelax\n\n#RainShorts #ClassicalMusic #StudyShorts #ClassicalNightRelax #Shorts",
        "thumb_prompt": "rainy window with warm candlelight interior, cozy, classical music study, atmospheric, no text",
        "tags":    ["rain shorts", "rainy window", "cozy", "classical music", "study shorts", "classical night relax", "shorts"],
    },
}


def make_vertical_short(loop_mp4: Path, start: float, out_mp4: Path) -> bool:
    """
    Extract 45s from loop, convert to 1080x1920, add fade in/out.
    Strategy: scale to fit 1080w, pad to 1920h with black bars.
    """
    vf = (
        f"scale=1080:-2:force_original_aspect_ratio=decrease,"
        f"pad=1080:1920:0:(oh-ih)/2:black,"
        f"fade=t=in:st=0:d={FADE_SECS},"
        f"fade=t=out:st={SHORT_DURATION - FADE_SECS}:d={FADE_SECS}"
    )
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start),
        "-i", str(loop_mp4),
        "-t", str(SHORT_DURATION),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-an",                     # no audio in shared loop
        "-movflags", "+faststart",
        str(out_mp4),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if r.returncode != 0 or not out_mp4.exists():
        log.error(f"ffmpeg failed: {r.stderr[:200]}")
        return False
    return True


def write_meta(theme: str, out_mp4: Path):
    m = THEME_META[theme]
    meta = {
        "title":         m["title"],
        "description":   m["desc"],
        "video_type":    "sleep_short",
        "theme":         theme,
        "language":      "en",
        "is_short":      True,
        "status":        "public",
        "made_for_kids": False,
        "tags":          m["tags"],
    }
    meta_path = out_mp4.parent / f"meta_{out_mp4.stem}.yaml"
    with open(meta_path, "w") as f:
        yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    log.info(f"  Meta → {meta_path.name}")


def generate_thumbnail(theme: str, out_mp4: Path) -> bool:
    if not TOGETHER_KEY_FILE.exists():
        return False
    m = THEME_META[theme]
    prompt = m["thumb_prompt"]
    thumb_path = out_mp4.parent / f"thumb_{out_mp4.stem}.png"
    if thumb_path.exists():
        return True
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("gat", ROOT / "scripts" / "generate_ai_thumbs.py")
        gat  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gat)
        img = gat.together_generate_image(prompt, TOGETHER_KEY_FILE.read_text().strip())
        if img:
            # Resize to vertical 720x1280 for shorts
            from PIL import Image
            import io
            pil = Image.open(io.BytesIO(img)).resize((720, 1280), Image.LANCZOS)
            buf = io.BytesIO()
            pil.save(buf, "PNG")
            thumb_path.write_bytes(buf.getvalue())
            log.info(f"  Thumb → {thumb_path.name}")
            return True
        return False
    except Exception as e:
        log.warning(f"  Thumbnail skipped: {e}")
        return False


def process_theme(theme: str, start: float = 30.0, dry_run: bool = False, force: bool = False):
    loop_mp4 = LOOPS_DIR / f"loop_{theme}_ph00.mp4"
    if not loop_mp4.exists():
        log.warning(f"  Loop not found: {loop_mp4} — run generate_sleep_classical.py --render-loops-only first")
        return False

    out_name = f"sleep_short_{theme}_t{int(start)}_{DATE_STR}.mp4"
    out_mp4  = QUEUE_CC / out_name

    if out_mp4.exists() and not force:
        log.info(f"  EXISTS: {out_name} — skipping (use --force to redo)")
        write_meta(theme, out_mp4)
        return True

    log.info(f"  [{theme}] start={start}s → {out_name}")

    if dry_run:
        return True

    ok = make_vertical_short(loop_mp4, start, out_mp4)
    if not ok:
        return False

    size_mb = out_mp4.stat().st_size / 1024 / 1024
    log.info(f"  ✓ {size_mb:.1f}MB")

    write_meta(theme, out_mp4)
    generate_thumbnail(theme, out_mp4)
    return True


BATCH_OFFSETS = [0, 45, 90, 135, 180]   # 5 batches × 4 themes = 20 shorts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all",      action="store_true", help="Generate one short per theme at --start offset")
    parser.add_argument("--batch",    action="store_true", help="Generate all BATCH_OFFSETS × all themes (up to 20 shorts)")
    parser.add_argument("--theme",    choices=list(THEME_META.keys()), help="Specific theme")
    parser.add_argument("--start",    type=float, default=30.0, help="Start time in loop (sec)")
    parser.add_argument("--dry-run",  action="store_true")
    parser.add_argument("--force",    action="store_true")
    args = parser.parse_args()

    QUEUE_CC.mkdir(parents=True, exist_ok=True)

    # Determine theme list
    if args.theme:
        themes = [args.theme]
    else:
        themes = list(THEME_META.keys())

    if not args.all and not args.batch and not args.theme:
        parser.print_help()
        return

    # Determine offset list
    if args.batch:
        offsets = BATCH_OFFSETS
    else:
        offsets = [args.start]

    done = 0
    total = len(themes) * len(offsets)
    for offset in offsets:
        for theme in themes:
            log.info(f"\n[{theme} t={int(offset)}s]")
            if process_theme(theme, start=offset, dry_run=args.dry_run, force=args.force):
                done += 1

    log.info(f"\nDone: {done}/{total} shorts")


if __name__ == "__main__":
    main()
