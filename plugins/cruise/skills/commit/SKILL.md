---
name: cruise-commit
description: (명시적 커맨드 실행 전용) /cruise:commit 명령이 입력된 경우에만 활성화한다.
disable-model-invocation: true
---

# Commit

> **종료 규칙:** 산출물 파일(commit.md)을 남기지 않는다.
> 커밋 결과의 진실 원천은 **git 이력**이며, jsync:log·result 스킬이 GitHub(gh)에서 직접 조회한다.
> 어떤 STEP에서 종료하든 상태 한 줄(완료/취소/실패)만 출력하고 [STOP]한다.

> **금지:**
> - `~/Documents/tasks/{KEY}/commit.md` 등 어떤 산출물 파일도 Write 하지 않는다
> - 상태 한 줄 외 요약·다음 액션 추천 일체 출력하지 않는다
> - 사용자가 명시적으로 요청하지 않은 어떤 액션도 수행하지 않는다
> - 다른 스킬을 자동으로 호출하지 않는다

---

## STEP 1 — 컨텍스트 수집

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/context.py
```

결과를 메모리에 보관: `root`, `branch`, `key`, `has_uncommitted`, `task_md_exists`.

---

## STEP 2 — 커밋 대상 확인

`has_uncommitted` 가 false면:
- "취소: 커밋할 변경사항이 없습니다." 한 줄 출력 후 [STOP]

---

## STEP 3 — 변경사항 그룹핑

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/commit/scripts/group_changes.py {root}
```

도메인/타입별 그룹 제안 출력.

---

## STEP 4 — 그룹핑 확정 (질문 없음)

STEP 3의 제안 그룹핑을 그대로 확정하고 STEP 5로 진행한다.
- 사용자에게 질문하지 않는다 (`AskUserQuestion` 사용 금지).
- 제안 그룹핑이 명백히 부적절한 경우에만 스스로 합리적으로 재조정한 뒤 진행한다.

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

## STEP 6 — 종료

산출물 파일을 남기지 않는다. 생성한 커밋은 git 이력에 남으며, 나중에 result·jsync:log 스킬이
GitHub(gh)에서 커밋·PR 정보를 직접 조회한다.

`완료: {n}개 커밋` 한 줄만 출력하고 [STOP].
