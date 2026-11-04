# 사이클별 상태 표 (각 사이클 끝)

## 사이클 0

이벤트: 없음

| Reg | Frontend | Arch |
|---|---|---|
| R1 | PR1 | PR1 |
| R2 | PR2 | PR2 |
| R3 | PR3 | PR3 |
| R4 | PR4 | PR4 |
| R5 | PR5 | PR5 |
| R6 | PR6 | PR6 |
| R7 | PR7 | PR7 |
| R8 | PR8 | PR8 |
| R9 | PR9 | PR9 |
| R10 | PR10 | PR10 |
| R11 | PR11 | PR11 |

PRF (V, 값): PR1=(1,1), PR2=(1,2), PR3=(1,3), PR4=(1,4), PR5=(1,5), PR6=(1,6), PR7=(1,7), PR8=(1,8), PR9=(1,9), PR10=(1,10), PR11=(1,11), PR12=(0,), PR13=(0,), PR14=(0,), PR15=(0,), PR16=(0,), PR17=(0,), PR18=(0,), PR19=(0,), PR20=(0,), PR21=(0,), PR22=(0,)

free list: PR12 PR13 PR14 PR15 PR16 PR17 PR18 PR19 PR20 PR21 PR22

ROB (head=0, tail=0):

| # | valid | dst | DestPR | oldPR | done |
|---|---|---|---|---|---|

RS:

| RS | V1 | PR1 | V2 | PR2 | DestPR | busy |
|---|---|---|---|---|---|---|

## 사이클 1

이벤트: 없음

| Reg | Frontend | Arch |
|---|---|---|
| R1 | PR1 | PR1 |
| R2 | PR2 | PR2 |
| R3 | PR3 | PR3 |
| R4 | PR4 | PR4 |
| R5 | PR5 | PR5 |
| R6 | PR6 | PR6 |
| R7 | PR7 | PR7 |
| R8 | PR8 | PR8 |
| R9 | PR9 | PR9 |
| R10 | PR10 | PR10 |
| R11 | PR11 | PR11 |

PRF (V, 값): PR1=(1,1), PR2=(1,2), PR3=(1,3), PR4=(1,4), PR5=(1,5), PR6=(1,6), PR7=(1,7), PR8=(1,8), PR9=(1,9), PR10=(1,10), PR11=(1,11), PR12=(0,), PR13=(0,), PR14=(0,), PR15=(0,), PR16=(0,), PR17=(0,), PR18=(0,), PR19=(0,), PR20=(0,), PR21=(0,), PR22=(0,)

free list: PR12 PR13 PR14 PR15 PR16 PR17 PR18 PR19 PR20 PR21 PR22

ROB (head=0, tail=0):

| # | valid | dst | DestPR | oldPR | done |
|---|---|---|---|---|---|

RS:

| RS | V1 | PR1 | V2 | PR2 | DestPR | busy |
|---|---|---|---|---|---|---|

## 사이클 2

이벤트: I1 디코드 → RS x, ROB 0, 소스 R1→PR1(V=1), R2→PR2(V=1); rename R3: PR3 → PR12

| Reg | Frontend | Arch |
|---|---|---|
| R1 | PR1 | PR1 |
| R2 | PR2 | PR2 |
| R3 | PR12 * | PR3 |
| R4 | PR4 | PR4 |
| R5 | PR5 | PR5 |
| R6 | PR6 | PR6 |
| R7 | PR7 | PR7 |
| R8 | PR8 | PR8 |
| R9 | PR9 | PR9 |
| R10 | PR10 | PR10 |
| R11 | PR11 | PR11 |

PRF (V, 값): PR1=(1,1), PR2=(1,2), PR3=(1,3), PR4=(1,4), PR5=(1,5), PR6=(1,6), PR7=(1,7), PR8=(1,8), PR9=(1,9), PR10=(1,10), PR11=(1,11), PR12=(0,), PR13=(0,), PR14=(0,), PR15=(0,), PR16=(0,), PR17=(0,), PR18=(0,), PR19=(0,), PR20=(0,), PR21=(0,), PR22=(0,)

free list: PR13 PR14 PR15 PR16 PR17 PR18 PR19 PR20 PR21 PR22

ROB (head=0, tail=1):

| # | valid | dst | DestPR | oldPR | done |
|---|---|---|---|---|---|
| 0 | 1 | R3 | PR12 | PR3 | 0 |

RS:

| RS | V1 | PR1 | V2 | PR2 | DestPR | busy |
|---|---|---|---|---|---|---|
| x | 1 | PR1 | 1 | PR2 | PR12 | 1 |

## 사이클 3

이벤트: I2 디코드 → RS a, ROB 1, 소스 R3→PR12(V=0), R4→PR4(V=1); rename R5: PR5 → PR13; RS x 실행 시작, PRF 읽기 PR1=1, PR2=2

| Reg | Frontend | Arch |
|---|---|---|
| R1 | PR1 | PR1 |
| R2 | PR2 | PR2 |
| R3 | PR12 * | PR3 |
| R4 | PR4 | PR4 |
| R5 | PR13 * | PR5 |
| R6 | PR6 | PR6 |
| R7 | PR7 | PR7 |
| R8 | PR8 | PR8 |
| R9 | PR9 | PR9 |
| R10 | PR10 | PR10 |
| R11 | PR11 | PR11 |

PRF (V, 값): PR1=(1,1), PR2=(1,2), PR3=(1,3), PR4=(1,4), PR5=(1,5), PR6=(1,6), PR7=(1,7), PR8=(1,8), PR9=(1,9), PR10=(1,10), PR11=(1,11), PR12=(0,), PR13=(0,), PR14=(0,), PR15=(0,), PR16=(0,), PR17=(0,), PR18=(0,), PR19=(0,), PR20=(0,), PR21=(0,), PR22=(0,)

free list: PR14 PR15 PR16 PR17 PR18 PR19 PR20 PR21 PR22

ROB (head=0, tail=2):

