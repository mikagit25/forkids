#!/usr/bin/env python3
"""
One-time script: copy existing EN dance videos to AR and ID queues
with proper language-specific meta files.

AR queue: dance_fruits (3) + dance_animals extras (3) + dance_vegetables v2 (1) + dance_mixed_interleave (1) = 8
ID queue: all dance themes = 16 videos
"""

import os
import shutil
from pathlib import Path

ROOT = Path("/opt/kids_channel")
UPLOADED = ROOT / "uploaded"
QUEUE_AR = ROOT / "output" / "queue_ar"
QUEUE_ID = ROOT / "output" / "queue_id"

AR_DESC_FRUITS = """مرحباً بكم في هابي بير كيدز! 🐻

30 دقيقة من الرقص والمرح المتواصل مع الفاكهة! جميع شخصياتنا المفضلة من الفاكهة هنا لتجعلكم أنتم وعائلتكم تتحركون وترقصون!

رسوماتنا المتحركة مصممة بألوان زاهية لجذب الأطفال الرضع والصغار.

🌟 المميزات:
• ألوان عالية التباين للتحفيز البصري
• حركات رقص ممتعة لكل شخصية
• شخصيات ودية وملونة
• موسيقى مرحة طوال الفيديو
• ترفيه مثالي في الخلفية

👶 رائع لـ:
• الأطفال الرضع — الوقت على البطن، التتبع البصري، التطور الحسي
• الأطفال الصغار — الرقص والحركة، تعلم أسماء الفاكهة
• الآباء والأمهات — يُسلّي الصغار أثناء إنجاز المهام

🎵 الموسيقى: Kevin MacLeod (incompetech.com)
مرخصة بموجب Creative Commons: رخصة النسب 4.0
http://creativecommons.org/licenses/by/4.0/

© هابي بير كيدز 2026 — جميع الحقوق محفوظة
فيديوهات جديدة كل أسبوع! اشتركوا ▶ @happybearkidsar"""

AR_DESC_ANIMALS = """مرحباً بكم في هابي بير كيدز! 🐻

30 دقيقة من الرقص والمرح المتواصل مع الحيوانات! جميع شخصياتنا المفضلة من الحيوانات هنا لتجعلكم أنتم وعائلتكم تتحركون وترقصون!

رسوماتنا المتحركة مصممة بألوان زاهية لجذب الأطفال الرضع والصغار.

🌟 المميزات:
• ألوان عالية التباين للتحفيز البصري
• حركات رقص ممتعة لكل شخصية
• شخصيات ودية وملونة
• موسيقى مرحة طوال الفيديو
• ترفيه مثالي في الخلفية

👶 رائع لـ:
• الأطفال الرضع — الوقت على البطن، التتبع البصري، التطور الحسي
• الأطفال الصغار — الرقص والحركة، تعلم أسماء الحيوانات
• الآباء والأمهات — يُسلّي الصغار أثناء إنجاز المهام

🎵 الموسيقى: Kevin MacLeod (incompetech.com)
مرخصة بموجب Creative Commons: رخصة النسب 4.0
http://creativecommons.org/licenses/by/4.0/

© هابي بير كيدز 2026 — جميع الحقوق محفوظة
فيديوهات جديدة كل أسبوع! اشتركوا ▶ @happybearkidsar"""

AR_DESC_VEGETABLES = """مرحباً بكم في هابي بير كيدز! 🐻

30 دقيقة من الرقص والمرح المتواصل مع الخضروات! جميع شخصياتنا المفضلة من الخضروات هنا لتجعلكم أنتم وعائلتكم تتحركون وترقصون!

رسوماتنا المتحركة مصممة بألوان زاهية لجذب الأطفال الرضع والصغار.

🌟 المميزات:
• ألوان عالية التباين للتحفيز البصري
• حركات رقص ممتعة لكل شخصية
• شخصيات ودية وملونة
• موسيقى مرحة طوال الفيديو
• ترفيه مثالي في الخلفية

👶 رائع لـ:
• الأطفال الرضع — الوقت على البطن، التتبع البصري، التطور الحسي
• الأطفال الصغار — الرقص والحركة، تعلم أسماء الخضروات
• الآباء والأمهات — يُسلّي الصغار أثناء إنجاز المهام

🎵 الموسيقى: Kevin MacLeod (incompetech.com)
مرخصة بموجب Creative Commons: رخصة النسب 4.0
http://creativecommons.org/licenses/by/4.0/

© هابي بير كيدز 2026 — جميع الحقوق محفوظة
فيديوهات جديدة كل أسبوع! اشتركوا ▶ @happybearkidsar"""

