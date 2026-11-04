"""Manim CE renderer for the ROB + PRF + pointer machine (L14 slides 78-82).

Reads ONLY out/prf_trace.json (override: PRF_TRACE).  Styling helpers (cells,
subtitles, prediction pause, phase bar, blink overlays) are reused from
common/style.py.

Scenes: PRFIntro, PRFCycles (PRF_CYCLES="0-3"), PRFOutro, PRFPreview (intro +
range), PRFFullVideo.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from manim import (BOLD, DOWN, LEFT, RIGHT, UP, WHITE, Arrow,  # noqa: E402
                   Create, FadeIn, FadeOut, Line, Polygon, Rectangle,
                   ReplacementTransform, RoundedRectangle, SurroundingRectangle,
                   Transform, VGroup, Write)
from common.style import (ASSUME, BLUE, FAINT, GREY, INK, MONO, ORANGE, RED,  # noqa: E402
                          YEL, YEL_STRONG, Cell, StyleScene, lab, subtitle_box, txt)

PATH = os.environ.get("PRF_TRACE", os.path.join(os.path.dirname(__file__), "..", "out", "prf_trace.json"))
with open(PATH, encoding="utf-8") as fh:
    P = json.load(fh)

PURPLE = "#7B3FB5"         # architectural map pointers (slide 80 uses purple for it)
CFG = P["config"]
PROG = CFG["program"]
NI = len(PROG)
REGS = CFG["registers"]
RS_IDS = CFG["rs_ids"]
N_PR = CFG["n_pr"]
PRS = [f"PR{i}" for i in range(1, N_PR + 1)]
ROB_SHOWN = 8              # entries drawn; the rest are summarised in one row
CYC = P["cycles"]
NCOL = P["total_cycles"]
SLOW = set(P["presentation"]["slow_cycles"])
UNIT_KO = {"ADD": "덧셈기(adder)", "MUL": "곱셈기(multiplier)"}
UNIT_SYM = {"ADD": "+", "MUL": "×"}


def iname(i):
    return f"I{i + 1}"


def itext(i):
    return PROG[i]["text_src_first"]


# ------------------------------------------------------------ display rules ---
def prf_disp(st, p):
    """[PR, V, Value] strings and whether the row is 'free' (faint)."""
    v = st["prf"][p]
    free = p in st["free_list"]
    if free and v["value"] is None:
        return [p, "", ""], True
    val = "" if v["value"] is None else str(v["value"])
    return [p, "1" if v["ready"] else "0", val], free


def rs_disp(st, e):
    x = st["rs"][e]
    if x is None:
        return [""] * 5
    s = x["src"]
    return [str(s[0]["valid"]), s[0]["pr"], str(s[1]["valid"]), s[1]["pr"], x["dest_pr"]]


def rob_disp(st, k):
    e = st["rob"][k]
    if e is None:
        return [str(k), "", "", "", "", ""]
    return [str(k), str(e["valid"]), e["dst"], e["dest_pr"], e["old_pr"], str(e["done"])]


# ------------------------------------------------------------------- board ---
class PBoard:
    SUB_Y = -3.33
    # timing table
    PX0, PX1 = -7.0, -4.6
    TX0 = -4.5
    TW = (1.95 - TX0) / NCOL
    TY0, TH = 3.40, 0.19
    # RS
    RS_X0 = {"ADD": -6.75, "MUL": 1.35}
    RS_W = [0.3, 0.55, 0.3, 0.55, 0.72]
    RS_H1, RS_H2, RS_ROW0, RS_H = 1.8, 1.6, 1.37, 0.24
    UNIT_CX = {"ADD": -3.5, "MUL": 4.6}
    UNIT_TOP, UNIT_BOT, OUT_Y = 1.45, 0.98, 0.72
    # PRF
    PRF_X0, PRF_W = -0.95, [0.6, 0.35, 0.65]
    PRF_HDR, PRF_H = 1.82, 0.2
    # maps / ROB
    MAP_HDR, MAP_H = 0.22, 0.215
    FR_X0, AR_X0, MAP_W = -3.15, 5.55, [0.6, 0.8]
    ROB_X0, ROB_W = 1.15, [0.35, 0.35, 0.5, 0.7, 0.7, 0.6]
    FREE_X0, FREE_Y, CHIP_W = 2.3, 2.93, 0.4

    def __init__(self):
        self.g = VGroup()
        self.title = txt("사이클 0", 24, weight=BOLD).move_to([-7.0, 3.76, 0], aligned_edge=LEFT)
        self.g.add(self.title)
        names = ["① Decode / Rename", "② Wake-up / Select", "③ PRF 읽기 & Execute", "④ Writeback & Retire"]
        self.phase_labels = VGroup(*[txt(n, 13) for n in names]).arrange(RIGHT, buff=0.3)
        self.phase_labels.move_to([2.7, 3.76, 0])
        self.phase_hl = None
        self.g.add(self.phase_labels)
        self.sub_box = subtitle_box(self.SUB_Y)
        self.g.add(self.sub_box)
        self._timing()
        self._free()
        self._rs()
        self._units()
        self._prf()
        self._maps()
        self._rob()
        self.f_arrow, self.a_arrow = {}, {}

    # timing -------------------------------------------------------------
    def row_y(self, i):
        return self.TY0 - (i + 1) * self.TH

    def col_x(self, k):
        return self.TX0 + (k - 0.5) * self.TW

    def _timing(self):
        self.prog_rows = []
        for i in range(NI):
            t = txt(itext(i), 11, font=MONO).move_to([self.PX0 + 0.08, self.row_y(i), 0], aligned_edge=LEFT)
            self.prog_rows.append(t)
        box = Rectangle(width=self.PX1 - self.PX0, height=NI * self.TH + 0.06, stroke_color=ORANGE,
                        stroke_width=1.4).move_to([(self.PX0 + self.PX1) / 2, self.row_y((NI - 1) / 2), 0])
        self.g.add(box, *self.prog_rows,
                   txt("Cycle", 11).move_to([self.PX1 - 0.04, self.TY0, 0], aligned_edge=RIGHT))
        self.theads, self.tcells = {}, {}
        for k in range(1, NCOL + 1):
            self.theads[k] = Cell(self.col_x(k), self.TY0, self.TW, self.TH, "", 11, border=False)
            self.g.add(self.theads[k].text)
            for i in range(NI):
                c = Cell(self.col_x(k), self.row_y(i), self.TW, self.TH, "", 11, border=False)
                self.tcells[(i, k)] = c
                self.g.add(c.text)
        self.prog_hl = self.col_hl = None

    # free list --------------------------------------------------------------
    def _free(self):
        self.g.add(txt("free list  (앞에서 꺼내 할당 → , retire 때 뒤에 반환)", 12, weight=BOLD)
                   .move_to([self.FREE_X0, self.FREE_Y + 0.3, 0], aligned_edge=LEFT))
        self.chips = []          # list of (pr, VGroup)

    def chip(self, p, k):
        r = Rectangle(width=self.CHIP_W - 0.03, height=0.26, stroke_color=INK, stroke_width=1)
        r.set_fill("#FFFFFF", 1).move_to(self.chip_pos(k))
        t = txt(p, 11).move_to(r)
        return VGroup(r, t)

    def chip_pos(self, k):
        return [self.FREE_X0 + (k + 0.5) * self.CHIP_W, self.FREE_Y, 0]

    # RS -----------------------------------------------------------------------
    def rs_x(self, op, k):
        return self.RS_X0[op] + sum(self.RS_W[:k]) + self.RS_W[k] / 2

    def rs_y(self, j):
        return self.RS_ROW0 - j * self.RS_H

    def _rs(self):
        self.rs, self.rs_of = {}, {}
        for op in ("ADD", "MUL"):
            x0 = self.RS_X0[op]
            for s in range(2):
                self.g.add(txt(f"Source {s + 1}", 11).move_to(
                    [(self.rs_x(op, 2 * s) + self.rs_x(op, 2 * s + 1)) / 2, self.RS_H1, 0]))
                self.g.add(txt("V", 11).move_to([self.rs_x(op, 2 * s), self.RS_H2, 0]))
                self.g.add(txt("PR", 11).move_to([self.rs_x(op, 2 * s + 1), self.RS_H2, 0]))
            self.g.add(txt("DestPR", 11).move_to([self.rs_x(op, 4), self.RS_H2, 0]))
            for j, e in enumerate(RS_IDS[op]):
                self.g.add(txt(e, 12).move_to([x0 - 0.13, self.rs_y(j), 0]))
                row = [Cell(self.rs_x(op, k), self.rs_y(j), self.RS_W[k], self.RS_H, "", 12) for k in range(5)]
                self.rs[e] = row
                self.rs_of[e] = op
                self.g.add(*[c.mobs() for c in row])
            w = sum(self.RS_W)
            self.g.add(txt(f"{op}용 RS — 값 없이 V 비트 + PR 번호", 11, weight=BOLD)
                       .move_to([x0 + w / 2, 1.99, 0]))

    def _units(self):
        self.unit, self.out_pr, self.out_val, self.countdown = {}, {}, {}, {}
        for op in ("ADD", "MUL"):
            cx = self.UNIT_CX[op]
            t, b = self.UNIT_TOP, self.UNIT_BOT
            poly = Polygon([cx - 0.68, t, 0], [cx - 0.08, t, 0], [cx, t - 0.08, 0], [cx + 0.08, t, 0],
                           [cx + 0.68, t, 0], [cx + 0.4, b, 0], [cx - 0.4, b, 0], color=INK, stroke_width=1.5)
            poly.set_fill(WHITE, 1)
            self.unit[op] = VGroup(poly, txt(UNIT_SYM[op], 20).move_to([cx, (t + b) / 2, 0]))
            pb = Cell(cx - 0.32, self.OUT_Y, 0.6, 0.24, "", 12)
            vb = Cell(cx + 0.32, self.OUT_Y, 0.6, 0.24, "", 12)
            self.out_pr[op], self.out_val[op] = pb, vb
            labels = VGroup(txt("DestPR", 10, RED).move_to([cx - 0.32, self.OUT_Y - 0.2, 0]),
                            txt("Value", 10, RED).move_to([cx + 0.32, self.OUT_Y - 0.2, 0]))
            self.countdown[op] = VGroup()
            self.g.add(self.unit[op], pb.mobs(), vb.mobs(), labels)

    # PRF --------------------------------------------------------------------
    def prf_x(self, k):
        return self.PRF_X0 + sum(self.PRF_W[:k]) + self.PRF_W[k] / 2

    def prf_y(self, p):
        return self.PRF_HDR - (PRS.index(p) + 1) * self.PRF_H

    def _prf(self):
        for k, h in enumerate(["PR", "V", "Value"]):
            c = Cell(self.prf_x(k), self.PRF_HDR, self.PRF_W[k], self.PRF_H, h, 11)
            c.text.set_color(RED)
            self.g.add(c.mobs())
        st = CYC[0]["state"]
        self.prf = {}
        for p in PRS:
            d, free = prf_disp(st, p)
            row = [Cell(self.prf_x(k), self.prf_y(p), self.PRF_W[k], self.PRF_H, d[k], 11) for k in range(3)]
            for c in row:
                c.recolor(FAINT if free else INK)
            self.prf[p] = row
            self.g.add(*[c.mobs() for c in row])
        self.prf_box = Rectangle(width=sum(self.PRF_W[1:]) + 0.06, height=N_PR * self.PRF_H + 0.06,
                                 stroke_color=ORANGE, stroke_width=3)
        self.prf_box.move_to([(self.prf_x(1) + self.prf_x(2)) / 2 + 0.07, self.PRF_HDR - (N_PR + 1) / 2 * self.PRF_H, 0])
        self.g.add(self.prf_box, txt("PRF — 값은 여기에만", 11, weight=BOLD).move_to(
            [self.PRF_X0 + sum(self.PRF_W) / 2, 1.99, 0]))

    def prf_left(self, p):
        return [self.PRF_X0, self.prf_y(p), 0]

    def prf_right(self, p):
        return [self.PRF_X0 + sum(self.PRF_W), self.prf_y(p), 0]

    # maps ---------------------------------------------------------------------
    def map_y(self, r):
        return self.MAP_HDR - (REGS.index(r) + 1) * self.MAP_H

    def _maps(self):
        st = CYC[0]["state"]
        self.fmap, self.amap = {}, {}
        for x0, key, store, title in ((self.FR_X0, "frontend_map", self.fmap, "Frontend Register Map"),
                                      (self.AR_X0, "arch_map", self.amap, "Arch Register Map")):
            xs = [x0 + self.MAP_W[0] / 2, x0 + self.MAP_W[0] + self.MAP_W[1] / 2]
            for k, h in enumerate(["Register", "PR"]):
                c = Cell(xs[k], self.MAP_HDR, self.MAP_W[k], self.MAP_H, h, 11)
                c.text.set_color(RED)
                self.g.add(c.mobs())
            for r in REGS:
                a = Cell(xs[0], self.map_y(r), self.MAP_W[0], self.MAP_H, r, 11)
                b = Cell(xs[1], self.map_y(r), self.MAP_W[1], self.MAP_H, st[key][r], 11)
                store[r] = b
                self.g.add(a.mobs(), b.mobs())
            cap = txt(title, 11, weight=BOLD, color=ORANGE if key == "frontend_map" else PURPLE)
            cap.move_to([x0 + sum(self.MAP_W) / 2, self.MAP_HDR - 12 * self.MAP_H - 0.07, 0])
            self.g.add(cap)

    # ROB ------------------------------------------------------------------------
    def rob_x(self, k):
        return self.ROB_X0 + sum(self.ROB_W[:k]) + self.ROB_W[k] / 2

    def rob_y(self, k):
        return self.MAP_HDR - (k + 1) * self.MAP_H

    def _rob(self):
        for k, h in enumerate(["#", "V", "Reg", "DestPR", "oldPR", "done"]):
            c = Cell(self.rob_x(k), self.MAP_HDR, self.ROB_W[k], self.MAP_H, h, 11)
            c.text.set_color(RED)
            self.g.add(c.mobs())
        st = CYC[0]["state"]
        self.rob = {}
        for k in range(ROB_SHOWN):
            d = rob_disp(st, k)
            row = [Cell(self.rob_x(j), self.rob_y(k), self.ROB_W[j], self.MAP_H, d[j], 11) for j in range(6)]
            self.rob[k] = row
            self.g.add(*[c.mobs() for c in row])
        self.g.add(txt(f"⋮  Entry {ROB_SHOWN}–{CFG['rob_size'] - 1} (이 프로그램에선 비어 있음)", 10, FAINT)
                   .move_to([self.ROB_X0 + sum(self.ROB_W) / 2, self.rob_y(ROB_SHOWN) + 0.02, 0]))
        self.g.add(txt(f"ROB ({CFG['rob_size']} 엔트리) — 값 없이 포인터만", 11, weight=BOLD)
                   .move_to([self.ROB_X0 + sum(self.ROB_W) / 2, self.MAP_HDR + 0.21, 0]))
        self.rob_ptr = VGroup()

    # arrow geometry ---------------------------------------------------------------
    def f_arrow_mob(self, r, p):
        start = [self.FR_X0 + sum(self.MAP_W), self.map_y(r), 0]
        return Arrow(start, self.prf_left(p), buff=0.02, color=ORANGE, stroke_width=2.5,
                     tip_length=0.1, max_tip_length_to_length_ratio=0.2)

    def a_arrow_mob(self, r, p):
        k = REGS.index(r)
        off = 0.055 * k
        ych = -2.33 - 0.025 * k
        y = self.map_y(r)
        pts = [[self.AR_X0, y, 0], [5.42 - off, y, 0], [5.42 - off, ych, 0],
               [0.75 + off, ych, 0], [0.75 + off, self.prf_y(p), 0]]
        segs = VGroup(*[Line(a, b, color=PURPLE, stroke_width=2.2) for a, b in zip(pts[:-1], pts[1:])])
        segs.add(Arrow(pts[-1], self.prf_right(p), buff=0, color=PURPLE, stroke_width=2.2,
                       tip_length=0.1, max_tip_length_to_length_ratio=0.6))
        return segs


# -------------------------------------------------------------------- scene ---
class PRFBase(StyleScene):
    # board ------------------------------------------------------------------
    def build_board(self, animate=True):
        self.B = PBoard()
        st = CYC[0]["state"]
        for k, p in enumerate(st["free_list"]):
            ch = self.B.chip(p, k)
            self.B.chips.append((p, ch))
            self.B.g.add(ch)
        self.blue_cells = []
        if animate:
            self.play(FadeIn(self.B.g, run_time=1.2))
        else:
            self.add(self.B.g)

    def set_cells(self, cells_and_values, color=BLUE):
        anims = []
        for cell, s in cells_and_values:
            if cell.s != s:
                anims.append(cell.change(s, color))
                if color == BLUE:
                    self.blue_cells.append(cell)
        return anims

    def sync_tables(self, st, prf_blue=False, which=("rs", "rob", "prf", "maps")):
        """Animations bringing every table to state `st`.  PRF value cells turn
        blue only if prf_blue (value created/changed); everything else black."""
        B = self.B
        anims = []
        if "rs" in which:
            for e in B.rs:
                d = rs_disp(st, e)
                anims += self.set_cells([(B.rs[e][k], d[k]) for k in range(5)], INK)
        if "rob" in which:
            for k in range(ROB_SHOWN):
                d = rob_disp(st, k)
                anims += self.set_cells([(B.rob[k][j], d[j]) for j in range(6)], INK)
                faint = st["rob"][k] is not None and not st["rob"][k]["valid"]
                for c in B.rob[k]:
                    c.recolor(FAINT if faint else INK)
        if "prf" in which:
            for p in PRS:
                d, free = prf_disp(st, p)
                col = FAINT if free else INK
                for k in range(3):
                    c = B.prf[p][k]
                    if c.s != d[k]:
                        anims.append(c.change(d[k], BLUE if (prf_blue and k == 2 and d[k]) else col))
                        if prf_blue and k == 2:
                            self.blue_cells.append(c)
                    elif c not in self.blue_cells:
                        c.recolor(col)
        if "maps" in which:
            for r in REGS:
                anims += self.set_cells([(B.fmap[r], st["frontend_map"][r])], INK)
                anims += self.set_cells([(B.amap[r], st["arch_map"][r])], INK)
        return anims

    def sync_free(self, st, from_cell=None):
        """Re-lay the free-list chips to match st['free_list'].  New chips fly in
        from `from_cell` (a Cell) if given."""
        B = self.B
        anims = []
        want = st["free_list"]
        have = [p for p, _ in B.chips]
        keep = []
        for p, ch in B.chips:
            if p in want:
                keep.append((p, ch))
            else:
                anims.append(FadeOut(ch, shift=DOWN * 0.3))
        new_chips = []
        for k, p in enumerate(want):
            found = [ch for q, ch in keep if q == p]
            if found:
                ch = found[0]
                anims.append(ch.animate.move_to(B.chip_pos(k)))
            else:
                ch = B.chip(p, k)
                if from_cell is not None:
                    start = ch.copy().move_to(from_cell.rect)
                    anims.append(Transform(start, ch))
                    ch = start
                else:
                    anims.append(FadeIn(ch))
            new_chips.append((p, ch))
        B.chips = new_chips
        _ = have
        return anims

    def sync_arrows(self, st, which=("f", "a")):
        """Arrows only for mappings that differ from the initial Ri -> PRi."""
        B = self.B
        init = CYC[0]["state"]
        anims = []
        for kind, key, store, mk in (("f", "frontend_map", B.f_arrow, B.f_arrow_mob),
                                     ("a", "arch_map", B.a_arrow, B.a_arrow_mob)):
            if kind not in which:
                continue
            for r in REGS:
                p = st[key][r]
                cur = store.get(r)
                if p == init[key][r] and cur is None:
                    continue
                if cur is not None and cur.target == p:
                    continue
                new = mk(r, p)
                new.target = p
                if cur is None:
                    old = mk(r, init[key][r])          # appear on the old PR, then move
                    old.target = init[key][r]
                    self.play(Create(old), run_time=self.rt(0.5))
                    cur = old
                anims.append(Transform(cur, new))
                cur.target = p
                store[r] = cur
        return anims

    def check_board(self, st, where):
        B = self.B
        errs = []
        for e in B.rs:
            d = rs_disp(st, e)
            errs += [f"RS {e}[{k}] '{B.rs[e][k].s}'≠'{d[k]}'" for k in range(5) if B.rs[e][k].s != d[k]]
        for k in range(ROB_SHOWN):
            d = rob_disp(st, k)
            errs += [f"ROB {k}[{j}] '{B.rob[k][j].s}'≠'{d[j]}'" for j in range(6) if B.rob[k][j].s != d[j]]
        for p in PRS:
            d, _ = prf_disp(st, p)
            errs += [f"{p}[{k}] '{B.prf[p][k].s}'≠'{d[k]}'" for k in range(3) if B.prf[p][k].s != d[k]]
        for r in REGS:
            if B.fmap[r].s != st["frontend_map"][r]:
                errs.append(f"Frontend {r}")
            if B.amap[r].s != st["arch_map"][r]:
                errs.append(f"Arch {r}")
            for store, key in ((B.f_arrow, "frontend_map"), (B.a_arrow, "arch_map")):
                a = store.get(r)
                want_arrow = st[key][r] != CYC[0]["state"][key][r]
                if want_arrow and (a is None or a.target != st[key][r]):
                    errs.append(f"{key} {r} 화살표가 {st[key][r]}를 가리키지 않음")
        if [p for p, _ in B.chips] != st["free_list"]:
            errs.append(f"free list {[p for p, _ in B.chips]} ≠ {st['free_list']}")
        fam = {id(m) for m in self.get_mobject_family_members()}
        for p in PRS:
            for c in B.prf[p]:
                if c.s and id(c.text) not in fam:
                    errs.append(f"{p} 글자가 화면에 없음")
        if errs:
            raise RuntimeError(f"화면/trace 불일치 ({where}):\n  " + "\n  ".join(errs))

    def update_rob_ptr(self, st):
        B = self.B
        h, t = st["rob_head"], st["rob_tail"]
        x = B.ROB_X0 + sum(B.ROB_W) + 0.05
        lines = []
        if h == t and not any(e and e["valid"] for e in st["rob"]):
            lines.append(txt("◀ head·tail", 10, RED).move_to([x, B.rob_y(h), 0], aligned_edge=LEFT))
        else:
            lines.append(txt("◀ head", 10, RED).move_to([x, B.rob_y(h), 0], aligned_edge=LEFT))
            if t < ROB_SHOWN:
                lines.append(txt("◀ tail", 10, FAINT).move_to([x, B.rob_y(t), 0], aligned_edge=LEFT))
        new = VGroup(*lines)
        anims = [ReplacementTransform(B.rob_ptr, new)] if len(B.rob_ptr) else [FadeIn(new)]
        B.rob_ptr = new
        return anims

    def update_countdown(self, st):
        B = self.B
        anims = []
        for op in ("ADD", "MUL"):
            lines = [txt(f"{u['rs']}: {lab('E' + str(u['stage']))} · 남은 {u['countdown']}", 12,
                         ORANGE if u["stage"] == 1 else INK, weight=BOLD) for u in st["units"][op]]
            new = VGroup(*lines).arrange(DOWN, buff=0.04, aligned_edge=LEFT) if lines else VGroup()
            if lines:
                new.move_to([B.UNIT_CX[op] + 0.75, (B.UNIT_TOP + B.UNIT_BOT) / 2, 0], aligned_edge=LEFT)
            old = B.countdown[op]
            if len(old) or len(new):
                anims += [FadeOut(old), FadeIn(new)]
            B.countdown[op] = new
        if anims:
            self.play(*anims, run_time=self.rt(0.4))

    def timing_write(self, c, pred):
        col = CYC[c]["column"]
        anims = [self.B.tcells[(i, c)].change(col[i], INK) for i in range(NI)
                 if col[i] and pred(col[i]) and self.B.tcells[(i, c)].s != col[i]]
        if anims:
            self.play(*anims, run_time=self.rt(0.4))

    def outline(self, cells, color=ORANGE):
        return SurroundingRectangle(VGroup(*[c.rect for c in cells]), color=color, buff=0.01, stroke_width=3)

    def arrow(self, a, b, color=ORANGE):
        return Arrow(a, b, buff=0.03, color=color, stroke_width=2.5, tip_length=0.11,
                     max_tip_length_to_length_ratio=0.25)

    # ---------------------------------------------------------------- cycle ---
    def cycle_speed(self, c):
        kinds = {e["type"] for p in CYC[c]["phases"] for e in p["events"]}
        if c in SLOW:
            return 1.5
        if kinds & {"decode_alloc", "select", "dispatch", "writeback", "retire", "rob_done"}:
            return 1.0
        return 0.45

    def start_cycle(self, c):
        B = self.B
        for cell in self.blue_cells:
            cell.recolor(INK)
        self.blue_cells = []
        anims = []
        nt = txt(f"사이클 {c}", 24, weight=BOLD).move_to(B.title, aligned_edge=LEFT)
        anims.append(ReplacementTransform(B.title, nt))
        B.title = nt
        hl = Rectangle(width=B.TW, height=(NI + 1) * B.TH + 0.04, stroke_width=0).set_fill(YEL, 1)
        hl.move_to([B.col_x(c), B.TY0 - NI * B.TH / 2, 0]).set_z_index(-2)
        anims.append(FadeIn(hl) if B.col_hl is None else ReplacementTransform(B.col_hl, hl))
        B.col_hl = hl
        anims.append(B.theads[c].change(str(c), INK))
        for op in ("ADD", "MUL"):
            for cell in (B.out_pr[op], B.out_val[op]):
                if cell.s:
                    anims.append(cell.change("", INK))
        if B.prog_hl is not None:
            anims.append(FadeOut(B.prog_hl))
            B.prog_hl = None
        self.play(*anims, run_time=self.rt(0.5))

    def play_cycle(self, c):
        self.k = self.cycle_speed(c) if c else 1.0
        if c == 0:
            st = CYC[0]["state"]
            self.play(*self.update_rob_ptr(st), run_time=0.3)
            self.say(["사이클 0 — 초기 상태: Frontend Map과 Arch Map 모두 Ri → PRi, PRi 값 = i,  "
                      f"free list = {st['free_list'][0]}–{st['free_list'][-1]}",
                      f"{ASSUME}: 초기 매핑·free list 순서·free PR의 값(빈칸)·PRF의 V(ready) 비트  "
                      "— 처음엔 Ri → PRi라서 화살표는 생략하고, 매핑이 바뀌면 화살표로 표시"], wait=4.0)
            self.check_board(st, "사이클 0")
            return
        self.predict(c)
        self.start_cycle(c)
        ph = {p["phase"]: p for p in CYC[c]["phases"]}
        self.phase_decode(c, ph["decode"])
        self.check_board(ph["decode"]["state"], f"사이클 {c} ①")
        self.phase_select(c, ph["select"])
        self.check_board(ph["select"]["state"], f"사이클 {c} ②")
        self.phase_execute(c, ph["execute"])
        self.check_board(ph["execute"]["state"], f"사이클 {c} ③")
        self.phase_wb_retire(c, ph["writeback"], ph["retire"])
        self.check_board(ph["retire"]["state"], f"사이클 {c} ④")

    # ① ------------------------------------------------------------------------
    def phase_decode(self, c, ph):
        B = self.B
        self.set_phase(0)
        ev = {e["type"]: e for e in ph["events"]}
        st = ph["state"]
        if "decode_alloc" in ev:
            d, rn = ev["decode_alloc"], ev["rename"]
            i, e, rob = d["instr"], d["rs"], d["rob"]
            hl = Rectangle(width=B.PX1 - B.PX0 - 0.04, height=B.TH, stroke_width=0).set_fill(YEL, 1)
            hl.move_to([(B.PX0 + B.PX1) / 2, B.row_y(i), 0]).set_z_index(-2)
            B.prog_hl = hl
            self.play(FadeIn(hl), run_time=self.rt(0.3))
            self.timing_write(c, lambda s: s == "D")
            head = f"① 디코드·리네임(Decode/Rename): {iname(i)}  {itext(i)}  →  RS {e}, ROB 엔트리 {rob}"
            # sources: Frontend Map -> RS (PR number), V from PRF ready bit
            outl, arrs, srcs = [], [], []
            for k, s in enumerate(d["sources"]):
                fr = B.fmap[s["reg"]]
                outl.append(self.outline([fr]))
                outl.append(self.outline(B.prf[s["pr"]][:2], color=YEL_STRONG))
                arrs.append(self.arrow(fr.rect.get_top(), B.rs[e][2 * k + 1].rect.get_bottom()))
                srcs.append(f"{s['reg']} → {s['pr']} (V={s['valid']}{'' if s['valid'] else ', 아직 계산 중'})")
            self.say([head, "소스: Frontend Map에서 PR 번호를 읽어 RS에 복사 —  " + ",   ".join(srcs),
                      "V 비트는 그 PR의 ready 비트(PRF의 V 열)에서 가져옴 — RS에는 값이 들어가지 않는다"], wait=0.3)
            self.play(*[Create(o) for o in outl], run_time=self.rt(0.4))
            self.play(*[Create(a) for a in arrs], run_time=self.rt(0.7))
            row = rs_disp(st, e)
            self.play(*self.set_cells([(B.rs[e][k], row[k]) for k in range(4)]), run_time=self.rt(0.5))
            self.pause(0.8)
            self.play(*[FadeOut(m) for m in outl + arrs], run_time=self.rt(0.3))
            # rename: free list head -> dest
            reg, new, old = rn["reg"], rn["dest_pr"], rn["old_pr"]
            chip = B.chips[0][1]
            extra = ""
            twice = sum(1 for q in PROG[:i] if q["dst"] == reg)
            if twice:
                extra = f"   ← {reg}의 두 번째 쓰기: 첫 번째와 다른 PR → WAW 의존 제거"
            self.say([head, f"목적 레지스터 {reg}: free list 맨 앞의 {new}를 할당(DestPR),  "
                            f"Frontend Map {reg}: {old} → {new}" + extra,
                      f"ROB {rob}에 기록: Reg={reg}, DestPR={new}, oldPR={old}(나중에 반환할 옛 PR)   "
                      f"{ASSUME}: ROB 필드 구성·oldPR 반환 방식(R10000)"], wait=0.2)
            fly = chip.copy()
            self.play(fly.animate.move_to(B.fmap[reg].rect), FadeOut(chip), run_time=self.rt(0.8))
            B.chips = B.chips[1:]
            self.play(FadeOut(fly), *self.set_cells([(B.fmap[reg], new)]), run_time=self.rt(0.3))
            arr = self.sync_arrows(st, which=("f",))
            mv = self.sync_free(st)
            prfa = self.sync_tables(st, which=("prf",))
            self.play(*arr, *mv, *prfa, run_time=self.rt(0.8))
            # ROB entry + RS DestPR, with pointer arrows to the PRF
            rrow = rob_disp(st, rob) if rob < ROB_SHOWN else None
            cells = [(B.rs[e][4], new)]
            if rrow:
                cells += [(B.rob[rob][j], rrow[j]) for j in range(1, 6)]
            self.play(*self.set_cells(cells), *self.update_rob_ptr(st), run_time=self.rt(0.6))
            ptr = []
            if rrow:
                ptr.append(self.arrow(B.rob[rob][3].rect.get_left(), B.prf_right(new), BLUE))
                ptr.append(self.arrow(B.rob[rob][4].rect.get_left(), B.prf_right(old), FAINT))
            ptr.append(self.arrow(B.rs[e][4].rect.get_bottom(), B.prf_left(new) if B.rs_of[e] == "ADD"
                                  else B.prf_right(new), BLUE))
            self.play(*[Create(a) for a in ptr], run_time=self.rt(0.6))
            self.pause(1.2 if twice else 0.8)
            self.play(*[FadeOut(a) for a in ptr], run_time=self.rt(0.3))
        if "fetch" in ev:
            self.timing_write(c, lambda s: s == "F")
            f = ev["fetch"]["instr"]
            note = f"인출(Fetch): {iname(f)}  {itext(f)}  (다음 사이클에 디코드)"
            self.say([("① 디코드할 명령어 없음 — " if "decode_alloc" not in ev else "① 동시에 ") + note], wait=0.6)
        if not ev:
            self.say(["① 디코드·리네임: 할 일 없음 — 6개 명령어 모두 이미 renaming 완료"], wait=0.4)

    # ② ------------------------------------------------------------------------
    def phase_select(self, c, ph):
        B = self.B
        self.set_phase(1)
        sel = [e for e in ph["events"] if e["type"] == "select"]
        wt = [e for e in ph["events"] if e["type"] == "waiting"]
        lines, marks, self.select_marks = [], [], []
        for e in sel:
            g = VGroup(*[x.rect for x in B.rs[e["rs"]]])
            bg = SurroundingRectangle(g, buff=0, stroke_width=0).set_fill(YEL, 1).set_z_index(-1)
            self.select_marks.append(bg)
            marks.append(SurroundingRectangle(g, color=YEL_STRONG, buff=0.02, stroke_width=4))
            lines.append(f"RS {e['rs']}: 두 소스 V=1 → 웨이크업(wake-up), {UNIT_KO[e['unit']]}로 선택")
        for e in wt:
            if e["just_ready"]:
                lines.append(f"RS {e['rs']}: 방금 준비됨 → 다음 사이클부터 선택 가능")
                continue
            for k in range(2):
                if B.rs[e["rs"]][2 * k].s == "0":
                    marks.append(SurroundingRectangle(VGroup(B.rs[e["rs"]][2 * k].rect, B.rs[e["rs"]][2 * k + 1].rect),
                                                      color=RED, buff=0, stroke_width=3))
            lines.append(f"RS {e['rs']}: {', '.join(e['missing_prs'])}의 DestPR 태그를 기다리는 중")
        if not lines:
            self.say(["② 웨이크업/선택(Wake-up/Select): 대기 중인 엔트리 없음"], wait=0.3)
            return
        self.say(["② 웨이크업/선택(Wake-up/Select): " + ("" if sel else "실행할 수 있는 엔트리 없음")]
                 + lines[:2] + ([" · ".join(lines[2:])] if lines[2:] else []), wait=0.2)
        if marks + self.select_marks:
            self.play(*[FadeIn(m) for m in marks + self.select_marks], run_time=self.rt(0.4))
        self.pause(1.0)
        if marks:
            self.play(*[FadeOut(m) for m in marks], run_time=self.rt(0.25))

    # ③ ------------------------------------------------------------------------
    def phase_execute(self, c, ph):
        B = self.B
        self.set_phase(2)
        disp = [e for e in ph["events"] if e["type"] == "dispatch"]
        exe = [e for e in ph["events"] if e["type"] == "execute" and not any(d["rs"] == e["rs"] for d in disp)]
        lines, arrs, outl = [], [], []
        for d in disp:
            cx = B.UNIT_CX[d["unit"]]
            for k, r in enumerate(d["prf_reads"]):
                outl.append(self.outline(B.prf[r["pr"]], YEL_STRONG))
                tgt = [cx - 0.35 + 0.7 * k, B.UNIT_TOP, 0]
                src = B.prf_left(r["pr"]) if d["unit"] == "ADD" else B.prf_right(r["pr"])
                arrs.append(self.arrow(src, tgt))
            reads = ",  ".join(f"{r['pr']}={r['value']}" for r in d["prf_reads"])
            a, b = (r["value"] for r in d["prf_reads"])
            lines.append(f"③ 실행 직전 PRF에서 소스 값 읽기(Before Execution): {reads}  →  {UNIT_KO[d['unit']]}  "
                         f"({a} {UNIT_SYM[d['unit']]} {b}, {d['latency']}사이클)")
            lines.append(f"RS {d['rs']}에는 PR 번호만 있으므로 값은 이 순간 PRF에서 처음 가져온다")
        if exe:
            lines.append(("실행 중(파이프라인): " if disp else "③ 실행 계속(파이프라인): ") +
                         ",  ".join(f"{e['rs']}: {lab('E' + str(e['stage']))}/{e['latency']}" for e in exe))
        if not lines:
            lines = ["③ PRF 읽기·실행: 실행 중인 연산 없음"]
        self.say(lines[:3], wait=0.2)
        if arrs:
            self.play(*[Create(o) for o in outl], *[Create(a) for a in arrs], run_time=self.rt(0.8))
        self.timing_write(c, lambda s: s == "-" or s.startswith("E"))
        self.update_countdown(ph["state"])
        self.pause(0.9 if disp else 0.4)
        if arrs:
            self.play(*[FadeOut(m) for m in outl + arrs], run_time=self.rt(0.25))
        if self.select_marks:
            self.play(*[FadeOut(m) for m in self.select_marks], run_time=self.rt(0.2))
            self.select_marks = []

    # ④ ------------------------------------------------------------------------
    def phase_wb_retire(self, c, wb, rt):
        B = self.B
        self.set_phase(3)
        said = False
        for e in [x for x in wb["events"] if x["type"] == "writeback"]:
            op, dest = e["unit"], e["dest_pr"]
            cx = B.UNIT_CX[op]
            self.play(B.out_pr[op].change(dest, INK), B.out_val[op].change(str(e["value"]), INK),
                      run_time=self.rt(0.4))
            src = B.out_val[op].rect.get_bottom() if op == "ADD" else B.out_pr[op].rect.get_bottom()
            w = self.arrow(src, B.prf_left(dest) if op == "ADD" else B.prf_right(dest))
            names = ", ".join(f"RS {m['rs']} Source {m['src'] + 1}" for m in e["matches"]) or "기다리는 RS 없음"
            self.say([f"④ 실행 후 결과를 PRF에 쓰기(After Execution): PRF[{dest}] ← {e['value']}  (V=1)",
                      f"DestPR 태그 {dest}만 broadcast ({e['tag_bits']}비트 태그, 값은 보내지 않음) → "
                      f"태그가 일치하는 RS의 V 비트 0→1: {names}"], wait=0.2)
            self.play(Create(w), run_time=self.rt(0.6))
            self.play(*self.sync_tables(e["after"], prf_blue=True, which=("prf",)), run_time=self.rt(0.6))
            tags, rects = [], []
            for m in e["matches"]:
                v = B.rs[m["rs"]][2 * m["src"]]
                tags.append(self.arrow(B.out_pr[op].rect.get_top(), v.rect.get_bottom()))
                rects += [v.rect, B.rs[m["rs"]][2 * m["src"] + 1].rect]
            if tags:
                self.play(*[Create(a) for a in tags], run_time=self.rt(0.7))
                self.play(self.blink(rects), *self.set_cells(
                    [(B.rs[m["rs"]][2 * m["src"]], "1") for m in e["matches"]]), run_time=self.rt(1.0))
                self.remove(*self.blink_overlays)
            self.pause(0.8)
            self.play(*[FadeOut(a) for a in tags + [w]], run_time=self.rt(0.3))
            said = True
        done = [x for x in wb["events"] if x["type"] == "rob_done"]
        if done:
            self.timing_write(c, lambda s: s == "R")
            cells = [B.rob[x["rob"]][5] for x in done if x["rob"] < ROB_SHOWN]
            self.say(["R: 실행이 끝난 명령어를 ROB에 완료로 표시 (done = 1) — " +
                      ", ".join(f"{iname(x['instr'])}(ROB {x['rob']})" for x in done),
                      f"{ASSUME}: R은 마지막 E 다음 사이클, retire(W)는 R 다음 사이클부터"], wait=0.2)
            self.play(self.blink([x.rect for x in cells]), *self.set_cells([(x, "1") for x in cells]),
                      run_time=self.rt(0.8))
            self.remove(*self.blink_overlays)
            said = True
        ret = [x for x in rt["events"] if x["type"] == "retire"]
        for r in ret:
            k = r["rob"]
            reg = r["reg"]
            st = rt["state"]
            box = self.outline(B.rob[k]) if k < ROB_SHOWN else VGroup()
            spec = [q for q in REGS if st["frontend_map"][q] != st["arch_map"][q]]
            self.say([f"④ Retire(W): ROB head {k} = {iname(r['instr'])} 완료 → Arch Map {reg}: "
                      f"{r['arch_prev']} → {r['arch_new']} (DestPR)",
                      f"oldPR {r['freed_pr']}는 이제 아무도 안 읽으므로 free list 뒤로 반환   "
                      f"{ASSUME}: 사이클당 1개, oldPR 반환(R10000)"] +
                     ([f"아직 Frontend ≠ Arch (투기적 상태): {', '.join(spec)}"] if spec else
                      ["이제 Frontend Map = Arch Map — 모든 명령어가 아키텍처 상태에 반영됨"]), wait=0.2)
            if k < ROB_SHOWN:
                self.play(Create(box), run_time=self.rt(0.3))
            self.timing_write(c, lambda s: s == "W")
            self.play(*self.set_cells([(B.amap[reg], r["arch_new"])]), *self.sync_arrows(st, which=("a",)),
                      run_time=self.rt(1.0))
            src_cell = B.rob[k][4] if k < ROB_SHOWN else None
            self.play(*self.sync_free(st, from_cell=src_cell), *self.sync_tables(st, which=("rob", "prf")),
                      *self.update_rob_ptr(st), run_time=self.rt(0.9))
            self.pause(1.0)
            if k < ROB_SHOWN:
                self.play(FadeOut(box), run_time=self.rt(0.2))
            said = True
        self.timing_write(c, lambda s: s == "·")
        rest = self.sync_tables(rt["state"])
        if rest:
            self.play(*rest, run_time=self.rt(0.3))
        self.update_countdown(rt["state"])
        ready = [o["rs"] for o in CYC[c]["outlook"] if o["ready_next"]]
        block = [f"RS {o['rs']}({', '.join(o['missing_prs'])} 대기)" for o in CYC[c]["outlook"] if not o["ready_next"]]
        tail = []
        if ready:
            tail.append("다음 사이클에 실행 가능: RS " + ", ".join(ready))
        if block:
            tail.append("아직 실행 불가: " + ", ".join(block))
        wait_ret = [x for x in rt["events"] if x["type"] == "retire_wait"]
        if not said:
            first = "④ Writeback & Retire: 이번 사이클엔 끝나는 연산도 retire할 명령어도 없음"
            if wait_ret:
                w = wait_ret[0]
                first = (f"④ Writeback & Retire: 없음 — ROB head({iname(w['instr'])})는 "
                         + ("아직 완료되지 않아 retire 불가" if w["why"] == "not_done"
                            else "이번 사이클에 막 완료(R)되어 다음 사이클에 retire"))
            self.say([first] + (["→ " + "   |   ".join(tail)] if tail else []), wait=0.9)
        elif tail:
            self.say(["→ " + "   |   ".join(tail)], wait=0.8)

    # -------------------------------------------------------------- intro ----
    def intro(self):
        title = txt("후속편: ROB + Physical Register File(PRF) + 포인터", 36, weight=BOLD).to_edge(UP, buff=0.4)
        src = txt("ETH DDCA · L14 · 슬라이드 71–82 — 같은 6개 명령어 프로그램", 18, FAINT).next_to(title, DOWN, buff=0.15)
        self.play(Write(title), FadeIn(src), run_time=1.2)
        self.wait(1.5)
        self.play(FadeOut(title), FadeOut(src), run_time=0.5)
        self.replication_scene()
        self.assumption_scene()

    def replication_scene(self):
        X = P["replication_example"]
        SC = P["storage_comparison"]["tomasulo_rob"]
        head = txt("기존 구조(슬라이드 75·78): 값이 여러 곳에 복제된다 (Value Replication)", 24, weight=BOLD)
        head.move_to([0, 3.65, 0])
        self.play(FadeIn(head), run_time=0.6)
        h = 0.24
        grp, value_cols = VGroup(), {}

        def table(x0, y0, cols, widths, rows, labels=None, size=11):
            g, cells = VGroup(), []
            xs = [x0 + sum(widths[:k]) + widths[k] / 2 for k in range(len(cols))]
            for k, cname in enumerate(cols):
                g.add(txt(cname, size).move_to([xs[k], y0, 0]))
            for j, row in enumerate(rows):
                y = y0 - (j + 1) * h
                rc = [Cell(xs[k], y, widths[k], h, row[k], size) for k in range(len(cols))]
                cells.append(rc)
                g.add(*[c.mobs() for c in rc])
                if labels:
                    g.add(txt(labels[j], size).move_to([x0 - 0.15, y, 0]))
            return g, cells
        # RS (with values), from the Tomasulo trace at the retire cycle
        rsd = X["rs_display"]
        rs_cols = ["V", "Tag", "Value", "V", "Tag", "Value"]
        rs_w = [0.3, 0.4, 0.55, 0.3, 0.4, 0.55]
        ga, rsa = table(-6.6, 2.95, rs_cols, rs_w, [rsd[e] for e in RS_IDS["ADD"]], RS_IDS["ADD"])
        gm, rsm = table(3.85, 2.95, rs_cols, rs_w, [rsd[e] for e in RS_IDS["MUL"]], RS_IDS["MUL"])
        fd = X["frontend_display"]
        gf, frc = table(-6.6, 1.25, ["Reg", "V", "Tag", "Value"], [0.55, 0.3, 0.4, 0.6],
                        [[r] + fd[r] for r in REGS])
        av = X["arch_values"]
        gr, arc = table(5.4, 1.25, ["Reg", "Value"], [0.6, 0.7], [[r, str(av[r])] for r in REGS])
        rob_rows = []
        for k in range(CFG["rob_size"]):
            e = X["rob"][k] if k < len(X["rob"]) else None
            rob_rows.append(["", "", "", ""] if e is None else
                            [str(e["valid"]), e["dst"], "" if e["value"] is None else str(e["value"]), str(e["done"])])
        gb, robc = table(-1.0, 2.25, ["V", "Dest", "Value", "done"], [0.35, 0.55, 0.7, 0.5], rob_rows,
                         [f"{k}" for k in range(CFG["rob_size"])], size=10)
        caps = VGroup(txt("RS for ADD", 13, BLUE, weight=BOLD).move_to([-5.3, 3.22, 0]),
                      txt("RS for MUL", 13, BLUE, weight=BOLD).move_to([5.1, 3.22, 0]),
                      txt("Frontend Register File", 13, BLUE, weight=BOLD).move_to([-5.7, -1.85, 0]),
                      txt("ROB (열 구성은 예시)", 13, BLUE, weight=BOLD).move_to([0.05, 2.5, 0]),
                      txt("Arch Register File", 13, BLUE, weight=BOLD).move_to([5.75, -1.85, 0]))
        grp.add(ga, gm, gf, gr, gb, caps)
        self.play(FadeIn(grp), run_time=1.2)
        value_cols = [
            VGroup(*[r[2].rect for r in rsa]), VGroup(*[r[5].rect for r in rsa]),
            VGroup(*[r[2].rect for r in rsm]), VGroup(*[r[5].rect for r in rsm]),
            VGroup(*[r[3].rect for r in frc]), VGroup(*[r[2].rect for r in robc]), VGroup(*[r[1].rect for r in arc])]
        boxes = [RoundedRectangle(corner_radius=0.08, width=v.width + 0.08, height=v.height + 0.08,
                                  stroke_color=ORANGE, stroke_width=4).move_to(v) for v in value_cols]
        total = SC["rs_value_fields"] + SC["frontend_rf_values"] + SC["rob_value_fields"] + SC["arch_rf_values"]
        cnt = txt(f"값(64비트)을 저장하는 칸: RS {SC['rs_value_fields']} + Frontend RF {SC['frontend_rf_values']} + "
                  f"ROB {SC['rob_value_fields']} + Arch RF {SC['arch_rf_values']} = {total}칸", 19, weight=BOLD)
        cnt.move_to([0, -2.75, 0])
        self.play(*[Create(b) for b in boxes], FadeIn(cnt), run_time=1.5)
        self.wait(2.5)
        # one concrete value
        val, ins = X["value"], X["instr"]
        self.play(*[FadeOut(b) for b in boxes], run_time=0.4)
        where = []
        for L in X["locations"]:
            if L["structure"] == "rs":
                tab = rsa if L["entry"] in RS_IDS["ADD"] else rsm
                ids = RS_IDS["ADD"] if L["entry"] in RS_IDS["ADD"] else RS_IDS["MUL"]
                where.append((tab[ids.index(L["entry"])][L["field"]], f"RS {L['entry']}"))
            elif L["structure"] == "frontend":
                where.append((frc[REGS.index(L["reg"])][3], f"Frontend RF {L['reg']}"))
            elif L["structure"] == "rob":
                where.append((robc[L["entry"]][2], f"ROB {L['entry']}"))
            else:
                where.append((arc[REGS.index(L["reg"])][1], f"Arch RF {L['reg']}"))
        line = txt(f"{iname(ins)} {itext(ins)}의 결과 {val} — {iname(ins)}가 retire하는 순간(사이클 {X['cycle']}):",
                   19, weight=BOLD).move_to([0, -2.6, 0])
        self.play(ReplacementTransform(cnt, line), run_time=0.5)
        counter = txt("같은 값이 저장된 곳: 0군데", 22, ORANGE, weight=BOLD).move_to([0, -3.15, 0])
        self.play(FadeIn(counter), run_time=0.3)
        for n, (cell, name) in enumerate(where, start=1):
            b = RoundedRectangle(corner_radius=0.06, width=cell.rect.width + 0.1, height=cell.rect.height + 0.1,
                                 stroke_color=ORANGE, stroke_width=5).move_to(cell.rect)
            nc = txt(f"같은 값이 저장된 곳: {n}군데  ({', '.join(w for _, w in where[:n])})", 22, ORANGE,
                     weight=BOLD).move_to(counter)
            self.play(Create(b), ReplacementTransform(counter, nc), run_time=0.7)
            counter = nc
            grp.add(b)
            self.wait(0.4)
        self.wait(2.5)
        msg = txt("→ 값은 PRF 한 곳에만 두고, 나머지 구조는 PR 번호(포인터)만 저장하자 (슬라이드 79–82)",
                  21, weight=BOLD).move_to([0, -3.15, 0])
        self.play(ReplacementTransform(counter, msg), run_time=0.6)
        self.wait(2.5)
        self.play(FadeOut(VGroup(grp, head, line, msg)), run_time=0.8)

    def assumption_scene(self):
        head = txt("이 영상의 구조와 가정", 28, weight=BOLD).to_edge(UP, buff=0.5)
        st = [
            f"• PRF: PR1–PR{N_PR} — 값은 오직 여기에만 (centralized value storage)",
            "• Frontend Register Map: Rx → PR (renaming용),  Architectural Register Map: Rx → PR (precise state용)",
            f"• ROB {CFG['rob_size']} 엔트리 — 값 없이 포인터만,  RS: 소스마다 V 비트 + PR 번호 (값 없음)",
            "• 실행 유닛 출력: DestPR + Value — 결과는 PRF에 쓰고, broadcast는 DestPR 태그만",
        ]
        g1 = VGroup(*[txt(s, 18) for s in st]).arrange(DOWN, aligned_edge=LEFT, buff=0.14)
        g2 = VGroup(txt(ASSUME + " (슬라이드에 없는 내용)", 18, RED, weight=BOLD),
                    *[txt("– " + a, 16) for a in CFG["assumptions"]]).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        g = VGroup(g1, g2).arrange(DOWN, aligned_edge=LEFT, buff=0.4).next_to(head, DOWN, buff=0.4)
        if g.width > 13.4:
            g.scale_to_fit_width(13.4)
        self.play(FadeIn(head), FadeIn(g1, lag_ratio=0.2), run_time=1.5)
        self.wait(3)
        self.play(FadeIn(g2, lag_ratio=0.15), run_time=1.5)
        self.wait(6)
        self.play(FadeOut(VGroup(head, g)), run_time=0.6)

    # -------------------------------------------------------------- outro ----
    def outro(self):
        S = P["storage_comparison"]
        T0 = S["tomasulo_rob"]
        tot = sum(T0.values())
        vb = S["value_bits"]
        head = txt("기존 구조 vs PRF 구조", 30, weight=BOLD).to_edge(UP, buff=0.5)
        rows = [
            ("", "기존 (RS·Frontend RF·ROB·Arch RF에 값)", "PRF + 포인터"),
            ("값을 저장하는 칸", f"{T0['rs_value_fields']} + {T0['frontend_rf_values']} + {T0['rob_value_fields']} + "
             f"{T0['arch_rf_values']} = {tot}칸", f"PRF {S['prf']['prf_values']}칸"),
            ("broadcast 폭", f"태그 {S['tomasulo_tag_bits']}비트 + 값 {vb}비트 = {S['tomasulo_tag_bits'] + vb}비트",
             f"DestPR 태그 {S['prf_tag_bits']}비트 (⌈log₂{N_PR}⌉)"),
            ("RS·ROB에 들어가는 것", "값 + 태그", "PR 번호(포인터) + V 비트"),
            ("값의 이동", "결과가 RS·RF·ROB·Arch RF로 복사", "PRF에 한 번 쓰고, 맵 포인터만 바뀜"),
        ]
        ws = [3.0, 5.4, 4.6]
        g = VGroup()
        for j, row in enumerate(rows):
            y = 2.2 - j * 0.75
            x = -6.5
            for k, s in enumerate(row):
                cell = Rectangle(width=ws[k], height=0.7, stroke_color=INK, stroke_width=1)
                cell.move_to([x + ws[k] / 2, y, 0])
                if j == 0:
                    cell.set_fill(GREY, 1)
                t = txt(s, 17, BLUE if (k == 2 and j) else INK, weight=BOLD if j == 0 or k == 0 else "NORMAL")
                if t.width > ws[k] - 0.15:
                    t.scale_to_fit_width(ws[k] - 0.15)
                g.add(cell, t.move_to(cell))
                x += ws[k]
        note = VGroup(
            txt(f"총 사이클: {P['total_cycles']} (기존 Tomasulo 20 + 순서대로 retire하는 R·W 단계)", 17),
            txt("실행 시점은 기존과 같고, 달라진 것은 값을 어디에 두고 무엇을 broadcast하는가", 17),
        ).arrange(DOWN, buff=0.1).move_to([0, -2.4, 0])
        self.play(FadeIn(head), run_time=0.6)
        self.play(FadeIn(g, lag_ratio=0.05), run_time=2.5)
        self.play(FadeIn(note), run_time=0.8)
        self.wait(8)


def cycle_range():
    spec = os.environ.get("PRF_CYCLES", "")
    if not spec:
        return list(range(len(CYC)))
    a, b = spec.split("-")
    return list(range(int(a), int(b) + 1))


class PRFIntro(PRFBase):
    def construct(self):
        self.intro()


class PRFCycles(PRFBase):
    def construct(self):
        self.build_board()
        for c in cycle_range():
            self.play_cycle(c)
        self.wait(1)


class PRFPreview(PRFBase):
    def construct(self):
        self.intro()
        self.build_board()
        for c in cycle_range():
            self.play_cycle(c)
        self.wait(1)


class PRFOutro(PRFBase):
    def construct(self):
        self.outro()


class PRFFullVideo(PRFBase):
    def construct(self):
        self.intro()
        self.build_board()
        for c in range(len(CYC)):
            self.play_cycle(c)
        self.wait(1.5)
        self.play(FadeOut(*self.mobjects), run_time=1.0)
        self.outro()
