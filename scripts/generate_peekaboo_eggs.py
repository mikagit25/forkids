#!/usr/bin/env python3
"""
generate_peekaboo_eggs.py — Peek-a-Boo Eggs series (magic egg hatching).
No text → universal → EN + AR + ID (pig→panda swap handled in composition).

Usage:
  python3 scripts/generate_peekaboo_eggs.py --list
  python3 scripts/generate_peekaboo_eggs.py --videos all [--dry-run] [--force]
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
TOGETHER_KEY_FILE = ROOT / "credentials" / "together_api_key.txt"
TOGETHER_URL   = "https://api.together.xyz/v1/images/generations"
TOGETHER_MODEL = "black-forest-labs/FLUX.1-schnell"
DATE_STR  = datetime.now().strftime("%Y%m%d")
COMP      = "PeekABooEggs"
DUR_LABEL = "45 sec"

LANG_MUSIC = {
    "peekaboo_eggs_farm": {
        "en": "Happy Happy Game Show.mp3",
        "ar": "Monkeys Spinning Monkeys.mp3",
        "id": "Hyperfun.mp3",
    },
}

VIDEOS = {
    "peekaboo_eggs_farm": {
        "name_en": "Magic Eggs",
        "name_ar": "بيضات سحرية",
        "name_id": "Telur Ajaib",
        "props": {
            "bgColor": "#FFF8F0",
        },
    },
}

PROMPTS = {
    "peekaboo_eggs_farm": (
        "colorful cartoon Easter eggs cracking open to reveal cute baby animals — "
        "cow, lion, duck, baby animals peeking out, magical sparkles, Pixar 3D style, "
        "children's illustration, bright cheerful colors"
    ),
}


def make_meta(vid: str, lang: str) -> dict:
    v  = VIDEOS[vid]
    ch = {"en": "@HappyBearKids1", "ar": "@happybearkidsar", "id": "@happybearkidsin"}
    name = v[f"name_{lang}"]
    if lang == "en":
        title = f"{name} | Baby Animals Hatching | Happy Bear Kids"
        desc = (
            f"✨ {name} — a magical egg hatching animation for babies and toddlers!\n\n"
            f"Watch as colorful eggs shake, crack open and baby animals spring out "
            f"with fun sparkles and bouncy music. No words needed — pure magical fun!\n\n"
            f"🐣 Each egg is a surprise! Green egg → Cow, Blue egg → Lion, "
            f"Pink egg → Panda, Yellow egg → Duck\n\n"
            f"🎯 Perfect for: visual stimulation, surprise learning, peek-a-boo play\n"
            f"👶 Age: 0–3 years | 📺 Looping baby animation\n"
            f"🌈 No language barriers — universal for any culture\n\n"
            f"🔔 Subscribe → {ch['en']}\n"
            f"🎵 Kevin MacLeod (incompetech.com) — CC Attribution 4.0\n\n"
            f"#MagicEggs #BabyAnimals #HappyBearKids #EggHatching "
            f"#BabyAnimation #ToddlerTV #PeekABoo\n© Happy Bear Kids 2026"
        )
        tags = ["magic eggs", "baby animals", "egg hatching", "peek a boo",
                "happy bear kids", "baby animation", "toddler tv", "surprise animals"]
    elif lang == "ar":
        title = f"{name} | حيوانات أطفال تفقس | هابي بير كيدز"
        desc = (
            f"✨ {name} — رسوم فقس البيض السحرية للرضع والأطفال الصغار!\n\n"
            f"شاهد البيض الملون يرتجف ثم يتشقق ليخرج منه حيوانات أطفال "
            f"لطيفة مع بريق ساحر وموسيقى مرحة. بدون كلمات — مجرد متعة سحرية!\n\n"
            f"🐣 كل بيضة مفاجأة! البيضة الخضراء → بقرة، الزرقاء → أسد، "
            f"الوردية → باندا، الصفراء → بطة\n\n"
            f"🎯 مثالي لـ: التحفيز البصري، التعلم بالمفاجأة، لعبة الاختباء\n"
            f"👶 العمر: 0–3 سنوات\n\n"
            f"🔔 اشتركوا → {ch['ar']}\n"
            f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
            f"#بيضات_سحرية #هابي_بير_كيدز #رسوم_أطفال #حيوانات_أطفال "
            f"#تحفيز_بصري\n© هابي بير كيدز 2026"
        )
        tags = ["بيضات سحرية", "حيوانات أطفال", "هابي بير كيدز", "رسوم أطفال", "تحفيز بصري"]
    else:
        title = f"{name} | Hewan Menetas | Happy Bear Kids Indonesia"
        desc = (
            f"✨ {name} — animasi telur menetas yang ajaib untuk bayi dan balita!\n\n"
            f"Saksikan telur berwarna bergetar, retak dan hewan bayi yang lucu muncul "
            f"dengan percikan bintang dan musik riang. Tanpa kata-kata — kesenangan murni!\n\n"
            f"🐣 Setiap telur adalah kejutan! Telur hijau → Sapi, Biru → Singa, "
            f"Merah muda → Panda, Kuning → Bebek\n\n"
            f"🎯 Sempurna untuk: stimulasi visual, belajar kejutan, bermain ciluk ba\n"
            f"👶 Usia: 0–3 tahun\n\n"
            f"🔔 Subscribe → {ch['id']}\n"
            f"🎵 Kevin MacLeod (incompetech.com) — CC Attribution 4.0\n\n"
            f"#TelurAjaib #HewanMenetas #HappyBearKids #AnimasiBayi "
            f"#StimulasiVisual\n© Happy Bear Kids Indonesia 2026"
        )
        tags = ["telur ajaib", "hewan menetas", "happy bear kids", "animasi bayi", "stimulasi visual"]
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
    prompt = PROMPTS.get(vid, "cute baby animals hatching from eggs") + f", YouTube thumbnail{notext}"
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
    region = {"en": "US", "ar": "AR", "id": "ID"}[lang]
    stem   = f"{vid}_{DATE_STR}" if lang == "en" else f"{vid}_{DATE_STR}_{lang}"
    out    = q / f"{stem}.mp4"
    if out.exists() and not force:
        print(f"  [{lang.upper()}] skip {out.name}"); return out
    music  = LANG_MUSIC[vid][lang]
    props  = dict(v["props"], musicFile=music, region=region)
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
