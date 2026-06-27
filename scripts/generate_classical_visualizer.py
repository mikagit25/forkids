#!/usr/bin/env python3
"""
Generate classical music visualizer videos for all 3 channels.

THEME ROTATION approach:
  Each 60-min video cycles through 4 visual themes (15 min each):
    stars → ocean → garden → forest
  Different pieces and channels start at different offsets so YouTube
  cannot detect duplicate content across videos.

  Shared Remotion loop files (12 total: 4 themes × 3 channels) are
  rendered once and reused for all 7 classical pieces — only FFmpeg
  assembly differs per piece.

7 pieces × 3 channels = 21 videos total.

Usage:
  python3 scripts/generate_classical_visualizer.py
  python3 scripts/generate_classical_visualizer.py --keys fantasia beethoven_5
  python3 scripts/generate_classical_visualizer.py --dry-run
  python3 scripts/generate_classical_visualizer.py --regen-meta
  python3 scripts/generate_classical_visualizer.py --render-loops-only
"""

import argparse
import base64
import json
import subprocess
import time
import yaml
import requests
from datetime import datetime
from pathlib import Path

ROOT      = Path(__file__).resolve().parent.parent
REMOTION  = ROOT / "remotion"
QUEUE_EN  = ROOT / "output" / "queue"
QUEUE_AR  = ROOT / "output" / "queue_ar"
QUEUE_ID  = ROOT / "output" / "queue_id"
TMP_DIR   = ROOT / "output" / "tmp_classical"
MUSIC_DIR = ROOT / "assets" / "music" / "mozart"

TOGETHER_KEY_FILE = ROOT / "credentials" / "together_api_key.txt"
TOGETHER_URL      = "https://api.together.xyz/v1/images/generations"

DATE_STR = datetime.now().strftime("%Y%m%d")

BG_TOP    = "#03020E"
BG_BOTTOM = "#070410"

# 4 visual themes in cyclic order
THEME_ORDER = ["stars", "ocean", "garden", "forest"]

THEME_COLORS = {
    "stars":  {"accent": "#C8A84B", "eq": "#D4B86A"},
    "ocean":  {"accent": "#3399BB", "eq": "#00CCDD"},
    "garden": {"accent": "#88BB55", "eq": "#CCEE88"},
    "forest": {"accent": "#44AA66", "eq": "#66FF88"},
}

# Base offset into THEME_ORDER for the first visual segment of each piece (EN channel).
# AR shifts by +1, ID shifts by +2 — so each channel sees a different theme first.
PIECE_BASE = {
    "fantasia":      0,   # en: stars  ar: ocean  id: garden
    "mozart_romance": 1,  # en: ocean  ar: garden id: forest
    "mozart_minuet":  2,  # en: garden ar: forest id: stars
    "mozart_rondo":   3,  # en: forest ar: stars  id: ocean
    "beethoven_5":   0,   # en: stars  ar: ocean  id: garden
    "verdi_traviata": 1,  # en: ocean  ar: garden id: forest
    "flute_fantaisie": 2, # en: garden ar: forest id: stars
}

LANG_SHIFT = {"en": 0, "ar": 1, "id": 2}

LANG_CONFIGS = {
    "en": {"queue": QUEUE_EN, "phase": 0.0},
    "ar": {"queue": QUEUE_AR, "phase": 0.37},
    "id": {"queue": QUEUE_ID, "phase": 0.68},
}

# ─── piece definitions ───────────────────────────────────────────────────────

