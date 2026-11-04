"""Manim CE renderer for the Tomasulo trace.

Reads ONLY out/trace.json (path override: TOMASULO_TRACE).  No simulation value
is written in this file; everything shown is taken from the trace.

Scenes
  Intro       program + assumptions
  Cycles      cycle-by-cycle animation (TOMASULO_CYCLES="0-3" limits the range)
  Outro       in-order vs out-of-order timing comparison (slides 37-38)
  FullVideo   Intro + all cycles + Outro
"""
from __future__ import annotations

import json
import os
import sys

from manim import (BOLD, DOWN, LEFT, RIGHT, UP, WHITE, Arrow, Create, Dot, FadeIn,
                   FadeOut, Line, MoveAlongPath, Polygon, Rectangle,
                   ReplacementTransform, SurroundingRectangle, VGroup, Write)

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from common.style import (BLUE, FAINT, INK, MONO, ORANGE, RED, YEL, YEL_STRONG,  # noqa: E402
                          Cell, StyleScene, lab, subtitle_box, txt)

TRACE_PATH = os.environ.get(
    "TOMASULO_TRACE", os.path.join(os.path.dirname(__file__), "..", "out", "trace.json"))
with open(TRACE_PATH, encoding="utf-8") as fh:
    T = json.load(fh)

UNIT_KO = {"ADD": "덧셈기(adder)", "MUL": "곱셈기(multiplier)"}
UNIT_SYM = {"ADD": "+", "MUL": "×"}

CFG = T["config"]
PROG = CFG["program"]
NI = len(PROG)
REGS = CFG["registers"]
RS_IDS = CFG["rs_ids"]
NCOL = T["total_cycles"]
CYCLES = T["cycles"]
SLOW = set(T["presentation"]["slow_cycles"])


def instr_name(i: int) -> str:
    return f"I{i + 1}"


def instr_text(i: int) -> str:
    return PROG[i]["text_src_first"]


