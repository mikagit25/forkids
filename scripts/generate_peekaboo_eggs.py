#!/usr/bin/env python3
"""
generate_peekaboo_eggs.py — Peek-a-Boo Eggs series (magic egg hatching).
No text → universal → EN + AR + ID. Pig → Panda swap handled per language.

6 episodes × 3 channels = 18 long videos (30 min each via FFmpeg ×6).
Each episode has a different animal theme. Short version also renderable.

Usage:
  python3 scripts/generate_peekaboo_eggs.py --list
  python3 scripts/generate_peekaboo_eggs.py --episodes all [--dry-run] [--force]
  python3 scripts/generate_peekaboo_eggs.py --episodes farm jungle
  python3 scripts/generate_peekaboo_eggs.py --shorts --episodes farm
  python3 scripts/generate_peekaboo_eggs.py --regen-meta
"""
import argparse, base64, json, shutil, subprocess, sys, time, yaml
from datetime import datetime
from pathlib import Path

ROOT      = Path(__file__).resolve().parent.parent
REMOTION  = ROOT / "remotion"
QUEUE_EN  = ROOT / "output" / "queue"
QUEUE_AR  = ROOT / "output" / "queue_ar"
QUEUE_ID  = ROOT / "output" / "queue_id"
LOOPS_DIR = ROOT / "output" / "_peekaboo_egg_loops"
TOGETHER_KEY_FILE = ROOT / "credentials" / "together_api_key.txt"
TOGETHER_URL   = "https://api.together.xyz/v1/images/generations"
TOGETHER_MODEL = "black-forest-labs/FLUX.1-schnell"
DATE_STR  = datetime.now().strftime("%Y%m%d")
COMP_LOOP  = "PeekABooEggsLoop"   # 5-min loop composition
DUR_LABEL  = "30 min"
SERIES_EN  = "Magic Eggs"
SERIES_AR  = "بيضات سحرية"
SERIES_ID  = "Telur Ajaib"

# ── Music rotation per language (unique fingerprint per channel) ───────────────
LANG_MUSIC = {
    "farm":    {"en": "Happy Happy Game Show.mp3", "ar": "Monkeys Spinning Monkeys.mp3", "id": "Hyperfun.mp3"},
    "jungle":  {"en": "Carefree.mp3",              "ar": "Merry Go.mp3",                 "id": "Walking Along.mp3"},
    "pets":    {"en": "Quirky Dog.mp3",             "ar": "Heartwarming.mp3",             "id": "Life of Riley.mp3"},
    "arctic":  {"en": "Wholesome.mp3",              "ar": "Salty Ditty.mp3",              "id": "Crinoline Dreams.mp3"},
    "safari":  {"en": "Pinball Spring.mp3",         "ar": "Fluffing a Duck.mp3",          "id": "Sneaky Snitch.mp3"},
    "night":   {"en": "Gymnopedie No 1.mp3",        "ar": "Pixelland.mp3",                "id": "Overworld.mp3"},
}

# ── Egg definitions per episode ────────────────────────────────────────────────
# "pig" entries are auto-replaced with panda for AR/ID languages
def _egg(shell, spot, sprite, accent, bg, audio=None):
    return {"shellColor": shell, "spotColor": spot, "animalSprite": sprite,
            "accentColor": accent, "bgColor": bg, "audio": audio}