VIDEOS = {
    "fantasia": {
        "music_file":  "Vaughan Williams - Fantasia on a Theme by Thomas Tallis.mp3",
        "duration_min": 60,
        "composer_en": "Ralph Vaughan Williams",
        "work_en":     "Fantasia on a Theme by Thomas Tallis",
        "work_ar":     "فنتازيا على موضوع توماس تاليس",
        "work_id":     "Fantasia on a Theme by Thomas Tallis",
        "year":        "1910",
        "license_en":  "Public Domain — Performed by The U.S. Army Strings (Musopen, CC0)",
        "license_ar":  "ملكية عامة — بأداء The U.S. Army Strings (Musopen، CC0)",
        "license_id":  "Domain Publik — Dimainkan oleh The U.S. Army Strings (Musopen, CC0)",
        "intro_en": (
            "Ralph Vaughan Williams (1872–1958) composed this extraordinary work in 1910 "
            "for double string orchestra. Based on a 16th-century psalm tune by Thomas Tallis, "
            "it is one of the most serene and transcendent pieces in the orchestral repertoire. "
            "Running nearly 15 minutes, the Fantasia builds from ethereal whispers to grand "
            "orchestral swells and back again — perfectly suited for deep relaxation or sleep. "
            "In this 1-hour version the piece plays on a continuous loop, filling the room "
            "with an unbroken wave of calm."
        ),
        "intro_ar": (
            "ألّف رالف فون ويليامز (1872–1958) هذا العمل الرائع عام 1910 لفرقة وترية مزدوجة. "
            "يعتمد على لحن مزمور يعود للقرن السادس عشر من تأليف توماس تاليس، "
            "ويُعدّ من أكثر المقطوعات الأوركسترالية هدوءًا وسموًا. "
            "تمتد الفنتازيا قرابة خمس عشرة دقيقة تبدأ بهمسات أثيرية تعلو إلى أمواج أوركسترالية فخمة ثم تعود. "
            "في هذا الإصدار الذي يمتد لساعة كاملة، تتكرر المقطوعة في حلقة متواصلة."
        ),
        "intro_id": (
            "Ralph Vaughan Williams (1872–1958) menggubah karya luar biasa ini pada tahun 1910 "
            "untuk orkestra dawai ganda. Berdasarkan lagu mazmur abad ke-16 karya Thomas Tallis, "
            "ini adalah salah satu karya orkestra paling tenang dan transenden dalam repertoar. "
            "Berdurasi hampir 15 menit, Fantasia berkembang dari bisikan halus hingga gelombang "
            "orkestra yang megah lalu kembali lagi — sempurna untuk relaksasi mendalam atau tidur. "
            "Dalam versi 1 jam ini, karya tersebut berputar terus-menerus."
        ),
    },

    "mozart_romance": {
        "music_file":  "Mozart - Serenade in G Major - I. Romance.mp3",
        "duration_min": 60,
        "composer_en": "Wolfgang Amadeus Mozart",
        "work_en":     "Serenade in G Major K.525 «Eine kleine Nachtmusik» — I. Romanze",
        "work_ar":     "سيريناد في صول الكبير K.525 — الحركة الأولى: رومانس",
        "work_id":     "Serenade in G Major K.525 «Eine kleine Nachtmusik» — I. Romanze",
        "year":        "1787",
        "license_en":  "Public Domain (1787) — Advent Chamber Orchestra, Musopen (CC0)",
        "license_ar":  "ملكية عامة (1787) — أداء Advent Chamber Orchestra، Musopen (CC0)",
        "license_id":  "Domain Publik (1787) — Advent Chamber Orchestra, Musopen (CC0)",
        "intro_en": (
            "The Romanze from Mozart's Serenade K.525 — «Eine kleine Nachtmusik» — "
            "is one of the most tender, heart-warming melodies ever written. "
            "Composed in 1787, this slow movement with its singing string melody "
            "is perfect for winding down, deep focus, or drifting gently to sleep. "
            "Mozart wrote it as a private gift, and it has since become beloved "
            "the world over for its simplicity and quiet beauty. "
            "In this 1-hour version it plays on loop, creating an unbroken cocoon of calm."
        ),
        "intro_ar": (
            "رومانس موتسارت من سيريناد K.525 «Eine kleine Nachtmusik» "
            "هي واحدة من أكثر الألحان دفئًا وأكثرها إلهامًا على الإطلاق. "
            "أُلِّفت عام 1787، وهذه الحركة البطيئة بلحنها الوتري الغنائي "
            "مثالية للاسترخاء أو التركيز العميق أو الانجراف إلى النوم الهانئ. "
            "في هذا الإصدار لمدة ساعة كاملة تتكرر في حلقة متواصلة."
        ),
        "intro_id": (
            "Romanze dari Serenade K.525 Mozart — «Eine kleine Nachtmusik» — "
            "adalah salah satu melodi paling lembut dan menghangatkan hati yang pernah ditulis. "
            "Digubah tahun 1787, gerakan lambat dengan melodi dawai yang merdu ini "
            "sempurna untuk bersantai, fokus mendalam, atau terlelap perlahan. "
            "Dalam versi 1 jam ini dimainkan secara berulang tanpa henti."
        ),
    },

    "mozart_minuet": {
        "music_file":  "Mozart - Serenade in G Major - II. Minuet.mp3",
        "duration_min": 60,
        "composer_en": "Wolfgang Amadeus Mozart",
        "work_en":     "Serenade in G Major K.525 «Eine kleine Nachtmusik» — II. Menuett",
        "work_ar":     "سيريناد في صول الكبير K.525 — الحركة الثانية: مينويت",
        "work_id":     "Serenade in G Major K.525 «Eine kleine Nachtmusik» — II. Menuett",
        "year":        "1787",
        "license_en":  "Public Domain (1787) — Advent Chamber Orchestra, Musopen (CC0)",
        "license_ar":  "ملكية عامة (1787) — أداء Advent Chamber Orchestra، Musopen (CC0)",
        "license_id":  "Domain Publik (1787) — Advent Chamber Orchestra, Musopen (CC0)",
        "intro_en": (
            "The Menuett from Mozart's Serenade K.525 — «Eine kleine Nachtmusik» — "
            "is a gentle, elegant dance in triple time. Composed in 1787, "
            "this movement is one of the most graceful in all of chamber music, "
            "with its soft ternary rhythm naturally slowing the heartbeat toward rest. "
            "Just over two minutes long in its original form, it returns here in an "
            "hour-long loop — a perfect companion for reading, rest, or quiet study."
        ),
        "intro_ar": (
            "مينويت موتسارت من سيريناد K.525 رقصة أنيقة رقيقة في وتيرة ثلاثية. "
            "أُلِّفت عام 1787، وهي من أرشق الحركات في موسيقى الغرفة بأسرها، "
            "إذ يُبطئ إيقاعها الثلاثي دقات القلب نحو الهدوء. "
            "تعود هنا في حلقة لمدة ساعة كاملة — رفيق مثالي للقراءة أو الراحة."
        ),
        "intro_id": (
            "Menuett dari Serenade K.525 Mozart — «Eine kleine Nachtmusik» — "
            "adalah tarian anggun dan lembut dalam irama tiga ketuk. Digubah tahun 1787, "
            "gerakan ini adalah salah satu yang paling elegan dalam seluruh musik kamar, "
            "dengan ritme ternary lembutnya yang secara alami memperlambat detak jantung menuju istirahat. "
            "Hadir di sini dalam putaran satu jam — teman sempurna untuk membaca atau bersantai."
        ),
    },

    "mozart_rondo": {
        "music_file":  "Mozart - Serenade in G Major - III. Rondo.mp3",
        "duration_min": 60,
        "composer_en": "Wolfgang Amadeus Mozart",
        "work_en":     "Serenade in G Major K.525 «Eine kleine Nachtmusik» — III. Rondo (Allegro)",
        "work_ar":     "سيريناد في صول الكبير K.525 — الحركة الثالثة: روندو",
        "work_id":     "Serenade in G Major K.525 «Eine kleine Nachtmusik» — III. Rondo",
        "year":        "1787",
        "license_en":  "Public Domain (1787) — Advent Chamber Orchestra, Musopen (CC0)",
        "license_ar":  "ملكية عامة (1787) — أداء Advent Chamber Orchestra، Musopen (CC0)",
        "license_id":  "Domain Publik (1787) — Advent Chamber Orchestra, Musopen (CC0)",
        "intro_en": (
            "Mozart's Rondo from his beloved Serenade K.525 — «Eine kleine Nachtmusik» — "
            "is one of the most joyful and uplifting pieces ever written. "
            "Composed in 1787, this finale movement brings a sparkling lightness that gently "
            "carries the mind into a peaceful, happy state. "
            "Its recurring main theme bounces back like a cheerful greeting, "
            "making it ideal as a bright yet calming background for play, learning, or rest. "
            "In this 1-hour version it loops continuously for uninterrupted joy."
        ),
        "intro_ar": (
            "روندو موتسارت من سيريناد K.525 «Eine kleine Nachtmusik» "
            "هو واحد من أكثر المقطوعات بهجةً وإلهامًا على الإطلاق. "
            "أُلِّف عام 1787، وتضفي هذه الحركة الختامية خفّةً متألقة "
            "تحمل العقل إلى حالة هادئة ومبهجة. "
            "موضوعها الرئيسي المتكرر يعود كتحية مفرحة، "
            "مثالية للعب أو التعلم أو الراحة في هذا الإصدار الذي يدوم ساعة كاملة."
        ),
        "intro_id": (
            "Rondo Mozart dari Serenade K.525 — «Eine kleine Nachtmusik» — "
            "adalah salah satu karya paling gembira dan mengangkat semangat yang pernah ditulis. "
            "Digubah tahun 1787, gerakan finale ini membawa keceriaan yang lembut "
            "membawa pikiran ke keadaan damai dan bahagia. "
            "Tema utamanya yang berulang seperti sapaan ceria, "
            "ideal sebagai latar ceria namun menenangkan untuk bermain, belajar, atau beristirahat. "
            "Dalam versi 1 jam ini berputar terus-menerus."
        ),
    },

    "beethoven_5": {
        "music_file":  "Beethoven - Symphony No. 5 Complete.mp3",
        "duration_min": 60,
        "composer_en": "Ludwig van Beethoven",
        "work_en":     "Symphony No. 5 in C minor, Op. 67",
        "work_ar":     "السيمفونية الخامسة في دو الصغير، أوبوس 67",
        "work_id":     "Simfoni No. 5 dalam C minor, Op. 67",
        "year":        "1808",
        "license_en":  "Public Domain (1808) — DHS Symphony Orchestra, Musopen (CC0)",
        "license_ar":  "ملكية عامة (1808) — أداء DHS Symphony Orchestra، Musopen (CC0)",
        "license_id":  "Domain Publik (1808) — DHS Symphony Orchestra, Musopen (CC0)",
        "intro_en": (
            "Ludwig van Beethoven's Fifth Symphony (1808) is one of the most iconic works "
            "in all of Western music. Its opening four-note motif — short-short-short-LONG — "
            "has echoed through two centuries of history and become the most recognisable "
            "musical phrase on Earth. All four movements are included in full: "
            "the driving Allegro con brio, the lyrical Andante con moto, "
            "the mysterious Allegro Scherzo, and the triumphant Allegro finale — "
            "then the entire symphony loops seamlessly to fill the hour. "
            "An extraordinary piece for any age: children often respond instinctively "
            "to its rhythmic power, while adults find it a perfect companion for focus and study."
        ),
        "intro_ar": (
            "سيمفونية بيتهوفن الخامسة (1808) هي واحدة من أكثر الأعمال شهرةً "
            "في تاريخ الموسيقى الغربية بأسره. "
            "تفتتحها عبارة موسيقية لا تُنسى من أربع نوتات — قصيرة قصيرة قصيرة طويلة — "
            "تردّدت صداها عبر قرنين من التاريخ لتصبح العبارة الموسيقية الأكثر تعرفًا على وجه الأرض. "
            "تشمل الأربع حركات كاملةً: الأليغرو كون بريو الطاغي، والأندانتي الغنائي، "
            "والسكيرتسو الغامض، وخاتمة الأليغرو المنتصرة — "
            "ثم تعود السيمفونية بأكملها في حلقة متواصلة لملء الساعة."
        ),
        "intro_id": (
            "Simfoni Kelima Beethoven (1808) adalah salah satu karya paling ikonik "
            "dalam seluruh musik Barat. Empat not pembukanya yang terkenal — "
            "pendek-pendek-pendek-PANJANG — telah bergema selama dua abad dan menjadi "
            "frase musik yang paling dikenal di seluruh dunia. "
            "Semua empat gerakan disertakan secara lengkap: Allegro con brio yang menggebu, "
            "Andante con moto yang liris, Allegro Scherzo yang misterius, "
            "dan finale Allegro yang triumfan — kemudian seluruh simfoni berputar kembali "
            "tanpa henti untuk mengisi satu jam penuh."
        ),
    },

    "verdi_traviata": {
        "music_file":  "Giuseppe Verdi - La Traviata - I.mp3",
        "duration_min": 60,
        "composer_en": "Giuseppe Verdi",
        "work_en":     "La Traviata — Prelude, Act I",
        "work_ar":     "لا ترافياتا — مقدمة الفصل الأول",
        "work_id":     "La Traviata — Prelude, Babak I",
        "year":        "1853",
        "license_en":  "Public Domain (1853) — open source orchestral recording",
        "license_ar":  "ملكية عامة (1853) — تسجيل أوركسترالي مفتوح المصدر",
        "license_id":  "Domain Publik (1853) — rekaman orkestra sumber terbuka",
        "intro_en": (
            "Giuseppe Verdi's opera La Traviata (1853) opens with one of the most tender "
            "preludes in all of opera — a delicate string melody that sets the scene "
            "of Violetta's poignant story. Translated as 'The Fallen Woman', the opera "
            "is built around themes of love, sacrifice, and redemption. "
            "The Prelude to Act I is just a few minutes long but contains the entire "
            "emotional world of the work in miniature: ethereal strings that bloom "
            "into a brief passionate outburst before fading back to silence. "
            "Looped over one hour here, it creates a rich, wistful soundscape — "
            "beautiful for quiet reflection, study, or as a graceful sleep aid."
        ),
        "intro_ar": (
            "يفتتح أوبرا جوزيبي فيردي «لا ترافياتا» (1853) بواحدة من أعذب المقدمات "
            "في تاريخ الأوبرا — لحن وتري رقيق يهيّئ مسرح قصة فيوليتا المؤلمة. "
            "تعني الكلمة 'المرأة الساقطة'، ويدور الأوبرا حول موضوعات الحب والتضحية والخلاص. "
            "مقدمة الفصل الأول قصيرة لكنها تحتوي على العالم العاطفي بأسره في نسخة مصغّرة: "
            "أوتار أثيرية تتفتح إلى موجة عاطفية مختصرة ثم تعود إلى الصمت. "
            "في هذه النسخة تتكرر على مدى ساعة كاملة لتخلق منظرًا صوتيًا غنيًا رائعًا."
        ),
        "intro_id": (
            "Opera Giuseppe Verdi La Traviata (1853) dibuka dengan salah satu prelude "
            "paling lembut dalam seluruh opera — melodi dawai yang halus yang mengatur "
            "panggung kisah Violetta yang menyentuh. Diterjemahkan sebagai 'Wanita yang Tersesat', "
            "opera ini dibangun di sekitar tema cinta, pengorbanan, dan penebusan. "
            "Prelude Babak I hanya beberapa menit namun mengandung seluruh dunia emosional "
            "dalam miniatur: dawai eteris yang mekar menjadi letupan penuh gairah sesaat "
            "sebelum memudar kembali ke keheningan. "
            "Diulang selama satu jam di sini, menciptakan lanskap suara yang kaya dan penuh kerinduan."
        ),
    },

    "flute_fantaisie": {
        "music_file":  "3 Fantaisies for Solo Flute, Op. 38 - Fantaisie no. 1.mp3",
        "duration_min": 60,
        "composer_en": "Georg Philipp Telemann",
        "work_en":     "Fantaisie No. 1 for Solo Flute (from 12 Fantasias, TWV 40)",
        "work_ar":     "فنتازيا رقم 1 للناي المنفرد",
        "work_id":     "Fantaisie No. 1 untuk Seruling Solo",
        "year":        "1732",
        "license_en":  "Public Domain (1732) — open source recording",
        "license_ar":  "ملكية عامة (1732) — تسجيل مفتوح المصدر",
        "license_id":  "Domain Publik (1732) — rekaman sumber terbuka",
        "intro_en": (
            "Georg Philipp Telemann (1681–1767) was one of the most prolific composers "
            "in history, and his 12 Fantasias for Solo Flute (1732) are among the finest "
            "unaccompanied flute works ever written. Each Fantasia is a brief self-contained "
            "world — a single flute creating multiple voices through melody, harmony, and rhythm. "
            "Fantaisie No. 1 is lyrical and exploratory, moving through contrasting moods "
            "with an improvisatory lightness that feels almost effortless. "
            "The flute's singing tone is one of the most naturally soothing sounds in music, "
            "and in this one-hour looped version it fills the space with an unbroken "
            "thread of calm, perfect for babies, toddlers, and adults seeking peaceful focus."
        ),
        "intro_ar": (
            "كان جورج فيليب تيليمان (1681–1767) من أكثر الملحنين غزارةً في التاريخ، "
            "وتُعدّ فنتازياته الاثنتا عشرة للناي المنفرد (1732) من أرقى الأعمال غير المصحوبة "
            "في تاريخ آلة الناي. كل فنتازيا عالم مكتمل في ذاته — ناي واحد يُنشئ أصواتًا "
            "متعددة عبر اللحن والتوافق والإيقاع. "
            "الفنتازيا الأولى غنائية واستكشافية، تنتقل بين مزاجيّات متباينة "
            "بخفة ارتجالية تبدو خالية من الجهد. "
            "في هذا الإصدار الذي يمتد ساعة كاملة تملأ الفضاء بخيط متواصل من الهدوء."
        ),
        "intro_id": (
            "Georg Philipp Telemann (1681–1767) adalah salah satu komposer paling produktif "
            "dalam sejarah, dan 12 Fantasianya untuk Seruling Solo (1732) adalah di antara "
            "karya seruling tanpa iringan terbaik yang pernah ditulis. "
            "Setiap Fantasia adalah dunia singkat yang mandiri — satu seruling menciptakan "
            "berbagai suara melalui melodi, harmoni, dan ritme. "
            "Fantaisie No. 1 bersifat liris dan eksplorasi, bergerak melalui suasana "
            "yang kontras dengan kebebasan improvisatoris yang terasa hampir tanpa usaha. "
            "Nada nyanyian seruling adalah salah satu suara paling menenangkan secara alami "
            "dalam musik, dan dalam versi satu jam yang diulang ini mengisi ruang "
            "dengan benang ketenangan yang tak terputus."
        ),
    },
}

