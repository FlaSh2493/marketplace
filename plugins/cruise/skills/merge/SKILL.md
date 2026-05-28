---
name: cruise-merge
description: (명시적 커맨드 실행 전용) /cruise:merge 명령이 입력된 경우에만 활성화한다.
disable-model-invocation: true
---

# Merge

> **종료 규칙:** 어떤 STEP에서 종료하든 Write 도구로
> `~/Documents/tasks/{KEY}/merge.md` 를 기록하고 [STOP]한다.
> - 신규: 새 파일 생성. 재호출: `entries[]` 에 append.
> - frontmatter 공통 10필드 + 스킬별 필드 완비
> - `status`: completed | cancelled | failed
> - KEY는 context.py 출력. 추출 실패 시 slug(branch) 사용

> **절대 금지:**
> - rebase / force-push / `--force-with-lease` / `pull --rebase`
> - push (pr·review 스킬 전용, 또는 사용자 수동)
> - 산출물 작성 후 요약·다음 액션 추천 일체 출력하지 않는다 ("완료" 한 줄만)
> - 다른 스킬을 자동으로 호출하지 않는다

단일 의미: **현재 브랜치로 source를 머지한다.**

---

## STEP 1 — 컨텍스트 수집

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/context.py
```

결과를 메모리에 보관: `root`, `branch`, `key`, `base_branch`, `base_source`, `has_uncommitted`, `task_md_exists`, `merge_md_exists`.

---

## STEP 2 — 미커밋 변경 확인

`has_uncommitted` 가 true면:
- status=cancelled 로 merge.md 기록 ("커밋 먼저 필요")
- [STOP]

---

## STEP 3 — [GATE] 머지 소스 선택

`AskUserQuestion`: "어느 브랜치를 현재 브랜치({branch})로 머지할까요?"

옵션 (동적 생성):
1. `origin/{base_branch}` — Recommended (`{base_source}` 기반)
2. `origin/main` (base_branch와 다를 경우)
3. `origin/develop` (base_branch와 다를 경우)
4. 직접 입력
5. 취소 → status=cancelled 로 merge.md 기록 후 [STOP]

base_branch 가 null/unknown이면 옵션 1 없이 표시, 사용자에게 직접 입력 유도.

---

## STEP 4 — fetch

```bash
git fetch origin {selected_source}
```

네트워크 실패 → status=failed 로 merge.md 기록 후 [STOP].

---

## STEP 5 — dry-run 충돌 감지

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/merge/scripts/precheck.py \
  --root {root} --source {selected_source}
```

충돌 파일 목록 수집.

---

## STEP 6 — [GATE] 머지 확인

`AskUserQuestion`: "다음 내용으로 머지를 진행할까요?"
표시 내용:
- 현재 브랜치: `{branch}`
- 머지 소스: `{selected_source}`
- 예상 충돌: `{conflict_count}건` (없으면 "없음")
- 충돌 파일 목록 (있을 경우)

**진행** → STEP 7
**취소** → status=cancelled 로 merge.md 기록 후 [STOP]

---

## STEP 7 — git merge 실행

```bash
git merge {selected_source}
```

**충돌 없음** → 머지 커밋 자동 생성 → STEP 8

**충돌 있음** → 충돌 파일마다 반복:
```
AskUserQuestion: "{filepath} 충돌 처리 방법"
  1) ours (현재 브랜치 버전 유지)
  2) theirs (머지 소스 버전 선택)
  3) 직접 편집 (에디터로 열기)
```

선택에 따라:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/merge/scripts/resolve_conflict.py {filepath} {ours|theirs}
# 직접 편집 시: 사용자가 편집 완료 후 확인 → git add {filepath}
```

모든 충돌 해결 후:
```bash
git add -A
git commit
```

실패 → status=failed 로 merge.md 기록 후 [STOP]

---

## STEP 8 — merge.md 저장

`merge_md_exists == true` 이면 기존 merge.md 의 `entries[]` 에 항목 append. `false` 이면 신규 생성.

frontmatter (공통 10필드 + 스킬별):
```yaml
---
key: {KEY}
key_source: {key_source}
skill: merge
summary: {task_md_exists == true 면 task.md 에서 상속, 아니면 ""}
branch: {branch}
repo: {repo}
head_sha: {git rev-parse --short HEAD}
status: completed
created: {최초 생성 UTC, 재호출 시 유지}
updated: {UTC ISO8601}
tags: []
entries:
  - at: {UTC ISO8601}
    source: {selected_source}
    target: {branch}
    conflicts_count: {n}
    result_sha: {git rev-parse --short HEAD}
---
```

본문:
- `# Merge — {KEY}` (H1)
- `## 머지 이력` — entries 테이블 (at, source→target, conflicts, sha)

"완료" 한 줄 출력 후 [STOP].
