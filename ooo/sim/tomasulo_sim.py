"""Cycle-accurate Tomasulo simulator for ETH DDCA L14 (slides 36-63).

Writes out/trace.json, which is the ONLY input of the Manim renderer.

Model (rules derived from slides 41-63, see README.md):
  * One instruction fetched per cycle (F), decoded/renamed the next cycle (D).
  * D = Decode & Allocate: take the first free RS entry of the right type
    (ADD: a,b,c,d / MUL: x,y,z,t), copy each source from the RAT (value if
    valid, otherwise tag), then rename the destination: RAT[dst] = (V=0, tag).
  * An entry may be selected in cycle c only if both sources were valid at the
    END of cycle c-1 ("ready to execute in the next cycle", slides 43/45/46/49).
  * Adder and multiplier are pipelined: each accepts one new op per cycle;
    oldest ready entry first.
  * In the last execute cycle E_n the unit broadcasts (tag, value) on its own
    Tag/Value bus; matching RS sources and RAT entries capture it in that same
    cycle (slides 49, 50, 52, 55, 58, 62).  The timing table shows W in the
    following cycle.  The entry is freed (busy=0) but - as on the slides - its
    contents stay visible.
  * Phase order inside a cycle: (1) Decode&Allocate -> (2) Wake-up/Select ->
    (3) Dispatch&Execute -> (4) Broadcast.  Readiness is latched (rule above),
    so a value captured in (4) is used no earlier than the next cycle.
"""
from __future__ import annotations

import copy
import json
import os
import sys

# ---------------------------------------------------------------- inputs ---
# Slide 36 (dst-first notation) == slide 40 (src-first notation).
PROGRAM = [
    # op,   src1,  src2,  dst
    ("MUL", "R1", "R2", "R3"),
    ("ADD", "R3", "R4", "R5"),
    ("ADD", "R2", "R6", "R7"),
    ("ADD", "R8", "R9", "R10"),
    ("MUL", "R7", "R10", "R11"),
    ("ADD", "R5", "R11", "R5"),
]
LATENCY = {"ADD": 4, "MUL": 6}                 # slide 36
UNITS = {"ADD": {"name": "adder", "count": 1, "pipelined": True},
         "MUL": {"name": "multiplier", "count": 1, "pipelined": True}}
RS_IDS = {"ADD": ["a", "b", "c", "d"], "MUL": ["x", "y", "z", "t"]}  # slide 40
REGS = [f"R{i}" for i in range(1, 12)]
INIT_VALUES = {f"R{i}": i for i in range(1, 12)}  # slide 40
OPFUNC = {"ADD": lambda a, b: a + b, "MUL": lambda a, b: a * b}

# Presentation hints (not simulation values): which cycles to play slowly.
SLOW_CYCLES = [3, 8, 17, 18, 19, 20]
# Slide number(s) showing each cycle (slide 41 = cycle 0; cycle 8 spans 3).
def slides_for_cycle(c: int) -> list[int]:
    if c < 8:
        return [41 + c]
    if c == 8:
        return [49, 50, 51]
    return [43 + c]