# ------------------------------------------------------------------ board ---
class Board:
    # geometry (Manim frame: x in [-7.1, 7.1], y in [-4, 4])
    PX0, PX1 = -7.0, -3.95                # program box
    TX0 = -3.85                           # timing table first column left edge
    TW = (6.95 - TX0) / NCOL
    TY0, TH = 3.30, 0.28                  # timing header y, row height
    RAT_TOP, RAT_H = 1.05, 0.31
    RAT_W = [0.75, 0.5, 0.45, 0.7]
    RAT_X0 = -7.0
    RS_TOP, RS_H = 1.05, 0.355
    RS_W = [0.55, 0.72, 0.85, 0.55, 0.72, 0.85]
    RS_X0 = {"ADD": -3.85, "MUL": 2.05}
    UNIT_TOP, UNIT_BOT = -1.33, -1.88
    OUT_Y = -2.12
    BUS_Y = {"ADD": -2.48, "MUL": -2.62}
    ROUTE_Y = 1.0
    GAP_X = -4.38
    RIGHT_X = 6.7
    SUB_Y = -3.33

    def __init__(self):
        self.g = VGroup()
        self._program()
        self._timing()
        self._rat()
        self._rs()
        self._units()
        self._phase_bar()
        self.title = txt("사이클 0", 26, weight=BOLD).move_to([-7.0, 3.73, 0], aligned_edge=LEFT)
        self.title.align_to([-7.0, 0, 0], LEFT)
        self.g.add(self.title)

    # program + timing table ----------------------------------------------
    def row_y(self, i):
        return self.TY0 - (i + 1) * self.TH

    def col_x(self, k):  # k = 1..NCOL
        return self.TX0 + (k - 0.5) * self.TW

    def _program(self):
        self.prog_rows = []
        for i in range(NI):
            t = txt(instr_text(i), 14, font=MONO)
            t.move_to([self.PX0 + 0.1, self.row_y(i), 0], aligned_edge=LEFT)
            self.prog_rows.append(t)
        box = Rectangle(width=self.PX1 - self.PX0, height=NI * self.TH + 0.08,
                        stroke_color=ORANGE, stroke_width=1.6)
        box.move_to([(self.PX0 + self.PX1) / 2, self.row_y((NI - 1) / 2), 0])
        cyc = txt("Cycle", 14).move_to([self.PX1 - 0.05, self.TY0, 0], aligned_edge=RIGHT)
        self.prog_box = box
        self.g.add(box, cyc, *self.prog_rows)
        self.prog_hl = None

    def _timing(self):
        self.tcells = {}
        self.theads = {}
        for k in range(1, NCOL + 1):
            h = Cell(self.col_x(k), self.TY0, self.TW, self.TH, "", 14, border=False)
            self.theads[k] = h
            self.g.add(h.text)
            for i in range(NI):
                c = Cell(self.col_x(k), self.row_y(i), self.TW, self.TH, "", 14, border=False)
                self.tcells[(i, k)] = c
                self.g.add(c.text)
        self.col_hl = None

    # RAT ----------------------------------------------------------------
    def rat_y(self, r):  # r index 0..10, header = -1
        return self.RAT_TOP - (r + 1.5) * self.RAT_H

    def rat_x(self, k):
        return self.RAT_X0 + sum(self.RAT_W[:k]) + self.RAT_W[k] / 2

    def _rat(self):
        self.rat = {}
        for k, h in enumerate(["Register", "Valid", "Tag", "Value"]):
            c = Cell(self.rat_x(k), self.rat_y(-1), self.RAT_W[k], self.RAT_H, h, 13)
            self.g.add(c.mobs())
        st = CYCLES[0]["state"]["rat_display"]
        for r, reg in enumerate(REGS):
            row = [Cell(self.rat_x(0), self.rat_y(r), self.RAT_W[0], self.RAT_H, reg, 13)]
            for k in range(3):
                row.append(Cell(self.rat_x(k + 1), self.rat_y(r), self.RAT_W[k + 1],
                                self.RAT_H, st[reg][k], 13))
            self.rat[reg] = row[1:]
            self.g.add(*[c.mobs() for c in row])
        self.apply_rat_fills(st, now=True)
        cap = txt("레지스터 별칭 테이블 (RAT)", 13, weight=BOLD)
        cap.move_to([(self.RAT_X0 + self.RAT_X0 + sum(self.RAT_W)) / 2, self.RAT_TOP + 0.13, 0])
        self.g.add(cap)

    def rat_fill_flags(self, row):
        valid = row[0] == "1"
        return [False, valid, not valid]

    def apply_rat_fills(self, st, now=False):
        anims = []
        for reg in REGS:
            for k, grey in enumerate(self.rat_fill_flags(st[reg])):
                if now:
                    self.rat[reg][k].set_fill_now(grey)
                else:
                    anims.append(self.rat[reg][k].fill(grey))
        return anims

    # RS -----------------------------------------------------------------
    def rs_x(self, op, k):
        return self.RS_X0[op] + sum(self.RS_W[:k]) + self.RS_W[k] / 2

    def rs_y(self, j):  # entry index; -2,-1 = header rows
        return self.RS_TOP - (j + 2.5) * self.RS_H

    def rs_table_of(self, e):
        return "ADD" if e in RS_IDS["ADD"] else "MUL"

    def _rs(self):
        self.rs = {}
        self.rs_row_of = {}
        for op in ("ADD", "MUL"):
            x0 = self.RS_X0[op]
            for s in range(2):
                xs = [self.rs_x(op, 3 * s + k) for k in range(3)]
                t = txt(f"Source {s + 1}", 13).move_to([sum(xs) / 3, self.rs_y(-2), 0])
                self.g.add(t)
                for k, h in enumerate(["V", "Tag", "Value"]):
                    self.g.add(txt(h, 12).move_to([xs[k], self.rs_y(-1), 0]))
            sep = Line([self.rs_x(op, 3) - self.RS_W[3] / 2, self.rs_y(-2.4), 0],
                       [self.rs_x(op, 3) - self.RS_W[3] / 2, self.rs_y(3.5), 0],
                       color=INK, stroke_width=2.5)
            self.g.add(sep)
            for j, e in enumerate(RS_IDS[op]):
                self.g.add(txt(e, 14).move_to([x0 - 0.17, self.rs_y(j), 0]))
                row = [Cell(self.rs_x(op, k), self.rs_y(j), self.RS_W[k], self.RS_H, "", 14)
                       for k in range(6)]
                self.rs[e] = row
                self.rs_row_of[e] = j
                self.g.add(*[c.mobs() for c in row])
            w = sum(self.RS_W)
            cap = txt(f"{op}용 예약 스테이션 (RS)", 13, weight=BOLD)
            cap.move_to([x0 + w / 2, self.RS_TOP + 0.29, 0])
            self.g.add(cap)

    def rs_fill_flags(self, row):
        if not any(row):
            return [False] * 6
        out = []
        for s in range(2):
            v = row[3 * s]
            out += [False, False, v == "0"]
        return out

    def rs_row_group(self, e):
        return VGroup(*[c.rect for c in self.rs[e]])

    # units + buses --------------------------------------------------------
    def unit_cx(self, op):
        return self.RS_X0[op] + sum(self.RS_W) / 2

    def _units(self):
        self.unit = {}
        self.out_tag, self.out_val = {}, {}
        self.countdown = {}
        for op in ("ADD", "MUL"):
            cx = self.unit_cx(op)
            poly = Polygon([cx - 1.25, self.UNIT_TOP, 0], [cx - 0.12, self.UNIT_TOP, 0],
                           [cx, self.UNIT_TOP - 0.12, 0], [cx + 0.12, self.UNIT_TOP, 0],
                           [cx + 1.25, self.UNIT_TOP, 0], [cx + 0.75, self.UNIT_BOT, 0],
                           [cx - 0.75, self.UNIT_BOT, 0], color=INK, stroke_width=1.6)
            poly.set_fill(WHITE, 1)
            sym = txt(UNIT_SYM[op], 24).move_to([cx, (self.UNIT_TOP + self.UNIT_BOT) / 2 - 0.04, 0])
            self.unit[op] = VGroup(poly, sym)
            tb = Cell(cx - 0.3, self.OUT_Y, 0.55, 0.3, "", 14)
            vb = Cell(cx + 0.3, self.OUT_Y, 0.55, 0.3, "", 14)
            self.out_tag[op], self.out_val[op] = tb, vb
            lt = txt("Tag", 12, RED).next_to(tb.rect, LEFT, buff=0.08)
            lv = txt("Value", 12, RED).next_to(vb.rect, RIGHT, buff=0.08)
            drops = VGroup(Line([cx - 0.3, self.OUT_Y - 0.15, 0], [cx - 0.3, self.BUS_Y[op], 0]),
                           Line([cx + 0.3, self.OUT_Y - 0.15, 0], [cx + 0.3, self.BUS_Y[op], 0]),
                           Line([cx - 0.3, self.UNIT_BOT, 0], [cx - 0.3, self.OUT_Y + 0.15, 0]),
                           Line([cx + 0.3, self.UNIT_BOT, 0], [cx + 0.3, self.OUT_Y + 0.15, 0]))
            drops.set_stroke(FAINT, 1.2)
            bus = Line([self.GAP_X, self.BUS_Y[op], 0], [self.RIGHT_X, self.BUS_Y[op], 0])
            bus.set_stroke(FAINT, 1.4)
            self.countdown[op] = VGroup()
            self.g.add(bus, drops, self.unit[op], tb.mobs(), vb.mobs(), lt, lv)
        bl = txt("Tag/Value 버스 (위: ADD, 아래: MUL)", 11, FAINT)
        bl.move_to([1.25, self.BUS_Y["MUL"] - 0.12, 0])
        self.g.add(bl)

    # phase indicator + subtitle ---------------------------------------------
    def _phase_bar(self):
        names = ["① Decode & Allocate", "② Wake-up / Select",
                 "③ Dispatch & Execute", "④ Broadcast"]
        self.phase_labels = VGroup(*[txt(n, 14) for n in names]).arrange(RIGHT, buff=0.35)
        self.phase_labels.move_to([2.45, 3.73, 0])
        self.phase_hl = None
        self.g.add(self.phase_labels)
        self.sub_box = subtitle_box(self.SUB_Y)
        self.g.add(self.sub_box)

    # geometry helpers ----------------------------------------------------
    def rs_cell(self, e, src, k):  # k: 0=V,1=Tag,2=Value
        return self.rs[e][3 * src + k]


