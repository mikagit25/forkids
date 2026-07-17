#!/usr/bin/env python3
"""
Generate CharacterDialogueLong videos — bear character speaks TO the child.
Covers: emotions, colors_character, numbers_character, animals_character.

Full automatic pipeline per episode × language:
  1. Generate missing bear/emotion/concept sprites (FLUX 3D)
  2. Generate missing TTS audio (edge-tts)
  3. Render Remotion CharacterDialogueLong composition
  4. Generate thumbnail via Together.ai FLUX
  5. Write meta YAML with full description
  6. Copy to appropriate queue folder

Usage:
  python3 scripts/generate_character_dialogue_long.py
  python3 scripts/generate_character_dialogue_long.py --episode emotions
  python3 scripts/generate_character_dialogue_long.py --episode emotions --lang en
  python3 scripts/generate_character_dialogue_long.py --regen-meta   # thumbnails + meta only
  python3 scripts/generate_character_dialogue_long.py --force         # overwrite renders
  python3 scripts/generate_character_dialogue_long.py --dry-run       # show what would run
"""
import argparse
import asyncio
import base64
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml

ROOT              = Path(__file__).resolve().parent.parent
DATA_PATH         = ROOT / "config" / "character_dialogue_data.yaml"
QUEUE_EN          = ROOT / "output" / "queue"
QUEUE_AR          = ROOT / "output" / "queue_ar"
QUEUE_ID          = ROOT / "output" / "queue_id"
REMOTION          = ROOT / "remotion"
AUDIO_DIR         = ROOT / "remotion" / "public" / "audio" / "character_dialogue"
SPRITES_DIR       = ROOT / "remotion" / "public" / "sprites"
TOGETHER_KEY_FILE = ROOT / "credentials" / "together_api_key.txt"
TOGETHER_URL      = "https://api.together.xyz/v1/images/generations"
TOGETHER_MODEL    = "black-forest-labs/FLUX.1-schnell"

QUEUE_MAP = {"en": QUEUE_EN, "ar": QUEUE_AR, "id": QUEUE_ID}
LANG_NAMES = {"en": "English", "ar": "Arabic", "id": "Indonesian"}
RTL_LANGS  = {"ar"}

MUSIC_TRACKS = [
    "Carefree.mp3", "Happy Happy Game Show.mp3", "Pinball Spring.mp3",
    "Wholesome.mp3", "Life of Riley.mp3", "Overworld.mp3",
]


# ── Thumbnail prompt per episode ──────────────────────────────────────────────
THUMB_PROMPTS: dict[str, str] = {
    "emotions": (
        "Cute 3D Pixar-style brown teddy bear with big happy eyes surrounded by "
        "colorful emotion face emojis — happy yellow, sad blue, angry red, surprised purple, "
        "bright cheerful background, children's educational YouTube thumbnail style, "
        "bold outlines, vivid colors, no text"
    ),
    "colors_character": (
        "Cute 3D Pixar-style brown teddy bear holding colorful paint splashes — "
        "red, blue, yellow, green — bright cheerful background, "
        "children's educational YouTube thumbnail style, bold outlines, vivid colors, no text"
    ),
    "numbers_character": (
        "Cute 3D Pixar-style brown teddy bear counting on fingers, "
        "big numbers 1 2 3 4 floating around in bright colors, "
        "cheerful background, children's educational YouTube thumbnail style, "
        "bold outlines, vivid colors, no text"
    ),
    "animals_character": (
        "Cute 3D Pixar-style brown teddy bear surrounded by cute animals — "
        "duck, cat, frog, elephant — all Pixar 3D style, bright cheerful background, "
        "children's educational YouTube thumbnail style, bold outlines, vivid colors, no text"
    ),
}

