#!/usr/bin/env python3
"""
generate_song_compilation.py — Children's song compilations from Suno AI tracks.

Concatenates 10-18 Suno songs into a 25-min video.
Audio: FFmpeg concat (loops playlist until 1500 sec, fades last 30 sec).
Visual: DanceSpriteLong bear animation with compiled audio.

Usage:
  python3 scripts/generate_song_compilation.py --type upbeat --lang en
  python3 scripts/generate_song_compilation.py --type lullaby --lang both
  python3 scripts/generate_song_compilation.py --type upbeat --lang ar
  python3 scripts/generate_song_compilation.py --list
  python3 scripts/generate_song_compilation.py --dry-run --type upbeat --lang en
"""
import argparse, base64, json, shutil, subprocess, sys, time
from datetime import datetime
from pathlib import Path

ROOT      = Path(__file__).resolve().parent.parent
REMOTION  = ROOT / "remotion"
QUEUE_EN  = ROOT / "output" / "queue"
QUEUE_AR  = ROOT / "output" / "queue_ar"
SUNO_DIR  = ROOT / "assets" / "audio" / "suno"
MUSIC_DIR = REMOTION / "public" / "music"
TMP_DIR   = ROOT / "output" / "tmp_compilation"

TOGETHER_KEY_FILE = ROOT / "credentials" / "together_api_key.txt"
TOGETHER_URL      = "https://api.together.xyz/v1/images/generations"
TOGETHER_MODEL    = "black-forest-labs/FLUX.1-schnell"

DATE_STR   = datetime.now().strftime("%Y%m%d")
TARGET_SEC = 1500  # 25 minutes
GAP_SEC    = 3     # silence between songs

EN_SONGS_UPBEAT = [
    "Animal Parade v4.mp3",
    "Count With Me v4.mp3",
    "Dancing Bears v2.mp3",
    "Dinosaur Stomp v2.mp3",
    "Down on the Farm v2.mp3",
    "Fruit Salad Song v2.mp3",
    "Head Shoulders Knees and Toes v2.mp3",
    "Hello World v2.mp3",
    "How Do You Feel Today_ v2.mp3",
    "Number Train v2.mp3",
    "Rainbow Colors v2.mp3",
    "Shapes Everywhere v2.mp3",
    "Sunny Day Ukulele v2.mp3",
    "The Bouncy Bunny March.mp3",
    "What's the Weather Today_ v2.mp3",
    "Wheels and Wings v2.mp3",
    "Clean Up Time v2.mp3",
    "Seven Days of Fun v2.mp3",
]

EN_SONGS_LULLABY = [
    "Baby Bear's Den v2.mp3",
    "Baby Bear's Forest Lullaby v2.mp3",
    "Dream On Little One v2.mp3",
    "Moon and Stars v2.mp3",
    "Moonlit Paws v2.mp3",
    "Rainbow Cradle v2.mp3",
    "Bear by the Window.mp3",
    "Honey Fields.mp3",
    "Firefly Night Lullaby v2.mp3",
    "Little Cloud Lullaby v2.mp3",
    "Autumn Leaves Lullaby v2.mp3",
    "Mama Bear's Song v2.mp3",
    "Music Box Lullaby v2.mp3",
    "Snowflakes Sing v2.mp3",
    "Ocean Waves Lullaby v2.mp3",
    "Forest Rain Lullaby v2.mp3",
    "Spring Morning Lullaby.mp3",
]

AR_SONGS_UPBEAT = [
    "النجمة الصغيرة.mp3",
    "أصوات الحيوانات.mp3",
    "ألوان الطبيعة.mp3",
    "طريق الفرح الصغير.mp3",
    "نعدّ مع بعض.mp3",
    "القمر الجميل.mp3",
]

AR_SONGS_LULLABY = [
    "هدوء الليل.mp3",
    "القمر الجميل.mp3",
    "النجمة الصغيرة.mp3",
    "طريق الفرح الصغير.mp3",
    "نعدّ مع بعض.mp3",
    "ألوان الطبيعة.mp3",
]

