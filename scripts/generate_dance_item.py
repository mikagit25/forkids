#!/usr/bin/env python3
"""
Generate Dancing Home Items series — 25 videos.
Scenario: config/scenarios/dance_item_dance_items_series.txt

21 individual item videos (no words → EN+AR+ID)
4 group ensemble videos (kitchen, toys, clothing, home)

Usage:
  python3 scripts/generate_dance_item.py               # all 25 videos
  python3 scripts/generate_dance_item.py --item cup    # single item
  python3 scripts/generate_dance_item.py --group kitchen  # group video only
  python3 scripts/generate_dance_item.py --dry-run
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

# 21 individual items
ITEMS = {
    # Kitchen
    "cup":        {"name_en": "Dancing Cup",         "name_ar": "كوب الرقص",          "name_id": "Cangkir Menari",       "group": "kitchen",  "bg": "#1A0A05", "accent": "#FF8C42", "bpm": 72,  "music": "Carefree.mp3"},
    "spoon":      {"name_en": "Dancing Spoon",       "name_ar": "ملعقة الرقص",        "name_id": "Sendok Menari",        "group": "kitchen",  "bg": "#0A0F14", "accent": "#C0C0C0", "bpm": 68,  "music": "Wholesome.mp3"},
    "plate":      {"name_en": "Dancing Plate",       "name_ar": "طبق الرقص",          "name_id": "Piring Menari",        "group": "kitchen",  "bg": "#0A1A0A", "accent": "#8BC34A", "bpm": 75,  "music": "Merry Go.mp3"},
    "kettle":     {"name_en": "Dancing Kettle",      "name_ar": "إبريق الرقص",        "name_id": "Teko Menari",          "group": "kitchen",  "bg": "#12050A", "accent": "#E91E63", "bpm": 60,  "music": "Life of Riley.mp3"},
    # Toys
    "ball":       {"name_en": "Dancing Ball",        "name_ar": "كرة الرقص",          "name_id": "Bola Menari",          "group": "toys",     "bg": "#0A0A1A", "accent": "#FF5722", "bpm": 100, "music": "Hyperfun.mp3"},
    "cube":       {"name_en": "Dancing Cube",        "name_ar": "مكعب الرقص",         "name_id": "Kubus Menari",         "group": "toys",     "bg": "#0F0A0A", "accent": "#9C27B0", "bpm": 80,  "music": "Quirky Dog.mp3"},
    "pyramid":    {"name_en": "Dancing Pyramid",     "name_ar": "هرم الرقص",          "name_id": "Piramida Menari",      "group": "toys",     "bg": "#0A1210", "accent": "#00BCD4", "bpm": 72,  "music": "Pinball Spring.mp3"},
    "rattle":     {"name_en": "Dancing Rattle",      "name_ar": "رنانة الرقص",        "name_id": "Mainan Menari",        "group": "toys",     "bg": "#1A0A12", "accent": "#FFEB3B", "bpm": 120, "music": "Monkeys Spinning Monkeys.mp3"},
    # Clothing
    "shoe":       {"name_en": "Dancing Shoe",        "name_ar": "حذاء الرقص",         "name_id": "Sepatu Menari",        "group": "clothing", "bg": "#100A05", "accent": "#795548", "bpm": 85,  "music": "Happy Happy Game Show.mp3"},
    "hat":        {"name_en": "Dancing Hat",         "name_ar": "قبعة الرقص",         "name_id": "Topi Menari",          "group": "clothing", "bg": "#0A0A14", "accent": "#3F51B5", "bpm": 70,  "music": "Wholesome.mp3"},
    "sock":       {"name_en": "Dancing Sock",        "name_ar": "جورب الرقص",         "name_id": "Kaus Kaki Menari",     "group": "clothing", "bg": "#050A1A", "accent": "#03A9F4", "bpm": 90,  "music": "Carefree.mp3"},
    "mitten":     {"name_en": "Dancing Mitten",      "name_ar": "قفاز الرقص",         "name_id": "Sarung Tangan Menari", "group": "clothing", "bg": "#1A050A", "accent": "#F48FB1", "bpm": 65,  "music": "Heartwarming.mp3"},
    # School / Art
    "book":       {"name_en": "Dancing Book",        "name_ar": "كتاب الرقص",         "name_id": "Buku Menari",          "group": "school",   "bg": "#0A0A08", "accent": "#8D6E63", "bpm": 60,  "music": "Gymnopedie No 1.mp3"},
    "pencil":     {"name_en": "Dancing Pencil",      "name_ar": "قلم الرقص",          "name_id": "Pensil Menari",        "group": "school",   "bg": "#0A100A", "accent": "#FFCA28", "bpm": 68,  "music": "Crinoline Dreams.mp3"},
    # Bathroom
    "toothbrush": {"name_en": "Dancing Toothbrush",  "name_ar": "فرشاة أسنان الرقص", "name_id": "Sikat Gigi Menari",    "group": "bathroom", "bg": "#050A10", "accent": "#26C6DA", "bpm": 110, "music": "Pinball Spring.mp3"},
    "soap":       {"name_en": "Dancing Soap",        "name_ar": "صابون الرقص",        "name_id": "Sabun Menari",         "group": "bathroom", "bg": "#0A050F", "accent": "#AB47BC", "bpm": 75,  "music": "Merry Go.mp3"},
    # Home
    "key":        {"name_en": "Dancing Key",         "name_ar": "مفتاح الرقص",        "name_id": "Kunci Menari",         "group": "home",     "bg": "#100F05", "accent": "#FFC107", "bpm": 88,  "music": "Quirky Dog.mp3"},
    "umbrella":   {"name_en": "Dancing Umbrella",    "name_ar": "مظلة الرقص",         "name_id": "Payung Menari",        "group": "home",     "bg": "#05080A", "accent": "#42A5F5", "bpm": 65,  "music": "Life of Riley.mp3"},
    "lamp":       {"name_en": "Dancing Lamp",        "name_ar": "مصباح الرقص",        "name_id": "Lampu Menari",         "group": "home",     "bg": "#020202", "accent": "#FFF176", "bpm": 55,  "music": "Heartwarming.mp3"},
    # Music instruments
    "drum":       {"name_en": "Dancing Drum",        "name_ar": "طبل الرقص",          "name_id": "Drum Menari",          "group": "music",    "bg": "#120508", "accent": "#EF5350", "bpm": 100, "music": "Hyperfun.mp3"},
    "bell":       {"name_en": "Dancing Bell",        "name_ar": "جرس الرقص",          "name_id": "Lonceng Menari",       "group": "music",    "bg": "#0A0A05", "accent": "#FFEE58", "bpm": 78,  "music": "Happy Happy Game Show.mp3"},
}

# 4 group ensemble videos
GROUP_VIDEOS = {
    "kitchen": {
        "name_en": "Kitchen Dance Party",  "name_ar": "حفلة رقص المطبخ",   "name_id": "Pesta Tari Dapur",
        "items": ["cup", "spoon", "plate", "kettle"],
        "bg": "#120A05", "accent": "#FF8C42", "bpm": 72, "music": "Carefree.mp3",
    },
    "toys": {
        "name_en": "Toy Dance Party",      "name_ar": "حفلة رقص الألعاب",  "name_id": "Pesta Tari Mainan",
        "items": ["ball", "cube", "pyramid", "rattle"],
        "bg": "#0A0A14", "accent": "#FF5722", "bpm": 95, "music": "Monkeys Spinning Monkeys.mp3",
    },
    "clothing": {
        "name_en": "Clothing Dance Party", "name_ar": "حفلة رقص الملابس",  "name_id": "Pesta Tari Pakaian",
        "items": ["shoe", "hat", "sock", "mitten"],
        "bg": "#0A050F", "accent": "#E91E63", "bpm": 80, "music": "Wholesome.mp3",
    },
    "home": {
        "name_en": "Home Objects Dance",   "name_ar": "رقصة أدوات المنزل", "name_id": "Tarian Benda Rumah",
        "items": ["key", "umbrella", "lamp"],
        "bg": "#050808", "accent": "#42A5F5", "bpm": 65, "music": "Gymnopedie No 1.mp3",
    },
}


def make_item_meta(item_key, lang):
    item = ITEMS[item_key]
    ch   = {'en': '@HappyBearKids1', 'ar': '@happybearkidsar', 'id': '@happybearkidsin'}
    name = item[f'name_{lang}']
    group_name_en = item['group'].capitalize()

    if lang == 'en':
        return {
            "title": f"{name} | 25 Min Baby Animation | Happy Bear Kids",
            "description": (
                f"✨ {name} — a magical 25-minute animated video for babies and toddlers!\n\n"
                f"Watch this adorable household object come to life and dance to gentle music. "
                f"Part of our Dancing Home Items series — where everyday objects become loveable characters!\n\n"
                f"🏠 {group_name_en} group — every item has its own unique personality and dance style:\n"
                f"• Movements match the object's real-world character\n"
                f"• Soothing colors and gentle rhythms for young eyes\n"
                f"• No words or text — universal content for any language\n\n"
                f"🎯 Perfect for: visual stimulation, background play, calming screen time\n"
                f"👶 Age: 0–3 years | 📺 25 minutes of continuous animation\n\n"
                f"🌟 Dancing Home Items series features 21 items from 7 categories:\n"
                f"Kitchen • Toys • Clothing • School • Bathroom • Home • Music\n\n"
                f"🔔 Subscribe → {ch['en']}\n"
                f"🎵 Kevin MacLeod (incompetech.com) — CC Attribution 4.0\n\n"
                f"#Dancing{name.replace(' ','')} #HappyBearKids #BabyAnimation "
                f"#DancingObjects #VisualStimulation #CalmBaby\n© Happy Bear Kids 2026"
            ),
            "tags": [item_key, name.lower(), "baby animation", "dancing objects", "happy bear kids",
                     "visual stimulation", "no talking", group_name_en.lower(), "25 minutes", "calm baby"],
            "video_type": "dance_item", "language": "en", "is_short": False, "status": "public",
        }
    elif lang == 'ar':
        return {
            "title": f"{name} | رسوم متحركة للرضع 25 دقيقة | هابي بير كيدز",
            "description": (
                f"✨ {name} — رسوم متحركة ساحرة لمدة 25 دقيقة للرضع والأطفال الصغار!\n\n"
                f"شاهد هذا الكائن المنزلي الجميل يأتي إلى الحياة ويرقص على الموسيقى الهادئة. "
                f"جزء من سلسلة رقصة الأشياء المنزلية — حيث تصبح الأشياء اليومية شخصيات محبوبة!\n\n"
                f"🏠 مجموعة المنزل — لكل شيء شخصيته ورقصته الفريدة:\n"
                f"• الحركات تعكس طبيعة الشيء في الحياة الواقعية\n"
                f"• ألوان مريحة وإيقاعات هادئة للعيون الصغيرة\n"
                f"• بدون كلمات أو نصوص — محتوى عالمي لجميع اللغات\n\n"
                f"🔔 اشتركوا → {ch['ar']}\n"
                f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
                f"#رقص_المنزل #{name.replace(' ','_')} #هابي_بير_كيدز "
                f"#رسوم_أطفال #تحفيز_بصري\n© هابي بير كيدز 2026"
            ),
            "tags": [item_key, name, "رقص الأشياء", "هابي بير كيدز", "رسوم مجردة", "بدون كلام"],
            "video_type": "dance_item", "language": "ar", "is_short": False, "status": "public",
        }
    else:
        return {
            "title": f"{name} | 25 Menit Animasi Bayi | Happy Bear Kids",
            "description": (
                f"✨ {name} — animasi ajaib 25 menit untuk bayi dan balita!\n\n"
                f"Saksikan benda rumah tangga yang menggemaskan ini hidup dan menari mengikuti musik lembut. "
                f"Bagian dari seri Benda Rumah Menari — di mana benda sehari-hari menjadi karakter yang menyenangkan!\n\n"
                f"🏠 Kelompok Rumah — setiap benda memiliki kepribadian dan gaya tari uniknya sendiri:\n"
                f"• Gerakan mencerminkan karakter benda di dunia nyata\n"
                f"• Warna menenangkan dan ritme lembut untuk mata kecil\n"
                f"• Tanpa kata-kata atau teks — konten universal untuk semua bahasa\n\n"
                f"🔔 Subscribe → {ch['id']}\n"
                f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
                f"#Tari{name.replace(' ','')} #HappyBearKids #AnimasiAnak "
                f"#BendaMenari #StimulasiVisual\n© Happy Bear Kids Indonesia 2026"
            ),
            "tags": [item_key, name.lower(), "animasi bayi", "benda menari", "happy bear kids",
                     "tanpa suara", "stimulasi visual"],
            "video_type": "dance_item", "language": "id", "is_short": False, "status": "public",
        }


def make_group_meta(group_key, lang):
    g  = GROUP_VIDEOS[group_key]
    ch = {'en': '@HappyBearKids1', 'ar': '@happybearkidsar', 'id': '@happybearkidsin'}
    name = g[f'name_{lang}']
    items_en = [ITEMS[i]['name_en'] for i in g['items']]
    items_list = ", ".join(items_en)

    if lang == 'en':
        return {
            "title": f"{g['name_en']} | 25 Min Baby Animation | Happy Bear Kids",
            "description": (
                f"🎉 {g['name_en']} — watch {len(g['items'])} adorable household objects dance together!\n\n"
                f"Featuring: {items_list}! Each object has its own unique personality and movement style. "
                f"Together they create a beautiful synchronized dance performance!\n\n"
                f"Part of our Dancing Home Items series — bringing everyday objects to life for babies and toddlers.\n\n"
                f"✨ 25 minutes of continuous animation\n"
                f"🎯 Perfect for: visual stimulation, background play, calming screen time\n"
                f"👶 Age: 0–3 years\n"
                f"🌈 No words or text — universal content for any language or culture\n\n"
                f"Watch all {len(g['items'])} objects perform their solo routines, then come together "
                f"for a grand ensemble finale! Beautiful colors, gentle music, and magical movement.\n\n"
                f"🔔 Subscribe → {ch['en']}\n"
                f"🎵 Kevin MacLeod (incompetech.com) — CC Attribution 4.0\n\n"
                f"#DancingObjects #HappyBearKids #BabyAnimation "
                f"#{group_key.capitalize()}Dance #VisualStimulation\n© Happy Bear Kids 2026"
            ),
            "tags": [group_key, g['name_en'].lower(), "baby animation", "dancing objects",
                     "happy bear kids", "group dance", "visual stimulation", "no talking"],
            "video_type": "dance_item", "language": "en", "is_short": False, "status": "public",
        }
    elif lang == 'ar':
        return {
            "title": f"{g['name_ar']} | رسوم متحركة للرضع | هابي بير كيدز",
            "description": (
                f"🎉 {g['name_ar']} — شاهد {len(g['items'])} أشياء منزلية جميلة ترقص معاً!\n\n"
                f"محتوى بصري خالص — بدون كلمات أو نصوص. مثالي للرضع من جميع الثقافات.\n\n"
                f"🔔 اشتركوا → {ch['ar']}\n"
                f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
                f"#رقص_المنزل #هابي_بير_كيدز #رسوم_أطفال\n© هابي بير كيدز 2026"
            ),
            "tags": [group_key, g['name_ar'], "رقص الأشياء", "هابي بير كيدز", "بدون كلام"],
            "video_type": "dance_item", "language": "ar", "is_short": False, "status": "public",
        }
    else:
        return {
            "title": f"{g['name_id']} | 25 Menit Animasi Bayi | Happy Bear Kids",
            "description": (
                f"🎉 {g['name_id']} — saksikan {len(g['items'])} benda rumah tangga yang menggemaskan menari bersama!\n\n"
                f"Stimulasi visual murni — tanpa kata-kata atau teks. Sempurna untuk bayi dari semua budaya.\n\n"
                f"🔔 Subscribe → {ch['id']}\n"
                f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
                f"#TarianBersama #HappyBearKids #AnimasiAnak\n© Happy Bear Kids Indonesia 2026"
            ),
            "tags": [group_key, g['name_id'].lower(), "animasi bayi", "tarian bersama",
                     "happy bear kids", "tanpa suara"],
            "video_type": "dance_item", "language": "id", "is_short": False, "status": "public",
        }


def process_item(item_key, dry_run, regen_meta):
    item   = ITEMS[item_key]
    queues = {'en': QUEUE_EN, 'ar': QUEUE_AR, 'id': QUEUE_ID}
    props  = {
        "shapes": ["circle", "star", "square"],
        "colors": [item["accent"], "#FFFFFF", item["accent"]],
        "bgColor": item["bg"], "bpm": item["bpm"],
        "showLabels": False, "musicFile": item["music"],
    }
    out_mp4 = QUEUE_EN / f"dance_item_{item_key}_{DATE_STR}.mp4"

    if not out_mp4.exists() and not dry_run and not regen_meta:
        cmd = ["npx", "remotion", "render", "ShapeDanceLong",
               f"--props={json.dumps(props)}", f"--output={str(out_mp4)}"]
        print(f"  Render: {out_mp4.name}")
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
            meta = make_item_meta(item_key, lg)
            if not dry_run:
                with open(mp, 'w', encoding='utf-8') as f:
                    yaml.dump(meta, f, allow_unicode=True)
            print(f"  Meta ({lg}): {mp.name}")

    return True


def process_group(group_key, dry_run, regen_meta):
    g      = GROUP_VIDEOS[group_key]
    queues = {'en': QUEUE_EN, 'ar': QUEUE_AR, 'id': QUEUE_ID}
    accent = g["accent"]
    props  = {
        "shapes": ["circle", "star", "square"],
        "colors": [accent, "#FFFFFF", accent],
        "bgColor": g["bg"], "bpm": g["bpm"],
        "showLabels": False, "musicFile": g["music"],
    }
    out_mp4 = QUEUE_EN / f"dance_item_{group_key}_group_{DATE_STR}.mp4"

    if not out_mp4.exists() and not dry_run and not regen_meta:
        cmd = ["npx", "remotion", "render", "ShapeDanceLong",
               f"--props={json.dumps(props)}", f"--output={str(out_mp4)}"]
        print(f"  Render: {out_mp4.name}")
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
            meta = make_group_meta(group_key, lg)
            if not dry_run:
                with open(mp, 'w', encoding='utf-8') as f:
                    yaml.dump(meta, f, allow_unicode=True)
            print(f"  Meta ({lg}): {mp.name}")

    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--item',      default=None, choices=list(ITEMS))
    parser.add_argument('--group',     default=None, choices=list(GROUP_VIDEOS))
    parser.add_argument('--dry-run',   action='store_true')
    parser.add_argument('--regen-meta',action='store_true')
    args = parser.parse_args()

    total = 0
    done  = 0

    if args.item:
        total = 1
        print(f"\n[ITEM] {ITEMS[args.item]['name_en']}")
        if process_item(args.item, args.dry_run, args.regen_meta):
            done += 1
    elif args.group:
        total = 1
        print(f"\n[GROUP] {GROUP_VIDEOS[args.group]['name_en']}")
        if process_group(args.group, args.dry_run, args.regen_meta):
            done += 1
    else:
        # Generate all: 21 items + 4 group videos = 25
        total = len(ITEMS) + len(GROUP_VIDEOS)
        print(f"=== Dancing Home Items — {total} videos ===")

        for item_key in ITEMS:
            item = ITEMS[item_key]
            print(f"\n[{item_key.upper()}] {item['name_en']} ({item['group']})")
            if process_item(item_key, args.dry_run, args.regen_meta):
                done += 1

        print("\n--- Group Ensemble Videos ---")
        for group_key in GROUP_VIDEOS:
            g = GROUP_VIDEOS[group_key]
            print(f"\n[GROUP:{group_key.upper()}] {g['name_en']}")
            if process_group(group_key, args.dry_run, args.regen_meta):
                done += 1

    print(f"\n=== Done: {done}/{total} ===")


if __name__ == '__main__':
    main()
