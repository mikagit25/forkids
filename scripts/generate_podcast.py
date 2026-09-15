#!/usr/bin/env python3
"""
generate_podcast.py — Classical Night Relax Podcast Generator

Produces a 10–15 minute narrated video podcast episode about a classical composer.

Pipeline:
  1. Generate narration script via Groq (llama-3.3-70b-versatile)
  2. Convert to speech via edge-tts (en-GB-RyanNeural)
  3. Generate 4 FLUX.1.1-pro images via Together.ai
  4. Assemble Ken Burns video from images
  5. Mix narration + background Musopen track at -22 dB
  6. Combine video + audio → final MP4
  7. Save thumbnail (first FLUX image)
  8. Write meta YAML for publish_queue.py

Usage:
  python3 scripts/generate_podcast.py \\
      --composer "Frédéric Chopin" \\
      --topic "The Nocturnes — Music Written for the Night" \\
      --bg-track "Nocturne No. 2"   # optional substring to match in licenses.yaml

  python3 scripts/generate_podcast.py --list   # print suggested episode schedule
"""
import argparse, asyncio, base64, json, logging, re, subprocess, sys, time, urllib.request
from datetime import date
from pathlib import Path

import yaml

ROOT          = Path(__file__).resolve().parent.parent
QUEUE_DIR     = ROOT / "output" / "queue_id"
MUSIC_DIR     = ROOT / "assets" / "music" / "classical" / "Music"
LICENSES_YAML = ROOT / "assets" / "music" / "classical" / "licenses.yaml"
TOGETHER_KEY  = ROOT / "credentials" / "together_api_key.txt"
LOGS_DIR      = ROOT / "logs"
WORK_DIR      = ROOT / "output" / "_podcast_work"

VOICE         = "en-GB-RyanNeural"
FLUX_MODEL    = "black-forest-labs/FLUX.1.1-pro"
FLUX_W, FLUX_H = 1344, 768
N_IMAGES      = 4
CLIP_DUR      = 35        # seconds per Ken Burns clip
XFADE_DUR     = 2.0
FADE_SECS     = 1.5

GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"
_GROQ_KEY_FILE = Path(__file__).resolve().parent.parent / "credentials" / "groq_api_keys.txt"
GROQ_KEYS  = [k.strip() for k in _GROQ_KEY_FILE.read_text().splitlines() if k.strip()] if _GROQ_KEY_FILE.exists() else []
_groq_idx = 0

KB_MOTIONS = [
    "zoompan=z='min(zoom+0.0008,1.3)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
    "zoompan=z='if(lte(zoom,1),1.3,max(1,zoom-0.0008))':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
    "zoompan=z='min(zoom+0.0006,1.25)':x='(iw/zoom/2)+((iw-iw/zoom)*on/(25*{d}))':y='ih/2-(ih/zoom/2)'",
    "zoompan=z='1.2':x='(iw-iw/zoom)*on/(25*{d})':y='(ih-ih/zoom)*on/(25*{d})'",
]

SUGGESTED_EPISODES = [
    ("Frédéric Chopin",         "The Nocturnes — Music Written for the Night"),
    ("Johann Sebastian Bach",   "The Goldberg Variations — Music That Cured Insomnia"),
    ("Claude Debussy",          "Clair de Lune — Moonlight Captured in Sound"),
    ("Ludwig van Beethoven",    "The Moonlight Sonata — A Mystery Solved"),
    ("Erik Satie",              "Gymnopédies — The Art of Doing Nothing"),
    ("Franz Schubert",          "Winterreise — A Journey Through the Cold"),
    ("Wolfgang Amadeus Mozart", "Eine Kleine Nachtmusik — The Little Night Music"),
    ("Johannes Brahms",         "The Lullabies — Tenderness in Four-Four Time"),
    ("Pyotr Ilyich Tchaikovsky","Swan Lake — The Magic of Ballet"),
    ("Antonio Vivaldi",         "The Four Seasons — Nature in Music"),
    ("George Frideric Handel",  "Water Music — A Party on the Thames"),
    ("Franz Liszt",             "The Piano Transcendentalist"),
]

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


