#!/usr/bin/env python3
"""
Generate Satisfying Loops series — 8 hypnotic shape-loop videos, 30 min, no text.
ShapeDanceLong with varied speeds and monochrome/gradient palettes. No text → EN+AR+ID.

Usage:
  python3 scripts/generate_satisfying_3fmt.py --key satisfying_guess_surprise
  python3 scripts/generate_satisfying_3fmt.py --regen-meta
"""
import argparse, base64, json, subprocess, yaml
from datetime import datetime
from pathlib import Path
import requests

ROOT     = Path(__file__).resolve().parent.parent
REMOTION = ROOT / "remotion"
QUEUE_EN = ROOT / "output" / "queue"
QUEUE_AR = ROOT / "output" / "queue_ar"
QUEUE_ID = ROOT / "output" / "queue_id"
TOGETHER_KEY_FILE = ROOT / "credentials" / "together_api_key.txt"
TOGETHER_URL      = "https://api.together.xyz/v1/images/generations"
DATE_STR = datetime.now().strftime("%Y%m%d")

_ALL_TRACKS = [
    "Carefree.mp3", "Crinoline Dreams.mp3", "Gymnopedie No 1.mp3",
    "Happy Happy Game Show.mp3", "Heartwarming.mp3", "Hyperfun.mp3",
    "Life of Riley.mp3", "Merry Go.mp3", "Monkeys Spinning Monkeys.mp3",
    "Overworld.mp3", "Pinball Spring.mp3", "Pixelland.mp3",
    "Quirky Dog.mp3", "Salty Ditty.mp3", "Sneaky Snitch.mp3",
    "Wholesome.mp3", "Fluffing a Duck.mp3", "Walking Along.mp3",
    "George Street Shuffle.mp3", "Circus of Freaks.mp3",
]

def alt_music(en_music: str, ep_idx: int, lang: str) -> str:
    if lang == "en":
        return en_music
    offset = 7 if lang == "ar" else 14
    pool = [t for t in _ALL_TRACKS if t != en_music]
    return pool[(ep_idx + offset) % len(pool)]

EPISODES = {
    "slow_circles": {
        "shapes": ["circle"],
        "colors": ["#FF4444", "#FF8C00", "#FFD700", "#44BB44"],
        "bgColor": "#050505", "bpm": 30, "music": "Gymnopedie No 1.mp3",
        "thumb_prompt": "satisfying slow expanding colorful circles on black background, hypnotic, mesmerizing, calming kids video",
    },
    "rainbow_drift": {
        "shapes": ["circle", "oval", "heart"],
        "colors": ["#FF0000", "#FF7F00", "#FFFF00", "#00FF00", "#0000FF", "#8B00FF"],
        "bgColor": "#020202", "bpm": 45, "music": "Carefree.mp3",
        "thumb_prompt": "rainbow colored circles drifting slowly on dark background, satisfying visual, kids hypnotic video",
    },
    "geometric_pulse": {
        "shapes": ["hexagon", "diamond", "triangle"],
        "colors": ["#00FFFF", "#00CCFF", "#0099FF", "#0066FF"],
        "bgColor": "#000A14", "bpm": 60, "music": "Heartwarming.mp3",
        "thumb_prompt": "geometric hexagons diamonds pulsing in blue gradient, satisfying loop animation, dark background",
    },
    "golden_spin": {
        "shapes": ["circle", "star", "diamond"],
        "colors": ["#FFD700", "#FFC200", "#FFE066", "#FFAA00"],
        "bgColor": "#060400", "bpm": 55, "music": "Wholesome.mp3",
        "thumb_prompt": "golden stars circles spinning slowly on dark background, satisfying golden glow, hypnotic kids animation",
    },
    "pastel_float": {
        "shapes": ["circle", "oval", "heart"],
        "colors": ["#FFB3BA", "#FFDFBA", "#FFFFBA", "#BAFFC9", "#BAE1FF"],
        "bgColor": "#050509", "bpm": 40, "music": "Crinoline Dreams.mp3",
        "thumb_prompt": "soft pastel circles hearts ovals floating gently, baby pink blue yellow, soothing satisfying animation",
    },
    "neon_bounce": {
        "shapes": ["circle", "square", "triangle"],
        "colors": ["#FF00FF", "#00FF00", "#00FFFF", "#FF4500"],
        "bgColor": "#010101", "bpm": 80, "music": "Quirky Dog.mp3",
        "thumb_prompt": "neon glowing shapes bouncing satisfyingly on black background, bright magenta green cyan, mesmerizing",
    },
    "monochrome_zen": {
        "shapes": ["circle", "oval"],
        "colors": ["#FFFFFF", "#CCCCCC", "#999999", "#666666"],
        "bgColor": "#000000", "bpm": 35, "music": "Life of Riley.mp3",
        "thumb_prompt": "minimalist white grey circles on pure black background, zen calming satisfying loop, babies meditation",
    },
    "fire_dance": {
        "shapes": ["circle", "heart", "star"],
        "colors": ["#FF4500", "#FF6347", "#FF7F50", "#FFD700"],
        "bgColor": "#080200", "bpm": 70, "music": "Merry Go.mp3",
        "thumb_prompt": "warm fire orange red golden circles stars dancing hypnotically, satisfying loop, dark background kids",
    },
}

