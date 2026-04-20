---
name: autopilot-pr
description: 현재 브랜치를 push하고 PR을 생성한다. base_branch는 .autopilot에서 자동 감지하며, 없으면 git 커밋 수 비교로 결정한다. assignee는 자신, label은 base_branch + 도메인영역.
---

# PR 생성

**실행 주체: Main Session**

## 사용법
`/autopilot:pr [{브랜치}]`
- 브랜치 생략 시 현재 브랜치 또는 목록에서 선택

## 실행 절차

STEP 0: 컨텍스트 확보 및 초기화

  **컨텍스트 확보:**
  ```bash
  python3 ${CLAUDE_PLUGIN_ROOT}/scripts/resolve_worktree.py '{브랜치}' --infer-base-by-commit-count
  ```
  - `status == "ok"` → `data`의 `worktree_path`, `branch` (`resolved_branch`), `base_branch`, `safe_branch`, `root_path` 보관.
  - `status == "error"`:
    - `reason == "WORKTREE_NOT_FOUND"`: `python3 scripts/list_worktrees.py` 실행 후 목록 제시, AskUserQuestion으로 선택. 선택된 브랜치로 다시 `resolve_worktree.py {branch}` 실행하여 컨텍스트 확보. (워크트리 없이 현재 브랜치에서 실행하는 경우 `worktree_path = git_root`로 간주)
    - 그 외: reason 출력 후 [STOP].

  상태 초기화:
  ```bash
  python3 ${CLAUDE_PLUGIN_ROOT}/scripts/init_state_dir.py --clear pr review-fix
  ```

  **이후 모든 Bash 명령은 `cd '{worktree_path 또는 git_root}' && command` 형태로 실행**

STEP 1: 사전 검증
  1-a. origin/{base_branch} fetch:
    ```bash
    cd '{worktree_path}' && git fetch origin {base_branch} 2>&1
    ```
    실패 시: "origin/{base_branch}을 fetch할 수 없습니다. remote 설정을 확인하세요." 출력 후 [STOP]

  1-b. gh CLI 확인:
    ```bash
    gh auth status 2>&1
    ```
    `command not found`: "gh CLI가 설치되어 있지 않습니다. https://cli.github.com 에서 설치하세요." 출력 후 [STOP]
    그 외 실패: "gh CLI 인증이 필요합니다. `gh auth login`을 실행하세요." 출력 후 [STOP]

  1-c. 기존 PR 확인:
    ```bash
    cd '{worktree_path}' && gh pr list --head '{resolved_branch}' --base {base_branch} --state open --json number,url -q '.[0].url // empty'
    ```
    출력이 비어있지 않으면: "이미 열린 PR이 있습니다: {url}" 출력 후 [STOP]

STEP 2: 미커밋 변경사항 확인
  `cd '{worktree_path}' && git status --porcelain` 실행
  출력이 있으면: "미커밋 변경사항이 있습니다. 먼저 커밋하세요." 출력 후 [STOP]

STEP 3: 커밋 목록 및 변경 파일 확보
  ```bash
  cd '{worktree_path}' && git log origin/{base_branch}..HEAD --oneline | head -51
  ```
  출력이 비어있으면: "{base_branch} 대비 새 커밋이 없습니다." 출력 후 [STOP]
  출력이 51줄이면 (50개 초과): "커밋이 50개를 초과합니다. 브랜치를 확인하세요 ({base_branch}과 공통 조상이 없을 수 있습니다)." 출력 후 [STOP]
  커밋 목록 보관.

  ```bash
  cd '{worktree_path}' && git diff --name-only origin/{base_branch}...HEAD
  ```
  주의: three-dot(`...`)을 사용한다 — 분기점 이후 현재 브랜치에서만 변경된 파일을 정확히 추출하기 위함.
  변경 파일 목록 보관.
  변경 파일이 없으면(커밋은 있지만 revert 등으로 diff가 비어있는 경우): "커밋은 있지만 {base_branch} 대비 변경된 파일이 없습니다. 브랜치 상태를 확인하세요." 출력 후 [STOP]

STEP 4: 도메인 라벨 추론
  ```bash
  python3 ${CLAUDE_PLUGIN_ROOT}/scripts/infer_labels.py '{worktree_path}' '{owner_repo}'
  ```
  결과: `data.labels[]` — {base_branch} + 도메인 라벨 (존재하는 것만)

STEP 5: 본인 계정 확보
  ```bash
  gh api user -q .login
  ```
  실패 시: "GitHub 사용자 정보를 가져올 수 없습니다." 출력 후 [STOP]
  → login 변수에 보관 (이후 재사용)

