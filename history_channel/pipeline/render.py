"""Step 3: assemble the video.

Archive photos get slow Ken Burns motion and cross-dissolves, chapter cards come from the script,
every photo carries an on-screen source credit, subtitles (SRT) and YouTube chapters are generated
from the real narration timings.
"""
from __future__ import annotations

import json
import zlib
import random
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from .tts import SR

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "fonts"
GOLD = (201, 164, 92)
XF = 0.8          # cross-dissolve seconds
CARD = 3.2        # chapter card seconds
TITLE = 4.5       # title card seconds (after the cold open)
ENDCARD = 12.0    # end screen seconds (YouTube end-screen elements need 5-20s)


# ------------------------------------------------------------------ text helpers
def font(name, size, weight=None):
    f = ImageFont.truetype(str(FONTS / name), size)
    if weight:
        try:
            f.set_variation_by_axes([weight])
        except Exception:
            pass
    return f


def draw_tracked(d: ImageDraw.ImageDraw, xy, text, f, fill, tracking=0, anchor_center=True):
    """Letter-spaced text (PIL has no tracking)."""
    widths = [d.textlength(ch, font=f) for ch in text]
    total = sum(widths) + tracking * (len(text) - 1)
    x, y = xy
    if anchor_center:
        x -= total / 2
    for ch, w in zip(text, widths):
        d.text((x, y), ch, font=f, fill=fill)
        x += w + tracking
    return total


def wrap(d, text, f, max_w):
    """Greedy wrap to find the line count, then rebalance so lines have similar width (no orphans)."""
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
    if len(lines) == 2:
        best = min(range(1, len(words)), key=lambda k: max(d.textlength(" ".join(words[:k]), font=f),
                                                             d.textlength(" ".join(words[k:]), font=f)))
        lines = [" ".join(words[:best]), " ".join(words[best:])]
    return lines


# ------------------------------------------------------------------ canvases (4K, so motion stays sharp at 1080p)
def load_photo(path: Path) -> Image.Image:
    im = Image.open(path).convert("RGB")
    im = ImageOps.autocontrast(im, cutoff=0.4)   # old scans are often washed out
    return im