# ─── helpers ─────────────────────────────────────────────────────────────────

def get_theme_sequence(key: str, lang: str) -> list:
    """Return ordered list of 4 themes for this piece-lang combo."""
    start = (PIECE_BASE[key] + LANG_SHIFT[lang]) % 4
    return [THEME_ORDER[(start + i) % 4] for i in range(4)]


def get_first_theme(key: str, lang: str) -> str:
    return get_theme_sequence(key, lang)[0]


def get_thumb_prompt(key: str, lang: str) -> str:
    first = get_first_theme(key, lang)
    v = VIDEOS[key]
    composer = v["composer_en"]

    # Theme-based scene descriptions
    scene = {
        "stars":  "deep night sky, softly glowing stars and galaxies, floating golden musical notes, rich purple and gold, cinematic digital art",
        "ocean":  "deep glowing ocean at night, luminescent jellyfish floating, bioluminescent blue tones, peaceful underwater scene",
        "garden": "moonlit garden at night, glowing fireflies and soft flowers, golden light, romantic dreamy atmosphere",
        "forest": "moonlit forest at night, glowing fireflies drifting, misty ancient trees, silver moonbeams, magical forest scene",
    }[first]

    # Composer mood hint
    mood = {
        "Ralph Vaughan Williams": "orchestral grandeur, serene and transcendent",
        "Wolfgang Amadeus Mozart": "elegant classical, graceful and light",
        "Ludwig van Beethoven":    "powerful and triumphant, dramatic depth",
        "Giuseppe Verdi":          "romantic opera atmosphere, wistful and passionate",
        "Georg Philipp Telemann":  "baroque lightness, airy and introspective",
    }.get(composer, "classical music atmosphere")

    suffix = "no text, no letters, no numbers, no words" if lang == "ar" else "no text"

    return f"{scene}, {mood}, {suffix}"


