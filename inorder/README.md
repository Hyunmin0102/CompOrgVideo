# inorder — single-cycle / multi-cycle / pipelined MIPS

ETH DDCA(Onur Mutlu) L10–L11의 세 가지 마이크로아키텍처가 **같은 프로그램**을 어떻게
처리하는지 비교하는 영상 3편. `ooo/`의 코드·가정은 쓰지 않는다 (CLAUDE.md 규칙 8).

## 공통 기반 (`shared/`)
| 파일 | 역할 |
|---|---|
| `isa.py` | 슬라이드의 MIPS 부분집합(add, sub, and, or, slt, addi, lw, sw, beq) 어셈블러/디코더. 실제 32비트 기계어를 만든다 |
| `program.py` | 3편 공통 프로그램, 초기 레지스터·메모리, 명령어별 설계 이유 |
| `interpreter.py` | ISA 수준 인터프리터 — 최종 상태가 3편 모든 검증의 기준 |
| `datapath.py` | H&H 단일 사이클 데이터패스(L11 55, j 제외)를 단순화한 그리기 모듈. 부품 위치(`LAYOUT`)와 단계 경계(`STAGE_X`)를 고정해 multi-cycle·pipeline 편에서도 같은 자리를 쓴다 |

## 공통 프로그램
| # | 주소 | 명령어 | 넣은 이유 |
|---|---|---|---|
| I1 | 0x00 | `lw $t0, 0($s0)` | Mem[0x40]=7 읽기. 바로 다음 명령어가 사용 |
| I2 | 0x04 | `add $t1, $t0, $s1` | lw 직후 사용 → **load-use** (pipeline 1 stall) |
| I3 | 0x08 | `sub $t2, $t1, $s2` | 바로 앞 결과 사용 → **거리 1 RAW** (MEM→EX forwarding) |
| I4 | 0x0C | `and $t3, $t1, $s3` | 두 칸 앞 결과 사용 → **거리 2 RAW** (WB→EX forwarding) |
| I5 | 0x10 | `sw $t1, 4($s0)` | **sw**. $t1은 세 칸 앞이라 forwarding 불필요 |
| I6 | 0x14 | `slt $t4, $s1, $s2` | 독립 명령어. beq와 피연산자 사이 간격 확보 |
| I7 | 0x18 | `beq $t2, $t3, skip` | **taken beq** (4==4). 피연산자가 4·3칸 앞 → 비교 stall 없음 |
| I8 | 0x1C | `add $s4, $s1, $s1` | 건너뛰는 명령어. 실행되면 $s4=10이 되므로 최종 상태로 확인 |
| I9 | 0x20 | `skip: addi $t5, $t3, 10` | 분기 목표. I-type ALU 경로 |
| I10 | 0x24 | `or $t6, $t4, $s3` | 마지막 명령어 |

초기값: `$s0=0x40, $s1=5, $s2=8, $s3=6`, 나머지 0. `Mem[0x40]=7, Mem[0x44]=0, Mem[0x48]=0`.
데이터는 프로그램(0x00–0x24) 위쪽 0x40부터 둔다 — multi-cycle은 명령어와 데이터가 메모리 하나를 같이 쓰기 때문.
실행되는 명령어 9개. 최종: `$t0=7 $t1=12 $t2=4 $t3=4 $t4=1 $t5=14 $t6=7 $s4=0`, `Mem[0x44]=12`.

## 영상
- `single_cycle/` — 1편 (single-cycle)
- `multi_cycle/`, `pipeline/` — 예정