TITLES = {
    "en": "✨ Satisfying Shapes Loop | 30 Minutes | Happy Bear Kids",
    "ar": "✨ حلقة الأشكال المُرضية | ٣٠ دقيقة | Happy Bear Kids",
    "id": "✨ Loop Bentuk yang Memuaskan | 30 Menit | Happy Bear Kids",
}

DESC = {
    "en": (
        "Welcome to Happy Bear Kids! 🐻\n\n"
        "30 minutes of wonderfully satisfying, hypnotic shape loops designed to captivate and "
        "calm babies, toddlers and young children. Watch as beautiful shapes pulse, drift and "
        "dance in perfectly satisfying rhythmic patterns — impossible to look away!\n\n"
        "Our Satisfying Shapes series is inspired by the ASMR and satisfying-video trend, "
        "adapted perfectly for the youngest viewers. Simple, beautiful, endlessly watchable.\n\n"
        "🌟 Key features:\n"
        "• Hypnotic, looping shape animations in beautiful colour combinations\n"
        "• Carefully chosen music tempo matched to each visual style\n"
        "• No sudden changes — smooth, satisfying transitions throughout\n"
        "• No words or text — perfect for all languages and cultures\n"
        "• 30 uninterrupted minutes of pure visual satisfaction\n\n"
        "👶 Perfect for:\n"
        "• Babies aged 0-12 months — visual tracking and colour stimulation\n"
        "• Toddlers who love patterns, shapes and repeating motions\n"
        "• Background for calm play or eating time\n"
        "• Winding down before sleep — the slow versions especially\n"
        "• Parents who need 30 minutes of peaceful baby entertainment\n\n"
        "🎯 Educational value:\n"
        "• Shape recognition — circles, stars, hexagons, hearts and more\n"
        "• Colour recognition and colour combinations\n"
        "• Pattern and symmetry awareness\n"
        "• Attention focus and visual tracking development\n"
        "• Rhythm and timing through perfectly matched music\n\n"
        "No talking, no surprises, no ads — just pure satisfying shape loops that babies "
        "and toddlers absolutely love!\n\n"
        "🎵 Music by Kevin MacLeod (incompetech.com)\n"
        "Licensed under Creative Commons: By Attribution 4.0 License\n"
        "http://creativecommons.org/licenses/by/4.0/\n\n"
        "© Happy Bear Kids 2026 — All rights reserved\n"
        "New videos every week! Subscribe ▶ @HappyBearKids1\n\n"
        "#HappyBearKids #SatisfyingShapes #BabyShapes #HypnoticShapes "
        "#SatisfyingVideo #KidsRelax #30Minutes #BabyCalm #ShapeLoop"
    ),
    "ar": (
        "أهلاً بكم في Happy Bear Kids! 🐻\n\n"
        "٣٠ دقيقة من حلقات الأشكال الساحرة والمُرضية المصممة لجذب انتباه الأطفال وتهدئتهم. "
        "شاهد الأشكال الجميلة تنبض وتطفو وترقص في أنماط إيقاعية مُرضية تماماً.\n\n"
        "🌟 المميزات:\n"
        "• رسوم متحركة حلقية ساحرة بمجموعات ألوان جميلة\n"
        "• موسيقى مختارة بعناية تتوافق مع كل نمط بصري\n"
        "• بدون كلمات أو أصوات مفاجئة\n"
        "• ٣٠ دقيقة كاملة من الإرضاء البصري\n\n"
        "🎵 موسيقى Kevin MacLeod — Creative Commons 4.0\n"
        "© Happy Bear Kids 2026 | @happybearkidsar\n"
        "#HappyBearKids #أشكال_مُرضية #تهدئة_الطفل #فيديو_أطفال"
    ),
    "id": (
        "Selamat datang di Happy Bear Kids! 🐻\n\n"
        "30 menit loop bentuk yang sangat memuaskan dan hipnotis, dirancang untuk memikat "
        "dan menenangkan bayi, balita, dan anak kecil. Saksikan bentuk-bentuk indah berdenyut, "
        "mengapung dan menari dalam pola ritmis yang sangat memuaskan.\n\n"
        "🌟 Fitur utama:\n"
        "• Animasi bentuk looping yang hipnotis dalam kombinasi warna indah\n"
        "• Musik dengan tempo yang dipilih dengan cermat\n"
        "• Tanpa kata-kata atau suara — cocok untuk semua bahasa\n"
        "• 30 menit penuh kepuasan visual yang tak terputus\n\n"
        "🎵 Musik oleh Kevin MacLeod — CC Attribution 4.0\n"
        "© Happy Bear Kids 2026 | @happybearkidsin\n"
        "#HappyBearKids #BentukMemuaskan #LoopBentuk #VideoBalita"
    ),
}