EPISODES = {
    "farm": {
        "name_en": "Farm Animals",
        "name_ar": "حيوانات المزرعة",
        "name_id": "Hewan Pertanian",
        "eggs": [
            _egg("#7BC67E", "#A5D6A7", "sprites/animals/cow.png",    "#66BB6A", "#F1F8E9"),
            _egg("#FFF176", "#FFF9C4", "sprites/animals/duck.png",    "#FDD835", "#FFFDE7"),
            _egg("#F48FB1", "#F8BBD0", "sprites/animals/pig.png",     "#EC407A", "#FCE4EC"),
            _egg("#80DEEA", "#B2EBF2", "sprites/animals/frog.png",    "#26C6DA", "#E0F7FA"),
            _egg("#FFCC80", "#FFE0B2", "sprites/animals/rabbit.png",  "#FFA726", "#FFF3E0"),
            _egg("#CE93D8", "#E1BEE7", "sprites/animals/cat.png",     "#AB47BC", "#F3E5F5"),
        ],
        "thumb_prompt": "cute cartoon farm animals hatching from colorful eggs — cow, duck, frog, rabbit, cat, Pixar 3D style, cheerful children's animation, bright green farm background",
    },
    "jungle": {
        "name_en": "Jungle Animals",
        "name_ar": "حيوانات الغابة",
        "name_id": "Hewan Hutan",
        "eggs": [
            _egg("#FFAB40", "#FFD180", "sprites/animals/lion.png",      "#FF6D00", "#FFF3E0",
                 audio="this_is_a_lion__lion__lion.mp3"),
            _egg("#CE93D8", "#E1BEE7", "sprites/animals/elephant.png",  "#7E57C2", "#EDE7F6"),
            _egg("#A5D6A7", "#C8E6C9", "sprites/animals/monkey.png",    "#2E7D32", "#E8F5E9"),
            _egg("#FF8A65", "#FFAB91", "sprites/animals/tiger.png",     "#E64A19", "#FBE9E7"),
            _egg("#80DEEA", "#B2EBF2", "sprites/animals/frog.png",      "#26C6DA", "#E0F7FA"),
            _egg("#F48FB1", "#F8BBD0", "sprites/animals/parrot.png",    "#E91E63", "#FCE4EC"),
        ],
        "thumb_prompt": "cute cartoon jungle animals hatching from colorful eggs — lion, elephant, monkey, tiger, parrot, Pixar 3D style, tropical forest background, vibrant colors",
    },
    "pets": {
        "name_en": "Cute Pets",
        "name_ar": "الحيوانات الأليفة",
        "name_id": "Hewan Peliharaan",
        "eggs": [
            _egg("#FF8A65", "#FFAB91", "sprites/animals/cat.png",    "#FF5722", "#FBE9E7"),
            _egg("#64B5F6", "#90CAF9", "sprites/animals/dog.png",    "#1565C0", "#E3F2FD"),
            _egg("#F48FB1", "#F8BBD0", "sprites/animals/rabbit.png", "#E91E63", "#FCE4EC"),
            _egg("#A5D6A7", "#C8E6C9", "sprites/animals/frog.png",   "#388E3C", "#E8F5E9"),
            _egg("#CE93D8", "#E1BEE7", "sprites/animals/owl.png",    "#7B1FA2", "#F3E5F5"),
            _egg("#80CBC4", "#B2DFDB", "sprites/animals/penguin.png","#00695C", "#E0F2F1"),
        ],
        "thumb_prompt": "cute cartoon pet animals hatching from colorful eggs — cat, dog, rabbit, owl, penguin, Pixar 3D style, cozy home background, pastel colors",
    },
    "arctic": {
        "name_en": "Arctic Friends",
        "name_ar": "أصدقاء القطب الشمالي",
        "name_id": "Sahabat Kutub",
        "eggs": [
            _egg("#E3F2FD", "#BBDEFB", "sprites/animals/polar_bear_3d.png", "#1565C0", "#E8EAF6"),
            _egg("#263238", "#37474F", "sprites/animals/penguin.png",        "#546E7A", "#ECEFF1"),
            _egg("#CE93D8", "#E1BEE7", "sprites/animals/owl.png",            "#7B1FA2", "#F3E5F5"),
            _egg("#FF8A65", "#FFAB91", "sprites/animals/fox.png",            "#E64A19", "#FBE9E7"),
            _egg("#A5D6A7", "#C8E6C9", "sprites/animals/rabbit.png",         "#388E3C", "#E8F5E9"),
        ],
        "thumb_prompt": "cute arctic animals hatching from icy blue eggs — polar bear, penguin, owl, fox, rabbit, Pixar 3D style, snowy tundra background, cool blue colors",
    },
    "safari": {
        "name_en": "Safari Adventure",
        "name_ar": "مغامرة السفاري",
        "name_id": "Petualangan Safari",
        "eggs": [
            _egg("#FFAB40", "#FFD180", "sprites/animals/lion.png",     "#FF6D00", "#FFF3E0",
                 audio="this_is_a_lion__lion__lion.mp3"),
            _egg("#CE93D8", "#E1BEE7", "sprites/animals/elephant.png", "#7E57C2", "#EDE7F6"),
            _egg("#FF8A65", "#FFAB91", "sprites/animals/tiger.png",    "#E64A19", "#FBE9E7"),
            _egg("#A5D6A7", "#C8E6C9", "sprites/animals/monkey.png",   "#388E3C", "#E8F5E9"),
            _egg("#FFCC80", "#FFE0B2", "sprites/animals/bear.png",     "#FFA726", "#FFF3E0"),
            _egg("#80DEEA", "#B2EBF2", "sprites/animals/flamingo_3d.png","#0097A7","#E0F7FA"),
        ],
        "thumb_prompt": "cute safari animals hatching from golden eggs — lion, elephant, tiger, monkey, flamingo, Pixar 3D style, sunny savanna background",
    },
    "night": {
        "name_en": "Night Friends",
        "name_ar": "أصدقاء الليل",
        "name_id": "Sahabat Malam",
        "eggs": [
            _egg("#9575CD", "#B39DDB", "sprites/animals/owl.png",    "#4527A0", "#EDE7F6"),
            _egg("#FF8A65", "#FFAB91", "sprites/animals/fox.png",    "#E64A19", "#FBE9E7"),
            _egg("#546E7A", "#78909C", "sprites/animals/cat.png",    "#263238", "#ECEFF1"),
            _egg("#A5D6A7", "#C8E6C9", "sprites/animals/frog.png",   "#1B5E20", "#E8F5E9"),
            _egg("#80CBC4", "#B2DFDB", "sprites/animals/bear.png",   "#004D40", "#E0F2F1"),
        ],
        "thumb_prompt": "cute nocturnal animals hatching from glowing eggs at night — owl, fox, cat, frog, bear, Pixar 3D style, magical starry night background",
    },
}

