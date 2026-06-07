#!/usr/bin/env python3
"""
Generate a color learning short using Manim.
Each color: ~15s scene × 4 = 60s video.
Usage: python3 manim_color_short.py --color red --output output/test_manim_red.mp4
"""
import subprocess
import tempfile
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

COLORS_MAP = {
    "red":    {"hex": "#FF4444", "manim": "RED",    "emoji": "🔴"},
    "orange": {"hex": "#FF7F2A", "manim": "ORANGE",  "emoji": "🟠"},
    "yellow": {"hex": "#FFD700", "manim": "YELLOW",  "emoji": "🟡"},
    "green":  {"hex": "#27AE60", "manim": "GREEN",   "emoji": "🟢"},
    "blue":   {"hex": "#2980B9", "manim": "BLUE",    "emoji": "🔵"},
    "purple": {"hex": "#8E44AD", "manim": "PURPLE",  "emoji": "🟣"},
    "pink":   {"hex": "#FF69B4", "manim": "PINK",    "emoji": "🩷"},
    "brown":  {"hex": "#8B4513", "manim": "\"#8B4513\"", "emoji": "🟤"},
}

SCENE_TEMPLATE = '''
from manim import *
import math

COLOR_HEX = "{hex}"
COLOR_NAME = "{name}"
COLOR_MANIM = {manim}
BG_HEX = "{bg_hex}"

config.background_color = BG_HEX
config.pixel_height = 1920
config.pixel_width = 1080
config.frame_rate = 30


class ColorShort(Scene):
    def construct(self):
        self._scene_intro()    # ~15s: big circle + name
        self._scene_bounce()   # ~15s: square bouncing
        self._scene_multi()    # ~15s: 6 circles pulsing
        self._scene_outro()    # ~15s: finale

    def _scene_intro(self):
        # ~15s: big pulsing circle with color name
        circle = Circle(radius=2.5, color=COLOR_MANIM, fill_opacity=1, stroke_width=0)
        label = Text(COLOR_NAME, font_size=120, color=WHITE, weight=BOLD)
        label.set_stroke(BLACK, width=4)
        sub = Text("This is " + COLOR_NAME + "!", font_size=54, color=WHITE)
        sub.next_to(label, DOWN, buff=0.5)

        self.play(GrowFromCenter(circle), run_time=0.8)
        self.play(FadeIn(label, scale=0.5), run_time=0.6)
        self.play(FadeIn(sub, shift=UP * 0.2), run_time=0.5)
        self.wait(0.5)

        for _ in range(12):
            self.play(circle.animate.scale(1.07), rate_func=there_and_back, run_time=0.8)
            self.wait(0.25)

        self.play(FadeOut(circle), FadeOut(label), FadeOut(sub), run_time=0.6)

    def _scene_bounce(self):
        # ~15s: big square bouncing up and down
        shape = RoundedRectangle(
            corner_radius=0.6, width=3.8, height=3.8,
            color=COLOR_MANIM, fill_opacity=1, stroke_width=0
        )
        shape.move_to(DOWN * 0.5)
        label = Text(COLOR_NAME, font_size=88, color=WHITE, weight=BOLD)
        label.set_stroke(BLACK, width=3)
        label.next_to(shape, UP, buff=0.5)

        self.play(FadeIn(shape, shift=DOWN * 0.5), FadeIn(label, shift=DOWN * 0.5), run_time=0.6)
        self.wait(0.3)

        for _ in range(14):
            self.play(
                shape.animate.shift(UP * 1.3).scale(0.88),
                label.animate.shift(UP * 1.3),
                rate_func=rush_into, run_time=0.25
            )
            self.play(
                shape.animate.shift(DOWN * 1.3).scale(1 / 0.88),
                label.animate.shift(DOWN * 1.3),
                rate_func=rush_from, run_time=0.3
            )
            self.wait(0.15)

        self.wait(0.8)
        self.play(FadeOut(shape), FadeOut(label), run_time=0.5)

    def _scene_multi(self):
        # ~15s: six circles pulsing together
        label = Text(COLOR_NAME + "!", font_size=80, color=COLOR_MANIM, weight=BOLD)
        label.set_stroke(BLACK, width=3)
        label.to_edge(UP, buff=0.5)

        positions = [
            UP * 2.2 + LEFT * 1.8, UP * 2.2 + RIGHT * 1.8,
            ORIGIN + LEFT * 2.0, ORIGIN + RIGHT * 2.0,
            DOWN * 2.2 + LEFT * 1.8, DOWN * 2.2 + RIGHT * 1.8,
        ]
        shapes = VGroup(*[
            Circle(radius=0.75, color=COLOR_MANIM, fill_opacity=1, stroke_width=0).move_to(p)
            for p in positions
        ])

        self.play(LaggedStart(*[GrowFromCenter(s) for s in shapes], lag_ratio=0.1), run_time=1.0)
        self.play(FadeIn(label, scale=0.5), run_time=0.4)
        self.wait(0.5)

        for _ in range(9):
            self.play(shapes.animate.scale(1.18), rate_func=there_and_back, run_time=0.7)
            self.wait(0.35)

        self.wait(0.5)
        self.play(
            LaggedStart(*[s.animate.scale(0) for s in shapes], lag_ratio=0.08),
            run_time=0.9
        )
        self.play(FadeOut(label), run_time=0.4)

    def _scene_outro(self):
        # ~15s: finale with slow pulses
        big = Circle(radius=3.5, color=COLOR_MANIM, fill_opacity=0.92, stroke_width=0)
        word = Text(COLOR_NAME, font_size=120, color=WHITE, weight=BOLD)
        word.set_stroke(BLACK, width=5)
        sub = Text("Great job! ⭐", font_size=60, color=WHITE)
        sub.set_stroke(BLACK, width=2)
        sub.next_to(word, DOWN, buff=0.5)

        self.play(GrowFromCenter(big), run_time=0.7)
        self.play(FadeIn(word, scale=0.6), run_time=0.5)
        self.play(FadeIn(sub, shift=UP * 0.3), run_time=0.4)
        self.wait(0.3)

        for _ in range(8):
            self.play(big.animate.scale(1.05), rate_func=there_and_back, run_time=1.0)
            self.wait(0.4)

        self.wait(0.8)
        self.play(FadeOut(big), FadeOut(word), FadeOut(sub), run_time=0.8)
'''


