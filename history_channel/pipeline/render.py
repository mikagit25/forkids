"""Step 3: assemble the video.

- Archive photos move with 2.5D parallax: a depth map (Depth Anything V2 Small) shifts near and far
  parts of the *same* pixels at different speeds. Nothing is painted in. Falls back to Ken Burns if
  the depth model is not installed.
- Shots marked `colorize` show the authentic black-and-white photo first, then dissolve to a
  colorized version; the on-screen credit then says "Digitally colorized".
- Quote cards show a primary-source quote while the narrator reads it.
- Chapter cards, title card, end card, on-screen source credit for every photo.
- Subtitles (SRT), YouTube chapters and a timeline of which photo appears when (for the description).
"""
from __future__ import annotations

import json
import random
import re
import subprocess
import zlib
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from . import vision
from .tts import SR

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "fonts"
GOLD = (201, 164, 92)
XF = 0.8          # cross-dissolve seconds
CARD = 3.2        # chapter card seconds
TITLE = 4.5       # title card seconds (after the cold open)
ENDCARD = 12.0    # end screen seconds (YouTube end-screen elements need 5-20s)
MAX_SHOT = 13.0   # longest time one photo stays on screen


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
    """Greedy wrap to find the line count, then rebalance two-line titles (no orphans)."""
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


# ------------------------------------------------------------------ photo canvases (4K, so motion stays sharp at 1080p)
def load_rgb(path: Path, autocontrast=True) -> np.ndarray:
    im = Image.open(path).convert("RGB")
    if autocontrast:
        im = ImageOps.autocontrast(im, cutoff=0.4)   # old scans are often washed out
    return np.array(im)


