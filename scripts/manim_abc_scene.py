"""
Manim scene for ABC letter videos.
Each scene: big letter + matching sprite/shape + word + tagline, ~55s.
Audio added via ffmpeg (3 repetitions of letter audio).

Params via /tmp/manim_abc_params.json:
  letter:        str   "A"
  word:          str   "APPLE"
  letter_color:  str   hex color for the letter
  bg_color:      str   hex background
  sprite_path:   str | null  absolute path to PNG sprite (or null)
  vertical:      bool  (1080x1920 if true)
  total_duration float  seconds (default 55)
"""
import json
import math
from pathlib import Path
from manim import *

PARAMS_FILE = Path("/tmp/manim_abc_params.json")
PARAMS = json.loads(PARAMS_FILE.read_text()) if PARAMS_FILE.exists() else {}

VERTICAL = PARAMS.get("vertical", True)
if VERTICAL:
    config.pixel_width  = 1080
    config.pixel_height = 1920
    # Portrait: Manim frame_width=14.22, pixels_per_unit=76
    # x: ±7.11, y: ±12.64 actual frame bounds
    HW = 7.11
    HH = 12.64
else:
    config.pixel_width  = 1920
    config.pixel_height = 1080
    HW = 7.11
    HH = 4.0

config.frame_rate = 24


