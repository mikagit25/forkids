#!/usr/bin/env python3
"""
Generate kids classical music compilation videos for the Happy Bear Kids EN channel.

Per-composer compilations: Bach, Beethoven, Mozart, Chopin, Schubert, Tchaikovsky, Verdi.
Visuals: KidsClassicsLoop Remotion component (3D sprites — bear + notes + stars).
Audio: Musopen PD/CC0 recordings from assets/music/classical/licenses.yaml.
Output: output/queue/ (made_for_kids: true).

Usage:
  python3 scripts/generate_kids_classical.py --list
  python3 scripts/generate_kids_classical.py --composer bach
  python3 scripts/generate_kids_classical.py --all
  python3 scripts/generate_kids_classical.py --all --dry-run
"""

import argparse, json, logging, re, shutil, subprocess, tempfile, yaml
from datetime import datetime
from pathlib import Path

ROOT          = Path(__file__).resolve().parent.parent
REMOTION      = ROOT / "remotion"
LICENSES_YAML = ROOT / "assets/music/classical/licenses.yaml"
CLASSICAL_DIR = ROOT / "assets/music/classical"
QUEUE_EN      = ROOT / "output" / "queue"
DATE_STR      = datetime.now().strftime("%Y%m%d")

CROSSFADE = 3    # seconds between tracks
FPS       = 30
LOOP_SECS = 300  # 5-min Remotion loop (9000 frames)

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ── Composer configs ───────────────────────────────────────────────────────────
# Each entry: display_name, composer_full (for licenses.yaml lookup),
#             bgTop, bgBottom, secondary_sprite, title_en, tags

