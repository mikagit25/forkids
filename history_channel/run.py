#!/usr/bin/env python3
"""Archive history video pipeline.

  python run.py episodes/1918-flu fetch      # find + download archive images, write contact sheet
  python run.py episodes/1918-flu voice      # narration (cached per sentence)
  python run.py episodes/1918-flu preview    # fast 540p render to check pacing
  python run.py episodes/1918-flu render     # final 1080p + subtitles + chapters
  python run.py episodes/1918-flu publish    # thumbnail + description
  python run.py episodes/1918-flu all        # fetch, voice, render, publish
  python run.py episodes/1918-flu candidates # numbered contact sheets from all archives, for picking by eye
  python run.py episodes/<ep> pool hurley "Photographs by Frank Hurley" ...   # sheets of whole Commons categories
  python run.py episodes/1918-flu research   # newspaper headlines of the time -> research/newspapers.md
  python run.py episodes/1918-flu framing    # BEFORE render: how each photo is cropped/moved -> build/framing/
  python run.py episodes/1918-flu review     # contact sheets of all photos for review (episodes/<ep>/review/)
  python run.py episodes/1918-flu upload [--at 2026-11-22T18:00:00Z|none]  # PRIVATE, auto-public at the next
                                             # every-other-day slot (owner switches it to a Premiere in Studio)
  python run.py episodes/1918-flu loc-request [scene ...]   # what to find on loc.gov -> loc_exchange/ (GitHub)
  python run.py episodes/1918-flu loc-import  # take Chrome-session picks from loc_exchange/picks/<ep>.yaml
  python run.py episodes/1918-flu shorts --suggest   # numbered sentences -> choose `shorts:` windows in episode.yaml
  python run.py episodes/1918-flu shorts [N ...]     # vertical Shorts from the finished render -> build/shorts/
  python run.py episodes/1918-flu shorts-upload 2026-11-21T16:00:00Z [hours]   # PRIVATE, scheduled every 24 h
"""
import sys
from pathlib import Path

import yaml

from pipeline import candidates, fetch, framing, locx, publish, render, research, review, shorts, tts


def main():
    research.load_env()   # API keys from history_channel/.env (never commit that file)
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    ep_dir, steps = Path(sys.argv[1]), sys.argv[2:]
    episode = yaml.safe_load((ep_dir / "episode.yaml").read_text())
    channel = Path("channel.yaml")
    if channel.exists():
        episode = {**yaml.safe_load(channel.read_text()), **episode}
    if "all" in steps:
        steps = ["fetch", "voice", "render", "publish"]
    for step in steps:
        print(f"\n=== {step} ===")
        if step == "fetch":
            fetch.fetch(ep_dir, episode, refresh="--refresh" in sys.argv)
        elif step == "voice":
            tts.voice_episode(ep_dir, episode)
        elif step in ("render", "preview"):
            render.render(ep_dir, episode, preview=step == "preview", parallax="--no-parallax" not in sys.argv,
                          allow_short="--allow-short" in sys.argv)
        elif step == "publish":
            publish.thumbnail(ep_dir, episode)
            publish.description(ep_dir, episode)
        elif step == "candidates":
            only = [a for a in sys.argv[sys.argv.index("candidates") + 1:] if not a.startswith("--")]
            candidates.build(ep_dir, episode, only or None)
            break
        elif step == "pool":          # pool <name> "Category A" "Category B" ...  (Commons categories, 1 level deep)
            a = sys.argv[sys.argv.index("pool") + 1:]
            candidates.pool(ep_dir, a[0], a[1:])
            break
        elif step == "research":
            research.research(ep_dir, episode)
        elif step == "framing":
            framing.framing_sheets(ep_dir, episode)
        elif step == "review":
            review.review_pack(ep_dir, episode)
        elif step == "loc-request":
            locx.request(ep_dir, episode, [a for a in sys.argv[sys.argv.index("loc-request") + 1:]
                                           if not a.startswith("--")] or None)
            break
        elif step == "loc-import":
            locx.import_picks(ep_dir, episode)
        elif step == "shorts":
            if "--suggest" in sys.argv:
                shorts.suggest(ep_dir)
            else:
                nums = [int(a) for a in sys.argv[sys.argv.index("shorts") + 1:] if a.isdigit()]
                shorts.build(ep_dir, episode, nums or None)
            break
        elif step == "shorts-upload":
            rest = sys.argv[sys.argv.index("shorts-upload") + 1:]
            shorts.upload(ep_dir, episode, rest[0], float(rest[1]) if len(rest) > 1 else 24.0)
            break
        elif step == "upload":
            at = sys.argv[sys.argv.index("--at") + 1] if "--at" in sys.argv else None
            publish.upload(ep_dir, episode, publish_at=at)
        elif not step.startswith("--"):
            sys.exit(f"unknown step: {step}")


if __name__ == "__main__":
    main()
