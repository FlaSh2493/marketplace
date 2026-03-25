---
name: write
description: Writer 서브에이전트 전용. fetch에서 선택된 Jira 이슈를 원본 그대로 로컬 문서로 변환한다. Bash 없이 Read/Write/MCP만 사용한다.
---

# Frontend Task Write

**실행 주체: Writer 에이전트 전용**
내용 요약·해석·추가 절대 금지. Jira 원본을 마크다운으로 변환하여 그대로 저장한다.

## 사용법
`/fe-task-extractor:write {이슈키} [{이슈키}...]`

## 실행 절차

STEP 0: 선택 검증 (Read 도구)
  Read: `.docs/task/{branch}/.state/pending.json`
  파일이 없으면:
    출력: "pending.json이 없습니다. /fe-task-extractor:fetch를 먼저 실행하세요."
    [STOP]
  요청된 이슈가 `selected` 목록에 없으면:
    출력: "{이슈키}는 선택되지 않은 이슈입니다."
    [STOP]

STEP 1: 이슈별 처리 (각 이슈 순서대로)

  1-1. Jira 상세 조회 (Claude MCP)
    - `jiraGetIssue({이슈키})` — summary, description, status, assignee, created
    - `jiraGetIssueComments({이슈키})` — 전체 댓글 (시간순)
    - attachments — 이미지/파일 목록

  1-2. 템플릿 로드 (Read 도구)
    Read: `${CLAUDE_PLUGIN_ROOT}/templates/fe-task-template.md`
    Read: `${CLAUDE_PLUGIN_ROOT}/templates/fe-task-example.md`
    포맷과 필드 순서 파악

  1-3. 마크다운 변환 (Claude 역할 — 유일한 자유 구간)
    - Jira ADF → 마크다운 변환
    - 요약 금지. 원본 구조(리스트, 테이블, 코드블록) 보존
    - 템플릿의 필드 순서와 구조 그대로 적용:
      ```
      # {이슈키}: {summary}

      - jira: {이슈키}
      - 상태: {status}
      - 담당자: {assignee}
      - 생성일: {created}
      - 최근 업데이트: {현재시각}
      - 출처: jira-fetch

      ---

      ## 설명

      {description 전문 — ADF→마크다운, 요약 금지}

      ---

      ## 메타데이터

      - deps: {파싱 결과 또는 없음}
      - api: {파싱 결과 또는 없음}
      - states: {파싱 결과 또는 없음}

      ---
      ```

  1-4. 파일 저장 (Write 도구)
    경로: `.docs/task/{branch}/{이슈키}.md`
    (디렉토리가 없으면 Write 도구가 자동 생성)

  1-5. 댓글 추가 (있는 경우, Edit 도구)
    파일 끝에 추가:
    ```
    ## 댓글

    > **@{작성자}** ({YYYY-MM-DD HH:mm})
    > {댓글 내용 — ADF→마크다운, 요약 금지}
    ```

  1-6. 완료 마커 저장 (Write 도구)
    Write: `.docs/task/{branch}/.state/{이슈키}.pending`
    내용: `{"issue": "{이슈키}", "written_at": "{현재시각}"}`

STEP 2: 완료 알림
  notify_user("문서 작성 완료 [{이슈키 목록}]: Main에서 /fe-task-extractor:publish 실행")

[TERMINATE]
내용 요약·추가·해석 금지. Jira 원본만 마크다운으로 변환한다.
