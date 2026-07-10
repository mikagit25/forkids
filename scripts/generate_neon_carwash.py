#!/usr/bin/env python3
"""
generate_neon_carwash.py — Neon Car Wash series (grey car → colorful through magic wash).
No text → universal → EN + AR + ID.

5 episodes × 3 channels = 15 long videos (30 min each via FFmpeg ×6).
Each episode has a different vehicle theme (city, emergency, heavy, rainbow, fantasy).

Usage:
  python3 scripts/generate_neon_carwash.py --list
  python3 scripts/generate_neon_carwash.py --episodes all [--dry-run] [--force]
  python3 scripts/generate_neon_carwash.py --episodes city emergency
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
LOOPS_DIR = ROOT / "output" / "_carwash_loops"
TOGETHER_KEY_FILE = ROOT / "credentials" / "together_api_key.txt"
TOGETHER_URL   = "https://api.together.xyz/v1/images/generations"
TOGETHER_MODEL = "black-forest-labs/FLUX.1-schnell"
DATE_STR  = datetime.now().strftime("%Y%m%d")
COMP_LOOP  = "NeonCarWashLoop"
DUR_LABEL  = "30 min"
SERIES_EN  = "Neon Car Wash"
SERIES_AR  = "غسيل السيارات النيون"
SERIES_ID  = "Cuci Mobil Neon"

LANG_MUSIC = {
    "city":      {"en": "Pinball Spring.mp3",   "ar": "Walking Along.mp3",  "id": "Heartwarming.mp3"},
    "emergency": {"en": "Quirky Dog.mp3",        "ar": "Hyperfun.mp3",       "id": "Carefree.mp3"},
    "heavy":     {"en": "Happy Happy Game Show.mp3", "ar": "Merry Go.mp3",   "id": "Life of Riley.mp3"},
    "rainbow":   {"en": "Wholesome.mp3",         "ar": "Sneaky Snitch.mp3",  "id": "Fluffing a Duck.mp3"},
    "fantasy":   {"en": "Gymnopedie No 1.mp3",   "ar": "Crinoline Dreams.mp3","id": "Salty Ditty.mp3"},
}

def _v(label, color, accent, bg, foam):
    return {"label": label, "color": color, "accentColor": accent, "bgColor": bg, "foamColor": foam}

EPISODES = {
    "city": {
        "name_en": "City Cars",
        "name_ar": "سيارات المدينة",
        "name_id": "Mobil Kota",
        "vehicles": [
            _v("truck", "#E53935", "#E53935", "#FFEBEE", "#FF8A80"),
            _v("car",   "#1565C0", "#1565C0", "#E3F2FD", "#82B1FF"),
            _v("bus",   "#F9A825", "#F9A825", "#FFFDE7", "#FFD740"),
        ],
        "thumb_prompt": "cute cartoon city cars going through a colorful neon car wash — red truck, blue police car, yellow bus, soap bubbles and sparkles, Pixar 3D style",
    },
    "emergency": {
        "name_en": "Emergency Vehicles",
        "name_ar": "سيارات الطوارئ",
        "name_id": "Kendaraan Darurat",
        "vehicles": [
            _v("firetruck",  "#C62828", "#FF1744", "#FFEBEE", "#FF5252"),
            _v("ambulance",  "#ECEFF1", "#E53935", "#FAFAFA", "#EF9A9A"),
            _v("car",        "#0D47A1", "#2979FF", "#E3F2FD", "#82B1FF"),
        ],
        "thumb_prompt": "cute cartoon emergency vehicles going through a colorful neon car wash — fire truck, ambulance, police car, neon lights and bubbles, Pixar 3D style",
    },
    "heavy": {
        "name_en": "Big Machines",
        "name_ar": "الآلات الكبيرة",
        "name_id": "Mesin Besar",
        "vehicles": [
            _v("truck",   "#E65100", "#FF6D00", "#FBE9E7", "#FF9E40"),
            _v("bus",     "#1B5E20", "#2E7D32", "#E8F5E9", "#66BB6A"),
            _v("tractor", "#827717", "#F9A825", "#FFFDE7", "#FFD740"),
        ],
        "thumb_prompt": "cute cartoon big machines going through a colorful neon car wash — orange truck, green bus, yellow tractor, soap suds and rainbow sparkles, Pixar 3D style",
    },
    "rainbow": {
        "name_en": "Rainbow Cars",
        "name_ar": "سيارات قوس قزح",
        "name_id": "Mobil Pelangi",
        "vehicles": [
            _v("car", "#AD1457", "#F06292", "#FCE4EC", "#F48FB1"),
            _v("car", "#4A148C", "#AB47BC", "#F3E5F5", "#CE93D8"),
            _v("car", "#006064", "#00BCD4", "#E0F7FA", "#80DEEA"),
            _v("car", "#E65100", "#FF9800", "#FFF3E0", "#FFCC80"),
        ],
        "thumb_prompt": "cute cartoon rainbow colored cars going through a magical neon car wash — pink, purple, cyan, orange cars emerging shiny, sparkles and bubbles, Pixar 3D style",
    },
    "fantasy": {
        "name_en": "Fantasy Cars",
        "name_ar": "سيارات الخيال",
        "name_id": "Mobil Fantasi",
        "vehicles": [
            _v("truck", "#F57F17", "#FFD600", "#FFFDE7", "#FFF176"),  # gold
            _v("bus",   "#1A237E", "#3F51B5", "#E8EAF6", "#9FA8DA"),  # royal blue
            _v("car",   "#880E4F", "#E91E63", "#FCE4EC", "#F48FB1"),  # magenta
        ],
        "thumb_prompt": "cute cartoon fantasy cars going through a magical neon car wash — gold truck, royal blue bus, magenta car, glowing neon lights and sparkles, Pixar 3D style",
    },
}


def _render_loop(ep_key: str, lang: str, loop_path: Path, dry_run: bool) -> bool:
    ep     = EPISODES[ep_key]
    music  = LANG_MUSIC[ep_key][lang]
    props  = json.dumps({"vehicles": ep["vehicles"], "musicFile": music, "bgColor": "#E8F5E9"})
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
        title = f"{name} | Neon Car Wash 30 Min | Happy Bear Kids"
        desc  = (
            f"✨ {name} — watch grey vehicles transform into bright colorful ones!\n\n"
            f"Each vehicle rolls in grey, gets covered in magical foam and neon sparkles, "
            f"then emerges shiny and colorful! The ultimate color transformation show!\n\n"
            f"🚗 Part of the {SERIES_EN} series — a new vehicle theme each episode!\n\n"
            f"🌈 Neon lights, soap foam, sparkle bursts and bouncy music!\n"
            f"🎯 Perfect for: visual cause-and-effect, color recognition, sensory stimulation\n"
            f"👶 Age: 0–4 years | 📺 30 minutes continuous\n\n"
            f"🔔 Subscribe → {ch['en']}\n"
            f"🎵 Kevin MacLeod (incompetech.com) — CC Attribution 4.0\n\n"
            f"#{name.replace(' ','')} #NeonCarWash #HappyBearKids #BabyAnimation "
            f"#CarsForKids #ColorTransform\n© Happy Bear Kids 2026"
        )
        tags = ["neon car wash", name.lower(), "cars for kids", "color transform",
                "happy bear kids", "baby animation", "toddler tv", "30 minutes"]
    elif lang == "ar":
        title = f"{name} | غسيل النيون 30 دقيقة | هابي بير كيدز"
        desc  = (
            f"✨ {name} — شاهد المركبات الرمادية تتحول إلى مركبات ملونة براقة!\n\n"
            f"كل مركبة تدخل رمادية، تُغطى بالرغوة السحرية والنيون اللامع، "
            f"ثم تخرج لامعة وملونة! عرض التحولات المذهلة!\n\n"
            f"🚗 جزء من سلسلة {SERIES_AR} — موضوع مركبات مختلف في كل حلقة!\n\n"
            f"🎯 مثالي لـ: تعلم السبب والنتيجة، التعرف على الألوان، التحفيز الحسي\n"
            f"👶 العمر: 0–4 سنوات | 📺 30 دقيقة متواصلة\n\n"
            f"🔔 اشتركوا → {ch['ar']}\n"
            f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
            f"#{name.replace(' ','_')} #هابي_بير_كيدز #رسوم_أطفال "
            f"#غسيل_السيارات #تحفيز_بصري\n© هابي بير كيدز 2026"
        )
        tags = [name, "هابي بير كيدز", "رسوم أطفال", "غسيل السيارات", "تحفيز بصري"]
    else:
        title = f"{name} | Cuci Mobil Neon 30 Menit | Happy Bear Kids Indonesia"
        desc  = (
            f"✨ {name} — saksikan kendaraan abu-abu berubah menjadi warna-warni!\n\n"
            f"Setiap kendaraan masuk abu-abu, tertutup busa ajaib dan kilauan neon, "
            f"lalu keluar berkilau dan berwarna-warni! Pertunjukan transformasi warna!\n\n"
            f"🚗 Bagian dari seri {SERIES_ID} — tema kendaraan berbeda setiap episode!\n\n"
            f"🎯 Sempurna untuk: belajar sebab-akibat, mengenal warna, stimulasi sensorik\n"
            f"👶 Usia: 0–4 tahun | 📺 30 menit\n\n"
            f"🔔 Subscribe → {ch['id']}\n"
            f"🎵 Kevin MacLeod (incompetech.com) — CC Attribution 4.0\n\n"
            f"#{name.replace(' ','')} #HappyBearKids #AnimasiBayi "
            f"#CuciMobilNeon #WarnaMobil\n© Happy Bear Kids Indonesia 2026"
        )
        tags = [name.lower(), "cuci mobil neon", "animasi bayi", "happy bear kids", "30 menit"]
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
        q        = {"en": QUEUE_EN, "ar": QUEUE_AR, "id": QUEUE_ID}[lang]
        stem     = f"carwash_{ep_key}_{DATE_STR}" if lang == "en" else f"carwash_{ep_key}_{DATE_STR}_{lang}"
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
        print(f"{'Episode':12s}  {'EN name':25s}  {'Vehicles':4s}")
        for k, ep in EPISODES.items():
            print(f"  {k:12s}  {ep['name_en']:25s}  {len(ep['vehicles'])} vehicles")
        return

    keys = list(EPISODES) if not args.episodes or args.episodes == ["all"] else args.episodes
    bad  = [k for k in keys if k not in EPISODES]
    if bad:
        print(f"Unknown episodes: {bad}"); sys.exit(1)

    if args.regen_meta:
        for k in keys:
            for lang in ("en", "ar", "id"):
                q    = {"en": QUEUE_EN, "ar": QUEUE_AR, "id": QUEUE_ID}[lang]
                stem = f"carwash_{k}_{DATE_STR}" if lang == "en" else f"carwash_{k}_{DATE_STR}_{lang}"
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
