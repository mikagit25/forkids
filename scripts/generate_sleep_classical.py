#!/usr/bin/env python3
"""
Generate Classical Night Relax (@ClassicalNightRelax) sleep/focus program videos.

Pipeline:
  Phase A — Render shared loops (SleepClassicalLoop, ~4-5 min, no audio)
  Phase B — Assemble long videos (1h / 3h / 8h) via FFmpeg:
             concatenate tracks + loop visual to match total duration

Usage:
  python3 scripts/generate_sleep_classical.py --render-loops-only
  python3 scripts/generate_sleep_classical.py --program sleep_chopin_01
  python3 scripts/generate_sleep_classical.py --program focus_bach_01 --durations 1
  python3 scripts/generate_sleep_classical.py --list-programs
  python3 scripts/generate_sleep_classical.py --regen-meta --program sleep_chopin_01
"""
import argparse, base64, json, logging, random, re, subprocess, sys, time, yaml
from datetime import datetime
from pathlib import Path

ROOT       = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from disk_guard import check_disk_space
REMOTION   = ROOT / "remotion"
PROGRAMS   = ROOT / "config" / "sleep_programs"
MUSIC_DIR  = ROOT / "assets" / "music" / "classical"
LICENSES   = ROOT / "assets" / "music" / "classical" / "licenses.yaml"
QUEUE_CC   = ROOT / "output" / "queue_id"    # Classical Night Relax queue (@ClassicalNightRelax)
QUEUE_EN   = ROOT / "output" / "queue"       # EN kids queue (for kids_sleep track)
LOOPS_DIR  = ROOT / "output" / "_sleep_loops"
TOGETHER_KEY_FILE = ROOT / "credentials" / "together_api_key.txt"
PEXELS_KEY_FILE   = ROOT / "credentials" / "pexels_api_key.txt"
DATE_STR   = datetime.now().strftime("%Y%m%d")

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ── Ken Burns visual loops — AI image per program ─────────────────────────────
KB_N_IMAGES  = 6    # images per program (×30s clips = ~3 min loop)
KB_CLIP_DUR  = 30   # seconds per clip
KB_XFADE_DUR = 3    # crossfade between clips
KB_FADE_SECS = 2    # fade in at start
KB_FPS       = 25
KB_MOTIONS   = ["zoom_in", "pan_right", "zoom_out", "pan_left", "pan_up", "pan_down"]

# Cinematic prompts per program — used for both Ken Burns loop images and thumbnail
PROGRAM_KB_PROMPTS: dict[str, str] = {
    "sleep_chopin_01":          "candlelit grand piano in dark Parisian salon, moonlight through tall windows, romantic atmosphere, cinematic 4K, no text, no letters",
    "sleep_chopin_02":          "Romantic era salon with soft candlelight, old gold picture frames, moonlit Parisian interior, warm amber glow, no text, no letters",
    "sleep_swan_lake_01":       "moonlit lake at night, white swans gliding on still water, full moon reflection, misty forest background, ethereal blue, no text, no letters",
    "sleep_swan_lake_02":       "swan lake at dusk, water surface reflecting stars, mist rising over dark water, dreamlike blue and silver tones, no text, no letters",
    "sleep_debussy_01":         "impressionist lily pond at dawn, water reflections, soft morning mist, Monet-inspired, gentle pastel colors, no text, no letters",
    "sleep_romantic_night_01":  "candlelit grand library at night, violin resting on velvet, moonlight through arched windows, warm amber fireplace glow, no text, no letters",
    "sleep_flute_01":           "misty morning forest, golden rays through ancient trees, dew on leaves, peaceful woodland atmosphere at dawn, no text, no letters",
    "sleep_baroque_01":         "baroque palace interior at night, ornate chandeliers, gold architecture, candlelight reflecting on marble floors, no text, no letters",
    "sleep_grand_night_01":     "grand concert hall at night, ornate ceiling, dramatic spotlights over empty seats, majestic orchestral atmosphere, no text, no letters",
    "focus_beethoven_01":       "dramatic storm clouds over hilltop, lightning in distance, powerful Romantic landscape, dark cinematic 4K, no text, no letters",
    "focus_beethoven_02":       "Beethoven-era Vienna concert hall, dramatic lighting, symphony orchestra silhouettes, intense passionate atmosphere, no text, no letters",
    "focus_mozart_01":          "Viennese baroque palace ballroom, crystal chandeliers, elegant 18th century interior, golden afternoon sunlight, no text, no letters",
    "focus_drama_01":           "dramatic opera house interior, red velvet curtains, ornate gilded balconies, theatrical spotlight, deep shadows, no text, no letters",
    "sleep_beethoven_cello_01": "cello leaning against window at dusk, autumn leaves outside, warm lamplight, cozy evening room ambiance, no text, no letters",
    "focus_beethoven_cello_01": "cello and piano in sunlit studio, warm afternoon light on wooden floor, sheet music, serene focus atmosphere, no text, no letters",
    "sleep_lullaby_01":         "cozy nursery at night, moonlight through curtains, soft mobile above crib, warm amber nightlight, peaceful, no text, no letters",
    "sleep_moonlight_01":       "moonlit grand piano in dark Parisian salon, silver moonlight through tall arched windows, Chopin nocturne atmosphere, romantic night, cinematic 4K, no text, no letters",
    "focus_classical_miniatures_01": "elegant study room on rainy afternoon, open books and sheet music, warm desk lamp, misty garden through tall French window, intellectual focus, classical music atmosphere, no text, no letters",
    "sleep_grand_orchestral_01":    "moonlit concert hall exterior at night, grand dome illuminated against dark sky, Tchaikovsky era Vienna opera house, majestic and serene, cinematic photography, no text, no letters",
    "sleep_complete_romantic_01":   "candlelit cello resting against grand piano in intimate salon, moonlight through silk curtains, romantic 19th century interior, Chopin and Beethoven atmosphere, no text, no letters",
    "focus_baroque_chamber_01":     "baroque library at golden afternoon, sunlight through tall windows onto musical manuscripts and violin, Bach era study room, scholarly and peaceful, no text, no letters",
    "sleep_schubert_01":            "moonlit Viennese salon at night, candlelit grand piano, pale blue moonlight through tall windows, Schubert era romantic interior, soft shadows and warm amber candle glow, no text, no letters",
    "focus_bach_violin_partita_01": "baroque violin resting on open score pages in sunlit studio, warm golden afternoon light, wooden music stand, Bach manuscript on desk, scholarly peaceful atmosphere, no text, no letters",
    "focus_beethoven_kreutzer_01":  "Beethoven-era concert hall, violinist and pianist on stage in dramatic spotlight, passionate performance, grand piano gleaming under warm stage lights, cinematic 4K, no text, no letters",
    "sleep_schubert_impromptus_01": "candlelit upright piano in cozy Viennese parlour at night, warm amber lamplight on sheet music, soft snow outside frosted window, Schubert era intimate interior, no text, no letters",
    "sleep_schubert_piano_01":      "moonlit grand piano in dark Romantic-era salon, silver moonlight streaming through tall arched window, Schubert D.960 atmosphere, blue-grey shadows and pale moonlight, no text, no letters",
    "sleep_chopin_ballades_01":     "candlelit Romantic salon at midnight, grand piano with sheet music, moonlight through silk curtains, Chopin era Polish parlour, warm gold and cool silver tones, no text, no letters",
    "sleep_schubert_chamber_01":    "Viennese chamber ensemble at night, cello and piano in intimate candlelit salon, warm amber glow on wooden floor, Schubert Winterreise atmosphere, soft shadows, no text, no letters",
    "sleep_baroque_romantics_01":   "baroque concert hall interior at night, ornate gilded arches, candlelight on marble, Vivaldi and Handel era atmosphere, golden chandeliers, no text, no letters",
    "sleep_grand_all_01":           "grand concert hall interior at night, ornate ceiling with dramatic chandeliers, Tchaikovsky era Vienna opera house, golden light on empty seats, majestic and serene, no text, no letters",
    "focus_bach_goldberg_complete_01": "baroque harpsichord in sunlit study, golden afternoon light through arched window, Bach manuscript pages open on music stand, scholarly peaceful atmosphere, no text, no letters",
    "focus_beethoven_violin_01":    "violin and piano on concert stage in dramatic spotlight, passionate performance, grand piano gleaming under warm stage lights, Beethoven era concert hall, no text, no letters",
    "focus_beethoven_concertos_01": "Beethoven-era grand concert hall, majestic piano on stage in dramatic spotlight, ornate golden ceiling, romantic atmosphere, cinematic 4K, no text, no letters",
    "sleep_beethoven_symphony9_01": "moonlit hilltop with dramatic clouds, moonlight breaking through storm over rolling hills, Beethoven Ninth Symphony atmosphere, majestic and serene, cinematic photography, no text, no letters",
    "focus_wagner_tannhaeuser_01":  "19th century opera house interior at night, ornate red velvet curtains, dramatic golden stage lights, Wagner era grand theater atmosphere, cinematic 4K, no text, no letters",
    "focus_franck_violin_01":       "violin and piano in sunlit French salon, warm afternoon light on wooden parquet, Romantic era chamber music atmosphere, sheet music on stand, no text, no letters",
    "focus_beethoven_eroica_01":    "dramatic Alpine landscape at sunset, storm clouds over mountain peaks, heroic Beethoven Eroica atmosphere, cinematic wide angle, no text, no letters",
    "sleep_romantic_orchestral_01": "moonlit lake at night, white swans on still water, full moon reflection, romantic orchestral atmosphere, Tchaikovsky era, ethereal blue tones, no text, no letters",
    "sleep_beethoven_complete_3h_01": "moonlit grand concert hall, Beethoven era symphony orchestra silhouettes under dramatic chandeliers, majestic golden interior, cinematic 4K night atmosphere, no text, no letters",
    "focus_wagner_complete_3h_01":    "19th century opera house at night, red velvet curtain with golden fringe, dramatic stage spotlights, Wagner era grand theater, atmospheric and cinematic, no text, no letters",
    "sleep_romantic_orchestral_3h_01": "moonlit lake at night with swans, full moon reflecting on still water, ethereal mist, Tchaikovsky era romantic atmosphere, cinematic photography, no text, no letters",
    # Kids sleep programs — Happy Bear Kids EN channel
    "sleep_kids_moonlight_3h_01": "sleeping baby bear cub curled up under a glowing moon, cozy forest den with soft stars, magical watercolor dreamscape, warm pastels, gentle and peaceful children's illustration, no text, no letters",
    "sleep_kids_stars_3h_01":     "baby animals sleeping together in an enchanted forest clearing under a canopy of shimmering stars, moonbeams through tall trees, Pixar-inspired dreamy illustration, soft pastel colors, no text, no letters",
    "sleep_kids_piano_3h_01":     "cozy moonlit nursery with sleeping teddy bear beside a tiny piano, stars twinkling outside a round window, warm amber nightlight glow, soft magical children's book illustration style, no text, no letters",
    "sleep_kids_mozart_3h_01":    "baby bunny and baby bear sleeping peacefully under a soft glowing moon, magical forest glade with floating musical notes and sparkling fireflies, pastel watercolor dreamy illustration, warm and gentle children's book style, no text, no letters",
    "sleep_kids_beethoven_3h_01": "sleeping baby bear cub in a cozy moonlit den, moonbeam streaming through a round window casting silver light on a fluffy blanket, tiny piano in the corner, enchanted forest night scene, soft Pixar-inspired illustration, warm pastels, no text, no letters",
    "sleep_kids_cello_3h_01":     "baby deer and baby rabbit curled together sleeping in an enchanted meadow, tiny golden cello floating among stars and soft glowing flowers, magical night sky with crescent moon, dreamy children's watercolor illustration, pastel blue and gold tones, no text, no letters",
    "sleep_kids_lullaby_3h_01":   "cozy nursery at night with sleeping baby animals in a wooden crib, moonlight through lace curtains, soft mobile with stars and moons gently turning, warm amber nightlight, teddy bear on a rocking chair, gentle children's illustration style, no text, no letters",
    "sleep_kids_dreams_3h_01":    "baby owl, baby fox and baby bunny sleeping together in a fluffy cloud nest high above a starlit forest, glowing moon nearby, soft golden dream bubbles floating upward, magical Pixar-style dreamscape, pastel lavender and gold tones, no text, no letters",
}