# ── Meta descriptions ─────────────────────────────────────────────────────────
META_DESCRIPTIONS: dict[str, dict[str, str]] = {
    "emotions": {
        "en": (
            "Join Roundy the Bear and learn about feelings and emotions! "
            "In this 20-minute educational video for toddlers and babies, "
            "Roundy teaches your child about HAPPY, SAD, ANGRY, and SURPRISED. "
            "Roundy speaks directly to your child, asks them to repeat the words, "
            "and encourages them with warm loving dialogue.\n\n"
            "Perfect for toddlers aged 1-4 years! Your little one will love learning "
            "emotional vocabulary with their new bear friend Roundy!\n\n"
            "What your child will learn:\n"
            "✓ HAPPY — how to recognize and express happiness\n"
            "✓ SAD — it's okay to feel sad, everyone does\n"
            "✓ ANGRY — identifying anger and taking deep breaths\n"
            "✓ SURPRISED — the excitement of unexpected moments\n\n"
            "Each concept is repeated multiple times with interactive questions: "
            "\"Can you say HAPPY? Say it with me!\" — helping children build "
            "emotional vocabulary and language skills simultaneously.\n\n"
            "🐻 Happy Bear Kids creates educational content for babies and toddlers "
            "aged 0-4, focusing on language development, emotional intelligence, "
            "and early learning through engaging Pixar-style animation and "
            "warm character dialogue.\n\n"
            "Subscribe for more learning videos with Roundy!\n\n"
            "🎵 Original music by Happy Bear Kids (AI-generated, © 2026)\n\n"
            "#feelings #emotions #toddlerlearning #babyvideo #preschool "
            "#happybearkids #roundythebear #emotionallearning #kidslearning "
            "#educationalvideo #toddler #babies #learningforkids"
        ),
        "ar": (
            "انضم إلى راوندي الدب وتعلم عن المشاعر والأحاسيس! "
            "في هذا الفيديو التعليمي لمدة 20 دقيقة للأطفال الصغار، "
            "يعلم راوندي طفلك عن السعيد والحزين والغاضب والمندهش.\n\n"
            "راوندي يتحدث مباشرة مع طفلك، يطلب منه تكرار الكلمات، "
            "ويشجعه بحوار دافئ ومحب.\n\n"
            "مثالي للأطفال من عمر 1-4 سنوات!\n\n"
            "ما سيتعلمه طفلك:\n"
            "✓ سعيد — كيفية التعرف على السعادة والتعبير عنها\n"
            "✓ حزين — من الطبيعي أن تشعر بالحزن أحياناً\n"
            "✓ غاضب — التعرف على الغضب والتنفس العميق\n"
            "✓ مندهش — إثارة اللحظات غير المتوقعة\n\n"
            "🐻 هابي بير كيدز يصنع محتوى تعليمياً للأطفال من 0-4 سنوات.\n\n"
            "اشترك للمزيد من مقاطع التعلم مع راوندي!\n\n"
            "🎵 موسيقى أصلية من هابي بير كيدز\n\n"
            "#مشاعر #تعليم_اطفال #هابي_بير_كيدز #راوندي #اطفال #تعلم"
        ),
        "id": (
            "Bergabunglah dengan Roundy si Beruang dan belajar tentang perasaan dan emosi! "
            "Dalam video edukasi 20 menit untuk balita ini, "
            "Roundy mengajarkan anakmu tentang SENANG, SEDIH, MARAH, dan TERKEJUT.\n\n"
            "Roundy berbicara langsung kepada anakmu, meminta mereka mengulang kata-kata, "
            "dan mendorong mereka dengan dialog yang hangat dan penuh kasih.\n\n"
            "Cocok untuk balita usia 1-4 tahun!\n\n"
            "Yang akan dipelajari anakmu:\n"
            "✓ SENANG — cara mengenali dan mengekspresikan kebahagiaan\n"
            "✓ SEDIH — tidak apa-apa merasa sedih, semua orang pernah merasakannya\n"
            "✓ MARAH — mengenali kemarahan dan menarik napas dalam-dalam\n"
            "✓ TERKEJUT — kegembiraan dari momen yang tidak terduga\n\n"
            "🐻 Happy Bear Kids membuat konten edukasi untuk bayi dan balita usia 0-4 tahun.\n\n"
            "Berlangganan untuk video belajar lebih banyak bersama Roundy!\n\n"
            "🎵 Original music by Happy Bear Kids (AI-generated, © 2026)\n\n"
            "#perasaan #emosi #belajarbalita #happybearkids #roundy #anakbelajar"
        ),
    },
    "colors_character": {
        "en": (
            "Learn COLORS with Roundy the Bear! Join your favorite bear friend "
            "for a fun 20-minute color learning adventure!\n\n"
            "Roundy teaches RED, BLUE, YELLOW, and GREEN through exciting interactive "
            "dialogue. He asks your child to find colors around them, say the words "
            "out loud, and celebrates every answer!\n\n"
            "Perfect for toddlers aged 1-4 years learning color recognition!\n\n"
            "🐻 Happy Bear Kids — educational videos for babies and toddlers.\n\n"
            "Subscribe for more learning with Roundy!\n\n"
            "🎵 Original music by Happy Bear Kids (AI-generated, © 2026)\n\n"
            "#colors #learncolors #toddler #preschool #happybearkids #roundy "
            "#colorlearning #babyvideo #educationalvideo #kidslearning"
        ),
        "ar": (
            "تعلم الألوان مع راوندي الدب! انضم لصديقك الدب المفضل "
            "لمغامرة تعلم الألوان الممتعة لمدة 20 دقيقة!\n\n"
            "راوندي يعلم الأحمر والأزرق والأصفر والأخضر من خلال حوار تفاعلي ممتع.\n\n"
            "🐻 هابي بير كيدز — مقاطع تعليمية للأطفال.\n\n"
            "اشترك للمزيد مع راوندي!\n\n"
            "🎵 موسيقى أصلية من هابي بير كيدز\n\n"
            "#الوان #تعلم_الالوان #اطفال #تعليم #هابي_بير_كيدز #راوندي"
        ),
        "id": (
            "Belajar WARNA bersama Roundy si Beruang! Bergabunglah dengan teman beruang "
            "favoritmu untuk petualangan belajar warna yang menyenangkan selama 20 menit!\n\n"
            "Roundy mengajarkan MERAH, BIRU, KUNING, dan HIJAU melalui dialog interaktif.\n\n"
            "🐻 Happy Bear Kids — video edukasi untuk bayi dan balita.\n\n"
            "Berlangganan untuk belajar lebih banyak bersama Roundy!\n\n"
            "🎵 Original music by Happy Bear Kids (AI-generated, © 2026)\n\n"
            "#warna #belajarwarna #balita #prasekolah #happybearkids #roundy"
        ),
    },
    "numbers_character": {
        "en": (
            "Count with Roundy the Bear! Learn numbers 1, 2, 3, 4 "
            "in this fun 20-minute counting adventure!\n\n"
            "Roundy counts with your child, asks them to hold up fingers, "
            "and makes learning numbers exciting and interactive!\n\n"
            "Perfect for toddlers aged 1-4 years learning to count!\n\n"
            "🐻 Happy Bear Kids — educational videos for babies and toddlers.\n\n"
            "Subscribe for more learning with Roundy!\n\n"
            "🎵 Original music by Happy Bear Kids (AI-generated, © 2026)\n\n"
            "#numbers #counting #toddler #preschool #happybearkids #roundy "
            "#learntocount #kidslearning #educationalvideo"
        ),
        "ar": (
            "اعد مع راوندي الدب! تعلم الأرقام 1، 2، 3، 4 "
            "في مغامرة عد ممتعة لمدة 20 دقيقة!\n\n"
            "راوندي يعد مع طفلك ويطلب منه رفع أصابعه!\n\n"
            "🐻 هابي بير كيدز — مقاطع تعليمية للأطفال.\n\n"
            "🎵 موسيقى أصلية من هابي بير كيدز\n\n"
            "#ارقام #عد #اطفال #تعليم #هابي_بير_كيدز #راوندي"
        ),
        "id": (
            "Hitung bersama Roundy si Beruang! Belajar angka 1, 2, 3, 4 "
            "dalam petualangan menghitung yang menyenangkan selama 20 menit!\n\n"
            "Roundy menghitung bersama anakmu dan meminta mereka mengangkat jari!\n\n"
            "🐻 Happy Bear Kids — video edukasi untuk bayi dan balita.\n\n"
            "🎵 Original music by Happy Bear Kids (AI-generated, © 2026)\n\n"
            "#angka #menghitung #balita #prasekolah #happybearkids #roundy"
        ),
    },
    "animals_character": {
        "en": (
            "Learn ANIMALS with Roundy the Bear! Meet cute animals — "
            "Duck, Cat, Frog, and Elephant — in this 20-minute learning adventure!\n\n"
            "Roundy introduces each animal with their sound, asks your child to repeat, "
            "and makes animal learning fun and interactive!\n\n"
            "Perfect for toddlers aged 1-4 years!\n\n"
            "🐻 Happy Bear Kids — educational videos for babies and toddlers.\n\n"
            "Subscribe for more learning with Roundy!\n\n"
            "🎵 Original music by Happy Bear Kids (AI-generated, © 2026)\n\n"
            "#animals #animalsforkids #toddler #preschool #happybearkids #roundy "
            "#learnanimals #kidslearning #educationalvideo"
        ),
        "ar": (
            "تعلم الحيوانات مع راوندي الدب! تعرف على حيوانات لطيفة — "
            "بطة وقط وضفدع وفيل — في مغامرة تعلم ممتعة لمدة 20 دقيقة!\n\n"
            "🐻 هابي بير كيدز — مقاطع تعليمية للأطفال.\n\n"
            "🎵 موسيقى أصلية من هابي بير كيدز\n\n"
            "#حيوانات #تعلم_الحيوانات #اطفال #تعليم #هابي_بير_كيدز"
        ),
        "id": (
            "Belajar HEWAN bersama Roundy si Beruang! Temui hewan-hewan lucu — "
            "Bebek, Kucing, Katak, dan Gajah — dalam petualangan belajar 20 menit!\n\n"
            "🐻 Happy Bear Kids — video edukasi untuk bayi dan balita.\n\n"
            "🎵 Original music by Happy Bear Kids (AI-generated, © 2026)\n\n"
            "#hewan #belajarhewan #balita #prasekolah #happybearkids #roundy"
        ),
    },
}


