---
name: pr
description: (명시적 커맨드 실행 전용) /autopilot:pr 명령이 입력된 경우에만 이 skill을 활성화한다.
disable-model-invocation: true
---

# PR 생성

**실행 주체: Main Session**

## 사용법
`/autopilot:pr [{브랜치}]`
- 브랜치 생략 시 현재 브랜치 또는 목록에서 선택

---

## STEP 0.5: 프로젝트 커스텀 지침 참조

[_shared/CUSTOM_INSTRUCTIONS.md](../_shared/CUSTOM_INSTRUCTIONS.md) 및 [reference/pr-conventions.md](reference/pr-conventions.md)에 따라 다음 명령을 실행하여 프로젝트 지침을 확인한다.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/load_custom_instructions.py pr
```

- **필수 참조**: 로드된 지침과 규약을 **반드시 준수**한다.

---

## STEP 0: 컨텍스트 확보 및 초기화

  **컨텍스트 확보:**
  ```bash
  python3 ${CLAUDE_PLUGIN_ROOT}/scripts/resolve_worktree.py '{브랜치}' --infer-base-by-commit-count
  ```
  - `status == "ok"` → `data`의 `worktree_path`, `branch` (`resolved_branch`), `base_branch`, `safe_branch`, `root_path`, `issue` 보관.
  - `status == "error"`:
    - `reason == "WORKTREE_NOT_FOUND"`: `python3 scripts/list_worktrees.py` 실행 후 목록 제시, AskUserQuestion으로 선택. 선택된 브랜치로 다시 `resolve_worktree.py {branch}` 실행하여 컨텍스트 확보.
    - 그 외: reason 출력 후 [STOP].

  **모드 결정:**
  - **워크트리 모드**: `worktree_path`가 `root_path`와 다를 때.
  - **직접 모드**: `worktree_path`가 없거나 `root_path`와 같을 때. (`worktree_path = root_path`로 간주)

  **상태 초기화:**
  ```bash
  python3 ${CLAUDE_PLUGIN_ROOT}/scripts/init_state_dir.py --issue {data.issue} --clear pr review-fix && \
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/pr/scripts/pr_state.py write --issue {data.issue} --phase init --branch {resolved_branch}
  ```

  **이후 모든 Bash 명령은 `cd '{worktree_path}' && command` 형태로 실행**

---

## STEP 1: 통합 사전 검증

  ```bash
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/pr/scripts/precheck_pr.py --worktree '{worktree_path}' --base {base_branch} --branch '{resolved_branch}'
  ```
  - `status == "error"`: 에러 메시지 출력 후 [STOP].
  - `status == "ok"`: `data.commit_count`, `data.over_limit` 확인.

  **[GATE] 커밋 개수 확인:**
  - `over_limit == true`: "커밋이 {commit_count}개로 50개를 초과합니다. 베이스 브랜치({base_branch})가 올바른지 확인하세요. 계속 진행할까요? (yes/no)"
    - "no": [TERMINATE]
    - "yes": STEP 2 진행

---

## STEP 2: 도메인 라벨 추론

  [reference/label-rules.md](reference/label-rules.md)를 참고하여 라벨을 추론한다.
  ```bash
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/pr/scripts/infer_labels.py '{worktree_path}' {base_branch}
  ```
  - 결과: `data.labels[]` — 실제 리포지토리에 존재하는 라벨만 반환됨.

---

## STEP 3: 본인 계정 확보

  ```bash
  gh api user -q .login
  ```
  실패 시: "GitHub 사용자 정보를 가져올 수 없습니다." 출력 후 [STOP]
  → `login` 변수에 보관.

---

## STEP 4: PR 컨텐츠 분석 데이터 확보 (토큰 최적화)

  전체 diff를 읽는 대신, 요약된 통계와 커밋 로그만 확보하여 토큰 소비를 최소화한다.
  ```bash
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/pr/scripts/prepare_pr_content.py '{worktree_path}' {base_branch} '{resolved_branch}'
  ```
  - 반환된 JSON(`commits`, `stats`, `major_areas`, `suggested_type`, `suggested_scope`, `issue_key`)을 확보한다.

---

## STEP 5: PR 제목 및 본문 생성

  [templates/pr-title.md](templates/pr-title.md) 및 [templates/pr-body.md](templates/pr-body.md)를 사용하여 제목과 본문을 작성한다.
  - STEP 4의 데이터를 기반으로 [reference/pr-conventions.md](reference/pr-conventions.md) 규약을 준수한다.

  **저장**: `/tmp/pr_{safe_branch}_title.txt`, `/tmp/pr_{safe_branch}_body.txt`에 저장.

---

## [GATE] STEP 6: PR 내용 최종 확인

  사용자에게 제목, 본문, 라벨을 보여주고 확인을 요청한다.
  AskUserQuestion("위 내용으로 PR을 생성할까요? (yes / 수정사항 / no)")
  [LOCK: 응답 전 push/PR 생성 금지]

  - "yes": STEP 7 진행
  - "no": "PR 생성 취소." [TERMINATE]
  - 그 외: 수정 요청 반영 후 STEP 6 재실행.

---

## STEP 7: Push 및 상태 기록

  ```bash
  cd '{worktree_path}' && git push -u origin HEAD && \
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/pr/scripts/pr_state.py write --issue {data.issue} --phase push_done --push-done true
  ```
  실패 시: 오류 메시지 출력 후 [STOP].

---

## STEP 8: PR 생성

  ```bash
  cd '{worktree_path}' && TITLE=$(cat '/tmp/pr_{safe_branch}_title.txt') && \
    gh pr create \
      --base {base_branch} \
      --assignee '{login}' \
      {각 라벨별 --label '{라벨}'} \
      --title "$TITLE" \
      --body-file '/tmp/pr_{safe_branch}_body.txt'
  ```
  - 성공 시: `pr_url` 보관 및 상태 업데이트:
    ```bash
    python3 ${CLAUDE_PLUGIN_ROOT}/skills/pr/scripts/pr_state.py write --issue {data.issue} --phase completed
    ```
  - 실패 시: 수동 생성 명령어 안내 후 [STOP].

---

## STEP 9: 완료 출력 및 후속 작업

  ```
  ┌───────────────────────────────────────────────┐
  │ PR 생성 완료                                   │
  │ URL: [{pr_url}]({pr_url})                      │
  │ Base: {base_branch} ← {resolved_branch}        │
  │ Labels: {labels}                               │
  └───────────────────────────────────────────────┘
  ```

  [reference/after-pr-menu.md](reference/after-pr-menu.md)에 따라 다음 선택지를 제시한다.

[TERMINATE]
