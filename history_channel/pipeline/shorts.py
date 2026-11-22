"""Vertical Shorts cut from a finished episode (same narration, music and photos — no new voice).

Which moments become Shorts is decided by hand in episode.yaml (like the photo framing), from the numbered
sentences of build/subtitles.en.srt:

    shorts:
      - {from: 1, to: 9, hook: "The parade that killed thousands", title: "Philadelphia's Deadly Parade, 1918"}

    python run.py episodes/<ep> shorts --suggest   # numbered sentences per scene with times -> pick windows
    python run.py episodes/<ep> shorts             # render build/shorts/short_N.mp4 + meta (needs a finished render)
    python run.py episodes/<ep> shorts-upload      # upload them PRIVATE, scheduled (needs build/youtube_id.txt)

Layout 1080x1920: blurred copy of the picture fills the frame, the photo itself sits large in the middle (whole
photo, never cropped), slow zoom; hook text at the top, burned-in captions below, the last seconds point to the
full story. Audio = the episode mix for the same window, with fades. Length is kept under 60 s.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "fonts"
W, H, FPS = 1080, 1920, 30
MAX_LEN = 59.0
OUTRO = 2.6                       # last seconds: "full story" line instead of captions
GOLD = (201, 164, 92)


def _font(name, size, weight=None):
    f = ImageFont.truetype(str(FONTS / name), size)
    if weight:
        try:
            f.set_variation_by_axes([weight])
        except Exception:
            pass
    return f


def read_srt(path: Path):
    out = []
    for block in path.read_text().strip().split("\n\n"):
        lines = block.strip().splitlines()
        if len(lines) < 3:
            continue
        a, b = lines[1].split(" --> ")
        sec = lambda s: int(s[:2]) * 3600 + int(s[3:5]) * 60 + int(s[6:8]) + int(s[9:12]) / 1000
        out.append({"n": int(lines[0]), "start": sec(a), "end": sec(b), "text": " ".join(lines[2:])})
    return out


def suggest(ep_dir: Path):
    """Print numbered sentences grouped by the timeline's chapter cards, so windows can be chosen by eye."""
    b = ep_dir / "build"
    subs = read_srt(b / "subtitles.en.srt")
    cards = [x["start"] for x in json.loads((b / "timeline.json").read_text()) if x["kind"] == "card"]
    ci = 0
    for s in subs:
        while ci < len(cards) and cards[ci] <= s["start"]:
            print(f"\n----- card at {cards[ci]:.0f}s -----")
            ci += 1
        print(f"{s['n']:3d}  {s['start']:7.1f}–{s['end']:7.1f}  ({s['end'] - s['start']:4.1f}s)  {s['text']}")


