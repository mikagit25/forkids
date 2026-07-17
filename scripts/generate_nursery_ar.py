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
        "music":          "Moonlight Waltz.mp3",
        "tts_voice":      "ar-EG-SalmaNeural",
        "duration_min":   22,
        "thumb_prompt":   "cute cartoon yellow duck splashing in blue water, happy Arabic children's song, bright cheerful animation style, no text, no letters, no words, no numbers, 1280x720",
    },
    "ya_matar": {
        "doc_id":         "1qaEqvUkGgKdXZup6KlwHGa4-IMgRbTdS_KHUFUkZRZ8",
        "title_arabic":   "يا مطر",
        "title_english":  "Ya Matar — The Rain Song",
        "sprite":         "objects/cloud_3d.png",
        "bg_top":         "#546E7A",
        "bg_bottom":      "#78909C",
        "accent":         "#80DEEA",
        "music":          "Rain Etude in C Minor v2.mp3",
        "tts_voice":      "ar-EG-SalmaNeural",
        "duration_min":   22,
        "thumb_prompt":   "cute cartoon rain cloud with smile, colorful raindrops falling, children's animation style, bright sky, no text, no letters, no words, no numbers, 1280x720",
    },
    "dajaja": {
        "doc_id":         "1PmbQnBPFcJ8HBUnVbiOMw9x-cTD4R_rFql3cxv9keI4",
        "title_arabic":   "دجاجة",
        "title_english":  "Dajaja — The Chicken Song",
        "sprite":         "animals_flux/parrot.png",
        "bg_top":         "#FFF9C4",
        "bg_bottom":      "#A5D6A7",
        "accent":         "#FF8F00",
        "music":          "Morning Trail v2.mp3",
        "tts_voice":      "ar-EG-SalmaNeural",
        "duration_min":   22,
        "thumb_prompt":   "cute cartoon colorful bird on a sunny farm, colorful grass and sunshine, happy Arabic children's song animation style, no text, no letters, no words, no numbers, 1280x720",
    },
}

FPS = 30

# ── Fetch Google Doc text ─────────────────────────────────────────────────────

def fetch_doc(doc_id: str) -> str:
    url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
    with urllib.request.urlopen(url, timeout=15) as r:
        return r.read().decode("utf-8")


# ── Parse doc into segments ───────────────────────────────────────────────────

