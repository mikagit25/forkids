#!/usr/bin/env python3
"""Archive history video pipeline.

  python run.py episodes/1918-flu fetch      # find + download archive images, write contact sheet
  python run.py episodes/1918-flu voice      # narration (cached per sentence)
  python run.py episodes/1918-flu preview    # fast 540p render to check pacing
  python run.py episodes/1918-flu render     # final 1080p + subtitles + chapters
  python run.py episodes/1918-flu publish    # thumbnail + description
  python run.py episodes/1918-flu all        # fetch, voice, render, publish
  python run.py episodes/1918-flu upload     # upload as PRIVATE (needs client_secret.json)
"""
import sys
from pathlib import Path

import yaml

from pipeline import fetch, publish, render, tts


def main():
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
            render.render(ep_dir, episode, preview=step == "preview")
        elif step == "publish":
            publish.thumbnail(ep_dir, episode)
            publish.description(ep_dir, episode)
        elif step == "upload":
            publish.upload(ep_dir, episode)
        elif not step.startswith("--"):
            sys.exit(f"unknown step: {step}")


if __name__ == "__main__":
    main()
