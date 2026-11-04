"""ROB + Physical Register File (PRF) + pointer machine (ETH DDCA L14, slides 78-82).

Runs the same 6-instruction program as tomasulo_sim.py and writes
out/prf_trace.json, the only input of the PRF renderer.

Structures (slides 79, 81, 82):
  PRF           PR1..PR22  - the ONLY place values live (+ ready bit, see ASSUMPTIONS)
  Frontend Map  R1..R11 -> PR   (renaming)
  Arch Map      R1..R11 -> PR   (precise state)
  ROB           16 entries, pointers only
  RS            ADD a-d / MUL x-t, per source: V bit + PR number (no value)
  unit output   DestPR + Value

Per-cycle phases (same rhythm as the Tomasulo video, plus retirement):
  (1) Decode/Rename   free PR -> dest, read + update Frontend Map, alloc ROB + RS
  (2) Wake-up/Select  both source V bits were 1 at the end of the previous cycle
  (3) Dispatch/Exec   read source VALUES from the PRF (slide 82 "Before Execution")
  (4) Writeback       last E cycle: write PRF[DestPR], broadcast DestPR tag -> RS V bits
                      R stage (cycle after last E): ROB done = 1
  (5) Retire          ROB head done since an earlier cycle -> Arch Map[dst] = DestPR,
                      old PR returned to the free list (MIPS R10000 style); 1 per cycle
Dispatch/execute timing is identical to tomasulo_sim.py (verified by verify_prf.py).
"""
from __future__ import annotations

import copy
import json
import math
import os
import sys
from collections import deque

sys.path.insert(0, os.path.dirname(__file__))
from tomasulo_sim import (LATENCY, OPFUNC, PROGRAM, REGS, RS_IDS, UNITS,  # noqa: E402
                          INIT_VALUES)

N_PR = 22                 # slide 79: PR1..PR22
ROB_SIZE = 16             # slide 74/75/79: Entry 0..15
VALUE_BITS = 64           # lecture: 64-bit values
SLOW_CYCLES = [2, 3, 7, 8, 10, 12, 14, 19, 20, 21]

ASSUMPTIONS = [
    "초기 상태: Frontend Map·Arch Map 모두 Ri → PRi (i=1..11), PRi 값 = i",
    "free list 초기값 = PR12–PR22 (앞에서부터 할당, 반환된 PR은 뒤에 추가); free PR의 값은 의미 없음(빈칸)",
    "PRF에 PR마다 ready 비트(V)를 둠 — 디코드 때 RS의 V 비트를 정하는 데 사용 (R10000의 busy-bit table 역할)",
    "ROB 엔트리 필드: valid, 목적 아키텍처 레지스터, DestPR, old PR(할당 직전 Frontend Map 값), done",
    "R(ROB 완료 기록) = 마지막 E 다음 사이클, W(retire) = R 다음 사이클부터, 사이클당 1개, program order",
    "retire 때 old PR을 free list로 반환 (MIPS R10000 방식)",
    "실행 가정은 기존과 동일: ADD 4·MUL 6사이클, adder·multiplier 각 1개, 파이프라인화",
]


def pr(n):
    return f"PR{n}"