# ------------------------------------------------------------ simulator ---
class Sim:
    def __init__(self):
        self.rat = {r: {"valid": 1, "tag": None, "value": INIT_VALUES[r]} for r in REGS}
        self.rs = {e: None for ids in RS_IDS.values() for e in ids}
        self.units = {op: [] for op in UNITS}   # in-flight ops
        self.fetched = None                      # index of instr fetched last cycle, waiting for D
        self.next_fetch = 0
        self.timing = [dict() for _ in PROGRAM]  # instr -> {cycle: label}
        self.instr_state = [{"rs": None, "D": None, "E1": None, "done": None, "W": None}
                            for _ in PROGRAM]
        self.pending_w = []                      # (cycle, instr)

    # ---- display helpers (exactly the slide notation) ----
    def rat_display(self):
        out = {}
        for r in REGS:
            e = self.rat[r]
            out[r] = ["1", "", str(e["value"])] if e["valid"] else ["0", e["tag"], ""]
        return out

    def rs_display(self):
        out = {}
        for k, e in self.rs.items():
            if e is None:
                out[k] = ["", "", "", "", "", ""]
                continue
            row = []
            for s in e["src"]:
                row += (["1", "~", str(s["value"])] if s["valid"] else ["0", s["tag"], ""])
            out[k] = row
        return out

    def snapshot(self):
        return {
            "rat": copy.deepcopy(self.rat),
            "rat_display": self.rat_display(),
            "rs": copy.deepcopy(self.rs),
            "rs_display": self.rs_display(),
            "units": {op: [dict(u, countdown=u["latency"] - u["stage"] + 1) for u in lst]
                      for op, lst in self.units.items()},
        }

    # ---- one cycle ----
    def step(self, c: int):
        phases = []

        # (1) Decode & Allocate ------------------------------------------------
        ev, changed = [], []
        decoded_now = None
        if self.fetched is not None:
            i = self.fetched
            op, s1, s2, dst = PROGRAM[i]
            free = [e for e in RS_IDS[op] if self.rs[e] is None or not self.rs[e]["busy"]]
            if free:
                ent = free[0]
                srcs, src_ev = [], []
                for k, reg in enumerate((s1, s2)):
                    r = self.rat[reg]
                    if r["valid"]:
                        srcs.append({"valid": 1, "tag": None, "value": r["value"]})
                        src_ev.append({"reg": reg, "copied": "value", "value": r["value"]})
                    else:
                        srcs.append({"valid": 0, "tag": r["tag"], "value": None})
                        src_ev.append({"reg": reg, "copied": "tag", "tag": r["tag"]})
                    changed.append({"table": "rs", "row": ent, "src": k})
                    changed.append({"table": "rat_read", "row": reg})
                ready = all(s["valid"] for s in srcs)
                self.rs[ent] = {"op": op, "instr": i, "src": srcs, "busy": True,
                                "status": "ready" if ready else "waiting",
                                "ready_at": c if ready else None, "issued": False}
                old = self.rat[dst]["tag"] if not self.rat[dst]["valid"] else None
                self.rat[dst] = {"valid": 0, "tag": ent, "value": None}
                changed.append({"table": "rat", "row": dst})
                self.instr_state[i]["rs"] = ent
                self.instr_state[i]["D"] = c
                self.timing[i][c] = "D"
                decoded_now = i
                self.fetched = None
                ev.append({"type": "decode_alloc", "instr": i, "op": op, "rs": ent,
                           "sources": src_ev})
                ev.append({"type": "rename", "instr": i, "reg": dst, "tag": ent,
                           "previous_tag": old})
            else:
                ev.append({"type": "decode_stall", "instr": i, "reason": "no free RS"})
        if self.fetched is None and self.next_fetch < len(PROGRAM):
            i = self.next_fetch
            self.fetched = i
            self.next_fetch += 1
            self.timing[i][c] = "F"
            ev.append({"type": "fetch", "instr": i})
        phases.append({"phase": "decode", "events": ev, "changed": changed,
                       "state": self.snapshot()})

        # (2) Wake-up / Select ---------------------------------------------------
        ev, changed, selected = [], [], {}
        for op in UNITS:
            cands = [e for e in RS_IDS[op]
                     if self.rs[e] and self.rs[e]["busy"] and not self.rs[e]["issued"]
                     and self.rs[e]["ready_at"] is not None and self.rs[e]["ready_at"] < c]
            cands.sort(key=lambda e: self.rs[e]["instr"])
            accept = 1 if UNITS[op]["pipelined"] else (0 if self.units[op] else 1)
            accept *= UNITS[op]["count"]
            for e in cands[:accept]:
                selected[op] = e
                ev.append({"type": "select", "rs": e, "instr": self.rs[e]["instr"], "unit": op})
                changed.append({"table": "rs_row", "row": e})
            for e in cands[accept:]:
                ev.append({"type": "ready_not_selected", "rs": e, "unit": op})
            for e in RS_IDS[op]:
                x = self.rs[e]
                if x and x["busy"] and not x["issued"] and e not in cands:
                    missing = [s["tag"] for s in x["src"] if not s["valid"]]
                    ev.append({"type": "waiting", "rs": e, "instr": x["instr"],
                               "missing_tags": missing,
                               "just_ready": x["ready_at"] == c})
        phases.append({"phase": "select", "events": ev, "changed": changed,
                       "state": self.snapshot()})

        # (3) Dispatch & Execute -------------------------------------------------
        ev, changed = [], []
        for op in UNITS:
            for u in self.units[op]:
                u["stage"] += 1
            if op in selected:
                e = selected[op]
                x = self.rs[e]
                x["issued"], x["status"] = True, "executing"
                i = x["instr"]
                self.instr_state[i]["E1"] = c
                self.units[op].append({"rs": e, "instr": i, "stage": 1,
                                       "latency": LATENCY[op],
                                       "operands": [s["value"] for s in x["src"]]})
                ev.append({"type": "dispatch", "rs": e, "instr": i, "unit": op,
                           "latency": LATENCY[op],
                           "operands": [s["value"] for s in x["src"]]})
            for u in self.units[op]:
                self.timing[u["instr"]][c] = f"E{u['stage']}"
                ev.append({"type": "execute", "rs": u["rs"], "instr": u["instr"], "unit": op,
                           "stage": u["stage"], "latency": u["latency"],
                           "countdown": u["latency"] - u["stage"] + 1})
        # instructions sitting in an RS (decoded earlier, not executing): '-'
        for i, st in enumerate(self.instr_state):
            if st["D"] is not None and st["D"] < c and (st["E1"] is None or st["E1"] > c) \
                    and c not in self.timing[i]:
                self.timing[i][c] = "-"
        phases.append({"phase": "execute", "events": ev, "changed": changed,
                       "state": self.snapshot()})

        # (4) Broadcast ------------------------------------------------------------
        ev, changed = [], []
        # separate buses -> logically simultaneous; listed oldest-first, which is
        # also the order slides 49 (MUL x) and 50 (ADD b) present them.
        finishing = sorted(((op, u) for op in UNITS for u in self.units[op]
                            if u["stage"] == u["latency"]), key=lambda t: t[1]["instr"])
        for op, u in finishing:
            if True:
                tag = u["rs"]
                val = OPFUNC[op](*u["operands"])
                matches = []
                for e, x in self.rs.items():
                    if x is None:
                        continue
                    for k, s in enumerate(x["src"]):
                        if not s["valid"] and s["tag"] == tag:
                            s["valid"], s["value"], s["tag"] = 1, val, None
                            matches.append({"kind": "rs", "rs": e, "src": k})
                            changed.append({"table": "rs", "row": e, "src": k})
                    if x["busy"] and not x["issued"] and all(s["valid"] for s in x["src"]) \
                            and x["ready_at"] is None:
                        x["ready_at"], x["status"] = c, "ready"
                for r in REGS:
                    if not self.rat[r]["valid"] and self.rat[r]["tag"] == tag:
                        self.rat[r] = {"valid": 1, "tag": None, "value": val}
                        matches.append({"kind": "rat", "reg": r})
                        changed.append({"table": "rat", "row": r})
                done = self.rs[tag]
                done["busy"], done["status"] = False, "done"
                i = u["instr"]
                self.instr_state[i]["done"] = c
                self.instr_state[i]["W"] = c + 1
                self.pending_w.append((c + 1, i))
                ev.append({"type": "broadcast", "unit": op, "tag": tag, "value": val,
                           "instr": i, "dst": PROGRAM[i][3], "matches": matches,
                           # state right after THIS broadcast (slides 49/50 show
                           # the MUL and ADD broadcasts of cycle 8 one at a time)
                           "after": {"rat_display": self.rat_display(),
                                     "rs_display": self.rs_display()}})
                self.units[op].remove(u)
        for (wc, i) in [p for p in self.pending_w if p[0] == c]:
            self.timing[i][c] = "W"
            ev.append({"type": "writeback", "instr": i})
        phases.append({"phase": "broadcast", "events": ev, "changed": changed,
                       "state": self.snapshot()})

        # end-of-cycle outlook (slide boxes "... ready to execute in the next cycle")
        outlook = []
        for e, x in self.rs.items():
            if x and x["busy"] and not x["issued"]:
                outlook.append({"rs": e, "instr": x["instr"],
                                "ready_next": all(s["valid"] for s in x["src"]),
                                "missing_tags": [s["tag"] for s in x["src"] if not s["valid"]]})
        return phases, outlook

    def column(self, c):
        return [self.timing[i].get(c, "") for i in range(len(PROGRAM))]

    def finished(self):
        return all(st["W"] is not None for st in self.instr_state) and \
            not any(p[0] >= self._c for p in self.pending_w if p[0] > self._c)