# ─── description / meta ──────────────────────────────────────────────────────

def make_description(key: str, lang: str) -> str:
    v = VIDEOS[key]
    composer = v["composer_en"]
    work = v[f"work_{lang}"]
    year = v["year"]
    license_line = v[f"license_{lang}"]
    intro = v[f"intro_{lang}"]
    themes = get_theme_sequence(key, lang)

    if lang == "en":
        is_mozart = "Mozart" in composer
        is_beethoven = "Beethoven" in composer
        is_vw = "Vaughan" in composer
        is_verdi = "Verdi" in composer
        is_telemann = "Telemann" in composer

        if is_mozart:
            search_tags = "#ClassicalMusic #Mozart #EineKleineNachtmusik #MozartForSleep"
        elif is_beethoven:
            search_tags = "#ClassicalMusic #Beethoven #Symphony5 #BeethovenForSleep"
        elif is_vw:
            search_tags = "#ClassicalMusic #VaughanWilliams #Fantasia #ThomasTallis"
        elif is_verdi:
            search_tags = "#ClassicalMusic #Verdi #LaTraviata #OperaMusic"
        else:
            search_tags = "#ClassicalMusic #Telemann #BaroqueFlute #SoloFlute"

        return (
            f"🎻 {composer} — {work} ({year})\n\n"
            f"{intro}\n\n"
            "✨ What you'll see:\n"
            "• A mesmerising animated visual — 4 different visual journeys each 15 minutes\n"
            f"• Themes in order: {' → '.join(t.capitalize() for t in themes)}\n"
            "• Floating golden musical notes and soft glowing orbs drifting across the screen\n"
            "• A gently pulsing music visualizer responding to the music at the bottom\n"
            "• Calming dark atmosphere — perfect for sleep, focus, or relaxation\n\n"
            "🎼 About the music:\n"
            f"• Composer: {composer} ({year})\n"
            f"• Work: {work}\n"
            f"• {license_line}\n\n"
            "🌙 Perfect for:\n"
            "• Falling asleep — babies, toddlers, and adults alike\n"
            "• Deep focus and study sessions\n"
            "• Meditation and mindfulness\n"
            "• Peaceful background listening\n"
            "• Introducing children to classical music\n\n"
            "Subscribe to Happy Bear Kids for more soothing classical and educational content!\n\n"
            f"{search_tags} #ClassicalMusicForBabies #SleepMusic #StudyMusic "
            "#RelaxingClassical #AmbientClassical #HappyBearKids #BabySleepMusic "
            "#CalmMusic #FocusMusic #ClassicalLullaby #ClassicalMusicForSleep"
        )

    elif lang == "ar":
        return (
            f"🎻 {composer} — {v['work_ar']} ({year})\n\n"
            f"{intro}\n\n"
            "✨ ما ستشاهده:\n"
            "• مشهد بصري آسر — أربع رحلات بصرية مختلفة كل منها خمس عشرة دقيقة\n"
            f"• الأجواء بالترتيب: {' ← '.join(t.capitalize() for t in themes)}\n"
            "• نوتات موسيقية ذهبية وكرات ضوئية ناعمة تسبح عبر الشاشة\n"
            "• مُرئيّ إيقاعي جميل في الأسفل يتجاوب مع الموسيقى\n"
            "• أجواء داكنة هادئة مثالية للنوم أو التركيز العميق\n\n"
            f"🎼 عن الموسيقى:\n"
            f"• الملحّن: {composer} ({year})\n"
            f"• العمل: {v['work_ar']}\n"
            f"• {license_line}\n\n"
            "🌙 مثالية لـ:\n"
            "• النوم العميق — للرضع والأطفال والبالغين على حد سواء\n"
            "• التركيز والدراسة\n"
            "• التأمل والهدوء الداخلي\n"
            "• الاستماع الهادئ في الخلفية\n"
            "• تعريف الأطفال بالموسيقى الكلاسيكية\n\n"
            "اشترك في Happy Bear Kids للمزيد من المحتوى الكلاسيكي والتعليمي المهدّئ!\n\n"
            "#موسيقى_كلاسيكية #موسيقى_للنوم #استرخاء #موسيقى_للتركيز "
            "#موسيقى_هادئة #نوم_الرضع #موسيقى_تأمل #HappyBearKids "
            "#classical_music #sleep_music #relax"
        )

    else:  # id
        return (
            f"🎻 {composer} — {v['work_id']} ({year})\n\n"
            f"{intro}\n\n"
            "✨ Yang akan kamu lihat:\n"
            "• Visual animasi memukau — 4 perjalanan visual berbeda masing-masing 15 menit\n"
            f"• Urutan tema: {' → '.join(t.capitalize() for t in themes)}\n"
            "• Not musik emas dan bola cahaya lembut melayang di layar\n"
            "• Equalizer animasi cantik yang merespons musik di bagian bawah\n"
            "• Suasana gelap menenangkan — sempurna untuk tidur atau fokus mendalam\n\n"
            f"🎼 Tentang musiknya:\n"
            f"• Komposer: {composer} ({year})\n"
            f"• Karya: {v['work_id']}\n"
            f"• {license_line}\n\n"
            "🌙 Sempurna untuk:\n"
            "• Tidur nyenyak — bayi, balita, dan orang dewasa\n"
            "• Fokus belajar mendalam\n"
            "• Meditasi dan ketenangan batin\n"
            "• Mendengarkan musik latar yang damai\n"
            "• Memperkenalkan musik klasik kepada anak-anak\n\n"
            "Subscribe ke Happy Bear Kids untuk konten klasik dan edukatif yang menenangkan!\n\n"
            "#MusikKlasik #MusikTidur #Relaksasi #FokusBelajar #MusikTenang "
            "#TidurBayi #Meditasi #HappyBearKids #classical_music #sleep_music"
        )


