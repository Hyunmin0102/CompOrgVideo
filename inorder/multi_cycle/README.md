# 2편: multi-cycle MIPS

슬라이드: `inorder/slides/B_multi_cycle_slides.pdf`
(PDF 1–12 = 슬라이드 24–35 데이터패스 구성, 13 = 36, 14–24 = 38–48 제어 FSM, 25–28 = 51–54 j,
29 = 57 데이터패스 정리, 30 = 58 FSM 정리, 31 = single-cycle 지연 표(L10 90과 같음))

## 실행 순서
```bash
python3 inorder/multi_cycle/sim/multi_cycle.py      # -> out/trace.json
python3 inorder/multi_cycle/verify/verify_multi.py  # -> out/verify_report.md (불일치 시 exit 1)
```

## 렌더링
```bash
manim --dry_run inorder/multi_cycle/render/multi_cycle_scene.py MultiCycle            # 화면 ↔ trace 대조만
MC_STEPS=9 manim -ql --media_dir /tmp/media inorder/multi_cycle/render/multi_cycle_scene.py MultiCycle   # 처음 N사이클
manim --resolution 1920,1080 --frame_rate 30 --media_dir /tmp/media \
      inorder/multi_cycle/render/multi_cycle_scene.py MultiCycle                      # 완성본 (약 17분)
```
렌더러는 multi-cycle trace만 읽고, 마지막 비교 장면에서만 1편 trace의 총 시간을 읽는다. mp4는 올리지 않는다.

## 연출
- 한 상태의 일을 "저장 목적"(trace `jobs`)별로 하나씩 보여주고, 배선은 인과 순서(`wire_hop`)대로 한 칸씩 켠다.
  지연 부품(메모리·ALU·레지스터 파일)이 일하는 동안 ps 막대가 자란다.
- 사이클 사이에 그림을 초기화하지 않고 바뀌는 부품·제어 신호만 움직인다. FSM 동그라미에 적힌 신호만 진하게 표시.
- 클록 에지에서 의미 있는 저장(trace `intended`)을 하나씩 레지스터 칸으로 옮기고, 덮어쓰이기만 하는 값은 회색.
- 마지막 장면: 명령어별 200ps 칸 + 1편 600ps 비교, 36 × 200ps = 7200ps vs 9 × 600ps = 5400ps.

## 구성
- `sim/multi_cycle.py` — 레지스터 수준 사이클 시뮬레이터. FSM(S0–S10)이 제어 신호를 내고,
  매 사이클 조합 값(Adr, SrcA/B, ALUResult, PC' …)과 클록 에지의 PC·IR·Data·A·B·ALUOut·레지스터·메모리 변화를 기록
- `verify/reference_slides.py` — 슬라이드 58(PDF 30쪽) 동그라미 글자·화살표, 슬라이드 57 mux 입력 순서
- `verify/verify_multi.py` — 인터프리터·슬라이드 대조, X 선택을 0/1 두 가지로 돌려 결과가 같은지 확인
- 데이터패스 그림: `inorder/shared/datapath.py`의 `Datapath(variant="multi")`.
  사용자가 준 H&H multi-cycle 프로세서 그림(`inorder/slides/B_multi_cycle_datapath_ref.png`,
  슬라이드 57과 같은 구성, j 없음)의 픽셀 좌표를 그대로 옮겨 부품·배선 위치를 정했다.
  그래서 1편과 부품 위치가 다르다(RegDst·MemtoReg mux는 레지스터 파일 왼쪽, PCSrc mux는 오른쪽 끝).

## 가정 (`config.assumptions`)
1. 클록 주기 200ps — 슬라이드에 multi-cycle 클록 값이 없어, L10 90 지연(레지스터 오버헤드 0)으로
   가장 긴 상태(메모리 접근)를 잡음.
2. ALUControl 인코딩과 ALU 디코더(ALUOp→연산)는 H&H 7장 표.
3. FSM 그림에 없는 쓰기 신호는 0, mux 선택은 X. 시뮬레이션은 X를 0번 입력으로 두고, 1로 바꿔도
   최종 상태가 같음을 검증.
4. j(S11) 생략.
