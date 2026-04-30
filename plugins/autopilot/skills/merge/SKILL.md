---
name: merge
description: (명시적 커맨드 실행 전용) /autopilot:merge 명령이 입력된 경우에만 이 skill을 활성화한다.
disable-model-invocation: true
---

# Worktree Merge

git push 금지.

## 사용법
`/autopilot:merge [{워크트리브랜치}]` — 워크트리명 지정 또는 목록에서 선택

| target_branch | 케이스 | 동작 |
|---------------|--------|------|
| main/develop/master 등 | **케이스 1** | origin/base → 워크트리 merge (PR 전 싱크) |
| umbrella 브랜치 | **케이스 2** | 워크트리 rebase 후 워크트리 → umbrella 머지 |

```
STEP 1  커스텀 지침 로드
STEP 2  컨텍스트 확보 + 사전 검증 + 케이스 판별
        ↓
  [케이스 1]              [케이스 2]
  STEP 3  미커밋 커밋     STEP 3  미커밋 커밋
  STEP 4  fetch + merge   STEP 4  umbrella 최신화
  STEP 5  완료 출력       STEP 5  머지 대상 확인 + 충돌 사전 검사
                          STEP 6  [GATE] 머지 승인
                          STEP 7  머지 실행
                          STEP 8  완료 출력
```

---

## STEP 1: 커스텀 지침 로드

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/load_custom_instructions.py merge
```

로드된 지침을 **반드시 준수**한다. 표준 절차를 왜곡하지 않는다.

---

## STEP 2: 컨텍스트 확보 + 사전 검증 + 케이스 판별

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/resolve_worktree.py '{워크트리브랜치}'
```

- `status == "ok"` → `worktree_path`, `worktree_branch`, `target_branch`, `issue_key`, `root_path`, `root_branch` 보관
- `status == "error"`:
  - `reason == "WORKTREE_NOT_FOUND"`: `list_worktrees.py` 실행 후 목록 제시, AskUserQuestion으로 선택. 선택된 경로로 재실행.
  - 그 외: reason 출력 후 [STOP]

**이후 모든 Bash 명령은 `cd '{worktree_path}' && command` 형태로 실행한다.**

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/init_state_dir.py --issue {data.issue} --clear merge merge-all pr review-fix
```

**사전 검증:**
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/merge/scripts/precheck_merge.py --worktree '{worktree_path}' --target '{target_branch}'
```
- `status == "error"`: reason 출력 후 [STOP]
- `status == "ok"`: 계속

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/merge/scripts/merge_state.py write --phase init --case 0 --target '{target_branch}' --branch '{worktree_branch}' --issue '{data.issue}'
```

**케이스 판별:**
BASE_BRANCHES = `["develop", "main", "master", "release", "staging", "stg", "stag", "dev"]`
- `target_branch`가 위 목록에 포함되거나 `"release/"`로 시작하면 → **케이스 1**
- 그 외 → **케이스 2**

---

## [케이스 1] 베이스 → 워크트리 merge (PR 전 싱크)

### STEP 3: 미커밋 변경사항 커밋

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/merge/scripts/merge_state.py write --phase step_1_commit --case 1 --target '{target_branch}' --branch '{worktree_branch}' --issue '{issue}'
```

**자동 커밋 시도:**
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/merge/scripts/auto_commit.py --worktree '{worktree_path}' --scope '{issue or worktree_branch}'
```

- `status == "committed"` / `"empty"` → STEP 4로 이동
- `status == "needs_manual"` → 수동 커밋 절차 진행:
  1. 전체 변경사항 파악:
     ```bash
     git status --porcelain
     git diff HEAD
     git ls-files --others --exclude-standard
     ```
     신규 파일은 내용도 Read하여 분석에 포함
  2. 변경사항을 논리적 단위로 그룹핑
  3. 각 그룹별로 커밋 (`subject: {type}({scope}): {단위 요약}`, body 포함):
     ```bash
     # Write("/tmp/commit_msg.txt", ...) 후
     git add -- {shlex.quote(파일1)} ... && git commit -F /tmp/commit_msg.txt
     ```

### STEP 4: fetch + merge

```bash
cd '{worktree_path}' && git fetch origin {target_branch}
```
실패 시: 에러 출력 후 [STOP]

```bash
cd '{worktree_path}' && git merge origin/{target_branch}
```

- 성공 (exit 0) → STEP 5로 이동
- 충돌 (exit 1) → Read(`${CLAUDE_PLUGIN_ROOT}/skills/merge/reference/CONFLICT_RESOLUTION.md`) 후 절차를 따른다.
  - 변수: `resolve_root={worktree_path}`, `피처브랜치={target_branch}`, `branch={worktree_branch}`
  - 해결 완료: `git merge --continue`
  - 해결 실패: [STOP]

### STEP 5: 완료 출력

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/merge/scripts/merge_state.py clear --issue '{issue}'
```

