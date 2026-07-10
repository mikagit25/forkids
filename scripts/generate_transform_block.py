#!/usr/bin/env python3
"""
Generate Transform Block videos — 4 videos per block, 5 blocks = 20 total.
Scenario docs: config/scenarios/transform_block_transform_*.txt

Each block has 4 scenarios:
  Block 1 (transform_1_fruits):   1.1 Fruit grows | 1.2 Shape morphing | 1.3 Big-small pulse | 1.4 Split-merge
  Block 2 (transform_2_color):    2.1 Color mixing | 2.2 Rainbow birth | 2.3 Color wave | 2.4 Fireworks
  Block 3 (transform_3_physics):  3.1 Gravity balls | 3.2 Magnetism | 3.3 Water ripples | 3.4 Wind leaves
  Block 4 (transform_4_patterns): 4.1 Kaleidoscope | 4.2 Tessellations | 4.3 Spiral | 4.4 Symmetry mirror
  Block 5 (transform_5_nature):   5.1 Day-night | 5.2 Seasons | 5.3 Plant growth | 5.4 Ocean tides

No text → publish to EN+AR+ID (same video, 3 separate meta files).

Usage:
  python3 scripts/generate_transform_block.py --key transform_1_fruits  # block 1 (4 videos)
  python3 scripts/generate_transform_block.py --key transform_2_color   # block 2
  python3 scripts/generate_transform_block.py --video 1.1               # specific video
  python3 scripts/generate_transform_block.py --dry-run
"""
import argparse, base64, json, subprocess, sys, time, yaml
from datetime import datetime
from pathlib import Path

ROOT     = Path(__file__).resolve().parent.parent
REMOTION = ROOT / "remotion"
QUEUE_EN = ROOT / "output" / "queue"
QUEUE_AR = ROOT / "output" / "queue_ar"
QUEUE_ID = ROOT / "output" / "queue_id"
TOGETHER_KEY_FILE = ROOT / "credentials" / "together_api_key.txt"
TOGETHER_URL   = "https://api.together.xyz/v1/images/generations"
TOGETHER_MODEL = "black-forest-labs/FLUX.1-schnell"
DATE_STR = datetime.now().strftime("%Y%m%d")

_ALL_TRACKS = [
    "Carefree.mp3", "Crinoline Dreams.mp3", "Gymnopedie No 1.mp3",
    "Happy Happy Game Show.mp3", "Heartwarming.mp3", "Hyperfun.mp3",
    "Life of Riley.mp3", "Merry Go.mp3", "Monkeys Spinning Monkeys.mp3",
    "Overworld.mp3", "Pinball Spring.mp3", "Pixelland.mp3",
    "Quirky Dog.mp3", "Salty Ditty.mp3", "Sneaky Snitch.mp3",
    "Wholesome.mp3", "Fluffing a Duck.mp3", "Walking Along.mp3",
    "George Street Shuffle.mp3", "Circus of Freaks.mp3",
]

def alt_music(en_music: str, ep_idx: int, lang: str) -> str:
    if lang == "en":
        return en_music
    offset = 7 if lang == "ar" else 14
    pool = [t for t in _ALL_TRACKS if t != en_music]
    return pool[(ep_idx + offset) % len(pool)]

