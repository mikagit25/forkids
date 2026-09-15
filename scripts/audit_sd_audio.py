#!/usr/bin/env python3
"""
Sacred Drift Audio Audit & Catalog Generator.

Analyzes:
  1. AI-generated tracks in sacred_drift/audio/uploads/
     - Groups by canonical name (strip variant suffixes)
     - Detects vocal vs instrumental via keyword heuristic
     - Flags duplicates already in assets/audio/suno_meditation/Meditation/
     - Optionally moves files into organized subdirectories

  2. Classical tracks in assets/music/classical/Music/
     - Decodes URL-encoded filenames
     - Identifies pure-UUID files via ffprobe duration
     - Detects duplicates within the folder and against licenses.yaml

Usage:
  python3 scripts/audit_sd_audio.py               # report only
  python3 scripts/audit_sd_audio.py --organize    # report + move AI files
  python3 scripts/audit_sd_audio.py --decode-classical  # rename URL-encoded classical files
"""

import argparse
import json
import re
import shutil
import subprocess
import yaml
from collections import defaultdict
from pathlib import Path
from datetime import datetime

ROOT      = Path(__file__).resolve().parent.parent
UPLOADS   = ROOT / "sacred_drift" / "audio" / "uploads"
SUNO_DIR  = ROOT / "assets" / "audio" / "suno_meditation" / "Meditation"
AI_INSTR  = ROOT / "sacred_drift" / "audio" / "ai_instrumental"
AI_CHANT  = ROOT / "sacred_drift" / "audio" / "ai_chant"
MUSIC_DIR = ROOT / "assets" / "music" / "classical" / "Music"
LICENSES  = ROOT / "assets" / "music" / "classical" / "licenses.yaml"
CATALOG   = ROOT / "sacred_drift" / "audio" / "catalog_ai.yaml"
CLASSIC_CATALOG = ROOT / "sacred_drift" / "audio" / "catalog_classical.yaml"


# ── Vocal keyword heuristic ───────────────────────────────────────────────────
# Note: "singing bowls" is instrumental — exclude before checking "singing"
VOCAL_KW = [
    'vocal', ' voice', 'voices', 'chant', 'chanting', 'mantra', 'kirtan',
    'om chant', 'om mani', 'om shanti', 'om mantra', 'aum ', 'humming',
    'narrat', 'guided breath', 'breathing guide', 'so hum', 'hymn',
    'prayer', 'choir', 'chorus', 'reiki healing chant', 'sanskrit peace mantra',
    'gratitude chant', 'voice of truth',
]

def is_vocal(name: str) -> bool:
    nl = name.lower()
    # Exclude common false positives
    nl_clean = nl.replace('singing bowl', '').replace('tibetan singing', '')
    return any(kw in nl_clean for kw in VOCAL_KW)


# ── Canonical name (strip variant suffix) ────────────────────────────────────
def canonical(filename: str) -> str:
    name = re.sub(r'\.mp3$', '', filename, flags=re.IGNORECASE)
    name = re.sub(r'\s*\(\d+\)\s*$', '', name).strip()
    return name


# ── ffprobe duration ──────────────────────────────────────────────────────────
def get_duration(path: Path) -> float:
    r = subprocess.run(
        ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', str(path)],
        capture_output=True
    )
    try:
        return float(json.loads(r.stdout)['format']['duration'])
    except Exception:
        return 0.0


def get_tags(path: Path) -> dict:
    r = subprocess.run(
        ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', str(path)],
        capture_output=True
    )
    try:
        return json.loads(r.stdout).get('format', {}).get('tags', {})
    except Exception:
        return {}