def _swap_pig_to_panda(eggs: list) -> list:
    """AR/ID: replace pig sprite with panda."""
    return [
        dict(e, animalSprite=e["animalSprite"].replace("/pig.png", "/panda.png"))
        for e in eggs
    ]


def _render_loop(ep_key: str, lang: str, loop_path: Path, dry_run: bool) -> bool:
    ep    = EPISODES[ep_key]
    eggs  = ep["eggs"] if lang == "en" else _swap_pig_to_panda(ep["eggs"])
    music = LANG_MUSIC[ep_key][lang]
    props = json.dumps({"eggs": eggs, "musicFile": music, "bgColor": "#FFF8F0"})
    cmd   = ["npx", "remotion", "render", "src/index.ts", COMP_LOOP,
             str(loop_path), "--props", props, "--concurrency", "1", "--log", "error"]
    if dry_run:
        print(f"    [DRY RUN] render loop {ep_key}/{lang}")
        return True
    loop_path.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    r  = subprocess.run(cmd, cwd=str(REMOTION), capture_output=True, text=True, timeout=21600)
    if r.returncode == 0 and loop_path.exists():
        print(f"    ✓ loop {(time.time()-t0)/60:.0f} min, {loop_path.stat().st_size//1024//1024} MB")
        return True
    print(f"    ✗ loop FAILED: {r.stderr[-400:]}"); return False


def _extend_to_30min(loop_path: Path, out_path: Path, dry_run: bool) -> bool:
    concat = out_path.parent / f"_concat_{out_path.stem}.txt"
    concat.write_text("\n".join([f"file '{loop_path.resolve()}'"] * 6))
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
           "-i", str(concat), "-c", "copy", str(out_path)]
    if dry_run:
        print(f"    [DRY RUN] ffmpeg concat 6× → {out_path.name}")
        concat.unlink(missing_ok=True)
        return True
    r = subprocess.run(cmd, capture_output=True, text=True)
    concat.unlink(missing_ok=True)
    if r.returncode == 0 and out_path.exists():
        print(f"    ✓ 30 min → {out_path.name} ({out_path.stat().st_size//1024//1024} MB)")
        return True
    print(f"    ✗ ffmpeg FAILED: {r.stderr[-400:]}"); return False


