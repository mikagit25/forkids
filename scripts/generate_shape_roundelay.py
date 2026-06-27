#!/usr/bin/env python3
"""
Generate Shape Roundelay series — 8 abstract shape-dance videos, 30 min, no text.
Uses ShapeDanceLong Remotion composition. No text → EN+AR+ID (1 render, 3 queues).

Usage:
  python3 scripts/generate_shape_roundelay.py --key shape_roundelay
  python3 scripts/generate_shape_roundelay.py --key shape_roundelay --regen-meta
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

MUSIC_TRACKS = [
    "Happy Happy Game Show.mp3", "Hyperfun.mp3", "Merry Go.mp3",
    "Quirky Dog.mp3", "Wholesome.mp3", "Carefree.mp3",
    "Monkeys Spinning Monkeys.mp3", "Pinball Spring.mp3",
]

# Episode N = exactly N shape TYPES in the video.
# Title "N Shape(s) Roundelay" matches the number of shapes on screen.
# Thumbnail shows EXACTLY those N shapes so thumbnail = video content.
EPISODES = {
    "roundelay_1": {
        "shapes": ["circle"],
        "colors": ["#FF6EB4"],
        "bgColor": "#0A0014", "bpm": 65, "music": "Wholesome.mp3",
        "thumb_prompt": (
            "one large pink circle, Pixar 3D render style, glossy smooth surface, "
            "soft studio lighting, subtle drop shadow, dark purple background, "
            "kids video thumbnail, no text, no letters"
        ),
    },
    "roundelay_2": {
        "shapes": ["circle", "star"],
        "colors": ["#44AAFF", "#FFD700"],
        "bgColor": "#00050F", "bpm": 70, "music": "Carefree.mp3",
        "thumb_prompt": (
            "exactly two shapes: one blue circle and one yellow star, "
            "Pixar 3D render style, glossy surfaces, soft lighting, "
            "dark navy background, kids video thumbnail, no text, no letters"
        ),
    },
    "roundelay_3": {
        "shapes": ["circle", "heart", "triangle"],
        "colors": ["#FF6EB4", "#FF4444", "#FFD700"],
        "bgColor": "#0A0500", "bpm": 75, "music": "Happy Happy Game Show.mp3",
        "thumb_prompt": (
            "exactly three shapes: pink circle, red heart, yellow triangle, "
            "Pixar 3D render style, glossy cute toy look, soft studio lighting, "
            "dark background, kids video thumbnail, no text, no letters"
        ),
    },
    "roundelay_4": {
        "shapes": ["circle", "heart", "star", "square"],
        "colors": ["#FF6EB4", "#FF4444", "#FFD700", "#FF8C00"],
        "bgColor": "#0F050A", "bpm": 75, "music": "Monkeys Spinning Monkeys.mp3",
        "thumb_prompt": (
            "exactly four shapes: pink circle, red heart, yellow star, orange square, "
            "Pixar 3D render style, glossy bright toy colours, soft studio lighting, "
            "dark background, kids thumbnail, no text, no letters"
        ),
    },
    "roundelay_5": {
        "shapes": ["circle", "heart", "star", "square", "triangle"],
        "colors": ["#FF6EB4", "#FF4444", "#FFD700", "#44AAFF", "#00CC66"],
        "bgColor": "#020A06", "bpm": 80, "music": "Hyperfun.mp3",
        "thumb_prompt": (
            "exactly five colorful 3D shapes: pink circle, red heart, yellow star, "
            "blue square, green triangle, Pixar 3D toy render, glossy surfaces, "
            "dark background, kids video thumbnail, no text, no letters"
        ),
    },
    "roundelay_6": {
        "shapes": ["circle", "heart", "star", "square", "triangle", "diamond"],
        "colors": ["#FF6EB4", "#FF4444", "#FFD700", "#44AAFF", "#00CC66", "#CC44FF"],
        "bgColor": "#05000A", "bpm": 85, "music": "Quirky Dog.mp3",
        "thumb_prompt": (
            "exactly six colorful 3D shapes: pink circle, red heart, yellow star, "
            "blue square, green triangle, purple diamond, Pixar 3D toy render, "
            "glossy surfaces, dark background, kids video thumbnail, no text, no letters"
        ),
    },
    "roundelay_7": {
        "shapes": ["circle", "heart", "star", "square", "triangle", "diamond", "hexagon"],
        "colors": ["#FF6EB4", "#FF4444", "#FFD700", "#44AAFF", "#00CC66", "#CC44FF", "#00CCCC"],
        "bgColor": "#00050A", "bpm": 80, "music": "Merry Go.mp3",
        "thumb_prompt": (
            "exactly seven colorful 3D shapes: pink circle, red heart, yellow star, "
            "blue square, green triangle, purple diamond, teal hexagon, "
            "Pixar 3D toy render, glossy surfaces, dark background, "
            "kids video thumbnail, no text, no letters"
        ),
    },
    "roundelay_8": {
        "shapes": ["circle", "heart", "star", "square", "triangle", "diamond", "hexagon", "oval"],
        "colors": ["#FF6EB4", "#FF4444", "#FFD700", "#44AAFF", "#00CC66", "#CC44FF", "#00CCCC", "#FF8C00"],
        "bgColor": "#050505", "bpm": 90, "music": "Pinball Spring.mp3",
        "thumb_prompt": (
            "exactly eight colorful 3D shapes: pink circle, red heart, yellow star, "
            "blue square, green triangle, purple diamond, teal hexagon, orange oval, "
            "all eight shapes clearly visible, Pixar 3D toy render, glossy surfaces, "
            "dark background, kids video thumbnail, no text, no letters"
        ),
    },
}

TITLE_EN = "🔄 {name} {shape_word} Roundelay | 30 Minutes | Happy Bear Kids"
TITLE_AR = "🔄 دائرة {num} أشكال | ٣٠ دقيقة | Happy Bear Kids"
TITLE_ID = "🔄 Rondo {num} Bentuk | 30 Menit | Happy Bear Kids"

DESC_EN = """\
Welcome to Happy Bear Kids! 🐻

