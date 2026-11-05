"""Shared datapath drawing for the inorder videos (single / multi / pipeline).

Simplified H&H single-cycle MIPS (L11 slide 55 = PDF p.23), without jump.
Every component has a FIXED position in LAYOUT so that the multi-cycle and the
pipeline videos can draw the same part at the same place.  Stage columns are
separated by STAGE_X gaps where the pipeline registers (or the multi-cycle
non-architectural registers) will be inserted.

  IF | ID | EX | MEM | WB
  PCMUX PC IMEM ADD4 | CTRL RF SIGNEXT | ALUSRCMUX ALU REGDSTMUX SL2 ADDBR AND | DMEM | RESMUX

Usage:
    dp = Datapath()              # VGroup; add to the scene
    dp.comps["ALU"], dp.wires["srcb"], dp.tags["ALUSrc"], dp.slots["SrcB"]
    anims = dp.paint(active_components, active_wires)

Colours come from common.style only.
"""
from __future__ import annotations

import numpy as np
from manim import (DOWN, LEFT, RIGHT, UP, WHITE, Arc, ArcBetweenPoints, Dot, Line, Polygon, Rectangle,
                   RoundedRectangle, Triangle, VGroup, VMobject)

from common.style import FAINT, GREY, INK, MONO, ORANGE, YEL, txt

# ------------------------------------------------------------------ layout ---
# stage boundaries (x) where pipeline registers go; and stage label centres
STAGE_X = {"IF/ID": -4.55, "ID/EX": -2.33, "EX/MEM": 0.30, "MEM/WB": 2.02}
STAGE_LABEL_X = {"IF": -5.8, "ID": -3.45, "EX": -1.0, "MEM": 1.15, "WB": 2.45}

LAYOUT = {
    # name        kind      centre          w     h     label
    "PCMUX":     ("mux",   (-6.72, 1.00), 0.24, 0.62, ""),
    "PC":        ("reg",   (-6.22, 1.00), 0.38, 0.55, "PC"),
    "IMEM":      ("box",   (-5.35, 1.00), 1.00, 1.30, "Instruction\nMemory"),
    "ADD4":      ("adder", (-5.40, -0.45), 0.42, 0.70, "+"),
    "CTRL":      ("ctrl",  (-3.30, 2.55), 1.15, 0.72, "Control\nUnit"),
    "RF":        ("box",   (-3.30, 1.00), 1.25, 1.50, "Register\nFile"),
    "SIGNEXT":   ("box",   (-3.30, -0.65), 1.05, 0.30, "Sign Extend"),
    "ALUSRCMUX": ("mux",   (-1.75, 0.70), 0.22, 0.55, ""),
    "ALU":       ("alu",   (-1.00, 1.00), 0.55, 1.10, "ALU"),
    "REGDSTMUX": ("mux",   (-1.00, -0.10), 0.22, 0.55, ""),
    "SL2":       ("box",   (-1.75, -0.65), 0.42, 0.28, "<<2"),
    "ADDBR":     ("adder", (-0.30, -0.85), 0.42, 0.70, "+"),
    "AND":       ("and",   (0.05, 2.75), 0.36, 0.34, ""),
    "DMEM":      ("box",   (1.05, 0.90), 1.10, 1.50, "Data\nMemory"),
    "RESMUX":    ("mux",   (2.45, 0.90), 0.22, 0.62, ""),
}

# mux input order (top, bottom) -> select value
MUX_INPUTS = {"PCMUX": ("1", "0"), "ALUSRCMUX": ("0", "1"),
              "REGDSTMUX": ("0", "1"), "RESMUX": ("1", "0")}

