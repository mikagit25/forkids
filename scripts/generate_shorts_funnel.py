#!/usr/bin/env python3
"""
Shorts Funnel — extract 60-second vertical clips from existing long videos.
Converts landscape 1920×1080 MP4s → vertical 1080×1920 with blurred background.
Generates meta for each short.  Designed to run via scenario_orchestrator.

Strategy:
  1. Scan output/queue/ (and queue_ar/, queue_id/) for long MP4s (is_short=False in meta)
  2. For each long video that doesn't already have a short clip extracted:
     - Find a good start time (e.g. 30s in to skip intros)
     - Extract 60s clip with ffmpeg pad-blur technique
     - Write short meta
  3. Limit to --max-per-run (default=5) to avoid long runs in the orchestrator.

Usage:
  python3 scripts/generate_shorts_funnel.py
  python3 scripts/generate_shorts_funnel.py --queue en --max-per-run 3
  python3 scripts/generate_shorts_funnel.py --dry-run
"""
import argparse, base64, re, shutil, subprocess, yaml
from datetime import datetime
from pathlib import Path
import requests

ROOT     = Path(__file__).resolve().parent.parent
QUEUE_EN = ROOT / "output" / "queue"
QUEUE_AR = ROOT / "output" / "queue_ar"
QUEUE_ID = ROOT / "output" / "queue_id"
TOGETHER_KEY_FILE = ROOT / "credentials" / "together_api_key.txt"
TOGETHER_URL      = "https://api.together.xyz/v1/images/generations"
DATE_STR = datetime.now().strftime("%Y%m%d")

QUEUE_DIRS = {"en": QUEUE_EN, "ar": QUEUE_AR, "id": QUEUE_ID}

# Video types that are good sources for funnel shorts
GOOD_SOURCE_TYPES = {
    "number_learn", "color_learn", "shape_learn", "shape_roundelay",
    "lullaby", "ocd_vehicles", "construction_music", "nature_calm",
    "satisfying_3fmt", "emotional_values", "sensory_loop", "dance",
    "stars_bubbles", "special_mechanics", "emotions_ocean", "ocean_creatures",
    "nursery_ar", "shadow_puppet",
}

# Start time offsets to use (cycle through these per source video)
START_TIMES = [30, 120, 300, 600, 900, 1200]


def get_video_duration(mp4: Path) -> float:
    """Get video duration in seconds via ffprobe."""
    r = subprocess.run([
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", str(mp4)
    ], capture_output=True, text=True)
    if r.returncode != 0:
        return 0.0
    import json
    try:
        return float(json.loads(r.stdout)["format"]["duration"])
    except Exception:
        return 0.0


def extract_vertical_clip(src: Path, start: float, duration: float, out: Path) -> bool:
    """Extract clip and convert to 1080×1920 with blurred background fill."""
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start),
        "-i", str(src),
        "-t", str(duration),
        "-vf", (
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            "boxblur=20:20,"
            "[blurred];"
            "[0:v]scale=1080:-2:force_original_aspect_ratio=decrease[fg];"
            "[blurred][fg]overlay=(W-w)/2:(H-h)/2"
        ),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-t", str(duration),
        str(out),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode == 0 and out.exists()


def extract_vertical_clip_simple(src: Path, start: float, duration: float, out: Path) -> bool:
    """Simpler crop-based vertical extraction (faster, slight crop)."""
    # For 1920×1080 → 1080×1920: use pillarbox approach
    # Scale 1080w, add black bars top/bottom (or blur)
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start),
        "-i", str(src),
        "-t", str(duration),
        "-vf", "scale=1080:608,pad=1080:1920:0:656:black",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        str(out),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode == 0 and out.exists()


