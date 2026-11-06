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
# Which register updates are the purpose of each state (H&H 7.4 text).  A, B,
# Data and ALUOut also load in every other cycle, but those values are not used.
INTENDED = {"S0": ["IR", "PC"], "S1": ["A", "B", "ALUOut"], "S2": ["ALUOut"], "S3": ["Data"],
            "S4": ["RF"], "S5": ["MEM"], "S6": ["ALUOut"], "S7": ["RF"], "S8": ["PC"],
            "S9": ["ALUOut"], "S10": ["RF"]}

# wire -> (source component, destination component) for arrival-time computation
WIRE_ENDS = {
    "pcnext": ("PCMUX", "PC"), "pc_iord": ("PC", "IORDMUX"), "pc_srca": ("PC", "SRCAMUX"),
    "iord_adr": ("IORDMUX", "MEM"), "aluout_iord": ("ALUOUT", "IORDMUX"), "mem_ir": ("MEM", "IR"),
    "mem_data": ("MEM", "DATA"), "b_wd": ("B", "MEM"), "ir_ctrl": ("IR", "CTRL"), "ir_a1": ("IR", "RF"),
    "ir_a2": ("IR", "RF"), "ir_rt_wr": ("IR", "REGDSTMUX"), "ir_rd_wr": ("IR", "REGDSTMUX"),
    "ir_imm": ("IR", "SIGNEXT"), "writereg": ("REGDSTMUX", "RF_W"), "data_res": ("DATA", "RESMUX"),
    "aluout_res": ("ALUOUT", "RESMUX"), "result_wd3": ("RESMUX", "RF_W"), "rd1_a": ("RF", "A"),
    "rd2_b": ("RF", "B"), "a_srca": ("A", "SRCAMUX"), "b_srcb": ("B", "SRCBMUX"),
    "four_srcb": ("CONST", "SRCBMUX"), "signimm_srcb": ("SIGNEXT", "SRCBMUX"),
    "signimm_sl2": ("SIGNEXT", "SL2"), "sl2_srcb": ("SL2", "SRCBMUX"), "srca": ("SRCAMUX", "ALU"),
    "srcb": ("SRCBMUX", "ALU"), "aluresult_aluout": ("ALU", "ALUOUT"), "aluresult_pcmux": ("ALU", "PCMUX"),
    "aluout_pcmux": ("ALUOUT", "PCMUX"), "zero_and": ("ALU", "AND"), "branch_and": ("CTRL", "AND"),
    "pcwrite_or": ("CTRL", "OR"), "and_or": ("AND", "OR"), "pcen": ("OR", "PC")}
SOURCES = {"PC", "IR", "A", "B", "ALUOUT", "DATA", "CTRL", "CONST"}   # valid at the start of the cycle
COMP_DELAY = {"MEM": DELAYS["mem"], "ALU": DELAYS["alu"], "RF": DELAYS["rf"], "RF_W": DELAYS["rf"]}


def arrival(wires):
    """Signal-valid time of every used wire and busy interval of every used part (ps)."""
    end = {}

    def t_end(comp):
        if comp in SOURCES:
            return 0
        if comp not in end:
            ins = [w for w in wires if WIRE_ENDS[w][1] == comp]
            start = max((t_end(WIRE_ENDS[w][0]) for w in ins), default=0)
            end[comp] = (start, start + COMP_DELAY.get(comp, 0))
        return end[comp][1]
    w_ps = {w: t_end(WIRE_ENDS[w][0]) for w in wires}
    for w in wires:                      # parts that only receive (RF_W, IR, DATA ...)
        d = WIRE_ENDS[w][1]
        if d not in SOURCES:
            t_end(d)
    c_ps = {k: [list(v)] for k, v in end.items()}
    for k in sorted(SOURCES - {"CONST"}):
        ins = [w_ps[w] for w in wires if WIRE_ENDS[w][1] == k]
        iv = [[0, 0]] if any(WIRE_ENDS[w][0] == k for w in wires) or not ins else []
        if ins:                             # a register lights up again when its new input arrives
            iv.append([max(ins), max(ins)])
        c_ps[k] = iv
    return w_ps, c_ps


