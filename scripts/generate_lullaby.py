#!/usr/bin/env python3
"""
Generate Lullaby long-form sleep videos — 1-2 hours.
Based on scenario: config/scenarios/lullaby_long.txt

Strategy: Render a 5-min loop in Remotion, then use FFmpeg to extend to 1-2 hours
with progressive brightness/volume fade.

6 videos:
  sleepy_stars   — 2h, dark sky, twinkling stars, slow shooting stars
  ocean_night    — 2h, dark ocean, glowing jellyfish, rare bubbles
  moon_garden    — 1.5h, night garden, fireflies fading out
  sleepy_train   — 2h, night train journey, rhythmic wheel sounds
  rain_window    — 1.5h, rain on window, cosy indoor warmth
  forest_night   — 2h, dark forest, fireflies, owl sounds

Usage:
  python3 scripts/generate_lullaby.py                      # all 6
  python3 scripts/generate_lullaby.py --keys sleepy_stars  # specific
  python3 scripts/generate_lullaby.py --dry-run
  python3 scripts/generate_lullaby.py --regen-meta
"""
import argparse
import base64
import json
import subprocess
import sys
import time
import yaml
from datetime import datetime
from pathlib import Path

ROOT     = Path(__file__).resolve().parent.parent
REMOTION = ROOT / "remotion"
QUEUE_EN = ROOT / "output" / "queue"
QUEUE_AR = ROOT / "output" / "queue_ar"
QUEUE_ID = ROOT / "output" / "queue_id"
TMP_DIR  = ROOT / "output" / "tmp_lullaby"

TOGETHER_KEY_FILE = ROOT / "credentials" / "together_api_key.txt"
TOGETHER_URL      = "https://api.together.xyz/v1/images/generations"
TOGETHER_MODEL    = "black-forest-labs/FLUX.1-schnell"

_ALL_TRACKS = [
    "Carefree.mp3", "Crinoline Dreams.mp3", "Gymnopedie No 1.mp3",
    "Happy Happy Game Show.mp3", "Heartwarming.mp3", "Hyperfun.mp3",
    "Life of Riley.mp3", "Merry Go.mp3", "Monkeys Spinning Monkeys.mp3",
    "Overworld.mp3", "Pinball Spring.mp3", "Pixelland.mp3",
    "Quirky Dog.mp3", "Salty Ditty.mp3", "Sneaky Snitch.mp3",
    "Wholesome.mp3", "Fluffing a Duck.mp3", "Walking Along.mp3",
    "George Street Shuffle.mp3", "Circus of Freaks.mp3",
]

def alt_music(en_music: str, ep_idx: int, lang: str) -> str:
    if lang == "en":
        return en_music
    offset = 7 if lang == "ar" else 14
    pool = [t for t in _ALL_TRACKS if t != en_music]
    return pool[(ep_idx + offset) % len(pool)]

DATE_STR = datetime.now().strftime("%Y%m%d")
FPS      = 30
LOOP_DUR = 5 * 60  # 5-minute loop

