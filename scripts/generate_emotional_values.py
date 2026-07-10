#!/usr/bin/env python3
"""
Generate Emotional Values series — 8 emotion dance videos, 20 min, no text.
Uses Manim pipeline (generate_video.py) with emotions sprites.
No text → EN+AR+ID (one render, 3 queues).

Usage:
  python3 scripts/generate_emotional_values.py --key emotions_values_cat4
  python3 scripts/generate_emotional_values.py --regen-meta
"""
import argparse, base64, json, subprocess, sys, yaml
from datetime import datetime
from pathlib import Path
import requests

ROOT      = Path(__file__).resolve().parent.parent
QUEUE_EN  = ROOT / "output" / "queue"
QUEUE_AR  = ROOT / "output" / "queue_ar"
QUEUE_ID  = ROOT / "output" / "queue_id"
SCRIPT_DIR= ROOT / "config" / "scripts"
TOGETHER_KEY_FILE = ROOT / "credentials" / "together_api_key.txt"
TOGETHER_URL      = "https://api.together.xyz/v1/images/generations"
DATE_STR  = datetime.now().strftime("%Y%m%d")

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

# Sprites in assets/sprites_new/emotions/ (stem names used in YAML)
CHOREOS = ["solo_bounce", "solo_sway", "solo_spin", "solo_wave",
           "solo_jump", "solo_twist", "solo_nod", "solo_shimmy"]

EPISODES = {
    "happy":     {"chars": ["happy_3d", "excited_3d"], "bg": "#FFF9E6",
                  "title_en": "😊 Happy and Excited! | 20 Minutes | Happy Bear Kids",
                  "title_ar": "😊 سعيد ومتحمس | ٢٠ دقيقة | Happy Bear Kids",
                  "title_id": "😊 Senang dan Bersemangat! | 20 Menit | Happy Bear Kids",
                  "thumb": "cute 3D cartoon happy excited emoji characters dancing joyfully, bright yellow colors, kids animation"},
    "love":      {"chars": ["love_3d", "happy_3d"], "bg": "#FCE4EC",
                  "title_en": "❤️ Love and Happiness | 20 Minutes | Happy Bear Kids",
                  "title_ar": "❤️ الحب والسعادة | ٢٠ دقيقة | Happy Bear Kids",
                  "title_id": "❤️ Cinta dan Kebahagiaan | 20 Menit | Happy Bear Kids",
                  "thumb": "cute 3D cartoon love heart happy emoji dancing, pink red colors, toddler kids animation"},
    "calm":      {"chars": ["sleepy_3d", "love_3d"], "bg": "#E3F2FD",
                  "title_en": "😴 Calm and Cosy | 20 Minutes | Happy Bear Kids",
                  "title_ar": "😴 هادئ ودافئ | ٢٠ دقيقة | Happy Bear Kids",
                  "title_id": "😴 Tenang dan Nyaman | 20 Menit | Happy Bear Kids",
                  "thumb": "cute 3D cartoon sleepy calm love emoji swaying gently, soft blue pastel colors, soothing baby animation"},
    "brave":     {"chars": ["scared_3d", "happy_3d", "excited_3d"], "bg": "#F3E5F5",
                  "title_en": "💪 Be Brave! | 20 Minutes | Happy Bear Kids",
                  "title_ar": "💪 كن شجاعاً | ٢٠ دقيقة | Happy Bear Kids",
                  "title_id": "💪 Jadilah Berani! | 20 Menit | Happy Bear Kids",
                  "thumb": "cute 3D cartoon brave happy characters dancing, purple golden colors, empowering kids animation"},
    "surprised":  {"chars": ["surprised_3d", "excited_3d"], "bg": "#E8F5E9",
                  "title_en": "😲 What a Surprise! | 20 Minutes | Happy Bear Kids",
                  "title_ar": "😲 يا له من مفاجأة | ٢٠ دقيقة | Happy Bear Kids",
                  "title_id": "😲 Sungguh Mengejutkan! | 20 Menit | Happy Bear Kids",
                  "thumb": "cute 3D cartoon surprised excited emoji jumping with joy, green yellow colors, toddler animation"},
    "all_emotions": {"chars": ["happy_3d", "sad_3d", "angry_3d", "scared_3d"], "bg": "#FFF3E0",
                  "title_en": "🎭 All Emotions Dance | 20 Minutes | Happy Bear Kids",
                  "title_ar": "🎭 رقصة كل المشاعر | ٢٠ دقيقة | Happy Bear Kids",
                  "title_id": "🎭 Tarian Semua Emosi | 20 Menit | Happy Bear Kids",
                  "thumb": "cute 3D cartoon emotion characters happy sad angry scared all dancing together, rainbow colors, kids animation"},
    "gentle":    {"chars": ["love_3d", "sleepy_3d", "happy_3d"], "bg": "#F1F8E9",
                  "title_en": "🌸 Gentle and Kind | 20 Minutes | Happy Bear Kids",
                  "title_ar": "🌸 لطيف وطيب | ٢٠ دقيقة | Happy Bear Kids",
                  "title_id": "🌸 Lembut dan Baik Hati | 20 Menit | Happy Bear Kids",
                  "thumb": "cute 3D cartoon kind gentle love sleepy happy emoji dancing softly, soft green pink pastel, baby animation"},
    "joy":       {"chars": ["happy_3d", "excited_3d", "love_3d"], "bg": "#FFFDE7",
                  "title_en": "🎉 Pure Joy! | 20 Minutes | Happy Bear Kids",
                  "title_ar": "🎉 فرح خالص | ٢٠ دقيقة | Happy Bear Kids",
                  "title_id": "🎉 Kegembiraan Murni! | 20 Menit | Happy Bear Kids",
                  "thumb": "cute 3D cartoon joyful happy excited love emoji party dancing, bright yellow orange pink, kids celebration animation"},
}

