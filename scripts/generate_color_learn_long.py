#!/usr/bin/env python3
"""
Generate "One Concept Deep" color learning videos via Remotion.
One 20-min video per color per language = 18 videos total.

Usage:
  python3 scripts/generate_color_learn_long.py --dry-run
  python3 scripts/generate_color_learn_long.py --color red
  python3 scripts/generate_color_learn_long.py --lang en
  python3 scripts/generate_color_learn_long.py           # all 18 videos
  python3 scripts/generate_color_learn_long.py --force   # re-render existing
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

ROOT             = Path(__file__).resolve().parent.parent
DATA_PATH        = ROOT / "config" / "color_learn_data.yaml"
QUEUE_DIR        = ROOT / "output" / "queue"
QUEUE_AR_DIR     = ROOT / "output" / "queue_ar"
QUEUE_ID_DIR     = ROOT / "output" / "queue_id"
UPLOADED_DIR     = ROOT / "uploaded"
REMOTION         = ROOT / "remotion"
TOGETHER_KEY_FILE = ROOT / "credentials" / "together_api_key.txt"
TOGETHER_URL     = "https://api.together.xyz/v1/images/generations"
TOGETHER_MODEL   = "black-forest-labs/FLUX.1-schnell"

STYLE_BASE = (
    "children's educational YouTube thumbnail, 1280x720, "
    "bold outlines, cheerful expression, bright vivid colors, "
    "no text, clean white background, simple design"
)

MUSIC_TRACKS = [
    "Happy Happy Game Show.mp3",
    "Carefree.mp3",
    "Pinball Spring.mp3",
    "Merry Go.mp3",
    "Wholesome.mp3",
    "Life of Riley.mp3",
    "Overworld.mp3",
    "Quirky Dog.mp3",
    "Hyperfun.mp3",
]

EN_TAGS_BASE = [
    "learn colors", "colors for kids", "color learning", "preschool", "toddler",
    "educational video", "happy bear kids", "one color deep", "kindergarten",
    "kids learning", "color recognition",
]
AR_TAGS_BASE = [
    "تعلم الألوان", "ألوان للأطفال", "تعليم أطفال", "رياض الأطفال", "هابي بير كيدز",
    "تعليمي", "تعلم الألوان بالعربية",
]
ID_TAGS_BASE = [
    "belajar warna", "warna untuk anak", "belajar anak", "prasekolah", "balita",
    "video edukasi", "happy bear kids", "belajar warna indonesia",
]


def load_data() -> list:
    with open(DATA_PATH) as f:
        return yaml.safe_load(f)["colors"]


def make_props(color: dict, lang: str, music_file: str) -> dict:
    rtl     = (lang == "ar")
    if lang == "id":
        name_localized = lambda obj: obj.get("name_id", obj["name_en"]).capitalize()
        color_name     = color.get("name_id", color["name_en"]).capitalize()
    elif rtl:
        name_localized = lambda obj: obj["name_ar"]
        color_name     = color["name_ar"]
    else:
        name_localized = lambda obj: obj["name_en"].capitalize()
        color_name     = color["name_en"]
    objects = [
        {
            "name":          obj["name_en"],
            "nameLocalized": name_localized(obj),
            "spritePath":    obj["sprite"],
        }
        for obj in color["objects"]
    ]
    return {
        "colorName": color_name,
        "colorHex":  color["hex"],
        "bgColor":   color["bg"],
        "rtl":       rtl,
        "lang":      lang,
        "colorKey":  color["key"],
        "musicFile": music_file,
        "objects":   objects,
    }


def make_meta(color: dict, lang: str, out_path: Path):
    rtl        = (lang == "ar")
    if lang == "id":
        color_name = color.get("name_id", color["name_en"]).capitalize()
        obj_names  = [o.get("name_id", o["name_en"]) for o in color["objects"]]
        tags_base  = ID_TAGS_BASE
    elif rtl:
        color_name = color["name_ar"]
        obj_names  = [o["name_ar"] for o in color["objects"]]
        tags_base  = AR_TAGS_BASE
    else:
        color_name = color["name_en"]
        obj_names  = [o["name_en"] for o in color["objects"]]
        tags_base  = EN_TAGS_BASE
    cn         = color["name_en"].lower()
    cn_cap     = color["name_en"].capitalize()

    if lang == "en":
        title = (
            f"Learn the Color {cn_cap} for Kids! "
            f"20 Minutes | Happy Bear Kids"
        )
        description = (
            f"🎨 Today we learn the color {cn}!\n\n"
            f"In this fun 20-minute learning video, we focus on ONE color — {cn} — "
            f"using the \"One Concept Deep\" method. Instead of rushing through many colors, "
            f"we repeat {cn} 7 to 9 times across different scenes, building a strong and "
            f"lasting memory for your toddler.\n\n"
            f"What we explore in this video:\n"
            f"🔴 {obj_names[0]} — discovering {cn} in real objects\n"
            f"🔴 {obj_names[1]} — counting and naming {cn} things\n"
            f"🔴 {obj_names[2]} — a fun {cn} song and review!\n\n"
            f"Each scene asks your child a question, then pauses 4 seconds so they can "
            f"answer out loud before we reveal. This active participation is proven to "
            f"boost color recognition in children ages 1 to 4.\n\n"
            f"🌟 Why this video works:\n"
            f"• One color only — deep focus builds real memory\n"
            f"• 7–9 repetitions per session — not just a quick flash\n"
            f"• Interactive questions — child answers, not just watches\n"
            f"• Positive reinforcement after every correct answer\n"
            f"• Gentle pace — great as background play video\n"
            f"• Safe, ad-free style content for babies and toddlers\n\n"
            f"Part of our complete 9-Color Series:\n"
            f"Red · Blue · Yellow · Green · Orange · Purple · Pink · White · Black\n\n"
            f"🔔 Subscribe to Happy Bear Kids → @HappyBearKids1\n"
            f"New educational videos every week!\n\n"
            f"🎵 Background Music: Kevin MacLeod (incompetech.com)\n"
            f"Licensed under Creative Commons Attribution 4.0\n"
            f"http://creativecommons.org/licenses/by/4.0/\n\n"
            f"#LearnColors #ColorsForKids #ToddlerLearning #PreschoolColors "
            f"#KidsEducation #{cn_cap}Color #HappyBearKids #BabyLearning "
            f"#ColorRecognition #KindergartenLearning\n\n"
            f"© Happy Bear Kids 2026"
        )
        tags = tags_base + [
            color["name_en"].lower(),
            f"learn {cn}",
            f"{cn} for kids",
            f"color {cn}",
            f"what is {cn}",
        ] + obj_names
    elif lang == "ar":
        title = f"تعلم اللون {color_name} | 20 دقيقة | هابي بير كيدز"
        description = (
            f"🎨 اليوم نتعلم اللون {color_name}!\n\n"
            f"في هذا الفيديو التعليمي الممتع لمدة 20 دقيقة، نركز على لون واحد فقط — "
            f"{color_name} — باستخدام طريقة \"التعمق في مفهوم واحد\". بدلاً من التسرع "
            f"في تعلم ألوان كثيرة، نكرر لون {color_name} من 7 إلى 9 مرات في مشاهد مختلفة، "
            f"مما يبني ذاكرة قوية ودائمة لطفلك الصغير.\n\n"
            f"ماذا نستكشف في هذا الفيديو:\n"
            f"🔴 {obj_names[0]} — اكتشاف اللون {color_name} في الأشياء الحقيقية\n"
            f"🔴 {obj_names[1]} — العد وتسمية الأشياء {color_name}\n"
            f"🔴 {obj_names[2]} — أغنية {color_name} الممتعة ومراجعة!\n\n"
            f"كل مشهد يسأل طفلك سؤالاً، ثم يتوقف 4 ثوانٍ ليتمكن من الإجابة بصوت عالٍ "
            f"قبل أن نكشف الجواب. هذه المشاركة الفعالة تُثبت أنها تعزز التعرف على الألوان "
            f"عند الأطفال من عمر 1 إلى 4 سنوات.\n\n"
            f"🌟 لماذا يُجدي هذا الفيديو:\n"
            f"• لون واحد فقط — التركيز العميق يبني ذاكرة حقيقية\n"
            f"• 7–9 تكرارات في كل جلسة — ليس مجرد لمحة سريعة\n"
            f"• أسئلة تفاعلية — الطفل يجيب ولا يكتفي بالمشاهدة\n"
            f"• تعزيز إيجابي بعد كل إجابة صحيحة\n"
            f"• إيقاع هادئ — رائع كفيديو خلفية أثناء اللعب\n"
            f"• محتوى آمن وبدون إعلانات للرضع والأطفال الصغار\n\n"
            f"جزء من سلسلة الألوان التسعة الكاملة:\n"
            f"أحمر · أزرق · أصفر · أخضر · برتقالي · بنفسجي · وردي · أبيض · أسود\n\n"
            f"🔔 اشتركوا في هابي بير كيدز → @HappyBearKids1\n"
            f"فيديوهات تعليمية جديدة كل أسبوع!\n\n"
            f"🎵 الموسيقى الخلفية: Kevin MacLeod (incompetech.com)\n"
            f"رخصة Creative Commons Attribution 4.0\n"
            f"http://creativecommons.org/licenses/by/4.0/\n\n"
            f"#تعلم_الألوان #ألوان_للأطفال #تعليم_أطفال #رياض_الأطفال "
            f"#هابي_بير_كيدز #تعلم_{color_name} #أطفال #تعليمي\n\n"
            f"© هابي بير كيدز 2026"
        )
        tags = tags_base + [color_name, f"اللون {color_name}",
                            f"تعلم {color_name}"] + obj_names
    elif lang == "id":
        title = (
            f"Belajar Warna {color_name} untuk Anak! "
            f"20 Menit | Happy Bear Kids Indonesia"
        )
        description = (
            f"🎨 Hari ini kita belajar warna {color_name}!\n\n"
            f"Dalam video belajar menyenangkan 20 menit ini, kita fokus pada SATU warna — "
            f"{color_name} — menggunakan metode \"Satu Konsep Mendalam\". Daripada terburu-buru "
            f"mempelajari banyak warna, kita mengulang {color_name} sebanyak 7 hingga 9 kali "
            f"dalam berbagai adegan, membangun memori yang kuat dan tahan lama untuk si kecil.\n\n"
            f"Apa yang kita jelajahi dalam video ini:\n"
            f"🔴 {obj_names[0]} — menemukan {color_name} dalam benda-benda nyata\n"
            f"🔴 {obj_names[1]} — menghitung dan menyebut benda-benda {color_name}\n"
            f"🔴 {obj_names[2]} — lagu {color_name} yang menyenangkan dan ulasan!\n\n"
            f"Setiap adegan mengajukan pertanyaan kepada anak, lalu berhenti 4 detik agar mereka "
            f"bisa menjawab dengan keras sebelum kita ungkap jawabannya. Partisipasi aktif ini "
            f"terbukti meningkatkan pengenalan warna pada anak usia 1 hingga 4 tahun.\n\n"
            f"🌟 Mengapa video ini berhasil:\n"
            f"• Satu warna saja — fokus mendalam membangun memori nyata\n"
            f"• 7–9 pengulangan per sesi — bukan hanya kilasan singkat\n"
            f"• Pertanyaan interaktif — anak menjawab, bukan hanya menonton\n"
            f"• Penguatan positif setelah setiap jawaban benar\n"
            f"• Tempo lembut — bagus sebagai video latar saat bermain\n"
            f"• Konten aman tanpa iklan untuk bayi dan balita\n\n"
            f"Bagian dari seri 9 Warna lengkap kami:\n"
            f"Merah · Biru · Kuning · Hijau · Oranye · Ungu · Merah Muda · Putih · Hitam\n\n"
            f"🔔 Subscribe ke Happy Bear Kids Indonesia → @happybearkidsin\n"
            f"Video edukatif baru setiap minggu!\n\n"
            f"🎵 Musik Latar: Kevin MacLeod (incompetech.com)\n"
            f"Berlisensi Creative Commons Attribution 4.0\n"
            f"http://creativecommons.org/licenses/by/4.0/\n\n"
            f"#BelajarWarna #WarnaUntukAnak #BelajarAnak #PresekolahIndonesia "
            f"#HappyBearKids #VideoEdukasi #WarnaBayi #Warna{cn_cap.replace(' ', '')} "
            f"#BelajarBersamaAnak #BalitaBelajar\n\n"
            f"© Happy Bear Kids Indonesia 2026"
        )
        tags = tags_base + [
            color_name.lower(),
            f"warna {color_name.lower()}",
            f"belajar {color_name.lower()}",
            cn,
        ] + obj_names

    meta = {
        "title":       title,
        "description": description,
        "tags":        tags[:40],
        "video_type":  "colors",
        "theme":       color["key"],
        "language":    lang,
        "status":      "public",
        "is_short":    False,
    }
    meta_path = out_path.parent / f"meta_{out_path.stem}.yaml"
    with open(meta_path, "w") as f:
        yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    print(f"    meta → {meta_path.name}")


def generate_thumbnail(color: dict, lang: str, out_path: Path) -> bool:
    """Generate AI thumbnail via Together.ai and save as thumb_{stem}.png."""
    thumb_path = out_path.parent / f"thumb_{out_path.stem}.png"
    if thumb_path.exists():
        print(f"    thumb exists: {thumb_path.name}")
        return True
    if not TOGETHER_KEY_FILE.exists():
        print("    no Together.ai key — skip thumbnail")
        return False

    try:
        import requests as _req
    except ImportError:
        print("    pip install requests — skip thumbnail")
        return False

    key        = TOGETHER_KEY_FILE.read_text().strip()
    cn         = color["name_en"].lower()
    color_hex  = color["hex"]
    obj_en     = [o["name_en"] for o in color["objects"]]

    if lang == "ar":
        colors_ar = {
            "red": "أحمر", "blue": "أزرق", "yellow": "أصفر",
            "green": "أخضر", "orange": "برتقالي", "purple": "بنفسجي",
            "pink": "وردي", "white": "أبيض", "black": "أسود",
        }
        cn_ar = colors_ar.get(cn, color["name_ar"])
        prompt = (
            f"Big bold {cn} color splash, cute cartoon {obj_en[0]} and {obj_en[1]} "
            f"in {cn} color, educational kids YouTube thumbnail, "
            f"bright {cn} background, cheerful friendly characters, "
            f"bold outlines, vivid {cn} tones, no text, no letters, no words, no numbers, 1280x720"
        )
    else:
        prompt = (
            f"Big bold {cn} color splash, cute cartoon {obj_en[0]} and {obj_en[1]} "
            f"in {cn} color, educational kids YouTube thumbnail, "
            f"bright {cn} background with confetti, cheerful friendly characters, "
            f"bold outlines, vivid {cn} tones, no text, 1280x720, {STYLE_BASE}"
        )

    print(f"    Generating thumbnail ({cn})...")
    try:
        r = _req.post(
            TOGETHER_URL,
            headers={"Authorization": f"Bearer {key}"},
            json={"model": TOGETHER_MODEL, "prompt": prompt,
                  "width": 1280, "height": 720, "steps": 4, "n": 1},
            timeout=90,
        )
        if r.status_code != 200:
            print(f"    Together error {r.status_code}: {r.text[:100]}")
            return False
        item = r.json()["data"][0]
        b64  = item.get("b64_json")
        if b64:
            img_bytes = base64.b64decode(b64)
        else:
            url_val = item.get("url", "")
            img_bytes = _req.get(url_val, timeout=30).content if url_val else None
        if not img_bytes:
            print("    no image data returned")
            return False
        thumb_path.write_bytes(img_bytes)
        print(f"    thumb → {thumb_path.name} ({len(img_bytes)//1024}KB)")
        return True
    except Exception as e:
        print(f"    thumbnail failed: {e}")
        return False


def render_video(color: dict, lang: str, force: bool = False, dry_run: bool = False) -> bool:
    key      = color["key"]
    date_str = datetime.now().strftime("%Y%m%d")
    fname    = f"color_learn_{key}_{lang}_{date_str}.mp4"
    if lang == "ar":
        dest_dir = QUEUE_AR_DIR
    elif lang == "id":
        dest_dir = QUEUE_ID_DIR
    else:
        dest_dir = QUEUE_DIR
    out_path = dest_dir / fname

    if not force:
        if out_path.exists():
            size_mb = out_path.stat().st_size / 1024 / 1024
            print(f"  skip {fname} (in queue, {size_mb:.1f}MB)")
            return True
        # Also skip if already published in uploaded/
        existing = list(UPLOADED_DIR.glob(f"color_learn_{key}_{lang}_*.mp4"))
        if existing:
            print(f"  skip {fname} (already published: {existing[-1].name})")
            return True

    # Pick music track
    color_idx   = [c["key"] for c in load_data()].index(key)
    music_file  = MUSIC_TRACKS[color_idx % len(MUSIC_TRACKS)]

    props       = make_props(color, lang, music_file)
    props_json  = json.dumps(props)

    print(f"\n  Rendering: {fname}")
    print(f"    Color: {color['name_en']} / {color['name_ar']} | lang={lang}")
    print(f"    Music: {music_file}")

    if dry_run:
        print(f"    [DRY RUN] props: {props_json[:120]}...")
        make_meta(color, lang, out_path)
        return True

    dest_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "npx", "remotion", "render",
        "src/index.ts", "ColorLearnLong",
        str(out_path),
        "--props", props_json,
        "--concurrency", "1",
        "--log", "error",
    ]

    print(f"    Running remotion render...")
    result = subprocess.run(
        cmd, cwd=str(REMOTION),
        capture_output=True, text=True,
        timeout=21600,  # 6h max per video (30-min videos need time)
    )

    if result.returncode == 0 and out_path.exists():
        size_mb = out_path.stat().st_size / 1024 / 1024
        print(f"    ✓ {fname} ({size_mb:.1f}MB)")
        make_meta(color, lang, out_path)
        time.sleep(2)
        generate_thumbnail(color, lang, out_path)
        return True
    else:
        print(f"    ✗ FAILED: {result.stderr[-300:]}")
        return False


def regen_metas(color_filter: str | None, lang_filter: str | None):
    """Regenerate meta+thumbnail for every existing MP4 in queue dirs."""
    colors_by_key = {c["key"]: c for c in load_data()}
    updated = 0
    for queue_dir, lang_default in [(QUEUE_DIR, "en"), (QUEUE_AR_DIR, "ar"), (QUEUE_ID_DIR, "id")]:
        for mp4 in sorted(queue_dir.glob("color_learn_*.mp4")):
            parts = mp4.stem.split("_")
            # stem: color_learn_{key}_{lang}_{date}
            if len(parts) < 4:
                continue
            key  = parts[2]
            lang = parts[3]
            if color_filter and key != color_filter:
                continue
            if lang_filter and lang != lang_filter:
                continue
            color = colors_by_key.get(key)
            if not color:
                print(f"  unknown key '{key}' in {mp4.name}")
                continue
            print(f"\n  Regen meta+thumb: {mp4.name}")
            make_meta(color, lang, mp4)
            time.sleep(1)
            generate_thumbnail(color, lang, mp4)
            updated += 1
    print(f"\nRegen done: {updated} meta files updated")


def main():
    parser = argparse.ArgumentParser(description="Generate color learn long videos")
    parser.add_argument("--color",      help="Single color key (e.g. red)")
    parser.add_argument("--lang",       choices=["en", "ar", "id"], help="Single language")
    parser.add_argument("--force",      action="store_true", help="Re-render existing")
    parser.add_argument("--dry-run",    action="store_true", help="Show what would render")
    parser.add_argument("--regen-meta", action="store_true",
                        help="Regenerate meta+thumbnail for existing MP4s (no re-render)")
    args = parser.parse_args()

    if args.regen_meta:
        regen_metas(args.color, args.lang)
        return

    colors = load_data()
    if args.color:
        colors = [c for c in colors if c["key"] == args.color]
        if not colors:
            print(f"Color '{args.color}' not found.")
            sys.exit(1)

    langs = [args.lang] if args.lang else ["en", "ar", "id"]

    print(f"\nColor Learn Long — {len(colors)} colors × {len(langs)} languages = {len(colors)*len(langs)} videos")

    ok = fail = 0
    for color in colors:
        for lang in langs:
            success = render_video(color, lang, force=args.force, dry_run=args.dry_run)
            if success:
                ok += 1
            else:
                fail += 1

    print(f"\nDone: {ok} rendered, {fail} failed")


if __name__ == "__main__":
    main()
