#!/usr/bin/env python3
"""
Generate Arabic nursery rhyme video from Google Doc scenario.

Reads the doc → extracts segments (arabic/english/animation/duration) →
generates TTS audio per segment via edge-tts → renders via Remotion NurseryRhymeLong.

Usage:
    python3 scripts/generate_nursery_ar.py --key batta_batta
    python3 scripts/generate_nursery_ar.py --key ya_matar
    python3 scripts/generate_nursery_ar.py --key dajaja
    python3 scripts/generate_nursery_ar.py --key batta_batta --dry-run
"""

import argparse
import asyncio
import base64
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

TOGETHER_KEY_FILE = ROOT / "credentials" / "together_api_key.txt"
TOGETHER_URL      = "https://api.together.xyz/v1/images/generations"

NURSERY_CONFIGS = {
    "batta_batta": {
        "doc_id":         "1MSKfq670CN-gcYZ-9DNm45eCNgxA2gQVDWiQIE5g1ws",
        "title_arabic":   "بتة بتة",
        "title_english":  "Batta Batta — The Duck Song",
        "sprite":         "animals_flux/duck.png",
        "bg_top":         "#87CEEB",
        "bg_bottom":      "#4FC3F7",
        "accent":         "#FFD700",
        "music":          "Fluffing a Duck.mp3",
        "tts_voice":      "ar-EG-SalmaNeural",
        "duration_min":   22,
        "thumb_prompt":   "cute cartoon yellow duck splashing in blue water, happy Arabic children's song, bright cheerful animation style, no text, no letters, no words, no numbers, 1280x720",
    },
    "ya_matar": {
        "doc_id":         "1qaEqvUkGgKdXZup6KlwHGa4-IMgRbTdS_KHUFUkZRZ8",
        "title_arabic":   "يا مطر",
        "title_english":  "Ya Matar — The Rain Song",
        "sprite":         "objects_flux/rain_cloud.png",
        "bg_top":         "#546E7A",   # stormy grey
        "bg_bottom":      "#78909C",
        "accent":         "#80DEEA",
        "music":          "Crinoline Dreams.mp3",
        "tts_voice":      "ar-EG-SalmaNeural",
        "duration_min":   22,
        "fallback_sprite": "animals_flux/duck.png",
        "thumb_prompt":   "cute cartoon rain cloud with smile, colorful raindrops falling, children's animation style, bright sky, no text, no letters, no words, no numbers, 1280x720",
    },
    "dajaja": {
        "doc_id":         "1PmbQnBPFcJ8HBUnVbiOMw9x-cTD4R_rFql3cxv9keI4",
        "title_arabic":   "دجاجة",
        "title_english":  "Dajaja — The Chicken Song",
        "sprite":         "objects_flux/chicken.png",
        "bg_top":         "#FFF9C4",
        "bg_bottom":      "#A5D6A7",
        "accent":         "#FF8F00",
        "music":          "Carefree.mp3",
        "tts_voice":      "ar-EG-SalmaNeural",
        "duration_min":   22,
        "fallback_sprite": "animals_flux/duck.png",
        "thumb_prompt":   "cute cartoon chicken on a sunny farm, colorful grass and sunshine, happy Arabic children's song animation style, no text, no letters, no words, no numbers, 1280x720",
    },
}

FPS = 30

# ── Fetch Google Doc text ─────────────────────────────────────────────────────

def fetch_doc(doc_id: str) -> str:
    url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
    with urllib.request.urlopen(url, timeout=15) as r:
        return r.read().decode("utf-8")


# ── Parse doc into segments ───────────────────────────────────────────────────

