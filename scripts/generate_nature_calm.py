#!/usr/bin/env python3
"""
Generate Nature Calm series — 6 soothing nature videos, 30 min, no text.
Uses NatureCalm Remotion composition (parallax sky/hills/grass + organic motion).
For themes without NatureCalm equiv (forest, rain), uses ShapeDanceLong as fallback.
No text → EN+AR+ID (1 render, 3 queues).

Usage:
  python3 scripts/generate_nature_calm.py --key nature_calm_cat2
  python3 scripts/generate_nature_calm.py --regen-meta
"""
import argparse, base64, json, subprocess, yaml
from datetime import datetime
from pathlib import Path
import requests

ROOT     = Path(__file__).resolve().parent.parent
REMOTION = ROOT / "remotion"
QUEUE_EN = ROOT / "output" / "queue"
QUEUE_AR = ROOT / "output" / "queue_ar"
QUEUE_ID = ROOT / "output" / "queue_id"
TOGETHER_KEY_FILE = ROOT / "credentials" / "together_api_key.txt"
TOGETHER_URL      = "https://api.together.xyz/v1/images/generations"
DATE_STR = datetime.now().strftime("%Y%m%d")

# Map episode keys to NatureCalm Remotion themes (None = use ShapeDanceLong fallback)
NATURE_CALM_THEME = {
    "ocean":     "underwater",
    "forest":    None,          # no NatureCalm equivalent — ShapeDanceLong fallback
    "night_sky": "night",
    "meadow":    "meadow",
    "rain":      None,          # ShapeDanceLong fallback
    "sunset":    "sunset",
}

LOOPS_DIR = ROOT / "output" / "_nature_loops"

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

EPISODES = {
    "ocean": {
        "shapes": ["circle", "oval"],
        "colors": ["#006994", "#0099CC", "#48CAE4", "#90E0EF"],
        "bgColor": "#010810", "bpm": 50, "music": "Gymnopedie No 1.mp3",
        "thumb_prompt": "deep blue calm ocean scene, glowing blue bubbles floating slowly, serene underwater atmosphere, soothing baby video",
    },
    "forest": {
        "shapes": ["hexagon", "circle", "oval"],
        "colors": ["#1B4332", "#2D6A4F", "#52B788", "#95D5B2"],
        "bgColor": "#010A04", "bpm": 45, "music": "Crinoline Dreams.mp3",
        "thumb_prompt": "magical dark green enchanted forest night, soft glowing green hexagons floating, fireflies, calming baby animation",
    },
    "night_sky": {
        "shapes": ["circle", "star"],
        "colors": ["#FFD700", "#FFF8DC", "#C0C0C0", "#87CEEB"],
        "bgColor": "#010108", "bpm": 40, "music": "Heartwarming.mp3",
        "thumb_prompt": "calm deep blue starry night sky, golden stars and circles drifting slowly, dark background, soothing baby video",
    },
    "meadow": {
        "shapes": ["heart", "oval", "circle"],
        "colors": ["#90EE90", "#ADFF2F", "#FFD700", "#FFC0CB"],
        "bgColor": "#030A01", "bpm": 55, "music": "Life of Riley.mp3",
        "thumb_prompt": "peaceful meadow sunrise, soft green yellow pink shapes floating gently, calm toddler video, nature colors",
    },
    "rain": {
        "shapes": ["circle", "oval"],
        "colors": ["#B0C4DE", "#778899", "#4682B4", "#87CEEB"],
        "bgColor": "#020508", "bpm": 48, "music": "Wholesome.mp3",
        "thumb_prompt": "gentle rain drops falling on dark background, soft blue grey circles, soothing calm rain for babies",
    },
    "sunset": {
        "shapes": ["circle", "heart", "oval"],
        "colors": ["#FF7043", "#FF8A65", "#FFAB91", "#CE93D8"],
        "bgColor": "#0A0205", "bpm": 52, "music": "Carefree.mp3",
        "thumb_prompt": "beautiful sunset orange purple sky, glowing circles and hearts floating, golden hour calming baby video",
    },
}

