"""
Indonesian (Bahasa Indonesia) translations and metadata for Happy Bear Kids channel.
Mirrors arabic_data.py — used by generate_dance_remotion.py and other generators.
"""

# ── Shapes ────────────────────────────────────────────────────────────────────
SHAPES_ID = {
    "circle":   "Lingkaran",
    "square":   "Kotak",
    "triangle": "Segitiga",
    "star":     "Bintang",
    "diamond":  "Belah Ketupat",
    "heart":    "Hati",
    "hexagon":  "Segi Enam",
    "oval":     "Oval",
}

# ── Colors ────────────────────────────────────────────────────────────────────
COLORS_ID = {
    "red":    {"name": "Merah",      "audio": None},
    "orange": {"name": "Oranye",     "audio": None},
    "yellow": {"name": "Kuning",     "audio": None},
    "green":  {"name": "Hijau",      "audio": None},
    "blue":   {"name": "Biru",       "audio": None},
    "purple": {"name": "Ungu",       "audio": None},
    "pink":   {"name": "Merah Muda", "audio": None},
}

COLOR_TAGLINES_ID = {
    "red":    "Dapatkah kamu menemukan sesuatu yang merah?",
    "orange": "Dapatkah kamu menemukan sesuatu yang oranye?",
    "yellow": "Dapatkah kamu menemukan sesuatu yang kuning?",
    "green":  "Dapatkah kamu menemukan sesuatu yang hijau?",
    "blue":   "Dapatkah kamu menemukan sesuatu yang biru?",
    "purple": "Dapatkah kamu menemukan sesuatu yang ungu?",
    "pink":   "Dapatkah kamu menemukan sesuatu yang merah muda?",
}

# ── Animals ───────────────────────────────────────────────────────────────────
ANIMALS_ID = {
    "bear":     "Beruang",
    "cat":      "Kucing",
    "cow":      "Sapi",
    "dino":     "Dinosaurus",
    "dog":      "Anjing",
    "duck":     "Bebek",
    "elephant": "Gajah",
    "fox":      "Rubah",
    "frog":     "Katak",
    "koala":    "Koala",
    "lion":     "Singa",
    "monkey":   "Monyet",
    "owl":      "Burung Hantu",
    "panda":    "Panda",
    "parrot":   "Burung Beo",
    "penguin":  "Penguin",
    "sheep":    "Domba",
    "camel":    "Unta",
    "rabbit":   "Kelinci",
    "tiger":    "Harimau",
    "unicorn":  "Unicorn",
}

# ── Fruits ────────────────────────────────────────────────────────────────────
FRUITS_ID = {
    "apple":      "Apel",
    "banana":     "Pisang",
    "cherry":     "Ceri",
    "grapes":     "Anggur",
    "lemon":      "Lemon",
    "melon":      "Melon",
    "orange":     "Jeruk",
    "peach":      "Persik",
    "pear":       "Pir",
    "pineapple":  "Nanas",
    "strawberry": "Stroberi",
    "watermelon": "Semangka",
}

# ── Vegetables ────────────────────────────────────────────────────────────────
VEGETABLES_ID = {
    "broccoli":  "Brokoli",
    "carrot":    "Wortel",
    "corn":      "Jagung",
    "cucumber":  "Timun",
    "eggplant":  "Terong",
    "mushroom":  "Jamur",
    "onion":     "Bawang",
    "pepper":    "Paprika",
    "potato":    "Kentang",
    "pumpkin":   "Labu",
    "tomato":    "Tomat",
}

# ── YouTube metadata templates ─────────────────────────────────────────────────

CHANNEL_NAME_ID = "Happy Bear Kids"


def dance_meta_id(subject_en: str, subject_id: str, theme: str) -> dict:
    """Indonesian metadata for dance videos (animals/fruits/vegetables)."""
    theme_id = {"animals": "hewan", "fruits": "buah", "vegetables": "sayuran"}.get(theme, theme)
    return {
        "title":       f"Tarian {subject_id} | Happy Bear Kids #shorts",
        "description": (
            f"Lihat {subject_id} menari! 🎵 "
            f"Video yang menyenangkan untuk balita dan anak-anak.\n"
            f"#{subject_id.replace(' ', '')} #tarian #anak #happybearkids #shorts"
        ),
        "tags": [
            subject_id.lower(), "tarian", "anak", "bayi",
            "happy bear kids", theme_id, "edukasi", "balita", "shorts",
        ],
        "video_type": "short_dance",
        "theme":      theme,
        "language":   "id",
        "is_short":   True,
        "status":     "public",
    }