TARGET_COMP = {"PC": "PC", "IR": "IR", "A": "A", "B": "B", "ALUOut": "ALUOUT", "Data": "DATA",
               "RF": "RF_W", "MEM": "MEM"}
STOP = SOURCES          # back-tracing stops at registers / control / constants


def jobs_of(wires, intended):
    """Split a state's work into one job per intended write: the wires that feed
    that destination (traced backwards), each with a causal hop number
    (0 = leaves a register, n = n parts after it).  Wires that feed no intended
    write (e.g. the opcode going to the control unit) join the first job."""
    hop = {}

    def h(w):
        if w not in hop:
            src = WIRE_ENDS[w][0]
            ins = [x for x in wires if WIRE_ENDS[x][1] == src] if src not in STOP else []
            hop[w] = 1 + max((h(x) for x in ins), default=-1)
        return hop[w]
    for w in wires:
        h(w)
    out, taken = [], set()
    groups = []                          # A and B are read together (same register-file read)
    for tgt in intended:
        if tgt == "B" and ["A"] in groups:
            groups[groups.index(["A"])] = ["A", "B"]
        else:
            groups.append([tgt])
    for grp in groups:
        tgt = ",".join(grp)
        dests = [TARGET_COMP[g] for g in grp]
        js, todo = set(), [w for w in wires if WIRE_ENDS[w][1] in dests]
        while todo:
            w = todo.pop()
            if w in js:
                continue
            js.add(w)
            src = WIRE_ENDS[w][0]
            if src not in STOP:
                todo += [x for x in wires if WIRE_ENDS[x][1] == src]
        out.append({"target": tgt, "wires": sorted(js, key=lambda w: (hop[w], w))})
        taken |= js
    rest = [w for w in wires if w not in taken]
    if rest:
        if not out:
            out.append({"target": None, "wires": []})
        out[0]["wires"] = sorted(set(out[0]["wires"]) | set(rest), key=lambda w: (hop[w], w))
    for j in out:
        comps = []
        for w in j["wires"]:
            for c in WIRE_ENDS[w]:
                if c not in comps and c != "CONST":
                    comps.append(c)
        j["comps"] = comps
    return out, hop


def state_work(s, c, op_name):
    D = DELAYS
    comps, wires, ev = ["PC", "CTRL"], [], []

    def add(comp, start, dur, stage):
        ev.append({"comp": comp, "stage": stage, "start": start, "end": start + dur})
        return start + dur
    if s == "S0":
        comps += ["IORDMUX", "MEM", "IR", "SRCAMUX", "SRCBMUX", "ALU", "PCMUX", "OR"]
        wires += ["pc_iord", "iord_adr", "mem_ir", "pc_srca", "four_srcb", "srca", "srcb",
                  "aluresult_pcmux", "pcnext", "pcwrite_or", "pcen"]
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
        comps += ["A", "B", "SRCAMUX", "SRCBMUX", "ALU", "AND", "OR", "PCMUX", "ALUOUT"]
        wires += ["a_srca", "b_srcb", "srca", "srcb", "zero_and", "branch_and", "and_or", "pcen",
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
        w_ps, c_ps = arrival(wires)
        intended = INTENDED[state] if state != "S8" or pcen else []
        jobs, hops = jobs_of(wires, intended)
        if max([used] + list(w_ps.values())) != used:
            raise RuntimeError(f"{state}: wire timing exceeds state work")
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
            "timing": {"events": ev, "used": used, "period": period, "waste": period - used,
                       "wire_ps": w_ps, "comp_ps": {k: v for k, v in c_ps.items()
                                                    if k in comps or k == "RF_W"}},
            "intended": intended, "jobs": jobs, "wire_hop": hops,
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
            "wire_ends": {w: list(v) for w, v in WIRE_ENDS.items()},
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
