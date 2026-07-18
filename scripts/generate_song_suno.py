#!/usr/bin/env python3
"""
Generate audio via Suno (browser session) and build a looped video.

Usage:
  python3 scripts/generate_song_suno.py --song goodnight_little_bear
  python3 scripts/generate_song_suno.py --song bubble_pop_song
  python3 scripts/generate_song_suno.py --song goodnight_little_bear --dry-run
  python3 scripts/generate_song_suno.py --song goodnight_little_bear --use-existing assets/audio/suno/goodnight_little_bear_v1.mp3
"""
import argparse, logging, os, re, subprocess, sys, time, urllib.request
from datetime import datetime
from pathlib import Path

import requests, yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")
log = logging.getLogger(__name__)

ROOT      = Path(__file__).resolve().parent.parent
CFG_DIR   = ROOT / "config" / "suno_songs"
AUDIO_DIR = ROOT / "assets" / "audio" / "suno"
DATE_STR  = datetime.now().strftime("%Y%m%d")

SUNO_API_BASE = "https://studio-api.suno.ai"

# ---------------------------------------------------------------------------
# Suno API client
# ---------------------------------------------------------------------------

def load_session() -> str:
    p = ROOT / "credentials" / "suno_session.txt"
    if not p.exists() or not p.read_text().strip():
        raise RuntimeError(
            "credentials/suno_session.txt is empty.\n"
            "Instructions:\n"
            "  1. Go to suno.com (logged in with paid account)\n"
            "  2. F12 → Network → reload page\n"
            "  3. Find any request to studio-api.suno.ai\n"
            "  4. Copy the 'Cookie' request header value\n"
            "  5. Save to credentials/suno_session.txt"
        )
    return p.read_text().strip()


def suno_generate(lyrics: str, style: str, title: str, session_cookie: str) -> list[str]:
    """Submit generation job to Suno. Returns list of clip IDs."""
    headers = {
        "Cookie": session_cookie,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }
    payload = {
        "prompt": lyrics,
        "tags": style,
        "title": title,
        "make_instrumental": False,
        "mv": "chirp-v3-5",
    }
    resp = requests.post(f"{SUNO_API_BASE}/api/generate/v2/", json=payload, headers=headers, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"Suno generate failed {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    clips = data.get("clips", [])
    ids = [c["id"] for c in clips]
    log.info(f"  Submitted: {len(ids)} clips → {ids}")
    return ids


def suno_wait_for_clips(clip_ids: list[str], session_cookie: str, timeout_sec: int = 600) -> list[dict]:
    """Poll Suno feed until all clips are complete."""
    headers = {
        "Cookie": session_cookie,
        "User-Agent": "Mozilla/5.0",
    }
    ids_str = ",".join(clip_ids)
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        resp = requests.get(f"{SUNO_API_BASE}/api/feed/?ids={ids_str}", headers=headers, timeout=30)
        if resp.status_code != 200:
            log.warning(f"  Feed poll {resp.status_code}, retrying...")
            time.sleep(10)
            continue
        clips = resp.json()
        statuses = {c["id"]: c.get("status", "unknown") for c in clips}
        done = all(s in ("complete", "streaming") for s in statuses.values())
        log.info(f"  Clip statuses: {statuses}")
        if done:
            return clips
        time.sleep(15)
    raise TimeoutError(f"Suno clips not ready after {timeout_sec}s: {statuses}")


def download_clip(clip: dict, out_path: Path):
    """Download audio_url from a Suno clip dict."""
    url = clip.get("audio_url") or clip.get("stream_audio_url")
    if not url:
        raise RuntimeError(f"No audio_url in clip {clip.get('id')}: {list(clip.keys())}")
    log.info(f"  Downloading {out_path.name} from Suno...")
    urllib.request.urlretrieve(url, out_path)
    size_mb = out_path.stat().st_size / 1e6
    log.info(f"  ✓ {out_path.name} ({size_mb:.1f}MB)")


# ---------------------------------------------------------------------------
# Audio / video assembly (mirrors generate_sleep_classical.py logic)
# ---------------------------------------------------------------------------

def get_audio_duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True
    )
    return float(r.stdout.strip())


