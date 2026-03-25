---
name: update
description: Writer 서브에이전트 전용. 로컬에서 수정된 마크다운 파일의 내용을 Jira 이슈에 동기화한다. "마크다운 수정했어", "지라에 반영해줘", "티켓 업데이트해" 등을 요청할 때 사용한다.
---

# Frontend Task Update

**실행 주체: Writer 에이전트 전용**
마크다운 → Jira 단방향 동기화. 요약·해석 없이 원문 그대로 반영한다.

## 사용법
`/fe-task-extractor:update`

## 실행 절차

STEP 0: 전제조건 검증
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py update`
  성공: data.branch, data.published 보관
  실패: reason 그대로 출력 후 [STOP]

STEP 1: PUBLISHED 목록 출력
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/list_tasks.py {branch} --state PUBLISHED`
  성공: 번호 테이블로 출력:
  ```
  | 번호 | Jira Key  | 작업 제목        |
  |-----|-----------|----------------|
  |  1  | PROJ-101  | 로그인 폼 UI    |
  |  2  | PROJ-102  | 목록 페이지 구현 |
  ```
  실패: reason 그대로 출력 후 [STOP]

[GATE] STEP 2: 동기화 대상 선택
  실행: AskUserQuestion("동기화할 이슈 번호를 선택하세요 (예: 1,3 / 전체: all)")
  [LOCK: 응답 전 jiraUpdateIssue 절대 실행 금지]

STEP 3: 변경 내용 분석 (Claude 역할)
  선택된 각 파일을 읽어 아래 필드 파악:
  - 작업 제목 (# 헤더에서)
  - ## 설명 섹션 원문 전체
  - deps, api, states 필드

  변경 예정 목록을 표로 출력:
  ```
  | Jira Key  | 변경 필드        |
  |-----------|----------------|
  | PROJ-101  | 설명, deps      |
  ```

[GATE] STEP 4: 동기화 확인
  실행: AskUserQuestion("위 변경사항을 Jira에 반영할까요?")
  [LOCK: 응답 전 jiraUpdateIssue 절대 실행 금지]

  응답 "no": [TERMINATE]

STEP 5: Jira 업데이트
  각 이슈마다:

  5-1. jiraUpdateIssue (Claude MCP):
    - summary: 작업 제목
    - description: ## 설명 섹션 원문 + 메타데이터 (요약 금지)
    실패: reason 출력, 해당 이슈 스킵 후 계속

  5-2. 상태 전이
    실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/transition.py {branch} {jira_key} PUBLISHED SYNCED`
    실패: reason 그대로 출력 (스킵 후 계속)

STEP 6: 완료 보고
  ```
  ✅ Jira 동기화 완료

  | Jira Key  | 작업 제목        | 결과       |
  |-----------|----------------|----------|
  | PROJ-101  | 로그인 폼 UI    | 완료       |
  | PROJ-102  | 목록 페이지 구현 | 완료       |
  ```

[TERMINATE]
댓글·이미지 역동기화 금지. ## 설명 섹션만 Jira에 반영한다.
