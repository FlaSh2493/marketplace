---
name: publish
description: Main Session 전용. Writer가 작성한 로컬 문서를 검증하고 Jira Story로 생성한다. "지라에 올려줘", "티켓 생성해줘" 등을 요청할 때 사용한다.
---

# Frontend Task Publish

**실행 주체: Main Session 전용**
사용자 승인 없이 jiraCreateIssue 실행 금지.

## 사용법
`/fe-task-extractor:publish`

## 실행 절차

STEP 0: 전제조건 검증
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py publish`
  성공: data.branch, data.task_dir 보관
  실패: reason 그대로 출력 후 [STOP]

STEP 1: Pending 파일 탐색 및 검증
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/list_tasks.py {branch} --state PENDING`
  성공: pending 이슈 목록 보관
  결과가 없으면: "검증할 파일이 없습니다." 출력 후 STEP 2로 바로 이동

  각 pending 이슈마다:
    실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate_template.py {task_dir}/{이슈키}/{이슈키}.md`
    성공: 통과
    실패: reason 출력 후 [STOP] — 파일을 수정한 뒤 다시 실행

  검증 통과 후 상태 전이:
    실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/transition.py {branch} {이슈키} NONE DRAFT`

STEP 2: DRAFT 목록 출력
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/list_tasks.py {branch} --state DRAFT`
  결과가 없으면: "DRAFT 상태인 이슈가 없습니다." [STOP]
  아래 형식으로 출력:
  ```
  | ID       | 작업 제목        |
  |----------|----------------|
  | FE-01    | 로그인 폼 UI    |
  | PROJ-102 | 목록 페이지 구현 |
  ```

[GATE] STEP 3: Jira 설정 확인
  AskUserQuestion("Jira Project Key / Epic (선택) / Sprint (선택)를 알려주세요")
  [LOCK: 응답 전 jiraCreateIssue 절대 실행 금지]

STEP 4: Jira Story 생성
  각 DRAFT 이슈마다:

  4-1. 상태 전이 (잠금)
    실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/transition.py {branch} {이슈키} DRAFT PUBLISHING`
    실패: reason 그대로 출력 후 [STOP]

  4-2. Jira Story 생성 (Claude MCP)
    `jiraCreateIssue`:
      - issuetype: Story
      - summary: 파일의 작업 제목
      - description: 파일의 ## 설명 섹션 원문
      - assignee: currentUser()
      - epic: (STEP 3에서 지정된 경우)
      - sprint: (STEP 3에서 지정된 경우)
    실패:
      실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/transition.py {branch} {이슈키} PUBLISHING DRAFT` (복구)
      reason 출력 후 [STOP]

STEP 5: 리네임 및 상태 전이
  전체 key_map 수집:
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/update_jira_keys.py {task_dir} '{"FE-01":"PROJ-101",...}'`
  실패: reason 그대로 출력 후 [STOP]

  각 이슈마다:
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/transition.py {branch} {jira_key} PUBLISHING PUBLISHED`
  실패: reason 그대로 출력 후 [STOP]

  pending 마커 정리:
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/transition.py {branch} {이슈키} NONE DRAFT` — 이미 처리됨, 스킵

STEP 6: 완료 보고
  ```
  ✅ Jira 등록 완료

  | 기존 폴더   | Jira Key  | 작업 제목        |
  |-----------|-----------|----------------|
  | FE-01/    | PROJ-101  | 로그인 폼 UI    |
  | FE-02/    | PROJ-102  | 목록 페이지 구현 |
  ```

[TERMINATE]
