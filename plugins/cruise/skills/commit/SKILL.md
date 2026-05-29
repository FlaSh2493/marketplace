---
name: cruise-commit
description: (명시적 커맨드 실행 전용) /cruise:commit 명령이 입력된 경우에만 활성화한다.
disable-model-invocation: true
---

# Commit

> **종료 규칙:** 어떤 STEP에서 종료하든 Write 도구로
> `~/Documents/tasks/{KEY}/commit.md` 를 기록하고 [STOP]한다.
> - frontmatter 공통 9필드 + 스킬별 필드 완비
> - `status`: completed | cancelled | failed
> - KEY는 context.py 출력. 추출 실패 시 slug(branch) 사용

> **금지:**
> - 산출물 작성 후 요약·다음 액션 추천 일체 출력하지 않는다 ("완료" 한 줄만)
> - 사용자가 명시적으로 요청하지 않은 어떤 액션도 수행하지 않는다
> - 다른 스킬을 자동으로 호출하지 않는다

---

## STEP 1 — 컨텍스트 수집

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/context.py
```

결과를 메모리에 보관: `root`, `branch`, `key`, `has_uncommitted`, `task_md_exists`, `commit_md_exists`.

---

## STEP 2 — 커밋 대상 확인

`has_uncommitted` 가 false면:
- status=cancelled 로 commit.md 기록 ("커밋할 변경사항이 없습니다.")
- [STOP]

---

## STEP 3 — 변경사항 그룹핑

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/commit/scripts/group_changes.py {root}
```

도메인/타입별 그룹 제안 출력.

---

## STEP 4 — [GATE] 그룹핑 확인

`AskUserQuestion`: "이 그룹핑으로 커밋할까요?"
- **확인** → STEP 5
- **수정** → 사용자 지시대로 그룹 재조정 → STEP 4 반복
- **취소** → status=cancelled 로 commit.md 기록 후 [STOP]

---

## STEP 5 — 커밋 실행

그룹별로 순서대로:
```bash
git add {파일들...}
git commit -m "{type}({scope}): {subject}{ [KEY]}

{body (선택)}"
```

커밋 메시지 규칙:
- Conventional Commits 형식: `type(scope): subject`
- type: feat | fix | refactor | chore | docs | style | test | perf
- subject: 명령형 동사로 시작, 소문자
- **이슈 키가 있으면 subject 끝에 ` [{KEY}]` 형태로 반드시 포함한다.** `key_source == "slug"`인 경우 생략.

---

## STEP 6 — commit.md 저장

frontmatter (공통 9필드 + 스킬별):
```yaml
---
key: {KEY}
key_source: {key_source}
skill: commit
summary: {task_md_exists == true 면 task.md 에서 상속, 아니면 ""}
branch: {branch}
repo: {repo}
status: completed
created: {UTC ISO8601}
updated: {UTC ISO8601}
tags: []
commits:
  - sha: {sha}
    message: {subject}
    files_count: {n}
commits_count: {n}
---
```

본문:
- `# Commit — {KEY}` (H1)
- `## 커밋 목록` — 생성된 커밋 sha/메시지/파일 수 표

"완료" 한 줄 출력 후 [STOP].