# ── AI tracks audit ───────────────────────────────────────────────────────────
def audit_ai_tracks(organize: bool = False) -> dict:
    print("\n" + "="*60)
    print("AI-GENERATED TRACKS (uploads)")
    print("="*60)

    if organize:
        AI_INSTR.mkdir(parents=True, exist_ok=True)
        AI_CHANT.mkdir(parents=True, exist_ok=True)

    suno_names = {canonical(f.name) for f in SUNO_DIR.glob('*.mp3')} if SUNO_DIR.exists() else set()

    groups: dict[str, list[Path]] = defaultdict(list)
    for f in sorted(UPLOADS.glob('*.mp3')):
        groups[canonical(f.name)].append(f)

    instrumental, chant, dup_suno, new_tracks = [], [], [], []
    catalog_entries = []

    for cn, files in sorted(groups.items()):
        vocal = is_vocal(cn)
        in_suno = cn in suno_names
        variants = sorted(f.name for f in files)
        dur = get_duration(files[0]) if files else 0

        entry = {
            'canonical_name': cn,
            'type': 'chant' if vocal else 'instrumental',
            'variants': variants,
            'variant_count': len(files),
            'duration_sec': round(dur),
            'in_suno_meditation': in_suno,
        }
        catalog_entries.append(entry)

        if vocal:
            chant.append(cn)
        else:
            instrumental.append(cn)

        if in_suno:
            dup_suno.append(cn)
        else:
            new_tracks.append(cn)

        if organize:
            dest_dir = AI_CHANT if vocal else AI_INSTR
            for f in files:
                target = dest_dir / f.name
                if not target.exists():
                    shutil.move(str(f), str(target))

    print(f"\nTotal files:   {sum(len(v) for v in groups.values())}")
    print(f"Unique tracks: {len(groups)}")
    print(f"  Instrumental: {len(instrumental)}")
    print(f"  Vocal/Chant:  {len(chant)}")
    print(f"\nAlready in suno_meditation (duplicates): {len(dup_suno)}")
    print(f"New tracks (not in suno_meditation):     {len(new_tracks)}")

    print(f"\n── Vocal/Chant tracks ({len(chant)}) ──")
    for cn in chant:
        cnt = len(groups[cn])
        suno_mark = " [DUP:suno]" if cn in suno_names else ""
        print(f"  [{cnt}v] {cn}{suno_mark}")

    print(f"\n── Duplicates with suno_meditation ({len(dup_suno)}) ──")
    for cn in dup_suno[:30]:
        print(f"  {cn}")
    if len(dup_suno) > 30:
        print(f"  ... and {len(dup_suno)-30} more")

    # Save catalog
    CATALOG.parent.mkdir(parents=True, exist_ok=True)
    CATALOG.write_text(yaml.dump({
        'generated': datetime.now().strftime('%Y-%m-%d'),
        'total_files': sum(len(v) for v in groups.values()),
        'unique_tracks': len(groups),
        'tracks': catalog_entries,
    }, allow_unicode=True, default_flow_style=False, sort_keys=False))
    print(f"\n✓ Catalog saved: {CATALOG.relative_to(ROOT)}")

    if organize:
        remaining = list(UPLOADS.glob('*.mp3'))
        print(f"\n✓ Files moved to ai_instrumental/ and ai_chant/")
        print(f"  Remaining in uploads/: {len(remaining)}")

    return {'instrumental': instrumental, 'chant': chant, 'dup_suno': dup_suno}