| # | valid | dst | DestPR | oldPR | done |
|---|---|---|---|---|---|
| 0 | 1 | R3 | PR12 | PR3 | 0 |
| 1 | 1 | R5 | PR13 | PR5 | 0 |

RS:

| RS | V1 | PR1 | V2 | PR2 | DestPR | busy |
|---|---|---|---|---|---|---|
| a | 0 | PR12 | 1 | PR4 | PR13 | 1 |
| x | 1 | PR1 | 1 | PR2 | PR12 | 1 |

## 사이클 4

이벤트: I3 디코드 → RS b, ROB 2, 소스 R2→PR2(V=1), R6→PR6(V=1); rename R7: PR7 → PR14

| Reg | Frontend | Arch |
|---|---|---|
| R1 | PR1 | PR1 |
| R2 | PR2 | PR2 |
| R3 | PR12 * | PR3 |
| R4 | PR4 | PR4 |
| R5 | PR13 * | PR5 |
| R6 | PR6 | PR6 |
| R7 | PR14 * | PR7 |
| R8 | PR8 | PR8 |
| R9 | PR9 | PR9 |
| R10 | PR10 | PR10 |
| R11 | PR11 | PR11 |

PRF (V, 값): PR1=(1,1), PR2=(1,2), PR3=(1,3), PR4=(1,4), PR5=(1,5), PR6=(1,6), PR7=(1,7), PR8=(1,8), PR9=(1,9), PR10=(1,10), PR11=(1,11), PR12=(0,), PR13=(0,), PR14=(0,), PR15=(0,), PR16=(0,), PR17=(0,), PR18=(0,), PR19=(0,), PR20=(0,), PR21=(0,), PR22=(0,)

free list: PR15 PR16 PR17 PR18 PR19 PR20 PR21 PR22

ROB (head=0, tail=3):

| # | valid | dst | DestPR | oldPR | done |
|---|---|---|---|---|---|
| 0 | 1 | R3 | PR12 | PR3 | 0 |
| 1 | 1 | R5 | PR13 | PR5 | 0 |
| 2 | 1 | R7 | PR14 | PR7 | 0 |

RS:

| RS | V1 | PR1 | V2 | PR2 | DestPR | busy |
|---|---|---|---|---|---|---|
| a | 0 | PR12 | 1 | PR4 | PR13 | 1 |
| b | 1 | PR2 | 1 | PR6 | PR14 | 1 |
| x | 1 | PR1 | 1 | PR2 | PR12 | 1 |

## 사이클 5

이벤트: I4 디코드 → RS c, ROB 3, 소스 R8→PR8(V=1), R9→PR9(V=1); rename R10: PR10 → PR15; RS b 실행 시작, PRF 읽기 PR2=2, PR6=6

| Reg | Frontend | Arch |
|---|---|---|
| R1 | PR1 | PR1 |
| R2 | PR2 | PR2 |
| R3 | PR12 * | PR3 |
| R4 | PR4 | PR4 |
| R5 | PR13 * | PR5 |
| R6 | PR6 | PR6 |
| R7 | PR14 * | PR7 |
| R8 | PR8 | PR8 |
| R9 | PR9 | PR9 |
| R10 | PR15 * | PR10 |
| R11 | PR11 | PR11 |

PRF (V, 값): PR1=(1,1), PR2=(1,2), PR3=(1,3), PR4=(1,4), PR5=(1,5), PR6=(1,6), PR7=(1,7), PR8=(1,8), PR9=(1,9), PR10=(1,10), PR11=(1,11), PR12=(0,), PR13=(0,), PR14=(0,), PR15=(0,), PR16=(0,), PR17=(0,), PR18=(0,), PR19=(0,), PR20=(0,), PR21=(0,), PR22=(0,)

free list: PR16 PR17 PR18 PR19 PR20 PR21 PR22

ROB (head=0, tail=4):

| # | valid | dst | DestPR | oldPR | done |
|---|---|---|---|---|---|
| 0 | 1 | R3 | PR12 | PR3 | 0 |
| 1 | 1 | R5 | PR13 | PR5 | 0 |
| 2 | 1 | R7 | PR14 | PR7 | 0 |
| 3 | 1 | R10 | PR15 | PR10 | 0 |

RS:

| RS | V1 | PR1 | V2 | PR2 | DestPR | busy |
|---|---|---|---|---|---|---|
| a | 0 | PR12 | 1 | PR4 | PR13 | 1 |
| b | 1 | PR2 | 1 | PR6 | PR14 | 1 |
| c | 1 | PR8 | 1 | PR9 | PR15 | 1 |
| x | 1 | PR1 | 1 | PR2 | PR12 | 1 |

## 사이클 6

이벤트: I5 디코드 → RS y, ROB 4, 소스 R7→PR14(V=0), R10→PR15(V=0); rename R11: PR11 → PR16; RS c 실행 시작, PRF 읽기 PR8=8, PR9=9

| Reg | Frontend | Arch |
|---|---|---|
| R1 | PR1 | PR1 |
| R2 | PR2 | PR2 |
| R3 | PR12 * | PR3 |
| R4 | PR4 | PR4 |
| R5 | PR13 * | PR5 |
| R6 | PR6 | PR6 |
| R7 | PR14 * | PR7 |
| R8 | PR8 | PR8 |
| R9 | PR9 | PR9 |
| R10 | PR15 * | PR10 |
| R11 | PR16 * | PR11 |

PRF (V, 값): PR1=(1,1), PR2=(1,2), PR3=(1,3), PR4=(1,4), PR5=(1,5), PR6=(1,6), PR7=(1,7), PR8=(1,8), PR9=(1,9), PR10=(1,10), PR11=(1,11), PR12=(0,), PR13=(0,), PR14=(0,), PR15=(0,), PR16=(0,), PR17=(0,), PR18=(0,), PR19=(0,), PR20=(0,), PR21=(0,), PR22=(0,)

free list: PR17 PR18 PR19 PR20 PR21 PR22

ROB (head=0, tail=5):