MUSIC_MAP = {
    "happy": "Happy Happy Game Show.mp3", "love": "Wholesome.mp3",
    "calm": "Heartwarming.mp3", "brave": "Hyperfun.mp3",
    "surprised": "Quirky Dog.mp3", "all_emotions": "Merry Go.mp3",
    "gentle": "Carefree.mp3", "joy": "Monkeys Spinning Monkeys.mp3",
}

DESC = {
    "en": (
        "Welcome to Happy Bear Kids! 🐻\n\n"
        "20 minutes of delightful emotion characters dancing and expressing feelings — "
        "helping babies and toddlers learn about the wonderful world of emotions through "
        "colourful animation and gentle music.\n\n"
        "Our Emotional Values series uses adorable 3D cartoon emotion characters to help "
        "young children develop emotional intelligence in the most fun and engaging way. "
        "Watch happy, excited, loving and calm characters dance and move to cheerful music!\n\n"
        "🌟 Key features:\n"
        "• Adorable 3D Pixar-style emotion characters\n"
        "• 20 minutes of continuous dancing and movement\n"
        "• Carefully chosen music matched to each emotion\n"
        "• No words on screen — pure visual emotional expression\n"
        "• Perfect for building emotional vocabulary in babies and toddlers\n\n"
        "👶 Great for:\n"
        "• Babies aged 0-2 years — seeing emotions expressed visually\n"
        "• Toddlers learning about feelings and emotional expression\n"
        "• Parents who want to introduce emotional literacy early\n"
        "• Background for calm play, meals or activities\n"
        "• Building empathy and emotional awareness from a young age\n\n"
        "🎯 Educational and developmental value:\n"
        "• Emotional recognition — learning to identify different feelings\n"
        "• Empathy development — understanding that characters have feelings\n"
        "• Vocabulary building — emotional expressions and words\n"
        "• Social development — watching characters interact positively\n"
        "• Self-regulation — seeing emotions expressed and resolved peacefully\n\n"
        "The adorable emotion characters move and dance in rhythm, expressing each feeling "
        "through their unique animation style. No narration needed — the visual language of "
        "emotion speaks to every child, in every language!\n\n"
        "🎵 Music by Kevin MacLeod (incompetech.com)\n"
        "Licensed under Creative Commons: By Attribution 4.0 License\n"
        "http://creativecommons.org/licenses/by/4.0/\n\n"
        "© Happy Bear Kids 2026 — All rights reserved\n"
        "New videos every week! Subscribe ▶ @HappyBearKids1\n\n"
        "#HappyBearKids #EmotionsForKids #BabyEmotions #ToddlerEmotions "
        "#EmotionalLearning #KidsEmotions #FeelingsDance #20Minutes"
    ),
    "ar": (
        "أهلاً بكم في Happy Bear Kids! 🐻\n\n"
        "٢٠ دقيقة من شخصيات المشاعر الرائعة ترقص وتعبّر عن مشاعرها — مما يساعد الأطفال "
        "الرضّع والصغار على تعلم عالم المشاعر الرائع من خلال الرسوم المتحركة الملوّنة.\n\n"
        "سلسلة القيم العاطفية تستخدم شخصيات كرتونية ثلاثية الأبعاد للمشاعر لمساعدة "
        "الأطفال الصغار على تطوير الذكاء العاطفي بأكثر الطرق متعةً وجاذبية.\n\n"
        "🌟 المميزات:\n"
        "• شخصيات مشاعر ثلاثية الأبعاد على طراز Pixar\n"
        "• ٢٠ دقيقة من الرقص والحركة المستمرة\n"
        "• بدون كلمات على الشاشة — تعبير بصري عاطفي خالص\n\n"
        "🎵 موسيقى Kevin MacLeod — Creative Commons 4.0\n"
        "© Happy Bear Kids 2026 | @happybearkidsar\n"
        "#HappyBearKids #مشاعر_الأطفال #تعلم_المشاعر #فيديو_أطفال #رقص_المشاعر"
    ),
    "id": (
        "Selamat datang di Happy Bear Kids! 🐻\n\n"
        "20 menit karakter emosi yang menggemaskan menari dan mengekspresikan perasaan — "
        "membantu bayi dan balita belajar tentang dunia emosi yang wonderful melalui animasi "
        "berwarna-warni dan musik yang lembut.\n\n"
        "Seri Nilai Emosional kami menggunakan karakter emosi kartun 3D yang menggemaskan "
        "untuk membantu anak kecil mengembangkan kecerdasan emosional dengan cara yang paling "
        "menyenangkan dan menarik.\n\n"
        "🌟 Fitur utama:\n"
        "• Karakter emosi 3D bergaya Pixar yang menggemaskan\n"
        "• 20 menit menari dan bergerak terus-menerus\n"
        "• Tanpa kata-kata di layar — ekspresi emosi visual murni\n\n"
        "🎵 Musik oleh Kevin MacLeod — CC Attribution 4.0\n"
        "© Happy Bear Kids 2026 | @happybearkidsin\n"
        "#HappyBearKids #EmosiAnak #BelajarEmosi #AnimasiEmosi #VideoBalita"
    ),
}


