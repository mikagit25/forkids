#!/usr/bin/env python3
"""
Enrich video descriptions in all meta_*.yaml files.
Generates full-length YouTube descriptions with welcome text,
key features, music credits (Suno AI), and copyright.

Usage:
  python3 scripts/enrich_descriptions.py              # both queues
  python3 scripts/enrich_descriptions.py --queue en
  python3 scripts/enrich_descriptions.py --queue ar
  python3 scripts/enrich_descriptions.py --dry-run    # preview only
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import yaml

YEAR = 2026
CHANNEL_EN = "Happy Bear Kids"
CHANNEL_AR = "هابي بير كيدز"
CHANNEL_URL = "@HappyBearKids1"

KM_LICENSE = "🎵 Original music by Happy Bear Kids (AI-generated, © 2026)"

KM_LICENSE_AR = "🎵 موسيقى أصلية من هابي بير كيدز"

# ── English description templates ─────────────────────────────────────────────

def desc_dance_short_en(character: str, theme: str) -> str:
    theme_label = {"animals": "animal", "fruits": "fruit", "vegetables": "vegetable"}.get(theme, theme)
    cap = character.capitalize()
    return f"""Welcome to {CHANNEL_EN}! 🐻

Watch {cap} dance and groove to the beat! Our cheerful {theme_label} characters are here to get you and your little ones dancing and smiling!

All animations feature bright, colorful characters set to upbeat music carefully chosen for babies, toddlers, and young children.

🌟 Key features:
• Colorful, engaging animation
• Fun dance routines synchronized to the beat
• Friendly {cap} character kids will love
• Upbeat music perfect for the whole family
• Great for visual tracking and sensory stimulation

👶 Perfect for:
• Babies (0–12 months) — visual stimulation & tracking
• Toddlers (1–3 years) — dancing & movement
• Preschoolers (3–5 years) — learning {theme_label} names

{KM_LICENSE}

© {CHANNEL_EN} {YEAR} — All rights reserved
Subscribe for new videos every week! ▶ {CHANNEL_URL}"""


def desc_dance_long_en(theme: str) -> str:
    theme_label = {"animals": "Animals", "fruits": "Fruits", "vegetables": "Vegetables",
                   "shapes": "Shapes"}.get(theme, theme.capitalize())
    return f"""Welcome to {CHANNEL_EN}! 🐻

30 minutes of non-stop {theme_label} dancing fun! All your favourite {theme_label.lower()} characters are here to get you and your family moving and grooving!

Our animations are designed in vivid colours to captivate babies and toddlers. Every character is uniquely designed and set to music carefully curated for the whole family to enjoy.

🌟 Key features:
• High contrast colours for visual stimulation
• Fun dance routines for every character
• Friendly, colourful characters
• Upbeat music throughout — no silence, no ads between songs
• Perfect background entertainment

👶 Great for:
• Babies — tummy time, visual tracking, sensory development
• Toddlers — dancing, movement, learning {theme_label.lower()} names
• Parents — entertains little ones while you get things done!

🎯 Educational value:
• {theme_label} recognition and vocabulary
• Colour and shape awareness
• Rhythm and music appreciation
• Cause-and-effect understanding

{KM_LICENSE}

© {CHANNEL_EN} {YEAR} — All rights reserved
New videos every week! Subscribe ▶ {CHANNEL_URL}"""


def desc_vocab_en(letter: str, word: str) -> str:
    return f"""Welcome to {CHANNEL_EN}! 🐻

{letter} is for {word.capitalize()}! 🌟 Let's learn the letter {letter} together with a fun, colourful animation!

Perfect for toddlers and preschoolers beginning their reading journey. Each video features clear letter display, a picture word, and cheerful audio to make learning stick!

📚 What your child will learn:
• Letter {letter} — upper and lowercase recognition
• The word "{word.capitalize()}" and what it looks like
• Letter-sound association: "{letter}" makes the "{letter.lower()}" sound
• Vocabulary building through visual memory

🌟 Key features:
• Big, bold letters — easy to see
• Colourful picture cards
• Clear pronunciation
• Bright, engaging animation
• Short format — perfect attention span for toddlers

{KM_LICENSE}

