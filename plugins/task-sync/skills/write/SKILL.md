---
name: task-sync-write
description: Writer 서브에이전트 전용. fetch에서 선택된 Jira 이슈를 원본 그대로 로컬 문서로 변환한다.
---

# Frontend Task Write

**실행 주체: Writer 에이전트 전용**
내용 요약·해석·추가 절대 금지. Jira 원본을 마크다운으로 변환하여 그대로 저장한다.

## 사용법
`/task-sync:write --branch {branch} {이슈키} [{이슈키}...]`

## 실행 절차

STEP 0: 브랜치 및 선택 검증
  인수에서 `--branch {값}` 파싱 → branch 변수로 보관
  없으면: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py fetch` 실행 → data.branch 사용

  Read: `.docs/task/{branch}/.state/pending.json`
  파일이 없으면:
    출력: "pending.json이 없습니다. /task-sync:fetch를 먼저 실행하세요."
    [STOP]
  요청된 이슈가 `selected` 목록에 없으면:
    출력: "{이슈키}는 선택되지 않은 이슈입니다."
    [STOP]

STEP 1: 이슈별 처리 (각 이슈 순서대로)

  1-1. Jira 상세 조회 (Bash 스크립트)
    실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/jira_fetch.py {이슈키} --out-dir {state_dir}`
    성공: 결과가 JSON으로 `{state_dir}/{이슈키}_raw.json` 저장
    실패: reason 출력 후 [STOP]

    Read: `{state_dir}/{이슈키}_raw.json`
    파일에서 다음 필드 추출:
      - summary: 이슈 제목
      - description: ADF 형식 설명 (또는 null)
      - status: {"name": "..."}
      - assignee: {"displayName": "..."}
      - created: ISO 8601 형식
      - fields.attachment: [{ filename, mimeType, content (다운로드 URL), size }] (없으면 [])
      - fields.comment.comments: [{ author, body (ADF), created, ... }] (없으면 [])

  1-2. 첨부파일 다운로드 (Bash 도구)
    attachment 목록을 순서대로 처리한다.
    이미지 MIME: image/png, image/jpeg, image/gif, image/svg+xml, image/webp
    비이미지 MIME: 그 외 (pdf, doc, xlsx 등)

    assets 디렉토리 생성:
      경로: `.docs/task/{branch}/{이슈키}/assets/`

    각 attachment에 대해 순번(1부터)을 부여하고 다운로드:
      저장명: `{이슈키}-{순번}.{확장자}` (예: SPT-3771-1.png)
      저장 경로: `.docs/task/{branch}/{이슈키}/assets/{저장명}`
      다운로드 명령 (Bash):
        `curl -sL -u "$JIRA_EMAIL:$JIRA_TOKEN" -o "{저장 경로}" "{content URL}"`
      50MB 초과(size > 52428800) 또는 다운로드 실패 시:
        로그: "⚠ {이슈키} {파일명} 다운로드 실패 — 스킵"
        해당 파일만 건너뛰고 계속 진행
      성공한 파일은 이미지/비이미지로 분류하여 목록 유지

    attachment ID → 로컬 파일명 매핑 테이블 유지:
      `{ "{attachment.id}": "{저장명}" }` (예: { "10001": "SPT-3771-1.png" })
      1-4 단계에서 description 내 mediaSingle 노드 위치 복원에 사용한다.

  1-3. 템플릿 로드 (Read 도구)
    Read: `${CLAUDE_PLUGIN_ROOT}/templates/fe-task-template.md`
    Read: `${CLAUDE_PLUGIN_ROOT}/templates/fe-task-example.md`
    포맷과 필드 순서 파악

  1-4. ADF → 마크다운 변환 (Claude 역할 — 유일한 자유 구간)
    - Jira ADF → 마크다운 변환
    - 요약 금지. 원본 구조(리스트, 테이블, 코드블록) 보존
    - description, deps, api, states 값 추출
    - description ADF 내 mediaSingle 노드를 만나면:
        1-2에서 만든 매핑 테이블로 attachment ID → 로컬 파일명 조회
        해당 위치에 `![{파일명}](./assets/{저장명})` 인라인 삽입 (본문 흐름 유지)
        인라인 삽입된 이미지는 "description 참조 이미지" 목록에 추가

  1-5. 파일 채우기 (Edit 도구)
    fetch가 이미 생성한 파일에 내용을 채운다:
    경로: `.docs/task/{branch}/{이슈키}/{이슈키}.md`
    파일이 없으면: "파일이 없습니다. /task-sync:fetch를 먼저 실행하세요." [STOP]

    파일 전체를 아래 형식으로 교체 (순서·필드명 변경 금지):
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

    ## 첨부 이미지     ← description에서 참조되지 않은 이미지가 1개 이상일 때만 포함. 없으면 이 섹션 전체 생략.

    ![{파일명}](./assets/{이슈키}-1.{확장자})
    ![{파일명}](./assets/{이슈키}-2.{확장자})

    ---

    ## 첨부 파일      ← 다운로드 성공한 비이미지 파일이 1개 이상일 때만 포함. 없으면 이 섹션 전체 생략.

    - [{파일명}](./assets/{이슈키}-{순번}.{확장자})

    ---
    ```

  1-6. 댓글 추가 (Edit 도구)
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

  1-7. 완료 마커 저장 (Write 도구)
    Jira에서 불러온 이슈는 이미 Jira에 존재하므로 PUBLISHED 상태로 저장:
    Write: `.docs/task/{branch}/.state/{이슈키}.published`
    내용: `{"issue": "{이슈키}", "written_at": "{현재시각}"}`

STEP 2: 완료 알림
  notify_user("문서 작성 완료 [{이슈키 목록}]: /autopilot:create로 워크트리 생성 가능")

[TERMINATE]
내용 요약·추가·해석 금지. Jira 원본만 마크다운으로 변환한다.
