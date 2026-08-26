#!/usr/bin/env python3
"""
Cut 60-second lullaby shorts from existing lullaby long videos.
No re-render — simple FFmpeg trim with fade, keeps landscape 1920x1080.
Outputs: short_lullaby_*.mp4 + meta + copies thumb from long video.

Usage:
    python3 scripts/generate_lullaby_shorts.py
    python3 scripts/generate_lullaby_shorts.py --dry-run
    python3 scripts/generate_lullaby_shorts.py --offset 120
"""
import argparse
import shutil
import subprocess
import yaml
from pathlib import Path
from datetime import datetime

ROOT     = Path(__file__).resolve().parent.parent
QUEUE_EN = ROOT / "output" / "queue"
QUEUE_AR = ROOT / "output" / "queue_ar"

DATE_STR   = datetime.now().strftime("%Y%m%d")
SHORT_SECS = 60
FADE_SECS  = 1


LULLABY_NAMES = {
    "sleepy_stars":  {"en": "Sleepy Stars 🌟",   "ar": "النجوم النائمة 🌟"},
    "ocean_night":   {"en": "Ocean Night 🌊",    "ar": "ليلة المحيط 🌊"},
    "moon_garden":   {"en": "Moon Garden 🌙",    "ar": "حديقة القمر 🌙"},
    "sleepy_train":  {"en": "Sleepy Train 🚂",   "ar": "قطار النوم 🚂"},
    "rain_window":   {"en": "Rain & Piano 🌧️",   "ar": "المطر والبيانو 🌧️"},
    "forest_night":  {"en": "Forest Night 🌲",   "ar": "ليلة الغابة 🌲"},
}


def make_meta(key: str, lang: str) -> dict:
    names = LULLABY_NAMES.get(key, {"en": key.replace("_", " ").title(), "ar": key})
    name  = names[lang]
    if lang == "ar":
        return {
            "title":       f"🌙 {name} | موسيقى نوم للأطفال #shorts | هابي بير كيدز",
            "description": (
                f"🌙 {name} — موسيقى هادئة لنوم الرضع والأطفال الصغار\n\n"
                "✨ بدون كلام — مناسبة لجميع اللغات\n"
                "🌙 مثالية لوقت النوم والاسترخاء\n\n"
                "#نوم_الأطفال #موسيقى_نوم #هابي_بير_كيدز #رضع #shorts"
            ),
            "video_type":    "sleep_short",
            "language":      "ar",
            "is_short":      True,
            "status":        "public",
            "made_for_kids": True,
            "tags": [
                "موسيقى نوم", "نوم الأطفال", "هابي بير كيدز",
                "تهدئة", "رضع", "لولبي", "shorts",
            ],
        }
    else:
        return {
            "title":       f"🌙 {name} | Baby Sleep Music #shorts | Happy Bear Kids",
            "description": (
                f"🌙 {name} — gentle lullaby music for babies and toddlers\n\n"
                "✨ No words — safe for all languages\n"
                "🌙 Perfect for bedtime and naptime\n"
                "🎵 Original music by Happy Bear Kids (AI-generated, © 2026)\n\n"
                "#babysleep #lullaby #sleepmusic #happybearkids #toddler #shorts"
            ),
            "video_type":    "sleep_short",
            "language":      "en",
            "is_short":      True,
            "status":        "public",
            "made_for_kids": True,
            "tags": [
                "baby sleep music", "lullaby", "sleep music", "happy bear kids",
                "toddler", "bedtime", "lullaby shorts", "shorts",
            ],
        }


def extract_short(src: Path, dst: Path, offset: int, dry_run: bool) -> bool:
    if dry_run:
        print(f"    [DRY RUN] would cut {src.name} → {dst.name}")
        return True

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(offset),
        "-i", str(src),
        "-t", str(SHORT_SECS),
        "-vf", f"fade=t=in:st=0:d={FADE_SECS},fade=t=out:st={SHORT_SECS - FADE_SECS}:d={FADE_SECS}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        str(dst),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if r.returncode != 0 or not dst.exists():
        print(f"    ✗ FFmpeg failed: {r.stderr[-200:]}")
        return False
    print(f"    ✓ {dst.name} ({dst.stat().st_size // 1024}KB)")
    return True


def process_queue(queue_dir: Path, lang: str, offset: int, dry_run: bool) -> int:
    sources = sorted(queue_dir.glob("lullaby_*.mp4"))
    if not sources:
        print(f"  [{lang.upper()}] No lullaby_*.mp4 in {queue_dir.name}/")
        return 0

    done = 0
    for src in sources:
        # Extract key from filename: lullaby_sleepy_stars_20260824.mp4 → sleepy_stars
        stem  = src.stem  # lullaby_sleepy_stars_20260824
        parts = stem.split("_")
        # key is everything between "lullaby_" and the date
        key   = "_".join(p for p in parts[1:] if not p.isdigit() and len(p) != 8)
        # fallback: drop last segment if it looks like a date
        if parts[-1].isdigit() and len(parts[-1]) == 8:
            key = "_".join(parts[1:-1])

        short_name = f"short_{stem}"
        dst        = queue_dir / f"{short_name}.mp4"
        meta_path  = queue_dir / f"meta_{short_name}.yaml"
        thumb_dst  = queue_dir / f"thumb_{short_name}.png"

        if dst.exists():
            print(f"  [{lang.upper()}] EXISTS: {dst.name}")
            done += 1
            continue

        print(f"  [{lang.upper()}] {src.name} → short (offset {offset}s)")
        ok = extract_short(src, dst, offset, dry_run)
        if ok and not dry_run:
            meta_path.write_text(
                yaml.dump(make_meta(key, lang), allow_unicode=True, sort_keys=False)
            )
            # Copy thumb from long video
            thumb_src = queue_dir / f"thumb_{stem}.png"
            if thumb_src.exists():
                shutil.copy2(thumb_src, thumb_dst)
                print(f"    ✓ thumb copied")
            done += 1

    return done


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--offset", type=int, default=60,
                        help="Seconds into video to start the short (default 60)")
    args = parser.parse_args()

    print("=== Lullaby Shorts Generator ===")
    total = 0
    for queue_dir, lang in [(QUEUE_EN, "en"), (QUEUE_AR, "ar")]:
        total += process_queue(queue_dir, lang, args.offset, args.dry_run)
    print(f"\nDone: {total} short(s) generated.")


if __name__ == "__main__":
    main()
