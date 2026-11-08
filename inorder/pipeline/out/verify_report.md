## 1. 최종 상태: pipeline vs ISA 인터프리터
| 항목 | pipeline (X→0) | pipeline (X→1) | 인터프리터 | 결과 |
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
| 완료한 명령어(PC) | 00 04 08 0C 10 14 18 20 24 | 15 사이클 | 00 04 08 0C 10 14 18 20 24 | OK |

## 2. 설계한 hazard가 설계한 명령어 쌍에서 일어나는가
| 쌍 | 레지스터 | 처리 | 언제 | 결과 |
|---|---|---|---|---|
| I1 → I2 | $t0 | load-use → 1 stall (StallF·StallD·FlushE) | 사이클 3 | OK |
| I1 → I2 | $t0 | WB→EX forwarding | 사이클 5 | OK |
| I2 → I3 | $t1 | MEM→EX forwarding | 사이클 6 | OK |
| I2 → I4 | $t1 | WB→EX forwarding | 사이클 7 | OK |
| I2 → I5 | $t1 | 레지스터 파일 (WB 전반 쓰기, ID 후반 읽기) | 사이클 7 | OK |
| I4 → I7 | $t3 | 레지스터 파일 (WB 전반 쓰기, ID 후반 읽기) | 사이클 9 | OK |
| I7 → I8 | PC | taken beq → 다음 명령어 flush (CLR=PCSrcD) | 사이클 9 | OK |
| I7 beq | $t2,$t3 | branchstall 없음 (피연산자가 충분히 앞) | 없음 | OK |

## 3. 슬라이드 69 식을 trace 값으로 다시 계산 (매 사이클)
StallF = StallD = FlushE = lwstall | branchstall, ForwardAD/BD 식: 15 사이클 중 불일치 0

## 4. Decode 단계 제어 신호 vs 1편(single-cycle) 제어 (슬라이드 20: 같은 제어 유닛)
| # | 명령어 | Decode 제어 신호 | 1편과 같음 |
|---|---|---|---|
| I1 | lw   $t0, 0($s0) | RegWrite=1, RegDst=0, ALUSrc=1, Branch=0, MemWrite=0, MemtoReg=1, ALUControl=010 | OK |
| I2 | add  $t1, $t0, $s1 | RegWrite=1, RegDst=1, ALUSrc=0, Branch=0, MemWrite=0, MemtoReg=0, ALUControl=010 | OK |
| I3 | sub  $t2, $t1, $s2 | RegWrite=1, RegDst=1, ALUSrc=0, Branch=0, MemWrite=0, MemtoReg=0, ALUControl=110 | OK |
| I4 | and  $t3, $t1, $s3 | RegWrite=1, RegDst=1, ALUSrc=0, Branch=0, MemWrite=0, MemtoReg=0, ALUControl=000 | OK |
| I5 | sw   $t1, 4($s0) | RegWrite=0, RegDst=X, ALUSrc=1, Branch=0, MemWrite=1, MemtoReg=X, ALUControl=010 | OK |
| I6 | slt  $t4, $s1, $s2 | RegWrite=1, RegDst=1, ALUSrc=0, Branch=0, MemWrite=0, MemtoReg=0, ALUControl=111 | OK |
| I7 | beq  $t2, $t3, skip | RegWrite=0, RegDst=X, ALUSrc=0, Branch=1, MemWrite=0, MemtoReg=X, ALUControl=110 | OK |
| I9 | addi $t5, $t3, 10 | RegWrite=1, RegDst=0, ALUSrc=1, Branch=0, MemWrite=0, MemtoReg=0, ALUControl=010 | OK |
| I10 | or   $t6, $t4, $s3 | RegWrite=1, RegDst=1, ALUSrc=0, Branch=0, MemWrite=0, MemtoReg=0, ALUControl=001 | OK |

## 5. 사이클 수와 실행 시간
5 + (명령어 9 - 1) + stall 1 + flush 1 = 15 — trace 15 사이클 (OK)

| 단계 | 식 (슬라이드 83) | L10 90 지연으로 (ps) |
|---|---|---|
| IF | t_mem | 200 |
| ID | 2 × (t_RFread + mux + eq + AND + mux) | 100 |
| EX | t_mux + t_mux + t_ALU | 100 |
| MEM | t_mem | 200 |
| WB | 2 × (t_mux + t_RFwrite) | 100 |

클록 주기 = 가장 느린 단계 = 200 ps (가정 1). 참고: 슬라이드 86은 다른 지연 표(250ps 메모리 등)로 Tc = 550 ps.

|  | single-cycle | multi-cycle | pipeline |
|---|---|---|---|
| 사이클 수 | 9 | 36 | 15 |
| CPI (명령어 9개) | 1.00 | 4.00 | 1.67 |
| 클록 주기 | 600 ps | 200 ps | 200 ps |
| 총 실행 시간 | 5400 ps | 7200 ps | 3000 ps |

pipeline CPI에는 파이프라인을 채우는 4사이클이 들어 있다 (명령어 9개뿐이라 크게 보임).

## 결과
모두 일치