# ── Groq ──────────────────────────────────────────────────────────────────────

def _next_groq_key() -> str:
    global _groq_idx
    key = GROQ_KEYS[_groq_idx % len(GROQ_KEYS)]
    _groq_idx += 1
    return key


def _groq(system: str, user: str, max_tokens: int = 3000, temp: float = 0.7) -> str:
    payload = json.dumps({
        "model": GROQ_MODEL,
        "messages": [{"role": "system", "content": system},
                     {"role": "user",   "content": user}],
        "temperature": temp,
        "max_tokens": max_tokens,
    }).encode()
    for attempt in range(len(GROQ_KEYS) * 2):
        key = _next_groq_key()
        req = urllib.request.Request(
            GROQ_URL, data=payload,
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": "application/json",
                     "User-Agent": "python-requests/2.31.0"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                msg = json.loads(resp.read())["choices"][0]["message"]
                content = (msg.get("content") or "").strip()
                if not content:  # reasoning models put text in 'reasoning' field
                    content = (msg.get("reasoning") or "").strip()
                return content
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="ignore")[:200]
            if e.code == 429:
                time.sleep(65 if attempt % len(GROQ_KEYS) == 0 else 3)
            else:
                raise RuntimeError(f"Groq {e.code}: {body}")
    raise RuntimeError("All Groq keys exhausted")


# ── Script generation ─────────────────────────────────────────────────────────

def generate_script(composer: str, topic: str) -> tuple[str, str, str]:
    """Returns (narration_text, youtube_title, flux_image_prompt)."""
    log.info(f"Generating script: {composer} — {topic}")

    system = (
        "You are a writer for a calm, intelligent classical music podcast called "
        "'Classical Night Relax'. Episodes are listened to in the evening before sleep. "
        "Your tone is warm, contemplative, and unhurried — like a knowledgeable friend "
        "sharing stories over a late-night drink. No jargon, no academia. "
        "Write pure narration only — no stage directions, no [MUSIC] markers, no headers. "
        "Always write exactly the requested number of words — do not stop early."
    )

    # 3-part structure: each ~650 words → total ~1950 words → ~12-13 min TTS
    user1 = f"""Write PART 1 of 3 of a podcast narration. Exactly 650 words. Topic: {composer} — {topic}.
Cover: (1) Opening hook — a vivid scene or intriguing fact; (2) composer's early life, background, formative years.
Begin immediately. No headers. Continue writing until you reach exactly 650 words."""

    user2 = f"""Write PART 2 of 3 of a podcast narration. Exactly 650 words. Topic: {composer} — {topic}.
Cover: (1) Career peak, key relationships, personal struggles; (2) how life shaped the music.
No headers. Pure narration. Continue writing until you reach exactly 650 words."""

    user3 = f"""Write PART 3 of 3 of a podcast narration. Exactly 650 words. Topic: {composer} — {topic}.
Cover: (1) The music itself — what makes it special, how it sounds; (2) why it belongs to evening and rest; (3) warm closing invitation to let the music carry the listener to sleep.
No headers. This is the episode finale. Continue writing until you reach exactly 650 words."""

    log.info("  Generating script part 1…")
    part1 = _groq(system, user1, max_tokens=1050, temp=0.75)
    log.info("  Generating script part 2…")
    part2 = _groq(system, user2, max_tokens=1050, temp=0.75)
    log.info("  Generating script part 3…")
    part3 = _groq(system, user3, max_tokens=1050, temp=0.75)
    narration = part1.strip() + "\n\n" + part2.strip() + "\n\n" + part3.strip()

    # YouTube title (with fallback)
    title_prompt = (
        f"Write a YouTube title for a podcast episode about {composer} — {topic}. "
        f"Format example: \"Chopin's Nocturnes | Classical Night Relax Podcast\". "
        "Max 70 characters. Calm, elegant. Return only the title text, nothing else."
    )
    title = _groq("You write concise YouTube titles.", title_prompt, max_tokens=80, temp=0.4).strip('"\'')
    if not title or len(title) < 10:
        last_name = composer.split()[-1]
        title = f"{last_name}: {topic[:40]} | Classical Night Relax Podcast"

    # FLUX image prompt
    img_prompt_req = (
        f"Write a FLUX AI image generation prompt for a podcast about {composer}. "
        "Style: dramatic oil painting or cinematic portrait photography. "
        "Show the composer at work, or their era's concert hall, or an evocative night scene. "
        "Mood: candlelit, contemplative, 19th century atmosphere. No text, no letters, no words. "
        "Return only the prompt text, max 80 words."
    )
    flux_prompt = _groq("You write image generation prompts.", img_prompt_req, max_tokens=150, temp=0.5)

    return narration, title, flux_prompt


