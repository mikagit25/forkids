#!/usr/bin/env python3
"""
Fix mislabeled shape-based videos (eo_o_dolphin, eo_p_builder, etc.)
These were rendered as DanceShapeLong (geometric shapes) but titled as
ocean/profession/transport videos, creating a content/title mismatch.

Actions:
  1. Update meta files (title, description, video_type=shapes_long)
  2. Generate new thumbnails showing actual geometric shapes
  3. Push updated title+description+thumbnail to YouTube

Usage:
  python3 scripts/fix_shape_videos.py --dry-run
  python3 scripts/fix_shape_videos.py
  python3 scripts/fix_shape_videos.py --skip-youtube   # meta+thumb only
  python3 scripts/fix_shape_videos.py --only-thumb     # regen thumbs only
"""
import argparse
import json
import sys
import time
from pathlib import Path

import yaml

ROOT      = Path(__file__).resolve().parent.parent
UPLOADED  = ROOT / "uploaded"
TOGETHER_KEY = (ROOT / "credentials" / "together_api_key.txt").read_text().strip()

# ── Per-video new identity ─────────────────────────────────────────────────────
# key: original video stem without date (eo_o_dolphin etc.)
# title_en/ar/id: new YouTube titles
# theme: dominant color/mood for thumbnail
# shapes: shape types shown in video
# colors: dominant hex colors