# Programs where real Pexels photography beats AI-generated images
# (nature, landscapes, lakes, forests — real photos look more cinematic)
PROGRAM_KB_PEXELS: dict[str, str] = {
    "sleep_swan_lake_01":             "moonlit lake swans reflection misty night serene water nature",
    "sleep_swan_lake_02":             "swan lake sunset water reflection peaceful nature birds",
    "sleep_flute_01":                 "misty forest dawn golden light ancient trees peaceful morning",
    "sleep_debussy_01":               "water lily pond reflection morning mist tranquil nature",
    "sleep_beethoven_symphony9_01":   "dramatic storm clouds mountain peaks moonlight epic landscape",
    "focus_beethoven_eroica_01":      "alpine mountains sunset dramatic heroic landscape clouds",
    "sleep_romantic_orchestral_01":   "moonlit lake night reflection romantic ethereal mist nature",
    "sleep_romantic_orchestral_3h_01":"moonlit lake swans night reflection ethereal romantic mist",
    "sleep_baroque_romantics_01":     "ancient forest moonlight mystical trees night serene nature",
    "sleep_grand_all_01":             "moonlit mountain lake reflection serene night starry sky",
}

THEME_LOOP_SECS = {
    "moon_clouds": 240,
    "night_bear":  300,
    "warm_waves":  240,
    "rain_window": 240,
}

THEME_COMPOSITION = {
    "moon_clouds": "SleepClassicalLoop",
    "night_bear":  "SleepClassicalLoopNightBear",
    "warm_waves":  "SleepClassicalLoop",
    "rain_window": "SleepClassicalLoop",
}

HOURS_TO_LABEL = {1: "1 Hour", 3: "3 Hours", 8: "8 Hours"}


