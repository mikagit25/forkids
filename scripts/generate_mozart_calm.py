#!/usr/bin/env python3
"""
Generate calm Mozart-themed videos (1 hour each).
Visuals: LullabyLoop composition rendered WITHOUT music.
Audio:   Mozart MP3 added via FFmpeg with volume fade at the end.

3 videos:
  romance  → stars theme  (Serenade in G, I. Romance — slow, lyrical)
  minuet   → garden theme (Serenade in G, II. Minuet — elegant, gentle)
  rondo    → ocean theme  (Serenade in G, III. Rondo — lively but calm)

Usage:
  python3 scripts/generate_mozart_calm.py              # all 3
  python3 scripts/generate_mozart_calm.py --keys romance minuet
  python3 scripts/generate_mozart_calm.py --dry-run
  python3 scripts/generate_mozart_calm.py --regen-meta
"""

import argparse
import base64
import json
import subprocess
import time
import yaml
import requests
from datetime import datetime
from pathlib import Path

ROOT      = Path(__file__).resolve().parent.parent
REMOTION  = ROOT / "remotion"
QUEUE_EN  = ROOT / "output" / "queue"
TMP_DIR   = ROOT / "output" / "tmp_mozart"
MUSIC_DIR = ROOT / "assets" / "music" / "mozart"

TOGETHER_KEY_FILE = ROOT / "credentials" / "together_api_key.txt"
TOGETHER_URL      = "https://api.together.xyz/v1/images/generations"

DATE_STR  = datetime.now().strftime("%Y%m%d")
FPS       = 30
LOOP_DUR  = 5 * 60          # 5-minute LullabyLoop visual

VIDEOS = {
    "romance": {
        "title":     "Mozart — Serenade in G Major: Romance 🎵 1 Hour Classical Music for Sleep & Relaxation",
        "movement":  "I. Romance (Andante)",
        "music_file":"Mozart - Serenade in G Major - I. Romance.mp3",
        "theme":     "stars",
        "bg_top":    "#020815",
        "bg_bottom": "#050A1A",
        "accent":    "#B8CCEA",
        "duration_min": 60,
        "thumb_prompt": (
            "moonlit night sky full of softly glowing stars, classical music theme, "
            "elegant golden musical notes floating gently in the dark blue air, "
            "dreamy peaceful atmosphere, deep blue and soft gold tones, "
            "cinematic digital art, no text, no people, no letters"
        ),
    },
    "minuet": {
        "title":     "Mozart — Serenade in G Major: Minuet 🎵 1 Hour Classical Music for Calm & Focus",
        "movement":  "II. Minuet (Menuetto: Allegretto)",
        "music_file":"Mozart - Serenade in G Major - II. Minuet.mp3",
        "theme":     "garden",
        "bg_top":    "#050A08",
        "bg_bottom": "#08120A",
        "accent":    "#88CC77",
        "duration_min": 60,
        "thumb_prompt": (
            "enchanted moonlit garden at night, softly glowing fireflies and flowers, "
            "elegant golden musical notes floating gently among the plants, "
            "classical Mozart era atmosphere, dark green and soft gold tones, "
            "dreamy cinematic art, no text, no people, no letters"
        ),
    },
    "rondo": {
        "title":     "Mozart — Serenade in G Major: Rondo 🎵 1 Hour Classical Music for Study & Relaxation",
        "movement":  "III. Rondo (Allegro)",
        "music_file":"Mozart - Serenade in G Major - III. Rondo.mp3",
        "theme":     "ocean",
        "bg_top":    "#020B18",
        "bg_bottom": "#041020",
        "accent":    "#4A90BB",
        "duration_min": 60,
        "thumb_prompt": (
            "deep ocean at night with glowing bioluminescent jellyfish, "
            "soft golden musical notes floating through the dark blue water, "
            "classical music theme, peaceful deep-sea atmosphere, "
            "cinematic digital art, no text, no people, no letters"
        ),
    },
}