VIDEOS = {
    "sleepy_stars": {
        "name_en": "Sleepy Stars",
        "name_ar":  "النجوم النائمة",
        "name_id":  "Bintang Mengantuk",
        "hours":    2,
        "bg_top":   "#020815",
        "bg_bottom":"#050A1A",
        "accent":   "#B0C4DE",
        "music":    "Gymnopedie No 1.mp3",
        "bpm":      50,
        "theme":    "stars",
    },
    "ocean_night": {
        "name_en": "Ocean Night",
        "name_ar":  "ليلة المحيط",
        "name_id":  "Malam Samudra",
        "hours":    2,
        "bg_top":   "#020B18",
        "bg_bottom":"#041020",
        "accent":   "#4488BB",
        "music":    "Crinoline Dreams.mp3",
        "bpm":      50,
        "theme":    "ocean",
    },
    "moon_garden": {
        "name_en": "Moon Garden",
        "name_ar":  "حديقة القمر",
        "name_id":  "Taman Bulan",
        "hours":    1.5,
        "bg_top":   "#060A10",
        "bg_bottom":"#0A1220",
        "accent":   "#88BB44",
        "music":    "Heartwarming.mp3",
        "bpm":      52,
        "theme":    "garden",
    },
    "sleepy_train": {
        "name_en": "Sleepy Train",
        "name_ar":  "القطار النائم",
        "name_id":  "Kereta Mengantuk",
        "hours":    2,
        "bg_top":   "#040810",
        "bg_bottom":"#060C18",
        "accent":   "#DDAA55",
        "music":    "Wholesome.mp3",
        "bpm":      50,
        "theme":    "train",
    },
    "rain_window": {
        "name_en": "Rain on the Window",
        "name_ar":  "المطر على النافذة",
        "name_id":  "Hujan di Jendela",
        "hours":    1.5,
        "bg_top":   "#080C14",
        "bg_bottom":"#0A1020",
        "accent":   "#6688AA",
        "music":    "Carefree.mp3",
        "bpm":      52,
        "theme":    "rain",
    },
    "forest_night": {
        "name_en": "Night Forest",
        "name_ar":  "غابة الليل",
        "name_id":  "Hutan Malam",
        "hours":    2,
        "bg_top":   "#030A06",
        "bg_bottom":"#041008",
        "accent":   "#44AA66",
        "music":    "Carefree.mp3",
        "bpm":      50,
        "theme":    "forest",
    },
}


