---
name: init-hooks
description: Stop 훅을 메인 저장소 .claude/settings.json에 등록한다. 모든 스킬 사용 전 1회 실행 필수.
---

# Init Hooks

**실행 주체: Main Session 전용**

## 사용법
`/worktree-flow:init-hooks`

## 실행 절차

STEP 0: 중복 등록 확인
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py init-hooks`
  성공 (already_registered=true): "Stop 훅이 이미 등록되어 있습니다." 출력 후 [TERMINATE]
  성공 (already_registered=false): STEP 1 진행
  실패: reason 그대로 출력 후 [STOP]

STEP 1: 훅 등록
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/install_hooks.py`
  성공: "Stop 훅 등록 완료. 세션 종료 시 WIP 자동 커밋이 활성화됩니다." 출력
  실패: reason 그대로 출력 후 [STOP]

[TERMINATE]