# ports (absolute coordinates)
P = {
    "pcmux_in1": (-6.84, 1.15), "pcmux_in0": (-6.84, 0.85), "pcmux_out": (-6.60, 1.00),
    "pcmux_sel": (-6.72, 1.31),
    "pc_in": (-6.41, 1.00), "pc_out": (-6.03, 1.00),
    "imem_a": (-5.85, 1.00), "imem_rd": (-4.85, 1.00),
    "add4_a": (-5.61, -0.30), "add4_b": (-5.61, -0.60), "add4_y": (-5.19, -0.45),
    "ctrl_in": (-3.875, 2.55), "ctrl_branch": (-2.725, 2.85),
    "rf_a1": (-3.925, 1.45), "rf_a2": (-3.925, 1.00), "rf_a3": (-3.925, 0.55), "rf_wd3": (-3.925, 0.35),
    "rf_rd1": (-2.675, 1.30), "rf_rd2": (-2.675, 0.85), "rf_we": (-3.30, 1.75),
    "se_in": (-3.825, -0.65), "se_out": (-2.775, -0.65),
    "asm_in0": (-1.86, 0.85), "asm_in1": (-1.86, 0.55), "asm_out": (-1.64, 0.70),
    "alu_a": (-1.275, 1.30), "alu_b": (-1.275, 0.70), "alu_y": (-0.725, 1.00), "alu_zero": (-0.725, 1.30),
    "rdm_in0": (-1.11, 0.05), "rdm_in1": (-1.11, -0.25), "rdm_out": (-0.89, -0.10),
    "sl2_in": (-1.96, -0.65), "sl2_out": (-1.54, -0.65),
    "addbr_a": (-0.51, -0.70), "addbr_b": (-0.51, -1.00), "addbr_y": (-0.09, -0.85),
    "and_a": (-0.13, 2.85), "and_b": (-0.13, 2.65), "and_y": (0.23, 2.75),
    "dm_a": (0.50, 1.25), "dm_wd": (0.50, 0.40), "dm_rd": (1.60, 1.25), "dm_we": (1.05, 1.65),
    "rsm_in1": (2.34, 1.05), "rsm_in0": (2.34, 0.75), "rsm_out": (2.56, 0.90),
}

SPINE_X = -4.30      # instruction bus
X_PC4 = -4.75        # PC+4 bus
Y_PC4 = -1.00
Y_PCBR = -1.20
Y_RES = -1.38
X_RES = -4.45
X_WREG = -4.05
Y_WREG = -0.42
Y_TOP = 3.10

# wire name -> list of points (polyline, arrow at the end)
WIRES = {
    "pcnext":        [P["pcmux_out"], P["pc_in"]],
    "pc_imem":       [P["pc_out"], P["imem_a"]],
    "pc_add4":       [(-5.95, 1.00), (-5.95, -0.30), P["add4_a"]],
    "four_add4":     [(-5.90, -0.60), P["add4_b"]],
    "pcplus4_pcmux": [P["add4_y"], (X_PC4, -0.45), (X_PC4, Y_PC4), (-6.95, Y_PC4), (-6.95, 0.85),
                      P["pcmux_in0"]],
    "pcplus4_addbr": [P["add4_y"], (X_PC4, -0.45), (X_PC4, Y_PC4), P["addbr_b"]],
    "instr_ctrl":    [P["imem_rd"], (SPINE_X, 1.00), (SPINE_X, 2.55), P["ctrl_in"]],
    "instr_a1":      [P["imem_rd"], (SPINE_X, 1.00), (SPINE_X, 1.45), P["rf_a1"]],
    "instr_a2":      [P["imem_rd"], P["rf_a2"]],
    "instr_rt_wr":   [P["imem_rd"], (SPINE_X, 1.00), (SPINE_X, 0.05), P["rdm_in0"]],
    "instr_rd_wr":   [P["imem_rd"], (SPINE_X, 1.00), (SPINE_X, -0.25), P["rdm_in1"]],
    "instr_imm":     [P["imem_rd"], (SPINE_X, 1.00), (SPINE_X, -0.65), P["se_in"]],
    "writereg":      [P["rdm_out"], (-0.75, -0.10), (-0.75, Y_WREG), (X_WREG, Y_WREG), (X_WREG, 0.55),
                      P["rf_a3"]],
    "rd1_srca":      [P["rf_rd1"], P["alu_a"]],
    "rd2_alusrc":    [P["rf_rd2"], P["asm_in0"]],
    "rd2_wd":        [P["rf_rd2"], (-2.20, 0.85), (-2.20, 0.40), P["dm_wd"]],
    "signimm_alusrc": [P["se_out"], (-2.45, -0.65), (-2.45, 0.55), P["asm_in1"]],
    "signimm_sl2":   [P["se_out"], P["sl2_in"]],
    "srcb":          [P["asm_out"], P["alu_b"]],
    "sl2_addbr":     [P["sl2_out"], (-0.80, -0.65), (-0.80, -0.70), P["addbr_a"]],
    "aluresult_addr": [P["alu_y"], (0.10, 1.00), (0.10, 1.25), P["dm_a"]],
    "aluresult_res": [P["alu_y"], (0.10, 1.00), (0.10, -0.05), (2.15, -0.05), (2.15, 0.75), P["rsm_in0"]],
    "readdata_res":  [P["dm_rd"], (2.00, 1.25), (2.00, 1.05), P["rsm_in1"]],
    "result_wd3":    [P["rsm_out"], (2.75, 0.90), (2.75, Y_RES), (X_RES, Y_RES), (X_RES, 0.35), P["rf_wd3"]],
    "zero_and":      [P["alu_zero"], (-0.40, 1.30), (-0.40, 2.65), P["and_b"]],
    "branch_and":    [P["ctrl_branch"], P["and_a"]],
    "pcsrc":         [P["and_y"], (0.45, 2.75), (0.45, Y_TOP), (-6.72, Y_TOP), P["pcmux_sel"]],
    "pcbranch":      [P["addbr_y"], (0.15, -0.85), (0.15, Y_PCBR), (-7.03, Y_PCBR), (-7.03, 1.15),
                      P["pcmux_in1"]],
}
JUNCTIONS = [(-5.95, 1.00), (X_PC4, -0.45), (X_PC4, Y_PC4), (SPINE_X, 1.00), (SPINE_X, 0.05),
             (SPINE_X, -0.25), (SPINE_X, 1.45), (-2.20, 0.85), (-2.45, -0.65), (0.10, 1.00)]