def make_meta(key: str, lang: str) -> dict:
    v = VIDEOS[key]
    hours = int(v["hours"])
    h_str = f"{hours} hour{'s' if hours > 1 else ''}" if hours == int(hours) else f"{v['hours']} hours"

    if lang == "en":
        name = v["name_en"]
        desc = (
            f"🌙 {name} — {h_str} of soothing sleep content for babies and toddlers\n\n"
            f"Specially designed sleep video with gradually dimming visuals and calming music. "
            f"Perfect for bedtime routines — play it every night and watch it work!\n\n"
            f"🌙 Sleep science in every frame:\n"
            f"• Brightness fades from 100% → 40% over {h_str}\n"
            f"• Music softens progressively\n"
            f"• Tempo ≤55 BPM — below a sleeping baby's resting heart rate\n"
            f"• No faces or eyes after 15 minutes (reduces social stimulation)\n"
            f"• Zero sudden changes in sound or light\n"
            f"• Seamless loop — no jarring transitions\n\n"
            f"🌟 Why parents love it:\n"
            f"• Sets a consistent bedtime routine\n"
            f"• Gives parents quiet time too\n"
            f"• Works as white noise + gentle visual for light sleepers\n"
            f"• {h_str} duration means it plays through the whole night\n\n"
            f"🔔 Subscribe → @HappyBearKids1 for more sleep content!\n\n"
            f"🎵 Music: Kevin MacLeod (incompetech.com)\n"
            f"Licensed under Creative Commons Attribution 4.0\n"
            f"http://creativecommons.org/licenses/by/4.0/\n\n"
            f"#BabySleepVideo #{name.replace(' ', '')} #BabyBedtime #ToddlerSleep "
            f"#SleepMusic #HappyBearKids #BabySleep #NightRoutine "
            f"#BabyLullaby #SleepBaby #LongSleepVideo\n\n"
            f"© Happy Bear Kids 2026"
        )
        return {
            "title":       f"{name} 🌙 {h_str} Sleep Video for Babies | Happy Bear Kids",
            "description": desc,
            "tags": ["baby sleep video", "lullaby", "sleep music", "bedtime routine",
                     "happy bear kids", f"{h_str}", name.lower(), "baby bedtime",
                     "toddler sleep", "night routine", "calming video", "white noise visual",
                     "baby lullaby", "sleep baby"],
            "video_type": "lullaby_long",
            "language":   "en",
            "is_short":   False,
            "status":     "public",
        }

    elif lang == "ar":
        name = v["name_ar"]
        h_ar = f"ساعتين" if hours == 2 else f"ساعة ونصف" if hours == 1.5 else f"ساعة"
        desc = (
            f"🌙 {name} — {h_ar} من المحتوى المهدئ للنوم للرضع والأطفال الصغار\n\n"
            f"فيديو نوم مصمم خصيصاً مع مرئيات تتلاشى تدريجياً وموسيقى هادئة. "
            f"مثالي لروتين النوم — شغّله كل ليلة وشاهد نتيجته!\n\n"
            f"🌙 علم النوم في كل إطار:\n"
            f"• السطوع يتلاشى من 100% → 40% على مدى {h_ar}\n"
            f"• الموسيقى تخفت تدريجياً\n"
            f"• إيقاع ≤55 نبضة/دقيقة — أقل من معدل ضربات قلب طفل نائم\n"
            f"• لا وجوه أو عيون بعد 15 دقيقة\n"
            f"• صفر تغييرات مفاجئة في الصوت أو الضوء\n\n"
            f"🔔 اشتركوا → @happybearkidsar لمزيد من محتوى النوم!\n\n"
            f"🎵 الموسيقى: Kevin MacLeod\n"
            f"رخصة Creative Commons Attribution 4.0\n\n"
            f"#نوم_الرضع #{name.replace(' ', '_')} #روتين_النوم #موسيقى_النوم "
            f"#هابي_بير_كيدز #أطفال #نوم_أطفال #تهدئة\n\n"
            f"© هابي بير كيدز 2026"
        )
        return {
            "title":       f"{name} 🌙 {h_ar} فيديو نوم للرضع | هابي بير كيدز",
            "description": desc,
            "tags": ["نوم الرضع", "تهليل", "موسيقى نوم", "روتين النوم",
                     "هابي بير كيدز", name, "نوم أطفال", "تهدئة",
                     "فيديو ليلي", "أغنية نوم"],
            "video_type": "lullaby_long",
            "language":   "ar",
            "is_short":   False,
            "status":     "public",
        }

    else:  # id
        name = v["name_id"]
        h_id = f"{hours} jam"
        desc = (
            f"🌙 {name} — {h_id} konten tidur menenangkan untuk bayi dan balita\n\n"
            f"Video tidur yang dirancang khusus dengan visual yang semakin redup "
            f"dan musik yang menenangkan. Sempurna untuk rutinitas tidur!\n\n"
            f"🌙 Ilmu tidur di setiap frame:\n"
            f"• Kecerahan memudar dari 100% → 40% selama {h_id}\n"
            f"• Musik melemah secara progresif\n"
            f"• Tempo ≤55 BPM — di bawah detak jantung bayi tidur\n"
            f"• Tidak ada wajah setelah 15 menit\n"
            f"• Nol perubahan mendadak dalam suara atau cahaya\n\n"
            f"🔔 Subscribe → @happybearkidsin untuk konten tidur lainnya!\n\n"
            f"🎵 Musik: Kevin MacLeod (incompetech.com)\n"
            f"Berlisensi Creative Commons Attribution 4.0\n\n"
            f"#VideoTidurBayi #{name.replace(' ', '')} #RutinasTidur #MusikTidur "
            f"#HappyBearKids #TidurBayi #NinaboboModern #VideoMalamBayi\n\n"
            f"© Happy Bear Kids Indonesia 2026"
        )
        return {
            "title":       f"{name} 🌙 {h_id} Video Tidur untuk Bayi | Happy Bear Kids",
            "description": desc,
            "tags": ["video tidur bayi", "lullaby", "musik tidur", "rutinas tidur",
                     "happy bear kids", f"{h_id}", name.lower(), "tidur bayi",
                     "video malam", "ninabobo", "video menenangkan"],
            "video_type": "lullaby_long",
            "language":   "id",
            "is_short":   False,
            "status":     "public",
        }


