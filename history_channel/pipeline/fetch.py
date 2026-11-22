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
import re
import time
from pathlib import Path

import numpy as np

from PIL import Image, ImageOps

from .archives import DEFAULT_SOURCES, SESSION, commons_file, museum_object, search_all

ALTERNATES = 3  # extra candidates kept per query for the reviewer


def _download(c: dict, media: Path) -> Path | None:
    name = c["id"].replace(":", "_").replace("/", "_") + "_" + hashlib.md5(c["download_url"].encode()).hexdigest()[:6] + ".jpg"
    dest = media / name
    if dest.exists():
        return dest
    for url in [c["download_url"], *c.get("download_fallbacks", [])]:
        try:
            if url.startswith("file://"):        # handed over by a person (archive behind a bot check)
                r = type("R", (), {"status_code": 200, "content": Path(url[7:]).read_bytes()})()
            else:
              for attempt in range(5):
                  time.sleep(1.5)                     # be polite: upload.wikimedia.org rate-limits bursts (HTTP 429)
                  r = SESSION.get(url, timeout=90)
                  if r.status_code != 429:
                      break
                  wait = min(int(r.headers.get("retry-after", 60) or 60), 120) * (attempt + 1)
                  print(f"   … rate-limited (429), waiting {wait}s and retrying")
                  time.sleep(wait)
            if r.status_code != 200:
                print(f"   ! HTTP {r.status_code} for {url[:90]}")
                continue
            im = Image.open(io.BytesIO(r.content))
            im.load()
            im = ImageOps.exif_transpose(im)      # phone/camera photos stored sideways with an EXIF flag
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
    qs = [q for q in scene.get("images", []) if not q.get("file")]
    have = sum(q.get("count", 1) for q in scene.get("images", []))
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
    missing: list = []     # hand-picked refs that could not be fetched -> loud summary at the end

    for sid, items in old.get("scenes", {}).items():
        for it in items:
            seen.add(it["id"])

    later_chapters = lambda i: sum(1 for x in episode["scenes"][i + 1:] if x.get("chapter"))
    for si, scene in enumerate(episode["scenes"]):
        sid = scene["id"]
        _scale_counts(scene, later_chapters(si))
        # framing keys (frame/zoom/pan/detail) only matter to render: changing them must not re-download
        sig_imgs = [{k: v for k, v in q.items() if k not in ("frame", "zoom", "pan", "detail")}
                    for q in scene.get("images", []) or []]
        sig = hashlib.md5(json.dumps(sig_imgs, sort_keys=True).encode()).hexdigest()[:12]
        manifest.setdefault("sig", {})[sid] = sig
        unchanged = old.get("sig", {}).get(sid, sig) == sig   # manifests from before this check count as unchanged
        want_rot = sum(1 for q in scene.get("images", []) if q.get("rotate"))
        have_rot = sum(1 for i in old.get("scenes", {}).get(sid, []) if i.get("rotate"))
        unchanged = unchanged and want_rot == have_rot
        # every hand-picked photo / clipping in the script must already be in the manifest, otherwise fetch again
        want_refs = sum(1 for q in scene.get("images", []) if q.get("file") or q.get("newspaper") or q.get("paperspast"))
        have_refs = sum(1 for i in old.get("scenes", {}).get(sid, []) if i.get("picked") or i.get("source") == "newspaper")
        if want_refs > have_refs:
            print(f"[{sid}] only {have_refs}/{want_refs} picked photos downloaded -> fetching this scene again")
            unchanged = False
        if not unchanged:
            print(f"[{sid}] images changed in episode.yaml -> fetching this scene again")
        if unchanged and sid in old.get("scenes", {}) and all((ep_dir / i["file"]).exists() for i in old["scenes"][sid]):
            manifest["scenes"][sid] = old["scenes"][sid]
            col = {q["query"]: bool(q.get("colorize")) for q in scene.get("images", []) if "query" in q}
            for it in manifest["scenes"][sid]:   # pick up colorize flags added to the script later
                it["colorize"] = it.get("colorize", col.get(it.get("query"), False)) or col.get(it.get("query"), False)
                hashes.append(select.phash(ep_dir / it["file"]))
            print(f"[{sid}] kept {sum(i['use'] for i in old['scenes'][sid])} images from previous run")
            continue
        chosen = []
        # 0) newspaper clippings: a crop of a scanned page (public domain: published before 1929)
        for q in scene.get("images", []):
            if not (q.get("newspaper") or q.get("paperspast")):
                continue
            c = paperspast_clipping(q, media, ep_dir) if q.get("paperspast") else newspaper_clipping(q, media, ep_dir)
            if c and q.get("match"):
                c["match"] = q["match"]
            if c:
                hashes.append(select.phash(ep_dir / c["file"]))
                chosen.append(c)
                print(f"[{sid}] clipping: {c['title'][:70]}")
        # 1) photos picked by hand (exact Commons files) always come first, in script order
        for q in scene.get("images", []):
            if not q.get("file"):
                continue
            ref = q["file"]
            prefix = ref.split(":", 1)[0]
            if prefix in ("met", "aic", "cleveland"):
                c = museum_object(ref)
            elif prefix in ("curid", "File") or ref.startswith("File:"):
                c = commons_file(ref)
            elif prefix == "loc" and q.get("image"):
                c = _loc_manual(ref, q)
            elif prefix == "web":
                c = _web_manual(ref, q)
            elif prefix == "loc" and not _from_candidates(ep_dir, ref):
                c = _loc_by_lccn(ref.split(":", 1)[1])
            else:   # smithsonian:, europeana:, wellcome:, loc:, commons: ... picked from a candidate sheet
                c = _from_candidates(ep_dir, ref)
            if not c:
                print(f"   !! {ref}: not found / licence not allowed")
                missing.append((sid, ref, "not found"))
                continue
            path = _download(c, media)
            if not path:
                print(f"   !! {ref}: download failed")
                missing.append((sid, ref, "download failed"))
                continue
            if q.get("crop"):     # [x0, y0, x1, y1] fractions: e.g. the photo inside an archive card
                path = _cropped(path, q["crop"])
                c["crop"] = list(q["crop"])
            if q.get("rotate"):
                path = _rotated(path, int(q["rotate"]))
                c["rotate"] = int(q["rotate"])
            c.update(file=str(path.relative_to(ep_dir)), use=True, query=q.get("note", q["file"]), ref=q["file"],
                     colorize=bool(q.get("colorize")), picked=True, score=1.0)
            if q.get("match"):
                c["match"] = q["match"]
            hashes.append(select.phash(path))
            seen.add(c["id"])
            chosen.append(c)
            print(f"[{sid}] picked: {c['title'][:70]}")
        # 2) automatic search for anything still described only by a query
        for q in scene.get("images", []):
            if q.get("file") or q.get("newspaper") or q.get("paperspast"):
                continue
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

    auto_colorize(ep_dir, episode, manifest)
    man_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    write_contact_sheet(ep_dir, episode, manifest)
    n = sum(i["use"] for v in manifest["scenes"].values() for i in v)
    print(f"\nmanifest: {n} images selected. Review: {ep_dir / 'contact_sheet.html'}")
    seen = {}
    for sc in episode.get("scenes", []):                  # the same photo picked in two scenes = repeat in the video
        if sc.get("montage"):                             # cold-open teasers re-use chapter photos on purpose
            continue
        for it in sc.get("images") or []:
            ref = it.get("file") if isinstance(it, dict) else None
            if ref and ref in seen and seen[ref] != sc["id"]:
                missing.append((sc["id"], ref, f"DUPLICATE: also picked in scene {seen[ref]}"))
            elif ref:
                seen[ref] = sc["id"]
    (ep_dir / "missing.json").write_text(json.dumps([list(m) for m in missing], indent=0))   # render refuses while non-empty
    if missing:
        print(f"\n!! {len(missing)} hand-picked photos are MISSING (replace them in episode.yaml before rendering):")
        for sid, ref, why in missing:
            print(f"   {sid}: {ref} ({why})")
    return manifest