COMPOSERS = {
    "bach": {
        "display":   "Bach for Kids 🎵",
        "composer":  "Johann Sebastian Bach",
        "bgTop":     "#0d1a5c",
        "bgBottom":  "#2233a8",
        "sprite2":   "animals/owl_3d.png",
        "title_en":  "Bach for Kids 🎵 1 Hour Classical Music for Children | Happy Bear Kids",
        "tags":      ["bach for kids", "classical music for kids", "bach kids",
                      "kids classical", "learning music", "happy bear kids",
                      "educational music", "brain development", "toddler music"],
    },
    "beethoven": {
        "display":   "Beethoven for Kids 🎻",
        "composer":  "Ludwig van Beethoven",
        "bgTop":     "#1a0a3c",
        "bgBottom":  "#4a1a90",
        "sprite2":   "objects/star_3d.png",
        "title_en":  "Beethoven for Kids 🎻 1 Hour Classical Music for Children | Happy Bear Kids",
        "tags":      ["beethoven for kids", "classical music for kids", "beethoven kids",
                      "kids classical", "learning music", "happy bear kids",
                      "educational music", "brain development", "toddler music"],
    },
    "mozart": {
        "display":   "Mozart for Kids 🎹",
        "composer":  "Wolfgang Amadeus Mozart",
        "bgTop":     "#0a3a20",
        "bgBottom":  "#1a7a40",
        "sprite2":   "animals/parrot_3d.png",
        "title_en":  "Mozart for Kids 🎹 1 Hour Classical Music for Children | Happy Bear Kids",
        "tags":      ["mozart for kids", "classical music for kids", "mozart kids",
                      "kids classical", "learning music", "happy bear kids",
                      "educational music", "brain development", "toddler music"],
    },
    "chopin": {
        "display":   "Chopin for Kids 🌙",
        "composer":  "Frédéric Chopin",
        "bgTop":     "#3a0a58",
        "bgBottom":  "#7a1a9a",
        "sprite2":   "animals/flamingo_3d.png",
        "title_en":  "Chopin for Kids 🌙 1 Hour Classical Music for Children | Happy Bear Kids",
        "tags":      ["chopin for kids", "classical music for kids", "chopin kids",
                      "kids classical", "learning music", "happy bear kids",
                      "educational music", "piano for kids", "toddler music"],
    },
    "schubert": {
        "display":   "Schubert for Kids 🍂",
        "composer":  "Franz Schubert",
        "bgTop":     "#3a1800",
        "bgBottom":  "#7a3800",
        "sprite2":   "animals/fox_3d.png",
        "title_en":  "Schubert for Kids 🍂 1 Hour Classical Music for Children | Happy Bear Kids",
        "tags":      ["schubert for kids", "classical music for kids", "schubert kids",
                      "kids classical", "learning music", "happy bear kids",
                      "educational music", "brain development", "toddler music"],
    },
    "tchaikovsky": {
        "display":   "Tchaikovsky for Kids 🦢",
        "composer":  "Pyotr Ilyich Tchaikovsky",
        "bgTop":     "#0a1a4a",
        "bgBottom":  "#1a3a8a",
        "sprite2":   "animals/blue_whale_3d.png",
        "title_en":  "Tchaikovsky for Kids 🦢 1 Hour Classical Music for Children | Happy Bear Kids",
        "tags":      ["tchaikovsky for kids", "classical music for kids", "swan lake kids",
                      "kids classical", "learning music", "happy bear kids",
                      "educational music", "brain development", "toddler music"],
    },
    "haydn": {
        "display":   "Haydn for Kids 🎼",
        "composer":  "Joseph Haydn",
        "bgTop":     "#2a1800",
        "bgBottom":  "#7a4800",
        "sprite2":   "animals/lion_3d.png",
        "title_en":  "Haydn for Kids 🎼 1 Hour Classical Music for Children | Happy Bear Kids",
        "tags":      ["haydn for kids", "classical music for kids", "haydn kids",
                      "kids classical", "learning music", "happy bear kids",
                      "educational music", "brain development", "toddler music"],
    },
    "vivaldi": {
        "display":   "Vivaldi for Kids 🌸",
        "composer":  "Antonio Vivaldi",
        "bgTop":     "#0a3a10",
        "bgBottom":  "#1a8030",
        "sprite2":   "animals/rabbit_3d.png",
        "title_en":  "Vivaldi for Kids 🌸 1 Hour Classical Music for Children | Happy Bear Kids",
        "tags":      ["vivaldi for kids", "classical music for kids", "four seasons kids",
                      "kids classical", "learning music", "happy bear kids",
                      "educational music", "brain development", "toddler music"],
    },
    "handel": {
        "display":   "Handel for Kids 🎺",
        "composer":  "George Frideric Handel",
        "bgTop":     "#2a0a40",
        "bgBottom":  "#600a90",
        "sprite2":   "animals/polar_bear_3d.png",
        "title_en":  "Handel for Kids 🎺 1 Hour Classical Music for Children | Happy Bear Kids",
        "tags":      ["handel for kids", "classical music for kids", "baroque music kids",
                      "kids classical", "learning music", "happy bear kids",
                      "educational music", "brain development", "toddler music"],
    },
    "debussy": {
        "display":   "Debussy for Kids 💧",
        "composer":  "Claude Debussy",
        "bgTop":     "#001a3a",
        "bgBottom":  "#003a7a",
        "sprite2":   "animals/cat_3d.png",
        "title_en":  "Debussy for Kids 💧 1 Hour Classical Music for Children | Happy Bear Kids",
        "tags":      ["debussy for kids", "classical music for kids", "impressionist music kids",
                      "kids classical", "learning music", "happy bear kids",
                      "educational music", "brain development", "toddler music"],
    },
}

# Day-of-week slots for EN kids classical (Wednesday=2, Saturday=5)
CLASSICAL_DOW = {2, 5}


# ── Helpers ────────────────────────────────────────────────────────────────────

def get_duration(path: Path) -> float:
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(path)],
            capture_output=True
        )
        return float(json.loads(r.stdout)["format"]["duration"])
    except Exception:
        return 0.0


def load_composer_tracks(composer_full: str) -> list[Path]:
    data = yaml.safe_load(LICENSES_YAML.read_text())
    tracks = []
    for rec in data.get("recordings", []):
        if rec.get("license") not in ("pd", "cc0"):
            continue
        if rec.get("composer", "") != composer_full:
            continue
        fpath = CLASSICAL_DIR / rec.get("file", "")
        if fpath.exists():
            dur = get_duration(fpath)
            if dur >= 60:
                tracks.append(fpath)
    return tracks


def load_piece_names(composer_full: str) -> dict[Path, str]:
    """Return {path: piece_name} for a composer."""
    data = yaml.safe_load(LICENSES_YAML.read_text())
    result = {}
    for rec in data.get("recordings", []):
        if rec.get("composer", "") != composer_full:
            continue
        fpath = CLASSICAL_DIR / rec.get("file", "")
        if fpath.exists():
            result[fpath] = rec.get("piece", fpath.stem)
    return result


