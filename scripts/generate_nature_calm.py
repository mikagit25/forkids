#!/usr/bin/env python3
"""
Generate Nature Calm series — 6 soothing nature videos, 30 min, no text.
Uses DanceSpriteLong with 3D Pixar-style sprites (Rule 4 — no CSS shapes).
No text → EN+AR queues only. CNR nature visuals → use make_visual_theme.py.

Usage:
  python3 scripts/generate_nature_calm.py
  python3 scripts/generate_nature_calm.py --ep forest
  python3 scripts/generate_nature_calm.py --regen-meta
  python3 scripts/generate_nature_calm.py --dry-run
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

# 30 min = 1800s — calm, slow motion blocks for all themes (Rule 7: wobble on every block)
_CALM_BLOCKS = [
    {"startSec": 0,    "endSec": 60,   "motion": "FADEIN", "amplitude": 30,                              "wobble": True},
    {"startSec": 60,   "endSec": 660,  "motion": "BOB",    "period": 5.5,  "amplitude": 28,             "wobble": True},
    {"startSec": 660,  "endSec": 1260, "motion": "WAVE",   "period": 6.0,  "amplitude": 24, "waveDelay": 0.9, "wobble": True},
    {"startSec": 1260, "endSec": 1800, "motion": "BOB",    "period": 5.0,  "amplitude": 26,             "wobble": True},
]

# All Suno AI tracks — Kevin MacLeod FORBIDDEN
EPISODES = {
    "forest": {
        # Rule 4: 3D sprites only. Rule 6: main 450px, secondary 130-175px. Rule 8: unique seeds.
        "sprites": [
            {"path": "animals/owl_3d.png",       "size": 450, "posX": 0.50, "posY": 0.44, "seed": 1},
            {"path": "animals/frog_3d.png",       "size": 175, "posX": 0.22, "posY": 0.65, "seed": 2},
            {"path": "objects/butterfly_3d.png",  "size": 155, "posX": 0.75, "posY": 0.32, "seed": 3},
            {"path": "objects/orb_amber.png",     "size": 140, "posX": 0.15, "posY": 0.28, "seed": 4},
            {"path": "objects/star_sleep.png",    "size": 130, "posX": 0.82, "posY": 0.68, "seed": 5},
        ],
        "music": "The Glass Forest v2.mp3",
        "bgColor": "#0A2410", "bgColorEnd": "#0D2E14",
        "thumb_prompt": "magical enchanted forest at night, glowing amber fireflies, cute Pixar 3D owl perched on branch, friendly 3D frog on mossy log, soft green forest glow, calming baby video, 3D render style",
    },
    "ocean": {
        "sprites": [
            {"path": "objects/jellyfish_glow.png", "size": 450, "posX": 0.50, "posY": 0.42, "seed": 1},
            {"path": "objects/fish_deep.png",      "size": 185, "posX": 0.20, "posY": 0.65, "seed": 2},
            {"path": "objects/octopus_3d.png",     "size": 165, "posX": 0.78, "posY": 0.65, "seed": 3},
            {"path": "objects/star_3d.png",        "size": 140, "posX": 0.15, "posY": 0.30, "seed": 4},
            {"path": "objects/orb_amber.png",      "size": 130, "posX": 0.85, "posY": 0.28, "seed": 5},
        ],
        "music": "Tide and Piano v2.mp3",
        "bgColor": "#061628", "bgColorEnd": "#082030",
        "thumb_prompt": "serene deep ocean, glowing jellyfish floating gently, colorful deep-sea fish, cute Pixar 3D octopus, bioluminescent underwater scene, calming baby video, 3D render style",
    },
    "night_sky": {
        "sprites": [
            {"path": "objects/star_sleep.png",  "size": 450, "posX": 0.50, "posY": 0.44, "seed": 1},
            {"path": "objects/star_3d.png",     "size": 185, "posX": 0.18, "posY": 0.25, "seed": 2},
            {"path": "objects/star_silver.png", "size": 165, "posX": 0.80, "posY": 0.28, "seed": 3},
            {"path": "objects/orb_amber.png",   "size": 140, "posX": 0.15, "posY": 0.65, "seed": 4},
            {"path": "objects/star_3d.png",     "size": 130, "posX": 0.85, "posY": 0.68, "seed": 5},
        ],
        "music": "Moonlight on the Piano v2.mp3",
        "bgColor": "#080818", "bgColorEnd": "#0A0C22",
        "thumb_prompt": "beautiful starry night sky, large glowing golden sleepy star, silver stars twinkling, glowing amber orb, deep dark blue sky, calming baby video, Pixar 3D render style",
    },
    "meadow": {
        "sprites": [
            {"path": "objects/butterfly_3d.png", "size": 450, "posX": 0.50, "posY": 0.42, "seed": 1},
            {"path": "animals/duck_3d.png",      "size": 180, "posX": 0.22, "posY": 0.68, "seed": 2},
            {"path": "animals/unicorn_3d.png",   "size": 165, "posX": 0.78, "posY": 0.65, "seed": 3},
            {"path": "objects/cloud_3d.png",     "size": 145, "posX": 0.15, "posY": 0.25, "seed": 4},
            {"path": "objects/butterfly_3d.png", "size": 135, "posX": 0.82, "posY": 0.25, "seed": 5},
        ],
        "music": "The Golden Meadow v2.mp3",
        "bgColor": "#183808", "bgColorEnd": "#1E4A0A",
        "thumb_prompt": "peaceful sunny meadow, large colorful Pixar 3D butterfly, cute 3D yellow duck, friendly 3D unicorn, fluffy white cloud, golden sunlight, calming baby video, 3D render style",
    },
    "rain": {
        "sprites": [
            {"path": "objects/cloud_3d.png",  "size": 450, "posX": 0.50, "posY": 0.38, "seed": 1},
            {"path": "animals/frog_3d.png",   "size": 180, "posX": 0.25, "posY": 0.68, "seed": 2},
            {"path": "animals/duck_3d.png",   "size": 165, "posX": 0.75, "posY": 0.65, "seed": 3},
            {"path": "objects/cloud_3d.png",  "size": 145, "posX": 0.18, "posY": 0.25, "seed": 4},
            {"path": "objects/cloud_3d.png",  "size": 135, "posX": 0.82, "posY": 0.22, "seed": 5},
        ],
        "music": "Rain Etude in C Minor v2.mp3",
        "bgColor": "#0E1828", "bgColorEnd": "#121E30",
        "thumb_prompt": "gentle rain scene, big fluffy 3D cloud, cute Pixar 3D frog smiling in rain, friendly 3D duck with raindrops, soft blue-grey sky, calming baby video, 3D render style",
    },
    "sunset": {
        "sprites": [
            {"path": "animals/flamingo_3d.png",  "size": 450, "posX": 0.50, "posY": 0.44, "seed": 1},
            {"path": "animals/parrot_3d.png",    "size": 185, "posX": 0.20, "posY": 0.32, "seed": 2},
            {"path": "objects/butterfly_3d.png", "size": 155, "posX": 0.78, "posY": 0.30, "seed": 3},
            {"path": "objects/butterfly_3d.png", "size": 145, "posX": 0.15, "posY": 0.65, "seed": 4},
            {"path": "objects/orb_amber.png",    "size": 135, "posX": 0.85, "posY": 0.65, "seed": 5},
        ],
        "music": "Afternoon in F v2.mp3",
        "bgColor": "#28100A", "bgColorEnd": "#341408",
        "thumb_prompt": "beautiful golden sunset, elegant pink Pixar 3D flamingo, colorful 3D parrot, butterflies floating in warm orange-purple sky, calming baby video, 3D render style",
    },
}

TITLES = {
    "ocean":     {"en": "🌊 Calm Ocean for Babies | 30 Minutes | Happy Bear Kids",
                  "ar": "🌊 محيط هادئ للأطفال | ٣٠ دقيقة | Happy Bear Kids"},
    "forest":    {"en": "🌿 Enchanted Forest Calm | 30 Minutes | Happy Bear Kids",
                  "ar": "🌿 غابة ساحرة هادئة | ٣٠ دقيقة | Happy Bear Kids"},
    "night_sky": {"en": "⭐ Starry Night Sky | 30 Minutes | Happy Bear Kids",
                  "ar": "⭐ سماء ليلية مرصّعة بالنجوم | ٣٠ دقيقة | Happy Bear Kids"},
    "meadow":    {"en": "🌸 Peaceful Meadow | 30 Minutes | Happy Bear Kids",
                  "ar": "🌸 مرج هادئ للأطفال | ٣٠ دقيقة | Happy Bear Kids"},
    "rain":      {"en": "🌧️ Gentle Rain Calm | 30 Minutes | Happy Bear Kids",
                  "ar": "🌧️ مطر هادئ للأطفال | ٣٠ دقيقة | Happy Bear Kids"},
    "sunset":    {"en": "🌅 Sunset Calm for Babies | 30 Minutes | Happy Bear Kids",
                  "ar": "🌅 غروب هادئ للأطفال | ٣٠ دقيقة | Happy Bear Kids"},
}

DESC = {
    "en": (
        "Welcome to Happy Bear Kids! 🐻\n\n"
        "30 minutes of beautiful, calming nature-inspired visuals with adorable 3D characters. "
        "Cute animals and nature friends gently float and bob to peaceful music — perfect for "
        "calming babies, helping toddlers relax, and creating a soothing screen-time experience.\n\n"
        "Our Nature Calm series brings the tranquillity of the natural world into your home "
        "through charming, soft-moving 3D characters in nature settings. No sudden movements, no "
        "surprises — just gentle, floating friends that soothe and delight.\n\n"
        "🌟 Key features:\n"
        "• Adorable 3D Pixar-style nature characters floating gently\n"
        "• Very low BPM music chosen specifically for calm and relaxation\n"
        "• No bright flashes or sudden changes — gentle transitions only\n"
        "• No words or voices — universally enjoyable for every child\n"
        "• 30 full minutes of uninterrupted calm visual experience\n\n"
        "👶 Perfect for:\n"
        "• Calming a fussy or overtired baby or toddler\n"
        "• Background during nap time preparation\n"
        "• Gentle screen time that does not overstimulate\n"
        "• Visual tracking practice for infants aged 0-6 months\n"
        "• Winding down after a busy or stimulating day\n\n"
        "🎯 Educational and developmental value:\n"
        "• Colour recognition through nature-inspired 3D characters\n"
        "• Visual tracking as characters drift slowly and predictably across the screen\n"
        "• Sensory regulation — gentle movement helps reduce visual stress in infants\n"
        "• Rhythm awareness through soft, slow music that supports brain development\n"
        "• Attention and focus development through simple, predictable movement patterns\n\n"
        "No loud sounds, no surprises, no talking — just 30 minutes of pure, soothing "
        "nature friends floating peacefully on screen.\n\n"
        "🎵 Original music by Happy Bear Kids (AI-generated, © 2026)\n\n"
        "© Happy Bear Kids 2026 — All rights reserved\n"
        "New videos every week! Subscribe ▶ @HappyBearKids1\n\n"
        "#HappyBearKids #CalmBabyVideo #NatureCalm #SoothingBaby #BabyCalm "
        "#ToddlerCalm #30Minutes #BabyRelax #CalmVisuals #NatureForBabies"
    ),
    "ar": (
        "أهلاً بكم في Happy Bear Kids! 🐻\n\n"
        "٣٠ دقيقة من المرئيات الطبيعية الهادئة مع شخصيات ثلاثية الأبعاد لطيفة. "
        "حيوانات وأصدقاء الطبيعة يطفون بلطف على موسيقى سلمية — مثالية لتهدئة الأطفال الرضّع والصغار.\n\n"
        "سلسلة الطبيعة الهادئة تجلب سكينة الطبيعة إلى منزلكم من خلال شخصيات ثلاثية الأبعاد ناعمة الحركة. "
        "لا حركات مفاجئة، لا مفاجآت — فقط أصدقاء هادئون يطفون ويُسعدون.\n\n"
        "🌟 المميزات الرئيسية:\n"
        "• شخصيات طبيعة ثلاثية الأبعاد تطفو بلطف\n"
        "• موسيقى منخفضة الإيقاع مختارة خصيصاً للاسترخاء\n"
        "• لا وميض أو تغييرات مفاجئة\n"
        "• بدون كلمات أو أصوات\n"
        "• ٣٠ دقيقة كاملة من الهدوء البصري\n\n"
        "👶 مناسب لـ:\n"
        "• تهدئة الطفل المتعب أو المتهيّج\n"
        "• خلفية هادئة أثناء الاستعداد للنوم\n"
        "• وقت شاشة لطيف لا يفرط في التحفيز\n\n"
        "🎵 موسيقى أصلية من هابي بير كيدز\n"
        "© Happy Bear Kids 2026 | اشترك ▶ @happybearkidsar\n\n"
        "#HappyBearKids #هدوء_الطبيعة #تهدئة_الطفل #فيديو_أطفال_هادئ #رضيع"
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
    tags = ["nature calm", "baby calm", "soothing", "toddler relax", "happy bear kids",
            "30 minutes", "baby video", "nature", ep_key.replace("_", " "), "3d animals"]
    meta = {
        "title": TITLES[ep_key][lang],
        "description": DESC[lang],
        "video_type": "nature_calm",
        "theme": ep_key,
        "language": lang,
        "duration_minutes": 30,
        "is_short": False,
        "status": "public",
        "made_for_kids": True,
        "tags": tags,
    }
    meta_path = queue / f"meta_{Path(out_name).stem}.yaml"
    with open(meta_path, "w", encoding="utf-8") as f:
        yaml.dump(meta, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def _render_episode(ep_key: str, ep: dict, out_path: Path, dry_run: bool) -> bool:
    props = json.dumps({
        "sprites": ep["sprites"],
        "blocks": _CALM_BLOCKS,
        "bgColor": ep["bgColor"],
        "bgColorEnd": ep.get("bgColorEnd", ep["bgColor"]),
        "musicFile": ep["music"],
        "wobble": True,
    })
    cmd = ["npx", "remotion", "render", "DanceSpriteLong", str(out_path),
           "--props", props, "--log", "error"]
    if dry_run:
        print(f"    [DRY RUN] DanceSpriteLong {ep_key} → {out_path.name}")
        return True
    out_path.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(cmd, cwd=str(REMOTION), timeout=86400)
    return r.returncode == 0


def render_episode(ep_key: str, ep: dict, dry_run: bool, regen_meta: bool) -> bool:
    out_name = f"nature_calm_{ep_key}_{DATE_STR}.mp4"
    en_mp4   = QUEUE_EN / out_name
    ar_mp4   = QUEUE_AR / out_name

    # nature_calm is kids content — ID/CNR queue blocked per CLAUDE.md
    # For CNR nature visuals → use make_visual_theme.py (AI images + Musopen classical)

    # Render once (no text/voice difference between EN and AR)
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

    # Copy to AR queue (identical video, no language difference for no-text content)
    if (en_mp4.exists() or dry_run) and not ar_mp4.exists():
        if not dry_run:
            shutil.copy2(str(en_mp4), str(ar_mp4))
            print(f"  ✓ copied → queue_ar/{out_name}")
        else:
            print(f"    [DRY RUN] copy → queue_ar/{out_name}")
    elif ar_mp4.exists():
        print(f"  EXISTS {ep_key} (ar)")

    # Meta + thumbnails per language
    for lang, queue, mp4 in [("en", QUEUE_EN, en_mp4), ("ar", QUEUE_AR, ar_mp4)]:
        if mp4.exists() or dry_run or regen_meta:
            make_meta(ep_key, lang, queue, out_name)
            generate_thumbnail(ep_key, ep, queue, out_name, lang)

    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ep",       default=None, help="Render only this episode key (e.g. forest)")
    parser.add_argument("--regen-meta", action="store_true", help="Regenerate meta+thumbnails only")
    parser.add_argument("--dry-run",    action="store_true")
    args = parser.parse_args()

    for d in (QUEUE_EN, QUEUE_AR):
        d.mkdir(parents=True, exist_ok=True)

    episodes = {k: v for k, v in EPISODES.items() if not args.ep or k == args.ep}
    if args.ep and not episodes:
        print(f"Unknown episode key '{args.ep}'. Valid: {', '.join(EPISODES)}")
        return

    print(f"\n=== Nature Calm: {len(episodes)} episode(s) → EN + AR ===\n")
    ok = 0
    for ep_key, ep in episodes.items():
        print(f"[{ep_key}]")
        if render_episode(ep_key, ep, args.dry_run, args.regen_meta):
            ok += 1
    print(f"\nDone: {ok}/{len(episodes)}")


if __name__ == "__main__":
    main()