def generate_description(composer: str, topic: str, narration: str, bg_track_name: str) -> str:
    system = "You write YouTube video descriptions for a classical music podcast."
    user = (
        f"Write a YouTube description (200-250 words) for a Classical Night Relax Podcast episode.\n"
        f"Composer: {composer}\nTopic: {topic}\n"
        f"Opening of narration: {narration[:300]}...\n\n"
        "Include: what the episode covers, why to listen at night, a line about the channel. "
        "End with these hashtags on a new line: #ClassicalMusic #ClassicalNightRelax #Podcast "
        "#SleepMusic #RelaxingMusic #ClassicalPodcast"
    )
    return _groq(system, user, max_tokens=400, temp=0.5)


# ── Background music selection ─────────────────────────────────────────────────

def pick_background_track(composer: str, bg_hint: str = "") -> tuple[Path, str] | None:
    """Return (mp3_path, track_name) from Musopen library, preferring composer match."""
    if not LICENSES_YAML.exists():
        return None
    data = yaml.safe_load(LICENSES_YAML.read_text())
    tracks = [t for t in data.get("recordings", [])
              if t.get("license") in ("pd", "cc0") and t.get("license") != "rejected"]

    def score(t):
        name = (t.get("composer", "") + " " + t.get("piece", "")).lower()
        s = 0
        if composer.split()[-1].lower() in name:  # last name match
            s += 10
        if bg_hint and bg_hint.lower() in name:
            s += 5
        return s

    tracks.sort(key=score, reverse=True)
    for t in tracks:
        fp = MUSIC_DIR / t.get("file", "").replace("Music/", "")
        if fp.exists():
            return fp, t.get("piece", fp.stem)
    return None


# ── TTS ───────────────────────────────────────────────────────────────────────

async def _tts_async(text: str, out: Path):
    import edge_tts
    communicate = edge_tts.Communicate(text, VOICE, rate="-5%", pitch="-2Hz")
    await communicate.save(str(out))


def tts(text: str, out: Path):
    log.info(f"TTS → {out.name}")
    asyncio.run(_tts_async(text, out))


# ── FLUX images ───────────────────────────────────────────────────────────────

LIGHTING = ["candlelit", "moonlit", "golden hour lamp light", "soft dawn light"]


def generate_images(flux_prompt: str, imgs_dir: Path, force: bool = False) -> list[Path]:
    if not TOGETHER_KEY.exists():
        log.error("No Together.ai API key — cannot generate images")
        return []
    api_key = TOGETHER_KEY.read_text().strip()
    images = []
    for i in range(N_IMAGES):
        out = imgs_dir / f"img_{i:02d}.jpg"
        if out.exists() and not force:
            log.info(f"  Image cached: {out.name}")
            images.append(out)
            continue
        prompt = f"{flux_prompt}, {LIGHTING[i % len(LIGHTING)]} atmosphere"
        log.info(f"  FLUX image {i+1}/{N_IMAGES}…")
        try:
            import requests as req
            resp = req.post(
                "https://api.together.xyz/v1/images/generations",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": FLUX_MODEL, "prompt": prompt,
                      "width": FLUX_W, "height": FLUX_H,
                      "steps": 4, "n": 1, "response_format": "b64_json"},
                timeout=90,
            )
            resp.raise_for_status()
            out.write_bytes(base64.b64decode(resp.json()["data"][0]["b64_json"]))
            images.append(out)
            time.sleep(2)
        except Exception as e:
            log.warning(f"  Image {i+1} failed: {e}")
    return images


