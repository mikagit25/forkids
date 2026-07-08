#!/usr/bin/env python3
"""
Scan local MP3 files and register them in assets/music/classical/licenses.yaml.
Replaces Musopen API for local-first workflow — drop files in the Music/ folder,
run this script, then generate_sleep_classical.py can find them.

Usage:
  python3 scripts/scan_music.py                    # scan and register all new files
  python3 scripts/scan_music.py --list             # show registered tracks only
  python3 scripts/scan_music.py --fix-paths        # update file fields for moved files
"""
import argparse, json, logging, re, subprocess
from pathlib import Path
import yaml

ROOT       = Path(__file__).resolve().parent.parent
MUSIC_DIR  = ROOT / "assets" / "music" / "classical"
LICENSES   = MUSIC_DIR / "licenses.yaml"

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# (keywords_in_lower_filename, composer_name, composer_slug)
COMPOSER_HINTS = [
    # Nocturne/Mazurka/Étude without explicit "Chopin" label = almost always Chopin on Musopen
    (["chopin", "nocturne op", "ballade op", "mazurka", "etude op. 25", "étude op",
      "nocturne in e flat", "nocturne in b flat", "nocturne in c", "nocturne in d",
      "nocturne in f", "nocturne in g", "nocturne in a", "nocturne in b"],
                                                  "Frédéric Chopin",              "chopin"),
    (["bwv", "bach", "cello suite", "partita", "invention", "well-tempered"],
                                                   "Johann Sebastian Bach",         "bach"),
    (["mozart", "serenade in g"],                  "Wolfgang Amadeus Mozart",       "mozart"),
    (["beethoven", "moonlight", "symphony no. 5", "symphony no.5", "für elise"],
                                                   "Ludwig van Beethoven",          "beethoven"),
    (["tchaikovsky", "swan lake", "nutcracker"],   "Pyotr Ilyich Tchaikovsky",      "tchaikovsky"),
    # Arabesque and Fantaisie Op.79 are Debussy; "arabesques" plural also
    (["debussy", "clair de lune", "arabesques", "arabesque", "fantaisie, op. 79",
      "reverie", "rêverie", "syrinx"],             "Claude Debussy",                "debussy"),
    (["satie", "gymnop", "gnossienne"],            "Erik Satie",                    "satie"),
    (["brahms"],                                   "Johannes Brahms",               "brahms"),
    (["schubert"],                                 "Franz Schubert",                "schubert"),
    (["verdi", "la traviata", "aida"],             "Giuseppe Verdi",                "verdi"),
    (["vaughan williams", "tallis", "fantasia on a theme by thomas"],
                                                   "Ralph Vaughan Williams",        "vwilliams"),
    # HWV = Handel catalogue number
    (["handel", "hwv"],                            "George Frideric Handel",        "handel"),
    # RV = Ryom-Verzeichnis (Vivaldi catalogue)
    (["vivaldi", "rv "],                           "Antonio Vivaldi",               "vivaldi"),
    (["liszt"],                                    "Franz Liszt",                   "liszt"),
    (["grieg", "peer gynt"],                       "Edvard Grieg",                  "grieg"),
    (["dvorak", "dvořák"],                         "Antonín Dvořák",                "dvorak"),
    (["mendelssohn"],                              "Felix Mendelssohn",             "mendelssohn"),
    (["saint-saens", "saint-saëns", "carnival"],  "Camille Saint-Saëns",           "saintsaens"),
    (["granados", "valses poeticos", "goyescas"],  "Enrique Granados",              "granados"),
]


def infer_composer(filename: str) -> tuple[str, str]:
    """Return (composer_name, composer_slug) or ('Unknown', 'unknown')."""
    low = filename.lower()
    for keywords, name, slug in COMPOSER_HINTS:
        if any(k in low for k in keywords):
            return name, slug
    return "Unknown", "unknown"


def make_slug(filename: str, composer_slug: str) -> str:
    """Generate a unique slug from composer + filename."""
    stem = Path(filename).stem
    # strip leading numbers and spaces
    clean = re.sub(r"[^\w\s-]", " ", stem)
    clean = re.sub(r"\s+", "_", clean.strip())
    clean = re.sub(r"_+", "_", clean)
    clean = clean.strip("_")
    slug = f"{composer_slug}_{clean[:60]}".lower()
    slug = re.sub(r"[^a-z0-9_]", "_", slug)
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug


