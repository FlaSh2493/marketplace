---
name: build
description: (명시적 커맨드 실행 전용) /autopilot:build 명령이 입력된 경우에만 이 skill을 활성화한다.
disable-model-invocation: true
---

# 구현

> **금지:** Plan 외 범위 수정 (리팩토링·import 정리·시그니처 변경) / 여러 Phase 동시 처리 / 모호한 Plan 임의 보강

Plan 산출물을 입력으로 받아 Phase 단위로 구현한다.

## 사용법
`/autopilot:build {브랜치명}`

## 흐름 개요

```
STEP 1  워크트리 확보
STEP 2  Plan 로드
STEP 3  Phase별 구현 (반복)
STEP 4  종료
```

---

## STEP 1: 워크트리 확보

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/resolve_worktree.py '{브랜치명}'
```

- `status == "ok"` → `data.worktree_path`, `data.root_path`, `data.issue` 보관
- `status == "error"`:
  - `reason == "WORKTREE_NOT_FOUND"`: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/list_worktrees.py` 실행 후 목록 제시, AskUserQuestion으로 선택. 선택된 브랜치로 다시 실행하여 컨텍스트 확보.
  - 그 외: reason 출력 후 [STOP]

**이후 모든 코드 파일 작업은 `worktree_path` 기준으로 수행한다.**

---

## STEP 2: Plan 로드

- `~/Documents/autopilot/{issue}/plan.md` 읽기
- Phase 의존성 그래프(`## Phase 의존성`) 파싱
- 실행 순서 결정

---

## STEP 3: Phase별 반복

각 Phase에 대해 아래 절차를 수행한다.

**분기 결정** — Phase 메타(`depends_on`, `scope`, `output_shape`) 확인:
- `depends_on=[]` && `scope ≥ medium` && `output_shape=interface` → **서브에이전트 위임**
- 그 외 → **메인 처리**

**구현:**
- `templates/impl-prompt.md` 형식으로 구현 요청을 구성한다.
- 의존 Phase가 있는 경우, 해당 Phase의 종결 요약(`phase-summary.md`)을 포함한다.
- **메인 처리**: 현재 세션에서 직접 구현 코드를 출력한다.
- **서브에이전트 위임**: `autopilot-builder` 등 전용 에이전트에게 위임하고 결과(인터페이스/결정사항)만 회수한다.

**종결:**
- `templates/phase-summary.md` 형식으로 해당 Phase의 결과를 요약한다.
- 사용자에게 요약을 출력한다.
- 다음 Phase가 있는 경우 **"새 세션에서 시작"**을 강력히 권장하는 안내 문구를 출력한다.

---

## STEP 4: 종료

- 모든 Phase 완료 후 전체 변경 파일 목록을 출력한다.
- 적용된 Phase 번호와 요약 내용을 최종 정리하여 보고한다.

---

**종결 후 세션 분리 권장:** Phase 전환 시 새 세션 사용을 안내한다 (컨텍스트 오염 방지).
