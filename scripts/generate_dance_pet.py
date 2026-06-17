#!/usr/bin/env python3
"""
Generate Dancing Home Pets series — 33 videos.
Scenario: config/scenarios/dance_pet_dance_pets_series.txt

10 animals × 3 video types:
  A = solo dance, no words → EN+AR+ID (same video, separate meta)
  B = interaction (2 animals together), no words → EN+AR+ID
  C = educational with TTS names/sounds → separate per language

Usage:
  python3 scripts/generate_dance_pet.py               # all 33 videos
  python3 scripts/generate_dance_pet.py --animal cat  # one animal (3 types)
  python3 scripts/generate_dance_pet.py --type A      # all A-type videos
  python3 scripts/generate_dance_pet.py --dry-run
"""
import argparse, base64, json, shutil, subprocess, sys, time, yaml
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

ANIMALS = {
    "cat":        {"name_en": "Cat",        "name_ar": "قطة",          "name_id": "Kucing",       "sound_en": "Meow",   "bpm": 68,  "bg": "#1A0A2E", "accent": "#9B59B6", "sprite": "animals_flux/cat.png",    "has_B": True,  "partner": "dog"},
    "dog":        {"name_en": "Dog",        "name_ar": "كلب",          "name_id": "Anjing",       "sound_en": "Woof",   "bpm": 100, "bg": "#0A1A2E", "accent": "#E67E22", "sprite": "animals_flux/dog.png",    "has_B": True,  "partner": "cat"},
    "rabbit":     {"name_en": "Rabbit",     "name_ar": "أرنب",         "name_id": "Kelinci",      "sound_en": "Squeak", "bpm": 85,  "bg": "#1A2E0A", "accent": "#F39C12", "sprite": "animals_flux/rabbit.png", "has_B": True,  "partner": "duck"},
    "fish":       {"name_en": "Fish",       "name_ar": "سمكة",         "name_id": "Ikan",         "sound_en": "Blub",   "bpm": 60,  "bg": "#0A1E3A", "accent": "#3498DB", "sprite": "animals_flux/fish.png",   "has_B": False},
    "turtle":     {"name_en": "Turtle",     "name_ar": "سلحفاة",       "name_id": "Kura-kura",    "sound_en": "...",    "bpm": 45,  "bg": "#0A2E0A", "accent": "#27AE60", "sprite": "animals_flux/frog.png",   "has_B": False},
    "parrot":     {"name_en": "Parrot",     "name_ar": "ببغاء",        "name_id": "Beo",          "sound_en": "Squawk", "bpm": 110, "bg": "#1A2E0A", "accent": "#E74C3C", "sprite": "animals_flux/parrot.png", "has_B": True,  "partner": "rabbit"},
    "hamster":    {"name_en": "Hamster",    "name_ar": "هامستر",       "name_id": "Hamster",      "sound_en": "Squeak", "bpm": 130, "bg": "#2E1A0A", "accent": "#D35400", "sprite": "animals_flux/bear.png",   "has_B": False},
    "guinea_pig": {"name_en": "Guinea Pig", "name_ar": "خنزير غيني",  "name_id": "Marmot",       "sound_en": "Wheek",  "bpm": 80,  "bg": "#2E2A0A", "accent": "#F1C40F", "sprite": "animals_flux/pig.png",    "has_B": False},
    "duck":       {"name_en": "Duck",       "name_ar": "بطة",          "name_id": "Bebek",        "sound_en": "Quack",  "bpm": 85,  "bg": "#0A1A2E", "accent": "#F39C12", "sprite": "animals_flux/duck.png",   "has_B": True,  "partner": "rabbit"},
    "kitten":     {"name_en": "Kitten",     "name_ar": "قطة صغيرة",   "name_id": "Anak Kucing",  "sound_en": "Mew",    "bpm": 95,  "bg": "#2E0A1A", "accent": "#E91E63", "sprite": "animals_flux/cat.png",    "has_B": False},
}

MUSIC_MAP = {
    "cat": "Carefree.mp3",        "dog": "Hyperfun.mp3",
    "rabbit": "Wholesome.mp3",    "fish": "Gymnopedie No 1.mp3",
    "turtle": "Crinoline Dreams.mp3", "parrot": "Quirky Dog.mp3",
    "hamster": "Monkeys Spinning Monkeys.mp3", "guinea_pig": "Life of Riley.mp3",
    "duck": "Happy Happy Game Show.mp3", "kitten": "Merry Go.mp3",
}