def make_description(key: str) -> str:
    v = VIDEOS[key]
    return (
        f"🎵 {v['title']}\n\n"
        f"1 hour of peaceful Mozart classical music — {v['movement']} — "
        "paired with beautifully animated visuals. Perfect for sleep, relaxation, "
        "study, or quiet background listening.\n\n"
        "Wolfgang Amadeus Mozart (1756–1791) was one of the greatest composers in history. "
        "His Serenade in G Major, K. 525 ('Eine kleine Nachtmusik') is one of the most beloved works "
        "in the classical repertoire — elegant, light and timeless.\n\n"
        "✨ What you'll see:\n"
        "• Smoothly animated visuals — nothing static, always in gentle motion\n"
        "• Calming colours and soft glowing elements\n"
        "• Designed for peaceful background viewing for adults and children alike\n\n"
        "🎼 About the music:\n"
        f"• Composer: Wolfgang Amadeus Mozart\n"
        f"• Work: Serenade in G Major, K. 525 — {v['movement']}\n"
        "• Recording courtesy of Musopen (musopen.org)\n"
        "• License: Public Domain / CC0\n\n"
        "🌙 Perfect for:\n"
        "• Falling asleep\n"
        "• Deep study and focus\n"
        "• Meditation and relaxation\n"
        "• Peaceful background music\n"
        "• Babies, toddlers and adults alike\n\n"
        "Subscribe to Happy Bear Kids for more soothing classical and educational content!\n\n"
        "#Mozart #ClassicalMusic #SleepMusic #RelaxingMusic #EineKleineNachtmusik "
        "#ClassicalMusicForSleep #StudyMusic #BabyMusic #LullabyMusic #HappyBearKids "
        "#ClassicalLullaby #MozartForBabies #RelaxingClassical #1HourMusic"
    )


def make_meta(key: str) -> dict:
    return {
        "title":       VIDEOS[key]["title"],
        "description": make_description(key),
        "tags": [
            "Mozart", "classical music", "sleep music", "relaxing music",
            "Eine kleine Nachtmusik", "Serenade in G major", "classical music for sleep",
            "study music", "baby music", "lullaby music", "relaxation music",
            "peaceful music", "ambient classical", "Mozart for babies",
            "classical music babies", "sleep aid music", "calm music",
            "background music", "focus music", "Mozart lullaby",
            "1 hour music", "classical lullaby", "baby sleep music",
        ],
        "video_type": "lullaby_long",
        "language":   "en",
        "is_short":   False,
        "status":     "public",
    }


def generate_thumbnail(key: str, out_path: Path) -> bool:
    key_file = TOGETHER_KEY_FILE
    if not key_file.exists():
        print("  No Together.ai key — skip thumbnail")
        return False
    api_key = key_file.read_text().strip()
    prompt  = VIDEOS[key]["thumb_prompt"]
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("gat", ROOT / "scripts" / "generate_ai_thumbs.py")
        gat = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gat)
        img = gat.together_generate_image(prompt, api_key)
        if img:
            out_path.write_bytes(gat.resize_to_720p(img))
            print(f"  Thumbnail: {out_path.name} ({out_path.stat().st_size // 1024}KB)")
            return True
        print(f"  Thumbnail error: API returned no image")
        return False
    except Exception as e:
        print(f"  Thumbnail error: {e}")
        return False


def render_visual_loop(key: str, loop_mp4: Path, dry_run: bool) -> bool:
    """Render the 5-min LullabyLoop WITHOUT music (audio added separately by FFmpeg)."""
    v = VIDEOS[key]
    props = {
        "theme":         v["theme"],
        "bgColorTop":    v["bg_top"],
        "bgColorBottom": v["bg_bottom"],
        "accentColor":   v["accent"],
        "phaseOffset":   0.0,
        # musicFile omitted → no audio rendered
    }
    cmd = [
        "npx", "remotion", "render", "LullabyLoop",
        f"--props={json.dumps(props)}",
        f"--output={str(loop_mp4)}",
    ]
    print(f"  [render] {loop_mp4.name}")
    if dry_run:
        print("    DRY RUN — skipped")
        return True
    result = subprocess.run(cmd, cwd=str(REMOTION), capture_output=False, timeout=3600)
    return result.returncode == 0


