---
name: write
description: Writer 서브에이전트 전용. fetch에서 선택된 Jira 이슈를 원본 그대로 로컬 문서로 변환한다. 직접 호출하거나 fetch가 런칭한다.
---

# Frontend Task Write

**실행 주체: Writer 에이전트 전용**
내용 요약·해석·추가 절대 금지. Jira 원본을 마크다운으로 변환하여 그대로 저장한다.

## 사용법
`/fe-task-extractor:write {이슈키} [{이슈키}...]`

## 실행 절차

STEP 0: 전제조건 검증
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py write {이슈키들}`
  성공: data.branch, data.task_dir, data.issues 보관
  실패: reason 그대로 출력 후 [STOP] — pending.json에 없는 이슈는 처리 불가

STEP 1: 이슈별 처리 (각 이슈 순서대로)

  1-1. Jira 상세 조회 (Claude MCP)
    - `jiraGetIssue({이슈키})` — summary, description, status, assignee, created
    - `jiraGetIssueComments({이슈키})` — 전체 댓글 (시간순)
    - attachments 필드 — 이미지/파일 목록

  1-2. 설명 변환 (Claude 역할 — 유일한 자유 구간)
    - Jira ADF → 마크다운 변환
    - 요약 금지. 원본 구조(리스트, 테이블, 코드블록) 보존
    - 변환된 내용을 stdin으로 전달하여 파일 생성:
    ```bash
    echo "{변환된 설명}" | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/create_task_file.py \
      "{branch}" "{이슈키}" "{summary}" \
      --status "{status}" \
      --assignee "{assignee}" \
      --source "jira-fetch" \
      --created-at "{created}" \
      --deps "{deps 파싱 결과 또는 없음}" \
      --api "{api 파싱 결과 또는 없음}" \
      --states "{states 파싱 결과 또는 없음}"
    ```
    실패: reason 그대로 출력 후 [STOP]

  1-3. 포맷 검증
    실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate_template.py {file_path}`
    실패: reason 그대로 출력 후 [STOP]

  1-4. 댓글 추가 (있는 경우)
    파일 끝에 아래 형식으로 시간순 추가:
    ```
    ---

    ## 댓글

    > **@{작성자}** ({YYYY-MM-DD HH:mm})
    > {댓글 내용 — ADF→마크다운 변환, 요약 금지}
    ```

  1-5. 첨부파일 처리 (있는 경우)
    이미지: assets/ 폴더에 저장, 파일에 `![{설명}](./assets/{이슈키}-{파일명})` 추가
    기타: 다운로드 URL 링크로 기재

  1-6. 상태 전이
    실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/transition.py {branch} {이슈키} NONE DRAFT`
    실패: reason 그대로 출력 후 [STOP]

STEP 2: 완료 보고
  처리된 이슈 목록 출력 후:
  notify_user("문서 작성 완료 [{이슈키 목록}]: /fe-task-extractor:publish 실행 가능")

[TERMINATE]
내용 요약·추가·해석 금지. Jira 원본만 마크다운으로 변환한다.
