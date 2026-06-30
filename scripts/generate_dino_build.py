#!/usr/bin/env python3
"""
generate_dino_build.py — Dino Build series (assembly piece by piece).
No text → universal → EN + AR + ID.

4 episodes × 3 channels = 12 long videos (30 min each via FFmpeg ×6).
Each episode uses different color themes (hue-rotate on the dino sprite).

Usage:
  python3 scripts/generate_dino_build.py --list
  python3 scripts/generate_dino_build.py --episodes all [--dry-run] [--force]
  python3 scripts/generate_dino_build.py --episodes prehistoric candy
  python3 scripts/generate_dino_build.py --regen-meta
"""
import argparse, base64, json, shutil, subprocess, sys, time, yaml
from datetime import datetime
from pathlib import Path

ROOT      = Path(__file__).resolve().parent.parent
REMOTION  = ROOT / "remotion"
QUEUE_EN  = ROOT / "output" / "queue"
QUEUE_AR  = ROOT / "output" / "queue_ar"
QUEUE_ID  = ROOT / "output" / "queue_id"
LOOPS_DIR = ROOT / "output" / "_dinobuild_loops"
TOGETHER_KEY_FILE = ROOT / "credentials" / "together_api_key.txt"
TOGETHER_URL   = "https://api.together.xyz/v1/images/generations"
TOGETHER_MODEL = "black-forest-labs/FLUX.1-schnell"
DATE_STR  = datetime.now().strftime("%Y%m%d")
COMP_LOOP  = "DinoBuildLoop"
DUR_LABEL  = "30 min"
SERIES_EN  = "Build a Dinosaur"
SERIES_AR  = "ابنِ ديناصوراً"
SERIES_ID  = "Bangun Dinosaurus"

LANG_MUSIC = {
    "prehistoric": {"en": "Wholesome.mp3",           "ar": "Carefree.mp3",       "id": "Quirky Dog.mp3"},
    "candy":       {"en": "Happy Happy Game Show.mp3","ar": "Merry Go.mp3",       "id": "Hyperfun.mp3"},
    "galaxy":      {"en": "Gymnopedie No 1.mp3",     "ar": "Crinoline Dreams.mp3","id": "Salty Ditty.mp3"},
    "volcano":     {"en": "Pinball Spring.mp3",       "ar": "Walking Along.mp3",  "id": "Heartwarming.mp3"},
}

def _dino(hue, bg_top, bg_bot, accent, snap):
    return {"sprite": "sprites/animals/dino.png", "hueRotate": hue,
            "bgTop": bg_top, "bgBottom": bg_bot, "accentColor": accent, "snapColor": snap}