# All 20 videos across 5 blocks
BLOCKS = {
    "transform_1_fruits": {
        "name": "Transformations",
        "videos": {
            "1_1": {"name_en": "Fruit Grows",         "name_ar": "الفاكهة تنمو",      "name_id": "Buah Tumbuh",       "bg": "#0A1A08", "accent": "#4CAF50", "bpm": 65, "music": "Carefree.mp3"},
            "1_2": {"name_en": "Shape Morphing",       "name_ar": "تحول الأشكال",     "name_id": "Morfing Bentuk",    "bg": "#0A0A1A", "accent": "#9B59B6", "bpm": 70, "music": "Wholesome.mp3"},
            "1_3": {"name_en": "Big and Small",        "name_ar": "كبير وصغير",       "name_id": "Besar dan Kecil",   "bg": "#1A0A1A", "accent": "#E91E63", "bpm": 60, "music": "Merry Go.mp3"},
            "1_4": {"name_en": "Split and Merge",      "name_ar": "الانقسام والدمج",  "name_id": "Pisah dan Gabung",  "bg": "#0A1A1A", "accent": "#00BCD4", "bpm": 72, "music": "Quirky Dog.mp3"},
        }
    },
    "transform_2_color": {
        "name": "Color as Character",
        "videos": {
            "2_1": {"name_en": "Color Mixing",         "name_ar": "مزج الألوان",      "name_id": "Pencampuran Warna", "bg": "#0A0808", "accent": "#FF5722", "bpm": 68, "music": "Happy Happy Game Show.mp3"},
            "2_2": {"name_en": "Rainbow Birth",        "name_ar": "ولادة قوس قزح",   "name_id": "Lahirnya Pelangi",  "bg": "#050510", "accent": "#FF4444", "bpm": 70, "music": "Life of Riley.mp3"},
            "2_3": {"name_en": "Color Wave",           "name_ar": "موجة اللون",       "name_id": "Gelombang Warna",   "bg": "#080508", "accent": "#8BC34A", "bpm": 75, "music": "Pinball Spring.mp3"},
            "2_4": {"name_en": "Fireworks",            "name_ar": "الألعاب النارية",  "name_id": "Kembang Api",       "bg": "#020205", "accent": "#FFEB3B", "bpm": 88, "music": "Hyperfun.mp3"},
        }
    },
    "transform_3_physics": {
        "name": "Physical Phenomena",
        "videos": {
            "3_1": {"name_en": "Gravity Balls",        "name_ar": "كرات الجاذبية",    "name_id": "Bola Gravitasi",    "bg": "#0A0A0A", "accent": "#FF9800", "bpm": 80, "music": "Monkeys Spinning Monkeys.mp3"},
            "3_2": {"name_en": "Magnetism",            "name_ar": "المغناطيسية",      "name_id": "Magnetisme",        "bg": "#05050F", "accent": "#3F51B5", "bpm": 65, "music": "Gymnopedie No 1.mp3"},
            "3_3": {"name_en": "Water Ripples",        "name_ar": "تموجات الماء",     "name_id": "Riak Air",          "bg": "#020A12", "accent": "#03A9F4", "bpm": 58, "music": "Crinoline Dreams.mp3"},
            "3_4": {"name_en": "Wind and Leaves",      "name_ar": "الريح والأوراق",   "name_id": "Angin dan Daun",    "bg": "#080F05", "accent": "#8BC34A", "bpm": 62, "music": "Carefree.mp3"},
        }
    },
    "transform_4_patterns": {
        "name": "Patterns and Symmetry",
        "videos": {
            "4_1": {"name_en": "Kaleidoscope",         "name_ar": "الكليدوسكوب",      "name_id": "Kaleidoskop",       "bg": "#080010", "accent": "#E040FB", "bpm": 70, "music": "Quirky Dog.mp3"},
            "4_2": {"name_en": "Tessellations",        "name_ar": "التبليطات",        "name_id": "Teselasi",          "bg": "#050808", "accent": "#26A69A", "bpm": 60, "music": "Wholesome.mp3"},
            "4_3": {"name_en": "Spiral",               "name_ar": "اللولبية",         "name_id": "Spiral",            "bg": "#0A0510", "accent": "#FF7043", "bpm": 55, "music": "Heartwarming.mp3"},
            "4_4": {"name_en": "Mirror Symmetry",      "name_ar": "تناسق المرآة",     "name_id": "Simetri Cermin",    "bg": "#050A0A", "accent": "#00E5FF", "bpm": 65, "music": "Merry Go.mp3"},
        }
    },
    "transform_5_nature": {
        "name": "Natural Cycles",
        "videos": {
            "5_1": {"name_en": "Day and Night",        "name_ar": "النهار والليل",    "name_id": "Siang dan Malam",   "bg": "#020508", "accent": "#FF8F00", "bpm": 50, "music": "Gymnopedie No 1.mp3"},
            "5_2": {"name_en": "Four Seasons",         "name_ar": "الفصول الأربعة",   "name_id": "Empat Musim",       "bg": "#050A05", "accent": "#4CAF50", "bpm": 55, "music": "Carefree.mp3"},
            "5_3": {"name_en": "Plant Growth",         "name_ar": "نمو النبات",       "name_id": "Pertumbuhan Tanaman","bg":"#030A03", "accent": "#66BB6A", "bpm": 48, "music": "Crinoline Dreams.mp3"},
            "5_4": {"name_en": "Ocean Tides",          "name_ar": "مد وجزر المحيط",  "name_id": "Pasang Surut Laut", "bg": "#020612", "accent": "#0288D1", "bpm": 45, "music": "Heartwarming.mp3"},
        }
    },
}