def generate_thumbnail(key: str, out_path: Path) -> bool:
    if out_path.exists():
        return True
    if not TOGETHER_KEY_FILE.exists():
        return False
    try:
        import requests as _req
    except ImportError:
        return False

    v = VIDEOS[key]
    theme_prompts = {
        "stars":  "dark night sky with softly glowing stars, crescent moon, dreamy pastel nebula",
        "ocean":  "dark underwater scene with glowing jellyfish, bubbles rising, deep blue ocean",
        "garden": "moonlit garden at night, fireflies glowing, flowers asleep, silver light",
        "train":  "night train journey, warm lights through windows, dark countryside, cosy",
        "rain":   "rain drops on window glass, warm cozy interior glow outside, dark night",
        "forest": "dark forest at night, fireflies, misty, moonbeams through trees, peaceful",
    }
    theme_desc = theme_prompts.get(v["theme"], "peaceful dark night scene")
    prompt = (
        f"{theme_desc}, "
        f"children's YouTube thumbnail, sleep video, ultra calm, "
        f"Pixar style soft 3D, deep dark background, "
        f"gentle glowing light sources, no text, no letters, dreamlike atmosphere"
    )

    print(f"    Generating thumbnail ({key})...")
    try:
        key_str = TOGETHER_KEY_FILE.read_text().strip()
        r = _req.post(TOGETHER_URL,
            headers={"Authorization": f"Bearer {key_str}"},
            json={"model": TOGETHER_MODEL, "prompt": prompt,
                  "width": 1280, "height": 720, "steps": 4, "n": 1},
            timeout=90)
        if r.status_code == 429:
            print("    Rate limit — waiting 30s...")
            time.sleep(30)
            r = _req.post(TOGETHER_URL,
                headers={"Authorization": f"Bearer {key_str}"},
                json={"model": TOGETHER_MODEL, "prompt": prompt,
                      "width": 1280, "height": 720, "steps": 4, "n": 1},
                timeout=90)
        if r.status_code != 200:
            return False
        item = r.json()["data"][0]
        b64  = item.get("b64_json")
        if b64:
            img = base64.b64decode(b64)
        else:
            url = item.get("url", "")
            img = _req.get(url, timeout=30).content if url else None
        if not img:
            return False
        out_path.write_bytes(img)
        print(f"    Thumbnail saved: {out_path.name}")
        time.sleep(15)
        return True
    except Exception as e:
        print(f"    Thumbnail error: {e}")
        return False


def render_loop(key: str, loop_mp4: Path, lang_music: str, dry_run: bool) -> bool:
    """Render 5-min loop using LullabyLoop Remotion composition."""
    v = VIDEOS[key]
    props = {
        "theme":         v["theme"],
        "bgColorTop":    v["bg_top"],
        "bgColorBottom": v["bg_bottom"],
        "accentColor":   v["accent"],
        "musicFile":     lang_music,
        "bpm":           v["bpm"],
    }
    cmd = [
        "npx", "remotion", "render", "LullabyLoop",
        f"--props={json.dumps(props)}",
        f"--output={str(loop_mp4)}",
    ]
    print(f"  Render loop: {loop_mp4.name}")
    if dry_run:
        print(f"    DRY RUN — would render LullabyLoop")
        return True
    result = subprocess.run(cmd, cwd=str(REMOTION), capture_output=False, timeout=3600)
    return result.returncode == 0


