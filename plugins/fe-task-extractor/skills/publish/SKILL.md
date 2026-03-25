---
name: publish
description: Main Session 전용. DRAFT 상태의 로컬 문서를 Jira Story로 생성하고 파일을 리네임한다. "지라에 올려줘", "티켓 생성해줘" 등을 요청할 때 사용한다.
---

# Frontend Task Publish

**실행 주체: Main Session 전용**
사용자 승인 없이 jiraCreateIssue 실행 금지.

## 사용법
`/fe-task-extractor:publish`

## 실행 절차

STEP 0: 전제조건 검증
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py publish`
  성공: data.branch, data.drafts 보관
  실패: reason 그대로 출력 후 [STOP]

STEP 1: DRAFT 목록 출력
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/list_tasks.py {branch} --state DRAFT`
  성공: 아래 형식으로 출력:
  ```
  | ID    | 작업 제목        |
  |-------|----------------|
  | FE-01 | 로그인 폼 UI    |
  | FE-02 | 목록 페이지 구현 |
  ```
  실패: reason 그대로 출력 후 [STOP]

[GATE] STEP 2: Jira 설정 확인
  실행: AskUserQuestion("Jira Project Key / Epic (선택) / Sprint (선택)를 알려주세요")
  [LOCK: 응답 전 jiraCreateIssue 절대 실행 금지]

STEP 3: Jira Story 생성
  각 DRAFT 이슈마다:

  3-1. 상태 전이 (잠금)
    실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/transition.py {branch} {issue} DRAFT PUBLISHING`
    실패: reason 그대로 출력 후 [STOP]

  3-2. Jira Story 생성 (Claude MCP)
    `jiraCreateIssue`:
      - issuetype: Story
      - summary: 파일의 작업 제목
      - description: 파일의 ## 설명 섹션 원문
      - assignee: currentUser()
      - epic: (STEP 2에서 지정된 경우)
      - sprint: (STEP 2에서 지정된 경우)
    실패:
      실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/transition.py {branch} {issue} PUBLISHING DRAFT` (복구)
      reason 출력 후 [STOP]

STEP 4: 리네임 및 상태 전이
  전체 key_map 수집 후 일괄 처리:
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/update_jira_keys.py {task_dir} '{"FE-01":"PROJ-101",...}'`
  실패: reason 그대로 출력 후 [STOP]

  각 이슈마다:
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/transition.py {branch} {jira_key} PUBLISHING PUBLISHED`
  실패: reason 그대로 출력 후 [STOP]

STEP 5: 완료 보고
  아래 형식으로 출력:
  ```
  ✅ Jira 등록 완료

  | 기존 파일 | Jira Key  | 작업 제목        |
  |---------|-----------|----------------|
  | FE-01.md | PROJ-101 | 로그인 폼 UI    |
  | FE-02.md | PROJ-102 | 목록 페이지 구현 |

  저장 경로: .docs/task/{branch}/
  ```

[TERMINATE]
