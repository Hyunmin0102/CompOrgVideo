## 1. 최종 상태: 시뮬레이터 vs ISA 인터프리터
| 항목 | single-cycle | 인터프리터 | 결과 |
|---|---|---|---|
| $t0 | 7 | 7 | OK |
| $t1 | 12 | 12 | OK |
| $t2 | 4 | 4 | OK |
| $t3 | 4 | 4 | OK |
| $t4 | 1 | 1 | OK |
| $t5 | 14 | 14 | OK |
| $t6 | 7 | 7 | OK |
| $s0 | 64 | 64 | OK |
| $s1 | 5 | 5 | OK |
| $s2 | 8 | 8 | OK |
| $s3 | 6 | 6 | OK |
| Mem[0x40] | 7 | 7 | OK |
| Mem[0x44] | 12 | 12 | OK |
| Mem[0x48] | 0 | 0 | OK |
| 실행 PC 순서 | 00 04 08 0C 10 14 18 20 24 | 00 04 08 0C 10 14 18 20 24 | OK |

## 2. 명령어별 제어 신호 vs 슬라이드 (L10 56–61 = PDF 5–10쪽 그림)
| # | 명령어 | 기준 | RegWrite | RegDst | ALUSrc | Branch | MemWrite | MemtoReg | ALUControl | PCSrc | MemRead(경로) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| I1 | lw   $t0, 0($s0) | p.7 | 1 | 0 | 1 | 0 | 0 | 1 | 010(add) | 0 | OK |
| I2 | add  $t1, $t0, $s1 | p.5 | 1 | 1 | 0 | 0 | 0 | 0 | 010(add) | 0 | OK |
| I3 | sub  $t2, $t1, $s2 | p.5 | 1 | 1 | 0 | 0 | 0 | 0 | 110(sub) | 0 | OK |
| I4 | and  $t3, $t1, $s3 | p.5 | 1 | 1 | 0 | 0 | 0 | 0 | 000(and) | 0 | OK |
| I5 | sw   $t1, 4($s0) | p.8 | 0 | X | 1 | 0 | 1 | X | 010(add) | 0 | OK |
| I6 | slt  $t4, $s1, $s2 | p.5 | 1 | 1 | 0 | 0 | 0 | 0 | 111(slt) | 0 | OK |
| I7 | beq  $t2, $t3, skip | p.10 | 0 | X | 0 | 1 | 0 | X | 110(sub) | 1 | OK |
| I9 | addi $t5, $t3, 10 | p.6 | 1 | 0 | 1 | 0 | 0 | 0 | 010(add) | 0 | OK |
| I10 | or   $t6, $t4, $s3 | p.5 | 1 | 1 | 0 | 0 | 0 | 0 | 001(or) | 0 | OK |

ALUControl 칸: H&H 3비트 값(연산 이름). 슬라이드 라벨 funct/opcode/Add/bcond를 연산 이름으로 바꿔 비교. Branch는 그림에 값이 없어 PDF 4쪽 식 PCSrc2=(opcode==Bxx)&&bcond에서 가져옴.

## 3. 지연 시간 vs 슬라이드 (L10 90 표, L10 92–95 경로 주석)
부품 지연: trace {'mem': 200, 'alu': 100, 'adder': 100, 'rf': 50, 'other': 0} / 슬라이드 {'mem': 200, 'alu': 100, 'adder': 100, 'rf': 50, 'other': 0} → OK

| 종류 | trace(ps) | 슬라이드(ps) | 결과 | 경로 도착 시각 |
|---|---|---|---|---|
| R | 400 | 400 | OK | IMEM=200 RF=250 ALU=350 RF_W=400 OK |
| I | 400 | 400 | OK |  |
| LW | 600 | 600 | OK | IMEM=200 RF=250 ALU=350 DMEM=550 RF_W=600 OK |
| SW | 550 | 550 | OK | IMEM=200 RF=250 ALU=350 DMEM=550 OK |
| BEQ | 350 | 350 | OK | ADD4=100 IMEM=200 RF=250 ALU=350 OK |

클록 주기 = 가장 느린 명령어(lw) = 600 ps (OK)

## 4. 공통 프로그램의 의존 관계 (실행 순서 기준, 거리 ≤ 3)
| 쌍(생산→소비) | 레지스터 | 거리 | 의미 |
|---|---|---|---|
| I1 → I2 | $t0 | 1 | load-use (1 stall) |
| I2 → I3 | $t1 | 1 | 거리 1 RAW → MEM→EX forwarding |
| I2 → I4 | $t1 | 2 | 거리 2 RAW → WB→EX forwarding |
| I2 → I5 | $t1 | 3 | 거리 3 → 레지스터 파일(쓰기 전반/읽기 후반), forwarding 불필요 |
| I4 → I7 | $t3 | 3 | beq 피연산자 — stall 없음 (H&H: 거리 ≥3) |
| I6 → I10 | $t4 | 3 | 거리 3 → 레지스터 파일(쓰기 전반/읽기 후반), forwarding 불필요 |

## 결과
모두 일치
