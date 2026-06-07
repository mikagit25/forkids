"""
Manim scene file for shape dance videos.
Reads parameters from /tmp/manim_shape_params.json — written by manim_shapes_video.py.
"""
import json
import math
import random
from pathlib import Path
from manim import *

# ── PARAMS ──────────────────────────────────────────────────────────────────
PARAMS = json.loads(Path("/tmp/manim_shape_params.json").read_text())

VERTICAL = PARAMS.get("vertical", False)
if VERTICAL:
    config.pixel_width  = 1080
    config.pixel_height = 1920
    HW = 2.2   # half frame width (portrait ~4.5 units wide)
    HH = 4.0   # half frame height
else:
    config.pixel_width  = 1920
    config.pixel_height = 1080
    HW = 7.0   # half frame width (landscape ~14 units wide)
    HH = 4.0

config.frame_rate   = 24
config.background_color = PARAMS["bg_color"]

COLORS     = PARAMS["colors"]
N          = PARAMS["n"]
SHAPE_TYPE = PARAMS["shape_type"]
DURATION   = PARAMS["duration"]
SIZE       = PARAMS.get("size", 0.65)


# ── SHAPE FACTORY ────────────────────────────────────────────────────────────
def _make_shape(shape_type=None, color=None, size=None):
    st = shape_type or SHAPE_TYPE
    c  = color or COLORS[0]
    sz = size  or SIZE
    kw = dict(fill_opacity=1, stroke_width=0, color=c)
    if st == "circle":   return Circle(radius=sz, **kw)
    if st == "square":   return Square(side_length=sz * 2, **kw)
    if st == "triangle": return Triangle(**kw).scale(sz)
    if st == "hexagon":  return RegularPolygon(6, **kw).scale(sz)
    if st == "star":     return Star(5, outer_radius=sz, **kw)
    if st == "ellipse":  return Ellipse(width=sz * 2.8, height=sz * 1.6, **kw)
    if st == "diamond":  return Square(side_length=sz * 2, **kw).rotate(PI / 4)
    if st == "pentagon": return RegularPolygon(5, **kw).scale(sz)
    if st == "cross":
        h = Rectangle(width=sz * 2.2, height=sz * 0.7, **kw)
        v = Rectangle(width=sz * 0.7, height=sz * 2.2, **kw)
        return VGroup(h, v)
    if st == "mixed":
        pick = random.choice(["circle", "square", "triangle", "hexagon",
                               "ellipse", "diamond", "pentagon"])
        return _make_shape(pick, c, sz)
    if st == "mixed2":   # original mixed without new shapes
        pick = random.choice(["circle", "square", "triangle", "hexagon"])
        return _make_shape(pick, c, sz)
    return Circle(radius=sz, **kw)


def _make_row(n=None, colors=None, shape=None, size=None):
    n = n or N
    colors = colors or COLORS
    shape  = shape  or SHAPE_TYPE
    size   = size   or SIZE
    max_spread = HW * 1.7
    spacing = min(max_spread / max(n, 1), 2.4)
    shapes = VGroup()
    for i in range(n):
        s = _make_shape(shape, colors[i % len(colors)], size)
        s.move_to(RIGHT * (i - (n - 1) / 2) * spacing)
        shapes.add(s)
    return shapes