PLAYLISTS = {
    "upbeat": {
        "songs": {"en": EN_SONGS_UPBEAT, "ar": AR_SONGS_UPBEAT},
        "name":  {"en": "Happy Songs for Kids", "ar": "أغاني سعيدة للأطفال"},
        "desc_en": (
            "25 minutes of happy, upbeat songs for babies and toddlers! "
            "18 fun educational songs about animals, numbers, colors, shapes, emotions, and more. "
            "Original AI-generated music, perfect for dancing, learning, and playtime.\n\n"
            "Includes: Animal Parade, Count With Me, Dancing Bears, Dinosaur Stomp, "
            "Rainbow Colors, Shapes Everywhere, and more!\n\n"
            "Perfect for kids ages 1–5. No talking, just music and fun!\n\n"
            "🎵 Original music by Happy Bear Kids (AI-generated, © 2026)\n"
            "🔔 Subscribe → @HappyBearKids1\n\n"
            "#HappySongs #KidsSongs #ToddlerMusic #ChildrensSongs #HappyBearKids "
            "#BabyMusic #KidsPlaylist #EducationalSongs #SongsForKids #ToddlerPlaylist"
        ),
        "desc_ar": (
            "٢٥ دقيقة من الأغاني السعيدة للأطفال! أغاني تعليمية ممتعة عن الحيوانات والأرقام "
            "والألوان والأشكال والمشاعر وأكثر. موسيقى أصلية مولودة بالذكاء الاصطناعي، "
            "مثالية للرقص والتعلم واللعب.\n\n"
            "🎵 موسيقى أصلية من هابي بير كيدز\n"
            "🔔 اشتركوا → @happybearkidsar\n\n"
            "#أغاني_أطفال #موسيقى_للأطفال #هابي_بير_كيدز #أغاني_تعليمية #ترفيه_أطفال"
        ),
        "bgColor":    "#080014",
        "bgColorEnd": "#040008",
        "accentColor":"#FFD700",
        "sprites": [
            {"path": "characters/bear_happy_3d.png", "size": 460, "posX": 0.50, "posY": 0.44, "seed": 1},
            {"path": "objects/star_3d.png",           "size": 175, "posX": 0.15, "posY": 0.28, "seed": 2},
            {"path": "objects/sun_3d.png",            "size": 185, "posX": 0.82, "posY": 0.30, "seed": 3},
            {"path": "objects/star_3d.png",           "size": 150, "posX": 0.20, "posY": 0.68, "seed": 4},
            {"path": "objects/rainbow_3d.png",        "size": 165, "posX": 0.78, "posY": 0.68, "seed": 5},
        ],
        "blocks": [
            {"startSec": 0,    "endSec": 120,  "motion": "FADEIN",  "amplitude": 60, "wobble": True},
            {"startSec": 120,  "endSec": 600,  "motion": "BOB",     "period": 3.0,   "amplitude": 50, "wobble": True},
            {"startSec": 600,  "endSec": 1100, "motion": "BOUNCE",  "period": 2.5,   "amplitude": 70, "wobble": True},
            {"startSec": 1100, "endSec": 1500, "motion": "SWAY",    "period": 4.0,   "amplitude": 45, "wobble": True},
        ],
        "thumb_en": (
            "cute 3D Pixar bear dancing joyfully surrounded by colorful musical notes and stars, "
            "bright cheerful background, children's animation style, vibrant colors, "
            "text: 'Happy Songs for Kids', 4K"
        ),
        "thumb_ar": (
            "cute 3D Pixar bear dancing joyfully surrounded by colorful musical notes and stars, "
            "bright cheerful background, children's animation style, vibrant colors, 4K, "
            "no text, no letters, no words, no numbers"
        ),
    },
    "lullaby": {
        "songs": {"en": EN_SONGS_LULLABY, "ar": AR_SONGS_LULLABY},
        "name":  {"en": "Lullaby Songs for Babies", "ar": "أغاني النوم للأطفال"},
        "desc_en": (
            "25 minutes of gentle lullabies and soothing songs to help your baby drift off to sleep. "
            "17 original lullaby songs featuring soft melodies, gentle rhythms, and dreamy soundscapes. "
            "Perfect for bedtime, nap time, and quiet moments.\n\n"
            "Includes: Baby Bear's Den, Dream On Little One, Moon and Stars, Rainbow Cradle, "
            "Moonlit Paws, and more!\n\n"
            "Designed for babies 0–3 years. Safe, gentle, and calming.\n\n"
            "🎵 Original lullabies by Happy Bear Kids (AI-generated, © 2026)\n"
            "🔔 Subscribe → @HappyBearKids1\n\n"
            "#Lullaby #BabyLullaby #BedtimeSongs #SleepMusic #HappyBearKids "
            "#BabySleep #ToddlerSleep #CalmingMusic #NightNight #SleepBaby"
        ),
        "desc_ar": (
            "٢٥ دقيقة من الأغاني الهادئة لتساعد طفلك على النوم. ألحان ناعمة ومريحة "
            "مثالية لوقت النوم والراحة.\n\n"
            "🎵 موسيقى أصلية من هابي بير كيدز\n"
            "🔔 اشتركوا → @happybearkidsar\n\n"
            "#أغاني_النوم #تهويدة #نوم_الأطفال #هابي_بير_كيدز #موسيقى_هادئة"
        ),
        "bgColor":    "#010510",
        "bgColorEnd": "#010308",
        "accentColor":"#90CAF9",
        "sprites": [
            {"path": "characters/bear_happy_3d.png", "size": 460, "posX": 0.50, "posY": 0.44, "seed": 1},
            {"path": "objects/star_3d.png",           "size": 165, "posX": 0.18, "posY": 0.28, "seed": 2},
            {"path": "objects/star_3d.png",           "size": 150, "posX": 0.80, "posY": 0.30, "seed": 3},
            {"path": "objects/star_3d.png",           "size": 140, "posX": 0.22, "posY": 0.68, "seed": 4},
            {"path": "objects/star_3d.png",           "size": 130, "posX": 0.78, "posY": 0.68, "seed": 5},
        ],
        "blocks": [
            {"startSec": 0,    "endSec": 200,  "motion": "FADEIN",  "amplitude": 40, "wobble": True},
            {"startSec": 200,  "endSec": 700,  "motion": "DRIFT",   "period": 12.0,  "amplitude": 80, "wobble": True},
            {"startSec": 700,  "endSec": 1200, "motion": "BOB",     "period": 6.0,   "amplitude": 40, "wobble": True},
            {"startSec": 1200, "endSec": 1500, "motion": "DRIFT",   "period": 14.0,  "amplitude": 60, "wobble": True},
        ],
        "thumb_en": (
            "cute 3D Pixar bear sleeping peacefully under a starry night sky, "
            "soft glowing stars and moon, dreamy pastel colors, children's animation, "
            "cozy and calm, text: 'Lullaby Songs for Babies', 4K"
        ),
        "thumb_ar": (
            "cute 3D Pixar bear sleeping peacefully under a starry night sky, "
            "soft glowing stars and moon, dreamy pastel colors, children's animation, "
            "cozy and calm, 4K, no text, no letters, no words, no numbers"
        ),
    },
}