def parse_doc(text: str, target_minutes: int = 22) -> list[dict]:
    """
    Extract lyric phrase pairs from doc, then expand to fill target_minutes.

    Strategy 1 (preferred): find explicit "* Arabic text: X / * English subtitle: Y"
    pairs from the per-Line sections of the scenario doc.

    Strategy 2 (fallback): core "Arabic (vocals):" block split by Arabic punctuation.

    Returns: [{arabic, english, animation, duration_sec, _unique_idx}]
    The _unique_idx field identifies which TTS audio file to use (reused across rounds).
    """
    # Strategy 1 — explicit bullet pairs inside Line X: sections
    pairs = re.findall(
        r'\*\s*Arabic text:\s*([^\n]+)\n\s*\*\s*English subtitle[s]?:\s*([^\n]+)',
        text
    )
    if pairs:
        pairs = [(a.strip(), e.strip()) for a, e in pairs if a.strip()]

    # Strategy 2 — core lyrics block, split by Arabic sentence markers
    if not pairs:
        core_ar = re.search(r'Arabic \(vocals\):\s*\n(.*?)\n(?:English|___)', text, re.DOTALL)
        core_en = re.search(r'English subtitles:\s*\n(.*?)\n(?:___|\n\n)', text, re.DOTALL)
        if core_ar:
            ar_text = core_ar.group(1).strip()
            en_text = core_en.group(1).strip() if core_en else ""
            ar_parts = [p.strip() for p in re.split(r'(?<=[؟!])\s+', ar_text) if p.strip()]
            en_parts = [p.strip() for p in re.split(r'(?<=[?!])\s+', en_text) if p.strip()]
            pairs = list(zip(ar_parts, en_parts or [""] * len(ar_parts)))

    if not pairs:
        print("  WARNING: Could not extract phrase pairs, using full-text scan")
        return _fallback_parse(text)

    n = len(pairs)
    print(f"  Extracted {n} unique lyric phrases")

    # How many rounds to fill target_minutes
    seg_dur = 8       # seconds per phrase
    bridge_dur = 15   # seconds between rounds
    round_dur = n * seg_dur + bridge_dur
    n_rounds = max(4, round(target_minutes * 60 / round_dur))

    animations = ["bounce", "swim", "walk", "wave", "bounce", "swim", "walk", "wave"]
    segments = []
    for round_num in range(n_rounds):
        dur = 8 if round_num < n_rounds * 0.6 else 6
        for idx, (ar, en) in enumerate(pairs):
            segments.append({
                "arabic":       ar,
                "english":      en,
                "animation":    animations[(round_num + idx) % len(animations)],
                "duration_sec": dur,
                "_unique_idx":  idx,   # index into the TTS audio file set
            })
        segments.append({
            "arabic":       "",
            "english":      "",
            "animation":    "idle",
            "duration_sec": bridge_dur,
            "_unique_idx":  None,
        })

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
                "_unique_idx": len(segments),
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

    # Cache audio durations per unique phrase index (avoid ffprobe on every repeated segment)
    dur_cache: dict[int, float] = {}

    for seg in segments_raw:
        uid = seg.get("_unique_idx")
        audio_file = None

        if uid is not None:
            audio_path = audio_dir / f"seg_{uid:03d}.mp3"
            if audio_path.exists():
                if uid not in dur_cache:
                    dur_cache[uid] = get_audio_duration(audio_path)
                dur_sec = max(dur_cache[uid], seg["duration_sec"])
                audio_file = f"seg_{uid:03d}.mp3"
            else:
                dur_sec = seg["duration_sec"]
        else:
            dur_sec = seg["duration_sec"]

        dur_frames = round(dur_sec * fps)

        remotion_segments.append({
            "arabic":         seg["arabic"],
            "english":        seg["english"],
            "startFrame":     current_frame,
            "durationFrames": dur_frames,
            "audioFile":      audio_file,
            "animation":      seg["animation"],
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

def _load_gat():
    import importlib.util
    spec = importlib.util.spec_from_file_location("gat", ROOT / "scripts" / "generate_ai_thumbs.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def generate_thumbnail(cfg: dict, out_path: Path) -> bool:
    if not TOGETHER_KEY_FILE.exists():
        print("    no Together.ai key — skip thumbnail")
        return False
    try:
        key = TOGETHER_KEY_FILE.read_text().strip()
        prompt = cfg.get("thumb_prompt",
            f"cute cartoon character for Arabic nursery rhyme {cfg['title_english']}, "
            f"children's YouTube thumbnail, bright vivid colors, no text, no letters, no words, no numbers, 1280x720"
        )
        gat = _load_gat()
        img = gat.together_generate_image(prompt, key)
        if img:
            out_path.write_bytes(gat.resize_to_720p(img))
            print(f"    thumb → {out_path.name} ({out_path.stat().st_size // 1024}KB)")
            return True
        print(f"    thumbnail failed: API returned no image")
        return False
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
            f'🎵 موسيقى أصلية من هابي بير كيدز\n\n'
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
            f'🎵 Original music by Happy Bear Kids (AI-generated, © 2026)\n\n'
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
        # Only generate TTS for unique phrases (indexed by _unique_idx)
        seen = set()
        for seg in segments:
            uid = seg.get("_unique_idx")
            if uid is None or not seg.get("arabic") or uid in seen:
                continue
            seen.add(uid)
            out_path = audio_dir / f"seg_{uid:03d}.mp3"
            if out_path.exists():
                print(f"    [{uid:03d}] cached  {seg['arabic'][:35]}")
                continue
            if not args.dry_run:
                ok = asyncio.run(generate_tts_segment(seg["arabic"], cfg["tts_voice"], out_path))
                if ok:
                    print(f"    [{uid:03d}] ✓ {seg['arabic'][:35]}")
                else:
                    print(f"    [{uid:03d}] ✗ failed: {seg['arabic'][:35]}")
            else:
                print(f"    [{uid:03d}] [DRY RUN] {seg['arabic'][:35]}")
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
