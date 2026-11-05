"""Multi-cycle MIPS simulator (H&H Ch. 7.4, slides 57-58 of the multi-cycle deck, without j).

Register-level, cycle by cycle:
  * the main controller FSM (S0..S10) gives the control signals of each state
  * combinational values are computed from the current registers
  * at the clock edge PC / IR / Data / A / B / ALUOut / register file / memory update
    (A, B, Data, ALUOut load every cycle, as in H&H; IR and PC only when enabled)

Writes inorder/multi_cycle/out/trace.json.

    python3 inorder/multi_cycle/sim/multi_cycle.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from inorder.shared.isa import (MASK32, OP_ADDI, OP_BEQ, OP_LW, OP_RTYPE, OP_SW,  # noqa: E402
                                FUNCT_NAME, assemble, decode, reg_name, s32)
from inorder.shared.interpreter import alu_r, initial_state  # noqa: E402
from inorder.shared.program import (BASE_PC, INIT_MEM, INIT_REGS, PROGRAM,  # noqa: E402
                                    REASONS, SHOW_MEM, SHOW_REGS)

OUT = ROOT / "inorder" / "multi_cycle" / "out" / "trace.json"

# --- L10 slide 90 delays (repeated as the last page of the multi-cycle deck) ---
DELAYS = {"mem": 200, "alu": 100, "adder": 100, "rf": 50, "other": 0}
ALUCTL = {"add": "010", "sub": "110", "and": "000", "or": "001", "slt": "111"}

ASSUMPTIONS = [
    "클록 주기: 슬라이드에 multi-cycle 클록 값이 없음. L10 90의 지연(메모리 200, ALU 100, "
    "레지스터 파일 50, 나머지·레지스터 오버헤드 0ps)으로 각 상태의 가장 긴 일을 계산하면 "
    "메모리 접근(S0, S3, S5) 200ps가 최대 → 클록 200ps.",
    "ALUControl 3비트 값은 H&H 7장 인코딩(add 010, sub 110, and 000, or 001, slt 111). "
    "ALU 디코더(ALUOp 00=add, 01=sub, 10=funct)도 H&H 표를 따름 — 슬라이드에는 블록 그림만 있음.",
    "FSM 그림에 적히지 않은 신호: 1비트 쓰기 신호(IRWrite, PCWrite, MemWrite, RegWrite, Branch)는 0, "
    "mux 선택(IorD, ALUSrcA, ALUSrcB, PCSrc, RegDst, MemtoReg)은 X(don't care) — H&H 관례. "
    "X인 mux는 시뮬레이션에서 0번 입력을 쓰고, 결과가 아키텍처 상태에 영향을 주지 않음을 검증함.",
    "j(S11)는 공통 프로그램에서 쓰지 않으므로 그리지 않음.",
]

# --- main controller FSM (slide 58).  Only what the bubble lists; rest per ASSUMPTIONS ---
WRITES = ("IRWrite", "PCWrite", "MemWrite", "RegWrite", "Branch")
SELECTS = ("IorD", "ALUSrcA", "ALUSrcB", "PCSrc", "RegDst", "MemtoReg")
FSM = {
    "S0": {"name": "Fetch", "IorD": 0, "ALUSrcA": 0, "ALUSrcB": "01", "ALUOp": "00", "PCSrc": "00",
           "IRWrite": 1, "PCWrite": 1},
    "S1": {"name": "Decode", "ALUSrcA": 0, "ALUSrcB": "11", "ALUOp": "00"},
    "S2": {"name": "MemAdr", "ALUSrcA": 1, "ALUSrcB": "10", "ALUOp": "00"},
    "S3": {"name": "MemRead", "IorD": 1},
    "S4": {"name": "Mem Writeback", "RegDst": 0, "MemtoReg": 1, "RegWrite": 1},
    "S5": {"name": "MemWrite", "IorD": 1, "MemWrite": 1},
    "S6": {"name": "Execute", "ALUSrcA": 1, "ALUSrcB": "00", "ALUOp": "10"},
    "S7": {"name": "ALU Writeback", "RegDst": 1, "MemtoReg": 0, "RegWrite": 1},
    "S8": {"name": "Branch", "ALUSrcA": 1, "ALUSrcB": "00", "ALUOp": "01", "PCSrc": "01", "Branch": 1},
    "S9": {"name": "ADDI Execute", "ALUSrcA": 1, "ALUSrcB": "10", "ALUOp": "00"},
    "S10": {"name": "ADDI Writeback", "RegDst": 0, "MemtoReg": 0, "RegWrite": 1},
}


def next_state(s, op):
    if s == "S0":
        return "S1"
    if s == "S1":
        return {OP_LW: "S2", OP_SW: "S2", OP_RTYPE: "S6", OP_BEQ: "S8", OP_ADDI: "S9"}[op]
    if s == "S2":
        return "S3" if op == OP_LW else "S5"
    return {"S3": "S4", "S6": "S7", "S9": "S10"}.get(s, "S0")


def signals(s):
    f = FSM[s]
    c = {k: f.get(k, 0) for k in WRITES}
    c.update({k: f.get(k, "X") for k in SELECTS})
    c["ALUOp"] = f.get("ALUOp", "X")
    return c


def alu_op(aluop, funct):
    if aluop == "00":
        return "add"
    if aluop == "01":
        return "sub"
    if aluop == "10":
        return FUNCT_NAME[funct]
    return None                     # ALU result unused in this state


X_DEFAULT = 0   # value the hardware happens to use for an X select (verify also tries 1)


def sel(v):
    """value used by the hardware for a mux select."""
    return X_DEFAULT if v == "X" else int(v, 2) if isinstance(v, str) else v


# --- what each state uses (for painting) and how long its work takes ---------
def state_work(s, c, op_name):
    D = DELAYS
    comps, wires, ev = ["PC", "CTRL"], [], []

    def add(comp, start, dur, stage):
        ev.append({"comp": comp, "stage": stage, "start": start, "end": start + dur})
        return start + dur
    if s == "S0":
        comps += ["IORDMUX", "MEM", "IR", "SRCAMUX", "SRCBMUX", "ALU", "PCMUX", "AND"]
        wires += ["pc_iord", "iord_adr", "mem_ir", "pc_srca", "four_srcb", "srca", "srcb",
                  "aluresult_pcmux", "pcnext", "pcen"]
        add("MEM", 0, D["mem"], "IF")
        add("ALU", 0, D["alu"], "IF")
    elif s == "S1":
        comps += ["IR", "RF", "A", "B", "SIGNEXT", "SL2", "SRCAMUX", "SRCBMUX", "ALU", "ALUOUT"]
        wires += ["ir_ctrl", "ir_a1", "ir_a2", "rd1_a", "rd2_b", "ir_imm", "signimm_sl2",
                  "sl2_srcb", "pc_srca", "srca", "srcb", "aluresult_aluout"]
        add("RF", 0, D["rf"], "ID")
        add("ALU", 0, D["alu"], "ID")
    elif s in ("S2", "S9"):
        comps += ["IR", "A", "SIGNEXT", "SRCAMUX", "SRCBMUX", "ALU", "ALUOUT"]
        wires += ["ir_imm", "signimm_srcb", "a_srca", "srca", "srcb", "aluresult_aluout"]
        add("ALU", 0, D["alu"], "EX")
    elif s == "S6":
        comps += ["A", "B", "SRCAMUX", "SRCBMUX", "ALU", "ALUOUT"]
        wires += ["a_srca", "b_srcb", "srca", "srcb", "aluresult_aluout"]
        add("ALU", 0, D["alu"], "EX")
    elif s == "S8":
        comps += ["A", "B", "SRCAMUX", "SRCBMUX", "ALU", "AND", "PCMUX", "ALUOUT"]
        wires += ["a_srca", "b_srcb", "srca", "srcb", "zero_and", "branch_and", "pcen",
                  "aluout_pcmux", "pcnext"]
        add("ALU", 0, D["alu"], "EX")
    elif s == "S3":
        comps += ["ALUOUT", "IORDMUX", "MEM", "DATA"]
        wires += ["aluout_iord", "iord_adr", "mem_data"]
        add("MEM", 0, D["mem"], "MEM")
    elif s == "S5":
        comps += ["ALUOUT", "IORDMUX", "MEM", "B"]
        wires += ["aluout_iord", "iord_adr", "b_wd"]
        add("MEM", 0, D["mem"], "MEM")
    elif s in ("S4", "S7", "S10"):
        comps += ["IR", "REGDSTMUX", "RESMUX", "RF"]
        wires += ["writereg", "result_wd3"]
        wires += ["ir_rd_wr"] if s == "S7" else ["ir_rt_wr"]
        if s == "S4":
            comps += ["DATA"]
            wires += ["data_res"]
        else:
            comps += ["ALUOUT"]
            wires += ["aluout_res"]
        add("RF_W", 0, D["rf"], "WB")
    used = max(e["end"] for e in ev)
    return sorted(set(comps)), sorted(set(wires)), ev, used


def build():
    prog = assemble(PROGRAM, BASE_PC)
    word_at = {p["addr"]: p["word"] for p in prog}
    text_at = {p["addr"]: (i + 1, p["text"]) for i, p in enumerate(prog)}
    regs, dmem = initial_state()
    # unified memory: instructions + data (byte address -> word)
    mem = dict(word_at)
    for a, v in dmem.items():
        if a in mem:
            raise ValueError("data overlaps program")
        mem[a] = v

    # cycle time: longest work of any state
    period = max(state_work(s, signals(s), None)[3] for s in FSM)

    PC, IR, DATA, A, B, ALUOUT = BASE_PC, 0, 0, 0, 0, 0
    state = "S0"
    steps, cur, n_instr = [], None, 0
    while True:
        if state == "S0":
            if PC not in word_at:
                break
            n_instr += 1
            cur = {"pc": PC, "index": text_at[PC][0], "text": text_at[PC][1], "n": n_instr}
            if n_instr > 200:
                raise RuntimeError("runaway")
        c = signals(state)
        d = decode(IR if state != "S0" else mem[PC])   # S0: control does not depend on IR
        dIR = decode(IR)
        # --- combinational ---
        adr = ALUOUT if sel(c["IorD"]) == 1 else PC
        rd = mem.get(adr, 0)
        rd1, rd2 = regs[dIR.rs], regs[dIR.rt]
        signimm = dIR.imm & MASK32
        srca = A if sel(c["ALUSrcA"]) == 1 else PC
        srcb = {0: B, 1: 4, 2: signimm, 3: (signimm << 2) & MASK32}[sel(c["ALUSrcB"])]
        op = alu_op(c["ALUOp"], dIR.funct) if c["ALUOp"] != "X" else None
        aluresult = alu_r(op, srca, srcb) if op else alu_r("add", srca, srcb)
        zero = int(aluresult == 0)
        pcnext = ALUOUT if sel(c["PCSrc"]) == 1 else aluresult
        pcen = c["PCWrite"] | (c["Branch"] & zero)
        writereg = None if c["RegDst"] == "X" else (dIR.rd if c["RegDst"] == 1 else dIR.rt)
        wd3 = None if c["MemtoReg"] == "X" else (DATA if c["MemtoReg"] == 1 else ALUOUT)

        comps, wires, ev, used = state_work(state, c, op)
        changes = {"regs": {}, "mem": {}, "nonarch": {}}
        # --- clock edge ---
        nPC, nIR = (pcnext if pcen else PC), (rd if c["IRWrite"] else IR)
        nDATA, nA, nB, nALUOUT = rd, rd1, rd2, aluresult
        if c["RegWrite"]:
            if writereg:
                regs[writereg] = wd3
            changes["regs"][reg_name(writereg)] = s32(wd3)
        if c["MemWrite"]:
            mem[adr] = B                        # WD = B register
            changes["mem"][f"0x{adr:02X}"] = s32(B)
        for name, old, new in (("PC", PC, nPC), ("IR", IR, nIR), ("Data", DATA, nDATA), ("A", A, nA),
                               ("B", B, nB), ("ALUOut", ALUOUT, nALUOUT)):
            if old != new:
                changes["nonarch"][name] = f"{new:08X}" if name == "IR" else s32(new)
        before = {"PC": PC, "IR": f"{IR:08X}", "Data": s32(DATA), "A": s32(A), "B": s32(B),
                  "ALUOut": s32(ALUOUT)}
        PC, IR, DATA, A, B, ALUOUT = nPC, nIR, nDATA, nA, nB, nALUOUT
        regs[0] = 0

        steps.append({
            "cycle": len(steps) + 1, "state": state, "state_name": FSM[state]["name"],
            "instr": dict(cur), "class": {OP_RTYPE: "R", OP_ADDI: "I", OP_LW: "LW", OP_SW: "SW",
                                         OP_BEQ: "BEQ"}[decode(mem_word(word_at, cur["pc"])).opcode],
            "control": dict(c, ALUControl=ALUCTL[op] if op else "X"), "alu_op": op,
            "PCEn": pcen, "Zero": zero,
            "regs_before": before,
            "values": {"Adr": adr, "ReadData": s32(rd), "RD1": s32(rd1), "RD2": s32(rd2),
                       "SignImm": dIR.imm, "SrcA": s32(srca), "SrcB": s32(srcb),
                       "ALUResult": s32(aluresult), "PCNext": pcnext,
                       "WriteReg": None if writereg is None else reg_name(writereg),
                       "WD3": None if wd3 is None else s32(wd3)},
            "active": {"components": comps, "wires": wires},
            "timing": {"events": ev, "used": used, "period": period, "waste": period - used},
            "changes": changes,
            "regs_after": {reg_name(i): s32(v) for i, v in enumerate(regs)},
            "mem_after": {f"0x{a:02X}": s32(mem.get(a, 0)) for a in sorted(dmem)},
            "nonarch_after": {"PC": PC, "IR": f"{IR:08X}", "Data": s32(DATA), "A": s32(A), "B": s32(B),
                              "ALUOut": s32(ALUOUT)},
        })
        state = next_state(state, d.opcode)

    per_instr = {}
    for s in steps:
        per_instr.setdefault(s["instr"]["n"], []).append(s["state"])
    trace = {
        "video": "inorder/multi_cycle",
        "config": {
            "delays_ps": DELAYS, "delays_source": "L10 slide 90 (single-cycle analysis, last page of deck B)",
            "period_ps": period, "alu_control_encoding": ALUCTL, "fsm": FSM,
            "assumptions": ASSUMPTIONS,
            "program": [{"addr": p["addr"], "word": f"{p['word']:08X}", "text": p["text"], "reason": r}
                        for p, r in zip(prog, REASONS)],
            "init_regs": INIT_REGS, "init_mem": {f"0x{a:02X}": v for a, v in INIT_MEM.items()},
            "show_regs": SHOW_REGS, "show_mem": [f"0x{a:02X}" for a in SHOW_MEM],
        },
        "steps": steps,
        "instr_states": [{"n": n, "pc": next(s["instr"]["pc"] for s in steps if s["instr"]["n"] == n),
                          "states": v} for n, v in per_instr.items()],
        "final": {"regs": {reg_name(i): s32(v) for i, v in enumerate(regs)},
                  "mem": {f"0x{a:02X}": s32(mem.get(a, 0)) for a in sorted(dmem)},
                  "cycles": len(steps), "instructions": n_instr,
                  "cpi": len(steps) / n_instr, "total_ps": len(steps) * period},
    }
    return trace


def main():
    trace = build()
    steps, period, n_instr = trace["steps"], trace["config"]["period_ps"], trace["final"]["instructions"]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(trace, indent=1, ensure_ascii=False))
    print(f"wrote {OUT.relative_to(ROOT)}: {n_instr} instructions, {len(steps)} cycles x {period} ps "
          f"= {len(steps) * period} ps (CPI {len(steps) / n_instr:.2f})")


def mem_word(word_at, pc):
    return word_at[pc]


if __name__ == "__main__":
    main()
