# 3편: pipelined MIPS

슬라이드: `inorder/slides/C_pipeline_slides.pdf` (쪽 ↔ 슬라이드 번호는 `verify/reference_slides.py` 머리말)

## 실행 순서
```bash
python3 inorder/pipeline/sim/pipeline.py                # -> out/trace.json
python3 inorder/pipeline/verify/verify_pipeline.py      # -> out/verify_report.md (불일치 시 exit 1)
```

## 구성
- `sim/pipeline.py` — H&H Fig. 7.58(슬라이드 79/85) 5단계 파이프라인 사이클 시뮬레이터.
  always-not-taken, Decode 단계 분기 판정, MEM→EX·WB→EX forwarding, Decode로의 forwarding,
  lwstall·branchstall·FlushE(슬라이드 69 식 그대로), taken 분기 시 IF/ID CLR=PCSrcD.
  WB는 사이클 앞 절반에 레지스터 파일을 쓰고 ID는 뒤 절반에 읽는다.
  매 사이클 단계별 명령어, hazard 신호, forwarding·stall·flush 사건, 값, 상태 변화를 기록.
- `verify/reference_slides.py` — 슬라이드 69 코드, forwarding 의사코드, Fig. 7.58 연결, 슬라이드 86 표
- `verify/verify_pipeline.py` — 인터프리터 대조, 설계한 hazard 위치, 슬라이드 20(같은 제어 유닛) 대조,
  사이클 수 식, 1·2편과 실행 시간 비교

- 데이터패스 그림: `inorder/shared/datapath.py`의 `Datapath(variant="pipe")` — 슬라이드 79(Fig. 7.58)를
  200dpi 이미지에서 픽셀 좌표로 옮긴 배치. 화면 왼쪽 2/3에 두고, 오른쪽은 파이프라인 다이어그램·레지스터 표.
  `PL_WIRE_STAGE`로 배선마다 단계를 정해, 그 단계에 있는 명령어의 색(`common/style.py`의 `INSTR_COLORS`)으로 칠한다.

## 결과
15 사이클 × 200ps = 3000ps (single 5400ps, multi 7200ps).
I1→I2 lw stall 1, I1→I2·I2→I4 WB→EX, I2→I3 MEM→EX, I2→I5·I4→I7 레지스터 파일 반 사이클, I7 taken → I8 flush.

## 가정 (`config.assumptions`)
1. 클록 200ps — L10 90 지연 + 슬라이드 83의 단계 식(ID·WB ×2). 슬라이드 86의 550ps는 다른 지연 표.
2. 제어 유닛·ALUControl은 1편과 동일. X 신호는 0으로 두고 1로도 결과 같음을 검증.
3. IF/ID는 StallD가 CLR보다 우선(H&H flopenrc) — 이 프로그램에서는 겹치지 않음.
4. 프로그램 끝 이후 fetch는 bubble. j 생략.
