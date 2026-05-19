---
name: pr
description: (명시적 커맨드 실행 전용) /autopilot:pr 명령이 입력된 경우에만 이 skill을 활성화한다.
disable-model-invocation: true
---

# PR 생성

> **종료 규칙:** issue 확보 후 어떤 이유로든 [STOP]할 때는 Write 도구로 `~/Documents/autopilot/{issue}/pr.md`에 중단 시점(STEP)과 이유를 기록한다. issue 미확보(STEP 2 resolve 실패) 시 `{브랜치}` fallback. STEP 8 성공은 pr_state.py가 자동 처리하므로 제외.

`/autopilot:pr [{브랜치}]`

```
STEP 1  커스텀 지침 로드
STEP 2  컨텍스트 확보 및 초기화
STEP 3  사전 검증
STEP 4  라벨 추론 + 계정 확보
STEP 5  PR 데이터 수집
STEP 6  PR 제목 · 본문 생성
STEP 7  [GATE] 최종 확인
STEP 8  Push → PR 생성 → 완료
```

---

## STEP 1: 커스텀 지침 로드

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/load_custom_instructions.py pr
```

로드된 지침과 [reference/pr-conventions.md](reference/pr-conventions.md) 규약을 준수한다.

---

## STEP 2: 컨텍스트 확보

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/resolve_worktree.py '{브랜치}' --infer-base-by-commit-count
```

- `status == "ok"` → `worktree_path`, `resolved_branch`, `base_branch`, `safe_branch`, `root_path`, `issue` 보관
- `status == "error"`:
  - `WORKTREE_NOT_FOUND`: list_worktrees.py 실행 → AskUserQuestion으로 선택 → 재실행
  - 그 외: [STOP]

**모드:** `worktree_path ≠ root_path` → 워크트리 모드, 동일 → 직접 모드

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/init_state_dir.py --issue {data.issue} --clear pr review-fix
python3 ${CLAUDE_PLUGIN_ROOT}/skills/pr/scripts/pr_state.py write --issue {data.issue} --phase init --branch {resolved_branch}
```

---

## STEP 3: 사전 검증

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/pr/scripts/precheck_pr.py --worktree '{worktree_path}' --base {base_branch} --branch '{resolved_branch}'
```

- `status == "error"` → [STOP]
- `over_limit == true` → AskUserQuestion: "커밋 {commit_count}개로 50개 초과. 베이스({base_branch}) 확인 후 계속할까요? (yes/no)" → no이면 [STOP]

---

## STEP 4: 라벨 추론 + 계정 확보

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/pr/scripts/infer_labels.py '{worktree_path}' {base_branch}
gh api user -q .login
```

→ `labels[]`, `login` 보관. login 실패 시 [STOP]

---

## STEP 5: PR 데이터 수집

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/pr/scripts/prepare_pr_content.py '{worktree_path}' {base_branch} '{resolved_branch}'
```

→ `commits`, `stats`, `major_areas`, `suggested_type`, `suggested_scope`, `issue_keys` 보관

---

## STEP 6: PR 제목 · 본문 생성

`templates/pr-title.md` · `templates/pr-body.md`를 사용해 STEP 5 데이터 기반으로 작성.

**이슈키 규칙:**
- `{issue_keys}`: `, `로 join (예: `PROJ-123, PROJ-456`)
- `{issue_keys_list}`: 한 줄씩 나열
- 비어있으면 제목의 `[{issue_keys}]`와 본문의 `## Related Issues` 생략

**저장:** `/tmp/pr_{safe_branch}_title.txt`, `/tmp/pr_{safe_branch}_body.txt`

---

## STEP 7: [GATE] 최종 확인

사용자에게 제목·본문·라벨 표시.

AskUserQuestion: "위 내용으로 PR을 생성할까요? (yes / 수정 / no)"
**[응답 전 push·PR 생성 금지]**

- yes → STEP 8
- no → [STOP]
- 수정 → "어떤 부분을 수정할까요?" 텍스트로 확인 → 반영 후 STEP 7 재실행

---

## STEP 8: Push → PR 생성 → 완료

```bash
cd '{worktree_path}' && git push -u origin HEAD
python3 ${CLAUDE_PLUGIN_ROOT}/skills/pr/scripts/pr_state.py write --issue {data.issue} --phase push_done --push-done true
```
실패 시 [STOP]

```bash
cd '{worktree_path}' && TITLE=$(cat '/tmp/pr_{safe_branch}_title.txt') && \
  gh pr create \
    --base {base_branch} \
    --assignee '{login}' \
    {각 라벨별 --label '{라벨}'} \
    --title "$TITLE" \
    --body-file '/tmp/pr_{safe_branch}_body.txt'
```

- 성공: `pr_url` 보관
  ```bash
  python3 ${CLAUDE_PLUGIN_ROOT}/skills/pr/scripts/pr_state.py write --issue {data.issue} --phase completed \
    --url '{pr_url}' --base {base_branch} --labels '{labels_comma_separated}'
  ```
  → 완료 시 `~/Documents/autopilot/{data.issue}/pr.md` 자동 생성
- 실패:
  - stderr에 "already exists" 포함 시 → `gh pr list --head '{resolved_branch}' --state open --json url -q '.[0].url'` 로 기존 PR URL 조회 → `pr_url` 보관 후 성공 경로로 이동
  - 그 외: 수동 생성 명령어 안내 후 [STOP]

**완료:** PR URL 출력 (`{pr_url}`, base: {base_branch} ← {resolved_branch}, labels: {labels}).

AskUserQuestion: "다음 단계: 1) `/autopilot:review-fix` 2) `/autopilot:end` 3) 추가 작업 계속"

[STOP]
