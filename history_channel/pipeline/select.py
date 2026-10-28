"""Picking the right archive photo for each scene.

Three filters, cheapest first:
1. Metadata: years in the date/title/description must fit the episode's era (`era: [1918, 1920]` in
   episode.yaml). A 2019 car race or a 2016 satellite image never reaches the download step.
2. Near-duplicates: Commons often holds the same photo 3-4 times (different scans, crops, restorations).
   A perceptual hash catches them across the whole episode, so the same picture never appears twice.
3. Meaning: CLIP (ViT-B/32, MIT licence, runs locally via fastembed) compares each downloaded photo with
   the scene text and rejects images that do not show what the narration is about.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
from PIL import Image

YEAR = re.compile(r"(?<!\d)(1[5-9]\d\d|20\d\d)(?!\d)")
JUNK = re.compile(r"\b(logo|icon|flag of|coat of arms|stamp|banknote|coin|signature|qr|screenshot|diagram|"
                  r"chart|map of|locator|svg)\b", re.I)


def years(text: str) -> list[int]:
    return [int(y) for y in YEAR.findall(text or "")]


def meta_score(c: dict, era: tuple[int, int] | None, query: str = "", allow_modern: bool = False) -> float:
    """Roughly -1..+0.4. Strongly negative = obviously off-period."""
    score = 0.0
    title = c.get("title", "")
    junk = JUNK.search(title)
    if junk and junk.group(0).lower() not in query.lower():   # a map is fine if the script asked for a map
        score -= 0.25
    if not era:
        return score
    y0, y1 = era
    ys_date = years(c.get("date", ""))
    ys_text = years(title + " " + c.get("description", ""))
    in_era = [y for y in ys_date + ys_text if y0 - 15 <= y <= y1 + 8]
    if in_era:
        score += 0.3
    if not allow_modern:
        modern_date = [y for y in ys_date if y > y1 + 30]
        modern_text = [y for y in ys_text if y > y1 + 30]
        if modern_date and not in_era:
            score -= 0.8
        elif modern_text and not in_era:
            score -= 0.5
    return score


# ---------------------------------------------------------------- perceptual hash
def phash(path: Path):
    """Several perceptual hashes (full frame + centre crops), so re-scans and re-crops still match."""
    try:
        import imagehash
        with Image.open(path) as im:
            g = im.convert("L")
            w, h = g.size
            out = [imagehash.phash(g)]
            for f in (0.08, 0.16):
                out.append(imagehash.phash(g.crop((int(w * f), int(h * f), int(w * (1 - f)), int(h * (1 - f))))))
            return out
    except Exception:
        return None


def is_duplicate(h, hashes: list, max_dist: int = 10) -> bool:
    if not h:
        return False
    return any(h2 and min(a - b for a in h for b in h2) <= max_dist for h2 in hashes)


# ---------------------------------------------------------------- CLIP relevance
class Relevance:
    """Cosine similarity between a photo and a text, via CLIP. Disabled gracefully if unavailable."""

    def __init__(self):
        self.ok = False
        try:
            from fastembed import ImageEmbedding, TextEmbedding
            self.img = ImageEmbedding("Qdrant/clip-ViT-B-32-vision")
            self.txt = TextEmbedding("Qdrant/clip-ViT-B-32-text")
            self.ok = True
        except Exception as e:
            print(f"   (relevance check off: {str(e)[:80]}; install fastembed to enable)")
        self._tcache = {}

    def text_vec(self, text: str):
        if text not in self._tcache:
            v = np.array(list(self.txt.embed([text]))[0], dtype=np.float32)
            self._tcache[text] = v / (np.linalg.norm(v) or 1)
        return self._tcache[text]

    def score(self, path: Path, texts: list[str]) -> float | None:
        if not self.ok:
            return None
        try:
            v = np.array(list(self.img.embed([str(path)]))[0], dtype=np.float32)
            v /= np.linalg.norm(v) or 1
            return float(max(v @ self.text_vec(t) for t in texts))
        except Exception:
            return None


# CLIP ViT-B/32 cosine scores for photo vs. caption sit around 0.18 (unrelated) to 0.32 (very close)
CLIP_MIN = 0.215


def prompts(query: str, scene: dict, episode: dict) -> list[str]:
    q = query.strip()
    ctx = episode.get("visual_context", "")
    out = [f"a historical photograph of {q}", f"an old archival image of {q}"]
    if ctx:
        out.append(f"{ctx}: {q}")
    return out


def combined(meta: float, clip: float | None) -> float:
    if clip is None:
        return meta
    return meta + (clip - CLIP_MIN) * 6