© {CHANNEL_EN} {YEAR} — All rights reserved
Learn all 26 letters! Subscribe ▶ {CHANNEL_URL}"""


def desc_colorlearn_en(color: str) -> str:
    cap = color.capitalize()
    return f"""Welcome to {CHANNEL_EN}! 🐻

Let's learn the colour {cap}! 🎨 Can YOU find something {color} around you?

This fun colour learning video will help your little one recognise and remember {cap} through bright visuals, colourful fruit and vegetable friends, and a catchy audio prompt!

🌈 What your child will learn:
• How to identify the colour {cap}
• The word "{cap}" — spoken clearly and repeated
• Real-world examples of things that are {color}
• Colour vocabulary through visual association

🌟 Key features:
• Bold {cap} colour theme throughout
• Colourful cartoon characters
• Repetition — the key to colour memory!
• Short format ideal for young attention spans
• Upbeat background music

{KM_LICENSE}

© {CHANNEL_EN} {YEAR} — All rights reserved
Learn all 7 colours! Subscribe ▶ {CHANNEL_URL}"""


def desc_shape_float_en(shape: str, mode: str) -> str:
    mode_label = {"tb": "raining down", "lr": "floating across", "diag": "drifting diagonally", "float": "gently floating"}.get(mode, "floating")
    cap = shape.capitalize()
    return f"""Welcome to {CHANNEL_EN}! 🐻

Watch {cap} shapes {mode_label} the screen in this relaxing, visually engaging animation! 🔷

Great for babies' visual tracking, or as calm background visuals for toddlers learning their shapes.

🔷 What your child will learn:
• The {cap} shape — recognising it in different sizes and colours
• The word "{cap}" — displayed and spoken clearly
• Shape tracking — following moving objects with their eyes

🌟 Key features:
• Smooth, calming animation
• Multiple sizes and shades of {cap}
• Clear shape label
• Soothing background music
• Perfect for tummy time, wind-down, or play

{KM_LICENSE}

© {CHANNEL_EN} {YEAR} — All rights reserved
Learn all shapes! Subscribe ▶ {CHANNEL_URL}"""


def desc_shape_dance_en(shapes: str) -> str:
    return f"""Welcome to {CHANNEL_EN}! 🐻

Shapes are dancing! ⭐ Watch {shapes} bounce and groove in this fun, colourful animation for kids!

🔷 What your child will learn:
• Shape recognition — circle, square, triangle, star and more
• Shape names through audio and visual repetition
• Colours and movement

🌟 Key features:
• Multiple shapes dancing together
• High-contrast vibrant colours
• Beat-synchronised animations
• Fun upbeat music
• Perfect for toddlers and preschoolers

{KM_LICENSE}

© {CHANNEL_EN} {YEAR} — All rights reserved
Learn all shapes! Subscribe ▶ {CHANNEL_URL}"""


def desc_counting_en() -> str:
    return f"""Welcome to {CHANNEL_EN}! 🐻

Let's count from 1 to 10! 🔢 This fun counting video uses colourful animated shapes to help toddlers and preschoolers learn their numbers!

🔢 What your child will learn:
• Counting from 1 to 10
• Number recognition
• One-to-one correspondence (one number = one object)
• Colour and shape vocabulary

🌟 Key features:
• Clear number display
• Colourful, engaging shapes
• Repetitive counting — builds memory
• Upbeat background music
• Perfect for ages 2–5

{KM_LICENSE}

© {CHANNEL_EN} {YEAR} — All rights reserved
Subscribe for more learning videos ▶ {CHANNEL_URL}"""


def desc_color_theme_en(color: str, theme: str) -> str:
    cap_color = color.capitalize()
    cap_theme = {"animals": "Animals", "fruits": "Fruits", "vegetables": "Vegetables"}.get(theme, theme.capitalize())
    return f"""Welcome to {CHANNEL_EN}! 🐻

Discover the colour {cap_color} through your favourite {cap_theme}! 🌈 Can you spot all the {color} things?

🌈 What your child will learn:
• The colour {cap_color} through real-world {cap_theme.lower()}
• {cap_theme} names and recognition
• Colour vocabulary building

🌟 Key features:
• Beautiful {cap_color} colour theme
• Fun {cap_theme.lower()} characters
• Clear audio labels
• Bright, engaging visuals

{KM_LICENSE}

