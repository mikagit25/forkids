#!/usr/bin/env python3
"""
Generate Fruits & Vegetables Group Dance series — 8 videos.
Scenario: config/scenarios/dance_fruits_group_fruits_veg_group_8.txt

8 color-family group videos, 25-30 min each, no words → EN+AR+ID.

Video 1: Red family    (apple, strawberry, tomato)
Video 2: Red + guest   (+ cherry)
Video 3: Yellow family (banana, lemon, corn)
Video 4: Yellow+orange (banana, pineapple, orange, carrot)
Video 5: Green family  (watermelon, broccoli, peas, cucumber)
Video 6: Orange family (orange, carrot, pumpkin)
Video 7: Grand parade  (apple, banana, carrot, watermelon, pineapple)
Video 8: All together  (apple, banana, orange, strawberry, carrot, pineapple)

Usage:
  python3 scripts/generate_dance_fruits_group.py          # all 8 videos
  python3 scripts/generate_dance_fruits_group.py --video 1
  python3 scripts/generate_dance_fruits_group.py --dry-run
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

VIDEOS = {
    "1": {
        "name_en": "Red Family Dance",           "name_ar": "رقصة العائلة الحمراء",     "name_id": "Tari Keluarga Merah",
        "items_en": ["Apple", "Strawberry", "Tomato"],
        "items_ar": ["تفاحة", "فراولة", "طماطم"],
        "items_id": ["Apel", "Stroberi", "Tomat"],
        "bg": "#0A0302", "accent": "#E53935", "bpm": 75, "music": "Carefree.mp3",
    },
    "2": {
        "name_en": "Red Family Plus Cherry",     "name_ar": "العائلة الحمراء والكرز",   "name_id": "Keluarga Merah Plus Ceri",
        "items_en": ["Apple", "Strawberry", "Tomato", "Cherry"],
        "items_ar": ["تفاحة", "فراولة", "طماطم", "كرز"],
        "items_id": ["Apel", "Stroberi", "Tomat", "Ceri"],
        "bg": "#0A0204", "accent": "#C62828", "bpm": 78, "music": "Wholesome.mp3",
    },
    "3": {
        "name_en": "Yellow Family Dance",        "name_ar": "رقصة العائلة الصفراء",    "name_id": "Tari Keluarga Kuning",
        "items_en": ["Banana", "Lemon", "Corn"],
        "items_ar": ["موزة", "ليمون", "ذرة"],
        "items_id": ["Pisang", "Lemon", "Jagung"],
        "bg": "#0A0A02", "accent": "#F9A825", "bpm": 80, "music": "Happy Happy Game Show.mp3",
    },
    "4": {
        "name_en": "Yellow and Orange Dance",   "name_ar": "رقصة الأصفر والبرتقالي",  "name_id": "Tari Kuning dan Oranye",
        "items_en": ["Banana", "Pineapple", "Orange", "Carrot"],
        "items_ar": ["موزة", "أناناس", "برتقالة", "جزرة"],
        "items_id": ["Pisang", "Nanas", "Jeruk", "Wortel"],
        "bg": "#0A0602", "accent": "#FB8C00", "bpm": 82, "music": "Merry Go.mp3",
    },
    "5": {
        "name_en": "Green Family Dance",        "name_ar": "رقصة العائلة الخضراء",    "name_id": "Tari Keluarga Hijau",
        "items_en": ["Watermelon", "Broccoli", "Peas", "Cucumber"],
        "items_ar": ["بطيخة", "بروكلي", "بازلاء", "خيار"],
        "items_id": ["Semangka", "Brokoli", "Kacang Polong", "Timun"],
        "bg": "#020A02", "accent": "#43A047", "bpm": 72, "music": "Life of Riley.mp3",
    },
    "6": {
        "name_en": "Orange Family Dance",       "name_ar": "رقصة العائلة البرتقالية", "name_id": "Tari Keluarga Oranye",
        "items_en": ["Orange", "Carrot", "Pumpkin"],
        "items_ar": ["برتقالة", "جزرة", "قرع"],
        "items_id": ["Jeruk", "Wortel", "Labu"],
        "bg": "#0A0502", "accent": "#EF6C00", "bpm": 75, "music": "Quirky Dog.mp3",
    },
    "7": {
        "name_en": "Grand Parade",              "name_ar": "الموكب الكبير",            "name_id": "Parade Besar",
        "items_en": ["Apple", "Banana", "Carrot", "Watermelon", "Pineapple"],
        "items_ar": ["تفاحة", "موزة", "جزرة", "بطيخة", "أناناس"],
        "items_id": ["Apel", "Pisang", "Wortel", "Semangka", "Nanas"],
        "bg": "#050A02", "accent": "#8BC34A", "bpm": 85, "music": "Monkeys Spinning Monkeys.mp3",
    },
    "8": {
        "name_en": "All Together Dance",        "name_ar": "رقصة الجميع معاً",        "name_id": "Tari Semua Bersama",
        "items_en": ["Apple", "Banana", "Orange", "Strawberry", "Carrot", "Pineapple"],
        "items_ar": ["تفاحة", "موزة", "برتقالة", "فراولة", "جزرة", "أناناس"],
        "items_id": ["Apel", "Pisang", "Jeruk", "Stroberi", "Wortel", "Nanas"],
        "bg": "#0A0A05", "accent": "#FFCA28", "bpm": 88, "music": "Hyperfun.mp3",
    },
}


def make_meta(vid_num, lang):
    v    = VIDEOS[vid_num]
    ch   = {'en': '@HappyBearKids1', 'ar': '@happybearkidsar', 'id': '@happybearkidsin'}
    name = v[f'name_{lang}']
    items = " • ".join(v[f'items_{lang}'])

    if lang == 'en':
        return {
            "title": f"{name} | Group Dance for Babies | Happy Bear Kids",
            "description": (
                f"🎉 {name} — watch {len(v['items_en'])} colorful fruits and vegetables dance together!\n\n"
                f"Featuring: {items}\n\n"
                f"Pure visual delight — no words, no text. Just beautiful colors, gentle movement, "
                f"and calming music designed for babies and toddlers.\n\n"
                f"Color family approach: objects that share colors help babies build visual categories "
                f"naturally — just like in real life!\n\n"
                f"✨ 25-30 minutes continuous animation\n"
                f"🎯 Dark background + bright characters = maximum visual contrast\n"
                f"🎵 BPM {v['bpm']} — gentle, never rushed\n"
                f"👶 Age: 0–3 years\n"
                f"🌈 No language barriers — universal content for any culture\n\n"
                f"🔔 Subscribe → {ch['en']}\n"
                f"🎵 Kevin MacLeod (incompetech.com) — CC Attribution 4.0\n\n"
                f"#{name.replace(' ','')} #HappyBearKids #FruitDance "
                f"#BabyAnimation #VisualStimulation\n© Happy Bear Kids 2026"
            ),
            "tags": [v['name_en'].lower()] + [i.lower() for i in v['items_en']] +
                    ["baby animation", "fruit dance", "happy bear kids", "group dance",
                     "visual stimulation", "no talking"],
            "video_type": "dance_fruits_group", "language": "en", "is_short": False, "status": "public",
        }
    elif lang == 'ar':
        return {
            "title": f"{name} | رقصة جماعية للرضع | هابي بير كيدز",
            "description": (
                f"🎉 {name} — شاهد {len(v['items_ar'])} فاكهة وخضروات ملونة ترقص معاً!\n\n"
                f"بطولة: {items}\n\n"
                f"بهجة بصرية خالصة — بدون كلمات أو نصوص. فقط ألوان جميلة وحركة هادئة "
                f"وموسيقى مريحة مصممة للرضع والأطفال الصغار.\n\n"
                f"🔔 اشتركوا → {ch['ar']}\n"
                f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
                f"#{name.replace(' ','_')} #هابي_بير_كيدز #رقص_الفاكهة "
                f"#رسوم_أطفال #تحفيز_بصري\n© هابي بير كيدز 2026"
            ),
            "tags": [v['name_ar']] + v['items_ar'] +
                    ["هابي بير كيدز", "رقص جماعي", "رسوم مجردة", "بدون كلام"],
            "video_type": "dance_fruits_group", "language": "ar", "is_short": False, "status": "public",
        }
    else:
        return {
            "title": f"{name} | Tari Kelompok untuk Bayi | Happy Bear Kids",
            "description": (
                f"🎉 {name} — saksikan {len(v['items_id'])} buah dan sayuran berwarna-warni menari bersama!\n\n"
                f"Menampilkan: {items}\n\n"
                f"Hiburan visual murni — tanpa kata-kata atau teks. Hanya warna-warna indah, "
                f"gerakan lembut, dan musik menenangkan yang dirancang untuk bayi dan balita.\n\n"
                f"🔔 Subscribe → {ch['id']}\n"
                f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
                f"#{name.replace(' ','')} #HappyBearKids #TariBuah "
                f"#AnimasiAnak #StimulasiVisual\n© Happy Bear Kids Indonesia 2026"
            ),
            "tags": [v['name_id'].lower()] + [i.lower() for i in v['items_id']] +
                    ["animasi bayi", "tari buah", "happy bear kids", "tari kelompok",
                     "stimulasi visual", "tanpa suara"],
            "video_type": "dance_fruits_group", "language": "id", "is_short": False, "status": "public",
        }


def process_video(vid_num, dry_run, regen_meta):
    v      = VIDEOS[vid_num]
    queues = {'en': QUEUE_EN, 'ar': QUEUE_AR, 'id': QUEUE_ID}
    props  = {
        "shapes": ["circle", "star", "square"],
        "colors": [v["accent"], "#FFFFFF", v["accent"]],
        "bgColor": v["bg"], "bpm": v["bpm"],
        "showLabels": False, "musicFile": v["music"],
    }
    out_mp4 = QUEUE_EN / f"dfg_{vid_num}_{DATE_STR}.mp4"

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
            meta = make_meta(vid_num, lg)
            if not dry_run:
                with open(mp, 'w', encoding='utf-8') as f:
                    yaml.dump(meta, f, allow_unicode=True)
            print(f"  Meta ({lg}): {mp.name}")

    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--key',        default=None, help='orchestrator key e.g. fruits_veg_group_8')
    parser.add_argument('--video',      default=None, choices=list(VIDEOS))
    parser.add_argument('--dry-run',    action='store_true')
    parser.add_argument('--regen-meta', action='store_true')
    args = parser.parse_args()

    videos = [args.video] if args.video else list(VIDEOS)
    print(f"=== Fruits & Vegetables Group Dance — {len(videos)} videos ===")

    done = 0
    for vid_num in videos:
        v = VIDEOS[vid_num]
        items_str = ", ".join(v['items_en'])
        print(f"\n[Video {vid_num}] {v['name_en']} | {items_str}")
        if process_video(vid_num, args.dry_run, args.regen_meta):
            done += 1

    print(f"\n=== Done: {done}/{len(videos)} ===")


if __name__ == '__main__':
    main()