def _wrap(d, text, f, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _chunks(sub, t0):
    """Split a sentence into caption chunks of <= 4 words, timed by character count (no word timings)."""
    words = sub["text"].split()
    groups, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= 4 or re.search(r"[,.;:!?]$", w) and len(cur) >= 2:
            groups.append(cur)
            cur = []
    if cur:
        if groups and len(cur) == 1:
            groups[-1] += cur
        else:
            groups.append(cur)
    total = sum(len(" ".join(g)) + 1 for g in groups)
    t, out = sub["start"] - t0, []
    span = sub["end"] - sub["start"]
    for g in groups:
        d = span * (len(" ".join(g)) + 1) / total
        out.append((t, t + d, " ".join(g)))
        t += d
    return out


def _still(ep_dir: Path, item: dict, manifest_files: dict, video: Path, cache: dict) -> Image.Image:
    """Source picture for a timeline item: the photo file itself, or (cards/maps/quotes) a frame of the episode."""
    key = item.get("id") or f"frame@{item['start']:.2f}"
    if key in cache:
        return cache[key]
    p = manifest_files.get(item.get("id")) if item.get("kind") == "photo" else None
    if p and (ep_dir / p).exists():
        img = Image.open(ep_dir / p).convert("RGB")
    else:
        t = (item["start"] + item["end"]) / 2
        raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1",
                              "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True, check=True).stdout
        import io
        img = Image.open(io.BytesIO(raw)).convert("RGB")
    cache[key] = img
    return img


def _layers(img: Image.Image, whole: bool = False):
    """Blurred, darkened background filling 9:16 + the whole photo fitted into the central area.
    whole=True (cards, maps, quotes rendered as episode frames): fit the entire frame to the width, no pan,
    so a number or a map route is never cut in half."""
    iw, ih = img.size
    s = max(W / iw, H / ih)
    bg = img.resize((int(iw * s) + 1, int(ih * s) + 1), Image.BILINEAR)
    bx, by = (bg.width - W) // 2, (bg.height - H) // 2
    bg = bg.crop((bx, by, bx + W, by + H)).filter(ImageFilter.GaussianBlur(38))
    bg = Image.blend(bg, Image.new("RGB", (W, H), (0, 0, 0)), 0.55)
    box_w, box_h = W - 60, 1180                         # photo area between hook (top) and captions (bottom)
    f = min(box_w / iw, box_h / ih)
    if whole:
        f = min(W / iw, box_h / ih)
    elif iw > ih * 1.05:                                # landscape: show it big and pan across the whole width
        f = max(f, min(1000 / ih, 1.9 * W / iw))
    fg = img.resize((max(1, int(iw * f)), max(1, int(ih * f))), Image.LANCZOS)
    return bg, fg


def _render_short(ep_dir: Path, spec: dict, idx: int, subs, timeline, manifest_files, video: Path, mix: Path,
                  out: Path, channel: str):
    by_n = {s["n"]: s for s in subs}
    s0, s1 = by_n[spec["from"]], by_n[spec["to"]]
    t0 = max(0.0, s0["start"] - 0.25)
    t1 = min(s1["end"] + 0.9, t0 + MAX_LEN)
    dur = t1 - t0
    seg_subs = [s for s in subs if s0["n"] <= s["n"] <= s1["n"] and s["start"] < t1]
    caps = [c for s in seg_subs for c in _chunks(s, t0)]
    shots = [x for x in timeline if x["end"] > t0 and x["start"] < t1]
    if not shots:
        raise SystemExit(f"short {idx}: no pictures between {t0:.1f}s and {t1:.1f}s")

    hook_f = _font("Oswald.ttf", 82, 600)
    cap_f = _font("Oswald.ttf", 74, 600)
    small_f = _font("SourceSans3.ttf", 40, 600)
    d0 = ImageDraw.Draw(Image.new("RGB", (W, H)))
    hook_lines = _wrap(d0, spec["hook"].upper(), hook_f, W - 120)[:3]

    cache, layers = {}, {}
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-ss", f"{t0:.3f}", "-t", f"{dur:.3f}",
                             "-i", str(mix), "-map", "0:v:0", "-map", "1:a:0",
                             "-af", f"afade=t=in:d=0.25,afade=t=out:st={dur - 1.0:.2f}:d=1.0,aresample=48000",
                             "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                             "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out)],
                            stdin=subprocess.PIPE)
    n = int(dur * FPS)
    for fi in range(n):
        t = t0 + fi / FPS
        cur = next((x for x in shots if x["start"] <= t < x["end"]), shots[-1])
        k = id(cur)
        if k not in layers:
            whole = cur.get("kind") != "photo" or not manifest_files.get(cur.get("id"))
            layers[k] = _layers(_still(ep_dir, cur, manifest_files, video, cache), whole=whole)
        bg, fg = layers[k]
        p = (t - max(cur["start"], t0)) / max(0.5, min(cur["end"], t1) - max(cur["start"], t0))
        p = min(max(p, 0), 1)
        frame = bg.copy()
        cx, cy = W // 2, 960
        if fg.width > W:                                  # wide photo: pan left -> right, every part is seen
            e = p * p * (3 - 2 * p)
            x = int((fg.width - W) * e)
            frame.paste(fg.crop((x, 0, x + W, fg.height)), (0, cy - fg.height // 2))
        else:
            z = 1.0 + 0.06 * p                            # slow push-in, whole photo stays visible at start
            fw, fh = int(fg.width * z), int(fg.height * z)
            im = fg.resize((fw, fh), Image.BILINEAR)
            # crop the zoomed photo back to its unzoomed box so it never grows over the text
            bw, bh = fg.width, fg.height
            im = im.crop(((fw - bw) // 2, (fh - bh) // 2, (fw - bw) // 2 + bw, (fh - bh) // 2 + bh))
            frame.paste(im, (cx - bw // 2, cy - bh // 2))
        # crossfade into the previous shot during the first 0.25 s
        if t - cur["start"] < 0.25 and cur is not shots[0]:
            prev = shots[shots.index(cur) - 1]
            pk = id(prev)
            if pk in layers:
                pbg, pfg = layers[pk]
                pf = pbg.copy()
                if pfg.width > W:                         # previous wide photo ended its pan at the right edge
                    pf.paste(pfg.crop((pfg.width - W, 0, pfg.width, pfg.height)), (0, cy - pfg.height // 2))
                else:
                    pf.paste(pfg, (cx - pfg.width // 2, cy - pfg.height // 2))
                frame = Image.blend(pf, frame, (t - cur["start"]) / 0.25)
        d = ImageDraw.Draw(frame)
        # hook (top)
        y = 150
        for line in hook_lines:
            d.text((W // 2, y), line, font=hook_f, fill=(255, 255, 255), anchor="mt", stroke_width=5,
                   stroke_fill=(0, 0, 0))
            y += 96
        d.text((W // 2, y + 10), channel.upper(), font=small_f, fill=GOLD, anchor="mt", stroke_width=3,
               stroke_fill=(0, 0, 0))
        # captions / outro (bottom)
        rel = t - t0
        if rel > dur - OUTRO:
            d.text((W // 2, 1640), "FULL STORY ON THE CHANNEL", font=cap_f, fill=GOLD, anchor="mm", stroke_width=5,
                   stroke_fill=(0, 0, 0))
        else:
            c = next((c for c in caps if c[0] <= rel < c[1]), None)
            if c:
                yy = 1600
                for line in _wrap(d, c[2], cap_f, W - 140)[:2]:
                    d.text((W // 2, yy), line, font=cap_f, fill=(255, 255, 255), anchor="mm", stroke_width=6,
                           stroke_fill=(0, 0, 0))
                    yy += 88
        proc.stdin.write(np.asarray(frame, dtype=np.uint8).tobytes())
    proc.stdin.close()
    if proc.wait() != 0:
        raise SystemExit(f"short {idx}: ffmpeg failed")
    return dur, " ".join(s["text"] for s in seg_subs)


def build(ep_dir: Path, episode: dict, only: list[int] | None = None):
    specs = episode.get("shorts") or []
    if not specs:
        raise SystemExit("no `shorts:` in episode.yaml — run `shorts --suggest` and pick sentence windows")
    b = ep_dir / "build"
    video, mix = b / f"{episode['slug']}.mp4", b / "mix.wav"
    for p in (video, mix, b / "subtitles.en.srt", b / "timeline.json"):
        if not p.exists():
            raise SystemExit(f"{p} missing — render the episode first")
    subs = read_srt(b / "subtitles.en.srt")
    timeline = json.loads((b / "timeline.json").read_text())
    man = json.loads((ep_dir / "manifest.json").read_text())
    files = {it["id"]: it["file"] for items in man["scenes"].values() for it in items if it.get("file")}
    out_dir = b / "shorts"
    out_dir.mkdir(exist_ok=True)
    full_id = (b / "youtube_id.txt").read_text().strip() if (b / "youtube_id.txt").exists() else None
    tags = [h.lstrip("#") for h in episode.get("hashtags", [])]
    for i, spec in enumerate(specs, 1):
        if only and i not in only:
            continue
        out = out_dir / f"short_{i}.mp4"
        print(f"short {i}: sentences {spec['from']}–{spec['to']} …")
        dur, text = _render_short(ep_dir, spec, i, subs, timeline, files, video, mix, out,
                                  episode.get("channel", "Archive Tales"))
        title = f"{spec['title']} #Shorts"
        link = f"https://youtu.be/{full_id}" if full_id else "[link to the full episode]"
        desc = (f"{text}\n\nFull story: {episode['title']}\n▶ {link}\n\n"
                f"Archive photographs from public collections (Wikimedia Commons, Library of Congress and others); "
                f"full credits in the description of the full episode.\n\n"
                + " ".join(episode.get("hashtags", [])) + " #shorts #history")
        meta = {"title": title[:100], "description": desc, "tags": tags + ["history", "shorts", "archive photos"],
                "duration_sec": round(dur, 1), "from": spec["from"], "to": spec["to"], "full_video": full_id}
        (out_dir / f"short_{i}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
        print(f"   {out}  {dur:.1f}s  title: {title}")


def upload(ep_dir: Path, episode: dict, start: str, every_hours: float = 24.0):
    """Upload rendered Shorts as PRIVATE with publishAt = start, start+every_hours, … (UTC ISO)."""
    import datetime as dt
    from googleapiclient.http import MediaFileUpload
    from .publish import youtube_client
    yt = youtube_client(episode)
    out_dir = ep_dir / "build" / "shorts"
    when = dt.datetime.fromisoformat(start.replace("Z", "+00:00"))
    for mp4 in sorted(out_dir.glob("short_*.mp4"), key=lambda p: int(p.stem.split("_")[1])):
        mp = mp4.with_suffix(".json")
        meta = json.loads(mp.read_text())
        if meta.get("youtube_id"):
            print(f"   {mp4.name}: already uploaded ({meta['youtube_id']})")
            continue
        body = {"snippet": {"title": meta["title"], "description": meta["description"][:5000], "tags": meta["tags"],
                            "categoryId": "27", "defaultLanguage": "en", "defaultAudioLanguage": "en"},
                "status": {"privacyStatus": "private", "publishAt": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
                           "selfDeclaredMadeForKids": False, "containsSyntheticMedia": False}}
        vid = yt.videos().insert(part="snippet,status", body=body,
                                 media_body=MediaFileUpload(str(mp4), resumable=True)).execute()["id"]
        meta["youtube_id"], meta["publish_at"] = vid, body["status"]["publishAt"]
        mp.write_text(json.dumps(meta, ensure_ascii=False, indent=1))
        print(f"   {mp4.name} -> https://youtu.be/{vid}  scheduled {meta['publish_at']}")
        when += dt.timedelta(hours=every_hours)


def daily(root: Path, episode_defaults: dict, at_hour: int = 16, per_day: int = 1):
    """Cron: upload the next `per_day` rendered Shorts (oldest episode first), scheduled today at at_hour UTC
    (tomorrow if that time has passed). Only for episodes whose full video is uploaded (build/youtube_id.txt).
    One upload costs ~1600 API units of the quota shared with MedMind Arabic, so keep per_day small."""
    import datetime as dt
    import yaml
    from googleapiclient.http import MediaFileUpload
    from .publish import youtube_client
    pending = []
    for ep_dir in sorted((root / "episodes").iterdir()):
        b = ep_dir / "build"
        if not (b / "youtube_id.txt").exists() or not (b / "shorts").exists():
            continue
        for mp in sorted((b / "shorts").glob("short_*.json"), key=lambda p: int(p.stem.split("_")[1])):
            meta = json.loads(mp.read_text())
            if not meta.get("youtube_id") and mp.with_suffix(".mp4").exists():
                pending.append((b.stat().st_mtime, ep_dir, mp, meta))
    if not pending:
        print("no Shorts waiting")
        return
    pending.sort(key=lambda x: (str(x[1]), int(x[2].stem.split("_")[1])))
    now = dt.datetime.now(dt.timezone.utc)
    when = now.replace(hour=at_hour, minute=0, second=0, microsecond=0)
    if when < now + dt.timedelta(minutes=30):
        when += dt.timedelta(days=1)
    yt = youtube_client({**episode_defaults})
    def _full_at(ep_dir):                                 # a Short must not go out before its full episode
        f = ep_dir / "build" / "publish_at.txt"
        if not f.exists():
            return None
        return dt.datetime.strptime(f.read_text().strip(), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
    pending = [x for x in pending if not _full_at(x[1]) or _full_at(x[1]) <= when]
    if not pending:
        print("Shorts are waiting for their full episodes to go public")
        return
    for _, ep_dir, mp, meta in pending[:per_day]:
        full_at = _full_at(ep_dir)
        if full_at and full_at > when:
            continue
        full = (ep_dir / "build" / "youtube_id.txt").read_text().strip()
        meta["description"] = meta["description"].replace("[link to the full episode]", f"https://youtu.be/{full}")
        body = {"snippet": {"title": meta["title"], "description": meta["description"][:5000], "tags": meta["tags"],
                            "categoryId": "27", "defaultLanguage": "en", "defaultAudioLanguage": "en"},
                "status": {"privacyStatus": "private", "publishAt": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
                           "selfDeclaredMadeForKids": False, "containsSyntheticMedia": False}}
        vid = yt.videos().insert(part="snippet,status", body=body,
                                 media_body=MediaFileUpload(str(mp.with_suffix(".mp4")), resumable=True)).execute()["id"]
        meta["youtube_id"], meta["publish_at"] = vid, body["status"]["publishAt"]
        mp.write_text(json.dumps(meta, ensure_ascii=False, indent=1))
        print(f"{ep_dir.name}/{mp.stem} -> https://youtu.be/{vid}  scheduled {meta['publish_at']}")
        when += dt.timedelta(hours=24 / per_day)