def make_canvas(im: Image.Image, W: int, H: int) -> tuple[Image.Image, bool]:
    """Returns (canvas, is_full_bleed). Wide images fill the frame; others sit on a blurred copy."""
    a = im.width / im.height
    if 1.42 <= a <= 2.3:
        return ImageOps.fit(im, (W, H), Image.LANCZOS, centering=(0.5, 0.42)), True
    bg = ImageOps.fit(im, (W // 8, H // 8), Image.BILINEAR).filter(ImageFilter.GaussianBlur(6))
    bg = bg.resize((W, H), Image.BILINEAR)
    bg = Image.eval(bg, lambda v: int(v * 0.38))
    fg = im.copy()
    fg.thumbnail((int(W * 0.94), int(H * 0.92)), Image.LANCZOS)
    # thin paper-like border + shadow to make it read as an archival object
    pad = max(6, fg.width // 160)
    framed = ImageOps.expand(fg, border=pad, fill=(232, 226, 212))
    shadow = Image.new("RGBA", (framed.width + 80, framed.height + 80), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rectangle([40, 50, framed.width + 40, framed.height + 50], fill=(0, 0, 0, 160))
    shadow = shadow.filter(ImageFilter.GaussianBlur(28))
    x, y = (W - framed.width) // 2, (H - framed.height) // 2
    bg.paste(shadow, (x - 40, y - 40), shadow)
    bg.paste(framed, (x, y))
    return bg, False


def card_canvas(bg_img: Image.Image | None, W, H, kicker, title, sub=None, big=False):
    if bg_img is not None:
        bg = ImageOps.fit(bg_img, (W // 6, H // 6), Image.BILINEAR).filter(ImageFilter.GaussianBlur(5)).resize((W, H))
        bg = Image.eval(ImageOps.grayscale(bg).convert("RGB"), lambda v: int(v * 0.26))
    else:
        bg = Image.new("RGB", (W, H), (14, 13, 12))
    d = ImageDraw.Draw(bg)
    s = W / 3840
    cy = H * 0.5
    tf = font("PlayfairDisplay.ttf", int((190 if big else 170) * s), 600)
    lines = wrap(d, title, tf, W * 0.78)
    lh = tf.size * 1.12
    block = lh * len(lines)
    y = cy - block / 2
    if kicker:
        kf = font("Oswald.ttf", int(62 * s), 500)
        draw_tracked(d, (W / 2, y - 150 * s), kicker.upper(), kf, GOLD, tracking=int(14 * s))
    for ln in lines:
        w = d.textlength(ln, font=tf)
        d.text(((W - w) / 2, y), ln, font=tf, fill=(244, 240, 230))
        y += lh
    d.line([(W / 2 - 110 * s, y + 75 * s), (W / 2 + 110 * s, y + 75 * s)], fill=GOLD, width=max(2, int(5 * s)))
    if sub:
        sf_ = font("EBGaramond-Italic.ttf", int(84 * s), 400)
        for i, ln in enumerate(wrap(d, sub, sf_, W * 0.7)):
            w = d.textlength(ln, font=sf_)
            d.text(((W - w) / 2, y + 125 * s + i * sf_.size * 1.2), ln, font=sf_, fill=(205, 198, 184))
    return bg


def credit_overlay(text: str, w: int, h: int) -> np.ndarray:
    """Small fixed caption, bottom-left. Returns BGRA uint8 strip."""
    s = h / 1080
    f = font("SourceSans3.ttf", int(28 * s), 500)
    im = Image.new("RGBA", (w, int(70 * s)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    text = text if len(text) <= 95 else text[:92] + "…"
    for dx, dy in ((2, 2), (1, 1)):
        d.text((int(44 * s) + dx, int(24 * s) + dy), text, font=f, fill=(0, 0, 0, 170))
    d.text((int(44 * s), int(24 * s)), text, font=f, fill=(236, 232, 222, 215))
    return cv2.cvtColor(np.array(im), cv2.COLOR_RGBA2BGRA)


SOURCE_NAMES = {"commons": "Wikimedia Commons", "loc": "Library of Congress", "wellcome": "Wellcome Collection"}


def credit_line(it: dict) -> str:
    if it["source"] == "loc":
        return it["credit"]
    lic = re.sub(r"\s+", " ", it.get("license", "")).strip()
    if it["source"] == "commons":
        who = it.get("credit", "")
        who = "" if (not who or "unknown" in who.lower() or len(who) > 50) else who + " · "
        return f"{who}Wikimedia Commons · {lic}"
    return f"{SOURCE_NAMES.get(it['source'], it['source'])} · {lic}"


# ------------------------------------------------------------------ timeline
@dataclass
class Shot:
    start: float
    end: float
    kind: str                 # photo | card
    file: str | None = None
    card: dict | None = None
    credit: str = ""
    seed: int = 0
    _canvas: np.ndarray | None = field(default=None, repr=False)
    full_bleed: bool = True


def build_timeline(ep_dir: Path, episode: dict, manifest: dict, timings: dict):
    shots, audio_marks, chapters = [], [], []
    t = 0.0
    first_bg = {}
    for scene in episode["scenes"]:
        imgs = [i for i in manifest["scenes"].get(scene["id"], []) if i["use"]]
        first_bg[scene["id"]] = imgs[0]["file"] if imgs else None

    for idx, scene in enumerate(episode["scenes"]):
        sid = scene["id"]
        imgs = [i for i in manifest["scenes"].get(sid, []) if i["use"]]
        if scene.get("chapter"):
            m = re.match(r"^([IVXLC]+)\.\s*(.+)$", scene["chapter"])
            kicker, title = (f"Chapter {m.group(1)}", m.group(2)) if m else ("", scene["chapter"])
            chapters.append((t, title))
            shots.append(Shot(t, t + CARD, "card", card={"bg": first_bg[sid], "kicker": kicker, "title": title,
                                                         "sub": scene.get("date")}, seed=zlib.crc32(sid.encode()) & 0xffff))
            t += CARD
        elif idx == 0:
            chapters.append((0.0, "Intro"))
        dur = timings[sid]["duration"]
        audio_marks.append((t, sid))
        if not imgs:
            raise SystemExit(f"scene '{sid}' has no images selected in manifest.json")
        # longer shots for fewer images, but never a single photo for more than ~14s
        n = len(imgs)
        reps = max(1, int(np.ceil(dur / (14.0 * n))))
        seq = (imgs * reps)[: max(n, int(np.ceil(dur / 14.0)))]
        step = dur / len(seq)
        for k, it in enumerate(seq):
            shots.append(Shot(t + k * step, t + (k + 1) * step, "photo", file=it["file"],
                              credit=credit_line(it), seed=(zlib.crc32(it["id"].encode()) + k) & 0xffff))
        t += dur
        if idx == 0:  # title card right after the cold open
            shots.append(Shot(t, t + TITLE, "card", card={"bg": first_bg[sid], "kicker": "",
                                                          "title": episode["title"], "sub": episode.get("subtitle"), "big": True}))
            t += TITLE
    shots.append(Shot(t, t + ENDCARD, "card", card={"bg": first_bg[episode["scenes"][-1]["id"]],
                                                    "kicker": episode.get("channel", ""), "title": "Thanks for watching",
                                                    "sub": "More stories from the archives"}))
    t += ENDCARD
    return shots, audio_marks, chapters, t


# ------------------------------------------------------------------ motion
def motion(shot: Shot, p: float, CW, CH):
    rnd = random.Random(shot.seed)
    if shot.kind == "card":
        z0, z1, (ax, ay), (bx, by) = 1.0, 1.035, (0.5, 0.5), (0.5, 0.5)
    else:
        zin = rnd.random() < 0.6
        zmax = 1.16 if shot.full_bleed else 1.10
        z0, z1 = (1.0, zmax) if zin else (zmax, 1.0)
        if shot.full_bleed:
            ax, ay = rnd.uniform(0.25, 0.75), rnd.uniform(0.3, 0.6)
            bx, by = rnd.uniform(0.25, 0.75), rnd.uniform(0.3, 0.6)
        else:
            ax, ay, bx, by = 0.5, 0.5, 0.5 + rnd.uniform(-0.04, 0.04), 0.5 + rnd.uniform(-0.04, 0.04)
    e = p * p * (3 - 2 * p)  # smoothstep easing
    z = z0 + (z1 - z0) * e
    fx, fy = ax + (bx - ax) * e, ay + (by - ay) * e
    hw, hh = CW / (2 * z), CH / (2 * z)
    cx = np.clip(fx * CW, hw, CW - hw)
    cy = np.clip(fy * CH, hh, CH - hh)
    return z, cx, cy


def render_frame(shot: Shot, t: float, W, H, CW, CH):
    span = (shot.end - shot.start) + XF
    p = np.clip((t - shot.start + XF / 2) / span, 0, 1)
    z, cx, cy = motion(shot, p, CW, CH)
    s = z * W / CW
    M = np.float32([[s, 0, W / 2 - s * cx], [0, s, H / 2 - s * cy]])
    return cv2.warpAffine(shot._canvas, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def prepare(shot: Shot, ep_dir: Path, CW, CH, cache: dict):
    if shot._canvas is not None:
        return
    if shot.kind == "photo":
        key = ("p", shot.file)
        if key not in cache:
            cv, fb = make_canvas(load_photo(ep_dir / shot.file), CW, CH)
            cache[key] = (cv2.cvtColor(np.array(cv), cv2.COLOR_RGB2BGR), fb)
        shot._canvas, shot.full_bleed = cache[key]
    else:
        c = shot.card
        bg = load_photo(ep_dir / c["bg"]) if c.get("bg") else None
        cv = card_canvas(bg, CW, CH, c.get("kicker"), c["title"], c.get("sub"), c.get("big", False))
        shot._canvas = cv2.cvtColor(np.array(cv), cv2.COLOR_RGB2BGR)


def vignette(W, H):
    y, x = np.ogrid[-1:1:H * 1j, -1:1:W * 1j]
    r = np.sqrt((x * 0.85) ** 2 + y ** 2)
    m = 1 - 0.42 * np.clip((r - 0.55) / 0.75, 0, 1) ** 1.6
    return (m * 256).astype(np.uint16)[..., None]


# ------------------------------------------------------------------ audio, subtitles, chapters
def build_audio(ep_dir, audio_marks, total, music: str | None):
    out = np.zeros(int(total * SR) + SR, np.float32)
    for t0, sid in audio_marks:
        a, _ = sf.read(ep_dir / "audio" / f"{sid}.wav", dtype="float32")
        i = int(t0 * SR)
        out[i:i + len(a)] += a
    if music:
        m, msr = sf.read(music, dtype="float32", always_2d=True)
        m = m.mean(axis=1)
        if msr != SR:
            x = np.linspace(0, len(m), int(len(m) * SR / msr), endpoint=False)
            m = np.interp(x, np.arange(len(m)), m).astype(np.float32)
        m = np.tile(m, int(np.ceil(len(out) / len(m))))[: len(out)]
        # duck under the voice
        env = np.abs(out)
        k = int(0.4 * SR)
        env = np.convolve(env, np.ones(k) / k, mode="same")
        gain = np.where(env > 0.01, 0.07, 0.16).astype(np.float32)
        gain = np.convolve(gain, np.ones(k) / k, mode="same")
        fade = np.ones_like(m)
        fade[: 2 * SR] = np.linspace(0, 1, 2 * SR)
        fade[-4 * SR:] = np.linspace(1, 0, 4 * SR)
        out += m * gain * fade
    peak = np.max(np.abs(out)) or 1
    out *= min(1.0, 0.89 / peak)
    path = ep_dir / "build" / "mix.wav"
    sf.write(path, out, SR)
    return path


def fmt_srt(t):
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s % 1) * 1000)):03d}".replace(",1000", ",999")


def write_srt(ep_dir, audio_marks, timings, path):
    cues = []
    for t0, sid in audio_marks:
        for s in timings[sid]["sentences"]:
            words = s["text"].split()
            n = max(1, -(-len(s["text"]) // 84))  # cues of <= ~84 chars (2 lines of 42), evenly sized
            per = len(s["text"]) / n
            parts, cur = [], []
            for w in words:
                cur.append(w)
                if len(parts) < n - 1 and len(" ".join(cur)) >= per:
                    parts.append(" ".join(cur))
                    cur = []
            if cur:
                parts.append(" ".join(cur))
            total_chars = sum(len(p) for p in parts)
            a = t0 + s["start"]
            for ptxt in parts:
                d = (s["end"] - s["start"]) * len(ptxt) / total_chars
                cues.append((a, a + d, ptxt))
                a += d
    with open(path, "w") as f:
        for i, (a, b, txt) in enumerate(cues, 1):
            f.write(f"{i}\n{fmt_srt(a)} --> {fmt_srt(b)}\n{txt}\n\n")


def fmt_ts(t):
    t = int(t)
    return f"{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}" if t >= 3600 else f"{t // 60}:{t % 60:02d}"


# ------------------------------------------------------------------ main
def render(ep_dir: Path, episode: dict, preview: bool = False):
    manifest = json.loads((ep_dir / "manifest.json").read_text())
    timings = json.loads((ep_dir / "audio" / "timings.json").read_text())
    build = ep_dir / "build"
    build.mkdir(exist_ok=True)
    W, H, FPS = (960, 540, 24) if preview else (1920, 1080, 30)
    CW, CH = (1920, 1080) if preview else (3840, 2160)

    shots, audio_marks, chapters, total = build_timeline(ep_dir, episode, manifest, timings)
    mix = build_audio(ep_dir, audio_marks, total, episode.get("music"))
    write_srt(ep_dir, audio_marks, timings, build / "subtitles.en.srt")
    (build / "chapters.txt").write_text("\n".join(f"{fmt_ts(a)} {b}" for a, b in chapters))
    (build / "timeline.json").write_text(json.dumps(
        [{"start": round(s.start, 2), "end": round(s.end, 2), "kind": s.kind, "file": s.file} for s in shots], indent=1))

    out = build / (f"{episode['slug']}_preview.mp4" if preview else f"{episode['slug']}.mp4")
    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", str(mix),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "24" if preview else "19", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", str(out)],
        stdin=subprocess.PIPE)

    vig = vignette(W, H)
    cache, credits = {}, {}
    nframes = int(total * FPS)
    cur = 0
    for fi in range(nframes):
        t = fi / FPS
        while cur < len(shots) - 1 and t >= shots[cur].end:
            shots[cur]._canvas = None
            cur += 1
        if len(cache) > 6:  # keep memory flat
            for k in list(cache)[:-4]:
                cache.pop(k)
        sh = shots[cur]
        prepare(sh, ep_dir, CW, CH, cache)
        frame = render_frame(sh, t, W, H, CW, CH)
        alpha_cur = 1.0
        nxt = shots[cur + 1] if cur + 1 < len(shots) else None
        if nxt and t > sh.end - XF / 2:
            prepare(nxt, ep_dir, CW, CH, cache)
            w = np.clip((t - (sh.end - XF / 2)) / XF, 0, 1)
            w = w * w * (3 - 2 * w)
            frame = cv2.addWeighted(frame, 1 - w, render_frame(nxt, t, W, H, CW, CH), w, 0)
            alpha_cur = 1 - w
        frame = ((frame.astype(np.uint16) * vig) >> 8).astype(np.uint8)
        # credits: fade in/out with their own shot
        for s_, a_ in ((sh, alpha_cur), (nxt, 1 - alpha_cur)):
            if s_ is None or s_.kind != "photo" or a_ <= 0.02 or not s_.credit:
                continue
            k = (s_.credit, W)
            if k not in credits:
                credits[k] = credit_overlay(s_.credit, W, H)
            ov = credits[k]
            fin = np.clip(min(t - s_.start - 0.6, s_.end - t - 0.2) / 0.6, 0, 1)
            a = (ov[..., 3:4].astype(np.float32) / 255) * a_ * fin
            if a.max() > 0:
                roi = frame[H - ov.shape[0]:H]
                roi[:] = (roi * (1 - a) + ov[..., :3] * a).astype(np.uint8)
        # fade in from / out to black
        fade = min(1.0, t / 0.8, (total - t) / 1.5)
        if fade < 1:
            frame = (frame * max(fade, 0)).astype(np.uint8)
        ff.stdin.write(frame.tobytes())
        if fi % (FPS * 30) == 0:
            print(f"   render {t / 60:5.1f} / {total / 60:.1f} min", flush=True)
    ff.stdin.close()
    ff.wait()
    print(f"video: {out}  ({total / 60:.1f} min)")
    return out, chapters, total
