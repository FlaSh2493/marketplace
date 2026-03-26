---
name: write
description: Writer 서브에이전트 전용. fetch에서 선택된 Jira 이슈를 원본 그대로 로컬 문서로 변환한다. 파일 저장은 반드시 create_task_file.py 스크립트로 한다.
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

  1-3. ADF → 마크다운 변환 (Claude 역할 — 유일한 자유 구간)
    - Jira ADF → 마크다운 변환
    - 요약 금지. 원본 구조(리스트, 테이블, 코드블록) 보존
    - description, deps, api, states 값 추출

  1-4. 파일 저장 (Bash — create_task_file.py 필수)
    ```
    echo "{description 마크다운}" | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/create_task_file.py \
      "{branch}" "{이슈키}" "{summary}" \
      --status "{status}" --assignee "{assignee}" \
      --source jira-fetch --created-at "{created}" \
      --deps "{deps}" --api "{api}" --states "{states}"
    ```
    성공: data.file_path 확인
    실패: reason 그대로 출력 후 [STOP]

  1-5. 댓글 추가 (Edit 도구)
    1-1에서 조회한 댓글 목록을 확인한다.
    댓글이 1개 이상이면 파일 끝에 반드시 추가한다 (작성자 무관, 전체 포함):
    ```
    ## 댓글

    > **@{작성자}** ({YYYY-MM-DD HH:mm})
    > {댓글 내용 — ADF→마크다운, 요약 금지}

    > **@{작성자2}** ({YYYY-MM-DD HH:mm})
    > {댓글 내용}
    ```
    댓글이 0개이면 이 단계를 스킵한다.

  1-6. 완료 마커 저장 (Write 도구)
    Jira에서 불러온 이슈는 이미 Jira에 존재하므로 PUBLISHED 상태로 저장:
    Write: `.docs/task/{branch}/.state/{이슈키}.published`
    내용: `{"issue": "{이슈키}", "written_at": "{현재시각}"}`

STEP 2: 완료 알림
  notify_user("문서 작성 완료 [{이슈키 목록}]: /worktree-flow:create로 워크트리 생성 가능")

[TERMINATE]
내용 요약·추가·해석 금지. Jira 원본만 마크다운으로 변환한다.