def _from_candidates(ep_dir: Path, ref: str) -> dict | None:
    from .archives import license_ok
    idx = ep_dir / "candidates" / "index.json"
    if not idx.exists():
        print(f"   ! {ref}: run the candidates step first (no candidates/index.json)")
        return None
    rec = json.loads(idx.read_text()).get(ref)
    if not rec:
        print(f"   ! {ref}: not in candidates/index.json")
        return None
    rec = dict(rec)
    lic = rec.get("license", "")
    if not (license_ok(lic) or lic.startswith("CC0") or "No known restrictions" in lic):
        print(f"   ! {ref}: licence not allowed ({lic})")
        return None
    for k in ("meta", "query", "size_from_thumb"):
        rec.pop(k, None)
    rec["width"] = rec["height"] = 0
    return rec


def _cropped(path: Path, box) -> Path:
    """crop: [x0, y0, x1, y1] as fractions of the original. Cached as a separate file; check it by eye."""
    tag = "_".join(f"{int(round(v * 1000)):03d}" for v in box)
    out = path.with_name(f"{path.stem}_c{tag}.jpg")
    if not out.exists():
        with Image.open(path) as im:
            w, h = im.size
            im.convert("RGB").crop((int(box[0] * w), int(box[1] * h), int(box[2] * w), int(box[3] * h))).save(out, "JPEG", quality=92)
    return out


