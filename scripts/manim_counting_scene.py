"""
Manim scene for counting videos.
Reads /tmp/manim_counting_params.json — written by generate_counting_*.py.

Params:
  shape_type: str  (circle|square|triangle|star|diamond|ellipse|hexagon|pentagon|rectangle)
  count:      int  (1-10)
  colors:     list[str]
  bg_color:   str
  intro_dur:  float  (seconds for shape intro phase)
  num_dur:    float  (seconds per count number)
  hold_dur:   float  (seconds for final celebration hold)
  vertical:   bool
  size:       float  (shape radius/scale)
"""
import json
import math
from pathlib import Path
from manim import *

PARAMS_FILE = Path("/tmp/manim_counting_params.json")
PARAMS = json.loads(PARAMS_FILE.read_text()) if PARAMS_FILE.exists() else {}

VERTICAL = PARAMS.get("vertical", False)
if VERTICAL:
    config.pixel_width  = 1080
    config.pixel_height = 1920
    HW = 2.2
    HH = 4.0
else:
    config.pixel_width  = 1920
    config.pixel_height = 1080
    HW = 7.0
    HH = 4.0

config.frame_rate = 24

SHAPE_LABELS = {
    "circle":    "CIRCLES",
    "square":    "SQUARES",
    "triangle":  "TRIANGLES",
    "star":      "STARS",
    "diamond":   "DIAMONDS",
    "ellipse":   "OVALS",
    "hexagon":   "HEXAGONS",
    "pentagon":  "PENTAGONS",
    "rectangle": "RECTANGLES",
}

NUM_WORDS = ["", "ONE", "TWO", "THREE", "FOUR", "FIVE",
             "SIX", "SEVEN", "EIGHT", "NINE", "TEN"]


def _make_shape(shape_type, color, size):
    kw = dict(fill_opacity=1, stroke_width=0, color=color)
    if shape_type == "circle":    return Circle(radius=size, **kw)
    if shape_type == "square":    return Square(side_length=size * 2, **kw)
    if shape_type == "triangle":  return Triangle(**kw).scale(size)
    if shape_type == "hexagon":   return RegularPolygon(6, **kw).scale(size)
    if shape_type == "pentagon":  return RegularPolygon(5, **kw).scale(size)
    if shape_type == "star":      return Star(5, outer_radius=size, **kw)
    if shape_type == "diamond":   return Square(side_length=size * 2, **kw).rotate(PI / 4)
    if shape_type == "ellipse":   return Ellipse(width=size * 2.6, height=size * 1.6, **kw)
    if shape_type == "rectangle": return Rectangle(width=size * 2.8, height=size * 1.5, **kw)
    return Circle(radius=size, **kw)


def _compute_positions(count, size, vertical):
    """Return list of (x, y) for each of `count` shapes, sized to fit screen."""
    if vertical:
        cols = 3 if count > 3 else count
        max_x = HW * 0.9
    else:
        cols = 5 if count > 5 else count
        max_x = HW * 0.85

    rows = math.ceil(count / cols)
    spacing_x = (max_x * 2) / max(cols, 1) if cols > 1 else 0
    spacing_y = min(spacing_x, (HH * 0.9) / max(rows, 1))

    y_offset = (rows - 1) / 2 * spacing_y

    positions = []
    for i in range(count):
        row = i // cols
        col = i % cols
        # How many shapes in this row?
        row_count = min(cols, count - row * cols)
        x = (col - (row_count - 1) / 2) * spacing_x
        y = y_offset - row * spacing_y
        positions.append((x, y))
    return positions


class CountingScene(Scene):
    def construct(self):
        shape_type = PARAMS.get("shape_type", "circle")
        count      = max(1, min(10, PARAMS.get("count", 5)))
        colors     = PARAMS.get("colors", ["#FF4444", "#FF7F2A", "#FFD700", "#27AE60", "#2980B9"])
        bg_color   = PARAMS.get("bg_color", "#FFF9E6")
        intro_dur  = PARAMS.get("intro_dur", 4.0)
        num_dur    = PARAMS.get("num_dur", 3.5)
        hold_dur   = PARAMS.get("hold_dur", 2.5)
        size       = PARAMS.get("size", 0.55)

        self.camera.background_color = ManimColor(bg_color)
        colors_ext = (colors * 20)[:20]

        label = SHAPE_LABELS.get(shape_type, shape_type.upper() + "S")
        accent = ManimColor(colors[0])

        # ── INTRO ─────────────────────────────────────────────────────────────
        title = Text("Let's Count!", font_size=70, color=WHITE,
                     stroke_color=accent, stroke_width=4)
        title.move_to([0, HH * 0.65, 0])

        shape_lbl = Text(label, font_size=54, color=accent)
        shape_lbl.move_to([0, HH * 0.38, 0])

        demo = _make_shape(shape_type, colors[0], size * 1.7)
        demo.move_to(ORIGIN)

        fade_in_t = min(1.0, intro_dur * 0.35)
        self.play(
            FadeIn(title, shift=DOWN * 0.3),
            FadeIn(shape_lbl, shift=DOWN * 0.3),
            GrowFromCenter(demo),
            run_time=fade_in_t,
        )
        pulse_t = intro_dur - fade_in_t - 0.4
        if pulse_t > 0.3:
            self.play(demo.animate.scale(1.3), run_time=pulse_t / 2,
                      rate_func=there_and_back)
            self.wait(pulse_t / 2)
        self.play(FadeOut(title), FadeOut(shape_lbl), FadeOut(demo), run_time=0.4)

        # ── COUNTING ──────────────────────────────────────────────────────────
        positions = _compute_positions(count, size, VERTICAL)
        placed = []

        for i in range(1, count + 1):
            col  = colors_ext[i - 1]
            pos  = positions[i - 1]
            shp  = _make_shape(shape_type, col, size)
            shp.move_to([pos[0], pos[1] + HH, 0])  # start above screen

            arrive_t = min(0.55, num_dur * 0.18)
            self.play(
                shp.animate.move_to([pos[0], pos[1], 0]),
                run_time=arrive_t,
                rate_func=rush_into,
            )
            placed.append(shp)

            # Show number word
            word = NUM_WORDS[i] if i <= 10 else str(i)
            num_txt = Text(word, font_size=86, color=ManimColor(col),
                           stroke_color=WHITE, stroke_width=3)
            num_txt.move_to([0, -HH * 0.65, 0])
            show_t  = min(0.25, num_dur * 0.08)
            linger  = num_dur - arrive_t - show_t - 0.22
            self.play(FadeIn(num_txt, scale=1.4), run_time=show_t)
            if linger > 0:
                self.wait(linger)
            self.play(FadeOut(num_txt), run_time=0.22)

        # ── CELEBRATION ───────────────────────────────────────────────────────
        big_num = Text(str(count), font_size=210, color=WHITE,
                       stroke_color=accent, stroke_width=10)
        big_num.move_to([0, -HH * 0.6, 0])

        self.play(GrowFromCenter(big_num), run_time=0.5)

        # Wiggle all placed shapes
        wiggle_t = hold_dur * 0.35
        self.play(
            *[s.animate.scale(1.35) for s in placed],
            run_time=wiggle_t,
            rate_func=there_and_back,
        )
        self.wait(hold_dur * 0.35)

        self.play(
            FadeOut(big_num),
            *[FadeOut(s) for s in placed],
            run_time=0.5,
        )
