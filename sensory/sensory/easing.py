"""Beat-locked motion. Everything is computed from the beat phase, not raw time → always on the music."""
from __future__ import annotations

import math


def beat_phase(t: float, bpm: float, offset: float = 0.0) -> tuple[int, float]:
    """(beat index, phase 0..1) for a steady tempo; offset in beats (0.25 = a quarter beat late)."""
    b = t * bpm / 60.0 - offset
    i = math.floor(b)
    return i, b - i


def ease_in_out(x: float) -> float:
    return 0.5 - 0.5 * math.cos(math.pi * max(0.0, min(1.0, x)))


def elastic_out(x: float) -> float:
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    return 2 ** (-10 * x) * math.sin((x * 10 - 0.75) * (2 * math.pi) / 3) + 1


def dance_pose(beat: int, phase: float, move: str = "bounce", amp: float = 1.0) -> dict:
    """Pose for one character on this frame.
    squash on the hit (exp decay), hop between hits, sway left/right every other beat."""
    k = math.exp(-phase * 6)                                  # impulse on the beat
    sy, sx = 1 - 0.16 * k * amp, 1 + 0.11 * k * amp           # squashed on the hit
    hop = -abs(math.sin(math.pi * phase)) * 46 * amp          # up between hits, down on the hit
    side = 1 if beat % 2 == 0 else -1
    sway = side * math.sin(math.pi * ease_in_out(phase))      # 0 → ±1 → 0 within the beat
    pose = {"sx": sx, "sy": sy, "dy": hop, "dx": 0.0, "tilt": 0.0, "look": (0.0, 0.0),
            "smile": 0.75 + 0.55 * k,                          # mouth opens wide on every hit ("singing")
            "happy": beat % 8 == 7}                            # a giggle with ^ ^ eyes once every 2 bars
    if move == "bounce":
        pose["tilt"] = 9 * sway * amp
        pose["look"] = (0.6 * side * ease_in_out(phase), 0.0)
    elif move == "sway":                                      # side-to-side wiggle, small hop
        pose["dy"] *= 0.35
        pose["dx"] = 38 * sway * amp
        pose["tilt"] = 14 * sway * amp
        pose["look"] = (side * 0.8, 0.0)
    elif move == "stretch":                                   # tall-short pump
        s = math.sin(math.pi * phase)
        pose["sy"], pose["sx"] = 1 - 0.16 * k * amp + 0.12 * s * amp, 1 + 0.11 * k * amp - 0.07 * s * amp
        pose["dy"] *= 0.2
        pose["look"] = (0.0, -0.6 * s)
    return pose