TITLES = {
    "ocean":     {"en": "🌊 Calm Ocean for Babies | 30 Minutes | Happy Bear Kids",
                  "ar": "🌊 محيط هادئ للأطفال | ٣٠ دقيقة | Happy Bear Kids",
                  "id": "🌊 Laut Tenang untuk Bayi | 30 Menit | Happy Bear Kids"},
    "forest":    {"en": "🌿 Enchanted Forest Calm | 30 Minutes | Happy Bear Kids",
                  "ar": "🌿 غابة ساحرة هادئة | ٣٠ دقيقة | Happy Bear Kids",
                  "id": "🌿 Hutan Ajaib yang Tenang | 30 Menit | Happy Bear Kids"},
    "night_sky": {"en": "⭐ Starry Night Sky | 30 Minutes | Happy Bear Kids",
                  "ar": "⭐ سماء ليلية مرصّعة بالنجوم | ٣٠ دقيقة | Happy Bear Kids",
                  "id": "⭐ Langit Malam Berbintang | 30 Menit | Happy Bear Kids"},
    "meadow":    {"en": "🌸 Peaceful Meadow | 30 Minutes | Happy Bear Kids",
                  "ar": "🌸 مرج هادئ للأطفال | ٣٠ دقيقة | Happy Bear Kids",
                  "id": "🌸 Padang Rumput Damai | 30 Menit | Happy Bear Kids"},
    "rain":      {"en": "🌧️ Gentle Rain Calm | 30 Minutes | Happy Bear Kids",
                  "ar": "🌧️ مطر هادئ للأطفال | ٣٠ دقيقة | Happy Bear Kids",
                  "id": "🌧️ Hujan Lembut yang Menenangkan | 30 Menit | Happy Bear Kids"},
    "sunset":    {"en": "🌅 Sunset Calm for Babies | 30 Minutes | Happy Bear Kids",
                  "ar": "🌅 غروب هادئ للأطفال | ٣٠ دقيقة | Happy Bear Kids",
                  "id": "🌅 Senja Tenang untuk Bayi | 30 Menit | Happy Bear Kids"},
}

