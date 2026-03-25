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

STEP 3: 완료 안내
  출력: "워크트리 생성 완료. 각 워크트리 세션에서 /worktree-flow:plan {이슈키}를 실행하세요."

[TERMINATE]
