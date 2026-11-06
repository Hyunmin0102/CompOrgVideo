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

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from manim import (BOLD, DOWN, LEFT, RIGHT, UP, WHITE, Create, DashedLine, FadeIn, Group,  # noqa: E402
                   FadeOut, GrowFromEdge, LaggedStart, Line, Rectangle, RoundedRectangle, VGroup, linear)

from common.style import (ASSUME, BLUE, FAINT, GREY, INK, MONO, ORANGE, RED, YEL,  # noqa: E402
                          YEL_STRONG, Cell, StyleScene, term, txt)
from inorder.shared.datapath import STAGE_LABEL_X, Datapath  # noqa: E402
from inorder.shared.isa import reg_name  # noqa: E402

TRACE = ROOT / "inorder/single_cycle/out/trace.json"
STAGES = ["IF", "ID", "EX", "MEM", "WB"]
SIGNALS = ["RegWrite", "RegDst", "ALUSrc", "Branch", "MemWrite", "MemtoReg", "ALUControl", "PCSrc"]
OPSYM = {"add": "+", "sub": "-", "and": "&", "or": "|", "slt": "<"}

# value label -> wires (the first one drawn makes it visible)
SLOT_WIRES = {"PC": ["pc_imem"], "Instr": ["instr_a1", "instr_ctrl"], "PCPlus4": ["pc_add4"],
              "RD1": ["rd1_srca"], "RD2": ["rd2_alusrc", "rd2_wd"], "SignImm": ["signimm_alusrc", "signimm_sl2"],
              "SrcB": ["srcb"], "ALUResult": ["aluresult_res", "aluresult_addr", "zero_and"],
              "Zero": ["zero_and"], "WriteReg": ["writereg"], "PCBranch": ["sl2_addbr"],
              "ReadData": ["readdata_res"], "WriteData": ["rd2_wd"], "Result": ["result_wd3"]}
