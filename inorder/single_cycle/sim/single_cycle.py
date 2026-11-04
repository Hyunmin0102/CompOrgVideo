"""Single-cycle MIPS simulator (H&H Fig. 7.11 style, without jump).

Writes inorder/single_cycle/out/trace.json:
  config   : delays (L10 slide 90), clock period, assumptions, program, initial state
  steps[]  : one per executed instruction = one clock cycle
             control signals, datapath values, active components/wires,
             timing events (ps), latency and wasted time, state changes
  final    : final architectural state

    python3 inorder/single_cycle/sim/single_cycle.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from inorder.shared.isa import (MASK32, OP_ADDI, OP_BEQ, OP_LW, OP_RTYPE, OP_SW,  # noqa: E402
                                assemble, decode, reg_name, s32)
from inorder.shared.interpreter import alu_r, initial_state  # noqa: E402
from inorder.shared.program import (BASE_PC, INIT_MEM, INIT_REGS, PROGRAM,  # noqa: E402
                                    REASONS, SHOW_MEM, SHOW_REGS)

OUT = ROOT / "inorder" / "single_cycle" / "out" / "trace.json"

# --- L10 slide 90 (PDF p.15): component delays in ps --------------------------
DELAYS = {"mem": 200, "alu": 100, "adder": 100, "rf": 50, "other": 0}

# H&H ALUControl encoding (H&H Table 7.1) -- slides only name the operation.
ALUCTL = {"add": "010", "sub": "110", "and": "000", "or": "001", "slt": "111"}

ASSUMPTIONS = [
    "ALUControl의 3비트 값(add=010, sub=110, and=000, or=001, slt=111)은 H&H 7장 표를 따름. "
    "슬라이드(L10 56–61)에는 funct/opcode/Add/bcond라는 연산 이름만 있음.",
    "beq의 비교(bcond)는 H&H처럼 ALU 뺄셈(sub) 후 Zero 신호로 판단함.",
    "분기 목표 덧셈기는 부호 확장된 즉치값이 준비된 뒤(200ps) 시작해 300ps에 끝난다고 계산함. "
    "슬라이드 L10 95의 그림은 이 지점을 200ps로 표시하지만, beq 전체 350ps에는 영향 없음.",
    "단순화한 데이터패스에는 j(jump) 경로를 그리지 않음 (공통 프로그램에서 j를 쓰지 않음).",
]


def control(d):
    """Main decoder + ALU decoder (H&H Tables 7.2/7.3).  'X' = don't care."""
    op = d.opcode
    if op == OP_RTYPE:
        c = dict(RegWrite=1, RegDst=1, ALUSrc=0, Branch=0, MemWrite=0, MemtoReg=0)
        alu = d.mnemonic
    elif op == OP_ADDI:
        c = dict(RegWrite=1, RegDst=0, ALUSrc=1, Branch=0, MemWrite=0, MemtoReg=0)
        alu = "add"
    elif op == OP_LW:
        c = dict(RegWrite=1, RegDst=0, ALUSrc=1, Branch=0, MemWrite=0, MemtoReg=1)
        alu = "add"
    elif op == OP_SW:
        c = dict(RegWrite=0, RegDst="X", ALUSrc=1, Branch=0, MemWrite=1, MemtoReg="X")
        alu = "add"
    elif op == OP_BEQ:
        c = dict(RegWrite=0, RegDst="X", ALUSrc=0, Branch=1, MemWrite=0, MemtoReg="X")
        alu = "sub"
    else:
        raise ValueError(f"opcode {op:#x} not supported")
    c["ALUControl"] = ALUCTL[alu]
    return c, alu


def klass(d):
    return {OP_RTYPE: "R", OP_ADDI: "I", OP_LW: "LW", OP_SW: "SW", OP_BEQ: "BEQ"}[d.opcode]


# --- which parts of the datapath an instruction uses ---------------------------
ALWAYS_C = ["PC", "IMEM", "ADD4", "CTRL", "PCMUX"]
ALWAYS_W = ["pc_imem", "pc_add4", "four_add4", "instr_ctrl", "pcnext"]