def make_meta(key: str, lang: str) -> dict:
    v = VIDEOS[key]
    composer = v["composer_en"]
    is_mozart = "Mozart" in composer
    is_beethoven = "Beethoven" in composer
    is_vw = "Vaughan" in composer
    is_verdi = "Verdi" in composer

    if lang == "en":
        base_tags = [
            "classical music", "classical music for sleep", "sleep music",
            "study music", "relaxing classical", "ambient classical",
            "1 hour music", "focus music", "meditation music", "calm music",
            "classical music for babies", "baby sleep music", "HappyBearKids",
            "orchestral music", "lullaby classical",
        ]
        if is_mozart:
            base_tags += ["mozart", "eine kleine nachtmusik", "mozart for babies", "mozart serenade"]
        elif is_beethoven:
            base_tags += ["beethoven", "symphony no 5", "beethoven symphony", "beethoven for sleep"]
        elif is_vw:
            base_tags += ["vaughan williams", "fantasia", "thomas tallis", "orchestral sleep"]
        elif is_verdi:
            base_tags += ["verdi", "la traviata", "opera music", "opera for sleep"]
        else:
            base_tags += ["telemann", "baroque flute", "solo flute", "baroque music"]
    elif lang == "ar":
        base_tags = [
            "موسيقى كلاسيكية", "موسيقى للنوم", "استرخاء", "موسيقى للتركيز",
            "موسيقى هادئة", "نوم الرضع", "موسيقى تأمل",
            "classical music", "sleep music", "HappyBearKids",
        ]
    else:
        base_tags = [
            "musik klasik", "musik tidur", "relaksasi", "fokus belajar",
            "musik tenang", "tidur bayi", "meditasi",
            "classical music", "sleep music", "HappyBearKids",
        ]

    title_en = f"🎻 {composer} — {v['work_en']} | 1 Hour Classical Music for Sleep & Focus"
    title_ar = f"🎻 {composer} — {v['work_ar']} | ساعة موسيقى كلاسيكية للنوم والاسترخاء"
    title_id = f"🎻 {composer} — {v['work_id']} | 1 Jam Musik Klasik untuk Tidur & Fokus"

    titles = {"en": title_en, "ar": title_ar, "id": title_id}

    return {
        "title":       titles[lang],
        "description": make_description(key, lang),
        "tags":        base_tags,
        "video_type":  "lullaby_long",
        "language":    lang,
        "is_short":    False,
        "status":      "public",
    }