SEC_PER_PS_UNIT = 0.012     # how long a timed unit is shown working (200 ps -> 2.4 s)

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
        self.wsrc = {w: v[0] for w, v in cfg["wire_ends"].items()}
        self.wdst = {w: v[1] for w, v in cfg["wire_ends"].items()}
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
        self.hdr_cycle = txt("사이클 – / –", 15).move_to([4.45, 3.62, 0])
        pc_name = Cell(5.75, 3.62, 0.5, 0.26, "PC", size=12, font=MONO)
        self.pc_cell = Cell(6.45, 3.62, 0.9, 0.26, f"0x{self.T['steps'][0]['pc']:02X}", size=12, font=MONO)
        self.pc_g = VGroup(pc_name.mobs(), self.pc_cell.mobs())
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
                  FadeIn(self.hdr_cycle), FadeIn(self.pc_g), FadeIn(self.tot_t), run_time=self.rt(0.8))
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
        self.cstyle = {n: "idle" for n in self.dp.comps}
        self.wstyle = {n: "idle" for n in self.dp.wires}
        self.shown_slots, self.job_ovs, self.cur_stage = set(), [], None
        for t in self.dp.tags.values():
            t._shown = None

    def add_to_back(self):
        pass

    def px(self, ps):
        return TL_X0 + (TL_X1 - TL_X0) * ps / self.period

    # --------------------------------------------------------------- cycle ---
    def cycle(self, st):
        c = st["cycle"]
        comps, wires = set(st["active"]["components"]), set(st["active"]["wires"])
        for cell in self.blue_cells:
            cell.recolor(INK)
        self.blue_cells = []

        # (C) header and only what changes — no reset of the drawing
        hdr = txt(f"사이클 {c} / {len(self.T['steps'])}", 15).move_to([4.45, 3.62, 0])
        ins = txt(f"I{st['index']}  {st['text']}", 15, font=MONO).move_to([5.2, 3.25, 0])
        anims = [FadeOut(m) for m in self.bars] + [FadeOut(self.hdr_cycle), FadeIn(hdr)]
        if c == 1:
            anims += [FadeIn(self.hdr_instr_box), FadeIn(ins)]
        else:
            anims += [FadeOut(self.hdr_instr), FadeIn(ins)]
        if self.B.phase_hl is not None:
            anims.append(FadeOut(self.B.phase_hl))
            self.B.phase_hl = None
        self.play(*anims, run_time=self.rt(0.5))
        self.hdr_cycle, self.hdr_instr = hdr, ins
        self.bars = VGroup()
        self.say([f"사이클 {c}: I{st['index']}  {st['text']}  (PC = 0x{st['pc']:02X})"], wait=0.8)

        self.predict(c, hint=f"I{st['index']} {st['text'].split()[0]}: 어떤 부품을 쓰고, 제어 신호는 몇일까?")

        an = []
        for n, comp in self.dp.comps.items():
            want = "idle" if n in comps else "off"
            if self.cstyle.get(n) != want:
                an.append(comp.animate.style(want))
                self.cstyle[n] = want
        for n, w in self.dp.wires.items():
            want = "idle" if n in wires else "off"
            if self.wstyle.get(n) != want:
                an.append(w.animate.style(want))
                self.wstyle[n] = want
        if an:
            self.play(*an, run_time=self.rt(0.6))

        # (C) control: changed signals one after another; X faint
        ctl = dict(st["control"], PCSrc=st["PCSrc"])
        changed, tags = [], []
        for s in SIGNALS:
            v = ctl[s]
            val = f"{v} ({st['alu_op']})" if s == "ALUControl" else str(v)
            if self.ctl[s].s != val:
                changed.append(self.ctl[s].change(val, FAINT if v == "X" else BLUE))
                if v != "X":
                    self.blue_cells.append(self.ctl[s])
            tag = self.dp.tags[s]
            new_t = f"{s}={v}"
            if getattr(tag, "_shown", None) != new_t:
                tags.append(tag.animate.become(txt(new_t, 9, FAINT if v == "X" else ORANGE,
                                                   weight="NORMAL" if v == "X" else BOLD).move_to(tag)))
                tag._shown = new_t
        if changed or tags:
            self.play(LaggedStart(*changed, lag_ratio=0.35), *tags,
                      run_time=self.rt(max(0.6, 0.3 * len(changed))))
        self.say(self.describe_control(st), wait=2.2)
        if c == 1:
            self.say([f"{ASSUME}: ALUControl 3비트 값은 H&H 7장 인코딩. 슬라이드(L10 56–61)에는 연산 이름(funct/Add/bcond)만 있다."],
                     wait=2.2)

        self.run_jobs(st)
        self.cycle_summary(st)
        self.clock_edge(st)
        self.check_board(st)

    def describe_control(self, st):
        k = st["class"]
        unused = [n for n in ("DMEM", "SIGNEXT", "ADDBR") if n not in st["active"]["components"]]
        names = {"DMEM": "데이터 메모리", "SIGNEXT": "부호 확장", "ADDBR": "분기 덧셈기"}
        un = ", ".join(names[n] for n in unused)
        if k == "LW":
            l1 = "lw: RegWrite=1, ALUSrc=1(즉치값을 ALU로), MemtoReg=1(메모리 값을 레지스터로), RegDst=0(rt에 씀)."
        elif k == "SW":
            l1 = "sw: MemWrite=1, ALUSrc=1, RegWrite=0 — 레지스터에 쓰지 않으니 RegDst·MemtoReg는 X(옅은 회색)."
        elif k == "BEQ":
            l1 = "beq: Branch=1, ALUSrc=0, ALU는 뺄셈 — RegWrite=0이라 RegDst·MemtoReg는 X(옅은 회색)."
        elif k == "I":
            l1 = "addi(I-type): RegWrite=1, ALUSrc=1(즉치값), RegDst=0(rt에 씀), MemtoReg=0."
        else:
            l1 = f"{st['mnemonic']}(R-type): RegWrite=1, RegDst=1(rd에 씀), ALUSrc=0(두 번째 레지스터), MemtoReg=0."
        return [l1, f"이 명령어가 쓰지 않는 부품은 회색: {un}." if un else "이 명령어는 분기 경로까지 사용한다."]

    # ------------------------------------------------------- jobs (A + B) ---
    def job_text(self, st, job):
        v = st["values"]
        dur = {e["comp"]: e["end"] - e["start"] for e in st["timing"]["events"]}
        n = job["name"]
        if n == "IF_FETCH":
            return [f"0ps → IF ①: 명령어 메모리(instruction memory)에서 주소 0x{st['pc']:02X}의 명령어 "
                    f"0x{st['word']}를 읽는다 ({dur['IMEM']}ps)."]
        if n == "IF_PC4":
            return [f"IF ②: PC+4 덧셈기(adder)가 다음 PC 0x{v['PCPlus4']:02X} 계산 ({dur['ADD4']}ps).",
                    "※ ①과 ②는 실제로는 동시에 진행된다 — 화면에서만 하나씩 보여준다."]
        if n == "NEXT_PC":
            if st["class"] == "BEQ":
                return [f"다음 PC 선택: Zero={st['Zero']} & Branch=1 → PCSrc={st['PCSrc']} → "
                        + ("분기 목표" if st["PCSrc"] else "PC+4") + f" 0x{v['PCNext']:02X}가 PC 입력에 도착.",
                        "실제 저장은 클록 에지(clock edge)에서 일어난다."]
            return [f"다음 PC 선택: Branch=0 → PCSrc=0 → PC+4(0x{v['PCNext']:02X})가 PC 입력으로.",
                    f"이 값은 IF ②가 끝난 {dur['ADD4']}ps부터 이미 준비돼 있었다. 저장은 클록 에지에서."]
        return self.stage_text(st, job["stage"])

    def run_jobs(self, st):
        hop = st["wire_hop"]
        ev = {e["comp"]: e for e in st["timing"]["events"]}
        done_bar, lit = set(), set()
        self.job_ovs = []
        for job in st["jobs"]:
            self.say(self.job_text(st, job), wait=2.0)
            if job["stage"] and (self.B.phase_hl is None or self.cur_stage != job["stage"]):
                self.set_phase(STAGES.index(job["stage"]))
                self.cur_stage = job["stage"]
            jw = job["wires"]
            first = []
            for w in jw:
                src = self.wsrc[w]
                if hop[w] == 0 and src in self.dp.comps and src not in lit:
                    first.append(self.dp.comps[src])
                    lit.add(src)
            if first:
                self.play(*[m.animate.style("on") for m in first], run_time=self.rt(0.3))
            ovs = []
            for h in sorted({hop[w] for w in jw}):
                ws = [w for w in jw if hop[w] == h]
                an = []
                for w in ws:
                    ov = self.dp.wires[w].copy().style("on").set_z_index(4)
                    ovs.append(ov)
                    an.append(Create(ov))
                for w in ws:
                    part = "RF" if self.wdst[w] == "RF_W" else self.wdst[w]
                    if part in self.dp.comps and part not in lit and self.wdst[w] not in ev:
                        an.append(self.dp.comps[part].animate.style("on"))
                        lit.add(part)
                an += [FadeIn(g) for g in self.slots_for(st, ws)]
                self.play(*an, run_time=self.rt(0.5))
                for w in ws:
                    d = self.wdst[w]
                    if d in ev and d not in done_bar and h == max(hop[x] for x in jw if self.wdst[x] == d):
                        done_bar.add(d)
                        self.timed_unit(ev[d])
                        lit.add("RF" if d == "RF_W" else d)
            # the unit at the start of a job may have no input wire in this job (e.g. the PC)
            for ov in ovs:
                ov.style("done")
            self.job_ovs += ovs
            self.pause(0.3)

    def timed_unit(self, e):
        part = self.dp.comps["RF" if e["comp"] == "RF_W" else e["comp"]]
        row = next(i for i, (cs, _) in enumerate(ROWS) if e["comp"] in cs)
        y = TL_Y0 - TL_DY * row
        bar = Rectangle(width=self.px(e["end"]) - self.px(e["start"]), height=TL_DY * 0.72,
                        stroke_width=0).set_fill(ORANGE, 0.9)
        bar.move_to([self.px(e["start"]), y, 0], aligned_edge=LEFT)
        lab = txt(f"{e['start']}→{e['end']}ps", 9, INK, font=MONO).next_to(bar, RIGHT, buff=0.06)
        self.bars.add(bar, lab)
        self.play(part.animate.style("hot"), run_time=self.rt(0.2))
        self.play(GrowFromEdge(bar, LEFT), FadeIn(lab),
                  run_time=self.rt((e["end"] - e["start"]) * SEC_PER_PS_UNIT), rate_func=linear)
        self.play(part.animate.style("on"), run_time=self.rt(0.2))

    def slots_for(self, st, ws):
        out = []
        for slot, wl in SLOT_WIRES.items():
            if slot in self.shown_slots or not any(w in ws for w in wl):
                continue
            val = self.slot_value(st, slot)
            if val is None:
                continue
            self.shown_slots.add(slot)
            pos, _ = self.dp.slot(slot)
            lab = txt(val, 10, BLUE, font=MONO)
            bg = Rectangle(width=lab.width + 0.08, height=lab.height + 0.06, stroke_width=0).set_fill(WHITE, 0.85)
            g = VGroup(bg, lab).move_to([pos[0], pos[1], 0]).set_z_index(6)
            self.bars.add(g)
            out.append(g)
        return out

    def cycle_summary(self, st):
        tm = st["timing"]
        lat, period = tm["latency"], tm["period"]
        ub = Rectangle(width=self.px(lat) - TL_X0, height=0.15, stroke_width=0).set_fill(YEL_STRONG, 1)
        ub.move_to([TL_X0, self.sum_y, 0], aligned_edge=LEFT)
        l1 = txt(f"필요 {lat}ps", 10, INK, weight=BOLD).move_to([self.px(lat / 2), self.sum_y, 0]).set_z_index(5)
        self.play(GrowFromEdge(ub, LEFT), run_time=self.rt(0.8))
        self.play(FadeIn(l1), run_time=self.rt(0.2))
        self.bars.add(ub, l1)
        lines = [f"{lat}ps에 이 명령어의 일은 끝났다 ({self.lat_note(st)})."]
        if tm["waste"] > 0:
            wb = Rectangle(width=self.px(period) - self.px(lat), height=0.15, stroke_width=0).set_fill(RED, 0.35)
            wb.move_to([self.px(lat), self.sum_y, 0], aligned_edge=LEFT)
            l2 = txt(f"낭비 {tm['waste']}ps", 10, RED, weight=BOLD).move_to(
                [self.px((lat + period) / 2), self.sum_y, 0]).set_z_index(5)
            self.play(GrowFromEdge(wb, LEFT), FadeIn(l2), run_time=self.rt(0.6))
            self.bars.add(wb, l2)
            lines.append(f"하지만 클록은 {period}ps — 남은 {tm['waste']}ps 동안 아무것도 하지 않는다(낭비).")
        else:
            l2 = txt("낭비 0ps — 가장 느린 명령어", 10, RED).move_to([self.px(period) - 1.2, self.sum_y + 0.2, 0])
            self.play(FadeIn(l2), run_time=self.rt(0.3))
            self.bars.add(l2)
            lines.append(f"lw는 IF→ID→EX→MEM→WB 모두 써서 클록 {period}ps를 꽉 채운다.")
        self.say(lines, wait=1.8)

    def lat_note(self, st):
        names = {"IMEM": "명령어 메모리", "RF": "레지스터 읽기", "ALU": "ALU", "DMEM": "데이터 메모리",
                 "RF_W": "레지스터 쓰기"}
        path = [e for e in st["timing"]["events"] if e["comp"] in names]
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

    @staticmethod
    def stage_starts(st):
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
        if stage == "ID":
            regs = f"{rs}={v['RD1']}" + (f", {rt}={v['RD2']}" if k in ("R", "SW", "BEQ") else "")
            l2 = "제어 유닛(control unit)은 opcode를 보고 제어 신호를 낸다 (0ps)."
            if k in ("I", "LW", "SW", "BEQ"):
                l2 = f"부호 확장(sign extend): 즉치값 {v['SignImm']}. " + l2
            return [head + f"명령어의 필드가 퍼지고, 레지스터 파일(register file) 읽기: {regs} ({dur['RF']}ps).", l2]
        if stage == "EX":
            if k in ("LW", "SW"):
                l1 = f"ALU가 주소를 계산한다: {v['SrcA']} + {v['SignImm']} = {v['ALUResult']} ({dur['ALU']}ps)."
            elif k == "BEQ":
                l1 = f"ALU가 비교한다: {v['SrcA']} - {v['SrcB']} = {v['ALUResult']} → Zero={st['Zero']} ({dur['ALU']}ps)."
            else:
                l1 = f"ALU가 {st['alu_op']} 연산: {v['SrcA']} {OPSYM[st['alu_op']]} {v['SrcB']} = {v['ALUResult']} ({dur['ALU']}ps)."
            out = [head + l1]
            if k == "BEQ":
                br = next(e for e in st["timing"]["events"] if e["comp"] == "ADDBR")
                out.append(f"분기 덧셈기({br['start']}→{br['end']}ps): PC+4 + 즉치값×4 = 0x{v['PCBranch']:02X}.")
            return out
        if stage == "MEM":
            if k == "LW":
                return [head + f"데이터 메모리(data memory) 주소 {v['ALUResult']} 읽기 → 값 {v['ReadData']} ({dur['DMEM']}ps)."]
            return [head + f"데이터 메모리(data memory) 주소 {v['ALUResult']}에 값 {v['WriteData']} 쓰기 준비 ({dur['DMEM']}ps).",
                    "실제 저장은 클록 에지(clock edge)에서 일어난다."]
        return [head + f"결과 값 {v['Result']} → 레지스터 파일의 {v['WriteReg']} 쓰기 입력에 도착 ({dur['RF_W']}ps).",
                "실제 저장은 클록 에지(clock edge)에서 일어난다."]

    # ------------------------------------------------------ clock edge (D) ---
    def clock_edge(self, st):
        p = st["timing"]["period"]
        nxt = st["values"]["PCNext"]
        moves = [(r, str(val), "RF", self.regs.get(r)) for r, val in st["changes"]["regs"].items()]
        moves += [(f"Mem[{a}]", str(val), "DMEM", self.mem.get(a)) for a, val in st["changes"]["mem"].items()]
        moves.append(("PC", f"0x{nxt:02X}", "PC", self.pc_cell))
        words = [f"{n} ← {v}" for n, v, _, _ in moves]
        self.say([f"{p}ps: 클록 에지(clock edge) — " + ", ".join(words) + ". 다음 사이클이 시작된다."], wait=1.0)
        for n, v, part, cell in moves:
            if cell is None:
                continue
            fly = txt(v, 13, BLUE, font=MONO, weight=BOLD).move_to(self.dp.comps[part]).set_z_index(8)
            self.play(FadeIn(fly), self.dp.comps[part].animate.style("hot"), run_time=self.rt(0.25))
            self.play(fly.animate.move_to(cell.rect), run_time=self.rt(0.6))
            self.play(cell.change(v, BLUE), FadeOut(fly), self.dp.comps[part].animate.style("on"),
                      run_time=self.rt(0.3))
            self.blue_cells.append(cell)
        self.cum_cycles += 1
        self.cum_need += st["timing"]["latency"]
        P = self.period
        n1 = txt(f"{self.cum_cycles} × {P}ps = {self.cum_cycles * P}ps", 14, font=MONO).move_to([5.2, -2.05, 0])
        n2 = txt(f"실제로 필요했던 시간 합: {self.cum_need}ps", 12, FAINT).move_to([5.2, -2.35, 0])
        n3 = txt(f"낭비 합: {self.cum_cycles * P - self.cum_need}ps", 12, RED).move_to([5.2, -2.6, 0])
        self.play(self.tot1.animate.become(n1), self.tot2.animate.become(n2), self.tot2b.animate.become(n3),
                  run_time=self.rt(0.5))
        if st["class"] == "BEQ" and st["PCSrc"]:
            self.say([f"분기 목표 0x{nxt:02X}로 이동 — 바로 다음 명령어(0x{st['pc'] + 4:02X})는 건너뛴다."], wait=1.8)
            self.say([f"{ASSUME}: 분기 목표 덧셈기는 부호 확장 값이 나온 200ps에 시작한다고 계산 (L10 95 그림은 200ps 표시).",
                      "beq 전체 지연에는 영향 없음."], wait=2.2)
        for w in st["active"]["wires"]:
            self.dp.wires[w].style("done")
            self.wstyle[w] = "done"
        for c_ in st["active"]["components"]:
            self.cstyle[c_] = "on"
        self.remove(*self.job_ovs)
        self.job_ovs = []
        self.shown_slots = set()

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
        if self.pc_cell.s != f"0x{st['values']['PCNext']:02X}":
            bad.append(f"PC: screen {self.pc_cell.s} trace 0x{st['values']['PCNext']:02X}")
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
