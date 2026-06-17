#!/usr/bin/env python3
"""
Generate Emotions + Ocean + Transport + Professions series.
Scenario: config/scenarios/emotions_ocean_emotions_4series.txt

Series 3 — Emotions (6 emotions × A+B = 12 videos)
Series 4 — Ocean creatures (8 creatures × A+B = 16 videos)
Series 5 — Transport (6 vehicles × A+B = 12 videos)
Series 6 — Professions (8 professions × A+B = 16 videos)
Total: 56 videos

A = no words → EN+AR+ID queues
B = educational EN+AR → EN+AR queues

Usage:
  python3 scripts/generate_emotions_ocean.py --key emotions_4series  # all 56 videos
  python3 scripts/generate_emotions_ocean.py --series emotions        # series 3 only
  python3 scripts/generate_emotions_ocean.py --item happy             # single item (A+B)
  python3 scripts/generate_emotions_ocean.py --dry-run
"""
import argparse, json, shutil, subprocess, yaml
from datetime import datetime
from pathlib import Path

ROOT     = Path(__file__).resolve().parent.parent
REMOTION = ROOT / "remotion"
QUEUE_EN = ROOT / "output" / "queue"
QUEUE_AR = ROOT / "output" / "queue_ar"
QUEUE_ID = ROOT / "output" / "queue_id"
DATE_STR = datetime.now().strftime("%Y%m%d")

# Series 3 — Emotions
EMOTIONS = {
    "happy":     {"name_en": "Happy",     "name_ar": "سعيد",          "name_id": "Bahagia",    "bg": "#0A0A05", "accent": "#FFD700", "bpm": 88, "music": "Happy Happy Game Show.mp3"},
    "sad":       {"name_en": "Sad",       "name_ar": "حزين",          "name_id": "Sedih",      "bg": "#050A14", "accent": "#90CAF9", "bpm": 58, "music": "Gymnopedie No 1.mp3"},
    "surprised": {"name_en": "Surprised", "name_ar": "مندهش",         "name_id": "Terkejut",   "bg": "#080510", "accent": "#FF6B35", "bpm": 80, "music": "Quirky Dog.mp3"},
    "angry":     {"name_en": "Angry",     "name_ar": "غاضب",          "name_id": "Marah",      "bg": "#140505", "accent": "#FF4444", "bpm": 90, "music": "Pinball Spring.mp3"},
    "scared":    {"name_en": "Scared",    "name_ar": "خائف",          "name_id": "Takut",      "bg": "#050510", "accent": "#7E57C2", "bpm": 70, "music": "Crinoline Dreams.mp3"},
    "love":      {"name_en": "Love",      "name_ar": "حب",            "name_id": "Cinta",      "bg": "#140508", "accent": "#F48FB1", "bpm": 65, "music": "Heartwarming.mp3"},
}

# Series 4 — Ocean
OCEAN = {
    "whale":     {"name_en": "Whale",       "name_ar": "حوت",           "name_id": "Paus",           "bg": "#020A1A", "accent": "#4FC3F7", "bpm": 50, "music": "Gymnopedie No 1.mp3"},
    "octopus":   {"name_en": "Octopus",     "name_ar": "أخطبوط",       "name_id": "Gurita",         "bg": "#08020F", "accent": "#AB47BC", "bpm": 68, "music": "Quirky Dog.mp3"},
    "dolphin":   {"name_en": "Dolphin",     "name_ar": "دلفين",         "name_id": "Lumba-lumba",    "bg": "#021218", "accent": "#00BCD4", "bpm": 85, "music": "Pinball Spring.mp3"},
    "jellyfish": {"name_en": "Jellyfish",   "name_ar": "قنديل البحر",  "name_id": "Ubur-ubur",      "bg": "#020212", "accent": "#E040FB", "bpm": 48, "music": "Crinoline Dreams.mp3"},
    "reef":      {"name_en": "Coral Reef",  "name_ar": "الشعاب المرجانية", "name_id": "Terumbu Karang", "bg": "#010810", "accent": "#26A69A", "bpm": 55, "music": "Carefree.mp3"},
    "starfish":  {"name_en": "Starfish",    "name_ar": "نجمة البحر",   "name_id": "Bintang Laut",   "bg": "#080208", "accent": "#FF8F00", "bpm": 40, "music": "Heartwarming.mp3"},
    "crab":      {"name_en": "Crab",        "name_ar": "سرطان البحر",  "name_id": "Kepiting",       "bg": "#120408", "accent": "#EF5350", "bpm": 75, "music": "Merry Go.mp3"},
    "seahorse":  {"name_en": "Seahorse",    "name_ar": "فرس البحر",    "name_id": "Kuda Laut",      "bg": "#050A10", "accent": "#66BB6A", "bpm": 60, "music": "Wholesome.mp3"},
}