# ── Ken Burns video ───────────────────────────────────────────────────────────

def _kb_clip(img: Path, out: Path, motion_template: str) -> bool:
    fps = 25
    motion = motion_template.replace("{d}", str(int(CLIP_DUR * fps)))
    vf = f"{motion}:d={int(CLIP_DUR * fps)}:fps={fps}:s={FLUX_W}x{FLUX_H}"
    r = subprocess.run(
        ["ffmpeg", "-y", "-loop", "1", "-i", str(img),
         "-t", str(CLIP_DUR), "-vf", vf,
         "-c:v", "libx264", "-preset", "fast", "-crf", "22",
         "-pix_fmt", "yuv420p", "-an", str(out)],
        capture_output=True, text=True, timeout=300,
    )
    return r.returncode == 0 and out.exists()


def build_kenburns_video(images: list[Path], clips_dir: Path, out: Path) -> bool:
    clips = []
    for i, img in enumerate(images):
        clip = clips_dir / f"clip_{i:02d}.mp4"
        if clip.exists():
            clips.append(clip)
            continue
        motion = KB_MOTIONS[i % len(KB_MOTIONS)]
        log.info(f"  Ken Burns clip {i+1}/{len(images)}")
        if _kb_clip(img, clip, motion):
            clips.append(clip)
        else:
            log.warning(f"  Clip {i+1} failed")

    if not clips:
        return False

    n = len(clips)
    inputs = []
    for p in clips:
        inputs += ["-i", str(p)]

    step  = CLIP_DUR - XFADE_DUR
    total = n * CLIP_DUR - (n - 1) * XFADE_DUR

    if n == 1:
        import shutil; shutil.copy(clips[0], out); return True

    fc = (f"[0:v]fade=t=in:st=0:d={FADE_SECS}[f0];"
          f"[f0][1:v]xfade=transition=fade:duration={XFADE_DUR}:offset={step}[v01]")
    for i in range(2, n):
        prev = f"[v{i-1:02d}]"
        nxt  = f"[v{i:02d}]" if i < n - 1 else "[vpre]"
        fc  += f";{prev}[{i}:v]xfade=transition=fade:duration={XFADE_DUR}:offset={i*step}{nxt}"
    last = "[vpre]" if n > 2 else "[v01]"
    fc  += f";{last}fade=t=out:st={total-FADE_SECS}:d={FADE_SECS}[vout]"

    log.info(f"  Concatenating {n} clips → {out.name}")
    r = subprocess.run(
        ["ffmpeg", "-y"] + inputs + [
            "-filter_complex", fc, "-map", "[vout]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-an", str(out)],
        capture_output=True, text=True, timeout=600,
    )
    if r.returncode != 0:
        log.error(f"  concat failed: {r.stderr[-300:]}")
        return False
    return True


# ── Audio mix ─────────────────────────────────────────────────────────────────

def mix_audio(narration: Path, bg_track: Path | None, total_dur: float, out: Path) -> bool:
    """Mix TTS narration with optional background music at -22 dB."""
    if bg_track is None:
        import shutil; shutil.copy(narration, out); return True

    log.info(f"  Mixing narration + {bg_track.name}")
    # Loop background music to cover full duration, then mix under narration
    r = subprocess.run(
        ["ffmpeg", "-y",
         "-i", str(narration),
         "-stream_loop", "-1", "-i", str(bg_track),
         "-filter_complex",
         f"[1:a]volume=0.12,atrim=0:{total_dur:.1f},asetpts=PTS-STARTPTS[bg];"
         f"[0:a][bg]amix=inputs=2:duration=first:dropout_transition=3[out]",
         "-map", "[out]",
         "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
         str(out)],
        capture_output=True, text=True, timeout=300,
    )
    if r.returncode != 0:
        log.error(f"  audio mix failed: {r.stderr[-200:]}")
        return False
    return True


