#!/usr/bin/env python3
"""
Generate Indonesian nursery rhyme video from Google Doc scenario.

Reads the doc → extracts segments (indonesian/english/animation/duration) →
generates TTS audio per segment via edge-tts → renders via Remotion NurseryRhymeLong.

Usage:
    python3 scripts/generate_nursery_id.py --key balonku
    python3 scripts/generate_nursery_id.py --key cicak
    python3 scripts/generate_nursery_id.py --key balonku --dry-run
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
    "balonku": {
        "doc_id":          "1hHT1dyti8MzWtxWi-NSuRKLFYaPRbYj9NYlWGE1gS_I",
        "title_arabic":    "بالوني",
        "title_english":   "Balonku Ada Lima — Balloon Song",
        "title_local":     "Balonku Ada Lima",
        "sprite":          "objects_flux/balloon.png",
        "bg_top":          "#FF8A65",
        "bg_bottom":       "#FFCC02",
        "accent":          "#E91E63",
        "music":           "Carefree.mp3",
        "tts_voice":       "id-ID-ArdiNeural",
        "duration_min":    22,
        "fallback_sprite": "animals_flux/duck.png",
        "thumb_prompt":    "five colorful balloons floating in blue sky, happy cartoon style, children's Indonesian song, no text, no letters, no words, no numbers, 1280x720",
    },
    "cicak": {
        "doc_id":          "1lcShtapwuWRVx5nZKqs3fa8N_TlYcGnNJbwdROvOdyY",
        "title_arabic":    "ابرص",
        "title_english":   "Cicak-Cicak di Dinding — Gecko Song",
        "title_local":     "Cicak-Cicak di Dinding",
        "sprite":          "objects_flux/gecko.png",
        "bg_top":          "#A5D6A7",
        "bg_bottom":       "#81C784",
        "accent":          "#FF5722",
        "music":           "George Street Shuffle.mp3",
        "tts_voice":       "id-ID-ArdiNeural",
        "duration_min":    22,
        "fallback_sprite": "animals_flux/frog.png",
        "thumb_prompt":    "cute cartoon gecko on a colorful wall, tropical Indonesian setting, children's animation style, no text, no letters, no words, no numbers, 1280x720",
    },
    "naik_kereta": {
        "doc_id":          "1uZ2uup5PjbHrZHHHcCKG98b2AQv3yLSkxRlT9e2kTeo",
        "title_arabic":    "قطار",
        "title_english":   "Naik Kereta Api — Train Song",
        "title_local":     "Naik Kereta Api",
        "sprite":          "objects_flux/train.png",
        "bg_top":          "#42A5F5",
        "bg_bottom":       "#90CAF9",
        "accent":          "#F44336",
        "music":           "Circus of Freaks.mp3",
        "tts_voice":       "id-ID-ArdiNeural",
        "duration_min":    22,
        "fallback_sprite": "animals_flux/duck.png",
        "thumb_prompt":    "cute cartoon steam train on colorful railroad through tropical landscape, children's animation style, bright vivid colors, no text, no letters, no words, no numbers, 1280x720",
    },
    "pelangi": {
        "doc_id":          "11LV7YtG3wlJEhVQkuhdSBAeugjXs8-p5JWUP8UCBFO4",
        "title_arabic":    "قوس قزح",
        "title_english":   "Pelangi — Rainbow Song",
        "title_local":     "Pelangi-Pelangi",
        "sprite":          "objects_flux/rainbow.png",
        "bg_top":          "#E1F5FE",
        "bg_bottom":       "#B3E5FC",
        "accent":          "#FF9800",
        "music":           "Crinoline Dreams.mp3",
        "tts_voice":       "id-ID-ArdiNeural",
        "duration_min":    22,
        "fallback_sprite": "animals_flux/duck.png",
        "thumb_prompt":    "beautiful colorful rainbow over green hills, sunny sky with clouds, children's animation style, bright vivid colors, no text, no letters, no words, no numbers, 1280x720",
    },
    "dua_mata": {
        "doc_id":          "1ZEPOqdpsPjRsYkjlHMx_hD_suLy5j2hk3MhjaF08vyQ",
        "title_arabic":    "عينان",
        "title_english":   "Dua Mata Saya — Body Parts Song",
        "title_local":     "Dua Mata Saya",
        "sprite":          "animals_flux/bear.png",
        "bg_top":          "#F8BBD0",
        "bg_bottom":       "#FCE4EC",
        "accent":          "#E91E63",
        "music":           "Carefree.mp3",
        "tts_voice":       "id-ID-ArdiNeural",
        "duration_min":    22,
        "thumb_prompt":    "cute cartoon bear character pointing to its eyes, body parts learning, children's animation style, bright pastel colors, no text, no letters, no words, no numbers, 1280x720",
    },
    "kebunku": {
        "doc_id":          "1oIY2INGvWZ05tQZ7hkG6ScJ4IoT46eEijOKdP5gEScw",
        "title_arabic":    "حديقتي",
        "title_english":   "Kebunku — My Garden Song",
        "title_local":     "Kebunku",
        "sprite":          "objects_flux/flower.png",
        "bg_top":          "#DCEDC8",
        "bg_bottom":       "#A5D6A7",
        "accent":          "#FF9800",
        "music":           "George Street Shuffle.mp3",
        "tts_voice":       "id-ID-ArdiNeural",
        "duration_min":    22,
        "fallback_sprite": "animals_flux/frog.png",
        "thumb_prompt":    "cute cartoon garden with colorful flowers and butterflies, Indonesian children's song, bright vivid colors, no text, no letters, no words, no numbers, 1280x720",
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
    """Extract lyric segments from Indonesian nursery rhyme doc."""
    segments = []

    # Extract core song lyrics block (Bahasa Indonesia)
    core_id = re.search(r'Bahasa Indonesia \(vocals\):\s*\n(.*?)\n(?:English|___)', text, re.DOTALL)
    core_en = re.search(r'English subtitles:\s*\n(.*?)\n(?:___|\n\n)', text, re.DOTALL)

    if not core_id:
        print("  WARNING: Could not find Bahasa Indonesia lyrics block, using full text scan")
        return _fallback_parse(text)

    id_full = core_id.group(1).strip()
    en_full = core_en.group(1).strip() if core_en else ""

    id_lines = [l.strip() for l in id_full.split('\n') if l.strip()]
    en_lines = [l.strip() for l in en_full.split('\n') if l.strip()]

    animations = ["bounce", "walk", "bounce", "wave", "bounce", "walk", "bounce", "swim"]

    for i, id_line in enumerate(id_lines):
        en_line = en_lines[i] if i < len(en_lines) else ""
        segments.append({
            "arabic":       id_line,   # reuse "arabic" field for local language text
            "english":      en_line,
            "animation":    animations[i % len(animations)],
            "duration_sec": 8,
        })

    # Expand: 4 rounds + bridges
    if segments:
        full = []
        for round_num in range(4):
            anim_cycle = ["bounce", "walk", "bounce", "wave"][round_num % 4]
            for seg in segments:
                new_seg = dict(seg)
                new_seg["animation"] = anim_cycle
                new_seg["duration_sec"] = 8 if round_num < 2 else 6
                full.append(new_seg)
            full.append({"arabic": "", "english": "", "animation": "idle", "duration_sec": 12})
        segments = full

    return segments


def _fallback_parse(text: str) -> list[dict]:
    """Fallback: grab Indonesian-looking lines (capitalized words)."""
    segments = []
    for line in text.split('\n'):
        line = line.strip()
        if len(line) > 10 and re.match(r'[A-Z][a-z]', line) and not line.startswith('http'):
            segments.append({
                "arabic": line, "english": "", "animation": "bounce", "duration_sec": 8,
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
            f"cute cartoon character for Indonesian nursery rhyme {cfg['title_english']}, "
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
    local_title = cfg.get("title_local", cfg["title_english"])
    t_en = cfg["title_english"]

    titles = {
        "id":  f'{local_title} | Lagu Anak Indonesia | Happy Bear Kids Indonesia',
        "en":  f'{t_en} | Indonesian Nursery Rhyme | Happy Bear Kids',
        "ar":  f'{cfg["title_arabic"]} | أغنية إندونيسية للأطفال | هابي بير كيدز',
    }
    descs = {
        "id": (
            f'🎵 Nikmati lagu anak {local_title} yang menyenangkan!\n\n'
            f'Lagu anak-anak Indonesia yang klasik ini disajikan dengan cara yang '
            f'menyenangkan dan interaktif. Dirancang khusus untuk anak-anak usia 0 hingga '
            f'5 tahun untuk membantu mereka belajar melalui musik dan animasi yang menarik.\n\n'
            f'✨ Yang akan dipelajari si kecil:\n'
            f'• Lirik lagu {local_title}\n'
            f'• Kosakata baru melalui lagu\n'
            f'• Ritme dan melodi yang menyenangkan\n'
            f'• Nilai-nilai positif melalui seni\n\n'
            f'🌟 Fitur video:\n'
            f'• Animasi berwarna-warni yang menarik untuk anak\n'
            f'• Suara yang jelas dan pengucapan yang tepat\n'
            f'• Musik latar yang tenang dan sesuai anak\n'
            f'• Bagus untuk pembelajaran dini dan perkembangan bahasa\n'
            f'• Konten aman dan bebas iklan untuk bayi dan balita\n\n'
            f'👶 Cocok untuk:\n'
            f'• Bayi (0–12 bulan) — stimulasi audio dan visual\n'
            f'• Balita (1–3 tahun) — belajar lagu anak\n'
            f'• Pra-sekolah (3–5 tahun) — pengembangan bahasa\n\n'
            f'🔔 Subscribe ke Happy Bear Kids Indonesia → @happybearkidsin\n'
            f'Video edukatif baru setiap minggu!\n\n'
            f'🎵 Musik Latar: Kevin MacLeod (incompetech.com)\n'
            f'Berlisensi Creative Commons Attribution 4.0\n'
            f'http://creativecommons.org/licenses/by/4.0/\n\n'
            f'#LaguAnak #HappyBearKids #LaguAnakIndonesia #{local_title.replace(" ", "")} '
            f'#BelajarAnak #BahasaIndonesia #BalitaBelajar\n\n'
            f'© Happy Bear Kids Indonesia 2026'
        ),
        "en": (
            f'🎵 Enjoy the classic Indonesian nursery rhyme — {t_en}!\n\n'
            f'This beloved Indonesian children\'s song is presented in a fun and interactive way. '
            f'Designed for children aged 0 to 5 to help them learn through music and engaging animation.\n\n'
            f'✨ What your child will learn:\n'
            f'• The lyrics of {local_title}\n'
            f'• New vocabulary through songs\n'
            f'• Fun rhythms and melodies\n'
            f'• Positive values through art and music\n\n'
            f'🌟 Video features:\n'
            f'• Colorful animated characters kids will love\n'
            f'• Clear pronunciation and proper diction\n'
            f'• Calm, child-appropriate background music\n'
            f'• Great for early learning and language development\n'
            f'• Safe, ad-free content for babies and toddlers\n\n'
            f'👶 Perfect for:\n'
            f'• Babies (0–12 months) — auditory and visual stimulation\n'
            f'• Toddlers (1–3 years) — learning nursery rhymes\n'
            f'• Preschoolers (3–5 years) — language development\n\n'
            f'🔔 Subscribe to Happy Bear Kids → @HappyBearKids1\n'
            f'New educational videos every week!\n\n'
            f'🎵 Background Music: Kevin MacLeod (incompetech.com)\n'
            f'Licensed under Creative Commons Attribution 4.0\n'
            f'http://creativecommons.org/licenses/by/4.0/\n\n'
            f'#IndonesianNurseryRhyme #HappyBearKids #KidsSongs #BabySongs '
            f'#ToddlerLearning #ChildrenSongs #NurseryRhymes\n\n'
            f'© Happy Bear Kids 2026'
        ),
        "ar": (
            f'🎵 استمتع بالأغنية الإندونيسية الكلاسيكية للأطفال — {t_en}!\n\n'
            f'هذه الأغنية الإندونيسية الشهيرة للأطفال مقدمة بطريقة ممتعة وتفاعلية. '
            f'مصممة للأطفال من عمر 0 إلى 5 سنوات للتعلم من خلال الموسيقى.\n\n'
            f'✨ ما يتعلمه طفلك:\n'
            f'• كلمات أغنية {local_title}\n'
            f'• مفردات جديدة من خلال الأغاني\n'
            f'• إيقاع وألحان ممتعة\n'
            f'• قيم إيجابية من خلال الفن والموسيقى\n\n'
            f'🔔 اشتركوا في هابي بير كيدز → @HappyBearKids1\n\n'
            f'🎵 الموسيقى: Kevin MacLeod — Creative Commons BY 4.0\n\n'
            f'#أغاني_أطفال #هابي_بير_كيدز #أغنية_إندونيسية #تعليم_أطفال\n\n'
            f'© هابي بير كيدز 2026'
        ),
    }

    meta = {
        "title":       titles.get(lang, titles["en"]),
        "description": descs.get(lang, descs["en"]),
        "tags":        ["lagu anak", "nursery rhyme", "indonesian kids songs",
                        local_title.lower(), "baby songs", "toddler", "happy bear kids",
                        "children music", "educational", "preschool",
                        "lagu anak indonesia", "belajar anak"],
        "video_type":  "nursery_id",
        "language":    lang,
        "is_short":    False,
        "status":      "public",
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
