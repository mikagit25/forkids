#!/usr/bin/env python3
"""
Universal 3D Pixar-style sprite generator via Together.ai FLUX.
Reads any *_data.yaml config and generates missing *_3d.png sprites.

Usage:
  python3 scripts/generate_sprites_3d.py --config color_learn_data.yaml
  python3 scripts/generate_sprites_3d.py --config number_learn_data.yaml
  python3 scripts/generate_sprites_3d.py --config color_learn_data.yaml --force
  python3 scripts/generate_sprites_3d.py --all        # all known configs
"""
import argparse, base64, sys, time
from pathlib import Path
import requests, yaml

ROOT        = Path(__file__).resolve().parent.parent
CONFIG_DIR  = ROOT / "config"
SPRITES_DIR = ROOT / "remotion" / "public" / "sprites"
KEY_FILE    = ROOT / "credentials" / "together_api_key.txt"

TOGETHER_URL   = "https://api.together.xyz/v1/images/generations"
TOGETHER_MODEL = "black-forest-labs/FLUX.1-schnell"

# ── Prompt templates per category ────────────────────────────────────────────
PROMPTS: dict[str, str] = {
    # animals
    "cat":        "A single cute 3D Pixar-style orange cat character, big round eyes, fluffy fur, happy smile, white background, no text",
    "frog":       "A single cute 3D Pixar-style green frog character, big round eyes, chubby body, happy smile, sitting pose, white background, no text",
    "penguin":    "A single cute 3D Pixar-style penguin character, black and white fluffy body, big round eyes, happy smile, white background, no text",
    "pig":        "A single cute 3D Pixar-style pink pig character, round chubby body, big eyes, curly tail, happy smile, white background, no text",
    "rabbit":     "A single cute 3D Pixar-style white rabbit character, long fluffy ears, big round eyes, happy smile, white background, no text",
    "bear":       "A single cute 3D Pixar-style brown teddy bear character, fluffy round body, big expressive eyes, happy smile, white background, no text",
    "duck":       "A single cute 3D Pixar-style yellow baby duck, big round eyes, orange beak, fluffy body, white background, no text",
    "elephant":   "A single cute 3D Pixar-style grey elephant, big floppy ears, round chubby body, happy smile, white background, no text",
    "lion":       "A single cute 3D Pixar-style lion cub, fluffy mane, big round eyes, happy smile, white background, no text",
    "monkey":     "A single cute 3D Pixar-style brown monkey, big round eyes, happy smile, sitting pose, white background, no text",
    "fish":       "A single cute 3D Pixar-style colorful tropical fish, big round eyes, happy smile, white background, no text",
    "turtle":     "A single cute 3D Pixar-style green turtle, round shell, big eyes, happy smile, white background, no text",
    # fruits
    "apple":      "A single cute 3D Pixar-style red apple character, big blue eyes, glossy surface, green leaf, happy smile, white background, no text",
    "banana":     "A single cute 3D Pixar-style yellow banana character, big round eyes, curved chubby shape, happy smile, white background, no text",
    "grapes":     "A single cute 3D Pixar-style purple grapes cluster character, big eyes on top grape, glossy round grapes, happy face, white background, no text",
    "lemon":      "A single cute 3D Pixar-style yellow lemon character, oval shape, big eyes, happy smile with rosy cheeks, white background, no text",
    "orange":     "A single cute 3D Pixar-style orange fruit character, round glossy body, big eyes, green leaf on top, happy smile, white background, no text",
    "peach":      "A single cute 3D Pixar-style pink peach character, soft round body, big eyes, happy smile, white background, no text",
    "strawberry": "A single cute 3D Pixar-style red strawberry character, heart-shaped body, big eyes, green leafy crown, happy smile, white background, no text",
    "cherry":     "Two cute 3D Pixar-style red cherries side by side on a shared green stem with a leaf, EACH cherry has its own big round eyes and happy smile, glossy red shiny surface, both cherries are identical characters with faces, white background, no text",
    "watermelon": "A single cute 3D Pixar-style watermelon slice character, red inside with black seeds, big eyes, happy smile, white background, no text",
    "pineapple":  "A single cute 3D Pixar-style pineapple character, yellow body with crown of leaves, big eyes, happy smile, white background, no text",
    # vegetables
    "broccoli":   "A single cute 3D Pixar-style green broccoli character, tree-like body, big round eyes, happy smile, white background, no text",
    "carrot":     "A single cute 3D Pixar-style orange carrot character, pointy body, green leafy top, big eyes, happy smile, white background, no text",
    "corn":       "A single cute 3D Pixar-style yellow corn character, round kernels body, green husk, big eyes, happy smile, white background, no text",
    "cucumber":   "A single cute 3D Pixar-style green cucumber character, long oval body, big eyes, happy smile, white background, no text",
    "eggplant":   "A single cute 3D Pixar-style purple eggplant character, round body, green crown, big eyes, happy smile, white background, no text",
    "tomato":     "A single cute 3D Pixar-style red tomato character, round glossy body, green star leaves, big eyes, happy smile, white background, no text",
    "pumpkin":    "A single cute 3D Pixar-style orange pumpkin character, round ribbed body, green stem, big eyes, happy smile, white background, no text",
    # objects
    "apple_green":     "A single cute 3D Pixar-style green apple character, glossy round body, big eyes, happy smile, white background, no text",
    "balloon":    "A single cute 3D Pixar-style red balloon character, shiny round body, big eyes, happy smile, thin string, white background, no text",
    "butterfly":  "A single cute 3D Pixar-style pink butterfly, symmetrical colorful wings, big eyes, happy face, white background, no text",
    "blue_butterfly": "A single cute 3D Pixar-style blue butterfly character, symmetrical blue wings with yellow dots, big eyes, happy smile, white background, no text",
    "car":        "A single cute 3D Pixar-style red toy car character, big round headlight eyes, rounded body, happy smile, white background, no text",
    "cloud":      "A single cute 3D Pixar-style white fluffy cloud character, puffy round shape, big eyes, happy smile, white background, no text",
    "crow":       "A single cute 3D Pixar-style black crow character, shiny feathers, big round eyes, happy beak, white background, no text",
    "flamingo":   "A single cute 3D Pixar-style pink flamingo character, long neck, fluffy feathers, big round eyes, happy smile, white background, no text",
    "blueberry":  "A single cute 3D Pixar-style dark blue blueberry character, round glossy body, tiny leaves, big eyes, happy smile, white background, no text",
    "blue_whale": "A single cute 3D Pixar-style blue whale character, big round body, friendly big eyes, happy smile, water spout on top, white background, no text",
    "plum":       "A single cute 3D Pixar-style dark purple plum character, round glossy body, big eyes, happy smile, white background, no text",
    "polar_bear": "A single cute 3D Pixar-style white polar bear character, round fluffy body, big eyes, happy smile, white background, no text",
    "octopus":    "A single cute 3D Pixar-style purple octopus character, round head, eight curly tentacles, big eyes, happy smile, white background, no text",
    "rainbow":    "A single cute 3D Pixar-style rainbow character, colorful arched stripes, big eyes, happy smile, fluffy cloud ends, white background, no text",
    "shoe":       "A single cute 3D Pixar-style colorful sneaker shoe character, big toe eyes, laces, happy smile, white background, no text",
    "star":       "A single cute 3D Pixar-style golden star character, five chubby points, big eyes, happy smile, rosy cheeks, white background, no text",
    "sun":        "A single cute 3D Pixar-style yellow sun character, round face, wavy rays, big eyes, happy smile, rosy cheeks, white background, no text",
}