AR_DESC_MIXED = """مرحباً بكم في هابي بير كيدز! 🐻

30 دقيقة من الرقص والمرح المتواصل! فيديو مميز يجمع بين الحيوانات والفاكهة والخضروات في عرض رقص واحد ممتع!

رسوماتنا المتحركة مصممة بألوان زاهية لجذب الأطفال الرضع والصغار.

🌟 المميزات:
• ألوان عالية التباين للتحفيز البصري
• حركات رقص ممتعة لجميع الشخصيات
• مزيج رائع من الحيوانات والفاكهة والأشكال
• موسيقى مرحة طوال الفيديو
• ترفيه مثالي في الخلفية

👶 رائع لـ:
• الأطفال الرضع — الوقت على البطن، التتبع البصري، التطور الحسي
• الأطفال الصغار — الرقص والحركة والمرح
• الآباء والأمهات — يُسلّي الصغار أثناء إنجاز المهام

🎵 الموسيقى: Kevin MacLeod (incompetech.com)
مرخصة بموجب Creative Commons: رخصة النسب 4.0
http://creativecommons.org/licenses/by/4.0/

© هابي بير كيدز 2026 — جميع الحقوق محفوظة
فيديوهات جديدة كل أسبوع! اشتركوا ▶ @happybearkidsar"""

ID_DESC_SHAPES = """Selamat datang di Happy Bear Kids Indonesia! 🐻

30 menit tari bentuk yang menyenangkan untuk si kecil! Semua karakter bentuk favorit kami hadir untuk mengajak kamu dan keluarga bergerak dan menari bersama!

Animasi kami dirancang dengan warna-warna cerah yang menarik perhatian bayi dan balita.

🌟 Fitur Video Ini:
• Warna kontras tinggi untuk stimulasi visual
• Gerakan tari yang menyenangkan untuk setiap karakter
• Karakter ramah dan penuh warna
• Musik ceria sepanjang video
• Hiburan sempurna sebagai latar belakang

👶 Cocok untuk:
• Bayi — tummy time, pelacakan visual, perkembangan sensorik
• Balita — menari, bergerak, dan belajar nama bentuk
• Orang tua — menghibur si kecil saat mengerjakan tugas

Bagian dari seri tari edukasi Happy Bear Kids!

🔔 Subscribe ke Happy Bear Kids Indonesia → @happybearkidsin
Video edukasi baru setiap minggu!

🎵 Musik Latar: Kevin MacLeod (incompetech.com)
Berlisensi Creative Commons Attribution 4.0
http://creativecommons.org/licenses/by/4.0/

#TariBentuk #BentukUntukAnak #BelajarAnak #HappyBearKids #VideoEdukasi #BalitaBelajar #TariAnak #BentukGeometri #PresekolahIndonesia #AnakCerdas

© Happy Bear Kids Indonesia 2026"""

ID_DESC_FRUITS = """Selamat datang di Happy Bear Kids Indonesia! 🐻

30 menit tari buah-buahan yang menyenangkan untuk si kecil! Semua karakter buah favorit kami hadir untuk mengajak kamu dan keluarga bergerak dan menari bersama!

Animasi kami dirancang dengan warna-warna cerah yang menarik perhatian bayi dan balita.

🌟 Fitur Video Ini:
• Warna kontras tinggi untuk stimulasi visual
• Gerakan tari yang menyenangkan untuk setiap karakter buah
• Karakter ramah dan penuh warna
• Musik ceria sepanjang video
• Hiburan sempurna sebagai latar belakang

👶 Cocok untuk:
• Bayi — tummy time, pelacakan visual, perkembangan sensorik
• Balita — menari, bergerak, dan belajar nama buah-buahan
• Orang tua — menghibur si kecil saat mengerjakan tugas

Bagian dari seri tari edukasi Happy Bear Kids!
Apel, pisang, stroberi, anggur, jeruk, semangka, dan banyak lagi menari bersama!

🔔 Subscribe ke Happy Bear Kids Indonesia → @happybearkidsin
Video edukasi baru setiap minggu!

🎵 Musik Latar: Kevin MacLeod (incompetech.com)
Berlisensi Creative Commons Attribution 4.0
http://creativecommons.org/licenses/by/4.0/

#TariBuah #BuahUntukAnak #BelajarAnak #HappyBearKids #VideoEdukasi #BalitaBelajar #TariAnak #BuahBuahan #PresekolahIndonesia #AnakCerdas

© Happy Bear Kids Indonesia 2026"""