def get_duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(path)],
        capture_output=True, text=True
    )
    return float(json.loads(r.stdout)["format"]["duration"])


def compile_audio(songs: list[str], lang: str, out_path: Path, dry_run: bool) -> bool:
    """FFmpeg-concat Suno songs (looping playlist) until TARGET_SEC, with fade-out."""
    available = [s for s in songs if (SUNO_DIR / s).exists()]
    missing   = [s for s in songs if not (SUNO_DIR / s).exists()]
    if missing:
        print(f"  ⚠ Missing songs: {missing}")
    if not available:
        print("  ✗ No songs available"); return False

    # Calculate total duration of one playlist pass
    total = sum(get_duration(SUNO_DIR / s) for s in available)
    total += GAP_SEC * (len(available) - 1)  # gaps between songs
    passes_needed = max(2, int(TARGET_SEC / total) + 1)

    print(f"  Playlist: {len(available)} songs × {passes_needed} passes "
          f"= {int(total * passes_needed // 60)}:{int(total * passes_needed % 60):02d} → trim to 25 min")

    if dry_run:
        print(f"  [DRY RUN] would compile {out_path.name}")
        return True

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    silence_path = TMP_DIR / "silence_3s.mp3"

    # Generate 3-sec silence file
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-t", "3", "-c:a", "libmp3lame", "-b:a", "128k", str(silence_path)
    ], capture_output=True)

    # Build concat list (N passes)
    playlist_txt = TMP_DIR / f"concat_{lang}.txt"
    lines = []
    for _ in range(passes_needed):
        for i, song in enumerate(available):
            lines.append(f"file '{(SUNO_DIR / song).resolve()}'")
            if i < len(available) - 1:
                lines.append(f"file '{silence_path.resolve()}'")
    playlist_txt.write_text("\n".join(lines))

    # FFmpeg concat + trim + fade out
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(playlist_txt),
        "-t", str(TARGET_SEC),
        "-af", f"afade=t=out:st={TARGET_SEC - 30}:d=30",
        "-c:a", "libmp3lame", "-b:a", "128k",
        str(out_path),
    ]
    result = subprocess.run(cmd, capture_output=False, timeout=300)
    return result.returncode == 0


