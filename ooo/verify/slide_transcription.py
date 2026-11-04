"""Hand transcription of slides 41-63 (read from 200-dpi page images, NOT from
the PDF text layer).  Each slide is written literally, including the partially
built cells that appear on slides 43-45 and 49-50.

Notation (identical to the slides):
  RAT row  = [Valid, Tag, Value]        ('' = empty / grey cell)
  RS  row  = [V1, Tag1, Value1, V2, Tag2, Value2]
  timing column = the newest column (cycle N) of the slide, rows = instr 1..6.

To keep the file readable, each slide lists only the cells that differ from the
previous slide (`rat` / `rs` deltas).  Every slide image was compared cell by
cell with its predecessor when writing these deltas, and older timing columns
of each slide were checked to equal the same columns of slide 63 (the only
exceptions are slides 49/50, column 8, written out below).
"""

E6 = ["", "", "", "", "", ""]

INIT_RAT = {f"R{i}": ["1", "", str(i)] for i in range(1, 12)}
INIT_RS = {k: list(E6) for k in "abcdxyzt"}

# Full timing table of slide 63 (cycles 1..20)
SLIDE63_TABLE = [
    ["F", "D", "E1", "E2", "E3", "E4", "E5", "E6", "W"] + [""] * 11,
    ["", "F", "D", "-", "-", "-", "-", "-", "E1", "E2", "E3", "E4", "W"] + [""] * 7,
    ["", "", "F", "D", "E1", "E2", "E3", "E4", "W"] + [""] * 11,
    ["", "", "", "F", "D", "E1", "E2", "E3", "E4", "W"] + [""] * 10,
    ["", "", "", "", "F", "D", "-", "-", "-", "E1", "E2", "E3", "E4", "E5", "E6", "W"] + [""] * 4,
    ["", "", "", "", "", "F", "D", "-", "-", "-", "-", "-", "-", "-", "-", "E1", "E2", "E3", "E4", "W"],
]