30 minutes of beautiful, mesmerising shapes dancing in a round! Watch as colourful \
geometric shapes spin, bounce and move in perfect rhythm — a wonderful treat for babies, \
toddlers and young children.

Our Shape Roundelay series is designed to captivate babies and young children with \
vivid, moving colours and shapes. Pure visual joy for little eyes and growing minds!

🌟 Key features:
• Beautifully coloured geometric shapes in constant, rhythmic motion
• Perfect visual stimulation for babies aged 0-3 years
• Calming yet engaging — great for focus and relaxation
• No words, no voices — universally enjoyable for every child
• Upbeat background music that supports brain development
• 30 full minutes of uninterrupted visual joy

👶 Great for:
• Tummy time — high-contrast shapes support visual tracking
• Calm play — shapes and colours spark curiosity
• Background entertainment during feeding or rest
• Toddlers who love patterns, shapes and colours
• Older children learning about geometric shapes

🎯 Educational value:
• Visual shape recognition (circles, stars, triangles, hexagons and more)
• Colour awareness and colour-matching
• Pattern and symmetry recognition
• Rhythm and timing awareness through music

No talking, no surprises — just 30 uninterrupted minutes of soothing shape motion \
and cheerful music. Perfect screen time that keeps little ones engaged!

🎵 Music by Kevin MacLeod (incompetech.com)
Licensed under Creative Commons: By Attribution 4.0 License
http://creativecommons.org/licenses/by/4.0/

© Happy Bear Kids 2026 — All rights reserved
New videos every week! Subscribe ▶ @HappyBearKids1

#HappyBearKids #ShapeRoundelay #ShapesForKids #KidsShapes #BabyShapes \
#ToddlerShapes #GeometricShapes #KidsAnimation #VisualLearning #30Minutes"""

