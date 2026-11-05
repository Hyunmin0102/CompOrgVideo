## 1. 최종 상태: multi-cycle vs ISA 인터프리터
| 항목 | multi-cycle (X→0) | multi-cycle (X→1) | 인터프리터 | 결과 |
|---|---|---|---|---|
| $t0 | 7 | 7 | 7 | OK |
| $t1 | 12 | 12 | 12 | OK |
| $t2 | 4 | 4 | 4 | OK |
| $t3 | 4 | 4 | 4 | OK |
| $t4 | 1 | 1 | 1 | OK |
| $t5 | 14 | 14 | 14 | OK |
| $t6 | 7 | 7 | 7 | OK |
| $s0 | 64 | 64 | 64 | OK |
| $s1 | 5 | 5 | 5 | OK |
| $s2 | 8 | 8 | 8 | OK |
| $s3 | 6 | 6 | 6 | OK |
| Mem[0x40] | 7 | 7 | 7 | OK |
| Mem[0x44] | 12 | 12 | 12 | OK |
| Mem[0x48] | 0 | 0 | 0 | OK |
| 실행 PC 순서 | 00 04 08 0C 10 14 18 20 24 |  | 00 04 08 0C 10 14 18 20 24 | OK |

## 2. 상태별 제어 신호 vs 슬라이드 58 (PDF 30쪽) 동그라미 안의 글자
| 상태 | 이름 | 슬라이드 | trace | 결과 |
|---|---|---|---|---|
| S0 | Fetch | IorD=0, ALUSrcA=0, ALUSrcB=01, ALUOp=00, PCSrc=00, IRWrite=1, PCWrite=1 | IorD=0, ALUSrcA=0, ALUSrcB=01, ALUOp=00, PCSrc=00, IRWrite=1, PCWrite=1 | OK |
| S1 | Decode | ALUSrcA=0, ALUSrcB=11, ALUOp=00 | ALUSrcA=0, ALUSrcB=11, ALUOp=00 | OK |
| S2 | MemAdr | ALUSrcA=1, ALUSrcB=10, ALUOp=00 | ALUSrcA=1, ALUSrcB=10, ALUOp=00 | OK |
| S3 | MemRead | IorD=1 | IorD=1 | OK |
| S4 | Mem Writeback | RegDst=0, MemtoReg=1, RegWrite=1 | RegDst=0, MemtoReg=1, RegWrite=1 | OK |
| S5 | MemWrite | IorD=1, MemWrite=1 | IorD=1, MemWrite=1 | OK |
| S6 | Execute | ALUSrcA=1, ALUSrcB=00, ALUOp=10 | ALUSrcA=1, ALUSrcB=00, ALUOp=10 | OK |
| S7 | ALU Writeback | RegDst=1, MemtoReg=0, RegWrite=1 | RegDst=1, MemtoReg=0, RegWrite=1 | OK |
| S8 | Branch | ALUSrcA=1, ALUSrcB=00, ALUOp=01, PCSrc=01, Branch=1 | ALUSrcA=1, ALUSrcB=00, ALUOp=01, PCSrc=01, Branch=1 | OK |
| S9 | ADDI Execute | ALUSrcA=1, ALUSrcB=10, ALUOp=00 | ALUSrcA=1, ALUSrcB=10, ALUOp=00 | OK |
| S10 | ADDI Writeback | RegDst=0, MemtoReg=0, RegWrite=1 | RegDst=0, MemtoReg=0, RegWrite=1 | OK |

모든 36 사이클에서 위 값 확인. 그림에 없는 쓰기 신호는 0, mux 선택은 X (가정 3).

## 3. 명령어별 상태 순서 vs 슬라이드 58의 화살표
| # | 명령어 | 상태 순서 | 사이클 | 결과 |
|---|---|---|---|---|
| I1 | lw   $t0, 0($s0) | S0 → S1 → S2 → S3 → S4 | 5 | OK |
| I2 | add  $t1, $t0, $s1 | S0 → S1 → S6 → S7 | 4 | OK |
| I3 | sub  $t2, $t1, $s2 | S0 → S1 → S6 → S7 | 4 | OK |
| I4 | and  $t3, $t1, $s3 | S0 → S1 → S6 → S7 | 4 | OK |
| I5 | sw   $t1, 4($s0) | S0 → S1 → S2 → S5 | 4 | OK |
| I6 | slt  $t4, $s1, $s2 | S0 → S1 → S6 → S7 | 4 | OK |
| I7 | beq  $t2, $t3, skip | S0 → S1 → S8 | 3 | OK |
| I9 | addi $t5, $t3, 10 | S0 → S1 → S9 → S10 | 4 | OK |
| I10 | or   $t6, $t4, $s3 | S0 → S1 → S6 → S7 | 4 | OK |

## 4. 클록 주기와 실행 시간
부품 지연(PDF 31쪽 = L10 90): {'mem': 200, 'alu': 100, 'adder': 100, 'rf': 50, 'other': 0} → OK

| 상태 | 이름 | 하는 일(ps) | 필요 시간(ps) |
|---|---|---|---|
| S0 | Fetch | MEM 200, ALU 100 | 200 |
| S1 | Decode | RF 50, ALU 100 | 100 |
| S2 | MemAdr | ALU 100 | 100 |
| S3 | MemRead | MEM 200 | 200 |
| S4 | Mem Writeback | RF_W 50 | 50 |
| S5 | MemWrite | MEM 200 | 200 |
| S6 | Execute | ALU 100 | 100 |
| S7 | ALU Writeback | RF_W 50 | 50 |
| S8 | Branch | ALU 100 | 100 |
| S9 | ADDI Execute | ALU 100 | 100 |
| S10 | ADDI Writeback | RF_W 50 | 50 |

클록 주기 = 가장 긴 상태 = 200 ps (가정 1: 레지스터 오버헤드 0ps)

|  | single-cycle | multi-cycle |
|---|---|---|
| 명령어 수 | 9 | 9 |
| 사이클 수 | 9 | 36 |
| CPI | 1 | 4.00 |
| 클록 주기 | 600 ps | 200 ps |
| 총 실행 시간 | 5400 ps | 7200 ps |

multi-cycle 사이클 안의 남는 시간 합: 2850 ps / 7200 ps

## 결과
모두 일치
