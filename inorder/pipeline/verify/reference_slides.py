"""Reference data transcribed by hand from the slide *images* of
inorder/slides/C_pipeline_slides.pdf (read at 60–200 dpi).

PDF page -> printed slide number (as printed on each page; deck mixes lectures):
  1 Pipeline Registers, 2 -> 111, 3 -> 112, 4 -> 17, 5 -> 18, 6 -> 19, 7 -> 20, 8 -> 21, 9 -> 22,
  10 -> 37, 11 RAW example, 12 -> stall, 13-16 data forwarding (locations, datapath, implementation, pseudocode),
  17-20 forwarding not always possible / stall / detection hardware / control dependence (60),
  21 -> 61 branch prediction, 22 -> 62, 23 -> 63 flush on misprediction, 24 -> 64 early branch,
  25 -> 65 early branch resolution, 26 -> 69 hazard control code, 27 -> 79 final processor (Fig. 7.58),
  28 title, 29-32 -> 80-83 performance example, 33 -> 85 final processor, 34 -> 86 delays/Tc,
  35 -> 87 exec time, 36 performance summary
"""

# PDF p.16 "Data Forwarding (in Pseudocode)" — ForwardAE (ForwardBE: rtE instead of rsE)
#   if ((rsE != 0) AND (rsE == WriteRegM) AND RegWriteM) ForwardAE = 10   # from Memory stage
#   else if ((rsE != 0) AND (rsE == WriteRegW) AND RegWriteW) ForwardAE = 01   # from Writeback
#   else ForwardAE = 00
#
# PDF p.26 (slide 69), verbatim:
#   ForwardAD = (rsD != 0) & (rsD == WriteRegM) & RegWriteM;
#   ForwardBD = (rtD != 0) & (rtD == WriteRegM) & RegWriteM;
#   lwstall = ((rsD == rtE) | (rtD == rtE)) & MemtoRegE;
#   branchstall = (BranchD & RegWriteE & (WriteRegE == rsD | WriteRegE == rtD))
#               | (BranchD & MemtoRegM & (WriteRegM == rsD | WriteRegM == rtD));
#   StallF = StallD = FlushE = lwstall | branchstall;
#
# PDF p.27 (slide 79, Fig. 7.58): PC EN = ~StallF; IF/ID EN = ~StallD, CLR = PCSrcD;
#   ID/EX CLR = FlushE; PCSrcD = BranchD & EqualD; PC' = PCSrcD ? PCBranchD : PCPlus4F.
#   "Includes always-not-taken br prediction, early branch resolution, forwarding, stall logic"
# PDF p.25 (slide 65): early branch resolution -> a taken beq flushes 1 instruction.
# PDF p.7 (slide 20): same control unit as the single-cycle processor, delayed per stage.

# The hazards the common program was designed to contain, and how the slide-69
# hardware must resolve each (instruction numbers = program lines I1..I10).
EXPECTED_EVENTS = [
    ("lwstall", 1, 2, "$t0"),      # lw then immediate use -> 1 stall (slide 18/66 "Stalling necessary")
    ("fwd_WB_EX", 1, 2, "$t0"),    # after the stall the loaded value is forwarded from WB
    ("fwd_MEM_EX", 2, 3, "$t1"),   # distance 1
    ("fwd_WB_EX", 2, 4, "$t1"),    # distance 2
    ("rf_half", 2, 5, "$t1"),      # distance 3: written in 1st half, read in 2nd half (no forwarding)
    ("rf_half", 4, 7, "$t3"),      # beq operand, distance 3
    ("flush", 7, 8, None),         # taken beq resolved in Decode flushes the next fetched instruction
]
FORBIDDEN = ["branchstall"]        # beq operands are computed early enough

# PDF p.34 (slide 86) table and Tc — a DIFFERENT delay set (H&H Table 7.6), for reference only
SLIDE86 = {"tpcq_PC": 30, "tsetup": 20, "tmux": 25, "tALU": 200, "tmem": 250, "tRFread": 150,
           "tRFsetup": 20, "teq": 40, "tAND": 15, "tmemwrite": 220, "tRFwrite": 100}
SLIDE86_TC = 550   # = 2*(150 + 25 + 40 + 15 + 25 + 20)

# L10 90 delays used in videos 1 and 2
DELAYS_REF = {"mem": 200, "alu": 100, "adder": 100, "rf": 50, "other": 0}
