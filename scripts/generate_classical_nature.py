#!/usr/bin/env python3
"""
generate_classical_nature.py — Classical music + NatureCalm nature backgrounds.

Series: "Classical in Nature" — Bach in a forest meadow, Chopin under the night
sky, Swan Lake underwater, Moonlight Sonata beneath the moon.

Pipeline:
  1. Render shared NatureCalm loops (4 themes × 3 langs = 12 × 5-min clips)
  2. FFmpeg: stream_loop -1 the clip + music file → 60-min video per piece × lang
  3. Generate meta (EN/AR/ID) + FLUX thumbnail per piece

Output: output/queue/, output/queue_ar/, output/queue_id/
Filename: nature_classical_{key}_{lang}_{date}.mp4

Usage:
  python3 scripts/generate_classical_nature.py               # all 18 pieces
  python3 scripts/generate_classical_nature.py --keys bach_cello swan_lake_act2_pt1
  python3 scripts/generate_classical_nature.py --dry-run
  python3 scripts/generate_classical_nature.py --render-loops-only
  python3 scripts/generate_classical_nature.py --regen-meta
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

ROOT      = Path(__file__).resolve().parent.parent
REMOTION  = ROOT / "remotion"
TMP_DIR   = ROOT / "tmp" / "nature_loops"
MUSIC1    = ROOT / "assets" / "music" / "mozart"
MUSIC2    = ROOT / "assets" / "music" / "classical" / "Music"
QUEUE     = {
    "en": ROOT / "output" / "queue",
    "ar": ROOT / "output" / "queue_ar",
    "id": ROOT / "output" / "queue_id",
}
TOGETHER_KEY_FILE = ROOT / "credentials" / "together_api_key.txt"
TOGETHER_URL      = "https://api.together.xyz/v1/images/generations"
TOGETHER_MODEL    = "black-forest-labs/FLUX.1-schnell"
DATE_STR = datetime.now().strftime("%Y%m%d")

THEMES     = ["meadow", "sunset", "night", "underwater"]
LANG_PHASE = {"en": 0.0, "ar": 0.33, "id": 0.67}

# ── Music file locator ─────────────────────────────────────────────────────────

def find_music(filename: str) -> Path:
    for d in [MUSIC1, MUSIC2]:
        p = d / filename
        if p.exists():
            return p
    return MUSIC2 / filename  # will fail later with clear error

# ── Piece definitions ──────────────────────────────────────────────────────────
# theme: the NatureCalm theme that best fits the piece's mood
# Each language gets phaseOffset 0/0.33/0.67 so visuals differ between channels

VIDEOS = {
    "bach_cello": {
        "music_file":    "Cello Suite no. 1 - Prelude in G, BWV 1007.mp3",
        "theme":         "meadow",
        "duration_min":  60,
        "composer_en":   "Johann Sebastian Bach",
        "work_en":       "Cello Suite No. 1 — Prelude in G (BWV 1007)",
        "work_ar":       "سويتة التشيللو رقم 1 — برلود في صول",
        "work_id":       "Cello Suite No. 1 — Prelude in G (BWV 1007)",
        "mood_en":       "Forest Meditation",
        "mood_ar":       "تأمل الغابة",
        "mood_id":       "Meditasi Hutan",
        "thumb_scene":   "peaceful forest meadow at dawn, sunlight filtering through tall oak trees, dew on green grass, Bach baroque music atmosphere, magical golden light",
    },
    "chopin_nocturne_1": {
        "music_file":    "Nocturne in B flat minor, Op. 9 no. 1.mp3",
        "theme":         "night",
        "duration_min":  60,
        "composer_en":   "Frédéric Chopin",
        "work_en":       "Nocturne in B♭ minor, Op. 9 No. 1",
        "work_ar":       "نوكتورن في سي بيمول مينور، أوب. 9 رقم 1",
        "work_id":       "Nocturne dalam B♭ minor, Op. 9 No. 1",
        "mood_en":       "Night Garden",
        "mood_ar":       "حديقة الليل",
        "mood_id":       "Taman Malam",
        "thumb_scene":   "romantic moonlit garden at night, silver moon reflecting on a still pond, fireflies glowing among dark roses, Chopin nocturne dreamy atmosphere, soft blue night light",
    },
    "chopin_nocturne_2": {
        "music_file":    "Nocturne in E flat major, Op. 9 no. 2.mp3",
        "theme":         "night",
        "duration_min":  60,
        "composer_en":   "Frédéric Chopin",
        "work_en":       "Nocturne in E♭ major, Op. 9 No. 2",
        "work_ar":       "نوكتورن في مي بيمول ماجور، أوب. 9 رقم 2",
        "work_id":       "Nocturne dalam E♭ mayor, Op. 9 No. 2",
        "mood_en":       "Starlit Night",
        "mood_ar":       "ليلة النجوم",
        "mood_id":       "Malam Berbintang",
        "thumb_scene":   "starlit night sky over a calm lake, reflections of thousands of stars on still water, weeping willow tree, Chopin romantic piano atmosphere, ethereal blue starlight",
    },
    "beethoven_moonlight": {
        "music_file":    "Piano Sonata no. 14 in C#m 'Moonlight', Op. 27 no. 2 - I. Adagio sostenuto.mp3",
        "theme":         "night",
        "duration_min":  60,
        "composer_en":   "Ludwig van Beethoven",
        "work_en":       "Moonlight Sonata, Op. 27 No. 2 — I. Adagio sostenuto",
        "work_ar":       "سوناتا ضوء القمر، أوب. 27 رقم 2 — حركة أداجيو",
        "work_id":       "Moonlight Sonata, Op. 27 No. 2 — I. Adagio sostenuto",
        "mood_en":       "Moonlight Dream",
        "mood_ar":       "حلم ضوء القمر",
        "mood_id":       "Mimpi Cahaya Bulan",
        "thumb_scene":   "moonlight reflecting on a peaceful lake at midnight, full glowing moon, silver light on rippling water, Beethoven moonlight sonata atmosphere, magical moonlit landscape",
    },
    "beethoven_5": {
        "music_file":    "Symphony no. 5 in Cm, Op. 67 - I. Allegro con brio.mp3",
        "theme":         "sunset",
        "duration_min":  60,
        "composer_en":   "Ludwig van Beethoven",
        "work_en":       "Symphony No. 5 in C minor, Op. 67 — I. Allegro con brio",
        "work_ar":       "السيمفونية رقم 5 — الحركة الأولى",
        "work_id":       "Simfoni No. 5 — I. Allegro con brio",
        "mood_en":       "Sunset Drama",
        "mood_ar":       "دراما الغروب",
        "mood_id":       "Drama Senja",
        "thumb_scene":   "dramatic sunset over rolling hills, golden and orange sky with dynamic clouds, silhouette of trees against blazing horizon, powerful Beethoven symphony atmosphere",
    },
    "mozart_romance": {
        "music_file":    "Mozart - Serenade in G Major - I. Romance.mp3",
        "theme":         "meadow",
        "duration_min":  60,
        "composer_en":   "Wolfgang Amadeus Mozart",
        "work_en":       "Serenade in G Major, K. 525 — I. Romance (Eine kleine Nachtmusik)",
        "work_ar":       "سيرينادة في صول ماجور — رومانس",
        "work_id":       "Serenade in G Mayor — I. Romance",
        "mood_en":       "Sunny Meadow",
        "mood_ar":       "المرج المشمس",
        "mood_id":       "Padang Rumput Cerah",
        "thumb_scene":   "bright sunny meadow in spring, colorful wildflowers, blue sky with fluffy white clouds, butterflies, cheerful Mozart serenade atmosphere, warm golden sunlight",
    },
    "mozart_minuet": {
        "music_file":    "Mozart - Serenade in G Major - II. Minuet.mp3",
        "theme":         "sunset",
        "duration_min":  60,
        "composer_en":   "Wolfgang Amadeus Mozart",
        "work_en":       "Serenade in G Major — II. Minuet",
        "work_ar":       "سيرينادة في صول ماجور — مينويت",
        "work_id":       "Serenade in G Mayor — II. Minuet",
        "mood_en":       "Golden Sunset",
        "mood_ar":       "غروب ذهبي",
        "mood_id":       "Senja Emas",
        "thumb_scene":   "warm golden sunset over a peaceful countryside, orange and pink clouds, gentle hills, elegant classical garden, Mozart elegant atmosphere, soft evening light",
    },
    "mozart_rondo": {
        "music_file":    "Mozart - Serenade in G Major - III. Rondo.mp3",
        "theme":         "meadow",
        "duration_min":  60,
        "composer_en":   "Wolfgang Amadeus Mozart",
        "work_en":       "Serenade in G Major — III. Rondo (Allegro)",
        "work_ar":       "سيرينادة في صول ماجور — روندو",
        "work_id":       "Serenade in G Mayor — III. Rondo",
        "mood_en":       "Joyful Meadow",
        "mood_ar":       "مرج البهجة",
        "mood_id":       "Padang Rumput Bahagia",
        "thumb_scene":   "lively spring meadow, deer grazing, blooming cherry trees, bright cheerful light, joyful Mozart rondo atmosphere, vivid colors",
    },
    "verdi_traviata": {
        "music_file":    "Giuseppe Verdi - La Traviata - I.mp3",
        "theme":         "sunset",
        "duration_min":  60,
        "composer_en":   "Giuseppe Verdi",
        "work_en":       "La Traviata — Prelude, Act I",
        "work_ar":       "لا ترافياتا — برلود من الفصل الأول",
        "work_id":       "La Traviata — Prelude, Babak I",
        "mood_en":       "Romantic Sunset",
        "mood_ar":       "غروب رومانسي",
        "mood_id":       "Senja Romantis",
        "thumb_scene":   "romantic Italian countryside at sunset, olive trees, golden hour light, dramatic opera atmosphere, warm Mediterranean colors, Verdi romantic drama",
    },
    "fantasia": {
        "music_file":    "Vaughan Williams - Fantasia on a Theme by Thomas Tallis.mp3",
        "theme":         "meadow",
        "duration_min":  60,
        "composer_en":   "Ralph Vaughan Williams",
        "work_en":       "Fantasia on a Theme by Thomas Tallis",
        "work_ar":       "فانتازيا على موضوع توماس تاليس",
        "work_id":       "Fantasia pada Tema Thomas Tallis",
        "mood_en":       "English Countryside",
        "mood_ar":       "الريف الإنجليزي",
        "mood_id":       "Pedesaan Inggris",
        "thumb_scene":   "misty English countryside morning, rolling green hills, ancient stone church in distance, pastoral sheep, Vaughan Williams pastoral atmosphere, soft morning light",
    },
    "flute_fantaisie": {
        "music_file":    "3 Fantaisies for Solo Flute, Op. 38 - Fantaisie no. 1.mp3",
        "theme":         "underwater",
        "duration_min":  60,
        "composer_en":   "Georg Philipp Telemann",
        "work_en":       "3 Fantaisies for Solo Flute, Op. 38 — Fantaisie No. 1",
        "work_ar":       "فانتازيا للفلوت المنفرد — رقم 1",
        "work_id":       "Fantaisie untuk Seruling Solo No. 1",
        "mood_en":       "Underwater Dream",
        "mood_ar":       "حلم تحت الماء",
        "mood_id":       "Mimpi Bawah Air",
        "thumb_scene":   "magical underwater world, sunlight filtering through crystal clear water, colorful coral, schools of glowing fish, flute music dreamlike underwater atmosphere",
    },
    "flute_etude_3": {
        "music_file":    "24 Etudes for Flute, Op. 15 - III. Allegro con brio in G major.mp3",
        "theme":         "meadow",
        "duration_min":  60,
        "composer_en":   "Ernesto Köhler",
        "work_en":       "24 Etudes for Flute, Op. 15 — No. 3 Allegro con brio in G major",
        "work_ar":       "24 إيتيد للفلوت — رقم 3",
        "work_id":       "24 Etudes untuk Seruling — No. 3",
        "mood_en":       "Bright Morning",
        "mood_ar":       "صباح مشرق",
        "mood_id":       "Pagi Cerah",
        "thumb_scene":   "fresh morning meadow, morning dew on wildflowers, birds in flight, bright cheerful flute music atmosphere, vibrant spring colors, sunrise light",
    },
    "flute_etude_6": {
        "music_file":    "24 Etudes for Flute, Op. 15 - VI. Moderato in B minor.mp3",
        "theme":         "sunset",
        "duration_min":  60,
        "composer_en":   "Ernesto Köhler",
        "work_en":       "24 Etudes for Flute, Op. 15 — No. 6 Moderato in B minor",
        "work_ar":       "24 إيتيد للفلوت — رقم 6",
        "work_id":       "24 Etudes untuk Seruling — No. 6",
        "mood_en":       "Evening Calm",
        "mood_ar":       "هدوء المساء",
        "mood_id":       "Ketenangan Sore",
        "thumb_scene":   "calm evening countryside, soft orange sunset, still pond reflecting warm colors, peaceful flute music atmosphere, gentle evening breeze",
    },
    "swan_lake_act2_pt1": {
        "music_file":    "Swan Lake Op.20 - Act II Pt.1.mp3",
        "theme":         "underwater",
        "duration_min":  60,
        "composer_en":   "Pyotr Ilyich Tchaikovsky",
        "work_en":       "Swan Lake, Op. 20 — Act II, Part 1",
        "work_ar":       "بحيرة البجع — الفصل الثاني، الجزء الأول",
        "work_id":       "Swan Lake, Op. 20 — Babak II, Bagian 1",
        "mood_en":       "Swan Lake Dream",
        "mood_ar":       "حلم بحيرة البجع",
        "mood_id":       "Mimpi Swan Lake",
        "thumb_scene":   "moonlit lake at night with white swans gliding on still water, silver reflection of full moon, misty lake shores, Tchaikovsky romantic ballet atmosphere",
    },
    "swan_lake_act2_concl": {
        "music_file":    "Swan Lake Op.20 - Act II Concl.mp3",
        "theme":         "underwater",
        "duration_min":  60,
        "composer_en":   "Pyotr Ilyich Tchaikovsky",
        "work_en":       "Swan Lake, Op. 20 — Act II, Conclusion",
        "work_ar":       "بحيرة البجع — خاتمة الفصل الثاني",
        "work_id":       "Swan Lake — Penutup Babak II",
        "mood_en":       "Enchanted Lake",
        "mood_ar":       "البحيرة المسحورة",
        "mood_id":       "Danau Ajaib",
        "thumb_scene":   "enchanted moonlit lake, white swan gliding in moonlight, magical blue mist rising from water, Tchaikovsky ballet enchantment, ethereal silver light",
    },
    "swan_lake_act3_pt1": {
        "music_file":    "Swan Lake Op.20 - Act III Pt.1.mp3",
        "theme":         "sunset",
        "duration_min":  60,
        "composer_en":   "Pyotr Ilyich Tchaikovsky",
        "work_en":       "Swan Lake, Op. 20 — Act III, Part 1",
        "work_ar":       "بحيرة البجع — الفصل الثالث، الجزء الأول",
        "work_id":       "Swan Lake — Babak III, Bagian 1",
        "mood_en":       "Ballroom Sunset",
        "mood_ar":       "غروب قاعة الرقص",
        "mood_id":       "Senja Ballroom",
        "thumb_scene":   "grand ballroom at sunset, golden chandelier light, red and gold colors, dramatic Tchaikovsky ballet atmosphere, elegant classical palace interior glow",
    },
    "swan_lake_act3_concl": {
        "music_file":    "Swan Lake Op.20 - Act III Concl, Allegro.mp3",
        "theme":         "sunset",
        "duration_min":  60,
        "composer_en":   "Pyotr Ilyich Tchaikovsky",
        "work_en":       "Swan Lake, Op. 20 — Act III, Finale",
        "work_ar":       "بحيرة البجع — خاتمة الفصل الثالث",
        "work_id":       "Swan Lake — Finale Babak III",
        "mood_en":       "Dramatic Finale",
        "mood_ar":       "الختام الدرامي",
        "mood_id":       "Finale Dramatis",
        "thumb_scene":   "dramatic blazing sunset, silhouette of swans flying across crimson sky, powerful Tchaikovsky finale atmosphere, dark orange clouds",
    },
    "swan_lake_act4_intro": {
        "music_file":    "Swan Lake Op.20 - Act IV Intro.mp3",
        "theme":         "night",
        "duration_min":  60,
        "composer_en":   "Pyotr Ilyich Tchaikovsky",
        "work_en":       "Swan Lake, Op. 20 — Act IV, Introduction",
        "work_ar":       "بحيرة البجع — مقدمة الفصل الرابع",
        "work_id":       "Swan Lake — Intro Babak IV",
        "mood_en":       "Moonlit Farewell",
        "mood_ar":       "وداع تحت ضوء القمر",
        "mood_id":       "Perpisahan di Bawah Bulan",
        "thumb_scene":   "moonlit lake at night, white swans in misty silver water, full moon above dark trees, melancholic Tchaikovsky farewell atmosphere, quiet magic",
    },
}

# ── Metadata generation ────────────────────────────────────────────────────────

def make_meta(key: str, lang: str) -> dict:
    v   = VIDEOS[key]
    ch  = {"en": "@HappyBearKids1", "ar": "@happybearkidsar", "id": "@happybearkidsin"}
    dur = v["duration_min"]

    composer = v["composer_en"]
    if lang == "en":
        work  = v["work_en"]
        mood  = v["mood_en"]
        title = f"{composer} — {mood} | {dur} min Classical for Babies"
        description = (
            f"🎼 {work}\n"
            f"🌿 {mood} — pure classical music for babies and toddlers.\n\n"
            f"Beautiful nature visuals paired with {composer}'s timeless masterpiece. "
            f"No words, no text — just music and nature.\n\n"
            f"✨ {dur} minutes of calm, beautiful {v['theme']} scenery with gentle "
            f"movement — clouds drifting, light shifting, nature breathing quietly.\n\n"
            f"🎯 Perfect for:\n"
            f"• Baby sleep and nap time\n"
            f"• Classical music introduction for children\n"
            f"• Calm background for play or tummy time\n"
            f"• Parent relaxation alongside baby\n"
            f"• Focus and concentration\n\n"
            f"No sudden sounds, no voices — gentle classical music as it was meant to be heard.\n\n"
            f"🎵 {work}\n"
            f"Composer: {composer}\n\n"
            f"🔔 Subscribe for daily baby animations → {ch['en']}\n"
            f"🎵 Music: Public domain classical recording.\n\n"
            f"#ClassicalForBabies #HappyBearKids #{composer.split()[-1]}Classical "
            f"#BabyClassical #NatureCalm #ClassicalMusic #BabyRelaxation "
            f"#ClassicalInNature #ToddlerMusic #BabyMeditation"
        )
        tags = [
            "classical for babies", "baby classical music", "nature calm",
            f"{composer.lower().split()[-1]}", "classical music", "baby relaxation",
            "baby meditation", "toddler music", "happy bear kids", "nature baby",
            v["mood_en"].lower(), f"{v['theme']} nature",
        ]
    elif lang == "ar":
        work  = v["work_ar"]
        mood  = v["mood_ar"]
        title = f"{composer} — {mood} | {dur} دقيقة موسيقى كلاسيكية للأطفال"
        description = (
            f"🎼 {work}\n"
            f"🌿 {mood} — موسيقى كلاسيكية خالصة للرضع والأطفال.\n\n"
            f"مناظر طبيعية جميلة مع موسيقى {composer} الخالدة. "
            f"بدون كلمات أو نصوص — فقط موسيقى وطبيعة خالصة تملأ الشاشة بالجمال والهدوء.\n\n"
            f"✨ {dur} دقيقة من المشاهد الطبيعية الهادئة مع حركة لطيفة — "
            f"غيوم تنجرف ببطء، ضوء يتحول بتدرج، طبيعة تتنفس بهدوء وسلام. "
            f"بدون مؤثرات صوتية مفاجئة، بدون حوارات — فقط الموسيقى الكلاسيكية العظيمة "
            f"تصاحب مشاهد الطبيعة الساكنة الجميلة.\n\n"
            f"🎯 مثالي لـ:\n"
            f"• نوم الطفل وقت القيلولة وعند النوم الليلي\n"
            f"• تعريف الرضع بالموسيقى الكلاسيكية منذ الصغر\n"
            f"• خلفية هادئة أثناء اللعب ووقت البطن\n"
            f"• استرخاء الوالدين مع الطفل في وقت واحد\n"
            f"• التركيز والدراسة والتأمل الهادئ\n\n"
            f"🎵 الموسيقى الكلاسيكية من أعظم الملحنين في التاريخ ثبت علميًا أن لها "
            f"تأثيرًا إيجابيًا على نمو الدماغ عند الأطفال الصغار. "
            f"استمع معنا يوميًا لخير الموسيقى الإنسانية.\n\n"
            f"الموسيقى: {work} — تسجيل في المجال العام، متاح للجميع بحرية.\n\n"
            f"🔔 اشترك في Happy Bear Kids للمزيد من المحتوى الهادئ والتعليمي → {ch['ar']}\n\n"
            f"#كلاسيكية_للأطفال #HappyBearKids #موسيقى_كلاسيكية "
            f"#استرخاء_الطفل #طبيعة_هادئة #موسيقى_للنوم #نوم_الرضع "
            f"#classical_music #baby_sleep #nature_calm #موسيقى_تأمل"
        )
        tags = [
            "كلاسيكية للأطفال", "موسيقى كلاسيكية", "استرخاء الطفل", "طبيعة هادئة",
            "موسيقى للنوم", "نوم الرضع", "موسيقى تأمل", "تعليم الأطفال",
            "happy bear kids", "classical music", "baby relaxation", "nature calm",
            "baby sleep", "classical for babies", "HappyBearKids",
        ]
    else:  # id
        work  = v["work_id"]
        mood  = v["mood_id"]
        title = f"{composer} — {mood} | {dur} Menit Klasik untuk Bayi"
        description = (
            f"🎼 {work}\n"
            f"🌿 {mood} — musik klasik murni untuk bayi dan balita.\n\n"
            f"Visual alam yang indah dipadukan dengan mahakarya {composer} yang abadi. "
            f"Tanpa kata-kata, tanpa teks — hanya musik dan alam yang mengisi layar "
            f"dengan keindahan dan ketenangan yang nyata.\n\n"
            f"✨ {dur} menit pemandangan alam yang tenang dan indah dengan gerakan lembut — "
            f"awan yang melayang perlahan, cahaya yang berubah secara bertahap, "
            f"alam yang bernapas dengan damai dan tenang. "
            f"Tanpa suara mendadak, tanpa dialog — hanya musik klasik agung "
            f"menemani pemandangan alam yang indah dan menenangkan.\n\n"
            f"🎯 Sempurna untuk:\n"
            f"• Tidur siang dan tidur malam bayi yang nyenyak\n"
            f"• Pengenalan musik klasik untuk anak sejak dini\n"
            f"• Latar belakang tenang saat bermain dan tummy time\n"
            f"• Relaksasi orang tua bersama bayi sekaligus\n"
            f"• Fokus belajar, meditasi, dan ketenangan batin\n\n"
            f"🎵 Musik klasik dari komposer terbesar sepanjang sejarah terbukti secara ilmiah "
            f"memiliki dampak positif pada perkembangan otak anak-anak kecil. "
            f"Dengarkan bersama kami setiap hari.\n\n"
            f"Musik: {work} — rekaman domain publik, tersedia bebas untuk semua.\n\n"
            f"🔔 Subscribe ke Happy Bear Kids untuk konten menenangkan dan edukatif lebih banyak "
            f"→ {ch['id']}\n\n"
            f"#KlasikUntukBayi #HappyBearKids #MusikKlasik "
            f"#RelaksasiBayi #AlamTenang #MusikTidur #TidurBayi "
            f"#classical_music #baby_sleep #nature_calm #MeditasiBayi"
        )
        tags = [
            "klasik untuk bayi", "musik klasik", "relaksasi bayi", "alam tenang",
            "musik tidur", "tidur bayi", "meditasi bayi", "edukasi anak",
            "happy bear kids", "classical music", "baby relaxation", "nature calm",
            "baby sleep", "classical for babies", "HappyBearKids",
        ]

    return {
        "title":       title,
        "description": description,
        "tags":        tags,
        "language":    lang,
        "video_type":  "nature_classical",
        "is_short":    False,
        "status":      "public",
    }

# ── Thumbnail ──────────────────────────────────────────────────────────────────

def _load_gat():
    import importlib.util
    spec = importlib.util.spec_from_file_location("gat", ROOT / "scripts" / "generate_ai_thumbs.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def gen_thumb(key: str, lang: str, out_path: Path, dry_run: bool) -> bool:
    if dry_run:
        print(f"    [DRY RUN] would generate thumb ({lang})")
        return True

    v = VIDEOS[key]
    if not TOGETHER_KEY_FILE.exists():
        print(f"    No Together.ai key at {TOGETHER_KEY_FILE}")
        return False

    api_key = TOGETHER_KEY_FILE.read_text().strip()
    no_txt  = "no text, no letters, no words, no numbers, " if lang == "ar" else ""
    prompt  = (
        f"{v['thumb_scene']}, {no_txt}dreamlike baby animation style, "
        f"beautiful soft 4K render, peaceful serene atmosphere"
    )
    try:
        gat = _load_gat()
        img = gat.together_generate_image(prompt, api_key)
        if img:
            out_path.write_bytes(gat.resize_to_720p(img))
            print(f"    ✓ thumb ({lang}): {out_path.name}")
            return True
        print(f"    ✗ thumb ({lang}) failed: API returned no image")
        return False
    except Exception as e:
        print(f"    ✗ thumb ({lang}) failed: {e}")
        return False

# ── Render shared NatureCalm loop ─────────────────────────────────────────────

def render_loop(theme: str, lang: str, out_path: Path, dry_run: bool) -> bool:
    phase = LANG_PHASE[lang]
    fps   = 30
    dur_s = 5 * 60
    frames = dur_s * fps - 1  # 0..8999

    props = json.dumps({
        "theme":       theme,
        "phaseOffset": phase,
        "musicFile":   "",   # empty string → NatureCalm plays no audio; classical piece added via FFmpeg
    })
    cmd = [
        "npx", "remotion", "render",
        "NatureCalm",
        str(out_path),
        f"--props={props}",
        f"--frames=0-{frames}",
        "--codec=h264",
        "--crf=22",
    ]
    print(f"  Render loop: {theme}/{lang} → {out_path.name}")
    if dry_run:
        print(f"    [DRY RUN] cmd: {' '.join(cmd[:4])} ...")
        return True
    result = subprocess.run(cmd, cwd=str(REMOTION))
    return result.returncode == 0

# ── FFmpeg: loop clip + overlay music → 60-min video ─────────────────────────

def assemble_video(loop_path: Path, music_path: Path, out_path: Path,
                   duration_min: int, dry_run: bool) -> bool:
    total_s = duration_min * 60
    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1", "-i", str(loop_path),   # input 0: video loop (no audio)
        "-stream_loop", "-1", "-i", str(music_path),  # input 1: classical music
        "-map", "0:v",   # video from loop
        "-map", "1:a",   # audio from classical piece only
        "-t", str(total_s),
        "-vf",  f"fade=t=out:st={total_s - 60}:d=60",
        "-af",  f"volume=0.85,afade=t=out:st={total_s - 60}:d=60",
        "-c:v", "libx264", "-crf", "22", "-preset", "fast",
        "-c:a", "aac", "-b:a", "128k",
        str(out_path),
    ]
    print(f"    [ffmpeg] → {out_path.name}")
    if dry_run:
        print(f"    [DRY RUN] skipped")
        return True
    result = subprocess.run(cmd, timeout=7200)
    return result.returncode == 0

# ── Process one piece × all languages ────────────────────────────────────────

def process_key(key: str, shared_loops: dict, dry_run: bool, regen_meta: bool) -> bool:
    v = VIDEOS[key]
    music_path = find_music(v["music_file"])
    if not music_path.exists():
        print(f"  ERROR: music not found: {music_path}")
        return False

    theme = v["theme"]
    print(f"\n{'='*65}")
    print(f"  [{key.upper()}] {v['composer_en']} — {v['work_en'][:50]}")
    print(f"  music: {v['music_file']}")
    print(f"  theme: {theme}")

    for lang in ["en", "ar", "id"]:
        q = QUEUE[lang]
        q.mkdir(parents=True, exist_ok=True)

        stem       = f"nature_classical_{key}_{lang}_{DATE_STR}"
        out_mp4    = q / f"{stem}.mp4"
        meta_path  = q / f"meta_{stem}.yaml"
        thumb_path = q / f"thumb_{stem}.png"

        print(f"\n  ── [{lang.upper()}] ──")

        if not regen_meta:
            if out_mp4.exists():
                print(f"    SKIP render — exists: {out_mp4.name}")
            else:
                loop_path = shared_loops.get(f"{theme}_{lang}")
                if not loop_path or (not dry_run and not loop_path.exists()):
                    print(f"    ERROR: loop not found for {theme}/{lang}")
                    continue
                ok = assemble_video(loop_path, music_path, out_mp4,
                                    v["duration_min"], dry_run)
                if not ok:
                    print(f"    FAILED: assemble_video ({lang})")
                    continue
        else:
            if not out_mp4.exists():
                print(f"    SKIP ({lang}) — no mp4 yet")
                continue

        if not dry_run:
            meta = make_meta(key, lang)
            meta_path.write_text(yaml.dump(meta, allow_unicode=True, sort_keys=False))
            print(f"    Meta: {meta_path.name}")

            if not thumb_path.exists() or regen_meta:
                time.sleep(2)
                gen_thumb(key, lang, thumb_path, dry_run)
            else:
                print(f"    Thumb exists: {thumb_path.name}")
        else:
            print(f"    [DRY RUN] meta + thumb for {lang}")

    return True

# ── Render/cache all shared loops ─────────────────────────────────────────────

def ensure_loops(dry_run: bool) -> dict:
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    used_themes = {v["theme"] for v in VIDEOS.values()}
    shared = {}
    for theme in used_themes:
        for lang in ["en", "ar", "id"]:
            loop_path = TMP_DIR / f"loop_{theme}_{lang}.mp4"
            shared[f"{theme}_{lang}"] = loop_path
            if not loop_path.exists():
                ok = render_loop(theme, lang, loop_path, dry_run)
                if not ok and not dry_run:
                    print(f"  ERROR: failed to render loop {theme}/{lang}")
    return shared

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Classical music + NatureCalm visuals")
    parser.add_argument("--keys", nargs="+", choices=list(VIDEOS.keys()),
                        help="Pieces to process (default: all)")
    parser.add_argument("--dry-run",            action="store_true")
    parser.add_argument("--render-loops-only",  action="store_true",
                        help="Only render shared NatureCalm loop files, skip assembly")
    parser.add_argument("--regen-meta",         action="store_true",
                        help="Re-generate meta + thumbnail only (no render)")
    parser.add_argument("--force",              action="store_true",
                        help="Re-render even if output exists")
    args = parser.parse_args()

    keys  = args.keys or list(VIDEOS.keys())
    total = len(VIDEOS)
    n     = len(keys)
    print(f"\nClassical in Nature — {n}/{total} piece(s) × 3 channels = {n * 3} videos")
    if args.dry_run:
        print("DRY RUN mode")

    # Step 1: shared NatureCalm loops
    shared = ensure_loops(args.dry_run)

    if args.render_loops_only:
        print("\n--render-loops-only: done.")
        return

    # Step 2: assemble videos
    ok_count = 0
    for key in keys:
        ok = process_key(key, shared, args.dry_run, args.regen_meta)
        if ok:
            ok_count += 1

    print(f"\n{'='*65}")
    print(f"Done: {ok_count}/{n} pieces processed.")
    print("Check queues:")
    for lang in ["en", "ar", "id"]:
        print(f"  python3 scripts/publish_queue.py --dry-run --queue {lang} --type long")


if __name__ == "__main__":
    main()