# small control-signal tags next to the unit they control
TAGS = {"RegWrite": ((-3.30, 1.90), "RegWrite"), "RegDst": ((-1.00, -0.50), "RegDst"),
        "ALUSrc": ((-1.75, 1.10), "ALUSrc"), "ALUControl": ((-1.00, 1.72), "ALUControl"),
        "Branch": ((-1.75, 2.98), "Branch"), "MemWrite": ((1.05, 1.80), "MemWrite"),
        "MemtoReg": ((2.45, 1.36), "MemtoReg"), "PCSrc": ((-6.10, 3.26), "PCSrc")}

# where data values are written (anchor, direction)
SLOTS = {
    "PC": ((-6.22, 0.55), DOWN), "Instr": ((-5.35, 1.80), UP), "PCPlus4": ((-4.95, -0.85), DOWN),
    "RD1": ((-2.15, 1.43), UP), "RD2": ((-2.45, 0.96), UP), "SignImm": ((-2.62, -0.80), DOWN),
    "SrcB": ((-1.48, 0.55), DOWN), "ALUResult": ((-0.33, 0.86), DOWN), "Zero": ((-0.40, 2.05), RIGHT),
    "WriteReg": ((-0.42, -0.24), RIGHT), "PCBranch": ((-0.30, -1.30), DOWN),
    "ReadData": ((1.75, 1.40), UP), "WriteData": ((0.0, 0.30), DOWN), "Result": ((2.98, 0.35), RIGHT),
}


# ------------------------------------------------------------------ shapes ---
def _label(s, size=12, color=INK):
    parts = s.split("\n")
    g = VGroup(*[txt(p, size, color) for p in parts]).arrange(DOWN, buff=0.04)
    return g


