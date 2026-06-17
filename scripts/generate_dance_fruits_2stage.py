#!/usr/bin/env python3
"""
Generate Fruits & Vegetables 2-Stage Dance series — 18 items × 2 stages = 36 videos.
Scenario: config/scenarios/dance_fruits_2stage_fruits_veg_2stage.txt

Stage A: No words — visual introduction (30 min, no text, no TTS) → EN+AR+ID
Stage B: With name + voiceover — language learning (25 min, EN+AR+ID separately)

10 Fruits: apple, banana, orange, strawberry, watermelon, grapes, pineapple, lemon, mango, cherry
8 Vegetables: carrot, tomato, corn, broccoli, peas, pumpkin, cucumber, eggplant

Usage:
  python3 scripts/generate_dance_fruits_2stage.py                   # all 36 videos
  python3 scripts/generate_dance_fruits_2stage.py --item apple      # single item (A+B)
  python3 scripts/generate_dance_fruits_2stage.py --type A          # all A videos
  python3 scripts/generate_dance_fruits_2stage.py --category fruits # fruits only
  python3 scripts/generate_dance_fruits_2stage.py --dry-run
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

# 10 fruits in introduction order
FRUITS = {
    "apple":      {"name_en": "Apple",      "name_ar": "تفاحة",    "name_id": "Apel",       "bg": "#0A0202", "accent": "#EF5350", "bpm": 75, "music": "Happy Happy Game Show.mp3"},
    "banana":     {"name_en": "Banana",     "name_ar": "موزة",     "name_id": "Pisang",     "bg": "#0A0A02", "accent": "#FFD600", "bpm": 72, "music": "Carefree.mp3"},
    "orange":     {"name_en": "Orange",     "name_ar": "برتقالة",  "name_id": "Jeruk",      "bg": "#0A0602", "accent": "#FF6D00", "bpm": 78, "music": "Merry Go.mp3"},
    "strawberry": {"name_en": "Strawberry", "name_ar": "فراولة",   "name_id": "Stroberi",   "bg": "#0A0204", "accent": "#E91E63", "bpm": 80, "music": "Wholesome.mp3"},
    "watermelon": {"name_en": "Watermelon", "name_ar": "بطيخة",    "name_id": "Semangka",   "bg": "#020A04", "accent": "#4CAF50", "bpm": 70, "music": "Quirky Dog.mp3"},
    "grapes":     {"name_en": "Grapes",     "name_ar": "عنب",      "name_id": "Anggur",     "bg": "#05020A", "accent": "#7B1FA2", "bpm": 68, "music": "Heartwarming.mp3"},
    "pineapple":  {"name_en": "Pineapple",  "name_ar": "أناناس",   "name_id": "Nanas",      "bg": "#0A0902", "accent": "#FFC107", "bpm": 82, "music": "Pinball Spring.mp3"},
    "lemon":      {"name_en": "Lemon",      "name_ar": "ليمون",    "name_id": "Lemon",      "bg": "#0A0A02", "accent": "#FFEE58", "bpm": 75, "music": "Life of Riley.mp3"},
    "mango":      {"name_en": "Mango",      "name_ar": "مانجو",    "name_id": "Mangga",     "bg": "#0A0702", "accent": "#FF8F00", "bpm": 78, "music": "Monkeys Spinning Monkeys.mp3"},
    "cherry":     {"name_en": "Cherry",     "name_ar": "كرز",      "name_id": "Ceri",       "bg": "#0A0204", "accent": "#D32F2F", "bpm": 85, "music": "Hyperfun.mp3"},
}

# 8 vegetables in introduction order
VEGETABLES = {
    "carrot":     {"name_en": "Carrot",     "name_ar": "جزرة",     "name_id": "Wortel",     "bg": "#0A0602", "accent": "#FF6D00", "bpm": 75, "music": "Carefree.mp3"},
    "tomato":     {"name_en": "Tomato",     "name_ar": "طماطم",    "name_id": "Tomat",      "bg": "#0A0202", "accent": "#F44336", "bpm": 72, "music": "Wholesome.mp3"},
    "corn":       {"name_en": "Corn",       "name_ar": "ذرة",      "name_id": "Jagung",     "bg": "#0A0A02", "accent": "#FDD835", "bpm": 80, "music": "Happy Happy Game Show.mp3"},
    "broccoli":   {"name_en": "Broccoli",   "name_ar": "بروكلي",   "name_id": "Brokoli",    "bg": "#020A02", "accent": "#388E3C", "bpm": 65, "music": "Gymnopedie No 1.mp3"},
    "peas":       {"name_en": "Peas",       "name_ar": "بازلاء",   "name_id": "Kacang Polong","bg": "#030A02","accent": "#66BB6A","bpm": 70, "music": "Merry Go.mp3"},
    "pumpkin":    {"name_en": "Pumpkin",    "name_ar": "قرع",      "name_id": "Labu",       "bg": "#0A0602", "accent": "#E65100", "bpm": 68, "music": "Quirky Dog.mp3"},
    "cucumber":   {"name_en": "Cucumber",   "name_ar": "خيار",     "name_id": "Timun",      "bg": "#020A04", "accent": "#4CAF50", "bpm": 72, "music": "Life of Riley.mp3"},
    "eggplant":   {"name_en": "Eggplant",   "name_ar": "باذنجان",  "name_id": "Terong",     "bg": "#08020A", "accent": "#7B1FA2", "bpm": 65, "music": "Heartwarming.mp3"},
}

ALL_ITEMS = {}
ALL_ITEMS.update({k: {**v, "category": "fruit"}   for k, v in FRUITS.items()})
ALL_ITEMS.update({k: {**v, "category": "vegetable"} for k, v in VEGETABLES.items()})


def make_meta_a(item_key, lang):
    item = ALL_ITEMS[item_key]
    ch   = {'en': '@HappyBearKids1', 'ar': '@happybearkidsar', 'id': '@happybearkidsin'}
    name = item[f'name_{lang}']
    cat  = "fruit" if item['category'] == 'fruit' else "vegetable"

    if lang == 'en':
        return {
            "title": f"Dancing {name} | 30 Min Baby Animation | Happy Bear Kids",
            "description": (
                f"🍎 Watch the adorable {name} come to life and dance for 30 minutes!\n\n"
                f"Stage 1 of 2 — Visual Introduction: Pure animation with no words, "
                f"no text — just the {name} dancing, bouncing, and moving to gentle music.\n\n"
                f"Why visual introduction first? Research shows babies learn objects "
                f"through repeated visual exposure BEFORE learning the word. "
                f"This is how all babies learn naturally!\n\n"
                f"Movement character: every {cat} has its own unique dance style "
                f"based on its real-world properties — shape, weight, texture.\n\n"
                f"✨ 30 minutes of continuous animation\n"
                f"🎵 BPM {item['bpm']} — gentle and calming\n"
                f"🌈 No language barriers — universal for any culture\n"
                f"👶 Age: 0–3 years\n\n"
                f"🔔 Subscribe → {ch['en']}\n"
                f"🎵 Kevin MacLeod (incompetech.com) — CC Attribution 4.0\n\n"
                f"#Dancing{name} #HappyBearKids #BabyAnimation "
                f"#VisualLearning #CalmBaby\n© Happy Bear Kids 2026"
            ),
            "tags": [item_key, f"dancing {name.lower()}", "baby animation", "visual learning",
                     "happy bear kids", "no talking", "calm baby", cat, "30 minutes"],
            "video_type": "dance_fruits_2stage", "language": "en", "is_short": False, "status": "public",
        }
    elif lang == 'ar':
        return {
            "title": f"{name} الراقصة | رسوم متحركة للرضع 30 دقيقة | هابي بير كيدز",
            "description": (
                f"🍎 شاهد {name} الجميلة تحيا وترقص لمدة 30 دقيقة!\n\n"
                f"المرحلة الأولى من 2 — التعرف البصري: رسوم متحركة خالصة بدون كلمات أو نصوص — "
                f"فقط {name} ترقص وتتحرك على موسيقى هادئة.\n\n"
                f"بهجة بصرية خالصة دون ضغط أو أسئلة — تماماً كما يتعلم الأطفال في الحياة الطبيعية!\n\n"
                f"🔔 اشتركوا → {ch['ar']}\n"
                f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
                f"#{name}_راقصة #هابي_بير_كيدز #رسوم_أطفال "
                f"#تحفيز_بصري\n© هابي بير كيدز 2026"
            ),
            "tags": [item_key, name, "رسوم مجردة", "هابي بير كيدز", "بدون كلام", "تحفيز بصري"],
            "video_type": "dance_fruits_2stage", "language": "ar", "is_short": False, "status": "public",
        }
    else:
        return {
            "title": f"{name} Menari | 30 Menit Animasi Bayi | Happy Bear Kids",
            "description": (
                f"🍎 Saksikan {name} yang menggemaskan hidup dan menari selama 30 menit!\n\n"
                f"Tahap 1 dari 2 — Pengenalan Visual: Animasi murni tanpa kata-kata atau teks — "
                f"hanya {name} menari, melompat, dan bergerak mengikuti musik lembut.\n\n"
                f"Kesenangan visual murni tanpa tekanan — persis seperti cara bayi belajar di kehidupan nyata!\n\n"
                f"🔔 Subscribe → {ch['id']}\n"
                f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
                f"#{name}Menari #HappyBearKids #AnimasiAnak "
                f"#BelajarVisual\n© Happy Bear Kids Indonesia 2026"
            ),
            "tags": [item_key, f"{name.lower()} menari", "animasi bayi", "belajar visual",
                     "happy bear kids", "tanpa suara"],
            "video_type": "dance_fruits_2stage", "language": "id", "is_short": False, "status": "public",
        }


def make_meta_b(item_key, lang):
    item    = ALL_ITEMS[item_key]
    ch      = {'en': '@HappyBearKids1', 'ar': '@happybearkidsar', 'id': '@happybearkidsin'}
    name_en = item['name_en']
    name_ar = item['name_ar']
    name_id = item['name_id']
    name    = item[f'name_{lang}']

    if lang == 'en':
        return {
            "title": f"Learn: {name_en}! Trilingual Baby Video | Happy Bear Kids",
            "description": (
                f"🎓 Learn to say {name_en}!\n\n"
                f"Stage 2 of 2 — Learning the Word: Now your baby already knows what "
                f"{name_en} looks like from Stage 1! Time to learn the name.\n\n"
                f"In this video:\n"
                f"• English: {name_en}\n"
                f"• Arabic: {name_ar}\n"
                f"• Indonesian: {name_id}\n\n"
                f"Same dancing {name_en} from Stage 1 — but now with the name added. "
                f"Your baby recognizes the character and feels confident!\n\n"
                f"✨ Educational approach based on speech development research\n"
                f"🌍 Trilingual content for multicultural families\n"
                f"👶 Age: 0–3 years | 📺 25 minutes\n\n"
                f"🔔 Subscribe → {ch['en']}\n"
                f"🎵 Kevin MacLeod (incompetech.com) — CC Attribution 4.0\n\n"
                f"#Learn{name_en} #HappyBearKids #TrilingualBaby "
                f"#BabyEducation #LearnEnglish\n© Happy Bear Kids 2026"
            ),
            "tags": [item_key, f"learn {name_en.lower()}", "trilingual baby", "educational",
                     "happy bear kids", "english arabic indonesian", name_en.lower()],
            "video_type": "dance_fruits_2stage", "language": "en", "is_short": False, "status": "public",
        }
    elif lang == 'ar':
        return {
            "title": f"تعلم: {name_ar}! فيديو ثلاثي اللغات للرضع | هابي بير كيدز",
            "description": (
                f"🎓 تعلم قول {name_ar}!\n\n"
                f"المرحلة الثانية من 2 — تعلم الكلمة: طفلك يعرف الآن كيف تبدو {name_ar} من المرحلة الأولى! "
                f"حان وقت تعلم الاسم.\n\n"
                f"في هذا الفيديو:\n"
                f"• بالعربية: {name_ar}\n"
                f"• بالإنجليزية: {name_en}\n"
                f"• بالإندونيسية: {name_id}\n\n"
                f"🔔 اشتركوا → {ch['ar']}\n"
                f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
                f"#تعلم_{name_ar} #هابي_بير_كيدز #تعليم_الرضع "
                f"#ثلاثي_اللغات\n© هابي بير كيدز 2026"
            ),
            "tags": [item_key, name_ar, "تعليم الرضع", "هابي بير كيدز", "ثلاثي اللغات"],
            "video_type": "dance_fruits_2stage", "language": "ar", "is_short": False, "status": "public",
        }
    else:
        return {
            "title": f"Belajar: {name_id}! Video Tiga Bahasa untuk Bayi | Happy Bear Kids",
            "description": (
                f"🎓 Belajar mengucapkan {name_id}!\n\n"
                f"Tahap 2 dari 2 — Belajar Kata: Bayi Anda sudah tahu penampilan {name_id} dari Tahap 1! "
                f"Saatnya belajar namanya.\n\n"
                f"Dalam video ini:\n"
                f"• Bahasa Indonesia: {name_id}\n"
                f"• Bahasa Inggris: {name_en}\n"
                f"• Bahasa Arab: {name_ar}\n\n"
                f"🔔 Subscribe → {ch['id']}\n"
                f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
                f"#Belajar{name_id.replace(' ','')} #HappyBearKids #TigaBahasa "
                f"#PendidikanBayi\n© Happy Bear Kids Indonesia 2026"
            ),
            "tags": [item_key, f"belajar {name_id.lower()}", "tiga bahasa", "happy bear kids",
                     "pendidikan bayi", name_id.lower()],
            "video_type": "dance_fruits_2stage", "language": "id", "is_short": False, "status": "public",
        }


def process_stage_a(item_key, dry_run, regen_meta):
    """No-words stage → all 3 queues."""
    item   = ALL_ITEMS[item_key]
    queues = {'en': QUEUE_EN, 'ar': QUEUE_AR, 'id': QUEUE_ID}
    props  = {
        "shapes": ["circle", "star", "square"],
        "colors": [item["accent"], "#FFFFFF", item["accent"]],
        "bgColor": item["bg"], "bpm": item["bpm"],
        "showLabels": False, "musicFile": item["music"],
    }
    out_mp4 = QUEUE_EN / f"dfs_{item_key}_a_{DATE_STR}.mp4"

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
            meta = make_meta_a(item_key, lg)
            if not dry_run:
                with open(mp, 'w', encoding='utf-8') as f:
                    yaml.dump(meta, f, allow_unicode=True)
            print(f"  Meta A ({lg}): {mp.name}")

    return True


def process_stage_b(item_key, dry_run, regen_meta):
    """Educational stage → all 3 queues (language-specific in future)."""
    item   = ALL_ITEMS[item_key]
    queues = {'en': QUEUE_EN, 'ar': QUEUE_AR, 'id': QUEUE_ID}
    props  = {
        "shapes": ["circle", "star"],
        "colors": [item["accent"], "#FFFFFF"],
        "bgColor": item["bg"], "bpm": item["bpm"],
        "showLabels": False, "musicFile": item["music"],
    }
    out_mp4 = QUEUE_EN / f"dfs_{item_key}_b_{DATE_STR}.mp4"

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
            meta = make_meta_b(item_key, lg)
            if not dry_run:
                with open(mp, 'w', encoding='utf-8') as f:
                    yaml.dump(meta, f, allow_unicode=True)
            print(f"  Meta B ({lg}): {mp.name}")

    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--key',        default=None, help='orchestrator key e.g. fruits_veg_2stage')
    parser.add_argument('--item',       default=None, choices=list(ALL_ITEMS))
    parser.add_argument('--category',   default=None, choices=['fruits', 'vegetables'])
    parser.add_argument('--type',       default='both', choices=['A', 'B', 'both'])
    parser.add_argument('--dry-run',    action='store_true')
    parser.add_argument('--regen-meta', action='store_true')
    args = parser.parse_args()

    if args.item:
        items = [args.item]
    elif args.category == 'fruits':
        items = list(FRUITS)
    elif args.category == 'vegetables':
        items = list(VEGETABLES)
    else:
        items = list(ALL_ITEMS)

    run_a = args.type in ('A', 'both')
    run_b = args.type in ('B', 'both')
    vids_per = (1 if run_a else 0) + (1 if run_b else 0)
    print(f"=== Fruits & Vegetables 2-Stage — {len(items)} items × {vids_per} stages = {len(items)*vids_per} videos ===")

    done = 0
    for item_key in items:
        item = ALL_ITEMS[item_key]
        cat  = item['category']
        print(f"\n[{item_key.upper()}] {item['name_en']} ({cat})")
        if run_a and process_stage_a(item_key, args.dry_run, args.regen_meta):
            done += 1
        if run_b and process_stage_b(item_key, args.dry_run, args.regen_meta):
            done += 1

    print(f"\n=== Done: {done}/{len(items)*vids_per} ===")


if __name__ == '__main__':
    main()
