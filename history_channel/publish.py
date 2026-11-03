"""Step 4: thumbnail, YouTube description (chapters + archive sources), optional upload as PRIVATE."""
from __future__ import annotations

import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageOps

from .render import GOLD, font, fmt_ts


def thumbnail(ep_dir: Path, episode: dict) -> Path:
    cfg = episode.get("thumbnail", {})
    man = json.loads((ep_dir / "manifest.json").read_text())
    used = [i for v in man["scenes"].values() for i in v if i["use"]]
    hero = next((i for i in used if i["id"] == cfg.get("image")), None)
    if not hero:
        scene = cfg.get("scene", episode["scenes"][0]["id"])
        cands = [i for i in man["scenes"].get(scene, []) if i["use"]] or used
        hero = max(cands, key=lambda i: (i["width"] / max(i["height"], 1) >= 1.3, i["width"]))
    W, H = 1280, 720
    im = Image.open(ep_dir / hero["file"]).convert("L")
    im = ImageOps.autocontrast(im, cutoff=1.5)
    im = ImageEnhance.Contrast(im).enhance(1.35).convert("RGB")
    im = ImageOps.fit(im, (W, H), Image.LANCZOS, centering=(0.68, 0.45))
    # dark gradient on the left for text
    grad = Image.new("L", (W, 1))
    for x in range(W):
        grad.putpixel((x, 0), int(235 * max(0, 1 - x / (W * 0.72)) ** 1.3))
    im.paste(Image.new("RGB", (W, H), (8, 8, 10)), (0, 0), grad.resize((W, H)))
    d = ImageDraw.Draw(im)
    big, small = cfg.get("big", "1918"), cfg.get("small", "THE FORGOTTEN PANDEMIC")
    fb = font("Oswald.ttf", 250, 700)
    d.text((58, 40), big, font=fb, fill=GOLD)
    fs = font("Oswald.ttf", 78, 600)
    y = 330
    for ln in small.split("\n") if "\n" in small else _wrap2(small):
        d.text((62, y), ln, font=fs, fill=(250, 248, 242))
        y += 92
    d.rectangle([62, y + 18, 230, y + 26], fill=(190, 40, 35))
    out = ep_dir / "build" / "thumbnail.jpg"
    im.save(out, "JPEG", quality=92)
    print(f"thumbnail: {out}")
    return out


def _wrap2(s):
    w = s.split()
    best = min(range(1, len(w)), key=lambda k: abs(len(" ".join(w[:k])) - len(" ".join(w[k:])))) if len(w) > 1 else 1
    return [" ".join(w[:best]), " ".join(w[best:])] if len(w) > 1 else [s]


def short_url(it: dict) -> str:
    if it["source"] == "commons" and it["id"].startswith("commons:"):
        return f"https://commons.wikimedia.org/?curid={it['id'].split(':', 1)[1]}"
    return it.get("page_url") or ""


def _short_title(t: str, n=60) -> str:
    t = re.sub(r"\s*\(.*?\)\s*", " ", t).strip(" ._-")
    return t if len(t) <= n else t[: n - 1].rsplit(" ", 1)[0] + "…"


def _image_index(ep_dir: Path):
    """Every photo in order of first appearance, with its timestamp in the video."""
    man = json.loads((ep_dir / "manifest.json").read_text())
    by_id = {i["id"]: i for v in man["scenes"].values() for i in v}
    tl = json.loads((ep_dir / "build" / "timeline.json").read_text())
    first, order = {}, []
    for s in tl:
        if s["kind"] == "photo" and s["id"] not in first:
            first[s["id"]] = s["start"]
            order.append(by_id[s["id"]])
    return order, first


