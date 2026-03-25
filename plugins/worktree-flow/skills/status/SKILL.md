---
name: status
description: 현재 활성화된 모든 워크트리의 상태(브랜치, WIP 커밋 수, 진행 단계)를 조회한다.
---

# Worktree Status

**실행 주체: Main Session 전용**

## 사용법
`/worktree-flow:status`

## 실행 절차

STEP 1: 상태 조회
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/status.py`
  성공: 아래 형식으로 출력
  ```
  ┌──────────┬──────────┬────────┬────────────────────────┐
  │ 이슈     │ 상태     │ WIP수  │ 마지막 커밋             │
  ├──────────┼──────────┼────────┼────────────────────────┤
  │ PLAT-101 │ BUILDING │  3개   │ 2026-03-25T14:32:01    │
  │ PLAT-102 │ APPROVED │  0개   │ -                      │
  └──────────┴──────────┴────────┴────────────────────────┘
  ```
  실패: reason 그대로 출력 후 [STOP]

[TERMINATE]
