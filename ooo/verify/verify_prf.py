"""Verify out/prf_trace.json.

Writes out/prf_verification_report.md (summary + checks) and
out/prf_state_tables.md (per-cycle Frontend Map, Arch Map, ROB, RS, PRF, free list).
Exit code 1 on any failed check.
"""
import json
import os
import sys

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, HERE)
import slide_transcription as ST  # noqa: E402

P = json.load(open(os.path.join(ROOT, "out", "prf_trace.json"), encoding="utf-8"))
OLD = json.load(open(os.path.join(ROOT, "out", "trace.json"), encoding="utf-8"))
CFG = P["config"]
PROG = CFG["program"]
REGS = CFG["registers"]
ALL_PR = [f"PR{i}" for i in range(1, CFG["n_pr"] + 1)]
results = []   # (group, item, expected, got, ok)


def check(group, item, exp, got):
    results.append((group, item, str(exp), str(got), exp == got))


# ---- 1. final architectural state vs slide 63 ------------------------------------
slide63 = ST.full_states()[-1]["rat_full"]
fin = P["cycles"][-1]["state"]
for r in REGS:
    p = fin["arch_map"][r]
    check("최종 Arch Map (슬라이드 63)", f"{r} → {p}", slide63[r][2], str(fin["prf"][p]["value"]))

# ---- 2. execution timing identical to the Tomasulo trace ---------------------------
def idx(row, lab):
    return row.index(lab) + 1 if lab in row else None


for i in range(len(PROG)):
    old, new = OLD["timing_table"][i], P["timing_table"][i]
    e_old = [k + 1 for k, s in enumerate(old) if s.startswith("E")]
    e_new = [k + 1 for k, s in enumerate(new) if s.startswith("E")]
    check("E 사이클 = 기존 Tomasulo", f"I{i+1} E 사이클", e_old, e_new)
    check("F·D 사이클 = 기존", f"I{i+1} (F,D)", (idx(old, "F"), idx(old, "D")), (idx(new, "F"), idx(new, "D")))
    check("R = 기존 W 사이클", f"I{i+1} R", idx(old, "W"), idx(new, "R"))

# ---- 3. rule checks ------------------------------------------------------------------
W = [P["instructions"][i]["W"] for i in range(len(PROG))]
R = [P["instructions"][i]["R"] for i in range(len(PROG))]
check("retire 규칙", "program order로 retire", sorted(W), W)
check("retire 규칙", "사이클당 최대 1개", len(W), len(set(W)))
check("retire 규칙", "W ≥ R + 1", True, all(w >= r + 1 for w, r in zip(W, R)))
check("retire 규칙", "W = max(R+1, 이전 W+1)", True,
      all(W[i] == max(R[i] + 1, (W[i - 1] + 1) if i else 0) for i in range(len(W))))
check("총 사이클", "마지막 W", max(W), P["total_cycles"])

# WAW on R5 (scene 1)
i2, i6 = P["instructions"][1], P["instructions"][5]
dec6 = [e for p in P["cycles"][i6["D"]]["phases"] for e in p["events"] if e["type"] == "decode_alloc"][0]
check("장면 ① R5 두 번 쓰기", "I2·I6 DestPR가 서로 다름", True, i2["dest_pr"] != i6["dest_pr"])
check("장면 ① R5 두 번 쓰기", "I6 Source 1(R5) PR = I2 DestPR", i2["dest_pr"], dec6["sources"][0]["pr"])
check("장면 ① R5 두 번 쓰기", "I6 old PR = I2 DestPR", i2["dest_pr"], i6["old_pr"])

# ---- 4. invariants every phase of every cycle -----------------------------------------
def seq_state(k):
    """Values after executing the first k instructions sequentially (precise state)."""
    v = dict(CFG["initial_values"])
    for p in PROG[:k]:
        a, b = v[p["src"][0]], v[p["src"][1]]
        v[p["dst"]] = a + b if p["op"] == "ADD" else a * b
    return v