def _rotated(path: Path, deg: int) -> Path:
    """rotate: 90 = turn clockwise, -90 = counter-clockwise, 180 = upside down. Cached as a separate file.
    Check the result by eye (Read the *_r<deg>.jpg file): text and people must be upright."""
    out = path.with_name(f"{path.stem}_r{deg % 360}.jpg")
    if not out.exists():
        with Image.open(path) as im:
            im.rotate(-deg, expand=True).save(out, "JPEG", quality=92)   # PIL rotates counter-clockwise
    return out


def newspaper_clipping(q: dict, media: Path, ep_dir: Path) -> dict | None:
    """q = {newspaper: <page image url>, crop: [x0, y0, x1, y1] (fractions of the page), paper: "...",
            date: "1918-10-05", page_url: "<link for the description>"}"""
    date = str(q.get("date", ""))
    if not date[:4].isdigit() or int(date[:4]) >= 1929:
        print(f"   ! clipping skipped: needs a publication date before 1929 ({date or 'no date'})")
        return None
    url = q["newspaper"]
    local_crop = q.get("crop")
    if "/iiif/" in url and url.rstrip("/").endswith("default.jpg"):
        parts = url.split("/")
        if local_crop:        # ask the IIIF server for just the clipping, at full scan resolution
            x0, y0, x1, y1 = (float(c) * 100 for c in local_crop)
            parts[-4] = f"pct:{x0:.2f},{y0:.2f},{x1 - x0:.2f},{y1 - y0:.2f}"
            parts[-3] = "full"
            local_crop = None
        else:
            parts[-4] = "full"
            parts[-3] = "3000,"   # whole page: a large render is enough
        url = "/".join(parts)
    key = hashlib.md5((url + str(q.get("crop"))).encode()).hexdigest()[:10]
    dest = media / f"news_{key}.jpg"
    if not dest.exists():
        im = None
        for attempt in range(4):          # tile.loc.gov sometimes drops the connection mid-transfer
            try:
                r = SESSION.get(url, timeout=180)
                r.raise_for_status()
                im = Image.open(io.BytesIO(r.content)).convert("RGB")
                break
            except Exception as e:
                err = e
                time.sleep(5 * (attempt + 1))
        if im is None:
            print(f"   ! clipping download failed: {err}")
            return None
        if local_crop:
            x0, y0, x1, y1 = local_crop
            W, H = im.size
            im = im.crop((int(x0 * W), int(y0 * H), int(x1 * W), int(y1 * H)))
        im.save(dest, "JPEG", quality=92)
    paper = q.get("paper", "Newspaper")
    return {"source": "newspaper", "id": f"news:{key}", "title": f"{paper}, {date}", "description": q.get("note", ""),
            "date": date, "page_url": q.get("page_url") or q["newspaper"], "download_url": q["newspaper"],
            "license": "Public domain (published before 1929)", "credit": f"{paper}, {date}",
            "width": 0, "height": 0, "file": str(dest.relative_to(ep_dir)), "use": True, "query": "newspaper",
            "colorize": False, "picked": True, "score": 1.0}


