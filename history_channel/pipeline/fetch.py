"""Step 1: find and download archive images for every scene.

Writes  <episode>/media/*.jpg
        <episode>/manifest.json      (chosen images per scene + alternates, all with source & license)
        <episode>/contact_sheet.html (open in a browser to review before rendering)

To swap an image: in manifest.json set "use": false on the bad one and "use": true on an alternate,
then run render again. Re-running fetch keeps your choices unless you pass --refresh.
"""
from __future__ import annotations

import hashlib
import html
import io
import json
from pathlib import Path

import numpy as np

from PIL import Image

from .archives import DEFAULT_SOURCES, SESSION, search_all

ALTERNATES = 3  # extra candidates kept per query for the reviewer


def _download(c: dict, media: Path) -> Path | None:
    name = c["id"].replace(":", "_").replace("/", "_") + "_" + hashlib.md5(c["download_url"].encode()).hexdigest()[:6] + ".jpg"
    dest = media / name
    if dest.exists():
        return dest
    for url in [c["download_url"], *c.get("download_fallbacks", [])]:
        try:
            r = SESSION.get(url, timeout=90)
            if r.status_code != 200:
                continue
            im = Image.open(io.BytesIO(r.content))
            im.load()
            if im.width < 700:
                return None
            if im.mode != "RGB":
                im = im.convert("RGB")
            if max(im.size) > 4000:
                im.thumbnail((4000, 4000), Image.LANCZOS)
            im.save(dest, "JPEG", quality=92)
            c["width"], c["height"] = im.size
            return dest
        except Exception as e:
            print(f"   ! download failed {url[:90]}: {e}")
    return None


WPM = 133          # narration speed of the default voice
SHOT_SECONDS = 6.5  # keep in sync with render.SHOT_TARGET


def _scale_counts(scene: dict, teasers: int = 0):
    """Ask for enough photos to cover the narration without repeats (about one per 6.5 s, 2.6 s in a montage)."""
    secs = len(scene["narration"].split()) / WPM * 60
    need = int(np.ceil(secs / (2.6 if scene.get("montage") else SHOT_SECONDS))) - (teasers if scene.get("montage") else 0)
    qs = scene.get("images", [])
    have = sum(q.get("count", 1) for q in qs)
    i = 0
    while have < need and qs:
        q = qs[i % len(qs)]
        q["count"] = q.get("count", 1) + 1
        have += 1
        i += 1