def _shape(kind, c, w, h):
    x, y = c
    if kind in ("box", "reg"):
        return Rectangle(width=w, height=h).move_to([x, y, 0])
    if kind == "ctrl":
        return RoundedRectangle(corner_radius=0.12, width=w, height=h).move_to([x, y, 0])
    if kind == "mux":
        return RoundedRectangle(corner_radius=w / 2 - 0.001, width=w, height=h).move_to([x, y, 0])
    if kind in ("alu", "adder"):
        x0, x1 = x - w / 2, x + w / 2
        pts = [(x0, y + h / 2), (x1, y + h / 4), (x1, y - h / 4), (x0, y - h / 2),
               (x0, y - h / 10), (x0 + w * 0.28, y), (x0, y + h / 10)]
        return Polygon(*[[a, b, 0] for a, b in pts])
    if kind == "or":
        x0, x1 = x - w / 2, x + w / 2
        back = ArcBetweenPoints([x0, y + h / 2, 0], [x0, y - h / 2, 0], angle=-0.9)
        top = ArcBetweenPoints([x0, y + h / 2, 0], [x1, y, 0], angle=-0.6)
        bot = ArcBetweenPoints([x0, y - h / 2, 0], [x1, y, 0], angle=0.6)
        return VGroup(back, top, bot)
    if kind == "and":
        x0 = x - w / 2
        body = VMobject()
        body.set_points_as_corners([[x, y + h / 2, 0], [x0, y + h / 2, 0], [x0, y - h / 2, 0],
                                    [x, y - h / 2, 0]])
        arc = Arc(radius=h / 2, start_angle=-np.pi / 2, angle=np.pi, arc_center=[x, y, 0])
        return VGroup(body, arc)
    raise ValueError(kind)


class Part(VGroup):
    """A datapath component: outline + label (+ mux input numbers)."""

    def __init__(self, name, kind, c, w, h, label, mux_labels=None):
        super().__init__()
        self.name, self.kind = name, kind
        self.body = _shape(kind, c, w, h)
        self.body.set_stroke(INK, 1.8).set_fill(WHITE, 1)
        self.add(self.body)
        self.labels = VGroup()
        if label:
            lab = _label(label, 11 if kind != "alu" else 12)
            maxw = w * (0.62 if kind == "box" and h > 1 else 0.92)
            if lab.width > maxw and kind not in ("adder",):
                lab.scale_to_fit_width(maxw)
            lab.move_to([c[0] + (0.05 if kind in ("alu", "adder") else 0), c[1], 0])
            self.labels.add(lab)
        if kind == "reg":    # clock triangle
            tri = Triangle().scale(0.06).rotate(np.pi).move_to([c[0], c[1] + h / 2 - 0.05, 0])
            tri.set_stroke(INK, 1)
            self.labels.add(tri)
        if mux_labels:
            for t_, yy in mux_labels:
                self.labels.add(txt(t_, 7).move_to([c[0], yy, 0]))
        elif name in MUX_INPUTS:
            top, bot = MUX_INPUTS[name]
            self.labels.add(txt(top, 9).move_to([c[0], c[1] + h / 2 - 0.12, 0]),
                            txt(bot, 9).move_to([c[0], c[1] - h / 2 + 0.12, 0]))
        self.add(self.labels)

    def style(self, mode):
        """mode: 'idle' (normal), 'off' (grey, unused), 'on' (used), 'hot' (signal now)."""
        if mode == "off":
            self.body.set_stroke(FAINT, 1.2).set_fill(GREY, 1)
            self.labels.set_color(FAINT)
        elif mode == "on":
            self.body.set_stroke(INK, 2.2).set_fill(YEL, 1)
            self.labels.set_color(INK)
        elif mode == "hot":
            self.body.set_stroke(INK, 2.6).set_fill(ORANGE, 0.55)
            self.labels.set_color(INK)
        else:
            self.body.set_stroke(INK, 1.8).set_fill(WHITE, 1)
            self.labels.set_color(INK)
        if self.kind in ("and", "or"):
            self.body.set_fill(opacity=0)
        return self


class Wire(VGroup):
    def __init__(self, name, pts):
        super().__init__()
        self.name = name
        pts3 = [np.array([a, b, 0.0]) for a, b in pts]
        self.line = VMobject().set_points_as_corners(pts3)
        d = pts3[-1] - pts3[-2]
        ang = np.arctan2(d[1], d[0])
        self.tip = Triangle().scale(0.045).rotate(ang - np.pi / 2).move_to(pts3[-1] - 0.03 * d / np.linalg.norm(d))
        self.add(self.line, self.tip)
        self.style("idle")

    def style(self, mode):
        if mode == "off":
            self.line.set_stroke(FAINT, 1.0, opacity=0.55)
            self.tip.set_stroke(width=0).set_fill(FAINT, 0.55)
        elif mode == "on":
            self.line.set_stroke(ORANGE, 3.2, opacity=1)
            self.tip.set_stroke(width=0).set_fill(ORANGE, 1)
        else:
            self.line.set_stroke(INK, 1.4, opacity=1)
            self.tip.set_stroke(width=0).set_fill(INK, 1)
        return self