def make_bg(hex_color: str) -> str:
    """Lighten the color for background."""
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    # Mix with white 85%
    r2 = int(r * 0.15 + 255 * 0.85)
    g2 = int(g * 0.15 + 255 * 0.85)
    b2 = int(b * 0.15 + 255 * 0.85)
    return f"#{r2:02X}{g2:02X}{b2:02X}"


def generate_color_short(color: str, output: Path, quality: str = "m") -> bool:
    info = COLORS_MAP.get(color.lower())
    if not info:
        print(f"Unknown color: {color}. Options: {list(COLORS_MAP.keys())}")
        return False

    bg_hex = make_bg(info["hex"])
    scene_code = SCENE_TEMPLATE.format(
        hex=info["hex"],
        name=color.capitalize(),
        manim=info["manim"],
        bg_hex=bg_hex,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        scene_file = Path(tmpdir) / "color_scene.py"
        scene_file.write_text(scene_code)

        cmd = [
            "manim",
            f"-q{quality}",          # qm=medium(854×480), qh=high(1920×1080), ql=low
            "--fps", "30",
            "--media_dir", tmpdir,
            str(scene_file),
            "ColorShort",
        ]
        print(f"Rendering {color} short...")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"Manim error:\n{result.stderr[-2000:]}")
            return False

        # Find rendered file
        rendered = list(Path(tmpdir).rglob("ColorShort.mp4"))
        if not rendered:
            print("No output file found")
            print(result.stdout[-1000:])
            return False

        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(rendered[0], output)
        size_mb = output.stat().st_size / 1024 / 1024
        print(f"✓ {output.name}  ({size_mb:.1f}MB)")
        return True


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--color", default="red", choices=list(COLORS_MAP.keys()))
    parser.add_argument("--output", default=None)
    parser.add_argument("--quality", default="m", choices=["l", "m", "h", "p"],
                        help="l=480p, m=720p, h=1080p, p=1440p")
    parser.add_argument("--all", action="store_true", help="Render all 8 colors")
    args = parser.parse_args()

    if args.all:
        for color in COLORS_MAP:
            out = ROOT / "output" / "queue" / f"manim_color_{color}.mp4"
            generate_color_short(color, out, args.quality)
    else:
        out = Path(args.output) if args.output else ROOT / "output" / f"test_manim_{args.color}.mp4"
        generate_color_short(args.color, out, args.quality)


if __name__ == "__main__":
    main()
