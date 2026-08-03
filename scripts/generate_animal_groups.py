#!/usr/bin/env python3
"""
Generate Animal Groups series — 5 themed animal episodes, 25 min each.
Uses DanceSpriteLong v2 with depth layers for 3D parallax effect.

Episodes: farm, jungle, arctic, forest, savanna
Each has 5 sprites in 3 depth planes: foreground (d≥0.7), mid (d≈0.5), background (d≤0.3)

Usage:
  python3 scripts/generate_animal_groups.py
  python3 scripts/generate_animal_groups.py --ep jungle
  python3 scripts/generate_animal_groups.py --dry-run
  python3 scripts/generate_animal_groups.py --regen-meta
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

# 25 min = 1500s — energetic dance with depth parallax
# Showcases MARCH + BOUNCE + ZFLOAT with depth-based parallax
_BLOCKS = [
    {"startSec": 0,    "endSec": 60,   "motion": "FADEIN",  "amplitude": 40,                              "wobble": True},
    {"startSec": 60,   "endSec": 500,  "motion": "BOB",     "period": 2.8,  "amplitude": 48,             "wobble": True},
    {"startSec": 500,  "endSec": 800,  "motion": "MARCH",   "period": 4.5,  "amplitude": 38,             "wobble": True},
    {"startSec": 800,  "endSec": 1100, "motion": "WAVE",    "period": 3.2,  "amplitude": 52, "waveDelay": 0.45, "wobble": True},
    {"startSec": 1100, "endSec": 1350, "motion": "BOUNCE",  "period": 2.2,  "amplitude": 58,             "wobble": True},
    {"startSec": 1350, "endSec": 1500, "motion": "ZFLOAT",  "period": 4.5,  "amplitude": 35,             "wobble": True},
]

EPISODES = {
    "farm": {
        # depth: cow=foreground, pig+duck=midground, dog+cat=background
        "sprites": [
            {"path": "animals/cow_3d.png",    "size": 455, "posX": 0.50, "posY": 0.46, "seed": 1, "depth": 0.85},
            {"path": "animals/pig_3d.png",    "size": 195, "posX": 0.22, "posY": 0.68, "seed": 2, "depth": 0.60},
            {"path": "animals/duck_3d.png",   "size": 175, "posX": 0.78, "posY": 0.65, "seed": 3, "depth": 0.55},
            {"path": "animals/dog_3d.png",    "size": 140, "posX": 0.15, "posY": 0.30, "seed": 4, "depth": 0.25},
            {"path": "animals/cat_3d.png",    "size": 130, "posX": 0.84, "posY": 0.28, "seed": 5, "depth": 0.15},
        ],
        "music": "Down on the Farm v2.mp3",
        "bgColor": "#1A3A0E", "bgColorEnd": "#224A12",
        "thumb_prompt": "cute Pixar 3D farm animals dancing together, friendly cow in front, pig and duck in middle, dog and cat in back, sunny green farm background, cheerful kids video, 3D render style",
    },
    "jungle": {
        # depth: monkey=foreground, elephant+parrot=mid, tiger+lion=background
        "sprites": [
            {"path": "animals/monkey_3d.png",  "size": 450, "posX": 0.50, "posY": 0.44, "seed": 1, "depth": 0.85},
            {"path": "animals/elephant_3d.png","size": 210, "posX": 0.20, "posY": 0.62, "seed": 2, "depth": 0.62},
            {"path": "animals/parrot_3d.png",  "size": 175, "posX": 0.80, "posY": 0.32, "seed": 3, "depth": 0.55},
            {"path": "animals/tiger_3d.png",   "size": 145, "posX": 0.16, "posY": 0.28, "seed": 4, "depth": 0.25},
            {"path": "animals/lion_3d.png",    "size": 135, "posX": 0.82, "posY": 0.68, "seed": 5, "depth": 0.15},
        ],
        "music": "Jungle Adventure Song v2.mp3",
        "bgColor": "#0F2810", "bgColorEnd": "#142E12",
        "thumb_prompt": "cute Pixar 3D jungle animals dancing, playful monkey in foreground, large elephant and colorful parrot behind, tiger and lion in background, lush jungle setting, vibrant kids video, 3D render style",
    },
    "arctic": {
        # depth: polar_bear=fg, penguin+owl=mid, fox+blue_whale=bg
        "sprites": [
            {"path": "animals/polar_bear_3d.png", "size": 455, "posX": 0.50, "posY": 0.44, "seed": 1, "depth": 0.85},
            {"path": "animals/penguin_3d.png",    "size": 195, "posX": 0.24, "posY": 0.68, "seed": 2, "depth": 0.62},
            {"path": "animals/owl_3d.png",        "size": 170, "posX": 0.78, "posY": 0.32, "seed": 3, "depth": 0.55},
            {"path": "animals/fox_3d.png",        "size": 145, "posX": 0.16, "posY": 0.28, "seed": 4, "depth": 0.25},
            {"path": "animals/blue_whale_3d.png", "size": 155, "posX": 0.82, "posY": 0.65, "seed": 5, "depth": 0.12},
        ],
        "music": "Forest Morning v2.mp3",
        "bgColor": "#0A1A30", "bgColorEnd": "#0C2040",
        "thumb_prompt": "cute Pixar 3D arctic animals dancing, fluffy polar bear in front, penguin and snowy owl behind, fox and whale in background, icy blue arctic scene, happy kids video, 3D render style",
    },
    "forest": {
        # depth: bear=fg, fox+rabbit=mid, owl+frog=bg
        "sprites": [
            {"path": "animals/bear_3d.png",   "size": 455, "posX": 0.50, "posY": 0.44, "seed": 1, "depth": 0.85},
            {"path": "animals/fox_3d.png",    "size": 195, "posX": 0.22, "posY": 0.66, "seed": 2, "depth": 0.62},
            {"path": "animals/rabbit_3d.png", "size": 175, "posX": 0.78, "posY": 0.64, "seed": 3, "depth": 0.55},
            {"path": "animals/owl_3d.png",    "size": 145, "posX": 0.15, "posY": 0.28, "seed": 4, "depth": 0.25},
            {"path": "animals/frog_3d.png",   "size": 135, "posX": 0.84, "posY": 0.70, "seed": 5, "depth": 0.15},
        ],
        "music": "Dancing Bears v2.mp3",
        "bgColor": "#0A2008", "bgColorEnd": "#0F2A0A",
        "thumb_prompt": "cute Pixar 3D forest animals dancing, friendly bear in front, fox and rabbit in middle, wise owl and frog in background, magical dark forest glow, fun kids video, 3D render style",
    },
    "savanna": {
        # depth: elephant=fg, lion+flamingo=mid, monkey+tiger=bg
        "sprites": [
            {"path": "animals/elephant_3d.png", "size": 455, "posX": 0.50, "posY": 0.46, "seed": 1, "depth": 0.85},
            {"path": "animals/lion_3d.png",     "size": 200, "posX": 0.20, "posY": 0.64, "seed": 2, "depth": 0.62},
            {"path": "animals/flamingo_3d.png", "size": 180, "posX": 0.80, "posY": 0.34, "seed": 3, "depth": 0.55},
            {"path": "animals/monkey_3d.png",   "size": 150, "posX": 0.15, "posY": 0.28, "seed": 4, "depth": 0.25},
            {"path": "animals/tiger_3d.png",    "size": 140, "posX": 0.84, "posY": 0.68, "seed": 5, "depth": 0.15},
        ],
        "music": "Animal Parade v3.mp3",
        "bgColor": "#2A1A06", "bgColorEnd": "#361E08",
        "thumb_prompt": "cute Pixar 3D savanna animals dancing, big elephant in front, lion and pink flamingo behind, monkey and tiger in background, warm golden sunset savanna, exciting kids video, 3D render style",
    },
}

TITLES = {
    "farm":    {"en": "🐄 Farm Animals Dance Party | 25 Minutes | Happy Bear Kids",
                "ar": "🐄 رقصة حيوانات المزرعة | ٢٥ دقيقة | Happy Bear Kids"},
    "jungle":  {"en": "🐒 Jungle Animals Dance | 25 Minutes | Happy Bear Kids",
                "ar": "🐒 رقصة حيوانات الغابة | ٢٥ دقيقة | Happy Bear Kids"},
    "arctic":  {"en": "🐻‍❄️ Arctic Animals Dance | 25 Minutes | Happy Bear Kids",
                "ar": "🐻‍❄️ رقصة الحيوانات القطبية | ٢٥ دقيقة | Happy Bear Kids"},
    "forest":  {"en": "🐻 Forest Friends Dance | 25 Minutes | Happy Bear Kids",
                "ar": "🐻 رقصة أصدقاء الغابة | ٢٥ دقيقة | Happy Bear Kids"},
    "savanna": {"en": "🐘 Savanna Animals Dance | 25 Minutes | Happy Bear Kids",
                "ar": "🐘 رقصة حيوانات السافانا | ٢٥ دقيقة | Happy Bear Kids"},
}

DESC = {
    "en": (
        "Welcome to Happy Bear Kids! 🐻\n\n"
        "25 minutes of adorable 3D animals dancing together in their natural habitats! "
        "Watch as our cute Pixar-style animal friends bounce, sway, and float to "
        "cheerful music — perfect for toddlers and young children.\n\n"
        "Our Animal Groups series brings together different animal families from around "
        "the world. Each group dances in beautiful 3D depth — close animals move more, "
        "background animals create a magical sense of depth and space.\n\n"
        "🌟 Key features:\n"
        "• Adorable Pixar-style 3D animals with realistic depth and shadows\n"
        "• Dynamic parallax movement — foreground animals dance closer to you!\n"
        "• Cheerful, original music at the perfect BPM for toddlers\n"
        "• No text, no voices — universally enjoyable\n"
        "• 25 full minutes of continuous dancing fun\n\n"
        "👶 Perfect for:\n"
        "• Learning about different animal groups and habitats\n"
        "• Background during playtime or meals\n"
        "• Encouraging movement and dancing in toddlers\n"
        "• Visual stimulation and tracking for young babies\n"
        "• Fun screen time that parents feel good about\n\n"
        "🎯 Educational value:\n"
        "• Animal recognition and grouping by habitat\n"
        "• Visual tracking with dynamic 3D depth movement\n"
        "• Rhythm and music appreciation\n"
        "• Colour and size recognition through varied 3D characters\n\n"
        "🎵 Original music by Happy Bear Kids (AI-generated, © 2026)\n\n"
        "© Happy Bear Kids 2026 — All rights reserved\n"
        "New videos every week! Subscribe ▶ @HappyBearKids1\n\n"
        "#HappyBearKids #AnimalDance #KidsAnimals #ToddlerDance #3DAnimals "
        "#BabyVideo #AnimalsForKids #DanceForKids #25Minutes #KidsLearning"
    ),
    "ar": (
        "أهلاً بكم في Happy Bear Kids! 🐻\n\n"
        "٢٥ دقيقة من الحيوانات الثلاثية الأبعاد اللطيفة ترقص معاً في بيئاتها الطبيعية! "
        "شاهد أصدقاءنا الحيوانات بأسلوب بيكسار ثلاثي الأبعاد يرقصون على موسيقى مبهجة.\n\n"
        "سلسلة مجموعات الحيوانات تجمع عائلات حيوانية مختلفة من حول العالم. "
        "كل مجموعة ترقص بعمق ثلاثي الأبعاد رائع.\n\n"
        "🌟 المميزات الرئيسية:\n"
        "• حيوانات ثلاثية الأبعاد بأسلوب بيكسار مع ظلال وعمق واقعي\n"
        "• حركة متوازية ديناميكية — الحيوانات القريبة ترقص أقرب إليك!\n"
        "• موسيقى أصلية مبهجة بالإيقاع المناسب للأطفال الصغار\n"
        "• بدون نصوص أو أصوات — ممتع للجميع\n"
        "• ٢٥ دقيقة كاملة من المرح المتواصل\n\n"
        "🎵 موسيقى أصلية من هابي بير كيدز\n"
        "© Happy Bear Kids 2026 | اشترك ▶ @happybearkidsar\n\n"
        "#HappyBearKids #رقصة_الحيوانات #حيوانات_للأطفال #رقص_أطفال"
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
        "animal dance", "3d animals", "kids dance", "toddler video",
        "happy bear kids", "25 minutes", "baby video", "animal groups",
        ep_key, ep_key + " animals", "animal party", "dance for kids",
        "animal learning", "kids animals", "3d cartoon",
    ]
    meta = {
        "title": TITLES[ep_key][lang],
        "description": DESC[lang],
        "video_type": "dance_animals",
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
    out_name = f"animal_groups_{ep_key}_{DATE_STR}.mp4"
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
    parser.add_argument("--ep",         default=None, help="Render only this episode (farm/jungle/arctic/forest/savanna)")
    parser.add_argument("--regen-meta", action="store_true")
    parser.add_argument("--dry-run",    action="store_true")
    args = parser.parse_args()

    for d in (QUEUE_EN, QUEUE_AR):
        d.mkdir(parents=True, exist_ok=True)

    episodes = {k: v for k, v in EPISODES.items() if not args.ep or k == args.ep}
    if args.ep and not episodes:
        print(f"Unknown episode '{args.ep}'. Valid: {', '.join(EPISODES)}")
        return

    print(f"\n=== Animal Groups: {len(episodes)} episode(s) → EN + AR ===\n")
    ok = 0
    for ep_key, ep in episodes.items():
        print(f"[{ep_key}]")
        if render_episode(ep_key, ep, args.dry_run, args.regen_meta):
            ok += 1
    print(f"\nDone: {ok}/{len(episodes)}")


if __name__ == "__main__":
    main()