DESC = {
    "en": (
        "Welcome to Happy Bear Kids! 🐻\n\n"
        "30 minutes of beautiful, calming abstract visuals inspired by the wonders of nature. "
        "Soft, slow-moving shapes in nature-inspired colours gently drift and float to peaceful "
        "music — perfect for calming babies, helping toddlers relax, and creating a soothing "
        "screen-time experience.\n\n"
        "Our Nature Calm series brings the tranquillity of the natural world into your home "
        "through simple, elegant abstract visuals. No characters, no sudden movements, no "
        "surprises — just gentle, flowing shapes and colours that soothe and delight.\n\n"
        "🌟 Key features:\n"
        "• Soft, slow-moving shapes in nature-inspired colour palettes\n"
        "• Very low BPM music chosen specifically for calm and relaxation\n"
        "• No bright flashes or sudden changes — gentle transitions only\n"
        "• No words or voices — universally enjoyable for every child\n"
        "• 30 full minutes of uninterrupted calm visual experience\n\n"
        "👶 Perfect for:\n"
        "• Calming a fussy or overtired baby or toddler\n"
        "• Background during nap time preparation\n"
        "• Gentle screen time that does not overstimulate\n"
        "• Visual tracking practice for infants aged 0-6 months\n"
        "• Winding down after a busy or stimulating day\n\n"
        "🎯 Educational and developmental value:\n"
        "• Colour recognition through nature-inspired hues and gradients\n"
        "• Visual tracking as shapes drift slowly and predictably across the screen\n"
        "• Sensory regulation — gentle colours help reduce visual stress in infants\n"
        "• Rhythm awareness through soft, slow music that supports brain development\n"
        "• Attention and focus development through simple, predictable movement patterns\n\n"
        "No loud sounds, no surprises, no talking — just 30 minutes of pure, soothing, "
        "nature-inspired visual calm. Your baby will love quietly watching as the shapes "
        "slowly float, glow and drift across the screen.\n\n"
        "🎵 Music by Kevin MacLeod (incompetech.com)\n"
        "Licensed under Creative Commons: By Attribution 4.0 License\n"
        "http://creativecommons.org/licenses/by/4.0/\n\n"
        "© Happy Bear Kids 2026 — All rights reserved\n"
        "New videos every week! Subscribe ▶ @HappyBearKids1\n\n"
        "#HappyBearKids #CalmBabyVideo #NatureCalm #SoothingBaby #BabyCalm "
        "#ToddlerCalm #30Minutes #BabyRelax #CalmVisuals #NatureForBabies"
    ),
    "ar": (
        "أهلاً بكم في Happy Bear Kids! 🐻\n\n"
        "٣٠ دقيقة من المرئيات الهادئة المستوحاة من الطبيعة. أشكال ناعمة تتحرك ببطء بألوان "
        "طبيعية مريحة تطفو بهدوء على موسيقى سلمية — مثالية لتهدئة الأطفال الرضّع والصغار.\n\n"
        "سلسلة الطبيعة الهادئة تجلب سكينة الطبيعة إلى منزلكم من خلال مرئيات بسيطة وأنيقة. "
        "لا شخصيات، لا حركات مفاجئة، لا مفاجآت — فقط أشكال وألوان ناعمة تهدّئ وتُسعد.\n\n"
        "🌟 المميزات الرئيسية:\n"
        "• أشكال ناعمة بألوان طبيعية هادئة\n"
        "• موسيقى منخفضة الإيقاع مختارة خصيصاً للاسترخاء\n"
        "• لا وميض أو تغييرات مفاجئة\n"
        "• بدون كلمات أو أصوات\n"
        "• ٣٠ دقيقة كاملة من الهدوء البصري\n\n"
        "👶 مناسب لـ:\n"
        "• تهدئة الطفل المتعب أو المتهيّج\n"
        "• خلفية هادئة أثناء الاستعداد للنوم\n"
        "• وقت شاشة لطيف لا يفرط في التحفيز\n\n"
        "🎵 موسيقى Kevin MacLeod (incompetech.com) — Creative Commons 4.0\n"
        "© Happy Bear Kids 2026 | اشترك ▶ @happybearkidsar\n\n"
        "#HappyBearKids #هدوء_الطبيعة #تهدئة_الطفل #فيديو_أطفال_هادئ #رضيع"
    ),
    "id": (
        "Selamat datang di Happy Bear Kids! 🐻\n\n"
        "30 menit visual abstrak yang menenangkan terinspirasi dari keajaiban alam. "
        "Bentuk-bentuk lembut bergerak perlahan dengan warna-warna alam mengapung dengan damai "
        "diiringi musik tenang — sempurna untuk menenangkan bayi dan balita yang rewel.\n\n"
        "Seri Alam Tenang kami menghadirkan ketenangan alam ke rumah Anda melalui visual "
        "abstrak yang sederhana dan elegan. Tidak ada karakter, tidak ada gerakan tiba-tiba "
        "— hanya bentuk dan warna lembut yang menenangkan dan menyenangkan.\n\n"
        "🌟 Fitur utama:\n"
        "• Bentuk lembut dengan palet warna terinspirasi alam\n"
        "• Musik BPM sangat rendah dipilih khusus untuk ketenangan\n"
        "• Tidak ada kilatan cahaya atau perubahan mendadak\n"
        "• Tanpa kata-kata atau suara\n"
        "• 30 menit penuh pengalaman visual tenang\n\n"
        "👶 Sempurna untuk:\n"
        "• Menenangkan bayi atau balita yang rewel atau kelelahan\n"
        "• Latar belakang saat bersiap tidur siang\n"
        "• Waktu layar lembut yang tidak merangsang berlebihan\n\n"
        "🎵 Musik oleh Kevin MacLeod (incompetech.com) — CC Attribution 4.0\n"
        "© Happy Bear Kids 2026 | Subscribe ▶ @happybearkidsin\n\n"
        "#HappyBearKids #TenangAlam #VideoTenangBayi #BalitaTenang #AnimasiLembut"
    ),
}