# Series 5 — Transport
TRANSPORT = {
    "airplane":  {"name_en": "Airplane",        "name_ar": "طائرة",              "name_id": "Pesawat",      "bg": "#050810", "accent": "#64B5F6", "bpm": 82, "music": "Hyperfun.mp3"},
    "helicopter":{"name_en": "Helicopter",      "name_ar": "طائرة مروحية",      "name_id": "Helikopter",   "bg": "#080A10", "accent": "#4CAF50", "bpm": 88, "music": "Monkeys Spinning Monkeys.mp3"},
    "ship":      {"name_en": "Ship",            "name_ar": "سفينة",              "name_id": "Kapal",        "bg": "#020610", "accent": "#1E88E5", "bpm": 55, "music": "Life of Riley.mp3"},
    "boat":      {"name_en": "Boat",            "name_ar": "قارب",               "name_id": "Perahu",       "bg": "#030A0A", "accent": "#26C6DA", "bpm": 65, "music": "Carefree.mp3"},
    "rocket":    {"name_en": "Rocket",          "name_ar": "صاروخ",              "name_id": "Roket",        "bg": "#010108", "accent": "#FF7043", "bpm": 100, "music": "Hyperfun.mp3"},
    "balloon":   {"name_en": "Hot Air Balloon", "name_ar": "بالون هوائي ساخن",  "name_id": "Balon Udara",  "bg": "#030808", "accent": "#FFEE58", "bpm": 50, "music": "Wholesome.mp3"},
}

# Series 6 — Professions
PROFESSIONS = {
    "chef":         {"name_en": "Chef",         "name_ar": "طباخ",       "name_id": "Koki",         "bg": "#0A0808", "accent": "#FF8C42", "bpm": 80, "music": "Happy Happy Game Show.mp3"},
    "doctor":       {"name_en": "Doctor",       "name_ar": "طبيب",       "name_id": "Dokter",       "bg": "#050A0F", "accent": "#4FC3F7", "bpm": 65, "music": "Carefree.mp3"},
    "builder":      {"name_en": "Builder",      "name_ar": "بنّاء",     "name_id": "Tukang Bangunan","bg": "#0A0805", "accent": "#FFC107", "bpm": 88, "music": "Monkeys Spinning Monkeys.mp3"},
    "teacher":      {"name_en": "Teacher",      "name_ar": "معلم",       "name_id": "Guru",         "bg": "#050A05", "accent": "#66BB6A", "bpm": 70, "music": "Wholesome.mp3"},
    "firefighter":  {"name_en": "Firefighter",  "name_ar": "إطفائي",    "name_id": "Pemadam Kebakaran","bg": "#120508","accent": "#EF5350","bpm": 95, "music": "Quirky Dog.mp3"},
    "farmer":       {"name_en": "Farmer",       "name_ar": "مزارع",      "name_id": "Petani",       "bg": "#050A03", "accent": "#8BC34A", "bpm": 72, "music": "Merry Go.mp3"},
    "pilot":        {"name_en": "Pilot",        "name_ar": "طيار",       "name_id": "Pilot",        "bg": "#030810", "accent": "#42A5F5", "bpm": 85, "music": "Pinball Spring.mp3"},
    "artist":       {"name_en": "Artist",       "name_ar": "فنان",       "name_id": "Seniman",      "bg": "#0A050F", "accent": "#CE93D8", "bpm": 68, "music": "Heartwarming.mp3"},
}

ALL_SERIES = {
    "emotions":    EMOTIONS,
    "ocean":       OCEAN,
    "transport":   TRANSPORT,
    "professions": PROFESSIONS,
}

SERIES_NAMES = {
    "emotions":    {"en": "Emotions", "ar": "المشاعر", "id": "Emosi"},
    "ocean":       {"en": "Ocean",    "ar": "المحيط",  "id": "Lautan"},
    "transport":   {"en": "Transport","ar": "المواصلات","id": "Transportasi"},
    "professions": {"en": "Professions","ar": "المهن", "id": "Profesi"},
}