def _format_natural_duration(total_secs: float) -> str:
    """Format total seconds as a human-readable duration label for titles/tags."""
    h = int(total_secs // 3600)
    m = int((total_secs % 3600) // 60)
    if h > 0 and m > 0:
        return f"{h}h {m}min"
    elif h > 0:
        return f"{h}h"
    return f"{m} min"

TITLES = {
    "sleep_chopin_01":          "Chopin Nocturnes for Sleep ✨ {dur} | Classical Night Relax",
    "sleep_chopin_02":          "Chopin Complete — Nocturnes, Mazurkas & Études 🌙 {dur} | Classical Night Relax",
    "sleep_debussy_01":         "Debussy for Sleep ✨ {dur} | Classical Night Relax",
    "sleep_swan_lake_01":       "Tchaikovsky Swan Lake for Sleep 🦢 {dur} | Classical Night Relax",
    "sleep_swan_lake_02":       "Swan Lake Act III & IV 🦢 {dur} | Tchaikovsky | Classical Night Relax",
    "sleep_romantic_night_01":  "Romantic Classics for Sleep 🌙 {dur} | Classical Night Relax",
    "sleep_flute_01":           "Flute & Piano for Sleep 🎵 {dur} | Classical Night Relax",
    "sleep_baroque_01":         "Baroque Classics for Sleep 🎻 {dur} | Classical Night Relax",
    "sleep_grand_night_01":     "Grand Night — Orchestral Classics for Sleep 🎻 {dur} | Classical Night Relax",
    "focus_bach_01":            "Bach for Focus & Study 🎵 {dur} | Classical Night Relax",
    "focus_beethoven_01":       "Beethoven for Focus & Study 🎵 {dur} | Classical Night Relax",
    "focus_beethoven_02":       "Beethoven Symphony No. 5 — Complete 🎻 {dur} | Classical Night Relax",
    "focus_mozart_01":          "Mozart for Focus & Study 🎵 {dur} | Classical Night Relax",
    "focus_drama_01":           "Dramatic Classics for Focus 🎻 {dur} | Classical Night Relax",
    "sleep_beethoven_cello_01": "Beethoven Cello Sonatas for Sleep 🎻 {dur} | Classical Night Relax",
    "focus_beethoven_cello_01": "Beethoven Cello Sonatas for Focus & Study 🎻 {dur} | Classical Night Relax",
    "sleep_lullaby_01":         "Classical Lullabies for Sleep 🌙 {dur} | Happy Bear Kids",
    "sleep_moonlight_01":       "Moonlight Sonata & Nocturnes 🌙 {dur} | Beethoven · Chopin | Classical Night Relax",
    "focus_classical_miniatures_01": "Classical Miniatures for Focus 🎼 {dur} | Debussy · Chopin · Bach | Classical Night Relax",
    "sleep_grand_orchestral_01":    "Grand Orchestral Night 🎻 {dur} | Tchaikovsky · Beethoven · Verdi | Classical Night Relax",
    "sleep_complete_romantic_01":   "Complete Romantic Night 🌙 {dur} | Beethoven · Chopin · Debussy | Classical Night Relax",
    "focus_baroque_chamber_01":     "Baroque & Chamber Music for Focus 🎻 {dur} | Bach · Vivaldi · Mozart · Beethoven | Classical Night Relax",
    "sleep_schubert_impromptus_01": "Schubert Impromptus for Sleep 🎹 {dur} | D. 899 & D. 935 | Classical Night Relax",
    "sleep_schubert_piano_01":      "Schubert Piano Works for Deep Sleep 🌙 {dur} | D. 960 · D. 959 · Wanderer | Classical Night Relax",
    "sleep_chopin_ballades_01":     "Chopin Ballades & Salon Pieces for Sleep 🌙 {dur} | Classical Night Relax",
    "sleep_schubert_chamber_01":    "Schubert Chamber & Sacred Music for Sleep 🎻 {dur} | String Quintet · Piano Trio | Classical Night Relax",
    "sleep_schubert_01":            "Schubert for Deep Sleep 🌙 {dur} | Piano · Trio · Symphony | Classical Night Relax",
    "sleep_baroque_romantics_01":   "Baroque to Romantic Sleep Journey 🌙 {dur} | Bach · Beethoven · Tchaikovsky | Classical Night Relax",
    "sleep_grand_all_01":           "Grand Classical Night ✨ {dur} | Tchaikovsky · Beethoven · Bach · Chopin | Classical Night Relax",
    "focus_bach_goldberg_complete_01": "Bach Goldberg Variations Complete 🎹 {dur} | Focus & Study | Classical Night Relax",
    "focus_bach_violin_partita_01": "Bach Violin Partitas Complete 🎻 {dur} | Focus & Study | Classical Night Relax",
    "focus_beethoven_violin_01":    "Beethoven Violin Concerto & Cello Sonatas 🎻 {dur} | Focus & Study | Classical Night Relax",
    "focus_beethoven_concertos_01": "Beethoven Piano Concertos 🎹 {dur} | Classical Music for Focus | Classical Night Relax",
    "sleep_beethoven_symphony9_01": "Beethoven Symphony No. 9 🎶 {dur} | Classical Music for Sleep | Classical Night Relax",
    "focus_wagner_tannhaeuser_01":  "Wagner Tannhäuser 🎭 {dur} | Classical Music for Focus | Classical Night Relax",
    "focus_franck_violin_01":       "Franck & Beethoven Violin Sonatas 🎻 {dur} | Classical Music for Focus | Classical Night Relax",
    "focus_beethoven_eroica_01":    "Beethoven Eroica & Pastoral 🏔️ {dur} | Classical Music for Focus | Classical Night Relax",
    "sleep_romantic_orchestral_01": "Romantic Orchestral Classics 🌙 {dur} | Classical Music for Sleep | Classical Night Relax",
    "sleep_beethoven_complete_3h_01": "Beethoven Complete — Symphony 9 & Piano Concertos 🎶 {dur} | Classical Sleep | Classical Night Relax",
    "focus_wagner_complete_3h_01":    "Wagner Tannhäuser — Complete Opera 🎭 {dur} | Classical Focus | Classical Night Relax",
    "sleep_romantic_orchestral_3h_01": "Romantic Orchestral Night 🌙 {dur} | Tchaikovsky · Rachmaninoff · Borodin | Classical Sleep | Classical Night Relax",
    # Kids programs — Happy Bear Kids EN channel
    "sleep_kids_moonlight_3h_01": "Classical Music for Baby Sleep 🌙 {dur} | Chopin & Schubert | Happy Bear Kids",
    "sleep_kids_stars_3h_01":     "Baby Bedtime Classical Music ⭐ {dur} | Bach & Schubert | Happy Bear Kids",
    "sleep_kids_piano_3h_01":     "Gentle Piano for Children's Sleep 🎹 {dur} | Bach & Mozart | Happy Bear Kids",
    "sleep_kids_mozart_3h_01":    "Mozart for Babies 🎵 {dur} | Classical Baby Sleep Music | Happy Bear Kids",
    "sleep_kids_beethoven_3h_01": "Beethoven for Babies 🌙 {dur} | Moonlight Sonata Baby Sleep | Happy Bear Kids",
    "sleep_kids_cello_3h_01":     "Cello & Strings for Babies 🎻 {dur} | Gentle Classical Baby Sleep | Happy Bear Kids",
    "sleep_kids_lullaby_3h_01":   "Classical Lullabies for Babies 🌙 {dur} | Baby Bedtime Music | Happy Bear Kids",
    "sleep_kids_dreams_3h_01":    "Sweet Dreams for Babies 🌟 {dur} | Peaceful Classical Sleep Music | Happy Bear Kids",
}

DESC_TEMPLATES = {
    "calm_classics": """\
Welcome to Classical Night Relax — beautiful classical music for sleep, focus and relaxation.

{program_desc}

🎵 Tracks in this program:
{track_list}

🌙 Perfect for:
• Deep sleep and bedtime relaxation
• Study and concentration sessions
• Meditation and mindfulness practice
• Working from home background music
• Unwinding after a long day

✨ All recordings are public domain performances sourced from Musopen (musopen.org).
Full attribution and license details in the description below.

🎼 Music attribution:
{attribution}

No ads during playback. New programs every week.
Subscribe ▶ @ClassicalNightRelax

© Classical Night Relax 2026 — All rights reserved
#ClassicalNightRelax #SleepMusic #ClassicalMusic #StudyMusic #{composer_tag}Sleep
""",
    "kids_sleep": """\
Welcome to Happy Bear Kids! 🌙 Gentle classical music to help babies and toddlers sleep deeply and peacefully.

{program_desc}

🎓 Did you know? Introducing children to classical music from an early age supports brain development, emotional intelligence, and creativity. Studies show that calm classical music helps babies sleep longer and more peacefully while stimulating healthy neural connections.

🌙 Tracks in this program:
{track_list}

✨ Perfect for:
• Baby and toddler bedtime routines
• Nap time relaxation
• Calming an overtired baby
• Peaceful background for night feeds
• Early childhood musical enrichment
• Developing your child's love of classical music

🎼 Music: Public domain recordings from Musopen (musopen.org)
All composers passed away 200+ years ago — music is in the public domain.
These timeless masterpieces have been enjoyed for centuries and are now shared freely for your child's benefit.

{attribution}

Nurture your child's musical journey from the very first lullaby. 🎵
New programs every week! Subscribe ▶ @HappyBearKids1
© Happy Bear Kids 2026
#HappyBearKids #ClassicalMusicForBabies #BabySleep #ClassicalLullaby #SleepMusic #BabyBedtime #ChildDevelopment #ClassicalMusic #ToddlerSleep #BabyMusic
""",
}


def load_program(program_id: str) -> dict:
    path = PROGRAMS / f"{program_id}.yaml"
    if not path.exists():
        log.error(f"Program config not found: {path}")
        raise FileNotFoundError(path)
    with open(path) as f:
        return yaml.safe_load(f)


def load_licenses() -> dict:
    if not LICENSES.exists():
        return {"recordings": []}
    with open(LICENSES) as f:
        return yaml.safe_load(f) or {"recordings": []}


def _rec_to_path(rec: dict) -> Path | None:
    fname = rec.get("file", "")
    if not fname:
        return None
    p = MUSIC_DIR / fname
    return p if p.exists() else None


def _keyword_score(piece_query: str, rec: dict) -> int:
    """Rough overlap score between requested piece name and a registered entry."""
    q_words = set(re.sub(r"[^a-z0-9]", " ", piece_query.lower()).split())
    r_words = set(re.sub(r"[^a-z0-9]", " ", rec.get("piece", "").lower()).split())
    stopwords = {"in", "the", "a", "an", "no", "op", "and", "for", "of", "by"}
    q_words -= stopwords
    r_words -= stopwords
    return len(q_words & r_words)


def find_track_file(track_id: str, licenses_data: dict,
                    composer: str = "", piece: str = "") -> Path | None:
    """
    Find local MP3 by (in order of preference):
      1. Exact ID match
      2. ID prefix match (handles minor naming differences)
      3. Composer + piece keyword overlap
      4. Composer-only fallback (any track from same composer, warns)
    """
    recs = licenses_data.get("recordings", [])
    if not recs:
        return None

    # 1. Exact ID
    for rec in recs:
        if rec.get("id") == track_id or rec.get("id") == f"musopen_{track_id}":
            p = _rec_to_path(rec)
            if p:
                return p

    # 2. ID prefix (first 25 chars)
    prefix = re.sub(r"[^a-z0-9]", "_", track_id.lower())[:25]
    for rec in recs:
        if rec.get("id", "").startswith(prefix):
            p = _rec_to_path(rec)
            if p:
                log.info(f"    Fuzzy ID match: {track_id!r} → {rec['id']}")
                return p

    # 3. Composer + keyword match
    if composer and piece:
        c_low = composer.lower()
        best_score, best_rec = 0, None
        for rec in recs:
            if c_low not in rec.get("composer", "").lower():
                continue
            score = _keyword_score(piece, rec)
            if score > best_score:
                best_score, best_rec = score, rec
        if best_score >= 2 and best_rec:
            p = _rec_to_path(best_rec)
            if p:
                log.info(f"    Keyword match (score={best_score}): {track_id!r} → {best_rec['id']}")
                return p

    # Step 4 (composer-only fallback) REMOVED — it returned random large files
    # causing natural-mode videos to balloon to 10-16h. Tracks not found via
    # steps 1-3 are now skipped; the program runs with fewer tracks rather than wrong ones.

    return None


def render_shared_loop(theme: str, phase_offset: float = 0.0, force: bool = False) -> Path:
    """Render a 4-5 min seamless loop with no audio. Returns path to MP4."""
    LOOPS_DIR.mkdir(parents=True, exist_ok=True)
    loop_secs  = THEME_LOOP_SECS[theme]
    composition = THEME_COMPOSITION[theme]
    out_mp4 = LOOPS_DIR / f"loop_{theme}_ph{int(phase_offset*100):02d}.mp4"

    if out_mp4.exists() and not force:
        log.info(f"  Loop exists: {out_mp4.name}")
        return out_mp4

    props = {
        "theme":       theme,
        "musicFile":   "",          # no audio in shared loop
        "loopSecs":    loop_secs,
        "phaseOffset": phase_offset,
    }
    cmd = [
        "npx", "remotion", "render", composition,
        f"--props={json.dumps(props)}",
        f"--output={out_mp4}",
        "--log=error",
    ]
    log.info(f"  Rendering loop: {theme} phase={phase_offset:.2f} ({loop_secs}s)…")
    r = subprocess.run(cmd, cwd=str(REMOTION), timeout=3600)
    if r.returncode != 0 or not out_mp4.exists():
        raise RuntimeError(f"Loop render failed: {theme}")
    log.info(f"  ✓ {out_mp4.name} ({out_mp4.stat().st_size / 1024 / 1024:.0f}MB)")
    return out_mp4


def _kb_motion_vf(motion: str) -> str:
    """FFmpeg Ken Burns zoompan filter string."""
    frames = KB_CLIP_DUR * KB_FPS
    scale  = "scale=2688:1536"
    if motion == "zoom_in":
        z, x, y = "min(zoom+0.0006,1.5)", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif motion == "zoom_out":
        z, x, y = "if(eq(on,0),1.5,max(zoom-0.0006,1.0))", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif motion == "pan_right":
        z, x, y = "1.4", f"min(on*(iw-iw/zoom)/{frames-1},iw-iw/zoom)", "ih/2-(ih/zoom/2)"
    elif motion == "pan_left":
        z, x, y = "1.4", f"max((iw-iw/zoom)-on*(iw-iw/zoom)/{frames-1},0)", "ih/2-(ih/zoom/2)"
    elif motion == "pan_up":
        z, x, y = "1.4", "iw/2-(iw/zoom/2)", f"max((ih-ih/zoom)-on*(ih-ih/zoom)/{frames-1},0)"
    else:  # pan_down
        z, x, y = "1.4", "iw/2-(iw/zoom/2)", f"min(on*(ih-ih/zoom)/{frames-1},ih-ih/zoom)"
    zp = f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s=1920x1080:fps={KB_FPS}"
    return f"{scale},{zp}"


def _kb_make_clip(img: Path, out: Path, motion: str) -> bool:
    r = subprocess.run(
        ["ffmpeg", "-y", "-loop", "1", "-i", str(img),
         "-t", str(KB_CLIP_DUR), "-vf", _kb_motion_vf(motion),
         "-c:v", "libx264", "-preset", "fast", "-crf", "22",
         "-pix_fmt", "yuv420p", "-an", str(out)],
        capture_output=True, text=True, timeout=300
    )
    return r.returncode == 0 and out.exists()


def _kb_concat(clips: list[Path], out: Path) -> bool:
    """Xfade-concatenate Ken Burns clips into a seamless visual loop."""
    n = len(clips)
    if n == 1:
        import shutil; shutil.copy(clips[0], out); return True

    inputs = []
    for p in clips:
        inputs += ["-i", str(p)]

    step  = KB_CLIP_DUR - KB_XFADE_DUR
    total = n * KB_CLIP_DUR - (n - 1) * KB_XFADE_DUR
    fc    = (f"[0:v]fade=t=in:st=0:d={KB_FADE_SECS}[f0];"
             f"[f0][1:v]xfade=transition=fade:duration={KB_XFADE_DUR}:offset={step}[v01]")
    for i in range(2, n):
        offset = i * step
        prev   = f"[v{i-1:02d}]"
        nxt    = f"[v{i:02d}]" if i < n - 1 else "[vpre]"
        fc    += f";{prev}[{i}:v]xfade=transition=fade:duration={KB_XFADE_DUR}:offset={offset}{nxt}"
    if n > 2:
        fc += f";[vpre]fade=t=out:st={total - KB_FADE_SECS}:d={KB_FADE_SECS}[vout]"
    else:
        fc += f";[v01]fade=t=out:st={total - KB_FADE_SECS}:d={KB_FADE_SECS}[vout]"

    r = subprocess.run(
        ["ffmpeg", "-y"] + inputs + [
            "-filter_complex", fc, "-map", "[vout]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-an", str(out)],
        capture_output=True, text=True, timeout=600
    )
    if r.returncode != 0 or not out.exists():
        log.error(f"  xfade concat failed: {r.stderr[-300:]}")
        return False
    return True


def _fetch_pexels_images(query: str, n_images: int, out_dir: Path, force: bool = False) -> list[Path]:
    """Download landscape photos from Pexels API. Returns list of saved Paths."""
    import urllib.request, urllib.parse, json as _json
    if not PEXELS_KEY_FILE.exists():
        return []
    api_key = PEXELS_KEY_FILE.read_text().strip()
    out_dir.mkdir(parents=True, exist_ok=True)

    url = ("https://api.pexels.com/v1/search?"
           + urllib.parse.urlencode({"query": query, "per_page": n_images * 2,
                                     "orientation": "landscape"}))
    try:
        req = urllib.request.Request(url, headers={"Authorization": api_key})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = _json.loads(resp.read())
    except Exception as e:
        log.warning(f"  Pexels search failed: {e}")
        return []

    photos = data.get("photos", [])
    if not photos:
        log.warning(f"  Pexels: no results for '{query}'")
        return []

    images: list[Path] = []
    for i, photo in enumerate(photos[:n_images]):
        img_path = out_dir / f"pexels_{i:02d}.jpg"
        if img_path.exists() and not force:
            images.append(img_path)
            continue
        src_url = photo.get("src", {}).get("large2x") or photo.get("src", {}).get("original")
        if not src_url:
            continue
        try:
            req2 = urllib.request.Request(src_url, headers={"User-Agent": "KidsChannel/1.0"})
            with urllib.request.urlopen(req2, timeout=60) as resp:
                img_path.write_bytes(resp.read())
            images.append(img_path)
            log.info(f"  Pexels photo {i+1}: saved ({img_path.stat().st_size // 1024}KB)")
        except Exception as e:
            log.warning(f"  Pexels photo {i+1} download failed: {e}")

    return images


def render_kenburns_loop(program_id: str, force: bool = False) -> Path | None:
    """Generate Ken Burns loop — Pexels photos first (natural landscape), FLUX AI fallback."""
    prompt = PROGRAM_KB_PROMPTS.get(program_id)
    if not prompt:
        return None

    loop_path = LOOPS_DIR / f"loop_kenburns_{program_id}.mp4"
    if loop_path.exists() and not force:
        log.info(f"  Ken Burns loop cached: {loop_path.name}")
        return loop_path

    imgs_dir = LOOPS_DIR / f"imgs_{program_id}"
    imgs_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Try Pexels photos if this program has a nature/landscape query
    images: list[Path] = []
    pexels_query = PROGRAM_KB_PEXELS.get(program_id)
    if pexels_query:
        log.info(f"  Fetching Pexels photos: '{pexels_query}'")
        images = _fetch_pexels_images(pexels_query, KB_N_IMAGES, imgs_dir, force)
        if images:
            log.info(f"  Using {len(images)} Pexels photos for Ken Burns")

    # Step 2: Fall back to FLUX AI generation if no Pexels images
    if not images:
        if not TOGETHER_KEY_FILE.exists():
            log.warning("  No Together API key — aborting Ken Burns")
            return None
        api_key  = TOGETHER_KEY_FILE.read_text().strip()
        lighting_variants = ["moonlit", "candlelit", "dawn light", "golden hour", "dusk", "twilight"]

    if not images:
        log.info(f"  Generating {KB_N_IMAGES} FLUX images…")
    for i in range(KB_N_IMAGES if not images else 0):
        img_path = imgs_dir / f"img_{i:02d}.jpg"
        if img_path.exists() and not force:
            images.append(img_path)
            log.info(f"  Image cached: {img_path.name}")
            continue
        varied = f"{prompt}, {lighting_variants[i % len(lighting_variants)]} atmosphere"
        log.info(f"  Generating image {i+1}/{KB_N_IMAGES} via FLUX…")
        try:
            import requests as req
            resp = req.post(
                "https://api.together.xyz/v1/images/generations",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": "black-forest-labs/FLUX.1.1-pro",
                      "prompt": varied, "width": 1344, "height": 768,
                      "steps": 4, "n": 1, "response_format": "b64_json"},
                timeout=90
            )
            resp.raise_for_status()
            img_path.write_bytes(base64.b64decode(resp.json()["data"][0]["b64_json"]))
            images.append(img_path)
            time.sleep(2)
        except Exception as e:
            log.warning(f"  Image {i+1} failed: {e}")

    if len(images) < 2:
        log.error(f"  Only {len(images)} images — skipping Ken Burns loop")
        return None

    # Step 3: Ken Burns clips
    clips_dir = LOOPS_DIR / f"clips_{program_id}"
    clips_dir.mkdir(exist_ok=True)
    clips: list[Path] = []
    for i, img in enumerate(images):
        clip = clips_dir / f"clip_{i:02d}.mp4"
        if clip.exists() and not force:
            clips.append(clip)
            continue
        motion = KB_MOTIONS[i % len(KB_MOTIONS)]
        log.info(f"  Ken Burns clip {i+1}/{len(images)}: {motion}")
        if _kb_make_clip(img, clip, motion):
            clips.append(clip)
        else:
            log.warning(f"  Clip {i+1} failed — skipping")

    if not clips:
        log.error("  No clips created — aborting")
        return None

    # Step 4: Xfade concat → loop
    log.info(f"  Concat {len(clips)} clips → {loop_path.name}")
    LOOPS_DIR.mkdir(parents=True, exist_ok=True)
    if _kb_concat(clips, loop_path):
        log.info(f"  ✓ Ken Burns loop: {loop_path.name} ({loop_path.stat().st_size / 1024**2:.0f}MB)")
        return loop_path

    log.error("  Loop concat failed — aborting")
    return None


def _get_mp3_duration(path: Path) -> float:
    """Return duration in seconds via ffprobe."""
    import json as _json
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", str(path)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        for s in _json.loads(r.stdout).get("streams", []):
            if s.get("duration"):
                return float(s["duration"])
    except Exception:
        pass
    return 0.0


def compute_unique_minutes(program: dict, licenses_data: dict) -> float:
    """Return total unique audio minutes available for this program (found tracks only)."""
    total = 0
    for t in program.get("tracks", []):
        f = find_track_file(t["id"], licenses_data,
                            composer=t.get("composer", ""),
                            piece=t.get("piece", ""))
        if f:
            total += t.get("duration_sec") or _get_mp3_duration(f)
    return total / 60.0


def select_durations(requested: list[int], unique_min: float,
                     max_repeat: float, program_id: str) -> list[int]:
    """
    Filter requested durations to those where repetition ≤ max_repeat.
    Logs a clear warning for each skipped duration with recommendation.
    """
    approved = []
    for h in requested:
        target_min = h * 60
        repeat_factor = target_min / unique_min if unique_min > 0 else 999
        if repeat_factor <= max_repeat:
            approved.append(h)
        else:
            log.warning(
                f"  ⚠ SKIP {h}h — unique content {unique_min:.0f}min would repeat "
                f"×{repeat_factor:.1f} (max allowed ×{max_repeat}). "
                f"Need {target_min - unique_min:.0f}min more tracks to enable {h}h."
            )
    if not approved:
        # Always generate at least 1h regardless
        approved = [1]
        log.warning(f"  ⚠ Falling back to 1h only — add more tracks to {program_id}")
    return approved


def pad_tracks_from_pool(found: list, target_secs: int, licenses_data: dict,
                         pad_programs: list[str]) -> list:
    """
    Supplement found tracks with tracks from other programs until target_secs is covered.
    Avoids duplicating tracks already in found.
    """
    existing_paths = {fp for fp, _ in found}
    total_dur = sum(d for _, d in found)

    for prog_id in pad_programs:
        if total_dur >= target_secs:
            break
        prog_path = PROGRAMS / f"{prog_id}.yaml"
        if not prog_path.exists():
            log.warning(f"  Pad source not found: {prog_id}")
            continue
        pad_prog = yaml.safe_load(prog_path.read_text())
        pool = []
        for t in pad_prog.get("tracks", []):
            f = find_track_file(t["id"], licenses_data,
                                composer=t.get("composer", ""),
                                piece=t.get("piece", ""))
            if f and str(f) not in existing_paths:
                dur = t.get("duration_sec") or _get_mp3_duration(f)
                pool.append((str(f), dur))
                existing_paths.add(str(f))
        random.shuffle(pool)
        for item in pool:
            if total_dur >= target_secs:
                break
            found.append(item)
            total_dur += item[1]
        added_min = sum(d for _, d in found) / 60 - (total_dur - sum(item[1] for item in pool)) / 60
        if pool:
            log.info(f"  Padded from {prog_id}: +{len(pool)} tracks "
                     f"(total now {sum(d for _, d in found)/60:.0f}min)")
    return found


def build_audio_track(program: dict, licenses_data: dict, out_dir: Path,
                      target_secs: int = 0) -> Path | None:
    """
    Concatenate track MP3s into a single audio file covering at least target_secs.
    When found tracks are shorter than target_secs, the playlist is repeated.
    Returns path to combined MP3 or None if no tracks found.
    """
    tracks = program.get("tracks", [])
    if not tracks:
        return None

    found = []
    for t in tracks:
        f = find_track_file(t["id"], licenses_data,
                            composer=t.get("composer", ""),
                            piece=t.get("piece", ""))
        if f:
            # Use actual file duration, not YAML-declared value.
            # YAML duration_sec may not match the actual Musopen file found via fallback,
            # causing natural-mode videos to become 10-16h instead of 1-2h.
            actual_dur = _get_mp3_duration(f)
            if actual_dur < 1:
                log.warning(f"  Track unreadable/silent: {t['id']} ({f.name}) — skipped")
                continue
            yaml_dur = t.get("duration_sec", 0)
            if yaml_dur and actual_dur > yaml_dur * 3:
                log.warning(f"  Track {t['id']}: actual {actual_dur/60:.0f}min >> declared {yaml_dur/60:.0f}min "
                            f"— file may be wrong match: {f.name}")
            found.append((str(f), actual_dur))
        else:
            log.warning(f"  Track not found: {t['id']} ({t.get('piece','?')}) — skipped")

    if not found:
        log.warning("  No track files found — will generate visual-only (no audio)")
        return None

    # Pad from other programs if configured and content is still short
    pad_from = program.get("pad_from", [])
    total_dur = sum(d for _, d in found)
    if pad_from and target_secs > 0 and total_dur < target_secs:
        log.info(f"  Content {total_dur/60:.0f}min < target — padding from: {pad_from}")
        found = pad_tracks_from_pool(found, target_secs, licenses_data, pad_from)

    shuffle = program.get("shuffle", False)
    if shuffle:
        random.shuffle(found)

    # Loop the playlist until we cover target_secs
    total_dur = sum(d for _, d in found)
    if target_secs > 0 and total_dur < target_secs:
        repeat_factor = target_secs / total_dur
        log.info(f"  Audio {total_dur/60:.1f}min < {target_secs/3600:.0f}h target "
                 f"— {'shuffle-' if shuffle else ''}repeating ×{repeat_factor:.1f}")
        if shuffle:
            # Each repeat cycle re-shuffled — no identical loop seam
            extended = list(found)
            while sum(d for _, d in extended) < target_secs + total_dur:
                cycle = list(found)
                random.shuffle(cycle)
                extended.extend(cycle)
            found = extended
        else:
            reps = int(target_secs / total_dur) + 2
            found = found * reps

    concat_list = out_dir / "concat_tracks.txt"
    with open(concat_list, "w") as f:
        for fp, _ in found:
            # Escape single quotes in path (ffmpeg concat uses single-quote delimiters)
            safe = str(fp).replace("'", "'\\''")
            f.write(f"file '{safe}'\n")

    audio_out = out_dir / "audio_combined.mp3"
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        # Normalize to 44100 Hz stereo — fixes mixed-format sources (22050/48000 Hz, mono).
        # Do NOT use aresample=async: it pads silence to fill VBR-header estimated gaps,
        # producing output with 40-70% silence when individual track headers overestimate.
        "-ar", "44100", "-ac", "2",
        "-c:a", "libmp3lame", "-b:a", "192k",
    ]
    if target_secs > 0:
        cmd += ["-t", str(target_secs)]
    cmd.append(str(audio_out))

    # Generous timeout: format conversion (mono→stereo, 22050/48000→44100) can be slow.
    # At least 2h for any file; for large targets give full target duration as budget.
    audio_timeout = max(7200, target_secs) if target_secs > 0 else 7200
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=audio_timeout)
    if r.returncode != 0 or not audio_out.exists():
        log.error(f"  Audio concat failed: {r.stderr[:300]}")
        return None
    size_mb = audio_out.stat().st_size / 1024 / 1024
    log.info(f"  ✓ Audio: {audio_out.name} ({size_mb:.1f}MB, "
             f"{len(found)} track instances)")
    return audio_out


