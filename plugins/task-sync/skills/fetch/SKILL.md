---
name: task-sync-fetch
description: Jira에서 나에게 할당된 미완료 이슈를 조회하고 로컬 마크다운으로 저장하는 스킬. "내 지라 이슈 가져와줘", "지라 불러와", "내 할 일 불러와" 등을 요청할 때 사용한다.
---

# Frontend Task Fetch

## 사용법
- `/task-sync:fetch` — 내 할당 미완료 이슈 전체
- `/task-sync:fetch PROJ-101 PROJ-102` — 이슈 직접 지정

## 실행 절차

STEP 0: 전제조건 검증
  `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py fetch`
  exit 0 → data(branch, task_dir, state_dir) 보관
  exit 1 → reason 출력, [STOP]

  CLAUDE_PLUGIN_ROOT 값 확보: `echo $CLAUDE_PLUGIN_ROOT`

STEP 1: fetch_write.py 실행
  `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/fetch_write.py {인수들} --task-dir {task_dir} --state-dir {state_dir}`
  → 스크립트 출력(테이블, 진행 상황, 결과 요약)을 그대로 사용자에게 표시
  exit 0 → [TERMINATE]
  exit 1 → 출력 내용 그대로 표시, [STOP]

[TERMINATE]
