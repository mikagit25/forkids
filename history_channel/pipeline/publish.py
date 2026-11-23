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
        def size(i):     # hand-picked LoC / web items carry no size in the manifest: read the file
            if not (i.get("width") and i.get("height")):
                i["width"], i["height"] = Image.open(ep_dir / i["file"]).size
            return i["width"], i["height"]
        hero = max(cands, key=lambda i: (size(i)[0] / max(size(i)[1], 1) >= 1.3, size(i)[0]))
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

    head = [episode.get("subtitle", ""), ""] + ([episode["summary"].strip(), ""] if episode.get("summary") else []) \
        + ["CHAPTERS", chapters, ""]
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


def youtube_client(episode: dict, client_secret: str = "client_secret.json"):
    """YouTube API client for the Archive Tales token; refuses any other channel."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    scopes = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.force-ssl"]
    tok = Path(__file__).resolve().parent.parent / "youtube_token.json"
    creds = Credentials.from_authorized_user_file(tok, scopes) if tok.exists() else None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            creds = InstalledAppFlow.from_client_secrets_file(client_secret, scopes).run_local_server(port=0)
        tok.write_text(creds.to_json())
    yt = build("youtube", "v3", credentials=creds)
    # never upload to the wrong channel: the token must belong to youtube_channel_id from channel.yaml
    # (until 11.2026 youtube_token.json here was a copy of the Sacred Drift token)
    want = episode.get("youtube_channel_id")
    me = yt.channels().list(part="snippet", mine=True).execute().get("items", [])
    have = me[0]["id"] if me else None
    if not want or have != want:
        raise SystemExit(f"   !! upload stopped: token belongs to {have} "
                         f"({me[0]['snippet']['title'] if me else '?'}), channel.yaml youtube_channel_id = {want}")
    return yt


def next_slot(root: Path, gap_days: int = 2, hour: int = 18):
    """Next long-video slot: every other day at 18:00 UTC, after the latest scheduled episode and >= 2 days ahead
    (time for the owner to review and switch it to a Premiere in YouTube Studio)."""
    import datetime as dt
    now = dt.datetime.now(dt.timezone.utc)
    when = (now + dt.timedelta(days=2)).replace(hour=hour, minute=0, second=0, microsecond=0)
    for f in (root / "episodes").glob("*/build/publish_at.txt"):
        last = dt.datetime.fromisoformat(f.read_text().strip().replace("Z", "+00:00"))
        when = max(when, last + dt.timedelta(days=gap_days))
    when = when.replace(hour=hour, minute=0, second=0)
    return when.strftime("%Y-%m-%dT%H:%M:%SZ")


def upload(ep_dir: Path, episode: dict, client_secret: str = "client_secret.json", publish_at: str | None = None,
           public: bool = False):
    """Uploads as PRIVATE with captions + thumbnail, scheduled to go public at publish_at (default: next free slot,
    every other day). The owner normally turns it into a Premiere in Studio; if not, it still goes public then."""
    from googleapiclient.http import MediaFileUpload

    yt = youtube_client(episode, client_secret)
    b = ep_dir / "build"
    body = {
        "snippet": {"title": episode["title"][:100], "description": (b / "description.txt").read_text()[:5000],
                    "tags": episode.get("tags", []), "categoryId": "27", "defaultLanguage": episode.get("language", "en"),
                    "defaultAudioLanguage": episode.get("language", "en")},
        "status": {"privacyStatus": "public" if public else "private", "selfDeclaredMadeForKids": False,
                   "containsSyntheticMedia": False},
    }
    if public:              # e.g. the weekly "100 Years Ago" episodes: straight to public, no slot
        publish_at = "none"
    if publish_at != "none":
        publish_at = publish_at or next_slot(ep_dir.parent.parent)
        body["status"]["publishAt"] = publish_at
    vid = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(str(b / f"{episode['slug']}.mp4"), resumable=True)).execute()["id"]
    if publish_at != "none":
        (b / "publish_at.txt").write_text(publish_at + "\n")
    try:
        yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(b / "thumbnail.jpg"))).execute()
    except Exception as e:
        print(f"   ! thumbnail upload skipped ({e.__class__.__name__}: {e}) — set manually in YouTube Studio")
    yt.captions().insert(part="snippet", body={"snippet": {"videoId": vid, "language": "en", "name": "English"}},
                         media_body=MediaFileUpload(str(b / "subtitles.en.srt"))).execute()
    (b / "youtube_id.txt").write_text(vid + "\n")      # Shorts link back to the full episode
    if episode.get("localizations"):
        localize(ep_dir, episode, client_secret, vid, yt)
    if public:
        print(f"uploaded as PUBLIC: https://youtu.be/{vid}")
    else:
        print(f"uploaded as PRIVATE: https://youtu.be/{vid}  goes public {publish_at} unless changed "
              f"(set it as a Premiere in YouTube Studio)")
    return vid


LOC_NOTE = {
    "es": "Todas las imágenes proceden de archivos públicos (dominio público o licencias abiertas). La lista completa con enlaces a los originales está en la descripción en inglés. Narración con voz sintética; guion documentado y verificado.",
    "pt": "Todas as imagens vêm de arquivos públicos (domínio público ou licenças abertas). A lista completa com links para os originais está na descrição em inglês. Narração com voz sintética; roteiro pesquisado e verificado.",
    "fr": "Toutes les images proviennent d'archives publiques (domaine public ou licences libres). La liste complète avec les liens vers les originaux figure dans la description en anglais. Narration par voix de synthèse ; scénario documenté et vérifié.",
    "de": "Alle Bilder stammen aus öffentlichen Archiven (gemeinfrei oder offen lizenziert). Die vollständige Liste mit Links zu den Originalen steht in der englischen Beschreibung. Erzählt mit synthetischer Stimme; Skript recherchiert und faktengeprüft.",
}
CH_WORD = {"es": "CAPÍTULOS", "pt": "CAPÍTULOS", "fr": "CHAPITRES", "de": "KAPITEL"}


def localize(ep_dir: Path, episode: dict, client_secret: str = "client_secret.json", vid: str | None = None, yt=None):
    """Title + description in other languages (episode.yaml `localizations:`), so YouTube shows the video in the
    viewer's language. Chapter names are translated in order; timestamps come from build/chapters.txt.
        localizations:
          es: {title: "...", subtitle: "...", summary: "...", chapters: ["Intro", "...", ...]}"""
    yt = yt or youtube_client(episode, client_secret)
    b = ep_dir / "build"
    vid = vid or (b / "youtube_id.txt").read_text().strip()
    stamps = [l.split(" ", 1)[0] for l in (b / "chapters.txt").read_text().splitlines() if l.strip()]
    cur = yt.videos().list(part="localizations,snippet", id=vid).execute()["items"][0]
    locs = cur.get("localizations", {}) or {}
    for lang, L in episode["localizations"].items():
        names = L.get("chapters") or []
        if len(names) != len(stamps):
            raise SystemExit(f"{lang}: {len(names)} chapter names for {len(stamps)} chapters")
        desc = "\n".join([L.get("subtitle", ""), "", L.get("summary", "").strip(), "", CH_WORD.get(lang, "CHAPTERS")]
                         + [f"{t} {n}" for t, n in zip(stamps, names)] + ["", LOC_NOTE.get(lang, "")]
                         + (["", " ".join(episode["hashtags"])] if episode.get("hashtags") else []))
        locs[lang] = {"title": L["title"][:100], "description": desc[:5000]}
        snip = cur["snippet"]
        body = {"id": vid, "localizations": locs,
                "snippet": {"title": snip["title"], "description": snip["description"], "categoryId": snip["categoryId"],
                            "defaultLanguage": snip.get("defaultLanguage", "en"), "tags": snip.get("tags", [])}}
        yt.videos().update(part="localizations,snippet", body=body).execute()   # one language per call (fewer 400s)
        print(f"   localized: {lang} — {L['title'][:70]}")