inv_fail = []
spec_cycles = {}
n_checked = 0
for c in P["cycles"]:
    states = [c["state"]] if not c["phases"] else [ph["state"] for ph in c["phases"]]
    retired = sum(1 for w in W if w <= c["cycle"])
    for ph_i, st in enumerate(states):
        n_checked += 1
        tag = f"사이클 {c['cycle']} 단계 {ph_i + 1}"
        fl = st["free_list"]
        rob_live = [e for e in st["rob"] if e and e["valid"]]
        used = set(st["frontend_map"].values()) | set(st["arch_map"].values())
        used |= {e["dest_pr"] for e in rob_live} | {e["old_pr"] for e in rob_live}
        if len(fl) != len(set(fl)):
            inv_fail.append(f"{tag}: free list 중복")
        if used & set(fl):
            inv_fail.append(f"{tag}: 사용 중인 PR이 free list에 있음 {sorted(used & set(fl))}")
        if used | set(fl) != set(ALL_PR):
            inv_fail.append(f"{tag}: 잃어버린 PR {sorted(set(ALL_PR) - used - set(fl))}")
        if len(rob_live) > CFG["rob_size"]:
            inv_fail.append(f"{tag}: ROB 초과")
        for r in REGS:   # arch map always ready
            if not st["prf"][st["arch_map"][r]]["ready"]:
                inv_fail.append(f"{tag}: Arch Map {r}가 준비 안 된 PR을 가리킴")
        # precise state (checked at end of cycle: retire is the last phase)
        if ph_i == len(states) - 1:
            ref = seq_state(retired)
            got = {r: st["prf"][st["arch_map"][r]]["value"] for r in REGS}
            if got != ref:
                inv_fail.append(f"{tag}: Arch 상태 ≠ 순차 실행 {retired}개 결과")
            diff = [r for r in REGS if st["frontend_map"][r] != st["arch_map"][r]]
            if diff:
                spec_cycles[c["cycle"]] = diff
        for e, x in st["rs"].items():   # RS hold no values, V bit consistent with PRF
            if x is None:
                continue
            for s in x["src"]:
                if set(s) != {"valid", "pr"}:
                    inv_fail.append(f"{tag}: RS {e}에 PR/V 이외 필드 {sorted(s)}")
                if x["busy"] and not x["issued"] and s["valid"] and not st["prf"][s["pr"]]["ready"]:
                    inv_fail.append(f"{tag}: RS {e} V=1인데 {s['pr']} 미준비")
        for e in rob_live:
            if "value" in e:
                inv_fail.append(f"{tag}: ROB에 값 필드")
check("불변식 (모든 사이클·단계)", f"{n_checked}개 상태 검사, 위반 수", 0, len(inv_fail))

# ---- report -----------------------------------------------------------------------
L = ["# PRF 시뮬레이터 검증 보고서 (슬라이드 78–82)", ""]
bad = [r for r in results if not r[4]]
L += [f"- 검사 항목: **{len(results)}**, 실패: **{len(bad)}**", ""]
L += ["| 분류 | 항목 | 기대 | 결과 | 판정 |", "|---|---|---|---|---|"]
L += [f"| {g} | {i} | {e} | {o} | {'✅' if ok else '❌'} |" for g, i, e, o, ok in results]
if inv_fail:
    L += ["", "## 불변식 위반", ""] + [f"- {x}" for x in inv_fail]
L += ["", "## 타이밍 표 (슬라이드 71 형식: F D E R W, '-' = RS 대기, '·' = 완료 후 retire 대기)", "",
      "| | " + " | ".join(str(k) for k in range(1, P["total_cycles"] + 1)) + " |",
      "|---" * (P["total_cycles"] + 1) + "|"]