# ─── thumbnail ───────────────────────────────────────────────────────────────

def generate_thumbnail(key: str, lang: str, out_path: Path) -> bool:
    if not TOGETHER_KEY_FILE.exists():
        print("  No Together.ai key — skip thumbnail")
        return False
    api_key = TOGETHER_KEY_FILE.read_text().strip()
    prompt = get_thumb_prompt(key, lang)
    try:
        r = requests.post(TOGETHER_URL, json={
            "model": "black-forest-labs/FLUX.1-schnell",
            "prompt": prompt,
            "width": 1280, "height": 720,
            "steps": 4, "n": 1,
            "response_format": "b64_json",
        }, headers={"Authorization": f"Bearer {api_key}"}, timeout=60)
        r.raise_for_status()
        out_path.write_bytes(base64.b64decode(r.json()["data"][0]["b64_json"]))
        print(f"  Thumbnail ({lang}): {out_path.name} ({out_path.stat().st_size // 1024}KB)")
        return True
    except Exception as e:
        print(f"  Thumbnail error ({lang}): {e}")
        return False


# ─── rendering ───────────────────────────────────────────────────────────────

def render_shared_loop(theme: str, lang: str, out_path: Path, dry_run: bool) -> bool:
    """Render a 5-min LullabyLoop for one theme+lang combination (shared across all pieces)."""
    colors = THEME_COLORS[theme]
    phase  = LANG_CONFIGS[lang]["phase"]
    props  = {
        "theme":          theme,
        "bgColorTop":     BG_TOP,
        "bgColorBottom":  BG_BOTTOM,
        "accentColor":    colors["accent"],
        "equalizerColor": colors["eq"],
        "showEqualizer":  True,
        "phaseOffset":    phase,
    }
    cmd = [
        "npx", "remotion", "render", "LullabyLoop",
        f"--props={json.dumps(props)}",
        f"--output={str(out_path)}",
    ]
    print(f"  [render] shared loop: theme={theme} lang={lang} → {out_path.name}")
    if dry_run:
        print("    DRY RUN — skipped")
        return True
    result = subprocess.run(cmd, cwd=str(REMOTION), capture_output=False, timeout=3600)
    return result.returncode == 0