# ── Final video assembly ──────────────────────────────────────────────────────

def assemble_video(video: Path, audio: Path, out: Path) -> bool:
    """Loop Ken Burns video to match audio duration, then combine."""
    log.info(f"  Assembling final video → {out.name}")

    # Get audio duration
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(audio)],
        capture_output=True, text=True, timeout=30,
    )
    if probe.returncode != 0 or not probe.stdout.strip():
        log.error("Could not probe audio duration")
        return False
    audio_dur = float(probe.stdout.strip())

    r = subprocess.run(
        ["ffmpeg", "-y",
         "-stream_loop", "-1", "-i", str(video),
         "-i", str(audio),
         "-map", "0:v:0", "-map", "1:a:0",
         "-t", str(audio_dur),
         "-c:v", "libx264", "-preset", "fast", "-crf", "20",
         "-pix_fmt", "yuv420p",
         "-c:a", "copy",
         "-movflags", "+faststart",
         str(out)],
        capture_output=True, text=True, timeout=1200,
    )
    if r.returncode != 0:
        log.error(f"  assemble failed: {r.stderr[-300:]}")
        return False
    return True


# ── Meta YAML ─────────────────────────────────────────────────────────────────

TAGS_BASE = [
    "classical music", "classical music podcast", "music podcast",
    "sleep music", "relaxing music", "classical night relax",
    "evening music", "calm music", "background music", "study music",
    "focus music", "bedtime music", "ambient classical",
]


