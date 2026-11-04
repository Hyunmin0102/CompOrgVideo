# Out-of-Order 실행 영상 (ETH DDCA L14)

공통 규칙은 저장소 루트의 `CLAUDE.md`, 공통 스타일은 `common/style.py`를 따른다.
아래 명령은 모두 이 `ooo/` 폴더에서 실행한다.

## 1편: Tomasulo (슬라이드 36–63)

```
sim/tomasulo_sim.py          시뮬레이터 → out/trace.json  (렌더러의 유일한 입력)
verify/slide_transcription.py 슬라이드 41–63 이미지를 칸 단위로 옮겨 적은 정답 데이터
verify/verify.py             trace.json ↔ 정답 비교 → out/verification_report.md (불일치 시 exit 1)
render/tomasulo_scene.py     Manim 렌더러: Intro / Cycles(TOMASULO_CYCLES="0-3") / Outro / FullVideo
```

실행:

```bash
python3 sim/tomasulo_sim.py && python3 verify/verify.py
```

```bash
cd render && manim -ql --media_dir /tmp/media tomasulo_scene.py FullVideo
```

## 슬라이드에서 확정한 사이클 내부 규칙

| 규칙 | 근거 슬라이드 |
|---|---|
| 명령어 i: 사이클 i에 F, i+1에 D (할당 + 소스 복사 + 목적 레지스터 renaming) | 42–48 |
| 할당 때 두 소스가 valid면 **다음 사이클**에 E1 | 43 (x), 45 (b), 46 (c) |
| 마지막 E 사이클에 tag/value broadcast → 같은 사이클에 RS·RAT 갱신 | 49, 50, 52, 55, 58, 62 |
| broadcast로 값을 받은 엔트리는 다음 사이클에 E1 | 49 하단 (a), 52 (y), 58 (d) |
| 타이밍 표의 W는 broadcast 다음 사이클 | 52 (사이클 9의 W) |
| 같은 사이클의 broadcast 두 개(버스 분리)는 program order로 나열 | 49 → 50 |
| 완료된 RS 엔트리의 내용은 지우지 않고 표시만 유지 (busy만 해제) | 52–63 |
| broadcast tag가 RAT의 현재 tag와 다르면 RAT는 갱신하지 않음 | 55 (a=6, R5는 d) |
| adder·multiplier는 각각 1개, 파이프라인화 (b와 c가 겹쳐 실행) | 강의 가정, 46–47 |

사이클 내 단계 순서: ① Decode & Allocate → ② Wake-up/Select → ③ Dispatch & Execute → ④ Broadcast.
선택 가능 조건이 "이전 사이클 끝까지 두 소스 valid"로 고정되어 있으므로 ④에서 받은 값은 다음 사이클에야 쓰입니다.

## 2편: ROB + PRF + 포인터 (슬라이드 71–82)

```
sim/prf_sim.py          → out/prf_trace.json   (실행 타이밍은 tomasulo_sim과 동일)
verify/verify_prf.py    → out/prf_verification_report.md, out/prf_state_tables.md
render/prf_scene.py     PRFPreview(PRF_CYCLES="0-3") / PRFFullVideo
```

```bash
python3 sim/prf_sim.py && python3 verify/verify_prf.py
```

```bash
cd render && manim -ql --media_dir /tmp/media prf_scene.py PRFFullVideo
```

규칙: R = 마지막 E 다음 사이클(ROB done=1), W(retire) = R 다음 사이클부터, 사이클당 1개, program order.
retire 시 Arch Map[dst] = DestPR, oldPR → free list 뒤. 총 21사이클.
렌더러는 매 단계 끝에 화면의 모든 칸·화살표·free list를 trace와 대조하고, 다르면 멈춘다.

## 완성본 (저장소에는 없음, .gitignore)
- `out/tomasulo_full_1080p.mp4` — 1편, 1080p 30fps, 5분 50초
- `out/prf_full_1080p.mp4` — 2편, 1080p 30fps, 7분 24초
