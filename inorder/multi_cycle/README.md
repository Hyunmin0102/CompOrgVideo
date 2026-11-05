# 2편: multi-cycle MIPS

슬라이드: `inorder/slides/B_multi_cycle_slides.pdf`
(PDF 1–12 = 슬라이드 24–35 데이터패스 구성, 13 = 36, 14–24 = 38–48 제어 FSM, 25–28 = 51–54 j,
29 = 57 데이터패스 정리, 30 = 58 FSM 정리, 31 = single-cycle 지연 표(L10 90과 같음))

## 실행 순서
```bash
python3 inorder/multi_cycle/sim/multi_cycle.py      # -> out/trace.json
python3 inorder/multi_cycle/verify/verify_multi.py  # -> out/verify_report.md (불일치 시 exit 1)
```

## 구성
- `sim/multi_cycle.py` — 레지스터 수준 사이클 시뮬레이터. FSM(S0–S10)이 제어 신호를 내고,
  매 사이클 조합 값(Adr, SrcA/B, ALUResult, PC' …)과 클록 에지의 PC·IR·Data·A·B·ALUOut·레지스터·메모리 변화를 기록
- `verify/reference_slides.py` — 슬라이드 58(PDF 30쪽) 동그라미 글자·화살표, 슬라이드 57 mux 입력 순서
- `verify/verify_multi.py` — 인터프리터·슬라이드 대조, X 선택을 0/1 두 가지로 돌려 결과가 같은지 확인
- 데이터패스 그림: `inorder/shared/datapath.py`의 `Datapath(variant="multi")`.
  공통 부품은 1편과 같은 자리, 통합 메모리는 명령어 메모리 자리, IR·A/B·ALUOut·Data는
  pipeline 레지스터가 들어갈 단계 경계(IF/ID, ID/EX, EX/MEM, MEM/WB)에 둔다.

## 가정 (`config.assumptions`)
1. 클록 주기 200ps — 슬라이드에 multi-cycle 클록 값이 없어, L10 90 지연(레지스터 오버헤드 0)으로
   가장 긴 상태(메모리 접근)를 잡음.
2. ALUControl 인코딩과 ALU 디코더(ALUOp→연산)는 H&H 7장 표.
3. FSM 그림에 없는 쓰기 신호는 0, mux 선택은 X. 시뮬레이션은 X를 0번 입력으로 두고, 1로 바꿔도
   최종 상태가 같음을 검증.
4. j(S11) 생략.
