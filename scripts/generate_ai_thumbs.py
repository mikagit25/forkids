#!/usr/bin/env python3
"""
Generate AI thumbnails for queue videos using Gemini image generation.

Uses Gemini API (free tier, 1500 req/day) to generate high-quality
YouTube thumbnails (1280×720). Falls back to PIL generator if API fails.

Usage:
  python3 scripts/generate_ai_thumbs.py              # both queues, skip existing
  python3 scripts/generate_ai_thumbs.py --queue en
  python3 scripts/generate_ai_thumbs.py --queue ar
  python3 scripts/generate_ai_thumbs.py --force      # regenerate all
  python3 scripts/generate_ai_thumbs.py --dry-run    # show prompts only
  python3 scripts/generate_ai_thumbs.py --test bear  # test one character

API key: credentials/gemini_api_key.txt
Model:   gemini-2.0-flash-preview-image-generation (free tier)
"""
import argparse
import base64
import json
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

import yaml

ROOT      = Path(__file__).resolve().parent.parent
QUEUE     = ROOT / "output" / "queue"
QUEUE_AR  = ROOT / "output" / "queue_ar"
QUEUE_ID  = ROOT / "output" / "queue_id"
UPLOADED  = ROOT / "uploaded"
KEY_FILE        = ROOT / "credentials" / "gemini_api_key.txt"
TOGETHER_KEY_FILE = ROOT / "credentials" / "together_api_key.txt"

# Gemini (free 1500/day when billing enabled on account)
GEMINI_IMAGE_MODEL = "gemini-2.0-flash-preview-image-generation"
GEMINI_API_BASE    = "https://generativelanguage.googleapis.com/v1beta/models"

# Together.ai — FLUX.1-schnell, free $25 credit on signup, then ~$0.0003/image
TOGETHER_IMAGE_URL = "https://api.together.xyz/v1/images/generations"
TOGETHER_MODEL     = "black-forest-labs/FLUX.1-schnell"  # serverless, pay-per-use

# ── Prompt templates ──────────────────────────────────────────────────────────

# Character Arabic names for prompt context
AR_NAMES = {
    "bear": "دب", "tiger": "نمر", "frog": "ضفدع", "penguin": "بطريق",
    "lion": "أسد", "panda": "باندا", "koala": "كوالا", "fox": "ثعلب",
    "rabbit": "أرنب", "cow": "بقرة", "duck": "بطة", "pig": "خنزير",
    "elephant": "فيل", "monkey": "قرد", "dog": "كلب", "cat": "قطة",
    "owl": "بومة", "unicorn": "وحيد القرن", "dino": "ديناصور", "parrot": "ببغاء",
    "apple": "تفاحة", "banana": "موزة", "strawberry": "فراولة",
    "watermelon": "بطيخ", "orange": "برتقالة", "grapes": "عنب",
    "pineapple": "أناناس", "cherry": "كرز", "lemon": "ليمون",
    "carrot": "جزرة", "broccoli": "بروكلي", "corn": "ذرة", "tomato": "طماطم",
    "cucumber": "خيار", "pumpkin": "قرع", "mushroom": "فطر",
}

STYLE_EN = (
    "bright colorful children's illustration, Pixar-style 3D cartoon, "
    "bold clean composition, cheerful expression, kids YouTube thumbnail, "
    "16:9 format 1280x720, no watermarks, no logos, no brand names, no copyright symbols"
)

# AR channel: same style but absolutely no text — FLUX can't render Arabic (non-Latin)
STYLE_AR_NOTXT = (
    "bright colorful children's illustration, Pixar-style 3D cartoon, "
    "bold clean composition, cheerful expression, kids YouTube thumbnail, "
    "16:9 format 1280x720, no text, no letters, no words, no numbers, "
    "no watermarks, no logos, no brand names, no copyright symbols"
)

# ID channel: Indonesian uses Latin script → text allowed, same style as EN
# (STYLE_EN is reused for Indonesian)

# Objects shown per number (first object used as main thumbnail subject)
_NUM_OBJECTS = {
    "1": ("apple",      "one cute smiling apple"),
    "2": ("banana",     "two cute smiling bananas"),
    "3": ("apple",      "three cute smiling apples in a row"),
    "4": ("balloon",    "four colorful balloons with cute faces"),
    "5": ("orange",     "five cute smiling oranges"),
    "6": ("balloon",    "six colorful balloons floating upward"),
    "7": ("apple",      "seven cute smiling apples arranged in a cluster"),
    "8": ("orange",     "eight cute smiling oranges in two rows of four"),
    "9": ("apple",      "nine cute smiling apples arranged in three rows of three"),
    "10": ("balloon",   "ten colorful balloons clustered together"),
}


