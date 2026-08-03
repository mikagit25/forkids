#!/usr/bin/env python3
"""
Generate Lullaby Animals series — 4 calm sleep/wind-down episodes, 25 min each.
Uses DanceSpriteLong v2 with ZFLOAT + slow BOB + depth layers.

Episodes: bear_night, bunny_dream, forest_lullaby, ocean_dream
Designed for kids_sleep track — calm visuals, slow music, bedtime mood.

Usage:
  python3 scripts/generate_lullaby_animals.py
  python3 scripts/generate_lullaby_animals.py --ep bear_night
  python3 scripts/generate_lullaby_animals.py --dry-run
  python3 scripts/generate_lullaby_animals.py --regen-meta
"""
import argparse, json, shutil, subprocess, yaml
from datetime import datetime
from pathlib import Path

ROOT     = Path(__file__).resolve().parent.parent
REMOTION = ROOT / "remotion"
QUEUE_EN = ROOT / "output" / "queue"
QUEUE_AR = ROOT / "output" / "queue_ar"
TOGETHER_KEY_FILE = ROOT / "credentials" / "together_api_key.txt"
DATE_STR = datetime.now().strftime("%Y%m%d")

# 25 min = 1500s — very slow, calm, ZFLOAT dominant
# ZFLOAT gives breathing zoom that soothes without stimulating
_BLOCKS = [
    {"startSec": 0,    "endSec": 90,   "motion": "FADEIN",  "amplitude": 22,                               "wobble": True},
    {"startSec": 90,   "endSec": 650,  "motion": "ZFLOAT",  "period": 7.0,  "amplitude": 22,              "wobble": True},
    {"startSec": 650,  "endSec": 1050, "motion": "BOB",     "period": 5.5,  "amplitude": 20,              "wobble": True},
    {"startSec": 1050, "endSec": 1380, "motion": "WAVE",    "period": 7.0,  "amplitude": 16, "waveDelay": 1.4, "wobble": True},
    {"startSec": 1380, "endSec": 1440, "motion": "ZFLOAT",  "period": 8.0,  "amplitude": 14,              "wobble": True},
    {"startSec": 1440, "endSec": 1500, "motion": "FADEOUT", "amplitude": 12,                               "wobble": True},
]