class Datapath(VGroup):
    """variant='single' (L11 55) or 'multi' (multi-cycle deck slide 57)."""

    def __init__(self, parts=None, wires=None, variant="single"):
        super().__init__()
        self.variant = variant
        if variant == "multi":
            lay, wdef, junc, tags, ports, slots = MC_LAYOUT, MC_WIRES, MC_JUNCTIONS, MC_TAGS, MC_PORTS, MC_SLOTS
        else:
            lay, wdef, junc, tags, ports, slots = LAYOUT, WIRES, JUNCTIONS, TAGS, None, SLOTS
        self.slots = slots
        self.comps = {n: Part(n, *lay[n][:5], mux_labels=MC_MUX_LABELS.get(n) if variant == "multi" else None)
                      for n in (parts or lay)}
        self.wires = {n: Wire(n, wdef[n]) for n in (wires or wdef)}
        self.wire_group = VGroup(*self.wires.values())
        self.comp_group = VGroup(*self.comps.values())
        self.dots = VGroup(*[Dot([x, y, 0], radius=0.03, color=INK) for x, y in junc])
        if variant == "multi":
            self.four = txt("4", 10).move_to([MC_FOUR[0], MC_FOUR[1], 0])
        else:
            self.four = txt("4", 11).move_to([-5.98, -0.60, 0]).shift(LEFT * 0.04)
        self.fields = VGroup() if variant == "multi" else VGroup(
            txt("25:21", 8).move_to([-4.12, 1.53, 0]),
            txt("20:16", 8).move_to([-4.12, 1.08, 0]),
            txt("20:16", 8).move_to([-3.40, 0.13, 0]),
            txt("15:11", 8).move_to([-3.40, -0.17, 0]),
            txt("15:0", 8).move_to([-4.12, -0.57, 0]),
            txt("31:26, 5:0", 8).move_to([-4.62, 2.66, 0]),
        )
        ports = ports or [
            ("A1", -3.78, 1.45), ("A2", -3.78, 1.00), ("A3", -3.78, 0.55), ("WD3", -3.74, 0.35),
            ("RD1", -2.84, 1.30), ("RD2", -2.84, 0.85), ("A", -5.75, 1.00), ("RD", -4.97, 1.00),
            ("A", 0.60, 1.25), ("WD", 0.63, 0.40), ("RD", 1.48, 1.25), ("Zero", -0.56, 1.40)]
        self.ports = VGroup(*[txt(s_, 8).move_to([x, y, 0]) for s_, x, y in ports])
        self.tags = {}
        for k, (pos, name) in tags.items():
            self.tags[k] = txt(name, 9, ORANGE).move_to([pos[0], pos[1], 0])
        self.tag_group = VGroup(*self.tags.values())
        self.add(self.wire_group, self.dots, self.comp_group, self.four, self.fields, self.ports,
                 self.tag_group)

    def slot(self, name):
        return self.slots[name]

    def paint(self, comps, wires, unused="off"):
        """Set used parts to 'on' and the rest to `unused`; returns nothing (instant)."""
        for n, c in self.comps.items():
            c.style("on" if n in comps else unused)
        for n, w in self.wires.items():
            w.style("on" if n in wires else unused)
            if n in wires:
                w.set_z_index(2)
            else:
                w.set_z_index(0)
        for n, t in self.tags.items():
            t.set_opacity(1)

    def reset(self):
        for c in self.comps.values():
            c.style("idle")
        for w in self.wires.values():
            w.style("idle").set_z_index(0)


# ====================================================================== multi ===
# Multi-cycle variant, drawn after the H&H multi-cycle processor figure the user
# supplied (inorder/slides/B_multi_cycle_datapath_ref.png, 1100x555 px, no jump;
# same figure as slide 57 = PDF p.29).  Coordinates below are pixel positions in
# that image, mapped linearly onto the datapath area x -7.0..3.1, y 3.30..-1.45.
_KX, _KY = 10.1 / 1020, 4.75 / 530