STEP 6: PR 제목 및 본문 생성
  커밋 로그와 diff를 분석하여 PR 제목과 본문을 작성한다.

  **제목 생성 규칙:**
  - 70자 이내, 단일 행
  - 형식: `{type}({scope}): {요약}` (conventional commit 스타일)
    - type: feat / fix / refactor / chore / docs / style / test / perf
    - scope: 도메인 라벨이 있으면 사용, 없으면 변경의 핵심 모듈/영역명
  - 커밋이 1개면 해당 커밋 메시지의 subject가 이미 conventional commit 형식이면 그대로 사용, 아니면 conventional commit 형식으로 변환
  - 커밋이 여러 개면 **가장 메이저한 주제(가장 중요한 변경사항)를 중심으로** 상위 요약을 작성 (개별 커밋 나열 금지)
    - 메이저한 주제: 가장 많은 파일이 변경된 영역, 또는 가장 영향력 큰 기능/수정
  - 브랜치명에 이슈키가 있으면 제목 끝에 포함: `feat(data-center): 리포트 필터 추가 (DC-123)`

  **본문 생성 규칙:**
  ```
  ## Summary
  - 주요 변경사항 bullet points (커밋 로그 + diff 기반, 3~5개)

  ## Changes
  - 커밋 목록 (해시 + 메시지)
  ```

  **제목과 본문은 Write 도구로 `/tmp/pr_{safe_branch}_title.txt`, `/tmp/pr_{safe_branch}_body.txt`에 각각 저장한다** (shell escaping 방지 + 동시 실행 충돌 방지)

[GATE] STEP 7: PR 내용 확인
  사용자에게 PR 제목, 본문, 라벨을 보여주고 확인을 요청한다.
  AskUserQuestion("위 내용으로 PR을 생성할까요? (yes / 수정사항 / no)")
  [LOCK: 응답 전 push/PR 생성 금지]

  응답 "yes": STEP 8 진행
  응답 "no": "PR 생성 취소." [TERMINATE]
  그 외 모든 응답(수정 요청, 질문 등): 요청에 따라 제목/본문/라벨을 수정하고 tmp 파일을 업데이트한 뒤 STEP 7을 다시 실행

STEP 8: Push
  ```bash
  cd '{worktree_path}' && git push -u origin HEAD
  ```
  (`HEAD`를 사용하여 브랜치명 특수문자 이슈를 회피. `-u`가 upstream을 현재 브랜치명으로 자동 설정)
  실패 시: 오류 메시지 출력 후 [STOP]

STEP 9: PR 생성
  labels 옵션: 각 라벨마다 `--label '{라벨}'`을 반복한다. 예: `--label '{base_branch}' --label 'data-center'`. 라벨이 없으면 `--label` 자체를 생략한다.
  주의: `--label 'a,b'`는 쉼표를 포함한 단일 라벨로 해석되므로 **반드시 개별 `--label`로 분리**한다.

  ```bash
  cd '{worktree_path}' && TITLE=$(cat '/tmp/pr_{safe_branch}_title.txt') && \
    gh pr create \
      --base {base_branch} \
      --assignee '{login}' \
      {각 라벨별 --label '{라벨}'} \
      --title "$TITLE" \
      --body-file '/tmp/pr_{safe_branch}_body.txt'
  ```
  `--body-file`로 본문을 파일에서 직접 읽는다 (gh 2.21.0+ 필요).
  `--body-file` 미지원 에러(`unknown flag`) 발생 시: `--body-file`을 `--body "$(cat '/tmp/pr_{safe_branch}_body.txt')"` 로 대체하여 재실행한다.
  성공 시: stdout 출력(PR URL)을 pr_url 변수에 보관 → STEP 10 진행
  실패 시: "PR 생성에 실패했습니다. push는 완료된 상태이므로 수동으로 PR을 생성하세요:\n`gh pr create --base {base_branch} --assignee '{login}'`" 출력 후 [STOP]

STEP 10: 완료 출력
  ```
  ┌───────────────────────────────────────────────┐
  │ PR 생성 완료                                   │
  │ URL: [{pr_url}]({pr_url})                      │
  │ Base: {base_branch} ← {resolved_branch}        │
  │ Labels: {labels 또는 "없음"}                    │
  └───────────────────────────────────────────────┘
  ```

  AskUserQuestion으로 다음 선택지 제시:
  ```
  PR이 생성되었습니다. 다음 중 선택하세요:
  1. `/autopilot:review-fix` — CodeRabbit 리뷰 반영
  2. `/autopilot:cleanup` — 머지 완료된 워크트리 정리
  3. `/autopilot:status` — 활성 워크트리 상태 조회
  4. 추가 작업 계속
  ```

  완료 마커
    Write: `{state_dir}/pr` (빈 파일)

[TERMINATE]