ID_DESC_ANIMALS = """Selamat datang di Happy Bear Kids Indonesia! 🐻

30 menit tari hewan yang menyenangkan untuk si kecil! Semua hewan favorit kami hadir untuk mengajak kamu dan keluarga bergerak dan menari bersama!

Animasi kami dirancang dengan warna-warna cerah yang menarik perhatian bayi dan balita.

🌟 Fitur Video Ini:
• Warna kontras tinggi untuk stimulasi visual
• Gerakan tari yang menyenangkan untuk setiap hewan
• Karakter hewan ramah dan penuh warna
• Musik ceria sepanjang video
• Hiburan sempurna sebagai latar belakang

👶 Cocok untuk:
• Bayi — tummy time, pelacakan visual, perkembangan sensorik
• Balita — menari, bergerak, dan belajar nama hewan
• Orang tua — menghibur si kecil saat mengerjakan tugas

Bagian dari seri tari edukasi Happy Bear Kids!
Beruang, singa, gajah, kelinci, dan banyak teman berbulu lainnya menari bersama!

🔔 Subscribe ke Happy Bear Kids Indonesia → @happybearkidsin
Video edukasi baru setiap minggu!

🎵 Musik Latar: Kevin MacLeod (incompetech.com)
Berlisensi Creative Commons Attribution 4.0
http://creativecommons.org/licenses/by/4.0/

#TariHewan #HewanUntukAnak #BelajarAnak #HappyBearKids #VideoEdukasi #BalitaBelajar #TariAnak #HewanLucu #PresekolahIndonesia #AnakCerdas

© Happy Bear Kids Indonesia 2026"""

ID_DESC_VEGETABLES = """Selamat datang di Happy Bear Kids Indonesia! 🐻

30 menit tari sayuran yang menyenangkan untuk si kecil! Semua karakter sayur favorit kami hadir untuk mengajak kamu dan keluarga bergerak dan menari bersama!

Animasi kami dirancang dengan warna-warna cerah yang menarik perhatian bayi dan balita.

🌟 Fitur Video Ini:
• Warna kontras tinggi untuk stimulasi visual
• Gerakan tari yang menyenangkan untuk setiap sayuran
• Karakter ramah dan penuh warna
• Musik ceria sepanjang video
• Hiburan sempurna sebagai latar belakang

👶 Cocok untuk:
• Bayi — tummy time, pelacakan visual, perkembangan sensorik
• Balita — menari, bergerak, dan belajar nama sayuran
• Orang tua — menghibur si kecil saat mengerjakan tugas

Bagian dari seri tari edukasi Happy Bear Kids!
Wortel, brokoli, jagung, tomat, dan banyak sayuran segar lainnya menari bersama!

🔔 Subscribe ke Happy Bear Kids Indonesia → @happybearkidsin
Video edukasi baru setiap minggu!

🎵 Musik Latar: Kevin MacLeod (incompetech.com)
Berlisensi Creative Commons Attribution 4.0
http://creativecommons.org/licenses/by/4.0/

#TariSayur #SayuranUntukAnak #BelajarAnak #HappyBearKids #VideoEdukasi #BalitaBelajar #TariAnak #SayurSehat #PresekolahIndonesia #AnakCerdas

© Happy Bear Kids Indonesia 2026"""

ID_DESC_MIXED = """Selamat datang di Happy Bear Kids Indonesia! 🐻

30 menit tari campuran yang menyenangkan untuk si kecil! Hewan, buah-buahan, dan bentuk hadir bersama dalam satu pertunjukan tari yang spektakuler!

Animasi kami dirancang dengan warna-warna cerah yang menarik perhatian bayi dan balita.

🌟 Fitur Video Ini:
• Warna kontras tinggi untuk stimulasi visual
• Gerakan tari yang menyenangkan untuk semua karakter
• Perpaduan hewan, buah, dan bentuk geometri
• Musik ceria sepanjang video
• Hiburan sempurna sebagai latar belakang

👶 Cocok untuk:
• Bayi — tummy time, pelacakan visual, perkembangan sensorik
• Balita — menari, bergerak, dan bersenang-senang
• Orang tua — menghibur si kecil saat mengerjakan tugas

Bagian dari seri tari edukasi Happy Bear Kids!

🔔 Subscribe ke Happy Bear Kids Indonesia → @happybearkidsin
Video edukasi baru setiap minggu!

🎵 Musik Latar: Kevin MacLeod (incompetech.com)
Berlisensi Creative Commons Attribution 4.0
http://creativecommons.org/licenses/by/4.0/

#TariCampuran #BelajarAnak #HappyBearKids #VideoEdukasi #BalitaBelajar #TariAnak #HewanBuahBentuk #PresekolahIndonesia #AnakCerdas #VideoBalita

© Happy Bear Kids Indonesia 2026"""

