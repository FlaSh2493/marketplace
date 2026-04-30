---
name: init
description: autopilot 초기 설정을 도와준다. code-review-graph 설치 확인, 그래프 빌드, 사용법 안내까지 진행한다.
disable-model-invocation: true
---

# Worktree Flow Init

## 사용법
`/autopilot:init`

---

## STEP 1: code-review-graph 설치 확인

```bash
claude plugin list 2>/dev/null | grep code-review-graph
```

- 설치됨 → STEP 2 진행
- 미설치 → 아래 안내 출력 후 [STOP]:

```
code-review-graph 플러그인이 필요합니다.

설치 방법:
  1. 마켓플레이스 등록 (최초 1회)
     /plugin marketplace add tirth8205/code-review-graph

  2. 플러그인 설치
     /plugin install code-review-graph@code-review-graph

설치 후 /autopilot:init 을 다시 실행하세요.
```

---

## STEP 2: 그래프 빌드 여부 확인

```bash
ls .code-review-graph/graph.db 2>/dev/null && echo "exists" || echo "missing"
```

- `exists` → STEP 3 진행
- `missing` → "코드 그래프를 빌드합니다. 프로젝트 크기에 따라 수 초~수십 초 소요됩니다." 출력 후 MCP tool 호출: `build_or_update_graph_tool` (full_rebuild: false)
  - 성공 → STEP 3 진행
  - 실패 → 아래 안내 출력 후 [STOP]:
    ```
    그래프 빌드에 실패했습니다.

    수동으로 빌드하려면:
      /code-review-graph:build-graph

    또는 터미널에서:
      uvx code-review-graph build
    ```

---

## STEP 3: 완료 안내

아래 출력 후 [STOP]:

```
autopilot 준비 완료!

사용 방법:
┌─────────────────────────────────────────────────────────┐
│ 작업 시작    /autopilot:plan {이슈키}               │
│ 상태 확인    /autopilot:status                      │
│ 머지         /autopilot:merge {피처브랜치}           │
└─────────────────────────────────────────────────────────┘

플랜 작성 시 code-review-graph로 관련 파일을 정확하게 분석합니다.
코드베이스가 변경되면 그래프를 업데이트하세요:
  /code-review-graph:build-graph
```