DESC_AR = """\
أهلاً بكم في Happy Bear Kids! 🐻

٣٠ دقيقة كاملة من الأشكال الجميلة الراقصة في دائرة ساحرة! شاهد الأشكال الهندسية الملوّنة \
وهي تدور وتقفز وتتحرك في إيقاع مثالي — متعة بصرية رائعة للأطفال الرضّع والصغار.

سلسلة دائرة الأشكال مصمّمة لتأسر انتباه الأطفال بالألوان والحركات الزاهية والمستمرة.

🌟 المميزات الرئيسية:
• أشكال هندسية ملوّنة في حركة إيقاعية مستمرة
• تحفيز بصري مثالي للأطفال من ٠ إلى ٣ سنوات
• محتوى هادئ وجذّاب في آنٍ معاً
• بدون كلمات أو أصوات — مناسب لجميع الأطفال
• موسيقى خلفية مرحة تدعم نمو الدماغ
• ٣٠ دقيقة كاملة من المتعة البصرية المتواصلة

👶 مناسب لـ:
• وقت البطن — الأشكال والألوان تدعم تتبع البصر
• اللعب الهادئ — الأشكال والألوان تحفّز الفضول
• ترفيه في الخلفية أثناء الرضاعة أو الراحة
• الأطفال الصغار الذين يحبون الأنماط والأشكال والألوان

🎯 القيمة التعليمية:
• التعرف البصري على الأشكال الهندسية
• الوعي بالألوان ومطابقتها
• التعرف على الأنماط والتماثل
• الوعي بالإيقاع والتوقيت من خلال الموسيقى

🎵 موسيقى Kevin MacLeod (incompetech.com)
ترخيص Creative Commons: النسب 4.0
© Happy Bear Kids 2026 — جميع الحقوق محفوظة
اشترك ▶ @happybearkidsar

#HappyBearKids #أشكال_للأطفال #تعليم_الأطفال #فيديو_أطفال"""

DESC_ID = """\
Selamat datang di Happy Bear Kids! 🐻

30 menit penuh bentuk-bentuk indah yang menari dalam lingkaran! Saksikan bentuk-bentuk \
geometris berwarna-warni berputar, melompat, dan bergerak dengan irama sempurna — \
hiburan visual yang luar biasa untuk bayi, balita, dan anak-anak kecil.

Seri Rondo Bentuk kami dirancang untuk memikat perhatian bayi dan anak kecil dengan \
warna-warna cerah dan gerakan yang mengalir. Kesenangan visual murni untuk mata kecil \
yang sedang berkembang!

🌟 Fitur utama:
• Bentuk geometris berwarna-warni dalam gerakan ritmis yang terus-menerus
• Stimulasi visual sempurna untuk bayi usia 0-3 tahun
• Menenangkan sekaligus menarik perhatian
• Tanpa kata-kata atau suara — cocok untuk semua anak
• Musik latar yang ceria mendukung perkembangan otak
• 30 menit penuh kesenangan visual tanpa gangguan

👶 Cocok untuk:
• Waktu tengkurap — bentuk kontras tinggi mendukung pelacakan visual
• Bermain tenang — bentuk dan warna memicu rasa ingin tahu
• Hiburan latar selama menyusui atau istirahat
• Balita yang menyukai pola, bentuk, dan warna

🎯 Nilai edukatif:
• Pengenalan bentuk geometris secara visual
• Kesadaran warna dan pencocokan warna
• Pengenalan pola dan simetri
• Kesadaran ritme dan waktu melalui musik

🎵 Musik oleh Kevin MacLeod (incompetech.com)
Lisensi Creative Commons: Atribusi 4.0
http://creativecommons.org/licenses/by/4.0/

© Happy Bear Kids 2026 — Hak cipta dilindungi
Video baru setiap minggu! Subscribe ▶ @happybearkidsin

#HappyBearKids #BentukUntukAnak #AnimasiAnak #BelajarBentuk #VideoBalita"""


def generate_thumbnail(ep_key: str, ep: dict, queue: Path, out_name: str, lang: str) -> bool:
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
        }, json={
            "model": "black-forest-labs/FLUX.1-schnell",
            "prompt": prompt, "width": 1280, "height": 720,
            "steps": 4, "n": 1, "response_format": "b64_json",
        }, timeout=60)
        if resp.status_code != 200:
            print(f"  thumb error {resp.status_code}: {resp.text[:100]}")
            return False
        data = resp.json()["data"][0]["b64_json"]
        thumb_path.write_bytes(base64.b64decode(data))
        print(f"  thumb → {thumb_path.name}")
        return True
    except Exception as e:
        print(f"  thumb error: {e}")
        return False