def load_data() -> list:
    with open(DATA_PATH) as f:
        return yaml.safe_load(f)["episodes"]


def load_together_key() -> str | None:
    if TOGETHER_KEY_FILE.exists():
        return TOGETHER_KEY_FILE.read_text().strip()
    return None


def flux_generate(prompt: str, key: str) -> bytes | None:
    try:
        import requests
        r = requests.post(
            TOGETHER_URL,
            headers={"Authorization": f"Bearer {key}"},
            json={"model": TOGETHER_MODEL, "prompt": prompt,
                  "width": 1280, "height": 720, "steps": 4, "n": 1},
            timeout=90,
        )
        if r.status_code != 200:
            print(f"    Thumbnail API {r.status_code}: {r.text[:80]}")
            return None
        item = r.json()["data"][0]
        b64 = item.get("b64_json")
        if b64:
            return base64.b64decode(b64)
        url = item.get("url")
        if url:
            ir = requests.get(url, timeout=30)
            return ir.content if ir.status_code == 200 else None
    except Exception as e:
        print(f"    Thumbnail failed: {e}")
    return None


def ensure_sprites(episode_key: str) -> None:
    """Run bear sprite generator if required sprites are missing."""
    required = [
        SPRITES_DIR / "characters" / "bear_happy_3d.png",
        SPRITES_DIR / "characters" / "bear_talking_3d.png",
    ]
    if episode_key == "emotions":
        required += [
            SPRITES_DIR / "emotions" / "happy_3d.png",
            SPRITES_DIR / "emotions" / "sad_3d.png",
            SPRITES_DIR / "emotions" / "angry_3d.png",
            SPRITES_DIR / "emotions" / "surprised_3d.png",
        ]

    missing = [p for p in required if not p.exists()]
    if not missing:
        print(f"  ✓ All sprites present")
        return

    print(f"  Generating {len(missing)} missing sprites...")
    cmd = [sys.executable, str(ROOT / "scripts" / "generate_bear_sprites.py")]
    r = subprocess.run(cmd, timeout=600)
    if r.returncode != 0:
        print(f"  WARNING: sprite generation failed (non-critical, may have partial sprites)")


