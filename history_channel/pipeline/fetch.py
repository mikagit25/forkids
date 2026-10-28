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

from PIL import Image

from .archives import SESSION, search_all

ALTERNATES = 3  # extra candidates kept per query for the reviewer


def _download(c: dict, media: Path) -> Path | None:
    name = c["id"].replace(":", "_") + "_" + hashlib.md5(c["download_url"].encode()).hexdigest()[:6] + ".jpg"
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


def fetch(ep_dir: Path, episode: dict, refresh: bool = False):
    media = ep_dir / "media"
    media.mkdir(exist_ok=True)
    man_path = ep_dir / "manifest.json"
    old = json.loads(man_path.read_text()) if man_path.exists() and not refresh else {}
    manifest = {"scenes": {}}
    seen: set[str] = set()

    # keep reviewer choices from a previous run
    for sid, items in old.get("scenes", {}).items():
        for it in items:
            seen.add(it["id"])

    for scene in episode["scenes"]:
        sid = scene["id"]
        if sid in old.get("scenes", {}) and all((ep_dir / i["file"]).exists() for i in old["scenes"][sid]):
            manifest["scenes"][sid] = old["scenes"][sid]
            print(f"[{sid}] kept {sum(i['use'] for i in old['scenes'][sid])} images from previous run")
            continue
        chosen = []
        for q in scene.get("images", []):
            want = q.get("count", 1)
            print(f"[{sid}] searching: {q['query']}")
            cands = search_all(q["query"], q.get("sources", ("commons", "wellcome", "loc")))
            got = 0
            for c in cands:
                if c["id"] in seen:
                    continue
                if got >= want + ALTERNATES:
                    break
                path = _download(c, media)
                if not path:
                    continue
                seen.add(c["id"])
                c["file"] = str(path.relative_to(ep_dir))
                c["use"] = got < want
                c["query"] = q["query"]
                chosen.append(c)
                got += 1
            if got < want:
                print(f"   ! only {got}/{want} usable images for '{q['query']}' - consider another query")
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
              <figcaption><b>{badge}</b> · {html.escape(it['id'])}<br>
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