def ensure_shared_loops(dry_run: bool) -> dict:
    """Render any missing shared loop files. Returns {theme_lang: Path}."""
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    shared = {}
    for lang in LANG_CONFIGS:
        for theme in THEME_ORDER:
            loop_path = TMP_DIR / f"shared_loop_{theme}_{lang}.mp4"
            shared[f"{theme}_{lang}"] = loop_path
            if not loop_path.exists():
                ok = render_shared_loop(theme, lang, loop_path, dry_run)
                if not ok and not dry_run:
                    print(f"  ERROR: failed to render shared loop {theme}/{lang}")
    return shared


def assemble_rotated_video(key: str, lang: str, shared: dict,
                            music_mp3: Path, out_mp4: Path,
                            duration_min: int, dry_run: bool) -> bool:
    """
    Build a 60-min video by concatenating 4 × 15-min visual segments
    (each segment = 3× the 5-min shared loop for that theme),
    then overlay the music file with stream_loop -1.
    """
    themes = get_theme_sequence(key, lang)
    total_sec = duration_min * 60
    seg_sec   = 15 * 60       # 15 min per theme
    loop_sec  = 5  * 60       # each shared loop is 5 min → need 3 per segment
    loops_per_seg = seg_sec // loop_sec  # = 3

    playlist = TMP_DIR / f"playlist_{key}_{lang}.txt"
    lines = []
    for theme in themes:
        loop_path = shared[f"{theme}_{lang}"]
        for _ in range(loops_per_seg):
            lines.append(f"file '{loop_path.resolve()}'")
    playlist.write_text("\n".join(lines))

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(playlist),
        "-stream_loop", "-1", "-i", str(music_mp3),
        "-t", str(total_sec),
        "-vf", f"fade=t=out:st={total_sec - 60}:d=60",
        "-af", f"volume=0.88,afade=t=out:st={total_sec - 90}:d=90",
        "-c:v", "libx264", "-crf", "22", "-preset", "fast",
        "-c:a", "aac", "-b:a", "128k",
        str(out_mp4),
    ]
    print(f"  [ffmpeg] {out_mp4.name} ({duration_min} min, themes: {' → '.join(themes)})")
    if dry_run:
        print("    DRY RUN — skipped")
        return True
    result = subprocess.run(cmd, capture_output=False, timeout=7200)
    return result.returncode == 0


