"""
Arabic translations and metadata for Happy Bear Kids channel.
All text used in video rendering and YouTube metadata.
"""

# ── Shapes ────────────────────────────────────────────────────────────────────
SHAPES_AR = {
    "circle":   "دائرة",
    "square":   "مربع",
    "triangle": "مثلث",
    "star":     "نجمة",
    "diamond":  "معين",
    "heart":    "قلب",
    "hexagon":  "مسدس",
    "oval":     "بيضاوي",
}

# Arabic TTS audio for shapes (-15% speed, ar-SA-ZariyahNeural)
SHAPES_AUDIO_AR = {
    "circle":   "ar/ar_circle__dairah__this_is_a_circle.mp3",
    "square":   "ar/ar_square__murabba__this_is_a_square.mp3",
    "triangle": "ar/ar_triangle__muthalath__this_is_a_triangle.mp3",
    "star":     "ar/ar_star__najma__this_is_a_star.mp3",
    "diamond":  "ar/ar_diamond__muaayan__this_is_a_diamond.mp3",
    "heart":    "ar/ar_heart__qalb__this_is_a_heart.mp3",
    "hexagon":  "ar/ar_hexagon__musaddas__this_is_a_hexagon.mp3",
    "oval":     "ar/ar_oval__baydawi__this_is_an_oval.mp3",
}

# ── Colors ────────────────────────────────────────────────────────────────────
# audioFile paths are relative to remotion/public/audio/ (for Remotion)
# Arabic TTS generated at -15% speed via ar-SA-ZariyahNeural
COLORS_AR = {
    "red":    {"name": "أحمر",    "audio": "ar/ar_red__احمر__هل_يمكنك_ايجاد_شيء_احمر.mp3"},
    "orange": {"name": "برتقالي", "audio": "ar/ar_orange__برتقالي__هل_يمكنك_ايجاد_شيء_برتقالي.mp3"},
    "yellow": {"name": "أصفر",    "audio": "ar/ar_yellow__اصفر__هل_يمكنك_ايجاد_شيء_اصفر.mp3"},
    "green":  {"name": "أخضر",    "audio": "ar/ar_green__اخضر__هل_يمكنك_ايجاد_شيء_اخضر.mp3"},
    "blue":   {"name": "أزرق",    "audio": "ar/ar_blue__ازرق__هل_يمكنك_ايجاد_شيء_ازرق.mp3"},
    "purple": {"name": "بنفسجي",  "audio": "ar/ar_purple__بنفسجي__هل_يمكنك_ايجاد_شيء_بنفسجي.mp3"},
    "pink":   {"name": "وردي",    "audio": "ar/ar_pink__وردي__هل_يمكنك_ايجاد_شيء_وردي.mp3"},
}

# Color taglines shown in video (Arabic text + Arabic TTS audio above)
COLOR_TAGLINES_AR = {
    "red":    "هل يمكنك إيجاد شيء أحمر؟",
    "orange": "هل يمكنك إيجاد شيء برتقالي؟",
    "yellow": "هل يمكنك إيجاد شيء أصفر؟",
    "green":  "هل يمكنك إيجاد شيء أخضر؟",
    "blue":   "هل يمكنك إيجاد شيء أزرق؟",
    "purple": "هل يمكنك إيجاد شيء بنفسجي؟",
    "pink":   "هل يمكنك إيجاد شيء وردي؟",
}

# ── Animals ───────────────────────────────────────────────────────────────────
ANIMALS_AR = {
    "bear":     "دب",
    "cat":      "قطة",
    "cow":      "بقرة",
    "dino":     "ديناصور",
    "dog":      "كلب",
    "duck":     "بطة",
    "elephant": "فيل",
    "fox":      "ثعلب",
    "frog":     "ضفدع",
    "koala":    "كوالا",
    "lion":     "أسد",
    "monkey":   "قرد",
    "owl":      "بومة",
    "panda":    "باندا",
    "parrot":   "ببغاء",
    "penguin":  "بطريق",
    "sheep":    "خروف",
    "camel":    "جمل",
    "rabbit":   "أرنب",
    "tiger":    "نمر",
    "unicorn":  "وحيد القرن",
}

# ── Fruits ────────────────────────────────────────────────────────────────────
FRUITS_AR = {
    "apple":      "تفاحة",
    "banana":     "موزة",
    "cherry":     "كرز",
    "grapes":     "عنب",
    "lemon":      "ليمون",
    "melon":      "شمام",
    "orange":     "برتقالة",
    "peach":      "خوخ",
    "pear":       "إجاصة",
    "pineapple":  "أناناس",
    "strawberry": "فراولة",
    "watermelon": "بطيخ",
}

# ── Vegetables ────────────────────────────────────────────────────────────────
VEGETABLES_AR = {
    "broccoli":  "بروكلي",
    "carrot":    "جزرة",
    "corn":      "ذرة",
    "cucumber":  "خيار",
    "eggplant":  "باذنجان",
    "mushroom":  "فطر",
    "onion":     "بصلة",
    "pepper":    "فلفل",
    "potato":    "بطاطا",
    "tomato":    "طماطم",
}

# ── YouTube metadata templates ─────────────────────────────────────────────────

CHANNEL_NAME_AR = "هابي بير كيدز"