def active_parts(k, taken):
    comps, wires = list(ALWAYS_C), list(ALWAYS_W)
    if k in ("R", "I", "LW", "SW", "BEQ"):
        comps += ["RF", "ALU"]
        wires += ["instr_a1", "rd1_srca", "srcb", ]
    if k in ("R", "SW", "BEQ"):
        wires += ["instr_a2"]
    if k in ("R", "BEQ"):
        wires += ["rd2_alusrc"]
    if k in ("I", "LW", "SW"):
        comps += ["SIGNEXT"]
        wires += ["instr_imm", "signimm_alusrc"]
    comps += ["ALUSRCMUX"]
    if k in ("R", "I", "LW"):
        comps += ["REGDSTMUX", "RESMUX"]
        wires += ["writereg", "result_wd3"]
        wires += ["instr_rd_wr"] if k == "R" else ["instr_rt_wr"]
    if k in ("R", "I"):
        wires += ["aluresult_res"]
    if k in ("LW", "SW"):
        comps += ["DMEM"]
        wires += ["aluresult_addr"]
    if k == "LW":
        wires += ["readdata_res"]
    if k == "SW":
        wires += ["instr_a2", "rd2_wd"]
    if k == "BEQ":
        comps += ["SIGNEXT", "SL2", "ADDBR", "AND"]
        wires += ["instr_imm", "signimm_sl2", "sl2_addbr", "pcplus4_addbr", "zero_and", "branch_and",
                  "pcsrc"]
        wires += ["pcbranch"] if taken else ["pcplus4_pcmux"]
    else:
        wires += ["pcplus4_pcmux"]
    return sorted(set(comps)), sorted(set(wires))


# --- timing: signal arrival along the used path (ps) ---------------------------
def timing(k):
    D = DELAYS
    ev = []   # (component, stage, start, end)

    def add(c, stage, s, dur):
        ev.append({"comp": c, "stage": stage, "start": s, "end": s + dur})
        return s + dur

    t_pc4 = add("ADD4", "IF", 0, D["adder"])
    t_ins = add("IMEM", "IF", 0, D["mem"])
    t_rf = add("RF", "ID", t_ins, D["rf"])                    # register read
    t_imm = t_ins + D["other"]                                 # sign extend (0 ps)
    srcb = t_imm if k in ("I", "LW", "SW") else t_rf
    t_alu = add("ALU", "EX", max(t_rf, srcb), D["alu"])
    pc_ready = t_pc4
    if k == "BEQ":
        t_br = add("ADDBR", "EX", max(t_pc4, t_imm), D["adder"])
        pc_ready = max(t_alu, t_br)                            # Zero & Branch -> PCSrc mux
    res = t_alu
    if k in ("LW", "SW"):
        res = add("DMEM", "MEM", t_alu, D["mem"])
    if k in ("R", "I", "LW"):
        res = add("RF_W", "WB", res, D["rf"])                  # register write
    latency = max(pc_ready, res, *(e["end"] for e in ev))
    return ev, latency


def arrival(k, ev, latency):
    """When the signal on each wire becomes valid, and when each component is
    busy ([start, end] list; zero-delay parts have start == end)."""
    end = {}
    for e in ev:
        end.setdefault(e["comp"], e["end"])
    t_ins, t_rf, t_alu = end["IMEM"], end["RF"], end["ALU"]
    t_srcb = t_ins if k in ("I", "LW", "SW") else t_rf
    t_res = end.get("DMEM", t_alu)
    t_pc = max(t_alu, end["ADDBR"]) if k == "BEQ" else end["ADD4"]
    w = {"pc_imem": 0, "pc_add4": 0, "four_add4": 0,
         "pcplus4_pcmux": end["ADD4"], "pcplus4_addbr": end["ADD4"],
         "instr_ctrl": t_ins, "instr_a1": t_ins, "instr_a2": t_ins, "instr_rt_wr": t_ins,
         "instr_rd_wr": t_ins, "instr_imm": t_ins, "writereg": t_ins, "branch_and": t_ins,
         "signimm_alusrc": t_ins, "signimm_sl2": t_ins, "sl2_addbr": t_ins,
         "rd1_srca": t_rf, "rd2_alusrc": t_rf, "rd2_wd": t_rf, "srcb": t_srcb,
         "aluresult_addr": t_alu, "aluresult_res": t_alu, "zero_and": t_alu, "pcsrc": t_alu,
         "pcbranch": end.get("ADDBR"), "readdata_res": end.get("DMEM"), "result_wd3": t_res,
         "pcnext": t_pc}
    c = {"PC": [[0, 0]], "PCMUX": [[t_pc, t_pc]], "CTRL": [[t_ins, t_ins]],
         "SIGNEXT": [[t_ins, t_ins]], "SL2": [[t_ins, t_ins]], "REGDSTMUX": [[t_ins, t_ins]],
         "ALUSRCMUX": [[t_srcb, t_srcb]], "AND": [[t_alu, t_alu]], "RESMUX": [[t_res, t_res]]}
    for e in ev:
        name = "RF" if e["comp"] == "RF_W" else e["comp"]
        c.setdefault(name, []).append([e["start"], e["end"]])
    return w, c


