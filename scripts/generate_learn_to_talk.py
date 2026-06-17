#!/usr/bin/env python3
"""
Generate Learn to Talk series — 10 videos × 3 languages = 30 meta files.
Scenario: config/scenarios/learn_to_talk_learn_to_talk_series.txt

Style: Ms Rachel — speech development for 6 months to 2 years.
Each video covers 3-4 first words with slow articulation, pauses, repetition.

Videos are language-specific (future TTS per language).
For now: render once, copy to all 3 queues, separate meta per language.

Usage:
  python3 scripts/generate_learn_to_talk.py               # all 10 videos
  python3 scripts/generate_learn_to_talk.py --video 1     # single video
  python3 scripts/generate_learn_to_talk.py --dry-run
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

# 10 videos, each with 2-3 words and trilingual titles
VIDEOS = {
    "1":  {
        "words_en": ["Mama", "Papa"],
        "words_ar": ["ماما", "بابا"],
        "words_id": ["Mama", "Papa"],
        "name_en": "Mama and Papa",          "name_ar": "ماما وبابا",          "name_id": "Mama dan Papa",
        "bg": "#0A0808", "accent": "#FF8FAB", "bpm": 55, "music": "Heartwarming.mp3",
    },
    "2":  {
        "words_en": ["Ball", "Up"],
        "words_ar": ["كرة", "أعلى"],
        "words_id": ["Bola", "Atas"],
        "name_en": "Ball and Up",            "name_ar": "كرة وأعلى",           "name_id": "Bola dan Atas",
        "bg": "#050A0F", "accent": "#64B5F6", "bpm": 65, "music": "Carefree.mp3",
    },
    "3":  {
        "words_en": ["More", "All Done"],
        "words_ar": ["أكثر", "انتهى"],
        "words_id": ["Lagi", "Selesai"],
        "name_en": "More and All Done",      "name_ar": "أكثر وانتهى",         "name_id": "Lagi dan Selesai",
        "bg": "#0A0A05", "accent": "#FFCC02", "bpm": 60, "music": "Wholesome.mp3",
    },
    "4":  {
        "words_en": ["Dog", "Cat"],
        "words_ar": ["كلب", "قطة"],
        "words_id": ["Anjing", "Kucing"],
        "name_en": "Dog and Cat",            "name_ar": "كلب وقطة",            "name_id": "Anjing dan Kucing",
        "bg": "#0A0500", "accent": "#FF8C42", "bpm": 72, "music": "Quirky Dog.mp3",
    },
    "5":  {
        "words_en": ["Hi", "Bye-Bye"],
        "words_ar": ["مرحبا", "وداعاً"],
        "words_id": ["Halo", "Dadah"],
        "name_en": "Hi and Bye-Bye",         "name_ar": "مرحبا ووداعاً",       "name_id": "Halo dan Dadah",
        "bg": "#050A0A", "accent": "#80CBC4", "bpm": 68, "music": "Merry Go.mp3",
    },
    "6":  {
        "words_en": ["Milk", "Water"],
        "words_ar": ["حليب", "ماء"],
        "words_id": ["Susu", "Air"],
        "name_en": "Milk and Water",         "name_ar": "حليب وماء",           "name_id": "Susu dan Air",
        "bg": "#050810", "accent": "#90CAF9", "bpm": 58, "music": "Gymnopedie No 1.mp3",
    },
    "7":  {
        "words_en": ["Open", "Help"],
        "words_ar": ["افتح", "مساعدة"],
        "words_id": ["Buka", "Tolong"],
        "name_en": "Open and Help",          "name_ar": "افتح ومساعدة",        "name_id": "Buka dan Tolong",
        "bg": "#0A0808", "accent": "#A5D6A7", "bpm": 62, "music": "Crinoline Dreams.mp3",
    },
    "8":  {
        "words_en": ["Yes", "No"],
        "words_ar": ["نعم", "لا"],
        "words_id": ["Ya", "Tidak"],
        "name_en": "Yes and No",             "name_ar": "نعم ولا",             "name_id": "Ya dan Tidak",
        "bg": "#0A0510", "accent": "#CE93D8", "bpm": 65, "music": "Wholesome.mp3",
    },
    "9":  {
        "words_en": ["Book", "Baby"],
        "words_ar": ["كتاب", "طفل"],
        "words_id": ["Buku", "Bayi"],
        "name_en": "Book and Baby",          "name_ar": "كتاب وطفل",           "name_id": "Buku dan Bayi",
        "bg": "#08080A", "accent": "#BCAAA4", "bpm": 58, "music": "Heartwarming.mp3",
    },
    "10": {
        "words_en": ["Go", "Stop"],
        "words_ar": ["اذهب", "قف"],
        "words_id": ["Pergi", "Berhenti"],
        "name_en": "Go and Stop",            "name_ar": "اذهب وقف",            "name_id": "Pergi dan Berhenti",
        "bg": "#050A05", "accent": "#C5E1A5", "bpm": 80, "music": "Happy Happy Game Show.mp3",
    },
}


def make_meta(vid_num, lang):
    v    = VIDEOS[vid_num]
    ch   = {'en': '@HappyBearKids1', 'ar': '@happybearkidsar', 'id': '@happybearkidsin'}
    name = v[f'name_{lang}']
    words = " • ".join(v[f'words_{lang}'])

    if lang == 'en':
        word_list = ", ".join(f'"{w}"' for w in v['words_en'])
        return {
            "title": f"Learn to Talk: {name} | Baby Speech | Happy Bear Kids",
            "description": (
                f"🗣️ Learn to Talk — {name}!\n\n"
                f"Help your baby say their first words: {words}\n\n"
                f"Inspired by speech development research (Ms Rachel style):\n"
                f"• SLOW articulation — mouth close-up for babies to see how words are formed\n"
                f"• PAUSE — 4 seconds after each word for baby to respond\n"
                f"• REPEAT — each word said 8-12 times in different contexts\n"
                f"• CELEBRATION — any sound from baby is success!\n\n"
                f"Video {vid_num} of 10 — teaching first words: {word_list}\n\n"
                f"Perfect for: language development, speech delay support, early literacy.\n"
                f"👶 Age: 6 months – 2 years | 📺 20 minutes\n\n"
                f"🔔 Subscribe → {ch['en']}\n"
                f"🎵 Kevin MacLeod (incompetech.com) — CC Attribution 4.0\n\n"
                f"#LearnToTalk #HappyBearKids #BabySpeech "
                f"#FirstWords #SpeechDevelopment #Baby\n© Happy Bear Kids 2026"
            ),
            "tags": ["learn to talk", name.lower()] + [w.lower() for w in v['words_en']] +
                    ["speech development", "happy bear kids", "first words", "baby learning"],
            "video_type": "learn_to_talk", "language": "en", "is_short": False, "status": "public",
        }
    elif lang == 'ar':
        return {
            "title": f"تعلم الكلام: {name} | كلام الرضع | هابي بير كيدز",
            "description": (
                f"🗣️ تعلم الكلام — {name}!\n\n"
                f"ساعد طفلك على قول أول كلماته: {words}\n\n"
                f"مستوحى من أبحاث تطوير الكلام:\n"
                f"• نطق بطيء — لقطة مقربة للفم ليرى الطفل كيف تُشكَّل الكلمات\n"
                f"• توقف — 4 ثوانٍ بعد كل كلمة حتى يستجيب الطفل\n"
                f"• تكرار — كل كلمة تُقال 8-12 مرة في سياقات مختلفة\n\n"
                f"فيديو {vid_num} من 10 — تعليم الكلمات الأولى\n\n"
                f"🔔 اشتركوا → {ch['ar']}\n"
                f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
                f"#تعلم_الكلام #هابي_بير_كيدز #كلام_الرضع "
                f"#أولى_الكلمات\n© هابي بير كيدز 2026"
            ),
            "tags": ["تعلم الكلام", name] + v['words_ar'] +
                    ["هابي بير كيدز", "كلام الرضع", "أولى الكلمات"],
            "video_type": "learn_to_talk", "language": "ar", "is_short": False, "status": "public",
        }
    else:
        return {
            "title": f"Belajar Bicara: {name} | Bicara Bayi | Happy Bear Kids",
            "description": (
                f"🗣️ Belajar Bicara — {name}!\n\n"
                f"Bantu bayi Anda mengucapkan kata-kata pertamanya: {words}\n\n"
                f"Terinspirasi dari penelitian pengembangan bicara:\n"
                f"• Artikulasi LAMBAT — close-up mulut agar bayi melihat cara kata dibentuk\n"
                f"• JEDA — 4 detik setelah setiap kata agar bayi bisa merespons\n"
                f"• ULANGAN — setiap kata diucapkan 8-12 kali dalam konteks berbeda\n\n"
                f"Video {vid_num} dari 10 — mengajarkan kata-kata pertama\n\n"
                f"🔔 Subscribe → {ch['id']}\n"
                f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
                f"#BelajarBicara #HappyBearKids #BayiBicara "
                f"#KataKataAwal\n© Happy Bear Kids Indonesia 2026"
            ),
            "tags": ["belajar bicara", name.lower()] + [w.lower() for w in v['words_id']] +
                    ["happy bear kids", "bicara bayi", "kata pertama"],
            "video_type": "learn_to_talk", "language": "id", "is_short": False, "status": "public",
        }


def process_video(vid_num, dry_run, regen_meta):
    v      = VIDEOS[vid_num]
    queues = {'en': QUEUE_EN, 'ar': QUEUE_AR, 'id': QUEUE_ID}
    props  = {
        "shapes": ["circle", "star"],
        "colors": [v["accent"], "#FFFFFF"],
        "bgColor": v["bg"], "bpm": v["bpm"],
        "showLabels": False, "musicFile": v["music"],
    }
    out_mp4 = QUEUE_EN / f"ltt_{vid_num:0>2}_{v['name_en'].replace(' ','_').lower()}_{DATE_STR}.mp4"

    if not out_mp4.exists() and not dry_run and not regen_meta:
        cmd = ["npx", "remotion", "render", "NurseryRhymeLong",
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
    parser.add_argument('--key',        default=None, help='orchestrator key e.g. learn_to_talk_series')
    parser.add_argument('--video',      default=None, choices=list(VIDEOS))
    parser.add_argument('--dry-run',    action='store_true')
    parser.add_argument('--regen-meta', action='store_true')
    args = parser.parse_args()

    videos = [args.video] if args.video else list(VIDEOS)
    print(f"=== Learn to Talk — {len(videos)} videos ===")

    done = 0
    for vid_num in videos:
        v = VIDEOS[vid_num]
        print(f"\n[Video {vid_num}] {v['name_en']} | Words: {', '.join(v['words_en'])}")
        if process_video(vid_num, args.dry_run, args.regen_meta):
            done += 1

    print(f"\n=== Done: {done}/{len(videos)} ===")


if __name__ == '__main__':
    main()