def dance_meta_ar(subject_en: str, subject_ar: str, theme: str) -> dict:
    """Arabic metadata for dance videos (animals/fruits/vegetables)."""
    theme_ar = {"animals": "الحيوانات", "fruits": "الفواكه",
                "vegetables": "الخضروات"}.get(theme, theme)
    return {
        "title":       f"رقص {subject_ar} | تعلم مع {CHANNEL_NAME_AR} | أغاني أطفال",
        "description": (
            f"شاهد {subject_ar} يرقص ويتحرك! 🎵\n"
            f"فيديو ممتع ومسلي للأطفال الصغار مع {CHANNEL_NAME_AR}.\n"
            f"تعلم أسماء {theme_ar} باللغة العربية من خلال الرقص والموسيقى.\n\n"
            f"#أطفال #تعليم #رقص #{subject_ar} #{theme_ar}"
        ),
        "tags": [
            "أطفال", "تعليم", "رقص", "موسيقى أطفال", subject_ar, theme_ar,
            "هابي بير كيدز", "فيديو أطفال", "تعلم معي", "أغاني أطفال",
        ],
        "language":    "ar",
        "status":      "public",
    }

def counting_meta_ar(theme: str) -> dict:
    theme_map = {
        "rainbow": "قوس قزح", "pastel": "ألوان باستيل", "warm": "دافئة",
        "neon": "نيون", "candy": "حلوى", "ocean": "المحيط",
        "cool": "باردة", "sunset": "الغروب",
    }
    theme_ar = theme_map.get(theme, theme)
    return {
        "title":       f"تعلم العد من 1 إلى 10 | أشكال {theme_ar} | {CHANNEL_NAME_AR}",
        "description": (
            f"تعلم كيف تعد من 1 إلى 10 مع أشكال جميلة بألوان {theme_ar}! 🔢\n"
            f"فيديو تعليمي ممتع للأطفال الصغار.\n\n"
            f"#تعليم #عد #أطفال #رياضيات #هابي_بير_كيدز"
        ),
        "tags": [
            "تعلم العد", "أرقام للأطفال", "عد", "رياضيات أطفال", theme_ar,
            "هابي بير كيدز", "تعليم أطفال", "أشكال هندسية",
        ],
        "language": "ar",
        "status":   "public",
    }

def shapes_dance_meta_ar(theme: str) -> dict:
    theme_map = {
        "rainbow": "قوس قزح", "pastel": "باستيل", "warm": "دافئة",
        "neon": "نيون", "cool": "باردة",
    }
    theme_ar = theme_map.get(theme, theme)
    return {
        "title":       f"رقص الأشكال | ألوان {theme_ar} | {CHANNEL_NAME_AR}",
        "description": (
            f"شاهد الأشكال الهندسية ترقص بألوان {theme_ar} الجميلة! ⭐\n"
            f"تعلم الأشكال: دائرة، مربع، مثلث، نجمة وأكثر!\n\n"
            f"#أشكال #رقص #أطفال #تعليم #هابي_بير_كيدز"
        ),
        "tags": [
            "أشكال هندسية", "رقص أشكال", "تعلم الأشكال", theme_ar,
            "دائرة مربع مثلث", "هابي بير كيدز", "تعليم أطفال",
        ],
        "language": "ar",
        "status":   "public",
    }

def short_dance_meta_ar(subject_en: str, subject_ar: str) -> dict:
    return {
        "title":       f"رقص {subject_ar} | {CHANNEL_NAME_AR} #shorts",
        "description": (
            f"شاهد {subject_ar} يرقص! 🎵 فيديو قصير ومسلٍّ للأطفال.\n"
            f"#{subject_ar} #رقص #أطفال #هابي_بير_كيدز #shorts"
        ),
        "tags": [
            subject_ar, "رقص", "أطفال", "فيديو قصير", "هابي بير كيدز",
            "تعليم", "مسلٍّ", "shorts",
        ],
        "language":    "ar",
        "is_short":    True,
        "status":      "public",
    }

def short_color_meta_ar(color_en: str, color_ar: str) -> dict:
    return {
        "title":       f"لون {color_ar} | تعلم الألوان | {CHANNEL_NAME_AR} #shorts",
        "description": (
            f"هيا نتعلم لون {color_ar} معاً! 🎨\n"
            f"فيديو تعليمي قصير للأطفال الصغار.\n"
            f"#{color_ar} #ألوان #أطفال #تعليم #shorts"
        ),
        "tags": [
            color_ar, "ألوان", "تعلم الألوان", "أطفال", "تعليم",
            "هابي بير كيدز", "shorts",
        ],
        "language": "ar",
        "is_short": True,
        "status":   "public",
    }

def short_shape_meta_ar(shape_en: str, shape_ar: str) -> dict:
    return {
        "title":       f"شكل {shape_ar} | تعلم الأشكال | {CHANNEL_NAME_AR} #shorts",
        "description": (
            f"هيا نتعرف على شكل {shape_ar}! ⭐\n"
            f"فيديو تعليمي قصير للأطفال.\n"
            f"#{shape_ar} #أشكال #أطفال #تعليم #shorts"
        ),
        "tags": [
            shape_ar, "أشكال هندسية", "تعلم الأشكال", "أطفال", "تعليم",
            "هابي بير كيدز", "shorts",
        ],
        "language": "ar",
        "is_short": True,
        "status":   "public",
    }