EPISODES = {
    "bear_night": {
        # Bear with stars — night nursery theme
        "sprites": [
            {"path": "characters/bear_happy_3d.png", "size": 460, "posX": 0.50, "posY": 0.46, "seed": 1, "depth": 0.85},
            {"path": "objects/star_sleep.png",        "size": 185, "posX": 0.20, "posY": 0.28, "seed": 2, "depth": 0.55},
            {"path": "objects/cloud_3d.png",          "size": 175, "posX": 0.78, "posY": 0.25, "seed": 3, "depth": 0.45},
            {"path": "objects/star_3d.png",           "size": 140, "posX": 0.14, "posY": 0.65, "seed": 4, "depth": 0.20},
            {"path": "objects/star_silver.png",       "size": 130, "posX": 0.84, "posY": 0.68, "seed": 5, "depth": 0.12},
        ],
        "music": "Baby Bear's Den v2.mp3",
        "bgColor": "#080818", "bgColorEnd": "#0A0C22",
        "nightMode": True,
        "thumb_prompt": "cute sleepy Pixar 3D bear floating in starry night sky, glowing golden sleepy star, fluffy white cloud, silver stars, deep blue night, calming lullaby baby video, 3D render style",
    },
    "bunny_dream": {
        # Bunny with butterflies and clouds — soft dreamy theme
        "sprites": [
            {"path": "animals/rabbit_3d.png",         "size": 455, "posX": 0.50, "posY": 0.46, "seed": 1, "depth": 0.85},
            {"path": "objects/butterfly_3d.png",       "size": 185, "posX": 0.22, "posY": 0.30, "seed": 2, "depth": 0.60},
            {"path": "animals/cat_3d.png",             "size": 165, "posX": 0.78, "posY": 0.65, "seed": 3, "depth": 0.50},
            {"path": "objects/cloud_3d.png",           "size": 150, "posX": 0.15, "posY": 0.62, "seed": 4, "depth": 0.22},
            {"path": "objects/star_sleep.png",         "size": 135, "posX": 0.84, "posY": 0.28, "seed": 5, "depth": 0.12},
        ],
        "music": "Sleepy Bear v2.mp3",
        "bgColor": "#18080E", "bgColorEnd": "#200A16",
        "nightMode": True,
        "thumb_prompt": "cute sleepy Pixar 3D bunny floating gently, colorful butterfly nearby, tiny cat sleeping, soft cloud, glowing sleepy star, soft purple-pink night sky, lullaby baby video, 3D render style",
    },
    "forest_lullaby": {
        # Bear + forest friends at night — cosy forest lullaby
        "sprites": [
            {"path": "characters/bear_happy_3d.png", "size": 455, "posX": 0.50, "posY": 0.46, "seed": 1, "depth": 0.85},
            {"path": "animals/owl_3d.png",            "size": 195, "posX": 0.20, "posY": 0.32, "seed": 2, "depth": 0.60},
            {"path": "animals/rabbit_3d.png",         "size": 170, "posX": 0.78, "posY": 0.65, "seed": 3, "depth": 0.50},
            {"path": "objects/butterfly_3d.png",      "size": 145, "posX": 0.15, "posY": 0.65, "seed": 4, "depth": 0.22},
            {"path": "objects/star_3d.png",           "size": 130, "posX": 0.85, "posY": 0.28, "seed": 5, "depth": 0.12},
        ],
        "music": "Baby Bear's Forest Lullaby v2.mp3",
        "bgColor": "#050E06", "bgColorEnd": "#080F08",
        "nightMode": True,
        "thumb_prompt": "cute sleepy Pixar 3D bear in magical dark forest at night, wise owl nearby, little bunny sleeping, butterfly glowing softly, twinkling star, enchanted cosy forest, lullaby baby video, 3D render style",
    },
    "ocean_dream": {
        # Whale + ocean friends drifting peacefully at night
        "sprites": [
            {"path": "animals/blue_whale_3d.png",  "size": 440, "posX": 0.50, "posY": 0.46, "seed": 1, "depth": 0.85},
            {"path": "animals/penguin_3d.png",     "size": 190, "posX": 0.22, "posY": 0.68, "seed": 2, "depth": 0.60},
            {"path": "objects/jellyfish_glow.png", "size": 175, "posX": 0.78, "posY": 0.32, "seed": 3, "depth": 0.50},
            {"path": "objects/octopus_3d.png",     "size": 150, "posX": 0.15, "posY": 0.30, "seed": 4, "depth": 0.22},
            {"path": "objects/star_sleep.png",     "size": 130, "posX": 0.84, "posY": 0.68, "seed": 5, "depth": 0.12},
        ],
        "music": "Ocean Waves Lullaby v2.mp3",
        "bgColor": "#060C1A", "bgColorEnd": "#081022",
        "nightMode": True,
        "thumb_prompt": "cute sleepy Pixar 3D blue whale floating in deep calm ocean at night, little penguin beside, glowing jellyfish drifting, friendly octopus, golden sleepy star, dark blue ocean, lullaby baby video, 3D render style",
    },
}

TITLES = {
    "bear_night":      {"en": "🐻 Sleepy Bear Lullaby | 25 Minutes | Happy Bear Kids",
                        "ar": "🐻 تهويدة الدب النعسان | ٢٥ دقيقة | Happy Bear Kids"},
    "bunny_dream":     {"en": "🐰 Dreamy Bunny Lullaby | 25 Minutes | Happy Bear Kids",
                        "ar": "🐰 تهويدة الأرنب الحالم | ٢٥ دقيقة | Happy Bear Kids"},
    "forest_lullaby":  {"en": "🌙 Forest Lullaby for Babies | 25 Minutes | Happy Bear Kids",
                        "ar": "🌙 تهويدة الغابة للأطفال | ٢٥ دقيقة | Happy Bear Kids"},
    "ocean_dream":     {"en": "🐋 Ocean Dream Lullaby | 25 Minutes | Happy Bear Kids",
                        "ar": "🐋 تهويدة حلم المحيط | ٢٥ دقيقة | Happy Bear Kids"},
}