| # | valid | dst | DestPR | oldPR | done |
|---|---|---|---|---|---|
| 0 | 1 | R3 | PR12 | PR3 | 0 |
| 1 | 1 | R5 | PR13 | PR5 | 0 |
| 2 | 1 | R7 | PR14 | PR7 | 0 |
| 3 | 1 | R10 | PR15 | PR10 | 0 |
| 4 | 1 | R11 | PR16 | PR11 | 0 |

RS:

| RS | V1 | PR1 | V2 | PR2 | DestPR | busy |
|---|---|---|---|---|---|---|
| a | 0 | PR12 | 1 | PR4 | PR13 | 1 |
| b | 1 | PR2 | 1 | PR6 | PR14 | 1 |
| c | 1 | PR8 | 1 | PR9 | PR15 | 1 |
| x | 1 | PR1 | 1 | PR2 | PR12 | 1 |
| y | 0 | PR14 | 0 | PR15 | PR16 | 1 |

## 사이클 7

이벤트: I6 디코드 → RS d, ROB 5, 소스 R5→PR13(V=0), R11→PR16(V=0); rename R5: PR13 → PR17

| Reg | Frontend | Arch |
|---|---|---|
| R1 | PR1 | PR1 |
| R2 | PR2 | PR2 |
| R3 | PR12 * | PR3 |
| R4 | PR4 | PR4 |
| R5 | PR17 * | PR5 |
| R6 | PR6 | PR6 |
| R7 | PR14 * | PR7 |
| R8 | PR8 | PR8 |
| R9 | PR9 | PR9 |
| R10 | PR15 * | PR10 |
| R11 | PR16 * | PR11 |

PRF (V, 값): PR1=(1,1), PR2=(1,2), PR3=(1,3), PR4=(1,4), PR5=(1,5), PR6=(1,6), PR7=(1,7), PR8=(1,8), PR9=(1,9), PR10=(1,10), PR11=(1,11), PR12=(0,), PR13=(0,), PR14=(0,), PR15=(0,), PR16=(0,), PR17=(0,), PR18=(0,), PR19=(0,), PR20=(0,), PR21=(0,), PR22=(0,)

free list: PR18 PR19 PR20 PR21 PR22

ROB (head=0, tail=6):

| # | valid | dst | DestPR | oldPR | done |
|---|---|---|---|---|---|
| 0 | 1 | R3 | PR12 | PR3 | 0 |
| 1 | 1 | R5 | PR13 | PR5 | 0 |
| 2 | 1 | R7 | PR14 | PR7 | 0 |
| 3 | 1 | R10 | PR15 | PR10 | 0 |
| 4 | 1 | R11 | PR16 | PR11 | 0 |
| 5 | 1 | R5 | PR17 | PR13 | 0 |

RS:

| RS | V1 | PR1 | V2 | PR2 | DestPR | busy |
|---|---|---|---|---|---|---|
| a | 0 | PR12 | 1 | PR4 | PR13 | 1 |
| b | 1 | PR2 | 1 | PR6 | PR14 | 1 |
| c | 1 | PR8 | 1 | PR9 | PR15 | 1 |
| d | 0 | PR13 | 0 | PR16 | PR17 | 1 |
| x | 1 | PR1 | 1 | PR2 | PR12 | 1 |
| y | 0 | PR14 | 0 | PR15 | PR16 | 1 |

## 사이클 8

이벤트: PRF[PR12] ← 2, DestPR PR12 broadcast → RS a.src1; PRF[PR14] ← 8, DestPR PR14 broadcast → RS y.src1

| Reg | Frontend | Arch |
|---|---|---|
| R1 | PR1 | PR1 |
| R2 | PR2 | PR2 |
| R3 | PR12 * | PR3 |
| R4 | PR4 | PR4 |
| R5 | PR17 * | PR5 |
| R6 | PR6 | PR6 |
| R7 | PR14 * | PR7 |
| R8 | PR8 | PR8 |
| R9 | PR9 | PR9 |
| R10 | PR15 * | PR10 |
| R11 | PR16 * | PR11 |

PRF (V, 값): PR1=(1,1), PR2=(1,2), PR3=(1,3), PR4=(1,4), PR5=(1,5), PR6=(1,6), PR7=(1,7), PR8=(1,8), PR9=(1,9), PR10=(1,10), PR11=(1,11), PR12=(1,2), PR13=(0,), PR14=(1,8), PR15=(0,), PR16=(0,), PR17=(0,), PR18=(0,), PR19=(0,), PR20=(0,), PR21=(0,), PR22=(0,)

free list: PR18 PR19 PR20 PR21 PR22

ROB (head=0, tail=6):

| # | valid | dst | DestPR | oldPR | done |
|---|---|---|---|---|---|
| 0 | 1 | R3 | PR12 | PR3 | 0 |
| 1 | 1 | R5 | PR13 | PR5 | 0 |
| 2 | 1 | R7 | PR14 | PR7 | 0 |
| 3 | 1 | R10 | PR15 | PR10 | 0 |
| 4 | 1 | R11 | PR16 | PR11 | 0 |
| 5 | 1 | R5 | PR17 | PR13 | 0 |

RS:

| RS | V1 | PR1 | V2 | PR2 | DestPR | busy |
|---|---|---|---|---|---|---|
| a | 1 | PR12 | 1 | PR4 | PR13 | 1 |
| b | 1 | PR2 | 1 | PR6 | PR14 | 0 |
| c | 1 | PR8 | 1 | PR9 | PR15 | 1 |
| d | 0 | PR13 | 0 | PR16 | PR17 | 1 |
| x | 1 | PR1 | 1 | PR2 | PR12 | 0 |
| y | 1 | PR14 | 0 | PR15 | PR16 | 1 |

## 사이클 9

이벤트: RS a 실행 시작, PRF 읽기 PR12=2, PR4=4; PRF[PR15] ← 17, DestPR PR15 broadcast → RS y.src2; R: ROB 0 (I1) done=1; R: ROB 2 (I3) done=1