def build_looped_audio(clips: list[Path], target_sec: int, out_path: Path):
    """Concatenate clips in order, repeat until target_sec, trim."""
    concat_list = out_path.parent / "_concat_list.txt"
    total = sum(get_audio_duration(c) for c in clips)
    repeats = max(1, -(-int(target_sec) // int(total)))  # ceil division
    log.info(f"  Audio {total/60:.1f}min < {target_sec/3600:.0f}h target — repeating ×{repeats}")

    lines = []
    for _ in range(repeats):
        for c in clips:
            lines.append(f"file '{c.resolve()}'")
    concat_list.write_text("\n".join(lines))

    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-t", str(target_sec), "-acodec", "libmp3lame", "-b:a", "192k", str(out_path)
    ], check=True, capture_output=True)
    concat_list.unlink(missing_ok=True)
    log.info(f"  ✓ Audio: {out_path.name} ({out_path.stat().st_size/1e6:.1f}MB)")


def assemble_video(loop_mp4: Path, audio_mp3: Path, duration_sec: int,
                   out_mp4: Path, preset: str = "medium"):
    log.info(f"  Assembling {duration_sec//3600}h video ({preset=}) → {out_mp4.name}…")
    subprocess.run([
        "ffmpeg", "-y",
        "-stream_loop", "-1", "-i", str(loop_mp4),
        "-i", str(audio_mp3),
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-t", str(duration_sec),
        "-movflags", "+faststart",
        "-preset", preset,
        str(out_mp4)
    ], check=True, capture_output=True)
    size_gb = out_mp4.stat().st_size / 1e9
    log.info(f"  ✓ {out_mp4.name} ({size_gb:.2f}GB)")


def render_loop(visual_theme: str, loop_sec: int) -> Path:
    """Render or reuse existing Remotion loop for given theme."""
    loop_path = ROOT / "output" / "loops" / f"loop_{visual_theme}_ph00.mp4"
    if loop_path.exists():
        log.info(f"  Reusing loop: {loop_path.name}")
        return loop_path
    log.info(f"  Rendering loop: {visual_theme} ({loop_sec}s)…")
    comp_id = visual_theme.replace("_", "-") + "-loop"
    subprocess.run([
        "npx", "remotion", "render",
        "--composition", comp_id,
        "--output", str(loop_path),
        "--frames", f"0-{loop_sec * 30 - 1}",
    ], cwd=str(ROOT / "remotion"), check=True, capture_output=True)
    return loop_path