# ---------------------------------------------------------------------------
# AR queue entries
# ---------------------------------------------------------------------------
AR_VIDEOS = [
    # (source_mp4, dest_name_in_queue, title, description, tags, theme)
    (
        "dance_fruits_20260524_213552.mp4",
        "dance_fruits_20260618.mp4",
        "رقص الفاكهة | الجزء 1 | 30 دقيقة | هابي بير كيدز",
        AR_DESC_FRUITS,
        ["رقص", "أطفال", "الفاكهة", "هابي بير كيدز", "تعليم", "30 دقيقة", "موسيقى أطفال", "فيديو أطفال", "رسوم متحركة"],
        "fruits",
    ),
    (
        "dance_fruits_20260527.mp4",
        "dance_fruits_20260619.mp4",
        "رقص الفاكهة | الجزء 2 | 30 دقيقة | هابي بير كيدز",
        AR_DESC_FRUITS,
        ["رقص", "أطفال", "الفاكهة", "هابي بير كيدز", "تعليم", "30 دقيقة", "موسيقى أطفال", "فيديو أطفال"],
        "fruits",
    ),
    (
        "dance_fruits_v2_20260528.mp4",
        "dance_fruits_v2_20260620.mp4",
        "رقص الفاكهة | النسخة المميزة | 30 دقيقة | هابي بير كيدز",
        AR_DESC_FRUITS,
        ["رقص", "أطفال", "الفاكهة", "هابي بير كيدز", "تعليم", "30 دقيقة", "موسيقى أطفال", "نسخة محسّنة"],
        "fruits",
    ),
    (
        "dance_animals_20260527.mp4",
        "dance_animals_20260621.mp4",
        "رقص الحيوانات | الجزء 2 | 30 دقيقة | هابي بير كيدز",
        AR_DESC_ANIMALS,
        ["رقص", "أطفال", "الحيوانات", "هابي بير كيدز", "تعليم", "30 دقيقة", "موسيقى أطفال", "حيوانات للأطفال"],
        "animals",
    ),
    (
        "dance_animals_v2_20260528.mp4",
        "dance_animals_v2_20260622.mp4",
        "رقص الحيوانات | النسخة المميزة | 30 دقيقة | هابي بير كيدز",
        AR_DESC_ANIMALS,
        ["رقص", "أطفال", "الحيوانات", "هابي بير كيدز", "تعليم", "30 دقيقة", "موسيقى أطفال", "نسخة محسّنة"],
        "animals",
    ),
    (
        "dance_animals_20260607.mp4",
        "dance_animals_20260623.mp4",
        "رقص الحيوانات | الجزء 3 | 30 دقيقة | هابي بير كيدز",
        AR_DESC_ANIMALS,
        ["رقص", "أطفال", "الحيوانات", "هابي بير كيدز", "تعليم", "30 دقيقة", "موسيقى أطفال"],
        "animals",
    ),
    (
        "dance_vegetables_20260527.mp4",
        "dance_vegetables_20260624.mp4",
        "رقص الخضروات | الجزء 2 | 30 دقيقة | هابي بير كيدز",
        AR_DESC_VEGETABLES,
        ["رقص", "أطفال", "الخضروات", "هابي بير كيدز", "تعليم", "30 دقيقة", "موسيقى أطفال", "خضروات صحية"],
        "vegetables",
    ),
    (
        "dance_mixed_interleave_20260528.mp4",
        "dance_mixed_20260625.mp4",
        "رقص الخلط المميز | حيوانات وفاكهة | هابي بير كيدز",
        AR_DESC_MIXED,
        ["رقص", "أطفال", "مختلط", "هابي بير كيدز", "حيوانات", "فاكهة", "30 دقيقة", "موسيقى أطفال"],
        "mixed",
    ),
]