def parse_doc(text: str) -> list[dict]:
    """
    Extract lyric segments from doc.
    Looks for patterns:
      Arabic (vocals): <arabic text>
      English subtitles: <english text>
    Also extracts structured segments from STRUCTURE or line-by-line sections.
    Returns: [{arabic, english, animation, duration_sec}]
    """
    segments = []

    # Extract core song lyrics block
    core_ar = re.search(r'Arabic \(vocals\):\s*\n(.*?)\n(?:English|___)', text, re.DOTALL)
    core_en = re.search(r'English subtitles:\s*\n(.*?)\n(?:___|\n\n)', text, re.DOTALL)

    if not core_ar:
        print("  WARNING: Could not find Arabic lyrics block, using full text scan")
        return _fallback_parse(text)

    arabic_full = core_ar.group(1).strip()
    english_full = core_en.group(1).strip() if core_en else ""

    # Split into lines
    ar_lines = [l.strip() for l in arabic_full.split('\n') if l.strip()]
    en_lines = [l.strip() for l in english_full.split('\n') if l.strip()]

    # Build segment list — repeat lyrics across the full video duration
    # Each line ~8 seconds, 4 rounds + bridges
    animations = ["bounce", "swim", "walk", "bounce", "wave", "bounce", "swim", "bounce"]

    for i, ar_line in enumerate(ar_lines):
        en_line = en_lines[i] if i < len(en_lines) else ""
        anim = animations[i % len(animations)]
        segments.append({
            "arabic":     ar_line,
            "english":    en_line,
            "animation":  anim,
            "duration_sec": 8,
        })

    # Also parse structured sections (Line 1:, Line 2: etc.)
    line_blocks = re.findall(
        r'Line \d+:.*?\n(.*?)\nAnimation:(.*?)\nSinging:(.*?)(?=\n___|Line \d+:|$)',
        text, re.DOTALL
    )
    if line_blocks:
        segments = []  # replace with detailed parse
        for ar_header, anim_desc, singing in line_blocks:
            ar_match = re.search(r'[؀-ۿ][^،\n]{3,}', ar_header + singing)
            en_match = re.search(r'English subtitle[s]?:\s*(.*)', ar_header + singing)
            if ar_match:
                segments.append({
                    "arabic":     ar_match.group(0).strip(),
                    "english":    en_match.group(1).strip() if en_match else "",
                    "animation":  "swim" if "swim" in anim_desc.lower() else
                                  "walk" if "walk" in anim_desc.lower() else "bounce",
                    "duration_sec": 10,
                })

    # Expand into full 22-min video: 4 rounds of lyrics + bridges
    if segments:
        full = []
        for round_num in range(4):
            anim_cycle = ["bounce", "swim", "bounce", "walk"][round_num % 4]
            for seg in segments:
                new_seg = dict(seg)
                new_seg["animation"] = anim_cycle
                new_seg["duration_sec"] = 8 if round_num < 2 else 6
                full.append(new_seg)
            # Bridge: silent pause segment
            full.append({
                "arabic":     "",
                "english":    "",
                "animation":  "swim",
                "duration_sec": 15,
            })
        segments = full

    return segments


def _fallback_parse(text: str) -> list[dict]:
    """Fallback: grab any Arabic-looking lines."""
    segments = []
    for line in text.split('\n'):
        ar = re.search(r'[؀-ۿ].{5,}', line)
        if ar:
            segments.append({
                "arabic": ar.group(0).strip(),
                "english": "",
                "animation": "bounce",
                "duration_sec": 8,
            })
    return segments


# ── TTS audio generation ──────────────────────────────────────────────────────

async def generate_tts_segment(text: str, voice: str, out_path: Path) -> bool:
    if not text.strip():
        return True  # silent segment, no audio needed
    try:
        import edge_tts
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(str(out_path))
        return True
    except Exception as e:
        print(f"    TTS error: {e}")
        return False


def get_audio_duration(path: Path) -> float:
    """Get audio duration in seconds via ffprobe."""
    try:
        r = subprocess.run([
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_streams", str(path)
        ], capture_output=True, text=True, timeout=10)
        data = json.loads(r.stdout)
        for s in data.get("streams", []):
            if "duration" in s:
                return float(s["duration"])
    except Exception:
        pass
    return 5.0  # fallback


# ── Build props JSON for Remotion ─────────────────────────────────────────────