SHAPE_FIX = {
    "eo_o_dolphin": {
        "title_en": "Blue Shapes Dance | 25 min Baby Sensory | Happy Bear Kids",
        "title_ar": "رقصة الأشكال الزرقاء | 25 دقيقة | هابي بير كيدز",
        "title_id": "Tarian Bentuk Biru | 25 Menit Bayi | Happy Bear Kids",
        "theme_en": "calm ocean blue",
        "shapes":   "oval and diamond shapes in shades of blue",
        "color_hex": "#5C9ED9",
        "music":    "calm, soothing",
    },
    "eo_o_jellyfish": {
        "title_en": "Pastel Shapes Dance | 25 min Baby Sensory | Happy Bear Kids",
        "title_ar": "رقصة الأشكال الباستيل | 25 دقيقة | هابي بير كيدز",
        "title_id": "Tarian Bentuk Pastel | 25 Menit Bayi | Happy Bear Kids",
        "theme_en": "soft pastel purple and teal",
        "shapes":   "circles and diamonds in purple, teal and mint",
        "color_hex": "#CE93D8",
        "music":    "calm, Gymnopédie style",
    },
    "eo_o_starfish": {
        "title_en": "Orange Stars Dance | 25 min Baby Sensory | Happy Bear Kids",
        "title_ar": "رقصة النجوم البرتقالية | 25 دقيقة | هابي بير كيدز",
        "title_id": "Tarian Bintang Oranye | 25 Menit Bayi | Happy Bear Kids",
        "theme_en": "warm orange",
        "shapes":   "star shapes in warm orange and coral",
        "color_hex": "#FF7043",
        "music":    "gentle, dreamy",
    },
    "eo_t_airplane": {
        "title_en": "Silver Shapes Dance | 25 min Baby Sensory | Happy Bear Kids",
        "title_ar": "رقصة الأشكال الفضية | 25 دقيقة | هابي بير كيدز",
        "title_id": "Tarian Bentuk Perak | 25 Menit Bayi | Happy Bear Kids",
        "theme_en": "silver and white",
        "shapes":   "circles and diamonds in silver and pale blue",
        "color_hex": "#CFD8DC",
        "music":    "carefree, uplifting",
    },
    "eo_t_helicopter": {
        "title_en": "Golden Shapes Dance | 25 min Baby Sensory | Happy Bear Kids",
        "title_ar": "رقصة الأشكال الذهبية | 25 دقيقة | هابي بير كيدز",
        "title_id": "Tarian Bentuk Emas | 25 Menit Bayi | Happy Bear Kids",
        "theme_en": "golden yellow",
        "shapes":   "circles and diamonds in golden yellow",
        "color_hex": "#FFB300",
        "music":    "quirky, playful",
    },
    "eo_t_ship": {
        "title_en": "Navy Shapes Dance | 25 min Baby Sensory | Happy Bear Kids",
        "title_ar": "رقصة الأشكال الكحلية | 25 دقيقة | هابي بير كيدز",
        "title_id": "Tarian Bentuk Biru Tua | 25 Menit Bayi | Happy Bear Kids",
        "theme_en": "deep navy blue and grey",
        "shapes":   "hexagons, squares and diamonds in deep blue and grey",
        "color_hex": "#29B6F6",
        "music":    "rhythmic, sailing",
    },
    "eo_t_boat": {
        "title_en": "Rainbow Shapes Dance | 25 min Baby Sensory | Happy Bear Kids",
        "title_ar": "رقصة الأشكال قوس قزح | 25 دقيقة | هابي بير كيدز",
        "title_id": "Tarian Bentuk Pelangi | 25 Menit Bayi | Happy Bear Kids",
        "theme_en": "colorful rainbow mix",
        "shapes":   "circles, triangles and ovals in rainbow colors",
        "color_hex": "#29B6F6",
        "music":    "carefree, happy",
    },
    "eo_p_builder": {
        "title_en": "Amber Shapes Dance | 25 min Baby Sensory | Happy Bear Kids",
        "title_ar": "رقصة الأشكال العنبرية | 25 دقيقة | هابي بير كيدز",
        "title_id": "Tarian Bentuk Amber | 25 Menit Bayi | Happy Bear Kids",
        "theme_en": "warm amber and orange",
        "shapes":   "hexagons, squares and diamonds in amber, orange and brown",
        "color_hex": "#FFB300",
        "music":    "upbeat, energetic",
    },
    "eo_p_chef": {
        "title_en": "Colorful Stars Dance | 25 min Baby Sensory | Happy Bear Kids",
        "title_ar": "رقصة النجوم الملونة | 25 دقيقة | هابي بير كيدز",
        "title_id": "Tarian Bintang Warna-warni | 25 Menit Bayi | Happy Bear Kids",
        "theme_en": "vivid rainbow",
        "shapes":   "circles, stars and ovals in vivid rainbow colors",
        "color_hex": "#FDD835",
        "music":    "happy, cheerful",
    },
    "eo_p_doctor": {
        "title_en": "Kaleidoscope Shapes | 25 min Baby Sensory | Happy Bear Kids",
        "title_ar": "أشكال الكاليدوسكوب | 25 دقيقة | هابي بير كيدز",
        "title_id": "Bentuk Kaleidoskop | 25 Menit Bayi | Happy Bear Kids",
        "theme_en": "multicolor kaleidoscope",
        "shapes":   "circles, hexagons, diamonds and stars in red, blue and green",
        "color_hex": "#29B6F6",
        "music":    "carefree, gentle",
    },
    "eo_p_firefighter": {
        "title_en": "Red & Blue Shapes Dance | 25 min Baby Sensory | Happy Bear Kids",
        "title_ar": "رقصة الأشكال الحمراء والزرقاء | 25 دقيقة | هابي بير كيدز",
        "title_id": "Tarian Bentuk Merah dan Biru | 25 Menit Bayi | Happy Bear Kids",
        "theme_en": "bold red and blue",
        "shapes":   "circles, triangles and diamonds in red, orange and blue",
        "color_hex": "#FF5722",
        "music":    "energetic, bold",
    },
    "eo_p_musician": {
        "title_en": "Pastel Stars Dance | 25 min Baby Sensory | Happy Bear Kids",
        "title_ar": "رقصة النجوم الباستيل | 25 دقيقة | هابي بير كيدز",
        "title_id": "Tarian Bintang Pastel | 25 Menit Bayi | Happy Bear Kids",
        "theme_en": "soft pastel purple and teal",
        "shapes":   "circles, stars and diamonds in soft purple, teal and peach",
        "color_hex": "#CE93D8",
        "music":    "soothing, harmonic",
    },
    "eo_p_teacher": {
        "title_en": "Emerald Shapes Dance | 25 min Baby Sensory | Happy Bear Kids",
        "title_ar": "رقصة الأشكال الزمردية | 25 دقيقة | هابي بير كيدز",
        "title_id": "Tarian Bentuk Zamrud | 25 Menit Bayi | Happy Bear Kids",
        "theme_en": "fresh green and gold",
        "shapes":   "circles, stars and squares in emerald green, orange and gold",
        "color_hex": "#66BB6A",
        "music":    "bright, cheerful",
    },
    "eo_p_captain": {
        "title_en": "Gold Stars Dance | 25 min Baby Sensory | Happy Bear Kids",
        "title_ar": "رقصة النجوم الذهبية | 25 دقيقة | هابي بير كيدز",
        "title_id": "Tarian Bintang Emas | 25 Menit Bayi | Happy Bear Kids",
        "theme_en": "dark navy with gold stars and blue diamonds",
        "shapes":   "gold stars and blue diamond shapes on deep dark navy",
        "color_hex": "#FDD835",
        "music":    "orbital, calm",
    },
}

