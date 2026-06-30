#!/usr/bin/env python3
"""
generate_dino_build.py — Dino Build series (dinosaur assembly piece by piece).
No text → universal → EN + AR + ID.

Usage:
  python3 scripts/generate_dino_build.py --list
  python3 scripts/generate_dino_build.py --videos all [--dry-run] [--force]
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
TOGETHER_KEY_FILE = ROOT / "credentials" / "together_api_key.txt"
TOGETHER_URL   = "https://api.together.xyz/v1/images/generations"
TOGETHER_MODEL = "black-forest-labs/FLUX.1-schnell"
DATE_STR  = datetime.now().strftime("%Y%m%d")
COMP      = "DinoBuild"
DUR_LABEL = "60 sec"

LANG_MUSIC = {
    "dino_build": {
        "en": "Wholesome.mp3",
        "ar": "Carefree.mp3",
        "id": "Quirky Dog.mp3",
    },
}

VIDEOS = {
    "dino_build": {
        "name_en": "Build a Dinosaur",
        "name_ar": "ابنِ ديناصوراً",
        "name_id": "Bangun Dinosaurus",
        "props": {},
    },
}

PROMPTS = {
    "dino_build": (
        "cute cartoon dinosaur being assembled piece by piece from flying parts, "
        "body parts flying through the air with sparkles and glowing effects, "
        "magical assembly animation, dinosaur puzzle, Pixar 3D style, "
        "children's animation, bright colorful prehistoric background with plants"
    ),
}


def make_meta(vid: str, lang: str) -> dict:
    v  = VIDEOS[vid]
    ch = {"en": "@HappyBearKids1", "ar": "@happybearkidsar", "id": "@happybearkidsin"}
    name = v[f"name_{lang}"]
    if lang == "en":
        title = f"{name} | Puzzle Animation for Babies | Happy Bear Kids"
        desc = (
            f"✨ {name} — watch a dinosaur get built piece by piece!\n\n"
            f"A magic silhouette appears, then body parts fly in from all directions "
            f"with exciting whoosh sounds and snap into place with sparkle flashes! "
            f"First the body, then the head, legs, and finally the tail — "
            f"and then the dino celebrates!\n\n"
            f"🦕 Green dino, Blue dino, Pink dino — three colorful dinosaurs!\n"
            f"✨ Parts fly on arc trajectories and magnetically snap together!\n\n"
            f"🎯 Perfect for: spatial reasoning, puzzle thinking, visual assembly\n"
            f"👶 Age: 0–4 years | 📺 Looping animation\n"
            f"🌎 No language barriers — universal for any culture\n\n"
            f"🔔 Subscribe → {ch['en']}\n"
            f"🎵 Kevin MacLeod (incompetech.com) — CC Attribution 4.0\n\n"
            f"#BuildADinosaur #DinoForKids #HappyBearKids #BabyAnimation "
            f"#ToddlerTV #PuzzleAnimation #Dinosaur\n© Happy Bear Kids 2026"
        )
        tags = ["build a dinosaur", "dino for kids", "puzzle animation", "happy bear kids",
                "baby animation", "toddler tv", "dinosaur kids", "assembly animation"]
    elif lang == "ar":
        title = f"{name} | رسوم أطفال ديناصور | هابي بير كيدز"
        desc = (
            f"✨ {name} — شاهد الديناصور يُبنى قطعة تلو الأخرى!\n\n"
            f"يظهر خيال سحري، ثم تطير أجزاء الجسم من كل الاتجاهات "
            f"بأصوات مبهجة وتنقر في مكانها مع وميض من البريق! "
            f"الجسم أولاً، ثم الرأس، الأرجل، وأخيراً الذيل — "
            f"ثم يحتفل الديناصور!\n\n"
            f"🦕 ديناصور أخضر، أزرق، وردي — ثلاثة ديناصورات ملونة!\n\n"
            f"🎯 مثالي لـ: التفكير المكاني، حل الألغاز، التجميع البصري\n"
            f"👶 العمر: 0–4 سنوات\n\n"
            f"🔔 اشتركوا → {ch['ar']}\n"
            f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
            f"#ابنِ_ديناصوراً #هابي_بير_كيدز #رسوم_أطفال #ديناصور_أطفال "
            f"#تحفيز_بصري\n© هابي بير كيدز 2026"
        )
        tags = ["ابنِ ديناصوراً", "ديناصور أطفال", "هابي بير كيدز", "رسوم أطفال", "تحفيز بصري"]
    else:
        title = f"{name} | Animasi Puzzle untuk Bayi | Happy Bear Kids Indonesia"
        desc = (
            f"✨ {name} — saksikan dinosaurus dibangun satu per satu!\n\n"
            f"Siluet ajaib muncul, lalu bagian tubuh beterbangan dari segala arah "
            f"dengan suara keren dan mengunci di tempatnya dengan kilatan bintang! "
            f"Pertama tubuh, lalu kepala, kaki, dan akhirnya ekor — "
            f"dan dinosaurusnya merayakan!\n\n"
            f"🦕 Dino hijau, biru, merah muda — tiga dinosaurus berwarna-warni!\n\n"
            f"🎯 Sempurna untuk: penalaran spasial, berpikir puzzle, perakitan visual\n"
            f"👶 Usia: 0–4 tahun\n\n"
            f"🔔 Subscribe → {ch['id']}\n"
            f"🎵 Kevin MacLeod (incompetech.com) — CC Attribution 4.0\n\n"
            f"#BangunDinosaurus #DinoAnakAnak #HappyBearKids #AnimasiBayi "
            f"#AnimasiPuzzle\n© Happy Bear Kids Indonesia 2026"
        )
        tags = ["bangun dinosaurus", "dino anak-anak", "happy bear kids", "animasi bayi", "animasi puzzle"]
    return {"title": title, "description": desc, "tags": tags,
            "video_type": "special_mechanics", "language": lang,
            "is_short": False, "status": "public"}


def generate_thumbnail(vid: str, out_path: Path, lang: str) -> bool:
    if out_path.exists():
        return True
    try:
        key = TOGETHER_KEY_FILE.read_text().strip()
    except Exception:
        return False
    notext = "" if lang in ("en", "id") else ", no text, no letters, no words, no numbers"
    prompt = PROMPTS.get(vid, "cute dinosaur puzzle assembly animation") + f", YouTube thumbnail{notext}"
    import urllib.request
    try:
        payload = json.dumps({"model": TOGETHER_MODEL, "prompt": prompt,
                              "width": 1280, "height": 720, "steps": 4, "n": 1}).encode()
        req = urllib.request.Request(TOGETHER_URL, data=payload,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read())
        out_path.write_bytes(base64.b64decode(data["data"][0]["b64_json"]))
        print(f"    ✓ thumb → {out_path.name}")
        return True
    except Exception as e:
        print(f"    ! thumb failed: {e}"); return False


def render_video(vid: str, lang: str, force: bool, dry_run: bool) -> Path | None:
    v      = VIDEOS[vid]
    q      = {"en": QUEUE_EN, "ar": QUEUE_AR, "id": QUEUE_ID}[lang]
    stem   = f"{vid}_{DATE_STR}" if lang == "en" else f"{vid}_{DATE_STR}_{lang}"
    out    = q / f"{stem}.mp4"
    if out.exists() and not force:
        print(f"  [{lang.upper()}] skip {out.name}"); return out
    music  = LANG_MUSIC[vid][lang]
    props  = dict(v["props"], musicFile=music)
    print(f"\n  [{lang.upper()}] Rendering {vid} (music: {music})")
    if dry_run:
        print(f"    [DRY RUN] {COMP}"); return out
    q.mkdir(parents=True, exist_ok=True)
    cmd = ["npx", "remotion", "render", "src/index.ts", COMP,
           str(out), "--props", json.dumps(props),
           "--concurrency", "1", "--log", "error"]
    t0 = time.time()
    r  = subprocess.run(cmd, cwd=str(REMOTION), capture_output=True, text=True, timeout=3600)
    if r.returncode == 0 and out.exists():
        print(f"    ✓ {out.stat().st_size // 1024 // 1024} MB in {(time.time()-t0)/60:.0f} min")
        return out
    print(f"    ✗ FAILED: {r.stderr[-400:]}"); return None


def distribute(vid: str, force: bool, dry_run: bool):
    for lang in ("en", "ar", "id"):
        q    = {"en": QUEUE_EN, "ar": QUEUE_AR, "id": QUEUE_ID}[lang]
        stem = f"{vid}_{DATE_STR}" if lang == "en" else f"{vid}_{DATE_STR}_{lang}"
        mp4  = q / f"{stem}.mp4"
        if not mp4.exists() or force:
            render_video(vid, lang, force, dry_run)
        q.mkdir(parents=True, exist_ok=True)
        mpath = q / f"meta_{stem}.yaml"
        if not mpath.exists():
            if dry_run:
                print(f"    [DRY RUN] meta {lang.upper()}")
            else:
                with open(mpath, "w", encoding="utf-8") as f:
                    yaml.dump(make_meta(vid, lang), f, allow_unicode=True,
                              default_flow_style=False, sort_keys=False)
                print(f"    meta {lang.upper()} → {mpath.name}")
        tp = q / f"thumb_{stem}.png"
        if not tp.exists() and not dry_run:
            time.sleep(0.5); generate_thumbnail(vid, tp, lang)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--list",       action="store_true")
    parser.add_argument("--videos",     nargs="*")
    parser.add_argument("--dry-run",    action="store_true")
    parser.add_argument("--force",      action="store_true")
    parser.add_argument("--regen-meta", action="store_true")
    args = parser.parse_args()

    if args.list:
        for vid, v in VIDEOS.items():
            print(f"  {vid}  {v['name_en']:30s}  {COMP}  {DUR_LABEL}")
        return

    ids = list(VIDEOS) if not args.videos or args.videos == ["all"] else args.videos
    bad = [v for v in ids if v not in VIDEOS]
    if bad:
        print(f"Unknown IDs: {bad}"); sys.exit(1)

    if args.regen_meta:
        for vid in ids:
            for lang in ("en", "ar", "id"):
                q    = {"en": QUEUE_EN, "ar": QUEUE_AR, "id": QUEUE_ID}[lang]
                stem = f"{vid}_{DATE_STR}" if lang == "en" else f"{vid}_{DATE_STR}_{lang}"
                mp4  = q / f"{stem}.mp4"
                if not mp4.exists():
                    continue
                mpath = q / f"meta_{stem}.yaml"
                with open(mpath, "w", encoding="utf-8") as f:
                    yaml.dump(make_meta(vid, lang), f, allow_unicode=True,
                              default_flow_style=False, sort_keys=False)
                print(f"  regen meta {lang.upper()} → {mpath.name}")
        return

    for vid in ids:
        print(f"\n▶ {vid}")
        distribute(vid, args.force, args.dry_run)


if __name__ == "__main__":
    main()