def _px(x, y):
    return (round(-7.0 + (x - 55) * _KX, 4), round(3.30 - (y - 15) * _KY, 4))


def _part(kind, x, y, w, h, label=""):
    return (kind, _px(x, y), w * _KX, h * _KY, label)


def _path(*pts):
    return [_px(x, y) for x, y in pts]


MC_LAYOUT = {
    "PC":      _part("reg", 90.5, 301, 24, 42, "PC"),
    "IORDMUX": _part("mux", 152, 312, 20, 42),
    "MEM":     _part("box", 235.5, 332.5, 83, 125, "Instr/Data\nMemory"),
    "IR":      _part("reg", 329, 301, 24, 42, "IR"),
    "DATA":    _part("reg", 329, 405, 24, 42, "Data"),
    "CTRL":    _part("ctrl", 443.5, 141.5, 63, 155, "Control\nUnit"),
    "REGDSTMUX": _part("mux", 422, 353, 20, 42),
    "RESMUX":  _part("mux", 464, 395, 20, 42),
    "RF":      _part("box", 547.5, 342.5, 125, 145, "Register\nFile"),
    "SIGNEXT": _part("box", 547.5, 478, 125, 40, "Sign Extend"),
    "A":       _part("reg", 630.5, 290, 21, 30, "A"),
    "B":       _part("reg", 630.5, 316, 21, 30, "B"),
    "SRCAMUX": _part("mux", 724, 281, 22, 42),
    "SRCBMUX": _part("mux", 766, 343, 42, 84),
    "SL2":     _part("box", 725, 425, 42, 40, "<<2"),
    "ALU":     _part("alu", 849, 317, 42, 84, "ALU"),
    "ALUOUT":  _part("reg", 973, 318, 24, 42, "ALU\nOut"),
    "PCMUX":   _part("mux", 1046, 307, 22, 42),
    "AND":     _part("and", 929, 99.5, 26, 22),
    "OR":      _part("or", 966, 93.5, 28, 23),
}
MC_MUX_LABELS = {
    "IORDMUX": [("0", _px(0, 302)[1]), ("1", _px(0, 322)[1])],
    "REGDSTMUX": [("0", _px(0, 340)[1]), ("1", _px(0, 362)[1])],
    "RESMUX": [("0", _px(0, 385)[1]), ("1", _px(0, 405)[1])],
    "SRCAMUX": [("0", _px(0, 270)[1]), ("1", _px(0, 291)[1])],
    "SRCBMUX": [("00", _px(0, 313)[1]), ("01", _px(0, 333)[1]), ("10", _px(0, 353)[1]),
                ("11", _px(0, 373)[1])],
    "PCMUX": [("0", _px(0, 296)[1]), ("1", _px(0, 317)[1])],
}
_S = 381.5      # instruction bus
MC_WIRES = {
    "pcnext":           _path((1056, 307), (1068, 307), (1068, 540), (59, 540), (59, 302), (80, 302)),
    "pc_iord":          _path((101, 302), (142, 302)),
    "pc_srca":          _path((101, 302), (131, 302), (131, 229), (703, 229), (703, 270), (713, 270)),
    "iord_adr":         _path((162, 312), (194, 312)),
    "aluout_iord":      _path((984, 317), (1025, 317), (1025, 518), (131, 518), (131, 322), (142, 322)),
    "mem_ir":           _path((277, 302), (318, 302)),
    "mem_data":         _path((277, 302), (298, 302), (298, 405), (318, 405)),
    "b_wd":             _path((641, 316), (662, 316), (662, 436), (173, 436), (173, 374), (194, 374)),
    "ir_ctrl":          _path((340, 302), (_S, 302), (_S, 177), (412, 177)),
    "ir_a1":            _path((340, 302), (_S, 302), (_S, 291), (485, 291)),
    "ir_a2":            _path((340, 302), (_S, 302), (_S, 312), (485, 312)),
    "ir_rt_wr":         _path((340, 302), (_S, 302), (_S, 340), (412, 340)),
    "ir_rd_wr":         _path((340, 302), (_S, 302), (_S, 361), (412, 361)),
    "ir_imm":           _path((340, 302), (_S, 302), (_S, 478), (485, 478)),
    "writereg":         _path((432, 353), (485, 353)),
    "data_res":         _path((340, 405), (454, 405)),
    "aluout_res":       _path((984, 317), (1025, 317), (1025, 518), (443, 518), (443, 385), (454, 385)),
    "result_wd3":       _path((474, 395), (485, 395)),
    "rd1_a":            _path((610, 291), (620, 291)),
    "rd2_b":            _path((610, 316), (620, 316)),
    "a_srca":           _path((641, 291), (713, 291)),
    "b_srcb":           _path((641, 316), (745, 316)),
    "four_srcb":        _path((722, 333), (745, 333)),
    "signimm_srcb":     _path((610, 475), (682, 475), (682, 353), (745, 353)),
    "signimm_sl2":      _path((610, 475), (725, 475), (725, 446)),
    "sl2_srcb":         _path((725, 405), (725, 373), (745, 373)),
    "srca":             _path((735, 281), (816, 281), (816, 291), (828, 291)),
    "srcb":             _path((787, 343), (828, 343)),
    "aluresult_aluout": _path((870, 317), (962, 317)),
    "aluresult_pcmux":  _path((870, 317), (952, 317), (952, 260), (1025, 260), (1025, 296), (1035, 296)),
    "aluout_pcmux":     _path((984, 317), (1035, 317)),
    "zero_and":         _path((870, 292), (910, 292), (910, 105), (916, 105)),
    "branch_and":       _path((475, 87), (900, 87), (900, 94), (916, 94)),
    "pcwrite_or":       _path((475, 66), (947, 66), (947, 87), (955, 87)),
    "and_or":           _path((942, 100), (955, 100)),
    "pcen":             _path((980, 94), (994, 94), (994, 22), (69, 22), (69, 333), (90, 333), (90, 322)),
}
MC_JUNCTIONS = [_px(*q) for q in [(131, 302), (298, 302), (_S, 302), (_S, 291), (_S, 312), (_S, 340),
                                  (_S, 361), (662, 316), (682, 475), (952, 317), (1025, 317),
                                  (1025, 518)]]