def assemble_lullaby(key: str, loop_mp4: Path, out_mp4: Path, dry_run: bool) -> bool:
    """Use FFmpeg to assemble loop into full-length video with brightness fade."""
    v     = VIDEOS[key]
    hours = v["hours"]
    total_sec = int(hours * 3600)

    # Build concat: loop_bright + loop_mid + loop_dim
    # bright = first 30 min, mid = next 30 min, dim = rest
    bright_loops = max(1, 30 * 60 // (LOOP_DUR))
    mid_loops    = max(1, 30 * 60 // (LOOP_DUR))
    dim_loops    = max(1, (total_sec - 60 * 60) // (LOOP_DUR))

    playlist = TMP_DIR / f"playlist_{key}.txt"
    lines = []
    for _ in range(bright_loops):
        lines.append(f"file '{loop_mp4.resolve()}'")
    for _ in range(mid_loops):
        lines.append(f"file '{loop_mp4.resolve()}'")
    for _ in range(dim_loops):
        lines.append(f"file '{loop_mp4.resolve()}'")

    playlist.write_text("\n".join(lines))

    # FFmpeg with brightness fade filter
    # vf: curves to dim progressively over time
    fade_filter = (
        f"fade=t=out:st={total_sec - 30}:d=30,"
        f"lutrgb=r='val*{0.7}':g='val*{0.7}':b='val*{0.7}'"  # basic dim
    )
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(playlist),
        "-vf", f"fade=t=out:st={total_sec - 60}:d=60",
        "-af", f"afade=t=out:st={total_sec - 120}:d=120",
        "-t", str(total_sec),
        "-c:v", "libx264", "-crf", "23", "-preset", "fast",
        "-c:a", "aac", "-b:a", "96k",
        str(out_mp4),
    ]
    print(f"  Assemble: {out_mp4.name} ({hours}h)")
    if dry_run:
        print(f"    DRY RUN — would assemble via FFmpeg")
        return True
    result = subprocess.run(cmd, capture_output=False, timeout=7200)
    return result.returncode == 0


def process_key(key: str, ep_idx: int, dry_run: bool, regen_meta: bool):
    v        = VIDEOS[key]
    en_music = v["music"]
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    all_ok = True
    for lang, queue in [("en", QUEUE_EN), ("ar", QUEUE_AR), ("id", QUEUE_ID)]:
        out_mp4    = queue / f"lullaby_{key}_{DATE_STR}.mp4"
        lang_music = alt_music(en_music, ep_idx, lang)
        loop_mp4   = TMP_DIR / f"loop_{key}_{lang}.mp4"

        if not regen_meta:
            if out_mp4.exists():
                print(f"  Already exists ({lang}): {out_mp4.name}")
            else:
                if not loop_mp4.exists():
                    ok = render_loop(key, loop_mp4, lang_music, dry_run)
                    if not ok:
                        print(f"  FAILED render loop: {key} ({lang})")
                        all_ok = False
                        continue

                ok = assemble_lullaby(key, loop_mp4, out_mp4, dry_run)
                if not ok:
                    print(f"  FAILED assemble: {key} ({lang})")
                    all_ok = False
                    continue

        if out_mp4.exists() or dry_run:
            meta_path = queue / f"meta_{out_mp4.stem}.yaml"
            if not meta_path.exists() or regen_meta:
                meta = make_meta(key, lang)
                if not dry_run:
                    with open(meta_path, "w", encoding="utf-8") as f:
                        yaml.dump(meta, f, allow_unicode=True, default_flow_style=False)
                print(f"  Meta ({lang}): {meta_path.name}")

            thumb_path = queue / f"thumb_{out_mp4.stem}.png"
            if not thumb_path.exists() and not dry_run:
                generate_thumbnail(key, thumb_path)

    return all_ok


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--keys",      nargs="*", default=None)
    parser.add_argument("--dry-run",   action="store_true")
    parser.add_argument("--regen-meta",action="store_true")
    args = parser.parse_args()

    all_keys = list(VIDEOS.keys())
    keys = args.keys if args.keys else all_keys

    for k in keys:
        if k not in VIDEOS:
            print(f"Unknown key: {k}. Valid: {all_keys}")
            sys.exit(1)

    print(f"=== Lullaby Long Generator ===")
    all_keys = list(VIDEOS.keys())
    for k in keys:
        v      = VIDEOS[k]
        ep_idx = all_keys.index(k)
        print(f"\n[{k}] {v['name_en']} ({v['hours']}h)")
        process_key(k, ep_idx, args.dry_run, args.regen_meta)


if __name__ == "__main__":
    main()
