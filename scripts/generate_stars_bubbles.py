#!/usr/bin/env python3
"""
Generate Stars and Bubbles video — 1 video, ~22 min.
Scenario: config/scenarios/stars_bubbles_stars_bubbles.txt

Pure visual entertainment — bubbles pop, stars shoot across screen.
No words → EN+AR+ID queues.

Usage:
  python3 scripts/generate_stars_bubbles.py
  python3 scripts/generate_stars_bubbles.py --dry-run
  python3 scripts/generate_stars_bubbles.py --regen-meta
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

VIDEO = {
    "name_en": "Stars and Bubbles",
    "name_ar": "النجوم والفقاعات",
    "name_id": "Bintang dan Gelembung",
    "bg": "#010108", "accent": "#80DEEA", "bpm": 80,
    "music": "Crinoline Dreams.mp3",
}


def make_meta(lang):
    ch   = {'en': '@HappyBearKids1', 'ar': '@happybearkidsar', 'id': '@happybearkidsin'}
    name = VIDEO[f'name_{lang}']

    if lang == 'en':
        return {
            "title": f"{name} | 22 Min Sensory Video for Babies | Happy Bear Kids",
            "description": (
                f"✨ {name} — pure sensory delight for babies and toddlers!\n\n"
                f"Watch colorful bubbles float, grow, and POP — while stars twinkle and shoot "
                f"across a dark night sky. 22 minutes of calming visual stimulation!\n\n"
                f"🫧 Bubbles: grow slowly, pause at maximum size... then POP! "
                f"Satisfying anticipation and release — babies love it!\n"
                f"⭐ Stars: twinkle gently, then shoot across the screen with a light trail\n\n"
                f"No words, no text — pure visual and auditory experience.\n"
                f"Soft music box + synth soundtrack, BPM 80.\n\n"
                f"🎯 Perfect for: sensory stimulation, background play, calming time\n"
                f"👶 Age: 0–3 years | 📺 22 minutes continuous\n"
                f"🌈 Universal — no language barriers\n\n"
                f"🔔 Subscribe → {ch['en']}\n"
                f"🎵 Kevin MacLeod (incompetech.com) — CC Attribution 4.0\n\n"
                f"#StarsAndBubbles #HappyBearKids #SensoryVideo "
                f"#BabyVisual #BubblesPop #CalmBaby\n© Happy Bear Kids 2026"
            ),
            "tags": ["stars and bubbles", "sensory video", "baby visual", "bubbles pop",
                     "happy bear kids", "calming baby", "no talking", "22 minutes", "visual stimulation"],
            "video_type": "stars_bubbles", "language": "en", "is_short": False, "status": "public",
        }
    elif lang == 'ar':
        return {
            "title": f"{name} | فيديو حسي للرضع 22 دقيقة | هابي بير كيدز",
            "description": (
                f"✨ {name} — بهجة حسية خالصة للرضع والأطفال الصغار!\n\n"
                f"شاهد الفقاعات الملونة تطفو وتكبر وتنفجر — بينما تتلألأ النجوم "
                f"وتطير عبر سماء الليل المظلمة. 22 دقيقة من التحفيز البصري الهادئ!\n\n"
                f"🫧 فقاعات: تنمو ببطء، تتوقف في أقصى حجم... ثم بوب!\n"
                f"⭐ نجوم: تتلألأ بلطف، ثم تطير عبر الشاشة\n\n"
                f"بدون كلمات أو نصوص — تجربة بصرية وسمعية خالصة.\n\n"
                f"🔔 اشتركوا → {ch['ar']}\n"
                f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
                f"#النجوم_والفقاعات #هابي_بير_كيدز #فيديو_حسي "
                f"#تحفيز_بصري\n© هابي بير كيدز 2026"
            ),
            "tags": ["النجوم والفقاعات", "فيديو حسي", "هابي بير كيدز", "تحفيز بصري", "بدون كلام"],
            "video_type": "stars_bubbles", "language": "ar", "is_short": False, "status": "public",
        }
    else:
        return {
            "title": f"{name} | 22 Menit Video Sensorik untuk Bayi | Happy Bear Kids",
            "description": (
                f"✨ {name} — kesenangan sensorik murni untuk bayi dan balita!\n\n"
                f"Saksikan gelembung berwarna-warni mengapung, tumbuh, dan MELETUS — "
                f"sementara bintang-bintang berkelip dan meluncur melintasi langit malam yang gelap. "
                f"22 menit stimulasi visual yang menenangkan!\n\n"
                f"🫧 Gelembung: tumbuh perlahan, berhenti di ukuran maksimum... lalu POP!\n"
                f"⭐ Bintang: berkelip lembut, lalu meluncur melintasi layar\n\n"
                f"Tanpa kata-kata atau teks — pengalaman visual dan auditori murni.\n\n"
                f"🔔 Subscribe → {ch['id']}\n"
                f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
                f"#BintangDanGelembung #HappyBearKids #VideoSensorik "
                f"#StimulasiVisual\n© Happy Bear Kids Indonesia 2026"
            ),
            "tags": ["bintang dan gelembung", "video sensorik", "stimulasi visual",
                     "happy bear kids", "tanpa suara"],
            "video_type": "stars_bubbles", "language": "id", "is_short": False, "status": "public",
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--key',        default=None)
    parser.add_argument('--dry-run',    action='store_true')
    parser.add_argument('--regen-meta', action='store_true')
    args = parser.parse_args()

    queues = {'en': QUEUE_EN, 'ar': QUEUE_AR, 'id': QUEUE_ID}
    props  = {
        "shapes": ["circle", "star"],
        "colors": [VIDEO["accent"], "#FFFFFF", "#FFD700"],
        "bgColor": VIDEO["bg"], "bpm": VIDEO["bpm"],
        "showLabels": False, "musicFile": VIDEO["music"],
    }
    out_mp4 = QUEUE_EN / f"stars_bubbles_{DATE_STR}.mp4"
    print(f"=== Stars and Bubbles — 1 video ===")

    if not out_mp4.exists() and not args.dry_run and not args.regen_meta:
        cmd = ["npx", "remotion", "render", "ShapeDanceLong",
               f"--props={json.dumps(props)}", f"--output={str(out_mp4)}"]
        print(f"  Render: {out_mp4.name}")
        r = subprocess.run(cmd, cwd=str(REMOTION), timeout=21600)
        if r.returncode != 0:
            print("  FAILED")
            return

    if out_mp4.exists() and not args.dry_run:
        for lg in ['ar', 'id']:
            dest = queues[lg] / out_mp4.name
            if not dest.exists():
                shutil.copy2(str(out_mp4), str(dest))

    for lg, q in queues.items():
        mp = q / f"meta_{out_mp4.stem}.yaml"
        if not mp.exists() or args.regen_meta:
            meta = make_meta(lg)
            if not args.dry_run:
                with open(mp, 'w', encoding='utf-8') as f:
                    yaml.dump(meta, f, allow_unicode=True)
            print(f"  Meta ({lg}): {mp.name}")

    print("=== Done ===")


if __name__ == '__main__':
    main()