EPISODES = {
    "prehistoric": {
        "name_en": "Prehistoric Dinos",
        "name_ar": "ديناصورات ما قبل التاريخ",
        "name_id": "Dinosaurus Prasejarah",
        "dinos": [
            _dino(  0, "#1B5E20", "#4CAF50", "#76FF03", "#B2FF59"),  # green
            _dino(200, "#0D47A1", "#42A5F5", "#40C4FF", "#80D8FF"),  # blue
            _dino( 30, "#BF360C", "#F4511E", "#FF6D00", "#FF9E40"),  # orange
        ],
        "thumb_prompt": "cute cartoon dinosaurs being assembled piece by piece from flying body parts, green and blue prehistoric dinos, magical assembly sparkles, jungle background, Pixar 3D style",
    },
    "candy": {
        "name_en": "Candy Dinos",
        "name_ar": "ديناصورات السكاكي",
        "name_id": "Dinosaurus Permen",
        "dinos": [
            _dino(300, "#880E4F", "#E91E63", "#FF80AB", "#FFB3C5"),  # pink
            _dino(260, "#4A148C", "#9C27B0", "#EA80FC", "#CE93D8"),  # purple
            _dino( 50, "#F57F17", "#FDD835", "#FFFF00", "#FFF176"),  # yellow
        ],
        "thumb_prompt": "cute cartoon candy-colored dinosaurs being assembled piece by piece — pink, purple and yellow dinos, sweet pastel colors, sparkles and confetti, Pixar 3D style",
    },
    "galaxy": {
        "name_en": "Galaxy Dinos",
        "name_ar": "ديناصورات المجرة",
        "name_id": "Dinosaurus Galaksi",
        "dinos": [
            _dino(180, "#006064", "#00BCD4", "#18FFFF", "#84FFFF"),  # cyan
            _dino(320, "#6A1B9A", "#E040FB", "#EA80FC", "#CE93D8"),  # magenta
            _dino( 45, "#E65100", "#FFD600", "#FFEA00", "#FFF176"),  # gold
        ],
        "thumb_prompt": "cute cartoon galaxy-colored glowing dinosaurs being assembled in space — cyan, magenta and gold dinos, cosmic background with stars and nebula, Pixar 3D style",
    },
    "volcano": {
        "name_en": "Volcano Dinos",
        "name_ar": "ديناصورات البركان",
        "name_id": "Dinosaurus Gunung Api",
        "dinos": [
            _dino( 15, "#B71C1C", "#E53935", "#FF1744", "#FF5252"),  # red
            _dino( 25, "#E65100", "#FF6D00", "#FF9100", "#FFAB40"),  # deep orange
            _dino(340, "#4E342E", "#795548", "#BCAAA4", "#D7CCC8"),  # brown/earth
        ],
        "thumb_prompt": "cute cartoon volcano dinosaurs being assembled near an erupting volcano — red, orange and earthy brown dinos, dramatic volcano background with lava, Pixar 3D style",
    },
}


