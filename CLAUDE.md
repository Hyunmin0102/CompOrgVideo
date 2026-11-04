# CompOrgVideo

ETH Zürich DDCA(Digital Design and Computer Architecture, Onur Mutlu) 강의의 개념을
눈으로 이해하기 위한 Manim(Community Edition) 학습 영상 시리즈.

## 폴더
- `common/style.py` — 모든 영상 공통 스타일 (색, 폰트, 자막, 예측용 정지, 단계 표시줄)
- `ooo/` — Out-of-Order 실행 (L14): Tomasulo(슬라이드 36–63), ROB + PRF(슬라이드 71–82)
- `inorder/` — single-cycle / multi-cycle / pipeline (예정)
- 각 영상 폴더: `sim/` 시뮬레이터, `verify/` 검증, `render/` 렌더러, `out/` 결과, `README.md`

## 규칙
1. **스타일**: `common/style.py`를 쓴다(`StyleScene`, `Cell`, `txt`, 색 상수, `term`, `ASSUME`).
   영상 폴더에서 색·폰트를 새로 정의하지 않는다.
   현재 사이클 = 노랑, 방금 바뀐 값 = 파랑, 연결선 = 주황, 흰 배경, 사이클마다 2초 예측 정지.
2. **데이터 흐름**: 시뮬레이터가 `out/*.json`(trace)을 만들고, 렌더러는 그 trace만 읽는다.
   레지스터 값·사이클 수·태그 같은 시뮬레이션 값을 렌더러 코드에 직접 적지 않는다.
3. **검증**: 렌더링 전에 `verify/`로 trace를 기준 데이터(슬라이드에서 옮겨 적은 표 등)와 대조하고,
   불일치는 표로 보고한다. 렌더러도 매 단계 화면과 trace를 대조(`check_board`)하고 다르면 멈춘다.
   `manim --dry_run`으로 렌더링 없이 이 대조만 먼저 돌릴 수 있다.
4. **슬라이드 읽기**: 표·그림·화살표는 PDF 텍스트 추출이 깨지므로 반드시 페이지 이미지로 읽는다
   (작은 칸은 고해상도로 확대). 기준 데이터도 이미지에서 옮겨 적는다.
5. **가정**: 슬라이드에 없는 가정은 trace의 `config.assumptions`에 적고,
   영상에는 "※ 강의 범위 밖 가정" 자막으로 표시한다. 강의에서 말로만 한 가정은 그렇다고 밝힌다.
6. **자막**: 한국어, 핵심 용어는 영어 병기 — 예: 예약 스테이션(reservation station) (`term()`).
7. **진행 순서**: 시뮬레이터 + 검증 보고 → 확인 → 저해상도(`-ql`) 미리보기 → 확인
   → 1080p 렌더링(`--resolution 1920,1080 --frame_rate 30`). 단계마다 멈추고 결과를 보여준다.
8. **영상 사이 독립성**: `ooo/`와 `inorder/`는 서로의 가정(실행 지연, 유닛 수, retire 규칙 등)을
   섞지 않는다. 함께 쓰는 것은 `common/`뿐이다.
9. **저장소**: mp4, `media/`, `__pycache__/`는 올리지 않는다(.gitignore).
   렌더링할 때는 `--media_dir`를 저장소 밖으로 주거나, 생긴 `media/`를 커밋하지 않는다.

## 환경
- Python 3, Manim CE 0.22, 폰트 Noto Sans CJK KR · DejaVu Sans Mono (LaTeX 없이 `Text`만 사용)
- 렌더러는 저장소 루트를 `sys.path`에 넣고 `from common.style import ...`로 가져온다.