def load_meta(mp4: Path) -> dict | None:
    """Load meta yaml for a video, return None if not found."""
    meta_path = mp4.parent / f"meta_{mp4.stem}.yaml"
    if not meta_path.exists():
        return None
    with open(meta_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def funnel_short_name(source_stem: str, start: int) -> str:
    """Build output filename for funnel short."""
    base = re.sub(r"_\d{8}$", "", source_stem)  # strip date suffix
    return f"funnel_{base}_t{start}_{DATE_STR}.mp4"


def make_short_meta(source_meta: dict, lang: str, title_override: str | None = None) -> dict:
    """Build short meta derived from source long video meta."""
    src_title = source_meta.get("title", "Happy Bear Kids Short")
    # Strip #shorts if already there, re-add cleanly
    clean_title = src_title.replace(" #shorts", "").replace("#shorts", "").strip()
    title = title_override or f"{clean_title} #shorts"

    src_desc = source_meta.get("description", "")
    # Short description derived from long
    if lang == "ar":
        desc = (
            f"مقطع قصير من: {clean_title}\n\n"
            f"تابع الفيديو الكامل على قناتنا!\n"
            f"اشترك ▶ @happybearkidsar\n\n"
            f"© Happy Bear Kids 2026\n"
            f"#HappyBearKids #أطفال #فيديو_قصير"
        )
    elif lang == "id":
        desc = (
            f"Klip pendek dari: {clean_title}\n\n"
            f"Tonton video lengkapnya di channel kami!\n"
            f"Subscribe ▶ @happybearkidsin\n\n"
            f"© Happy Bear Kids 2026\n"
            f"#HappyBearKids #Anak #VideoPendek"
        )
    else:
        desc = (
            f"Short clip from: {clean_title}\n\n"
            f"Watch the full video on our channel!\n"
            f"Subscribe ▶ @HappyBearKids1\n\n"
            f"© Happy Bear Kids 2026\n"
            f"#HappyBearKids #KidsVideo #Shorts"
        )

    src_tags = source_meta.get("tags", [])
    tags = (src_tags[:15] if src_tags else []) + ["shorts", "kids shorts", "happy bear kids", "baby shorts"]

    return {
        "title":            title,
        "description":      desc,
        "video_type":       "funnel_short",
        "theme":            source_meta.get("theme", "mixed"),
        "language":         lang,
        "duration_minutes": 1,
        "is_short":         True,
        "status":           "public",
        "made_for_kids":    lang != "id",   # false only for CNR adult channel
        "tags":             list(dict.fromkeys(tags))[:40],
        "source_video":     str(source_meta.get("title", "")),
    }


def generate_thumbnail(out: Path, prompt: str, lang: str) -> bool:
    thumb_path = out.parent / f"thumb_{out.stem}.png"
    if thumb_path.exists():
        return True
    if not TOGETHER_KEY_FILE.exists():
        return False
    api_key = TOGETHER_KEY_FILE.read_text().strip()
    if lang == "ar":
        prompt += ", no text, no letters, no words, no numbers"
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("gat", ROOT / "scripts" / "generate_ai_thumbs.py")
        gat = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gat)
        img = gat.together_generate_image(prompt, api_key)
        if img:
            thumb_path.write_bytes(gat.resize_to_720p(img))
            print(f"  thumb → {thumb_path.name}")
            return True
        return False
    except Exception:
        return False


def find_candidates(queue: Path) -> list[tuple[Path, dict]]:
    """Find long MP4s in queue that are good funnel sources."""
    candidates = []
    for mp4 in sorted(queue.glob("*.mp4")):
        meta = load_meta(mp4)
        if not meta:
            continue
        if meta.get("is_short", False):
            continue
        vtype = meta.get("video_type", "")
        if vtype not in GOOD_SOURCE_TYPES:
            continue
        dur = get_video_duration(mp4)
        if dur < 180:  # need at least 3 min to extract a short
            continue
        candidates.append((mp4, meta))
    return candidates


def already_extracted(source: Path, queue: Path, start: int) -> bool:
    """Check if a funnel short for this source+start already exists."""
    base = re.sub(r"_\d{8}$", "", source.stem)
    pattern = f"funnel_{base}_t{start}_*.mp4"
    return bool(list(queue.glob(pattern)))


def process_queue(queue_name: str, max_per_run: int, dry_run: bool) -> int:
    queue = QUEUE_DIRS[queue_name]
    lang  = queue_name
    candidates = find_candidates(queue)
    print(f"  [{queue_name}] {len(candidates)} source videos found")

    done = 0
    for src_mp4, src_meta in candidates:
        if done >= max_per_run:
            break

        duration = get_video_duration(src_mp4)
        # Find a start time that hasn't been extracted yet
        chosen_start = None
        for st in START_TIMES:
            if st + 62 > duration:
                continue
            if not already_extracted(src_mp4, queue, st):
                chosen_start = st
                break

        if chosen_start is None:
            continue  # all slots extracted already

        out_name = funnel_short_name(src_mp4.stem, chosen_start)
        out_mp4  = queue / out_name
        print(f"  [{queue_name}] {src_mp4.name} → {out_name} (start={chosen_start}s)")

        if dry_run:
            done += 1
            continue

        ok = extract_vertical_clip_simple(src_mp4, chosen_start, 60, out_mp4)
        if not ok:
            print(f"    ✗ ffmpeg failed")
            continue

        size_mb = out_mp4.stat().st_size / 1024 / 1024
        print(f"    ✓ {size_mb:.1f}MB")

        short_meta = make_short_meta(src_meta, lang)
        meta_path  = queue / f"meta_{out_mp4.stem}.yaml"
        with open(meta_path, "w", encoding="utf-8") as f:
            yaml.dump(short_meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        thumb_prompt = (
            f"colorful kids animation screenshot vertical format, "
            f"vibrant shapes and colors, toddler content, 1080x1920"
        )
        generate_thumbnail(out_mp4, thumb_prompt, lang)

        done += 1

    return done


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue",       default="en", choices=["en", "ar", "id", "all"])
    parser.add_argument("--max-per-run", type=int, default=5)
    parser.add_argument("--dry-run",     action="store_true")
    args = parser.parse_args()

    queues = ["en", "ar", "id"] if args.queue == "all" else [args.queue]
    total  = 0

    print(f"\n=== Shorts Funnel: queue={args.queue}, max={args.max_per_run} ===\n")
    for q in queues:
        n = process_queue(q, args.max_per_run, args.dry_run)
        total += n
        print(f"  [{q}] extracted: {n}")

    print(f"\nDone: {total} funnel shorts created")


if __name__ == "__main__":
    main()
