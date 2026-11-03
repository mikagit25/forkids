"""Review pack: contact-sheet images of every candidate photo, small enough to commit to git.

    python run.py episodes/1918-flu review     -> episodes/1918-flu/review/sheet_01.jpg, ...
    bash share_review.sh 1918-flu              -> commits sheets + manifest.json and pushes

Claude (or a person) can then look at the sheets in the repo and change the picks in manifest.json:
each tile shows a number; "picks" lists those numbers per scene.
"""
from __future__ import annotations

import json
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

from .render import font

TW, TH = 300, 200   # tile size
COLS = 6


def review_pack(ep_dir: Path, episode: dict):
    man = json.loads((ep_dir / "manifest.json").read_text())
    out = ep_dir / "review"
    out.mkdir(exist_ok=True)
    for old in out.glob("sheet_*.jpg"):
        old.unlink()
    f_title = font("SourceSans3.ttf", 22, 700)
    f_txt = font("SourceSans3.ttf", 15, 500)
    rows, index = [], {}
    n = 0
    for scene in episode["scenes"]:
        items = man["scenes"].get(scene["id"], [])
        label = f"{scene['id']}  {scene.get('chapter', '')}"
        rows.append(("head", label, textwrap.shorten(scene["narration"], 230)))
        line = []
        for it in items:
            n += 1
            index[n] = it["id"]
            line.append((n, it))
            if len(line) == COLS:
                rows.append(("tiles", line))
                line = []
        if line:
            rows.append(("tiles", line))
    # paginate into sheets of ~1900 px height
    pages, cur, h = [], [], 0
    for r in rows:
        rh = 64 if r[0] == "head" else TH + 46
        if h + rh > 1900 and cur:
            pages.append(cur)
            cur, h = [], 0
        cur.append(r)
        h += rh
    if cur:
        pages.append(cur)
    W = COLS * (TW + 8) + 8
    for pi, page in enumerate(pages, 1):
        H = sum(64 if r[0] == "head" else TH + 46 for r in page) + 8
        im = Image.new("RGB", (W, H), (18, 18, 18))
        d = ImageDraw.Draw(im)
        y = 4
        for r in page:
            if r[0] == "head":
                d.text((10, y + 4), r[1], font=f_title, fill=(230, 200, 120))
                d.text((10, y + 34), r[2][:170], font=f_txt, fill=(170, 170, 170))
                y += 64
                continue
            for k, (num, it) in enumerate(r[1]):
                x = 8 + k * (TW + 8)
                try:
                    t = ImageOps.fit(Image.open(ep_dir / it["file"]).convert("RGB"), (TW, TH))
                except Exception:
                    t = Image.new("RGB", (TW, TH), (60, 0, 0))
                im.paste(t, (x, y))
                col = (60, 200, 110) if it["use"] else (90, 90, 90)
                d.rectangle([x - 2, y - 2, x + TW + 1, y + TH + 1], outline=col, width=3)
                d.rectangle([x, y, x + 52, y + 26], fill=(0, 0, 0))
                d.text((x + 6, y + 3), f"#{num}", font=f_title, fill=col)
                cap = f"{'USE' if it['use'] else 'alt'} s={it.get('score', '-')} {it['title']}"
                d.text((x, y + TH + 4), cap[:44], font=f_txt, fill=(210, 210, 210))
                d.text((x, y + TH + 23), it["query"][:44], font=f_txt, fill=(130, 130, 130))
            y += TH + 46
        im.save(out / f"sheet_{pi:02d}.jpg", quality=80)
    (out / "index.json").write_text(json.dumps(index, indent=0))
    print(f"review: {len(pages)} sheets, {n} photos -> {out}")


def apply_picks(ep_dir: Path, picks: dict[str, list[int]]):
    """picks = {"scene-id": [3, 5, 9]} using the tile numbers from the sheets."""
    man_path = ep_dir / "manifest.json"
    man = json.loads(man_path.read_text())
    index = {int(k): v for k, v in json.loads((ep_dir / "review" / "index.json").read_text()).items()}
    for sid, nums in picks.items():
        ids = {index[n] for n in nums}
        for it in man["scenes"].get(sid, []):
            it["use"] = it["id"] in ids
    man_path.write_text(json.dumps(man, indent=2, ensure_ascii=False))