# ── Classical tracks audit ────────────────────────────────────────────────────
def audit_classical(decode: bool = False) -> dict:
    print("\n" + "="*60)
    print("CLASSICAL TRACKS (assets/music/classical/Music/)")
    print("="*60)

    from urllib.parse import unquote_plus
    import unicodedata

    lic_data = yaml.safe_load(LICENSES.read_text()) if LICENSES.exists() else {}
    yaml_files = {r.get('file', '').replace('Music/', '') for r in lic_data.get('recordings', [])}
    yaml_pieces = {r.get('piece', '').lower() for r in lic_data.get('recordings', []) if r.get('piece')}

    all_files = list(MUSIC_DIR.glob('*.mp3'))

    url_encoded, pure_uuid, plain_new, plain_existing = [], [], [], []

    for f in all_files:
        stem = f.stem
        if '+' in stem:
            url_encoded.append(f)
        elif all(c in '0123456789abcdef-' for c in stem.lower()) and len(stem) > 30:
            pure_uuid.append(f)
        elif f.name in yaml_files:
            plain_existing.append(f)
        else:
            plain_new.append(f)

    print(f"\nTotal files on disk: {len(all_files)}")
    print(f"  Plain (in YAML):      {len(plain_existing)}")
    print(f"  Plain (NEW, not YAML):{len(plain_new)}")
    print(f"  URL-encoded:          {len(url_encoded)}")
    print(f"  Pure UUID (opaque):   {len(pure_uuid)}")

    # Decode URL-encoded
    decoded_map = {}   # original filename → decoded name
    url_dups_within = []
    url_dups_yaml = []
    url_decoded_names = set()

    for f in url_encoded:
        decoded_name = unquote_plus(f.name)
        decoded_clean = re.sub(r'\s+', ' ', decoded_name).strip()
        decoded_map[f.name] = decoded_clean
        # Check duplicate within url group
        if decoded_clean.lower() in url_decoded_names:
            url_dups_within.append((f.name, decoded_clean))
        url_decoded_names.add(decoded_clean.lower())
        # Check duplicate against yaml pieces (fuzzy)
        for piece in yaml_pieces:
            if decoded_clean.lower()[:30] in piece or piece[:30] in decoded_clean.lower():
                url_dups_yaml.append((f.name, decoded_clean, piece))
                break

    print(f"\n  URL-encoded — duplicates within group: {len(url_dups_within)}")
    print(f"  URL-encoded — likely duplicates with YAML pieces: {len(url_dups_yaml)}")

    if url_dups_within:
        print("  Within-group duplicates:")
        for fn, dn in url_dups_within[:10]:
            print(f"    {dn}")

    if url_dups_yaml:
        print("  Cross-duplicates with existing YAML:")
        for fn, dn, yp in url_dups_yaml[:15]:
            print(f"    NEW: {dn[:50]}")
            print(f"    OLD: {yp[:50]}")
            print()

    # UUID files — try to get title from ID3
    print(f"\n  Pure UUID files — checking ID3 metadata...")
    uuid_with_title, uuid_no_title = [], []
    for f in pure_uuid[:20]:  # sample
        tags = get_tags(f)
        title = tags.get('title', '') or tags.get('TITLE', '')
        if title:
            uuid_with_title.append((f.name, title))
        else:
            uuid_no_title.append(f.name)

    print(f"  (sampled 20) With ID3 title: {len(uuid_with_title)} | Without: {len(uuid_no_title)}")
    for fn, title in uuid_with_title[:5]:
        print(f"    {fn[:36]} → {title[:50]}")

    # Plain new files
    print(f"\n  New plain files (not in YAML) — {len(plain_new)}:")
    for f in plain_new[:20]:
        print(f"    {f.name}")
    if len(plain_new) > 20:
        print(f"    ... and {len(plain_new)-20} more")

    # Decode and optionally rename
    if decode:
        renamed = 0
        for f in url_encoded:
            decoded_name = decoded_map.get(f.name, '')
            if not decoded_name or decoded_name == f.name:
                continue
            target = f.parent / decoded_name
            if target.exists():
                print(f"  SKIP (exists): {decoded_name[:60]}")
                continue
            f.rename(target)
            renamed += 1
        print(f"\n✓ Renamed {renamed} URL-encoded files to human-readable names")

    # Save classical catalog
    classic_entries = []
    for f in plain_existing:
        classic_entries.append({'file': f.name, 'status': 'in_yaml', 'type': 'classical'})
    for f in plain_new:
        classic_entries.append({'file': f.name, 'status': 'new_unregistered', 'type': 'classical'})
    for f in url_encoded:
        decoded = decoded_map.get(f.name, f.name)
        dup = any(fn == f.name for fn, _dn, _yp in url_dups_yaml)
        classic_entries.append({
            'file': f.name,
            'decoded_name': decoded,
            'status': 'url_encoded_dup' if dup else 'url_encoded_new',
            'type': 'classical',
        })
    for f in pure_uuid[:10]:
        classic_entries.append({'file': f.name, 'status': 'uuid_opaque', 'type': 'classical'})

    CLASSIC_CATALOG.write_text(yaml.dump({
        'generated': datetime.now().strftime('%Y-%m-%d'),
        'summary': {
            'total': len(all_files),
            'in_yaml': len(plain_existing),
            'new_plain': len(plain_new),
            'url_encoded': len(url_encoded),
            'pure_uuid': len(pure_uuid),
            'url_dups_with_yaml': len(url_dups_yaml),
        },
        'files': classic_entries[:200],  # limit for readability
    }, allow_unicode=True, default_flow_style=False, sort_keys=False))
    print(f"\n✓ Classical catalog saved: {CLASSIC_CATALOG.relative_to(ROOT)}")

    return {
        'url_dups_yaml': url_dups_yaml,
        'plain_new': plain_new,
        'pure_uuid': pure_uuid,
    }


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--organize', action='store_true',
                        help='Move AI files into ai_instrumental/ and ai_chant/ subdirs')
    parser.add_argument('--decode-classical', action='store_true',
                        help='Rename URL-encoded classical files to human-readable names')
    args = parser.parse_args()

    audit_ai_tracks(organize=args.organize)
    audit_classical(decode=args.decode_classical)

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print("AI catalog:       sacred_drift/audio/catalog_ai.yaml")
    print("Classical catalog: sacred_drift/audio/catalog_classical.yaml")
    print()
    print("Next steps:")
    print("  1. Run --organize to move AI files into ai_instrumental/ / ai_chant/")
    print("  2. Run --decode-classical to rename URL-encoded files")
    print("  3. Register new plain classical files in licenses.yaml")
    print("  4. UUID files (138): need manual identification or deletion")


if __name__ == '__main__':
    main()