def description(ep_dir: Path, episode: dict) -> Path:
    from .render import fmt_ts
    LIMIT = 5000
    chapters = (ep_dir / "build" / "chapters.txt").read_text().strip()
    order, first = _image_index(ep_dir)
    colorized = [i for i in order if i.get("colorize")]

    # full list for the archive: sources.md (can be published on your site and linked)
    md = [f"# Sources: {episode['title']}", "", "## Archive images (in order of appearance)", "",
          "| Time | Image | Archive | License | Link |", "|---|---|---|---|---|"]
    for n, i in enumerate(order, 1):
        md.append(f"| {fmt_ts(first[i['id']])} | {i['title'].replace('|', '/')}"
                  f"{' (shown original, then digitally colorized)' if i.get('colorize') else ''} | {i['credit'].replace('|', '/')} "
                  f"| {i['license']} | {i['page_url']} |")
    if episode.get("references"):
        md += ["", "## Research sources", ""] + [f"- {r}" for r in episode["references"]]
    (ep_dir / "build" / "sources.md").write_text("\n".join(md) + "\n")

    head = [episode.get("subtitle", ""), "", "CHAPTERS", chapters, ""]
    tail = []
    if episode.get("references"):
        tail += ["", "RESEARCH SOURCES"] + [f"• {r}" for r in episode["references"]]
    tail += ["", "Every image in this video comes from a public archive and is in the public domain or openly licensed.",
             "Each one is listed above with the time it appears and a link to the original, so you can check it yourself."]
    if colorized:
        tail += ["Colorized images are always shown in their original black and white first. Their colours are an "
                 "algorithmic estimate, not historical record."]
    tail += ["Narration uses a synthetic voice. Script researched and fact-checked by our team."]
    if episode.get("hashtags"):
        tail += ["", " ".join(episode["hashtags"])]
    src_url = episode.get("sources_url")  # optional: where sources.md is published (e.g. your site)

    def build_list(title_len):
        out = ["ARCHIVE IMAGES (time · image · license · original)"]
        for i in order:
            lic = re.sub(r"\s+", " ", i["license"])[:28]
            col = " [colorized]" if i.get("colorize") else ""
            out.append(f"{fmt_ts(first[i['id']])} {_short_title(i['title'], title_len)}{col} · {lic} · {short_url(i)}")
        return out

    for title_len in (60, 45, 32, 22):
        lines = head + build_list(title_len) + tail
        text = "\n".join(lines)
        if len(text) <= LIMIT:
            break
    else:  # still too long: keep links only for what fits and point to the full list
        lst = build_list(22)
        more = [f"Full list of all {len(order)} images with links: {src_url}" if src_url else
                "Full list of all images with links: see the pinned comment."]
        while len("\n".join(head + lst + more + tail)) > LIMIT and len(lst) > 2:
            lst.pop()
        text = "\n".join(head + lst + more + tail)
    out = ep_dir / "build" / "description.txt"
    out.write_text(text)
    print(f"description: {out} ({len(text)} chars, {len(order)} images listed; YouTube limit {LIMIT})")
    print(f"sources:     {ep_dir / 'build' / 'sources.md'}")
    return out


def upload(ep_dir: Path, episode: dict, client_secret: str = "client_secret.json"):
    """Uploads as PRIVATE with captions + thumbnail. Needs a Google Cloud OAuth client (YouTube Data API v3)."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    scopes = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.force-ssl"]
    tok = Path("youtube_token.json")
    creds = Credentials.from_authorized_user_file(tok, scopes) if tok.exists() else None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            creds = InstalledAppFlow.from_client_secrets_file(client_secret, scopes).run_local_server(port=0)
        tok.write_text(creds.to_json())
    yt = build("youtube", "v3", credentials=creds)
    b = ep_dir / "build"
    body = {
        "snippet": {"title": episode["title"][:100], "description": (b / "description.txt").read_text()[:5000],
                    "tags": episode.get("tags", []), "categoryId": "27", "defaultLanguage": episode.get("language", "en"),
                    "defaultAudioLanguage": episode.get("language", "en")},
        "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False, "containsSyntheticMedia": False},
    }
    vid = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(str(b / f"{episode['slug']}.mp4"), resumable=True)).execute()["id"]
    yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(b / "thumbnail.jpg"))).execute()
    yt.captions().insert(part="snippet", body={"snippet": {"videoId": vid, "language": "en", "name": "English"}},
                         media_body=MediaFileUpload(str(b / "subtitles.en.srt"))).execute()
    print(f"uploaded as PRIVATE: https://youtu.be/{vid}  (review, then publish in YouTube Studio)")
    return vid
