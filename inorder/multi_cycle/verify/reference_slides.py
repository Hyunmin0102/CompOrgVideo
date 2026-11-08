"""Reference data transcribed by hand from the slide *images* of
inorder/slides/B_multi_cycle_slides.pdf (read at 220 dpi).

PDF page -> printed slide number:
  1-12 -> 24-35 (datapath built step by step), 13 -> 36, 14-24 -> 38-48 (control FSM),
  25-28 -> 51-54 (j), 29 -> 57 (datapath review), 30 -> 58 (FSM review),
  31 -> single-cycle analysis table (same as L10 90)

FSM_REF: the text inside each bubble of PDF p.30 (slide 58), exactly as printed.
Signals NOT printed in a bubble are not part of the reference (see ASSUMPTIONS in the sim).
"""

FSM_REF = {
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

# arrows of the same figure: S0 -> S1 always; from S1 by opcode; S2 by opcode; then back to S0
TRANSITIONS_REF = {"LW": ["S0", "S1", "S2", "S3", "S4"],
                   "SW": ["S0", "S1", "S2", "S5"],
                   "R": ["S0", "S1", "S6", "S7"],
                   "BEQ": ["S0", "S1", "S8"],
                   "I": ["S0", "S1", "S9", "S10"]}

# PDF p.29 (slide 57) datapath: SrcB mux inputs 00=B, 01=4, 10=SignImm, 11=SignImm<<2;
# SrcA mux 0=PC, 1=A; IorD mux 0=PC, 1=ALUOut; PC' mux 00=ALUResult, 01=ALUOut, 10=PCJump;
# RegDst mux 0=rt(20:16), 1=rd(15:11); MemtoReg mux 0=ALUOut, 1=Data; PCEn = PCWrite | (Branch & Zero)
SRCB_REF = {"00": "B", "01": "4", "10": "SignImm", "11": "SignImm<<2"}

# PDF p.31 delays (same table as L10 90)
DELAYS_REF = {"mem": 200, "alu": 100, "adder": 100, "rf": 50, "other": 0}