def make_meta_a(series, item_key, lang):
    item    = ALL_SERIES[series][item_key]
    ch      = {'en': '@HappyBearKids1', 'ar': '@happybearkidsar', 'id': '@happybearkidsin'}
    name    = item[f'name_{lang}']
    ser_name = SERIES_NAMES[series][lang]

    if lang == 'en':
        return {
            "title": f"{name} | 25 Min Baby Animation | Happy Bear Kids",
            "description": (
                f"✨ {name} — pure visual animation for babies and toddlers!\n\n"
                f"Part of our '{ser_name}' series — beautiful animation with no words, no text, "
                f"just mesmerizing visuals set to gentle music.\n\n"
                f"Perfect for: visual stimulation, background play, calming screen time.\n"
                f"No language barriers — universal content for any culture.\n\n"
                f"👶 Age: 0–3 years | 📺 25 minutes continuous animation\n\n"
                f"🔔 Subscribe → {ch['en']}\n"
                f"🎵 Kevin MacLeod (incompetech.com) — CC Attribution 4.0\n\n"
                f"#{name.replace(' ','')} #HappyBearKids #BabyAnimation "
                f"#VisualStimulation #NoTalking\n© Happy Bear Kids 2026"
            ),
            "tags": [item_key, name.lower(), ser_name.lower(), "baby animation", "happy bear kids",
                     "no talking", "visual stimulation", "calm baby", "25 minutes"],
            "video_type": "emotions_ocean", "language": "en", "is_short": False, "status": "public",
        }
    elif lang == 'ar':
        return {
            "title": f"{name} | رسوم متحركة للرضع 25 دقيقة | هابي بير كيدز",
            "description": (
                f"✨ {name} — رسوم متحركة بصرية خالصة للرضع والأطفال الصغار!\n\n"
                f"جزء من سلسلة '{ser_name}' — رسوم جميلة بدون كلمات أو نصوص، "
                f"مع موسيقى هادئة ومريحة.\n\n"
                f"مثالي للتحفيز البصري والتشغيل في الخلفية ووقت الشاشة الهادئ.\n"
                f"بدون حواجز لغوية — محتوى عالمي لجميع الثقافات.\n\n"
                f"🔔 اشتركوا → {ch['ar']}\n"
                f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
                f"#{name.replace(' ','_')} #هابي_بير_كيدز #رسوم_أطفال "
                f"#تحفيز_بصري\n© هابي بير كيدز 2026"
            ),
            "tags": [item_key, name, ser_name, "هابي بير كيدز", "رسوم مجردة", "بدون كلام"],
            "video_type": "emotions_ocean", "language": "ar", "is_short": False, "status": "public",
        }
    else:
        return {
            "title": f"{name} | 25 Menit Animasi Bayi | Happy Bear Kids",
            "description": (
                f"✨ {name} — animasi visual murni untuk bayi dan balita!\n\n"
                f"Bagian dari seri '{ser_name}' — animasi indah tanpa kata-kata atau teks, "
                f"dengan musik lembut yang menenangkan.\n\n"
                f"Sempurna untuk: stimulasi visual, hiburan latar belakang, waktu layar yang tenang.\n"
                f"Tanpa hambatan bahasa — konten universal untuk semua budaya.\n\n"
                f"🔔 Subscribe → {ch['id']}\n"
                f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
                f"#{name.replace(' ','')} #HappyBearKids #AnimasiAnak "
                f"#StimulasiVisual\n© Happy Bear Kids Indonesia 2026"
            ),
            "tags": [item_key, name.lower(), ser_name.lower(), "animasi bayi", "happy bear kids",
                     "tanpa suara", "stimulasi visual"],
            "video_type": "emotions_ocean", "language": "id", "is_short": False, "status": "public",
        }