class PRFSim:
    def __init__(self):
        self.prf = {pr(i): {"value": None, "ready": False} for i in range(1, N_PR + 1)}
        for i, r in enumerate(REGS, start=1):
            self.prf[pr(i)] = {"value": INIT_VALUES[r], "ready": True}
        self.front = {r: pr(i) for i, r in enumerate(REGS, start=1)}
        self.arch = dict(self.front)
        self.free = deque(pr(i) for i in range(len(REGS) + 1, N_PR + 1))
        self.rob = [None] * ROB_SIZE
        self.head = self.tail = 0
        self.rob_count = 0
        self.rs = {e: None for ids in RS_IDS.values() for e in ids}
        self.units = {op: [] for op in UNITS}
        self.fetched = None
        self.next_fetch = 0
        self.timing = [dict() for _ in PROGRAM]
        self.ist = [{"rs": None, "rob": None, "dest_pr": None, "old_pr": None, "D": None,
                     "E1": None, "E_last": None, "R": None, "W": None} for _ in PROGRAM]
        self.pending_R = []

    # ------------------------------------------------------------ snapshot ---
    def snapshot(self):
        return {
            "prf": copy.deepcopy(self.prf),
            "frontend_map": dict(self.front),
            "arch_map": dict(self.arch),
            "free_list": list(self.free),
            "rob": copy.deepcopy(self.rob),
            "rob_head": self.head,
            "rob_tail": self.tail,
            "rs": copy.deepcopy(self.rs),
            "units": {op: [dict(u, countdown=u["latency"] - u["stage"] + 1) for u in lst]
                      for op, lst in self.units.items()},
        }

    # ---------------------------------------------------------------- step ---
    def step(self, c):
        phases = []

        # (1) Decode / Rename ------------------------------------------------
        ev = []
        if self.fetched is not None:
            i = self.fetched
            op, s1, s2, dst = PROGRAM[i]
            free_rs = [e for e in RS_IDS[op] if self.rs[e] is None or not self.rs[e]["busy"]]
            if free_rs and self.free and self.rob_count < ROB_SIZE:
                ent = free_rs[0]
                srcs, src_ev = [], []
                for reg in (s1, s2):            # read Frontend Map BEFORE renaming dst
                    p = self.front[reg]
                    ok = self.prf[p]["ready"]
                    srcs.append({"valid": 1 if ok else 0, "pr": p})
                    src_ev.append({"reg": reg, "pr": p, "valid": 1 if ok else 0})
                dest = self.free.popleft()
                old = self.front[dst]
                self.front[dst] = dest
                self.prf[dest] = {"value": None, "ready": False}
                rob_i = self.tail
                self.rob[rob_i] = {"valid": 1, "instr": i, "dst": dst, "dest_pr": dest,
                                   "old_pr": old, "done": 0}
                self.tail = (self.tail + 1) % ROB_SIZE
                self.rob_count += 1
                ready = all(s["valid"] for s in srcs)
                self.rs[ent] = {"op": op, "instr": i, "src": srcs, "dest_pr": dest, "rob": rob_i,
                                "busy": True, "issued": False, "ready_at": c if ready else None,
                                "status": "ready" if ready else "waiting"}
                st = self.ist[i]
                st.update(rs=ent, rob=rob_i, dest_pr=dest, old_pr=old, D=c)
                self.timing[i][c] = "D"
                self.fetched = None
                ev.append({"type": "decode_alloc", "instr": i, "op": op, "rs": ent, "rob": rob_i,
                           "sources": src_ev})
                ev.append({"type": "rename", "instr": i, "reg": dst, "dest_pr": dest, "old_pr": old,
                           "free_list_after": list(self.free)})
            else:
                ev.append({"type": "decode_stall", "instr": i})
        if self.fetched is None and self.next_fetch < len(PROGRAM):
            i = self.next_fetch
            self.fetched, self.next_fetch = i, i + 1
            self.timing[i][c] = "F"
            ev.append({"type": "fetch", "instr": i})
        phases.append({"phase": "decode", "events": ev, "state": self.snapshot()})

        # (2) Wake-up / Select -------------------------------------------------
        ev, selected = [], {}
        for op in UNITS:
            cands = sorted((e for e in RS_IDS[op] if self.rs[e] and self.rs[e]["busy"]
                            and not self.rs[e]["issued"] and self.rs[e]["ready_at"] is not None
                            and self.rs[e]["ready_at"] < c), key=lambda e: self.rs[e]["instr"])
            accept = UNITS[op]["count"] if UNITS[op]["pipelined"] else (0 if self.units[op] else 1)
            for e in cands[:accept]:
                selected[op] = e
                ev.append({"type": "select", "rs": e, "instr": self.rs[e]["instr"], "unit": op})
            for e in RS_IDS[op]:
                x = self.rs[e]
                if x and x["busy"] and not x["issued"] and e not in cands:
                    ev.append({"type": "waiting", "rs": e, "instr": x["instr"],
                               "missing_prs": [s["pr"] for s in x["src"] if not s["valid"]],
                               "just_ready": x["ready_at"] == c})
        phases.append({"phase": "select", "events": ev, "state": self.snapshot()})

        # (3) Dispatch (read PRF) & Execute ------------------------------------------
        ev = []
        for op in UNITS:
            for u in self.units[op]:
                u["stage"] += 1
            if op in selected:
                e = selected[op]
                x = self.rs[e]
                x["issued"], x["status"] = True, "executing"
                reads = []
                for s in x["src"]:
                    v = self.prf[s["pr"]]
                    assert v["ready"], (c, e, s)
                    reads.append({"pr": s["pr"], "value": v["value"]})
                i = x["instr"]
                self.ist[i]["E1"] = c
                self.units[op].append({"rs": e, "instr": i, "stage": 1, "latency": LATENCY[op],
                                       "operands": [r["value"] for r in reads],
                                       "dest_pr": x["dest_pr"]})
                ev.append({"type": "dispatch", "rs": e, "instr": i, "unit": op,
                           "latency": LATENCY[op], "prf_reads": reads, "dest_pr": x["dest_pr"]})
            for u in self.units[op]:
                self.timing[u["instr"]][c] = f"E{u['stage']}"
                ev.append({"type": "execute", "rs": u["rs"], "instr": u["instr"], "unit": op,
                           "stage": u["stage"], "latency": u["latency"],
                           "countdown": u["latency"] - u["stage"] + 1})
        for i, st in enumerate(self.ist):
            if st["D"] is not None and st["D"] < c and (st["E1"] is None or st["E1"] > c) \
                    and c not in self.timing[i]:
                self.timing[i][c] = "-"
        phases.append({"phase": "execute", "events": ev, "state": self.snapshot()})

        # (4) Writeback: PRF write + DestPR broadcast; R stage --------------------------
        ev = []
        finishing = sorted(((op, u) for op in UNITS for u in self.units[op]
                            if u["stage"] == u["latency"]), key=lambda t: t[1]["instr"])
        for op, u in finishing:
            val = OPFUNC[op](*u["operands"])
            dest = u["dest_pr"]
            self.prf[dest] = {"value": val, "ready": True}
            matches = []
            for e, x in self.rs.items():
                if x is None:
                    continue
                for k, s in enumerate(x["src"]):
                    if not s["valid"] and s["pr"] == dest:
                        s["valid"] = 1
                        matches.append({"rs": e, "src": k})
                if x["busy"] and not x["issued"] and x["ready_at"] is None \
                        and all(s["valid"] for s in x["src"]):
                    x["ready_at"], x["status"] = c, "ready"
            self.rs[u["rs"]]["busy"], self.rs[u["rs"]]["status"] = False, "done"
            i = u["instr"]
            self.ist[i]["E_last"] = c
            self.pending_R.append((c + 1, i))
            self.units[op].remove(u)
            ev.append({"type": "writeback", "unit": op, "instr": i, "dest_pr": dest, "value": val,
                       "dst": PROGRAM[i][3], "matches": matches,
                       "tag_bits": math.ceil(math.log2(N_PR)),
                       "after": self.snapshot()})
        for (rc, i) in [p for p in self.pending_R if p[0] == c]:
            rob_i = self.ist[i]["rob"]
            self.rob[rob_i]["done"] = 1
            self.ist[i]["R"] = c
            self.timing[i][c] = "R"
            ev.append({"type": "rob_done", "instr": i, "rob": rob_i})
        phases.append({"phase": "writeback", "events": ev, "state": self.snapshot()})

        # (5) Retire ---------------------------------------------------------------
        ev = []
        h = self.rob[self.head] if self.rob_count else None
        if h and h["valid"] and h["done"] and self.ist[h["instr"]]["R"] < c:
            i = h["instr"]
            prev_arch = self.arch[h["dst"]]
            self.arch[h["dst"]] = h["dest_pr"]
            self.free.append(h["old_pr"])
            h["valid"] = 0
            rob_i = self.head
            self.head = (self.head + 1) % ROB_SIZE
            self.rob_count -= 1
            self.ist[i]["W"] = c
            self.timing[i][c] = "W"
            ev.append({"type": "retire", "instr": i, "rob": rob_i, "reg": h["dst"],
                       "arch_prev": prev_arch, "arch_new": h["dest_pr"], "freed_pr": h["old_pr"],
                       "free_list_after": list(self.free)})
        elif h and h["valid"]:
            why = "not_done" if not h["done"] else "done_this_cycle"
            ev.append({"type": "retire_wait", "instr": h["instr"], "rob": self.head, "why": why})
        # instructions done but not yet retired: '·'
        for i, st in enumerate(self.ist):
            if st["R"] is not None and st["R"] < c and (st["W"] is None or st["W"] > c) \
                    and c not in self.timing[i]:
                self.timing[i][c] = "·"
        phases.append({"phase": "retire", "events": ev, "state": self.snapshot()})

        outlook = [{"rs": e, "instr": x["instr"], "ready_next": all(s["valid"] for s in x["src"]),
                    "missing_prs": [s["pr"] for s in x["src"] if not s["valid"]]}
                   for e, x in self.rs.items() if x and x["busy"] and not x["issued"]]
        return phases, outlook