© {CHANNEL_EN} {YEAR} — All rights reserved
Subscribe ▶ {CHANNEL_URL}"""


# ── Arabic description templates ──────────────────────────────────────────────

def desc_dance_short_ar(character_ar: str, character_en: str, theme: str) -> str:
    theme_ar = {"animals": "الحيوانات", "fruits": "الفواكه", "vegetables": "الخضروات"}.get(theme, theme)
    return f"""مرحباً بكم في {CHANNEL_AR}! 🐻

شاهدوا {character_ar} يرقص على الإيقاع! شخصياتنا الملونة من {theme_ar} هنا لتجعلكم أنتم وأطفالكم ترقصون وتبتسمون!

جميع الرسوم المتحركة تتميز بشخصيات مشرقة وملونة مع موسيقى مرحة مختارة بعناية للأطفال الصغار.

🌟 المميزات:
• رسوم متحركة ملونة وجذابة
• حركات رقص ممتعة
• شخصية {character_ar} المحبوبة
• موسيقى مرحة مناسبة للعائلة كلها
• رائع للتتبع البصري والتحفيز الحسي

👶 مناسب لـ:
• الأطفال الرضع (0–12 شهر) — التحفيز البصري
• الأطفال الصغار (1–3 سنوات) — الرقص والحركة
• أطفال ما قبل المدرسة (3–5 سنوات) — تعلم أسماء {theme_ar}

{KM_LICENSE_AR}

© {CHANNEL_AR} {YEAR} — جميع الحقوق محفوظة
اشتركوا لمتابعة فيديوهات جديدة كل أسبوع! ▶ {CHANNEL_URL}"""


def desc_dance_long_ar(theme: str) -> str:
    theme_ar = {"animals": "الحيوانات", "fruits": "الفواكه", "vegetables": "الخضروات",
                "shapes": "الأشكال"}.get(theme, theme)
    return f"""مرحباً بكم في {CHANNEL_AR}! 🐻

30 دقيقة من الرقص والمرح المتواصل مع {theme_ar}! جميع شخصياتنا المفضلة من {theme_ar} هنا لتجعلكم أنتم وعائلتكم تتحركون وترقصون!

رسوماتنا المتحركة مصممة بألوان زاهية لجذب الأطفال الرضع والصغار.

🌟 المميزات:
• ألوان عالية التباين للتحفيز البصري
• حركات رقص ممتعة لكل شخصية
• شخصيات ودية وملونة
• موسيقى مرحة طوال الفيديو
• ترفيه مثالي في الخلفية

👶 رائع لـ:
• الأطفال الرضع — الوقت على البطن، التتبع البصري، التطور الحسي
• الأطفال الصغار — الرقص والحركة، تعلم أسماء {theme_ar}
• الآباء والأمهات — يُسلّي الصغار أثناء إنجاز المهام

{KM_LICENSE_AR}

© {CHANNEL_AR} {YEAR} — جميع الحقوق محفوظة
فيديوهات جديدة كل أسبوع! اشتركوا ▶ {CHANNEL_URL}"""


def desc_colorlearn_ar(color_ar: str, color_en: str) -> str:
    return f"""مرحباً بكم في {CHANNEL_AR}! 🐻

هيا نتعلم لون {color_ar}! 🎨 هل تستطيع إيجاد شيء {color_ar} من حولك؟

هذا الفيديو الممتع لتعليم الألوان سيساعد طفلك الصغير على التعرف على لون {color_ar} وتذكره!

🌈 ما سيتعلمه طفلك:
• كيفية التعرف على لون {color_ar}
• كلمة "{color_ar}" — تُنطق بوضوح وتتكرر
• أمثلة من الواقع على الأشياء {color_ar} اللون
• مفردات الألوان من خلال الربط البصري

🌟 المميزات:
• ألوان {color_ar} زاهية طوال الفيديو
• شخصيات كرتونية ملونة
• التكرار — مفتاح تذكر الألوان!
• تنسيق قصير مثالي للأطفال الصغار
• موسيقى مرحة في الخلفية

{KM_LICENSE_AR}

© {CHANNEL_AR} {YEAR} — جميع الحقوق محفوظة
تعلموا جميع الألوان السبعة! اشتركوا ▶ {CHANNEL_URL}"""


def desc_shape_float_ar(shape_ar: str, shape_en: str) -> str:
    return f"""مرحباً بكم في {CHANNEL_AR}! 🐻

