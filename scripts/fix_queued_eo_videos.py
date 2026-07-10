"""
Fix mislabeled eo_p_* videos still waiting in queue_ar / queue_id.

These videos used DanceShapeLong (geometric shapes) but their meta files
say "Firefighter", "Builder" etc. — they need to be renamed to match the
actual content (geometric shapes) before they get published.

Also generates correct geometric shape thumbnails to replace the wrong ones.

eo_p_gardener is CORRECT (DanceSpriteLong with real fruit/veggie sprites) — skipped.
"""

import importlib.util
import sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

TOGETHER_KEY = (ROOT / "credentials" / "together_api_key.txt").read_text().strip()

# ── What each video actually shows ────────────────────────────────────────────
FIXES = {
    "eo_p_builder": {
        "title_ar":  "رقصة الأشكال العنبرية | 25 دقيقة تحفيز حسي | هابي بير كيدز",
        "title_id":  "Tarian Bentuk Kuning Emas | 25 Menit Sensori Bayi | Happy Bear Kids",
        "desc_ar": (
            "✨ أشكال هندسية عنبرية وذهبية ترقص برفق للرضع والأطفال الصغار!\n\n"
            "بدون كلمات أو نصوص — تجربة بصرية خالصة مصممة لإشراك العقول الصغيرة. "
            "مربعات ومسدسات بألوان كهرمانية دافئة تتحرك بسلاسة مع موسيقى هادئة "
            "تخلق تجربة آسرة للرضع.\n\n"
            "👶 العمر: 0–3 سنوات | 📺 25 دقيقة متواصلة\n\n"
            "🔔 اشتركوا ← @happybearkidsar\n"
            "🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
            "#أشكال_هندسية #هابي_بير_كيدز #تحفيز_حسي #رضع #بدون_كلام"
        ),
        "desc_id": (
            "✨ Bentuk geometris kuning emas yang menari lembut untuk bayi dan balita!\n\n"
            "Tanpa kata-kata atau teks — pengalaman visual murni yang dirancang untuk "
            "merangsang pikiran kecil. Persegi dan segi enam berwarna amber hangat bergerak "
            "lembut dengan musik yang menenangkan.\n\n"
            "👶 Usia: 0–3 tahun | 📺 25 menit terus menerus\n\n"
            "🔔 Berlangganan ← @happybearkidsin\n"
            "🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
            "#BentukGeometris #HappyBearKids #SensoriBalita #BayiTenang #TanpaKata"
        ),
        "tags_ar": ["أشكال هندسية", "تحفيز حسي", "هابي بير كيدز", "رضع", "بدون كلام"],
        "tags_id": ["bentuk geometris", "sensori bayi", "happy bear kids", "bayi", "tanpa teks"],
        "thumb_prompt": "amber golden geometric squares and hexagons dancing gracefully on deep dark background, warm orange tones, baby sensory video",
    },
    "eo_p_captain": {
        "title_ar":  "رقصة النجوم الذهبية | 25 دقيقة تحفيز حسي | هابي بير كيدز",
        "title_id":  "Tarian Bintang Emas | 25 Menit Sensori Bayi | Happy Bear Kids",
        "desc_ar": (
            "✨ نجوم ذهبية ومعينات زرقاء ترقص في الليل للرضع والأطفال الصغار!\n\n"
            "بدون كلمات أو نصوص — تجربة بصرية خالصة مصممة لإشراك العقول الصغيرة. "
            "نجوم لامعة ومعينات زرقاء تتحرك بأناقة على خلفية داكنة هادئة.\n\n"
            "👶 العمر: 0–3 سنوات | 📺 25 دقيقة متواصلة\n\n"
            "🔔 اشتركوا ← @happybearkidsar\n"
            "🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
            "#نجوم_ذهبية #هابي_بير_كيدز #تحفيز_حسي #رضع #بدون_كلام"
        ),
        "desc_id": (
            "✨ Bintang emas dan berlian biru yang menari di malam hari untuk bayi dan balita!\n\n"
            "Tanpa kata-kata atau teks — pengalaman visual murni yang memikat perhatian bayi. "
            "Bintang-bintang berkilau dan berlian biru bergerak elegan di latar belakang gelap.\n\n"
            "👶 Usia: 0–3 tahun | 📺 25 menit terus menerus\n\n"
            "🔔 Berlangganan ← @happybearkidsin\n"
            "🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
            "#BintangEmas #HappyBearKids #SensoriBalita #BayiTenang #TanpaKata"
        ),
        "tags_ar": ["نجوم ذهبية", "تحفيز حسي", "هابي بير كيدز", "رضع", "بدون كلام"],
        "tags_id": ["bintang emas", "sensori bayi", "happy bear kids", "bayi", "tanpa teks"],
        "thumb_prompt": "golden yellow twinkling stars and blue diamond shapes orbiting on deep dark navy background, sparkling lights, baby sensory video",
    },
    "eo_p_firefighter": {
        "title_ar":  "رقصة الأشكال الحمراء والزرقاء | 25 دقيقة تحفيز حسي | هابي بير كيدز",
        "title_id":  "Tarian Bentuk Merah & Biru | 25 Menit Sensori Bayi | Happy Bear Kids",
        "desc_ar": (
            "✨ مثلثات حمراء ومعينات زرقاء ترقص بحيوية للرضع والأطفال الصغار!\n\n"
            "بدون كلمات أو نصوص — تجربة بصرية خالصة مصممة لإشراك العقول الصغيرة. "
            "أشكال هندسية حمراء وبرتقالية وزرقاء تتحرك بطاقة ولكن برفق على خلفية داكنة.\n\n"
            "👶 العمر: 0–3 سنوات | 📺 25 دقيقة متواصلة\n\n"
            "🔔 اشتركوا ← @happybearkidsar\n"
            "🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
            "#أشكال_هندسية #هابي_بير_كيدز #تحفيز_حسي #رضع #بدون_كلام"
        ),
        "desc_id": (
            "✨ Segitiga merah dan berlian biru yang menari bersemangat untuk bayi dan balita!\n\n"
            "Tanpa kata-kata atau teks — pengalaman visual murni yang merangsang indra bayi. "
            "Bentuk merah, oranye, dan biru bergerak penuh energi namun lembut di latar gelap.\n\n"
            "👶 Usia: 0–3 tahun | 📺 25 menit terus menerus\n\n"
            "🔔 Berlangganan ← @happybearkidsin\n"
            "🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
            "#BentukMerahBiru #HappyBearKids #SensoriBalita #BayiTenang #TanpaKata"
        ),
        "tags_ar": ["أشكال حمراء وزرقاء", "تحفيز حسي", "هابي بير كيدز", "رضع", "بدون كلام"],
        "tags_id": ["bentuk merah biru", "sensori bayi", "happy bear kids", "bayi", "tanpa teks"],
        "thumb_prompt": "red orange triangles and cool blue diamond shapes bouncing dynamically on dark background, vivid contrast, baby sensory video",
    },
    "eo_p_musician": {
        "title_ar":  "رقصة الأشكال الباستيلية | 25 دقيقة تحفيز حسي | هابي بير كيدز",
        "title_id":  "Tarian Bentuk Pastel | 25 Menit Sensori Bayi | Happy Bear Kids",
        "desc_ar": (
            "✨ أشكال هندسية بألوان باستيل ناعمة ترقص برفق للرضع والأطفال الصغار!\n\n"
            "بدون كلمات أو نصوص — تجربة بصرية خالصة مصممة لإشراك العقول الصغيرة. "
            "معينات ونجوم ودوائر بألوان أرجوانية وزهرية وأخضر مائي تتحرك بسلاسة وجمال.\n\n"
            "👶 العمر: 0–3 سنوات | 📺 25 دقيقة متواصلة\n\n"
            "🔔 اشتركوا ← @happybearkidsar\n"
            "🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
            "#أشكال_باستيل #هابي_بير_كيدز #تحفيز_حسي #رضع #بدون_كلام"
        ),
        "desc_id": (
            "✨ Bentuk geometris berwarna pastel lembut yang menari untuk bayi dan balita!\n\n"
            "Tanpa kata-kata atau teks — pengalaman visual murni yang menenangkan bayi. "
            "Berlian, bintang, dan lingkaran berwarna ungu, merah muda, dan hijau toska "
            "bergerak anggun dan memukau.\n\n"
            "👶 Usia: 0–3 tahun | 📺 25 menit terus menerus\n\n"
            "🔔 Berlangganan ← @happybearkidsin\n"
            "🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
            "#BentukPastel #HappyBearKids #SensoriBalita #BayiTenang #TanpaKata"
        ),
        "tags_ar": ["أشكال باستيل", "تحفيز حسي", "هابي بير كيدز", "رضع", "بدون كلام"],
        "tags_id": ["bentuk pastel", "sensori bayi", "happy bear kids", "bayi", "tanpa teks"],
        "thumb_prompt": "soft pastel geometric diamonds stars and circles in purple pink teal yellow floating on dark background, dreamy colors, baby sensory video",
    },
    "eo_p_teacher": {
        "title_ar":  "رقصة الأشكال الزمردية | 25 دقيقة تحفيز حسي | هابي بير كيدز",
        "title_id":  "Tarian Bentuk Zamrud | 25 Menit Sensori Bayi | Happy Bear Kids",
        "desc_ar": (
            "✨ مربعات زمردية ونجوم ذهبية ترقص برفق للرضع والأطفال الصغار!\n\n"
            "بدون كلمات أو نصوص — تجربة بصرية خالصة مصممة لإشراك العقول الصغيرة. "
            "مربعات خضراء غنية ونجوم برتقالية وصفراء تتحرك ببطء وسلاسة على خلفية داكنة.\n\n"
            "👶 العمر: 0–3 سنوات | 📺 25 دقيقة متواصلة\n\n"
            "🔔 اشتركوا ← @happybearkidsar\n"
            "🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
            "#أشكال_زمردية #هابي_بير_كيدز #تحفيز_حسي #رضع #بدون_كلام"
        ),
        "desc_id": (
            "✨ Persegi zamrud dan bintang emas yang menari lembut untuk bayi dan balita!\n\n"
            "Tanpa kata-kata atau teks — pengalaman visual murni yang menenangkan dan memukau. "
            "Persegi hijau zamrud dan bintang oranye-kuning bergerak perlahan dan anggun "
            "di latar belakang gelap yang menenangkan.\n\n"
            "👶 Usia: 0–3 tahun | 📺 25 menit terus menerus\n\n"
            "🔔 Berlangganan ← @happybearkidsin\n"
            "🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
            "#BentukZamrud #HappyBearKids #SensoriBalita #BayiTenang #TanpaKata"
        ),
        "tags_ar": ["أشكال زمردية", "تحفيز حسي", "هابي بير كيدز", "رضع", "بدون كلام"],
        "tags_id": ["bentuk zamrud", "sensori bayi", "happy bear kids", "bayi", "tanpa teks"],
        "thumb_prompt": "emerald green squares and golden yellow glowing stars dancing on dark deep green background, rich vibrant colors, baby sensory video",
    },
}

