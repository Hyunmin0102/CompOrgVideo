"""The common program run by all three inorder videos.

Hazards are described in terms of the *dynamic* instruction stream
(the skipped instruction after the taken beq is never executed).

Index (1-based)  ->  why it is there
"""
from __future__ import annotations

PROGRAM = [
    "lw   $t0, 0($s0)",       # I1  t0 = Mem[0x10] = 7: the load whose value is used immediately
    "add  $t1, $t0, $s1",     # I2  uses t0 right after the lw -> load-use (1 stall in pipeline)
    "sub  $t2, $t1, $s2",     # I3  uses t1 from I2 (1 back) -> MEM->EX forwarding
    "and  $t3, $t1, $s3",     # I4  uses t1 from I2 (2 back) -> WB->EX forwarding
    "sw   $t1, 4($s0)",       # I5  the store; t1 is 3 back -> no forwarding needed
    "slt  $t4, $s1, $s2",     # I6  independent; puts distance between beq and its operands
    "beq  $t2, $t3, skip",    # I7  t2 (4 back) == t3 (3 back) == 4 -> taken, no compare stall
    "add  $s4, $s1, $s1",     # I8  must be skipped; if it ran, $s4 would become 10
    "skip: addi $t5, $t3, 10",  # I9  branch target; t3 is far back
    "or   $t6, $t4, $s3",     # I10 last instruction; t4 from I6 is far back
]

REASONS = [
    "Mem[0x10]=7을 읽어 오는 load. 바로 다음 명령어가 이 값을 쓴다.",
    "lw 결과 $t0을 곧바로 사용 → load-use 의존 (파이프라인 1 stall).",
    "바로 앞 add의 결과 $t1 사용 → 거리 1 RAW (MEM→EX forwarding).",
    "두 칸 앞 add의 결과 $t1 사용 → 거리 2 RAW (WB→EX forwarding). 결과 4.",
    "sw: $t1(=12)을 Mem[0x14]에 저장. $t1은 세 칸 앞이라 forwarding 불필요.",
    "slt: 독립 명령어. beq와 그 피연산자 사이 간격을 벌려 비교 stall을 없앤다.",
    "beq $t2,$t3: 둘 다 4 → taken. 피연산자가 3·4칸 앞에서 계산돼 stall 없음.",
    "taken 분기로 건너뛰는 명령어. 실행됐다면 $s4=10이 되므로 최종 상태로 확인 가능.",
    "분기 목표(skip). addi로 I-type ALU 경로를 보여준다. $t5 = 4+10 = 14.",
    "마지막 명령어 or. $t6 = 1 | 6 = 7. 피연산자는 모두 멀리 앞에서 계산됨.",
]

BASE_PC = 0x00

# initial architectural state (registers not listed are 0)
INIT_REGS = {"$s0": 0x10, "$s1": 5, "$s2": 8, "$s3": 6}
# data memory: byte address -> word
INIT_MEM = {0x10: 7, 0x14: 0, 0x18: 0}

# registers / memory words shown on screen in every video
SHOW_REGS = ["$t0", "$t1", "$t2", "$t3", "$t4", "$t5", "$t6",
             "$s0", "$s1", "$s2", "$s3", "$s4"]
SHOW_MEM = [0x10, 0x14, 0x18]