# ── SCENE ────────────────────────────────────────────────────────────────────
class ShapeScene(Scene):

    def construct(self):
        choreo = PARAMS["choreo"]
        getattr(self, f"do_{choreo}")()

    # time tracker helper
    def _timer(self):
        t = ValueTracker(0)
        t.add_updater(lambda m, dt: m.increment_value(dt))
        self.add(t)
        return t

    # ── BOUNCE ROW ────────────────────────────────────────────────────────
    def do_bounce_row(self):
        """Shapes in a row do a phase-shifted bounce wave."""
        shapes = _make_row()
        n = len(shapes)
        init_ys = [s.get_center()[1] for s in shapes]
        t = self._timer()

        for i in range(n):
            def upd(m, i=i, iy=init_ys[i]):
                m.set_y(iy + math.sin(t.get_value() * 2.8 + i * TAU / n) * 1.6)
            shapes[i].add_updater(upd)

        self.add(shapes)
        self.wait(DURATION)

    # ── CAROUSEL ──────────────────────────────────────────────────────────
    def do_carousel(self):
        """Shapes orbit a center point like a carousel."""
        n = N
        radius = min(2.8, HW * 0.9)
        t = self._timer()
        shapes = VGroup(*[
            _make_shape(color=COLORS[i % len(COLORS)]) for i in range(n)
        ])

        for i, s in enumerate(shapes):
            def upd(m, i=i):
                angle = t.get_value() * 1.1 + i * TAU / n
                r = radius + math.sin(t.get_value() * 0.7 + i) * 0.5
                m.move_to([r * math.cos(angle), r * math.sin(angle), 0])
            s.add_updater(upd)

        self.add(shapes)
        self.wait(DURATION)

    # ── SIZE PULSE ────────────────────────────────────────────────────────
    def do_size_pulse(self):
        """Shapes pulse big→small in sync."""
        n = min(N, 5)
        shapes = _make_row(n=n)
        self.add(shapes)
        cycles = max(4, int(DURATION / 1.8))
        for _ in range(cycles):
            self.play(*[s.animate.scale(1.65) for s in shapes],
                      run_time=0.5, rate_func=rush_into)
            self.play(*[s.animate.scale(1 / 1.65) for s in shapes],
                      run_time=0.55, rate_func=rush_from)
            self.wait(0.6)

    # ── COLOR MORPH ───────────────────────────────────────────────────────
    def do_color_morph(self):
        """Shapes continuously cycle through colors."""
        shapes = _make_row()
        n_c = len(COLORS)
        t = self._timer()

        for i, s in enumerate(shapes):
            offset = i * 0.6
            def upd(m, off=offset):
                tv = t.get_value()
                idx  = int((tv + off) / 2.5) % n_c
                nxt  = (idx + 1) % n_c
                frac = ((tv + off) / 2.5) % 1.0
                m.set_color(interpolate_color(ManimColor(COLORS[idx]),
                                              ManimColor(COLORS[nxt]), frac))
            s.add_updater(upd)

        self.add(shapes)
        self.wait(DURATION)

    # ── SCATTER GATHER ────────────────────────────────────────────────────
    def do_scatter_gather(self):
        """Shapes scatter to random spots, then return home."""
        n = N
        rng = random.Random(PARAMS.get("seed", 0))
        shapes = VGroup(*[_make_shape(color=COLORS[i % len(COLORS)]) for i in range(n)])
        shapes.arrange_in_grid(rows=max(1, n // 3), buff=0.7)
        shapes.center()
        self.add(shapes)
        home = [s.get_center().copy() for s in shapes]

        self.wait(0.8)
        cycles = max(3, int(DURATION / 8))
        for _ in range(cycles):
            targets = [[rng.uniform(-HW + 0.5, HW - 0.5), rng.uniform(-HH + 0.5, HH - 0.5), 0]
                       for _ in range(n)]
            self.play(*[shapes[i].animate.move_to(targets[i]) for i in range(n)],
                      run_time=1.5, rate_func=smooth)
            self.wait(0.8)
            self.play(*[shapes[i].animate.move_to(home[i]) for i in range(n)],
                      run_time=1.5, rate_func=smooth)
            self.wait(0.8)

    # ── FOLLOW PATH ───────────────────────────────────────────────────────
    def do_follow_path(self):
        """Chain of shapes follows a figure-8 path with trailing delay."""
        n = N
        t = self._timer()
        shapes = VGroup(*[
            _make_shape(color=COLORS[i % len(COLORS)]) for i in range(n)
        ])
        px = HW * 0.65
        py = HH * 0.55

        for i, s in enumerate(shapes):
            delay = i * 0.35
            def upd(m, d=delay):
                tv = max(0, t.get_value() - d)
                x = px * math.sin(tv * 0.7)
                y = py * math.sin(tv * 1.4)
                m.move_to([x, y, 0])
            s.add_updater(upd)

        self.add(shapes)
        self.wait(DURATION)

    # ── RAIN ──────────────────────────────────────────────────────────────
    def do_rain(self):
        """Shapes fall from top, bounce at bottom."""
        n = max(3, N)
        rng = random.Random(PARAMS.get("seed", 1))
        iters = max(4, int(DURATION / 5))
        for it in range(iters):
            drops = VGroup(*[
                _make_shape(color=COLORS[(it * n + i) % len(COLORS)]).move_to(
                    [rng.uniform(-HW + 0.3, HW - 0.3), HH + 1.0, 0]
                )
                for i in range(n)
            ])
            self.add(drops)
            self.play(*[d.animate.set_y(-HH + 0.4) for d in drops],
                      run_time=1.1, rate_func=rush_into)
            self.play(*[d.animate.shift(UP * 1.1) for d in drops],
                      run_time=0.28, rate_func=rush_from)
            self.play(*[d.animate.shift(DOWN * 0.5) for d in drops],
                      run_time=0.22, rate_func=rush_into)
            self.play(FadeOut(drops), run_time=0.3)
            self.wait(0.3)

    # ── SPIN ZOOM ─────────────────────────────────────────────────────────
    def do_spin_zoom(self):
        """Shapes orbit + spin on their own axis, radius pulses."""
        n = N
        base_r = min(2.5, HW * 0.8)
        t = self._timer()
        shapes = VGroup(*[
            _make_shape(color=COLORS[i % len(COLORS)]) for i in range(n)
        ])

        for i, s in enumerate(shapes):
            def upd(m, i=i, dt=0):
                tv  = t.get_value()
                r   = base_r + min(1.2, HW * 0.4) * math.sin(tv * 0.8 + i * PI / n)
                ang = tv * 1.3 + i * TAU / n
                m.move_to([r * math.cos(ang), r * math.sin(ang), 0])
            s.add_updater(upd)

            # Individual spin via separate rotation updater
            def spin(m, dt, i=i):
                m.rotate(dt * (2.0 + i * 0.3))
            s.add_updater(spin)

        self.add(shapes)
        self.wait(DURATION)

    # ── MIRROR PAIR ───────────────────────────────────────────────────────
    def do_mirror_pair(self):
        """Left and right groups move symmetrically."""
        n = max(2, min(N, 4))
        t = self._timer()
        left  = VGroup()
        right = VGroup()

        for i in range(n):
            y = (i - (n - 1) / 2) * 2.0
            lc = _make_shape(color=COLORS[i % len(COLORS)])
            rc = _make_shape(color=COLORS[(i + len(COLORS) // 2) % len(COLORS)])
            lc.move_to([-HW * 0.75, y, 0])
            rc.move_to([ HW * 0.75, y, 0])
            left.add(lc)
            right.add(rc)

        for i in range(n):
            base_y = left[i].get_center()[1]
            def upd_l(m, i=i, by=base_y):
                m.set_y(by + math.sin(t.get_value() * 2.2 + i * PI / n) * 1.4)
            def upd_r(m, i=i, by=base_y):
                m.set_y(by - math.sin(t.get_value() * 2.2 + i * PI / n) * 1.4)
            left[i].add_updater(upd_l)
            right[i].add_updater(upd_r)

        self.add(left, right)
        self.wait(DURATION)

    # ── WAVE GRID ─────────────────────────────────────────────────────────
    def do_wave_grid(self):
        """Grid of shapes doing a diagonal wave (3×5 landscape, 4×3 portrait)."""
        if VERTICAL:
            rows, cols = 4, 3
            sx, sy = 1.2, 2.2
        else:
            rows, cols = 3, 5
            sx, sy = 2.4, 2.1
        t = self._timer()
        shapes = VGroup()
        base_ys = []

        for r in range(rows):
            for c in range(cols):
                color = COLORS[(r * cols + c) % len(COLORS)]
                s = _make_shape(color=color, size=SIZE * 0.85)
                x = (c - (cols - 1) / 2) * sx
                y = (r - (rows - 1) / 2) * sy
                s.move_to([x, y, 0])
                shapes.add(s)
                base_ys.append(y)

        for i, (s, by) in enumerate(zip(shapes, base_ys)):
            r, c = i // cols, i % cols
            phase = (r + c) * PI / 3
            def upd(m, by=by, ph=phase):
                m.set_y(by + math.sin(t.get_value() * 2.5 + ph) * 0.85)
            s.add_updater(upd)

        self.add(shapes)
        self.wait(DURATION)

    # ── PENDULUM ──────────────────────────────────────────────────────────
    def do_pendulum(self):
        """Shapes hang from top and swing like pendulums."""
        n = min(N, 7)
        t = self._timer()
        spacing = min(HW * 1.6 / max(n, 1), 2.2)
        shapes  = VGroup()

        for i in range(n):
            s  = _make_shape(color=COLORS[i % len(COLORS)])
            ax = (i - (n - 1) / 2) * spacing
            ay = HH - 0.3
            arm   = HH * 0.55 + (i % 3) * 0.4
            freq  = 0.9 + i * 0.07
            phase = i * PI / n
            def upd(m, ax=ax, ay=ay, arm=arm, fr=freq, ph=phase):
                tv  = t.get_value()
                ang = math.sin(tv * fr + ph) * 0.55
                m.move_to([ax + arm * math.sin(ang), ay - arm * math.cos(ang), 0])
            s.add_updater(upd)
            shapes.add(s)

        self.add(shapes)
        self.wait(DURATION)

    # ── ORBIT LAYERS ──────────────────────────────────────────────────────
    def do_orbit_layers(self):
        """Inner ring CW, outer ring CCW — hypnotic double carousel."""
        t       = self._timer()
        n_inner = max(3, N // 2)
        n_outer = max(4, N - n_inner)
        r_inner = min(1.4, HW * 0.45)
        r_outer = min(2.8, HW * 0.85)

        inner = VGroup(*[_make_shape(color=COLORS[i % len(COLORS)],
                                     size=SIZE * 0.9)
                         for i in range(n_inner)])
        outer = VGroup(*[_make_shape(color=COLORS[(i + 3) % len(COLORS)],
                                     size=SIZE * 0.75)
                         for i in range(n_outer)])

        for i, s in enumerate(inner):
            def upd(m, i=i):
                ang = t.get_value() * 1.4 + i * TAU / n_inner
                m.move_to([r_inner * math.cos(ang), r_inner * math.sin(ang), 0])
            s.add_updater(upd)

        for i, s in enumerate(outer):
            def upd(m, i=i):
                ang = -t.get_value() * 0.9 + i * TAU / n_outer
                m.move_to([r_outer * math.cos(ang), r_outer * math.sin(ang), 0])
            s.add_updater(upd)

        self.add(inner, outer)
        self.wait(DURATION)

    # ── POPCORN ───────────────────────────────────────────────────────────
    def do_popcorn(self):
        """Shapes randomly pop up from random positions."""
        rng   = random.Random(PARAMS.get("seed", 5))
        iters = max(6, int(DURATION / 3.5))
        for it in range(iters):
            n_pop = rng.randint(2, min(5, N))
            pops  = VGroup()
            for i in range(n_pop):
                s = _make_shape(color=COLORS[(it * n_pop + i) % len(COLORS)])
                s.move_to([rng.uniform(-HW + 0.5, HW - 0.5),
                            rng.uniform(-HH + 0.5, HH - 0.5), 0])
                s.scale(0.01)
                pops.add(s)
            self.add(pops)
            self.play(LaggedStart(*[GrowFromCenter(s) for s in pops], lag_ratio=0.15),
                      run_time=0.6)
            self.wait(rng.uniform(0.4, 0.9))
            self.play(LaggedStart(*[s.animate.scale(0.01) for s in pops], lag_ratio=0.1),
                      run_time=0.5)
            self.remove(pops)
            self.wait(0.2)

    # ── HEARTBEAT ─────────────────────────────────────────────────────────
    def do_heartbeat(self):
        """Double-pulse rhythm like a heartbeat."""
        n = min(N, 5)
        shapes = _make_row(n=n)
        self.add(shapes)
        cycles = max(4, int(DURATION / 3.2))
        for _ in range(cycles):
            self.play(*[s.animate.scale(1.45) for s in shapes],
                      run_time=0.18, rate_func=rush_into)
            self.play(*[s.animate.scale(1 / 1.45) for s in shapes],
                      run_time=0.18, rate_func=rush_from)
            self.play(*[s.animate.scale(1.25) for s in shapes],
                      run_time=0.16, rate_func=rush_into)
            self.play(*[s.animate.scale(1 / 1.25) for s in shapes],
                      run_time=0.16, rate_func=rush_from)
            self.wait(1.6)

    # ── BREATHING ─────────────────────────────────────────────────────────
    def do_breathing(self):
        """Shapes slowly expand and contract, colors shift gently."""
        n   = min(N, 6)
        n_c = len(COLORS)
        t   = self._timer()
        shapes = _make_row(n=n)

        for i, s in enumerate(shapes):
            offset = i * 0.4
            def color_upd(m, off=offset):
                tv   = t.get_value()
                idx  = int((tv + off) / 4.0) % n_c
                nxt  = (idx + 1) % n_c
                frac = ((tv + off) / 4.0) % 1.0
                m.set_color(interpolate_color(ManimColor(COLORS[idx]),
                                              ManimColor(COLORS[nxt]), frac))
            s.add_updater(color_upd)

        self.add(shapes)
        cycles = max(4, int(DURATION / 5.0))
        for _ in range(cycles):
            self.play(*[s.animate.scale(1.55) for s in shapes],
                      run_time=2.0, rate_func=smooth)
            self.play(*[s.animate.scale(1 / 1.55) for s in shapes],
                      run_time=2.0, rate_func=smooth)
            self.wait(0.5)

    # ── SNAKE LINE ────────────────────────────────────────────────────────
    def do_snake_line(self):
        """Shapes follow a scrolling horizontal sine-wave path."""
        n = min(N, 8)
        t = self._timer()
        shapes = VGroup(*[
            _make_shape(color=COLORS[i % len(COLORS)]) for i in range(n)
        ])
        delay_step = 0.5

        for i, s in enumerate(shapes):
            d = i * delay_step
            def upd(m, d=d):
                tv = t.get_value()
                x  = HW - ((tv - d) * 1.2 % (HW * 2 + 1.0))
                y  = HH * 0.7 * math.sin((tv - d) * 1.5)
                m.move_to([x, y, 0])
            s.add_updater(upd)

        self.add(shapes)
        self.wait(DURATION)