def ensure_audio(episode_key: str, lang: str) -> None:
    """Run character dialogue audio generator if audio is missing."""
    out_dir = AUDIO_DIR / lang / episode_key
    sections = ["intro", "scene1", "scene2", "scene3", "scene4", "song", "outro"]
    missing = [s for s in sections
               if not (out_dir / f"{episode_key}_{s}.mp3").exists()]
    if not missing:
        print(f"  ✓ All audio present for {episode_key}/{lang}")
        return

    print(f"  Generating {len(missing)} missing audio sections for {episode_key}/{lang}...")
    cmd = [sys.executable, str(ROOT / "scripts" / "generate_character_dialogue_audio.py"),
           "--episode", episode_key, "--lang", lang]
    r = subprocess.run(cmd, timeout=300)
    if r.returncode != 0:
        print(f"  WARNING: audio generation failed for {episode_key}/{lang}")


def make_props(ep: dict, lang: str) -> dict:
    rtl = lang in RTL_LANGS

    def scene_title(scene: dict) -> str:
        return scene.get(f"title_{lang}", scene["title_en"])

    return {
        "episodeKey":      ep["key"],
        "episodeTitle":    ep.get(f"title_{lang}", ep["title_en"]),
        "characterSprite": ep["character_sprite"],
        "accentColor":     ep["accent_color"],
        "bgColor":         ep["bg_color"],
        "rtl":             rtl,
        "lang":            lang,
        "musicFile":       ep["music_file"],
        "audioBase":       f"audio/character_dialogue/{lang}/{ep['key']}/{ep['key']}",
        "scenes": [
            {
                "id":             sc["id"],
                "title":          sc["title_en"],
                "titleLocalized": scene_title(sc),
                "spritePath":     sc["sprite"],
                "bgColor":        sc["bg_color"],
            }
            for sc in ep["scenes"]
        ],
    }