TAGS_SHAPES = [
    "baby sensory", "shapes dance", "geometric shapes", "baby visual",
    "toddler sensory", "calming baby video", "shapes for babies",
    "baby relaxation", "happy bear kids", "25 minutes", "no talking",
    "sensory stimulation", "colorful shapes", "baby focus",
]


def make_desc_en(info: dict) -> str:
    title = info["title_en"]
    shapes = info["shapes"]
    theme = info["theme_en"]
    return f"""{title}

25 minutes of soothing geometric shapes in {theme} colors, gently floating, bouncing and dancing to soft music — perfect for calming babies and toddlers aged 0–3 years.

🎨 What you'll see:
• Beautiful {shapes} moving smoothly across a dark background
• Gentle color variations and soft glowing effects
• Slow, predictable movements that babies love to track

🎵 Soft background music to soothe and relax

👶 Perfect for:
• Visual sensory stimulation for newborns and infants
• Calm focus time for babies aged 0–18 months
• Background gentle stimulation during tummy time
• Calming an overtired or fussy baby
• Screen time that does not overstimulate

🌟 Benefits for baby development:
• Visual tracking practice — following smooth shape movement builds eye muscle control
• Color recognition — babies naturally respond to high-contrast and vivid colors
• Sensory regulation — predictable, calm movement patterns reduce infant stress
• Attention and focus — simple shapes hold baby's interest without overwhelming
• Pattern recognition — repeated shape cycles build early cognitive connections

No characters, no voices, no sudden changes — just gentle shapes and colors in a pure visual experience for your little one.

🎵 Music by Kevin MacLeod (incompetech.com)
Licensed under Creative Commons: By Attribution 4.0 License
http://creativecommons.org/licenses/by/4.0/

© Happy Bear Kids 2026 — All rights reserved
New videos every week! Subscribe → @HappyBearKids1

#HappyBearKids #BabySensory #ShapesDance #GeometricShapes #BabyVisual #ToddlerCalm #SensoryBaby #CalmBabyVideo #ShapesForBabies #BabyRelaxation #25Minutes #NoTalking"""


def make_desc_ar(info: dict) -> str:
    title = info["title_ar"]
    return f"""{title}

25 دقيقة من الأشكال الهندسية المريحة والألوان الجميلة، تتحرك وترقص بلطف على موسيقى هادئة — مثالية لتهدئة الأطفال الرضع والصغار من عمر 0 إلى 3 سنوات.

🎨 ما ستشاهده:
• أشكال هندسية جميلة تتحرك بسلاسة على خلفية داكنة
• تدرجات لونية ناعمة وتأثيرات توهج خفيفة
• حركات بطيئة ومتوقعة يحبها الأطفال الرضع

🎵 موسيقى هادئة للاسترخاء والتهدئة

👶 مثالية لـ:
• التحفيز الحسي البصري للمواليد والرضع
• وقت التركيز الهادئ للأطفال من 0 إلى 18 شهراً
• التحفيز اللطيف في خلفية الصورة أثناء وقت الاستلقاء على البطن
• تهدئة الطفل المتعب أو الباكي

🌟 فوائد لتطور الطفل:
• تدريب على التتبع البصري — تقوية عضلات العين
• التعرف على الألوان — الأطفال يستجيبون للألوان الزاهية بشكل طبيعي
• التنظيم الحسي — الحركات الهادئة تقلل توتر الرضع
• الانتباه والتركيز — الأشكال البسيطة تجذب الاهتمام دون إرهاق

لا شخصيات، لا أصوات، لا تغييرات مفاجئة — فقط تجربة بصرية نقية وهادئة لطفلك الصغير.

© هابي بير كيدز 2026 — جميع الحقوق محفوظة
اشترك → @happybearkidsar

#هابي_بير_كيدز #تحفيز_حسي #أشكال_هندسية #فيديو_الرضع #هدوء_الأطفال #25_دقيقة"""


