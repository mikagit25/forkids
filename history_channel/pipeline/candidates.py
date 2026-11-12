"""Candidate sheets for picking photos by eye (the hand-picked workflow that gave the best videos).

    python run.py episodes/smallpox candidates          # all scenes
    python run.py episodes/smallpox candidates kansas   # one scene (scene ids after the step name)

For every scene it searches all archives with the scene's `query:` entries (plus optional `candidates:`
queries), keeps only licences that are safe for a monetized channel, drops near-duplicates, and writes:

    episodes/<ep>/candidates/<scene>_NN.jpg   numbered contact sheets (open them and look)
    episodes/<ep>/candidates/<scene>.md       number -> ref, source, date, size, licence, title, link
    episodes/<ep>/candidates/index.json       every candidate's full record (fetch uses it for picked refs)

Picking: write the ref from the .md table into the scene's images, e.g.
    - {file: "smithsonian:NMAH-AHB2025q024595"}
    - {file: "curid:25513204", rotate: -90}
"""
from __future__ import annotations

import io
import json
import re
import textwrap
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from . import select
from .archives import DEFAULT_SOURCES, SESSION, SOURCES

TW, TH, COLS = 300, 220, 6
PER_SOURCE = 8


def thumb_url(c: dict) -> str:
    u = c.get("download_url") or ""
    s = c["source"]
    if s == "commons":
        return re.sub(r"/\d+px-", "/400px-", u)
    if s == "met":
        return u.replace("/original/", "/web-large/")
    if s == "cleveland":
        return u.replace("_print.jpg", "_web.jpg")
    if s in ("aic", "wellcome", "europeana"):
        return re.sub(r"/full/[^/]+/", "/full/400,/", u)
    if s == "smithsonian":
        return u.replace("&max=3000", "&max=400")
    return u


def _thumb(c: dict) -> Image.Image | None:
    for url in (thumb_url(c), c.get("download_url")):
        if not url:
            continue
        try:
            r = SESSION.get(url, timeout=40)
            if r.status_code != 200:
                continue
            im = Image.open(io.BytesIO(r.content))
            im.load()
            im = ImageOps.exif_transpose(im).convert("RGB")
            if not c.get("width"):
                c["width"], c["height"] = im.size   # proportions only; real size comes with the download
                c["size_from_thumb"] = True
            im.thumbnail((TW * 2, TH * 2))
            return im
        except Exception:
            continue
    return None


def _search(source, query):
    try:
        return SOURCES[source](query)[:PER_SOURCE]
    except Exception as e:
        print(f"   ! {source} '{query}': {str(e)[:80]}")
        return []


def scene_candidates(scene: dict, episode: dict, seen_ids: set) -> list[dict]:
    queries = [q["query"] for q in scene.get("images", []) if q.get("query")]
    queries += scene.get("candidates", []) or []
    era = tuple(episode["era"]) if episode.get("era") else None
    jobs = [(s, q) for q in queries for s in DEFAULT_SOURCES]
    out = []
    with ThreadPoolExecutor(max_workers=4) as ex:   # one query per archive at a time, politely
        for (s, q), res in zip(jobs, ex.map(lambda j: _search(*j), jobs)):
            for c in res:
                if c["id"] in seen_ids:
                    continue
                c["query"] = q
                c["meta"] = round(select.meta_score(c, era, q), 2)
                if c["meta"] <= -0.75:
                    continue          # clearly modern or junk: not even worth a tile
                seen_ids.add(c["id"])
                out.append(c)
            time.sleep(0.2)
    return out


def build(ep_dir: Path, episode: dict, only: list[str] | None = None):
    from .render import font
    out_dir = ep_dir / "candidates"
    out_dir.mkdir(exist_ok=True)
    idx_path = out_dir / "index.json"
    index = json.loads(idx_path.read_text()) if idx_path.exists() else {}
    f_big = font("SourceSans3.ttf", 22, 700)
    f_sm = font("SourceSans3.ttf", 15, 500)
    seen: set = set()
    for scene in episode["scenes"]:
        sid = scene["id"]
        if only and sid not in only:
            continue
        print(f"[{sid}] searching all archives...")
        cands = scene_candidates(scene, episode, seen)
        with ThreadPoolExecutor(max_workers=6) as ex:
            thumbs = list(ex.map(_thumb, cands))
        rows, hashes = [], []
        for c, im in zip(cands, thumbs):
            if im is None:
                continue
            h = select.phash_img(im)
            if select.is_duplicate(h, hashes, max_dist=8):
                continue
            hashes.append(h)
            rows.append((c, im))
        for old in out_dir.glob(f"{sid}_*.jpg"):
            old.unlink()
        md = [f"# {sid} — {scene.get('chapter', '')}", "", textwrap.shorten(scene["narration"], 600), "",
              "| # | ref | source | date | W×H | licence | title |", "|---|---|---|---|---|---|---|"]
        per_sheet = COLS * 5
        for si in range(0, len(rows), per_sheet):
            chunk = rows[si:si + per_sheet]
            n_rows = (len(chunk) + COLS - 1) // COLS
            sheet = Image.new("RGB", (COLS * (TW + 6) + 6, n_rows * (TH + 52) + 6), (18, 18, 18))
            d = ImageDraw.Draw(sheet)
            for k, (c, im) in enumerate(chunk):
                n = si + k + 1
                x = 6 + (k % COLS) * (TW + 6)
                y = 6 + (k // COLS) * (TH + 52)
                t = im.copy()
                t.thumbnail((TW, TH))
                sheet.paste(t, (x + (TW - t.width) // 2, y + (TH - t.height) // 2))
                d.rectangle([x, y, x + 46, y + 26], fill=(0, 0, 0))
                d.text((x + 5, y + 2), f"{n}", font=f_big, fill=(255, 220, 60))
                tag = c["source"]
                d.rectangle([x + TW - 8 - d.textlength(tag, font=f_sm), y, x + TW, y + 20], fill=(0, 50, 100))
                d.text((x + TW - 4 - d.textlength(tag, font=f_sm), y + 1), tag, font=f_sm, fill=(255, 255, 255))
                w, h = c.get("width") or 0, c.get("height") or 0
                orient = "vertical" if h > w * 1.1 else "wide" if w > h * 1.1 else "square"
                d.text((x, y + TH + 4), f"{(c.get('date') or '')[:12]} · {orient}", font=f_sm, fill=(170, 170, 170))
                d.text((x, y + TH + 24), (c.get("title") or "")[:40], font=f_sm, fill=(225, 225, 225))
                ref = "curid:" + c["id"].split(":", 1)[1] if c["source"] == "commons" else c["id"]
                index[ref] = {k2: v for k2, v in c.items() if k2 not in ("_h",)}
                md.append(f"| {n} | `{ref}` | {c['source']} | {(c.get('date') or '')[:20]} | {w}×{h} | "
                          f"{(c.get('license') or '')[:30]} | [{(c.get('title') or '').replace('|', '/')[:70]}]({c.get('page_url')}) |")
            sheet.save(out_dir / f"{sid}_{si // per_sheet + 1:02d}.jpg", quality=82)
        (out_dir / f"{sid}.md").write_text("\n".join(md) + "\n")
        print(f"[{sid}] {len(rows)} candidates -> {out_dir}/{sid}_*.jpg")
    idx_path.write_text(json.dumps(index, indent=0, ensure_ascii=False))