def make_meta(block_key, vid_key, lang):
    block = BLOCKS[block_key]
    vid   = block["videos"][vid_key]
    ch    = {'en': '@HappyBearKids1', 'ar': '@happybearkidsar', 'id': '@happybearkidsin'}
    name  = vid[f'name_{lang}']
    block_name = block['name']

    if lang == 'en':
        return {
            "title": f"{name} | Abstract Animation for Babies | Happy Bear Kids",
            "description": (
                f"✨ {name} — mesmerizing abstract animation for babies and toddlers!\n\n"
                f"Part of our '{block_name}' series — pure visual magic with no words, "
                f"no text — just beautiful animated transformations set to gentle music.\n\n"
                f"🎯 Perfect for: visual stimulation, background play, calming screen time\n"
                f"🌈 No language barriers — universal content for any culture\n\n"
                f"🔔 Subscribe → {ch['en']}\n"
                f"🎵 Kevin MacLeod (incompetech.com) — CC Attribution 4.0\n\n"
                f"#AbstractAnimation #{name.replace(' ','')} #HappyBearKids "
                f"#BabyVisual #VisualStimulation #CalmBabyVideo\n© Happy Bear Kids 2026"
            ),
            "tags": ["abstract animation", name.lower(), "baby visual", "visual stimulation",
                     "happy bear kids", "no talking", "calm baby", block_name.lower()],
            "video_type": "transform_block", "language": "en", "is_short": False, "status": "public",
        }
    elif lang == 'ar':
        return {
            "title": f"{name} | رسوم متحركة مجردة للرضع | هابي بير كيدز",
            "description": (
                f"✨ {name} — رسوم متحركة مجردة ساحرة للرضع والأطفال الصغار!\n\n"
                f"تحفيز بصري خالص — بدون كلمات أو نصوص. محتوى عالمي لجميع الثقافات.\n\n"
                f"🔔 اشتركوا → {ch['ar']}\n"
                f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
                f"#رسوم_مجردة #{name.replace(' ','_')} #هابي_بير_كيدز "
                f"#تحفيز_بصري\n© هابي بير كيدز 2026"
            ),
            "tags": ["رسوم مجردة", name, "تحفيز بصري", "هابي بير كيدز", "بدون كلام"],
            "video_type": "transform_block", "language": "ar", "is_short": False, "status": "public",
        }
    else:
        return {
            "title": f"{name} | Animasi Abstrak untuk Bayi | Happy Bear Kids",
            "description": (
                f"✨ {name} — animasi abstrak yang memukau untuk bayi dan balita!\n\n"
                f"Stimulasi visual murni — tanpa kata-kata atau teks. Konten universal.\n\n"
                f"🔔 Subscribe → {ch['id']}\n"
                f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
                f"#AnimasiAbstrak #{name.replace(' ','')} #HappyBearKids "
                f"#StimulasiVisual\n© Happy Bear Kids Indonesia 2026"
            ),
            "tags": ["animasi abstrak", name.lower(), "stimulasi visual", "happy bear kids", "tanpa suara"],
            "video_type": "transform_block", "language": "id", "is_short": False, "status": "public",
        }