def generate_thumbnail(ep_key, ep, queue, out_name, lang):
    thumb_path = queue / f"thumb_{Path(out_name).stem}.png"
    if thumb_path.exists():
        return True
    if not TOGETHER_KEY_FILE.exists():
        return False
    api_key = TOGETHER_KEY_FILE.read_text().strip()
    prompt = ep["thumb_prompt"]
    if lang == "ar":
        prompt += ", no text, no letters, no words, no numbers"
    try:
        resp = requests.post(TOGETHER_URL, headers={
            "Authorization": f"Bearer {api_key}", "Content-Type": "application/json"
        }, json={"model": "black-forest-labs/FLUX.1-schnell",
                 "prompt": prompt, "width": 1280, "height": 720,
                 "steps": 4, "n": 1, "response_format": "b64_json"}, timeout=60)
        if resp.status_code != 200:
            print(f"  thumb error {resp.status_code}")
            return False
        thumb_path.write_bytes(__import__("base64").b64decode(resp.json()["data"][0]["b64_json"]))
        print(f"  thumb → {thumb_path.name}")
        return True
    except Exception as e:
        print(f"  thumb error: {e}")
        return False


def make_meta(ep_key, lang, queue, out_name):
    meta = {
        "title": TITLES[ep_key][lang], "description": DESC[lang],
        "video_type": "nature_calm", "theme": ep_key, "language": lang,
        "duration_minutes": 30, "is_short": False, "status": "public",
        "tags": ["nature calm", "baby calm", "soothing", "toddler relax", "happy bear kids",
                 "30 minutes", "calm shapes", "baby video", "nature", ep_key.replace("_", " ")],
    }
    meta_path = queue / f"meta_{Path(out_name).stem}.yaml"
    with open(meta_path, "w", encoding="utf-8") as f:
        yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def _render_nature_calm_loop(ep_key, ep, lang, loop_path, dry_run) -> bool:
    """Render 5-min NatureCalm loop or fall back to 30-min ShapeDanceLong."""
    nc_theme = NATURE_CALM_THEME.get(ep_key)
    if nc_theme:
        props = json.dumps({
            "theme": nc_theme,
            "musicFile": ep["music"],
            "phaseOffset": {"en": 0.0, "ar": 0.37, "id": 0.68}.get(lang, 0.0),
        })
        cmd = ["npx", "remotion", "render", "NatureCalm", str(loop_path),
               "--props", props, "--log", "error"]
    else:
        # fallback: ShapeDanceLong renders the full 30 min directly
        props = json.dumps({
            "shapes": ep["shapes"], "colors": ep["colors"],
            "bgColor": ep["bgColor"], "bpm": ep["bpm"],
            "showLabels": False, "musicFile": ep["music"],
        })
        cmd = ["npx", "remotion", "render", "ShapeDanceLong", str(loop_path),
               "--props", props, "--log", "error"]
    if dry_run:
        print(f"    [DRY RUN] {' '.join(cmd[:4])}")
        return True
    loop_path.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(cmd, cwd=str(REMOTION), timeout=86400)
    return r.returncode == 0