def run():
    sim = PRFSim()
    cycles = [{"cycle": 0, "phases": [], "state": sim.snapshot(),
               "column": [""] * len(PROGRAM), "outlook": []}]
    c = 0
    while True:
        c += 1
        phases, outlook = sim.step(c)
        cycles.append({"cycle": c, "phases": phases, "state": phases[-1]["state"],
                       "column": [sim.timing[i].get(c, "") for i in range(len(PROGRAM))],
                       "outlook": outlook})
        if all(st["W"] is not None for st in sim.ist):
            break
        if c > 200:
            raise RuntimeError("did not terminate")
    table = [[sim.timing[i].get(k, "") for k in range(1, c + 1)] for i in range(len(PROGRAM))]
    return sim, cycles, table, c


def replication_example(sim, instr=4):
    """Slide 75/78 machine (values everywhere) at the moment instruction `instr`
    retires: where does its result value live?  Built from the Tomasulo trace
    (RS, frontend RF) plus the ROB/retire timing of this simulation."""
    old_path = os.path.join(os.path.dirname(__file__), "..", "out", "trace.json")
    with open(old_path, encoding="utf-8") as fh:
        old = json.load(fh)
    c = sim.ist[instr]["W"]
    ost = old["cycles"][min(c, len(old["cycles"]) - 1)]["state"]
    # architectural RF after the first instr+1 instructions retired (in order)
    v = dict(INIT_VALUES)
    for op, s1, s2, d in PROGRAM[:instr + 1]:
        v[d] = OPFUNC[op](v[s1], v[s2])
    val = v[PROGRAM[instr][3]]
    rob = []
    for i, (op, s1, s2, d) in enumerate(PROGRAM):
        st = sim.ist[i]
        if st["W"] < c:
            rob.append(None)                       # already retired, entry freed
        else:
            done = st["R"] is not None and st["R"] < c
            vv = None
            if done:
                # value produced by instruction i (sequential semantics)
                w = dict(INIT_VALUES)
                for op2, a, b, dd in PROGRAM[:i + 1]:
                    w[dd] = OPFUNC[op2](w[a], w[b])
                vv = w[d]
            rob.append({"valid": 1, "dst": d, "value": vv, "done": 1 if done else 0, "instr": i})
    locs = []
    for e, row in ost["rs_display"].items():
        for k in (2, 5):
            if row[k] == str(val):
                locs.append({"structure": "rs", "entry": e, "field": k})
    for r, row in ost["rat_display"].items():
        if row[2] == str(val):
            locs.append({"structure": "frontend", "reg": r})
    for k, e in enumerate(rob):
        if e and e["value"] == val:
            locs.append({"structure": "rob", "entry": sim.ist[e["instr"]]["rob"]})
    for r in REGS:
        if v[r] == val:
            locs.append({"structure": "arch", "reg": r})
    return {"instr": instr, "cycle": c, "value": val,
            "rs_display": ost["rs_display"], "frontend_display": ost["rat_display"],
            "rob": rob, "arch_values": v, "locations": locs}