def build_yaml_script(ep_key, ep):
    chars = ep["chars"]
    music = MUSIC_MAP.get(ep_key, "Happy Happy Game Show.mp3")
    duration_min = 20
    duration_sec = duration_min * 60
    scene_dur = 45
    n_scenes = duration_sec // scene_dur
    scenes = []
    for i in range(n_scenes):
        char = chars[i % len(chars)]
        choreo = CHOREOS[i % len(CHOREOS)]
        scenes.append({
            "start_sec": float(i * scene_dur),
            "duration": float(scene_dur),
            "choreo": choreo,
            "n": 1,
            "chars": [char],
            "entry": "zoom_in",
            "bg_color": ep["bg"],
        })
    return {
        "video_type": "emotional_values",
        "theme": "emotions",
        "duration_minutes": duration_min,
        "style": "tutitu",
        "music": music,
        "scenes": scenes,
    }


def generate_thumbnail(ep_key, ep, queue, out_name, lang):
    thumb_path = queue / f"thumb_{Path(out_name).stem}.png"
    if thumb_path.exists():
        return True
    if not TOGETHER_KEY_FILE.exists():
        return False
    api_key = TOGETHER_KEY_FILE.read_text().strip()
    prompt  = ep["thumb"]
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


def make_meta(ep_key, ep, lang, queue, out_name):
    title_key = f"title_{lang}"
    meta = {
        "title": ep[title_key], "description": DESC[lang],
        "video_type": "emotional_values", "theme": "emotions",
        "language": lang, "duration_minutes": 20,
        "is_short": False, "status": "public",
        "tags": ["emotions", "feelings", "kids emotions", "toddler emotions",
                 "happy bear kids", "20 minutes", "emotional learning",
                 "baby dance", ep_key.replace("_", " ")],
    }
    meta_path = queue / f"meta_{Path(out_name).stem}.yaml"
    with open(meta_path, "w", encoding="utf-8") as f:
        yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def render_episode(ep_key, ep, ep_idx, dry_run, regen_meta):
    out_name  = f"emotional_values_{ep_key}_{DATE_STR}.mp4"
    en_music  = MUSIC_MAP.get(ep_key, "Happy Happy Game Show.mp3")
    ok = True
    SCRIPT_DIR.mkdir(parents=True, exist_ok=True)

    for lang, queue in [("en", QUEUE_EN), ("ar", QUEUE_AR), ("id", QUEUE_ID)]:
        out_mp4    = queue / out_name
        lang_music = alt_music(en_music, ep_idx, lang)
        if not out_mp4.exists() and not regen_meta and not dry_run:
            script_data = build_yaml_script(ep_key, ep)
            script_data["music"] = lang_music
            script_path = SCRIPT_DIR / f"emotional_{ep_key}_{lang}.yaml"
            with open(script_path, "w") as f:
                yaml.dump(script_data, f, allow_unicode=True, default_flow_style=False)
            cmd = [sys.executable, str(ROOT / "scripts" / "generate_video.py"),
                   "--theme", "emotions", "--duration", "20",
                   "--script", str(script_path), "--output", str(out_mp4)]
            print(f"  Rendering {ep_key} ({lang}, 20 min, Manim)...", flush=True)
            r = subprocess.run(cmd, capture_output=False, timeout=86400, cwd=str(ROOT))
            if r.returncode != 0 or not out_mp4.exists():
                print(f"  FAILED: {ep_key} ({lang})")
                ok = False
                continue
            print(f"  ✓ {out_name} ({out_mp4.stat().st_size/1024/1024:.1f}MB)")
        elif out_mp4.exists():
            print(f"  EXISTS {ep_key} ({lang})")
        if out_mp4.exists() or dry_run:
            make_meta(ep_key, ep, lang, queue, out_name)
            generate_thumbnail(ep_key, ep, queue, out_name, lang)

    return ok


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--key",        default="emotions_values_cat4")
    parser.add_argument("--regen-meta", action="store_true")
    parser.add_argument("--dry-run",    action="store_true")
    args = parser.parse_args()
    for d in (QUEUE_EN, QUEUE_AR, QUEUE_ID):
        d.mkdir(parents=True, exist_ok=True)
    print(f"\n=== Emotional Values: {len(EPISODES)} episodes → EN+AR+ID ===\n")
    ok = 0
    for ep_idx, (ep_key, ep) in enumerate(EPISODES.items()):
        print(f"[{ep_key}]")
        if render_episode(ep_key, ep, ep_idx, args.dry_run, args.regen_meta):
            ok += 1
    print(f"\nDone: {ok}/{len(EPISODES)}")

if __name__ == "__main__":
    main()
