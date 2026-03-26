---
name: update
description: Writer 서브에이전트 전용. 로컬에서 수정된 마크다운 파일의 내용을 Jira 이슈에 동기화한다.
---

# Frontend Task Update

**실행 주체: Writer 에이전트 전용**
마크다운 → Jira 단방향 동기화. 요약·해석 없이 원문 그대로 반영한다.

## 사용법
`/fe-task-extractor:update`

## 실행 절차

STEP 0: 대상 파일 탐색 (Glob 도구)
  Glob: `.docs/task/{branch}/.state/*.published`
  결과가 없으면:
    출력: "PUBLISHED 상태인 이슈가 없습니다. publish를 먼저 실행하세요."
    [STOP]
  이슈 키 목록 추출 (파일명에서 `.published` 제거)

STEP 1: 목록 출력
  번호 테이블로 출력:
  ```
  | 번호 | Jira Key  | 작업 제목        |
  |-----|-----------|----------------|
  |  1  | PROJ-101  | 로그인 폼 UI    |
  |  2  | PROJ-102  | 목록 페이지 구현 |
  ```
  (각 파일 Read하여 # 헤더에서 제목 파악)

[GATE] STEP 2: 동기화 대상 선택
  AskUserQuestion("동기화할 이슈 번호를 선택하세요 (예: 1,3 / 전체: all)")
  [LOCK: 응답 전 jiraUpdateIssue 절대 실행 금지]

STEP 3: 변경 내용 분석 (Read 도구)
  선택된 각 파일 Read:
  - 작업 제목 (# 헤더에서)
  - ## 설명 섹션 원문 전체
  - ## 추가 요구사항 섹션 (있는 경우)
  - deps, api, states 필드

  변경 예정 목록 출력:
  ```
  | Jira Key  | 동기화 내용    |
  |-----------|-------------|
  | PROJ-101  | 설명, deps   |
  ```

[GATE] STEP 4: 동기화 확인
  AskUserQuestion("위 내용을 Jira에 반영할까요?")
  [LOCK: 응답 전 jiraUpdateIssue 절대 실행 금지]
  응답 "no": [TERMINATE]

STEP 5: Jira 업데이트 (MCP)
  각 이슈마다:
  jiraUpdateIssue:
    - summary: 작업 제목
    - description: ## 설명 원문 + ## 추가 요구사항 (있는 경우) + 메타데이터 (요약 금지)
  실패: 해당 이슈 오류 출력 후 다음 이슈 계속

STEP 6: 완료 알림
  notify_user("Jira 동기화 완료 [{이슈키 목록}]")

[TERMINATE]
댓글·이미지 역동기화 금지. ## 설명 + ## 추가 요구사항 섹션만 Jira에 반영한다.
