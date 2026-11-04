"""Verify the single-cycle trace before rendering.

  1. final state == ISA interpreter
  2. control signals per instruction == slide figures L10 56–61 (PDF p.5–10)
  3. latency per class / arrival times == L10 90–95 (PDF p.15–20)
  4. hazard map of the common program (dependency distances in the dynamic stream)

Prints markdown tables and writes out/verify_report.md.  Exit code 1 on mismatch.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from inorder.shared.interpreter import run  # noqa: E402
from inorder.single_cycle.verify.reference_slides import (ARRIVAL_REF, BRANCH_EQ,  # noqa: E402
                                                          CONTROL_REF, DELAYS_REF, LATENCY_REF,
                                                          alu_ref)

TRACE = ROOT / "inorder/single_cycle/out/trace.json"
REPORT = ROOT / "inorder/single_cycle/out/verify_report.md"
INV_ALU = None
lines, bad = [], []


def out(s=""):
    lines.append(s)
    print(s)


def table(head, rows):
    out("| " + " | ".join(head) + " |")
    out("|" + "---|" * len(head))
    for r in rows:
        out("| " + " | ".join(str(x) for x in r) + " |")
    out()


def main():
    t = json.loads(TRACE.read_text())
    inv_alu = {v: k for k, v in t["config"]["alu_control_encoding"].items()}

    # 1. final state ---------------------------------------------------------
    ref = run()
    out("## 1. 최종 상태: 시뮬레이터 vs ISA 인터프리터")
    rows = []
    for n in sorted(set(ref["regs"]) | set(t["final"]["regs"]), key=list(ref["regs"]).index):
        a, b = t["final"]["regs"][n], ref["regs"][n]
        if a or b:
            rows.append([n, a, b, "OK" if a == b else "**불일치**"])
            if a != b:
                bad.append(f"reg {n}")
    for k in sorted(set(ref["mem"]) | set(t["final"]["mem"])):
        a, b = t["final"]["mem"].get(k), ref["mem"].get(k)
        rows.append([f"Mem[{k}]", a, b, "OK" if a == b else "**불일치**"])
        if a != b:
            bad.append(f"mem {k}")
    exe_t = [s["pc"] for s in t["steps"]]
    rows.append(["실행 PC 순서", " ".join(f"{p:02X}" for p in exe_t),
                 " ".join(f"{p:02X}" for p in ref["executed_pcs"]),
                 "OK" if exe_t == ref["executed_pcs"] else "**불일치**"])
    if exe_t != ref["executed_pcs"]:
        bad.append("pc order")
    table(["항목", "single-cycle", "인터프리터", "결과"], rows)

    # 2. control signals -----------------------------------------------------
    out("## 2. 명령어별 제어 신호 vs 슬라이드 (L10 56–61 = PDF 5–10쪽 그림)")
    sigs = ["RegWrite", "RegDst", "ALUSrc", "Branch", "MemWrite", "MemtoReg", "ALUControl", "PCSrc"]
    rows = []
    for s in t["steps"]:
        k = s["class"] if s["class"] != "BEQ" else ("BEQ_T" if s["PCSrc"] else "BEQ_NT")
        r = CONTROL_REF[k]
        c = s["control"]
        exp = {"RegWrite": r["RegWrite"], "RegDst": r["RegDst"], "ALUSrc": r["ALUSrc"],
               "Branch": BRANCH_EQ[k], "MemWrite": r["MemWrite"], "MemtoReg": r["MemtoReg"],
               "ALUControl": alu_ref(r["ALUop"], s["mnemonic"]), "PCSrc": r["PCSrc2"]}
        got = dict(c, PCSrc=s["PCSrc"])
        got["ALUControl"] = inv_alu[c["ALUControl"]]
        cells = []
        for g in sigs:
            ok = got[g] == exp[g]
            val = f"{c['ALUControl']}({got[g]})" if g == "ALUControl" else got[g]
            cells.append(f"{val}" if ok else f"**{val}≠{exp[g]}**")
            if not ok:
                bad.append(f"I{s['index']} {g}")
        # MemRead does not exist in H&H; check that the data memory read port is used only by lw
        used_read = "readdata_res" in s["active"]["wires"]
        if int(used_read) != r["MemRead"]:
            bad.append(f"I{s['index']} MemRead")
        cells.append("OK" if int(used_read) == r["MemRead"] else "**불일치**")
        rows.append([f"I{s['index']}", s["text"], f"p.{r['page']}"] + cells)
    table(["#", "명령어", "기준"] + sigs + ["MemRead(경로)"], rows)
    out("ALUControl 칸: H&H 3비트 값(연산 이름). 슬라이드 라벨 funct/opcode/Add/bcond를 연산 이름으로 바꿔 비교."
        " Branch는 그림에 값이 없어 PDF 4쪽 식 PCSrc2=(opcode==Bxx)&&bcond에서 가져옴.")
    out()

    # 3. timing --------------------------------------------------------------
    out("## 3. 지연 시간 vs 슬라이드 (L10 90 표, L10 92–95 경로 주석)")
    d = t["config"]["delays_ps"]
    if d != DELAYS_REF:
        bad.append("delays")
    out(f"부품 지연: trace {d} / 슬라이드 {DELAYS_REF} → {'OK' if d == DELAYS_REF else '**불일치**'}")
    out()
    rows = []
    lat = t["config"]["latency_by_class"]
    for k, v in LATENCY_REF.items():
        ok = lat[k] == v
        if not ok:
            bad.append(f"latency {k}")
        step = next((s for s in t["steps"] if s["class"] == k), None)
        arr = ""
        if step and k in ARRIVAL_REF:
            ends = {e["comp"]: e["end"] for e in step["timing"]["events"]}
            arr_ok = all(ends.get(c) == ps for c, ps in ARRIVAL_REF[k].items())
            if not arr_ok:
                bad.append(f"arrival {k}")
            arr = " ".join(f"{c}={ends.get(c)}" for c in ARRIVAL_REF[k]) + (" OK" if arr_ok else " **불일치**")
        rows.append([k, lat[k], v, "OK" if ok else "**불일치**", arr])
    table(["종류", "trace(ps)", "슬라이드(ps)", "결과", "경로 도착 시각"], rows)
    out(f"클록 주기 = 가장 느린 명령어(lw) = {t['config']['period_ps']} ps "
        f"({'OK' if t['config']['period_ps'] == 600 else '**불일치**'})")
    if t["config"]["period_ps"] != 600:
        bad.append("period")
    out()

    # 4. hazards -------------------------------------------------------------
    out("## 4. 공통 프로그램의 의존 관계 (실행 순서 기준, 거리 ≤ 3)")
    rows = []
    st = t["steps"]
    for j, s in enumerate(st):
        f = s["fields"]
        srcs = {f["rs"]} if s["class"] in ("I", "LW") else {f["rs"], f["rt"]}
        srcs.discard(0)
        for dist in (1, 2, 3):
            if j - dist < 0:
                continue
            p = st[j - dist]
            w = p["values"]["WriteReg"] if p["control"]["RegWrite"] else None
            if w is None:
                continue
            from inorder.shared.isa import REG_NUM
            if REG_NUM[w] in srcs:
                if s["class"] == "BEQ":
                    kind = "beq 피연산자 — " + ("stall 없음 (H&H: 거리 ≥3)" if dist >= 3 else "**분기 비교 stall 가능**")
                elif p["class"] == "LW" and dist == 1:
                    kind = "load-use (1 stall)"
                elif dist == 1:
                    kind = "거리 1 RAW → MEM→EX forwarding"
                elif dist == 2:
                    kind = "거리 2 RAW → WB→EX forwarding"
                else:
                    kind = "거리 3 → 레지스터 파일(쓰기 전반/읽기 후반), forwarding 불필요"
                rows.append([f"I{p['index']} → I{s['index']}", w, dist, kind])
    table(["쌍(생산→소비)", "레지스터", "거리", "의미"], rows)

    out("## 결과")
    out("모두 일치" if not bad else "불일치: " + ", ".join(bad))
    REPORT.write_text("\n".join(lines) + "\n")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
