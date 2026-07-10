#!/usr/bin/env python3
"""
Shadow Puppet Show — series of 30-min silhouette dance videos.

Uses black silhouette sprites (from generate_silhouettes.py) on warm
parchment/lantern backgrounds — classic shadow-theatre aesthetic.
DanceSpriteLong30 composition: all existing motion modules (BOB/SWAY/SPIN/
ORBIT/BOUNCE/MARCH/WAVE/DRIFT/PULSE).

3 themes × 3 channels = 9 videos total.

Usage:
  python3 scripts/generate_shadow_puppet.py
  python3 scripts/generate_shadow_puppet.py --themes animals
  python3 scripts/generate_shadow_puppet.py --dry-run
  python3 scripts/generate_shadow_puppet.py --regen-meta
  python3 scripts/generate_shadow_puppet.py --force
"""
import argparse, base64, json, subprocess, time
from datetime import datetime
from pathlib import Path

import requests
import yaml

ROOT         = Path(__file__).resolve().parent.parent
QUEUE_EN     = ROOT / "output" / "queue"
QUEUE_AR     = ROOT / "output" / "queue_ar"
QUEUE_ID     = ROOT / "output" / "queue_id"
TOGETHER_KEY = (ROOT / "credentials" / "together_api_key.txt").read_text().strip()
TOGETHER_URL = "https://api.together.xyz/v1/images/generations"

QUEUES = {"en": QUEUE_EN, "ar": QUEUE_AR, "id": QUEUE_ID}

# ── Sprite grid positions ──────────────────────────────────────────────────────
GRID_8 = [
    {"posX": 0.12, "posY": 0.28}, {"posX": 0.37, "posY": 0.22},
    {"posX": 0.63, "posY": 0.22}, {"posX": 0.88, "posY": 0.28},
    {"posX": 0.12, "posY": 0.68}, {"posX": 0.37, "posY": 0.74},
    {"posX": 0.63, "posY": 0.74}, {"posX": 0.88, "posY": 0.68},
]
GRID_6 = [
    {"posX": 0.18, "posY": 0.28}, {"posX": 0.50, "posY": 0.22}, {"posX": 0.82, "posY": 0.28},
    {"posX": 0.18, "posY": 0.68}, {"posX": 0.50, "posY": 0.74}, {"posX": 0.82, "posY": 0.68},
]


def make_sprites(names: list, grid: list, size: int = 240) -> list:
    return [
        {"path": n, "size": size,
         "posX": grid[i]["posX"], "posY": grid[i]["posY"], "seed": i + 1}
        for i, n in enumerate(names)
    ]


def make_blocks() -> list:
    """30-min motion sequence — slow, theatrical pacing suits shadow puppets."""
    amp = 70
    per = 3.5
    return [
        {"startSec":    0, "endSec":  180, "motion": "SWAY",   "period": per,       "amplitude": amp},
        {"startSec":  180, "endSec":  360, "motion": "BOB",    "period": per,       "amplitude": amp},
        {"startSec":  360, "endSec":  540, "motion": "WAVE",   "period": per,       "amplitude": amp, "waveDelay": 0.30},
        {"startSec":  540, "endSec":  720, "motion": "BOUNCE", "period": per,       "amplitude": amp},
        {"startSec":  720, "endSec":  900, "motion": "ORBIT",  "period": per * 1.6, "amplitude": amp, "orbitCenterX": 0.50, "orbitCenterY": 0.45},
        {"startSec":  900, "endSec": 1080, "motion": "DRIFT",  "period": per * 1.4, "amplitude": amp},
        {"startSec": 1080, "endSec": 1260, "motion": "MARCH",  "period": 13,        "amplitude": amp, "bobAmplitude": 30},
        {"startSec": 1260, "endSec": 1440, "motion": "PULSE",  "period": per,       "amplitude": 35},
        {"startSec": 1440, "endSec": 1620, "motion": "SWAY",   "period": per * 1.2, "amplitude": amp},
        {"startSec": 1620, "endSec": 1800, "motion": "BOB",    "period": per,       "amplitude": amp},
    ]