class ABCScene(Scene):
    def construct(self):
        letter       = PARAMS.get("letter", "A")
        word         = PARAMS.get("word", "APPLE")
        lcolor       = ManimColor(PARAMS.get("letter_color", "#FF4444"))
        bg_color     = PARAMS.get("bg_color", "#E3F2FD")
        sprite_path  = PARAMS.get("sprite_path", None)
        total_dur    = PARAMS.get("total_duration", 55.0)

        self.camera.background_color = ManimColor(bg_color)

        # ── MOBJECTS ──────────────────────────────────────────────────────────
        if VERTICAL:
            # Portrait 1080×1920: 1 unit ≈ 76px, HH=12.64 (full half-height)
            ltr_fs    = 380
            word_fs   = 96
            tag_fs    = 58
            ltr_y     = 8.0     # upper area: 608px above center (20% from top)
            sprite_y  = 1.5     # slightly above center
            word_y    = -6.5    # lower area
            tag_y     = -9.2    # near bottom
            sprite_h  = 5.0     # ~380px tall sprite
        else:
            # Landscape 1920×1080: 1 unit ≈ 135px, HH=4.0
            ltr_fs    = 420
            word_fs   = 100
            tag_fs    = 60
            ltr_y     = 2.0
            sprite_y  = 0.0
            word_y    = -2.0
            tag_y     = -3.0
            sprite_h  = 3.2

        big_letter = Text(letter, font_size=ltr_fs, color=lcolor,
                          stroke_color=WHITE, stroke_width=8,
                          weight=BOLD)
        big_letter.move_to([0, ltr_y, 0])

        word_text = Text(word, font_size=word_fs, color=lcolor,
                         stroke_color=WHITE, stroke_width=3,
                         weight=BOLD)
        word_text.move_to([0, word_y, 0])

        tagline = Text(f"{letter} is for {word.capitalize()}", font_size=tag_fs,
                       color=WHITE, stroke_color=lcolor, stroke_width=3)
        tagline.move_to([0, tag_y, 0])

        # Sprite or fallback shape
        if sprite_path and Path(sprite_path).exists():
            sprite = ImageMobject(sprite_path)
            sprite.height = sprite_h
            sprite.move_to([0, sprite_y, 0])
            has_sprite = True
        else:
            # Fallback: large colored star (no sprite available)
            r = sprite_h / 2.0
            sprite = Star(5, outer_radius=r, inner_radius=r * 0.45,
                          color=lcolor, fill_opacity=0.9, stroke_width=0)
            sprite.move_to([0, sprite_y, 0])
            has_sprite = False

        # ── PHASE 1: Letter intro (0 → ~18s) ─────────────────────────────────
        # Letter drops in from above
        big_letter.shift(UP * 16)
        self.play(big_letter.animate.shift(DOWN * 16),
                  run_time=1.0, rate_func=rush_into)

        # Audio lands at t ≈ 1.0s — pulse to reinforce
        self.play(big_letter.animate.scale(1.3),
                  run_time=0.9, rate_func=there_and_back)

        # Sprite slides in from right
        sprite.shift(RIGHT * 10)
        self.play(sprite.animate.shift(LEFT * 10),
                  run_time=0.8, rate_func=rush_into)

        self.wait(0.8)

        # Letter and sprite bounce together × 2
        for _ in range(2):
            self.play(
                big_letter.animate.scale(1.2),
                sprite.animate.scale(1.15),
                run_time=0.7, rate_func=there_and_back,
            )
        self.wait(0.5)

        # Word writes in
        self.play(Write(word_text), run_time=1.4)
        self.wait(2.0)

        # Phase 1 total so far: 1+0.9+0.8+0.8+0.7*2+0.5+1.4+2.0 = ~9.3s
        # Pad to 18s
        self.wait(max(0, 18.0 - 9.3 - 0.1))

        # ── PHASE 2: Tagline + repetition (18 → ~36s) ────────────────────────
        # Tagline fades in — audio 2nd play lands here (t ≈ 18s)
        self.play(FadeIn(tagline, shift=UP * 0.3), run_time=0.8)
        self.wait(0.5)

        # Highlight letter in tagline rhythm
        self.play(big_letter.animate.scale(1.35),
                  run_time=0.7, rate_func=there_and_back)
        self.wait(0.5)

        # Everything wiggles
        for _ in range(3):
            self.play(
                big_letter.animate.shift(LEFT * 0.15),
                sprite.animate.shift(RIGHT * 0.15),
                run_time=0.35, rate_func=there_and_back,
            )

        self.wait(1.0)

        # Word pulses × 2
        self.play(word_text.animate.scale(1.25),
                  run_time=0.6, rate_func=there_and_back)
        self.wait(0.4)
        self.play(word_text.animate.scale(1.25),
                  run_time=0.6, rate_func=there_and_back)

        self.wait(2.5)

        # Tagline pulses — phase 2 ends at ~36s
        self.play(tagline.animate.scale(1.2),
                  run_time=0.7, rate_func=there_and_back)

        # Phase 2 used: 0.8+0.5+0.7+0.5+3*(0.35+0.35)+1.0+0.6+0.4+0.6+2.5+0.7 ≈ 10s
        self.wait(max(0, 36.0 - 18.0 - 10.0 - 0.1))

        # ── PHASE 3: Final review (36 → 55s) ─────────────────────────────────
        # Fade out word and tagline, reintroduce freshly — audio 3rd play at t≈37s
        self.play(FadeOut(word_text), FadeOut(tagline), run_time=0.5)
        self.play(
            big_letter.animate.scale(1.0),  # ensure scale reset
            run_time=0.3,
        )
        self.wait(0.3)

        # Re-show word + tagline with bounce entrance
        self.play(
            FadeIn(word_text, scale=1.3),
            run_time=0.7,
        )
        self.play(
            FadeIn(tagline, scale=1.3),
            run_time=0.6,
        )
        self.wait(1.0)

        # Celebration: everything bounces together × 4
        for _ in range(4):
            self.play(
                big_letter.animate.shift(UP * 0.2),
                sprite.animate.shift(DOWN * 0.2),
                word_text.animate.shift(UP * 0.1),
                run_time=0.45, rate_func=there_and_back,
            )

        self.wait(1.5)

        # Final big pulse of letter
        self.play(big_letter.animate.scale(1.4),
                  run_time=0.8, rate_func=there_and_back)
        self.wait(2.0)

        # Phase 3 used: 0.5+0.3+0.3+0.7+0.6+1.0+4*0.45+1.5+0.8+2.0 ≈ 9.5s
        # Pad to 55s total
        elapsed_phase3 = 9.5
        remaining = total_dur - 36.0 - elapsed_phase3 - 1.5  # 1.5 for fadeout
        if remaining > 0:
            self.wait(remaining)

        # Fade out
        all_objs = [big_letter, sprite, word_text, tagline]
        self.play(*[FadeOut(o) for o in all_objs], run_time=1.0)
        self.wait(0.5)
