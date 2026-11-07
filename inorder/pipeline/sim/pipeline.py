"""5-stage pipelined MIPS simulator — H&H Fig. 7.58 (pipeline deck slide 79/85):
always-not-taken branch prediction, early branch resolution in Decode,
forwarding to Execute (MEM->EX, WB->EX) and to Decode (for beq),
lw/branch stalls and flushes exactly as on slide 69.

Cycle model (one clock cycle per loop iteration):
  WB writes the register file in the first half of the cycle, Decode reads it in
  the second half (so a value written in WB is seen by the instruction in D).
  At the clock edge all pipeline registers load, unless stalled (EN=0) or
  cleared (CLR=1):  PC   EN=~StallF
                    D    EN=~StallD, CLR=PCSrcD   (a taken branch flushes the fetched instruction)
                    E    CLR=FlushE               (a stall inserts a bubble)

Writes inorder/pipeline/out/trace.json.

    python3 inorder/pipeline/sim/pipeline.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from inorder.shared.isa import MASK32, assemble, decode, reg_name, s32  # noqa: E402
from inorder.shared.interpreter import alu_r, initial_state  # noqa: E402
from inorder.shared.program import (BASE_PC, INIT_MEM, INIT_REGS, PROGRAM,  # noqa: E402
                                    REASONS, SHOW_MEM, SHOW_REGS)
# slide 20: "Same control unit as single-cycle processor"
from inorder.single_cycle.sim.single_cycle import ALUCTL, control  # noqa: E402

OUT = ROOT / "inorder" / "pipeline" / "out" / "trace.json"
STAGES = ["F", "D", "E", "M", "W"]
DELAYS = {"mem": 200, "alu": 100, "adder": 100, "rf": 50, "other": 0}

ASSUMPTIONS = [
    "클록 주기: 슬라이드 85의 550ps는 다른 지연 표(H&H 표 7.6: 메모리 250, ALU 200 …)로 계산한 값. "
    "1·2편과 비교하려고 같은 L10 90 지연(메모리 200, ALU·덧셈기 100, 레지스터 파일 50, 나머지 0)과 "
    "슬라이드 83의 단계별 식(ID·WB는 반 사이클이라 ×2)을 써서 가장 긴 단계 = 메모리 200ps → 클록 200ps.",
    "제어 유닛과 ALUControl 인코딩은 1편과 같음(슬라이드 20: same control unit as single-cycle). "
    "X(don't care)인 RegDst·MemtoReg는 하드웨어에서 0으로 둠 — 1로 바꿔도 결과가 같음을 검증.",
    "IF/ID 레지스터는 StallD가 1이면 CLR(PCSrcD)보다 유지가 우선(H&H flopenrc). 이 프로그램에서는 둘이 겹치지 않음.",
    "프로그램 끝(0x28) 이후의 fetch는 bubble(nop)로 처리.",
    "j는 공통 프로그램에서 쓰지 않으므로 그리지 않음.",
]

X_DEFAULT = 0


def hw(v):
    return X_DEFAULT if v == "X" else v


NOP_CTL = dict(RegWrite=0, RegDst=0, ALUSrc=0, Branch=0, MemWrite=0, MemtoReg=0, ALUControl="010")


def stage_delay():
    """Slide 83: Tc = max(fetch, 2*(RF read + mux + eq + AND + mux), execute, memory, 2*(RF write))."""
    D = DELAYS
    return {"F": D["mem"], "D": 2 * (D["rf"] + 4 * D["other"]), "E": D["alu"] + 2 * D["other"],
            "M": D["mem"], "W": 2 * (D["rf"] + D["other"])}


# ------------------------------------------------------------------ paths ---
# Causal order of every datapath wire inside its stage (0 = leaves a pipeline
# register / the PC; n = after n parts).  Wire names = inorder/shared/datapath.py PL_WIRES.
PL_HOP = {
    "pc_imem": 0, "pc_add4": 0, "four_add4": 0, "imem_ifid": 1, "pcplus4f_ifid": 1, "pcplus4f_pcmux": 1,
    "pcnext": 2, "h_stallf": 0,
    "instrd_ctrl": 0, "instrd_a1": 0, "instrd_a2": 0, "instrd_rs": 0, "instrd_rt": 0, "instrd_rd": 0,
    "instrd_imm": 0, "pcplus4d_addbr": 0, "fwd_m_fad": 0, "fwd_m_fbd": 0, "h_fwdad": 0, "h_fwdbd": 0,
    "h_stalld": 0, "c_regwrite_d": 1, "c_memtoreg_d": 1, "c_memwrite_d": 1, "c_aluctl_d": 1, "c_alusrc_d": 1,
    "c_regdst_d": 1, "c_branch_d": 1, "rd1_idex": 1, "rd2_idex": 1, "rd1_fad": 1, "rd2_fbd": 1,
    "signimm_idex": 1, "signimm_sl2": 1, "fad_eq": 2, "fbd_eq": 2, "sl2_addbr": 2, "eq_and": 3,
    "pcbranch": 3, "pcsrc": 4, "pcsrc_clr": 4,
    "rd1e_fae": 0, "rd2e_fbe": 0, "fwd_m_fae": 0, "fwd_m_fbe": 0, "fwd_w_fae": 0, "fwd_w_fbe": 0,
    "h_fwdae": 0, "h_fwdbe": 0, "h_flushe": 0, "signimme_alusrc": 0, "rte_rdst": 0, "rde_rdst": 0,
    "c_regwrite_e": 0, "c_memtoreg_e": 0, "c_memwrite_e": 0, "c_aluctl_e": 0, "c_alusrc_e": 0,
    "c_regdst_e": 0, "fae_srca": 1, "fbe_alusrc": 1, "writedatae": 1, "writerege": 1, "srcb": 2,
    "alu_exmem": 3,
    "aluoutm_dmem": 0, "writedatam_dmem": 0, "aluoutm_memwb": 0, "writeregm_memwb": 0, "c_memwrite_m": 0,
    "c_regwrite_m": 0, "c_memtoreg_m": 0, "dmem_memwb": 1,
    "readdataw_mux": 0, "aluoutw_mux": 0, "c_memtoreg_w": 0, "c_regwrite_w": 0, "writeregw_a3": 0,
    "resultw_wd3": 1,
}


def klass(word):
    d = decode(word)
    return {0x00: "R", 0x08: "I", 0x23: "LW", 0x2B: "SW", 0x04: "BEQ"}[d.opcode]


def stage_paths(k, st, word_of):
    """Which wires / parts / timed units each occupied stage uses in cycle st (sim result).
    Delays: WB writes the register file in the first half (0-50 ps), Decode reads it in
    the second half (100-150 ps) — slide 83's x2 for these two stages."""
    D = DELAYS
    half = st["_period"] // 2
    out = {}
    h = st["hazard"]
    for sname, occ_key in (("WB", "W"), ("MEM", "M"), ("EX", "E"), ("ID", "D"), ("IF", "F")):
        i = st["occupancy"][occ_key]
        if i is None:
            continue
        c = klass(word_of[i])
        w, comps, ev = [], [], []
        uses_rt = c in ("R", "SW", "BEQ")
        if sname == "IF":
            w += ["pc_imem", "imem_ifid", "pc_add4", "four_add4", "pcplus4f_ifid"]
            comps += ["PC", "IMEM", "ADD4", "IFID"]
            if not h["StallF"] and not h["PCSrcD"]:
                w += ["pcplus4f_pcmux", "pcnext"]
                comps += ["PCMUX"]
            ev += [{"comp": "IMEM", "start": 0, "end": D["mem"], "after_hop": 0},
                   {"comp": "ADD4", "start": 0, "end": D["adder"], "after_hop": 0}]
        elif sname == "ID":
            ctl = st["D"]["control"]
            w += ["instrd_ctrl", "instrd_a1", "rd1_idex", "instrd_rs", "instrd_rt", "c_aluctl_d"]
            comps += ["IFID", "CTRL", "RF", "IDEX"]
            if uses_rt:
                w += ["instrd_a2", "rd2_idex"]
            if c == "R":
                w += ["instrd_rd"]
            if c in ("I", "LW", "SW", "BEQ"):
                w += ["instrd_imm"]
                comps += ["SIGNEXT"]
            if c in ("I", "LW", "SW"):
                w += ["signimm_idex"]
            for sig, wire in (("RegWrite", "c_regwrite_d"), ("MemtoReg", "c_memtoreg_d"),
                              ("MemWrite", "c_memwrite_d"), ("ALUSrc", "c_alusrc_d"), ("RegDst", "c_regdst_d")):
                if ctl[sig] == 1:
                    w.append(wire)
            ev.append({"comp": "RF", "start": half, "end": half + D["rf"], "after_hop": 0})
            if c == "BEQ":
                w += ["c_branch_d", "rd1_fad", "rd2_fbd", "fad_eq", "fbd_eq", "eq_and", "signimm_sl2",
                      "sl2_addbr", "pcplus4d_addbr", "pcbranch"]
                comps += ["FADMUX", "FBDMUX", "EQ", "AND", "SL2", "ADDBR"]
                ev.append({"comp": "ADDBR", "start": 0, "end": D["adder"], "after_hop": 2})
                if h["PCSrcD"]:
                    w += ["pcsrc", "pcsrc_clr"]
                    comps += ["PCMUX", "PC"]
            if h["ForwardAD"]:
                w += ["fwd_m_fad", "h_fwdad"]
            if h["ForwardBD"]:
                w += ["fwd_m_fbd", "h_fwdbd"]
        elif sname == "EX":
            e = st["E"]
            fa, fb = h["ForwardAE"], h["ForwardBE"]
            w += [{"00": "rd1e_fae", "10": "fwd_m_fae", "01": "fwd_w_fae"}[fa], "fae_srca", "srcb", "alu_exmem",
                  "c_aluctl_e"]
            comps += ["IDEX", "FAEMUX", "ALU", "EXMEM", "ALUSRCMUX"]
            if fa != "00":
                w.append("h_fwdae")
            if uses_rt:
                w.append({"00": "rd2e_fbe", "10": "fwd_m_fbe", "01": "fwd_w_fbe"}[fb])
                comps.append("FBEMUX")
                if fb != "00":
                    w.append("h_fwdbe")
            if c in ("R", "BEQ"):
                w += ["fbe_alusrc"]
            else:
                w += ["signimme_alusrc", "c_alusrc_e"]
            if c == "SW":
                w += ["writedatae", "c_memwrite_e"]
            if c in ("R", "I", "LW"):
                w += ["writerege", "c_regwrite_e"]
                comps.append("REGDSTMUX")
                w += ["rde_rdst", "c_regdst_e"] if c == "R" else ["rte_rdst"]
            if c == "LW":
                w.append("c_memtoreg_e")
            ev.append({"comp": "ALU", "start": 0, "end": D["alu"], "after_hop": 2})
            del e
        elif sname == "MEM":
            comps += ["EXMEM", "MEMWB"]
            if c in ("LW", "SW"):
                w += ["aluoutm_dmem"]
                comps.append("DMEM")
                ev.append({"comp": "DMEM", "start": 0, "end": D["mem"], "after_hop": 0})
            if c == "SW":
                w += ["writedatam_dmem", "c_memwrite_m"]
            if c == "LW":
                w += ["dmem_memwb", "c_memtoreg_m"]
            if c in ("R", "I"):
                w += ["aluoutm_memwb"]
            if c in ("R", "I", "LW"):
                w += ["writeregm_memwb", "c_regwrite_m"]
        else:   # WB
            comps += ["MEMWB"]
            if c in ("R", "I", "LW"):
                w += ["readdataw_mux" if c == "LW" else "aluoutw_mux", "resultw_wd3", "writeregw_a3",
                      "c_regwrite_w"]
                comps += ["RESMUX", "RF"]
                if c == "LW":
                    w.append("c_memtoreg_w")
                ev.append({"comp": "RF_W", "start": 0, "end": D["rf"], "after_hop": 1})
        used = max([e_["end"] for e_ in ev], default=0)
        out[sname] = {"id": i, "class": c, "wires": sorted(set(w), key=lambda x: (PL_HOP[x], x)),
                      "hop": {x: PL_HOP[x] for x in set(w)}, "comps": list(dict.fromkeys(comps)),
                      "timed": ev, "used_ps": used}
    haz = []
    if h["StallF"]:
        haz += ["h_stallf", "h_stalld", "h_flushe"]
    return out, haz