# ── Theme definitions ──────────────────────────────────────────────────────────
# Backgrounds: warm golden/parchment — classic lantern shadow-theatre look.
# Each channel uses different music + slightly different bg tint → unique fingerprint.
THEMES = {
    "animals": {
        "sprites": make_sprites([
            "silhouettes/animals/bear_3d.png",
            "silhouettes/animals/elephant_3d.png",
            "silhouettes/animals/fox_3d.png",
            "silhouettes/animals/rabbit_3d.png",
            "silhouettes/animals/penguin_3d.png",
            "silhouettes/animals/owl_3d.png",
            "silhouettes/animals/frog_3d.png",
            "silhouettes/animals/cat_3d.png",
        ], GRID_8),
        "blocks": make_blocks(),
        "bgEffect": "sparkles",
        "channels": {
            "en": {"music": "Sneaky Snitch.mp3",   "bgColor": "#FFF8DC", "bgColorEnd": "#FFE5A0", "accentColor": "#D4A017"},
            "ar": {"music": "Gymnopedie No 1.mp3",  "bgColor": "#FFFAED", "bgColorEnd": "#FFE8B0", "accentColor": "#C89B20"},
            "id": {"music": "Walking Along.mp3",    "bgColor": "#FFF5E0", "bgColorEnd": "#FFD98A", "accentColor": "#C8901A"},
        },
        "thumb_prompt": (
            "shadow puppet theatre show, black silhouettes of cute animals — bear elephant fox "
            "rabbit penguin owl frog cat — dancing on warm golden glowing screen, "
            "Chinese shadow theatre style, warm amber light, magical theatrical atmosphere, "
            "no background details, pure silhouette art, cinematic"
        ),
        "titles": {
            "en": "Shadow Puppet Show — Animals 🐾 | 30 Min | Happy Bear Kids",
            "ar": "مسرح الظل — الحيوانات 🐾 | 30 دقيقة | هابي بير كيدز",
            "id": "Pertunjukan Bayangan — Hewan 🐾 | 30 Menit | Happy Bear Kids",
        },
        "tags": [
            "shadow puppet", "shadow theatre", "silhouette animation",
            "animal shadows", "kids shadow show", "toddler visual",
            "baby sensory", "shadow dance", "happy bear kids",
            "30 minutes", "no talking", "calm kids video",
        ],
    },

    "fruits": {
        "sprites": make_sprites([
            "silhouettes/fruits/apple_3d.png",
            "silhouettes/fruits/banana_3d.png",
            "silhouettes/fruits/strawberry_3d.png",
            "silhouettes/fruits/pineapple_3d.png",
            "silhouettes/fruits/grapes_3d.png",
            "silhouettes/fruits/orange_3d.png",
            "silhouettes/fruits/watermelon_3d.png",
            "silhouettes/fruits/cherry_3d.png",
        ], GRID_8),
        "blocks": make_blocks(),
        "bgEffect": "sparkles",
        "channels": {
            "en": {"music": "Quirky Dog.mp3",        "bgColor": "#FFF8DC", "bgColorEnd": "#FFE09A", "accentColor": "#D4A820"},
            "ar": {"music": "Crinoline Dreams.mp3",   "bgColor": "#FFFAED", "bgColorEnd": "#FFE4B0", "accentColor": "#C8941C"},
            "id": {"music": "Heartwarming.mp3",       "bgColor": "#FFF5E0", "bgColorEnd": "#FFD890", "accentColor": "#C8881A"},
        },
        "thumb_prompt": (
            "shadow puppet theatre show, black silhouettes of cute fruits — apple banana "
            "strawberry pineapple grapes orange watermelon cherry — dancing on warm golden "
            "glowing screen, shadow theatre style, warm amber lantern light, "
            "magical theatrical atmosphere, pure silhouette art, cinematic"
        ),
        "titles": {
            "en": "Shadow Puppet Show — Fruits 🍎 | 30 Min | Happy Bear Kids",
            "ar": "مسرح الظل — الفواكه 🍎 | 30 دقيقة | هابي بير كيدز",
            "id": "Pertunjukan Bayangan — Buah 🍎 | 30 Menit | Happy Bear Kids",
        },
        "tags": [
            "shadow puppet", "shadow theatre", "silhouette animation",
            "fruit shadows", "kids shadow show", "toddler visual",
            "baby sensory", "shadow dance", "happy bear kids",
            "30 minutes", "no talking", "fruit learning",
        ],
    },

    "mixed": {
        "sprites": make_sprites([
            "silhouettes/animals/lion_3d.png",
            "silhouettes/animals/monkey_3d.png",
            "silhouettes/animals/panda_3d.png",
            "silhouettes/animals/tiger_3d.png",
            "silhouettes/vegetables/carrot_3d.png",
            "silhouettes/vegetables/broccoli_3d.png",
            "silhouettes/fruits/lemon_3d.png",
            "silhouettes/fruits/peach_3d.png",
        ], GRID_8),
        "blocks": make_blocks(),
        "bgEffect": "sparkles",
        "channels": {
            "en": {"music": "Salty Ditty.mp3",      "bgColor": "#FFF8DC", "bgColorEnd": "#FFE59C", "accentColor": "#D4A21A"},
            "ar": {"music": "George Street Shuffle.mp3", "bgColor": "#FFFAED", "bgColorEnd": "#FFE0AC", "accentColor": "#C89218"},
            "id": {"music": "Overworld.mp3",         "bgColor": "#FFF5E0", "bgColorEnd": "#FFD898", "accentColor": "#C88A18"},
        },
        "thumb_prompt": (
            "shadow puppet theatre show, black silhouettes of mixed characters — lion monkey "
            "panda tiger carrot broccoli lemon peach — dancing on warm amber glowing screen, "
            "shadow puppet show style, warm golden lantern light, magical theatrical scene, "
            "pure silhouette art, no text, cinematic kids animation"
        ),
        "titles": {
            "en": "Shadow Puppet Show — Mix 🎭 | 30 Min | Happy Bear Kids",
            "ar": "مسرح الظل — مزيج 🎭 | 30 دقيقة | هابي بير كيدز",
            "id": "Pertunjukan Bayangan — Campuran 🎭 | 30 Menit | Happy Bear Kids",
        },
        "tags": [
            "shadow puppet", "shadow theatre", "silhouette animation",
            "mixed characters", "kids shadow show", "toddler visual",
            "baby sensory", "shadow dance", "happy bear kids",
            "30 minutes", "no talking",
        ],
    },
}