def render_video(props: dict, out_path: Path, dry_run: bool) -> bool:
    props_json = json.dumps(props)
    cmd = [
        "npx", "remotion", "render",
        "CharacterDialogueLong",
        str(out_path),
        "--props", props_json,
        "--log", "error",
    ]
    print(f"  Render → {out_path.name}")
    if dry_run:
        print(f"  [DRY RUN] {' '.join(cmd[:4])} ...")
        return True
    result = subprocess.run(cmd, cwd=str(REMOTION), timeout=7200)
    return result.returncode == 0


def generate_thumbnail(ep_key: str, lang: str, out_path: Path, together_key: str) -> bool:
    prompt = THUMB_PROMPTS.get(ep_key, THUMB_PROMPTS["emotions"])
    if lang == "ar":
        prompt += ", no text, no letters, no words, no numbers"
    print(f"  Generating thumbnail...", end=" ", flush=True)
    data = flux_generate(prompt, together_key)
    if data:
        out_path.write_bytes(data)
        print(f"✓ {len(data)//1024}KB")
        return True
    print("FAILED")
    return False


def write_meta(ep: dict, lang: str, mp4_name: str, queue_dir: Path) -> None:
    ep_key      = ep["key"]
    title       = ep.get(f"title_{lang}", ep["title_en"])
    description = META_DESCRIPTIONS.get(ep_key, {}).get(lang, "")
    tags_base   = {
        "en": ["happy bear kids", "roundy bear", "character learning", "toddler",
               "preschool", "babies", "educational video", "kids learning",
               "20 minutes for toddlers"],
        "ar": ["هابي بير كيدز", "راوندي", "تعليم اطفال", "رياض اطفال", "اطفال صغار"],
        "id": ["happy bear kids", "roundy", "belajar anak", "balita", "prasekolah",
               "video edukasi", "anak belajar"],
    }
    tags = tags_base.get(lang, [])

    meta_name = "meta_" + mp4_name.replace(".mp4", ".yaml")
    meta_path = queue_dir / meta_name
    meta = {
        "title":       title,
        "description": description,
        "tags":        tags,
        "video_type":  "character_dialogue",
        "language":    lang,
        "is_short":    False,
        "status":      "public",
    }
    with open(meta_path, "w") as f:
        yaml.dump(meta, f, allow_unicode=True, default_flow_style=False)
    print(f"  Meta → {meta_name}")


