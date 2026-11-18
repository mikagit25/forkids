#!/usr/bin/env python3
"""Cron (daily): schedule the next Archive Tales Short for today 16:00 UTC.  python shorts_daily.py [per_day]"""
import sys
from pathlib import Path

import yaml

from pipeline import research, shorts

ROOT = Path(__file__).resolve().parent
research.load_env()
shorts.daily(ROOT, yaml.safe_load((ROOT / "channel.yaml").read_text()),
             per_day=int(sys.argv[1]) if len(sys.argv) > 1 else 1)
