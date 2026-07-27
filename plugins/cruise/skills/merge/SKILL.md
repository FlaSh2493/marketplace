---
name: cruise-merge
description: (명시적 커맨드 실행 전용) /cruise:merge 명령이 입력된 경우에만 활성화한다.
disable-model-invocation: true
---

# Merge

> **종료 규칙:** 산출물 파일(merge.md)을 남기지 않는다.
> 머지 이력의 진실 원천은 **git 이력**이며, 소비자는 `git log --merges` 로 직접 조회한다.
> 어떤 STEP에서 종료하든 상태 한 줄(완료/취소/실패)만 출력하고 [STOP]한다.

> **절대 금지:**
> - rebase / force-push / `--force-with-lease` / `pull --rebase`
> - push (pr·review 스킬 전용, 또는 사용자 수동)
> - `~/Documents/tasks/{KEY}/merge.md` 등 어떤 산출물 파일도 Write 하지 않는다
> - 상태 한 줄 외 요약·다음 액션 추천 일체 출력하지 않는다
> - 다른 스킬을 자동으로 호출하지 않는다

단일 의미: **현재 브랜치로 source를 머지한다.**

---

## STEP 1 — 컨텍스트 수집

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/context.py
```

결과를 메모리에 보관: `root`, `branch`, `key`, `base_branch`, `base_source`, `has_uncommitted`, `task_md_exists`.

---

## STEP 2 — 미커밋 변경 확인

`has_uncommitted` 가 true면:
- "취소: 미커밋 변경이 있습니다. 커밋 먼저 필요." 한 줄 출력 후 [STOP]

---

## STEP 3 — [GATE] 머지 소스 선택

`AskUserQuestion`: "어느 브랜치를 현재 브랜치({branch})로 머지할까요?"

옵션 (동적 생성):
1. `origin/{base_branch}` — Recommended (`{base_source}` 기반)
2. `origin/main` (base_branch와 다를 경우)
3. `origin/develop` (base_branch와 다를 경우)
4. 직접 입력
5. 취소 → "취소: 사용자가 머지를 취소했습니다." 한 줄 출력 후 [STOP]

base_branch 가 null/unknown이면 옵션 1 없이 표시, 사용자에게 직접 입력 유도.

---

## STEP 4 — fetch

```bash
git fetch origin {selected_source}
```

네트워크 실패 → "실패: fetch 실패 ({원인})." 한 줄 출력 후 [STOP].

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
**취소** → "취소: 사용자가 머지를 취소했습니다." 한 줄 출력 후 [STOP]

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

실패 → "실패: 머지 실패 ({원인})." 한 줄 출력 후 [STOP]

---

## STEP 8 — 종료

산출물 파일을 남기지 않는다. 머지 커밋은 git 이력이 진실 원천이며,
나중에 소비자가 `git log --merges` 로 직접 조회한다.

`완료: {selected_source} → {branch} 머지 ({result_sha})` 한 줄만 출력하고 [STOP].
(`result_sha` = `git rev-parse --short HEAD`)
