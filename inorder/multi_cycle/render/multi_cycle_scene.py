"""Multi-cycle MIPS video renderer.  Reads ONLY simulator traces:
inorder/multi_cycle/out/trace.json (and, for the final comparison,
inorder/single_cycle/out/trace.json).

    # preview of the first N cycles (stage 2: first two instructions = 9 cycles)
    MC_STEPS=9 manim -ql --media_dir /tmp/media inorder/multi_cycle/render/multi_cycle_scene.py MultiCycle
    # full video
    manim --resolution 1920,1080 --frame_rate 30 --media_dir /tmp/media \
          inorder/multi_cycle/render/multi_cycle_scene.py MultiCycle
    # check only (no frames)
    manim --dry_run inorder/multi_cycle/render/multi_cycle_scene.py MultiCycle
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from manim import (BOLD, DOWN, LEFT, RIGHT, UP, WHITE, Create, DashedLine, FadeIn, FadeOut,  # noqa: E402
                   Group, Line, Rectangle, RoundedRectangle, ValueTracker, VGroup, linear)

from common.style import (ASSUME, BLUE, FAINT, GREY, INK, MONO, ORANGE, RED, YEL,  # noqa: E402
                          YEL_STRONG, Cell, StyleScene, term, txt)
from inorder.shared.datapath import Datapath  # noqa: E402
from inorder.shared.isa import reg_name  # noqa: E402

TRACE = ROOT / "inorder/multi_cycle/out/trace.json"
SC_TRACE = ROOT / "inorder/single_cycle/out/trace.json"
STAGES = ["IF", "ID", "EX", "MEM", "WB"]
STAGE_LBL_X = [-6.0, -4.3, -2.6, -0.9, 0.8]
SIG_L = ["IorD", "MemWrite", "IRWrite", "PCWrite", "Branch", "PCSrc"]
SIG_R = ["ALUSrcA", "ALUSrcB", "ALUOp", "ALUControl", "RegDst", "MemtoReg", "RegWrite"]
NONARCH = [("PC", "IR"), ("A", "B"), ("ALUOut", "Data")]
OPSYM = {"add": "+", "sub": "-", "and": "&", "or": "|", "slt": "<"}

# value label -> wires (any used one makes it visible)
SLOT_WIRES = {"PC": ["pc_iord", "pc_srca"], "Adr": ["iord_adr"], "ReadData": ["mem_ir", "mem_data"],
              "IR": ["ir_a1", "ir_imm", "ir_rt_wr", "ir_rd_wr"], "Data": ["data_res"],
              "RD1": ["rd1_a"], "RD2": ["rd2_b"], "SignImm": ["signimm_srcb", "signimm_sl2"],
              "SrcA": ["srca"], "SrcB": ["srcb"], "ALUResult": ["aluresult_aluout", "aluresult_pcmux"],
              "Zero": ["zero_and"], "ALUOut": ["aluout_iord", "aluout_res", "aluout_pcmux"],
              "WriteReg": ["writereg"], "WD3": ["result_wd3"], "WriteData": ["b_wd"],
              "PCNext": ["pcnext"]}

ROWS = [("MEM", term("메모리", "memory")), ("RF", "레지스터 읽기"), ("ALU", "ALU"),
        ("RF_W", "레지스터 쓰기")]
TL_X0, TL_X1 = -5.25, 2.95
TL_Y0, TL_DY = -1.70, 0.17
LBL_X = -6.15
SEC_PER_PS = 0.017            # same pace as the single-cycle video


def hx(v, w=2):
    return f"0x{v:0{w}X}"


def nv(v):
    """number for a panel cell: large values (instruction words read into Data) in hex."""
    return str(v) if abs(v) < 100000 else f"0x{v & 0xFFFFFFFF:08X}"


class Board:
    SUB_Y = StyleScene.SUB_Y

    def __init__(self):
        self.phase_labels = VGroup(*[txt(s, 15, FAINT, weight=BOLD).move_to([x, 3.62, 0])
                                     for s, x in zip(STAGES, STAGE_LBL_X)])
        self.phase_hl = None


class MultiCycle(StyleScene):
    def construct(self):
        self.T = json.loads(TRACE.read_text())
        self.period = self.T["config"]["period_ps"]
        n_env = os.environ.get("MC_STEPS")
        steps = self.T["steps"][: int(n_env)] if n_env else self.T["steps"]
        self.B = Board()
        self.intro()
        self.build_board()
        for st in steps:
            self.cycle(st)
        self.finale(len(steps) == len(self.T["steps"]))

    # ------------------------------------------------------------- intro ---
    def intro(self):
        cfg = self.T["config"]
        t1 = txt("Multi-cycle MIPS 프로세서", 44, weight=BOLD)
        t2 = txt("명령어 하나 = 짧은 클록 사이클 여러 개", 28)
        t3 = txt("ETH DDCA · Onur Mutlu  |  Harris & Harris 7.4", 20, FAINT)
        g = VGroup(t1, t2, t3).arrange(DOWN, buff=0.35).move_to([0, 0.4, 0])
        self.play(FadeIn(g, shift=UP * 0.2))
        self.pause(1.5)
        self.play(FadeOut(g))

        head = txt("3편 공통 프로그램 (1편과 같음)", 28, weight=BOLD).move_to([0, 3.45, 0])
        rows = VGroup()
        for i, p in enumerate(cfg["program"]):
            r = VGroup(txt(f"I{i + 1}", 15, FAINT, font=MONO), txt(hx(p["addr"]), 15, FAINT, font=MONO),
                       txt(p["text"], 16, font=MONO))
            r[0].move_to([-3.6, 0, 0]); r[1].move_to([-2.9, 0, 0])
            r[2].move_to([-2.3, 0, 0], aligned_edge=LEFT)
            r.move_to([r.get_x(), 2.85 - 0.5 * i, 0])
            rows.add(r)
        init = ", ".join(f"{k}={v}" for k, v in cfg["init_regs"].items())
        mem = ", ".join(f"Mem[{k}]={v}" for k, v in cfg["init_mem"].items())
        foot = txt(f"초기값: {init}  (나머지 0)   |   {mem}", 15).move_to([0, -2.35, 0])
        executed = {i["pc"] for i in self.T["instr_states"]}
        self.play(FadeIn(head), FadeIn(rows, lag_ratio=0.08, run_time=self.rt(1.6)), FadeIn(foot))
        for i, p in enumerate(cfg["program"]):
            if p["addr"] not in executed:
                self.play(rows[i].animate.set_opacity(0.35), run_time=self.rt(0.4))
        self.say(["1편과 같은 프로그램·초기값. 이번에는 명령어를 여러 개의 짧은 단계(사이클)로 나눠 실행한다.",
                  "명령어와 데이터가 메모리 하나를 같이 쓰므로, 데이터는 프로그램 위쪽 0x40부터 둔다."], wait=3.5)
        self.play(FadeOut(VGroup(head, rows, foot)), FadeOut(self.sub))
        self.sub = None

    # ------------------------------------------------------------- board ---
    def build_board(self):
        cfg = self.T["config"]
        self.dp = Datapath(variant="multi")
        self.dp.reset()

        self.hdr = txt("사이클 – / –", 15).move_to([5.2, 3.62, 0])
        self.ins_box = RoundedRectangle(corner_radius=0.06, width=3.55, height=0.34, stroke_width=0)
        self.ins_box.set_fill(YEL, 1).move_to([5.2, 3.27, 0])
        self.ins = txt("–", 15, font=MONO).move_to([5.2, 3.27, 0]).set_opacity(0)
        self.chips = VGroup()

        ctl_t = txt(term("제어 신호", "control"), 13, weight=BOLD).move_to([5.2, 2.66, 0])
        self.ctl = {}
        cg = VGroup(ctl_t)
        for col, names in ((0, SIG_L), (1, SIG_R)):
            for i, s in enumerate(names):
                y = 2.45 - 0.19 * i
                xn, xv = (3.97, 4.82) if col == 0 else (5.62, 6.52)
                a = Cell(xn, y, 1.04, 0.19, s, size=11, font=MONO)
                b = Cell(xv, y, 0.66 if col == 0 else 0.86, 0.19, "", size=11, font=MONO)
                self.ctl[s] = b
                cg.add(a.mobs(), b.mobs())

        na_t = txt(term("중간 레지스터", "non-architectural"), 13, weight=BOLD).move_to([5.2, 1.0, 0])
        self.na = {}
        ng = VGroup(na_t)
        first = self.T["steps"][0]["regs_before"]
        for r, pair in enumerate(NONARCH):
            for col, n in enumerate(pair):
                y = 0.79 - 0.2 * r
                xn, xv = (3.72, 4.47) if col == 0 else (5.47, 6.22)
                a = Cell(xn, y, 0.55, 0.2, n, size=11, font=MONO)
                b = Cell(xv, y, 0.95, 0.2, self.na_text(n, first[n]), size=11, font=MONO)
                self.na[n] = b
                ng.add(a.mobs(), b.mobs())

        reg_t = txt(term("레지스터", "register file"), 13, weight=BOLD).move_to([5.2, 0.12, 0])
        self.regs = {}
        rg = VGroup(reg_t)
        for i, n in enumerate(cfg["show_regs"]):
            col, row = divmod(i, 6)
            y = -0.09 - 0.19 * row
            xn, xv = (3.73, 4.58) if col == 0 else (5.48, 6.33)
            a = Cell(xn, y, 0.56, 0.19, n, size=11, font=MONO)
            b = Cell(xv, y, 1.14, 0.19, str(cfg["init_regs"].get(n, 0)), size=11, font=MONO)
            self.regs[n] = b
            rg.add(a.mobs(), b.mobs())

        mem_t = txt(term("메모리 데이터", "memory"), 13, weight=BOLD).move_to([5.2, -1.33, 0])
        self.mem = {}
        mg = VGroup(mem_t)
        for i, a_ in enumerate(cfg["show_mem"]):
            y = -1.53 - 0.19 * i
            a = Cell(4.32, y, 1.74, 0.19, f"Mem[{a_}]", size=11, font=MONO)
            b = Cell(6.05, y, 1.72, 0.19, str(cfg["init_mem"].get(a_, 0)), size=11, font=MONO)
            self.mem[a_] = b
            mg.add(a.mobs(), b.mobs())

        self.tot1 = txt("–", 13, font=MONO).move_to([5.2, -2.2, 0]).set_opacity(0)
        self.tot2 = txt("–", 11, FAINT).move_to([5.2, -2.45, 0]).set_opacity(0)
        self.tot3 = txt("–", 11, RED).move_to([5.2, -2.68, 0]).set_opacity(0)

        tl = VGroup(Line([TL_X0, TL_Y0 + 0.1, 0], [TL_X1, TL_Y0 + 0.1, 0], stroke_width=1.2, color=INK))
        for ps in range(0, self.period + 1, 50):
            x = self.px(ps)
            tl.add(Line([x, TL_Y0 + 0.07, 0], [x, TL_Y0 + 0.13, 0], stroke_width=1, color=INK),
                   txt(f"{ps}", 9, INK, font=MONO).move_to([x, TL_Y0 + 0.21, 0]),
                   DashedLine([x, TL_Y0 + 0.07, 0], [x, TL_Y0 - TL_DY * 4.6, 0], stroke_width=0.6,
                              color=FAINT, dash_length=0.04))
        tl.add(txt("ps", 9, INK, font=MONO).move_to([TL_X1 + 0.22, TL_Y0 + 0.21, 0]))
        for i, (_, lbl) in enumerate(ROWS):
            tl.add(txt(lbl, 10).move_to([LBL_X, TL_Y0 - TL_DY * i, 0]))
        self.sum_y = TL_Y0 - TL_DY * 4 - 0.03
        tl.add(txt("이 사이클 / 클록", 10, weight=BOLD).move_to([LBL_X, self.sum_y, 0]))
        tl.add(Line([self.px(self.period), TL_Y0 + 0.1, 0], [self.px(self.period), self.sum_y - 0.1, 0],
                    stroke_width=2.2, color=RED))
        self.tl = tl

        self.play(FadeIn(self.dp, run_time=self.rt(1.2)))
        self.play(FadeIn(self.B.phase_labels), FadeIn(self.hdr), FadeIn(cg), FadeIn(ng), FadeIn(rg),
                  FadeIn(mg), run_time=self.rt(0.8))
        self.say(["H&H multi-cycle 데이터패스: 메모리 하나(명령어+데이터), ALU 하나(PC+4·주소·연산 모두).",
                  "사이클 사이의 값은 중간 레지스터 IR·A·B·ALUOut·Data에 잠시 보관한다."], wait=3.5)
        self.say(["제어 유닛은 FSM: 상태(S0–S10)마다 제어 신호가 정해지고, 명령어 종류에 따라 다음 상태로 간다.",
                  f"{ASSUME}: FSM 그림에 없는 쓰기 신호는 0, mux 선택은 X(don't care). j 경로와 대부분의 제어선은 생략."],
                 wait=3.5)
        d = cfg["delays_ps"]
        self.play(FadeIn(tl, run_time=self.rt(0.8)))
        self.say([f"지연은 1편과 같다: 메모리 {d['mem']}ps, ALU {d['alu']}ps, 레지스터 파일 {d['rf']}ps.",
                  f"{ASSUME}: 슬라이드에 클록 값이 없어, 가장 긴 단계(메모리 {d['mem']}ps)로 클록 {self.period}ps를 잡았다."],
                 wait=3.5)
        self.cum_cycles, self.cum_used, self.done = 0, 0, 0
        self.bars, self.slot_mobs, self.blue_cells = VGroup(), [], []
        self.cur_instr = None

    def na_text(self, n, v):
        if n == "PC":
            return hx(v)
        if n == "IR":
            return v
        return nv(v)

    def px(self, ps):
        return TL_X0 + (TL_X1 - TL_X0) * ps / self.period

    # ------------------------------------------------------------- cycle ---
    def cycle(self, st):
        c, ins, s = st["cycle"], st["instr"], st["state"]
        comps, wires = st["active"]["components"], st["active"]["wires"]
        for cell in self.blue_cells:
            cell.recolor(INK)
        self.blue_cells = []
        clear = [FadeOut(m) for m in self.bars]
        self.dp.reset()
        for k, t in self.dp.tags.items():
            t.become(txt(k, 9, ORANGE).move_to(t))
        hdr = txt(f"사이클 {c} / {len(self.T['steps'])}   ·   {s} {st['state_name']}", 15).move_to([5.2, 3.62, 0])
        anims = clear + [FadeOut(self.hdr), FadeIn(hdr)]
        new_instr = ins["n"] != self.cur_instr
        if new_instr:
            self.cur_instr = ins["n"]
            new_ins = txt(f"I{ins['index']}  {ins['text']}", 15, font=MONO).move_to([5.2, 3.27, 0])
            seq = next(i["states"] for i in self.T["instr_states"] if i["n"] == ins["n"])
            chips = VGroup()
            for k_, name in enumerate(seq):
                box = RoundedRectangle(corner_radius=0.05, width=0.5, height=0.24, stroke_color=INK,
                                       stroke_width=1).set_fill(WHITE, 1)
                chips.add(VGroup(box, txt(name, 11, font=MONO).move_to(box)))
            chips.arrange(RIGHT, buff=0.18).move_to([5.2, 2.93, 0])
            arrows = VGroup(*[txt("→", 10, FAINT).move_to((a.get_right() + b.get_left()) / 2)
                              for a, b in zip(chips[:-1], chips[1:])])
            if c == 1:
                anims += [FadeIn(self.ins_box), FadeIn(new_ins), FadeIn(chips), FadeIn(arrows)]
            else:
                anims += [FadeOut(self.ins), FadeIn(new_ins), FadeOut(self.chips), FadeIn(chips),
                          FadeIn(arrows)]
            self.ins, self.chips, self.chip_arrows_new = new_ins, VGroup(chips, arrows), chips
        self.play(*anims, run_time=self.rt(0.5))
        self.hdr = hdr
        self.bars, self.slot_mobs = VGroup(), []
        # current state chip
        seq_chips = self.chips[0]
        k_now = [i for i, ch in enumerate(seq_chips) if ch[1].text == s][0]
        for i, ch in enumerate(seq_chips):
            ch[0].set_fill(YEL_STRONG if i == k_now else (GREY if i < k_now else WHITE), 0.8 if i == k_now else 1)
        if self.B.phase_hl is not None:
            self.play(FadeOut(self.B.phase_hl), run_time=self.rt(0.15))
            self.B.phase_hl = None

        if new_instr:
            seq = [ch[1].text for ch in seq_chips]
            self.say([f"새 명령어 I{ins['index']}  {ins['text']}  (PC = {hx(ins['pc'])})",
                      f"FSM 경로: {' → '.join(seq)} — {len(seq)}사이클이 걸린다."], wait=1.6)
        else:
            self.say([f"사이클 {c}: I{ins['index']}의 {k_now + 1}번째 사이클 — 상태 {s} {st['state_name']}"], wait=0.8)

        self.predict(c, hint=f"상태 {s} {st['state_name']}: 어떤 부품을 쓰고, 어느 레지스터에 무엇이 저장될까?")

        # control signals
        ctl = dict(st["control"])
        an = []
        for sname in SIG_L + SIG_R:
            val = str(ctl[sname]) + (f" {st['alu_op']}" if sname == "ALUControl" and st["alu_op"] else "")
            if self.ctl[sname].s != val:
                an.append(self.ctl[sname].change(val, BLUE))
                self.blue_cells.append(self.ctl[sname])
            if sname in self.dp.tags:
                tag = self.dp.tags[sname]
                an.append(tag.animate.become(txt(f"{sname}={ctl[sname]}", 9, ORANGE, weight=BOLD).move_to(tag)))
        for n, comp in self.dp.comps.items():
            if n not in comps:
                an.append(comp.animate.style("off"))
        for n, w in self.dp.wires.items():
            if n not in wires:
                an.append(w.animate.style("off"))
        self.play(*an, run_time=self.rt(0.8))
        if c == 1:
            self.say([f"{ASSUME}: ALUControl 3비트 값과 ALU 디코더(ALUOp 00=add, 01=sub, 10=funct)는 H&H 7장 표."],
                     wait=2.2)

        self.propagate(st)
        self.clock_edge(st)
        self.check_board(st)

    # ------------------------------------------------------------ text ---
    def state_text(self, st):
        s, v, b = st["state"], st["values"], st["regs_before"]
        d = {e["comp"]: e["end"] - e["start"] for e in st["timing"]["events"]}
        tag = f"{s} {st['state_name']}"
        if s == "S0":
            return [f"{tag}: 메모리 주소 PC={hx(b['PC'])}에서 명령어를 읽어 IR에 넣는다 (메모리 {d['MEM']}ps).",
                    f"같은 사이클에 ALU가 PC+4 = {hx(v['ALUResult'])} 계산 → PCWrite=1로 PC 갱신 (ALU {d['ALU']}ps)."]
        if s == "S1":
            return [f"{tag}: IR의 rs·rt로 레지스터 읽기 → A={v['RD1']}, B={v['RD2']} (레지스터 파일 {d['RF']}ps).",
                    f"ALU는 미리 분기 목표 PC + imm×4 = {hx(v['SrcA'])} + {v['SrcB']} = {hx(v['ALUResult'])} → ALUOut ({d['ALU']}ps)."]
        if s in ("S2", "S9"):
            what = "주소" if s == "S2" else "덧셈 결과"
            return [f"{tag}: ALU가 {what} 계산: A({v['SrcA']}) + SignImm({v['SrcB']}) = {v['ALUResult']} → ALUOut (ALU {d['ALU']}ps)."]
        if s == "S3":
            return [f"{tag}: IorD=1 → ALUOut의 주소 {v['Adr']}({hx(v['Adr'])})에서 값 {v['ReadData']}을 읽어 Data에 넣는다 (메모리 {d['MEM']}ps)."]
        if s == "S5":
            return [f"{tag}: IorD=1 → 주소 {v['Adr']}({hx(v['Adr'])})에 B={b['B']} 쓰기 (메모리 {d['MEM']}ps).",
                    "실제 저장은 클록 에지(clock edge)에서 일어난다."]
        if s == "S6":
            op = st["alu_op"]
            return [f"{tag}: ALU가 {op} 연산: A({v['SrcA']}) {OPSYM[op]} B({v['SrcB']}) = {v['ALUResult']} → ALUOut (ALU {d['ALU']}ps)."]
        if s == "S8":
            return [f"{tag}: ALU가 비교: A({v['SrcA']}) - B({v['SrcB']}) = {v['ALUResult']} → Zero={st['Zero']} (ALU {d['ALU']}ps).",
                    f"Branch & Zero = {st['PCEn']} → PCEn: PC ← ALUOut({hx(b['ALUOut'])}, S1에서 미리 계산한 분기 목표)."]
        src = "Data" if st["control"]["MemtoReg"] == 1 else "ALUOut"
        return [f"{tag}: {src}의 값 {v['WD3']} → 레지스터 {v['WriteReg']} (RegDst={st['control']['RegDst']}, "
                f"MemtoReg={st['control']['MemtoReg']}, 레지스터 파일 {d['RF_W']}ps).",
                "실제 저장은 클록 에지(clock edge)에서 일어난다."]

    def slot_value(self, st, slot):
        v, b = st["values"], st["regs_before"]
        return {"PC": lambda: hx(b["PC"]), "Adr": lambda: hx(v["Adr"]),
                "ReadData": lambda: (f"0x{v['ReadData'] & 0xFFFFFFFF:08X}" if st["state"] == "S0"
                                     else str(v["ReadData"])),
                "IR": lambda: f"0x{b['IR']}", "Data": lambda: str(b["Data"]), "RD1": lambda: str(v["RD1"]),
                "RD2": lambda: str(v["RD2"]), "SignImm": lambda: str(v["SignImm"]),
                "SrcA": lambda: str(v["SrcA"]), "SrcB": lambda: str(v["SrcB"]),
                "ALUResult": lambda: str(v["ALUResult"]), "Zero": lambda: f"Zero={st['Zero']}",
                "ALUOut": lambda: str(b["ALUOut"]), "WriteReg": lambda: v["WriteReg"],
                "WD3": lambda: str(v["WD3"]), "WriteData": lambda: str(b["B"]),
                "PCNext": lambda: hx(v["PCNext"])}[slot]()

    # -------------------------------------------------------- propagate ---
    def propagate(self, st):
        tm = st["timing"]
        used, period = tm["used"], tm["period"]
        wps, cps = tm["wire_ps"], tm["comp_ps"]
        T = ValueTracker(0)
        WIN = 8

        ovs = []
        for n, t0 in wps.items():
            base = self.dp.wires[n].style("idle")
            ov = base.copy().style("on")
            full = ov.line.copy()
            ov.line.pointwise_become_partial(full, 0, 0)
            ov.tip.set_opacity(0)
            ov.set_z_index(4)

            def upd(m, full=full, t0=t0):
                a = float(np.clip((T.get_value() - t0) / WIN, 0, 1))
                m.line.pointwise_become_partial(full, 0, max(a, 1e-4))
                m.line.set_stroke(opacity=1 if a > 0 else 0)
                m.tip.set_opacity(1 if a >= 1 else 0)
            ov.add_updater(upd)
            ovs.append(ov)

        part_iv = {}
        for n, iv in cps.items():
            part_iv.setdefault("RF" if n == "RF_W" else n, []).extend(iv)

        def comp_upd(m, iv):
            t = T.get_value()
            if t < min(s for s, _ in iv):
                m.style("idle")
            elif any(s <= t <= max(e, s + WIN) for s, e in iv):
                m.style("hot")
            else:
                m.style("on")
        for n, iv in part_iv.items():
            if n in self.dp.comps:
                self.dp.comps[n].add_updater(lambda m, iv=iv: comp_upd(m, iv))

        for slot, wl in SLOT_WIRES.items():
            ws = [w for w in wl if w in wps]
            if not ws:
                continue
            val = self.slot_value(st, slot)
            if val is None:
                continue
            pos, _ = self.dp.slot(slot)
            lab = txt(val, 10, BLUE, font=MONO)
            bg = Rectangle(width=lab.width + 0.08, height=lab.height + 0.06, stroke_width=0).set_fill(WHITE, 0.85)
            g = VGroup(bg, lab).move_to([pos[0], pos[1], 0]).set_z_index(6).set_opacity(0)
            t0 = min(wps[w] for w in ws)
            g.add_updater(lambda m, t0=t0: m.set_opacity(1 if T.get_value() >= t0 + WIN else 0))
            self.slot_mobs.append(g)

        bars = VGroup()
        for e in tm["events"]:
            row = next(i for i, (cn, _) in enumerate(ROWS) if cn == e["comp"])
            y = TL_Y0 - TL_DY * row
            bar = Rectangle(width=0.01, height=TL_DY * 0.72, stroke_width=0).set_fill(ORANGE, 0.9)

            def bupd(m, e=e, y=y):
                t = min(T.get_value(), e["end"])
                w = max(self.px(t) - self.px(e["start"]), 0.001)
                m.stretch_to_fit_width(w).move_to([self.px(e["start"]) + w / 2, y, 0])
                m.set_opacity(0.9 if T.get_value() > e["start"] else 0)
            bar.add_updater(bupd)
            bars.add(bar)
        ub = Rectangle(width=0.01, height=0.15, stroke_width=0).set_fill(YEL_STRONG, 1)
        ub.add_updater(lambda m: m.stretch_to_fit_width(max(self.px(min(T.get_value(), used)) - TL_X0, 0.001))
                       .move_to([TL_X0, self.sum_y, 0], aligned_edge=LEFT))
        wb = Rectangle(width=0.01, height=0.15, stroke_width=0).set_fill(RED, 0.35)

        def wupd(m):
            t = T.get_value()
            w = max(self.px(min(t, period)) - self.px(used), 0.001)
            m.stretch_to_fit_width(w).move_to([self.px(used), self.sum_y, 0], aligned_edge=LEFT)
            m.set_opacity(0.35 if t > used else 0)
        wb.add_updater(wupd)
        cursor = Line([0, TL_Y0 + 0.1, 0], [0, self.sum_y - 0.1, 0], stroke_width=2, color=INK)
        cursor.add_updater(lambda m: m.move_to([self.px(T.get_value()), m.get_y(), 0]))
        clk = txt("", 10, INK, font=MONO)
        clk.add_updater(lambda m: m.become(txt(f"t={int(T.get_value())}ps", 10, INK, font=MONO))
                        .move_to([self.px(T.get_value()), TL_Y0 + 0.36, 0]))
        bars.add(ub, wb, cursor, clk)
        self.add(*ovs, *self.slot_mobs, bars)

        # announce what this state does (cursor stopped), then mark the stage and sweep
        self.say(self.state_text(st), wait=2.0)
        stage = st["timing"]["events"][0]["stage"]
        self.set_phase(STAGES.index(stage))
        self.pause(0.3)
        marks = sorted({0, used, period})
        for a, b in zip(marks[:-1], marks[1:]):
            if a == used:
                self.on_used(st)
            self.play(T.animate.set_value(b), run_time=self.rt((b - a) * SEC_PER_PS), rate_func=linear)
        if used == period:
            self.on_used(st)

        for m in [*ovs, *self.slot_mobs, *bars]:
            m.clear_updaters()
        for n in part_iv:
            if n in self.dp.comps:
                self.dp.comps[n].clear_updaters()
                self.dp.comps[n].style("on")
        for n in wps:
            self.dp.wires[n].style("on")
        self.remove(*ovs, bars, *self.slot_mobs)
        self.bars = VGroup(*bars, *self.slot_mobs)
        self.add(self.bars)
        self.slot_mobs = []

    def on_used(self, st):
        tm = st["timing"]
        l1 = txt(f"필요 {tm['used']}ps", 10, INK, weight=BOLD).move_to([self.px(tm["used"] / 2), self.sum_y, 0])
        if tm["waste"] > 0:
            l2 = txt(f"남는 {tm['waste']}ps", 10, RED, weight=BOLD).move_to(
                [self.px((tm["used"] + tm["period"]) / 2), self.sum_y, 0])
            line = (f"{tm['used']}ps에 이 단계의 일은 끝났지만, 클록은 {tm['period']}ps — "
                    f"남은 {tm['waste']}ps는 쓰지 않는다.")
        else:
            l2 = txt("남는 0ps — 메모리 단계", 10, RED).move_to([self.px(tm["period"]) - 1.2, self.sum_y, 0])
            line = f"메모리 접근은 {tm['period']}ps 클록을 꽉 채운다 (클록 주기를 정한 단계)."
        l1.set_z_index(5); l2.set_z_index(5)
        self.play(FadeIn(l1), FadeIn(l2), run_time=self.rt(0.3))
        self.say([line], wait=1.4)
        self.slot_mobs += [l1, l2]

    # -------------------------------------------------------- clock edge ---
    def clock_edge(self, st):
        p = st["timing"]["period"]
        self.say([f"{p}ps: 클록 에지(clock edge) — 레지스터들이 새 값을 저장하고 다음 사이클로 넘어간다."], wait=1.4)
        an, words, side = [], [], []
        intended = set(st["intended"])
        for n, val in st["changes"]["nonarch"].items():
            txtv = self.na_text(n, val)
            meaningful = n in intended
            an.append(self.na[n].change(txtv, BLUE if meaningful else FAINT))
            if meaningful:
                self.blue_cells.append(self.na[n])
                words.append(f"{n} ← {txtv}")
            else:
                side.append(n)
        for r, val in st["changes"]["regs"].items():
            if r in self.regs:
                an.append(self.regs[r].change(str(val), BLUE))
                self.blue_cells.append(self.regs[r])
            words.append(f"{r} ← {val}")
        for a, val in st["changes"]["mem"].items():
            if a in self.mem:
                an.append(self.mem[a].change(str(val), BLUE))
                self.blue_cells.append(self.mem[a])
            words.append(f"Mem[{a}] ← {val}")
        self.cum_cycles += 1
        self.cum_used += st["timing"]["used"]
        seq = next(i["states"] for i in self.T["instr_states"] if i["n"] == st["instr"]["n"])
        if st["state"] == seq[-1]:
            self.done += 1
        P = self.period
        n1 = txt(f"{self.cum_cycles} 사이클 × {P}ps = {self.cum_cycles * P}ps", 13, font=MONO).move_to([5.2, -2.2, 0])
        cpi = f", CPI {self.cum_cycles / self.done:.2f}" if self.done else ""
        n2 = txt(f"완료한 명령어 {self.done}개{cpi}", 11, FAINT).move_to([5.2, -2.45, 0])
        n3 = txt(f"사이클 안의 남는 시간 합: {self.cum_cycles * P - self.cum_used}ps", 11, RED).move_to([5.2, -2.68, 0])
        an += [self.tot1.animate.become(n1), self.tot2.animate.become(n2), self.tot3.animate.become(n3)]
        self.play(*an, run_time=self.rt(0.7))
        lines = ["클록 에지: " + (", ".join(words) if words else "아키텍처 상태 변화 없음") + "."]
        if side:
            lines.append(f"{', '.join(side)}도 매 사이클 덮어쓰이지만 이 값은 쓰이지 않는다(회색).")
        elif st["state"] == seq[-1]:
            lines.append(f"I{st['instr']['index']} 끝 — {len(seq)}사이클 × {P}ps = {len(seq) * P}ps.")
        self.say(lines, wait=2.2)
        if st["state"] == seq[-1] and side:
            self.say([f"I{st['instr']['index']} 끝 — {len(seq)}사이클 × {P}ps = {len(seq) * P}ps."], wait=1.2)

    # ------------------------------------------------------- check board ---
    def check_board(self, st):
        bad = []
        for s in SIG_L + SIG_R:
            exp = str(st["control"][s]) + (f" {st['alu_op']}" if s == "ALUControl" and st["alu_op"] else "")
            if self.ctl[s].s != exp:
                bad.append(f"control {s}: screen {self.ctl[s].s} trace {exp}")
        for n, cell in self.na.items():
            exp = self.na_text(n, st["nonarch_after"][n])
            if cell.s != exp:
                bad.append(f"{n}: screen {cell.s} trace {exp}")
        for r, cell in self.regs.items():
            if cell.s != str(st["regs_after"][r]):
                bad.append(f"{r}: screen {cell.s} trace {st['regs_after'][r]}")
        for a, cell in self.mem.items():
            if cell.s != str(st["mem_after"].get(a, 0)):
                bad.append(f"Mem[{a}]: screen {cell.s} trace {st['mem_after'].get(a)}")
        if f"{st['state']}{st['state_name']}".replace(" ", "") not in self.hdr.text.replace(" ", ""):
            bad.append("state header")
        if self.ins.text.replace(" ", "") != f"I{st['instr']['index']}{st['instr']['text']}".replace(" ", ""):
            bad.append("instruction header")
        if bad:
            raise RuntimeError(f"check_board cycle {st['cycle']}: " + "; ".join(bad))

    # ------------------------------------------------------------ finale ---
    def finale(self, complete):
        T, P = self.T, self.period
        sc_t = json.loads(SC_TRACE.read_text())
        SP = sc_t["config"]["period_ps"]
        self.play(FadeOut(Group(*self.mobjects)))
        self.clear()
        self.sub, self.B.phase_hl = None, None
        title = txt("multi-cycle vs single-cycle: 명령어별 시간", 30, weight=BOLD).move_to([0, 3.45, 0])
        self.play(FadeIn(title))
        X0 = -3.0
        longest = max(len(i["states"]) for i in T["instr_states"]) * P
        sc = 8.6 / max(longest, SP)
        rows = VGroup()
        by_n = {}
        for s in T["steps"]:
            by_n.setdefault(s["instr"]["n"], []).append(s)
        for r, (n, sts) in enumerate(by_n.items()):
            y = 2.75 - 0.43 * r
            ins = sts[0]["instr"]
            g = VGroup(txt(f"I{ins['index']}  {ins['text']}", 13, font=MONO).move_to([-5.0, y, 0])
                       .align_to([-6.9, 0, 0], LEFT))
            for k, s in enumerate(sts):
                x = X0 + k * P * sc
                u = Rectangle(width=s["timing"]["used"] * sc, height=0.3, stroke_width=0).set_fill(YEL_STRONG, 1)
                u.move_to([x, y, 0], aligned_edge=LEFT)
                w = Rectangle(width=max(s["timing"]["waste"] * sc, 0.001), height=0.3, stroke_width=0)
                w.set_fill(RED, 0.35).move_to([x + s["timing"]["used"] * sc, y, 0], aligned_edge=LEFT)
                f = Rectangle(width=P * sc, height=0.3, stroke_color=INK, stroke_width=0.8).move_to(
                    [x + P * sc / 2, y, 0])
                g.add(u, w, f, txt(s["state"], 10, font=MONO).move_to(f))
            g.add(DashedLine([X0 + SP * sc, y - 0.2, 0], [X0 + SP * sc, y + 0.2, 0], color=BLUE, stroke_width=2))
            rows.add(g)
        key = VGroup(txt(f"칸 하나 = 클록 {P}ps (노랑: 일하는 시간, 분홍: 남는 시간)", 13),
                     txt(f"파란 점선 = single-cycle의 한 명령어 {SP}ps", 13, BLUE)).arrange(RIGHT, buff=0.6)
        key.move_to([0, 2.75 - 0.43 * len(by_n) + 0.05, 0])
        self.play(FadeIn(rows, lag_ratio=0.1, run_time=self.rt(2.5)), FadeIn(key))
        fin = T["final"]
        n, cyc = fin["instructions"], fin["cycles"]
        e1 = txt(f"multi-cycle: {cyc} 사이클 × {P}ps = {cyc * P}ps   (CPI {cyc / n:.2f})", 22, weight=BOLD)
        e2 = txt(f"single-cycle: {sc_t['final']['cycles']} 사이클 × {SP}ps = {sc_t['final']['total_ps']}ps   (CPI 1)",
                 22, BLUE)
        VGroup(e1, e2).arrange(DOWN, buff=0.18).move_to([0, -1.95, 0])
        self.play(FadeIn(e1))
        self.play(FadeIn(e2))
        if complete:
            assert fin["total_ps"] == cyc * P
        faster = cyc * P < sc_t["final"]["total_ps"]
        self.say(["lw·sw는 짧아졌지만, 레지스터 읽기(50ps)·ALU(100ps) 단계도 메모리에 맞춘 클록을 통째로 쓴다.",
                  ("단계 길이가 고르지 않아, 이 지연 값에서는 multi-cycle이 오히려 더 느리다. 다음 편: 단계를 겹치는 pipeline."
                   if not faster else "다음 편: 단계를 겹쳐 실행하는 pipeline.")], wait=4.5)
        self.play(FadeOut(Group(*self.mobjects)))
        self.clear()
