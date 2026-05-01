---
name: check
description: (명시적 커맨드 실행 전용) /autopilot:check 명령이 입력된 경우에만 이 skill을 활성화한다.
disable-model-invocation: true
---

# 검증

> **금지:** `as any` · `@ts-ignore` · 린트 비활성화 주석으로 에러 우회 / `run_check.py` 결과 무시하고 직접 판단 / Fix 3회 초과 시도

검증 도구(lint → check-types → test)를 순차 실행하고 실패 시 자동 수정을 시도한다.

## 사용법
`/autopilot:check [{브랜치명}]`

## 흐름 개요

```
STEP 1  컨텍스트 및 설정 로드
STEP 2  순차적 검증 실행 (lint → check-types → test)
STEP 3  자동 Fix 루프 (최대 3회, 실패 시 진입)
STEP 4  결과 보고
```

---

## STEP 1: 컨텍스트 및 설정 로드

1. **워크트리 확인:**
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/resolve_worktree.py {브랜치명}
   ```
   → `data.worktree_path` → `worktree_path`, `data.issue` → `issue_key`

2. **검증 설정 로드:**
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/check/scripts/detect_commands.py {worktree_path}
   ```

3. **변경 파일 파악:**
   최근 Build 작업에서 변경된 파일 목록을 확보한다. (기록이 없으면 `git diff --name-only` 활용)

---

## STEP 2: 순차적 검증 실행

`lint` → `check-types` → `test` 순서로 실행한다. 각 단계에서 실패하면 즉시 STEP 3으로 진입한다.

**Lint:**
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/check/scripts/run_check.py lint "{config.lint}" --cwd {worktree_path} --auto-fix
```

**Check-types:**
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/check/scripts/run_check.py check-types "{config.check-types}" --cwd {worktree_path}
```

**Test:**
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/check/scripts/run_check.py test "{config.test}" --cwd {worktree_path}
```

모든 단계 통과 시 → STEP 4로 이동

---

## STEP 3: 자동 Fix 루프 (최대 3회)

lint는 `--auto-fix` 플래그로 eslint/biome/ruff `--fix`를 먼저 자동 실행한다. 남은 에러와 check-types·test 실패는 아래 절차:

1. **에러 분석:** `templates/fix-prompt.md`를 사용해 실패 도구의 JSON 결과(`errors`, `error_count`)와 대상 파일 내용 포함하여 수정 요청.
2. **수정 적용:** 제안된 수정 사항을 파일에 반영.
3. **재검증:** 실패했던 단계부터 재실행.

종료 조건:
- 모든 검증 통과 → STEP 4
- 3회 시도 후에도 실패 → 보고 후 [STOP]

---

## STEP 4: 결과 보고

- 모든 검사 통과: `✅ All checks passed`
- 실패 시: 실패한 도구와 남은 에러 개수 보고

---