| Reg | Frontend | Arch |
|---|---|---|
| R1 | PR1 | PR1 |
| R2 | PR2 | PR2 |
| R3 | PR12 * | PR3 |
| R4 | PR4 | PR4 |
| R5 | PR17 * | PR5 |
| R6 | PR6 | PR6 |
| R7 | PR14 * | PR7 |
| R8 | PR8 | PR8 |
| R9 | PR9 | PR9 |
| R10 | PR15 * | PR10 |
| R11 | PR16 * | PR11 |

PRF (V, 값): PR1=(1,1), PR2=(1,2), PR3=(1,3), PR4=(1,4), PR5=(1,5), PR6=(1,6), PR7=(1,7), PR8=(1,8), PR9=(1,9), PR10=(1,10), PR11=(1,11), PR12=(1,2), PR13=(0,), PR14=(1,8), PR15=(1,17), PR16=(0,), PR17=(0,), PR18=(0,), PR19=(0,), PR20=(0,), PR21=(0,), PR22=(0,)

free list: PR18 PR19 PR20 PR21 PR22

ROB (head=0, tail=6):

| # | valid | dst | DestPR | oldPR | done |
|---|---|---|---|---|---|
| 0 | 1 | R3 | PR12 | PR3 | 1 |
| 1 | 1 | R5 | PR13 | PR5 | 0 |
| 2 | 1 | R7 | PR14 | PR7 | 1 |
| 3 | 1 | R10 | PR15 | PR10 | 0 |
| 4 | 1 | R11 | PR16 | PR11 | 0 |
| 5 | 1 | R5 | PR17 | PR13 | 0 |

RS:

| RS | V1 | PR1 | V2 | PR2 | DestPR | busy |
|---|---|---|---|---|---|---|
| a | 1 | PR12 | 1 | PR4 | PR13 | 1 |
| b | 1 | PR2 | 1 | PR6 | PR14 | 0 |
| c | 1 | PR8 | 1 | PR9 | PR15 | 0 |
| d | 0 | PR13 | 0 | PR16 | PR17 | 1 |
| x | 1 | PR1 | 1 | PR2 | PR12 | 0 |
| y | 1 | PR14 | 1 | PR15 | PR16 | 1 |

## 사이클 10

이벤트: RS y 실행 시작, PRF 읽기 PR14=8, PR15=17; R: ROB 3 (I4) done=1; W: I1 retire, Arch R3: PR3 → PR12, PR3 → free list

| Reg | Frontend | Arch |
|---|---|---|
| R1 | PR1 | PR1 |
| R2 | PR2 | PR2 |
| R3 | PR12 | PR12 |
| R4 | PR4 | PR4 |
| R5 | PR17 * | PR5 |
| R6 | PR6 | PR6 |
| R7 | PR14 * | PR7 |
| R8 | PR8 | PR8 |
| R9 | PR9 | PR9 |
| R10 | PR15 * | PR10 |
| R11 | PR16 * | PR11 |

PRF (V, 값): PR1=(1,1), PR2=(1,2), PR3=(1,3), PR4=(1,4), PR5=(1,5), PR6=(1,6), PR7=(1,7), PR8=(1,8), PR9=(1,9), PR10=(1,10), PR11=(1,11), PR12=(1,2), PR13=(0,), PR14=(1,8), PR15=(1,17), PR16=(0,), PR17=(0,), PR18=(0,), PR19=(0,), PR20=(0,), PR21=(0,), PR22=(0,)

free list: PR18 PR19 PR20 PR21 PR22 PR3

ROB (head=1, tail=6):

| # | valid | dst | DestPR | oldPR | done |
|---|---|---|---|---|---|
| 0 | 0 | R3 | PR12 | PR3 | 1 |
| 1 | 1 | R5 | PR13 | PR5 | 0 |
| 2 | 1 | R7 | PR14 | PR7 | 1 |
| 3 | 1 | R10 | PR15 | PR10 | 1 |
| 4 | 1 | R11 | PR16 | PR11 | 0 |
| 5 | 1 | R5 | PR17 | PR13 | 0 |

RS:

| RS | V1 | PR1 | V2 | PR2 | DestPR | busy |
|---|---|---|---|---|---|---|
| a | 1 | PR12 | 1 | PR4 | PR13 | 1 |
| b | 1 | PR2 | 1 | PR6 | PR14 | 0 |
| c | 1 | PR8 | 1 | PR9 | PR15 | 0 |
| d | 0 | PR13 | 0 | PR16 | PR17 | 1 |
| x | 1 | PR1 | 1 | PR2 | PR12 | 0 |
| y | 1 | PR14 | 1 | PR15 | PR16 | 1 |

## 사이클 11

이벤트: 없음

| Reg | Frontend | Arch |
|---|---|---|
| R1 | PR1 | PR1 |
| R2 | PR2 | PR2 |
| R3 | PR12 | PR12 |
| R4 | PR4 | PR4 |
| R5 | PR17 * | PR5 |
| R6 | PR6 | PR6 |
| R7 | PR14 * | PR7 |
| R8 | PR8 | PR8 |
| R9 | PR9 | PR9 |
| R10 | PR15 * | PR10 |
| R11 | PR16 * | PR11 |

PRF (V, 값): PR1=(1,1), PR2=(1,2), PR3=(1,3), PR4=(1,4), PR5=(1,5), PR6=(1,6), PR7=(1,7), PR8=(1,8), PR9=(1,9), PR10=(1,10), PR11=(1,11), PR12=(1,2), PR13=(0,), PR14=(1,8), PR15=(1,17), PR16=(0,), PR17=(0,), PR18=(0,), PR19=(0,), PR20=(0,), PR21=(0,), PR22=(0,)

free list: PR18 PR19 PR20 PR21 PR22 PR3

ROB (head=1, tail=6):

| # | valid | dst | DestPR | oldPR | done |
|---|---|---|---|---|---|
| 0 | 0 | R3 | PR12 | PR3 | 1 |
| 1 | 1 | R5 | PR13 | PR5 | 0 |
| 2 | 1 | R7 | PR14 | PR7 | 1 |
| 3 | 1 | R10 | PR15 | PR10 | 1 |
| 4 | 1 | R11 | PR16 | PR11 | 0 |
| 5 | 1 | R5 | PR17 | PR13 | 0 |