# ------------------------------------------------------------------ scene ---
class TomasuloBase(StyleScene):
    # board state ----------------------------------------------------------
    def build_board(self, animate=True):
        self.B = Board()
        self.disp_rat = {r: list(v) for r, v in CYCLES[0]["state"]["rat_display"].items()}
        self.disp_rs = {e: list(v) for e, v in CYCLES[0]["state"]["rs_display"].items()}
        self.blue_cells = []
        if animate:
            self.play(FadeIn(self.B.g, run_time=1.2))
        else:
            self.add(self.B.g)

    def diff_anims(self, rat_disp, rs_disp, only=None):
        """Animations turning displayed tables into the given display state."""
        anims, changed = [], []
        for reg in REGS:
            new = rat_disp[reg]
            if new != self.disp_rat[reg]:
                for k in range(3):
                    if new[k] != self.disp_rat[reg][k]:
                        c = self.B.rat[reg][k]
                        anims.append(c.change(new[k]))
                        changed.append(c)
                for k, grey in enumerate(self.B.rat_fill_flags(new)):
                    anims.append(self.B.rat[reg][k].fill(grey))
                self.disp_rat[reg] = list(new)
        for e in self.disp_rs:
            new = rs_disp[e]
            if new != self.disp_rs[e]:
                for k in range(6):
                    if new[k] != self.disp_rs[e][k]:
                        c = self.B.rs[e][k]
                        anims.append(c.change(new[k]))
                        changed.append(c)
                for k, grey in enumerate(self.B.rs_fill_flags(new)):
                    anims.append(self.B.rs[e][k].fill(grey))
                self.disp_rs[e] = list(new)
        self.blue_cells += changed
        return anims, changed

    def play_diff(self, state, rt=0.6):
        anims, changed = self.diff_anims(state["rat_display"], state["rs_display"])
        if anims:
            self.play(*anims, run_time=self.rt(rt))
        return changed

    def timing_write(self, c, labels_for):
        """Write the cells of column c whose label passes labels_for(label)."""
        col = CYCLES[c]["column"]
        anims = []
        for i in range(NI):
            s = col[i]
            cell = self.B.tcells[(i, c)]
            if s and labels_for(s) and cell.s != s:
                anims.append(cell.change(s, INK))
        if anims:
            self.play(*anims, run_time=self.rt(0.4))

    def update_countdown(self, state):
        anims = []
        for op in ("ADD", "MUL"):
            lines = []
            for u in state["units"][op]:
                lines.append(txt(f"{u['rs']}: {lab('E' + str(u['stage']))} · 남은 {u['countdown']}",
                                 15, ORANGE if u["stage"] == 1 else INK, weight=BOLD))
            new = VGroup(*lines).arrange(DOWN, buff=0.05, aligned_edge=LEFT) if lines else VGroup()
            if lines:
                cx = self.B.unit_cx(op)
                y = (self.B.UNIT_TOP + self.B.UNIT_BOT) / 2
                if op == "ADD":   # right of the adder, left of the multiplier
                    new.move_to([cx + 1.3, y, 0], aligned_edge=LEFT)
                else:
                    new.move_to([cx - 1.3, y, 0], aligned_edge=RIGHT)
            old = self.B.countdown[op]
            if len(old) or len(new):
                anims.append(FadeOut(old))
                anims.append(FadeIn(new))
            self.B.countdown[op] = new
        if anims:
            self.play(*anims, run_time=self.rt(0.4))

    # arrows -----------------------------------------------------------------
    def route_to_rs(self, start, e, src, k=2, side=None, off=0.0, from_bus=None):
        """Route: start -> (bus) -> side -> over the RS tables -> down into a cell."""
        cell = self.B.rs_cell(e, src, k).rect
        table = self.B.rs_table_of(e)
        if side is None:
            side = self.B.GAP_X if table == "ADD" else self.B.RIGHT_X
        x, y = start[0], start[1]
        pts = [start]
        if from_bus is not None:
            pts.append([x, from_bus, 0])
            y = from_bus
        pts += [[side + off, y, 0], [side + off, self.B.ROUTE_Y + off, 0],
                [cell.get_center()[0], self.B.ROUTE_Y + off, 0],
                [cell.get_center()[0], cell.get_top()[1] + 0.01, 0]]
        return self.polyline_arrow(pts)

    def route_to_rat(self, start, reg, bus_y):
        cell = self.B.rat[reg][2].rect
        pts = [start, [start[0], bus_y, 0], [self.B.GAP_X, bus_y, 0],
               [self.B.GAP_X, cell.get_center()[1], 0], [cell.get_right()[0] + 0.01, cell.get_center()[1], 0]]
        return self.polyline_arrow(pts)

    def check_board(self, st, where):
        """Assert that what is on screen equals the trace display state:
        cell text, grey fill, text visible and drawn above its own cell."""
        B = self.B
        fam = self.get_mobject_family_members()
        pos = {id(m): k for k, m in enumerate(fam)}
        errs = []

        def chk(name, cell, exp, grey):
            if cell.s != exp:
                errs.append(f"{name}: 화면 '{cell.s}' / trace '{exp}'")
            if exp:
                t = cell.text
                if id(t) not in pos:
                    errs.append(f"{name}: 글자가 화면에 없음")
                elif t.get_fill_opacity() < 0.5:
                    errs.append(f"{name}: 글자가 투명함")
                elif cell.rect.get_fill_opacity() > 0.05 and pos[id(t)] < pos.get(id(cell.rect), -1):
                    errs.append(f"{name}: 글자가 칸 채우기 아래에 가려짐")
            actual_grey = cell.rect.get_fill_opacity() > 0.5
            if actual_grey != grey:
                errs.append(f"{name}: 회색 채우기 {actual_grey} / 기대 {grey}")

        for reg in REGS:
            exp = st["rat_display"][reg]
            for k, grey in enumerate(B.rat_fill_flags(exp)):
                chk(f"RAT {reg}[{k}]", B.rat[reg][k], exp[k], grey)
        for e in B.rs:
            exp = st["rs_display"][e]
            for k, grey in enumerate(B.rs_fill_flags(exp)):
                chk(f"RS {e}[{k}]", B.rs[e][k], exp[k], grey)
        self.checks_done = getattr(self, "checks_done", 0) + 1
        if errs:
            raise RuntimeError(f"화면/trace 불일치 ({where}):\n  " + "\n  ".join(errs))

    # ------------------------------------------------------------- cycles ---
    def cycle_speed(self, c):
        C = CYCLES[c]
        kinds = {e["type"] for p in C["phases"] for e in p["events"]}
        if c in SLOW:
            return 1.5
        if kinds & {"decode_alloc", "select", "dispatch", "broadcast"}:
            return 1.0
        return 0.45

    def start_cycle(self, c):
        B = self.B
        for cell in self.blue_cells:
            cell.recolor(INK)
        self.blue_cells = []
        anims = []
        new_title = txt(f"사이클 {c}", 26, weight=BOLD).move_to(B.title, aligned_edge=LEFT)
        anims.append(ReplacementTransform(B.title, new_title))
        B.title = new_title
        hl = Rectangle(width=B.TW, height=(NI + 1) * B.TH + 0.06, stroke_width=0)
        hl.set_fill(YEL, 1).move_to([B.col_x(c), B.TY0 - NI * B.TH / 2, 0]).set_z_index(-2)
        anims.append(FadeIn(hl) if B.col_hl is None else ReplacementTransform(B.col_hl, hl))
        B.col_hl = hl
        anims.append(B.theads[c].change(str(c), INK))
        for op in ("ADD", "MUL"):
            for cell in (B.out_tag[op], B.out_val[op]):
                if cell.s:
                    anims.append(cell.change("", INK))
        if B.prog_hl is not None:
            anims.append(FadeOut(B.prog_hl))
            B.prog_hl = None
        self.play(*anims, run_time=self.rt(0.5))

    def play_cycle(self, c):
        self.k = self.cycle_speed(c) if c > 0 else 1.0
        if c == 0:
            st = CYCLES[0]["state"]
            n_rs = sum(len(v) for v in RS_IDS.values())
            self.say([f"사이클 0 — 초기 상태: 예약 스테이션(reservation station) {n_rs}개는 모두 비어 있음(Invalid),",
                      f"레지스터 별칭 테이블(RAT)의 {len(st['rat'])}개 레지스터는 모두 Valid — 값은 레지스터 파일의 값 그대로"],
                     wait=3.0)
            return
        self.predict(c)
        self.start_cycle(c)
        phases = {p["phase"]: p for p in CYCLES[c]["phases"]}
        self.phase_decode(c, phases["decode"])
        self.check_board(phases["decode"]["state"], f"사이클 {c} ①")
        self.phase_select(c, phases["select"])
        self.check_board(phases["select"]["state"], f"사이클 {c} ②")
        self.phase_execute(c, phases["execute"])
        self.check_board(phases["execute"]["state"], f"사이클 {c} ③")
        self.phase_broadcast(c, phases["broadcast"])
        self.check_board(phases["broadcast"]["state"], f"사이클 {c} ④")

    # ① ---------------------------------------------------------------------
    def phase_decode(self, c, ph):
        B = self.B
        self.set_phase(0)
        ev = {e["type"]: e for e in ph["events"]}
        lines = []
        if "decode_alloc" in ev:
            d, rn = ev["decode_alloc"], ev["rename"]
            i, e = d["instr"], d["rs"]
            row = B.prog_rows[i]
            hl = Rectangle(width=B.PX1 - B.PX0 - 0.04, height=B.TH, stroke_width=0)
            hl.set_fill(YEL, 1).move_to([(B.PX0 + B.PX1) / 2, row.get_center()[1], 0]).set_z_index(-2)
            B.prog_hl = hl
            self.play(FadeIn(hl), run_time=self.rt(0.3))
            self.timing_write(c, lambda s: s in ("D",))
            lines.append(f"① 디코드·할당(Decode & Allocate): {instr_name(i)}  {instr_text(i)}  →  "
                         f"예약 스테이션(reservation station) {e}")
            self.say(lines, wait=0.6)
            # sources: RAT -> RS
            src_txt = []
            outlines, arrows = [], []
            for k, s in enumerate(d["sources"]):
                reg = s["reg"]
                rr = VGroup(*[cc.rect for cc in B.rat[reg]])
                outlines.append(SurroundingRectangle(rr, color=ORANGE, buff=0.01, stroke_width=3))
                start = [B.rat[reg][2].rect.get_right()[0], B.rat[reg][2].rect.get_center()[1], 0]
                segs, _ = self.route_to_rs(start, e, k, k=1 if s["copied"] == "tag" else 2,
                                           off=0.06 * k)
                arrows.append(segs)
                src_txt.append(f"{reg}: Valid → 값 {s['value']} 복사" if s["copied"] == "value"
                               else f"{reg}: 아직 계산 중(Valid=0) → 태그(tag) {s['tag']} 복사")
            self.say(lines + ["소스 피연산자(source)를 RAT에서 읽기 —  " + ",   ".join(src_txt)], wait=0.2)
            self.play(*[Create(o) for o in outlines], run_time=self.rt(0.4))
            self.play(*[Create(a, lag_ratio=1) for a in arrows], run_time=self.rt(1.0))
            st = ph["state"]
            rs_only = dict(self.disp_rs)
            rs_only[e] = st["rs_display"][e]
            anims, _ = self.diff_anims(self.disp_rat, rs_only)
            self.play(*anims, run_time=self.rt(0.6))
            self.pause(0.6)
            self.play(*[FadeOut(a) for a in arrows], *[FadeOut(o) for o in outlines],
                      run_time=self.rt(0.3))
            # rename destination
            reg = rn["reg"]
            rr = VGroup(*[cc.rect for cc in B.rat[reg]])
            o = SurroundingRectangle(rr, color=ORANGE, buff=0.01, stroke_width=3)
            extra = (f"  ({reg}는 이미 {rn['previous_tag']}로 renaming되어 있었음 → 두 번째 renaming)"
                     if rn["previous_tag"] else "")
            self.say(lines + [f"목적 레지스터(destination) {reg} 이름 바꾸기(renaming): "
                              f"Valid=0, Tag={rn['tag']}  — 이제 {reg}의 새 값은 RS {rn['tag']}가 만든다" + extra],
                     wait=0.2)
            self.play(Create(o), run_time=self.rt(0.3))
            self.play_diff(st)
            self.pause(1.0)
            self.play(FadeOut(o), run_time=self.rt(0.2))
        if "fetch" in ev:
            self.timing_write(c, lambda s: s == "F")
            f = ev["fetch"]["instr"]
            note = f"인출(Fetch): {instr_name(f)}  {instr_text(f)}  (다음 사이클에 디코드)"
            if "decode_alloc" not in ev:
                self.say([f"① 디코드할 명령어 없음 — {note}"], wait=0.8)
            else:
                self.say([f"① 동시에 {note}"], wait=0.6)
        if not ev:
            self.say(["① 디코드·할당: 할 일 없음 — 6개 명령어 모두 이미 renaming 완료"], wait=0.5)

    # ② ---------------------------------------------------------------------
    def phase_select(self, c, ph):
        B = self.B
        self.set_phase(1)
        sel = [e for e in ph["events"] if e["type"] == "select"]
        wait_ev = [e for e in ph["events"] if e["type"] == "waiting"]
        lines, marks = [], []
        for e in sel:
            r = SurroundingRectangle(B.rs_row_group(e["rs"]), color=YEL_STRONG, buff=0.02, stroke_width=5)
            bg = SurroundingRectangle(B.rs_row_group(e["rs"]), buff=0.0, stroke_width=0)
            bg.set_fill(YEL, 1).set_z_index(-1)
            marks += [bg, r]
            lines.append(f"RS {e['rs']}: 두 소스 모두 Valid → 웨이크업(wake-up), {UNIT_KO[e['unit']]}로 선택(select)")
        for e in wait_ev:
            if e["just_ready"]:
                lines.append(f"RS {e['rs']}: 방금 준비됨 → 다음 사이클부터 선택 가능")
                continue
            for k in range(2):
                cell = B.rs_cell(e["rs"], k, 1)
                if cell.s and cell.s != "~":
                    marks.append(SurroundingRectangle(cell.rect, color=RED, buff=0.0, stroke_width=3))
            lines.append(f"RS {e['rs']}: 태그 {', '.join(e['missing_tags'])}의 결과를 기다리는 중 (대기)")
        if not sel and not wait_ev:
            self.say(["② 웨이크업/선택(Wake-up/Select): 대기 중인 엔트리 없음"], wait=0.4)
            return
        head = "② 웨이크업/선택(Wake-up/Select): "
        if not sel:
            head += "실행할 수 있는 엔트리 없음"
        self.say([head] + lines[:2] + ([" · ".join(lines[2:])] if lines[2:] else []), wait=0.2)
        if marks:
            self.play(*[FadeIn(m) for m in marks], run_time=self.rt(0.4))
        self.pause(1.0)
        self.select_marks = [m for m in marks if m.get_z_index() == -1]
        rest = [m for m in marks if m.get_z_index() != -1]
        if rest:
            self.play(*[FadeOut(m) for m in rest], run_time=self.rt(0.25))

    # ③ ---------------------------------------------------------------------
    def phase_execute(self, c, ph):
        B = self.B
        self.set_phase(2)
        disp = [e for e in ph["events"] if e["type"] == "dispatch"]
        exe = [e for e in ph["events"] if e["type"] == "execute"]
        lines = []
        arrows = []
        for d in disp:
            cx = B.unit_cx(d["unit"])
            for k in range(2):
                cell = B.rs_cell(d["rs"], k, 2).rect
                tx = cx - 0.6 + 1.2 * k
                pts = [cell.get_bottom(), [cell.get_center()[0], B.UNIT_TOP + 0.25, 0],
                       [tx, B.UNIT_TOP + 0.25, 0], [tx, B.UNIT_TOP + 0.01, 0]]
                arrows.append(self.polyline_arrow(pts)[0])
            a, b = d["operands"]
            lines.append(f"③ 디스패치·실행(Dispatch & Execute): RS {d['rs']} → {UNIT_KO[d['unit']]}  "
                         f"({a} {UNIT_SYM[d['unit']]} {b},  {d['latency']}사이클 걸림)")
        prog = [f"{e['rs']}: {lab('E' + str(e['stage']))}/{e['latency']}" for e in exe
                if not any(d["rs"] == e["rs"] for d in disp)]
        if prog:
            lines.append(("실행 중(파이프라인): " if disp else "③ 실행 계속(파이프라인): ") + ",  ".join(prog))
        if not lines:
            lines = ["③ 디스패치·실행: 실행 중인 연산 없음"]
        self.say(lines, wait=0.2)
        if arrows:
            self.play(*[Create(a, lag_ratio=1) for a in arrows], run_time=self.rt(0.8))
        self.timing_write(c, lambda s: s == "-" or s.startswith("E"))
        self.update_countdown(ph["state"])
        self.pause(0.8 if disp else 0.4)
        if arrows:
            self.play(*[FadeOut(a) for a in arrows], run_time=self.rt(0.25))
        if getattr(self, "select_marks", None):
            self.play(*[FadeOut(m) for m in self.select_marks], run_time=self.rt(0.2))
            self.select_marks = []

    # ④ ---------------------------------------------------------------------
    def phase_broadcast(self, c, ph):
        B = self.B
        self.set_phase(3)
        bcs = [e for e in ph["events"] if e["type"] == "broadcast"]
        wbs = [e for e in ph["events"] if e["type"] == "writeback"]
        for b in bcs:
            op = b["unit"]
            cx = B.unit_cx(op)
            self.play(B.out_tag[op].change(b["tag"], INK), B.out_val[op].change(str(b["value"]), INK),
                      run_time=self.rt(0.4))
            arrows, paths, rects = [], [], []
            names = []
            for m in b["matches"]:
                if m["kind"] == "rs":
                    segs, path = self.route_to_rs([cx, B.OUT_Y - 0.15, 0], m["rs"], m["src"], k=2,
                                                  from_bus=B.BUS_Y[op])
                    rects += [B.rs_cell(m["rs"], m["src"], k).rect for k in range(3)]
                    names.append(f"RS {m['rs']} Source {m['src'] + 1}")
                else:
                    segs, path = self.route_to_rat([cx, B.OUT_Y - 0.15, 0], m["reg"], B.BUS_Y[op])
                    rects += [cc.rect for cc in B.rat[m["reg"]]]
                    names.append(f"RAT {m['reg']}")
                arrows.append(segs)
                paths.append(path)
            dst = b["dst"]
            after = b["after"]
            note = ""
            if not any(m["kind"] == "rat" for m in b["matches"]):
                cur = after["rat_display"][dst][1]
                note = f"   ※ RAT {dst}는 이미 {cur}로 renaming되었으므로 갱신하지 않음"
            self.say([f"④ 브로드캐스트(Broadcast): RS {b['tag']} 완료 → {UNIT_KO[op]} 버스에 태그 {b['tag']}, 값 {b['value']}",
                      "태그가 일치하는 칸이 값을 받음: " + ", ".join(names) + note], wait=0.2)
            dots = [Dot(p.get_start(), radius=0.07, color=ORANGE) for p in paths]
            self.play(*[Create(a, lag_ratio=1) for a in arrows],
                      *[MoveAlongPath(d, p) for d, p in zip(dots, paths)], run_time=self.rt(1.2))
            self.play(*[FadeOut(d) for d in dots], run_time=0.15)
            anims, _ = self.diff_anims(after["rat_display"], after["rs_display"])
            self.play(self.blink(rects), *anims, run_time=self.rt(1.0))
            self.remove(*self.blink_overlays)
            self.check_board(after, f"사이클 {c} ④ broadcast {b['tag']}")
            self.pause(1.0)
            self.play(*[FadeOut(a) for a in arrows], run_time=self.rt(0.3))
        # writeback column + remaining changes
        self.timing_write(c, lambda s: s == "W")
        self.play_diff(ph["state"])
        self.update_countdown(ph["state"])
        lines = []
        if wbs:
            lines.append("W(쓰기 완료): " + ", ".join(instr_name(w["instr"]) for w in wbs)
                         + " — 값은 이전 사이클의 broadcast에서 이미 전달됨")
        ready = [o["rs"] for o in CYCLES[c]["outlook"] if o["ready_next"]]
        blocked = [f"RS {o['rs']}(태그 {', '.join(o['missing_tags'])} 대기)"
                   for o in CYCLES[c]["outlook"] if not o["ready_next"]]
        nxt = []
        if ready:
            nxt.append("다음 사이클에 실행 가능: RS " + ", ".join(ready))
        if blocked:
            nxt.append("아직 실행 불가: " + ", ".join(blocked))
        if nxt:
            lines.append("→ " + "   |   ".join(nxt))
        if not bcs:
            lines.insert(0, "④ 브로드캐스트(Broadcast): 이번 사이클에 끝나는 연산 없음")
        if lines and (wbs or nxt or not bcs):
            self.say(lines[:3], wait=1.0)
        else:
            self.pause(0.6)

    # ----------------------------------------------------------- intro ----
    def intro(self):
        title = txt("Tomasulo 알고리즘 — 사이클 단위로 따라가기", 40, weight=BOLD).to_edge(UP, buff=0.5)
        src = txt("ETH DDCA · L14 Out-of-Order Execution · 슬라이드 36–63", 20, FAINT).next_to(title, DOWN)
        self.play(Write(title), FadeIn(src), run_time=1.5)
        left = VGroup(txt("슬라이드 36 표기 (목적지 ← 소스)", 18, weight=BOLD),
                      *[txt(p["text_dst_first"], 18, font=MONO) for p in PROG]).arrange(DOWN, aligned_edge=LEFT, buff=0.12)
        right = VGroup(txt("슬라이드 40 이후 표기 (소스 → 목적지)", 18, weight=BOLD),
                       *[txt(p["text_src_first"], 18, font=MONO) for p in PROG]).arrange(DOWN, aligned_edge=LEFT, buff=0.12)
        progs = VGroup(left, right).arrange(RIGHT, buff=1.4).next_to(src, DOWN, buff=0.45)
        same = txt("= 같은 프로그램", 20, ORANGE, weight=BOLD).next_to(progs, DOWN, buff=0.2)
        self.play(FadeIn(left), run_time=0.8)
        self.play(FadeIn(right), FadeIn(same), run_time=0.8)
        self.wait(3)
        lat, units, iv = CFG["latency"], CFG["units"], CFG["initial_values"]
        regs = CFG["registers"]
        rs = CFG["rs_ids"]
        bullets = [
            f"• 실행 시간: ADD {lat['ADD']}사이클, MUL {lat['MUL']}사이클",
            f"• 덧셈기(adder) {units['ADD']['count']}개, 곱셈기(multiplier) {units['MUL']['count']}개 — "
            + ("둘 다 파이프라인화(pipelined): 매 사이클 새 연산을 받을 수 있음"
               if units['ADD']['pipelined'] and units['MUL']['pipelined'] else "파이프라인 아님"),
            f"• 초기 레지스터 값: {regs[0]}..{regs[-1]} = {iv[regs[0]]}..{iv[regs[-1]]}, 모두 Valid",
            f"• 예약 스테이션(reservation station): ADD용 {rs['ADD'][0]}–{rs['ADD'][-1]}, "
            f"MUL용 {rs['MUL'][0]}–{rs['MUL'][-1]} — 처음엔 모두 비어 있음",
            "• 사이클 수는 마지막 쓰기(W)까지 포함해서 셈",
        ]
        bl = VGroup(*[txt(b, 21) for b in bullets]).arrange(DOWN, aligned_edge=LEFT, buff=0.18)
        if bl.width > 13.2:
            bl.scale_to_fit_width(13.2)
        bl.next_to(src, DOWN, buff=0.5)
        self.play(FadeOut(progs), FadeOut(same), run_time=0.5)
        self.play(FadeIn(bl, lag_ratio=0.3), run_time=2.5)
        self.wait(4)
        steps = VGroup(
            txt("매 사이클은 4단계로 진행", 22, weight=BOLD),
            txt("① 디코드·할당(Decode & Allocate) — RS 할당, 소스는 RAT에서 값 또는 태그 복사, 목적 레지스터 renaming", 18),
            txt("② 웨이크업/선택(Wake-up / Select) — 두 소스가 모두 Valid인 엔트리를 고름", 18),
            txt("③ 디스패치·실행(Dispatch & Execute) — 실행 유닛으로 보내고, 남은 사이클을 카운트다운", 18),
            txt("④ 브로드캐스트(Broadcast) — 결과의 태그와 값을 버스로 뿌려 태그가 일치하는 칸이 값을 받음", 18),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.16)
        legend = VGroup(
            VGroup(Rectangle(width=0.5, height=0.3, stroke_width=0).set_fill(YEL, 1), txt("현재 사이클", 18)).arrange(RIGHT),
            VGroup(txt("42", 20, BLUE, weight=BOLD), txt("방금 바뀐 값", 18)).arrange(RIGHT),
            VGroup(Arrow(LEFT * 0.3, RIGHT * 0.3, color=ORANGE, buff=0, stroke_width=4), txt("연결선(데이터 이동)", 18)).arrange(RIGHT),
        ).arrange(RIGHT, buff=0.8)
        grp = VGroup(steps, legend).arrange(DOWN, buff=0.45, aligned_edge=LEFT).next_to(src, DOWN, buff=0.5)
        self.play(FadeOut(bl), run_time=0.5)
        self.play(FadeIn(grp, lag_ratio=0.2), run_time=2.0)
        self.wait(5)
        self.play(FadeOut(VGroup(title, src, grp)), run_time=0.8)

    # ----------------------------------------------------------- outro ----
    def outro(self):
        inord = T["inorder"]["forwarding"]
        t_in, t_ooo = inord["total_cycles"], T["total_cycles"]
        ncol = max(t_in, t_ooo)
        x0, w, h = -3.6, (6.95 + 3.6) / ncol, 0.27
        title = txt("in-order dispatch vs out-of-order dispatch (forwarding 있음)", 28, weight=BOLD)
        title.to_edge(UP, buff=0.3)
        self.play(FadeIn(title))

        def table(rows, total, y_top, head, color):
            g = VGroup()
            hd = txt(head, 19, color, weight=BOLD).move_to([-7.0, y_top + 0.35, 0], aligned_edge=LEFT)
            g.add(hd)
            for k in range(1, ncol + 1):
                g.add(txt(str(k), 12, INK if k <= total else FAINT).move_to([x0 + (k - 0.5) * w, y_top, 0]))
            for i, row in enumerate(rows):
                y = y_top - (i + 1) * h
                g.add(txt(PROG[i]["text_src_first"], 13, font=MONO).move_to([-7.0, y, 0], aligned_edge=LEFT))
                for k, s in enumerate(row):
                    if s:
                        g.add(txt(lab(s), 13, BLUE if s == "W" else INK).move_to([x0 + (k + 0.5) * w, y, 0]))
            end = Line([x0 + total * w, y_top + 0.15, 0], [x0 + total * w, y_top - (NI + 0.5) * h, 0],
                       color=color, stroke_width=4)
            tot = txt(f"{total} 사이클", 22, color, weight=BOLD).next_to(end, RIGHT, buff=0.1)
            if tot.get_right()[0] > 7.0:
                tot.next_to(end, LEFT, buff=0.1).shift(UP * 0.0)
            tot.move_to([tot.get_center()[0], y_top + 0.35, 0])
            g.add(end, tot)
            return g

        g1 = table(inord["table"], t_in, 2.75, "in-order dispatch (슬라이드 37 아래)", RED)
        g2 = table(T["timing_table"], t_ooo, 0.05, "out-of-order dispatch = Tomasulo (슬라이드 38, 63)", BLUE)
        self.play(FadeIn(g1, lag_ratio=0.02), run_time=2.5)
        self.wait(2)
        self.play(FadeIn(g2, lag_ratio=0.02), run_time=2.5)
        # independent instructions (no source written by an older instruction)
        # that nevertheless start later in the in-order machine
        written, indep = set(), []
        for i, p in enumerate(PROG):
            ooo_e1 = T["timing_table"][i].index("E1") + 1
            if not (set(p["src"]) & written) and inord["rows"][i]["E1"] > ooo_e1:
                indep.append(instr_name(i))
            written.add(p["dst"])
        msg = VGroup(
            txt(f"같은 프로그램, 같은 실행 유닛 — {t_in} 사이클 → {t_ooo} 사이클 ({t_in - t_ooo} 사이클 단축)", 22, weight=BOLD),
            txt(f"in-order: 앞 명령어가 기다리면 뒤의 독립적인 명령어({', '.join(indep)})도 함께 멈춤", 18),
            txt("Tomasulo: 기다리는 명령어는 예약 스테이션에 두고, 준비된 명령어부터 실행 → 대기 시간이 겹쳐 숨겨짐", 18),
            txt("'-' = 예약 스테이션에서 대기 중   (in-order 표는 슬라이드 37처럼 대기 칸을 비워 둠)", 15, FAINT),
        ).arrange(DOWN, buff=0.1).move_to([0, -2.9, 0])
        self.play(FadeIn(msg, lag_ratio=0.2), run_time=1.5)
        self.wait(8)


class Intro(TomasuloBase):
    def construct(self):
        self.intro()


def cycle_range():
    spec = os.environ.get("TOMASULO_CYCLES", "")
    if not spec:
        return list(range(0, len(CYCLES)))
    a, b = spec.split("-")
    return list(range(int(a), int(b) + 1))


class Cycles(TomasuloBase):
    def construct(self):
        rng = cycle_range()
        self.build_board(animate=True)
        assert rng[0] == 0, "cycle range must start at 0 (board state is replayed)"
        for c in rng:
            self.play_cycle(c)
        self.wait(1)


class Outro(TomasuloBase):
    def construct(self):
        self.outro()


class FullVideo(TomasuloBase):
    def construct(self):
        self.intro()
        self.build_board(animate=True)
        for c in range(len(CYCLES)):
            self.play_cycle(c)
        self.wait(1.5)
        self.play(FadeOut(*self.mobjects), run_time=1.0)
        self.outro()