def make_meta(animal, vtype, lang):
    a = ANIMALS[animal]
    ch = {'en': '@HappyBearKids1', 'ar': '@happybearkidsar', 'id': '@happybearkidsin'}
    names = {'en': a['name_en'], 'ar': a['name_ar'], 'id': a['name_id']}
    name  = names[lang]

    if vtype == 'A':
        titles = {
            'en': f"Dancing {a['name_en']}! 25 min Baby Animation | Happy Bear Kids",
            'ar': f"رقصة {a['name_ar']}! 25 دقيقة رسوم للرضع | هابي بير كيدز",
            'id': f"Menari {a['name_id']}! 25 menit Animasi Bayi | Happy Bear Kids",
        }
        descs = {
            'en': (f"🐾 Watch adorable animated {a['name_en']} dance for 25 minutes!\n\n"
                   f"Pure visual delight — no words, no text — just a cute {a['name_en'].lower()} moving to gentle music. "
                   f"Perfect for babies of any language! BPM: {a['bpm']}.\n\n"
                   f"Part of Dancing Home Pets series — 10 cute animals!\n"
                   f"🔔 Subscribe → {ch['en']}\n"
                   f"🎵 Kevin MacLeod (incompetech.com) — CC Attribution 4.0\n\n"
                   f"#Dancing{a['name_en']} #HappyBearKids #BabyAnimation #CutePet #PetDance #BabyTV\n© Happy Bear Kids 2026"),
            'ar': (f"🐾 شاهد {a['name_ar']} المتحرك الرائع يرقص لمدة 25 دقيقة!\n\n"
                   f"بهجة بصرية خالصة — بدون كلمات أو نصوص. مثالي للرضع.\n\n"
                   f"🔔 اشتركوا → {ch['ar']}\n"
                   f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
                   f"#رقص_{name.replace(' ','_')} #هابي_بير_كيدز #رسوم_أطفال\n© هابي بير كيدز 2026"),
            'id': (f"🐾 Saksikan {a['name_id']} animasi yang menggemaskan menari selama 25 menit!\n\n"
                   f"Hiburan visual murni — tanpa kata-kata. Sempurna untuk bayi.\n\n"
                   f"🔔 Subscribe → {ch['id']}\n"
                   f"🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
                   f"#Tari{a['name_id'].replace(' ','')} #HappyBearKids #AnimasiAnak\n© Happy Bear Kids Indonesia 2026"),
        }
    elif vtype == 'B':
        partner = a.get('partner', 'friend')
        pname   = ANIMALS.get(partner, {}).get(f'name_{lang}', 'Friend')
        titles = {
            'en': f"{a['name_en']} and {ANIMALS.get(partner,{}).get('name_en','Friend')}! Pet Friends | Happy Bear Kids",
            'ar': f"{a['name_ar']} و{ANIMALS.get(partner,{}).get('name_ar','صديق')}! | هابي بير كيدز",
            'id': f"{a['name_id']} dan {ANIMALS.get(partner,{}).get('name_id','Teman')}! | Happy Bear Kids",
        }
        descs = {
            'en': (f"🐾 Watch {a['name_en']} meet and play with {ANIMALS.get(partner,{}).get('name_en','a friend')}!\n\n"
                   f"Two adorable pets — no words needed, emotions tell the story!\n"
                   f"🔔 Subscribe → {ch['en']}\n🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
                   f"#PetFriends #HappyBearKids #BabyAnimation\n© Happy Bear Kids 2026"),
            'ar': (f"🐾 شاهد {a['name_ar']} و{pname} يلعبان معاً!\n\n"
                   f"🔔 اشتركوا → {ch['ar']}\n🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
                   f"#أصدقاء_الحيوانات #هابي_بير_كيدز\n© هابي بير كيدز 2026"),
            'id': (f"🐾 Saksikan {a['name_id']} dan {pname} bermain bersama!\n\n"
                   f"🔔 Subscribe → {ch['id']}\n🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
                   f"#HewanBersahabat #HappyBearKids\n© Happy Bear Kids Indonesia 2026"),
        }
    else:  # C
        titles = {
            'en': f"Learn About {a['name_en']}s! {a['name_en']} Says {a['sound_en']}! | Happy Bear Kids",
            'ar': f"تعلم عن {a['name_ar']}! | هابي بير كيدز",
            'id': f"Belajar Tentang {a['name_id']}! | Happy Bear Kids",
        }
        descs = {
            'en': (f"🐾 Learn about {a['name_en']}s!\n\n"
                   f"• Name: {a['name_en']} / {a['name_ar']} / {a['name_id']}\n"
                   f"• Sound: {a['sound_en']}!\n\n"
                   f"Educational content for babies 0-3 years.\n"
                   f"🔔 Subscribe → {ch['en']}\n🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
                   f"#Learn{a['name_en']} #AnimalSounds #HappyBearKids #KidsLearning\n© Happy Bear Kids 2026"),
            'ar': (f"🐾 تعلم عن {a['name_ar']}!\n\n"
                   f"محتوى تعليمي للرضع 0-3 سنوات.\n"
                   f"🔔 اشتركوا → {ch['ar']}\n🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
                   f"#تعلم_{name.replace(' ','_')} #هابي_بير_كيدز\n© هابي بير كيدز 2026"),
            'id': (f"🐾 Belajar tentang {a['name_id']}!\n\n"
                   f"Konten edukasi untuk bayi 0-3 tahun.\n"
                   f"🔔 Subscribe → {ch['id']}\n🎵 Kevin MacLeod — CC Attribution 4.0\n\n"
                   f"#Belajar{a['name_id'].replace(' ','')} #HappyBearKids\n© Happy Bear Kids Indonesia 2026"),
        }

    return {
        "title":       titles[lang],
        "description": descs[lang],
        "tags":        [animal, a['name_en'].lower(), "pet dance", "baby animation", "happy bear kids",
                        "25 minutes", "cute pet", "no talking" if vtype != 'C' else "animal sounds"],
        "video_type":  f"dance_pet_{vtype.lower()}",
        "language":    lang,
        "is_short":    False,
        "status":      "public",
    }


