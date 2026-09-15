#!/usr/bin/env python3
"""
Disk space guard — call check_disk_space() at the start of any generation script.
Aborts with a clear message if free space is below MIN_FREE_GB.
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIN_FREE_GB = 50  # minimum free space required to start generation


def check_disk_space(min_gb: int = MIN_FREE_GB, path: str | Path = ROOT) -> None:
    """Abort if free disk space is below min_gb. Call at the top of generation scripts."""
    stat = shutil.disk_usage(str(path))
    free_gb = stat.free / (1024 ** 3)
    total_gb = stat.total / (1024 ** 3)
    used_pct = (stat.used / stat.total) * 100

    if free_gb < min_gb:
        print(
            f"\n{'='*60}\n"
            f"  DISK SPACE ERROR — не хватает места для генерации!\n"
            f"  Свободно: {free_gb:.1f}GB  |  Занято: {used_pct:.0f}%  |  Всего: {total_gb:.0f}GB\n"
            f"  Требуется минимум: {min_gb}GB свободного места\n\n"
            f"  Что сделать:\n"
            f"    1. python3 scripts/disk_guard.py   ← показать что занимает место\n"
            f"    2. Удалить MP4 из uploaded/ (уже опубликованы на YouTube)\n"
            f"    3. Удалить _tmp_* папки из output/\n"
            f"{'='*60}\n",
            file=sys.stderr,
        )
        sys.exit(1)


def report() -> None:
    """Print disk usage summary for the project."""
    stat = shutil.disk_usage(str(ROOT))
    free_gb = stat.free / (1024 ** 3)
    used_pct = (stat.used / stat.total) * 100
    print(f"Диск: {free_gb:.1f}GB свободно ({used_pct:.0f}% занято)")

    dirs_to_check = [
        ROOT / "output" / "queue_id",
        ROOT / "output" / "queue",
        ROOT / "output" / "queue_ar",
        ROOT / "uploaded",
        ROOT / "output",
    ]
    for d in dirs_to_check:
        if d.exists():
            size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
            print(f"  {d.relative_to(ROOT)}: {size / (1024**3):.1f}GB")


if __name__ == "__main__":
    report()
    check_disk_space()
    print(f"OK — достаточно места для генерации (>{MIN_FREE_GB}GB свободно)")