RS:

| RS | V1 | PR1 | V2 | PR2 | DestPR | busy |
|---|---|---|---|---|---|---|
| a | 1 | PR12 | 1 | PR4 | PR13 | 1 |
| b | 1 | PR2 | 1 | PR6 | PR14 | 0 |
| c | 1 | PR8 | 1 | PR9 | PR15 | 0 |
| d | 0 | PR13 | 0 | PR16 | PR17 | 1 |
| x | 1 | PR1 | 1 | PR2 | PR12 | 0 |
| y | 1 | PR14 | 1 | PR15 | PR16 | 1 |

## 사이클 12

이벤트: PRF[PR13] ← 6, DestPR PR13 broadcast → RS d.src1

| Reg | Frontend | Arch |
|---|---|---|
| R1 | PR1 | PR1 |
| R2 | PR2 | PR2 |
| R3 | PR12 | PR12 |
| R4 | PR4 | PR4 |
| R5 | PR17 * | PR5 |
| R6 | PR6 | PR6 |
| R7 | PR14 * | PR7 |
| R8 | PR8 | PR8 |
| R9 | PR9 | PR9 |
| R10 | PR15 * | PR10 |
| R11 | PR16 * | PR11 |

PRF (V, 값): PR1=(1,1), PR2=(1,2), PR3=(1,3), PR4=(1,4), PR5=(1,5), PR6=(1,6), PR7=(1,7), PR8=(1,8), PR9=(1,9), PR10=(1,10), PR11=(1,11), PR12=(1,2), PR13=(1,6), PR14=(1,8), PR15=(1,17), PR16=(0,), PR17=(0,), PR18=(0,), PR19=(0,), PR20=(0,), PR21=(0,), PR22=(0,)

free list: PR18 PR19 PR20 PR21 PR22 PR3

ROB (head=1, tail=6):

| # | valid | dst | DestPR | oldPR | done |
|---|---|---|---|---|---|
| 0 | 0 | R3 | PR12 | PR3 | 1 |
| 1 | 1 | R5 | PR13 | PR5 | 0 |
| 2 | 1 | R7 | PR14 | PR7 | 1 |
| 3 | 1 | R10 | PR15 | PR10 | 1 |
| 4 | 1 | R11 | PR16 | PR11 | 0 |
| 5 | 1 | R5 | PR17 | PR13 | 0 |

RS:

| RS | V1 | PR1 | V2 | PR2 | DestPR | busy |
|---|---|---|---|---|---|---|
| a | 1 | PR12 | 1 | PR4 | PR13 | 0 |
| b | 1 | PR2 | 1 | PR6 | PR14 | 0 |
| c | 1 | PR8 | 1 | PR9 | PR15 | 0 |
| d | 1 | PR13 | 0 | PR16 | PR17 | 1 |
| x | 1 | PR1 | 1 | PR2 | PR12 | 0 |
| y | 1 | PR14 | 1 | PR15 | PR16 | 1 |

## 사이클 13

이벤트: R: ROB 1 (I2) done=1

| Reg | Frontend | Arch |
|---|---|---|
| R1 | PR1 | PR1 |
| R2 | PR2 | PR2 |
| R3 | PR12 | PR12 |
| R4 | PR4 | PR4 |
| R5 | PR17 * | PR5 |
| R6 | PR6 | PR6 |
| R7 | PR14 * | PR7 |
| R8 | PR8 | PR8 |
| R9 | PR9 | PR9 |
| R10 | PR15 * | PR10 |
| R11 | PR16 * | PR11 |

PRF (V, 값): PR1=(1,1), PR2=(1,2), PR3=(1,3), PR4=(1,4), PR5=(1,5), PR6=(1,6), PR7=(1,7), PR8=(1,8), PR9=(1,9), PR10=(1,10), PR11=(1,11), PR12=(1,2), PR13=(1,6), PR14=(1,8), PR15=(1,17), PR16=(0,), PR17=(0,), PR18=(0,), PR19=(0,), PR20=(0,), PR21=(0,), PR22=(0,)

free list: PR18 PR19 PR20 PR21 PR22 PR3

ROB (head=1, tail=6):

| # | valid | dst | DestPR | oldPR | done |
|---|---|---|---|---|---|
| 0 | 0 | R3 | PR12 | PR3 | 1 |
| 1 | 1 | R5 | PR13 | PR5 | 1 |
| 2 | 1 | R7 | PR14 | PR7 | 1 |
| 3 | 1 | R10 | PR15 | PR10 | 1 |
| 4 | 1 | R11 | PR16 | PR11 | 0 |
| 5 | 1 | R5 | PR17 | PR13 | 0 |

RS:

| RS | V1 | PR1 | V2 | PR2 | DestPR | busy |
|---|---|---|---|---|---|---|
| a | 1 | PR12 | 1 | PR4 | PR13 | 0 |
| b | 1 | PR2 | 1 | PR6 | PR14 | 0 |
| c | 1 | PR8 | 1 | PR9 | PR15 | 0 |
| d | 1 | PR13 | 0 | PR16 | PR17 | 1 |
| x | 1 | PR1 | 1 | PR2 | PR12 | 0 |
| y | 1 | PR14 | 1 | PR15 | PR16 | 1 |

## 사이클 14

이벤트: W: I2 retire, Arch R5: PR5 → PR13, PR5 → free list

| Reg | Frontend | Arch |
|---|---|---|
| R1 | PR1 | PR1 |
| R2 | PR2 | PR2 |
| R3 | PR12 | PR12 |
| R4 | PR4 | PR4 |
| R5 | PR17 * | PR13 |
| R6 | PR6 | PR6 |
| R7 | PR14 * | PR7 |
| R8 | PR8 | PR8 |
| R9 | PR9 | PR9 |
| R10 | PR15 * | PR10 |
| R11 | PR16 * | PR11 |