def assemble_video(loop_mp4: Path, audio_mp3: Path | None,
                   target_hours: int, out_mp4: Path) -> bool:
    """Loop visual to fill target duration, overlay audio, write output.
    target_hours=0 means natural length: use actual audio duration (no padding).
    """
    if target_hours == 0:
        target_secs = int(_get_mp3_duration(audio_mp3)) if audio_mp3 else 3600
        if target_secs == 0:
            log.warning("  Natural mode: could not read audio duration — defaulting to 3600s")
            target_secs = 3600
        max_natural_secs = 6 * 3600  # safety cap: natural videos must not exceed 6h
        if target_secs > max_natural_secs:
            log.error(
                f"  Natural mode ABORTED: audio is {target_secs/3600:.1f}h > 6h cap. "
                f"This likely means find_track_file returned wrong (oversized) recordings. "
                f"Fix track IDs in the program YAML to match actual Musopen filenames."
            )
            return False
        log.info(f"  Natural duration: {_format_natural_duration(target_secs)}")
    else:
        target_secs = target_hours * 3600
    # Use faster preset for long videos: slow→fast saves hours on 8h renders.
    # fast for all durations — slow takes 6h+ for 1h video on this server (OOM/timeout risk)
    preset = "fast"
    # Generous timeout: 4× video length + 2h buffer (medium/slow can take 4x real-time on this server)
    video_timeout = int(target_secs * 4) + 7200

    if audio_mp3:
        # Natural mode (target_hours=0): rely on -shortest alone — ffprobe duration
        # estimate for concatenated VBR MP3 is unreliable, so don't use -t to cap.
        # Fixed mode: -t is the primary duration control; -shortest guards against
        # silence if the audio track ends fractionally before target.
        duration_args = [] if target_hours == 0 else ["-t", str(target_secs)]
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", str(loop_mp4),   # infinite loop visual
            "-i", str(audio_mp3),
            *duration_args,
            "-map", "0:v:0",            # video from loop
            "-map", "1:a:0",            # audio from music MP3, NOT from silent loop
            "-shortest",                # stop at actual audio end (prevents silent tail)
            "-c:v", "libx264", "-preset", preset, "-crf", "20",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            str(out_mp4),
        ]
    else:
        # Visual only (no audio yet — placeholder)
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", str(loop_mp4),
            "-t", str(target_secs),
            "-c:v", "libx264", "-preset", preset, "-crf", "20",
            "-an",
            "-movflags", "+faststart",
            str(out_mp4),
        ]

    log.info(f"  Assembling {target_hours}h video (preset={preset}) → {out_mp4.name}…")
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=video_timeout)
    if r.returncode != 0 or not out_mp4.exists():
        log.error(f"  Assembly failed: {r.stderr[:300]}")
        return False
    size_gb = out_mp4.stat().st_size / 1024 / 1024 / 1024
    log.info(f"  ✓ {out_mp4.name} ({size_gb:.2f}GB)")
    return True


