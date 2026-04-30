---
name: start
description: (명시적 커맨드 실행 전용) /autopilot:start 명령이 입력된 경우에만 이 skill을 활성화한다.
disable-model-invocation: true
---

# Worktree Start

브랜치에 대한 워크트리를 생성하거나 재사용한다.

## 사용법

```
/autopilot:worktree-start {브랜치명} [--issue PLAT-123]
```

## 실행 절차

STEP 1: 워크트리 생성/재사용
실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ensure_worktree.py $ARGUMENTS`

결과 JSON 파싱:
- `status: ok` → `data.display` 내용을 그대로 출력 후 [TERMINATE]
- `status: error` → `data.reason` 내용을 에러로 출력 후 [TERMINATE]