def make_desc_id(info: dict) -> str:
    title = info["title_id"]
    return f"""{title}

25 menit penuh bentuk geometris yang menenangkan dalam warna-warna indah, melayang dan menari lembut dengan musik yang menenangkan — sempurna untuk menenangkan bayi dan balita usia 0–3 tahun.

🎨 Yang akan kamu lihat:
• Bentuk-bentuk geometris indah bergerak lembut di latar belakang gelap
• Variasi warna lembut dan efek cahaya yang halus
• Gerakan lambat dan dapat diprediksi yang disukai bayi

🎵 Musik latar lembut untuk menenangkan dan relaksasi

👶 Sempurna untuk:
• Stimulasi sensori visual untuk bayi baru lahir dan bayi kecil
• Waktu fokus tenang untuk bayi usia 0–18 bulan
• Stimulasi lembut selama waktu tummy time
• Menenangkan bayi yang kelelahan atau rewel

🌟 Manfaat untuk perkembangan bayi:
• Latihan pelacakan visual — mengikuti gerakan bentuk membangun kontrol otot mata
• Pengenalan warna — bayi secara alami merespons warna-warna cerah
• Regulasi sensori — pola gerakan yang tenang mengurangi stres bayi
• Perhatian dan fokus — bentuk sederhana menarik minat tanpa membebani

Tidak ada karakter, tidak ada suara, tidak ada perubahan mendadak — hanya pengalaman visual yang murni dan menenangkan untuk si kecil.

🎵 Musik oleh Kevin MacLeod (incompetech.com)
Dilisensikan di bawah Creative Commons: By Attribution 4.0 License

© Happy Bear Kids 2026 — Semua hak dilindungi
Video baru setiap minggu! Berlangganan → @happybearkidsin

#HappyBearKids #SensoriBalita #TarianBentuk #BentukGeometris #VideoBalita #TenangBayi #25Menit"""


def build_thumb_prompt(info: dict, is_ar: bool) -> str:
    shapes = info["shapes"]
    color_hex = info["color_hex"]
    theme = info["theme_en"]
    no_txt = ", no text, no letters, no words, no numbers, no faces, no characters, no watermarks"
    return (
        f"Beautiful {shapes} floating and dancing on a deep dark background, "
        f"soft glowing light in {theme} tones, gentle bokeh sparkles, "
        f"smooth dreamy visual for babies, minimalist geometric art, "
        f"16:9 format 1280x720{no_txt}"
    )