def make_meta(ep_key: str, lang: str) -> dict:
    ep   = EPISODES[ep_key]
    ch   = {"en": "@HappyBearKids1", "ar": "@happybearkidsar", "id": "@happybearkidsin"}
    name = ep[f"name_{lang}"]
    if lang == "en":
        title = f"{name} Magic Eggs | 30 Min Baby Animation | Happy Bear Kids"
        desc  = (
            f"✨ {name} — magic eggs hatch to reveal adorable animals!\n\n"
            f"Watch colorful eggs fall, shake, crack open and baby animals spring out "
            f"with fun sparkles and bouncy music! Each egg is a surprise!\n\n"
            f"🐣 Part of the {SERIES_EN} series — a new animal theme each episode!\n\n"
            f"🎯 Perfect for: visual cause-and-effect, surprise learning, peek-a-boo play\n"
            f"👶 Age: 0–3 years | 📺 30 minutes continuous\n"
            f"🌈 No language barriers — universal for any culture\n\n"
            f"🔔 Subscribe → {ch['en']}\n"
            f"🎵 Kevin MacLeod (incompetech.com) — CC Attribution 4.0\n\n"
            f"#MagicEggs #{name.replace(' ','')} #HappyBearKids #BabyAnimation "
            f"#EggHatching #ToddlerTV #BabySensory\n© Happy Bear Kids 2026"
        )
        tags = ["magic eggs", name.lower(), "egg hatching", "baby animation",
                "happy bear kids", "toddler tv", "peek a boo", "surprise animals", "30 minutes"]
    elif lang == "ar":
        title = f"بيضات {name} السحرية | 30 دقيقة رسوم أطفال | هابي بير كيدز"
        desc  = (
            f"✨ {name} — البيضات السحرية تفقس لتكشف عن حيوانات رائعة!\n\n"
            f"شاهد البيض الملون يسقط ويرتجف ويتشقق ليخرج منه حيوانات لطيفة "
            f"مع بريق ساحر وموسيقى مرحة! كل بيضة مفاجأة!\n\n"
            f"🐣 جزء من سلسلة {SERIES_AR} — موضوع حيواني مختلف في كل حلقة!\n\n"
            f"🎯 مثالي لـ: تعلم السبب والنتيجة، التعلم بالمفاجأة، لعبة الاختباء\n"
            f"👶 العمر: 0–3 سنوات | 📺 30 دقيقة متواصلة\n\n"
            f"🔔 اشتركوا → {ch['ar']}\n"
            f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
            f"#{name.replace(' ','_')} #هابي_بير_كيدز #رسوم_أطفال "
            f"#بيضات_سحرية #تحفيز_بصري\n© هابي بير كيدز 2026"
        )
        tags = [name, "هابي بير كيدز", "رسوم أطفال", "بيضات سحرية", "تحفيز بصري", "حيوانات أطفال"]
    else:
        title = f"Telur Ajaib {name} | 30 Menit Animasi Bayi | Happy Bear Kids Indonesia"
        desc  = (
            f"✨ {name} — telur ajaib menetas mengungkap hewan-hewan lucu!\n\n"
            f"Saksikan telur berwarna jatuh, bergetar, retak dan hewan bayi muncul "
            f"dengan percikan bintang dan musik riang! Setiap telur adalah kejutan!\n\n"
            f"🐣 Bagian dari seri {SERIES_ID} — tema hewan berbeda setiap episode!\n\n"
            f"🎯 Sempurna untuk: belajar sebab-akibat, belajar kejutan, ciluk ba\n"
            f"👶 Usia: 0–3 tahun | 📺 30 menit\n\n"
            f"🔔 Subscribe → {ch['id']}\n"
            f"🎵 Kevin MacLeod (incompetech.com) — CC Attribution 4.0\n\n"
            f"#{name.replace(' ','')} #HappyBearKids #AnimasiBayi "
            f"#TelurAjaib #StimulasiVisual\n© Happy Bear Kids Indonesia 2026"
        )
        tags = [name.lower(), "telur ajaib", "animasi bayi", "happy bear kids",
                "hewan menetas", "stimulasi visual", "30 menit"]
    return {"title": title, "description": desc, "tags": tags,
            "video_type": "special_mechanics", "language": lang,
            "is_short": False, "status": "public"}


