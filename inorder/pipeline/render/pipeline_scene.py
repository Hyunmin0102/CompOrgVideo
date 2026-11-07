"""Pipelined MIPS video renderer.  Reads ONLY simulator traces:
inorder/pipeline/out/trace.json (and, for the final comparison, the single- and
multi-cycle traces).

    PL_STEPS=7 manim -ql --media_dir /tmp/media inorder/pipeline/render/pipeline_scene.py Pipeline
    manim --resolution 1920,1080 --frame_rate 30 --media_dir /tmp/media \
          inorder/pipeline/render/pipeline_scene.py Pipeline
    manim --dry_run inorder/pipeline/render/pipeline_scene.py Pipeline
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from manim import (BOLD, DOWN, LEFT, RIGHT, UP, WHITE, Create, DashedLine, FadeIn, FadeOut,  # noqa: E402
                   GrowFromEdge, Group, LaggedStart, Line, Rectangle, VGroup, linear)

from common.style import (ASSUME, BLUE, FAINT, GREY, INK, INSTR_COLORS, MONO, RED,  # noqa: E402
                          YEL, YEL_STRONG, Cell, StyleScene, term, txt)
from inorder.shared.datapath import PL_STAGE_X, Datapath  # noqa: E402

TRACE = ROOT / "inorder/pipeline/out/trace.json"
SC_TRACE = ROOT / "inorder/single_cycle/out/trace.json"
MC_TRACE = ROOT / "inorder/multi_cycle/out/trace.json"
STAGES = ["IF", "ID", "EX", "MEM", "WB"]
OCC = {"IF": "F", "ID": "D", "EX": "E", "MEM": "M", "WB": "W"}
LETTER = {"IF": "F", "ID": "D", "EX": "E", "MEM": "M", "WB": "W"}
SHOW_ORDER = ["WB", "MEM", "EX", "ID", "IF"]          # register file: WB writes 1st half, ID reads 2nd
HAZ_SIG = [("StallF", "StallF"), ("StallD", "StallD"), ("FlushE", "FlushE"), ("PCSrcD", "PCSrcD"),
           ("ForwardAE", "ForwardAE"), ("ForwardBE", "ForwardBE"), ("ForwardAD", "ForwardAD"),
           ("ForwardBD", "ForwardBD")]
OPSYM = {"add": "+", "sub": "-", "and": "&", "or": "|", "slt": "<"}

# timeline (bottom left)
TL_X0, TL_X1 = -5.3, 1.6
TL_Y0, TL_DY = -1.68, 0.2
LBL_X = -6.25
SEC_PER_PS_UNIT = 0.012

# pipeline diagram (top right)
DG_X0, DG_DX = 3.95, 0.2
DG_Y0, DG_DY = 3.12, 0.2


def icol(i):
    return INSTR_COLORS[(i - 1) % len(INSTR_COLORS)]


def hx(v):
    return f"0x{v:02X}"


class Board:
    SUB_Y = StyleScene.SUB_Y

    def __init__(self):
        self.phase_labels = VGroup(*[txt(s, 14, FAINT, weight=BOLD).move_to([(PL_STAGE_X[s][0] + PL_STAGE_X[s][1]) / 2,
                                                                              3.72, 0]) for s in STAGES])
        self.phase_hl = None


class Pipeline(StyleScene):
    def construct(self):
        self.T = json.loads(TRACE.read_text())
        self.period = self.T["config"]["period_ps"]
        self.texts = {i + 1: p["text"] for i, p in enumerate(self.T["config"]["program"])}
        n_env = os.environ.get("PL_STEPS")
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
        g = VGroup(txt("Pipelined MIPS 프로세서", 44, weight=BOLD),
                   txt("다섯 단계를 겹쳐서: 매 사이클 새 명령어 하나가 들어온다", 28),
                   txt("ETH DDCA · Onur Mutlu  |  Harris & Harris 7.5 (Fig. 7.58)", 20, FAINT)
                   ).arrange(DOWN, buff=0.35).move_to([0, 0.4, 0])
        self.play(FadeIn(g, shift=UP * 0.2))
        self.pause(1.5)
        self.play(FadeOut(g))
        head = txt("3편 공통 프로그램 (1·2편과 같음)", 28, weight=BOLD).move_to([0, 3.45, 0])
        rows = VGroup()
        for i, p in enumerate(cfg["program"]):
            r = VGroup(txt(f"I{i + 1}", 15, icol(i + 1), font=MONO, weight=BOLD), txt(hx(p["addr"]), 15, FAINT, font=MONO),
                       txt(p["text"], 16, font=MONO), txt(p["reason"], 12))
            r[0].move_to([-6.55, 0, 0]); r[1].move_to([-5.85, 0, 0])
            r[2].move_to([-5.3, 0, 0], aligned_edge=LEFT); r[3].move_to([-1.6, 0, 0], aligned_edge=LEFT)
            if r[3].width > 8.4:
                r[3].scale_to_fit_width(8.4).move_to([-1.6, 0, 0], aligned_edge=LEFT)
            r.move_to([r.get_x(), 2.85 - 0.5 * i, 0])
            rows.add(r)
        self.play(FadeIn(head), FadeIn(rows, lag_ratio=0.08, run_time=self.rt(1.6)))
        self.say(["이번 편의 주인공은 명령어 사이의 의존(dependency): 1·2편에서는 문제가 없던 것들이다.",
                  "명령어마다 색을 정해 두었다 — 한 화면에서 다섯 명령어가 동시에 움직이기 때문."], wait=4.0)
        self.say(["lw→add(load-use), add→sub(거리 1), add→and(거리 2), taken beq, sw를 일부러 넣었다."], wait=3.0)
        self.play(FadeOut(VGroup(head, rows)), FadeOut(self.sub))
        self.sub = None

    # ------------------------------------------------------------- board ---
    def build_board(self):
        cfg = self.T["config"]
        self.dp = Datapath(variant="pipe")
        self.dp.reset()
        self.shade = {}
        for s in STAGES:
            x0, x1 = PL_STAGE_X[s]
            self.shade[s] = Rectangle(width=x1 - x0, height=4.85, stroke_width=0).set_fill(WHITE, 0).move_to(
                [(x0 + x1) / 2, 1.05, 0]).set_z_index(-5)
        self.hdr = txt("사이클 – / –", 15).move_to([3.9, 3.72, 0])
        pcn = Cell(5.6, 3.72, 0.45, 0.24, "PC", size=11, font=MONO)
        self.pc_cell = Cell(6.3, 3.72, 0.9, 0.24, hx(self.T["steps"][0]["pcF"]), size=11, font=MONO)

        # pipeline diagram
        n_c = len(self.T["steps"])
        dg = VGroup()
        for c in range(1, n_c + 1):
            dg.add(txt(str(c), 8, FAINT, font=MONO).move_to([DG_X0 + DG_DX * (c - 1), DG_Y0 + 0.2, 0]))
        self.dg_cells = {}
        for i in range(1, len(cfg["program"]) + 1):
            y = DG_Y0 - DG_DY * (i - 1)
            lab = txt(f"I{i} {self.texts[i].split()[0]}", 9, icol(i), font=MONO, weight=BOLD)
            lab.move_to([DG_X0 - 0.25, y, 0], aligned_edge=RIGHT)
            dg.add(lab)
            for c in range(1, n_c + 1):
                cell = Rectangle(width=DG_DX, height=DG_DY, stroke_color=GREY, stroke_width=0.6).move_to(
                    [DG_X0 + DG_DX * (c - 1), y, 0])
                dg.add(cell)
                self.dg_cells[(i, c)] = cell
        self.dg = dg
        self.dg_marks = {}
        self.col_hl = None

        # hazard signals
        hz_t = txt(term("hazard unit 출력", "slide 69"), 12, weight=BOLD).move_to([5.2, 0.95, 0])
        self.hz = {}
        hg = VGroup(hz_t)
        for k, (name, _) in enumerate(HAZ_SIG):
            col, row = divmod(k, 4)
            y = 0.76 - 0.18 * row
            xn, xv = (3.42, 4.27) if col == 0 else (5.27, 6.42)
            a = Cell(xn, y, 1.0 if col == 0 else 1.2, 0.18, name, size=10, font=MONO)
            b = Cell(xv, y, 0.7, 0.18, "0" if not name.startswith("ForwardA") and not name.startswith("ForwardB")
                     else ("00" if name.endswith("E") else "0"), size=10, font=MONO)
            self.hz[name] = b
            hg.add(a.mobs(), b.mobs())

        reg_t = txt(term("레지스터", "register file"), 12, weight=BOLD).move_to([5.2, -0.05, 0])
        self.regs = {}
        rg = VGroup(reg_t)
        for i, n in enumerate(cfg["show_regs"]):
            col, row = divmod(i, 6)
            y = -0.24 - 0.18 * row
            xn, xv = (3.73, 4.58) if col == 0 else (5.48, 6.33)
            a = Cell(xn, y, 0.56, 0.18, n, size=10, font=MONO)
            b = Cell(xv, y, 1.14, 0.18, str(cfg["init_regs"].get(n, 0)), size=10, font=MONO)
            self.regs[n] = b
            rg.add(a.mobs(), b.mobs())
        mem_t = txt(term("데이터 메모리", "data memory"), 12, weight=BOLD).move_to([5.2, -1.4, 0])
        self.mem = {}
        mg = VGroup(mem_t)
        for i, a_ in enumerate(cfg["show_mem"]):
            y = -1.58 - 0.18 * i
            a = Cell(4.32, y, 1.74, 0.18, f"Mem[{a_}]", size=10, font=MONO)
            b = Cell(6.05, y, 1.72, 0.18, str(cfg["init_mem"].get(a_, 0)), size=10, font=MONO)
            self.mem[a_] = b
            mg.add(a.mobs(), b.mobs())
        self.tot1 = txt("–", 12, font=MONO).move_to([5.2, -2.3, 0]).set_opacity(0)
        self.tot2 = txt("–", 11, FAINT).move_to([5.2, -2.55, 0]).set_opacity(0)

        # timeline: one row per stage
        tl = VGroup(Line([TL_X0, TL_Y0 + 0.12, 0], [TL_X1, TL_Y0 + 0.12, 0], stroke_width=1.2, color=INK))
        for ps in range(0, self.period + 1, 50):
            x = self.px(ps)
            tl.add(Line([x, TL_Y0 + 0.09, 0], [x, TL_Y0 + 0.15, 0], stroke_width=1, color=INK),
                   txt(f"{ps}", 9, INK, font=MONO).move_to([x, TL_Y0 + 0.23, 0]),
                   DashedLine([x, TL_Y0 + 0.09, 0], [x, TL_Y0 - TL_DY * 4.6, 0], stroke_width=0.6, color=FAINT,
                              dash_length=0.04))
        tl.add(txt("ps", 9, INK, font=MONO).move_to([TL_X1 + 0.2, TL_Y0 + 0.23, 0]))
        half = self.px(self.period / 2)
        tl.add(Line([half, TL_Y0 + 0.12, 0], [half, TL_Y0 - TL_DY * 4.6, 0], stroke_width=1.6, color=INK))
        tl.add(txt("반 사이클", 9, INK).move_to([half, TL_Y0 - TL_DY * 4.85, 0]))
        tl.add(Line([self.px(self.period), TL_Y0 + 0.12, 0], [self.px(self.period), TL_Y0 - TL_DY * 4.6, 0],
                    stroke_width=2.2, color=RED))
        self.tl_lbl = {}
        for k, s in enumerate(STAGES):
            lab = txt(s, 10, FAINT, weight=BOLD).move_to([LBL_X, TL_Y0 - TL_DY * k, 0])
            self.tl_lbl[s] = lab
            tl.add(lab)
        self.tl = tl

        self.play(FadeIn(self.dp, run_time=self.rt(1.2)), *[FadeIn(r) for r in self.shade.values()])
        self.say(["H&H 최종 pipeline 프로세서(슬라이드 79, Fig. 7.58). 단계 사이의 세로 막대가 pipeline 레지스터.",
                  "제어 신호(파란 선 자리)도 명령어와 함께 단계마다 한 칸씩 늦게 전달된다(슬라이드 20)."], wait=3.5)
        self.play(FadeIn(self.B.phase_labels), FadeIn(self.hdr), FadeIn(VGroup(pcn.mobs(), self.pc_cell.mobs())),
                  FadeIn(self.dg), run_time=self.rt(0.8))
        self.say(["오른쪽 위는 파이프라인 다이어그램: 행 = 명령어, 열 = 사이클. 매 사이클 한 열씩 채운다.",
                  "F·D·E·M·W = IF·ID·EX·MEM·WB."], wait=3.0)
        self.play(FadeIn(hg), FadeIn(rg), FadeIn(mg), FadeIn(self.tl), run_time=self.rt(0.8))
        d = cfg["delays_ps"]
        self.say(["아래 hazard unit(슬라이드 69)이 stall·forwarding·flush를 정한다. 출력 값은 오른쪽 표.",
                  f"단계 시간(1·2편과 같은 지연): IF·MEM 메모리 {d['mem']}ps, EX ALU {d['alu']}ps, ID·WB 레지스터 파일 {d['rf']}ps(반 사이클)."],
                 wait=3.5)
        self.say([f"{ASSUME}: 슬라이드 86의 550ps는 다른 지연 표의 값. 1·2편과 비교하려고 같은 지연으로 클록 {self.period}ps를 잡았다.",
                  "레지스터 파일은 WB가 앞 절반에 쓰고 ID가 뒤 절반에 읽는다 — 그래서 매 사이클 WB부터 거꾸로 보여준다."], wait=4.0)
        self.cstyle = {n: "idle" for n in self.dp.comps}
        self.wstyle = {n: "idle" for n in self.dp.wires}
        self.bars, self.blue_cells, self.job_ovs, self.shown_slots = VGroup(), [], [], set()
        self.done = 0

    def px(self, ps):
        return TL_X0 + (TL_X1 - TL_X0) * ps / self.period

    # ------------------------------------------------------------- cycle ---
    def cycle(self, st):
        c = st["cycle"]
        stages = st["stages"]
        for cell in self.blue_cells:
            cell.recolor(INK)
        self.blue_cells = []

        # header, stage colours, diagram column (who is where this cycle)
        hdr = txt(f"사이클 {c} / {len(self.T['steps'])}", 15).move_to([3.9, 3.72, 0])
        an = [FadeOut(m) for m in self.bars] + [FadeOut(self.hdr), FadeIn(hdr)]
        for s in STAGES:
            i = st["occupancy"][OCC[s]]
            col = icol(i) if i else WHITE
            an.append(self.shade[s].animate.set_fill(col, 0.08 if i else 0))
            lab = self.B.phase_labels[STAGES.index(s)]
            new = txt(f"{s}: I{i}" if i else f"{s}: –", 14, icol(i) if i else FAINT, weight=BOLD).move_to(lab)
            an.append(lab.animate.become(new))
            self.tl_lbl[s].set_color(icol(i) if i else FAINT)
        col_x = DG_X0 + DG_DX * (c - 1)
        new_hl = Rectangle(width=DG_DX, height=DG_DY * 10 + 0.05, stroke_width=0).set_fill(YEL, 0.6).move_to(
            [col_x, DG_Y0 - DG_DY * 4.5, 0]).set_z_index(-2)
        an.append(FadeIn(new_hl) if self.col_hl is None else self.col_hl.animate.move_to(new_hl))
        if self.col_hl is None:
            self.col_hl = new_hl
        marks = []
        for s in STAGES:
            i = st["occupancy"][OCC[s]]
            if i is None:
                continue
            stalled = (s == "IF" and st["stalled"]["F"]) or (s == "ID" and st["stalled"]["D"])
            m = VGroup(Rectangle(width=DG_DX, height=DG_DY, stroke_width=0).set_fill(icol(i), 0.85 if not stalled else 0.4),
                       txt(LETTER[s], 9, WHITE, font=MONO, weight=BOLD)).move_to(self.dg_cells[(i, c)])
            self.dg_marks[(i, c)] = m
            marks.append(m)
        self.play(*an, LaggedStart(*[FadeIn(m) for m in marks], lag_ratio=0.2), run_time=self.rt(0.9))
        self.hdr = hdr
        self.bars = VGroup()
        occ_txt = ", ".join(f"{s} I{st['occupancy'][OCC[s]]}" for s in STAGES if st["occupancy"][OCC[s]])
        self.say([f"사이클 {c}: {occ_txt}"], wait=1.0)
        self.predict(c, hint="각 단계의 명령어는 무엇을 하고, hazard unit은 stall·forwarding·flush를 낼까?")

        # (C) restyle only what changes
        used_w = {w for v in stages.values() for w in v["wires"]} | set(st["hazard_wires"])
        used_c = {p for v in stages.values() for p in v["comps"]}
        if st["hazard_wires"]:
            used_c.add("HAZ")
        an = []
        for n, comp in self.dp.comps.items():
            want = "idle" if n in used_c else "off"
            if self.cstyle.get(n) != want:
                an.append(comp.animate.style(want))
                self.cstyle[n] = want
        for n, w in self.dp.wires.items():
            want = "idle" if n in used_w else "off"
            if self.wstyle.get(n) != want:
                an.append(w.animate.style(want))
                self.wstyle[n] = want
        if an:
            self.play(*an, run_time=self.rt(0.6))

        # (C) hazard signal table: only changes
        h = st["hazard"]
        ch = []
        for name, key in HAZ_SIG:
            v = str(h[key])
            if self.hz[name].s != v:
                ch.append(self.hz[name].change(v, BLUE))
                self.blue_cells.append(self.hz[name])
        if ch:
            self.play(LaggedStart(*ch, lag_ratio=0.3), run_time=self.rt(max(0.6, 0.3 * len(ch))))

        # (A + B) one stage at a time: WB, MEM, EX, ID, (hazard), IF
        for s in SHOW_ORDER:
            if s in stages:
                self.run_stage(st, s)
            if s == "ID":
                self.hazard_job(st)
        self.cycle_note(st)
        self.clock_edge(st)
        self.check_board(st)

    # ------------------------------------------------------------ text ---
    def stage_text(self, st, s):
        v = st["stages"][s]
        i, k = v["id"], v["class"]
        tag = f"{s} — I{i} {self.texts[i]}: "
        if s == "WB":
            w = st["W"]
            if k in ("R", "I", "LW"):
                return [tag + f"결과 {w['ResultW']} → {w['WriteRegW']} (레지스터 파일 앞 절반 0→50ps에 쓰기)."]
            return [tag + "쓸 레지스터 없음 — 지나가기만 한다."]
        if s == "MEM":
            m = st["M"]
            if k == "LW":
                return [tag + f"데이터 메모리 주소 {m['ALUOutM']} 읽기 → {m['ReadDataM']} (200ps)."]
            if k == "SW":
                return [tag + f"데이터 메모리 주소 {m['ALUOutM']}에 {m['WriteDataM']} 쓰기 (200ps, 저장은 클록 에지)."]
            return [tag + f"메모리를 쓰지 않음 — ALU 결과 {m['ALUOutM']}를 MEM/WB로 넘긴다."]
        if s == "EX":
            e = st["E"]
            fa, fb = st["hazard"]["ForwardAE"], st["hazard"]["ForwardBE"]
            src = {"00": "ID/EX(레지스터 값)", "10": "MEM 단계의 ALUOutM (forwarding)",
                   "01": "WB 단계의 ResultW (forwarding)"}
            l2 = f"SrcA ← {src[fa]}" + (f", B ← {src[fb]}" if k in ("R", "SW", "BEQ") and fb != "00" else "")
            op = OPSYM.get(st_alu(self.T, i), "+")
            if k == "BEQ":
                return [tag + "분기는 이미 ID에서 판정됐다 — EX에서는 할 일이 거의 없다."]
            return [tag + f"ALU: {e['SrcAE']} {op} {e['SrcBE']} = {e['ALUOutE']} (100ps).", l2 + "."]
        if s == "ID":
            d = st["D"]
            regs = f"{d['rsD']}={d['RD1']}" + (f", {d['rtD']}={d['RD2']}" if k in ("R", "SW", "BEQ") else "")
            out = [tag + f"제어 신호 생성, 레지스터 읽기 {regs} (뒤 절반 100→150ps)."]
            if k == "BEQ":
                out.append(f"분기를 여기서 판정(early branch resolution): EqualD={d['EqualD']} → PCSrcD={d['PCSrcD']}, "
                           f"목표 {hx(d['PCBranchD'])}.")
            return out
        f = st["F"]
        if st["hazard"]["StallF"]:
            return [tag + f"명령어 메모리에서 {hx(f['pc'])} 읽기 — 하지만 StallF=1이라 PC는 그대로(같은 명령어를 다시 읽게 된다)."]
        if st["hazard"]["PCSrcD"]:
            return [tag + f"{hx(f['pc'])}의 명령어를 읽었지만, 분기가 taken이라 IF/ID가 비워진다(flush)."]
        return [tag + f"명령어 메모리에서 {hx(f['pc'])} 읽기(200ps), PC+4 = {hx(f['PCPlus4F'])}."]

    def run_stage(self, st, s):
        v = st["stages"][s]
        i = v["id"]
        col = icol(i)
        self.say(self.stage_text(st, s), wait=1.6)
        self.set_phase(STAGES.index(s))
        lit = set()
        hops = sorted(set(v["hop"].values()))
        ovs = []
        timed = {e["after_hop"]: [] for e in v["timed"]}
        for e in v["timed"]:
            timed[e["after_hop"]].append(e)
        first = [p for p in v["comps"] if p in ("PC", "IFID", "IDEX", "EXMEM", "MEMWB") and p in self.dp.comps]
        if first:
            self.play(*[self.tint(self.dp.comps[p], col) for p in first], run_time=self.rt(0.3))
            lit |= set(first)
        for h in hops:
            ws = [w for w in v["wires"] if v["hop"][w] == h]
            an = []
            for w in ws:
                ov = self.dp.wires[w].copy()
                ov.line.set_stroke(col, 3.2, opacity=1)
                ov.tip.set_fill(col, 1)
                ov.set_z_index(4)
                ovs.append(ov)
                an.append(Create(ov))
            an += [FadeIn(g) for g in self.slots_for(st, s, ws)]
            self.play(*an, run_time=self.rt(0.45))
            for e in timed.get(h, []):
                self.timed_unit(s, e, col)
                lit.add("RF" if e["comp"] == "RF_W" else e["comp"])
        rest = [p for p in v["comps"] if p not in lit and p in self.dp.comps]
        if rest:
            self.play(*[self.tint(self.dp.comps[p], col) for p in rest], run_time=self.rt(0.3))
        for ov in ovs:
            ov.line.set_stroke(opacity=0.45, width=2.4)
            ov.tip.set_fill(opacity=0.45)
        self.job_ovs += ovs

    def tint(self, part, col):
        part.generate_target()
        part.target.body.set_stroke(INK, 2.0).set_fill(col, 0.22 if part.kind not in ("and",) else 0)
        part.target.labels.set_color(INK)
        from manim import MoveToTarget
        return MoveToTarget(part)

    def timed_unit(self, s, e, col):
        part = self.dp.comps["RF" if e["comp"] == "RF_W" else e["comp"]]
        y = TL_Y0 - TL_DY * STAGES.index(s)
        bar = Rectangle(width=self.px(e["end"]) - self.px(e["start"]), height=TL_DY * 0.7, stroke_width=0)
        bar.set_fill(col, 0.85).move_to([self.px(e["start"]), y, 0], aligned_edge=LEFT)
        nm = {"IMEM": "명령어 메모리", "ADD4": "PC+4", "RF": "레지스터 읽기", "ADDBR": "분기 덧셈기", "ALU": "ALU",
              "DMEM": "데이터 메모리", "RF_W": "레지스터 쓰기"}[e["comp"]]
        lab = txt(f"{nm} {e['start']}→{e['end']}", 8, INK).next_to(bar, RIGHT, buff=0.05)
        if s == "IF" and e["comp"] == "ADD4":
            lab.next_to(bar, DOWN, buff=0.0).shift(UP * 0.02).set_opacity(0)
        self.bars.add(bar, lab)
        self.play(part.animate.style("hot"), run_time=self.rt(0.2))
        self.play(GrowFromEdge(bar, LEFT), FadeIn(lab), run_time=self.rt((e["end"] - e["start"]) * SEC_PER_PS_UNIT),
                  rate_func=linear)
        self.play(self.tint(part, col), run_time=self.rt(0.2))

    def slots_for(self, st, s, ws):
        vals = []
        d, e, m, w, f = st["D"], st["E"], st["M"], st["W"], st["F"]
        table = {
            "IF": [("PCF", ["pc_imem"], lambda: hx(f["pc"]))],
            "ID": [("InstrD", ["instrd_ctrl"], lambda: f"I{st['stages']['ID']['id']}"),
                   ("RD1", ["rd1_idex"], lambda: str(d["RD1"])), ("RD2", ["rd2_idex"], lambda: str(d["RD2"])),
                   ("SignImmD", ["signimm_idex", "signimm_sl2"], lambda: str(d["SignImmD"])),
                   ("EqualD", ["eq_and"], lambda: f"EqualD={d['EqualD']}"),
                   ("PCBranchD", ["pcbranch"], lambda: hx(d["PCBranchD"]))],
            "EX": [("SrcAE", ["fae_srca"], lambda: str(e["SrcAE"])), ("SrcBE", ["srcb"], lambda: str(e["SrcBE"])),
                   ("ALUOutE", ["alu_exmem"], lambda: str(e["ALUOutE"])),
                   ("WriteRegE", ["writerege"], lambda: e["WriteRegE"])],
            "MEM": [("ALUOutM", ["aluoutm_dmem", "aluoutm_memwb"], lambda: str(m["ALUOutM"])),
                    ("WriteDataM", ["writedatam_dmem"], lambda: str(m["WriteDataM"])),
                    ("ReadDataM", ["dmem_memwb"], lambda: str(m["ReadDataM"]))],
            "WB": [("ResultW", ["resultw_wd3"], lambda: str(w["ResultW"])),
                   ("WriteRegW", ["writeregw_a3"], lambda: w["WriteRegW"])],
        }[s]
        for slot, wl, fn in table:
            if slot in self.shown_slots or not any(x in ws for x in wl):
                continue
            self.shown_slots.add(slot)
            pos, _ = self.dp.slot(slot)
            lab = txt(fn(), 9, BLUE, font=MONO)
            bg = Rectangle(width=lab.width + 0.06, height=lab.height + 0.05, stroke_width=0).set_fill(WHITE, 0.85)
            g = VGroup(bg, lab).move_to([pos[0], pos[1], 0]).set_z_index(6)
            self.bars.add(g)
            vals.append(g)
        return vals

    # ------------------------------------------------------------ hazards ---
    def hazard_job(self, st):
        evs = st["events"]
        h = st["hazard"]
        for e in evs:
            if e["type"] == "lwstall":
                self.say([f"hazard unit: lwstall = ((rsD == rtE) | (rtD == rtE)) & MemtoRegE = 1 — "
                          f"I{e['from']} lw의 {e['reg']} 값은 MEM이 끝나야 나온다.",
                          "→ StallF·StallD=1 (PC·IF/ID 유지), FlushE=1 (ID/EX에 bubble). I2는 한 사이클 기다린다."],
                         wait=2.4)
                self.flash_wires(st["hazard_wires"], RED)
            elif e["type"] == "flush":
                self.say([f"I{e['by']} beq가 ID에서 taken으로 판정 → PCSrcD=1: PC ← {hx(e['target'])}, "
                          f"IF/ID의 CLR=1 → 방금 읽은 I{e['flushed']}를 버린다(flush 1개).",
                          "always-not-taken 예측이 틀린 대가: 1사이클(슬라이드 65)."], wait=2.6)
                self.flash_wires(["pcsrc", "pcsrc_clr"], RED)
            elif e["type"] == "rf_half":
                self.say([f"I{e['to']}가 읽는 {e['reg']}는 같은 사이클에 WB의 I{e['from']}가 앞 절반에 쓴 값({e['value']}).",
                          "레지스터 파일을 반 사이클씩 나눠 써서 forwarding 없이 해결된다."], wait=2.4)
        if h["ForwardAE"] != "00" or h["ForwardBE"] != "00":
            fe = [e for e in evs if e["type"].startswith("fwd_")]
            for e in fe:
                where = "MEM 단계(ALUOutM)" if e["type"] == "fwd_MEM_EX" else "WB 단계(ResultW)"
                code = "10" if e["type"] == "fwd_MEM_EX" else "01"
                port = "ForwardAE" if e["port"] == "A" else "ForwardBE"
                cond = "WriteRegM & RegWriteM" if code == "10" else "WriteRegW & RegWriteW"
                self.say([f"forwarding: I{e['to']}의 {e['reg']} = I{e['from']}의 결과 {e['value']}가 아직 레지스터에 없다.",
                          f"rs/rtE == {cond} → {port} = {code}: {where}에서 바로 ALU로 가져온다."], wait=2.4)
                wires = {"fwd_MEM_EX": {"A": ["fwd_m_fae"], "B": ["fwd_m_fbe"]},
                         "fwd_WB_EX": {"A": ["fwd_w_fae"], "B": ["fwd_w_fbe"]}}[e["type"]][e["port"]]
                self.flash_wires(wires + (["h_fwdae"] if e["port"] == "A" else ["h_fwdbe"]), RED)

    def flash_wires(self, names, color):
        ovs = []
        for n in names:
            ov = self.dp.wires[n].copy()
            ov.line.set_stroke(color, 4.5, opacity=1)
            ov.tip.set_fill(color, 1)
            ov.set_z_index(7)
            ovs.append(ov)
        self.play(*[Create(o) for o in ovs], run_time=self.rt(0.6))
        self.pause(0.8)
        self.play(*[o.animate.set_stroke(opacity=0.35) for o in ovs], run_time=self.rt(0.3))
        self.job_ovs += ovs

    def cycle_note(self, st):
        used = max((v["used_ps"] for v in st["stages"].values()), default=0)
        busy = ", ".join(f"{s} {v['used_ps']}" for s, v in st["stages"].items() if v["used_ps"])
        self.say([f"이 사이클에서 각 단계의 일이 끝나는 시각(ps): {busy} — 가장 늦은 것 {used}ps, 클록 {self.period}ps.",
                  "다섯 단계가 같은 클록 안에서 동시에 일한다 (ID는 반 사이클 뒤에 시작)."], wait=1.6)

    # ------------------------------------------------------- clock edge ---
    def clock_edge(self, st):
        moves = []
        for r, val in st["changes"]["regs"].items():
            moves.append((r, str(val), "RF", self.regs.get(r)))
        for a, val in st["changes"]["mem"].items():
            moves.append((f"Mem[{a}]", str(val), "DMEM", self.mem.get(a)))
        if st["PCnext"] != st["pcF"] or True:
            moves.append(("PC", hx(st["PCnext"]), "PC", self.pc_cell))
        words = [f"{n} ← {v}" for n, v, _, _ in moves]
        adv = "pipeline 레지스터는 다음 단계로 한 칸씩" + (" (IF/ID는 유지, ID/EX에는 bubble)" if st["hazard"]["StallD"]
                                                     else " (IF/ID는 비움)" if st["hazard"]["PCSrcD"] else "")
        self.say([f"{self.period}ps: 클록 에지 — " + ", ".join(words) + ".", adv + "."], wait=1.2)
        for n, v, part, cell in moves:
            if cell is None:
                continue
            fly = txt(v, 12, BLUE, font=MONO, weight=BOLD).move_to(self.dp.comps[part]).set_z_index(8)
            self.play(FadeIn(fly), run_time=self.rt(0.2))
            self.play(fly.animate.move_to(cell.rect), run_time=self.rt(0.55))
            self.play(cell.change(v, BLUE), FadeOut(fly), run_time=self.rt(0.25))
            self.blue_cells.append(cell)
        if st["occupancy"]["W"] is not None:
            self.done += 1
        P = self.period
        n1 = txt(f"{st['cycle']} 사이클 × {P}ps = {st['cycle'] * P}ps", 12, font=MONO).move_to([5.2, -2.3, 0])
        n2 = txt(f"끝난 명령어 {self.done}개", 11, FAINT).move_to([5.2, -2.55, 0])
        self.play(self.tot1.animate.become(n1), self.tot2.animate.become(n2), run_time=self.rt(0.4))
        for w in self.dp.wires:
            if self.wstyle.get(w) == "idle":
                self.dp.wires[w].style("done")
                self.wstyle[w] = "done"
        self.remove(*self.job_ovs)
        self.job_ovs = []
        self.shown_slots = set()
        for n, part in self.dp.comps.items():
            if self.cstyle.get(n) == "idle":
                part.style("on")
                self.cstyle[n] = "on"

    # ------------------------------------------------------ check board ---
    def check_board(self, st):
        bad = []
        c = st["cycle"]
        for s in STAGES:
            i = st["occupancy"][OCC[s]]
            if i is not None and (i, c) not in self.dg_marks:
                bad.append(f"diagram I{i} cycle {c}")
        for (i, cc), m in self.dg_marks.items():
            if cc == c and i not in st["occupancy"].values():
                bad.append(f"diagram extra I{i}")
        for name, key in HAZ_SIG:
            if self.hz[name].s != str(st["hazard"][key]):
                bad.append(f"{name}: screen {self.hz[name].s} trace {st['hazard'][key]}")
        for r, cell in self.regs.items():
            if cell.s != str(st["regs_after"][r]):
                bad.append(f"{r}: screen {cell.s} trace {st['regs_after'][r]}")
        for a, cell in self.mem.items():
            if cell.s != str(st["mem_after"].get(a, 0)):
                bad.append(f"Mem[{a}]")
        if self.pc_cell.s != hx(st["PCnext"]):
            bad.append("PC")
        if bad:
            raise RuntimeError(f"check_board cycle {c}: " + "; ".join(bad))

    # ------------------------------------------------------------ finale ---
    def finale(self, complete):
        T, P = self.T, self.period
        sc, mc = json.loads(SC_TRACE.read_text()), json.loads(MC_TRACE.read_text())
        # mark the flushed instruction in the diagram before leaving
        for i in T["flushed"]:
            cs = [c for (j, c) in self.dg_marks if j == i]
            for c in cs:
                self.add(txt("×", 14, RED, weight=BOLD).move_to(self.dg_cells[(i, c)]).set_z_index(9))
        self.play(FadeOut(Group(*self.mobjects)))
        self.clear()
        self.sub, self.B.phase_hl = None, None
        title = txt("세 마이크로아키텍처 비교 (같은 프로그램, 같은 부품 지연)", 28, weight=BOLD).move_to([0, 3.4, 0])
        self.play(FadeIn(title))
        rows = [("single-cycle", sc["final"]["cycles"], sc["config"]["period_ps"], sc["final"]["total_ps"]),
                ("multi-cycle", mc["final"]["cycles"], mc["config"]["period_ps"], mc["final"]["total_ps"]),
                ("pipeline", T["final"]["cycles"], P, T["final"]["total_ps"])]
        mx = max(r[3] for r in rows)
        X0, W = -2.2, 8.4
        g = VGroup()
        for k, (name, cyc, per, tot) in enumerate(rows):
            y = 2.3 - 1.0 * k
            bar = Rectangle(width=W * tot / mx, height=0.5, stroke_width=0).set_fill(
                [FAINT, GREY, YEL_STRONG][k] if k < 2 else YEL_STRONG, 1).move_to([X0, y, 0], aligned_edge=LEFT)
            g.add(txt(name, 20, weight=BOLD).move_to([-4.4, y, 0]), bar,
                  txt(f"{cyc} 사이클 × {per}ps = {tot}ps", 16, font=MONO).next_to(bar, RIGHT, buff=0.15)
                  if bar.get_right()[0] < 3.2 else
                  txt(f"{cyc} 사이클 × {per}ps = {tot}ps", 16, font=MONO).move_to(bar))
        self.play(LaggedStart(*[FadeIn(x) for x in g], lag_ratio=0.15), run_time=self.rt(2.0))
        n = T["final"]["instructions"]
        stalls = sum(1 for s in T["steps"] for e in s["events"] if e["type"] in ("lwstall", "branchstall"))
        flushes = len(T["flushed"])
        eq = txt(f"pipeline: 5 + ({n} − 1) + stall {stalls} + flush {flushes} = {T['final']['cycles']} 사이클", 22,
                 weight=BOLD).move_to([0, -1.0, 0])
        self.play(FadeIn(eq))
        if complete:
            assert T["final"]["cycles"] == 5 + (n - 1) + stalls + flushes
        self.say(["forwarding이 대부분의 의존을 stall 없이 해결했고, load-use 1번과 taken 분기 1번만 1사이클씩 잃었다.",
                  "명령어가 많아지면 채우는 4사이클의 비중이 줄어 CPI는 1에 가까워진다(슬라이드 80–87의 예: CPI 1.15)."], wait=5.0)
        self.play(FadeOut(Group(*self.mobjects)))
        self.clear()


def st_alu(T, i):
    for s in T["steps"]:
        if s["D"] and s["occupancy"]["D"] == i:
            return s["D"]["alu_op"]
    return "add"