def concat_audio(tracks: list[Path], out_mp3: Path, target_dur: float) -> float:
    selected, total = [], 0.0
    pool = list(tracks)
    idx  = 0
    while total < target_dur:
        t   = pool[idx % len(pool)]
        dur = get_duration(t)
        if dur > 0:
            selected.append(t)
            total += dur
        idx += 1
        if idx > len(pool) * 4:
            break

    # Write concat list
    concat_list = out_mp3.parent / f"_concat_{out_mp3.stem}.txt"
    with concat_list.open("w") as f:
        for t in selected:
            # ffmpeg concat: escape backslash, single-quote, then wrap in single quotes
            # For paths with embedded single quotes use backslash escape outside quotes
            p = str(t)
            if "'" not in p:
                f.write(f"file '{p}'\n")
            else:
                # Escape every special char with backslash — no outer quoting
                escaped = re.sub(r"([ '\"\\#:,!])", r"\\\1", p)
                f.write(f"file {escaped}\n")

    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-af", f"afade=t=in:d=3,afade=t=out:st={int(total)-3}:d=3",
        "-ar", "44100", "-ab", "192k",
        str(out_mp3),
    ]
    r = subprocess.run(cmd, capture_output=True, timeout=600)
    concat_list.unlink(missing_ok=True)
    if r.returncode != 0:
        log.error(f"Audio concat failed: {r.stderr.decode()[-300:]}")
        return 0.0
    actual = get_duration(out_mp3)
    mb = out_mp3.stat().st_size // 1024 // 1024
    log.info(f"  Audio: {out_mp3.name} ({actual/60:.1f} min, {mb}MB)")
    return actual


def render_loop(cfg: dict, out_path: Path, dry_run: bool) -> bool:
    """Render 5-min KidsClassicsLoop visual (silent)."""
    sprites = [
        {"path": "animals/bear_3d.png",   "size": 460, "baseX": 0.50, "baseY": 0.44,
         "xAmp": 80,  "xN": 3, "yAmp": 50, "yN": 2, "scaleAmp": 0.05, "seed": 1},
        {"path": "objects/note_gold.png", "size": 160, "baseX": 0.18, "baseY": 0.28,
         "xAmp": 100, "xN": 2, "yAmp": 70, "yN": 3, "scaleAmp": 0.08, "seed": 2},
        {"path": "objects/note_gold.png", "size": 130, "baseX": 0.80, "baseY": 0.32,
         "xAmp": 90,  "xN": 4, "yAmp": 60, "yN": 2, "scaleAmp": 0.07, "seed": 3},
        {"path": cfg["sprite2"],          "size": 145, "baseX": 0.14, "baseY": 0.68,
         "xAmp": 70,  "xN": 3, "yAmp": 55, "yN": 4, "scaleAmp": 0.06, "seed": 4},
        {"path": "objects/star_3d.png",   "size": 110, "baseX": 0.86, "baseY": 0.72,
         "xAmp": 80,  "xN": 2, "yAmp": 45, "yN": 3, "scaleAmp": 0.08, "seed": 5},
    ]
    props = json.dumps({
        "bgTop":    cfg["bgTop"],
        "bgBottom": cfg["bgBottom"],
        "sprites":  sprites,
    })
    cmd = [
        "npx", "remotion", "render", "src/index.ts", "KidsClassicsLoop",
        str(out_path),
        "--props", props,
        "--concurrency", "2",
        "--log", "error",
    ]
    if dry_run:
        log.info(f"  [DRY RUN] npx remotion render KidsClassicsLoop → {out_path.name}")
        return True
    log.info(f"  Rendering 5-min visual loop → {out_path.name}")
    r = subprocess.run(cmd, cwd=str(REMOTION), capture_output=False, timeout=3600)
    if r.returncode != 0 or not out_path.exists():
        log.error("Remotion render failed")
        return False
    mb = out_path.stat().st_size // 1024 // 1024
    log.info(f"  ✓ Loop rendered ({mb}MB)")
    return True