def _render_loop(ep_key: str, lang: str, loop_path: Path, dry_run: bool) -> bool:
    ep     = EPISODES[ep_key]
    music  = LANG_MUSIC[ep_key][lang]
    props  = json.dumps({"dinos": ep["dinos"], "musicFile": music})
    cmd    = ["npx", "remotion", "render", "src/index.ts", COMP_LOOP,
              str(loop_path), "--props", props, "--concurrency", "1", "--log", "error"]
    if dry_run:
        print(f"    [DRY RUN] render loop {ep_key}/{lang}"); return True
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
        concat.unlink(missing_ok=True); return True
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
        title = f"{name} | Build a Dino 30 Min | Happy Bear Kids"
        desc  = (
            f"✨ {name} — watch dinosaurs get built piece by piece!\n\n"
            f"A magic silhouette appears, then body parts fly in from all directions "
            f"and magnetically snap into place with exciting flashes! "
            f"Body, head, legs, tail — and then the dino celebrates!\n\n"
            f"🦕 Part of the {SERIES_EN} series — a new color theme each episode!\n\n"
            f"✨ Parts fly on arc trajectories and spring-snap into place!\n"
            f"🎯 Perfect for: spatial reasoning, puzzle thinking, visual assembly\n"
            f"👶 Age: 0–4 years | 📺 30 minutes continuous\n\n"
            f"🔔 Subscribe → {ch['en']}\n"
            f"🎵 Kevin MacLeod (incompetech.com) — CC Attribution 4.0\n\n"
            f"#{name.replace(' ','')} #BuildADinosaur #HappyBearKids #BabyAnimation "
            f"#DinoForKids #PuzzleAnimation\n© Happy Bear Kids 2026"
        )
        tags = ["build a dinosaur", name.lower(), "dino for kids", "puzzle animation",
                "happy bear kids", "baby animation", "30 minutes", "assembly animation"]
    elif lang == "ar":
        title = f"{name} | ابنِ ديناصوراً 30 دقيقة | هابي بير كيدز"
        desc  = (
            f"✨ {name} — شاهد الديناصور يُبنى قطعة تلو الأخرى!\n\n"
            f"يظهر خيال سحري، ثم تطير أجزاء الجسم من كل الاتجاهات "
            f"وتنقر مغناطيسياً في مكانها مع وميض مثير! "
            f"الجسم، الرأس، الأرجل، الذيل — ثم يحتفل الديناصور!\n\n"
            f"🦕 جزء من سلسلة {SERIES_AR} — ألوان مختلفة في كل حلقة!\n\n"
            f"🎯 مثالي لـ: التفكير المكاني، حل الألغاز، التجميع البصري\n"
            f"👶 العمر: 0–4 سنوات | 📺 30 دقيقة متواصلة\n\n"
            f"🔔 اشتركوا → {ch['ar']}\n"
            f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
            f"#{name.replace(' ','_')} #هابي_بير_كيدز #رسوم_أطفال "
            f"#ابنِ_ديناصوراً #ديناصور_أطفال\n© هابي بير كيدز 2026"
        )
        tags = [name, "هابي بير كيدز", "رسوم أطفال", "ديناصور أطفال", "تحفيز بصري"]
    else:
        title = f"{name} | Bangun Dinosaurus 30 Menit | Happy Bear Kids Indonesia"
        desc  = (
            f"✨ {name} — saksikan dinosaurus dibangun satu per satu!\n\n"
            f"Siluet ajaib muncul, lalu bagian tubuh beterbangan dari segala arah "
            f"dan mengunci secara magnetis di tempatnya dengan kilatan seru! "
            f"Tubuh, kepala, kaki, ekor — lalu dinosaurusnya merayakan!\n\n"
            f"🦕 Bagian dari seri {SERIES_ID} — tema warna berbeda setiap episode!\n\n"
            f"🎯 Sempurna untuk: penalaran spasial, berpikir puzzle, perakitan visual\n"
            f"👶 Usia: 0–4 tahun | 📺 30 menit\n\n"
            f"🔔 Subscribe → {ch['id']}\n"
            f"🎵 Kevin MacLeod (incompetech.com) — CC Attribution 4.0\n\n"
            f"#{name.replace(' ','')} #HappyBearKids #AnimasiBayi "
            f"#BangunDinosaurus #DinoAnakAnak\n© Happy Bear Kids Indonesia 2026"
        )
        tags = [name.lower(), "bangun dinosaurus", "animasi bayi", "happy bear kids", "30 menit"]
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
    import urllib.request
    try:
        payload = json.dumps({"model": TOGETHER_MODEL, "prompt": prompt,
                              "width": 1280, "height": 720, "steps": 4, "n": 1}).encode()
        req = urllib.request.Request(TOGETHER_URL, data=payload,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read())
        out_path.write_bytes(base64.b64decode(data["data"][0]["b64_json"]))
        print(f"    ✓ thumb → {out_path.name}"); return True
    except Exception as e:
        print(f"    ! thumb failed: {e}"); return False


def distribute(ep_key: str, force: bool, dry_run: bool):
    ep = EPISODES[ep_key]
    LOOPS_DIR.mkdir(parents=True, exist_ok=True)
    for lang in ("en", "ar", "id"):
        q        = {"en": QUEUE_EN, "ar": QUEUE_AR, "id": QUEUE_ID}[lang]
        stem     = f"dinobuild_{ep_key}_{DATE_STR}" if lang == "en" else f"dinobuild_{ep_key}_{DATE_STR}_{lang}"
        out_mp4  = q / f"{stem}.mp4"
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
        print(f"{'Episode':12s}  {'EN name':30s}  {'Dinos':5s}")
        for k, ep in EPISODES.items():
            print(f"  {k:12s}  {ep['name_en']:30s}  {len(ep['dinos'])} dinos")
        return

    keys = list(EPISODES) if not args.episodes or args.episodes == ["all"] else args.episodes
    bad  = [k for k in keys if k not in EPISODES]
    if bad:
        print(f"Unknown episodes: {bad}"); sys.exit(1)

    if args.regen_meta:
        for k in keys:
            for lang in ("en", "ar", "id"):
                q    = {"en": QUEUE_EN, "ar": QUEUE_AR, "id": QUEUE_ID}[lang]
                stem = f"dinobuild_{k}_{DATE_STR}" if lang == "en" else f"dinobuild_{k}_{DATE_STR}_{lang}"
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
