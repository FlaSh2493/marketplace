---
name: create
description: 피처 브랜치에서 이슈별 워크트리를 생성하고 Planner 에이전트를 런칭한다.
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

STEP 3: Planner 에이전트 런칭
  생성된 각 이슈에 대해 헤드리스 Planner 에이전트 런칭:
    - 에이전트: wt-manager (planner 역할)
    - 작업 디렉토리: {워크트리 경로}
    - 프롬프트: "/worktree-flow:plan {issue}"
  출력: "Planner 에이전트 {N}개 시작됨. 플랜 완료 시 알림 예정."

[TERMINATE]
