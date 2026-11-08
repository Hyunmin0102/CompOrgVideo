"""Reference data transcribed by hand from the slide *images*
(inorder/slides/A_single_cycle_slides.pdf, read as 130–260 dpi page images).

Mux selections on L10 56–61 are drawn as red slashes over the input that passes
through; 'X' on a mux / a value = don't care.  Data-memory top number = MemWrite,
bottom number = MemRead.
"""

# PDF page -> lecture slide
PAGES = {5: "L10 56 R-Type ALU", 6: "L10 57 I-Type ALU", 7: "L10 58 LW", 8: "L10 59 SW",
         9: "L10 60 Branch (Not Taken)", 10: "L10 61 Branch (Taken)"}

# per instruction class: values read off the figure.
#   ALUop: the red label on 'ALU control' ("funct", "opcode", "Add", "bcond")
#   PCSrc2: slash on the PCSrc2 (= Br Taken) mux: 0 = PC+4 input, 1 = branch target
CONTROL_REF = {
    "R":         {"page": 5, "RegWrite": 1, "RegDst": 1, "ALUSrc": 0, "MemWrite": 0, "MemRead": 0,
                  "MemtoReg": 0, "PCSrc2": 0, "ALUop": "funct"},
    "I":         {"page": 6, "RegWrite": 1, "RegDst": 0, "ALUSrc": 1, "MemWrite": 0, "MemRead": 0,
                  "MemtoReg": 0, "PCSrc2": 0, "ALUop": "opcode"},
    "LW":        {"page": 7, "RegWrite": 1, "RegDst": 0, "ALUSrc": 1, "MemWrite": 0, "MemRead": 1,
                  "MemtoReg": 1, "PCSrc2": 0, "ALUop": "Add"},
    "SW":        {"page": 8, "RegWrite": 0, "RegDst": "X", "ALUSrc": 1, "MemWrite": 1, "MemRead": 0,
                  "MemtoReg": "X", "PCSrc2": 0, "ALUop": "Add"},
    "BEQ_NT":    {"page": 9, "RegWrite": 0, "RegDst": "X", "ALUSrc": 0, "MemWrite": 0, "MemRead": 0,
                  "MemtoReg": "X", "PCSrc2": 0, "ALUop": "bcond"},
    "BEQ_T":     {"page": 10, "RegWrite": 0, "RegDst": "X", "ALUSrc": 0, "MemWrite": 0, "MemRead": 0,
                  "MemtoReg": "X", "PCSrc2": 1, "ALUop": "bcond"},
}

# PDF p.4 (L10 55) equation: PCSrc2 = (opcode==Bxx) && "bcond is satisfied"
#  -> the Branch control line is 1 exactly for branch opcodes.
BRANCH_EQ = {"R": 0, "I": 0, "LW": 0, "SW": 0, "BEQ_NT": 1, "BEQ_T": 1}

# PDF p.15 / p.22 (L10 90 / 97): delay table
DELAYS_REF = {"mem": 200, "alu": 100, "adder": 100, "rf": 50, "other": 0}
LATENCY_REF = {"R": 400, "I": 400, "LW": 600, "SW": 550, "BEQ": 350}   # Jump 200 not used
# per-step contributions (IF, ID, EX, MEM, WB) from the same table
STEPS_REF = {"R": [200, 50, 100, None, 50], "I": [200, 50, 100, None, 50],
             "LW": [200, 50, 100, 200, 50], "SW": [200, 50, 100, 200, None],
             "BEQ": [200, 50, 100, None, None]}
# PDF p.17–20 (L10 92–95) red-path annotations: cumulative arrival (ps)
ARRIVAL_REF = {"R": {"IMEM": 200, "RF": 250, "ALU": 350, "RF_W": 400},
               "LW": {"IMEM": 200, "RF": 250, "ALU": 350, "DMEM": 550, "RF_W": 600},
               "SW": {"IMEM": 200, "RF": 250, "ALU": 350, "DMEM": 550},
               "BEQ": {"ADD4": 100, "IMEM": 200, "RF": 250, "ALU": 350}}

# Operation name on 'ALU control' -> what the ALU must do for each instruction.
#   funct/opcode: the operation named by the instruction itself; Add: add;
#   bcond: equality compare (implemented as sub + Zero, H&H)
def alu_ref(label, mnemonic):
    if label == "funct":
        return mnemonic
    if label == "opcode":
        return {"addi": "add"}[mnemonic]
    if label == "Add":
        return "add"
    if label == "bcond":
        return "sub"
    raise ValueError(label)