شاهد أشكال {shape_ar} تتحرك بسلاسة عبر الشاشة في هذه الرسوم المتحركة المريحة بصرياً! 🔷

رائع لتتبع الأطفال الرضع بصرياً، أو كخلفية هادئة للأطفال الصغار وهم يتعلمون الأشكال.

🔷 ما سيتعلمه طفلك:
• شكل {shape_ar} — التعرف عليه بأحجام وألوان مختلفة
• كلمة "{shape_ar}" — تُعرض وتُنطق بوضوح
• تتبع الأشكال بصرياً

🌟 المميزات:
• رسوم متحركة سلسة وهادئة
• أحجام وظلال متعددة من {shape_ar}
• تسمية واضحة للشكل
• موسيقى هادئة في الخلفية
• مثالي لوقت البطن أو الاسترخاء

{KM_LICENSE_AR}

© {CHANNEL_AR} {YEAR} — جميع الحقوق محفوظة
تعلموا جميع الأشكال! اشتركوا ▶ {CHANNEL_URL}"""


def desc_shape_dance_ar(shapes_ar: str) -> str:
    return f"""مرحباً بكم في {CHANNEL_AR}! 🐻

الأشكال ترقص! ⭐ شاهد {shapes_ar} يقفزون ويرقصون في هذه الرسوم المتحركة الممتعة والملونة للأطفال!

🔷 ما سيتعلمه طفلك:
• التعرف على الأشكال — دائرة، مربع، مثلث، نجمة والمزيد
• أسماء الأشكال من خلال التكرار السمعي والبصري
• الألوان والحركة

🌟 المميزات:
• أشكال متعددة ترقص معاً
• ألوان زاهية عالية التباين
• رسوم متحركة متزامنة مع الإيقاع
• موسيقى مرحة
• مثالي للأطفال الصغار

{KM_LICENSE_AR}

© {CHANNEL_AR} {YEAR} — جميع الحقوق محفوظة
تعلموا جميع الأشكال! اشتركوا ▶ {CHANNEL_URL}"""


def desc_counting_ar() -> str:
    return f"""مرحباً بكم في {CHANNEL_AR}! 🐻

هيا نعد من 1 إلى 10! 🔢 يستخدم هذا الفيديو الممتع للعد أشكالاً متحركة ملونة لمساعدة الأطفال الصغار على تعلم الأرقام!

🔢 ما سيتعلمه طفلك:
• العد من 1 إلى 10
• التعرف على الأرقام
• التوافق بين العدد والكمية
• مفردات الألوان والأشكال

🌟 المميزات:
• عرض واضح للأرقام
• أشكال ملونة جذابة
• التكرار يبني الذاكرة
• موسيقى مرحة في الخلفية
• مثالي للأعمار 2–5 سنوات

{KM_LICENSE_AR}

