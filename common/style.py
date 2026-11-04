"""Shared visual style for all CompOrgVideo Manim videos.

Import from a renderer with the repository root on sys.path:

    from common.style import (INK, BLUE, ORANGE, YEL, Cell, StyleScene, txt, ...)

Colour rules (slide conventions, keep identical across videos):
  YEL     current cycle / current instruction highlight
  BLUE    value that just changed (reset to INK at the start of the next cycle)
  ORANGE  connection arrows / data movement
Subtitles: Korean, key terms with English in parentheses -> term("예약 스테이션", "reservation station").
Assumptions not on the slides are shown with the ASSUME prefix.

A scene using StyleScene must set `self.B` to a board object providing
  SUB_Y         y of the subtitle strip (default StyleScene.SUB_Y)
  phase_labels  VGroup of phase-name Texts (for set_phase)
  phase_hl      None initially (managed by set_phase)
"""
from __future__ import annotations

from manim import (BOLD, DOWN, LEFT, WHITE, AnimationGroup, Arrow, FadeIn, FadeOut,
                   Line, Rectangle, ReplacementTransform, RoundedRectangle, Scene,
                   Succession, Text, VGroup, VMobject, config)

config.background_color = WHITE

# ------------------------------------------------------------------ fonts ---
FONT = "Noto Sans CJK KR"
MONO = "DejaVu Sans Mono"

# ----------------------------------------------------------------- colours ---
INK = "#111111"
BLUE = "#1F4FE0"          # value that just changed (slide convention)
ORANGE = "#E39400"        # connection arrows (slide convention: gold/orange)
YEL = "#FFF0A8"           # current cycle highlight (slide convention)
YEL_STRONG = "#F2C200"
GREY = "#ECECEC"
RED = "#C62828"
FAINT = "#9E9E9E"

# ------------------------------------------------------------ conventions ---
PREDICT_SECONDS = 2.0     # pause before every cycle for prediction
ASSUME = "※ 강의 범위 밖 가정"
SUBSCRIPT = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")


def term(ko: str, en: str) -> str:
    """Korean term with English in parentheses: 예약 스테이션(reservation station)."""
    return f"{ko}({en})"


def lab(s: str) -> str:
    """'E3' -> 'E₃' (timing table notation)."""
    if len(s) > 1 and s[0] == "E" and s[1:].isdigit():
        return "E" + s[1:].translate(SUBSCRIPT)
    return s


def txt(s, size=16, color=INK, font=FONT, weight="NORMAL"):
    return Text(s, font=font, font_size=size, color=color, weight=weight)


def subtitle_box(y):
    """Light strip behind the subtitles."""
    box = Rectangle(width=14.1, height=0.92, stroke_color=FAINT, stroke_width=1)
    return box.set_fill("#FAFAFA", 1).move_to([0, y, 0])


# ------------------------------------------------------------------- cell ---
class Cell:
    """A table cell: border rectangle + text.  `change` returns the animation
    and updates `s` immediately, so call it only when the animation is played."""

    def __init__(self, x, y, w, h, s="", size=15, font=FONT, border=True):
        self.rect = Rectangle(width=w, height=h, stroke_color=INK,
                              stroke_width=1.1 if border else 0)
        self.rect.move_to([x, y, 0]).set_fill(WHITE, 0)
        self.size, self.font, self.s, self.color = size, font, s, INK
        self.text = self.make(s, INK)

    def make(self, s, color):
        t = Text(lab(s) if s else "0", font=self.font, font_size=self.size, color=color)
        if t.width > self.rect.width * 0.9:
            t.scale_to_fit_width(self.rect.width * 0.9)
        t.move_to(self.rect.get_center())
        if not s:
            t.set_opacity(0)
        return t

    def mobs(self):
        return VGroup(self.rect, self.text)

    def change(self, s, color=BLUE):
        """Return animation replacing the text."""
        new = self.make(s, color)
        old = self.text
        self.text, self.s, self.color = new, s, color
        return ReplacementTransform(old, new)

    def recolor(self, color):
        if self.s:
            self.text.set_color(color)
        self.color = color

    def fill(self, grey: bool):
        return self.rect.animate.set_fill(GREY if grey else WHITE, 1 if grey else 0)

    def set_fill_now(self, grey: bool):
        self.rect.set_fill(GREY if grey else WHITE, 1 if grey else 0)