# ── Descriptions ──────────────────────────────────────────────────────────────
def make_desc(lang: str, title: str, theme_key: str) -> str:
    if lang == "en":
        return (
            f"🎭 {title}\n\n"
            f"Welcome to the Shadow Puppet Show! Watch beautiful black silhouettes dance, "
            f"sway and move against a warm golden glow — inspired by the ancient art of shadow theatre.\n\n"
            f"Eight mysterious shapes float, bounce and perform to gentle music. "
            f"No text, no words — pure visual magic for babies and toddlers of any language.\n\n"
            f"✨ Silhouette art is one of the most visually captivating things for young eyes. "
            f"The high contrast between dark shapes and warm glowing background naturally "
            f"draws and holds a baby's attention.\n\n"
            f"🎯 Perfect for: visual stimulation, focus development, calm background play, "
            f"sensory exploration, winding down before sleep.\n\n"
            f"👶 Age: 0–4 years | 📺 30 minutes continuous | 🔇 No talking\n\n"
            f"🎵 Music: Kevin MacLeod (incompetech.com) — Creative Commons CC BY 4.0\n\n"
            f"🔔 Subscribe to Happy Bear Kids for new videos every day!\n\n"
            f"#ShadowPuppet #ShadowTheatre #SilhouetteAnimation #BabySensory "
            f"#ToddlerVisual #HappyBearKids #KidsAnimation #ShadowDance "
            f"#VisualStimulation #BabyVideo #NoTalking #CalmKidsVideo"
        )
    if lang == "ar":
        return (
            f"🎭 {title}\n\n"
            f"أهلاً بكم في مسرح الظل! شاهدوا ظلالاً سوداء جميلة ترقص وتتأرجح وتتحرك "
            f"أمام وهج ذهبي دافئ — مستوحى من الفن القديم لمسرح الظل.\n\n"
            f"ثمانية أشكال غامضة تطفو وترتد وتؤدي على موسيقى هادئة. "
            f"لا نصوص، لا كلمات — سحر بصري خالص للرضع والأطفال الصغار من أي لغة.\n\n"
            f"✨ فن السيلويت هو من أكثر الأشياء جاذبية بصرياً للعيون الصغيرة. "
            f"التباين العالي بين الأشكال الداكنة والخلفية الدافئة المضيئة "
            f"يستقطب انتباه الرضيع ويُبقيه بشكل طبيعي.\n\n"
            f"🎯 مثالي لـ: التحفيز البصري، تطوير التركيز، التشغيل الهادئ في الخلفية، "
            f"الاستكشاف الحسي، الاسترخاء قبل النوم.\n\n"
            f"👶 العمر: 0–4 سنوات | 📺 30 دقيقة متواصلة | 🔇 بدون كلام\n\n"
            f"🎵 Kevin MacLeod — Creative Commons CC BY 4.0\n\n"
            f"🔔 اشترك في هابي بير كيدز للمزيد من الفيديوهات!\n\n"
            f"#مسرح_الظل #ظلال #رسوم_سيلويت #تحفيز_بصري "
            f"#هابي_بير_كيدز #رسوم_أطفال #بدون_كلام #رضع"
        )
    # id
    return (
        f"🎭 {title}\n\n"
        f"Selamat datang di Pertunjukan Bayangan! Saksikan siluet hitam yang indah menari, "
        f"bergoyang dan bergerak di depan cahaya emas yang hangat — terinspirasi dari "
        f"seni kuno teater bayangan.\n\n"
        f"Delapan bentuk misterius melayang, memantul dan beraksi mengikuti musik lembut. "
        f"Tanpa teks, tanpa kata — keajaiban visual murni untuk bayi dan balita dari bahasa apapun.\n\n"
        f"✨ Seni siluet adalah salah satu hal yang paling memikat secara visual untuk mata bayi. "
        f"Kontras tinggi antara bentuk gelap dan latar belakang hangat yang bercahaya "
        f"secara alami menarik dan menahan perhatian bayi.\n\n"
        f"🎯 Sempurna untuk: stimulasi visual, pengembangan fokus, tayangan latar yang tenang, "
        f"eksplorasi sensorik, bersantai sebelum tidur.\n\n"
        f"👶 Usia: 0–4 tahun | 📺 30 menit terus-menerus | 🔇 Tanpa suara\n\n"
        f"🎵 Musik: Kevin MacLeod (incompetech.com) — Creative Commons CC BY 4.0\n\n"
        f"🔔 Subscribe Happy Bear Kids Indonesia untuk video baru setiap hari!\n\n"
        f"#PertunjukanBayangan #TeaterBayangan #AnimasiSiluet #StimulasiBayi "
        f"#HappyBearKids #AnimasiAnak #TanpaSuara #BayiBelajar #Balita"
    )