def assemble_video(loop_path: Path, audio_path: Path, out_path: Path,
                   duration: float, dry_run: bool) -> bool:
    """Loop the visual to match audio duration, then mux audio."""
    n_loops = max(1, int(duration / LOOP_SECS) + 1)
    tmp_video = out_path.parent / f"_tmp_video_{out_path.stem}.mp4"

    if dry_run:
        log.info(f"  [DRY RUN] ffmpeg -stream_loop {n_loops-1} → mux audio → {out_path.name}")
        return True

    # Step 1: loop visual to slightly more than audio duration
    cmd1 = [
        "ffmpeg", "-y",
        "-stream_loop", str(n_loops - 1),
        "-i", str(loop_path),
        "-t", str(int(duration) + 5),
        "-c:v", "copy",
        str(tmp_video),
    ]
    r = subprocess.run(cmd1, capture_output=True, timeout=600)
    if r.returncode != 0:
        log.error(f"Video loop failed: {r.stderr.decode()[-300:]}")
        return False

    # Step 2: mux audio (trim to exact audio duration)
    cmd2 = [
        "ffmpeg", "-y",
        "-i", str(tmp_video),
        "-i", str(audio_path),
        "-map", "0:v:0", "-map", "1:a:0",
        "-t", str(int(duration)),
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        str(out_path),
    ]
    r = subprocess.run(cmd2, capture_output=True, timeout=600)
    tmp_video.unlink(missing_ok=True)
    if r.returncode != 0 or not out_path.exists():
        log.error(f"Mux failed: {r.stderr.decode()[-300:]}")
        return False

    mb = out_path.stat().st_size // 1024 // 1024
    log.info(f"  ✓ Video: {out_path.name} ({mb}MB)")
    return True


def make_thumbnail(cfg: dict, out_path: Path):
    """Use Pollinations (free) to generate an educational kids classical thumbnail."""
    import requests, urllib.parse
    composer_short = cfg["composer"].split()[-1]
    prompt = (
        f"happy cartoon bear cub playing piano, classical music for children, "
        f"{composer_short} for kids, colorful 3D Pixar style illustration, "
        f"music notes floating, bright {cfg['bgTop']} background, joyful educational, "
        f"no text, no letters, no words, 1280x720"
    )
    url  = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?width=1280&height=720&nologo=true&model=flux"
    try:
        resp = requests.get(url, timeout=120)
        resp.raise_for_status()
        out_path.write_bytes(resp.content)
        log.info(f"  ✓ Thumb: {out_path.name}")
    except Exception as e:
        log.warning(f"  Thumb failed: {e}")


def build_meta(key: str, cfg: dict, tracks: list[Path], duration: float) -> dict:
    piece_names = load_piece_names(cfg["composer"])
    composer    = cfg["composer"]
    last_name   = composer.split()[-1]
    mins        = int(duration / 60)
    hours, rem  = mins // 60, mins % 60
    dur_str     = f"{hours} Hour {rem} Min" if hours else f"{mins} Minutes"

    seen, tracklist = set(), []
    for t in tracks:
        name = piece_names.get(t, t.stem)
        if name not in seen:
            seen.add(name)
            tracklist.append(name)
    tl_text = "\n".join(f"  {i:02d}. {n}" for i, n in enumerate(tracklist, 1))

    description = f"""{cfg['display']}

🎓 Introducing children to classical music from an early age supports brain development, emotional intelligence, and creativity!

This {dur_str.lower()} compilation brings {last_name}'s greatest works to life for babies and toddlers — gentle enough for sleep, lively enough to spark curiosity.

👶 Ages: 0–5 years
🎧 Best with: headphones or good speakers
✨ Ideal for: learning, playtime, background music, bedtime

━━━━━━━━━━━━━━━━━━━━━━━
About Happy Bear Kids:
Fun and educational videos for babies and toddlers — songs, dances, colors, numbers, and classical music to help your child grow and learn!

Subscribe ⭐ @HappyBearKids1
━━━━━━━━━━━━━━━━━━━━━━━

🎵 {last_name} — Works in this compilation:
{tl_text}

🎼 Music: {composer} | Public Domain recordings via Musopen.org
🎵 Original music © Happy Bear Kids | Visuals © Happy Bear Kids 2026

#classicalmusicforkids #{last_name.lower()}forkids #kidsclassical #classicalbabies
#happybearkids #babymusic #toddlermusic #braindevelopment #educationalmusic"""

    tags = cfg["tags"][:25]
    seen_t, final_tags, total = set(), [], 0
    for t in tags:
        if t and t not in seen_t and len(t) <= 30 and len(final_tags) < 25 and total + len(t) <= 400:
            seen_t.add(t); final_tags.append(t); total += len(t)

    return {
        "title":         cfg["title_en"],
        "description":   description,
        "tags":          final_tags,
        "video_type":    "kids_classical",
        "language":      "en",
        "is_short":      False,
        "status":        "public",
        "made_for_kids": True,
        "ai_generated":  False,
        "composer":      composer,
        "category":      key,
        "track_count":   len(tracks),
        "duration_sec":  int(duration),
    }