def layout(w, h, CW, CH):
    a = w / h
    if 1.42 <= a <= 2.3:                              # wide: fill the frame
        s = max(CW / w, CH / h)
        nw, nh = round(w * s), round(h * s)
        return {"fill": True, "nw": nw, "nh": nh, "ox": int((nw - CW) * 0.5), "oy": int((nh - CH) * 0.42)}
    s = min(CW * 0.92 / w, CH * 0.90 / h)             # otherwise: framed print on a blurred copy
    nw, nh = round(w * s), round(h * s)
    return {"fill": False, "nw": nw, "nh": nh, "x": (CW - nw) // 2, "y": (CH - nh) // 2}


def photo_canvas(rgb: np.ndarray, L, CW, CH) -> np.ndarray:
    if L["fill"]:
        r = cv2.resize(rgb, (L["nw"], L["nh"]), interpolation=cv2.INTER_CUBIC)
        return np.ascontiguousarray(r[L["oy"]:L["oy"] + CH, L["ox"]:L["ox"] + CW])
    bg = cv2.resize(rgb, (CW // 8, CH // 8), interpolation=cv2.INTER_AREA)
    bg = cv2.GaussianBlur(bg, (0, 0), 6)
    bg = (cv2.resize(bg, (CW, CH), interpolation=cv2.INTER_LINEAR) * 0.38).astype(np.float32)
    x, y, nw, nh = L["x"], L["y"], L["nw"], L["nh"]
    pad = max(6, nw // 160)
    # soft shadow
    sh = np.zeros((CH, CW), np.float32)
    sh[y - pad + 40:y + nh + pad + 40, x - pad + 20:x + nw + pad + 20] = 0.65
    sh = cv2.GaussianBlur(sh, (0, 0), 28)
    bg *= (1 - sh)[..., None]
    bg[y - pad:y + nh + pad, x - pad:x + nw + pad] = (232, 226, 212)   # paper-like border
    bg[y:y + nh, x:x + nw] = cv2.resize(rgb, (nw, nh), interpolation=cv2.INTER_AREA if nw < rgb.shape[1] else cv2.INTER_CUBIC)
    return bg.clip(0, 255).astype(np.uint8)


def depth_canvas(d: np.ndarray, L, CW, CH) -> np.ndarray:
    if L["fill"]:
        r = cv2.resize(d, (L["nw"], L["nh"]), interpolation=cv2.INTER_LINEAR)
        return np.ascontiguousarray(r[L["oy"]:L["oy"] + CH, L["ox"]:L["ox"] + CW])
    x, y, nw, nh = L["x"], L["y"], L["nw"], L["nh"]
    inner = 0.25 + 0.75 * cv2.resize(d, (nw, nh), interpolation=cv2.INTER_LINEAR)
    c = np.full((CH, CW), 0.15, np.float32)
    c[y:y + nh, x:x + nw] = float(np.median(inner))   # the print moves as one flat plane...
    c = cv2.GaussianBlur(c, (0, 0), 20)
    m = np.zeros((CH, CW), np.float32)
    m[y + 60:y + nh - 60, x + 60:x + nw - 60] = 1
    m = cv2.GaussianBlur(m, (0, 0), 30)                # ...with depth inside, feathered to its edges
    full = c.copy()
    full[y:y + nh, x:x + nw] = inner
    return (m * full + (1 - m) * c).astype(np.float32)


def quote_canvas(W, H, text, source):
    """Aged-paper card with the quote, for primary-source citations."""
    rng = np.random.default_rng(zlib.crc32(text.encode()))
    paper = np.empty((H, W, 3), np.float32)
    paper[:] = (226, 214, 188)
    n = cv2.resize(rng.normal(0, 1, (H // 16, W // 16)).astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC)
    n2 = rng.normal(0, 1, (H, W)).astype(np.float32)
    paper += (n * 9 + n2 * 4)[..., None]
    y, x = np.ogrid[-1:1:H * 1j, -1:1:W * 1j]
    paper *= (1 - 0.35 * np.clip(np.sqrt(x * x * 0.8 + y * y) - 0.45, 0, 1))[..., None]
    im = Image.fromarray(paper.clip(0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    s = W / 3840
    ink = (43, 33, 24)
    qf = font("EBGaramond-Italic.ttf", int(150 * s), 500)
    lines = []
    for para in text.split("\n"):
        lines += wrap(d, para, qf, W * 0.66) if len(para) > 30 else [para]
    lh = qf.size * 1.28
    y0 = H / 2 - lh * len(lines) / 2 - 60 * s
    mf = font("PlayfairDisplay.ttf", int(420 * s), 700)
    d.text((W * 0.13, y0 - 330 * s), "“", font=mf, fill=(176, 138, 70))
    for i, ln in enumerate(lines):
        w = d.textlength(ln, font=qf)
        d.text(((W - w) / 2, y0 + i * lh), ln, font=qf, fill=ink)
    sf_ = font("Oswald.ttf", int(64 * s), 500)
    yy = y0 + lh * len(lines) + 90 * s
    d.line([(W / 2 - 90 * s, yy - 30 * s), (W / 2 + 90 * s, yy - 30 * s)], fill=(140, 110, 60), width=max(2, int(4 * s)))
    draw_tracked(d, (W / 2, yy), source.upper(), sf_, (95, 72, 45), tracking=int(9 * s))
    return np.array(im)


def card_canvas(bg_rgb: np.ndarray | None, W, H, kicker, title, sub=None, big=False):
    if bg_rgb is not None:
        g = cv2.cvtColor(bg_rgb, cv2.COLOR_RGB2GRAY)
        g = cv2.resize(g, (W // 6, H // 6), interpolation=cv2.INTER_AREA)
        g = cv2.resize(cv2.GaussianBlur(g, (0, 0), 5), (W, H))
        bg = Image.fromarray((np.stack([g] * 3, -1) * 0.26).astype(np.uint8))
    else:
        bg = Image.new("RGB", (W, H), (14, 13, 12))
    d = ImageDraw.Draw(bg)
    s = W / 3840
    tf = font("PlayfairDisplay.ttf", int((190 if big else 170) * s), 600)
    lines = wrap(d, title, tf, W * 0.78)
    lh = tf.size * 1.12
    y = H * 0.5 - lh * len(lines) / 2
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
    return np.array(bg)


def credit_overlay(text: str, w: int, h: int) -> np.ndarray:
    """Small fixed caption, bottom-left. Returns BGRA uint8 strip."""
    s = h / 1080
    f = font("SourceSans3.ttf", int(28 * s), 500)
    im = Image.new("RGBA", (w, int(70 * s)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    text = text if len(text) <= 110 else text[:107] + "…"
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
    kind: str                 # photo | card | quote | stat
    item: dict | None = None  # manifest entry for photos
    card: dict | None = None
    quote: dict | None = None
    colorize: bool = False
    detail: bool = False      # second look at a photo: tight crop on its most detailed region
    seed: int = 0
    credit: str = ""
    focus: tuple | None = None
    canvas: np.ndarray | None = field(default=None, repr=False)
    color: np.ndarray | None = field(default=None, repr=False)
    depth: np.ndarray | None = field(default=None, repr=False)
    full_bleed: bool = True


def _seed(s: str) -> int:
    return zlib.crc32(s.encode()) & 0xffff


SHOT_TARGET = 6.5   # seconds per photo in normal scenes
SHOT_MIN = 4.0
SHOT_MAX = 10.0
MONTAGE_SHOT = 2.6  # cold-open montage cut length


def _photo_shots(imgs, t0, t1, state, target=SHOT_TARGET, lo=SHOT_MIN, hi=SHOT_MAX):
    """Fill [t0, t1] with photos without ever showing the same framing twice in a scene.

    state["queue"]: photos not shown yet in this scene; state["details"]: photos that may get one
    close-up "detail" shot. If the scene still runs out of pictures, shots simply last longer.
    """
    dur = t1 - t0
    if dur <= 0.05:
        return []
    n = max(1, min(round(dur / target), int(dur // lo)))
    avail = len(state["queue"]) + len(state["details"])
    if n > avail:                       # not enough fresh pictures: hold each one longer, up to `hi`
        n = max(avail, int(np.ceil(dur / hi)), 1)
    out, last = [], state.get("last")
    for k in range(n):
        if state["queue"]:
            it, detail = state["queue"].pop(0), False
        elif state["details"]:
            # never put a detail right after its own wide shot
            j = next((i for i, x in enumerate(state["details"]) if x["id"] != last), 0)
            it, detail = state["details"].pop(j), True
        else:
            it, detail = state["all"][k % len(state["all"])], True
        a, b = t0 + k * dur / n, t0 + (k + 1) * dur / n
        out.append(Shot(a, b, "photo", item=it, colorize=bool(it.get("colorize")) and not detail, detail=detail,
                        credit=credit_line(it), seed=(_seed(it["id"]) + (7 if detail else 0)) & 0xffff))
        last = it["id"]
    state["last"] = last
    return out


def _overlay_intervals(scene, timings, dur):
    """Quote and stat cards are timed to the sentence that contains their `match` text."""
    items = []
    if scene.get("quote"):
        items.append(("quote", scene["quote"]))
    for c in scene.get("cards", []) or []:
        items.append(("stat", c))
    out = []
    sents = timings["sentences"]
    for kind, c in items:
        key = (c.get("match") or c.get("text", "")[:25]).lower()
        hit = next((i for i, s in enumerate(sents) if key in s["text"].lower()), None)
        if hit is None:
            print(f"   ! {kind} card in '{scene['id']}': no sentence contains '{key}', skipped")
            continue
        last = min(hit + int(c.get("sentences", 1)) - 1, len(sents) - 1)
        a, b = max(0.0, sents[hit]["start"] - 0.35), min(dur, sents[last]["end"] + 0.6)
        if kind == "stat":
            b = min(b, a + 6.0)
        out.append((a, b, kind, c))
    out.sort(key=lambda x: x[0])
    merged = []
    for a, b, k, c in out:   # drop overlaps, snap tiny gaps to the card
        if merged and a < merged[-1][1]:
            continue
        if merged and a - merged[-1][1] < 2.0:
            a = merged[-1][1]
        merged.append([a, b, k, c])
    for m in merged:
        if m[0] < 2.5:
            m[0] = 0.0
        if dur - m[1] < 2.5:
            m[1] = dur
    return merged


def build_timeline(episode: dict, manifest: dict, timings: dict):
    shots, audio_marks, chapters = [], [], []
    t = 0.0
    used = {sc["id"]: [i for i in manifest["scenes"].get(sc["id"], []) if i["use"]] for sc in episode["scenes"]}
    for idx, scene in enumerate(episode["scenes"]):
        sid = scene["id"]
        imgs = used[sid]
        if not imgs:
            raise SystemExit(f"scene '{sid}' has no images selected in manifest.json")
        if scene.get("chapter"):
            m = re.match(r"^([IVXLC]+)\.\s*(.+)$", scene["chapter"])
            kicker, title = (f"Chapter {m.group(1)}", m.group(2)) if m else ("", scene["chapter"])
            chapters.append((t, title))
            shots.append(Shot(t, t + CARD, "card", card={"bg": imgs[0]["file"], "kicker": kicker, "title": title,
                                                         "sub": scene.get("date")}, seed=_seed(sid)))
            t += CARD
        elif idx == 0:
            chapters.append((0.0, "Intro"))
        dur = timings[sid]["duration"]
        audio_marks.append((t, sid))

        montage = bool(scene.get("montage"))
        pool = list(imgs)
        if montage:   # cold open: this scene's photos plus the strongest photo of every later chapter
            for later in episode["scenes"][idx + 1:]:
                for it in used[later["id"]][:1 if later.get("chapter") else 0]:
                    if it["id"] not in {x["id"] for x in pool}:
                        pool.append(it)
        state = {"queue": list(pool), "details": [] if montage else list(pool), "all": pool}
        kw = dict(target=MONTAGE_SHOT, lo=2.0, hi=4.0) if montage else {}
        cur = 0.0
        for a, b, kind, c in _overlay_intervals(scene, timings[sid], dur):
            shots += _photo_shots(pool, t + cur, t + a, state, **kw)
            shots.append(Shot(t + a, t + b, kind, quote={**c, "bg": imgs[0]["file"]}, seed=_seed(c.get("text", "") + kind)))
            cur = b
        shots += _photo_shots(pool, t + cur, t + dur, state, **kw)
        t += dur
        if idx == 0:
            shots.append(Shot(t, t + TITLE, "card", card={"bg": imgs[0]["file"], "kicker": "", "title": episode["title"],
                                                          "sub": episode.get("subtitle"), "big": True}))
            t += TITLE
    last_imgs = used[episode["scenes"][-1]["id"]]
    shots.append(Shot(t, t + ENDCARD, "card", card={"bg": last_imgs[0]["file"], "kicker": episode.get("channel", ""),
                                                    "title": "Thanks for watching", "sub": "More stories from the archives"}))
    t += ENDCARD
    return shots, audio_marks, chapters, t


# ------------------------------------------------------------------ motion
def smooth(p):
    return p * p * (3 - 2 * p)


def find_focus(canvas: np.ndarray) -> tuple[float, float]:
    """Most detailed region of a photo (edge energy), as relative x, y. Used to frame detail shots."""
    g = cv2.cvtColor(cv2.resize(canvas, (192, 108), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY).astype(np.float32)
    e = np.abs(cv2.Sobel(g, cv2.CV_32F, 1, 0)) + np.abs(cv2.Sobel(g, cv2.CV_32F, 0, 1))
    e = cv2.GaussianBlur(e, (0, 0), 9)
    e[:, :30] = e[:, -30:] = 0
    e[:22, :] = e[-22:, :] = 0
    y, x = np.unravel_index(int(np.argmax(e)), e.shape)
    return x / 192, y / 108


def motion(shot: Shot, p: float, CW, CH):
    rnd = random.Random(shot.seed)
    zin = True
    if shot.kind != "photo":
        z0, z1, (ax, ay), (bx, by) = 1.0, 1.035, (0.5, 0.5), (0.5, 0.5)
    elif shot.detail:
        fx0, fy0 = shot.focus or (0.5, 0.45)
        zbase = 1.65 if shot.full_bleed else 1.85
        z0, z1 = zbase, zbase + 0.12
        ax, ay = fx0 + rnd.uniform(-0.03, 0.03), fy0 + rnd.uniform(-0.03, 0.03)
        bx, by = fx0, fy0
    else:
        zin = rnd.random() < 0.6
        zmax = 1.14 if shot.full_bleed else 1.06
        z0, z1 = (1.0, zmax) if zin else (zmax, 1.0)
        if shot.full_bleed:
            ax, ay = rnd.uniform(0.3, 0.7), rnd.uniform(0.32, 0.58)
            bx, by = rnd.uniform(0.3, 0.7), rnd.uniform(0.32, 0.58)
        else:
            ax, ay, bx, by = 0.5, 0.5, 0.5 + rnd.uniform(-0.03, 0.03), 0.5 + rnd.uniform(-0.03, 0.03)
    e = smooth(p)
    z = z0 + (z1 - z0) * e
    fx, fy = ax + (bx - ax) * e, ay + (by - ay) * e
    hw, hh = CW / (2 * z), CH / (2 * z)
    return z, float(np.clip(fx * CW, hw, CW - hw)), float(np.clip(fy * CH, hh, CH - hh)), zin


def stat_canvas(bg_rgb, W, H, big, text):
    """Big number card, e.g. '675,000' / 'Americans died'."""
    if bg_rgb is not None:
        g = cv2.cvtColor(bg_rgb, cv2.COLOR_RGB2GRAY)
        g = cv2.resize(cv2.GaussianBlur(cv2.resize(g, (W // 6, H // 6)), (0, 0), 5), (W, H))
        im = Image.fromarray((np.stack([g] * 3, -1) * 0.22).astype(np.uint8))
    else:
        im = Image.new("RGB", (W, H), (14, 13, 12))
    d = ImageDraw.Draw(im)
    s = W / 3840
    bf = font("PlayfairDisplay.ttf", int(540 * s), 700)
    w = d.textlength(big, font=bf)
    while w > W * 0.85:
        bf = font("PlayfairDisplay.ttf", int(bf.size * 0.9), 700)
        w = d.textlength(big, font=bf)
    y = H * 0.30
    d.text(((W - w) / 2, y), big, font=bf, fill=GOLD)
    tf = font("EBGaramond-Italic.ttf", int(110 * s), 500)
    for i, ln in enumerate(wrap(d, text, tf, W * 0.7)):
        lw = d.textlength(ln, font=tf)
        d.text(((W - lw) / 2, y + bf.size * 1.25 + i * tf.size * 1.25), ln, font=tf, fill=(236, 230, 216))
    return np.array(im)


class Renderer:
    def __init__(self, ep_dir: Path, W, H, CW, CH, parallax: bool):
        self.ep_dir, self.W, self.H, self.CW, self.CH = ep_dir, W, H, CW, CH
        self.parallax = parallax
        self.X, self.Y = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
        self.Xc, self.Yc = self.X - W / 2, self.Y - H / 2
        self.cache = {}

    def prepare(self, sh: Shot):
        if sh.canvas is not None:
            return
        W, H, CW, CH = self.W, self.H, self.CW, self.CH
        if sh.kind == "photo":
            f = sh.item["file"]
            key = ("p", f)
            if key not in self.cache:
                path = self.ep_dir / f
                rgb = load_rgb(path)
                L = layout(rgb.shape[1], rgb.shape[0], CW, CH)
                canvas = cv2.cvtColor(photo_canvas(rgb, L, CW, CH), cv2.COLOR_RGB2BGR)
                depth = None
                if self.parallax:
                    d = vision.depth(path)
                    if d is not None:
                        depth = depth_canvas(d, L, CW, CH)
                color = None
                if sh.colorize:
                    cp = vision.colorize(path) if vision.is_grayscale(cv2.imread(str(path))) else None
                    if cp is not None:
                        color = cv2.cvtColor(photo_canvas(load_rgb(cp), L, CW, CH), cv2.COLOR_RGB2BGR)
                    else:
                        print(f"   ! colorize skipped for {f} (model missing or photo already in colour)")
                self.cache[key] = (canvas, depth, color, L["fill"])
                while len(self.cache) > 5:
                    self.cache.pop(next(iter(self.cache)))
            sh.canvas, sh.depth, sh.color, sh.full_bleed = self.cache[key]
            if sh.color is None:
                sh.colorize = False
            if sh.detail and sh.focus is None:
                sh.focus = find_focus(sh.canvas)
        elif sh.kind == "quote":
            sh.canvas = cv2.cvtColor(quote_canvas(CW, CH, sh.quote["text"], sh.quote.get("source", "")), cv2.COLOR_RGB2BGR)
        elif sh.kind == "stat":
            bg = load_rgb(self.ep_dir / sh.quote["bg"]) if sh.quote.get("bg") else None
            sh.canvas = cv2.cvtColor(stat_canvas(bg, CW, CH, str(sh.quote["big"]), sh.quote.get("text", "")),
                                     cv2.COLOR_RGB2BGR)
        else:
            c = sh.card
            bg = load_rgb(self.ep_dir / c["bg"]) if c.get("bg") else None
            sh.canvas = cv2.cvtColor(card_canvas(bg, CW, CH, c.get("kicker"), c["title"], c.get("sub"), c.get("big", False)),
                                     cv2.COLOR_RGB2BGR)

    def color_mix(self, sh: Shot, t: float) -> float:
        """0 = authentic original, 1 = colorized. Original holds for ~45% of the shot first."""
        if not sh.colorize:
            return 0.0
        d = sh.end - sh.start
        a = sh.start + max(2.5, 0.42 * d)
        return float(smooth(np.clip((t - a) / 2.2, 0, 1)))

    def frame(self, sh: Shot, t: float) -> np.ndarray:
        W, H, CW, CH = self.W, self.H, self.CW, self.CH
        span = (sh.end - sh.start) + XF
        p = float(np.clip((t - sh.start + XF / 2) / span, 0, 1))
        z, cx, cy, zin = motion(sh, p, CW, CH)
        s = z * W / CW
        M = np.float32([[s, 0, W / 2 - s * cx], [0, s, H / 2 - s * cy]])
        f = cv2.warpAffine(sh.canvas, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        c = self.color_mix(sh, t)
        if c > 0:
            fc = cv2.warpAffine(sh.color, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            f = cv2.addWeighted(f, 1 - c, fc, c, 0)
        if sh.depth is not None:
            d = cv2.warpAffine(sh.depth, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
            rnd = random.Random(sh.seed * 7 + 1)
            ang = rnd.uniform(0, 2 * np.pi)
            amp = (0.022 if sh.full_bleed else 0.012) * W     # total lateral parallax travel, in pixels
            e = smooth(p) - 0.5
            k = d - 0.4                                        # focus plane: far things drift back, near things forward
            sx, sy = float(amp * e * np.cos(ang)), float(amp * e * 0.6 * np.sin(ang))
            dolly = (0.035 if zin else -0.035) * e             # depth-dependent zoom = the "3D push-in"
            mx = (self.X - sx * k - self.Xc * (dolly * k)).astype(np.float32, copy=False)
            my = (self.Y - sy * k - self.Yc * (dolly * k)).astype(np.float32, copy=False)
            f = cv2.remap(f, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        return f


def vignette(W, H):
    y, x = np.ogrid[-1:1:H * 1j, -1:1:W * 1j]
    r = np.sqrt((x * 0.85) ** 2 + y ** 2)
    m = 1 - 0.42 * np.clip((r - 0.55) / 0.75, 0, 1) ** 1.6
    return (m * 256).astype(np.uint16)[..., None]


# ------------------------------------------------------------------ audio, subtitles, chapters
def music_track(episode, total, chapters):
    m = episode.get("music")
    if not m:
        return None
    if isinstance(m, str):
        a, msr = sf.read(m, dtype="float32", always_2d=True)
        a = a.mean(axis=1)
        if msr != SR:
            x = np.linspace(0, len(a), int(len(a) * SR / msr), endpoint=False)
            a = np.interp(x, np.arange(len(a)), a).astype(np.float32)
        return np.tile(a, int(np.ceil(total * SR / len(a))))[: int(total * SR)]
    if m.get("generate"):
        from .music import underscore
        print("   synthesizing underscore...")
        hits = [c[0] for c in chapters if c[0] > 1]
        return underscore(total, seed=int(m.get("seed", 1)), mood=m.get("mood", "somber"), hits=hits)
    return None


def build_audio(ep_dir, audio_marks, total, music):
    out = np.zeros(int(total * SR) + SR, np.float32)
    for t0, sid in audio_marks:
        a, _ = sf.read(ep_dir / "audio" / f"{sid}.wav", dtype="float32")
        i = int(t0 * SR)
        out[i:i + len(a)] += a
    if music is not None:
        m = np.zeros_like(out)
        m[: len(music)] = music[: len(out)]
        k = int(0.4 * SR)
        env = np.convolve(np.abs(out), np.ones(k) / k, mode="same")
        gain = np.where(env > 0.01, 0.075, 0.22).astype(np.float32)   # duck under the voice, rise on cards
        gain = np.convolve(gain, np.ones(2 * k) / (2 * k), mode="same")
        out += m * gain
    peak = np.max(np.abs(out)) or 1
    out *= min(1.0, 0.89 / peak)
    path = ep_dir / "build" / "mix.wav"
    sf.write(path, out, SR)
    return path


def fmt_srt(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(audio_marks, timings, path):
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
def render(ep_dir: Path, episode: dict, preview: bool = False, parallax: bool = True):
    manifest = json.loads((ep_dir / "manifest.json").read_text())
    timings = json.loads((ep_dir / "audio" / "timings.json").read_text())
    build = ep_dir / "build"
    build.mkdir(exist_ok=True)
    W, H, FPS = (960, 540, 24) if preview else (1920, 1080, 30)
    CW, CH = (1920, 1080) if preview else (3840, 2160)
    if parallax and not vision.depth_available():
        print("   depth model not installed -> plain Ken Burns (run setup to download it)")
        parallax = False

    shots, audio_marks, chapters, total = build_timeline(episode, manifest, timings)
    music = music_track(episode, total, chapters)
    mix = build_audio(ep_dir, audio_marks, total, music)
    write_srt(audio_marks, timings, build / "subtitles.en.srt")
    (build / "chapters.txt").write_text("\n".join(f"{fmt_ts(a)} {b}" for a, b in chapters))
    (build / "timeline.json").write_text(json.dumps(
        [{"start": round(s.start, 2), "end": round(s.end, 2), "kind": s.kind,
          "id": s.item["id"] if s.item else None, "colorized": bool(s.item and s.item.get("colorize"))} for s in shots],
        indent=1))

    out = build / (f"{episode['slug']}_preview.mp4" if preview else f"{episode['slug']}.mp4")
    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", str(mix),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "24" if preview else "19", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", str(out)],
        stdin=subprocess.PIPE)

    R = Renderer(ep_dir, W, H, CW, CH, parallax)
    vig = vignette(W, H)
    credits = {}

    def credit_img(text):
        if text not in credits:
            credits[text] = credit_overlay(text, W, H)
        return credits[text]

    def overlay(frame, ov, a):
        if a <= 0.01:
            return
        al = (ov[..., 3:4].astype(np.float32) / 255) * a
        roi = frame[H - ov.shape[0]:H]
        roi[:] = (roi * (1 - al) + ov[..., :3] * al).astype(np.uint8)

    nframes = int(total * FPS)
    cur = 0
    for fi in range(nframes):
        t = fi / FPS
        while cur < len(shots) - 1 and t >= shots[cur].end:
            shots[cur].canvas = shots[cur].depth = shots[cur].color = None
            cur += 1
        sh = shots[cur]
        R.prepare(sh)
        frame = R.frame(sh, t)
        a_cur = 1.0
        nxt = shots[cur + 1] if cur + 1 < len(shots) else None
        if nxt and t > sh.end - XF / 2:
            R.prepare(nxt)
            w = smooth(float(np.clip((t - (sh.end - XF / 2)) / XF, 0, 1)))
            frame = cv2.addWeighted(frame, 1 - w, R.frame(nxt, t), w, 0)
            a_cur = 1 - w
        frame = ((frame.astype(np.uint16) * vig) >> 8).astype(np.uint8)
        for s_, a_ in ((sh, a_cur), (nxt, 1 - a_cur)):
            if s_ is None or s_.kind != "photo" or a_ <= 0.02:
                continue
            fin = float(np.clip(min(t - s_.start - 0.6, s_.end - t - 0.2) / 0.6, 0, 1)) * a_
            c = R.color_mix(s_, t)
            overlay(frame, credit_img(s_.credit), fin * (1 - c))
            if c > 0:
                overlay(frame, credit_img(s_.credit + " · Digitally colorized"), fin * c)
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