def _extend_to_30min(loop_path: Path, out_path: Path, dry_run: bool) -> bool:
    """Tile 5-min loop 6× to make 30 min. For ShapeDanceLong, loop is already 30 min → just copy."""
    import shutil
    if loop_path.stat().st_size > 2_000_000_000 if not dry_run else False:
        # Already 30 min (ShapeDanceLong), just copy
        shutil.copy2(str(loop_path), str(out_path))
        return True
    concat = out_path.parent / f"_concat_{out_path.stem}.txt"
    concat.write_text("\n".join([f"file '{loop_path.resolve()}'"] * 6))
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
           "-i", str(concat), "-c", "copy", str(out_path)]
    if dry_run:
        print(f"    [DRY RUN] ffmpeg concat 6× → {out_path.name}")
        concat.unlink(missing_ok=True)
        return True
    r = subprocess.run(cmd, timeout=600)
    concat.unlink(missing_ok=True)
    return r.returncode == 0


def render_episode(ep_key, ep, ep_idx, dry_run, regen_meta):
    out_name = f"nature_calm_{ep_key}_{DATE_STR}.mp4"
    nc_theme = NATURE_CALM_THEME.get(ep_key)
    ok = True
    LOOPS_DIR.mkdir(parents=True, exist_ok=True)

    for lang, queue in [("en", QUEUE_EN), ("ar", QUEUE_AR), ("id", QUEUE_ID)]:
        out_mp4  = queue / out_name
        loop_mp4 = LOOPS_DIR / f"nature_loop_{ep_key}_{lang}.mp4"

        if not out_mp4.exists() and not regen_meta and not dry_run:
            if nc_theme:
                # Step 1: render 5-min loop (once per lang for different phaseOffset)
                if not loop_mp4.exists():
                    print(f"  NatureCalm render {ep_key}/{nc_theme} ({lang})...", flush=True)
                    ok2 = _render_nature_calm_loop(ep_key, ep, lang, loop_mp4, dry_run)
                    if not ok2:
                        print(f"  FAILED: {ep_key} ({lang})")
                        ok = False
                        continue
                # Step 2: extend 5 min × 6 = 30 min
                print(f"  Extending 6× → {out_name}", flush=True)
                ok2 = _extend_to_30min(loop_mp4, out_mp4, dry_run)
                if not ok2:
                    ok = False
                    continue
            else:
                # ShapeDanceLong renders 30 min directly
                loop_mp4_30 = LOOPS_DIR / f"nature_loop_{ep_key}_{lang}_30.mp4"
                lang_music = alt_music(ep["music"], ep_idx, lang)
                ep_lang = dict(ep, music=lang_music)
                print(f"  ShapeDanceLong render {ep_key} ({lang})...", flush=True)
                ok2 = _render_nature_calm_loop(ep_key, ep_lang, lang, loop_mp4_30, dry_run)
                if not ok2:
                    ok = False
                    continue
                import shutil
                shutil.copy2(str(loop_mp4_30), str(out_mp4))

            if out_mp4.exists():
                print(f"  ✓ {out_name} ({out_mp4.stat().st_size/1024/1024:.1f}MB)")

        elif out_mp4.exists():
            print(f"  EXISTS {ep_key} ({lang})")

        if out_mp4.exists() or dry_run:
            make_meta(ep_key, lang, queue, out_name)
            generate_thumbnail(ep_key, ep, queue, out_name, lang)

    return ok


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--key",        default="nature_calm_cat2")
    parser.add_argument("--regen-meta", action="store_true")
    parser.add_argument("--dry-run",    action="store_true")
    args = parser.parse_args()
    for d in (QUEUE_EN, QUEUE_AR, QUEUE_ID):
        d.mkdir(parents=True, exist_ok=True)
    print(f"\n=== Nature Calm: {len(EPISODES)} episodes → EN+AR+ID ===\n")
    ok = 0
    for ep_idx, (ep_key, ep) in enumerate(EPISODES.items()):
        print(f"[{ep_key}]")
        if render_episode(ep_key, ep, ep_idx, args.dry_run, args.regen_meta):
            ok += 1
    print(f"\nDone: {ok}/{len(EPISODES)}")

if __name__ == "__main__":
    main()
