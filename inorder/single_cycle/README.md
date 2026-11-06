# 1편: single-cycle MIPS

슬라이드: `inorder/slides/A_single_cycle_slides.pdf`
(PDF 1 = L10 49, 2–11 = L10 52–61, 12–22 = L10 87–97, 23–24 = L11 55–56)

## 실행 순서
```bash
python3 inorder/shared/interpreter.py                 # 기준 최종 상태
python3 inorder/single_cycle/sim/single_cycle.py      # -> out/trace.json
python3 inorder/single_cycle/verify/verify_single.py  # -> out/verify_report.md (불일치 시 exit 1)
```

## 구성
- `sim/single_cycle.py` — 명령어마다 제어 신호(RegWrite, RegDst, ALUSrc, Branch, MemWrite,
  MemtoReg, ALUControl), 데이터 값, 사용 부품·배선, ps 단위 신호 도착 시각, 낭비 시간을 `out/trace.json`에 기록
- `verify/reference_slides.py` — 슬라이드 페이지 이미지에서 옮겨 적은 기준 데이터
  (L10 56–61 그림의 mux 선택·신호 값, L10 90 지연 표, L10 92–95 경로 주석)
- `verify/verify_single.py` — trace ↔ 인터프리터 / 슬라이드 대조 보고
- `render/single_cycle_scene.py` — Manim 렌더러. `out/trace.json`만 읽고, 매 사이클 `check_board`로 화면과 trace를 대조

## 렌더링
```bash
manim --dry_run inorder/single_cycle/render/single_cycle_scene.py SingleCycle          # 대조만
SC_STEPS=2 manim -ql --media_dir /tmp/media inorder/single_cycle/render/single_cycle_scene.py SingleCycle   # 처음 N개 미리보기
manim --resolution 1920,1080 --frame_rate 30 --media_dir /tmp/media \
      inorder/single_cycle/render/single_cycle_scene.py SingleCycle                    # 완성본 (약 7분 40초)
```
mp4는 저장소에 올리지 않는다(.gitignore).

## 연출 (2편과 같은 방식)
- 명령어 하나 = 클록 1개. 사이클 안을 일(trace `jobs`) 단위로 하나씩 보여준다:
  IF ① 명령어 읽기 → IF ② PC+4 → ID → EX → MEM → WB → 다음 PC 선택.
  배선은 인과 순서(`wire_hop`)대로 한 칸씩 켜고, 지연 부품이 일하는 동안 ps 막대(시작→끝)가 자란다.
- 사이클 사이에 그림을 초기화하지 않고 바뀌는 부품·제어 신호만 움직인다(X는 옅은 회색).
- 일이 끝난 시각 이후 600ps까지는 빨간 "낭비" 막대. 클록 에지에서 레지스터·메모리·PC 값을 하나씩 칸으로 옮긴다.
- 마지막 장면: 9 × 1 × 600ps = 5400ps (필요 3900ps, 낭비 1500ps). 완성본 약 7분 40초.

## 가정 (`config.assumptions`, 영상에는 "※ 강의 범위 밖 가정")
1. ALUControl 3비트 값은 H&H 7장 인코딩(add 010, sub 110, and 000, or 001, slt 111).
   슬라이드에는 funct/opcode/Add/bcond라는 연산 이름만 나온다.
2. beq 비교(bcond)는 H&H처럼 ALU 뺄셈 + Zero 신호로 한다.
3. 분기 목표 덧셈기는 부호 확장 즉치값이 준비된 200ps에 시작해 300ps에 끝나는 것으로 계산.
   L10 95 그림은 이 지점을 200ps로 표시하지만, beq 전체 350ps에는 영향이 없다.
4. 단순화한 데이터패스에는 j 경로가 없다. 제어선은 Branch→AND만 그리고, 나머지 제어 신호는
   해당 부품 옆 주황 라벨과 오른쪽 패널로 보여준다.