def together_gen_image(prompt: str) -> bytes | None:
    import importlib.util
    spec = importlib.util.spec_from_file_location("gat", ROOT / "scripts" / "generate_ai_thumbs.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.together_generate_image(prompt, TOGETHER_KEY)


def resize_720p(img_bytes: bytes) -> bytes:
    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        img = img.resize((1280, 720), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue()
    except Exception:
        return img_bytes


def update_youtube_thumb(video_id: str, thumb_path: Path, channel: str, dry_run: bool) -> bool:
    if dry_run:
        print(f"    [DRY RUN] would update YouTube {video_id} [{channel}]")
        return True
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("uym", ROOT / "scripts" / "update_youtube_meta.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        from googleapiclient.http import MediaFileUpload
        config = mod.load_config()
        yt = mod.get_youtube_service(config, channel)
        media = MediaFileUpload(str(thumb_path), mimetype="image/png")
        yt.thumbnails().set(videoId=video_id, media_body=media).execute()
        print(f"    ✓ thumbnail updated on YouTube")
        return True
    except Exception as e:
        print(f"    ✗ YouTube thumb error: {e}")
        return False


def update_youtube_snippet(video_id: str, title: str, description: str, channel: str, dry_run: bool) -> bool:
    if dry_run:
        print(f"    [DRY RUN] would update snippet: {title[:60]}")
        return True
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("uym", ROOT / "scripts" / "update_youtube_meta.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        config = mod.load_config()
        yt = mod.get_youtube_service(config, channel)
        body = {
            "id": video_id,
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": TAGS_SHAPES,
                "categoryId": "27",
            },
        }
        yt.videos().update(part="snippet", body=body).execute()
        print(f"    ✓ snippet updated on YouTube")
        return True
    except Exception as e:
        print(f"    ✗ YouTube snippet error: {e}")
        return False


def process_video(stem_base: str, info: dict, args) -> None:
    """Process one video key (e.g. 'eo_o_dolphin') across all language variants."""
    lang_map = {
        "":     ("en", info["title_en"], make_desc_en(info)),
        "_ar":  ("ar", info["title_ar"], make_desc_ar(info)),
        "_id":  ("id", info["title_id"], make_desc_id(info)),
    }

    for date_sfx in ["_20260630"]:  # adjust if other dates exist
        for lang_sfx, (lang, title, desc) in lang_map.items():
            stem = f"{stem_base}{date_sfx}{lang_sfx}"
            meta_path  = UPLOADED / f"meta_{stem}.yaml"
            thumb_path = UPLOADED / f"thumb_{stem}.png"

            if not meta_path.exists():
                continue

            meta = yaml.safe_load(meta_path.read_text()) or {}
            video_id = meta.get("youtube_id", "")

            print(f"\n  [{lang.upper()}] {stem}")

            # ── 1. Update meta ─────────────────────────────────────
            if not args.only_thumb:
                meta["title"]       = title
                meta["description"] = desc
                meta["tags"]        = TAGS_SHAPES
                meta["video_type"]  = "shapes_long"
                meta["theme"]       = f"shapes_{info['theme_en'].split()[0]}"
                if not args.dry_run:
                    meta_path.write_text(yaml.dump(meta, allow_unicode=True, sort_keys=False))
                    print(f"    ✓ meta updated")
                else:
                    print(f"    [DRY RUN] meta → {title[:60]}")

            # ── 2. Generate thumbnail ──────────────────────────────
            if not thumb_path.exists() or args.force or args.only_thumb:
                prompt = build_thumb_prompt(info, is_ar=(lang == "ar"))
                print(f"    generating thumb: {prompt[:80]}...")
                if not args.dry_run:
                    img = together_gen_image(prompt)
                    if img:
                        thumb_path.write_bytes(resize_720p(img))
                        print(f"    ✓ thumb saved ({len(img)//1024}KB)")
                    else:
                        print(f"    ✗ thumb failed")
                    time.sleep(1.5)
                else:
                    print(f"    [DRY RUN] would generate thumb")
            else:
                print(f"    thumb exists (use --force to regen)")

            # ── 3. Update YouTube ──────────────────────────────────
            if not args.skip_youtube and not args.only_thumb and video_id:
                update_youtube_snippet(video_id, title, desc, lang, args.dry_run)
                time.sleep(2)

            if not args.skip_youtube and video_id and thumb_path.exists():
                update_youtube_thumb(video_id, thumb_path, lang, args.dry_run)
                time.sleep(3)


def main():
    parser = argparse.ArgumentParser(description="Fix mislabeled shape-based videos")
    parser.add_argument("--dry-run",      action="store_true")
    parser.add_argument("--skip-youtube", action="store_true", help="Update meta+thumb locally only")
    parser.add_argument("--only-thumb",   action="store_true", help="Regenerate thumbnails only")
    parser.add_argument("--force",        action="store_true", help="Force regen thumbnails even if exist")
    parser.add_argument("--video",        help="Process single video key (e.g. eo_p_builder)")
    args = parser.parse_args()

    targets = {args.video: SHAPE_FIX[args.video]} if args.video and args.video in SHAPE_FIX else SHAPE_FIX

    print(f"Fixing {len(targets)} shape-based video(s)...")
    for stem_base, info in targets.items():
        print(f"\n{'='*60}")
        print(f"Video: {stem_base}")
        print(f"  New title (EN): {info['title_en']}")
        process_video(stem_base, info, args)

    print("\n\nDone!")


if __name__ == "__main__":
    main()