# ---------------------------------------------------------------------------
# ID queue entries
# ---------------------------------------------------------------------------
ID_VIDEOS = [
    (
        "dance_shapes_cool_20260529.mp4",
        "dance_shapes_cool_20260618.mp4",
        "Tari Bentuk - Warna Keren | 30 Menit | Happy Bear Kids Indonesia",
        ID_DESC_SHAPES,
        ["tari bentuk", "bentuk untuk anak", "happy bear kids", "video edukasi", "balita", "tari anak", "geometri", "belajar bentuk", "warna keren"],
        "shapes",
    ),
    (
        "dance_shapes_pastel_20260529.mp4",
        "dance_shapes_pastel_20260619.mp4",
        "Tari Bentuk - Warna Pastel | 30 Menit | Happy Bear Kids Indonesia",
        ID_DESC_SHAPES,
        ["tari bentuk", "bentuk untuk anak", "happy bear kids", "video edukasi", "balita", "tari anak", "geometri", "warna pastel"],
        "shapes",
    ),
    (
        "dance_shapes_rainbow_20260529.mp4",
        "dance_shapes_rainbow_20260620.mp4",
        "Tari Bentuk - Pelangi | 30 Menit | Happy Bear Kids Indonesia",
        ID_DESC_SHAPES,
        ["tari bentuk", "bentuk untuk anak", "happy bear kids", "video edukasi", "balita", "tari anak", "pelangi", "warna pelangi"],
        "shapes",
    ),
    (
        "dance_shapes_neon_20260605.mp4",
        "dance_shapes_neon_20260621.mp4",
        "Tari Bentuk - Warna Neon | 30 Menit | Happy Bear Kids Indonesia",
        ID_DESC_SHAPES,
        ["tari bentuk", "bentuk untuk anak", "happy bear kids", "video edukasi", "balita", "tari anak", "neon", "warna cerah"],
        "shapes",
    ),
    (
        "dance_shapes_warm_20260529.mp4",
        "dance_shapes_warm_20260622.mp4",
        "Tari Bentuk - Warna Hangat | 30 Menit | Happy Bear Kids Indonesia",
        ID_DESC_SHAPES,
        ["tari bentuk", "bentuk untuk anak", "happy bear kids", "video edukasi", "balita", "tari anak", "warna hangat"],
        "shapes",
    ),
    (
        "dance_fruits_20260524_213552.mp4",
        "dance_fruits_20260623.mp4",
        "Tari Buah-Buahan | Bagian 1 | 30 Menit | Happy Bear Kids Indonesia",
        ID_DESC_FRUITS,
        ["tari buah", "buah untuk anak", "happy bear kids", "video edukasi", "balita", "tari anak", "belajar buah", "buah-buahan"],
        "fruits",
    ),
    (
        "dance_fruits_20260527.mp4",
        "dance_fruits_20260624.mp4",
        "Tari Buah-Buahan | Bagian 2 | 30 Menit | Happy Bear Kids Indonesia",
        ID_DESC_FRUITS,
        ["tari buah", "buah untuk anak", "happy bear kids", "video edukasi", "balita", "tari anak", "belajar buah"],
        "fruits",
    ),
    (
        "dance_fruits_v2_20260528.mp4",
        "dance_fruits_v2_20260625.mp4",
        "Tari Buah-Buahan | Edisi Spesial | 30 Menit | Happy Bear Kids Indonesia",
        ID_DESC_FRUITS,
        ["tari buah", "buah untuk anak", "happy bear kids", "video edukasi", "balita", "tari anak", "edisi spesial"],
        "fruits",
    ),
    (
        "dance_animals_20260524_203703.mp4",
        "dance_animals_20260626.mp4",
        "Tari Hewan | Bagian 1 | 30 Menit | Happy Bear Kids Indonesia",
        ID_DESC_ANIMALS,
        ["tari hewan", "hewan untuk anak", "happy bear kids", "video edukasi", "balita", "tari anak", "belajar hewan", "hewan lucu"],
        "animals",
    ),
    (
        "dance_animals_20260527.mp4",
        "dance_animals_20260627.mp4",
        "Tari Hewan | Bagian 2 | 30 Menit | Happy Bear Kids Indonesia",
        ID_DESC_ANIMALS,
        ["tari hewan", "hewan untuk anak", "happy bear kids", "video edukasi", "balita", "tari anak", "hewan lucu"],
        "animals",
    ),
    (
        "dance_animals_v2_20260528.mp4",
        "dance_animals_v2_20260628.mp4",
        "Tari Hewan | Edisi Spesial | 30 Menit | Happy Bear Kids Indonesia",
        ID_DESC_ANIMALS,
        ["tari hewan", "hewan untuk anak", "happy bear kids", "video edukasi", "balita", "tari anak", "edisi spesial"],
        "animals",
    ),
    (
        "dance_animals_20260607.mp4",
        "dance_animals_20260629.mp4",
        "Tari Hewan | Bagian 3 | 30 Menit | Happy Bear Kids Indonesia",
        ID_DESC_ANIMALS,
        ["tari hewan", "hewan untuk anak", "happy bear kids", "video edukasi", "balita", "tari anak"],
        "animals",
    ),
    (
        "dance_vegetables_20260524_223401.mp4",
        "dance_vegetables_20260630.mp4",
        "Tari Sayuran | Bagian 1 | 30 Menit | Happy Bear Kids Indonesia",
        ID_DESC_VEGETABLES,
        ["tari sayur", "sayuran untuk anak", "happy bear kids", "video edukasi", "balita", "tari anak", "belajar sayur", "sayur sehat"],
        "vegetables",
    ),
    (
        "dance_vegetables_20260527.mp4",
        "dance_vegetables_20260701.mp4",
        "Tari Sayuran | Bagian 2 | 30 Menit | Happy Bear Kids Indonesia",
        ID_DESC_VEGETABLES,
        ["tari sayur", "sayuran untuk anak", "happy bear kids", "video edukasi", "balita", "tari anak", "sayur sehat"],
        "vegetables",
    ),
    (
        "dance_mixed_blocks_20260528.mp4",
        "dance_mixed_blocks_20260702.mp4",
        "Tari Campuran | Blok Warna | 30 Menit | Happy Bear Kids Indonesia",
        ID_DESC_MIXED,
        ["tari campuran", "belajar anak", "happy bear kids", "video edukasi", "balita", "tari anak", "warna blok"],
        "mixed",
    ),
    (
        "dance_mixed_interleave_20260528.mp4",
        "dance_mixed_interleave_20260703.mp4",
        "Tari Campuran | Hewan & Buah | 30 Menit | Happy Bear Kids Indonesia",
        ID_DESC_MIXED,
        ["tari campuran", "belajar anak", "happy bear kids", "video edukasi", "balita", "tari anak", "hewan buah"],
        "mixed",
    ),
]