for i, row in enumerate(P["timing_table"]):
    L.append(f"| I{i+1} {PROG[i]['text_src_first']} | " + " | ".join(row) + " |")
L += ["", "## 투기적 상태 구간 (Frontend Map ≠ Arch Map, 사이클 끝 기준)", ""]
L += [f"- 사이클 {c}: {', '.join(rs)}" for c, rs in spec_cycles.items()]
open(os.path.join(ROOT, "out", "prf_verification_report.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")

# per-cycle state tables
T = ["# 사이클별 상태 표 (각 사이클 끝)", ""]
for c in P["cycles"]:
    st = c["state"]
    evs = [e for p in c["phases"] for e in p["events"]]
    T += [f"## 사이클 {c['cycle']}", ""]
    notes = []
    for e in evs:
        if e["type"] == "decode_alloc":
            notes.append(f"I{e['instr']+1} 디코드 → RS {e['rs']}, ROB {e['rob']}, 소스 " +
                         ", ".join(f"{s['reg']}→{s['pr']}(V={s['valid']})" for s in e["sources"]))
        elif e["type"] == "rename":
            notes.append(f"rename {e['reg']}: {e['old_pr']} → {e['dest_pr']}")
        elif e["type"] == "dispatch":
            notes.append(f"RS {e['rs']} 실행 시작, PRF 읽기 " +
                         ", ".join(f"{r['pr']}={r['value']}" for r in e["prf_reads"]))
        elif e["type"] == "writeback":
            notes.append(f"PRF[{e['dest_pr']}] ← {e['value']}, DestPR {e['dest_pr']} broadcast → " +
                         (", ".join(f"RS {m['rs']}.src{m['src']+1}" for m in e["matches"]) or "일치 없음"))
        elif e["type"] == "rob_done":
            notes.append(f"R: ROB {e['rob']} (I{e['instr']+1}) done=1")
        elif e["type"] == "retire":
            notes.append(f"W: I{e['instr']+1} retire, Arch {e['reg']}: {e['arch_prev']} → {e['arch_new']}, "
                         f"{e['freed_pr']} → free list")
    T += ["이벤트: " + ("; ".join(notes) if notes else "없음"), ""]
    T += ["| Reg | Frontend | Arch |", "|---|---|---|"]
    T += [f"| {r} | {st['frontend_map'][r]}{' *' if st['frontend_map'][r] != st['arch_map'][r] else ''} | {st['arch_map'][r]} |"
          for r in REGS]
    T += ["", "PRF (V, 값): " + ", ".join(
        f"{p}=({1 if v['ready'] else 0},{'' if v['value'] is None else v['value']})"
        for p, v in st["prf"].items()), ""]
    T += [f"free list: {' '.join(st['free_list'])}", ""]
    T += [f"ROB (head={st['rob_head']}, tail={st['rob_tail']}):", "", "| # | valid | dst | DestPR | oldPR | done |", "|---|---|---|---|---|---|"]
    T += [f"| {k} | {e['valid']} | {e['dst']} | {e['dest_pr']} | {e['old_pr']} | {e['done']} |"
          for k, e in enumerate(st["rob"]) if e]
    T += ["", "RS:", "", "| RS | V1 | PR1 | V2 | PR2 | DestPR | busy |", "|---|---|---|---|---|---|---|"]
    T += [f"| {k} | {x['src'][0]['valid']} | {x['src'][0]['pr']} | {x['src'][1]['valid']} | {x['src'][1]['pr']} | {x['dest_pr']} | {int(x['busy'])} |"
          for k, x in st["rs"].items() if x]
    T += [""]
open(os.path.join(ROOT, "out", "prf_state_tables.md"), "w", encoding="utf-8").write("\n".join(T) + "\n")

print("\n".join(L[:4]))
for g, i, e, o, ok in results:
    if not ok:
        print("FAIL", g, i, e, o)
print("\n".join(inv_fail[:20]))
sys.exit(1 if bad else 0)