def main():
    prog = assemble(PROGRAM, BASE_PC)
    imem = {p["addr"]: p for p in prog}
    regs, mem = initial_state()
    period = max(timing(k)[1] for k in ("R", "I", "LW", "SW", "BEQ"))
    lat_by_class = {k: timing(k)[1] for k in ("R", "I", "LW", "SW", "BEQ")}

    steps, pc = [], BASE_PC
    while pc in imem:
        p = imem[pc]
        d = decode(p["word"])
        c, alu_op = control(d)
        rd1, rd2 = regs[d.rs], regs[d.rt]
        signimm = d.imm & MASK32
        srca = rd1
        srcb = signimm if c["ALUSrc"] == 1 else rd2
        aluresult = alu_r(alu_op, srca, srcb)
        zero = int(aluresult == 0)
        pcplus4 = (pc + 4) & MASK32
        pcbranch = (pcplus4 + (signimm << 2)) & MASK32
        pcsrc = c["Branch"] & zero
        pcnext = pcbranch if pcsrc else pcplus4
        writereg = None if c["RegDst"] == "X" else (d.rd if c["RegDst"] == 1 else d.rt)
        readdata = mem.get(aluresult, 0) if d.opcode == OP_LW else None
        result = None if c["MemtoReg"] == "X" else (readdata if c["MemtoReg"] == 1 else aluresult)

        changes = {"regs": {}, "mem": {}}
        if c["RegWrite"]:
            if writereg != 0:
                regs[writereg] = result
            changes["regs"][reg_name(writereg)] = s32(result)
        if c["MemWrite"]:
            mem[aluresult] = rd2
            changes["mem"][f"0x{aluresult:02X}"] = s32(rd2)

        k = klass(d)
        comps, wires = active_parts(k, bool(pcsrc))
        ev, lat = timing(k)
        wt, ct = arrival(k, ev, lat)
        wt = {n: wt[n] for n in wires}
        ct = {n: ct[n] for n in comps}
        steps.append({
            "cycle": len(steps) + 1, "index": prog.index(p) + 1, "pc": pc, "word": f"{p['word']:08X}",
            "text": p["text"], "mnemonic": d.mnemonic, "class": k,
            "fields": {"opcode": d.opcode, "rs": d.rs, "rt": d.rt, "rd": d.rd, "funct": d.funct,
                       "imm": d.imm},
            "control": c, "alu_op": alu_op, "PCSrc": pcsrc, "Zero": zero,
            "values": {"PCPlus4": pcplus4, "RD1": s32(rd1), "RD2": s32(rd2), "SignImm": d.imm,
                       "SrcA": s32(srca), "SrcB": s32(srcb), "ALUResult": s32(aluresult),
                       "ReadData": None if readdata is None else s32(readdata),
                       "WriteData": s32(rd2) if c["MemWrite"] else None,
                       "WriteReg": None if writereg is None else reg_name(writereg),
                       "Result": None if result is None else s32(result),
                       "PCBranch": pcbranch, "PCNext": pcnext},
            "active": {"components": comps, "wires": wires},
            "timing": {"events": ev, "latency": lat, "period": period, "waste": period - lat,
                       "wire_ps": wt, "comp_ps": ct},
            "changes": changes,
            "regs_after": {n: s32(regs[i]) for i, n in enumerate(map(reg_name, range(32)))},
            "mem_after": {f"0x{a:02X}": s32(v) for a, v in sorted(mem.items())},
        })
        pc = pcnext

    trace = {
        "video": "inorder/single_cycle",
        "config": {
            "delays_ps": DELAYS, "delays_source": "L10 slide 90 (PDF p.15)",
            "period_ps": period, "latency_by_class": lat_by_class,
            "alu_control_encoding": ALUCTL, "assumptions": ASSUMPTIONS,
            "program": [{"addr": p["addr"], "word": f"{p['word']:08X}", "text": p["text"],
                         "reason": r} for p, r in zip(prog, REASONS)],
            "init_regs": INIT_REGS, "init_mem": {f"0x{a:02X}": v for a, v in INIT_MEM.items()},
            "show_regs": SHOW_REGS, "show_mem": [f"0x{a:02X}" for a in SHOW_MEM],
        },
        "steps": steps,
        "final": {"regs": {reg_name(i): s32(v) for i, v in enumerate(regs)},
                  "mem": {f"0x{a:02X}": s32(v) for a, v in sorted(mem.items())},
                  "cycles": len(steps), "total_ps": len(steps) * period},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(trace, indent=1, ensure_ascii=False))
    print(f"wrote {OUT.relative_to(ROOT)}: {len(steps)} cycles x {period} ps = {len(steps) * period} ps")


if __name__ == "__main__":
    main()