© {CHANNEL_AR} {YEAR} — جميع الحقوق محفوظة
اشتركوا لمزيد من الفيديوهات التعليمية ▶ {CHANNEL_URL}"""


# ── Extraction helpers ─────────────────────────────────────────────────────────

ANIMALS_AR_MAP = {
    "bear": "دب", "tiger": "نمر", "frog": "ضفدع", "penguin": "بطريق",
    "lion": "أسد", "panda": "باندا", "koala": "كوالا", "fox": "ثعلب",
    "rabbit": "أرنب", "cow": "بقرة", "duck": "بطة", "pig": "خنزير",
    "elephant": "فيل", "monkey": "قرد", "dog": "كلب", "cat": "قطة",
    "owl": "بومة", "unicorn": "وحيد القرن", "dino": "ديناصور", "parrot": "ببغاء",
}
FRUITS_AR_MAP = {
    "apple": "تفاحة", "banana": "موزة", "strawberry": "فراولة", "watermelon": "بطيخ",
    "orange": "برتقالة", "grapes": "عنب", "pineapple": "أناناس", "cherry": "كرز",
    "lemon": "ليمون", "peach": "خوخ", "pear": "إجاصة", "melon": "شمام",
}
VEGS_AR_MAP = {
    "carrot": "جزرة", "broccoli": "بروكلي", "corn": "ذرة", "tomato": "طماطم",
    "cucumber": "خيار", "eggplant": "باذنجان", "onion": "بصلة", "pepper": "فلفل",
    "potato": "بطاطا", "pumpkin": "قرع",
}
COLORS_AR_MAP = {
    "red": "أحمر", "orange": "برتقالي", "yellow": "أصفر", "green": "أخضر",
    "blue": "أزرق", "purple": "بنفسجي", "pink": "وردي", "brown": "بني",
}
SHAPES_AR_MAP = {
    "circle": "دائرة", "square": "مربع", "triangle": "مثلث", "star": "نجمة",
    "diamond": "معين", "heart": "قلب", "hexagon": "مسدس", "oval": "بيضاوي",
}
ALL_AR = {**ANIMALS_AR_MAP, **FRUITS_AR_MAP, **VEGS_AR_MAP}

THEME_FOR = {}
for k in ANIMALS_AR_MAP: THEME_FOR[k] = "animals"
for k in FRUITS_AR_MAP:  THEME_FOR[k] = "fruits"
for k in VEGS_AR_MAP:    THEME_FOR[k] = "vegetables"


def extract_character(stem: str) -> tuple[str, str]:
    """Return (character_en, theme) from stem."""
    n = re.sub(r'^ar_', '', stem)
    n = re.sub(r'_\d{8}.*$', '', n)
    m = re.search(r'short_dance_(\w+)', n)
    if m:
        char = m.group(1)
        return char, THEME_FOR.get(char, "animals")
    return "", "animals"


def extract_color(stem: str) -> str:
    n = re.sub(r'^ar_', '', stem)
    n = re.sub(r'_\d{8}.*$', '', n)
    for pat in [r'colorlearn_(\w+)', r'short_color_(\w+?)(?:_\w+)?$', r'color_(\w+)_']:
        m = re.search(pat, n)
        if m:
            return m.group(1)
    return ""


def extract_shape(stem: str) -> str:
    n = re.sub(r'^ar_', '', stem)
    n = re.sub(r'_\d{8}.*$', '', n)
    for shape in SHAPES_AR_MAP:
        if shape in n:
            return shape
    return ""


def extract_float_mode(stem: str) -> str:
    for m in ["_tb", "_lr", "_diag", "_float"]:
        if m in stem:
            return m[1:]
    return "float"


def extract_theme_from_stem(stem: str) -> str:
    n = re.sub(r'^ar_', '', stem)
    if "animal" in n: return "animals"
    if "fruit" in n: return "fruits"
    if "vegetable" in n or "veg" in n: return "vegetables"
    if "shape" in n: return "shapes"
    return "animals"


def classify_video(stem: str, meta: dict) -> str:
    vtype = meta.get("video_type", "")
    n = re.sub(r'^ar_', '', re.sub(r'_\d{8}.*$', '', stem))
    if vtype == "short_dance" or re.search(r'short_dance_\w+', n): return "short_dance"
    if vtype == "dance" or n.startswith("dance_"): return "dance_long"
    if "colorlearn" in n or vtype == "short_colorlearn": return "colorlearn"
    if "vocab" in n or vtype == "short_vocab": return "vocab"
    if re.search(r'short_float_|ar_short_float_', stem): return "shape_float"
    if "sdance" in n or vtype == "short_shape_dance": return "shape_dance"
    if "shapes" in n: return "shape_pattern"
    if "counting" in n and "short" in n: return "counting_short"
    if "counting" in n: return "counting_long"
    if re.search(r'short_color_', n): return "color_theme"
    return "generic"


# ── Main enrichment ────────────────────────────────────────────────────────────

def build_description(stem: str, meta: dict, is_ar: bool) -> str:
    vclass = classify_video(stem, meta)
    title  = meta.get("title", "")

    if is_ar:
        # Arabic descriptions
        if vclass == "short_dance":
            char_en, theme = extract_character(stem)
            char_ar = ALL_AR.get(char_en, meta.get("customLabel", char_en))
            return desc_dance_short_ar(char_ar, char_en, theme)
        elif vclass == "dance_long":
            theme = meta.get("theme", extract_theme_from_stem(stem))
            return desc_dance_long_ar(theme)
        elif vclass == "colorlearn":
            color_en = extract_color(stem)
            color_ar = COLORS_AR_MAP.get(color_en, color_en)
            return desc_colorlearn_ar(color_ar, color_en)
        elif vclass == "shape_float":
            shape_en = extract_shape(stem)
            shape_ar = SHAPES_AR_MAP.get(shape_en, shape_en)
            return desc_shape_float_ar(shape_ar, shape_en)
        elif vclass in ("shape_dance", "shape_pattern"):
            # Extract shape names from title or stem
            shapes_found = [SHAPES_AR_MAP[s] for s in SHAPES_AR_MAP if s in stem]
            shapes_ar = " + ".join(shapes_found) if shapes_found else "الأشكال"
            return desc_shape_dance_ar(shapes_ar)
        elif vclass in ("counting_short", "counting_long"):
            return desc_counting_ar()
        else:
            # Fallback: use Arabic dance_long style
            return desc_dance_long_ar(meta.get("theme", "animals"))
    else:
        # English descriptions
        if vclass == "short_dance":
            char_en, theme = extract_character(stem)
            return desc_dance_short_en(char_en or "Bear", theme)
        elif vclass == "dance_long":
            theme = meta.get("theme", extract_theme_from_stem(stem))
            return desc_dance_long_en(theme)
        elif vclass == "colorlearn":
            color = extract_color(stem)
            return desc_colorlearn_en(color or "blue")
        elif vclass == "vocab":
            # Extract letter and word from title e.g. "A is for Apple"
            m = re.search(r'\b([A-Z])\b.*\b([A-Z][a-z]+)\b', title)
            letter = m.group(1) if m else "A"
            word   = m.group(2) if m else "Apple"
            return desc_vocab_en(letter, word)
        elif vclass == "shape_float":
            shape = extract_shape(stem)
            mode  = extract_float_mode(stem)
            return desc_shape_float_en(shape or "circle", mode)
        elif vclass in ("shape_dance", "shape_pattern"):
            shapes_found = [s.capitalize() for s in SHAPES_AR_MAP if s in stem]
            shapes_str = " + ".join(shapes_found) if shapes_found else "Shapes"
            return desc_shape_dance_en(shapes_str)
        elif vclass in ("counting_short", "counting_long"):
            return desc_counting_en()
        elif vclass == "color_theme":
            color = extract_color(stem)
            theme = meta.get("theme", extract_theme_from_stem(stem))
            return desc_color_theme_en(color or "red", theme)
        else:
            theme = meta.get("theme", "animals")
            return desc_dance_long_en(theme)


def process_queue(queue_dir: Path, dry_run: bool, label: str):
    meta_files = sorted(queue_dir.glob("meta_*.yaml"))
    if not meta_files:
        print(f"  No meta files in {queue_dir}")
        return

    updated = skipped = 0
    for mf in meta_files:
        with open(mf) as f:
            meta = yaml.safe_load(f) or {}

        stem    = mf.stem.replace("meta_", "")
        is_ar   = meta.get("language", "en") == "ar" or stem.startswith("ar_")
        new_desc = build_description(stem, meta, is_ar)

        old_desc = meta.get("description", "")
        if old_desc == new_desc and not dry_run:
            skipped += 1
            continue

        if dry_run:
            print(f"\n{'='*60}")
            print(f"FILE: {mf.name}")
            print(f"NEW DESC:\n{new_desc[:300]}...")
            updated += 1
            if updated >= 3:
                print("\n[showing first 3 only in dry-run]")
                break
            continue

        meta["description"] = new_desc
        with open(mf, "w") as f:
            yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
        updated += 1

    if not dry_run:
        print(f"  [{label}] Updated: {updated} | Skipped (unchanged): {skipped}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue",   choices=["en", "ar", "both"], default="both")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.dry_run:
        print("DRY RUN — showing sample output only\n")

    if args.queue in ("en", "both"):
        q = ROOT / "output" / "queue"
        print(f"\nProcessing English queue ({len(list(q.glob('meta_*.yaml')))} files)...")
        process_queue(q, args.dry_run, "EN")

    if args.queue in ("ar", "both"):
        q = ROOT / "output" / "queue_ar"
        print(f"\nProcessing Arabic queue ({len(list(q.glob('meta_*.yaml')))} files)...")
        process_queue(q, args.dry_run, "AR")


if __name__ == "__main__":
    main()