def fetch(ep_dir: Path, episode: dict, refresh: bool = False):
    from . import select
    media = ep_dir / "media"
    media.mkdir(exist_ok=True)
    man_path = ep_dir / "manifest.json"
    old = json.loads(man_path.read_text()) if man_path.exists() and not refresh else {}
    manifest = {"scenes": {}}
    era = tuple(episode["era"]) if episode.get("era") else None
    rel = select.Relevance()
    seen: set[str] = set()
    hashes: list = []

    for sid, items in old.get("scenes", {}).items():
        for it in items:
            seen.add(it["id"])

    later_chapters = lambda i: sum(1 for x in episode["scenes"][i + 1:] if x.get("chapter"))
    for si, scene in enumerate(episode["scenes"]):
        sid = scene["id"]
        _scale_counts(scene, later_chapters(si))
        if sid in old.get("scenes", {}) and all((ep_dir / i["file"]).exists() for i in old["scenes"][sid]):
            manifest["scenes"][sid] = old["scenes"][sid]
            col = {q["query"]: bool(q.get("colorize")) for q in scene.get("images", [])}
            for it in manifest["scenes"][sid]:   # pick up colorize flags added to the script later
                it["colorize"] = it.get("colorize", col.get(it.get("query"), False)) or col.get(it.get("query"), False)
                hashes.append(select.phash(ep_dir / it["file"]))
            print(f"[{sid}] kept {sum(i['use'] for i in old['scenes'][sid])} images from previous run")
            continue
        chosen = []
        for q in scene.get("images", []):
            want = q.get("count", 1)
            print(f"[{sid}] searching: {q['query']}")
            cands = search_all(q["query"], q.get("sources") or DEFAULT_SOURCES)
            for c in cands:
                c["meta"] = round(select.meta_score(c, era, q["query"], q.get("modern", False)), 3)
            cands = [c for c in cands if c["id"] not in seen and c["meta"] > -0.45]
            cands.sort(key=lambda c: -c["meta"])          # stable: keeps archive relevance order within ties
            pool, tried = [], 0
            texts = select.prompts(q["query"], scene, episode)
            for c in cands:
                if len(pool) >= want * 3 + 2 or tried >= want * 5 + 8:
                    break
                tried += 1
                path = _download(c, media)
                if not path:
                    continue
                h = select.phash(path)
                if select.is_duplicate(h, hashes + [p["_h"] for p in pool]):
                    print(f"   - duplicate of an image already used: {c['title'][:60]}")
                    path.unlink(missing_ok=True)
                    continue
                c["clip"] = rel.score(path, texts)
                c["score"] = round(select.combined(c["meta"], c["clip"]), 3)
                c["_h"], c["file"] = h, str(path.relative_to(ep_dir))
                pool.append(c)
            pool.sort(key=lambda c: -c["score"])
            good = [c for c in pool if c["clip"] is None or c["clip"] >= select.CLIP_MIN]
            weak = [c for c in pool if c not in good]
            use, alts = good[:want], (good[want:] + weak)[:ALTERNATES]
            for c in pool:
                if c not in use and c not in alts:
                    (ep_dir / c["file"]).unlink(missing_ok=True)
            for c in use + alts:
                c["use"] = c in use
                c["query"] = q["query"]
                c["colorize"] = bool(q.get("colorize")) and c in use[:1]
                hashes.append(c.pop("_h"))
                seen.add(c["id"])
                chosen.append(c)
            if len(use) < want:
                print(f"   ! only {len(use)}/{want} relevant images for '{q['query']}' "
                      f"({len(pool)} downloaded) - consider another query")
        manifest["scenes"][sid] = chosen

    man_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    write_contact_sheet(ep_dir, episode, manifest)
    n = sum(i["use"] for v in manifest["scenes"].values() for i in v)
    print(f"\nmanifest: {n} images selected. Review: {ep_dir / 'contact_sheet.html'}")
    return manifest


def write_contact_sheet(ep_dir: Path, episode: dict, manifest: dict):
    rows = []
    for scene in episode["scenes"]:
        sid = scene["id"]
        cards = []
        for it in manifest["scenes"].get(sid, []):
            badge = "USE" if it["use"] else "alternate"
            cards.append(f"""
            <figure class="{'use' if it['use'] else 'alt'}">
              <img src="{html.escape(it['file'])}" loading="lazy">
              <figcaption><b>{badge}</b>{' · COLORIZE' if it.get('colorize') else ''} · {html.escape(it['id'])}
              <small>score {it.get('score', '-')} · clip {it.get('clip') if it.get('clip') is not None else '-'}</small><br>
              {html.escape(it['title'][:120])}<br>
              <small>{html.escape(it['license'])} · {html.escape(it['credit'][:80])}</small><br>
              <a href="{html.escape(it['page_url'] or '')}" target="_blank">source page</a></figcaption>
            </figure>""")
        rows.append(f"<section><h2>{html.escape(scene.get('chapter') or sid)}</h2>"
                    f"<p class=n>{html.escape(scene['narration'][:300])}…</p><div class=g>{''.join(cards)}</div></section>")
    (ep_dir / "contact_sheet.html").write_text(f"""<!doctype html><meta charset=utf-8>
<title>Contact sheet · {html.escape(episode['title'])}</title>
<style>body{{font:14px system-ui;margin:24px;background:#111;color:#ddd}}
.g{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}}
figure{{margin:0;background:#1c1c1c;border:2px solid #333;border-radius:6px;overflow:hidden}}
figure.use{{border-color:#3a7}} figure.alt{{opacity:.55}}
img{{width:100%;height:180px;object-fit:cover;display:block}} figcaption{{padding:8px;line-height:1.35}}
a{{color:#8bf}} .n{{color:#999;max-width:900px}}</style>
<h1>{html.escape(episode['title'])}</h1>
<p>Green = will be used. Faded = alternates. To swap, edit <code>"use"</code> in manifest.json.</p>
{''.join(rows)}""")