def generate_thumbnail(ep_key, ep, queue, out_name, lang):
    thumb_path = queue / f"thumb_{Path(out_name).stem}.png"
    if thumb_path.exists():
        return True
    if not TOGETHER_KEY_FILE.exists():
        return False
    api_key = TOGETHER_KEY_FILE.read_text().strip()
    prompt  = ep["thumb_prompt"]
    if lang == "ar":
        prompt += ", no text, no letters, no words, no numbers"
    try:
        resp = requests.post(TOGETHER_URL, headers={
            "Authorization": f"Bearer {api_key}", "Content-Type": "application/json"
        }, json={"model": "black-forest-labs/FLUX.1-schnell",
                 "prompt": prompt, "width": 1280, "height": 720,
                 "steps": 4, "n": 1, "response_format": "b64_json"}, timeout=60)
        if resp.status_code != 200:
            print(f"  thumb error {resp.status_code}")
            return False
        thumb_path.write_bytes(__import__("base64").b64decode(resp.json()["data"][0]["b64_json"]))
        print(f"  thumb → {thumb_path.name}")
        return True
    except Exception as e:
        print(f"  thumb: {e}")
        return False


def make_meta(ep_key, lang, queue, out_name):
    ep_name = ep_key.replace("_", " ").title()
    title = TITLES[lang].replace("Satisfying Shapes Loop", f"Satisfying Shapes — {ep_name}")
    title = title.replace("حلقة الأشكال المُرضية", f"حلقة الأشكال — {ep_name}")
    title = title.replace("Loop Bentuk yang Memuaskan", f"Loop Bentuk — {ep_name}")
    meta = {
        "title": title, "description": DESC[lang],
        "video_type": "satisfying_loop", "theme": ep_key, "language": lang,
        "duration_minutes": 30, "is_short": False, "status": "public",
        "tags": ["satisfying shapes", "hypnotic", "baby calm", "shape loop",
                 "happy bear kids", "30 minutes", "satisfying video", "kids relax",
                 "baby shapes", ep_key.replace("_", " ")],
    }
    meta_path = queue / f"meta_{Path(out_name).stem}.yaml"
    with open(meta_path, "w", encoding="utf-8") as f:
        yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def render_episode(ep_key, ep, ep_idx, dry_run, regen_meta):
    out_name = f"satisfying_{ep_key}_{DATE_STR}.mp4"
    ok = True

    for lang, queue in [("en", QUEUE_EN), ("ar", QUEUE_AR), ("id", QUEUE_ID)]:
        out_mp4    = queue / out_name
        lang_music = alt_music(ep["music"], ep_idx, lang)
        if not out_mp4.exists() and not regen_meta and not dry_run:
            props = {"shapes": ep["shapes"], "colors": ep["colors"],
                     "bgColor": ep["bgColor"], "bpm": ep["bpm"],
                     "showLabels": False, "musicFile": lang_music}
            cmd = ["npx", "remotion", "render", "ShapeDanceLong",
                   f"--props={json.dumps(props)}", f"--output={str(out_mp4)}", "--log=error"]
            print(f"  Rendering {ep_key} ({lang}, BPM={ep['bpm']})...", flush=True)
            r = subprocess.run(cmd, cwd=str(REMOTION), timeout=86400)
            if r.returncode != 0 or not out_mp4.exists():
                print(f"  FAILED: {ep_key} ({lang})")
                ok = False
                continue
            print(f"  ✓ {out_name} ({out_mp4.stat().st_size/1024/1024:.1f}MB)")
        elif out_mp4.exists():
            print(f"  EXISTS {ep_key} ({lang})")
        if out_mp4.exists() or dry_run:
            make_meta(ep_key, lang, queue, out_name)
            generate_thumbnail(ep_key, ep, queue, out_name, lang)

    return ok


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--key",        default="satisfying_guess_surprise")
    parser.add_argument("--regen-meta", action="store_true")
    parser.add_argument("--dry-run",    action="store_true")
    args = parser.parse_args()
    for d in (QUEUE_EN, QUEUE_AR, QUEUE_ID):
        d.mkdir(parents=True, exist_ok=True)
    print(f"\n=== Satisfying Shapes: {len(EPISODES)} episodes → EN+AR+ID ===\n")
    ok = 0
    for ep_idx, (ep_key, ep) in enumerate(EPISODES.items()):
        print(f"[{ep_key}]")
        if render_episode(ep_key, ep, ep_idx, args.dry_run, args.regen_meta):
            ok += 1
    print(f"\nDone: {ok}/{len(EPISODES)}")

if __name__ == "__main__":
    main()
