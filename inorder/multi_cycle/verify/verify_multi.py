"""Verify the multi-cycle trace before rendering.

  1. final state == ISA interpreter (also with X selects driven as 1 instead of 0)
  2. every cycle's control signals == bubble text of slide 58 (PDF p.30)
  3. state sequence per instruction == FSM arrows of slide 58
  4. clock period / per-state work from the L10 90 delays; comparison with single-cycle

Prints markdown tables and writes out/verify_report.md.  Exit code 1 on mismatch.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import inorder.multi_cycle.sim.multi_cycle as mc  # noqa: E402
from inorder.shared.interpreter import run  # noqa: E402
from inorder.multi_cycle.verify.reference_slides import (DELAYS_REF, FSM_REF,  # noqa: E402
                                                         TRANSITIONS_REF)

TRACE = ROOT / "inorder/multi_cycle/out/trace.json"
SC_TRACE = ROOT / "inorder/single_cycle/out/trace.json"
REPORT = ROOT / "inorder/multi_cycle/out/verify_report.md"
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

    # 1 ------------------------------------------------------------------
    out("## 1. 최종 상태: multi-cycle vs ISA 인터프리터")
    mc.X_DEFAULT = 1
    t_x1 = mc.build()
    mc.X_DEFAULT = 0
    rows = []
    for n in ref["regs"]:
        a, b, c = t["final"]["regs"][n], ref["regs"][n], t_x1["final"]["regs"][n]
        if a or b:
            ok = a == b == c
            rows.append([n, a, c, b, "OK" if ok else "**불일치**"])
            if not ok:
                bad.append(f"reg {n}")
    for k in ref["mem"]:
        a, b, c = t["final"]["mem"].get(k), ref["mem"][k], t_x1["final"]["mem"].get(k)
        ok = a == b == c
        rows.append([f"Mem[{k}]", a, c, b, "OK" if ok else "**불일치**"])
        if not ok:
            bad.append(f"mem {k}")
    pcs = [i["pc"] for i in t["instr_states"]]
    ok = pcs == ref["executed_pcs"]
    rows.append(["실행 PC 순서", " ".join(f"{p:02X}" for p in pcs), "",
                 " ".join(f"{p:02X}" for p in ref["executed_pcs"]), "OK" if ok else "**불일치**"])
    if not ok:
        bad.append("pc order")
    table(["항목", "multi-cycle (X→0)", "multi-cycle (X→1)", "인터프리터", "결과"], rows)

    # 2 ------------------------------------------------------------------
    out("## 2. 상태별 제어 신호 vs 슬라이드 58 (PDF 30쪽) 동그라미 안의 글자")
    rows, seen = [], set()
    for s in t["steps"]:
        r = FSM_REF[s["state"]]
        c = s["control"]
        for k, v in r.items():
            if k == "name":
                continue
            if c[k] != v:
                bad.append(f"cycle {s['cycle']} {s['state']} {k}: {c[k]} != {v}")
        if s["state"] not in seen:
            seen.add(s["state"])
            sig = ", ".join(f"{k}={v}" for k, v in r.items() if k != "name")
            got = ", ".join(f"{k}={c[k]}" for k in r if k != "name")
            rows.append([s["state"], r["name"], sig, got, "OK" if sig == got else "**불일치**"])
    rows.sort(key=lambda r: int(r[0][1:]))
    table(["상태", "이름", "슬라이드", "trace", "결과"], rows)
    out(f"모든 {len(t['steps'])} 사이클에서 위 값 확인. 그림에 없는 쓰기 신호는 0, mux 선택은 X (가정 3).")
    out()

    # 3 ------------------------------------------------------------------
    out("## 3. 명령어별 상태 순서 vs 슬라이드 58의 화살표")
    rows = []
    cls = {}
    for s in t["steps"]:
        cls[s["instr"]["n"]] = (s["class"], s["instr"])
    for i in t["instr_states"]:
        k, ins = cls[i["n"]]
        exp = TRANSITIONS_REF[k]
        ok = i["states"] == exp
        if not ok:
            bad.append(f"I{ins['index']} states")
        rows.append([f"I{ins['index']}", ins["text"], " → ".join(i["states"]), len(i["states"]),
                     "OK" if ok else "**불일치**"])
    table(["#", "명령어", "상태 순서", "사이클", "결과"], rows)

    # 4 ------------------------------------------------------------------
    out("## 4. 클록 주기와 실행 시간")
    d = t["config"]["delays_ps"]
    if d != DELAYS_REF:
        bad.append("delays")
    out(f"부품 지연(PDF 31쪽 = L10 90): {d} → {'OK' if d == DELAYS_REF else '**불일치**'}")
    out()
    per = {}
    for s in t["steps"]:
        per[s["state"]] = (s["state_name"], s["timing"]["used"],
                           ", ".join(f"{e['comp']} {e['end'] - e['start']}" for e in s["timing"]["events"]))
    table(["상태", "이름", "하는 일(ps)", "필요 시간(ps)"],
          [[k, v[0], v[2], v[1]] for k, v in sorted(per.items(), key=lambda x: int(x[0][1:]))])
    P = t["config"]["period_ps"]
    out(f"클록 주기 = 가장 긴 상태 = {P} ps (가정 1: 레지스터 오버헤드 0ps)")
    out()
    sc = json.loads(SC_TRACE.read_text())
    f = t["final"]
    table(["", "single-cycle", "multi-cycle"],
          [["명령어 수", sc["final"]["cycles"], f["instructions"]],
           ["사이클 수", sc["final"]["cycles"], f["cycles"]],
           ["CPI", "1", f"{f['cpi']:.2f}"],
           ["클록 주기", f"{sc['config']['period_ps']} ps", f"{P} ps"],
           ["총 실행 시간", f"{sc['final']['total_ps']} ps", f"{f['total_ps']} ps"]])
    waste = sum(s["timing"]["waste"] for s in t["steps"])
    out(f"multi-cycle 사이클 안의 남는 시간 합: {waste} ps / {f['total_ps']} ps")
    out()

    out("## 결과")
    out("모두 일치" if not bad else "불일치: " + ", ".join(bad))
    REPORT.write_text("\n".join(lines) + "\n")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