# ─── per-piece processing ────────────────────────────────────────────────────

def process_key(key: str, shared: dict, dry_run: bool, regen_meta: bool) -> bool:
    v = VIDEOS[key]
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    music_mp3 = MUSIC_DIR / v["music_file"]

    print(f"\n{'='*72}")
    print(f"  [{key.upper()}] {v['composer_en']} — {v['work_en'][:55]}")
    print(f"  music: {v['music_file']}")

    if not music_mp3.exists():
        print(f"  ERROR: music not found: {music_mp3}")
        return False

    for lang, cfg in LANG_CONFIGS.items():
        queue_dir = cfg["queue"]
        queue_dir.mkdir(parents=True, exist_ok=True)

        out_mp4    = queue_dir / f"classical_{key}_{lang}_{DATE_STR}.mp4"
        meta_path  = queue_dir / f"meta_classical_{key}_{lang}_{DATE_STR}.yaml"
        thumb_path = queue_dir / f"thumb_classical_{key}_{lang}_{DATE_STR}.png"
        themes     = get_theme_sequence(key, lang)

        print(f"\n  ── [{lang.upper()}] themes: {' → '.join(themes)} ──")

        if not regen_meta:
            if out_mp4.exists():
                print(f"  Video exists — skip: {out_mp4.name}")
            else:
                ok = assemble_rotated_video(key, lang, shared, music_mp3,
                                            out_mp4, v["duration_min"], dry_run)
                if not ok:
                    print(f"  FAILED: assemble_rotated_video ({lang})")
                    continue

        if out_mp4.exists() or dry_run:
            meta_path.write_text(
                yaml.dump(make_meta(key, lang), allow_unicode=True, sort_keys=False)
            )
            print(f"  Meta: {meta_path.name}")

            if not thumb_path.exists():
                time.sleep(3)
                generate_thumbnail(key, lang, thumb_path)
            else:
                print(f"  Thumb exists: {thumb_path.name}")

    return True


# ─── main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate classical music visualizer videos")
    parser.add_argument("--keys", nargs="+", choices=list(VIDEOS.keys()),
                        help="Which pieces to process (default: all)")
    parser.add_argument("--dry-run",          action="store_true")
    parser.add_argument("--regen-meta",       action="store_true",
                        help="Re-write meta + thumbnail only (no render/assemble)")
    parser.add_argument("--render-loops-only", action="store_true",
                        help="Only render 12 shared loops, do not assemble videos")
    args = parser.parse_args()

    keys = args.keys or list(VIDEOS.keys())
    n = len(keys)
    print(f"Classical visualizer — {n} piece(s) × 3 channels = {n*3} videos")
    print(f"  dry_run={args.dry_run}  regen_meta={args.regen_meta}  loops_only={args.render_loops_only}")
    print(f"  Shared loops: 4 themes × 3 channels = 12 Remotion renders")

    if not args.regen_meta:
        print("\nStep 1: ensure 12 shared loop files …")
        shared = ensure_shared_loops(args.dry_run)
    else:
        # For regen-meta we still need the paths (even if files don't exist)
        shared = {
            f"{t}_{l}": TMP_DIR / f"shared_loop_{t}_{l}.mp4"
            for t in THEME_ORDER for l in LANG_CONFIGS
        }

    if args.render_loops_only:
        print("\nLoop rendering complete. Exiting (--render-loops-only).")
        return

    print("\nStep 2: assemble videos …")
    for key in keys:
        process_key(key, shared, args.dry_run, args.regen_meta)

    print("\nAll done.")


if __name__ == "__main__":
    main()