def render_video(ptype: str, lang: str, music_file: str, out_mp4: Path, dry_run: bool) -> bool:
    """Render DanceSpriteLong with compiled audio track."""
    p = PLAYLISTS[ptype]
    props = {
        "bgColor":    p["bgColor"],
        "bgColorEnd": p["bgColorEnd"],
        "accentColor":p["accentColor"],
        "musicFile":  music_file,
        "volume":     0.90,
        "bgEffect":   "sparkles",
        "sprites":    p["sprites"],
        "blocks":     p["blocks"],
    }
    cmd = [
        "npx", "remotion", "render", "DanceSpriteLong",
        f"--props={json.dumps(props)}",
        f"--output={str(out_mp4)}",
    ]
    print(f"  Render: {out_mp4.name}")
    if dry_run:
        print(f"  [DRY RUN] would render DanceSpriteLong"); return True
    result = subprocess.run(cmd, cwd=str(REMOTION), capture_output=False, timeout=3600)
    return result.returncode == 0


def generate_thumbnail(ptype: str, lang: str, out_png: Path, dry_run: bool) -> bool:
    """Generate FLUX thumbnail via Together.ai."""
    p = PLAYLISTS[ptype]
    prompt = p["thumb_ar"] if lang == "ar" else p["thumb_en"]

    if dry_run:
        print(f"  [DRY RUN] would generate thumbnail"); return True
    if not TOGETHER_KEY_FILE.exists():
        print(f"  ✗ No Together.ai key"); return False

    key = TOGETHER_KEY_FILE.read_text().strip()
    import urllib.request
    payload = json.dumps({
        "model": TOGETHER_MODEL,
        "prompt": prompt,
        "width": 1280, "height": 720,
        "steps": 4, "n": 1,
        "response_format": "b64_json",
    }).encode()
    req = urllib.request.Request(
        TOGETHER_URL,
        data=payload,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
        img_b64 = data["data"][0]["b64_json"]
        out_png.write_bytes(base64.b64decode(img_b64))
        print(f"  Thumbnail: {out_png.name} ({out_png.stat().st_size // 1024}KB)")
        return True
    except Exception as e:
        print(f"  ✗ Thumbnail error: {e}")
        return False


def make_meta(ptype: str, lang: str, songs: list[str]) -> dict:
    p = PLAYLISTS[ptype]
    queue = QUEUE_AR if lang == "ar" else QUEUE_EN
    name  = p["name"][lang]
    desc  = p["desc_ar"] if lang == "ar" else p["desc_en"]
    song_count = len([s for s in songs if (SUNO_DIR / s).exists()])
    if lang == "en":
        title = f"{name} | {song_count} Songs | 25 Min | Happy Bear Kids"
    else:
        title = f"{name} | {song_count} أغاني | ٢٥ دقيقة | هابي بير كيدز"
    tags_en = [
        "kids songs", "children's songs", "happy bear kids", "baby music",
        "toddler songs", "educational songs", "songs for kids", "kids music",
        ptype, "25 minutes", "song compilation",
    ]
    tags_ar = [
        "أغاني أطفال", "موسيقى للأطفال", "هابي بير كيدز", "أغاني تعليمية",
        ptype, "أغاني للأطفال الصغار",
    ]
    return {
        "title":         title,
        "description":   desc,
        "tags":          tags_ar if lang == "ar" else tags_en,
        "video_type":    "song_compilation",
        "language":      lang,
        "is_short":      False,
        "status":        "public",
        "made_for_kids": True,
        "ai_generated":  True,
    }


def process(ptype: str, lang: str, dry_run: bool, force: bool):
    import yaml
    p = PLAYLISTS[ptype]
    songs = p["songs"][lang]
    queue = QUEUE_AR if lang == "ar" else QUEUE_EN

    slug      = f"compilation_{ptype}_{lang}_{DATE_STR}"
    out_mp4   = queue / f"{slug}.mp4"
    meta_path = queue / f"meta_{slug}.yaml"
    thumb_path= queue / f"thumb_{slug}.png"
    music_key = f"comp_{ptype}_{lang}_{DATE_STR}.mp3"
    music_tmp = MUSIC_DIR / music_key
    audio_tmp = TMP_DIR / music_key

    if out_mp4.exists() and not force:
        print(f"  Already exists: {out_mp4.name} (use --force to redo)")
        return

    print(f"\n=== Compilation: {ptype}/{lang} ===")

    # 1. Compile audio
    print("1. Compiling audio...")
    if not compile_audio(songs, lang, audio_tmp, dry_run):
        print("✗ Audio compile failed"); return

    # 2. Copy to Remotion public/music/
    if not dry_run:
        shutil.copy2(audio_tmp, music_tmp)
        print(f"  Copied to remotion/public/music/{music_key}")

    # 3. Render video
    print("2. Rendering video...")
    if not render_video(ptype, lang, music_key, out_mp4, dry_run):
        print("✗ Render failed"); return

    # 4. Thumbnail
    print("3. Generating thumbnail...")
    generate_thumbnail(ptype, lang, thumb_path, dry_run)

    # 5. Meta
    print("4. Writing meta...")
    meta = make_meta(ptype, lang, songs)
    if not dry_run:
        meta_path.write_text(yaml.dump(meta, allow_unicode=True, default_flow_style=False))
        print(f"  Meta: {meta_path.name}")

    # 6. Cleanup
    if not dry_run:
        if music_tmp.exists():
            music_tmp.unlink()
        print(f"\n✓ Done: {out_mp4.name}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--type",   choices=["upbeat", "lullaby"], help="Compilation type")
    ap.add_argument("--lang",   default="en", choices=["en", "ar", "both"])
    ap.add_argument("--dry-run",action="store_true")
    ap.add_argument("--force",  action="store_true")
    ap.add_argument("--list",   action="store_true")
    args = ap.parse_args()

    if args.list:
        for ptype, p in PLAYLISTS.items():
            for lang, songs in p["songs"].items():
                available = [s for s in songs if (SUNO_DIR / s).exists()]
                total = sum(get_duration(SUNO_DIR / s) for s in available)
                print(f"{ptype}/{lang}: {len(available)}/{len(songs)} songs, "
                      f"{int(total//60)}:{int(total%60):02d}")
        return

    if not args.type:
        ap.print_help(); sys.exit(1)

    langs = ["en", "ar"] if args.lang == "both" else [args.lang]
    for lang in langs:
        process(args.type, lang, args.dry_run, args.force)


if __name__ == "__main__":
    main()
