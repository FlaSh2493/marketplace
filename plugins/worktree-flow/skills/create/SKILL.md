---
name: create
description: 피처 브랜치에서 이슈별 워크트리를 생성한다. 플랜 진행 여부는 사용자가 선택한다.
---

# Worktree Create

**실행 주체: Main Session 전용**

## 사용법
- `/worktree-flow:create` — 현재 브랜치 기준, 문서에서 이슈 자동 탐색
- `/worktree-flow:create {피처브랜치}` — 특정 브랜치 기준
- `/worktree-flow:create {피처브랜치} {이슈1} {이슈2}` — 이슈 직접 지정

## 실행 절차

STEP 0: 전제조건 검증
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py create`
  실패: reason 그대로 출력 후 [STOP]

STEP 1: 이슈 목록 확인 및 워크트리 생성
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/create_worktrees.py $ARGUMENTS`
  성공 (mode=selection):
    data.tasks 목록을 표로 출력
    [GATE] STEP 1-A로 이동
  성공 (mode 없음, worktrees 존재):
    STEP 2로 진행
  실패: reason 그대로 출력 후 [STOP]

[GATE] STEP 1-A: 이슈 선택
  실행: AskUserQuestion("생성할 이슈를 선택하세요 (예: PLAT-101 PLAT-102, 전체: all)")
  [LOCK: 응답 전 워크트리 생성 금지]
  응답 수신 후:
    실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/create_worktrees.py {feature} {선택된 이슈들}`
    성공: STEP 2 진행
    실패: reason 그대로 출력 후 [STOP]

STEP 2: 결과 보고
  data.worktrees를 아래 형식으로 출력:
  ```
  ┌──────────┬──────────────────────────────────────┬─────────────────────────────────┐
  │ 이슈     │ 경로                                  │ 브랜치                           │
  ├──────────┼──────────────────────────────────────┼─────────────────────────────────┤
  │ PLAT-101 │ .worktrees/PLAT-101                  │ feat/order--wt-PLAT-101         │
  └──────────┴──────────────────────────────────────┴─────────────────────────────────┘
  ```
  (.wip-active 자동 생성됨 — 수동 활성화 불필요)

[GATE] STEP 3: 플랜 진행 여부 선택
  실행: AskUserQuestion("워크트리 생성이 완료됐습니다.\n플랜을 어떻게 진행할까요?\n- all: 모든 이슈 플랜을 지금 바로 병렬 시작\n- {이슈키...}: 선택한 이슈만 플랜 시작 (예: PROJ-101 PROJ-102)\n- no: 플랜 없이 종료 (나중에 /worktree-flow:plan {이슈키}로 직접 실행)")
  [LOCK: 응답 전 플랜 에이전트 런칭 금지]

  응답 "no":
    출력: "완료. 작업할 워크트리에서 /worktree-flow:plan {이슈키}를 실행하세요."
    [TERMINATE]

  응답 "all":
    대상 이슈 = 생성된 전체 워크트리 이슈 목록

  응답 "{이슈키...}":
    대상 이슈 = 응답에서 파싱한 이슈 키 목록

  대상 이슈에 대해 헤드리스 Planner 에이전트 병렬 런칭:
    - 에이전트: wt-manager (planner 역할)
    - 작업 디렉토리: .worktrees/{이슈키}/
    - 프롬프트: "/worktree-flow:plan {이슈키}"
  출력: "Planner 에이전트 {N}개 시작됨. 플랜 완료 시 알림 예정."

[TERMINATE]