def get_duration_sec(mp3_path: Path) -> float:
    """Use ffprobe to get audio duration in seconds."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", str(mp3_path)
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        data = json.loads(r.stdout)
        for stream in data.get("streams", []):
            dur = stream.get("duration")
            if dur:
                return float(dur)
    except Exception:
        pass
    return 0.0


def load_licenses() -> dict:
    if LICENSES.exists():
        with open(LICENSES) as f:
            data = yaml.safe_load(f) or {}
    else:
        data = {}
    if "recordings" not in data:
        data["recordings"] = []
    return data


def save_licenses(data: dict):
    # Preserve the header comment by reading existing file header
    header = ""
    if LICENSES.exists():
        with open(LICENSES) as f:
            for line in f:
                if line.startswith("#") or line.strip() == "":
                    header += line
                else:
                    break

    with open(LICENSES, "w") as f:
        if header:
            f.write(header)
        yaml.dump(
            {"recordings": data["recordings"]},
            f,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )


def scan_and_register(fix_paths: bool = False) -> int:
    data = load_licenses()
    existing = {r["id"]: r for r in data["recordings"]}
    existing_files = {r.get("file", ""): r["id"] for r in data["recordings"] if r.get("file")}

    mp3_files = sorted(MUSIC_DIR.rglob("*.mp3"))
    log.info(f"Found {len(mp3_files)} MP3 files under {MUSIC_DIR}")

    added = 0
    for mp3 in mp3_files:
        rel_path = str(mp3.relative_to(MUSIC_DIR))  # e.g. "Music/Nocturne in E flat..."

        if rel_path in existing_files and not fix_paths:
            log.info(f"  Already registered: {mp3.name}")
            continue

        composer_name, composer_slug = infer_composer(mp3.name)
        slug = make_slug(mp3.name, composer_slug)

        # avoid duplicate slugs
        base_slug = slug
        n = 2
        while slug in existing and existing[slug].get("file", "") != rel_path:
            slug = f"{base_slug}_{n}"
            n += 1

        dur = get_duration_sec(mp3)
        log.info(f"  [{composer_slug}] {mp3.name} — {dur:.0f}s")

        entry = {
            "id":           slug,
            "composer":     composer_name,
            "piece":        Path(mp3.stem).name,   # raw filename as piece label
            "performer":    "",
            "year":         0,
            "source":       "musopen.org",
            "license":      "pd",
            "duration_sec": round(dur),
            "file":         rel_path,
            "programs":     [],
            "notes":        "Local file — verify PD status from Musopen download history",
        }

        if fix_paths and rel_path in existing_files:
            old_id = existing_files[rel_path]
            existing[old_id]["file"] = rel_path
            log.info(f"    Updated path for {old_id}")
        elif slug not in existing:
            data["recordings"].append(entry)
            existing[slug] = entry
            existing_files[rel_path] = slug
            added += 1

    save_licenses(data)
    log.info(f"\nDone: {added} new tracks registered (total: {len(data['recordings'])})")
    return added


def list_tracks():
    data = load_licenses()
    recs = data.get("recordings", [])
    if not recs:
        print("No tracks registered yet. Run: python3 scripts/scan_music.py")
        return
    print(f"\n{'ID':<55} {'Composer':<25} {'Dur':>6}  File")
    print("-" * 120)
    for r in sorted(recs, key=lambda x: x.get("composer", "")):
        dur = r.get("duration_sec", 0)
        mins = f"{dur//60}:{dur%60:02d}"
        fpath = r.get("file", "—")
        print(f"{r['id']:<55} {r.get('composer','?'):<25} {mins:>6}  {fpath}")
    print(f"\nTotal: {len(recs)} tracks")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--list",       action="store_true", help="List registered tracks")
    parser.add_argument("--fix-paths",  action="store_true", help="Update file paths for moved files")
    args = parser.parse_args()

    if args.list:
        list_tracks()
        return

    scan_and_register(fix_paths=args.fix_paths)
    if not args.fix_paths:
        print("\nTip: run --list to see all registered tracks")


if __name__ == "__main__":
    main()
