#!/usr/bin/env python3
"""
Extract 60-second vertical Shorts from PeekABoo Long videos.
Converts 1920×1080 landscape → 1080×1920 vertical with blurred background.

Scans output/queue/ and output/queue_ar/ for peekaboo_*.mp4 that don't
already have a corresponding short.  Writes short_ prefixed file + meta.

Usage:
    python3 scripts/generate_peekaboo_shorts.py
    python3 scripts/generate_peekaboo_shorts.py --dry-run
    python3 scripts/generate_peekaboo_shorts.py --start-offset 60
"""
import argparse
import subprocess
import yaml
from pathlib import Path

ROOT     = Path(__file__).resolve().parent.parent
QUEUE_EN = ROOT / "output" / "queue"
QUEUE_AR = ROOT / "output" / "queue_ar"

OUT_W, OUT_H  = 1080, 1920
SHORT_SECS    = 60
FADE_SECS     = 1

VARIANT_LABELS = {
    "mix":          {"en": "Animals, Fruits & Veggies", "ar": "حيوانات وفواكه"},
    "animals":      {"en": "Animals",                   "ar": "الحيوانات"},
    "fruits":       {"en": "Fruits & Vegetables",       "ar": "فواكه وخضروات"},
    "fruits_veggies":{"en": "Fruits & Vegetables",      "ar": "فواكه وخضروات"},
}


def make_meta(slug: str, lang: str) -> dict:
    # slug: peekaboo_{variant}[_{theme}]_s{n}_{date}
    parts = slug.split("_")
    variant = parts[1] if len(parts) > 1 else "mix"
    label = VARIANT_LABELS.get(variant, VARIANT_LABELS["mix"])

    if lang == "ar":
        title = f"🎁 بيكا بو {label['ar']}! #shorts | هابي بير كيدز"
        desc  = (
            "من يختبئ في الصندوق؟ 🎁 شاهد الشخصيات الرائعة تظهر واحدة تلو الأخرى!\n\n"
            "🌟 مثالي للرضع والأطفال 0-3 سنوات\n"
            "🎉 بدون كلام — مناسب لجميع اللغات\n\n"
            "#بيكابو #أطفال #هابي_بير_كيدز #برامج_اطفال #مفاجأة #shorts"
        )
    else:
        title = f"🎁 Peek-a-Boo {label['en']}! #shorts | Happy Bear Kids"
        desc  = (
            "Who's hiding in the box? 🎁 Watch adorable 3D characters pop out one by one!\n\n"
            "🌟 Perfect for babies and toddlers 0–3 years\n"
            "🎉 No words — safe for all languages\n"
            "🎁 Every character gets their own colour box!\n\n"
            "#peekaboo #babyanimals #toddlervideos #happybearkids #shorts "
            "#surprisebox #babytv #kidsvideos #sensoryplay"
        )

    return {
        "title":         title,
        "description":   desc,
        "tags":          ["peek a boo", "peekaboo", "baby animals", "toddler videos",
                          "happy bear kids", "surprise box", "shorts", "baby tv",
                          "peek a boo game", "3d cartoon", "sensory play"],
        "video_type":    "peekaboo_short",
        "language":      lang,
        "is_short":      True,
        "status":        "public",
        "made_for_kids": True,
    }


def extract_short(src: Path, dst: Path, start: int, dry_run: bool) -> bool:
    # Blur-pad: scale to cover 1080×1920 blurred background, overlay scaled fg centred
    vf = (
        f"[0:v]scale={OUT_W}:{OUT_H}:force_original_aspect_ratio=increase,"
        f"crop={OUT_W}:{OUT_H},boxblur=25:3[bg];"
        f"[0:v]scale={OUT_W}:-2[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2,"
        f"fade=t=in:st=0:d={FADE_SECS},"
        f"fade=t=out:st={SHORT_SECS - FADE_SECS}:d={FADE_SECS}[out]"
    )
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start),
        "-i", str(src),
        "-t", str(SHORT_SECS),
        "-filter_complex", vf,
        "-map", "[out]",
        "-map", "0:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-c:a", "aac", "-b:a", "128k",
        str(dst),
    ]
    if dry_run:
        print(f"    [DRY RUN] {src.name} → {dst.name}")
        return True

    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if r.returncode != 0 or not dst.exists():
        print(f"    ✗ FFmpeg failed: {r.stderr[-250:]}")
        return False
    print(f"    ✓ {dst.name} ({dst.stat().st_size // 1024}KB)")
    return True


def process_queue(queue_dir: Path, lang: str, start_offset: int, dry_run: bool) -> int:
    sources = sorted(queue_dir.glob("peekaboo_*.mp4"))
    if not sources:
        print(f"  [{lang.upper()}] No peekaboo_*.mp4 found in {queue_dir.name}/")
        return 0

    done = 0
    for src in sources:
        slug      = src.stem                              # peekaboo_mix_warm_s1_20260810
        short_name = f"short_{slug}"
        dst        = queue_dir / f"{short_name}.mp4"
        meta_path  = queue_dir / f"meta_{short_name}.yaml"

        if dst.exists():
            print(f"  [{lang.upper()}] EXISTS: {dst.name}")
            done += 1
            continue

        print(f"  [{lang.upper()}] {src.name} → short (offset {start_offset}s)")
        ok = extract_short(src, dst, start_offset, dry_run)
        if ok:
            if not dry_run:
                meta_path.write_text(
                    yaml.dump(make_meta(slug, lang), allow_unicode=True, sort_keys=False)
                )
                print(f"    ✓ meta written")
            done += 1

    return done


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run",      action="store_true")
    parser.add_argument("--start-offset", type=int, default=30,
                        help="Seconds into video to start the short (default 30)")
    args = parser.parse_args()

    print("\n=== PeekABoo Shorts ===")
    print(f"Offset: {args.start_offset}s | Duration: {SHORT_SECS}s | Output: {OUT_W}×{OUT_H}\n")

    total = 0
    total += process_queue(QUEUE_EN, "en", args.start_offset, args.dry_run)
    total += process_queue(QUEUE_AR, "ar", args.start_offset, args.dry_run)

    print(f"\nDone: {total} short(s) generated.")


if __name__ == "__main__":
    main()