def make_track_list(program: dict) -> str:
    lines = []
    for t in program.get("tracks", []):
        composer = t.get("composer", "")
        piece = t.get("piece", "")
        dur = t.get("duration_sec", 0)
        m, s = divmod(dur, 60)
        lines.append(f"• {composer} — {piece} ({m}:{s:02d})")
    return "\n".join(lines)


def make_attribution(program: dict) -> str:
    composers = set(t.get("composer", "") for t in program.get("tracks", []))
    parts = []
    for c in sorted(composers):
        parts.append(f"Music by {c}. Performed by public domain recording (Musopen.org). "
                     f"Licensed under Public Domain / CC0.")
    return "\n".join(parts)


def write_meta(program: dict, hours: int, queue: Path, out_name: str):
    prog_id  = program["id"]
    track    = program.get("track", "calm_classics")
    if hours == 0:
        # Natural mode: derive duration label from actual output file
        out_path = queue / out_name
        actual_secs = _get_mp3_duration(out_path) if out_path.exists() else 0
        dur_label = _format_natural_duration(actual_secs) if actual_secs > 0 else "Complete"
    else:
        dur_label = HOURS_TO_LABEL.get(hours, f"{hours} Hours")
    # Priority: TITLES dict → title_en from YAML config → generic fallback
    _default_tpl = program.get("title_en", "Classical Music for Sleep ✨ {dur} | Classical Night Relax")
    title_tpl = TITLES.get(prog_id, _default_tpl)
    title    = title_tpl.replace("{duration}", dur_label).replace("{dur}", dur_label)

    composer_names = set(t.get("composer", "").split()[0] for t in program.get("tracks", []))
    composer_tag   = "".join(sorted(composer_names))

    desc_tpl = DESC_TEMPLATES.get(track, DESC_TEMPLATES["calm_classics"])
    desc = desc_tpl.format(
        program_desc=f"{dur_label} of {', '.join(sorted(composer_names))} for {track.replace('_', ' ')}.",
        track_list=make_track_list(program),
        attribution=make_attribution(program),
        composer_tag=composer_tag,
    )

    if hours == 0:
        extra_tags = ["classical night relax", "classical music", "sleep music", "relaxation",
                      "complete recording", dur_label.lower()]
    else:
        extra_tags = [dur_label.lower(), f"{hours} hour music", "classical night relax",
                      "classical music", "sleep music", "relaxation"]
    tags = (program.get("tags", []) + extra_tags)[:40]

    meta = {
        "title":          title,
        "description":    desc,
        "video_type":     program.get("video_type", "sleep_program"),
        "theme":          program["visual_theme"],
        "language":       "en",
        "is_short":       False,
        "status":         "public",
        "made_for_kids":  program.get("made_for_kids", False),
        "duration_hours": hours,
        "program_id":     prog_id,
        "tags":           tags,
    }

    stem = Path(out_name).stem
    meta_path = queue / f"meta_{stem}.yaml"
    with open(meta_path, "w") as f:
        yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    log.info(f"  Meta → {meta_path.name}")