def assemble_video(key: str, loop_mp4: Path, music_mp3: Path, out_mp4: Path, dry_run: bool) -> bool:
    """Concatenate 5-min visual loop to 60 min + add Mozart audio via FFmpeg."""
    v = VIDEOS[key]
    total_sec = v["duration_min"] * 60

    # Write concat playlist: enough loops to cover total duration
    n_loops  = (total_sec // LOOP_DUR) + 2
    playlist = TMP_DIR / f"playlist_{key}.txt"
    playlist.write_text("\n".join([f"file '{loop_mp4.resolve()}'" for _ in range(n_loops)]))

    cmd = [
        "ffmpeg", "-y",
        # Video: looped visual
        "-f", "concat", "-safe", "0", "-i", str(playlist),
        # Audio: Mozart track looped with -stream_loop -1
        "-stream_loop", "-1", "-i", str(music_mp3),
        "-t", str(total_sec),
        # Gentle video fade to black in last 60s
        "-vf", f"fade=t=out:st={total_sec - 60}:d=60",
        # Audio: slight volume reduction + fade out in last 90s
        "-af", f"volume=0.88,afade=t=out:st={total_sec - 90}:d=90",
        "-c:v", "libx264", "-crf", "22", "-preset", "fast",
        "-c:a", "aac", "-b:a", "128k",
        str(out_mp4),
    ]
    print(f"  [ffmpeg] {out_mp4.name} ({v['duration_min']} min)")
    if dry_run:
        print("    DRY RUN — skipped")
        return True
    result = subprocess.run(cmd, capture_output=False, timeout=7200)
    return result.returncode == 0


def process_key(key: str, dry_run: bool, regen_meta: bool) -> bool:
    v          = VIDEOS[key]
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    QUEUE_EN.mkdir(parents=True, exist_ok=True)

    out_mp4    = QUEUE_EN  / f"mozart_{key}_{DATE_STR}.mp4"
    loop_mp4   = TMP_DIR   / f"loop_{key}_visual.mp4"
    music_mp3  = MUSIC_DIR / v["music_file"]
    meta_path  = QUEUE_EN  / f"meta_mozart_{key}_{DATE_STR}.yaml"
    thumb_path = QUEUE_EN  / f"thumb_mozart_{key}_{DATE_STR}.png"

    print(f"\n{'='*60}\n  [{key.upper()}] {v['title'][:55]}...")
    print(f"  music: {v['music_file']}")
    print(f"  theme: {v['theme']}  duration: {v['duration_min']} min")

    if not music_mp3.exists():
        print(f"  ERROR: music not found: {music_mp3}")
        return False

    if not regen_meta:
        if out_mp4.exists():
            print(f"  Video exists — skipping render: {out_mp4.name}")
        else:
            if not loop_mp4.exists():
                ok = render_visual_loop(key, loop_mp4, dry_run)
                if not ok:
                    print("  FAILED: render_visual_loop")
                    return False
            ok = assemble_video(key, loop_mp4, music_mp3, out_mp4, dry_run)
            if not ok:
                print("  FAILED: assemble_video")
                return False

    # Write meta
    if out_mp4.exists() or dry_run:
        meta_path.write_text(yaml.dump(make_meta(key), allow_unicode=True, sort_keys=False))
        print(f"  Meta: {meta_path.name}")

        if not thumb_path.exists():
            time.sleep(5)   # respect Together.ai rate limit
            generate_thumbnail(key, thumb_path)
        else:
            print(f"  Thumb exists: {thumb_path.name}")

    return True


def main():
    parser = argparse.ArgumentParser(description="Generate Mozart calm lullaby videos")
    parser.add_argument("--keys",      nargs="+", choices=list(VIDEOS.keys()),
                        help="Which keys to process (default: all)")
    parser.add_argument("--dry-run",   action="store_true")
    parser.add_argument("--regen-meta", action="store_true",
                        help="Re-write meta + thumbnail only (skip render)")
    args = parser.parse_args()

    keys = args.keys or list(VIDEOS.keys())
    print(f"Mozart calm generator — keys: {keys}  dry_run={args.dry_run}")
    for key in keys:
        process_key(key, args.dry_run, args.regen_meta)
    print("\nDone.")


if __name__ == "__main__":
    main()