def build_props(cfg: dict, segments_raw: list[dict], audio_dir: Path) -> dict:
    """Convert raw segments into Remotion NurseryRhymeLong props with frame timings."""
    fps = FPS
    remotion_segments = []
    current_frame = fps * 2  # 2s intro before lyrics

    for i, seg in enumerate(segments_raw):
        audio_file = None
        audio_path = audio_dir / f"seg_{i:03d}.mp3"

        if audio_path.exists() and seg.get("arabic"):
            dur_sec = max(get_audio_duration(audio_path), seg["duration_sec"])
        else:
            dur_sec = seg["duration_sec"]

        dur_frames = round(dur_sec * fps)

        if audio_path.exists() and seg.get("arabic"):
            audio_file = f"seg_{i:03d}.mp3"

        remotion_segments.append({
            "arabic":       seg["arabic"],
            "english":      seg["english"],
            "startFrame":   current_frame,
            "durationFrames": dur_frames,
            "audioFile":    audio_file,
            "animation":    seg["animation"],
        })
        current_frame += dur_frames

    # Outro: 3s
    total_frames = current_frame + fps * 3

    # Resolve sprite with fallback
    sprite = cfg["sprite"]
    sprite_full = ROOT / "remotion" / "public" / "sprites" / sprite
    if not sprite_full.exists() and "fallback_sprite" in cfg:
        print(f"  Sprite {sprite} not found, using fallback: {cfg['fallback_sprite']}")
        sprite = cfg["fallback_sprite"]

    return {
        "segments":       remotion_segments,
        "characterSprite": sprite,
        "bgColorTop":     cfg["bg_top"],
        "bgColorBottom":  cfg["bg_bottom"],
        "accentColor":    cfg["accent"],
        "musicFile":      cfg["music"],
        "titleArabic":    cfg["title_arabic"],
        "titleEnglish":   cfg["title_english"],
        "_totalFrames":   total_frames,
    }


# ── Make meta sidecar ─────────────────────────────────────────────────────────