# ── Thumbnail ─────────────────────────────────────────────────────────────────
def _load_gat():
    import importlib.util
    spec = importlib.util.spec_from_file_location("gat", ROOT / "scripts" / "generate_ai_thumbs.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def generate_thumb(prompt: str, out_path: Path) -> bool:
    try:
        gat = _load_gat()
        img = gat.together_generate_image(prompt, TOGETHER_KEY)
        if img:
            out_path.write_bytes(gat.resize_to_720p(img))
            print(f"    Thumb → {out_path.name} ({out_path.stat().st_size // 1024}KB)")
            return True
        print(f"    Thumb error: API returned no image")
        return False
    except Exception as e:
        print(f"    Thumb error: {e}")
        return False


# ── Render ────────────────────────────────────────────────────────────────────
def render_video(theme_key: str, t: dict, lang: str, ch: dict,
                 out_mp4: Path, dry_run: bool) -> bool:
    props = {
        "sprites":     t["sprites"],
        "blocks":      t["blocks"],
        "bgColor":     ch["bgColor"],
        "bgColorEnd":  ch.get("bgColorEnd", ch["bgColor"]),
        "accentColor": ch.get("accentColor", "#D4A017"),
        "musicFile":   ch["music"],
        "volume":      0.20,
        "bgEffect":    t.get("bgEffect", "sparkles"),
        "nightMode":   False,
        "wobble":      False,   # silhouettes look cleaner without wobble outline
    }
    cmd = [
        "npx", "remotion", "render",
        "src/index.ts", "DanceSpriteLong30",
        str(out_mp4),
        "--props", json.dumps(props),
        "--concurrency", "2",
    ]
    print(f"  [{lang.upper()}] Rendering → {out_mp4.name}")
    print(f"         music={ch['music']}  bg={ch['bgColor']}")
    if dry_run:
        print(f"  [dry-run] skipped")
        return True
    result = subprocess.run(cmd, cwd=ROOT / "remotion", capture_output=False)
    return result.returncode == 0


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--themes",    nargs="+", default=list(THEMES.keys()),
                        choices=list(THEMES.keys()))
    parser.add_argument("--langs",     nargs="+", default=["en", "ar", "id"])
    parser.add_argument("--force",     action="store_true")
    parser.add_argument("--dry-run",   action="store_true")
    parser.add_argument("--regen-meta", action="store_true",
                        help="Re-write meta + thumbnail only (skip render)")
    args = parser.parse_args()

    date = datetime.now().strftime("%Y%m%d")

    for theme_key in args.themes:
        t = THEMES[theme_key]
        print(f"\n{'='*60}\n[shadow_{theme_key}] Processing...\n{'='*60}")

        for lang in args.langs:
            ch          = t["channels"][lang]
            q           = QUEUES[lang]
            lang_sfx    = f"_{lang}" if lang != "en" else ""
            mp4         = q / f"shadow_{theme_key}{lang_sfx}_{date}.mp4"
            meta_path   = q / f"meta_shadow_{theme_key}{lang_sfx}_{date}.yaml"
            thumb_path  = q / f"thumb_shadow_{theme_key}{lang_sfx}_{date}.png"

            # ── Render ──────────────────────────────────────────────────────
            if not args.regen_meta:
                if mp4.exists() and not args.force:
                    print(f"  [{lang.upper()}] MP4 exists — skip render")
                else:
                    ok = render_video(theme_key, t, lang, ch, mp4, args.dry_run)
                    if not ok:
                        print(f"  [{lang.upper()}] RENDER FAILED — skip meta/thumb")
                        continue

            # ── Meta ────────────────────────────────────────────────────────
            if mp4.exists() or args.dry_run or args.regen_meta:
                title = t["titles"][lang]
                meta  = {
                    "title":       title,
                    "description": make_desc(lang, title, theme_key),
                    "tags":        t["tags"],
                    "video_type":  "shadow_puppet",
                    "theme":       f"shadow_{theme_key}",
                    "language":    lang,
                    "is_short":    False,
                    "status":      "public",
                }
                meta_path.write_text(
                    yaml.dump(meta, allow_unicode=True, default_flow_style=False, sort_keys=False)
                )
                print(f"  [{lang.upper()}] Meta → {meta_path.name}")

            # ── Thumbnail ───────────────────────────────────────────────────
            prompt = t["thumb_prompt"]
            if lang == "ar":
                prompt += ", no text, no letters, no words, no numbers"
            if not thumb_path.exists() or args.force or args.regen_meta:
                print(f"  [{lang.upper()}] Generating thumbnail...")
                if not args.dry_run:
                    generate_thumb(prompt, thumb_path)
                    time.sleep(4)
            else:
                print(f"  [{lang.upper()}] Thumb exists — skip")

    print(f"\nAll done.")


if __name__ == "__main__":
    main()