KNOWN_CONFIGS = [
    "color_learn_data.yaml",
    "number_learn_data.yaml",
]


def load_key() -> str:
    if not KEY_FILE.exists():
        sys.exit(f"Together.ai key not found: {KEY_FILE}")
    return KEY_FILE.read_text().strip()


def flux_generate(prompt: str, key: str) -> bytes | None:
    try:
        r = requests.post(
            TOGETHER_URL,
            headers={"Authorization": f"Bearer {key}"},
            json={"model": TOGETHER_MODEL, "prompt": prompt,
                  "width": 1024, "height": 1024, "steps": 4, "n": 1},
            timeout=90,
        )
        if r.status_code != 200:
            print(f"    API {r.status_code}: {r.text[:100]}")
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
        print(f"    Request failed: {e}")
    return None


def collect_sprites_from_config(config_path: Path) -> list[str]:
    """Return unique sprite base names (e.g. 'apple') from a data yaml."""
    with open(config_path) as f:
        data = yaml.safe_load(f)

    sprites = set()
    def walk(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "sprite" and isinstance(v, str):
                    # "fruits/apple.png" or "fruits/apple_3d.png" → "apple"
                    name = Path(v.split("#")[0].strip()).stem.replace("_3d", "")
                    sprites.add(name)
                else:
                    walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)
    walk(data)
    return sorted(sprites)