def paperspast_clipping(q: dict, media: Path, ep_dir: Path) -> dict | None:
    """A whole article from Papers Past (New Zealand), stitched from its column images.
    q = {paperspast: "NOT19190129.2.34.3", areas: [1, 2] (optional), paper: "...", date: "1919-01-29"}
    Articles whose page says the paper is not available for commercial use are refused."""
    import base64
    import re as _re
    oid = q["paperspast"]
    page = f"https://paperspast.natlib.govt.nz/newspapers/{oid}"
    dest = media / f"pp_{oid.replace('.', '_')}.jpg"
    date = str(q.get("date", ""))
    if not dest.exists():
        try:
            html_ = SESSION.get(page, timeout=60).text
        except Exception as e:
            print(f"   ! Papers Past {oid}: {e}")
            return None
        if "not available for commercial use" in html_.lower():
            print(f"   ! Papers Past {oid}: newspaper not available for commercial use, skipped")
            return None
        found = {}
        for enc in _re.findall(r"imageserver/newspapers/([A-Za-z0-9=+/]+)", html_):
            try:
                dec = base64.b64decode(enc + "=" * (-len(enc) % 4)).decode("utf-8", "ignore")
            except Exception:
                continue
            m = _re.search(r"area=(\d+)", dec)
            if oid in dec and m:
                found[int(m.group(1))] = dec
        areas = q.get("areas") or sorted(found)
        parts = []
        for a in areas:
            if a not in found:
                continue
            spec = _re.sub(r"width=\d+", "width=1200", found[a])
            url = "https://paperspast.natlib.govt.nz/imageserver/newspapers/" + base64.b64encode(spec.encode()).decode()
            try:
                r = SESSION.get(url, timeout=60)
                r.raise_for_status()
                parts.append(Image.open(io.BytesIO(r.content)).convert("RGB"))
            except Exception as e:
                print(f"   ! Papers Past {oid} area {a}: {e}")
        if not parts:
            return None
        W = max(p.width for p in parts)
        H = sum(p.height for p in parts)
        im = Image.new("RGB", (W, H), (255, 255, 255))
        y = 0
        for p in parts:
            im.paste(p, ((W - p.width) // 2, y))
            y += p.height
        # warm the white a little, like aged newsprint
        im = Image.blend(im, Image.new("RGB", im.size, (236, 228, 208)), 0.18)
        im.save(dest, "JPEG", quality=92)
    paper = q.get("paper", "Newspaper")
    return {"source": "newspaper", "id": f"paperspast:{oid}", "title": f"{paper}, {date}", "description": q.get("note", ""),
            "date": date, "page_url": page, "download_url": page,
            "license": "Out of copyright (Papers Past, National Library of New Zealand)",
            "credit": f"{paper}, {date} · Papers Past", "width": 0, "height": 0,
            "file": str(dest.relative_to(ep_dir)), "use": True, "query": "newspaper",
            "colorize": False, "picked": True, "score": 1.0}


def auto_colorize(ep_dir: Path, episode: dict, manifest: dict):
    """`colorize_per_scene: N` in episode.yaml marks N black-and-white photos per scene for the
    original-then-colour reveal, if the script did not mark any. Prefers large, wide photos."""
    import cv2
    from .vision import is_grayscale
    n = int(episode.get("colorize_per_scene", 0) or 0)
    if not n:
        return
    for scene in episode["scenes"]:
        if scene.get("montage"):
            continue
        items = [i for i in manifest["scenes"].get(scene["id"], []) if i["use"]]
        if any(i.get("colorize") for i in items):
            continue
        cands = []
        for it in items:
            im = cv2.imread(str(ep_dir / it["file"]))
            if im is not None and is_grayscale(im):
                h, w = im.shape[:2]
                cands.append((-(w >= h * 1.2), -w * h, it))
        for _, _, it in sorted(cands, key=lambda x: (x[0], x[1]))[:n]:
            it["colorize"] = True


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


def _loc_manual(ref: str, q: dict) -> dict | None:
    """A Library of Congress item picked by hand in a browser (loc.gov search is closed to servers by a
    Cloudflare bot check; the image server tile.loc.gov is open). episode.yaml:
      - {file: "loc:2013646123", image: "https://tile.loc.gov/storage-services/service/pnp/ggbain/.../....jpg",
         title: "...", date: "1915", rights: "No known restrictions on publication."}
    Only items whose loc.gov "Rights Advisory" says no known restrictions / public domain may be used."""
    rights = q.get("rights", "")
    if not re.search(r"no known restrictions|public domain|no known copyright", rights, re.I):
        print(f"   !! {ref}: rights '{rights}' — need 'No known restrictions' from the loc.gov item page")
        return None
    if not q["image"].startswith("https://tile.loc.gov/"):
        print(f"   !! {ref}: image must be a tile.loc.gov link (the 'Download JPEG' link on the item page)")
        return None
    lccn = ref.split(":", 1)[1]
    return {"source": "loc", "id": ref, "title": q.get("title", ref), "description": q.get("note", ""),
            "date": q.get("date", ""), "page_url": f"https://www.loc.gov/item/{lccn}/", "download_url": q["image"],
            "license": "No known restrictions on publication (Library of Congress)",
            "credit": f"Library of Congress, LCCN {lccn}", "width": q.get("width"), "height": q.get("height")}


# archives a person may pick from by hand in Chrome (loc_exchange); the image must come from the archive itself
WEB_HOSTS = {"nsarchives": ("archives.novascotia.ca",), "nlm": ("collections.nlm.nih.gov", "nlm.nih.gov"),
             "cdc": ("phil.cdc.gov", "cdc.gov"), "bpl": ("digitalcommonwealth.org", "ark.digitalcommonwealth.org"),
             "nara": ("catalog.archives.gov", "s3.amazonaws.com/NARAprodstorage", "archives.gov")}


INBOX = Path(__file__).resolve().parent.parent / "loc_exchange" / "inbox"


def _web_manual(ref: str, q: dict) -> dict | None:
    """- {file: "web:nsarchives:<id>", image: "<largest JPEG>", page_url: "...", rights: "...", title, date}
    Picked by hand on an archive site (loc_exchange). Rights must say public domain / no known restrictions."""
    src = ref.split(":")[1] if ref.count(":") >= 2 else ""
    rights = q.get("rights", "")
    if src not in WEB_HOSTS:
        print(f"   !! {ref}: unknown source '{src}' (known: {', '.join(WEB_HOSTS)})"); return None
    if not re.search(r"no known restrictions|public domain|no known copyright|use:? unrestricted|cc0|^cc by \d", rights, re.I) \
            or re.search(r"\b(nc|nd)\b|non-?commercial|no derivatives", rights, re.I):
        print(f"   !! {ref}: rights '{rights}' not allowed"); return None
    if not any(h in q.get("image", "") for h in WEB_HOSTS[src]):
        print(f"   !! {ref}: image link is not on {WEB_HOSTS[src][0]}"); return None
    # sites behind a bot check (NLM uses an AWS WAF challenge): the image is downloaded by a person in a
    # normal browser and dropped into loc_exchange/inbox/<src>-<id>.jpg (we never try to pass the check)
    pid = ref.split(":", 2)[2]
    local = next((f for f in (sorted(INBOX.rglob(f"*{pid}*")) if INBOX.exists() else [])
                  if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".tif", ".tiff")), None)   # any name containing the id
    url = f"file://{local}" if local else q["image"]
    return {"source": src, "id": ref, "title": q.get("title", ref), "description": q.get("note", ""),
            "date": q.get("date", ""), "page_url": q.get("page_url", ""), "download_url": url,
            "license": rights[:80], "credit": q.get("credit") or src, "width": None, "height": None}


def _loc_by_lccn(lccn: str) -> dict | None:
    """loc:<LCCN> without an image link: take the Commons copy of that LoC item, if there is one."""
    from .archives import search_commons
    hits = [h for h in search_commons(f'"LCCN{lccn}" OR "{lccn}" insource:"loc.gov"', 10)
            if lccn in h["title"] or lccn in h.get("description", "")]
    if not hits:
        return None
    h = max(hits, key=lambda x: x.get("width") or 0)
    h["credit"] = f"Library of Congress, LCCN {lccn} (via Wikimedia Commons)"
    return h