DESC = {
    "en": (
        "Welcome to Happy Bear Kids! 🐻\n\n"
        "25 minutes of gentle, calming lullaby visuals to help your baby drift off to sleep. "
        "Cute 3D characters float and breathe softly to soothing lullaby music — "
        "perfect for bedtime, nap time, or winding down.\n\n"
        "Our Lullaby Animals series combines the magic of 3D characters with gentle, "
        "breathing animations that slow down with the music. Our new ZFLOAT animation "
        "makes characters appear to breathe toward you and away — deeply calming for babies.\n\n"
        "🌙 Key features:\n"
        "• Adorable Pixar-style 3D animals with gentle breathing zoom animation\n"
        "• Soft depth layers — closer characters move slowly, background ones barely move\n"
        "• Drop shadows give a cosy, warm 3D feel even without bright colours\n"
        "• Calm, slow lullaby music chosen for sleep and relaxation\n"
        "• No sudden movements, no surprises — only gentle visual comfort\n\n"
        "👶 Perfect for:\n"
        "• Bedtime wind-down routine for babies and toddlers\n"
        "• Nap time visual comfort\n"
        "• Reducing evening over-stimulation\n"
        "• Background during feeding at night\n"
        "• Gentle sensory experience for newborns\n\n"
        "🎯 Benefits:\n"
        "• Breathing animation rhythm synchronises with natural baby breathing patterns\n"
        "• Dark backgrounds reduce blue light exposure at bedtime\n"
        "• Slow movement tempo gradually signals sleep time to young brains\n"
        "• Familiar animal characters provide emotional comfort\n\n"
        "🎵 Original music by Happy Bear Kids (AI-generated, © 2026)\n\n"
        "© Happy Bear Kids 2026 — All rights reserved\n"
        "New videos every week! Subscribe ▶ @HappyBearKids1\n\n"
        "#HappyBearKids #LullabyForBabies #BabyLullaby #SleepBaby #BedtimeVideo "
        "#ToddlerSleep #BabyCalm #NightTime #LullabyAnimals #25Minutes"
    ),
    "ar": (
        "أهلاً بكم في Happy Bear Kids! 🐻\n\n"
        "٢٥ دقيقة من المرئيات التهويدة الهادئة لمساعدة طفلك على النوم. "
        "شخصيات ثلاثية الأبعاد لطيفة تطفو وتتنفس برفق على موسيقى تهويدة مريحة.\n\n"
        "سلسلة حيوانات التهويدة تجمع بين سحر الشخصيات ثلاثية الأبعاد والحركات الهادئة المتنفسة "
        "التي تتزامن مع الموسيقى. مثالية لوقت النوم وراحة الطفل.\n\n"
        "🌙 المميزات الرئيسية:\n"
        "• حيوانات ثلاثية الأبعاد بأسلوب بيكسار مع حركة تنفس هادئة\n"
        "• طبقات عمق ناعمة — الشخصيات القريبة تتحرك ببطء، والخلفية تكاد لا تتحرك\n"
        "• موسيقى تهويدة هادئة مختارة للنوم والاسترخاء\n"
        "• لا حركات مفاجئة — فقط راحة بصرية لطيفة\n\n"
        "🎵 موسيقى أصلية من هابي بير كيدز\n"
        "© Happy Bear Kids 2026 | اشترك ▶ @happybearkidsar\n\n"
        "#HappyBearKids #تهويدة_أطفال #نوم_الطفل #تهويدة #فيديو_نوم"
    ),
}


def generate_thumbnail(ep_key, ep, queue, out_name, lang):
    thumb_path = queue / f"thumb_{Path(out_name).stem}.png"
    if thumb_path.exists():
        return True
    if not TOGETHER_KEY_FILE.exists():
        return False
    api_key = TOGETHER_KEY_FILE.read_text().strip()
    prompt = ep["thumb_prompt"]
    if lang == "ar":
        prompt += ", no text, no letters, no words, no numbers"
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("gat", ROOT / "scripts" / "generate_ai_thumbs.py")
        gat = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gat)
        img = gat.together_generate_image(prompt, api_key)
        if img:
            thumb_path.write_bytes(gat.resize_to_720p(img))
            print(f"  thumb → {thumb_path.name}")
            return True
        print(f"  thumb error: API returned no image")
        return False
    except Exception as e:
        print(f"  thumb error: {e}")
        return False