def _apply_thumb_text(thumb_path: Path, program: dict, hours: int) -> None:
    """Apply beautiful text overlay (BebasNeue title + duration badge)."""
    try:
        import importlib.util, io
        spec = importlib.util.spec_from_file_location("tt", ROOT / "scripts" / "thumb_text.py")
        tt = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tt)
        from PIL import Image
        img  = Image.open(thumb_path).convert("RGB")
        text = tt.thumb_text_for_program(program)
        img  = tt.add_thumb_text(img, text, duration_hours=hours)
        img.save(str(thumb_path), "PNG")
        log.info(f"  Thumb overlay: {text!r}")
    except Exception as e:
        log.warning(f"  Thumb overlay skipped: {e}")


def generate_thumbnail(out_mp4: Path, program: dict, hours: int) -> bool:
    thumb_path = out_mp4.parent / f"thumb_{out_mp4.stem}.png"
    if thumb_path.exists():
        return True

    prog_id = program.get("id", "")

    # Prefer a cached KB image (already generated for the loop)
    kb_img = LOOPS_DIR / f"imgs_{prog_id}" / "img_00.jpg"
    if kb_img.exists():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("gat", ROOT / "scripts" / "generate_ai_thumbs.py")
            gat  = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(gat)
            thumb_path.write_bytes(gat.resize_to_720p(kb_img.read_bytes()))
            log.info(f"  Thumb from KB image → {thumb_path.name}")
            return True
        except Exception as e:
            log.warning(f"  KB thumb resize failed: {e}")

    # Fall back: generate new FLUX image from prompt
    if not TOGETHER_KEY_FILE.exists():
        return False
    prompt = PROGRAM_KB_PROMPTS.get(prog_id)
    if not prompt:
        theme = program.get("visual_theme", "moon_clouds")
        prompt_map = {
            "moon_clouds": "moonlit grand concert hall interior, ornate balconies, dramatic chandeliers, cinematic photography",
            "warm_waves":  "ocean waves at dusk with amber sunset glow, classical music relaxation, cinematic",
            "rain_window": "rainy window with warm candle glow inside, classical music study, cozy, cinematic",
        }
        prompt = prompt_map.get(theme, "elegant concert hall at night, classical music atmosphere, cinematic photography")
    # Do NOT append composer names — FLUX renders them as visible text in the image,
    # causing double text when _apply_thumb_text() adds the title overlay on top.
    prompt += ", no text, no letters, no words, no numbers"

    try:
        import requests as req
        api_key = TOGETHER_KEY_FILE.read_text().strip()
        resp = req.post(
            "https://api.together.xyz/v1/images/generations",
            headers={
                "Authorization": f"Bearer {api_key}",
                "User-Agent": "python-requests/2.31.0",
            },
            json={"model": "black-forest-labs/FLUX.1.1-pro",
                  "prompt": prompt, "width": 1280, "height": 704,
                  "steps": 4, "n": 1, "response_format": "b64_json"},
            timeout=60
        )
        resp.raise_for_status()
        raw = base64.b64decode(resp.json()["data"][0]["b64_json"])
        from PIL import Image as _PILImg
        import io as _io
        img_pil = _PILImg.open(_io.BytesIO(raw)).convert("RGB").resize((1280, 720), _PILImg.LANCZOS)
        buf = _io.BytesIO()
        img_pil.save(buf, "PNG", optimize=True)
        thumb_path.write_bytes(buf.getvalue())
        log.info(f"  Thumb → {thumb_path.name}")
        return True
    except Exception as e:
        log.warning(f"  Thumbnail skipped: {e}")
        return False


