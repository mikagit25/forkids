#!/usr/bin/env python3
"""
Sync classical music from Google Drive → assets/music/classical/Music/

Usage:
  python3 scripts/sync_gdrive_music.py            # dry run
  python3 scripts/sync_gdrive_music.py --download # actually download new files

Google Drive folder: https://drive.google.com/drive/folders/1q7-rkzjSkUwmFTxms8uzSS8nKWvb04uk
"""
import argparse, json, re, subprocess, sys
from pathlib import Path

GDRIVE_FOLDER = "https://drive.google.com/drive/folders/1q7-rkzjSkUwmFTxms8uzSS8nKWvb04uk"
MUSIC_DIR     = Path(__file__).resolve().parent.parent / "assets" / "music" / "classical" / "Music"
SKIP_PATTERNS = [
    r"^8 HOURS",          # YouTube compilations
    r"^\._",              # macOS metadata files
    r"^_Concerto",        # corrupted/duplicate filenames
    r"\.zip$",            # zip archives
    r"\.png$",            # images
    r"\.jpeg$",
    r"gemini|hidream|mai-image",  # AI thumbnails
]
KIDS_AUDIO_PATTERNS = [
    r"Starlight Lullaby",
    r"Music Box",
    r"Opus for Starlight",
]

def should_skip(name: str) -> str | None:
    for pat in SKIP_PATTERNS:
        if re.search(pat, name, re.IGNORECASE):
            return f"skip pattern: {pat}"
    return None

def is_kids_audio(name: str) -> bool:
    return any(re.search(p, name, re.IGNORECASE) for p in KIDS_AUDIO_PATTERNS)

def list_drive_files() -> list[dict]:
    print("Получаю список файлов с Google Drive...")
    r = subprocess.run(["gdown", "--folder", GDRIVE_FOLDER, "--json"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"gdown failed: {r.stderr}")
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        # gdown outputs warning lines before JSON
        lines = r.stdout.strip().split("\n")
        for i, line in enumerate(lines):
            if line.startswith("["):
                return json.loads("\n".join(lines[i:]))
        sys.exit("Не удалось распарсить JSON от gdown")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true", help="Скачать новые файлы")
    args = parser.parse_args()

    all_files = list_drive_files()
    mp3s = [f for f in all_files if f["path"].endswith(".mp3")]
    server_files = {p.name for p in MUSIC_DIR.iterdir() if p.suffix == ".mp3"}

    new, skipped, kids = [], [], []
    for f in mp3s:
        name = f["path"].split("/")[-1]
        if name.startswith("._"):
            continue
        reason = should_skip(name)
        if reason:
            skipped.append((name, reason))
            continue
        if is_kids_audio(name):
            kids.append(name)
            continue
        if name not in server_files:
            new.append(f)

    print(f"\nНа Drive: {len(mp3s)} mp3  |  На сервере: {len(server_files)}  |  Новых: {len(new)}")

    if kids:
        print(f"\n⚠️  Детское аудио (в assets/audio/suno/, не качаем сюда):")
        for n in kids:
            print(f"   {n}")

    if skipped:
        print(f"\n⏭️  Пропускаем ({len(skipped)}):")
        for name, reason in skipped:
            print(f"   {name}  [{reason}]")

    if not new:
        print("\n✓ Всё актуально, нечего скачивать.")
        return

    print(f"\n{'📥 Скачиваю' if args.download else '🔍 Dry-run'} {len(new)} новых файла(ов):")
    for f in new:
        name = f["path"].split("/")[-1]
        folder = f["path"].split("/")[0] if "/" in f["path"] else ""
        label = f"[{folder}/] " if folder else ""
        print(f"  {label}{name}")
        if args.download:
            out = MUSIC_DIR / name
            r = subprocess.run(["gdown", f["url"], "-O", str(out), "-q"],
                               capture_output=True, text=True)
            if r.returncode == 0 and out.exists():
                print(f"    ✓ {out.stat().st_size / 1024**2:.1f}MB")
            else:
                print(f"    ✗ ОШИБКА: {r.stderr[:100]}")

    if args.download:
        print(f"\n✓ Готово. Не забудь добавить новые треки в licenses.yaml!")
    else:
        print(f"\nЗапусти с --download чтобы скачать.")

if __name__ == "__main__":
    main()