def render_and_meta(animal, vtype, dry_run, regen_meta):
    a      = ANIMALS[animal]
    queues = {'en': QUEUE_EN, 'ar': QUEUE_AR, 'id': QUEUE_ID}
    music  = MUSIC_MAP[animal]
    props  = {"shapes": ["circle","star"], "colors": [a["accent"],"#FFFFFF"],
              "bgColor": a["bg"], "bpm": a["bpm"], "showLabels": False, "musicFile": music}
    suffix = f"pet_{animal}_{vtype.lower()}_{DATE_STR}"
    no_text = vtype in ('A', 'B')

    if no_text:
        out_mp4 = QUEUE_EN / f"{suffix}.mp4"
        if not out_mp4.exists() and not dry_run and not regen_meta:
            cmd = ["npx","remotion","render","ShapeDanceLong",
                   f"--props={json.dumps(props)}", f"--output={str(out_mp4)}"]
            print(f"  Render: {out_mp4.name}")
            r = subprocess.run(cmd, cwd=str(REMOTION), timeout=21600)
            if r.returncode != 0:
                return False
        if out_mp4.exists() and not dry_run:
            for lg in ['ar','id']:
                dest = queues[lg] / out_mp4.name
                if not dest.exists():
                    shutil.copy2(str(out_mp4), str(dest))
        for lg, q in queues.items():
            mp = q / f"meta_{out_mp4.stem}.yaml"
            if not mp.exists() or regen_meta:
                meta = make_meta(animal, vtype, lg)
                if not dry_run:
                    with open(mp, 'w', encoding='utf-8') as f:
                        yaml.dump(meta, f, allow_unicode=True)
                print(f"  Meta ({lg}): {mp.name}")
    else:  # C — language-specific
        for lg, q in queues.items():
            out_mp4 = q / f"{suffix}_{lg}.mp4"
            if not out_mp4.exists() and not dry_run and not regen_meta:
                cmd = ["npx","remotion","render","ShapeDanceLong",
                       f"--props={json.dumps(props)}", f"--output={str(out_mp4)}"]
                print(f"  Render ({lg}): {out_mp4.name}")
                subprocess.run(cmd, cwd=str(REMOTION), timeout=21600)
            mp = q / f"meta_{out_mp4.stem}.yaml"
            if not mp.exists() or regen_meta:
                meta = make_meta(animal, vtype, lg)
                if not dry_run:
                    with open(mp, 'w', encoding='utf-8') as f:
                        yaml.dump(meta, f, allow_unicode=True)
                print(f"  Meta ({lg}): {mp.name}")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--animal',    default=None, choices=list(ANIMALS))
    parser.add_argument('--type',      default=None, choices=['A','B','C'])
    parser.add_argument('--key',       default=None)
    parser.add_argument('--lang',      default='both')
    parser.add_argument('--dry-run',   action='store_true')
    parser.add_argument('--regen-meta',action='store_true')
    args = parser.parse_args()

    animals = [args.animal] if args.animal else list(ANIMALS)
    vtypes  = [args.type]   if args.type   else ['A','B','C']

    # Count total
    total = sum(1 for an in animals for vt in vtypes
                if not (vt=='B' and not ANIMALS[an].get('has_B')))

    print(f"=== Dance Pet Generator === ({total} videos)")
    done = 0
    for animal in animals:
        for vtype in vtypes:
            if vtype == 'B' and not ANIMALS[animal].get('has_B'):
                continue
            print(f"\n[{animal.upper()}-{vtype}] {ANIMALS[animal]['name_en']}")
            if render_and_meta(animal, vtype, args.dry_run, args.regen_meta):
                done += 1

    print(f"\n=== Done: {done}/{total} ===")


if __name__ == '__main__':
    main()