def process_episode(ep: dict, lang: str, together_key: str | None,
                    force: bool, regen_meta: bool, dry_run: bool) -> bool:
    ep_key    = ep["key"]
    date_str  = datetime.now().strftime("%Y%m%d")
    mp4_name  = f"character_dialogue_{ep_key}_{lang}_{date_str}.mp4"
    queue_dir = QUEUE_MAP[lang]
    out_mp4   = queue_dir / mp4_name
    thumb_name = "thumb_" + mp4_name.replace(".mp4", ".png")
    out_thumb  = queue_dir / thumb_name

    queue_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n[{ep_key} / {lang}]")

    if not regen_meta:
        # ── STEP 1: sprites ──
        ensure_sprites(ep_key)

        # ── STEP 2: audio ──
        ensure_audio(ep_key, lang)

        # ── STEP 3: render ──
        if out_mp4.exists() and not force:
            print(f"  ✓ Video exists — skip render (--force to overwrite)")
        else:
            props = make_props(ep, lang)
            ok = render_video(props, out_mp4, dry_run)
            if not ok:
                print(f"  FAILED render: {ep_key} / {lang}")
                return False

    # ── STEP 4: thumbnail ──
    if not out_thumb.exists() or force or regen_meta:
        if together_key:
            generate_thumbnail(ep_key, lang, out_thumb, together_key)
        else:
            print(f"  No Together.ai key — thumbnail skipped")

    # ── STEP 5: meta ──
    write_meta(ep, lang, mp4_name, queue_dir)

    print(f"  ✓ {ep_key}/{lang} → {queue_dir.name}/{mp4_name}")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode", help="Single episode key (e.g. emotions)")
    parser.add_argument("--lang",    choices=["en", "ar", "id"],
                        help="Single language (default: all)")
    parser.add_argument("--force",     action="store_true", help="Overwrite existing renders")
    parser.add_argument("--regen-meta", action="store_true",
                        help="Regenerate thumbnails + meta only (skip render)")
    parser.add_argument("--dry-run",  action="store_true", help="Show plan, no rendering")
    args = parser.parse_args()

    episodes = load_data()
    if args.episode:
        episodes = [e for e in episodes if e["key"] == args.episode]
        if not episodes:
            sys.exit(f"Episode not found: {args.episode}")

    langs = [args.lang] if args.lang else ["en", "ar", "id"]
    together_key = load_together_key()

    ok = fail = 0
    for ep in episodes:
        for lg in langs:
            success = process_episode(
                ep, lg, together_key,
                force=args.force,
                regen_meta=args.regen_meta,
                dry_run=args.dry_run,
            )
            if success:
                ok += 1
            else:
                fail += 1
            time.sleep(2)

    print(f"\n{'='*50}")
    print(f"Done: {ok} succeeded, {fail} failed")


if __name__ == "__main__":
    main()