def cmd_render_loops_only(force: bool = False):
    """Render all 4 shared CSS loops without audio."""
    log.info("=== Rendering shared SleepClassicalLoop files ===")
    for theme in THEME_LOOP_SECS:
        render_shared_loop(theme, phase_offset=0.0, force=force)
    log.info("Done.")


def cmd_gen_visuals(force: bool = False):
    """Generate Ken Burns visual loops for all programs that have a prompt."""
    log.info("=== Generating Ken Burns visual loops ===")
    for prog_id in PROGRAM_KB_PROMPTS:
        log.info(f"\n--- {prog_id} ---")
        render_kenburns_loop(prog_id, force=force)
    log.info("\nDone — all Ken Burns loops generated.")


def cmd_generate_program(program_id: str, durations: list[int] | None,
                         regen_meta: bool, dry_run: bool, force: bool,
                         natural: bool = False):
    program = load_program(program_id)
    licenses_data = load_licenses()

    theme       = program["visual_theme"]
    track_type  = program.get("track", "calm_classics")
    queue       = QUEUE_EN if track_type == "kids_sleep" else QUEUE_CC

    if natural:
        # Natural mode: output once at the actual total track duration (no repeating)
        hours_list = [0]
        unique_min = compute_unique_minutes(program, load_licenses())
        log.info(f"=== Program: {program_id} | theme: {theme} | queue: {queue.name} ===")
        log.info(f"  Natural mode: {unique_min:.0f}min unique content → single output, no repeat")
    else:
        requested   = durations or program.get("durations_hours", [1, 3])
        licenses_data_check = load_licenses()
        unique_min  = compute_unique_minutes(program, licenses_data_check)
        max_repeat  = program.get("max_repeat", 2.0)
        hours_list  = select_durations(requested, unique_min, max_repeat, program_id)
        log.info(f"=== Program: {program_id} | theme: {theme} | queue: {queue.name} ===")
        log.info(f"  Unique content: {unique_min:.0f}min | max_repeat: ×{max_repeat} "
                 f"| durations: {hours_list}h")

    loop_mp4 = None
    audio_mp3 = None

    if not regen_meta and not dry_run:
        # AI image + Ken Burns loop — CSS fallback DISABLED (produces low-quality blobs)
        loop_mp4 = render_kenburns_loop(program_id, force=force)
        if loop_mp4 is None:
            log.error(f"  No Ken Burns loop available for {program_id} — run --gen-visuals first. Aborting.")
            return

        # Natural mode: build audio without target_secs (no truncation, no repeating)
        # Standard mode: build audio long enough for the longest requested duration
        max_hours = 0 if natural else (max(hours_list) if hours_list else 1)
        tmp_dir = ROOT / "output" / f"_tmp_{program_id}"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        audio_mp3 = build_audio_track(program, licenses_data, tmp_dir,
                                      target_secs=max_hours * 3600)
    elif not regen_meta and dry_run:
        # In dry-run: just verify which tracks are found, skip rendering
        log.info("  [dry-run] Checking track availability:")
        for t in program.get("tracks", []):
            p = find_track_file(t["id"], licenses_data,
                                composer=t.get("composer", ""),
                                piece=t.get("piece", ""))
            status = f"✓ {p.name}" if p else "✗ NOT FOUND"
            log.info(f"    {t['id']}: {status}")

    queue.mkdir(parents=True, exist_ok=True)
    generated = 0

    for hours in hours_list:
        dur_label = HOURS_TO_LABEL.get(hours, f"{hours}h")
        out_name  = f"{program_id}_natural_{DATE_STR}.mp4" if hours == 0 else f"{program_id}_{hours}h_{DATE_STR}.mp4"
        out_mp4   = queue / out_name

        if not regen_meta and not dry_run and not out_mp4.exists():
            if loop_mp4 is None:
                log.error("No loop MP4 available — run --render-loops-only first")
                continue
            ok = assemble_video(loop_mp4, audio_mp3, hours, out_mp4)
            if not ok:
                continue

        if out_mp4.exists() or dry_run or regen_meta:
            write_meta(program, hours, queue, out_name)
            if not dry_run:
                generate_thumbnail(out_mp4 if out_mp4.exists() else queue / out_name,
                                   program, hours)
            generated += 1

    log.info(f"Done: {generated}/{len(hours_list)} for {program_id}")

    if generated > 0 and not dry_run:
        queue_key = "id" if queue == QUEUE_CC else "en"
        log.info(f"  → Starting background pre-localization for queue={queue_key}...")
        log_path = ROOT / "logs" / "prepare_queue.log"
        subprocess.Popen(
            ["python3", str(ROOT / "scripts" / "prepare_queue.py"),
             "--queue", queue_key, "--limit", str(generated)],
            stdout=open(log_path, "a"),
            stderr=subprocess.STDOUT,
        )


