"""Library of Congress exchange through GitHub (loc.gov search is closed to servers by a Cloudflare bot check,
so a person / Claude in Chrome searches loc.gov, and this server takes the results from the repo).

    python run.py episodes/<ep> loc-request [scene ...]   # writes loc_exchange/requests/<ep>.md -> commit + push
    (Chrome session: reads the request on GitHub, fills loc_exchange/picks/<ep>.yaml, commits)
    python run.py episodes/<ep> loc-import                # git pull, check every pick, add to episode.yaml scenes

Protocol and rules for the Chrome side: loc_exchange/README.md
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
X = ROOT / "loc_exchange"
RIGHTS_OK = re.compile(r"no known restrictions|public domain|no known copyright", re.I)


def request(ep_dir: Path, episode: dict, only: list[str] | None = None):
    slug = episode["slug"]
    lines = [f"# LoC request: {episode['title']}", "",
             f"Episode `{slug}`. Era of the photos: {episode.get('era', '?')}. "
             f"Write results to `history_channel/loc_exchange/picks/{slug}.yaml` (format: ../README.md).", "",
             "For every scene: 2–6 photos that SHOW what the narration says (place, people, objects, the time).",
             "Search https://www.loc.gov/photos/ — the queries below are only a start, try your own words too.", ""]
    for s in episode["scenes"]:
        if only and s["id"] not in only:
            continue
        words = s["narration"].split()
        need = max(2, round(len(words) / 130 * 60 / 6.5 / 2))      # LoC adds to other archives: about half
        qs = [q.get("query") for q in s.get("images", []) if q.get("query")] + list(s.get("candidates", []))
        lines += [f"## scene `{s['id']}` — {s.get('chapter', '')} {s.get('date', '')}".rstrip(),
                  f"wanted: up to {need} photos",
                  f"searches: {', '.join(dict.fromkeys(qs)) or '—'}", "",
                  "> " + " ".join(words[:90]) + (" …" if len(words) > 90 else ""), ""]
    out = X / "requests" / f"{slug}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
    print(f"{out}  -> git add/commit/push, then ask the Chrome session to fill picks/{slug}.yaml")
    return out


def import_picks(ep_dir: Path, episode: dict):
    subprocess.run(["git", "-C", str(ROOT), "pull", "--rebase", "--autostash", "-q"], check=False)
    slug = episode["slug"]
    files = [f for f in (X / "picks" / f"{slug}.yaml", X / "picks" / f"{slug}-news.yaml") if f.exists()]
    if not files:
        raise SystemExit(f"no picks/{slug}.yaml or picks/{slug}-news.yaml yet")
    picks = [p for f in files for p in (yaml.safe_load(f.read_text()) or [])]
    ep_yaml = ep_dir / "episode.yaml"
    text = ep_yaml.read_text()
    data = yaml.safe_load(text)
    scenes = {s["id"]: s for s in data["scenes"]}
    # a page may give several clippings: a newspaper pick is a duplicate only with the same page AND crop
    have = {q.get("file") or (q.get("newspaper"), tuple(round(float(c), 3) for c in q.get("crop") or []))
            for s in data["scenes"] for q in s.get("images", [])}
    # picks already imported once (the crop may have been adjusted by hand since): never add them again
    seen_f = X / "picks" / f".imported-{slug}.json"
    seen = set(json.loads(seen_f.read_text())) if seen_f.exists() else set()
    sig = lambda p: f"{p.get('lccn') or p.get('image')}|{p.get('crop')}"
    for p in picks:            # everything that is in episode.yaml now counts as imported
        if p.get("kind") == "newspaper" and (p.get("image"), tuple(round(float(c), 3) for c in p.get("crop") or [])) in have:
            seen.add(sig(p))
    added, bad = [], []
    for p in picks:
        if sig(p) in seen:
            continue
        if p.get("kind") == "newspaper":
            why = None
            crop = p.get("crop")
            year = int(str(p.get("date", "0"))[:4] or 0)
            if p.get("scene") not in scenes:
                why = f"unknown scene {p.get('scene')}"
            elif not str(p.get("image", "")).startswith("https://tile.loc.gov/"):
                why = "image link is not tile.loc.gov"
            elif not (1800 <= year <= 1928):
                why = f"date {p.get('date')} (only pages up to 1928)"
            elif not (isinstance(crop, list) and len(crop) == 4 and all(0 <= float(c) <= 1 for c in crop)
                      and crop[0] < crop[2] and crop[1] < crop[3]):
                why = f"bad crop {crop}"
            elif (p["image"], tuple(round(float(c), 3) for c in crop)) in have:
                why = "already in episode.yaml"
            if why:
                bad.append((p.get("page_url", "?"), why))
                continue
            ref = {"newspaper": p["image"], "date": str(p["date"]), "paper": p.get("paper", ""),
                   "page_url": p.get("page_url", ""), "crop": [round(float(c), 3) for c in crop]}
            if p.get("match"):
                ref["match"] = p["match"]
            if p.get("note"):
                ref["note"] = p["note"]
            added.append((p["scene"], ref))
            have.add((p["image"], tuple(ref["crop"])))
            continue
        lccn = str(p.get("lccn", "")).strip()
        why = None
        if p.get("scene") not in scenes:
            why = f"unknown scene {p.get('scene')}"
        elif not re.fullmatch(r"[a-z]{0,3}\d{8,12}", lccn):
            why = f"bad lccn '{lccn}'"
        elif not RIGHTS_OK.search(str(p.get("rights", ""))):
            why = f"rights '{p.get('rights')}' (need 'No known restrictions' / public domain)"
        elif p.get("image") and not str(p["image"]).startswith("https://tile.loc.gov/"):
            why = "image link is not tile.loc.gov"
        elif f"loc:{lccn}" in have:
            why = "already in episode.yaml"
        if why:
            bad.append((lccn, why))
            continue
        ref = {"file": f"loc:{lccn}"}
        for k in ("image", "rights", "title", "date", "note"):
            if p.get(k):
                ref[k] = str(p[k])
        added.append((p["scene"], ref))
        have.add(ref["file"])
    seen |= {sig(p) for p in picks if p.get("kind") == "newspaper" or f"loc:{p.get('lccn')}" in have}
    seen_f.write_text(json.dumps(sorted(seen), indent=0))
    if not added:
        print("nothing new to add"); [print(f"   skipped {l}: {w}") for l, w in bad]
        return
    # append as flow-style lines at the end of each scene's images: keeps the hand-written yaml as it is
    lines = text.splitlines()
    for sid, ref in added:
        flow = "{" + ", ".join(f'{k}: ' + (json.dumps(v) if isinstance(v, list) else
                                           yaml.safe_dump(v, default_style=chr(34), width=10**6).strip())
                                for k, v in ref.items()) + "}"
        i = next(n for n, l in enumerate(lines) if re.match(rf"\s*- id: {re.escape(sid)}\s*$", l))
        j = next((n for n in range(i + 1, len(lines)) if re.match(r"\s*- id: ", lines[n])), len(lines))
        img = next((n for n in range(i, j) if re.match(r"\s*images:\s*$", lines[n])), None)
        if img is None:
            raise SystemExit(f"scene {sid}: no `images:` block to add to")
        last = img
        for n in range(img + 1, j):
            if re.match(r"\s*- ", lines[n]) and len(lines[n]) - len(lines[n].lstrip()) > \
                    len(lines[img]) - len(lines[img].lstrip()):
                last = n
        indent = " " * (len(lines[img]) - len(lines[img].lstrip()) + 2)
        lines.insert(last + 1, f"{indent}- {flow}   # LoC via Chrome")
    ep_yaml.write_text("\n".join(lines) + "\n")
    seen_f.write_text(json.dumps(sorted(seen | {sig(p) for p in picks}), indent=0))
    yaml.safe_load(ep_yaml.read_text())        # must still parse
    for sid, ref in added:
        print(f"   + [{sid}] {ref.get('file') or ref.get('paper', 'newspaper') + ' ' + ref.get('date', '')}  "
              f"{(ref.get('title') or ref.get('note', ''))[:60]}")
    for l, w in bad:
        print(f"   skipped {l}: {w}")
    print("next: python run.py episodes/%s fetch  (then framing / review)" % slug)