def generate_thumbnail(ep_key: str, out_path: Path, lang: str) -> bool:
    if out_path.exists():
        return True
    try:
        key = TOGETHER_KEY_FILE.read_text().strip()
    except Exception:
        return False
    notext = "" if lang in ("en", "id") else ", no text, no letters, no words, no numbers"
    prompt = EPISODES[ep_key]["thumb_prompt"] + f", YouTube thumbnail 16:9{notext}"
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("gat", ROOT / "scripts" / "generate_ai_thumbs.py")
        gat = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gat)
        img = gat.together_generate_image(prompt, key)
        if img:
            out_path.write_bytes(gat.resize_to_720p(img))
            print(f"    ✓ thumb → {out_path.name}")
            return True
        print(f"    ! thumb failed: API returned no image")
        return False
    except Exception as e:
        print(f"    ! thumb failed: {e}")
        return False


def distribute(ep_key: str, force: bool, dry_run: bool):
    ep = EPISODES[ep_key]
    LOOPS_DIR.mkdir(parents=True, exist_ok=True)
    for lang in ("en", "ar", "id"):
        q      = {"en": QUEUE_EN, "ar": QUEUE_AR, "id": QUEUE_ID}[lang]
        stem   = f"peekegg_{ep_key}_{DATE_STR}" if lang == "en" else f"peekegg_{ep_key}_{DATE_STR}_{lang}"
        out_mp4 = q / f"{stem}.mp4"
        loop_mp4 = LOOPS_DIR / f"loop_{ep_key}_{lang}.mp4"

        print(f"\n  [{lang.upper()}] {ep[f'name_{lang}']}")
        if not out_mp4.exists() or force:
            q.mkdir(parents=True, exist_ok=True)
            if not loop_mp4.exists() or force:
                _render_loop(ep_key, lang, loop_mp4, dry_run)
            if not dry_run and loop_mp4.exists():
                _extend_to_30min(loop_mp4, out_mp4, dry_run)
            elif dry_run:
                print(f"    [DRY RUN] extend → {out_mp4.name}")
        else:
            print(f"    skip {out_mp4.name}")

        if dry_run:
            continue
        if not out_mp4.exists():
            continue

        mpath = q / f"meta_{stem}.yaml"
        if not mpath.exists():
            with open(mpath, "w", encoding="utf-8") as f:
                yaml.dump(make_meta(ep_key, lang), f, allow_unicode=True,
                          default_flow_style=False, sort_keys=False)
            print(f"    meta → {mpath.name}")

        tp = q / f"thumb_{stem}.png"
        if not tp.exists():
            time.sleep(0.5); generate_thumbnail(ep_key, tp, lang)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--list",       action="store_true")
    parser.add_argument("--episodes",   nargs="*")
    parser.add_argument("--dry-run",    action="store_true")
    parser.add_argument("--force",      action="store_true")
    parser.add_argument("--regen-meta", action="store_true")
    args = parser.parse_args()

    if args.list:
        print(f"{'Episode':15s}  {'EN name':25s}  {'Eggs':5s}")
        for k, ep in EPISODES.items():
            print(f"  {k:15s}  {ep['name_en']:25s}  {len(ep['eggs'])} eggs")
        return

    keys = list(EPISODES) if not args.episodes or args.episodes == ["all"] else args.episodes
    bad  = [k for k in keys if k not in EPISODES]
    if bad:
        print(f"Unknown episodes: {bad}"); sys.exit(1)

    if args.regen_meta:
        for k in keys:
            for lang in ("en", "ar", "id"):
                q    = {"en": QUEUE_EN, "ar": QUEUE_AR, "id": QUEUE_ID}[lang]
                stem = f"peekegg_{k}_{DATE_STR}" if lang == "en" else f"peekegg_{k}_{DATE_STR}_{lang}"
                mp4  = q / f"{stem}.mp4"
                if not mp4.exists():
                    continue
                mpath = q / f"meta_{stem}.yaml"
                with open(mpath, "w", encoding="utf-8") as f:
                    yaml.dump(make_meta(k, lang), f, allow_unicode=True,
                              default_flow_style=False, sort_keys=False)
                print(f"  regen {lang.upper()} → {mpath.name}")
        return

    for k in keys:
        print(f"\n▶ episode: {k}")
        distribute(k, args.force, args.dry_run)


if __name__ == "__main__":
    main()
