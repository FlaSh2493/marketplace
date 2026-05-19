---
name: merge
description: (명시적 커맨드 실행 전용) /autopilot:merge 명령이 입력된 경우에만 이 skill을 활성화한다.
disable-model-invocation: true
---

# 워크트리 머지

> **금지:** git push / force push (사용자 확인 없는 강제 동작 일체)

> **종료 규칙:** 어떤 이유로든 [STOP]할 때는 Write 도구로 `~/Documents/autopilot/{issue_key}/merge.md`에 중단 시점(STEP)과 이유를 기록한다. `issue_key`를 알 수 없는 경우(STEP 2 resolve_worktree 실패)에는 `{워크트리브랜치}`를 경로로 대신 사용한다.

## 사용법
`/autopilot:merge [{워크트리브랜치}]`

| target_branch | 케이스 | 동작 |
|---|---|---|
| main/develop/master 등 | **케이스 1** | origin/base → 워크트리 merge (PR 전 싱크) |
| umbrella 브랜치 | **케이스 2** | 워크트리 rebase 후 워크트리 → umbrella 머지 |

```
STEP 1  커스텀 지침 로드
STEP 2  컨텍스트 확보 + 사전 검증 + 케이스 판별
        ↓
  [케이스 1]              [케이스 2]
  STEP 3  미커밋 커밋     STEP 3  미커밋 커밋
  STEP 4  fetch + merge   STEP 4  umbrella 최신화
  STEP 5  완료            STEP 5  머지 대상 확인 + 충돌 사전 검사
                          STEP 6  [GATE] 머지 승인
                          STEP 7  머지 실행
                          STEP 8  완료
```

---

## STEP 1: 커스텀 지침 로드

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/load_custom_instructions.py merge
```

---

## STEP 2: 컨텍스트 확보 + 사전 검증 + 케이스 판별

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/resolve_worktree.py '{워크트리브랜치}'
```

- `status == "ok"` → `worktree_path`, `worktree_branch`, `target_branch`, `issue_key`, `root_path`, `root_branch` 보관
- `status == "error"` → `reason == "WORKTREE_NOT_FOUND"`: list_worktrees.py 실행 후 AskUserQuestion으로 선택. 그 외: [STOP]

**이후 모든 Bash는 `cd '{worktree_path}' && command` 형태.**

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/init_state_dir.py --issue {data.issue} --clear merge merge-all pr review-fix
python3 ${CLAUDE_PLUGIN_ROOT}/skills/merge/scripts/precheck_merge.py --worktree '{worktree_path}' --target '{target_branch}'
```
- `status == "error"` → reason 출력 후 [STOP]

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/merge/scripts/merge_state.py write --phase init --case 0 --target '{target_branch}' --branch '{worktree_branch}' --issue '{data.issue}'
```

**케이스 판별:** `BASE_BRANCHES = ["develop","main","master","release","staging","stg","stag","dev"]`
- `target_branch`가 목록에 있거나 `"release/"`로 시작 → **케이스 1**, 그 외 → **케이스 2**

---

## [케이스 1] 베이스 → 워크트리 merge

### STEP 3: 미커밋 커밋

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/merge/scripts/auto_commit.py --worktree '{worktree_path}' --scope '{issue or worktree_branch}'
```

- `committed` / `empty` → STEP 4
- `needs_manual` → git status/diff로 파악 (신규 파일은 내용도 Read), 논리 단위별 커밋:
  ```bash
  git add -- {파일들} && git commit -F /tmp/commit_msg.txt
  ```

### STEP 4: fetch + merge

```bash
cd '{worktree_path}' && git fetch origin {target_branch}
cd '{worktree_path}' && git merge origin/{target_branch}
```

- exit 0 → STEP 5
- 충돌 → `Read(${CLAUDE_PLUGIN_ROOT}/skills/merge/reference/CONFLICT_RESOLUTION.md)` 후 절차 수행 (`resolve_root={worktree_path}`, `피처브랜치={target_branch}`, `branch={worktree_branch}`)
  - 해결 완료 → STEP 5 / 실패 → [STOP]

### STEP 5: 완료

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/merge/scripts/merge_state.py clear --issue '{issue}'
```

- Write 도구로 `~/Documents/autopilot/{issue_key}/merge.md`에 아래 내용을 작성한다:
  - target_branch, worktree_branch

싱크 완료 메시지 출력 (target_branch, worktree_branch, issue_key). AskUserQuestion: "다음 단계: 1) `/autopilot:pr` 2) 추가 작업 계속"

[STOP]

---

## [케이스 2] 워크트리 → umbrella 머지

### STEP 3: 미커밋 커밋

케이스 1 STEP 3과 동일.

### STEP 4: umbrella 최신화

```bash
cd {worktree_path} && git fetch origin {target_branch}
```

`origin/{target_branch}` 존재 시:
```bash
cd {worktree_path} && git rebase origin/{target_branch}
```
- 충돌 → `Read(CONFLICT_RESOLUTION.md)` (`resolve_root={worktree_path}`, `피처브랜치={target_branch}`, `branch={worktree_branch}`)
  - 해결 완료: `git rebase --continue` / 실패: [STOP]

### STEP 5: 머지 대상 확인 + 충돌 사전 검사

```bash
cd '{worktree_path}' && \
  MERGE_BASE=$(git merge-base "origin/{target_branch}" HEAD 2>/dev/null || git merge-base "{target_branch}" HEAD 2>/dev/null) && \
  [ -n "$MERGE_BASE" ] && git log "$MERGE_BASE"..HEAD --oneline || echo "MERGE_BASE_NOT_FOUND"
```
- `MERGE_BASE_NOT_FOUND` → [STOP]

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/merge/scripts/merge_worktrees.py '{target_branch}' --dry-run --branch '{worktree_branch}'
```
- `conflict_count > 0` → 충돌 예상 파일 목록 표시

### STEP 6: [GATE] 머지 승인

AskUserQuestion: "{target_branch}에 위 커밋들을 머지할까요? (충돌 {conflict_count}건 예상)"
- yes → STEP 7 / no → [STOP]

### STEP 7: 머지 실행

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/merge/scripts/merge_worktrees.py {target_branch} --branch {worktree_branch}
```

- exit 0 → 워크트리 동기화:
  ```bash
  cd {root_path} && git checkout {root_branch}
  cd {worktree_path} && git merge --ff-only {target_branch}
  ```
  → STEP 8
- exit 2 → `Read(CONFLICT_RESOLUTION.md)` (`resolve_root={root_path}`, `피처브랜치={target_branch}`, `branch={worktree_branch}`)
  - 해결 완료: 워크트리 동기화 → STEP 8 / 실패: [STOP]

### STEP 8: 완료

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/merge/scripts/merge_state.py clear --issue '{issue}'
```

- Write 도구로 `~/Documents/autopilot/{issue_key}/merge.md`에 아래 내용을 작성한다:
  - target_branch, worktree_branch

머지 완료 메시지 출력 (target_branch, worktree_branch, issue_key). AskUserQuestion: "다음 단계: 1) `/autopilot:pr` 2) `/autopilot:end` 3) 추가 작업 계속"

[STOP]
