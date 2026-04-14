---
name: task-sync-update
description: Writer 서브에이전트 전용. 로컬에서 수정된 마크다운 파일의 내용을 Jira 이슈에 동기화한다.
---

# Frontend Task Update

**실행 주체: Writer 에이전트 전용**
마크다운 → Jira 단방향 동기화. 요약·해석 없이 원문 그대로 반영.

## 사용법
`/task-sync:update`

## 실행 절차

STEP 0: 대상 탐색
  `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py update`
  exit 0 → data(branch, task_dir, state_dir, published) 보관
  exit 1 → reason 출력, [STOP]

STEP 1: 목록 출력
  `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/list_tasks.py {branch} --state PUBLISHED`
  exit 0 → 응답의 tasks 배열로 테이블 출력 (스크립트가 issue, title 반환):
    | 번호 | Jira Key | 작업 제목 |
  결과 없음 → "PUBLISHED 이슈 없음" [STOP]

[GATE] STEP 2: 동기화 대상 선택
  AskUserQuestion("동기화할 이슈 번호 (예: 1,3 / 전체: all)")
  [LOCK: 응답 전 jira_update.py 실행 금지]

STEP 3: 변경 내용 분석
  선택된 각 파일 Read → 제목, ## 설명, ## 추가 요구사항, ## 첨부 이미지, deps/api/states 추출
  테이블: | Jira Key | 동기화 내용 |

[GATE] STEP 4: 동기화 확인
  AskUserQuestion("위 내용을 Jira에 반영할까요?")
  [LOCK: 응답 전 jira_update.py 실행 금지]
  "no" → [TERMINATE]

STEP 5: Jira 업데이트
  각 이슈:
    `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/md_to_adf.py {jira_key} "$(pwd)/.docs/task/{branch}/{이슈키}/{이슈키}.md" --sections "설명,화면/디자인,컴포넌트 힌트,영향 범위,완료 조건,추가 요구사항" > /tmp/{이슈키}_adf.json`
    exit 1 → reason 출력, 다음 이슈 계속
    `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/jira_update.py {이슈키} --summary "{제목}" --adf-file /tmp/{이슈키}_adf.json`
    exit 1 → reason 출력, 다음 이슈 계속

STEP 6: 완료 알림
  notify_user("Jira 동기화 완료 [{이슈키 목록}]")

[TERMINATE]
댓글 역동기화 금지. 반영 섹션: 설명, 화면/디자인, 컴포넌트 힌트, 영향 범위, 완료 조건, 추가 요구사항. 헤더 메타데이터(- jira:, - 상태: 등)는 Jira에 반영하지 않는다.