def make_prompt(stem: str, meta: dict, is_ar: bool = False) -> str:
    """Build an English image generation prompt from video metadata.

    Always English — FLUX/Gemini don't render Arabic text well.
    is_ar=True → adds 'no text, no letters' suffix to keep images clean.
    Indonesian (id) uses Latin script, so text is allowed — same style as EN.
    """
    vtype  = meta.get("video_type", "")
    style  = STYLE_AR_NOTXT if is_ar else STYLE_EN

    # Normalise stem: strip lang suffix and date
    name = re.sub(r'_(en|ar|id)$', '', re.sub(r'_\d{8}.*$', '', stem))
    name = re.sub(r'^(ar|id)_', '', name)

    # Infer theme from meta, fallback to filename
    if meta.get("theme"):
        theme = meta["theme"]
    elif "fruit" in name:
        theme = "fruits"
    elif "vegetable" in name or "veggie" in name:
        theme = "vegetables"
    elif "shape" in name:
        theme = "shapes"
    elif "mixed" in name:
        theme = "mixed"
    else:
        theme = "animals"

    # Detect specific character/object from filename
    character = ""
    for char in AR_NAMES:
        if char in name:
            character = char
            break

    # ── Calm Classics: sleep_program / focus_program / visual_theme ──────────
    if vtype in ("sleep_program", "focus_program", "visual_theme", "sleep_short"):
        _CC_THEME_PROMPTS = {
            "moon_clouds":  "peaceful moonlit night sky with soft drifting clouds, full moon glow, "
                            "classical music sleep relaxation, dark blue cinematic, no text",
            "night_bear":   "sleeping bear silhouette under moonlit night sky with fireflies, "
                            "classical lullaby, peaceful dark forest, cozy, no text",
            "warm_waves":   "calm ocean waves at dusk with warm amber golden sunset, "
                            "classical music relaxation, cinematic peaceful, no text",
            "rain_window":  "cozy rainy window with warm candlelight inside glowing, "
                            "classical music study focus atmosphere, no text",
        }
        cc_theme = meta.get("theme", "moon_clouds")
        base_prompt = _CC_THEME_PROMPTS.get(cc_theme, _CC_THEME_PROMPTS["moon_clouds"])
        dur_label = meta.get("duration_hours", "")
        dur_str = f", {dur_label} hour" if dur_label else ""
        return f"{base_prompt}, {meta.get('title', 'classical music')[:40]}{dur_str}, professional YouTube thumbnail{style}"

    # ── numbers / counting ────────────────────────────────────────────────────
    if "counting" in vtype or "counting" in name or vtype == "numbers" or "number_learn" in name:
        num_match = re.search(
            r'number_learn_(one|two|three|four|five|six|seven|eight|nine|ten)', name)
        digit_map = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
                     "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10"}
        if num_match:
            digit = digit_map[num_match.group(1)]
            obj_name, obj_desc = _NUM_OBJECTS.get(digit, ("apple", f"{digit} cute apples"))
            if is_ar:
                # No digit (FLUX can't render Arabic numerals cleanly)
                prompt = (
                    f"{obj_desc} with big round eyes and happy smiles, "
                    f"grouped together in a cheerful cluster, "
                    f"all faces clearly visible and unobstructed, "
                    f"bright warm gradient background, small colorful confetti around them, "
                    f"clean open composition, educational toddler video, {style}"
                )
            else:
                prompt = (
                    f"Giant bold bubble-letter number {digit} in vivid yellow with dark outline "
                    f"centered at the top of the image, "
                    f"{obj_desc} with big round eyes and happy smiles "
                    f"arranged in a neat row at the bottom, "
                    f"objects placed well below the number not overlapping it, "
                    f"all characters' faces clearly visible and unobstructed, "
                    f"bright cheerful background, small colorful confetti falling, "
                    f"clean composition with clear separation between number and objects, "
                    f"{style}"
                )
        else:
            if is_ar:
                prompt = (
                    f"Cute smiling cartoon apple and balloon characters in a cheerful group, "
                    f"all faces clearly visible, bright educational background, "
                    f"small confetti and sparkles, {style}"
                )
            else:
                prompt = (
                    f"Three giant bold bubble-letter numbers 1 2 3 in vivid colors at the top, "
                    f"cute smiling cartoon animals standing below them in a row, "
                    f"characters' faces unobstructed, bright cheerful background, "
                    f"small colorful confetti falling, {style}"
                )

    # ── colors ────────────────────────────────────────────────────────────────
    elif "color" in vtype or "color_learn" in name or "color" in name:
        color_match = re.search(
            r'(red|blue|green|yellow|orange|purple|pink|brown|white|black)', name)
        color = color_match.group(1) if color_match else "rainbow"
        if color == "rainbow":
            prompt = (
                f"Vibrant rainbow arc over a cheerful scene, cute cartoon bear character "
                f"standing below it with arms raised, colorful objects in every color, "
                f"bright saturated background, educational color learning for kids, {style}"
            )
        else:
            prompt = (
                f"Scene bathed in vivid {color} light, cute Pixar-style cartoon bear character "
                f"surrounded by large {color} objects like fruits and balloons, "
                f"bold {color} gradient background, character's face clearly visible, "
                f"educational color learning for toddlers, {style}"
            )

    # ── shapes ────────────────────────────────────────────────────────────────
    elif "shape" in vtype or "shape" in name or "float" in name:
        shape_match = re.search(
            r'(circle|square|triangle|star|heart|diamond|hexagon|oval|pentagon)', name)
        shape = shape_match.group(1) if shape_match else "circle"
        color_map = {
            "circle": "bright red", "square": "vivid blue", "triangle": "lime green",
            "star": "golden yellow", "heart": "hot pink", "diamond": "cyan",
            "hexagon": "deep purple", "oval": "orange", "pentagon": "teal",
        }
        shape_color = color_map.get(shape, "vivid")
        prompt = (
            f"Giant {shape_color} cartoon {shape} character with big cute eyes and wide happy smile "
            f"taking up most of the image, bold and eye-catching, "
            f"several smaller {shape} shapes with happy faces scattered in the background, "
            f"the main {shape}'s face is fully clear and unobstructed, "
            f"bright vivid background in contrasting color, educational shapes for kids, {style}"
        )

    # ── dance ─────────────────────────────────────────────────────────────────
    elif "dance" in vtype or "dance" in name:
        theme_en = {"animals": "animals", "fruits": "fruits",
                    "vegetables": "vegetables", "shapes": "geometric shapes",
                    "mixed": "cartoon characters"}.get(theme, "cartoon characters")
        if character:
            prompt = (
                f"Cute Pixar-style 3D {character} character in an energetic joyful dance pose, "
                f"arms raised, big smile, facing the viewer, "
                f"bright colorful background with musical notes and colorful confetti, "
                f"character face clearly visible and prominent, no shapes overlapping the face, "
                f"vibrant and eye-catching, {style}"
            )
        else:
            prompt = (
                f"Group of three cute Pixar-style 3D cartoon {theme_en} characters "
                f"dancing together joyfully, each with big smiles and raised arms, "
                f"all faces clearly visible and unobstructed, "
                f"colorful confetti and musical notes in the background, "
                f"bright vivid background, energetic and fun, {style}"
            )

    # ── character dialogue (Roundy the bear) ─────────────────────────────────
    elif vtype == "character_dialogue" or "character_dialogue" in name:
        topic_map = {
            "emotions":  ("happy bear showing emotions", "colorful emotion face icons around it"),
            "colors":    ("bear surrounded by colorful paint splashes", "rainbow colors everywhere"),
            "numbers":   ("bear pointing at floating numbers", "colorful number bubbles"),
            "animals":   ("bear surrounded by cute animal friends", "jungle scene"),
        }
        topic = next((k for k in topic_map if k in name), None)
        desc, detail = topic_map.get(topic, ("cute cartoon bear character talking to child",
                                             "speech bubble, friendly educational scene"))
        prompt = (
            f"Cute Pixar-style 3D bear character with big expressive eyes and warm smile, "
            f"{desc}, {detail}, "
            f"bear's face is the clear main focus of the image, "
            f"bright friendly background, engaging and inviting for toddlers, {style}"
        )

    # ── ABC / vocabulary shorts ───────────────────────────────────────────────
    elif vtype == "short_vocab" or "short_vocab" in name or "vocab" in name:
        letter_match = re.search(r'short_vocab_([a-z])', name)
        if letter_match:
            letter = letter_match.group(1).upper()
            prompt = (
                f"Giant bold bubble letter {letter} in vivid color taking up the left half, "
                f"cute cartoon object starting with {letter} on the right side with big eyes, "
                f"letter and object clearly separated, bright cheerful background, "
                f"ABC learning for toddlers, {style}"
            )
        else:
            prompt = (
                f"Colorful alphabet letters A B C in giant bubble style, "
                f"cute cartoon characters around them, bright educational background, {style}"
            )

    # ── Indonesian nursery songs ──────────────────────────────────────────────
    elif vtype == "nursery_id" or "nursery_id" in name or "balonku" in name or "cicak" in name \
            or "naik_kereta" in name or "pelangi" in name or "dua_mata" in name or "kebunku" in name:
        song_visuals = {
            "balonku":     "three colorful balloons with happy faces floating in blue sky, "
                           "cute cartoon bear holding balloon strings below",
            "cicak":       "cute cartoon gecko character with big eyes clinging to a wall, "
                           "bright tropical green leaves behind it",
            "naik_kereta": "cute cartoon steam train with smiling face, colorful carriages, "
                           "happy animal passengers waving from windows",
            "pelangi":     "beautiful vivid rainbow arching across blue sky, "
                           "cute cartoon animals standing under it with arms raised joyfully",
            "dua_mata":    "cute cartoon bear character pointing to its big round eyes with a smile, "
                           "simple bright background",
            "kebunku":     "colorful garden with giant sunflowers and flowers, "
                           "cute cartoon butterfly with big eyes landing on a flower",
        }
        song_key = next((k for k in song_visuals if k in name), None)
        visual = song_visuals.get(song_key,
                    "cute cartoon characters singing together, colorful musical notes floating around")
        prompt = f"{visual}, bright cheerful kids illustration, {style}"

    # ── Arabic nursery songs ───────────────────────────────────────────────────
    elif vtype == "nursery_ar" or "nursery_ar" in name or "batta_batta" in name \
            or "ya_matar" in name or "dajaja" in name:
        song_visuals = {
            "batta_batta": "cute Pixar-style cartoon duck with big eyes splashing happily in a pond, "
                           "water droplets sparkling around it",
            "ya_matar":    "cartoon rain clouds with smiling faces and bright rainbow, "
                           "colorful raindrops falling, happy animals dancing in the rain",
            "dajaja":      "cute cartoon mother hen with fluffy yellow baby chicks around her, "
                           "cheerful sunny farm background",
        }
        song_key = next((k for k in song_visuals if k in name), None)
        visual = song_visuals.get(song_key,
                    "cute cartoon animals in a cheerful singing pose, colorful musical notes")
        prompt = f"{visual}, bright cheerful kids illustration, {style}"

    # ── lullaby / sensory ─────────────────────────────────────────────────────
    elif vtype in ("sensory_loop", "lullaby_long") or "sensory" in name or "lullaby" in name:
        prompt = (
            f"Dreamy night sky with glowing crescent moon and soft twinkling stars, "
            f"gentle pastel clouds in purple and blue tones, "
            f"floating soft glowing orbs and sparkles, "
            f"peaceful and magical baby sleep atmosphere, "
            f"16:9 format 1280x720, no text, no letters, no words, no numbers, "
            f"no faces, no watermarks, no logos, no brand names"
        )

    # ── dancing shapes ────────────────────────────────────────────────────────
    elif vtype == "dance_shape" or "dance_shape" in name:
        prompt = (
            f"Four cute cartoon geometric shape characters — a circle, square, triangle, and star — "
            f"each with big eyes and wide smiles, dancing together in a joyful pose, "
            f"all faces clearly visible and unobstructed, "
            f"bright vivid pastel background with colorful confetti, {style}"
        )

    # ── stars and bubbles ─────────────────────────────────────────────────────
    elif vtype == "stars_bubbles" or "stars_bubble" in name:
        prompt = (
            f"Dozens of transparent soap bubbles floating in a magical glowing scene, "
            f"one giant bubble in the center reflecting rainbow light, "
            f"soft twinkling stars in the background, "
            f"sparkles and light trails, dreamy and mesmerizing for babies, "
            f"16:9 format 1280x720, no text, no letters, no words, no numbers, "
            f"no watermarks, no logos, no brand names"
        )

    # ── special mechanics (sm1-sm14) ──────────────────────────────────────────
    elif vtype == "special_mechanics" and re.match(r'^sm\d+', name):
        _SM_PROMPTS = {
            "sm7":  "cute cartoon rabbit, cat and dog playing peek-a-boo behind colorful trees, "
                    "surprised expressions, dark magical forest background, Pixar 3D style",
            "sm8":  "colorful bright 3D shapes casting dark dramatic shadows on the ground, "
                    "warm golden directional light, clean dark background, Pixar 3D style",
            "sm9":  "magical glowing transparent soap bubbles of all sizes floating upward, "
                    "iridescent rainbow reflections inside each bubble, deep dark blue background, Pixar 3D style",
            "sm10": "colorful geometric shapes — star, circle, diamond — each with a perfect mirror "
                    "reflection below it on a shiny surface, dark blue symmetric background, Pixar 3D style",
            "sm11": "ten colorful glowing circles arranged in two neat rows of five, "
                    "two large golden stars above them, counting visual, dark background, Pixar 3D style",
            "sm12": "festive birthday celebration scene with colorful balloons, rainbow confetti, "
                    "stars and sparkles, warm golden party background, Pixar 3D style",
            "sm13": "cute bear and cat character dancing joyfully with their perfect mirror reflections "
                    "below them on a shiny purple floor, purple sparkles background, Pixar 3D style",
            "sm14": "peaceful glowing crescent moon and seven soft twinkling stars in a deep dark blue "
                    "night sky, gentle sparkles, magical serene baby sleep atmosphere, Pixar 3D style",
        }
        sm_match = re.match(r'^(sm\d+)', name)
        sm_key = sm_match.group(1) if sm_match else ""
        visual = _SM_PROMPTS.get(sm_key,
            "magical colorful abstract visual effects, glowing geometric patterns, "
            "dreamy baby animation atmosphere, Pixar 3D style")
        prompt = f"{visual}, {style}"

    # ── emotions_ocean (eo_e_* emotions, eo_o_* ocean, eo_t_* transport, eo_p_* professions) ───
    elif vtype == "special_mechanics" and re.match(r'^eo_', name):
        _EMOTION_PROMPTS = {
            "happy":     "cute Pixar-style 3D bear character with the biggest joyful smile, "
                         "arms raised in celebration, golden sunlight and confetti background",
            "sad":       "cute Pixar-style 3D bear with big teary blue eyes, one small teardrop "
                         "falling on its cheek, soft blue-grey clouds background, gentle and sympathetic",
            "angry":     "cute Pixar-style 3D bear with a grumpy scowl and crossed arms, "
                         "wavy red and orange energy lines background, eyebrows furrowed",
            "surprised": "cute Pixar-style 3D bear with huge wide-open eyes and open mouth in shock, "
                         "yellow sparkle burst around it, comic surprise expression",
            "scared":    "cute Pixar-style 3D bear peeking nervously with big fearful eyes, "
                         "hiding behind a colorful pillow, dark cozy night background",
            "love":      "cute Pixar-style 3D bear with rosy cheeks and heart-shaped eyes, "
                         "surrounded by floating pink and red hearts, warm pink background",
            "calm":      "cute Pixar-style 3D bear in a peaceful relaxed pose with soft closed eyes, "
                         "gentle pastel blue background, floating soft glowing orbs",
            "excited":   "cute Pixar-style 3D bear jumping with pure excitement, confetti everywhere, "
                         "rainbow streaks background, big open smile",
        }
        _OCEAN_PROMPTS = {
            "octopus":   "cute Pixar-style 3D purple octopus character with big eyes and eight curly "
                         "tentacles, underwater bubble background, friendly smile",
            "whale":     "majestic cute Pixar-style 3D blue whale character with kind eyes, "
                         "deep ocean background, light rays from above, water bubbles",
            "dolphin":   "cute smiling Pixar-style 3D dolphin leaping from sparkling ocean waves, "
                         "sunny tropical background",
            "crab":      "cute Pixar-style 3D red crab character with big claws and happy expression, "
                         "sandy beach with colorful shells background",
            "seahorse":  "cute Pixar-style 3D seahorse with a curling tail and big eyes, "
                         "colorful coral reef background",
            "jellyfish": "beautiful glowing Pixar-style 3D jellyfish with trailing tentacles, "
                         "deep dark ocean, bioluminescent glow",
            "fish":      "cute Pixar-style 3D tropical fish with bright orange and white stripes "
                         "and a big friendly smile, coral reef background",
        }
        _TRANSPORT_PROMPTS = {
            "bus":       "cute Pixar-style 3D red bus with a friendly smiling face and big round eyes, "
                         "cheerful city street background",
            "train":     "cute Pixar-style 3D steam train with a smiling face and colorful carriages, "
                         "green countryside track background",
            "airplane":  "cute Pixar-style 3D white airplane with a joyful smile, fluffy clouds "
                         "and blue sky background, colorful wingtips",
            "car":       "cute Pixar-style 3D colorful car character with big headlight eyes and "
                         "wide grill smile, bright road background",
            "boat":      "cute Pixar-style 3D sailing boat with a happy face on its bow, "
                         "sparkling ocean waves and sunny sky background",
            "rocket":    "cute Pixar-style 3D rocket ship with a big smile, "
                         "launching through space with colorful stars and planets",
        }
        _PROFESSION_PROMPTS = {
            "doctor":    "cute Pixar-style 3D bear doctor character in white coat with stethoscope, "
                         "friendly smile, clean clinic background",
            "teacher":   "cute Pixar-style 3D bear teacher character holding a book, "
                         "colorful classroom with blackboard background",
            "chef":      "cute Pixar-style 3D bear chef character in a white hat, holding a big spoon, "
                         "colorful kitchen background",
            "firefighter": "cute Pixar-style 3D bear firefighter in red helmet and suit, "
                           "fire truck background, heroic pose",
            "police":    "cute Pixar-style 3D bear police character with a badge, "
                         "friendly city background",
            "farmer":    "cute Pixar-style 3D bear farmer with overalls and a straw hat, "
                         "sunny farm with colorful crops background",
        }
        # Extract category and subject: eo_e_happy → e/happy, eo_o_whale → o/whale
        eo_match = re.match(r'^eo_([eopt])_(.+)', name)
        if eo_match:
            cat, subject = eo_match.group(1), eo_match.group(2)
            if cat == "e":
                visual = _EMOTION_PROMPTS.get(subject,
                    f"cute Pixar-style 3D bear character showing {subject} emotion, expressive face, "
                    f"colorful emotional background")
            elif cat == "o":
                visual = _OCEAN_PROMPTS.get(subject,
                    f"cute Pixar-style 3D {subject} sea creature character with big eyes and smile, "
                    f"colorful underwater background")
            elif cat == "t":
                visual = _TRANSPORT_PROMPTS.get(subject,
                    f"cute Pixar-style 3D {subject} vehicle character with a friendly face, "
                    f"cheerful transportation background")
            elif cat == "p":
                visual = _PROFESSION_PROMPTS.get(subject,
                    f"cute Pixar-style 3D bear character dressed as a {subject}, "
                    f"relevant background for the profession")
            else:
                visual = "cute Pixar-style 3D bear character in an expressive educational scene"
        else:
            visual = "cute Pixar-style 3D character with big expressive eyes, colorful background"
        prompt = f"{visual}, {style}"

    # ── shadow puppet ─────────────────────────────────────────────────────────
    elif vtype == "special_mechanics" and name.startswith("shadow_"):
        subj_map = {
            "animals": "cute cartoon rabbit, cat, bear and elephant as shadow puppets on a warm glowing "
                       "screen, dramatic shadow silhouettes with soft backlight",
            "fruits":  "shadow puppet silhouettes of apple, banana, strawberry and orange on a warm "
                       "glowing amber screen, dramatic crisp shadows with colorful back-lighting",
            "mixed":   "whimsical mix of animal and fruit shadow puppets on a glowing backlit screen, "
                       "crisp dark silhouettes, colorful ambient glow around the edges",
        }
        subj = next((k for k in subj_map if k in name), "animals")
        no_txt = ", no text, no letters, no words, no numbers, no watermarks"
        prompt = (
            f"{subj_map[subj]}, magical theatrical shadow puppet show for children, "
            f"warm amber and golden backlight, dark vignette border, "
            f"16:9 format 1280x720{no_txt}"
        )

    # ── nature_calm / lullaby (nature backgrounds) ────────────────────────────
    elif vtype in ("nature_calm", "lullaby_long", "sensory_loop") \
            or any(k in name for k in ("nature_calm", "sensory", "lullaby")):
        _NATURE_PROMPTS = {
            "night":      "peaceful moonlit night sky with glowing crescent moon, soft twinkling "
                          "stars, gentle purple-blue gradient, calm and serene baby sleep atmosphere",
            "night_sky":  "beautiful starry night sky with glowing full moon, soft nebula colors in "
                          "deep blue and purple, magical peaceful baby sleep atmosphere",
            "meadow":     "beautiful sunlit meadow with wildflowers, soft clouds in blue sky, "
                          "butterflies, peaceful nature scene for babies",
            "sunset":     "warm golden sunset over rolling hills, orange and pink sky, gentle silhouette "
                          "of trees, peaceful romantic nature atmosphere",
            "underwater": "magical underwater world with soft blue-green light, colorful coral, "
                          "gentle fish and bubbles rising, dreamy ocean depth",
            "garden":     "moonlit garden with soft glowing flowers, fireflies, gentle night breeze, "
                          "magical and peaceful baby sleep nature scene",
            "forest":     "misty forest at dawn with sunlight filtering through tall trees, "
                          "dew on leaves, peaceful magical woodland atmosphere",
            "rain":       "gentle rain falling on a cozy window, soft drops on glass, "
                          "warm orange light from inside, peaceful rainy night mood",
            "train":      "cute cozy train traveling through a moonlit countryside at night, "
                          "glowing windows, stars above, peaceful baby lullaby atmosphere",
            "stars":      "deep night sky full of twinkling stars, glowing crescent moon, "
                          "soft purple and blue clouds, magical peaceful sleeping atmosphere",
            "ocean":      "calm moonlit ocean at night, silver reflection of moon on still water, "
                          "gentle waves, peaceful baby sleep atmosphere",
        }
        # Match scene from filename
        scene_key = next((k for k in _NATURE_PROMPTS if k in name), None)
        visual = _NATURE_PROMPTS.get(scene_key,
            "dreamy peaceful night sky with soft glowing moon and twinkling stars, "
            "gentle pastel clouds in purple and blue, magical baby sleep atmosphere")
        no_txt_suffix = ", no text, no letters, no words, no numbers, no faces, no watermarks"
        prompt = f"{visual}, soft dreamlike illustration style, 16:9 format 1280x720{no_txt_suffix}"

    # ── satisfying loop ───────────────────────────────────────────────────────
    elif vtype == "satisfying_loop" or "satisfying" in name:
        _SATISFYING_PROMPTS = {
            "rainbow":    "mesmerizing rainbow color wave flowing smoothly, satisfying gradient "
                          "ripple effect, vivid spectrum colors, abstract baby visual",
            "neon":       "glowing neon geometric shapes bouncing and pulsing in a dark background, "
                          "electric blue and pink neon trails, satisfying loop visual",
            "bubble":     "hundreds of colorful soap bubbles rising and popping, satisfying visual "
                          "pop effect, soft pastel background, mesmerizing for babies",
            "spiral":     "hypnotic colorful spiral pattern rotating smoothly, vivid colors, "
                          "satisfying infinite zoom effect, baby attention visual",
            "bounce":     "colorful geometric shapes bouncing perfectly off walls, "
                          "bright vivid colors on dark background, satisfying physics visual",
            "flow":       "smooth flowing colorful liquid waves, paint-like gradient flow, "
                          "mesmerizing and satisfying visual for babies",
        }
        subj = next((k for k in _SATISFYING_PROMPTS if k in name), None)
        visual = _SATISFYING_PROMPTS.get(subj,
            "mesmerizing colorful abstract shapes flowing and transforming smoothly, "
            "vibrant rainbow colors, satisfying visual loop for babies")
        no_txt_suffix = ", no text, no letters, no words, no numbers, no watermarks"
        prompt = f"{visual}, dreamy soft illustration style, 16:9 format 1280x720{no_txt_suffix}"

    # ── shapes_long / shape_learn ─────────────────────────────────────────────
    elif vtype in ("shapes_long", "shape_learn") or "shape_learn" in name:
        shape_match = re.search(
            r'(circle|square|triangle|star|heart|diamond|hexagon|oval|pentagon)', name)
        shape = shape_match.group(1) if shape_match else "circle"
        color_map = {
            "circle": "bright red", "square": "vivid blue", "triangle": "lime green",
            "star": "golden yellow", "heart": "hot pink", "diamond": "cyan",
            "hexagon": "deep purple", "oval": "orange", "pentagon": "teal",
        }
        shape_color = color_map.get(shape, "vivid rainbow")
        prompt = (
            f"Giant {shape_color} {shape} glowing softly in the center of the frame, "
            f"smaller {shape} shapes in the same color scattered elegantly around it, "
            f"deep dark background making the shapes pop with vibrant glow, "
            f"beautiful and hypnotic, educational shapes for babies, "
            f"no text, no letters, no words, no numbers, 16:9 1280x720"
        )

    # ── shape_roundelay / wiggle_party ────────────────────────────────────────
    elif vtype in ("shape_roundelay", "wiggle_party") or "roundelay" in name or "wiggle" in name:
        theme_en = {"animals": "animals", "fruits": "fruits",
                    "vegetables": "vegetables", "mixed": "cartoon characters"}.get(theme, "characters")
        prompt = (
            f"Group of five cute Pixar-style 3D cartoon {theme_en} characters "
            f"dancing in a joyful circle, all smiling with arms out, "
            f"vibrant colorful confetti and musical notes in the background, "
            f"bright festive background, energetic party atmosphere, {style}"
        )

    # ── nature_classical ──────────────────────────────────────────────────────
    elif vtype == "nature_classical" or "nature_classical" in name:
        _CLASSICAL_NATURE = {
            "meadow":     "sunlit meadow with wildflowers and butterflies, golden morning light, "
                          "peaceful pastoral scene, classical music atmosphere",
            "sunset":     "warm golden sunset over rolling hills, orange-pink sky, dramatic classical "
                          "music atmosphere, silhouettes of trees",
            "night":      "moonlit peaceful night landscape, full glowing moon reflected in still lake, "
                          "twinkling stars, romantic classical music atmosphere",
            "underwater": "moonlit lake with white swans gliding on still silver water, "
                          "magical mist rising, classical ballet atmosphere",
        }
        scene = next((k for k in _CLASSICAL_NATURE if k in name), "meadow")
        visual = _CLASSICAL_NATURE[scene]
        no_txt_suffix = ", no text, no letters, no words, no numbers, no watermarks" if is_ar else ""
        prompt = (
            f"{visual}, beautiful dreamlike illustration, 16:9 format 1280x720{no_txt_suffix}"
        )

    # ── bubble color series ───────────────────────────────────────────────────
    elif vtype == "stars_bubbles" and "bubbles_" in name:
        color_match = re.search(
            r'bubbles_(red|blue|green|yellow|orange|purple|pink|teal|rainbow|swirl|rain|drift)', name)
        bcolor = color_match.group(1) if color_match else "rainbow"
        color_desc = {
            "red": "deep ruby red", "blue": "electric blue", "green": "emerald green",
            "yellow": "golden yellow", "orange": "warm orange", "purple": "violet purple",
            "pink": "rose pink", "teal": "turquoise teal",
            "rainbow": "rainbow multicolored", "swirl": "swirling blue",
            "rain": "falling violet", "drift": "drifting rainbow",
        }.get(bcolor, "colorful")
        no_txt_suffix = ", no text, no letters, no words, no numbers, no watermarks"
        prompt = (
            f"Dozens of beautiful {color_desc} transparent bubbles floating in a magical dark space, "
            f"one giant {color_desc} bubble in the center glowing from within, "
            f"soft twinkling stars in background, sparkles and light trails, "
            f"dreamy mesmerizing for babies, 16:9 format 1280x720{no_txt_suffix}"
        )

    # ── generic fallback ──────────────────────────────────────────────────────
    else:
        if character:
            prompt = (
                f"Cute Pixar-style 3D {character} character with big eyes and happy smile, "
                f"face clearly visible and prominent, bright colorful background, "
                f"educational kids video, {style}"
            )
        else:
            prompt = (
                f"Three cute Pixar-style cartoon animal characters with big smiles "
                f"waving at the viewer, all faces clearly visible, "
                f"bright vivid colorful background, educational kids video, {style}"
            )

    return prompt