def make_meta(ep_key: str, ep_num: int, lang: str, queue: Path, out_name: str):
    num_str   = str(ep_num)
    name_str  = ep_key.replace("roundelay_", "").replace("_", " ").title()
    shape_word = "Shape" if ep_num == 1 else "Shapes"
    if lang == "en":
        title = TITLE_EN.format(name=name_str, shape_word=shape_word)
        desc  = DESC_EN
    elif lang == "ar":
        title = TITLE_AR.format(num=num_str)
        desc  = DESC_AR
    else:
        title = TITLE_ID.format(num=num_str)
        desc  = DESC_ID
    meta = {
        "title": title, "description": desc,
        "video_type": "shape_roundelay", "theme": "shapes",
        "language": lang, "duration_minutes": 30,
        "is_short": False, "status": "public",
        "tags": ["shapes", "roundelay", "kids", "toddler", "baby", "happy bear kids",
                 "geometric shapes", "shapes for kids", "colorful shapes", "30 minutes",
                 "shapes dance", "baby shapes", "kids animation"],
    }
    meta_path = queue / f"meta_{Path(out_name).stem}.yaml"
    with open(meta_path, "w", encoding="utf-8") as f:
        yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def render_episode(ep_key: str, ep: dict, ep_num: int, ep_idx: int, dry_run: bool, regen_meta: bool) -> bool:
    out_name = f"shape_roundelay_{ep_key}_{DATE_STR}.mp4"
    ok = True

    for lang, queue in [("en", QUEUE_EN), ("ar", QUEUE_AR), ("id", QUEUE_ID)]:
        out_mp4    = queue / out_name
        lang_music = alt_music(ep["music"], ep_idx, lang)
        if out_mp4.exists() and not regen_meta:
            print(f"  SKIP {ep_key} ({lang}, exists)")
        elif not dry_run and not regen_meta:
            props = {
                "shapes": ep["shapes"], "colors": ep["colors"],
                "bgColor": ep["bgColor"], "bpm": ep["bpm"],
                "showLabels": False, "musicFile": lang_music,
            }
            cmd = ["npx", "remotion", "render", "ShapeDanceLong",
                   f"--props={json.dumps(props)}", f"--output={str(out_mp4)}",
                   "--log=error"]
            print(f"  Rendering {ep_key} ({lang}, 30 min)...", flush=True)
            r = subprocess.run(cmd, cwd=str(REMOTION), timeout=86400)
            if r.returncode != 0 or not out_mp4.exists():
                print(f"  FAILED render: {ep_key} ({lang})")
                ok = False
                continue
            print(f"  ✓ {out_name} ({out_mp4.stat().st_size/1024/1024:.1f}MB)")

        if out_mp4.exists() or dry_run:
            make_meta(ep_key, ep_num, lang, queue, out_name)
            generate_thumbnail(ep_key, ep, queue, out_name, lang)

    return ok


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--key",       default="shape_roundelay")
    parser.add_argument("--lang",      default="both")
    parser.add_argument("--dry-run",   action="store_true")
    parser.add_argument("--regen-meta", action="store_true")
    args = parser.parse_args()

    for d in (QUEUE_EN, QUEUE_AR, QUEUE_ID):
        d.mkdir(parents=True, exist_ok=True)

    print(f"\n=== Shape Roundelay: {len(EPISODES)} episodes → EN+AR+ID ===\n")
    ok = 0
    for ep_num, (ep_key, ep) in enumerate(EPISODES.items(), 1):
        print(f"[{ep_num}/{len(EPISODES)}] {ep_key}")
        if render_episode(ep_key, ep, ep_num, ep_num - 1, args.dry_run, args.regen_meta):
            ok += 1
    print(f"\nDone: {ok}/{len(EPISODES)} episodes")


if __name__ == "__main__":
    main()