QUEUES = {
    "ar": ROOT / "output" / "queue_ar",
    "id": ROOT / "output" / "queue_id",
}
DATES = {"ar": "20260630", "id": "20260630"}


def load_gat():
    spec = importlib.util.spec_from_file_location("gat", ROOT / "scripts" / "generate_ai_thumbs.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fix_meta(key: str, lang: str, queue: Path, fix: dict, dry_run: bool):
    date = DATES[lang]
    lang_sfx = f"_{lang}"
    meta_path = queue / f"meta_{key}_{date}{lang_sfx}.yaml"

    if not meta_path.exists():
        print(f"  [{lang.upper()}] meta not found: {meta_path.name}")
        return

    if dry_run:
        print(f"  [{lang.upper()}] [DRY] would update: {meta_path.name}")
        print(f"           title → {fix[f'title_{lang}']}")
        return

    with open(meta_path) as f:
        meta = yaml.safe_load(f)

    meta["title"] = fix[f"title_{lang}"]
    meta["description"] = fix[f"desc_{lang}"]
    meta["tags"] = fix[f"tags_{lang}"]
    meta["video_type"] = "shapes_long"

    meta_path.write_text(yaml.dump(meta, allow_unicode=True, sort_keys=False))
    print(f"  [{lang.upper()}] meta updated → {fix[f'title_{lang}'][:50]}")


def fix_thumb(key: str, lang: str, queue: Path, fix: dict, dry_run: bool, force: bool):
    date = DATES[lang]
    lang_sfx = f"_{lang}"
    thumb_path = queue / f"thumb_{key}_{date}{lang_sfx}.png"

    if thumb_path.exists() and not force:
        print(f"  [{lang.upper()}] thumb exists (use --force to regen)")
        return

    prompt = fix["thumb_prompt"]
    if lang == "ar":
        prompt += ", no text, no letters, no words, no numbers, no watermarks"
    else:
        prompt += ", vibrant colors, 16:9 format 1280x720"

    if dry_run:
        print(f"  [{lang.upper()}] [DRY] thumb: {prompt[:60]}")
        return

    gat = load_gat()
    img = gat.together_generate_image(prompt, TOGETHER_KEY)
    if img:
        thumb_path.write_bytes(gat.resize_to_720p(img))
        print(f"  [{lang.upper()}] thumb generated ✓")
    else:
        print(f"  [{lang.upper()}] thumb FAILED")


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--force", action="store_true", help="Regenerate thumbs even if they exist")
    p.add_argument("--only-meta", action="store_true")
    p.add_argument("--only-thumb", action="store_true")
    args = p.parse_args()

    for key, fix in FIXES.items():
        print(f"\n{'='*60}")
        print(f"Fixing: {key}")
        for lang, queue in QUEUES.items():
            if not args.only_thumb:
                fix_meta(key, lang, queue, fix, args.dry_run)
            if not args.only_meta:
                fix_thumb(key, lang, queue, fix, args.dry_run, args.force)


if __name__ == "__main__":
    main()