def make_meta_b(series, item_key, lang):
    item    = ALL_SERIES[series][item_key]
    ch      = {'en': '@HappyBearKids1', 'ar': '@happybearkidsar', 'id': '@happybearkidsin'}
    name_en = item['name_en']
    name_ar = item['name_ar']
    name_id = item['name_id']
    name    = item[f'name_{lang}']
    ser_name = SERIES_NAMES[series][lang]

    if lang == 'en':
        return {
            "title": f"Learn: {name_en}! Educational Baby Video | Happy Bear Kids",
            "description": (
                f"🎓 Learn about {name_en}! Educational video for babies 0-3 years.\n\n"
                f"Part of our '{ser_name}' series — featuring Roundy the circle character "
                f"with expressive animations.\n\n"
                f"In this educational video:\n"
                f"• Learn the word '{name_en}' in English, Arabic ({name_ar}), and Indonesian ({name_id})\n"
                f"• Interactive pauses for baby response time\n"
                f"• Simple dialogue repeated for language learning\n"
                f"• Gentle music and colorful visuals\n\n"
                f"Perfect for: language learning, cognitive development, multicultural families.\n\n"
                f"👶 Age: 0–3 years | 📺 25 minutes\n\n"
                f"🔔 Subscribe → {ch['en']}\n"
                f"🎵 Kevin MacLeod (incompetech.com) — CC Attribution 4.0\n\n"
                f"#Learn{name_en.replace(' ','')} #HappyBearKids #BilingualBaby "
                f"#BabyEducation #LearnEnglish\n© Happy Bear Kids 2026"
            ),
            "tags": [item_key, f"learn {name_en.lower()}", "bilingual baby", "educational",
                     "baby learning", "happy bear kids", "english arabic", ser_name.lower()],
            "video_type": "emotions_ocean", "language": "en", "is_short": False, "status": "public",
        }
    elif lang == 'ar':
        return {
            "title": f"تعلم: {name_ar}! فيديو تعليمي للرضع | هابي بير كيدز",
            "description": (
                f"🎓 تعلم عن {name_ar}! فيديو تعليمي للرضع من 0-3 سنوات.\n\n"
                f"جزء من سلسلة '{ser_name}' — يضم شخصية كروكي الدائرة مع رسوم تعبيرية جميلة.\n\n"
                f"في هذا الفيديو التعليمي:\n"
                f"• تعلم كلمة '{name_ar}' بالعربية والإنجليزية ({name_en})\n"
                f"• توقفات تفاعلية لوقت استجابة الطفل\n"
                f"• حوار بسيط مكرر لتعلم اللغة\n"
                f"• موسيقى هادئة ورسوم ملونة\n\n"
                f"🔔 اشتركوا → {ch['ar']}\n"
                f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
                f"#تعلم_{name_ar.replace(' ','_')} #هابي_بير_كيدز #تعليم_الرضع "
                f"#ثنائي_اللغة\n© هابي بير كيدز 2026"
            ),
            "tags": [item_key, name_ar, "تعليم الرضع", "هابي بير كيدز", "ثنائي اللغة"],
            "video_type": "emotions_ocean", "language": "ar", "is_short": False, "status": "public",
        }
    else:  # id
        return {
            "title": f"Belajar: {name_id}! Video Edukasi Bayi | Happy Bear Kids",
            "description": (
                f"🎓 Belajar tentang {name_id}! Video edukasi untuk bayi 0-3 tahun.\n\n"
                f"Bagian dari seri '{ser_name}' — menampilkan karakter Roundy si lingkaran "
                f"dengan animasi ekspresif yang menarik.\n\n"
                f"Dalam video edukasi ini:\n"
                f"• Belajar kata '{name_id}' dalam Bahasa Indonesia, Inggris ({name_en}), dan Arab ({name_ar})\n"
                f"• Jeda interaktif untuk waktu respons bayi\n"
                f"• Dialog sederhana yang diulang untuk pembelajaran bahasa\n"
                f"• Musik lembut dan visual berwarna-warni\n\n"
                f"Sempurna untuk: pembelajaran bahasa, perkembangan kognitif, pendidikan multikultural.\n\n"
                f"👶 Usia: 0–3 tahun | 📺 25 menit\n\n"
                f"🔔 Subscribe → {ch['id']}\n"
                f"🎵 Kevin MacLeod (incompetech.com) — CC Attribution 4.0\n\n"
                f"#Belajar{name_id.replace(' ','')} #HappyBearKids #BayiPintar "
                f"#PendidikanBayi #BelajarIndonesia\n© Happy Bear Kids Indonesia 2026"
            ),
            "tags": [item_key, f"belajar {name_id.lower()}", "bayi pintar", "pendidikan bayi",
                     "happy bear kids", "bahasa indonesia", ser_name.lower()],
            "video_type": "emotions_ocean", "language": "id", "is_short": False, "status": "public",
        }