PRF (V, 값): PR1=(1,1), PR2=(1,2), PR3=(1,3), PR4=(1,4), PR5=(1,5), PR6=(1,6), PR7=(1,7), PR8=(1,8), PR9=(1,9), PR10=(1,10), PR11=(1,11), PR12=(1,2), PR13=(1,6), PR14=(1,8), PR15=(1,17), PR16=(0,), PR17=(0,), PR18=(0,), PR19=(0,), PR20=(0,), PR21=(0,), PR22=(0,)

free list: PR18 PR19 PR20 PR21 PR22 PR3 PR5

ROB (head=2, tail=6):

| # | valid | dst | DestPR | oldPR | done |
|---|---|---|---|---|---|
| 0 | 0 | R3 | PR12 | PR3 | 1 |
| 1 | 0 | R5 | PR13 | PR5 | 1 |
| 2 | 1 | R7 | PR14 | PR7 | 1 |
| 3 | 1 | R10 | PR15 | PR10 | 1 |
| 4 | 1 | R11 | PR16 | PR11 | 0 |
| 5 | 1 | R5 | PR17 | PR13 | 0 |

RS:

| RS | V1 | PR1 | V2 | PR2 | DestPR | busy |
|---|---|---|---|---|---|---|
| a | 1 | PR12 | 1 | PR4 | PR13 | 0 |
| b | 1 | PR2 | 1 | PR6 | PR14 | 0 |
| c | 1 | PR8 | 1 | PR9 | PR15 | 0 |
| d | 1 | PR13 | 0 | PR16 | PR17 | 1 |
| x | 1 | PR1 | 1 | PR2 | PR12 | 0 |
| y | 1 | PR14 | 1 | PR15 | PR16 | 1 |

## 사이클 15

이벤트: PRF[PR16] ← 136, DestPR PR16 broadcast → RS d.src2; W: I3 retire, Arch R7: PR7 → PR14, PR7 → free list

| Reg | Frontend | Arch |
|---|---|---|
| R1 | PR1 | PR1 |
| R2 | PR2 | PR2 |
| R3 | PR12 | PR12 |
| R4 | PR4 | PR4 |
| R5 | PR17 * | PR13 |
| R6 | PR6 | PR6 |
| R7 | PR14 | PR14 |
| R8 | PR8 | PR8 |
| R9 | PR9 | PR9 |
| R10 | PR15 * | PR10 |
| R11 | PR16 * | PR11 |

PRF (V, 값): PR1=(1,1), PR2=(1,2), PR3=(1,3), PR4=(1,4), PR5=(1,5), PR6=(1,6), PR7=(1,7), PR8=(1,8), PR9=(1,9), PR10=(1,10), PR11=(1,11), PR12=(1,2), PR13=(1,6), PR14=(1,8), PR15=(1,17), PR16=(1,136), PR17=(0,), PR18=(0,), PR19=(0,), PR20=(0,), PR21=(0,), PR22=(0,)

free list: PR18 PR19 PR20 PR21 PR22 PR3 PR5 PR7

ROB (head=3, tail=6):

| # | valid | dst | DestPR | oldPR | done |
|---|---|---|---|---|---|
| 0 | 0 | R3 | PR12 | PR3 | 1 |
| 1 | 0 | R5 | PR13 | PR5 | 1 |
| 2 | 0 | R7 | PR14 | PR7 | 1 |
| 3 | 1 | R10 | PR15 | PR10 | 1 |
| 4 | 1 | R11 | PR16 | PR11 | 0 |
| 5 | 1 | R5 | PR17 | PR13 | 0 |

RS:

| RS | V1 | PR1 | V2 | PR2 | DestPR | busy |
|---|---|---|---|---|---|---|
| a | 1 | PR12 | 1 | PR4 | PR13 | 0 |
| b | 1 | PR2 | 1 | PR6 | PR14 | 0 |
| c | 1 | PR8 | 1 | PR9 | PR15 | 0 |
| d | 1 | PR13 | 1 | PR16 | PR17 | 1 |
| x | 1 | PR1 | 1 | PR2 | PR12 | 0 |
| y | 1 | PR14 | 1 | PR15 | PR16 | 0 |

## 사이클 16

이벤트: RS d 실행 시작, PRF 읽기 PR13=6, PR16=136; R: ROB 4 (I5) done=1; W: I4 retire, Arch R10: PR10 → PR15, PR10 → free list

| Reg | Frontend | Arch |
|---|---|---|
| R1 | PR1 | PR1 |
| R2 | PR2 | PR2 |
| R3 | PR12 | PR12 |
| R4 | PR4 | PR4 |
| R5 | PR17 * | PR13 |
| R6 | PR6 | PR6 |
| R7 | PR14 | PR14 |
| R8 | PR8 | PR8 |
| R9 | PR9 | PR9 |
| R10 | PR15 | PR15 |
| R11 | PR16 * | PR11 |

PRF (V, 값): PR1=(1,1), PR2=(1,2), PR3=(1,3), PR4=(1,4), PR5=(1,5), PR6=(1,6), PR7=(1,7), PR8=(1,8), PR9=(1,9), PR10=(1,10), PR11=(1,11), PR12=(1,2), PR13=(1,6), PR14=(1,8), PR15=(1,17), PR16=(1,136), PR17=(0,), PR18=(0,), PR19=(0,), PR20=(0,), PR21=(0,), PR22=(0,)

free list: PR18 PR19 PR20 PR21 PR22 PR3 PR5 PR7 PR10

ROB (head=4, tail=6):

| # | valid | dst | DestPR | oldPR | done |
|---|---|---|---|---|---|
| 0 | 0 | R3 | PR12 | PR3 | 1 |
| 1 | 0 | R5 | PR13 | PR5 | 1 |
| 2 | 0 | R7 | PR14 | PR7 | 1 |
| 3 | 0 | R10 | PR15 | PR10 | 1 |
| 4 | 1 | R11 | PR16 | PR11 | 1 |
| 5 | 1 | R5 | PR17 | PR13 | 0 |

RS:

