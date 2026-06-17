#!/usr/bin/env python3
"""
Generate Special Mechanics series — 8 episodes × A+B = 16 videos.
Scenario: config/scenarios/special_mechanics_special_mech_8series.txt

Series 7:  Hide & Seek (HIDE-A no words, HIDE-B EN+AR)
Series 8:  Shadows (SHADOW-A, SHADOW-B)
Series 9:  Bubbles (BUBBLE-A, BUBBLE-B)
Series 10: Reflections (REFLECT-A, REFLECT-B)
Series 11: Silent Count (COUNT-A only — no B version)
Series 12: Birthday (BDAY-A, BDAY-B)
Series 13: Mirror Dance (MIRROR-A, MIRROR-B)
Series 14: Sleep Time (SLEEP-A only — calming, no B)

A = no words → EN+AR+ID queues
B = educational EN+AR → EN+AR queues

Usage:
  python3 scripts/generate_special_mechanics.py --key special_mech_8series  # all 16 videos
  python3 scripts/generate_special_mechanics.py --episode hide_seek          # single episode
  python3 scripts/generate_special_mechanics.py --dry-run
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

# 8 episodes. has_b=False means only A version is produced.
EPISODES = {
    "hide_seek": {
        "name_en": "Hide and Seek",       "name_ar": "الغميضة",            "name_id": "Petak Umpet",
        "bg": "#0A1010", "accent": "#66BB6A", "bpm": 75,  "music": "Quirky Dog.mp3",   "has_b": True,
        "b_tag_en": "Hide and Seek",      "b_tag_ar": "الغميضة",
        "b_key_en": "Behind! Under! Inside! On top!",
        "b_key_ar": "خلف! تحت! داخل! فوق!",
    },
    "shadows": {
        "name_en": "Shadows",             "name_ar": "الظلال",             "name_id": "Bayangan",
        "bg": "#050505", "accent": "#B0BEC5", "bpm": 65,  "music": "Crinoline Dreams.mp3", "has_b": True,
        "b_tag_en": "Shadow",             "b_tag_ar": "ظل",
        "b_key_en": "Dark! Big shadow! Small shadow!",
        "b_key_ar": "داكن! ظل كبير! ظل صغير!",
    },
    "bubbles": {
        "name_en": "Bubbles",             "name_ar": "فقاعات",             "name_id": "Gelembung",
        "bg": "#030814", "accent": "#80DEEA", "bpm": 62,  "music": "Wholesome.mp3",    "has_b": True,
        "b_tag_en": "Bubble",             "b_tag_ar": "فقاعة",
        "b_key_en": "Big bubble! Small bubble! POP!",
        "b_key_ar": "فقاعة كبيرة! فقاعة صغيرة! بوب!",
    },
    "reflections": {
        "name_en": "Reflections",         "name_ar": "انعكاسات",           "name_id": "Pantulan",
        "bg": "#020A10", "accent": "#4FC3F7", "bpm": 60,  "music": "Gymnopedie No 1.mp3", "has_b": True,
        "b_tag_en": "Reflection",         "b_tag_ar": "انعكاس",
        "b_key_en": "Look in the mirror! Same but backwards!",
        "b_key_ar": "انظر في المرآة! نفسه ولكن معكوس!",
    },
    "counting": {
        "name_en": "Silent Count",        "name_ar": "العد الصامت",        "name_id": "Hitung Diam",
        "bg": "#0A0A05", "accent": "#FFF176", "bpm": 70,  "music": "Carefree.mp3",     "has_b": False,
    },
    "birthday": {
        "name_en": "Birthday Party",      "name_ar": "حفلة عيد الميلاد",  "name_id": "Pesta Ulang Tahun",
        "bg": "#0A0510", "accent": "#FF4081", "bpm": 88,  "music": "Happy Happy Game Show.mp3", "has_b": True,
        "b_tag_en": "Birthday",           "b_tag_ar": "عيد الميلاد",
        "b_key_en": "Happy Birthday! One candle! Two candles!",
        "b_key_ar": "عيد ميلاد سعيد! شمعة واحدة! شمعتان!",
    },
    "mirror_dance": {
        "name_en": "Mirror Dance",        "name_ar": "رقصة المرآة",        "name_id": "Tari Cermin",
        "bg": "#050508", "accent": "#CE93D8", "bpm": 80,  "music": "Pinball Spring.mp3", "has_b": True,
        "b_tag_en": "Mirror",             "b_tag_ar": "مرآة",
        "b_key_en": "Copy me! Same as me! Mirror mirror!",
        "b_key_ar": "انسخني! مثلي تماماً! مرآة مرآة!",
    },
    "sleep_time": {
        "name_en": "Sleep Time",          "name_ar": "وقت النوم",          "name_id": "Waktu Tidur",
        "bg": "#010208", "accent": "#7986CB", "bpm": 45,  "music": "Gymnopedie No 1.mp3", "has_b": False,
    },
}


def make_meta_a(ep_key, lang):
    ep  = EPISODES[ep_key]
    ch  = {'en': '@HappyBearKids1', 'ar': '@happybearkidsar', 'id': '@happybearkidsin'}
    name = ep[f'name_{lang}']

    if lang == 'en':
        return {
            "title": f"{name} | 25 Min Baby Animation | Happy Bear Kids",
            "description": (
                f"✨ {name} — mesmerizing animation for babies and toddlers!\n\n"
                f"Pure visual experience — no words, no text, just beautiful visuals "
                f"and gentle music designed for young viewers.\n\n"
                f"Part of our Special Mechanics series — exploring fascinating visual concepts "
                f"through animation that babies and toddlers find captivating.\n\n"
                f"🎯 Perfect for: visual stimulation, background play, calming screen time\n"
                f"👶 Age: 0–3 years | 📺 25 minutes continuous\n"
                f"🌈 No language barriers — universal for any culture\n\n"
                f"🔔 Subscribe → {ch['en']}\n"
                f"🎵 Kevin MacLeod (incompetech.com) — CC Attribution 4.0\n\n"
                f"#{name.replace(' ','')} #HappyBearKids #BabyAnimation "
                f"#SpecialMechanics #VisualStimulation\n© Happy Bear Kids 2026"
            ),
            "tags": [ep_key.replace('_',' '), name.lower(), "baby animation", "happy bear kids",
                     "special mechanics", "visual stimulation", "no talking", "25 minutes"],
            "video_type": "special_mechanics", "language": "en", "is_short": False, "status": "public",
        }
    elif lang == 'ar':
        return {
            "title": f"{name} | رسوم متحركة للرضع 25 دقيقة | هابي بير كيدز",
            "description": (
                f"✨ {name} — رسوم متحركة رائعة للرضع والأطفال الصغار!\n\n"
                f"تجربة بصرية خالصة — بدون كلمات أو نصوص، فقط مرئيات جميلة "
                f"وموسيقى هادئة مصممة للمشاهدين الصغار.\n\n"
                f"جزء من سلسلة الميكانيكا الخاصة — استكشاف مفاهيم بصرية رائعة "
                f"من خلال الرسوم المتحركة التي يجدها الرضع والأطفال الصغار آسرة.\n\n"
                f"🔔 اشتركوا → {ch['ar']}\n"
                f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
                f"#{name.replace(' ','_')} #هابي_بير_كيدز #رسوم_أطفال "
                f"#تحفيز_بصري\n© هابي بير كيدز 2026"
            ),
            "tags": [ep_key.replace('_',' '), name, "هابي بير كيدز", "رسوم مجردة", "بدون كلام"],
            "video_type": "special_mechanics", "language": "ar", "is_short": False, "status": "public",
        }
    else:
        return {
            "title": f"{name} | 25 Menit Animasi Bayi | Happy Bear Kids",
            "description": (
                f"✨ {name} — animasi memukau untuk bayi dan balita!\n\n"
                f"Pengalaman visual murni — tanpa kata-kata atau teks, hanya visual indah "
                f"dan musik lembut yang dirancang untuk penonton kecil.\n\n"
                f"Bagian dari seri Mekanika Khusus — menjelajahi konsep visual yang menakjubkan "
                f"melalui animasi yang memikat bayi dan balita.\n\n"
                f"🔔 Subscribe → {ch['id']}\n"
                f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
                f"#{name.replace(' ','')} #HappyBearKids #AnimasiAnak "
                f"#StimulasiVisual\n© Happy Bear Kids Indonesia 2026"
            ),
            "tags": [ep_key.replace('_',' '), name.lower(), "animasi bayi", "happy bear kids",
                     "stimulasi visual", "tanpa suara"],
            "video_type": "special_mechanics", "language": "id", "is_short": False, "status": "public",
        }


def make_meta_b(ep_key, lang):
    ep       = EPISODES[ep_key]
    ch       = {'en': '@HappyBearKids1', 'ar': '@happybearkidsar', 'id': '@happybearkidsin'}
    name_en  = ep['name_en']
    name_ar  = ep['name_ar']
    name_id  = ep['name_id']
    name     = ep[f'name_{lang}']
    tag_en   = ep.get('b_tag_en', name_en)
    tag_ar   = ep.get('b_tag_ar', name_ar)
    keys_en  = ep.get('b_key_en', '')
    keys_ar  = ep.get('b_key_ar', '')

    if lang == 'en':
        return {
            "title": f"Learn: {tag_en}! Educational Baby Video | Happy Bear Kids",
            "description": (
                f"🎓 Learn about {tag_en}! Educational bilingual video for babies 0-3 years.\n\n"
                f"In this video: {keys_en}\n\n"
                f"Bilingual English-Arabic content to help babies in both language communities. "
                f"Simple vocabulary repeated with visual reinforcement.\n\n"
                f"📌 Key phrases: English + Arabic ({tag_ar})\n"
                f"Interactive pauses let babies respond before answers appear.\n\n"
                f"Perfect for: language learning, cognitive development, bilingual education.\n"
                f"👶 Age: 0–3 years | 📺 25 minutes\n\n"
                f"🔔 Subscribe → {ch['en']}\n"
                f"🎵 Kevin MacLeod (incompetech.com) — CC Attribution 4.0\n\n"
                f"#Learn{tag_en.replace(' ','')} #HappyBearKids #BilingualBaby "
                f"#BabyEducation\n© Happy Bear Kids 2026"
            ),
            "tags": [ep_key.replace('_',' '), f"learn {tag_en.lower()}", "bilingual baby",
                     "educational", "happy bear kids", "english arabic"],
            "video_type": "special_mechanics", "language": "en", "is_short": False, "status": "public",
        }
    elif lang == 'ar':
        return {
            "title": f"تعلم: {tag_ar}! فيديو تعليمي للرضع | هابي بير كيدز",
            "description": (
                f"🎓 تعلم عن {tag_ar}! فيديو تعليمي ثنائي اللغة للرضع 0-3 سنوات.\n\n"
                f"في هذا الفيديو: {keys_ar}\n\n"
                f"محتوى ثنائي اللغة عربي-إنجليزي لمساعدة الرضع في مجتمعات اللغتين. "
                f"مفردات بسيطة مكررة مع تعزيز بصري.\n\n"
                f"🔔 اشتركوا → {ch['ar']}\n"
                f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
                f"#تعلم_{tag_ar.replace(' ','_')} #هابي_بير_كيدز #تعليم_الرضع "
                f"#ثنائي_اللغة\n© هابي بير كيدز 2026"
            ),
            "tags": [ep_key.replace('_',' '), tag_ar, "تعليم الرضع", "هابي بير كيدز", "ثنائي اللغة"],
            "video_type": "special_mechanics", "language": "ar", "is_short": False, "status": "public",
        }
    else:  # id
        return {
            "title": f"Belajar: {name_id}! Video Edukasi Bayi | Happy Bear Kids",
            "description": (
                f"🎓 Belajar tentang {name_id}! Video edukasi untuk bayi 0-3 tahun.\n\n"
                f"Dalam video ini: {keys_en}\n\n"
                f"Konten edukatif dalam Bahasa Indonesia, Inggris ({tag_en}), dan Arab ({tag_ar}). "
                f"Kosakata sederhana diulang dengan penguatan visual.\n\n"
                f"📌 Jeda interaktif memberi bayi waktu untuk merespons sebelum jawaban muncul.\n\n"
                f"Sempurna untuk: pembelajaran bahasa, perkembangan kognitif, pendidikan anak.\n"
                f"👶 Usia: 0–3 tahun | 📺 25 menit\n\n"
                f"🔔 Subscribe → {ch['id']}\n"
                f"🎵 Kevin MacLeod (incompetech.com) — CC Attribution 4.0\n\n"
                f"#Belajar{name_id.replace(' ','')} #HappyBearKids #BayiPintar "
                f"#PendidikanBayi\n© Happy Bear Kids Indonesia 2026"
            ),
            "tags": [ep_key.replace('_',' '), f"belajar {name_id.lower()}", "bayi pintar",
                     "pendidikan bayi", "happy bear kids", "bahasa indonesia"],
            "video_type": "special_mechanics", "language": "id", "is_short": False, "status": "public",
        }


def process_a(ep_key, dry_run, regen_meta):
    ep     = EPISODES[ep_key]
    queues = {'en': QUEUE_EN, 'ar': QUEUE_AR, 'id': QUEUE_ID}
    props  = {
        "shapes": ["circle", "star", "square"],
        "colors": [ep["accent"], "#FFFFFF", ep["accent"]],
        "bgColor": ep["bg"], "bpm": ep["bpm"],
        "showLabels": False, "musicFile": ep["music"],
    }
    out_mp4 = QUEUE_EN / f"sm_{ep_key}_a_{DATE_STR}.mp4"

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
            meta = make_meta_a(ep_key, lg)
            if not dry_run:
                with open(mp, 'w', encoding='utf-8') as f:
                    yaml.dump(meta, f, allow_unicode=True)
            print(f"  Meta A ({lg}): {mp.name}")

    return True


def process_b(ep_key, dry_run, regen_meta):
    ep     = EPISODES[ep_key]
    props  = {
        "shapes": ["circle", "star"],
        "colors": [ep["accent"], "#FFFFFF"],
        "bgColor": ep["bg"], "bpm": ep["bpm"],
        "showLabels": False, "musicFile": ep["music"],
    }
    out_mp4 = QUEUE_EN / f"sm_{ep_key}_b_{DATE_STR}.mp4"

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
            dest = {'ar': QUEUE_AR, 'id': QUEUE_ID}[lg] / out_mp4.name
            if not dest.exists():
                shutil.copy2(str(out_mp4), str(dest))

    for lg, q in [('en', QUEUE_EN), ('ar', QUEUE_AR), ('id', QUEUE_ID)]:
        mp = q / f"meta_{out_mp4.stem}.yaml"
        if not mp.exists() or regen_meta:
            meta = make_meta_b(ep_key, lg)
            if not dry_run:
                with open(mp, 'w', encoding='utf-8') as f:
                    yaml.dump(meta, f, allow_unicode=True)
            print(f"  Meta B ({lg}): {mp.name}")

    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--key',        default=None, help='orchestrator key e.g. special_mech_8series')
    parser.add_argument('--episode',    default=None, choices=list(EPISODES))
    parser.add_argument('--type',       default='both', choices=['A', 'B', 'both'])
    parser.add_argument('--dry-run',    action='store_true')
    parser.add_argument('--regen-meta', action='store_true')
    args = parser.parse_args()

    episodes = [args.episode] if args.episode else list(EPISODES)
    run_a = args.type in ('A', 'both')
    run_b = args.type in ('B', 'both')

    total = sum(1 + (1 if EPISODES[e]['has_b'] else 0) for e in episodes
                if (run_a or (run_b and EPISODES[e]['has_b'])))
    print(f"=== Special Mechanics — {len(episodes)} episodes ===")

    done = 0
    for ep_key in episodes:
        ep = EPISODES[ep_key]
        print(f"\n[{ep_key.upper()}] {ep['name_en']}")
        if run_a and process_a(ep_key, args.dry_run, args.regen_meta):
            done += 1
        if run_b and ep['has_b'] and process_b(ep_key, args.dry_run, args.regen_meta):
            done += 1

    print(f"\n=== Done: {done} videos ===")


if __name__ == '__main__':
    main()