def main(out_path):
    sim, cycles, table, total = run()
    final = cycles[-1]["state"]
    n_rs = sum(len(v) for v in RS_IDS.values())
    trace = {
        "meta": {"title": "ROB + PRF + pointers - ETH DDCA L14 slides 78-82",
                 "slides": "PDF page -> slide: 1=36, 2=40, 3=63, 4-9=71-76, 10-14=78-82"},
        "config": {
            "program": [{"op": op, "src": [s1, s2], "dst": d,
                         "text_src_first": f"{op} {s1}, {s2} → {d}",
                         "text_dst_first": f"{op} {d} ← {s1}, {s2}"} for op, s1, s2, d in PROGRAM],
            "latency": LATENCY, "units": UNITS, "rs_ids": RS_IDS, "registers": REGS,
            "initial_values": INIT_VALUES, "n_pr": N_PR, "rob_size": ROB_SIZE,
            "assumptions": ASSUMPTIONS,
        },
        "storage_comparison": {
            # value-holding fields in the slide 75/78 machine vs slide 79/81 machine
            "tomasulo_rob": {"rs_value_fields": n_rs * 2, "frontend_rf_values": len(REGS),
                             "rob_value_fields": ROB_SIZE, "arch_rf_values": len(REGS)},
            "prf": {"prf_values": N_PR},
            "value_bits": VALUE_BITS,
            "tomasulo_tag_bits": math.ceil(math.log2(n_rs)),
            "prf_tag_bits": math.ceil(math.log2(N_PR)),
        },
        "presentation": {"slow_cycles": SLOW_CYCLES},
        "cycles": cycles,
        "timing_table": table,
        "instructions": sim.ist,
        "total_cycles": total,
        "final_arch_values": {r: final["prf"][final["arch_map"][r]]["value"] for r in REGS},
        "final_arch_map": final["arch_map"],
    }
    trace["replication_example"] = replication_example(sim)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(trace, fh, ensure_ascii=False, indent=1)
    print(f"wrote {out_path}: {total} cycles; arch values {trace['final_arch_values']}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else
         os.path.join(os.path.dirname(__file__), "..", "out", "prf_trace.json"))