def generate_thumbnail(song_id: str, title: str, visual_theme: str, out_path: Path):
    theme_prompts = {
        "night_bear":  "cute teddy bear sleeping peacefully under starry night sky, moon glowing, soft purple and blue tones, dreamlike, children's illustration style",
        "moon_clouds": "soft moon and dreamy clouds, peaceful night scene, glowing blue light",
        "warm_waves":  "warm ocean waves at sunset, golden light, peaceful and serene",
        "rain_window": "cozy rainy window, warm light inside, raindrops on glass, peaceful",
    }
    prompt = theme_prompts.get(visual_theme, f"peaceful {visual_theme} scene for kids lullaby")

    api_key_path = ROOT / "credentials" / "together_api_key.txt"
    if not api_key_path.exists():
        log.warning("  No Together API key — skipping thumbnail")
        return

    import urllib.request, json
    api_key = api_key_path.read_text().strip()
    payload = json.dumps({
        "model": "black-forest-labs/FLUX.1-schnell-Free",
        "prompt": prompt,
        "width": 1344, "height": 768,
        "steps": 4, "n": 1,
        "response_format": "url"
    }).encode()
    req = urllib.request.Request(
        "https://api.together.xyz/v1/images/generations",
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        url = json.loads(resp.read())["data"][0]["url"]
    urllib.request.urlretrieve(url, out_path)
    log.info(f"  Thumb → {out_path.name}")


def write_meta(song_cfg: dict, duration_h: int, video_path: Path):
    base = video_path.stem
    meta_path = video_path.parent / f"meta_{base}.yaml"
    title = song_cfg["title_en"].replace("{duration}", f"{duration_h} Hour{'s' if duration_h > 1 else ''}")
    meta = {
        "title": title,
        "description": (
            f"{title}\n\n"
            f"A gentle lullaby to help your little one drift off to sleep. "
            f"Safe, calm content designed for babies and toddlers (0-3 years).\n\n"
            f"♪ Original song by Happy Bear Kids\n"
            f"AI-assisted music production\n\n"
            f"Subscribe → @HappyBearKids1\n\n"
            f"#lullaby #babysleep #kidsmusic #happybearkids #bedtimesongs #toddlersong"
        ),
        "tags": ["lullaby", "baby sleep", "goodnight song", "kids music", "bedtime",
                 "toddler", "happy bear kids", "sleep music for babies", "gentle lullaby"],
        "video_type": song_cfg["video_type"],
        "language": song_cfg.get("language", "en"),
        "is_short": False,
        "status": "public",
        "made_for_kids": song_cfg.get("made_for_kids", True),
        "ai_generated": True,
    }
    with open(meta_path, "w") as f:
        yaml.dump(meta, f, allow_unicode=True, default_flow_style=False)
    log.info(f"  Meta → {meta_path.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--song", required=True, help="Song ID (matches config/suno_songs/<id>.yaml)")
    ap.add_argument("--dry-run", action="store_true", help="Skip Suno API calls, log only")
    ap.add_argument("--use-existing", help="Path to existing MP3 — skip Suno generation")
    ap.add_argument("--durations", nargs="+", type=int, help="Override durations in hours")
    args = ap.parse_args()

    cfg_path = CFG_DIR / f"{args.song}.yaml"
    if not cfg_path.exists():
        sys.exit(f"Config not found: {cfg_path}")
    cfg = yaml.safe_load(cfg_path.read_text())

    song_id   = cfg["id"]
    title     = cfg["title_en"]
    lyrics    = cfg["lyrics"]
    style     = cfg["suno"]["style"]
    theme     = cfg["visual_theme"]
    loop_sec  = cfg["loop_duration_sec"]
    durations = args.durations or cfg["durations_hours"]
    queue_dir = ROOT / cfg["queue"]
    queue_dir.mkdir(parents=True, exist_ok=True)

    log.info(f"=== Song: {song_id} | theme: {theme} ===")

    # 1. Get Suno audio clips
    clip_files: list[Path] = []

    if args.use_existing:
        clip_files = [Path(args.use_existing)]
        log.info(f"  Using existing audio: {clip_files[0]}")
    elif args.dry_run:
        log.info("  [DRY RUN] Would call Suno API to generate audio")
        clip_files = []
    else:
        session = load_session()
        log.info("  Submitting to Suno API…")
        clip_ids = suno_generate(lyrics, style, title, session)
        clips = suno_wait_for_clips(clip_ids, session)

        for i, clip in enumerate(clips):
            out = AUDIO_DIR / f"{song_id}_clip{i+1}_{DATE_STR}.mp3"
            download_clip(clip, out)
            clip_files.append(out)

    if not clip_files:
        if args.dry_run:
            log.info("[DRY RUN] Done — no files written")
        else:
            sys.exit("No audio clips generated")
        return

    # 2. Render visual loop (reuse if exists)
    loop_mp4 = render_loop(theme, loop_sec)

    # 3. For each duration: build audio, assemble video, write meta+thumb
    presets = {1: "slow", 2: "medium", 3: "medium", 8: "fast"}
    for h in durations:
        target_sec = h * 3600
        out_base   = f"{song_id}_{h}h_{DATE_STR}"
        audio_path = AUDIO_DIR / f"audio_{out_base}.mp3"
        video_path = queue_dir / f"{out_base}.mp4"
        thumb_path = queue_dir / f"thumb_{out_base}.png"

        if video_path.exists():
            log.info(f"  Already exists: {video_path.name} — skipping")
            continue

        build_looped_audio(clip_files, target_sec, audio_path)
        assemble_video(loop_mp4, audio_path, target_sec, video_path,
                       preset=presets.get(h, "medium"))
        write_meta(cfg, h, video_path)
        generate_thumbnail(song_id, title, theme, thumb_path)
        audio_path.unlink(missing_ok=True)

    log.info(f"Done: {song_id}")


if __name__ == "__main__":
    main()