| RS | V1 | PR1 | V2 | PR2 | DestPR | busy |
|---|---|---|---|---|---|---|
| a | 1 | PR12 | 1 | PR4 | PR13 | 0 |
| b | 1 | PR2 | 1 | PR6 | PR14 | 0 |
| c | 1 | PR8 | 1 | PR9 | PR15 | 0 |
| d | 1 | PR13 | 1 | PR16 | PR17 | 1 |
| x | 1 | PR1 | 1 | PR2 | PR12 | 0 |
| y | 1 | PR14 | 1 | PR15 | PR16 | 0 |

## 사이클 17

이벤트: W: I5 retire, Arch R11: PR11 → PR16, PR11 → free list

| Reg | Frontend | Arch |
|---|---|---|
| R1 | PR1 | PR1 |
| R2 | PR2 | PR2 |
| R3 | PR12 | PR12 |
| R4 | PR4 | PR4 |
| R5 | PR17 * | PR13 |
| R6 | PR6 | PR6 |
| R7 | PR14 | PR14 |
| R8 | PR8 | PR8 |
| R9 | PR9 | PR9 |
| R10 | PR15 | PR15 |
| R11 | PR16 | PR16 |

PRF (V, 값): PR1=(1,1), PR2=(1,2), PR3=(1,3), PR4=(1,4), PR5=(1,5), PR6=(1,6), PR7=(1,7), PR8=(1,8), PR9=(1,9), PR10=(1,10), PR11=(1,11), PR12=(1,2), PR13=(1,6), PR14=(1,8), PR15=(1,17), PR16=(1,136), PR17=(0,), PR18=(0,), PR19=(0,), PR20=(0,), PR21=(0,), PR22=(0,)

free list: PR18 PR19 PR20 PR21 PR22 PR3 PR5 PR7 PR10 PR11

ROB (head=5, tail=6):

| # | valid | dst | DestPR | oldPR | done |
|---|---|---|---|---|---|
| 0 | 0 | R3 | PR12 | PR3 | 1 |
| 1 | 0 | R5 | PR13 | PR5 | 1 |
| 2 | 0 | R7 | PR14 | PR7 | 1 |
| 3 | 0 | R10 | PR15 | PR10 | 1 |
| 4 | 0 | R11 | PR16 | PR11 | 1 |
| 5 | 1 | R5 | PR17 | PR13 | 0 |

RS:

| RS | V1 | PR1 | V2 | PR2 | DestPR | busy |
|---|---|---|---|---|---|---|
| a | 1 | PR12 | 1 | PR4 | PR13 | 0 |
| b | 1 | PR2 | 1 | PR6 | PR14 | 0 |
| c | 1 | PR8 | 1 | PR9 | PR15 | 0 |
| d | 1 | PR13 | 1 | PR16 | PR17 | 1 |
| x | 1 | PR1 | 1 | PR2 | PR12 | 0 |
| y | 1 | PR14 | 1 | PR15 | PR16 | 0 |

## 사이클 18

이벤트: 없음

| Reg | Frontend | Arch |
|---|---|---|
| R1 | PR1 | PR1 |
| R2 | PR2 | PR2 |
| R3 | PR12 | PR12 |
| R4 | PR4 | PR4 |
| R5 | PR17 * | PR13 |
| R6 | PR6 | PR6 |
| R7 | PR14 | PR14 |
| R8 | PR8 | PR8 |
| R9 | PR9 | PR9 |
| R10 | PR15 | PR15 |
| R11 | PR16 | PR16 |

PRF (V, 값): PR1=(1,1), PR2=(1,2), PR3=(1,3), PR4=(1,4), PR5=(1,5), PR6=(1,6), PR7=(1,7), PR8=(1,8), PR9=(1,9), PR10=(1,10), PR11=(1,11), PR12=(1,2), PR13=(1,6), PR14=(1,8), PR15=(1,17), PR16=(1,136), PR17=(0,), PR18=(0,), PR19=(0,), PR20=(0,), PR21=(0,), PR22=(0,)

free list: PR18 PR19 PR20 PR21 PR22 PR3 PR5 PR7 PR10 PR11

ROB (head=5, tail=6):

| # | valid | dst | DestPR | oldPR | done |
|---|---|---|---|---|---|
| 0 | 0 | R3 | PR12 | PR3 | 1 |
| 1 | 0 | R5 | PR13 | PR5 | 1 |
| 2 | 0 | R7 | PR14 | PR7 | 1 |
| 3 | 0 | R10 | PR15 | PR10 | 1 |
| 4 | 0 | R11 | PR16 | PR11 | 1 |
| 5 | 1 | R5 | PR17 | PR13 | 0 |

RS:

| RS | V1 | PR1 | V2 | PR2 | DestPR | busy |
|---|---|---|---|---|---|---|
| a | 1 | PR12 | 1 | PR4 | PR13 | 0 |
| b | 1 | PR2 | 1 | PR6 | PR14 | 0 |
| c | 1 | PR8 | 1 | PR9 | PR15 | 0 |
| d | 1 | PR13 | 1 | PR16 | PR17 | 1 |
| x | 1 | PR1 | 1 | PR2 | PR12 | 0 |
| y | 1 | PR14 | 1 | PR15 | PR16 | 0 |

## 사이클 19

이벤트: PRF[PR17] ← 142, DestPR PR17 broadcast → 일치 없음

| Reg | Frontend | Arch |
|---|---|---|
| R1 | PR1 | PR1 |
| R2 | PR2 | PR2 |
| R3 | PR12 | PR12 |
| R4 | PR4 | PR4 |
| R5 | PR17 * | PR13 |
| R6 | PR6 | PR6 |
| R7 | PR14 | PR14 |
| R8 | PR8 | PR8 |
| R9 | PR9 | PR9 |
| R10 | PR15 | PR15 |
| R11 | PR16 | PR16 |

PRF (V, 값): PR1=(1,1), PR2=(1,2), PR3=(1,3), PR4=(1,4), PR5=(1,5), PR6=(1,6), PR7=(1,7), PR8=(1,8), PR9=(1,9), PR10=(1,10), PR11=(1,11), PR12=(1,2), PR13=(1,6), PR14=(1,8), PR15=(1,17), PR16=(1,136), PR17=(1,142), PR18=(0,), PR19=(0,), PR20=(0,), PR21=(0,), PR22=(0,)