def run_tomasulo():
    sim = Sim()
    cycles = [{"cycle": 0, "slides": slides_for_cycle(0), "phases": [],
               "state": sim.snapshot(), "column": [""] * len(PROGRAM), "outlook": []}]
    c = 0
    while True:
        c += 1
        sim._c = c
        phases, outlook = sim.step(c)
        cycles.append({"cycle": c, "slides": slides_for_cycle(c), "phases": phases,
                       "state": phases[-1]["state"], "column": sim.column(c),
                       "outlook": outlook})
        last_w = max((st["W"] or 0) for st in sim.instr_state)
        if all(st["W"] is not None for st in sim.instr_state) and c >= last_w:
            break
        if c > 200:
            raise RuntimeError("simulation did not terminate")
    table = [[sim.timing[i].get(k, "") for k in range(1, c + 1)] for i in range(len(PROGRAM))]
    return cycles, table, sim.instr_state, c


# ------------------------------------------------ in-order reference model ---
def run_inorder(forwarding: bool):
    """In-order-dispatch pipeline of slide 37 (F, D, E..., W; one F and one D slot).

    An instruction leaves D (starts E1) only when it is the oldest, the unit
    accepts it (pipelined: next cycle after the previous dispatch) and its
    producers are done:  with forwarding  E1 >= producer_lastE + 1
                         w/o forwarding   E1 >= producer_W + 2 (re-read in D after W)
    The next instruction enters D in the cycle the previous one leaves it, and
    the F slot frees when its instruction moves into D.
    """
    last_writer = {}
    rows, f, prev_e, prev_d = [], 1, None, None
    for i, (op, s1, s2, dst) in enumerate(PROGRAM):
        lat = LATENCY[op]
        d = f + 1 if prev_e is None else max(f + 1, prev_e)
        e = d + 1 if prev_e is None else max(d + 1, prev_e + 1)
        reread = None
        for s in (s1, s2):
            if s in last_writer:
                pe, pl = last_writer[s]
                need = pe + pl if forwarding else pe + pl + 2
                if need > e:
                    e = need
                    reread = None if forwarding else e - 1
        w = e + lat
        cells = {f: "F", d: "D"}
        if reread is not None:
            cells[reread] = "D"
            for k in range(d + 1, reread):
                cells[k] = "-"
        for k in range(lat):
            cells[e + k] = f"E{k+1}"
        cells[w] = "W"
        if not forwarding:  # slide 37 (top) marks stalls with '-'
            for k in range(f + 1, d):
                cells.setdefault(k, "-")
        rows.append({"instr": i, "F": f, "D": d, "E1": e, "W": w, "cells": cells})
        last_writer[dst] = (e, lat)
        prev_e = e
        f = d
    total = max(r["W"] for r in rows)
    table = [[r["cells"].get(k, "") for k in range(1, total + 1)] for r in rows]
    return {"total_cycles": total, "table": table,
            "rows": [{k: v for k, v in r.items() if k != "cells"} for r in rows]}


