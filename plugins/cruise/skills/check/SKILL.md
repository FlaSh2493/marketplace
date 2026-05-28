---
name: cruise-check
description: (명시적 커맨드 실행 전용) /cruise:check 명령이 입력된 경우에만 활성화한다.
disable-model-invocation: true
---

# Check

> **종료 규칙:** 어떤 STEP에서 종료하든 Write 도구로
> `~/Documents/tasks/{KEY}/check.md` 를 기록하고 [STOP]한다.
> - frontmatter 공통 10필드 + 스킬별 필드 완비
> - `status`: completed | cancelled | failed
> - KEY는 context.py 출력. 추출 실패 시 slug(branch) 사용

> **금지:**
> - `as any` · `@ts-ignore` · 린트 비활성화 주석으로 에러 우회
> - run_check.py 결과 무시하고 직접 판단
> - Fix 3회 초과 시도
> - 산출물 작성 후 요약·다음 액션 추천 일체 출력하지 않는다 ("완료" 한 줄만)
> - 다른 스킬을 자동으로 호출하지 않는다

---

## STEP 1 — 컨텍스트 수집

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/context.py
```

결과를 메모리에 보관: `root`, `branch`, `key`, `task_md_exists`, `check_md_exists`.

---

## STEP 2 — 앱 환경 탐지

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/check/scripts/detect_commands.py {root}
```

앱 디렉토리별 lint/check-types/test 명령어 목록 확보.
탐지 실패 시 check.md에 `status: failed` 기록 후 [STOP].

---

## STEP 3 — 순차 실행 (lint → type → test)

각 앱 디렉토리에서 순서대로 실행한다.

**lint:**
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/check/scripts/run_check.py \
  lint "{config.lint}" --cwd {check_dir} --auto-fix
```

**check-types:**
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/check/scripts/run_check.py \
  check-types "{config.check-types}" --cwd {check_dir}
```

**test:**
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/check/scripts/run_check.py \
  test "{config.test}" --cwd {check_dir}
```

모든 단계 통과 → STEP 5.
실패 → STEP 4.

---

## STEP 4 — 자동 Fix 루프 (최대 3회)

**카운터**: fix_attempts (0에서 시작)

1. 에러 분석: run_check.py 출력의 `errors` 배열과 해당 파일을 읽고 수정 적용
   - lint: `--auto-fix` 가 이미 실행됨. 잔여 에러를 파일 단위 수정
   - check-types / test: 에러 메시지 분석 후 파일 수정
2. fix_attempts += 1
3. 실패했던 단계부터 재실행
4. 통과 → STEP 5
5. fix_attempts >= 3 → check.md에 `status: failed` 기록 후 [STOP]

---

## STEP 5 — check.md 저장

frontmatter (공통 10필드 + 스킬별):
```yaml
---
key: {KEY}
key_source: {key_source}
skill: check
summary: {task_md_exists == true 면 task.md 에서 상속, 아니면 ""}
branch: {branch}
repo: {repo}
head_sha: {git rev-parse --short HEAD}
status: completed  # 또는 failed
created: {UTC ISO8601}
updated: {UTC ISO8601}
tags: []
result: pass  # 또는 fail
tools:
  lint: pass    # pass | fail | skipped
  type: pass
  test: pass
fix_attempts: 0
---
```

본문:
- `# Check — {KEY}` (H1)
- `## 결과` — 각 도구별 통과/실패 요약
- `## 에러 (실패 시)` — 남은 에러 목록

"완료" 한 줄 출력 후 [STOP].