def sprite_output_path(name: str) -> Path | None:
    """Find where to save sprite based on name → category mapping."""
    animals   = {"cat","frog","penguin","pig","rabbit","bear","duck","elephant",
                 "lion","monkey","fish","turtle","crow","flamingo","polar_bear","blue_whale"}
    fruits    = {"apple","banana","grapes","lemon","orange","peach","strawberry",
                 "cherry","watermelon","pineapple","blueberry","plum"}
    vegs      = {"broccoli","carrot","corn","cucumber","eggplant","tomato","pumpkin"}
    objects   = {"balloon","butterfly","blue_butterfly","car","cloud","octopus",
                 "rainbow","shoe","star","sun","apple_green","blueberry"}

    if name in animals:
        return SPRITES_DIR / "animals" / f"{name}_3d.png"
    if name in fruits:
        return SPRITES_DIR / "fruits" / f"{name}_3d.png"
    if name in vegs:
        return SPRITES_DIR / "vegetables" / f"{name}_3d.png"
    if name in objects:
        return SPRITES_DIR / "objects" / f"{name}_3d.png"
    # fallback
    return SPRITES_DIR / "objects" / f"{name}_3d.png"


def update_config_sprites(config_path: Path) -> None:
    """Replace sprite: "x/y.png" with "x/y_3d.png" in a yaml config file."""
    text = config_path.read_text()
    import re
    def replacer(m):
        path = m.group(1)
        stem = Path(path).stem
        if stem.endswith("_3d"):
            return m.group(0)   # already updated
        new_path = str(Path(path).with_stem(stem + "_3d"))
        return f'sprite: "{new_path}"'
    updated = re.sub(r'sprite:\s*"([^"]+\.png)"', replacer, text)
    # strip # AI generated comments that refer to old paths
    config_path.write_text(updated)
    print(f"  Updated sprite paths in {config_path.name}")


def generate_for_config(config_path: Path, force: bool, key: str) -> tuple[int, int, int]:
    names = collect_sprites_from_config(config_path)
    ok = skip = fail = 0
    print(f"\n[{config_path.name}] {len(names)} unique sprites: {names}")

    for name in names:
        out = sprite_output_path(name)
        if out is None:
            print(f"  ? {name}: unknown category, skip")
            continue
        if out.exists() and not force:
            print(f"  ✓ {name} exists — skip")
            skip += 1
            continue
        if name not in PROMPTS:
            print(f"  ! {name}: no prompt defined — skip (add to PROMPTS dict)")
            fail += 1
            continue

        print(f"  Generating {name}...", end=" ", flush=True)
        data = flux_generate(PROMPTS[name], key)
        if data:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(data)
            print(f"✓ {len(data)//1024}KB → {out.relative_to(ROOT)}")
            ok += 1
            time.sleep(0.5)
        else:
            print("FAILED")
            fail += 1

    # Update config to use _3d paths
    if ok > 0:
        update_config_sprites(config_path)

    return ok, skip, fail


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="Config yaml filename (e.g. color_learn_data.yaml)")
    parser.add_argument("--all",    action="store_true", help="Process all known configs")
    parser.add_argument("--force",  action="store_true", help="Overwrite existing files")
    args = parser.parse_args()

    key = load_key()

    configs: list[Path] = []
    if args.all:
        configs = [CONFIG_DIR / c for c in KNOWN_CONFIGS]
    elif args.config:
        configs = [CONFIG_DIR / args.config]
    else:
        parser.print_help()
        sys.exit(1)

    total_ok = total_skip = total_fail = 0
    for cfg in configs:
        if not cfg.exists():
            print(f"Config not found: {cfg}")
            continue
        ok, sk, fa = generate_for_config(cfg, args.force, key)
        total_ok += ok; total_skip += sk; total_fail += fa

    print(f"\n{'='*50}")
    print(f"Total: {total_ok} generated, {total_skip} skipped, {total_fail} failed")


if __name__ == "__main__":
    main()
