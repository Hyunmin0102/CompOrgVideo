"""Single-cycle MIPS video renderer.  Reads ONLY inorder/single_cycle/out/trace.json.

    # preview of the first N instructions (stage 2)
    SC_STEPS=2 manim -ql --media_dir /tmp/media inorder/single_cycle/render/single_cycle_scene.py SingleCycle
    # full video
    manim --resolution 1920,1080 --frame_rate 30 --media_dir /tmp/media \
          inorder/single_cycle/render/single_cycle_scene.py SingleCycle
    # check only (no frames)
    manim --dry_run inorder/single_cycle/render/single_cycle_scene.py SingleCycle
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from manim import (BOLD, DOWN, LEFT, RIGHT, UP, WHITE, Create, DashedLine, FadeIn, Group,  # noqa: E402
                   FadeOut, Line, Rectangle, RoundedRectangle, ValueTracker, VGroup, linear)

from common.style import (ASSUME, BLUE, FAINT, GREY, INK, MONO, ORANGE, RED, YEL,  # noqa: E402
                          YEL_STRONG, Cell, StyleScene, term, txt)
from inorder.shared.datapath import STAGE_LABEL_X, SLOTS, Datapath  # noqa: E402
from inorder.shared.isa import reg_name  # noqa: E402

TRACE = ROOT / "inorder/single_cycle/out/trace.json"
STAGES = ["IF", "ID", "EX", "MEM", "WB"]
SIGNALS = ["RegWrite", "RegDst", "ALUSrc", "Branch", "MemWrite", "MemtoReg", "ALUControl", "PCSrc"]
OPSYM = {"add": "+", "sub": "-", "and": "&", "or": "|", "slt": "<"}

# value label -> the wire whose arrival makes it visible
SLOT_WIRE = {"PC": "pc_imem", "Instr": "instr_a1", "PCPlus4": "pcplus4_pcmux", "RD1": "rd1_srca",
             "RD2": "rd2_alusrc", "SignImm": "instr_imm", "SrcB": "srcb", "ALUResult": "aluresult_res",
             "Zero": "zero_and", "WriteReg": "writereg", "PCBranch": "pcbranch",
             "ReadData": "readdata_res", "WriteData": "rd2_wd", "Result": "result_wd3"}
SLOT_ALT = {"PCPlus4": "pcplus4_addbr", "ALUResult": "aluresult_addr", "SignImm": "instr_imm",
            "RD2": "rd2_wd", "Instr": "instr_ctrl"}

# timeline rows: (components, label)
ROWS = [(("ADD4", "ADDBR"), term("덧셈기", "adder")),
        (("IMEM",), "명령어 메모리 (IF)"),
        (("RF",), "레지스터 읽기 (ID)"),
        (("ALU",), "ALU (EX)"),
        (("DMEM",), "데이터 메모리 (MEM)"),
        (("RF_W",), "레지스터 쓰기 (WB)")]
TL_X0, TL_X1 = -5.25, 2.95          # 0 ps .. period
TL_Y0, TL_DY = -1.68, 0.165
LBL_X = -6.15


class Board:
    SUB_Y = StyleScene.SUB_Y

    def __init__(self):
        self.phase_labels = VGroup(*[txt(s, 15, FAINT, weight=BOLD).move_to([STAGE_LABEL_X[s], 3.62, 0])
                                     for s in STAGES])
        self.phase_hl = None


def fmt(v):
    return "–" if v is None else str(v)


class SingleCycle(StyleScene):
    def construct(self):
        self.T = json.loads(TRACE.read_text())
        cfg = self.T["config"]
        self.period = cfg["period_ps"]
        n_env = os.environ.get("SC_STEPS")
        steps = self.T["steps"][: int(n_env)] if n_env else self.T["steps"]
        self.B = Board()

        self.intro()
        self.build_board()
        for st in steps:
            self.cycle(st)
        self.finale(len(steps) == len(self.T["steps"]))

    # --------------------------------------------------------------- intro ---
    def intro(self):
        cfg = self.T["config"]
        t1 = txt("Single-cycle MIPS 프로세서", 44, weight=BOLD)
        t2 = txt("명령어 하나 = 클록 사이클(clock cycle) 1개", 28)
        t3 = txt("ETH DDCA · Onur Mutlu  L10–L11  |  Harris & Harris 7장", 20, FAINT)
        g = VGroup(t1, t2, t3).arrange(DOWN, buff=0.35).move_to([0, 0.4, 0])
        self.play(FadeIn(g, shift=UP * 0.2))
        self.pause(1.5)
        self.play(FadeOut(g))

        # program listing
        head = txt("3편 공통 프로그램", 28, weight=BOLD).move_to([0, 3.45, 0])
        rows = VGroup()
        for i, p in enumerate(cfg["program"]):
            r = VGroup(txt(f"I{i + 1}", 15, FAINT, font=MONO),
                       txt(f"0x{p['addr']:02X}", 15, FAINT, font=MONO),
                       txt(p["text"], 16, font=MONO),
                       txt(p["reason"], 13))
            r[0].move_to([-6.55, 0, 0]); r[1].move_to([-5.85, 0, 0])
            r[2].move_to([-5.3, 0, 0], aligned_edge=LEFT); r[3].move_to([-1.6, 0, 0], aligned_edge=LEFT)
            if r[3].width > 8.4:
                r[3].scale_to_fit_width(8.4).move_to([-1.6, 0, 0], aligned_edge=LEFT)
            r.move_to([r.get_x(), 2.85 - 0.5 * i, 0])
            rows.add(r)
        init = ", ".join(f"{k}={v}" for k, v in cfg["init_regs"].items())
        mem = ", ".join(f"Mem[{k}]={v}" for k, v in cfg["init_mem"].items())
        foot = txt(f"초기값: {init}  (나머지 0)   |   {mem}", 15).move_to([0, -2.35, 0])
        self.play(FadeIn(head), FadeIn(rows, lag_ratio=0.08, run_time=self.rt(1.6)), FadeIn(foot))
        self.say(["슬라이드의 MIPS 부분집합(add, sub, and, or, slt, addi, lw, sw, beq)만 쓰는 10줄 프로그램.",
                  "pipeline 편에서 문제가 될 의존(dependency)을 일부러 넣었지만, single-cycle에서는 명령어가 겹치지 않는다."],
                 wait=3.5)
        skipped = [i for i, p in enumerate(cfg["program"])
                   if p["addr"] not in {s["pc"] for s in self.T["steps"]}]
        for i in skipped:
            self.play(rows[i].animate.set_opacity(0.35), run_time=self.rt(0.4))
        self.say([f"beq가 taken이라 I{skipped[0] + 1}은 실행되지 않는다 → 실제 실행 명령어 {len(self.T['steps'])}개."],
                 wait=2.0)
        self.play(FadeOut(VGroup(head, rows, foot)), FadeOut(self.sub))
        self.sub = None

    # --------------------------------------------------------------- board ---
    def build_board(self):
        cfg = self.T["config"]
        self.dp = Datapath()
        self.dp.reset()
        self.tag_vals = {}
        for k, t in self.dp.tags.items():
            t.become(txt(f"{t.text if hasattr(t, 'text') else k}", 9, ORANGE).move_to(t))

        # right panel: header, control, registers, memory, total time
        X0 = 3.45
        self.hdr_cycle = txt("사이클 – / –", 15).move_to([5.2, 3.62, 0])
        self.hdr_instr_box = RoundedRectangle(corner_radius=0.06, width=3.55, height=0.36, stroke_width=0)
        self.hdr_instr_box.set_fill(YEL, 1).move_to([5.2, 3.25, 0])
        self.hdr_instr = txt("", 16, font=MONO).move_to([5.2, 3.25, 0])

        ctl_t = txt(term("제어 신호", "control"), 14, weight=BOLD).move_to([5.2, 2.92, 0])
        self.ctl = {}
        cg = VGroup(ctl_t)
        for i, s in enumerate(SIGNALS):
            y = 2.68 - 0.215 * i
            a = Cell(4.32, y, 1.74, 0.215, s, size=12, font=MONO)
            b = Cell(6.05, y, 1.72, 0.215, "", size=12, font=MONO)
            self.ctl[s] = b
            cg.add(a.mobs(), b.mobs())

        reg_t = txt(term("레지스터", "register file"), 14, weight=BOLD).move_to([5.2, 0.86, 0])
        self.regs = {}
        rg = VGroup(reg_t)
        init = self.T["steps"][0]["regs_after"]  # placeholder; real initial values below
        for i, n in enumerate(cfg["show_regs"]):
            col, row = divmod(i, 6)
            y = 0.62 - 0.21 * row
            xn, xv = (3.73, 4.58) if col == 0 else (5.48, 6.33)
            a = Cell(xn, y, 0.56, 0.21, n, size=12, font=MONO)
            v = cfg["init_regs"].get(n, 0)
            b = Cell(xv, y, 1.14, 0.21, str(v), size=12, font=MONO)
            self.regs[n] = b
            rg.add(a.mobs(), b.mobs())
        del init

        mem_t = txt(term("데이터 메모리", "data memory"), 14, weight=BOLD).move_to([5.2, -0.72, 0])
        self.mem = {}
        mg = VGroup(mem_t)
        for i, a_ in enumerate(cfg["show_mem"]):
            y = -0.96 - 0.21 * i
            a = Cell(4.32, y, 1.74, 0.21, f"Mem[{a_}]", size=12, font=MONO)
            b = Cell(6.05, y, 1.72, 0.21, str(cfg["init_mem"].get(a_, 0)), size=12, font=MONO)
            self.mem[a_] = b
            mg.add(a.mobs(), b.mobs())

        # total time box
        self.tot_t = txt(term("누적 실행 시간", "execution time"), 14, weight=BOLD).move_to([5.2, -1.75, 0])
        self.tot1 = txt("0 × 0ps", 14, font=MONO).move_to([5.2, -2.05, 0]).set_opacity(0)
        self.tot2 = txt("–", 12, FAINT).move_to([5.2, -2.35, 0]).set_opacity(0)
        self.tot2b = txt("–", 12, RED).move_to([5.2, -2.6, 0]).set_opacity(0)

        # timeline
        tl = VGroup()
        ax = Line([TL_X0, TL_Y0 + 0.1, 0], [TL_X1, TL_Y0 + 0.1, 0], stroke_width=1.2, color=INK)
        tl.add(ax)
        for ps in range(0, self.period + 1, 100):
            x = self.px(ps)
            tl.add(Line([x, TL_Y0 + 0.07, 0], [x, TL_Y0 + 0.13, 0], stroke_width=1, color=INK),
                   txt(f"{ps}", 9, INK, font=MONO).move_to([x, TL_Y0 + 0.21, 0]))
            tl.add(DashedLine([x, TL_Y0 + 0.07, 0], [x, TL_Y0 - TL_DY * 6.6, 0], stroke_width=0.6,
                              color=FAINT, dash_length=0.04))
        tl.add(txt("ps", 9, INK, font=MONO).move_to([TL_X1 + 0.22, TL_Y0 + 0.21, 0]))
        for i, (_, lbl) in enumerate(ROWS):
            tl.add(txt(lbl, 10).move_to([LBL_X, TL_Y0 - TL_DY * i, 0]))
        self.sum_y = TL_Y0 - TL_DY * 6 - 0.03
        tl.add(txt("이 명령어 / 클록", 10, weight=BOLD).move_to([LBL_X, self.sum_y, 0]))
        clk = Line([self.px(self.period), TL_Y0 + 0.1, 0], [self.px(self.period), self.sum_y - 0.1, 0],
                   stroke_width=2.2, color=RED)
        tl.add(clk)
        self.tl = tl

        self.add_to_back()
        self.play(FadeIn(self.dp, run_time=self.rt(1.2)))
        self.play(FadeIn(self.B.phase_labels), FadeIn(ctl_t), FadeIn(cg), FadeIn(rg), FadeIn(mg),
                  FadeIn(self.hdr_cycle), FadeIn(self.tot_t), run_time=self.rt(0.8))
        self.say(["H&H single-cycle 데이터패스(L11 55)를 단순화한 그림. 오른쪽은 제어 신호와 레지스터·메모리.",
                  "IF·ID·EX·MEM·WB는 L10 88의 처리 단계: 한 클록 안에서 차례로 일어난다."], wait=3.0)
        self.say([f"{ASSUME}: j 경로는 그리지 않음. 제어선은 Branch→AND만 그리고, 나머지는 부품 옆 주황 라벨로 표시."],
                 wait=2.5)
        d = cfg["delays_ps"]
        self.play(FadeIn(tl, run_time=self.rt(0.8)))
        self.say([f"지연(L10 90): 메모리 {d['mem']}ps, ALU·덧셈기 {d['alu']}ps, 레지스터 파일 {d['rf']}ps, 나머지 {d['other']}ps.",
                  f"클록 주기(clock period)는 가장 느린 명령어 lw에 맞춰 {self.period}ps — 모든 명령어가 이 시간을 쓴다."],
                 wait=3.5)
        self.cum_cycles, self.cum_need = 0, 0
        self.bars = VGroup()
        self.blue_cells = []

    def add_to_back(self):
        pass

    def px(self, ps):
        return TL_X0 + (TL_X1 - TL_X0) * ps / self.period

    # --------------------------------------------------------------- cycle ---
    def cycle(self, st):
        c, tm = st["cycle"], st["timing"]
        comps, wires = st["active"]["components"], st["active"]["wires"]

        # 1. reset previous cycle: blue -> ink, datapath back to neutral
        for cell in self.blue_cells:
            cell.recolor(INK)
        self.blue_cells = []
        clear = [FadeOut(m) for m in self.bars] + [FadeOut(m) for m in getattr(self, "slot_mobs", [])]
        self.dp.reset()
        for k, t in self.dp.tags.items():
            t.become(txt(k, 9, ORANGE).move_to(t))
        hdr = txt(f"사이클 {c} / {len(self.T['steps'])}   ·   PC = 0x{st['pc']:02X}", 15).move_to([5.2, 3.62, 0])
        ins = txt(f"I{st['index']}  {st['text']}", 15, font=MONO).move_to([5.2, 3.25, 0])
        anims = clear + [self.hdr_cycle.animate.become(hdr)]
        if c == 1:
            anims += [FadeIn(self.hdr_instr_box), FadeIn(ins)]
        else:
            anims += [FadeOut(self.hdr_instr), FadeIn(ins)]
        self.play(*anims, run_time=self.rt(0.5))
        self.hdr_instr = ins
        self.bars = VGroup()
        self.slot_mobs = []
        if self.B.phase_hl is not None:
            self.play(FadeOut(self.B.phase_hl), run_time=self.rt(0.15))
            self.B.phase_hl = None

        self.say([f"사이클 {c}: I{st['index']}  {st['text']}  (PC = 0x{st['pc']:02X})"], wait=0.8)

        # 2. prediction pause
        self.predict(c, hint=f"I{st['index']} {st['text'].split()[0]}: 어떤 부품을 쓰고, 제어 신호는 몇일까?")

        # 3. control signals
        ctl = dict(st["control"], PCSrc=st["PCSrc"])
        an = []
        for s in SIGNALS:
            v = ctl[s]
            val = f"{v} ({st['alu_op']})" if s == "ALUControl" else str(v)
            if self.ctl[s].s != val:
                an.append(self.ctl[s].change(val, BLUE))
                self.blue_cells.append(self.ctl[s])
            tag = self.dp.tags[s]
            an.append(tag.animate.become(txt(f"{s}={ctl[s]}", 9, ORANGE, weight=BOLD).move_to(tag)))
        # unused parts grey right away, used ones stay neutral until the signal arrives
        for n, comp in self.dp.comps.items():
            if n not in comps:
                an.append(comp.animate.style("off"))
        for n, w in self.dp.wires.items():
            if n not in wires:
                an.append(w.animate.style("off"))
        self.play(*an, run_time=self.rt(0.8))
        self.say(self.describe_control(st), wait=2.2)
        if c == 1:
            self.say([f"{ASSUME}: ALUControl 3비트 값은 H&H 7장 인코딩. 슬라이드(L10 56–61)에는 연산 이름(funct/Add/bcond)만 있다."],
                     wait=2.2)

        # 4. signal propagation, ps by ps
        self.propagate(st)

        # 5. clock edge: state update
        self.clock_edge(st)
        self.check_board(st)

    def describe_control(self, st):
        k, cl = st["class"], st["control"]
        unused = [n for n in ("DMEM", "SIGNEXT", "ADDBR") if n not in st["active"]["components"]]
        names = {"DMEM": "데이터 메모리", "SIGNEXT": "부호 확장", "ADDBR": "분기 덧셈기"}
        un = ", ".join(names[n] for n in unused)
        if k == "LW":
            l1 = f"lw: RegWrite=1, ALUSrc=1(즉치값을 ALU로), MemtoReg=1(메모리 값을 레지스터로), RegDst=0(rt에 씀)."
        elif k == "SW":
            l1 = "sw: MemWrite=1, ALUSrc=1, RegWrite=0 — 레지스터에 쓰지 않으니 RegDst·MemtoReg는 X(don't care)."
        elif k == "BEQ":
            l1 = "beq: Branch=1, ALUSrc=0, ALU는 뺄셈 — RegWrite=0이라 RegDst·MemtoReg는 X(don't care)."
        elif k == "I":
            l1 = "addi(I-type): RegWrite=1, ALUSrc=1(즉치값), RegDst=0(rt에 씀), MemtoReg=0."
        else:
            l1 = f"{st['mnemonic']}(R-type): RegWrite=1, RegDst=1(rd에 씀), ALUSrc=0(두 번째 레지스터), MemtoReg=0."
        return [l1, f"이 명령어가 쓰지 않는 부품은 회색: {un}." if un else "이 명령어는 분기 경로까지 사용한다."]

    # ----------------------------------------------------------- propagate ---
    def propagate(self, st):
        tm = st["timing"]
        lat, period = tm["latency"], tm["period"]
        wps, cps = tm["wire_ps"], tm["comp_ps"]
        T = ValueTracker(0)
        WIN = 18  # ps used to draw a wire / flash a zero-delay part

        # wire overlays
        ovs = []
        for n, t0 in wps.items():
            base = self.dp.wires[n]
            base.style("idle")
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

        # components
        def comp_upd(m, iv):
            t = T.get_value()
            if t < iv[0][0]:
                m.style("idle")
            elif any(s <= t <= max(e, s + WIN) for s, e in iv):
                m.style("hot")
            else:
                m.style("on")
        for n, iv in cps.items():
            self.dp.comps[n].add_updater(lambda m, iv=iv: comp_upd(m, iv))

        # value labels on wires
        for slot, wn in SLOT_WIRE.items():
            v = self.slot_value(st, slot)
            wire = wn if wn in wps else SLOT_ALT.get(slot)
            if v is None or wire not in wps:
                continue
            pos, d = SLOTS[slot]
            lab = txt(v, 10, BLUE, font=MONO)
            bg = Rectangle(width=lab.width + 0.08, height=lab.height + 0.06, stroke_width=0).set_fill(WHITE, 0.85)
            g = VGroup(bg, lab).move_to([pos[0], pos[1], 0]).set_z_index(6)
            g.set_opacity(0)
            g.add_updater(lambda m, t0=wps[wire]: m.set_opacity(1 if T.get_value() >= t0 + WIN else 0))
            self.slot_mobs.append(g)

        # timeline bars
        bars = VGroup()
        for e in tm["events"]:
            row = next(i for i, (cs, _) in enumerate(ROWS) if e["comp"] in cs)
            y = TL_Y0 - TL_DY * row
            bar = Rectangle(width=0.01, height=TL_DY * 0.72, stroke_width=0).set_fill(ORANGE, 0.9)

            def bupd(m, e=e, y=y):
                t = min(T.get_value(), e["end"])
                w = max(self.px(t) - self.px(e["start"]), 0.001)
                m.stretch_to_fit_width(w).move_to([self.px(e["start"]) + w / 2, y, 0])
                m.set_opacity(0.9 if T.get_value() > e["start"] else 0)
            bar.add_updater(bupd)
            bars.add(bar)
        used = Rectangle(width=0.01, height=0.15, stroke_width=0).set_fill(YEL_STRONG, 1)
        used.add_updater(lambda m: m.stretch_to_fit_width(max(self.px(min(T.get_value(), lat)) - TL_X0, 0.001))
                         .move_to([TL_X0, self.sum_y, 0], aligned_edge=LEFT))
        waste = Rectangle(width=0.01, height=0.15, stroke_width=0).set_fill(RED, 0.35)

        def wupd(m):
            t = T.get_value()
            w = max(self.px(min(t, period)) - self.px(lat), 0.001)
            m.stretch_to_fit_width(w).move_to([self.px(lat), self.sum_y, 0], aligned_edge=LEFT)
            m.set_opacity(0.35 if t > lat else 0)
        waste.add_updater(wupd)
        cursor = Line([0, TL_Y0 + 0.1, 0], [0, self.sum_y - 0.1, 0], stroke_width=2, color=INK)
        cursor.add_updater(lambda m: m.move_to([self.px(T.get_value()), m.get_y(), 0]))
        clock_lbl = txt("", 10, INK, font=MONO)
        clock_lbl.add_updater(lambda m: m.become(txt(f"t={int(T.get_value())}ps", 10, INK, font=MONO))
                              .move_to([self.px(T.get_value()), TL_Y0 + 0.36, 0]))
        bars.add(used, waste, cursor, clock_lbl)
        self.add(*ovs, *self.slot_mobs, bars)

        # sweep in segments; highlight the stage when its first event starts
        first = self.stage_starts(st)
        stage_at = {}
        for sname in STAGES:
            if sname in first:
                stage_at.setdefault(first[sname], sname)
        marks = sorted(set([0, lat, period] + list(stage_at)))
        SEC_PER_PS = 0.017          # 600 ps ~ 10 s
        for a, b in zip(marks[:-1], marks[1:]):
            if a in stage_at:
                # announce the stage first (cursor stopped), then switch the phase marker
                self.say(self.stage_text(st, stage_at[a]), wait=1.8)
                self.set_phase(STAGES.index(stage_at[a]))
                self.pause(0.4)
            if a == lat:
                self.on_latency(st)
            self.play(T.animate.set_value(b), run_time=self.rt((b - a) * SEC_PER_PS), rate_func=linear)
        if lat == period:           # slowest instruction: no waste
            self.on_latency(st)

        # freeze: remove updaters, leave final look
        for m in [*ovs, *self.slot_mobs, *bars]:
            m.clear_updaters()
        for n in cps:
            self.dp.comps[n].clear_updaters()
            self.dp.comps[n].style("on")
        for n in wps:
            self.dp.wires[n].style("on")
        self.remove(*ovs)
        self.bars = VGroup(*bars, *self.slot_mobs)
        self.remove(bars, *self.slot_mobs)
        self.add(self.bars)
        self.slot_mobs = []

    def on_latency(self, st):
        tm = st["timing"]
        lbl1 = txt(f"필요 {tm['latency']}ps", 10, INK, weight=BOLD).move_to(
            [self.px(tm["latency"] / 2), self.sum_y, 0])
        lbl2 = txt(f"낭비 {tm['waste']}ps", 10, RED, weight=BOLD).move_to(
            [self.px((tm["latency"] + tm["period"]) / 2), self.sum_y, 0]).set_z_index(5)
        if tm["waste"] == 0:
            lbl2 = txt("낭비 0ps — 가장 느린 명령어", 10, RED).move_to([self.px(tm["period"]) - 1.2, self.sum_y + 0.0, 0])
        lbl1.set_z_index(5)
        self.play(FadeIn(lbl1), run_time=self.rt(0.3))
        self.bars_extra = [lbl1, lbl2]
        lines = [f"{tm['latency']}ps에 이 명령어의 일은 끝났다 ({self.lat_note(st)})."]
        if tm["waste"] > 0:
            lines.append(f"하지만 클록은 {tm['period']}ps — 남은 {tm['waste']}ps 동안 아무것도 하지 않는다(낭비).")
        else:
            lines.append(f"lw는 IF→ID→EX→MEM→WB 모두 써서 클록 {tm['period']}ps를 꽉 채운다.")
        self.say(lines, wait=1.6)
        self.add(lbl2)
        self.slot_mobs += [lbl1, lbl2]

    def lat_note(self, st):
        ev = st["timing"]["events"]
        names = {"IMEM": "명령어 메모리", "RF": "레지스터 읽기", "ALU": "ALU", "DMEM": "데이터 메모리",
                 "RF_W": "레지스터 쓰기", "ADD4": "PC+4", "ADDBR": "분기 덧셈기"}
        path = [e for e in ev if e["comp"] not in ("ADD4", "ADDBR")]
        return " + ".join(f"{names[e['comp']]} {e['end'] - e['start']}" for e in path)

    def slot_value(self, st, slot):
        v = st["values"]
        if slot == "PC":
            return f"0x{st['pc']:02X}"
        if slot == "Instr":
            return f"0x{st['word']}"
        if slot == "Zero":
            return f"Zero={st['Zero']}"
        if slot in ("PCPlus4", "PCBranch"):
            return f"0x{v[slot]:02X}"
        if slot == "SignImm":
            return str(v["SignImm"])
        if slot == "WriteReg":
            return v["WriteReg"]
        x = v.get(slot)
        return None if x is None else str(x)

    # ---------------------------------------------------------- clock edge ---
    @staticmethod
    def stage_starts(st):
        """Stage start = start of its main unit (adders run alongside, not as stage markers)."""
        out = {}
        for e in st["timing"]["events"]:
            if e["comp"] not in ("ADD4", "ADDBR") or e["stage"] == "IF":
                out[e["stage"]] = min(out.get(e["stage"], e["start"]), e["start"])
        return out

    def stage_text(self, st, stage):
        v, f, k = st["values"], st["fields"], st["class"]
        dur = {e["comp"]: e["end"] - e["start"] for e in st["timing"]["events"]}
        start = self.stage_starts(st)[stage]
        rs, rt = reg_name(f["rs"]), reg_name(f["rt"])
        head = f"{start}ps → {stage}: "
        if stage == "IF":
            return [head + f"명령어 메모리(instruction memory)에서 주소 0x{st['pc']:02X}의 명령어를 읽는다 ({dur['IMEM']}ps).",
                    f"동시에 PC+4 덧셈기(adder)가 다음 PC 0x{v['PCPlus4']:02X} 계산 ({dur['ADD4']}ps)."]
        if stage == "ID":
            regs = f"{rs}={v['RD1']}" + (f", {rt}={v['RD2']}" if k in ("R", "SW", "BEQ") else "")
            l2 = "제어 유닛(control unit)은 opcode를 보고 제어 신호를 낸다 (0ps)."
            if k in ("I", "LW", "SW", "BEQ"):
                l2 = f"부호 확장(sign extend): 즉치값 {v['SignImm']}. " + l2
            return [head + f"레지스터 파일(register file) 읽기: {regs} ({dur['RF']}ps).", l2]
        if stage == "EX":
            if k in ("LW", "SW"):
                l1 = f"ALU가 주소를 계산한다: {v['SrcA']} + {v['SignImm']} = {v['ALUResult']} ({dur['ALU']}ps)."
            elif k == "BEQ":
                l1 = f"ALU가 비교한다: {v['SrcA']} - {v['SrcB']} = {v['ALUResult']} → Zero={st['Zero']} ({dur['ALU']}ps)."
            else:
                l1 = f"ALU가 {st['alu_op']} 연산: {v['SrcA']} {OPSYM[st['alu_op']]} {v['SrcB']} = {v['ALUResult']} ({dur['ALU']}ps)."
            br = next((e for e in st["timing"]["events"] if e["comp"] == "ADDBR"), None)
            l2 = (f"분기 덧셈기(200ps 시작 → {br['end']}ps): PC+4 + 즉치값×4 = 0x{v['PCBranch']:02X}."
                  .replace("200ps", f"{br['start']}ps")
                  if k == "BEQ" else "")
            return [head + l1] + ([l2] if l2 else [])
        if stage == "MEM":
            if k == "LW":
                return [head + f"데이터 메모리(data memory) 주소 {v['ALUResult']} 읽기 → 값 {v['ReadData']} ({dur['DMEM']}ps)."]
            return [head + f"데이터 메모리(data memory) 주소 {v['ALUResult']}에 값 {v['WriteData']} 쓰기 준비 ({dur['DMEM']}ps).",
                    "실제 저장은 클록 에지(clock edge)에서 일어난다."]
        return [head + f"결과 값 {v['Result']} → 레지스터 파일의 {v['WriteReg']} 쓰기 입력에 도착 ({dur['RF_W']}ps).",
                "실제 저장은 클록 에지(clock edge)에서 일어난다."]

    def clock_edge(self, st):
        p = st["timing"]["period"]
        self.say([f"{p}ps: 클록 주기 끝 — 다음 클록 에지(clock edge)에서 상태가 바뀌고 다음 사이클이 시작된다."],
                 wait=1.6)
        an, words = [], []
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
        self.cum_need += st["timing"]["latency"]
        p = self.period
        new1 = txt(f"{self.cum_cycles} × {p}ps = {self.cum_cycles * p}ps", 14, font=MONO).move_to([5.2, -2.05, 0])
        new2 = txt(f"실제로 필요했던 시간 합: {self.cum_need}ps", 12, FAINT).move_to([5.2, -2.35, 0])
        new2b = txt(f"낭비 합: {self.cum_cycles * p - self.cum_need}ps", 12, RED).move_to([5.2, -2.6, 0])
        an += [self.tot1.animate.become(new1), self.tot2.animate.become(new2), self.tot2b.animate.become(new2b)]
        self.play(*an, run_time=self.rt(0.7))
        nxt = st["values"]["PCNext"]
        if st["class"] == "BEQ":
            line2 = (f"Zero={st['Zero']} & Branch=1 → PCSrc={st['PCSrc']}: 다음 PC = 0x{nxt:02X}"
                     + (" (분기 목표, 바로 다음 명령어를 건너뜀)." if st["PCSrc"] else "."))
        else:
            line2 = f"PC ← 0x{nxt:02X} (PC+4). 다음 클록에 다음 명령어."
        line1 = self.describe_values(st) + ("  클록 에지(clock edge)에서 " + ", ".join(words) + "."
                                            if words else "")
        self.say([line1, line2], wait=2.6)
        if st["class"] == "BEQ":
            self.say([f"{ASSUME}: 분기 목표 덧셈기는 부호 확장 값이 나온 200ps에 시작한다고 계산 (L10 95 그림은 200ps 표시).",
                      "beq 전체 지연에는 영향 없음."], wait=2.2)

    def describe_values(self, st):
        v, f, k = st["values"], st["fields"], st["class"]
        rs, rt = reg_name(f["rs"]), reg_name(f["rt"])
        if k == "LW":
            return f"주소 = {rs}({v['SrcA']}) + {v['SignImm']} = {v['ALUResult']} → 메모리에서 {v['ReadData']} 읽음."
        if k == "SW":
            return f"주소 = {rs}({v['SrcA']}) + {v['SignImm']} = {v['ALUResult']}, 쓸 값 {rt}={v['WriteData']}."
        if k == "BEQ":
            return f"ALU: {rs}({v['SrcA']}) - {rt}({v['SrcB']}) = {v['ALUResult']}."
        if k == "I":
            return f"ALU: {rs}({v['SrcA']}) + {v['SignImm']} = {v['ALUResult']}."
        return f"ALU: {rs}({v['SrcA']}) {OPSYM[st['alu_op']]} {rt}({v['SrcB']}) = {v['ALUResult']}."

    # --------------------------------------------------------- check board ---
    def check_board(self, st):
        bad = []
        ctl = dict(st["control"], PCSrc=st["PCSrc"])
        for s in SIGNALS:
            exp = f"{ctl[s]} ({st['alu_op']})" if s == "ALUControl" else str(ctl[s])
            if self.ctl[s].s != exp:
                bad.append(f"control {s}: screen {self.ctl[s].s} trace {exp}")
        for r, cell in self.regs.items():
            if cell.s != str(st["regs_after"][r]):
                bad.append(f"{r}: screen {cell.s} trace {st['regs_after'][r]}")
        for a, cell in self.mem.items():
            if cell.s != str(st["mem_after"].get(a, 0)):
                bad.append(f"Mem[{a}]: screen {cell.s} trace {st['mem_after'].get(a)}")
        if self.hdr_instr.text.replace(" ", "") != f"I{st['index']}{st['text']}".replace(" ", ""):
            bad.append("instruction header")
        if bad:
            raise RuntimeError(f"check_board cycle {st['cycle']}: " + "; ".join(bad))

    # -------------------------------------------------------------- finale ---
    def finale(self, complete):
        steps = self.T["steps"]
        fin = self.T["final"]
        p = self.period
        self.play(FadeOut(Group(*self.mobjects)))
        self.clear()
        self.sub = None
        self.B.phase_hl = None
        title = txt("single-cycle의 총 실행 시간", 32, weight=BOLD).move_to([0, 3.4, 0])
        self.play(FadeIn(title))
        X0, X1 = -3.2, 5.2
        sc = (X1 - X0) / p
        rows = VGroup()
        for i, s in enumerate(steps):
            y = 2.65 - 0.42 * i
            lat = s["timing"]["latency"]
            lab = txt(f"I{s['index']}  {s['text']}", 14, font=MONO).move_to([-5.0, y, 0])
            lab.align_to([-6.7, 0, 0], LEFT)
            u = Rectangle(width=lat * sc, height=0.3, stroke_width=0).set_fill(YEL_STRONG, 1)
            u.move_to([X0, y, 0], aligned_edge=LEFT)
            w = Rectangle(width=max((p - lat) * sc, 0.001), height=0.3, stroke_width=0).set_fill(RED, 0.35)
            w.move_to([X0 + lat * sc, y, 0], aligned_edge=LEFT)
            t = txt(f"{lat}", 11, font=MONO).move_to(u)
            rows.add(VGroup(lab, u, w, t))
        frame = Rectangle(width=p * sc, height=0.42 * len(steps), stroke_color=INK, stroke_width=1)
        frame.move_to([X0 + p * sc / 2, 2.65 - 0.42 * (len(steps) - 1) / 2, 0])
        self.play(FadeIn(rows, lag_ratio=0.1, run_time=self.rt(2.0)), Create(frame))
        need = sum(s["timing"]["latency"] for s in steps)
        n = len(steps)
        total = n * p
        eq = txt(f"총 실행 시간 = {n} 명령어 × 1 사이클 × {p}ps = {total}ps", 26, weight=BOLD)
        eq.move_to([0, -1.75, 0])
        note = txt(f"각 명령어가 필요한 만큼만 썼다면 {need}ps — {total - need}ps({100 * (total - need) / total:.0f}%)는 낭비",
                   20, RED).move_to([0, -2.35, 0])
        self.play(FadeIn(eq))
        self.play(FadeIn(note))
        if complete:
            assert fin["cycles"] == n and fin["total_ps"] == total
        self.say(["CPI=1이지만 클록 주기가 가장 느린 lw(600ps)에 묶여, 빠른 명령어도 600ps를 다 쓴다.",
                  "다음 편 multi-cycle: 명령어마다 필요한 단계 수만큼만 짧은 클록을 쓴다."], wait=4.0)
        self.play(FadeOut(Group(*self.mobjects)))
        self.clear()