def generate_thumbnail(prompt: str, out_path: Path) -> bool:
    if out_path.exists():
        return True
    try:
        import importlib.util
        key = TOGETHER_KEY_FILE.read_text().strip()
        spec = importlib.util.spec_from_file_location("gat", ROOT / "scripts" / "generate_ai_thumbs.py")
        gat = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gat)
        img = gat.together_generate_image(prompt, key)
        if img:
            out_path.write_bytes(gat.resize_to_720p(img))
            print(f"  ✓ thumb → {out_path.name}")
            return True
        print(f"  ! thumb failed: API returned no image")
        return False
    except Exception as e:
        print(f"  ! thumb failed: {e}")
        return False


def process_video(block_key, vid_key, ep_idx, dry_run, regen_meta):
    vid  = BLOCKS[block_key]["videos"][vid_key]
    name = f"transform_{vid_key}_{DATE_STR}.mp4"
    ok   = True

    for lang, queue in [("en", QUEUE_EN), ("ar", QUEUE_AR), ("id", QUEUE_ID)]:
        out_mp4    = queue / name
        lang_music = alt_music(vid["music"], ep_idx, lang)
        props = {
            "shapes": ["circle", "star", "square"],
            "colors": [vid["accent"], "#FFFFFF", vid["accent"]],
            "bgColor": vid["bg"], "bpm": vid["bpm"],
            "showLabels": False, "musicFile": lang_music,
        }
        if not out_mp4.exists() and not dry_run and not regen_meta:
            cmd = ["npx", "remotion", "render", "ShapeDanceLong",
                   f"--props={json.dumps(props)}", f"--output={str(out_mp4)}"]
            print(f"  Render ({lang}): {out_mp4.name}")
            r = subprocess.run(cmd, cwd=str(REMOTION), timeout=21600)
            if r.returncode != 0:
                print(f"  FAILED ({lang})")
                ok = False
                continue

        mp = queue / f"meta_{Path(name).stem}.yaml"
        if not mp.exists() or regen_meta:
            meta = make_meta(block_key, vid_key, lang)
            if not dry_run:
                with open(mp, 'w', encoding='utf-8') as f:
                    yaml.dump(meta, f, allow_unicode=True)
            print(f"  Meta ({lang}): {mp.name}")

        tp = queue / f"thumb_{Path(name).stem}.png"
        no_text = ", no text, no letters, no words, no numbers" if lang == "ar" else ""
        thumb_prompt = (
            f"abstract baby animation: {vid['name_en'].lower()}, colorful glowing shapes, "
            f"dark background, accent color {vid['accent']}, smooth motion, "
            f"children's YouTube thumbnail{no_text}"
        )
        if not dry_run:
            generate_thumbnail(thumb_prompt, tp)
            time.sleep(1)

    return ok


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--key',       default=None, help='block key e.g. transform_1_fruits')
    parser.add_argument('--video',     default=None, help='specific video e.g. 1_1')
    parser.add_argument('--lang',      default='both')
    parser.add_argument('--dry-run',   action='store_true')
    parser.add_argument('--regen-meta',action='store_true')
    args = parser.parse_args()

    # Determine which block(s) to process
    if args.key and args.key in BLOCKS:
        block_keys = [args.key]
    else:
        block_keys = list(BLOCKS.keys())

    # Build global ep_idx across all blocks/videos
    all_vid_keys = [(bk, vk) for bk in BLOCKS for vk in BLOCKS[bk]["videos"]]
    for block_key in block_keys:
        block = BLOCKS[block_key]
        vid_keys = [args.video] if args.video else list(block["videos"].keys())
        print(f"\n=== Block: {block['name']} ({len(vid_keys)} videos) ===")
        for vid_key in vid_keys:
            if vid_key not in block["videos"]:
                print(f"  Unknown video: {vid_key}")
                continue
            vid = block["videos"][vid_key]
            ep_idx = all_vid_keys.index((block_key, vid_key))
            print(f"\n[{vid_key}] {vid['name_en']}")
            process_video(block_key, vid_key, ep_idx, args.dry_run, args.regen_meta)


if __name__ == '__main__':
    main()