def generate_thumbnail(cfg: dict, out_path: Path) -> bool:
    if not TOGETHER_KEY_FILE.exists():
        print("    no Together.ai key — skip thumbnail")
        return False
    try:
        import urllib.request as req
        key = TOGETHER_KEY_FILE.read_text().strip()
        prompt = cfg.get("thumb_prompt",
            f"cute cartoon character for Arabic nursery rhyme {cfg['title_english']}, "
            f"children's YouTube thumbnail, bright vivid colors, no text, no letters, no words, no numbers, 1280x720"
        )
        body = json.dumps({
            "model": "black-forest-labs/FLUX.1-schnell-Free",
            "prompt": prompt,
            "width": 1280, "height": 720,
            "steps": 4, "n": 1,
            "response_format": "b64_json",
        }).encode()
        request = req.Request(TOGETHER_URL, data=body,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        with req.urlopen(request, timeout=60) as r:
            data = json.loads(r.read())
        img_b64 = data["data"][0]["b64_json"]
        out_path.write_bytes(base64.b64decode(img_b64))
        print(f"    thumb → {out_path.name} ({out_path.stat().st_size // 1024}KB)")
        return True
    except Exception as e:
        print(f"    thumbnail failed: {e}")
        return False


def make_meta(cfg: dict, out_path: Path, lang: str) -> Path:
    title_ar = f'{cfg["title_arabic"]} | {cfg["title_english"]} | هابي بير كيدز'
    title_en = f'{cfg["title_english"]} | Arabic Nursery Rhyme | Happy Bear Kids'
    t_en = cfg["title_english"]
    t_ar = cfg["title_arabic"]

    if lang == "ar":
        title = title_ar
        desc = (
            f'🎵 استمتع بأغنية {t_ar} الجميلة!\n\n'
            f'هذه الأنشودة العربية الكلاسيكية للأطفال الصغار مقدمة بطريقة ممتعة وتفاعلية. '
            f'صُممت خصيصاً للأطفال من عمر 0 إلى 5 سنوات لمساعدتهم على تعلم اللغة العربية '
            f'من خلال الموسيقى والرسوم المتحركة الجذابة.\n\n'
            f'✨ ما يتعلمه طفلك:\n'
            f'• كلمات الأغنية العربية {t_ar}\n'
            f'• مفردات عربية جديدة من خلال الأناشيد\n'
            f'• إيقاع اللغة العربية وموسيقاها\n'
            f'• القيم الإيجابية من خلال الفن\n\n'
            f'🌟 مميزات الفيديو:\n'
            f'• رسوم متحركة ملونة وجذابة للأطفال\n'
            f'• صوت واضح ونطق صحيح للعربية\n'
            f'• موسيقى هادئة ومناسبة للأطفال\n'
            f'• مثالي للتعلم المبكر والتطور اللغوي\n'
            f'• آمن وخالٍ من الإعلانات للأطفال الصغار\n\n'
            f'👶 مناسب لـ:\n'
            f'• الرضع (0–12 شهر) للتحفيز السمعي والبصري\n'
            f'• الأطفال الصغار (1–3 سنوات) لتعلم الأناشيد\n'
            f'• ما قبل المدرسة (3–5 سنوات) لتعلم العربية\n\n'
            f'🔔 اشتركوا في هابي بير كيدز العربية → @happybearkidsar\n'
            f'فيديوهات تعليمية جديدة كل أسبوع!\n\n'
            f'🎵 الموسيقى الخلفية: Kevin MacLeod (incompetech.com)\n'
            f'رخصة Creative Commons Attribution 4.0\n'
            f'http://creativecommons.org/licenses/by/4.0/\n\n'
            f'#أناشيد_أطفال #هابي_بير_كيدز #{t_ar.replace(" ", "_")} '
            f'#تعليم_أطفال #أغاني_عربية #رياض_أطفال #لغة_عربية\n\n'
            f'© هابي بير كيدز 2026'
        )
    else:
        title = title_en
        desc = (
            f'🎵 Enjoy the beautiful Arabic nursery rhyme — {t_en}!\n\n'
            f'This classic Arabic children\'s song is presented in a fun and interactive way. '
            f'Designed specifically for children aged 0 to 5 to help them learn Arabic through '
            f'music and engaging animation.\n\n'
            f'✨ What your child will learn:\n'
            f'• The Arabic lyrics of {t_en}\n'
            f'• New Arabic vocabulary through songs\n'
            f'• The rhythm and music of the Arabic language\n'
            f'• Positive values through art and music\n\n'
            f'🌟 Video features:\n'
            f'• Colorful animated characters kids will love\n'
            f'• Clear pronunciation and proper Arabic diction\n'
            f'• Calm, child-appropriate background music\n'
            f'• Great for early learning and language development\n'
            f'• Safe, ad-free content for babies and toddlers\n\n'
            f'👶 Perfect for:\n'
            f'• Babies (0–12 months) — auditory and visual stimulation\n'
            f'• Toddlers (1–3 years) — learning nursery rhymes\n'
            f'• Preschoolers (3–5 years) — learning Arabic\n\n'
            f'🔔 Subscribe to Happy Bear Kids → @HappyBearKids1\n'
            f'New educational videos every week!\n\n'
            f'🎵 Background Music: Kevin MacLeod (incompetech.com)\n'
            f'Licensed under Creative Commons Attribution 4.0\n'
            f'http://creativecommons.org/licenses/by/4.0/\n\n'
            f'#ArabicNurseryRhyme #HappyBearKids #KidsSongs #BabySongs '
            f'#ArabicForKids #ToddlerLearning #PreschoolSongs\n\n'
            f'© Happy Bear Kids 2026'
        )

    meta = {
        "title":      title,
        "description": desc,
        "tags":       ["arabic nursery rhyme", "kids songs", t_en.lower(),
                       "baby songs", "toddler songs", "arabic for kids", "happy bear kids",
                       "children music", "educational", "preschool", t_ar,
                       "أناشيد أطفال", "تعليم عربي"],
        "video_type": "nursery_ar",
        "language":   lang,
        "is_short":   False,
        "status":     "public",
    }
    meta_path = out_path.parent / f"meta_{out_path.stem}.yaml"
    with open(meta_path, "w", encoding="utf-8") as f:
        yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    return meta_path


# ── Render via Remotion ───────────────────────────────────────────────────────

def render(props: dict, out_path: Path, dry_run: bool) -> bool:
    total_frames = props.pop("_totalFrames", FPS * 1380)
    props_json = json.dumps(props)

    cmd = [
        "npx", "remotion", "render",
        "NurseryRhymeLong",
        str(out_path),
        "--props", props_json,
        "--frames", f"0-{total_frames - 1}",
        "--concurrency", "2",
    ]
    print(f"  Rendering {total_frames} frames → {out_path.name}")
    if dry_run:
        print(f"  [DRY RUN] cmd: {' '.join(cmd[:6])}...")
        return True

    r = subprocess.run(cmd, cwd=str(ROOT / "remotion"), timeout=7200)
    return r.returncode == 0


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--key", required=True, choices=list(NURSERY_CONFIGS.keys()),
                        help="Which nursery rhyme to generate")
    parser.add_argument("--lang", choices=["ar", "en", "id", "both", "all"], default="ar",
                        help="Output language queue (both/all = en+ar+id)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-tts", action="store_true", help="Skip TTS generation")
    args = parser.parse_args()

    cfg = NURSERY_CONFIGS[args.key]
    date_str = time.strftime("%Y%m%d")
    audio_dir = ROOT / "assets" / "audio" / "nursery" / args.key
    audio_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*55}")
    print(f"  Nursery AR: {args.key} — {cfg['title_arabic']}")
    print(f"{'='*55}")

    # 1. Fetch & parse doc
    print("  Fetching scenario from Google Doc...")
    try:
        doc_text = fetch_doc(cfg["doc_id"])
        print(f"  Doc: {len(doc_text)} chars")
    except Exception as e:
        print(f"  ERROR fetching doc: {e}")
        sys.exit(1)

    segments = parse_doc(doc_text)
    print(f"  Parsed {len(segments)} lyric segments")

    # 2. Generate TTS for each segment
    if not args.skip_tts:
        print(f"  Generating TTS ({cfg['tts_voice']})...")
        for i, seg in enumerate(segments):
            if not seg.get("arabic"):
                continue
            out_path = audio_dir / f"seg_{i:03d}.mp3"
            if out_path.exists():
                continue
            if not args.dry_run:
                ok = asyncio.run(generate_tts_segment(seg["arabic"], cfg["tts_voice"], out_path))
                if ok:
                    print(f"    [{i:03d}] ✓ {seg['arabic'][:30]}")
                else:
                    print(f"    [{i:03d}] ✗ failed: {seg['arabic'][:30]}")
            else:
                print(f"    [{i:03d}] [DRY RUN] {seg['arabic'][:30]}")
    else:
        print("  Skipping TTS (--skip-tts)")

    # Copy audio to Remotion public
    remotion_audio = ROOT / "remotion" / "public" / "audio" / "nursery" / args.key
    remotion_audio.mkdir(parents=True, exist_ok=True)
    for mp3 in audio_dir.glob("*.mp3"):
        dst = remotion_audio / mp3.name
        if not dst.exists():
            import shutil
            shutil.copy2(mp3, dst)

    # 3. Build Remotion props
    props = build_props(cfg, segments, audio_dir)
    print(f"  Total duration: {props['_totalFrames'] / FPS / 60:.1f} min")

    # 4. Render for each language
    if args.lang in ("both", "all"):
        langs = ["en", "ar", "id"]
    else:
        langs = [args.lang]

    queue_map = {"en": ROOT/"output"/"queue", "ar": ROOT/"output"/"queue_ar", "id": ROOT/"output"/"queue_id"}

    for lang in langs:
        queue_dir = queue_map[lang]
        queue_dir.mkdir(parents=True, exist_ok=True)
        out_mp4 = queue_dir / f"nursery_{args.key}_{date_str}.mp4"

        print(f"\n  [{lang.upper()}] Rendering → {out_mp4.name}")
        ok = render(dict(props), out_mp4, args.dry_run)

        if ok and not args.dry_run:
            meta_path = make_meta(cfg, out_mp4, lang)
            print(f"  ✓ Meta: {meta_path.name}")
            thumb_path = queue_dir / f"thumb_{out_mp4.stem}.png"
            generate_thumbnail(cfg, thumb_path)
            print(f"  ✓ Video: {out_mp4.name}")
        elif ok:
            print(f"  [DRY RUN] would write to {out_mp4.name}")

    print("\n✓ Done.")


if __name__ == "__main__":
    main()
