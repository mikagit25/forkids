#!/usr/bin/env python3
"""
Generate SensoryBlobLoop videos: 5-min Remotion render → FFmpeg loop → 30/60 min.

Music: Suno AI v2-tracks (our own). Kevin MacLeod NOT used.
No text → one render → EN queue + AR queue copy.

Usage:
    python3 scripts/generate_sensory_blob.py
    python3 scripts/generate_sensory_blob.py --durations 30 60
    python3 scripts/generate_sensory_blob.py --sound --music "The Glass Forest v2.mp3"
    python3 scripts/generate_sensory_blob.py --dry-run
"""
import argparse
import base64
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import requests
import yaml

ROOT     = Path(__file__).resolve().parent.parent
REMOTION = ROOT / "remotion"
QUEUE_EN = ROOT / "output" / "queue"
QUEUE_AR = ROOT / "output" / "queue_ar"
TOGETHER_KEY_FILE = ROOT / "credentials" / "together_api_key.txt"
TOGETHER_URL      = "https://api.together.xyz/v1/images/generations"
TOGETHER_MODEL    = "black-forest-labs/FLUX.1-schnell"
DATE_STR          = datetime.now().strftime("%Y%m%d")
FPS               = 30
LOOP_FRAMES       = 5 * 60 * FPS   # 9000

# Calming Suno tracks suitable for sensory/meditative content
CALM_TRACKS = [
    "Dreamy Arpeggios v2.mp3",
    "The Glass Forest v2.mp3",
    "Moonlight Waltz.mp3",
    "Rainbow Lantern v2.mp3",
    "Spring Waltz v2.mp3",
]

THUMB_PROMPT = (
    "dark blue purple background with colorful glowing liquid blobs merging and morphing, "
    "abstract sensory art for babies, calming meditative metaball animation, "
    "vibrant neon pink cyan green orange purple glowing drops on dark, 1280x720, "
    "no text, no letters"
)
THUMB_PROMPT_AR = THUMB_PROMPT + ", no text, no letters, no words, no numbers"


def render_loop(sound: bool, music: str, out_path: Path, dry_run: bool) -> bool:
    props = {
        "sound":     sound,
        "musicFile": music if sound else "",
    }
    cmd = [
        "npx", "remotion", "render",
        "src/index.ts", "SensoryBlobLoop",
        str(out_path),
        "--props", json.dumps(props),
        "--frames", f"0-{LOOP_FRAMES - 1}",
        "--concurrency", "1",
        "--log", "error",
    ]
    print(f"  Rendering 5-min loop → {out_path.name}")
    if dry_run:
        print(f"  [DRY RUN] {' '.join(cmd[:6])} ...")
        return True
    res = subprocess.run(cmd, cwd=str(REMOTION), capture_output=True, text=True, timeout=3600)
    if res.returncode != 0:
        print(f"  ✗ Render failed:\n{res.stderr[-600:]}")
        return False
    sz = out_path.stat().st_size // 1024 // 1024
    print(f"  ✓ Rendered ({sz} MB)")
    return True


def ffmpeg_loop(src: Path, out: Path, total_min: int, dry_run: bool) -> bool:
    loop_count = (total_min * 60 * FPS) // LOOP_FRAMES  # total plays
    n_loops    = loop_count - 1                          # -stream_loop arg
    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", str(n_loops),
        "-i", str(src),
        "-c", "copy",
        "-movflags", "+faststart",
        str(out),
    ]
    print(f"  FFmpeg loop ×{loop_count} → {out.name} ({total_min} min)")
    if dry_run:
        print(f"  [DRY RUN] {' '.join(cmd[:5])} ...")
        return True
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if res.returncode != 0:
        print(f"  ✗ FFmpeg failed:\n{res.stderr[-400:]}")
        return False
    sz = out.stat().st_size // 1024 // 1024
    print(f"  ✓ {total_min}min video ({sz} MB)")
    return True


def generate_thumbnail(out_path: Path, lang: str, dry_run: bool) -> bool:
    if out_path.exists():
        return True
    if dry_run:
        print(f"  [DRY RUN] Thumb {lang.upper()} → {out_path.name}")
        return True
    try:
        api_key = TOGETHER_KEY_FILE.read_text().strip()
        prompt  = THUMB_PROMPT_AR if lang == "ar" else THUMB_PROMPT
        resp = requests.post(
            TOGETHER_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "python-requests/2.31.0",
            },
            json={
                "model": TOGETHER_MODEL,
                "prompt": prompt,
                "width": 1280, "height": 720,
                "steps": 4, "n": 1, "response_format": "b64_json",
            },
            timeout=90,
        )
        resp.raise_for_status()
        out_path.write_bytes(base64.b64decode(resp.json()["data"][0]["b64_json"]))
        print(f"  ✓ Thumb {lang.upper()} → {out_path.name}")
        return True
    except Exception as e:
        print(f"  ✗ Thumb {lang.upper()} failed: {e}")
        return False


