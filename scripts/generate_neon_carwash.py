#!/usr/bin/env python3
"""
generate_neon_carwash.py — Neon Car Wash series (grey car → colorful through magic wash).
No text → universal → EN + AR + ID.

Usage:
  python3 scripts/generate_neon_carwash.py --list
  python3 scripts/generate_neon_carwash.py --videos all [--dry-run] [--force]
  python3 scripts/generate_neon_carwash.py --regen-meta
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
COMP      = "NeonCarWash"
DUR_LABEL = "54 sec"

LANG_MUSIC = {
    "neon_carwash": {
        "en": "Pinball Spring.mp3",
        "ar": "Walking Along.mp3",
        "id": "Heartwarming.mp3",
    },
}

VIDEOS = {
    "neon_carwash": {
        "name_en": "Neon Car Wash",
        "name_ar": "غسيل السيارات النيون",
        "name_id": "Cuci Mobil Neon",
        "props": {
            "bgColor": "#E8F5E9",
        },
    },
}

PROMPTS = {
    "neon_carwash": (
        "cute cartoon cars going through a magical neon car wash — gray car enters, "
        "colorful foam and bubbles, car emerges bright and shiny with rainbow sparkles, "
        "Pixar 3D style, children's animation, vibrant neon colors"
    ),
}


def make_meta(vid: str, lang: str) -> dict:
    v  = VIDEOS[vid]
    ch = {"en": "@HappyBearKids1", "ar": "@happybearkidsar", "id": "@happybearkidsin"}
    name = v[f"name_{lang}"]
    if lang == "en":
        title = f"{name} | Cars Transform! | Happy Bear Kids"
        desc = (
            f"✨ {name} — watch grey cars transform into bright colorful cars!\n\n"
            f"A grey car rolls into the magic neon wash, gets covered in foam and "
            f"sparkles, then drives out shiny and colorful! Red truck, blue police "
            f"car, and yellow school bus — all transformed!\n\n"
            f"🚗 Watch the amazing transformation: Grey → Colorful!\n"
            f"🌈 Neon lights, soap foam, sparkle bursts and bouncy music!\n\n"
            f"🎯 Perfect for: visual cause-and-effect learning, color recognition, "
            f"sensory stimulation\n"
            f"👶 Age: 0–4 years | 📺 Looping animation\n"
            f"🌎 No language barriers — universal for any culture\n\n"
            f"🔔 Subscribe → {ch['en']}\n"
            f"🎵 Kevin MacLeod (incompetech.com) — CC Attribution 4.0\n\n"
            f"#NeonCarWash #CarsForKids #HappyBearKids #BabyAnimation "
            f"#ToddlerTV #ColorTransform #CarWash\n© Happy Bear Kids 2026"
        )
        tags = ["neon car wash", "cars for kids", "color transform", "happy bear kids",
                "baby animation", "toddler tv", "cars animation", "color learning"]
    elif lang == "ar":
        title = f"{name} | السيارات تتحول! | هابي بير كيدز"
        desc = (
            f"✨ {name} — شاهد السيارات الرمادية تتحول إلى سيارات ملونة براقة!\n\n"
            f"سيارة رمادية تدخل غسيل السحري، تُغطى بالرغوة واللمعان، "
            f"ثم تخرج لامعة وملونة! شاحنة حمراء، سيارة شرطة زرقاء، "
            f"وحافلة مدرسية صفراء — كلها متحولة!\n\n"
            f"🚗 شاهد التحول الرائع: رمادي → ملون!\n"
            f"🌈 أضواء النيون، رغوة الصابون، لمعان وموسيقى مرحة!\n\n"
            f"🎯 مثالي لـ: تعلم السبب والنتيجة، التعرف على الألوان، التحفيز الحسي\n"
            f"👶 العمر: 0–4 سنوات\n\n"
            f"🔔 اشتركوا → {ch['ar']}\n"
            f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
            f"#غسيل_السيارات #هابي_بير_كيدز #رسوم_أطفال #سيارات_أطفال "
            f"#تحفيز_بصري\n© هابي بير كيدز 2026"
        )
        tags = ["غسيل السيارات", "سيارات أطفال", "هابي بير كيدز", "رسوم أطفال", "تحفيز بصري"]
    else:
        title = f"{name} | Mobil Berubah Warna! | Happy Bear Kids Indonesia"
        desc = (
            f"✨ {name} — saksikan mobil abu-abu berubah menjadi mobil warna-warni!\n\n"
            f"Mobil abu-abu masuk ke tempat cuci ajaib, tertutup busa dan kilauan, "
            f"lalu keluar berkilau dan berwarna-warni! Truk merah, mobil polisi biru, "
            f"dan bus kuning — semuanya bertransformasi!\n\n"
            f"🚗 Saksikan transformasi menakjubkan: Abu-abu → Warna-warni!\n"
            f"🌈 Lampu neon, busa sabun, percikan bintang dan musik riang!\n\n"
            f"🎯 Sempurna untuk: belajar sebab-akibat, mengenal warna, stimulasi sensorik\n"
            f"👶 Usia: 0–4 tahun\n\n"
            f"🔔 Subscribe → {ch['id']}\n"
            f"🎵 Kevin MacLeod (incompetech.com) — CC Attribution 4.0\n\n"
            f"#CuciMobilNeon #MobilAnakAnak #HappyBearKids #AnimasiBayi "
            f"#WarnaMobil\n© Happy Bear Kids Indonesia 2026"
        )
        tags = ["cuci mobil neon", "mobil anak-anak", "happy bear kids", "animasi bayi", "warna-warni"]
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
    prompt = PROMPTS.get(vid, "colorful car wash animation") + f", YouTube thumbnail{notext}"
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
