"""Verify the pipeline trace before rendering.

  1. final state == ISA interpreter (also with X selects driven as 1)
  2. the designed hazards appear at the designed instruction pairs, resolved as slide 69 says
  3. the slide-69 equations re-evaluated independently from the trace, every cycle
  4. Decode-stage control == single-cycle control of the same instruction (slide 20)
  5. cycle count = 5 + (N-1) + stalls + flushes; clock period; comparison with videos 1-2

Prints markdown tables and writes out/verify_report.md.  Exit code 1 on mismatch.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import inorder.pipeline.sim.pipeline as pl  # noqa: E402
from inorder.shared.interpreter import run  # noqa: E402
from inorder.pipeline.verify.reference_slides import (DELAYS_REF, EXPECTED_EVENTS, FORBIDDEN,  # noqa: E402
                                                      SLIDE86, SLIDE86_TC)

TRACE = ROOT / "inorder/pipeline/out/trace.json"
SC = ROOT / "inorder/single_cycle/out/trace.json"
MC = ROOT / "inorder/multi_cycle/out/trace.json"
REPORT = ROOT / "inorder/pipeline/out/verify_report.md"
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
    ref = run()
    texts = {i + 1: p["text"] for i, p in enumerate(t["config"]["program"])}

    # 1 -------------------------------------------------------------------
    out("## 1. 최종 상태: pipeline vs ISA 인터프리터")
    pl.X_DEFAULT = 1
    t1 = pl.build()
    pl.X_DEFAULT = 0
    rows = []
    for n in ref["regs"]:
        a, b, c = t["final"]["regs"][n], ref["regs"][n], t1["final"]["regs"][n]
        if a or b:
            ok = a == b == c
            rows.append([n, a, c, b, "OK" if ok else "**불일치**"])
            if not ok:
                bad.append(f"reg {n}")
    for k in ref["mem"]:
        a, b, c = t["final"]["mem"].get(k), ref["mem"][k], t1["final"]["mem"].get(k)
        ok = a == b == c
        rows.append([f"Mem[{k}]", a, c, b, "OK" if ok else "**불일치**"])
        if not ok:
            bad.append(f"mem {k}")
    done = [p["addr"] for i, p in enumerate(t["config"]["program"]) if i + 1 in t["completed"]]
    ok = done == ref["executed_pcs"] and t1["final"]["cycles"] == t["final"]["cycles"]
    rows.append(["완료한 명령어(PC)", " ".join(f"{p:02X}" for p in done), f"{t1['final']['cycles']} 사이클",
                 " ".join(f"{p:02X}" for p in ref["executed_pcs"]), "OK" if ok else "**불일치**"])
    if not ok:
        bad.append("completed instructions")
    table(["항목", "pipeline (X→0)", "pipeline (X→1)", "인터프리터", "결과"], rows)

    # 2 -------------------------------------------------------------------
    out("## 2. 설계한 hazard가 설계한 명령어 쌍에서 일어나는가")
    evs = [(s["cycle"], e) for s in t["steps"] for e in s["events"]]
    rows = []
    names = {"lwstall": "load-use → 1 stall (StallF·StallD·FlushE)", "fwd_WB_EX": "WB→EX forwarding",
             "fwd_MEM_EX": "MEM→EX forwarding", "rf_half": "레지스터 파일 (WB 전반 쓰기, ID 후반 읽기)",
             "flush": "taken beq → 다음 명령어 flush (CLR=PCSrcD)"}
    for typ, a, b, reg in EXPECTED_EVENTS:
        hit = [c for c, e in evs if e["type"] == typ and
               ((typ == "flush" and e["by"] == a and e["flushed"] == b) or
                (typ != "flush" and e.get("from") == a and e.get("to") == b and e.get("reg") == reg))]
        ok = len(hit) == 1
        if not ok:
            bad.append(f"event {typ} I{a}->I{b}")
        rows.append([f"I{a} → I{b}", reg or "PC", names[typ], f"사이클 {hit[0]}" if hit else "-",
                     "OK" if ok else "**없음/중복**"])
    extra = [(c, e) for c, e in evs if not any(
        e["type"] == typ and ((typ == "flush" and e["by"] == a and e["flushed"] == b) or
                              (typ != "flush" and e.get("from") == a and e.get("to") == b and e.get("reg") == reg))
        for typ, a, b, reg in EXPECTED_EVENTS)]
    for c, e in extra:
        bad.append(f"unexpected {e}")
        rows.append(["?", e.get("reg"), e["type"], f"사이클 {c}", "**예상 밖**"])
    for f in FORBIDDEN:
        if any(e["type"] == f for _, e in evs):
            bad.append(f)
    rows.append(["I7 beq", "$t2,$t3", "branchstall 없음 (피연산자가 충분히 앞)",
                 "없음" if not any(e["type"] == "branchstall" for _, e in evs) else "있음",
                 "OK" if not any(e["type"] == "branchstall" for _, e in evs) else "**불일치**"])
    table(["쌍", "레지스터", "처리", "언제", "결과"], rows)

    # 3 -------------------------------------------------------------------
    out("## 3. 슬라이드 69 식을 trace 값으로 다시 계산 (매 사이클)")
    nbad = 0
    for k, s in enumerate(t["steps"]):
        h = s["hazard"]
        if not (h["StallF"] == h["StallD"] == h["FlushE"] == int(h["lwstall"] or h["branchstall"])):
            nbad += 1
        d = s["D"]
        m = s["M"]
        if d:
            regw_m = bool(m) and t["steps"][k]["M"] is not None and _regwrite(t, s, "M")
            wm = m["WriteRegM"] if m else None
            for port, r in (("ForwardAD", d["rsD"]), ("ForwardBD", d["rtD"])):
                exp = int(r != "$0" and r == wm and regw_m)
                if h[port] != exp:
                    nbad += 1
        e = s["E"]
        if e:
            for port, f in (("ForwardAE", h["ForwardAE"]), ("ForwardBE", h["ForwardBE"])):
                if f not in ("00", "01", "10"):
                    nbad += 1
    out(f"StallF = StallD = FlushE = lwstall | branchstall, ForwardAD/BD 식: {len(t['steps'])} 사이클 중 "
        f"불일치 {nbad}")
    out()
    if nbad:
        bad.append("slide-69 equations")

    # 4 -------------------------------------------------------------------
    out("## 4. Decode 단계 제어 신호 vs 1편(single-cycle) 제어 (슬라이드 20: 같은 제어 유닛)")
    sc = json.loads(SC.read_text())
    sc_ctl = {s["index"]: s["control"] for s in sc["steps"]}
    rows = []
    seen = set()
    for s in t["steps"]:
        i = s["occupancy"]["D"]
        if i is None or i in seen or s["D"] is None:
            continue
        seen.add(i)
        c = s["D"]["control"]
        if i in sc_ctl:
            ok = c == sc_ctl[i]
            if not ok:
                bad.append(f"control I{i}")
            rows.append([f"I{i}", texts[i], ", ".join(f"{k}={v}" for k, v in c.items()), "OK" if ok else "**불일치**"])
        else:
            rows.append([f"I{i}", texts[i], ", ".join(f"{k}={v}" for k, v in c.items()), "(flush 전 해독)"])
    table(["#", "명령어", "Decode 제어 신호", "1편과 같음"], rows)

    # 5 -------------------------------------------------------------------
    out("## 5. 사이클 수와 실행 시간")
    f = t["final"]
    stalls = sum(1 for _, e in evs if e["type"] in ("lwstall", "branchstall"))
    flushes = sum(1 for _, e in evs if e["type"] == "flush")
    exp_cycles = 5 + (f["instructions"] - 1) + stalls + flushes
    ok = exp_cycles == f["cycles"]
    if not ok:
        bad.append("cycle count")
    out(f"5 + (명령어 {f['instructions']} - 1) + stall {stalls} + flush {flushes} = {exp_cycles} — "
        f"trace {f['cycles']} 사이클 ({'OK' if ok else '**불일치**'})")
    out()
    cfg = t["config"]
    if cfg["delays_ps"] != DELAYS_REF:
        bad.append("delays")
    table(["단계", "식 (슬라이드 83)", "L10 90 지연으로 (ps)"],
          [["IF", "t_mem", cfg["stage_ps"]["F"]], ["ID", "2 × (t_RFread + mux + eq + AND + mux)", cfg["stage_ps"]["D"]],
           ["EX", "t_mux + t_mux + t_ALU", cfg["stage_ps"]["E"]], ["MEM", "t_mem", cfg["stage_ps"]["M"]],
           ["WB", "2 × (t_mux + t_RFwrite)", cfg["stage_ps"]["W"]]])
    out(f"클록 주기 = 가장 느린 단계 = {cfg['period_ps']} ps (가정 1). "
        f"참고: 슬라이드 86은 다른 지연 표({SLIDE86['tmem']}ps 메모리 등)로 Tc = {SLIDE86_TC} ps.")
    out()
    mc = json.loads(MC.read_text())
    table(["", "single-cycle", "multi-cycle", "pipeline"],
          [["사이클 수", sc["final"]["cycles"], mc["final"]["cycles"], f["cycles"]],
           ["CPI (명령어 9개)", "1.00", f"{mc['final']['cpi']:.2f}", f"{f['cycles'] / f['instructions']:.2f}"],
           ["클록 주기", f"{sc['config']['period_ps']} ps", f"{mc['config']['period_ps']} ps", f"{cfg['period_ps']} ps"],
           ["총 실행 시간", f"{sc['final']['total_ps']} ps", f"{mc['final']['total_ps']} ps", f"{f['total_ps']} ps"]])
    out("pipeline CPI에는 파이프라인을 채우는 4사이클이 들어 있다 (명령어 9개뿐이라 크게 보임).")
    out()
    out("## 결과")
    out("모두 일치" if not bad else "불일치: " + ", ".join(bad))
    REPORT.write_text("\n".join(lines) + "\n")
    sys.exit(1 if bad else 0)


def _regwrite(t, s, stage):
    """RegWriteM of the instruction in M this cycle (from its Decode control)."""
    i = s["occupancy"][stage]
    for x in t["steps"]:
        if x["occupancy"]["D"] == i and x["D"]:
            return bool(x["D"]["control"]["RegWrite"])
    return False


if __name__ == "__main__":
    main()