# claims made by the text boxes / annotations of each slide
#   ("alloc", rs, instr#)         instruction decoded & allocated into RS
#   ("rename", reg, tag)
#   ("dispatch", rs)              starts executing this cycle (E1)
#   ("ready_next", rs, bool)      "... is (NOT) ready to execute in the next cycle"
#   ("broadcast", unit, tag, value)
#   ("timer", unit, n)            "n Cycles" stopwatch next to unit
SLIDES = [
    dict(slide=41, cycle=0, col=None, rat={}, rs={}, claims=[]),
    dict(slide=42, cycle=1, col=["F", "", "", "", "", ""], rat={}, rs={}, claims=[]),
    dict(slide=43, cycle=2, col=["D", "F", "", "", "", ""],
         rat={"R3": ["0", "x", ""]},
         rs={"x": ["", "~", "", "", "~", ""]},           # only the tag cells are drawn
         claims=[("alloc", "x", 1), ("rename", "R3", "x"), ("ready_next", "x", True)]),
    dict(slide=44, cycle=3, col=["E1", "D", "F", "", "", ""],
         rat={"R5": ["0", "a", ""]},
         rs={"x": ["1", "~", "1", "1", "~", "2"],
             "a": ["", "", "", "", "~", ""]},             # only src2 tag drawn
         claims=[("dispatch", "x"), ("alloc", "a", 2), ("rename", "R5", "a"),
                 ("timer", "MUL", 6), ("ready_next", "a", False)]),
    dict(slide=45, cycle=4, col=["E2", "-", "D", "F", "", ""],
         rat={"R7": ["0", "b", ""]},
         rs={"a": ["0", "x", "", "1", "~", "4"],
             "b": ["", "~", "", "", "~", ""]},            # only tag cells drawn
         claims=[("alloc", "b", 3), ("rename", "R7", "b"), ("ready_next", "b", True)]),
    dict(slide=46, cycle=5, col=["E3", "-", "E1", "D", "F", ""],
         rat={"R10": ["0", "c", ""]},
         rs={"b": ["1", "~", "2", "1", "~", "6"],
             "c": ["1", "~", "8", "1", "~", "9"]},
         claims=[("dispatch", "b"), ("timer", "ADD", 4), ("alloc", "c", 4),
                 ("rename", "R10", "c"), ("ready_next", "c", True)]),
    dict(slide=47, cycle=6, col=["E4", "-", "E2", "E1", "D", "F"],
         rat={"R11": ["0", "y", ""]},
         rs={"y": ["0", "b", "", "0", "c", ""]},
         claims=[("alloc", "y", 5), ("rename", "R11", "y")]),
    dict(slide=48, cycle=7, col=["E5", "-", "E3", "E2", "-", "D"],
         rat={"R5": ["0", "d", ""]},
         rs={"d": ["0", "a", "", "0", "y", ""]},
         claims=[("alloc", "d", 6), ("rename", "R5", "d")]),
    dict(slide=49, cycle=8, sub=1, col=["E6", "", "", "", "", ""],
         rat={"R3": ["1", "", "2"]},
         rs={"a": ["1", "", "2", "1", "~", "4"]},          # tag cell still blank
         claims=[("broadcast", "MUL", "x", 2), ("ready_next", "a", True)]),
    dict(slide=50, cycle=8, sub=2, col=["E6", "-", "E4", "", "", ""],
         rat={"R7": ["1", "", "8"]},
         rs={"a": ["1", "~", "2", "1", "~", "4"],
             "y": ["1", "", "8", "0", "c", ""]},           # tag cell still blank
         claims=[("broadcast", "ADD", "b", 8), ("ready_next", "y", False)]),
    dict(slide=51, cycle=8, sub=3, col=["E6", "-", "E4", "E3", "-", "-"],
         rat={},
         rs={"y": ["1", "~", "8", "0", "c", ""]},
         claims=[]),
    dict(slide=52, cycle=9, col=["W", "E1", "W", "E4", "-", "-"],
         rat={"R10": ["1", "", "17"]},
         rs={"y": ["1", "~", "8", "1", "~", "17"]},
         claims=[("broadcast", "ADD", "c", 17), ("dispatch", "a"), ("ready_next", "y", True)]),
    dict(slide=53, cycle=10, col=["", "E2", "", "W", "E1", "-"], rat={}, rs={},
         claims=[("dispatch", "y")]),
    dict(slide=54, cycle=11, col=["", "E3", "", "", "E2", "-"], rat={}, rs={}, claims=[]),
    dict(slide=55, cycle=12, col=["", "E4", "", "", "E3", "-"], rat={},
         rs={"d": ["1", "~", "6", "0", "y", ""]},
         claims=[("broadcast", "ADD", "a", 6)]),
    dict(slide=56, cycle=13, col=["", "W", "", "", "E4", "-"], rat={}, rs={}, claims=[]),
    dict(slide=57, cycle=14, col=["", "", "", "", "E5", "-"], rat={}, rs={}, claims=[]),
    dict(slide=58, cycle=15, col=["", "", "", "", "E6", "-"],
         rat={"R11": ["1", "", "136"]},
         rs={"d": ["1", "~", "6", "1", "~", "136"]},
         claims=[("broadcast", "MUL", "y", 136), ("ready_next", "d", True)]),
    dict(slide=59, cycle=16, col=["", "", "", "", "W", "E1"], rat={}, rs={},
         claims=[("dispatch", "d")]),
    dict(slide=60, cycle=17, col=["", "", "", "", "", "E2"], rat={}, rs={}, claims=[]),
    dict(slide=61, cycle=18, col=["", "", "", "", "", "E3"], rat={}, rs={}, claims=[]),
    dict(slide=62, cycle=19, col=["", "", "", "", "", "E4"],
         rat={"R5": ["1", "", "142"]}, rs={},
         claims=[("broadcast", "ADD", "d", 142)]),
    dict(slide=63, cycle=20, col=["", "", "", "", "", "W"], rat={}, rs={}, claims=[]),
]

# Slides that explicitly draw a broadcast on a Tag/Value bus.  No other slide
# shows a value under an execution unit.
BROADCAST_SLIDES = {49, 50, 52, 55, 58, 62}

# Slides 37 (bottom) and 38: handwritten timelines (cycle of F, D, first E, W)
SLIDE37_FWD = {"total": 25, "rows": [  # (F, D, E1, W)
    (1, 2, 3, 9), (2, 3, 9, 13), (3, 9, 10, 14), (9, 10, 11, 15), (10, 11, 15, 21), (11, 15, 21, 25)]}
SLIDE37_NOFWD_TOTAL = 31
SLIDE38_OOO = {"total": 20, "rows": [
    (1, 2, 3, 9), (2, 3, 9, 13), (3, 4, 5, 9), (4, 5, 6, 10), (5, 6, 10, 16), (6, 7, 16, 20)]}


def full_states():
    """Expand deltas into the literal full tables of every slide."""
    rat = {k: list(v) for k, v in INIT_RAT.items()}
    rs = {k: list(v) for k, v in INIT_RS.items()}
    out = []
    for s in SLIDES:
        for k, v in s["rat"].items():
            rat[k] = list(v)
        for k, v in s["rs"].items():
            rs[k] = list(v)
        n = s["cycle"]
        if s["slide"] in (49, 50):
            table = [row[:7] + [s["col"][i]] for i, row in enumerate(SLIDE63_TABLE)]
        else:
            table = [row[:n] for row in SLIDE63_TABLE]
        if s["col"] is not None:
            assert [t[-1] for t in table] == s["col"], s["slide"]
        out.append(dict(s, rat_full={k: list(v) for k, v in rat.items()},
                        rs_full={k: list(v) for k, v in rs.items()}, table=table))
    return out