```
┌─────────────────────────────────────────────┐
│ 싱크 완료 (merge)                            │
│ 반영된 브랜치: {target_branch}               │
│ 워크트리: {worktree_branch}                  │
│ 이슈: {issues_str}                           │
└─────────────────────────────────────────────┘
```

AskUserQuestion으로 다음 선택지 제시:
```
싱크가 완료되었습니다. 다음 중 선택하세요:
1. `/autopilot:pr` — PR 생성
2. 추가 작업 계속
```

[STOP]

---

## [케이스 2] 워크트리 → umbrella 머지 (커밋 통합)

워크트리의 커밋들을 umbrella(피처) 브랜치에 통합한다.

### STEP 3: 미커밋 변경사항 커밋

케이스 1 STEP 3과 동일 프로세스

### STEP 4: umbrella 브랜치 최신화 (rebase)

```bash
cd {worktree_path} && git fetch origin {target_branch}
```

`origin/{target_branch}` 존재 시:
```bash
cd {worktree_path} && git rebase origin/{target_branch}
```
- 충돌 시: Read(`CONFLICT_RESOLUTION.md`) 후 절차를 따른다.
  - 변수: `resolve_root={worktree_path}`, `피처브랜치={target_branch}`, `branch={worktree_branch}`
  - 해결 완료: `git rebase --continue`
  - 해결 실패: [STOP]

`origin/{target_branch}` 없으면 (로컬 only): rebase 생략, 계속 진행

### STEP 5: 머지 대상 확인 + 충돌 사전 검사

**커밋 목록 확보:**
```bash
cd '{worktree_path}' && \
  MERGE_BASE=$(git merge-base "origin/{target_branch}" HEAD 2>/dev/null || git merge-base "{target_branch}" HEAD 2>/dev/null) && \
  [ -n "$MERGE_BASE" ] && git log "$MERGE_BASE"..HEAD --oneline || echo "MERGE_BASE_NOT_FOUND"
```
- `"MERGE_BASE_NOT_FOUND"` → "머지 베이스를 찾을 수 없습니다." 출력 후 [STOP]
- 그 외: 커밋 목록 표시

**충돌 사전 검사 (Dry-run):**
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/merge/scripts/merge_worktrees.py '{target_branch}' --dry-run --branch '{worktree_branch}'
```
- `status == "ok"`: `merge_order`와 `conflict_count` 확인
- `conflict_count > 0`: `conflict_files` 목록 표시 및 사용자 주의 알림

### STEP 6: [GATE] 머지 승인

AskUserQuestion: "{target_branch}에 위 커밋들을 머지할까요? {conflict_count}건의 충돌이 예상됩니다. 진행하시겠습니까? (yes / no)"
**[응답 전 머지 실행 금지]**

- "yes" → STEP 7 진행
- "no" → "머지 취소." [STOP]

### STEP 7: 머지 실행

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/merge/scripts/merge_worktrees.py {target_branch} --branch {worktree_branch}
```

**성공 (exit 0):** 워크트리 동기화 후 STEP 8
```bash
cd {root_path} && git checkout {root_branch}
cd {worktree_path} && git merge --ff-only {target_branch}
```

**충돌 (exit 2):** 충돌 해결 프로세스 (충돌은 root_path에서 발생)
Read(`${CLAUDE_PLUGIN_ROOT}/skills/merge/reference/CONFLICT_RESOLUTION.md`) 후 절차를 따른다.
- 변수: `resolve_root={root_path}`, `피처브랜치={target_branch}`, `branch={worktree_branch}`
- 해결 실패 (exit 1): [STOP]
- 해결 완료: 워크트리 동기화 후 STEP 8

### STEP 8: 완료 출력

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/merge/scripts/merge_state.py clear --issue '{issue}'
```

```
┌───────────────────────────────────────────────┐
│ 머지 완료                                      │
│ umbrella: {target_branch}                      │
│ 워크트리: {worktree_branch}                    │
│ 이슈: {issues_str}                             │
└───────────────────────────────────────────────┘
```

AskUserQuestion으로 다음 선택지 제시:
```
머지가 완료되었습니다. 다음 중 선택하세요:
1. `/autopilot:pr` — PR 생성
2. `/autopilot:cleanup` — 머지 완료된 워크트리 정리
3. 추가 작업 계속
```

[STOP]