def process_composer(key: str, dry_run: bool = False, force: bool = False) -> bool:
    cfg    = COMPOSERS[key]
    tracks = load_composer_tracks(cfg["composer"])
    if not tracks:
        log.warning(f"[{key}] No tracks found for {cfg['composer']}")
        return False

    out_stem    = f"kids_classical_{key}_{DATE_STR}"
    out_mp4     = QUEUE_EN / f"{out_stem}.mp4"
    out_meta    = QUEUE_EN / f"meta_{out_stem}.yaml"
    out_thumb   = QUEUE_EN / f"thumb_{out_stem}.png"
    tmp_mp3     = QUEUE_EN / f"_tmp_{out_stem}.mp3"
    loop_path   = QUEUE_EN / f"_loop_{out_stem}.mp4"

    if out_mp4.exists() and not force:
        log.info(f"[{key}] EXISTS — skip (--force to redo)")
        return True

    log.info(f"\n{'='*60}")
    log.info(f"Kids Classical: {cfg['display']}")
    log.info(f"  Composer: {cfg['composer']} | Tracks: {len(tracks)}")
    for t in tracks[:4]:
        log.info(f"    {t.name[:60]}")
    if len(tracks) > 4:
        log.info(f"    ... +{len(tracks)-4} more")

    if dry_run:
        total = sum(get_duration(t) for t in tracks)
        log.info(f"  [DRY RUN] {len(tracks)} tracks → ~{min(total, 3600)/60:.0f}min video")
        return True

    QUEUE_EN.mkdir(parents=True, exist_ok=True)
    try:
        # 1. Concat audio
        duration = concat_audio(tracks, tmp_mp3, 3600)
        if duration < 60:
            log.error("Audio too short")
            return False

        # 2. Render 5-min visual loop (reuse across all compilations if same config)
        if not loop_path.exists():
            if not render_loop(cfg, loop_path, dry_run=False):
                return False
        else:
            log.info(f"  ✓ Loop exists: {loop_path.name}")

        # 3. Assemble: loop visual + mux audio
        if not assemble_video(loop_path, tmp_mp3, out_mp4, duration, dry_run=False):
            return False

        # 4. Thumbnail
        make_thumbnail(cfg, out_thumb)

        # 5. Meta
        meta_doc = build_meta(key, cfg, tracks, duration)
        out_meta.write_text(yaml.dump(meta_doc, allow_unicode=True, default_flow_style=False))
        log.info(f"  ✓ Meta: {out_meta.name}")

        return True
    finally:
        tmp_mp3.unlink(missing_ok=True)
        loop_path.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--list",     action="store_true", help="List composers and track counts")
    parser.add_argument("--composer", help="Composer key: " + ", ".join(COMPOSERS))
    parser.add_argument("--all",      action="store_true", help="Generate all composers")
    parser.add_argument("--dry-run",  action="store_true")
    parser.add_argument("--force",    action="store_true")
    args = parser.parse_args()

    if args.list:
        print(f"\n{'Key':<14} {'Composer':<30} {'Tracks':>7}")
        print(f"{'-'*14} {'-'*30} {'-'*7}")
        for key, cfg in COMPOSERS.items():
            tracks = load_composer_tracks(cfg["composer"])
            total  = sum(get_duration(t) for t in tracks)
            print(f"{key:<14} {cfg['composer']:<30} {len(tracks):>5}  (~{total/60:.0f}min)")
        return

    if args.composer:
        if args.composer not in COMPOSERS:
            log.error(f"Unknown composer: {args.composer}. Keys: {list(COMPOSERS)}")
            return
        to_process = [args.composer]
    elif args.all:
        to_process = list(COMPOSERS.keys())
    else:
        parser.print_help()
        return

    ok = fail = 0
    for key in to_process:
        if process_composer(key, dry_run=args.dry_run, force=args.force):
            ok += 1
        else:
            fail += 1

    log.info(f"\nDone: {ok} OK, {fail} failed")


if __name__ == "__main__":
    main()
