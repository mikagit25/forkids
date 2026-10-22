"""Choreography: song sections → dance scenes with their own cast and formation.

Every section of the song gets a formation template and a fresh cast drawn from the pool
(no character repeats between neighbouring scenes). Characters pop in with an elastic ease on
the section's first beat and shrink out on its last beat, so scene changes land on the music.

Templates (positions for 1920×1080, scaled for other sizes):
  solo    one big character centre stage
  duet    two, mirrored moves
  trio    three in a row, phase-shifted
  wave    five in a row, each a quarter beat after the previous (a "wave")
  conga   four hopping across the screen in a line
  party   everyone from the scene before + more, finale
  rest    break: one character breathes and giggles, the rest of the stage empty
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

from .characters import CHARACTERS
from .easing import dance_pose, elastic_out

SECTION_TEMPLATE = {"intro": ["solo"], "A": ["trio", "duet"], "A2": ["duet", "trio"], "B": ["wave", "conga"],
                    "B2": ["conga", "wave"], "break": ["rest"], "outro": ["party"]}
SECTION_ENERGY = {"intro": 0.55, "A": 1.0, "A2": 1.05, "B": 1.2, "B2": 1.2, "break": 0.45, "outro": 0.8}
MOVES = ["bounce", "sway", "stretch"]


@dataclass
class Slot:
    name: str          # character key
    x: float
    y: float
    r: float
    move: str
    offset: float      # in beats
    mirror: bool = False
    seed: int = 1


@dataclass
class Scene:
    start: float
    end: float
    section: str
    template: str
    slots: list


def formation(template: str, cast: list[str], rnd: random.Random) -> list[Slot]:
    mv = rnd.choice(MOVES)
    if template == "solo":
        return [Slot(cast[0], 960, 520, 310, "bounce", 0.0)]
    if template == "duet":
        return [Slot(cast[0], 650, 540, 260, mv, 0.0), Slot(cast[1], 1270, 540, 260, mv, 0.0, mirror=True)]
    if template == "trio":
        mv2 = rnd.choice(MOVES)
        return [Slot(cast[0], 470, 560, 215, mv2, 0.0), Slot(cast[1], 960, 520, 250, "bounce", 0.25),
                Slot(cast[2], 1450, 560, 215, mv2, 0.0, mirror=True)]
    if template == "wave":
        return [Slot(c, 230 + i * 365, 560, 172, "bounce", i * 0.25) for i, c in enumerate(cast[:5])]
    if template == "conga":
        return [Slot(c, i * 530.0, 600, 165, "bounce", i * 0.5) for i, c in enumerate(cast[:4])]
    if template == "rest":
        return [Slot(cast[0], 960, 540, 280, "stretch", 0.0)]
    # party: two rows, everybody
    out = []
    for i, c in enumerate(cast[:6]):
        row, col = divmod(i, 3)
        out.append(Slot(c, 480 + col * 480 + (row * 240 - 120), 380 + row * 360, 150, MOVES[i % 3], (i % 3) * 0.25))
    return out


def build(bmap: dict, pool: list[str], seed: int) -> list[Scene]:
    rnd = random.Random(seed)
    scenes, last = [], set()
    need = {"solo": 1, "duet": 2, "trio": 3, "wave": 5, "conga": 4, "rest": 1, "party": 6}
    for k, sec in enumerate(bmap["sections"]):
        options = SECTION_TEMPLATE.get(sec["name"], ["trio"])
        prev = scenes[-1].template if scenes else None
        choices = [o for o in options if o != prev] or options            # never the same formation twice in a row
        template = choices[(k + seed) % len(choices)]
        n = need[template]
        fresh = [c for c in pool if c not in last] or pool[:]
        rnd.shuffle(fresh)
        cast = (fresh + [c for c in pool if c not in fresh])[:n] if template != "party" else rnd.sample(pool, min(n, len(pool)))
        while len(cast) < n:
            cast.append(rnd.choice(pool))
        slots = formation(template, cast, rnd)
        for i, s in enumerate(slots):
            s.seed = k * 10 + i + 1
        scenes.append(Scene(sec["start"], sec["end"], sec["name"], template, slots))
        last = set(cast)
    return scenes


def scene_at(scenes, t):
    for s in scenes:
        if s.start <= t < s.end:
            return s
    return scenes[-1]


_CHAR_CACHE: dict = {}


def frame_items(scenes, bmap: dict, t: float, phase_fn, energy: float, w=1920, h=1080):
    """Characters to draw at time t → [(character, cx, cy, r, pose), …]."""
    sc = scene_at(scenes, t)
    beat = bmap["beat_s"]
    k = w / 1920
    enter = elastic_out(min(1.0, (t - sc.start) / (beat * 1.2)))
    leave = min(1.0, max(0.0, (sc.end - t) / (beat * 0.8)))
    leave = 0.5 - 0.5 * math.cos(math.pi * leave)
    items = []
    for i, s in enumerate(sc.slots):
        key = (s.name, s.seed)
        ch = _CHAR_CACHE.get(key) or _CHAR_CACHE.setdefault(key, CHARACTERS[s.name](seed=s.seed))
        b, ph = phase_fn(t, s.offset)
        pose = dance_pose(b, ph, s.move, energy)
        if s.mirror:
            pose["tilt"] = -pose["tilt"]; pose["dx"] = -pose["dx"]
            pose["look"] = (-pose["look"][0], pose["look"][1])
        x = s.x
        if sc.template == "conga":                            # march across, wrap around
            span = 4 * 530.0
            x = (s.x + (t - sc.start) * 150) % span - 100
            pose["look"] = (0.9, 0.0)
        if sc.template == "rest":
            pose["happy"] = (b % 4) >= 2
        stagger = min(1.0, max(0.0, enter * 1.0 - i * 0.04)) if sc.template in ("wave", "party") else enter
        scale = stagger * leave
        if scale < 0.02:
            continue
        items.append((ch, x * k, s.y * k, s.r * k * scale, pose))
    return items


def energy_at(bmap: dict, t: float) -> float:
    """Dance energy from the song section, cross-faded over one beat (pure function of t → parallel-safe)."""
    secs = bmap["sections"]; beat = bmap["beat_s"]
    for i, sec in enumerate(secs):
        if sec["start"] <= t < sec["end"]:
            e = SECTION_ENERGY.get(sec["name"], 1.0)
            if i and t - sec["start"] < beat:
                p = SECTION_ENERGY.get(secs[i - 1]["name"], 1.0)
                return p + (e - p) * (t - sec["start"]) / beat
            return e
    return 0.6