def main(out_path):
    cycles, table, istate, total = run_tomasulo()
    final = cycles[-1]["state"]["rat"]
    trace = {
        "meta": {
            "title": "Tomasulo's algorithm - ETH DDCA L14 slides 36-63",
            "slide_offset_note": "PDF page + 35 = slide number",
        },
        "config": {
            "program": [{"op": op, "src": [s1, s2], "dst": d,
                         "text_src_first": f"{op} {s1}, {s2} → {d}",
                         "text_dst_first": f"{op} {d} ← {s1}, {s2}"}
                        for op, s1, s2, d in PROGRAM],
            "latency": LATENCY,
            "units": UNITS,
            "rs_ids": RS_IDS,
            "registers": REGS,
            "initial_values": INIT_VALUES,
            "nonpipelined_cycles_slide36": 50,
        },
        "presentation": {"slow_cycles": SLOW_CYCLES},
        "cycles": cycles,
        "timing_table": table,
        "instructions": istate,
        "total_cycles": total,
        "final_registers": {r: final[r]["value"] for r in REGS},
        "inorder": {"forwarding": run_inorder(True), "no_forwarding": run_inorder(False)},
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(trace, fh, ensure_ascii=False, indent=1)
    print(f"wrote {out_path}: {total} cycles, final {trace['final_registers']}")
    print(f"in-order: fwd={trace['inorder']['forwarding']['total_cycles']} "
          f"no-fwd={trace['inorder']['no_forwarding']['total_cycles']}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else
         os.path.join(os.path.dirname(__file__), "..", "out", "trace.json"))