# ------------------------------------------------------------------ scene ---
class StyleScene(Scene):
    """Pacing, subtitles, phase bar, prediction pause and shared effects."""

    SUB_Y = -3.33

    def setup(self):
        self.k = 1.0
        self.sub = None

    # pacing -------------------------------------------------------------
    def rt(self, t):
        return max(0.15, t * self.k)

    def pause(self, t):
        self.wait(max(0.1, t * self.k))

    # subtitles -----------------------------------------------------------
    def say(self, lines, wait=1.0):
        if isinstance(lines, str):
            lines = [lines]
        g = VGroup(*[txt(l, 18) for l in lines]).arrange(DOWN, buff=0.07, aligned_edge=LEFT)
        if g.width > 13.7:
            g.scale_to_fit_width(13.7)
        if g.height > 0.84:
            g.scale_to_fit_height(0.84)
        g.move_to([0, getattr(getattr(self, "B", None), "SUB_Y", self.SUB_Y), 0])
        anims = [FadeIn(g, run_time=self.rt(0.3))]
        if self.sub is not None:
            anims.append(FadeOut(self.sub, run_time=self.rt(0.2)))
        self.play(*anims)
        self.sub = g
        self.pause(wait)

    def set_phase(self, idx):
        lbl = self.B.phase_labels[idx]
        new = RoundedRectangle(corner_radius=0.06, width=lbl.width + 0.16, height=lbl.height + 0.14,
                               stroke_width=0).set_fill(YEL_STRONG, 0.55).move_to(lbl)
        new.set_z_index(-1)
        if self.B.phase_hl is None:
            self.play(FadeIn(new, run_time=self.rt(0.2)))
        else:
            self.play(ReplacementTransform(self.B.phase_hl, new, run_time=self.rt(0.25)))
        self.B.phase_hl = new

    # prediction pause -----------------------------------------------------
    def predict(self, c, hint="RAT · RS · 실행 유닛 · 버스를 보고 잠시 예측해 보세요"):
        veil = Rectangle(width=14.4, height=8.2, stroke_width=0).set_fill(WHITE, 0.82)
        box = RoundedRectangle(corner_radius=0.15, width=8.6, height=1.9, stroke_color=ORANGE,
                               stroke_width=3).set_fill(WHITE, 1)
        t1 = txt(f"다음 사이클(사이클 {c})에 무엇이 바뀔까?", 34, weight=BOLD)
        t2 = txt(hint, 20, FAINT)
        g = VGroup(box, VGroup(t1, t2).arrange(DOWN, buff=0.25))
        self.play(FadeIn(veil), FadeIn(g), run_time=0.3)
        self.wait(PREDICT_SECONDS)
        self.play(FadeOut(veil), FadeOut(g), run_time=0.3)

    # effects ----------------------------------------------------------------
    def polyline_arrow(self, pts):
        segs = VGroup()
        for a, b in zip(pts[:-2], pts[1:-1]):
            segs.add(Line(a, b, color=ORANGE, stroke_width=3))
        segs.add(Arrow(pts[-2], pts[-1], buff=0, color=ORANGE, stroke_width=3,
                       max_tip_length_to_length_ratio=0.5, max_stroke_width_to_length_ratio=40,
                       tip_length=0.13))
        path = VMobject().set_points_as_corners(pts)
        return segs, path

    def blink(self, rects):
        """Blink matched cells with separate overlay rectangles.

        The cell rectangles themselves are never animated here: animating them
        re-adds them on top of the cell text and restores their old (grey)
        fill, which hid the broadcast value.  The overlays are transparent in
        the middle (stroke + faint tint); call self.remove(*self.blink_overlays)
        after playing.
        """
        overlays = [Rectangle(width=r.width, height=r.height, stroke_color=ORANGE, stroke_width=4)
                    .set_fill("#CFE0FF", 0.35).move_to(r) for r in rects]
        self.blink_overlays = overlays
        on = AnimationGroup(*[FadeIn(o) for o in overlays])
        off = AnimationGroup(*[FadeOut(o) for o in overlays])
        on2 = AnimationGroup(*[FadeIn(o) for o in overlays])
        off2 = AnimationGroup(*[FadeOut(o) for o in overlays])
        return Succession(on, off, on2, off2, run_time=self.rt(1.0))