MC_TAGS = {k: (_px(x, y), k) for k, x, y in [
    ("PCWrite", 640, 58), ("Branch", 640, 79), ("PCSrc", 1046, 276), ("IorD", 152, 280),
    ("MemWrite", 236, 258), ("IRWrite", 300, 266), ("RegDst", 422, 322), ("MemtoReg", 464, 428),
    ("RegWrite", 547, 258), ("ALUSrcA", 724, 248), ("ALUSrcB", 774, 292), ("ALUControl", 849, 266)]}
MC_PORTS = [(t, *_px(x, y)) for t, x, y in [
    ("A", 202, 312), ("RD", 266, 302), ("WD", 206, 374), ("EN", 90.5, 314), ("EN", 329, 314),
    ("A1", 497, 291), ("A2", 497, 312), ("A3", 497, 353), ("WD3", 500, 395), ("RD1", 597, 291),
    ("RD2", 597, 316), ("Zero", 888, 284), ("Op", 400, 172), ("Funct", 398, 196), ("PCEn", 1010, 84),
    ("25:21", 398, 286), ("20:16", 398, 307), ("20:16", 398, 335),
    ("15:11", 398, 356), ("15:0", 398, 472)]]
MC_FOUR = _px(712, 333)
MC_SLOTS = {k: (_px(x, y), d) for k, x, y, d in [
    ("PC", 112, 352, DOWN), ("Adr", 178, 298, UP), ("ReadData", 296, 285, UP), ("IR", 329, 252, UP),
    ("Data", 329, 440, DOWN), ("RD1", 660, 280, UP), ("RD2", 700, 326, DOWN), ("SignImm", 640, 466, UP),
    ("SrcA", 785, 270, UP), ("SrcB", 805, 333, UP), ("ALUResult", 912, 330, DOWN),
    ("Zero", 896, 278, UP), ("ALUOut", 1000, 350, DOWN), ("WriteReg", 452, 343, UP),
    ("WD3", 476, 420, DOWN), ("WriteData", 420, 448, DOWN), ("PCNext", 1040, 530, UP)]}