free list: PR18 PR19 PR20 PR21 PR22 PR3 PR5 PR7 PR10 PR11

ROB (head=5, tail=6):

| # | valid | dst | DestPR | oldPR | done |
|---|---|---|---|---|---|
| 0 | 0 | R3 | PR12 | PR3 | 1 |
| 1 | 0 | R5 | PR13 | PR5 | 1 |
| 2 | 0 | R7 | PR14 | PR7 | 1 |
| 3 | 0 | R10 | PR15 | PR10 | 1 |
| 4 | 0 | R11 | PR16 | PR11 | 1 |
| 5 | 1 | R5 | PR17 | PR13 | 0 |

RS:

| RS | V1 | PR1 | V2 | PR2 | DestPR | busy |
|---|---|---|---|---|---|---|
| a | 1 | PR12 | 1 | PR4 | PR13 | 0 |
| b | 1 | PR2 | 1 | PR6 | PR14 | 0 |
| c | 1 | PR8 | 1 | PR9 | PR15 | 0 |
| d | 1 | PR13 | 1 | PR16 | PR17 | 0 |
| x | 1 | PR1 | 1 | PR2 | PR12 | 0 |
| y | 1 | PR14 | 1 | PR15 | PR16 | 0 |

## 사이클 20

이벤트: R: ROB 5 (I6) done=1

| Reg | Frontend | Arch |
|---|---|---|
| R1 | PR1 | PR1 |
| R2 | PR2 | PR2 |
| R3 | PR12 | PR12 |
| R4 | PR4 | PR4 |
| R5 | PR17 * | PR13 |
| R6 | PR6 | PR6 |
| R7 | PR14 | PR14 |
| R8 | PR8 | PR8 |
| R9 | PR9 | PR9 |
| R10 | PR15 | PR15 |
| R11 | PR16 | PR16 |

PRF (V, 값): PR1=(1,1), PR2=(1,2), PR3=(1,3), PR4=(1,4), PR5=(1,5), PR6=(1,6), PR7=(1,7), PR8=(1,8), PR9=(1,9), PR10=(1,10), PR11=(1,11), PR12=(1,2), PR13=(1,6), PR14=(1,8), PR15=(1,17), PR16=(1,136), PR17=(1,142), PR18=(0,), PR19=(0,), PR20=(0,), PR21=(0,), PR22=(0,)

free list: PR18 PR19 PR20 PR21 PR22 PR3 PR5 PR7 PR10 PR11

ROB (head=5, tail=6):

| # | valid | dst | DestPR | oldPR | done |
|---|---|---|---|---|---|
| 0 | 0 | R3 | PR12 | PR3 | 1 |
| 1 | 0 | R5 | PR13 | PR5 | 1 |
| 2 | 0 | R7 | PR14 | PR7 | 1 |
| 3 | 0 | R10 | PR15 | PR10 | 1 |
| 4 | 0 | R11 | PR16 | PR11 | 1 |
| 5 | 1 | R5 | PR17 | PR13 | 1 |

RS:

| RS | V1 | PR1 | V2 | PR2 | DestPR | busy |
|---|---|---|---|---|---|---|
| a | 1 | PR12 | 1 | PR4 | PR13 | 0 |
| b | 1 | PR2 | 1 | PR6 | PR14 | 0 |
| c | 1 | PR8 | 1 | PR9 | PR15 | 0 |
| d | 1 | PR13 | 1 | PR16 | PR17 | 0 |
| x | 1 | PR1 | 1 | PR2 | PR12 | 0 |
| y | 1 | PR14 | 1 | PR15 | PR16 | 0 |

## 사이클 21

이벤트: W: I6 retire, Arch R5: PR13 → PR17, PR13 → free list

| Reg | Frontend | Arch |
|---|---|---|
| R1 | PR1 | PR1 |
| R2 | PR2 | PR2 |
| R3 | PR12 | PR12 |
| R4 | PR4 | PR4 |
| R5 | PR17 | PR17 |
| R6 | PR6 | PR6 |
| R7 | PR14 | PR14 |
| R8 | PR8 | PR8 |
| R9 | PR9 | PR9 |
| R10 | PR15 | PR15 |
| R11 | PR16 | PR16 |

PRF (V, 값): PR1=(1,1), PR2=(1,2), PR3=(1,3), PR4=(1,4), PR5=(1,5), PR6=(1,6), PR7=(1,7), PR8=(1,8), PR9=(1,9), PR10=(1,10), PR11=(1,11), PR12=(1,2), PR13=(1,6), PR14=(1,8), PR15=(1,17), PR16=(1,136), PR17=(1,142), PR18=(0,), PR19=(0,), PR20=(0,), PR21=(0,), PR22=(0,)

free list: PR18 PR19 PR20 PR21 PR22 PR3 PR5 PR7 PR10 PR11 PR13

ROB (head=6, tail=6):

| # | valid | dst | DestPR | oldPR | done |
|---|---|---|---|---|---|
| 0 | 0 | R3 | PR12 | PR3 | 1 |
| 1 | 0 | R5 | PR13 | PR5 | 1 |
| 2 | 0 | R7 | PR14 | PR7 | 1 |
| 3 | 0 | R10 | PR15 | PR10 | 1 |
| 4 | 0 | R11 | PR16 | PR11 | 1 |
| 5 | 0 | R5 | PR17 | PR13 | 1 |

RS:

| RS | V1 | PR1 | V2 | PR2 | DestPR | busy |
|---|---|---|---|---|---|---|
| a | 1 | PR12 | 1 | PR4 | PR13 | 0 |
| b | 1 | PR2 | 1 | PR6 | PR14 | 0 |
| c | 1 | PR8 | 1 | PR9 | PR15 | 0 |
| d | 1 | PR13 | 1 | PR16 | PR17 | 0 |
| x | 1 | PR1 | 1 | PR2 | PR12 | 0 |
| y | 1 | PR14 | 1 | PR15 | PR16 | 0 |

