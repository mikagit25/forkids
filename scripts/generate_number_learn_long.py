#!/usr/bin/env python3
"""
Generate "One Concept Deep" number learning videos via Remotion.
One 20-min video per number per language = 20 videos total (1-10 × EN+AR).

Usage:
  python3 scripts/generate_number_learn_long.py --dry-run
  python3 scripts/generate_number_learn_long.py --number three
  python3 scripts/generate_number_learn_long.py --lang en
  python3 scripts/generate_number_learn_long.py            # all 20 videos
  python3 scripts/generate_number_learn_long.py --force
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

ROOT              = Path(__file__).resolve().parent.parent
DATA_PATH         = ROOT / "config" / "number_learn_data.yaml"
QUEUE_DIR         = ROOT / "output" / "queue"
QUEUE_AR_DIR      = ROOT / "output" / "queue_ar"
QUEUE_ID_DIR      = ROOT / "output" / "queue_id"
REMOTION          = ROOT / "remotion"
TOGETHER_KEY_FILE = ROOT / "credentials" / "together_api_key.txt"
TOGETHER_URL      = "https://api.together.xyz/v1/images/generations"
TOGETHER_MODEL    = "black-forest-labs/FLUX.1-schnell"

STYLE_BASE = (
    "children's educational YouTube thumbnail, 1280x720, "
    "bold outlines, cheerful expression, bright vivid colors, "
    "no text, clean background, simple design"
)

MUSIC_TRACKS = [
    "Gymnopedie No 1.mp3", "Heartwarming.mp3", "Crinoline Dreams.mp3",
    "Wholesome.mp3", "Carefree.mp3", "Walking Along.mp3",
    "Fluffing a Duck.mp3", "George Street Shuffle.mp3", "Life of Riley.mp3", "Merry Go.mp3",
]

EN_TAGS_BASE = [
    "learn numbers", "counting for kids", "number learning", "preschool", "toddler",
    "one two three", "educational video", "happy bear kids", "kindergarten",
    "count to ten", "number recognition", "math for kids",
]
AR_TAGS_BASE = [
    "تعلم الأرقام", "العد للأطفال", "أرقام للأطفال", "تعليم أطفال", "هابي بير كيدز",
    "رياض الأطفال", "عد من 1 إلى 10", "الرياضيات للأطفال",
]
ID_TAGS_BASE = [
    "belajar angka", "menghitung untuk anak", "angka untuk anak", "belajar anak",
    "happy bear kids", "prasekolah", "hitung sampai 10", "matematika anak",
]


def load_data() -> list:
    with open(DATA_PATH) as f:
        return yaml.safe_load(f)["numbers"]


def make_props(num: dict, lang: str, music_file: str) -> dict:
    rtl  = (lang == "ar")
    if lang == "id":
        name_loc   = lambda o: o.get("name_id", o["name_en"]).capitalize()
        plural_loc = lambda o: o.get("plural_id", o["plural_en"]).capitalize()
        num_name   = num.get("name_id", num["name_en"]).capitalize()
    elif rtl:
        name_loc   = lambda o: o["name_ar"]
        plural_loc = lambda o: o["plural_ar"]
        num_name   = num["name_ar"]
    else:
        name_loc   = lambda o: o["name_en"].capitalize()
        plural_loc = lambda o: o["plural_en"].capitalize()
        num_name   = num["name_en"]
    objs = [
        {
            "name":            o["name_en"],
            "nameLocalized":   name_loc(o),
            "pluralLocalized": plural_loc(o),
            "spritePath":      o["sprite"],
        }
        for o in num["objects"]
    ]
    return {
        "numberValue":  num["value"],
        "numberName":   num_name,
        "numberDigit":  num["digit"],
        "accentColor":  num["accent"],
        "bgColor":      num["bg"],
        "rtl":          rtl,
        "lang":         lang,
        "numberKey":    num["key"],
        "musicFile":    music_file,
        "objects":      objs,
    }


def make_meta(num: dict, lang: str, out_path: Path):
    rtl        = (lang == "ar")
    digit      = num["digit"]
    if lang == "id":
        num_name  = num.get("name_id", num["name_en"]).capitalize()
        obj_names = [o.get("name_id", o["name_en"]) for o in num["objects"]]
        tags_base = ID_TAGS_BASE
    elif rtl:
        num_name  = num["name_ar"]
        obj_names = [o["name_ar"] for o in num["objects"]]
        tags_base = AR_TAGS_BASE
    else:
        num_name  = num["name_en"]
        obj_names = [o["name_en"] for o in num["objects"]]
        tags_base = EN_TAGS_BASE
    name_cap   = num["name_en"].capitalize()
    name_lower = num["name_en"].lower()

    if lang == "en":
        title = (
            f"Learn Number {digit} — {name_cap} for Kids! "
            f"20 Minutes | Happy Bear Kids"
        )
        description = (
            f"🔢 Today we learn the number {digit} — {name_cap}!\n\n"
            f"This 20-minute educational video uses the \"One Concept Deep\" method. "
            f"Instead of rushing through all numbers at once, we spend a full 20 minutes "
            f"learning just the number {digit}. Every scene repeats {digit} in a new fun way, "
            f"building deep counting memory for toddlers and preschoolers.\n\n"
            f"What we practice in this video:\n"
            f"🔢 {name_cap} {obj_names[0]}s — count along one by one!\n"
            f"🔢 {name_cap} {obj_names[1]}s — how many do you see?\n"
            f"🔢 {name_cap} {obj_names[2]}s — let's count together!\n"
            f"🖐️ Finger counting activity — hold up {digit} fingers!\n"
            f"🎵 The number {digit} song — sing along!\n\n"
            f"Each counting scene shows objects appearing one by one with bright number badges. "
            f"After each scene we pause so your child can count along out loud. "
            f"Research shows that interactive counting with pauses builds "
            f"math skills far faster than passive watching.\n\n"
            f"🌟 Why this video works:\n"
            f"• One number only — deep focus builds real counting skill\n"
            f"• 7+ repetitions — objects appear in 3 different counting scenes\n"
            f"• Finger counting activity — connects number to body memory\n"
            f"• Objects appear one by one with animated number badge\n"
            f"• 1-second pause between each count — child counts along!\n"
            f"• Positive reinforcement — celebrate every correct count\n"
            f"• Gentle pace — great as background video during play time\n"
            f"• Safe, calm content for babies and toddlers ages 1–4\n\n"
            f"Part of the complete Number 1 to 10 series!\n"
            f"1 · 2 · 3 · 4 · 5 · 6 · 7 · 8 · 9 · 10\n\n"
            f"🔔 Subscribe to Happy Bear Kids → @HappyBearKids1\n"
            f"New educational videos every week!\n\n"
            f"🎵 Background Music: Kevin MacLeod (incompetech.com)\n"
            f"Licensed under Creative Commons Attribution 4.0\n"
            f"http://creativecommons.org/licenses/by/4.0/\n\n"
            f"#LearnNumbers #CountingForKids #Number{digit} #{name_cap}ForKids "
            f"#ToddlerLearning #PreschoolMath #HappyBearKids #BabyLearning "
            f"#CountTo{digit} #KidsEducation #MathForKids\n\n"
            f"© Happy Bear Kids 2026"
        )
        tags = tags_base + [
            digit, name_lower,
            f"number {digit}", f"count to {digit}",
            f"learn {digit}", f"learn {name_lower}",
        ] + obj_names
    elif lang == "ar":
        title = f"تعلم الرقم {digit} — {num_name} | 20 دقيقة | هابي بير كيدز"
        description = (
            f"🔢 اليوم نتعلم الرقم {digit} — {num_name}!\n\n"
            f"هذا الفيديو التعليمي لمدة 20 دقيقة يستخدم طريقة \"التعمق في مفهوم واحد\". "
            f"بدلاً من التسرع في تعلم جميع الأرقام دفعة واحدة، نقضي 20 دقيقة كاملة "
            f"في تعلم الرقم {digit} فقط. كل مشهد يكرر {digit} بطريقة ممتعة جديدة، "
            f"مما يبني ذاكرة عميقة للعد لدى الرضع وأطفال ما قبل المدرسة.\n\n"
            f"ماذا نتدرب عليه في هذا الفيديو:\n"
            f"🔢 {num_name} {obj_names[0]} — عد معنا واحداً تلو الآخر!\n"
            f"🔢 {num_name} {obj_names[1]} — كم تعد؟\n"
            f"🔢 {num_name} {obj_names[2]} — هيا نعد معاً!\n"
            f"🖐️ نشاط العد بالأصابع — ارفع {digit} أصابع!\n"
            f"🎵 أغنية الرقم {digit} — اغنِ معنا!\n\n"
            f"كل مشهد عد يُظهر الأشياء واحداً تلو الآخر مع شارات أرقام مضيئة. "
            f"بعد كل مشهد نتوقف ليتمكن طفلك من العد بصوت عالٍ. "
            f"تُثبت الأبحاث أن العد التفاعلي مع التوقفات يبني "
            f"مهارات الرياضيات أسرع بكثير من المشاهدة السلبية.\n\n"
            f"🌟 لماذا يُجدي هذا الفيديو:\n"
            f"• رقم واحد فقط — التركيز العميق يبني مهارة العد الحقيقية\n"
            f"• 7+ تكرارات — الأشياء تظهر في 3 مشاهد عد مختلفة\n"
            f"• نشاط العد بالأصابع — يربط الرقم بذاكرة الجسم\n"
            f"• الأشياء تظهر واحداً تلو الآخر مع شارة رقم متحركة\n"
            f"• توقف لمدة ثانية بين كل عدد — الطفل يعد معنا!\n"
            f"• تعزيز إيجابي — نحتفل بكل عد صحيح\n"
            f"• إيقاع هادئ — رائع كفيديو خلفية أثناء اللعب\n"
            f"• محتوى آمن وهادئ للرضع والأطفال من 1–4 سنوات\n\n"
            f"جزء من سلسلة الأرقام 1 إلى 10 الكاملة!\n"
            f"١ · ٢ · ٣ · ٤ · ٥ · ٦ · ٧ · ٨ · ٩ · ١٠\n\n"
            f"🔔 اشتركوا في هابي بير كيدز → @HappyBearKids1\n"
            f"فيديوهات تعليمية جديدة كل أسبوع!\n\n"
            f"🎵 الموسيقى الخلفية: Kevin MacLeod (incompetech.com)\n"
            f"رخصة Creative Commons Attribution 4.0\n"
            f"http://creativecommons.org/licenses/by/4.0/\n\n"
            f"#تعلم_الأرقام #العد_للأطفال #رقم_{digit} #تعليم_أطفال "
            f"#هابي_بير_كيدز #رياض_الأطفال #أرقام_للأطفال #عد_مع_أطفال\n\n"
            f"© هابي بير كيدز 2026"
        )
        tags = tags_base + [
            digit, num_name,
            f"رقم {digit}", f"العد إلى {digit}",
            f"تعلم {digit}", f"تعلم {num_name}",
        ] + obj_names
    elif lang == "id":
        title = (
            f"Belajar Angka {digit} — {num_name} untuk Anak! "
            f"20 Menit | Happy Bear Kids Indonesia"
        )
        description = (
            f"🔢 Hari ini kita belajar angka {digit} — {num_name}!\n\n"
            f"Video edukatif 20 menit ini menggunakan metode \"Satu Konsep Mendalam\". "
            f"Daripada terburu-buru mempelajari semua angka sekaligus, kita menghabiskan 20 menit "
            f"penuh untuk belajar angka {digit} saja. Setiap adegan mengulang {digit} dengan cara "
            f"baru yang menyenangkan, membangun memori menghitung yang dalam untuk balita dan "
            f"anak prasekolah.\n\n"
            f"Apa yang kita latih dalam video ini:\n"
            f"🔢 {num_name} {obj_names[0]} — hitung satu per satu!\n"
            f"🔢 {num_name} {obj_names[1]} — berapa yang kamu lihat?\n"
            f"🔢 {num_name} {obj_names[2]} — ayo hitung bersama!\n"
            f"🖐️ Aktivitas menghitung dengan jari — angkat {digit} jari!\n"
            f"🎵 Lagu angka {digit} — nyanyikan bersama!\n\n"
            f"Setiap adegan menampilkan benda-benda muncul satu per satu dengan lencana angka "
            f"berwarna cerah. Setelah setiap adegan kita berhenti agar anak bisa menghitung "
            f"dengan keras. Penelitian menunjukkan bahwa menghitung interaktif dengan jeda "
            f"membangun keterampilan matematika jauh lebih cepat daripada menonton pasif.\n\n"
            f"🌟 Mengapa video ini berhasil:\n"
            f"• Satu angka saja — fokus mendalam membangun keterampilan menghitung nyata\n"
            f"• 7+ pengulangan — benda muncul dalam 3 adegan menghitung berbeda\n"
            f"• Aktivitas menghitung dengan jari — menghubungkan angka dengan memori tubuh\n"
            f"• Benda muncul satu per satu dengan lencana angka animasi\n"
            f"• Jeda 1 detik antara setiap hitungan — anak ikut menghitung!\n"
            f"• Penguatan positif — rayakan setiap hitungan yang benar\n"
            f"• Tempo lembut — bagus sebagai video latar saat waktu bermain\n"
            f"• Konten aman dan tenang untuk bayi dan balita usia 1–4 tahun\n\n"
            f"Bagian dari seri Angka 1 sampai 10 yang lengkap!\n"
            f"1 · 2 · 3 · 4 · 5 · 6 · 7 · 8 · 9 · 10\n\n"
            f"🔔 Subscribe ke Happy Bear Kids Indonesia → @happybearkidsin\n"
            f"Video edukatif baru setiap minggu!\n\n"
            f"🎵 Musik Latar: Kevin MacLeod (incompetech.com)\n"
            f"Berlisensi Creative Commons Attribution 4.0\n"
            f"http://creativecommons.org/licenses/by/4.0/\n\n"
            f"#BelajarAngka #MenghitungUntukAnak #Angka{digit} #{num_name}UntukAnak "
            f"#BelajarAnak #PresekolahIndonesia #HappyBearKids #BayiBelajar "
            f"#HitungBersama #VideoEdukasi #MatematikaAnak\n\n"
            f"© Happy Bear Kids Indonesia 2026"
        )
        tags = tags_base + [
            digit, num_name.lower(),
            f"angka {digit}", f"hitung sampai {digit}",
            f"belajar {digit}", f"belajar {num_name.lower()}",
        ] + obj_names

    meta = {
        "title":       title,
        "description": description,
        "tags":        tags[:40],
        "video_type":  "numbers",
        "theme":       num["key"],
        "language":    lang,
        "status":      "public",
        "is_short":    False,
    }
    meta_path = out_path.parent / f"meta_{out_path.stem}.yaml"
    with open(meta_path, "w") as f:
        yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    print(f"    meta → {meta_path.name}")


def generate_thumbnail(num: dict, lang: str, out_path: Path, force: bool = False) -> bool:
    """Generate AI thumbnail via Together.ai and save as thumb_{stem}.png."""
    thumb_path = out_path.parent / f"thumb_{out_path.stem}.png"
    if thumb_path.exists() and not force:
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

    key       = TOGETHER_KEY_FILE.read_text().strip()
    digit     = num["digit"]
    name_en   = num["name_en"].lower()
    obj_en    = [o["name_en"] for o in num["objects"]]
    acc_color = num["accent"]

    if lang == "ar":
        prompt = (
            f"Big bold cartoon number {digit}, cute {obj_en[0]} and {obj_en[1]} "
            f"characters, educational kids YouTube thumbnail, "
            f"bright colorful background with stars and confetti, "
            f"number {digit} large and central, cheerful friendly style, "
            f"bold outlines, no text, no letters, no words, 1280x720"
        )
    else:
        prompt = (
            f"Big bold cartoon number {digit} with cute {obj_en[0]} and {obj_en[1]}, "
            f"educational kids YouTube thumbnail, "
            f"bright colorful background with stars and confetti, "
            f"number {digit} large and central, cheerful style, "
            f"bold outlines, no text, 1280x720, {STYLE_BASE}"
        )

    print(f"    Generating thumbnail (number {digit})...")
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


def render_video(num: dict, lang: str, force: bool, dry_run: bool) -> bool:
    key      = num["key"]
    date_str = datetime.now().strftime("%Y%m%d")
    fname    = f"number_learn_{key}_{lang}_{date_str}.mp4"
    if lang == "ar":
        dest_dir = QUEUE_AR_DIR
    elif lang == "id":
        dest_dir = QUEUE_ID_DIR
    else:
        dest_dir = QUEUE_DIR
    out_path = dest_dir / fname

    if out_path.exists() and not force:
        print(f"  skip {fname} ({out_path.stat().st_size/1024/1024:.1f}MB)")
        return True

    all_nums   = load_data()
    num_idx    = [n["key"] for n in all_nums].index(key)
    music_file = MUSIC_TRACKS[num_idx % len(MUSIC_TRACKS)]
    props      = make_props(num, lang, music_file)
    props_json = json.dumps(props)

    print(f"\n  Rendering: {fname}")
    print(f"    Number: {num['name_en']} / {num['name_ar']} ({num['digit']}) | lang={lang}")
    print(f"    Music: {music_file}")

    if dry_run:
        print(f"    [DRY RUN] {props_json[:100]}...")
        make_meta(num, lang, out_path)
        return True

    dest_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "npx", "remotion", "render",
        "src/index.ts", "NumberLearnLong",
        str(out_path),
        "--props", props_json,
        "--concurrency", "1",
        "--log", "error",
    ]

    print(f"    Running remotion render...")
    result = subprocess.run(
        cmd, cwd=str(REMOTION),
        capture_output=True, text=True,
        timeout=21600,  # 6h max per video
    )

    if result.returncode == 0 and out_path.exists():
        size_mb = out_path.stat().st_size / 1024 / 1024
        print(f"    ✓ {fname} ({size_mb:.1f}MB)")
        make_meta(num, lang, out_path)
        time.sleep(2)
        generate_thumbnail(num, lang, out_path, force=force)
        return True
    else:
        print(f"    ✗ FAILED: {result.stderr[-300:]}")
        return False


def regen_metas(number_filter: str | None, lang_filter: str | None):
    """Regenerate meta+thumbnail for every existing number MP4 in queue dirs."""
    nums_by_key = {n["key"]: n for n in load_data()}
    updated = 0
    for queue_dir in [QUEUE_DIR, QUEUE_AR_DIR, QUEUE_ID_DIR]:
        for mp4 in sorted(queue_dir.glob("number_learn_*.mp4")):
            parts = mp4.stem.split("_")
            # stem: number_learn_{key}_{lang}_{date}
            if len(parts) < 4:
                continue
            key  = parts[2]
            lang = parts[3]
            if number_filter and key != number_filter:
                continue
            if lang_filter and lang != lang_filter:
                continue
            num = nums_by_key.get(key)
            if not num:
                print(f"  unknown key '{key}' in {mp4.name}")
                continue
            print(f"\n  Regen meta+thumb: {mp4.name}")
            make_meta(num, lang, mp4)
            time.sleep(1)
            generate_thumbnail(num, lang, mp4)
            updated += 1
    print(f"\nRegen done: {updated} meta files updated")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--number",     help="Single number key e.g. three")
    parser.add_argument("--lang",       choices=["en", "ar", "id"])
    parser.add_argument("--force",      action="store_true")
    parser.add_argument("--dry-run",    action="store_true")
    parser.add_argument("--regen-meta", action="store_true",
                        help="Regenerate meta+thumbnail for existing MP4s (no re-render)")
    args = parser.parse_args()

    if args.regen_meta:
        regen_metas(args.number, args.lang)
        return

    numbers = load_data()
    if args.number:
        numbers = [n for n in numbers if n["key"] == args.number]
        if not numbers:
            print(f"Number '{args.number}' not found.")
            sys.exit(1)

    langs = [args.lang] if args.lang else ["en", "ar", "id"]
    print(f"\nNumber Learn Long — {len(numbers)} numbers × {len(langs)} languages = {len(numbers)*len(langs)} videos")

    ok = fail = 0
    for num in numbers:
        for lang in langs:
            if render_video(num, lang, args.force, args.dry_run):
                ok += 1
            else:
                fail += 1

    print(f"\nDone: {ok} rendered, {fail} failed")


if __name__ == "__main__":
    main()
