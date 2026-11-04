"""Compare out/trace.json with the hand transcription of slides 36-63.

Writes out/verification_report.md and exits 1 if there is any mismatch that is
not explained as a partially-built slide (see CLASSIFY below).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import slide_transcription as T  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
trace = json.load(open(os.path.join(ROOT, "out", "trace.json"), encoding="utf-8"))
cyc = {c["cycle"]: c for c in trace["cycles"]}
PROG = trace["config"]["program"]
RS_COLS = ["V1", "Tag1", "Value1", "V2", "Tag2", "Value2"]

rows = []          # (slide, cycle, where, slide_value, sim_value, verdict)
checks = 0


def build_step(slide, slide_val, sim_val):
    """Cells that the slide has simply not drawn yet (animation build)."""
    return slide in (43, 44, 45, 49, 50) and slide_val == "" and sim_val != ""


def cmp(slide, cycle, where, sv, mv):
    global checks
    checks += 1
    if sv == mv:
        return
    verdict = "부분 표시(빌드 단계)" if build_step(slide, sv, mv) else "불일치"
    rows.append((slide, cycle, where, sv if sv != "" else "(빈칸)", mv if mv != "" else "(빈칸)", verdict))


def bcasts(c):
    return [e for p in cyc[c]["phases"] for e in p["events"] if e["type"] == "broadcast"]


for s in T.full_states():
    n, sl = s["cycle"], s["slide"]
    if n not in cyc or n + 1 not in cyc and n < 20:
        cmp(sl, n, "시뮬레이터에 이 사이클이 없음", "있음", "없음")
        continue
    st = cyc[n]["state"]
    rat, rs = st["rat_display"], st["rs_display"]
    if sl in (49, 50):  # intermediate: after the MUL (49) / ADD (50) broadcast
        b = [e for e in bcasts(8) if e["unit"] == ("MUL" if sl == 49 else "ADD")]
        if b:
            rat, rs = b[0]["after"]["rat_display"], b[0]["after"]["rs_display"]
        else:
            cmp(sl, n, "사이클 8 broadcast", "있음", "없음")
    for r, v in s["rat_full"].items():
        for k, name in enumerate(["Valid", "Tag", "Value"]):
            cmp(sl, n, f"RAT {r}.{name}", v[k], rat[r][k])
    for e, v in s["rs_full"].items():
        for k in range(6):
            cmp(sl, n, f"RS {e}.{RS_COLS[k]}", v[k], rs[e][k])
    for i, row in enumerate(s["table"]):
        for k, val in enumerate(row):
            tt = trace["timing_table"][i]
            cmp(sl, n, f"타이밍 I{i+1}@{k+1}", val, tt[k] if k < len(tt) else "")
    # claims in text boxes
    for cl in s["claims"]:
        kind = cl[0]
        evs = [e for p in cyc[n]["phases"] for e in p["events"]]
        if kind == "alloc":
            ok = any(e["type"] == "decode_alloc" and e["rs"] == cl[1] and e["instr"] == cl[2] - 1 for e in evs)
            cmp(sl, n, f"설명: I{cl[2]} → RS {cl[1]} 할당", "예", "예" if ok else "아니오")
        elif kind == "rename":
            ok = any(e["type"] == "rename" and e["reg"] == cl[1] and e["tag"] == cl[2] for e in evs)
            cmp(sl, n, f"설명: rename {cl[1]} → {cl[2]}", "예", "예" if ok else "아니오")
        elif kind == "dispatch":
            ok = any(e["type"] == "dispatch" and e["rs"] == cl[1] for e in evs)
            cmp(sl, n, f"설명: RS {cl[1]} 실행 시작", "예", "예" if ok else "아니오")
        elif kind == "timer":
            d = [e for e in evs if e["type"] == "dispatch" and e["unit"] == cl[1]]
            cmp(sl, n, f"설명: {cl[1]} 타이머", str(cl[2]), str(d[0]["latency"]) if d else "(없음)")
        elif kind == "ready_next":
            nxt = [e for p in cyc.get(n + 1, {"phases": []})["phases"] for e in p["events"]]
            disp = any(e["type"] == "dispatch" and e["rs"] == cl[1] for e in nxt)
            cmp(sl, n, f"설명: RS {cl[1]} 다음 사이클 실행 가능?", "예" if cl[2] else "아니오",
                "예" if disp else "아니오")
        elif kind == "broadcast":
            b = [e for e in bcasts(n) if e["unit"] == cl[1]]
            got = f"{b[0]['tag']}={b[0]['value']}" if b else "(없음)"
            cmp(sl, n, f"설명: {cl[1]} 버스 broadcast", f"{cl[2]}={cl[3]}", got)

# broadcasts only where the slides draw them
sim_bslides = set()
for c in trace["cycles"]:
    for e in bcasts(c["cycle"]) if c["cycle"] else []:
        sim_bslides.add({8: 49 if e["unit"] == "MUL" else 50}.get(c["cycle"], c["cycle"] + 43))
cmp("-", "-", "broadcast가 나오는 슬라이드 집합", str(sorted(T.BROADCAST_SLIDES)), str(sorted(sim_bslides)))

# slide 38 OoO summary, slide 37 in-order
for i, (f, d, e1, w) in enumerate(T.SLIDE38_OOO["rows"]):
    row = trace["timing_table"][i]
    got = tuple(row.index(x) + 1 if x in row else None for x in ("F", "D", "E1", "W"))
    cmp(38, "-", f"OoO I{i+1} (F,D,E1,W)", str((f, d, e1, w)), str(got))
cmp(38, "-", "OoO 총 사이클", str(T.SLIDE38_OOO["total"]), str(trace["total_cycles"]))
for i, (f, d, e1, w) in enumerate(T.SLIDE37_FWD["rows"]):
    r = trace["inorder"]["forwarding"]["rows"][i]
    cmp(37, "-", f"in-order(fwd) I{i+1} (F,D,E1,W)", str((f, d, e1, w)), str((r["F"], r["D"], r["E1"], r["W"])))
cmp(37, "-", "in-order forwarding 총 사이클", "25", str(trace["inorder"]["forwarding"]["total_cycles"]))
cmp(37, "-", "in-order no-forwarding 총 사이클", "31", str(trace["inorder"]["no_forwarding"]["total_cycles"]))

# user-requested spot checks
must = []
b8 = [e for e in bcasts(8) if e["unit"] == "MUL"]
must.append(("사이클 8 (슬라이드 49): MUL x 완료, tag x / value 2 broadcast",
             bool(b8) and b8[0]["tag"] == "x" and b8[0]["value"] == 2
             and trace["timing_table"][0][7] == "E6"))
fr = trace["final_registers"]
for r, v in [("R3", 2), ("R5", 142), ("R7", 8), ("R10", 17), ("R11", 136)]:
    must.append((f"사이클 20 (슬라이드 63): {r} = {v}", fr[r] == v))
must.append(("총 20 사이클 (마지막 W 포함)", trace["total_cycles"] == 20
             and trace["timing_table"][5][19:20] == ["W"]))

# A "partially drawn" cell is accepted only if the NEXT slide shows exactly the
# simulator's value in that cell; otherwise it is downgraded to a mismatch.
states = {x["slide"]: x for x in T.full_states()}
for idx, r in enumerate(rows):
    if r[5] == "불일치":
        continue
    sl, where, simv = r[0], r[2], (r[4] if r[4] != "(빈칸)" else "")
    if not where.startswith(("RAT", "RS", "타이밍")):
        continue
    def cell(st):
        if where.startswith("RAT"):
            reg, col = where[4:].split(".")
            return st["rat_full"][reg][["Valid", "Tag", "Value"].index(col)]
        if where.startswith("RS"):
            e, col = where[3:].split(".")
            return st["rs_full"][e][RS_COLS.index(col)]
        i, k = where.split("I")[1].split("@")
        return st["table"][int(i) - 1][int(k) - 1]
    nxt_sl = sl + 1                      # first later slide that draws the cell
    while cell(states[nxt_sl]) == "" and nxt_sl < 63:
        nxt_sl += 1
    v = cell(states[nxt_sl])
    checks += 1
    rows[idx] = r[:5] + (f"부분 표시 → 슬라이드 {nxt_sl}에서 {v or '(빈칸)'} 로 채워짐"
                         if v == simv else f"불일치 (슬라이드 {nxt_sl}에서 {v or '(빈칸)'})",)

real = [r for r in rows if r[5].startswith("불일치")]
part = [r for r in rows if r[5] != "불일치"]
L = ["# 검증 보고서 — 시뮬레이터 vs 슬라이드 36~63", "",
     f"- 비교한 항목 수: **{checks}** (RAT·RS 칸, 타이밍 표 칸, 설명 박스 주장, 요약 수치)",
     f"- 실제 불일치: **{len(real)}**",
     f"- 슬라이드가 해당 사이클에 아직 그리지 않은 칸(부분 표시): **{len(part)}**", "",
     "## 필수 확인 항목", "", "| 항목 | 결과 |", "|---|---|"]
L += [f"| {a} | {'✅ 일치' if ok else '❌ 불일치'} |" for a, ok in must]
L += ["", "## 불일치 / 차이 목록", ""]
if rows:
    L += ["| 슬라이드 | 사이클 | 위치 | 슬라이드 | 시뮬레이터 | 판정 |", "|---|---|---|---|---|---|"]
    L += [f"| {a} | {b} | {c} | {d} | {e} | {f} |" for a, b, c, d, e, f in rows]
else:
    L += ["없음."]
out = os.path.join(ROOT, "out", "verification_report.md")
open(out, "w", encoding="utf-8").write("\n".join(L) + "\n")
print("\n".join(L))
sys.exit(1 if real or not all(ok for _, ok in must) else 0)
