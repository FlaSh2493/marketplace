---
name: task-sync-write
description: 이슈키를 지정하여 Jira 이슈를 로컬 마크다운으로 저장하는 스킬. fetch 후에 직접 호출하여 사용한다.
---

# Frontend Task Write

## 사용법
`/task-sync:write {이슈키} [{이슈키}...]`

## 실행 절차

STEP 0: 전제조건 검증
  `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py fetch`
  exit 0 → data(branch, task_dir, state_dir) 보관
  exit 1 → reason 출력, [STOP]

  CLAUDE_PLUGIN_ROOT 값 확보: `echo $CLAUDE_PLUGIN_ROOT`

STEP 1: write.py 실행 (마크다운 생성)
  `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/write.py {이슈키들} --task-dir {task_dir} --state-dir {state_dir}`
  → 스크립트 출력을 그대로 사용자에게 표시
  exit 0 → [TERMINATE]
  exit 1 → 출력 내용 그대로 표시, [STOP]

[TERMINATE]
