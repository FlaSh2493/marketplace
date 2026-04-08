---
name: task-sync-publish
description: Main Session 전용. Writer가 작성한 로컬 문서를 검증하고 Jira Story로 생성한다. "지라에 올려줘", "티켓 생성해줘" 등을 요청할 때 사용한다.
---

# Frontend Task Publish

**실행 주체: Main Session 전용**
사용자 승인 없이 jira_create.py 실행 금지.

## 사용법
`/task-sync:publish`

## 실행 절차

STEP 0: 전제조건 검증
  `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py publish`
  exit 0 → data(branch, task_dir, state_dir) 보관
  exit 1 → reason 출력, [STOP]

STEP 1: Pending 파일 탐색·검증
  `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/list_tasks.py {branch} --state PENDING`
  결과 없음 → STEP 2로.
  각 pending 이슈:
    `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate_template.py {task_dir}/{이슈키}/{이슈키}.md`
    exit 1 → reason 출력, [STOP] (수정 후 재실행 안내)
  검증 통과:
    `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/transition.py {branch} {이슈키} NONE DRAFT`

STEP 2: DRAFT 목록 출력
  `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/list_tasks.py {branch} --state DRAFT`
  결과 없음 → "DRAFT 이슈 없음" [STOP]
  테이블 출력: | ID | 작업 제목 |

[GATE] STEP 3: Jira 설정 확인
  AskUserQuestion("Jira Project Key / Epic (선택) / Sprint ID (선택)를 알려주세요")
  [LOCK: 응답 전 jira_create.py 절대 실행 금지]

STEP 4: Jira Story 생성
  각 DRAFT 이슈:
    4-1. `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/transition.py {branch} {이슈키} DRAFT PUBLISHING`
         exit 1 → reason 출력, [STOP]
    4-2. `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/md_to_adf.py {이슈키} "$(pwd)/{task_dir}/{이슈키}/{이슈키}.md" > /tmp/{이슈키}_adf.json`
         exit 1 → reason 출력, [STOP]
    4-3. `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/jira_create.py --project {project_key} --summary "{제목}" --adf-file /tmp/{이슈키}_adf.json {--epic ...} {--sprint ...}`
         exit 0 → key 보관
         exit 1 → `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/transition.py {branch} {이슈키} PUBLISHING DRAFT` (복구) → reason 출력, [STOP]

STEP 5: 리네임·상태 전이
  `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/update_jira_keys.py {task_dir} '{"FE-01":"PROJ-101",...}'`
  exit 1 → reason 출력, [STOP]
  각 이슈: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/transition.py {branch} {jira_key} PUBLISHING PUBLISHED`

STEP 6: 완료 보고
  테이블 출력: | 기존 폴더 | Jira Key | 작업 제목 |

[TERMINATE]