MAX_QUEUE_LONG = 10   # skip generation if queue_id has this many long videos


def _queue_long_count() -> int:
    return len([
        p for p in QUEUE_CC.glob("*.mp4")
        if not any(x in p.name for x in ("_short_", "kw_short", "visual_short"))
    ])


def main():
    check_disk_space()
    parser = argparse.ArgumentParser(description="Generate Classical Night Relax sleep programs")
    parser.add_argument("--render-loops-only", action="store_true",
                        help="Only render the 4 shared CSS loop MP4s (no audio, no assembly)")
    parser.add_argument("--gen-visuals", action="store_true",
                        help="Generate Ken Burns visual loops for all programs (FLUX images + FFmpeg)")
    parser.add_argument("--program",    help="Program ID (e.g. sleep_chopin_01)")
    parser.add_argument("--durations",  type=int, nargs="+",
                        help="Hours to generate (e.g. --durations 1 3). Default: from config")
    parser.add_argument("--list-programs", action="store_true", help="List available programs")
    parser.add_argument("--regen-meta", action="store_true", help="Regenerate meta+thumb only")
    parser.add_argument("--dry-run",    action="store_true")
    parser.add_argument("--force",      action="store_true", help="Re-render even if exists")
    parser.add_argument("--natural",    action="store_true",
                        help="Output at natural track length — no padding, no repeating audio")
    args = parser.parse_args()

    if args.list_programs:
        print("Available programs:")
        for p in sorted(PROGRAMS.glob("*.yaml")):
            prog = yaml.safe_load(p.read_text())
            print(f"  {prog['id']:30s} track={prog.get('track','?')} theme={prog.get('visual_theme','?')}")
        return

    if args.render_loops_only:
        cmd_render_loops_only(force=args.force)
        return

    if args.gen_visuals:
        if not args.force:
            count = _queue_long_count()
            if count >= MAX_QUEUE_LONG:
                print(f"Queue has {count} long videos (≥{MAX_QUEUE_LONG}) — skipping generation to save disk space.")
                return
        cmd_gen_visuals(force=args.force)
        return

    if args.program:
        cmd_generate_program(
            program_id=args.program,
            durations=args.durations,
            regen_meta=args.regen_meta,
            dry_run=args.dry_run,
            force=args.force,
            natural=args.natural,
        )
        return

    parser.print_help()


if __name__ == "__main__":
    main()