def process_item_a(series, item_key, dry_run, regen_meta):
    """No-words version → all 3 queues."""
    item   = ALL_SERIES[series][item_key]
    queues = {'en': QUEUE_EN, 'ar': QUEUE_AR, 'id': QUEUE_ID}
    props  = {
        "shapes": ["circle", "star", "square"],
        "colors": [item["accent"], "#FFFFFF", item["accent"]],
        "bgColor": item["bg"], "bpm": item["bpm"],
        "showLabels": False, "musicFile": item["music"],
    }
    out_mp4 = QUEUE_EN / f"eo_{series}_{item_key}_a_{DATE_STR}.mp4"

    if not out_mp4.exists() and not dry_run and not regen_meta:
        cmd = ["npx", "remotion", "render", "ShapeDanceLong",
               f"--props={json.dumps(props)}", f"--output={str(out_mp4)}"]
        print(f"  Render A: {out_mp4.name}")
        r = subprocess.run(cmd, cwd=str(REMOTION), timeout=21600)
        if r.returncode != 0:
            print("  FAILED")
            return False

    if out_mp4.exists() and not dry_run:
        for lg in ['ar', 'id']:
            dest = queues[lg] / out_mp4.name
            if not dest.exists():
                shutil.copy2(str(out_mp4), str(dest))

    for lg, q in queues.items():
        mp = q / f"meta_{out_mp4.stem}.yaml"
        if not mp.exists() or regen_meta:
            meta = make_meta_a(series, item_key, lg)
            if not dry_run:
                with open(mp, 'w', encoding='utf-8') as f:
                    yaml.dump(meta, f, allow_unicode=True)
            print(f"  Meta A ({lg}): {mp.name}")

    return True


def process_item_b(series, item_key, dry_run, regen_meta):
    """Educational version → all 3 queues (same video, language-specific meta)."""
    item   = ALL_SERIES[series][item_key]
    queues = {'en': QUEUE_EN, 'ar': QUEUE_AR, 'id': QUEUE_ID}
    props  = {
        "shapes": ["circle", "star"],
        "colors": [item["accent"], "#FFFFFF"],
        "bgColor": item["bg"], "bpm": item["bpm"],
        "showLabels": False, "musicFile": item["music"],
    }
    out_mp4 = QUEUE_EN / f"eo_{series}_{item_key}_b_{DATE_STR}.mp4"

    if not out_mp4.exists() and not dry_run and not regen_meta:
        cmd = ["npx", "remotion", "render", "ShapeDanceLong",
               f"--props={json.dumps(props)}", f"--output={str(out_mp4)}"]
        print(f"  Render B: {out_mp4.name}")
        r = subprocess.run(cmd, cwd=str(REMOTION), timeout=21600)
        if r.returncode != 0:
            print("  FAILED")
            return False

    if out_mp4.exists() and not dry_run:
        for lg in ['ar', 'id']:
            dest = queues[lg] / out_mp4.name
            if not dest.exists():
                shutil.copy2(str(out_mp4), str(dest))

    for lg, q in queues.items():
        mp = q / f"meta_{out_mp4.stem}.yaml"
        if not mp.exists() or regen_meta:
            meta = make_meta_b(series, item_key, lg)
            if not dry_run:
                with open(mp, 'w', encoding='utf-8') as f:
                    yaml.dump(meta, f, allow_unicode=True)
            print(f"  Meta B ({lg}): {mp.name}")

    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--key',        default=None, help='orchestrator key e.g. emotions_4series')
    parser.add_argument('--series',     default=None, choices=list(ALL_SERIES))
    parser.add_argument('--item',       default=None)
    parser.add_argument('--type',       default='both', choices=['A', 'B', 'both'])
    parser.add_argument('--dry-run',    action='store_true')
    parser.add_argument('--regen-meta', action='store_true')
    args = parser.parse_args()

    if args.item:
        # Find which series this item belongs to
        found_series = None
        for s, items in ALL_SERIES.items():
            if args.item in items:
                found_series = s
                break
        if not found_series:
            print(f"Unknown item: {args.item}")
            return
        series_to_run = {found_series: {args.item: ALL_SERIES[found_series][args.item]}}
    elif args.series:
        series_to_run = {args.series: ALL_SERIES[args.series]}
    else:
        # --key emotions_4series or no args → all 4 series
        series_to_run = ALL_SERIES

    total = sum(len(items) for items in series_to_run.values())
    run_a = args.type in ('A', 'both')
    run_b = args.type in ('B', 'both')
    videos_per_item = (1 if run_a else 0) + (1 if run_b else 0)
    total_videos = total * videos_per_item
    print(f"=== Emotions+Ocean+Transport+Professions — {total_videos} videos ===")

    done = 0
    for series, items in series_to_run.items():
        ser_name = SERIES_NAMES[series]['en']
        print(f"\n--- Series: {ser_name} ({len(items)} items) ---")
        for item_key in items:
            item = items[item_key]
            print(f"\n[{item_key.upper()}] {item['name_en']}")
            if run_a and process_item_a(series, item_key, args.dry_run, args.regen_meta):
                done += 1
            if run_b and process_item_b(series, item_key, args.dry_run, args.regen_meta):
                done += 1

    print(f"\n=== Done: {done}/{total_videos} ===")


if __name__ == '__main__':
    main()
