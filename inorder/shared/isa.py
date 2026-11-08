"""MIPS subset used by all three inorder videos (single-cycle, multi-cycle, pipeline).

Only the instructions on the lecture slides: add, sub, and, or, slt, addi, lw, sw, beq.
(j exists on the slides but is not in the final H&H pipeline, so it is excluded.)

The assembler produces real 32-bit machine words; every simulator decodes those
bits (opcode/funct/rs/rt/rd/imm), it never looks at the mnemonic text.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# --------------------------------------------------------------- registers ---
REG_NAMES = ["$0", "$at", "$v0", "$v1", "$a0", "$a1", "$a2", "$a3",
             "$t0", "$t1", "$t2", "$t3", "$t4", "$t5", "$t6", "$t7",
             "$s0", "$s1", "$s2", "$s3", "$s4", "$s5", "$s6", "$s7",
             "$t8", "$t9", "$k0", "$k1", "$gp", "$sp", "$fp", "$ra"]
REG_NUM = {n: i for i, n in enumerate(REG_NAMES)}
REG_NUM["$zero"] = 0

# ------------------------------------------------------------------ opcodes ---
OP_RTYPE, OP_LW, OP_SW, OP_BEQ, OP_ADDI = 0x00, 0x23, 0x2B, 0x04, 0x08
FUNCT = {"add": 0x20, "sub": 0x22, "and": 0x24, "or": 0x25, "slt": 0x2A}
FUNCT_NAME = {v: k for k, v in FUNCT.items()}
OPCODE = {"lw": OP_LW, "sw": OP_SW, "beq": OP_BEQ, "addi": OP_ADDI}
SUPPORTED = set(FUNCT) | set(OPCODE)

MASK32 = 0xFFFFFFFF


def s32(x: int) -> int:
    x &= MASK32
    return x - (1 << 32) if x & 0x80000000 else x


def sext16(x: int) -> int:
    x &= 0xFFFF
    return x - 0x10000 if x & 0x8000 else x


@dataclass(frozen=True)
class Decoded:
    word: int
    opcode: int
    rs: int
    rt: int
    rd: int
    funct: int
    imm: int          # sign-extended

    @property
    def mnemonic(self) -> str:
        if self.opcode == OP_RTYPE:
            return FUNCT_NAME[self.funct]
        return {OP_LW: "lw", OP_SW: "sw", OP_BEQ: "beq", OP_ADDI: "addi"}[self.opcode]


def decode(word: int) -> Decoded:
    return Decoded(word=word, opcode=(word >> 26) & 0x3F, rs=(word >> 21) & 0x1F,
                   rt=(word >> 16) & 0x1F, rd=(word >> 11) & 0x1F, funct=word & 0x3F,
                   imm=sext16(word & 0xFFFF))


def _reg(tok: str) -> int:
    tok = tok.strip()
    if tok not in REG_NUM:
        raise ValueError(f"unknown register {tok}")
    return REG_NUM[tok]


def assemble(lines: list[str], base: int = 0) -> list[dict]:
    """Two-pass assembler.  Each line: '[label:] mnemonic operands'.
    Returns [{addr, text, label, word}]."""
    parsed, labels = [], {}
    for i, raw in enumerate(lines):
        line = raw.split("#")[0].strip()
        label = None
        if ":" in line:
            label, line = (s.strip() for s in line.split(":", 1))
            labels[label] = base + 4 * i
        parsed.append((label, line))
    out = []
    for i, (label, line) in enumerate(parsed):
        addr = base + 4 * i
        m, _, ops = line.partition(" ")
        ops = [o.strip() for o in ops.split(",")]
        if m not in SUPPORTED:
            raise ValueError(f"instruction {m} is not in the slide subset")
        if m in FUNCT:                      # rd, rs, rt
            rd, rs, rt = map(_reg, ops)
            w = (OP_RTYPE << 26) | (rs << 21) | (rt << 16) | (rd << 11) | FUNCT[m]
        elif m == "addi":                   # rt, rs, imm
            rt, rs, imm = _reg(ops[0]), _reg(ops[1]), int(ops[2], 0)
            w = (OP_ADDI << 26) | (rs << 21) | (rt << 16) | (imm & 0xFFFF)
        elif m in ("lw", "sw"):             # rt, imm(rs)
            mm = re.fullmatch(r"(-?\w+)\((\$\w+)\)", ops[1])
            rt, imm, rs = _reg(ops[0]), int(mm.group(1), 0), _reg(mm.group(2))
            w = (OPCODE[m] << 26) | (rs << 21) | (rt << 16) | (imm & 0xFFFF)
        else:                               # beq rs, rt, label
            rs, rt = _reg(ops[0]), _reg(ops[1])
            off = (labels[ops[2]] - (addr + 4)) // 4
            w = (OP_BEQ << 26) | (rs << 21) | (rt << 16) | (off & 0xFFFF)
        out.append({"addr": addr, "text": line, "label": label, "word": w})
    return out


def reg_name(n: int) -> str:
    return REG_NAMES[n]