def make_meta(lang: str, duration_min: int, sound: bool, music: str) -> dict:
    titles = {
        "en": f"🌈 Sensory Blobs | {duration_min} Min Calming Colors | Happy Bear Kids",
        "ar": f"🌈 فقاعات حسية | {duration_min} دقيقة ألوان مهدئة | هابي بير كيدز",
    }
    music_note_en = f"🎵 Original music by Happy Bear Kids (AI-generated, © 2026)" if sound else "🔇 Silent version — no music"
    music_note_ar = f"🎵 موسيقى أصلية من هابي بير كيدز" if sound else "🔇 نسخة بدون موسيقى"
    descs = {
        "en": (
            f"Watch colourful glowing blobs drift, merge, split and swirl in this soothing "
            f"{duration_min}-minute sensory experience! Smooth, hypnotic colour motion with "
            "no words, no surprises — just gentle shapes for the youngest viewers.\n\n"
            "🌈 Smooth colour morphing — no flashes, no sudden movements\n"
            "👶 Designed for babies 0–3 years\n"
            "🎨 Stimulates visual tracking and colour recognition\n"
            "🌙 Perfect for quiet time, nap time or background play\n"
            f"{music_note_en}\n\n"
            "#sensory #babyvideos #toddlervideos #calmingvideos #colorsforbabies "
            "#happybearkids #sensoryplay #babylearning #visualstimulation #quiettime "
            "#infantdevelopment #kidsrelax #mindfulbaby #blobcolors #goo"
        ),
        "ar": (
            f"شاهد الفقاعات الملونة المضيئة تتحرك وتتمازج في هذه التجربة الحسية المهدئة "
            f"لمدة {duration_min} دقيقة! حركة لونية ناعمة بدون كلام، بدون مفاجآت.\n\n"
            "🌈 مورفينج لوني ناعم — بدون وميض أو حركات مفاجئة\n"
            "👶 مصممة للرضع 0-3 سنوات\n"
            "🎨 تحفز التتبع البصري والتعرف على الألوان\n"
            "🌙 مثالية لوقت الهدوء وقيلولة الرضع\n"
            f"{music_note_ar}\n\n"
            "#حسي #فيديو_أطفال #هابي_بير_كيدز #ألوان_للأطفال #تنمية_الرضع #هدوء"
        ),
    }
    tags = [
        "sensory", "baby sensory", "calming video", "color blobs", "happy bear kids",
        "toddler videos", "baby videos", "visual stimulation", "quiet time",
        "sensory play", "baby development", "colors for babies", "infant videos",
        "relaxing baby", "morphing colors", "goo", "metaball",
    ]
    return {
        "title":         titles[lang],
        "description":   descs[lang],
        "tags":          tags,
        "video_type":    "sensory_blob",
        "language":      lang,
        "is_short":      False,
        "status":        "public",
        "made_for_kids": True,
        "music_track":   music if sound else "none",
        "ai_generated":  True,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--durations", nargs="+", type=int, default=[30, 60],
                        help="Output durations in minutes (default: 30 60)")
    parser.add_argument("--sound",   action="store_true",
                        help="Include ambient music (Suno AI track)")
    parser.add_argument("--music",   default="Dreamy Arpeggios v2.mp3",
                        help="Music filename in remotion/public/music/")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force",   action="store_true")
    args = parser.parse_args()

    sound     = args.sound
    music     = args.music
    dry_run   = args.dry_run
    durations = sorted(set(args.durations))

    sound_sfx = "_sound" if sound else ""
    loop_name = f"sensory_blob{sound_sfx}_5min_loop_{DATE_STR}"
    loop_path = QUEUE_EN / f"{loop_name}.mp4"

    print(f"\n=== SensoryBlobLoop ===")
    print(f"  Sound:     {sound}" + (f" ({music})" if sound else ""))
    print(f"  Durations: {durations} min")
    print(f"  Loop file: {loop_path.name}\n")

    # Step 1: render 5-min base loop
    if not loop_path.exists() or args.force:
        ok = render_loop(sound, music, loop_path, dry_run)
        if not ok:
            return
    else:
        print(f"  ✓ Loop file exists: {loop_path.name}")

    # Step 2: per-duration final videos
    for dur in durations:
        slug   = f"sensory_blob{sound_sfx}_{dur}min_{DATE_STR}"
        vid_en = QUEUE_EN / f"{slug}.mp4"
        vid_ar = QUEUE_AR / f"{slug}.mp4"

        if not vid_en.exists() or args.force:
            if not ffmpeg_loop(loop_path, vid_en, dur, dry_run):
                continue
        else:
            print(f"  ✓ {dur}min EN exists: {vid_en.name}")

        # AR copy
        if vid_en.exists() and (not vid_ar.exists() or args.force):
            if dry_run:
                print(f"  [DRY RUN] Copy {dur}min → queue_ar")
            else:
                shutil.copy2(vid_en, vid_ar)
                print(f"  ✓ Copied {dur}min → queue_ar")

        # Thumbnails
        thumb_en = QUEUE_EN / f"thumb_{slug}.png"
        thumb_ar = QUEUE_AR / f"thumb_{slug}.png"
        generate_thumbnail(thumb_en, "en", dry_run)
        generate_thumbnail(thumb_ar, "ar", dry_run)

        # Meta YAML
        for lang, queue in [("en", QUEUE_EN), ("ar", QUEUE_AR)]:
            meta_path = queue / f"meta_{slug}.yaml"
            if not meta_path.exists() or args.force:
                meta = make_meta(lang, dur, sound, music)
                if not dry_run:
                    meta_path.write_text(yaml.dump(meta, allow_unicode=True, sort_keys=False))
                    print(f"  ✓ Meta {lang.upper()} {dur}min → {meta_path.name}")
                else:
                    print(f"  [DRY RUN] meta {lang.upper()} {dur}min")

    # Clean up 5-min loop (not needed in queue, just used for FFmpeg input)
    if not dry_run and loop_path.exists():
        loop_path.unlink()
        print(f"\n  Cleaned up loop file: {loop_path.name}")

    print(f"\nDone — {len(durations)} duration(s), EN+AR.")


if __name__ == "__main__":
    main()