def build():
    prog = assemble(PROGRAM, BASE_PC)
    imem = {p["addr"]: p for p in prog}
    idx = {p["addr"]: i + 1 for i, p in enumerate(prog)}
    regs, mem = initial_state()
    sd = stage_delay()
    period = max(sd.values())

    PC = BASE_PC
    Dr = None          # IF/ID: {"id","pc","word","PCPlus4"}  (None = bubble)
    Er = None          # ID/EX
    Mr = None          # EX/MEM
    Wr = None          # MEM/WB
    steps = []
    for cyc in range(1, 200):
        if Dr is None and Er is None and Mr is None and Wr is None and PC not in imem and cyc > 1:
            break
        occ = {"F": None, "D": Dr and Dr["id"], "E": Er and Er["id"], "M": Mr and Mr["id"], "W": Wr and Wr["id"]}
        ev = []                      # human-readable hazard events this cycle
        changes = {"regs": {}, "mem": {}}

        # ---- WB (first half) ------------------------------------------------
        ResultW = None
        if Wr:
            ResultW = Wr["ReadData"] if Wr["MemtoReg"] else Wr["ALUOut"]
            if Wr["RegWrite"] and Wr["WriteReg"]:
                regs[Wr["WriteReg"]] = ResultW & MASK32
                changes["regs"][reg_name(Wr["WriteReg"])] = s32(ResultW)
        RegWriteW = Wr["RegWrite"] if Wr else 0
        WriteRegW = Wr["WriteReg"] if Wr else 0

        # ---- MEM --------------------------------------------------------------
        ReadDataM = None
        if Mr:
            if Mr["MemtoReg"]:
                ReadDataM = mem.get(Mr["ALUOut"], 0)
        RegWriteM = Mr["RegWrite"] if Mr else 0
        WriteRegM = Mr["WriteReg"] if Mr else 0
        MemtoRegM = Mr["MemtoReg"] if Mr else 0
        ALUOutM = Mr["ALUOut"] if Mr else 0

        # ---- EX (forwarding, slide "Data Forwarding (in Pseudocode)") ----------
        ex = None
        RegWriteE = Er["RegWrite"] if Er else 0
        MemtoRegE = Er["MemtoReg"] if Er else 0
        rtE = Er["Rt"] if Er else 0
        WriteRegE = 0
        if Er:
            def fwd(r):
                if r != 0 and r == WriteRegM and RegWriteM:
                    return "10"
                if r != 0 and r == WriteRegW and RegWriteW:
                    return "01"
                return "00"
            FAE, FBE = fwd(Er["Rs"]), fwd(Er["Rt"])
            pick = {"00": None, "01": ResultW, "10": ALUOutM}
            SrcA = Er["RD1"] if FAE == "00" else pick[FAE]
            WriteDataE = Er["RD2"] if FBE == "00" else pick[FBE]
            SrcB = Er["SignImm"] if Er["ALUSrc"] else WriteDataE
            ALUOutE = alu_r(Er["alu_op"], SrcA, SrcB)
            WriteRegE = Er["Rd"] if Er["RegDst"] else Er["Rt"]
            for name, f, r in (("A", FAE, Er["Rs"]), ("B", FBE, Er["Rt"])):
                if f != "00":
                    src = Mr["id"] if f == "10" else Wr["id"]
                    ev.append({"type": "fwd_MEM_EX" if f == "10" else "fwd_WB_EX", "port": name,
                               "reg": reg_name(r), "from": src, "to": Er["id"],
                               "value": s32(ALUOutM if f == "10" else ResultW)})
            ex = {"ForwardAE": FAE, "ForwardBE": FBE, "SrcAE": s32(SrcA), "SrcBE": s32(SrcB),
                  "WriteDataE": s32(WriteDataE), "ALUOutE": s32(ALUOutE), "WriteRegE": reg_name(WriteRegE)}

        # ---- ID (register read in 2nd half, early branch) ---------------------
        de = None
        if Dr:
            d = decode(Dr["word"])
            ctl, alu = control(d)
            rsD, rtD, rdD = d.rs, d.rt, d.rd
            RD1, RD2 = regs[rsD], regs[rtD]
            FAD = int(rsD != 0 and rsD == WriteRegM and bool(RegWriteM))
            FBD = int(rtD != 0 and rtD == WriteRegM and bool(RegWriteM))
            cA = ALUOutM if FAD else RD1
            cB = ALUOutM if FBD else RD2
            EqualD = int(cA == cB)
            BranchD = ctl["Branch"]
            PCSrcD = BranchD & EqualD
            SignImmD = d.imm & MASK32
            PCBranchD = (Dr["PCPlus4"] + (SignImmD << 2)) & MASK32
            srcs = [rsD] + ([rtD] if ctl["RegDst"] == 1 or ctl["MemWrite"] or BranchD else [])
            for r in srcs:
                if r != 0 and RegWriteW and r == WriteRegW:
                    ev.append({"type": "rf_half", "reg": reg_name(r), "from": Wr["id"], "to": Dr["id"],
                               "value": s32(ResultW)})
            de = {"control": ctl, "alu_op": alu, "rsD": reg_name(rsD), "rtD": reg_name(rtD),
                  "RD1": s32(RD1), "RD2": s32(RD2), "SignImmD": d.imm, "ForwardAD": FAD, "ForwardBD": FBD,
                  "EqualD": EqualD if BranchD else None, "PCSrcD": PCSrcD,
                  "PCBranchD": PCBranchD if BranchD else None}
        else:
            ctl, alu, rsD, rtD, rdD = NOP_CTL, "add", 0, 0, 0
            RD1 = RD2 = SignImmD = 0
            BranchD = PCSrcD = 0
            PCBranchD = 0

        # ---- hazard unit (slide 69, verbatim) ---------------------------------
        lwstall = int(((rsD == rtE) or (rtD == rtE)) and bool(hw(MemtoRegE)))
        branchstall = int((BranchD and RegWriteE and (WriteRegE == rsD or WriteRegE == rtD)) or
                          (BranchD and hw(MemtoRegM) and (WriteRegM == rsD or WriteRegM == rtD)))
        StallF = StallD = FlushE = int(lwstall or branchstall)
        if lwstall:
            ev.append({"type": "lwstall", "from": Er["id"], "to": Dr["id"], "reg": reg_name(rtE)})
        if branchstall:
            ev.append({"type": "branchstall", "to": Dr["id"]})

        # ---- IF ----------------------------------------------------------------
        InstrF = imem.get(PC)
        occ["F"] = idx[PC] if InstrF else None
        PCPlus4F = (PC + 4) & MASK32
        if PCSrcD and not StallD and InstrF:
            ev.append({"type": "flush", "flushed": idx[PC], "by": Dr["id"], "target": PCBranchD})

        # ---- clock edge --------------------------------------------------------
        nPC = PC if StallF else (PCBranchD if PCSrcD else PCPlus4F)
        if StallD:
            nD = Dr
        elif PCSrcD:
            nD = None
        else:
            nD = {"id": idx[PC], "pc": PC, "word": InstrF["word"], "PCPlus4": PCPlus4F} if InstrF else None
        if FlushE or not Dr:
            nE = None
        else:
            nE = {"id": Dr["id"], "RegWrite": ctl["RegWrite"], "MemtoReg": hw(ctl["MemtoReg"]),
                  "MemWrite": ctl["MemWrite"], "ALUSrc": ctl["ALUSrc"], "RegDst": hw(ctl["RegDst"]),
                  "alu_op": alu, "RD1": RD1, "RD2": RD2, "Rs": rsD, "Rt": rtD, "Rd": rdD, "SignImm": SignImmD}
        nM = None
        if Er:
            nM = {"id": Er["id"], "RegWrite": Er["RegWrite"], "MemtoReg": Er["MemtoReg"],
                  "MemWrite": Er["MemWrite"], "ALUOut": ALUOutE & MASK32, "WriteData": WriteDataE & MASK32,
                  "WriteReg": WriteRegE}
        if Mr and Mr["MemWrite"]:
            mem[Mr["ALUOut"]] = Mr["WriteData"]
            changes["mem"][f"0x{Mr['ALUOut']:02X}"] = s32(Mr["WriteData"])
        nW = None
        if Mr:
            nW = {"id": Mr["id"], "RegWrite": Mr["RegWrite"], "MemtoReg": Mr["MemtoReg"],
                  "ReadData": ReadDataM if ReadDataM is not None else 0, "ALUOut": Mr["ALUOut"],
                  "WriteReg": Mr["WriteReg"]}

        steps.append({
            "cycle": cyc, "pcF": PC, "occupancy": occ,
            "stalled": {"F": StallF, "D": StallD}, "bubble_into_E": FlushE,
            "hazard": {"lwstall": lwstall, "branchstall": branchstall, "StallF": StallF, "StallD": StallD,
                       "FlushE": FlushE, "PCSrcD": PCSrcD, "ForwardAD": de["ForwardAD"] if de else 0,
                       "ForwardBD": de["ForwardBD"] if de else 0,
                       "ForwardAE": ex["ForwardAE"] if ex else "00", "ForwardBE": ex["ForwardBE"] if ex else "00"},
            "events": ev,
            "F": {"pc": PC, "PCPlus4F": PCPlus4F, "word": f"{InstrF['word']:08X}" if InstrF else None},
            "D": de, "E": ex,
            "M": ({"ALUOutM": s32(Mr["ALUOut"]), "MemWriteM": Mr["MemWrite"], "WriteDataM": s32(Mr["WriteData"]),
                   "ReadDataM": None if ReadDataM is None else s32(ReadDataM), "WriteRegM": reg_name(Mr["WriteReg"])}
                  if Mr else None),
            "W": ({"ResultW": s32(ResultW), "RegWriteW": Wr["RegWrite"], "WriteRegW": reg_name(Wr["WriteReg"])}
                  if Wr else None),
            "PCnext": nPC, "changes": changes,
            "regs_after": {reg_name(i): s32(v) for i, v in enumerate(regs)},
            "mem_after": {f"0x{a:02X}": s32(v) for a, v in sorted(mem.items())},
        })
        PC, Dr, Er, Mr, Wr = nPC, nD, nE, nM, nW
        regs[0] = 0

    word_of = {idx[p["addr"]]: p["word"] for p in prog}
    for k, st in enumerate(steps):
        st["_period"] = period
        st["stages"], st["hazard_wires"] = stage_paths(k, st, word_of)
        del st["_period"]
        st["classes"] = {sn: v["class"] for sn, v in st["stages"].items()}

    # pipeline diagram: instruction -> {cycle: stage}
    diagram = {}
    for s in steps:
        for st, i in s["occupancy"].items():
            if i is not None:
                diagram.setdefault(str(i), {})
                # a stalled instruction stays in its stage for several cycles
                diagram[str(i)].setdefault(str(s["cycle"]), st)
    flushed = sorted({e["flushed"] for s in steps for e in s["events"] if e["type"] == "flush"})
    completed = [i for i in range(1, len(prog) + 1) if any(s["W"] and s["occupancy"]["W"] == i
                                                             for s in steps)]
    trace = {
        "video": "inorder/pipeline",
        "config": {"delays_ps": DELAYS, "stage_ps": sd, "period_ps": period, "alu_control_encoding": ALUCTL,
                   "assumptions": ASSUMPTIONS,
                   "program": [{"addr": p["addr"], "word": f"{p['word']:08X}", "text": p["text"], "reason": r}
                               for p, r in zip(prog, REASONS)],
                   "init_regs": INIT_REGS, "init_mem": {f"0x{a:02X}": v for a, v in INIT_MEM.items()},
                   "show_regs": SHOW_REGS, "show_mem": [f"0x{a:02X}" for a in SHOW_MEM]},
        "steps": steps, "diagram": diagram, "classes": {str(i): klass(w) for i, w in word_of.items()}, "flushed": flushed, "completed": completed,
        "final": {"regs": {reg_name(i): s32(v) for i, v in enumerate(regs)},
                  "mem": {f"0x{a:02X}": s32(mem.get(a, 0)) for a in sorted(INIT_MEM)},
                  "cycles": len(steps), "instructions": len(completed),
                  "total_ps": len(steps) * period},
    }
    return trace


def main():
    t = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(t, indent=1, ensure_ascii=False))
    f = t["final"]
    print(f"wrote {OUT.relative_to(ROOT)}: {f['instructions']} instructions, {f['cycles']} cycles x "
          f"{t['config']['period_ps']} ps = {f['total_ps']} ps")


if __name__ == "__main__":
    main()