def make_meta(ep_key, lang, queue, out_name):
    tags = [
        "lullaby", "baby lullaby", "sleep baby", "bedtime video", "happy bear kids",
        "25 minutes", "baby sleep", "toddler sleep", "lullaby animals",
        ep_key.replace("_", " "), "night time", "calm baby", "baby calm",
        "3d animals", "sleep music for babies",
    ]
    meta = {
        "title": TITLES[ep_key][lang],
        "description": DESC[lang],
        "video_type": "lullaby_long",
        "theme": ep_key,
        "language": lang,
        "duration_minutes": 25,
        "is_short": False,
        "status": "public",
        "made_for_kids": True,
        "tags": tags,
    }
    meta_path = queue / f"meta_{Path(out_name).stem}.yaml"
    with open(meta_path, "w", encoding="utf-8") as f:
        yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def _render_episode(ep_key, ep, out_path, dry_run):
    props = json.dumps({
        "sprites": ep["sprites"],
        "blocks": _BLOCKS,
        "bgColor": ep["bgColor"],
        "bgColorEnd": ep.get("bgColorEnd", ep["bgColor"]),
        "musicFile": ep["music"],
        "nightMode": ep.get("nightMode", False),
        "wobble": True,
    })
    cmd = ["npx", "remotion", "render", "DanceSpriteLong", str(out_path),
           "--props", props, "--concurrency", "1", "--log", "error"]
    if dry_run:
        print(f"    [DRY RUN] DanceSpriteLong {ep_key} → {out_path.name}")
        return True
    out_path.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(cmd, cwd=str(REMOTION), timeout=86400)
    return r.returncode == 0


def render_episode(ep_key, ep, dry_run, regen_meta):
    out_name = f"lullaby_animals_{ep_key}_{DATE_STR}.mp4"
    en_mp4   = QUEUE_EN / out_name
    ar_mp4   = QUEUE_AR / out_name

    if not en_mp4.exists() and not regen_meta:
        print(f"  DanceSpriteLong render [{ep_key}]...", flush=True)
        if not _render_episode(ep_key, ep, en_mp4, dry_run):
            print(f"  FAILED: {ep_key}")
            return False
        if en_mp4.exists():
            print(f"  ✓ {out_name} ({en_mp4.stat().st_size / 1024 / 1024:.1f} MB)")
    else:
        if en_mp4.exists():
            print(f"  EXISTS {ep_key} (en)")

    if (en_mp4.exists() or dry_run) and not ar_mp4.exists():
        if not dry_run:
            shutil.copy2(str(en_mp4), str(ar_mp4))
            print(f"  ✓ copied → queue_ar/{out_name}")
        else:
            print(f"    [DRY RUN] copy → queue_ar/{out_name}")
    elif ar_mp4.exists():
        print(f"  EXISTS {ep_key} (ar)")

    for lang, queue, mp4 in [("en", QUEUE_EN, en_mp4), ("ar", QUEUE_AR, ar_mp4)]:
        if mp4.exists() or dry_run or regen_meta:
            make_meta(ep_key, lang, queue, out_name)
            generate_thumbnail(ep_key, ep, queue, out_name, lang)

    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ep",         default=None, help="Episode: bear_night/bunny_dream/forest_lullaby/ocean_dream")
    parser.add_argument("--regen-meta", action="store_true")
    parser.add_argument("--dry-run",    action="store_true")
    args = parser.parse_args()

    for d in (QUEUE_EN, QUEUE_AR):
        d.mkdir(parents=True, exist_ok=True)

    episodes = {k: v for k, v in EPISODES.items() if not args.ep or k == args.ep}
    if args.ep and not episodes:
        print(f"Unknown episode '{args.ep}'. Valid: {', '.join(EPISODES)}")
        return

    print(f"\n=== Lullaby Animals: {len(episodes)} episode(s) → EN + AR ===\n")
    ok = 0
    for ep_key, ep in episodes.items():
        print(f"[{ep_key}]")
        if render_episode(ep_key, ep, args.dry_run, args.regen_meta):
            ok += 1
    print(f"\nDone: {ok}/{len(episodes)}")


if __name__ == "__main__":
    main()