# ── Gemini API ────────────────────────────────────────────────────────────────

def load_key() -> str | None:
    if KEY_FILE.exists():
        return KEY_FILE.read_text().strip()
    return None


def load_together_key() -> str | None:
    if TOGETHER_KEY_FILE.exists():
        return TOGETHER_KEY_FILE.read_text().strip()
    return None


def together_generate_image(prompt: str, key: str) -> bytes | None:
    """Generate image via Together.ai FLUX.1-schnell."""
    try:
        import requests as _req
    except ImportError:
        print("    pip install requests  (needed for Together.ai)")
        return None
    try:
        r = _req.post(
            TOGETHER_IMAGE_URL,
            headers={"Authorization": f"Bearer {key}"},
            json={"model": TOGETHER_MODEL, "prompt": prompt,
                  "width": 1280, "height": 720, "steps": 4, "n": 1},
            timeout=90)
        if r.status_code != 200:
            try:
                msg = r.json().get("error", {}).get("message", r.text[:120])
            except Exception:
                msg = r.text[:120]
            print(f"    Together error {r.status_code}: {msg}")
            return None
        item = r.json()["data"][0]
        b64 = item.get("b64_json")
        if b64:
            return base64.b64decode(b64)
        url = item.get("url")
        if url:
            img_r = _req.get(url, timeout=30)
            if img_r.status_code == 200:
                return img_r.content
    except Exception as e:
        print(f"    Together request failed: {e}")
    return None