def write_meta(out_path: Path, title: str, description: str,
               composer: str, bg_track_name: str):
    tags = TAGS_BASE + [composer.split()[-1].lower(),
                        composer.lower(), "podcast", "classical podcast"]
    meta = {
        "title":        title,
        "description":  description,
        "tags":         tags[:40],
        "video_type":   "podcast",
        "language":     "en",
        "is_short":     False,
        "status":       "public",
        "made_for_kids": False,
        "ai_generated": True,
        "podcast_episode": True,
        "playlist_id":  "PLY2DzDbU_Vlg",
        "composer":     composer,
    }
    if bg_track_name:
        meta["background_music"] = bg_track_name
        meta["background_music_source"] = "Musopen (Public Domain)"
    out_path.write_text(yaml.dump(meta, allow_unicode=True, sort_keys=False))
    log.info(f"  Meta → {out_path.name}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--composer",    help="Composer full name")
    parser.add_argument("--topic",       help="Episode topic / piece name")
    parser.add_argument("--bg-track",    default="", help="Substring to match background track")
    parser.add_argument("--force",       action="store_true", help="Re-generate cached assets")
    parser.add_argument("--list",        action="store_true", help="Print suggested episode list")
    parser.add_argument("--script-file", help="Use pre-written narration from this file (skips Groq script gen)")
    args = parser.parse_args()

    if args.list:
        print("\nSuggested podcast episodes (1-2 per week):\n")
        for i, (comp, topic) in enumerate(SUGGESTED_EPISODES, 1):
            print(f"  {i:2d}. {comp}: {topic}")
        print()
        print("Run example:")
        print('  python3 scripts/generate_podcast.py \\')
        print('      --composer "Frédéric Chopin" \\')
        print('      --topic "The Nocturnes — Music Written for the Night"')
        return

    if not args.composer or not args.topic:
        parser.print_help()
        sys.exit(1)

    composer = args.composer
    topic    = args.topic
    today    = date.today().strftime("%Y%m%d")
    slug     = re.sub(r"[^a-z0-9]+", "_", composer.split()[-1].lower())
    ep_id    = f"podcast_{slug}_{today}"

    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    work = WORK_DIR / ep_id
    work.mkdir(parents=True, exist_ok=True)
    imgs_dir  = work / "images"
    clips_dir = work / "clips"
    imgs_dir.mkdir(exist_ok=True)
    clips_dir.mkdir(exist_ok=True)

    out_mp4   = QUEUE_DIR / f"{ep_id}.mp4"
    out_meta  = QUEUE_DIR / f"meta_{ep_id}.yaml"
    out_thumb = QUEUE_DIR / f"thumb_{ep_id}.png"

    if out_mp4.exists() and not args.force:
        log.info(f"Already exists: {out_mp4.name} — use --force to regenerate")
        return

    # ── 1. Script ──
    if args.script_file:
        narration = Path(args.script_file).read_text().strip()
        last_name = composer.split()[-1]
        yt_title  = f"{last_name}: {topic} | Classical Night Relax Podcast"
        flux_prompt = (
            f"A contemplative 19th century oil painting scene evoking {composer}'s music. "
            "Candlelit room, period piano, dramatic chiaroscuro lighting, romantic era atmosphere. "
            "No text, no letters, no words."
        )
        (work / "narration.txt").write_text(narration)
        log.info(f"Script: {len(narration.split())} words (from file)")
        log.info(f"Title: {yt_title}")
    else:
        narration, yt_title, flux_prompt = generate_script(composer, topic)
        (work / "narration.txt").write_text(narration)
        log.info(f"Script: {len(narration.split())} words")
        log.info(f"Title: {yt_title}")

    # ── 2. TTS ──
    tts_mp3 = work / "narration.mp3"
    if not tts_mp3.exists() or args.force:
        tts(narration, tts_mp3)
    else:
        log.info(f"TTS cached: {tts_mp3.name}")

    # Get TTS duration
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(tts_mp3)],
        capture_output=True, text=True, timeout=30,
    )
    tts_dur = float(probe.stdout.strip()) if probe.returncode == 0 else 600.0
    log.info(f"TTS duration: {tts_dur/60:.1f} min")

    # ── 3. Background music ──
    bg_result = pick_background_track(composer, args.bg_track)
    bg_path, bg_name = bg_result if bg_result else (None, "")
    if bg_path:
        log.info(f"Background track: {bg_name}")
    else:
        log.warning("No background track found — narration only")

    # ── 4. FLUX images ──
    images = generate_images(flux_prompt, imgs_dir, force=args.force)
    if not images:
        log.error("No images generated — aborting")
        sys.exit(1)

    # Save thumbnail (best quality = first image)
    import shutil
    shutil.copy(images[0], out_thumb)
    log.info(f"Thumbnail → {out_thumb.name}")

    # ── 5. Ken Burns video ──
    kb_video = work / "kenburns.mp4"
    if not kb_video.exists() or args.force:
        if not build_kenburns_video(images, clips_dir, kb_video):
            log.error("Ken Burns video failed — aborting")
            sys.exit(1)
    else:
        log.info(f"Ken Burns cached: {kb_video.name}")

    # ── 6. Audio mix ──
    mixed_audio = work / "audio_mixed.aac"
    if not mixed_audio.exists() or args.force:
        if not mix_audio(tts_mp3, bg_path, tts_dur, mixed_audio):
            log.warning("Audio mix failed — using narration only")
            shutil.copy(tts_mp3, mixed_audio)
    else:
        log.info(f"Audio cached: {mixed_audio.name}")

    # ── 7. Final video ──
    if not assemble_video(kb_video, mixed_audio, out_mp4):
        log.error("Final assembly failed")
        sys.exit(1)
    log.info(f"✓ Video → {out_mp4.name} ({out_mp4.stat().st_size/1024**2:.0f} MB)")

    # ── 8. Description + meta ──
    description = generate_description(composer, topic, narration, bg_name)
    write_meta(out_meta, yt_title, description, composer, bg_name)

    print(f"\n{'='*60}")
    print(f"✓ Podcast episode ready:")
    print(f"  Video:     {out_mp4.name}")
    print(f"  Meta:      {out_meta.name}")
    print(f"  Thumbnail: {out_thumb.name}")
    print(f"  Duration:  {tts_dur/60:.1f} min")
    print(f"  Title:     {yt_title}")
    print(f"\nPublish with:")
    print(f"  python3 scripts/publish_queue.py --queue id --type long --dry-run")


if __name__ == "__main__":
    main()
