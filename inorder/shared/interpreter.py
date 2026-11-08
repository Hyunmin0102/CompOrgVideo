"""ISA-level reference interpreter.  The final state it prints is the ground
truth that every microarchitecture simulator (single/multi/pipeline) must match.

    python3 inorder/shared/interpreter.py            # prints final state
    python3 inorder/shared/interpreter.py --json F   # also writes it as JSON
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from inorder.shared.isa import (MASK32, OP_ADDI, OP_BEQ, OP_LW, OP_RTYPE, OP_SW,  # noqa: E402
                                REG_NUM, assemble, decode, reg_name, s32)
from inorder.shared.program import BASE_PC, INIT_MEM, INIT_REGS, PROGRAM  # noqa: E402


def initial_state():
    regs = [0] * 32
    for n, v in INIT_REGS.items():
        regs[REG_NUM[n]] = v & MASK32
    return regs, dict(INIT_MEM)


def alu_r(funct_name, a, b):
    if funct_name == "add":
        return (a + b) & MASK32
    if funct_name == "sub":
        return (a - b) & MASK32
    if funct_name == "and":
        return a & b
    if funct_name == "or":
        return a | b
    if funct_name == "slt":
        return 1 if s32(a) < s32(b) else 0
    raise ValueError(funct_name)


def run(max_steps=1000):
    prog = assemble(PROGRAM, BASE_PC)
    imem = {p["addr"]: p["word"] for p in prog}
    regs, mem = initial_state()
    pc, executed = BASE_PC, []
    while pc in imem:
        if len(executed) >= max_steps:
            raise RuntimeError("step limit (infinite loop?)")
        d = decode(imem[pc])
        a, b = regs[d.rs], regs[d.rt]
        nxt = (pc + 4) & MASK32
        if d.opcode == OP_RTYPE:
            regs[d.rd] = alu_r(d.mnemonic, a, b)
        elif d.opcode == OP_ADDI:
            regs[d.rt] = (a + d.imm) & MASK32
        elif d.opcode == OP_LW:
            regs[d.rt] = mem.get((a + d.imm) & MASK32, 0)
        elif d.opcode == OP_SW:
            mem[(a + d.imm) & MASK32] = b
        elif d.opcode == OP_BEQ:
            if a == b:
                nxt = (pc + 4 + (d.imm << 2)) & MASK32
        regs[0] = 0
        executed.append(pc)
        pc = nxt
    return {"regs": {reg_name(i): s32(v) for i, v in enumerate(regs)},
            "mem": {f"0x{k:02X}": s32(v) for k, v in sorted(mem.items())},
            "executed_pcs": executed, "instr_count": len(executed)}


def main():
    st = run()
    prog = assemble(PROGRAM, BASE_PC)
    print("== program ==")
    for p in prog:
        mark = "" if p["addr"] in st["executed_pcs"] else "   <- not executed"
        print(f"  0x{p['addr']:02X}  {p['word']:08X}  {p['text']}{mark}")
    print(f"== executed {st['instr_count']} instructions ==")
    print("== final registers (non-zero) ==")
    for n, v in st["regs"].items():
        if v:
            print(f"  {n:4s} = {v}")
    print("== final data memory ==")
    for a, v in st["mem"].items():
        print(f"  Mem[{a}] = {v}")
    if "--json" in sys.argv:
        Path(sys.argv[sys.argv.index("--json") + 1]).write_text(json.dumps(st, indent=1))


if __name__ == "__main__":
    main()