def gemini_generate_image(prompt: str, key: str,
                          retries: int = 3) -> bytes | None:
    """Call Gemini image generation. Returns raw PNG/JPEG bytes or None."""
    url = f"{GEMINI_API_BASE}/{GEMINI_IMAGE_MODEL}:generateContent?key={key}"
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]},
    }).encode()

    for attempt in range(retries):
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read())
                parts = data["candidates"][0]["content"]["parts"]
                for p in parts:
                    if "inlineData" in p:
                        return base64.b64decode(p["inlineData"]["data"])
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            err  = json.loads(body).get("error", {})
            code = err.get("code", e.code)
            msg  = err.get("message", "")

            if code == 429:  # rate limit — wait and retry
                wait = 2 ** attempt * 5
                print(f"    Rate limit, waiting {wait}s …")
                time.sleep(wait)
                continue
            elif code in (404, 400) and "not found" in msg.lower():
                print(f"    Model not available: {msg[:80]}")
                return None
            else:
                print(f"    API error {code}: {msg[:80]}")
                return None
        except Exception as e:
            print(f"    Request failed: {e}")
            if attempt < retries - 1:
                time.sleep(3)

    return None


def resize_to_720p(img_bytes: bytes) -> bytes:
    """Resize image to 1280×720 using PIL."""
    from PIL import Image
    import io
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    img = img.resize((1280, 720), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


# ── Queue processor ───────────────────────────────────────────────────────────

SHORT_PREFIXES = (
    "short_", "ar_short_",
)


def is_short(name: str) -> bool:
    return any(name.startswith(p) for p in SHORT_PREFIXES)


def process_queue(queue_dir: Path, key: str, force: bool,
                  dry_run: bool, label: str, backend: str = "gemini",
                  long_only: bool = True):
    mp4s = sorted([
        p for p in queue_dir.glob("*.mp4")
        if "test_" not in p.name and p.exists() and not p.is_symlink()
    ])
    if long_only:
        mp4s = [p for p in mp4s if not is_short(p.name)]
    if not mp4s:
        print(f"  [{label}] Queue empty")
        return

    ok = skip = err = api_fail = consec_fail = 0

    for i, mp4 in enumerate(mp4s):
        thumb_path = queue_dir / f"thumb_{mp4.stem}.png"
        if thumb_path.exists() and not force:
            skip += 1
            continue

        meta_path = queue_dir / f"meta_{mp4.stem}.yaml"
        meta = {}
        if meta_path.exists():
            with open(meta_path) as f:
                meta = yaml.safe_load(f) or {}

        lang   = meta.get("language", "en")
        is_ar  = lang == "ar" or mp4.name.startswith("ar_")
        # Indonesian uses Latin script → text allowed, same style as EN (is_ar=False)
        prompt = make_prompt(mp4.stem, meta, is_ar=is_ar)

        print(f"  [{label}] {i+1}/{len(mp4s)} {mp4.name}")
        print(f"    Prompt: {prompt[:100]}")

        if dry_run:
            ok += 1
            continue

        if backend == "together":
            img_bytes = together_generate_image(prompt, key)
        else:
            img_bytes = gemini_generate_image(prompt, key)
        if img_bytes:
            try:
                final = resize_to_720p(img_bytes)
                thumb_path.write_bytes(final)
                print(f"    ✓ saved {len(final)//1024}KB")
                ok += 1
                consec_fail = 0
            except Exception as e:
                print(f"    PIL resize error: {e}")
                err += 1
        else:
            api_fail += 1
            consec_fail += 1
            if consec_fail >= 5:
                wait = 60
                print(f"    5 consecutive failures — waiting {wait}s before retry …")
                time.sleep(wait)
                consec_fail = 0
            elif consec_fail >= 10:
                print(f"\n  API persistently unavailable — stopping.")
                break
            continue  # skip sleep on failure, retry sooner

        # Rate limit: ~10 RPM
        time.sleep(6)

    print(f"\n  [{label}] Done: {ok} generated, {skip} skipped, "
          f"{err} errors, {api_fail} API failures")


def main():
    parser = argparse.ArgumentParser(
        description="Generate AI thumbnails via Gemini or Together.ai")
    parser.add_argument("--queue",   choices=["en", "ar", "id", "all", "both", "none"], default="both")
    parser.add_argument("--force",   action="store_true")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show prompts without calling API")
    parser.add_argument("--test",    metavar="CHARACTER",
                        help="Test one character (e.g. --test bear)")
    parser.add_argument("--backend",  choices=["gemini", "together", "auto"],
                        default="auto", help="Force specific backend (default: auto)")
    parser.add_argument("--uploaded", action="store_true",
                        help="Also process uploaded/ directory (for already-published videos)")
    parser.add_argument("--shorts", action="store_true",
                        help="Process shorts (short_* files) instead of long videos")
    args = parser.parse_args()

    gemini_key   = load_key()
    together_key = load_together_key()

    if not gemini_key and not together_key:
        print("No API keys found. Add one of:")
        print(f"  Gemini (free):  {KEY_FILE}")
        print(f"  Together.ai:    {TOGETHER_KEY_FILE}")
        sys.exit(1)

    # Pick backend
    if args.backend == "together":
        if not together_key:
            print(f"Together.ai key not found: {TOGETHER_KEY_FILE}")
            sys.exit(1)
        key, backend = together_key, "together"
    elif args.backend == "gemini":
        if not gemini_key:
            print(f"Gemini key not found: {KEY_FILE}")
            sys.exit(1)
        key, backend = gemini_key, "gemini"
    else:
        # auto: prefer Gemini, fall back to Together
        key    = gemini_key or together_key
        backend = "gemini" if gemini_key else "together"
    print(f"Backend: {backend}  key: {key[:14]}…")

    if args.test:
        # Quick single test
        stem = f"short_dance_{args.test}_20260101"
        meta = {"video_type": "short_dance", "theme": "animals", "language": "en"}
        prompt = make_prompt(stem, meta, is_ar=False)
        print(f"Prompt: {prompt}")
        if not args.dry_run:
            if backend == "together":
                img = together_generate_image(prompt, key)
            else:
                img = gemini_generate_image(prompt, key)
            if img:
                out = ROOT / f"output/test_ai_thumb_{args.test}.png"
                out.write_bytes(resize_to_720p(img))
                print(f"Saved: {out}")
            else:
                print("Generation failed — model may need billing enabled")
        return

    long_only = not args.shorts

    if args.queue in ("en", "both", "all"):
        process_queue(QUEUE, key, args.force, args.dry_run, "EN", backend, long_only=long_only)

    if args.queue in ("ar", "both", "all"):
        process_queue(QUEUE_AR, key, args.force, args.dry_run, "AR", backend, long_only=long_only)

    if args.queue in ("id", "all"):
        process_queue(QUEUE_ID, key, args.force, args.dry_run, "ID", backend, long_only=long_only)

    if args.uploaded:
        process_queue(UPLOADED, key, args.force, args.dry_run, "UPLOADED", backend, long_only=long_only)


if __name__ == "__main__":
    main()
