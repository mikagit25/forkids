#!/usr/bin/env python3
"""
Generate classical music visualizer videos for all 3 channels.

THEME ROTATION approach:
  Each 60-min video cycles through 4 visual themes (15 min each):
    stars → ocean → garden → forest
  Different pieces and channels start at different offsets so YouTube
  cannot detect duplicate content across videos.

  Shared Remotion loop files (12 total: 4 themes × 3 channels) are
  rendered once and reused for all 18 classical pieces — only FFmpeg
  assembly differs per piece.

18 pieces × 3 channels = 54 videos total.

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
MUSIC_DIR  = ROOT / "assets" / "music" / "mozart"
MUSIC_DIR2 = ROOT / "assets" / "music" / "classical" / "Music"

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
    # original 7
    "fantasia":           0,   # en: stars  ar: ocean  id: garden
    "mozart_romance":     1,   # en: ocean  ar: garden id: forest
    "mozart_minuet":      2,   # en: garden ar: forest id: stars
    "mozart_rondo":       3,   # en: forest ar: stars  id: ocean
    "beethoven_5":        0,   # en: stars  ar: ocean  id: garden
    "verdi_traviata":     1,   # en: ocean  ar: garden id: forest
    "flute_fantaisie":    2,   # en: garden ar: forest id: stars
    # new 11
    "bach_cello_suite":       3,   # en: forest
    "chopin_nocturne_1":      0,   # en: stars
    "chopin_nocturne_2":      1,   # en: ocean
    "beethoven_moonlight":    2,   # en: garden
    "flute_etude_3":          3,   # en: forest
    "flute_etude_6":          0,   # en: stars
    "swan_lake_act2_pt1":     1,   # en: ocean  (blue water fits)
    "swan_lake_act2_concl":   2,   # en: garden
    "swan_lake_act3_pt1":     1,   # en: ocean
    "swan_lake_act3_concl":   3,   # en: forest
    "swan_lake_act4_intro":   1,   # en: ocean
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

    # ── New pieces from Google Drive ─────────────────────────────────────────

    "bach_cello_suite": {
        "music_file":  "Cello Suite no. 1 - Prelude in G, BWV 1007.mp3",
        "duration_min": 60,
        "composer_en": "Johann Sebastian Bach",
        "work_en":     "Cello Suite No. 1 in G major, BWV 1007 — Prélude",
        "work_ar":     "جناح التشيللو رقم 1 في صول الكبير، BWV 1007 — البريلود",
        "work_id":     "Suite Cello No. 1 dalam G mayor, BWV 1007 — Prélude",
        "year":        "1720",
        "license_en":  "Public Domain (c.1720) — open source cello recording",
        "license_ar":  "ملكية عامة (حوالي 1720) — تسجيل تشيللو مفتوح المصدر",
        "license_id":  "Domain Publik (c.1720) — rekaman cello sumber terbuka",
        "intro_en": (
            "Johann Sebastian Bach's Cello Suite No. 1 Prélude is one of the most "
            "recognised and beloved pieces ever written for a solo instrument. "
            "Composed around 1720, this single unbroken stream of arpeggios unfolds "
            "like a meditation — each note flowing naturally into the next without pause. "
            "Its gentle rocking motion and pure, unaccompanied cello tone have made it "
            "a favourite for quiet reflection, study, and deep sleep. "
            "In this one-hour version the Prélude repeats in a seamless loop, "
            "turning two minutes of genius into an hour-long sonic sanctuary."
        ),
        "intro_ar": (
            "بريلود جناح التشيللو رقم 1 لباخ هو أحد أكثر الأعمال شهرةً وعمقًا "
            "في تاريخ الموسيقى المكتوبة لآلة منفردة. "
            "أُلِّف حوالي عام 1720، وهذا التدفق المتواصل من الأرپيجيات "
            "يتكشّف كأنه تأمل عميق — كل نغمة تسيل إلى التالية دون توقف. "
            "حركته الهادئة المتأرجحة ونقاء صوت التشيللو المنفرد جعلاه مفضلًا "
            "للتأمل والدراسة والنوم العميق. "
            "في هذا الإصدار الذي يمتد ساعة كاملة يتكرر البريلود في حلقة سلسة."
        ),
        "intro_id": (
            "Prélude dari Cello Suite No. 1 Bach adalah salah satu karya yang paling "
            "dikenal dan dicintai yang pernah ditulis untuk instrumen solo. "
            "Digubah sekitar tahun 1720, aliran arpeggio yang tak terputus ini "
            "terbuka seperti meditasi — setiap not mengalir alami ke not berikutnya tanpa jeda. "
            "Gerakan mengayun lembut dan nada cello murni tanpa iringan menjadikannya "
            "favorit untuk refleksi tenang, belajar, dan tidur mendalam. "
            "Dalam versi satu jam ini Prélude berulang dalam putaran mulus."
        ),
    },

    "chopin_nocturne_1": {
        "music_file":  "Nocturne in B flat minor, Op. 9 no. 1.mp3",
        "duration_min": 60,
        "composer_en": "Frédéric Chopin",
        "work_en":     "Nocturne in B♭ minor, Op. 9 No. 1",
        "work_ar":     "نوكتورن في سي♭ الصغير، أوبوس 9 رقم 1",
        "work_id":     "Nocturne dalam B♭ minor, Op. 9 No. 1",
        "year":        "1830",
        "license_en":  "Public Domain (1830) — open source piano recording",
        "license_ar":  "ملكية عامة (1830) — تسجيل بيانو مفتوح المصدر",
        "license_id":  "Domain Publik (1830) — rekaman piano sumber terbuka",
        "intro_en": (
            "Frédéric Chopin (1810–1849) revolutionised piano music with his Nocturnes — "
            "short, introspective pieces written for the night. "
            "The Nocturne in B♭ minor, Op. 9 No. 1 is one of his earliest and most hauntingly "
            "beautiful: a long, flowing melody over a gently rocking left-hand accompaniment. "
            "Its melancholic lyricism touches something deep and universal — "
            "a quiet ache, a night reverie, a tender farewell. "
            "In this one-hour version it plays on a continuous loop, "
            "creating an unbroken atmosphere of moonlit calm — perfect for sleep, "
            "meditation, or late-night study."
        ),
        "intro_ar": (
            "أحدث فريدريك شوبان (1810–1849) ثورة في موسيقى البيانو بنوكتورناته "
            "— مقطوعات قصيرة تأملية كُتبت لأجواء الليل. "
            "نوكتورن سي♭ الصغير أوبوس 9 رقم 1 من أجمل ما كتبه وأعمقه: "
            "لحن متدفق طويل فوق مصاحبة يسرى تتأرجح بهدوء. "
            "غنائيته الحزينة تلمس شيئًا عميقًا وإنسانيًا — "
            "ألم هادئ، حلم ليلي، وداع رقيق. "
            "في هذا الإصدار يتكرر على مدى ساعة كاملة "
            "في هدوء ضوء القمر — مثالي للنوم أو التأمل أو الدراسة الليلية."
        ),
        "intro_id": (
            "Frédéric Chopin (1810–1849) merevolusi musik piano dengan Noturnnya "
            "— karya-karya pendek dan introspektif yang ditulis untuk malam hari. "
            "Nocturne dalam B♭ minor, Op. 9 No. 1 adalah salah satu yang paling "
            "awal dan paling memesona: melodi panjang mengalir di atas iringan tangan kiri "
            "yang berayun lembut. "
            "Lirisisme melankolisnya menyentuh sesuatu yang dalam dan universal — "
            "kerinduan diam, lamunan malam, perpisahan lembut. "
            "Dalam versi satu jam ini dimainkan dalam putaran terus-menerus, "
            "menciptakan suasana tenang cahaya bulan yang tak terputus."
        ),
    },

    "chopin_nocturne_2": {
        "music_file":  "Nocturne in E flat major, Op. 9 no. 2.mp3",
        "duration_min": 60,
        "composer_en": "Frédéric Chopin",
        "work_en":     "Nocturne in E♭ major, Op. 9 No. 2",
        "work_ar":     "نوكتورن في مي♭ الكبير، أوبوس 9 رقم 2",
        "work_id":     "Nocturne dalam E♭ mayor, Op. 9 No. 2",
        "year":        "1830",
        "license_en":  "Public Domain (1830) — open source piano recording",
        "license_ar":  "ملكية عامة (1830) — تسجيل بيانو مفتوح المصدر",
        "license_id":  "Domain Publik (1830) — rekaman piano sumber terbuka",
        "intro_en": (
            "Chopin's Nocturne in E♭ major, Op. 9 No. 2 is perhaps the most famous "
            "Nocturne ever written — its opening melody instantly recognisable to "
            "millions of listeners around the world. "
            "Composed in 1830, this piece unfolds with an almost vocal quality, "
            "the piano singing a long-breathed, ornate melody of extraordinary tenderness. "
            "It is gentle, luminous, and deeply comforting — one of the best pieces "
            "in all of music for easing a busy mind into stillness. "
            "In this one-hour looped version it fills the space with a continuous "
            "thread of warmth, ideal for sleep, relaxation, or peaceful background music."
        ),
        "intro_ar": (
            "نوكتورن شوبان في مي♭ الكبير أوبوس 9 رقم 2 ربما هو أشهر نوكتورن "
            "كُتب على الإطلاق — لحنه الافتتاحي يُعرِّفه الملايين حول العالم فورًا. "
            "أُلِّف عام 1830، وتتكشّف هذه المقطوعة بجودة صوتية شبه غنائية، "
            "البيانو يُغني لحنًا طويل النَّفَس مزيّنًا برقة استثنائية. "
            "هادئ، مُضيء، ومريح في أعماقه — من أجمل ما كُتب في تاريخ الموسيقى "
            "لتهدئة العقل المشغول. "
            "في هذا الإصدار الذي يمتد ساعة كاملة يملأ المكان بخيط متواصل من الدفء."
        ),
        "intro_id": (
            "Nocturne Chopin dalam E♭ mayor, Op. 9 No. 2 mungkin adalah Nocturne "
            "paling terkenal yang pernah ditulis — melodinya yang pembuka langsung "
            "dikenali jutaan pendengar di seluruh dunia. "
            "Digubah tahun 1830, karya ini terbuka dengan kualitas hampir vokal, "
            "piano menyanyikan melodi panjang berhias dengan kelembutan luar biasa. "
            "Lembut, bercahaya, dan sangat menghibur — salah satu karya terbaik "
            "dalam seluruh musik untuk menenangkan pikiran yang sibuk. "
            "Dalam versi satu jam ini mengisi ruang dengan benang kehangatan yang tak terputus."
        ),
    },

    "beethoven_moonlight": {
        "music_file":  "Piano Sonata no. 14 in C#m 'Moonlight', Op. 27 no. 2 - I. Adagio sostenuto.mp3",
        "duration_min": 60,
        "composer_en": "Ludwig van Beethoven",
        "work_en":     "Piano Sonata No. 14 «Moonlight» in C♯ minor, Op. 27 No. 2 — I. Adagio sostenuto",
        "work_ar":     "سوناتا البيانو رقم 14 «ضوء القمر» في دو♯ الصغير، أوبوس 27 رقم 2 — الأداجيو",
        "work_id":     "Sonata Piano No. 14 «Moonlight» dalam C♯ minor, Op. 27 No. 2 — I. Adagio sostenuto",
        "year":        "1801",
        "license_en":  "Public Domain (1801) — open source piano recording",
        "license_ar":  "ملكية عامة (1801) — تسجيل بيانو مفتوح المصدر",
        "license_id":  "Domain Publik (1801) — rekaman piano sumber terbuka",
        "intro_en": (
            "Beethoven's «Moonlight» Sonata (1801) is one of the most iconic piano pieces "
            "ever written. Its first movement — Adagio sostenuto — opens with three notes "
            "repeating in a hypnotic triplet pattern beneath a singing melody, "
            "evoking moonlight rippling across still water. "
            "Beethoven himself described the sonata as a work of profound personal expression, "
            "and listeners have felt that intimacy for over two centuries. "
            "The Adagio sostenuto alone runs just over five minutes, "
            "making it perfect for looping: in this one-hour version "
            "that quiet, moonlit world plays on without interruption — "
            "ideal for falling asleep, deep focus, or late-night reflection."
        ),
        "intro_ar": (
            "«سوناتا ضوء القمر» لبيتهوفن (1801) هي واحدة من أكثر مقطوعات البيانو "
            "شهرةً في التاريخ. تفتتح حركتها الأولى — أداجيو سوستينوتو — "
            "بثلاث نغمات تتكرر في نمط ثلاثي تنويمي تحت لحن غنائي رائع، "
            "مستحضرةً ضوء القمر يتموّج فوق مياه ساكنة. "
            "الحركة الأولى تمتد قليلًا فوق خمس دقائق مما يجعلها مثالية للتكرار: "
            "في هذا الإصدار الذي يمتد ساعة كاملة "
            "يستمر ذلك العالم الهادئ المضاء بالقمر دون انقطاع."
        ),
        "intro_id": (
            "Sonata «Moonlight» Beethoven (1801) adalah salah satu karya piano "
            "paling ikonik yang pernah ditulis. Gerakan pertamanya — Adagio sostenuto — "
            "dibuka dengan tiga not yang berulang dalam pola triplet hipnotis "
            "di bawah melodi menyanyi, membangkitkan cahaya bulan beriak di atas air tenang. "
            "Adagio sostenuto saja berdurasi sedikit lebih dari lima menit, "
            "membuatnya sempurna untuk diputar berulang: dalam versi satu jam ini "
            "dunia sunyi berlumur cahaya bulan itu bermain tanpa gangguan — "
            "ideal untuk tertidur, fokus mendalam, atau refleksi larut malam."
        ),
    },

    "flute_etude_3": {
        "music_file":  "24 Etudes for Flute, Op. 15 - III. Allegro con brio in G major.mp3",
        "duration_min": 60,
        "composer_en": "Ernesto Köhler",
        "work_en":     "24 Etudes for Flute, Op. 15 — No. 3 in G major, Allegro con brio",
        "work_ar":     "24 تمريناً للناي، أوبوس 15 — رقم 3 في صول الكبير، أليغرو كون بريو",
        "work_id":     "24 Etudes untuk Seruling, Op. 15 — No. 3 dalam G mayor, Allegro con brio",
        "year":        "1890",
        "license_en":  "Public Domain (c.1890) — open source flute recording",
        "license_ar":  "ملكية عامة (حوالي 1890) — تسجيل ناي مفتوح المصدر",
        "license_id":  "Domain Publik (c.1890) — rekaman seruling sumber terbuka",
        "intro_en": (
            "Ernesto Köhler (1849–1907) was a virtuoso flutist and the principal flutist "
            "of the Imperial Opera in St. Petersburg, and his 24 Etudes for Flute, Op. 15 "
            "are among the most beloved and widely performed flute studies ever written. "
            "Etude No. 3 in G major is marked Allegro con brio — with spirit and brilliance — "
            "a bright, running cascade of notes that dances through the upper registers "
            "of the flute with joyful lightness. "
            "At just over three minutes long, it loops beautifully: "
            "in this one-hour version, the clear singing tone of the solo flute "
            "creates a gentle, bright atmosphere perfect for babies, focused play, "
            "or light, refreshing background music."
        ),
        "intro_ar": (
            "إرنستو كولر (1849–1907) كان عازف ناي بارعًا ورئيس الناي "
            "في أوبرا الإمبراطورية في سانت بطرسبورغ، "
            "وتمارينه الأربعة والعشرون للناي أوبوس 15 من أكثر دراسات الناي "
            "شهرةً وانتشارًا في العالم. "
            "التمرين الثالث في صول الكبير موصوف بـ أليغرو كون بريو — بروح وإشراق — "
            "سيل لامع من النغمات يرقص عبر النطاقات العليا للناي بخفة مبهجة. "
            "في هذا الإصدار الذي يمتد ساعة كاملة "
            "يخلق نبرة الناي المنفرد الصافية أجواءً مشرقة رقيقة."
        ),
        "intro_id": (
            "Ernesto Köhler (1849–1907) adalah pemain suling virtuoso dan pemain suling utama "
            "Opera Kekaisaran di St. Petersburg, dan 24 Etudes untuk Serulingnya, Op. 15 "
            "adalah di antara studi seruling yang paling dicintai dan banyak dimainkan. "
            "Etude No. 3 dalam G mayor ditandai Allegro con brio — dengan semangat dan kecemerlangan — "
            "deretan not yang cerah dan mengalir menari melalui register atas seruling "
            "dengan keceriaan ringan. "
            "Dalam versi satu jam ini nada menyanyi jernih dari seruling solo "
            "menciptakan suasana cerah lembut yang sempurna untuk bayi, bermain fokus, "
            "atau musik latar yang menyegarkan."
        ),
    },

    "flute_etude_6": {
        "music_file":  "24 Etudes for Flute, Op. 15 - VI. Moderato in B minor.mp3",
        "duration_min": 60,
        "composer_en": "Ernesto Köhler",
        "work_en":     "24 Etudes for Flute, Op. 15 — No. 6 in B minor, Moderato",
        "work_ar":     "24 تمريناً للناي، أوبوس 15 — رقم 6 في سي الصغير، موديراتو",
        "work_id":     "24 Etudes untuk Seruling, Op. 15 — No. 6 dalam B minor, Moderato",
        "year":        "1890",
        "license_en":  "Public Domain (c.1890) — open source flute recording",
        "license_ar":  "ملكية عامة (حوالي 1890) — تسجيل ناي مفتوح المصدر",
        "license_id":  "Domain Publik (c.1890) — rekaman seruling sumber terbuka",
        "intro_en": (
            "Köhler's Etude No. 6 in B minor, Moderato is one of the most lyrical "
            "and expressive studies in the entire Op. 15 collection. "
            "Where the third etude dances with brightness, No. 6 sings with a quiet, "
            "searching beauty in the minor mode — a more introspective, contemplative mood "
            "that feels like a gentle conversation with the flute's singing voice. "
            "Its five-minute span makes it ideal for seamless looping: "
            "in this one-hour version the intimate, meditative quality of the solo flute "
            "fills the space with calm depth — beautiful for winding down, "
            "soft background music, or guiding little ones toward sleep."
        ),
        "intro_ar": (
            "التمرين السادس لكولر في سي الصغير — موديراتو — هو من أكثر الدراسات "
            "غنائيةً وتعبيرًا في مجموعة أوبوس 15 بأسرها. "
            "يُغني بجمال هادئ باحث في النغم الصغير — "
            "مزاج أكثر تأملًا واستبطانًا يشبه محادثة رقيقة مع صوت الناي الغنائي. "
            "في هذا الإصدار الذي يمتد ساعة كاملة "
            "تملأ الجودة التأملية الحميمة للناي المنفرد المكان بهدوء عميق."
        ),
        "intro_id": (
            "Etude No. 6 Köhler dalam B minor, Moderato adalah salah satu studi "
            "yang paling liris dan ekspresif dalam seluruh koleksi Op. 15. "
            "Jika etude ketiga menari dengan keceriaan, No. 6 bernyanyi dengan keindahan "
            "tenang yang mencari dalam mode minor — suasana lebih introspektif dan kontemplatif "
            "yang terasa seperti percakapan lembut dengan suara nyanyian seruling. "
            "Dalam versi satu jam ini kualitas meditatif intim dari seruling solo "
            "mengisi ruang dengan kedalaman tenang — indah untuk bersantai "
            "atau mengantar anak-anak kecil menuju tidur."
        ),
    },

    "swan_lake_act2_pt1": {
        "music_file":  "Swan Lake Op.20 - Act II Pt.1.mp3",
        "duration_min": 60,
        "composer_en": "Pyotr Ilyich Tchaikovsky",
        "work_en":     "Swan Lake, Op. 20 — Act II, Part 1 (White Swan Scene)",
        "work_ar":     "بحيرة البجعة، أوبوس 20 — الفصل الثاني، الجزء الأول (مشهد البجعة البيضاء)",
        "work_id":     "Swan Lake, Op. 20 — Babak II, Bagian 1 (Adegan Angsa Putih)",
        "year":        "1876",
        "license_en":  "Public Domain (1876) — open source orchestral recording",
        "license_ar":  "ملكية عامة (1876) — تسجيل أوركسترالي مفتوح المصدر",
        "license_id":  "Domain Publik (1876) — rekaman orkestra sumber terbuka",
        "intro_en": (
            "Tchaikovsky's Swan Lake (1876) is one of the greatest ballets ever written, "
            "and Act II contains some of the most ethereally beautiful music in all of classical art. "
            "The famous White Swan theme — introduced by a solo oboe, then taken up by the full orchestra "
            "— is a melody of heart-breaking tenderness, representing the cursed Princess Odette "
            "and her flock of enchanted swans. "
            "Part 1 of Act II sets the nocturnal moonlit lake scene with shimmering strings, "
            "dark winds, and that unforgettable oboe melody. "
            "In this one-hour version it plays on continuous loop — "
            "a magical soundscape perfect for sleep, relaxation, or quiet creative work."
        ),
        "intro_ar": (
            "بحيرة البجعة لتشايكوفسكي (1876) هي واحدة من أعظم الباليهات التي كُتبت على الإطلاق، "
            "والفصل الثاني يحتوي على بعض أكثر الموسيقى سموًا في كل الفن الكلاسيكي. "
            "الموضوع الشهير للبجعة البيضاء — يقدمه الأوبوا المنفرد ثم تتسلمه الأوركسترا بأسرها "
            "— لحن من الرقة الجارحة للقلب، يمثّل الأميرة أوديت الملعونة وقطيعها من البجعات المسحورة. "
            "الجزء الأول من الفصل الثاني يرسم مشهد البحيرة الليلي المضاء بالقمر "
            "بأوتار متلألئة ورياح داكنة وذلك اللحن المنسي للأوبوا. "
            "في هذا الإصدار يتكرر في حلقة متواصلة لمدة ساعة كاملة."
        ),
        "intro_id": (
            "Swan Lake Tchaikovsky (1876) adalah salah satu balet terhebat yang pernah ditulis, "
            "dan Babak II mengandung beberapa musik paling eteris-indah dalam seluruh seni klasik. "
            "Tema Angsa Putih yang terkenal — diperkenalkan oleh oboe solo kemudian diambil alih "
            "oleh seluruh orkestra — adalah melodi dengan kelembutan yang memilukan hati, "
            "mewakili Putri Odette yang terkutuk dan kawanan angsa pesonanya. "
            "Bagian 1 Babak II mengatur adegan danau berlumur cahaya bulan nokturnal "
            "dengan dawai berkilauan, angin gelap, dan melodi oboe yang tak terlupakan. "
            "Dalam versi satu jam ini dimainkan dalam putaran terus-menerus."
        ),
    },

    "swan_lake_act2_concl": {
        "music_file":  "Swan Lake Op.20 - Act II Concl.mp3",
        "duration_min": 60,
        "composer_en": "Pyotr Ilyich Tchaikovsky",
        "work_en":     "Swan Lake, Op. 20 — Act II, Conclusion (White Swan Adagio)",
        "work_ar":     "بحيرة البجعة، أوبوس 20 — الفصل الثاني، الخاتمة (أداجيو البجعة البيضاء)",
        "work_id":     "Swan Lake, Op. 20 — Babak II, Penutup (Adagio Angsa Putih)",
        "year":        "1876",
        "license_en":  "Public Domain (1876) — open source orchestral recording",
        "license_ar":  "ملكية عامة (1876) — تسجيل أوركسترالي مفتوح المصدر",
        "license_id":  "Domain Publik (1876) — rekaman orkestra sumber terbuka",
        "intro_en": (
            "The conclusion of Act II of Swan Lake is one of the most poignant and beautiful "
            "passages in all of Tchaikovsky's output. "
            "After the famous White Swan Adagio — in which Prince Siegfried and Odette dance "
            "their first, moonlit pas de deux — the music broadens into a sublime farewell "
            "as dawn breaks and the swans must return to the lake. "
            "Shimmering strings, tender woodwind solos, and a sense of bittersweet longing "
            "pervade every bar. "
            "In this one-hour version this extraordinarily emotional music plays on loop, "
            "filling the room with beauty and calm — perfect for sleep, "
            "emotional healing, or quiet contemplation."
        ),
        "intro_ar": (
            "خاتمة الفصل الثاني من بحيرة البجعة هي أحد أجمل المقاطع وأكثرها مؤثّرًا "
            "في كل إنتاج تشايكوفسكي. "
            "بعد أداجيو البجعة البيضاء الشهير — حيث يرقص الأمير سيغفريد وأوديت "
            "ثنائيهما الأول في ضوء القمر — تتسع الموسيقى إلى وداع سامٍ "
            "مع بزوغ الفجر وعودة البجعات إلى البحيرة. "
            "في هذا الإصدار الذي يمتد ساعة كاملة "
            "تتكرر هذه الموسيقى البالغة العاطفة في حلقة متواصلة."
        ),
        "intro_id": (
            "Penutup Babak II dari Swan Lake adalah salah satu bagian paling menyentuh "
            "dan indah dalam seluruh karya Tchaikovsky. "
            "Setelah Adagio Angsa Putih yang terkenal — di mana Pangeran Siegfried dan Odette "
            "menari pas de deux pertama mereka yang berlumur cahaya bulan — "
            "musik melebar menjadi perpisahan yang agung saat fajar menyingsing "
            "dan para angsa harus kembali ke danau. "
            "Dalam versi satu jam ini musik yang luar biasa emosional ini berputar dalam loop, "
            "mengisi ruangan dengan keindahan dan ketenangan."
        ),
    },

    "swan_lake_act3_pt1": {
        "music_file":  "Swan Lake Op.20 - Act III Pt.1.mp3",
        "duration_min": 60,
        "composer_en": "Pyotr Ilyich Tchaikovsky",
        "work_en":     "Swan Lake, Op. 20 — Act III, Part 1 (Grand Ball)",
        "work_ar":     "بحيرة البجعة، أوبوس 20 — الفصل الثالث، الجزء الأول (الحفل الكبير)",
        "work_id":     "Swan Lake, Op. 20 — Babak III, Bagian 1 (Pesta Besar)",
        "year":        "1876",
        "license_en":  "Public Domain (1876) — open source orchestral recording",
        "license_ar":  "ملكية عامة (1876) — تسجيل أوركسترالي مفتوح المصدر",
        "license_id":  "Domain Publik (1876) — rekaman orkestra sumber terbuka",
        "intro_en": (
            "Act III of Swan Lake transforms the nocturnal magic of Act II into a glittering, "
            "festive grand ball — one of the most dramatically varied and exciting sections "
            "of the ballet. "
            "Part 1 of Act III includes the brilliant national character dances "
            "(Spanish, Neapolitan, Hungarian, Mazurka) that bring the ballroom to life, "
            "as well as the fateful introduction of Odile, the Black Swan, "
            "who bewitches the Prince with her dazzling virtuosity. "
            "Tchaikovsky's orchestration here is at its most inventive and theatrical. "
            "In this one-hour version the music plays on continuous loop — "
            "vivid, exciting classical music perfect for creative play and active listening."
        ),
        "intro_ar": (
            "يحوّل الفصل الثالث من بحيرة البجعة السحر الليلي للفصل الثاني "
            "إلى حفل راقص كبير براق — أحد أكثر أقسام الباليه تنوعًا ديناميكيًا وإثارةً. "
            "يتضمن الجزء الأول من الفصل الثالث رقصات الشخصيات القومية الرائعة "
            "(الإسبانية والنابولية والهنغارية والمازوركا) التي تُحيي قاعة الرقص، "
            "فضلًا عن مقدمة أوديل المصيرية، البجعة السوداء. "
            "في هذا الإصدار الذي يمتد ساعة كاملة تتكرر الموسيقى في حلقة متواصلة."
        ),
        "intro_id": (
            "Babak III dari Swan Lake mengubah keajaiban nokturnal Babak II "
            "menjadi pesta besar yang berkilau — salah satu bagian balet yang paling "
            "beragam secara dramatis dan menggembirakan. "
            "Bagian 1 Babak III mencakup tarian karakter nasional yang brilian "
            "(Spanyol, Napoli, Hungaria, Mazurka) yang menghidupkan ruang dansa, "
            "serta perkenalan fatal Odile, Angsa Hitam. "
            "Dalam versi satu jam ini musik dimainkan dalam putaran terus-menerus — "
            "musik klasik yang hidup dan menggembirakan untuk bermain kreatif."
        ),
    },

    "swan_lake_act3_concl": {
        "music_file":  "Swan Lake Op.20 - Act III Concl, Allegro.mp3",
        "duration_min": 60,
        "composer_en": "Pyotr Ilyich Tchaikovsky",
        "work_en":     "Swan Lake, Op. 20 — Act III, Conclusion (Black Swan Coda)",
        "work_ar":     "بحيرة البجعة، أوبوس 20 — الفصل الثالث، الخاتمة (كودا البجعة السوداء)",
        "work_id":     "Swan Lake, Op. 20 — Babak III, Penutup (Koda Angsa Hitam)",
        "year":        "1876",
        "license_en":  "Public Domain (1876) — open source orchestral recording",
        "license_ar":  "ملكية عامة (1876) — تسجيل أوركسترالي مفتوح المصدر",
        "license_id":  "Domain Publik (1876) — rekaman orkestra sumber terbuka",
        "intro_en": (
            "The conclusion of Act III — the Black Swan Coda — is one of the most "
            "breathtaking finales in all of classical music. "
            "After Odile, the Black Swan, has tricked the Prince into pledging his love "
            "and breaking his vow to Odette, the music explodes in a triumphant, racing Allegro. "
            "Tchaikovsky's orchestration surges with dark energy, brass fanfares, "
            "and swirling strings as von Rothbart reveals his deception "
            "and the Act ends in catastrophe. "
            "This is thrillingly dramatic classical music — in its one-hour looped form "
            "it makes for an extraordinary listening experience, "
            "equally powerful for dramatic background during creative work or active play."
        ),
        "intro_ar": (
            "خاتمة الفصل الثالث — كودا البجعة السوداء — هي واحدة من أكثر النهايات "
            "إبهارًا في تاريخ الموسيقى الكلاسيكية بأسره. "
            "بعد أن خدعت أوديل، البجعة السوداء، الأمير لكي يُقسم بحبه ويخون عهده لأوديت، "
            "تنفجر الموسيقى في أليغرو متسابق منتصر. "
            "في هذا الإصدار الذي يمتد ساعة كاملة تتكرر هذه الموسيقى الدرامية في حلقة متواصلة."
        ),
        "intro_id": (
            "Penutup Babak III — Koda Angsa Hitam — adalah salah satu finale paling "
            "memukau dalam seluruh musik klasik. "
            "Setelah Odile, Angsa Hitam, mengelabui Pangeran agar bersumpah cintanya "
            "dan mengkhianati janjinya pada Odette, musik meledak dalam Allegro yang berlomba-lomba triumfan. "
            "Ini adalah musik klasik yang dramatis menggembirakan — dalam bentuk putaran satu jam "
            "menjadi pengalaman mendengarkan yang luar biasa."
        ),
    },

    "swan_lake_act4_intro": {
        "music_file":  "Swan Lake Op.20 - Act IV Intro.mp3",
        "duration_min": 60,
        "composer_en": "Pyotr Ilyich Tchaikovsky",
        "work_en":     "Swan Lake, Op. 20 — Act IV, Introduction (The Lake's Tragedy)",
        "work_ar":     "بحيرة البجعة، أوبوس 20 — الفصل الرابع، المقدمة (مأساة البحيرة)",
        "work_id":     "Swan Lake, Op. 20 — Babak IV, Intro (Tragedi Danau)",
        "year":        "1876",
        "license_en":  "Public Domain (1876) — open source orchestral recording",
        "license_ar":  "ملكية عامة (1876) — تسجيل أوركسترالي مفتوح المصدر",
        "license_id":  "Domain Publik (1876) — rekaman orkestra sumber terbuka",
        "intro_en": (
            "Act IV of Swan Lake is the most emotionally devastating section of the entire ballet — "
            "the tragic finale in which Odette, having learned of the Prince's betrayal, "
            "prepares to take her own life to break the spell. "
            "The Introduction to Act IV returns to the moonlit lake, "
            "but now everything is suffused with grief, a dark storm gathering on the horizon. "
            "Tchaikovsky's writing here is of shattering emotional depth: "
            "the White Swan theme returns, now transformed into something heartbreaking. "
            "In this one-hour version this music of extraordinary emotional power "
            "plays on continuous loop — deeply moving for quiet listening, "
            "meditation, or any moment when you need music to match the depth of human feeling."
        ),
        "intro_ar": (
            "الفصل الرابع من بحيرة البجعة هو الأكثر مأساوية عاطفيًا في الباليه بأسره — "
            "الخاتمة المأساوية التي تعلم فيها أوديت بخيانة الأمير "
            "وتستعد لتضحية بنفسها كسرًا للسحر. "
            "مقدمة الفصل الرابع تعود إلى البحيرة المضاءة بالقمر، "
            "لكن الآن كل شيء متشرّب بالحزن وعاصفة داكنة تتجمع في الأفق. "
            "كتابة تشايكوفسكي هنا من عمق عاطفي مروّع: "
            "موضوع البجعة البيضاء يعود، متحوّلًا الآن إلى شيء مؤلم. "
            "في هذا الإصدار تتكرر هذه الموسيقى في حلقة متواصلة لمدة ساعة كاملة."
        ),
        "intro_id": (
            "Babak IV Swan Lake adalah bagian paling menghancurkan secara emosional "
            "dari seluruh balet — finale tragis di mana Odette, setelah mengetahui pengkhianatan Sang Pangeran, "
            "bersiap mengorbankan dirinya untuk memecahkan mantra. "
            "Intro Babak IV kembali ke danau berlumur cahaya bulan, "
            "tetapi kini semuanya diliputi kesedihan, badai gelap berkumpul di cakrawala. "
            "Penulisan Tchaikovsky di sini memiliki kedalaman emosional yang menghancurkan. "
            "Dalam versi satu jam ini musik dengan kekuatan emosional luar biasa ini "
            "dimainkan dalam putaran terus-menerus — sangat mengharukan untuk mendengarkan dalam ketenangan."
        ),
    },
}

# ─── helpers ─────────────────────────────────────────────────────────────────

def find_music_file(filename: str) -> Path:
    """Search MUSIC_DIR first, then MUSIC_DIR2; return first match."""
    p1 = MUSIC_DIR / filename
    if p1.exists():
        return p1
    p2 = MUSIC_DIR2 / filename
    if p2.exists():
        return p2
    return p1  # caller gets a clear "not found" on the original path


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

    # Swan Lake pieces get a special moonlit-lake scene override
    if key.startswith("swan_lake"):
        scene = (
            "moonlit lake at night, white swans gliding on silver water, "
            "mist rising from the surface, ethereal blue and silver tones, "
            "magical fairy-tale atmosphere, cinematic digital art"
        )
    else:
        scene = {
            "stars":  "deep night sky, softly glowing stars and galaxies, floating golden musical notes, rich purple and gold, cinematic digital art",
            "ocean":  "deep glowing ocean at night, luminescent jellyfish floating, bioluminescent blue tones, peaceful underwater scene",
            "garden": "moonlit garden at night, glowing fireflies and soft flowers, golden light, romantic dreamy atmosphere",
            "forest": "moonlit forest at night, glowing fireflies drifting, misty ancient trees, silver moonbeams, magical forest scene",
        }[first]

    # Composer mood hint
    mood = {
        "Ralph Vaughan Williams":     "orchestral grandeur, serene and transcendent",
        "Wolfgang Amadeus Mozart":     "elegant classical, graceful and light",
        "Ludwig van Beethoven":        "powerful and triumphant, dramatic depth",
        "Giuseppe Verdi":              "romantic opera atmosphere, wistful and passionate",
        "Georg Philipp Telemann":      "baroque lightness, airy and introspective",
        "Johann Sebastian Bach":       "baroque depth, pure and meditative",
        "Frédéric Chopin":             "romantic piano, dreamy and introspective",
        "Pyotr Ilyich Tchaikovsky":    "romantic ballet, dramatic and lyrical",
        "Ernesto Köhler":              "elegant flute, bright and expressive",
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
        is_mozart      = "Mozart" in composer
        is_beethoven   = "Beethoven" in composer
        is_vw          = "Vaughan" in composer
        is_verdi       = "Verdi" in composer
        is_telemann    = "Telemann" in composer
        is_bach        = "Bach" in composer
        is_chopin      = "Chopin" in composer
        is_tchaikovsky = "Tchaikovsky" in composer
        is_kohler      = "Köhler" in composer

        if is_mozart:
            search_tags = "#ClassicalMusic #Mozart #EineKleineNachtmusik #MozartForSleep"
        elif is_beethoven and "Moonlight" in v["work_en"]:
            search_tags = "#ClassicalMusic #Beethoven #MoonlightSonata #BeethovenForSleep"
        elif is_beethoven:
            search_tags = "#ClassicalMusic #Beethoven #Symphony5 #BeethovenForSleep"
        elif is_vw:
            search_tags = "#ClassicalMusic #VaughanWilliams #Fantasia #ThomasTallis"
        elif is_verdi:
            search_tags = "#ClassicalMusic #Verdi #LaTraviata #OperaMusic"
        elif is_bach:
            search_tags = "#ClassicalMusic #Bach #CelloSuite #BWV1007"
        elif is_chopin:
            search_tags = "#ClassicalMusic #Chopin #Nocturne #ChopinForSleep"
        elif is_tchaikovsky:
            search_tags = "#ClassicalMusic #Tchaikovsky #SwanLake #Ballet"
        elif is_kohler:
            search_tags = "#ClassicalMusic #Köhler #FluteEtude #SoloFlute"
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
    is_mozart      = "Mozart" in composer
    is_beethoven   = "Beethoven" in composer
    is_vw          = "Vaughan" in composer
    is_verdi       = "Verdi" in composer
    is_bach        = "Bach" in composer
    is_chopin      = "Chopin" in composer
    is_tchaikovsky = "Tchaikovsky" in composer
    is_kohler      = "Köhler" in composer

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
        elif is_beethoven and "Moonlight" in v["work_en"]:
            base_tags += ["beethoven", "moonlight sonata", "piano sonata", "beethoven for sleep"]
        elif is_beethoven:
            base_tags += ["beethoven", "symphony no 5", "beethoven symphony", "beethoven for sleep"]
        elif is_vw:
            base_tags += ["vaughan williams", "fantasia", "thomas tallis", "orchestral sleep"]
        elif is_verdi:
            base_tags += ["verdi", "la traviata", "opera music", "opera for sleep"]
        elif is_bach:
            base_tags += ["bach", "cello suite", "bwv 1007", "baroque music"]
        elif is_chopin:
            base_tags += ["chopin", "nocturne", "chopin nocturne", "piano music for sleep"]
        elif is_tchaikovsky:
            base_tags += ["tchaikovsky", "swan lake", "ballet music", "tchaikovsky for sleep"]
        elif is_kohler:
            base_tags += ["kohler", "flute etude", "solo flute", "flute music"]
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
        "video_type":  "classical_visualizer",
        "language":    lang,
        "is_short":    False,
        "status":      "public",
    }


# ─── thumbnail ───────────────────────────────────────────────────────────────

def _load_gat():
    import importlib.util
    spec = importlib.util.spec_from_file_location("gat", ROOT / "scripts" / "generate_ai_thumbs.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def generate_thumbnail(key: str, lang: str, out_path: Path) -> bool:
    if not TOGETHER_KEY_FILE.exists():
        print("  No Together.ai key — skip thumbnail")
        return False
    api_key = TOGETHER_KEY_FILE.read_text().strip()
    prompt = get_thumb_prompt(key, lang)
    try:
        gat = _load_gat()
        img = gat.together_generate_image(prompt, api_key)
        if img:
            out_path.write_bytes(gat.resize_to_720p(img))
            print(f"  Thumbnail ({lang}): {out_path.name} ({out_path.stat().st_size // 1024}KB)")
            return True
        print(f"  Thumbnail error ({lang}): API returned no image")
        return False
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
        "musicFile":      "",   # no audio in shared loop — classical music added via FFmpeg
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
    music_mp3 = find_music_file(v["music_file"])

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
    total = len(VIDEOS)
    print(f"Classical visualizer — {n}/{total} piece(s) × 3 channels = {n*3} videos")
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