def make_yaml(title, description, tags, theme, language, dest_mp4_path):
    tag_list = "\n".join(f"- {t}" for t in tags)
    return f"""title: "{title}"
description: |
{chr(10).join('  ' + line for line in description.strip().splitlines())}
tags:
{tag_list}
video_type: dance
language: {language}
theme: {theme}
status: public
is_short: false
source_mp4: {dest_mp4_path}
"""


def setup_queue(videos, queue_dir, language):
    created_mp4 = 0
    created_meta = 0
    skipped = 0
    for src_name, dest_name, title, desc, tags, theme in videos:
        src = UPLOADED / src_name
        dest_mp4 = queue_dir / dest_name
        dest_meta = queue_dir / f"meta_{dest_name.replace('.mp4', '.yaml')}"

        if not src.exists():
            print(f"  MISSING source: {src_name}")
            continue

        if dest_mp4.exists():
            print(f"  skip (exists): {dest_name}")
            skipped += 1
        else:
            try:
                os.link(src, dest_mp4)
                print(f"  linked: {dest_name}")
                created_mp4 += 1
            except OSError:
                shutil.copy2(src, dest_mp4)
                print(f"  copied: {dest_name}")
                created_mp4 += 1

        if dest_meta.exists():
            print(f"  skip (meta exists): {dest_meta.name}")
        else:
            yaml_content = make_yaml(title, desc, tags, theme, language, str(dest_mp4))
            dest_meta.write_text(yaml_content, encoding="utf-8")
            print(f"  meta: {dest_meta.name}")
            created_meta += 1

    print(f"\n  Total: {created_mp4} MP4s linked/copied, {created_meta} meta files created, {skipped} skipped")


print("=== Setting up AR queue (8 dance videos) ===")
setup_queue(AR_VIDEOS, QUEUE_AR, "ar")

print("\n=== Setting up ID queue (16 dance videos) ===")
setup_queue(ID_VIDEOS, QUEUE_ID, "id")

print("\nDone! Next: python3 scripts/generate_ai_thumbs.py --queue ar --backend together")
print("      Then: python3 scripts/generate_ai_thumbs.py --queue id --backend together")
