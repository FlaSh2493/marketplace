---
name: autopilot-build
description: /autopilot:plan 이 생성한 {이슈키}/plan.md 를 읽어 구현만 수행한다. 스크립트 기반 Phase 분할과 세션 간 handoff를 지원한다.
---

# Worktree Build (Phased)

**실행 주체: Main Session**

이 스킬은 **plan.md 기반 구현만** 담당한다. 스크립트를 사용하여 컨텍스트를 관리하고, 대규모 작업은 서브에이전트에게 위임한다.

## 사용법
```
/autopilot:build {브랜치명}
/autopilot:build                  ← 워크트리 내에서 실행 시 현재 브랜치 자동 감지
```

---

## Phase 1: Setup (환경 준비 및 플랜 로드)

1. **컨텍스트 확보**:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/build_context.py {브랜치명}
   ```
   - 결과 `data` (`worktree_path`, `branch`, `issue_doc_root`, `issues`, `resume`) 확보.
   - `resume: true` 이면 이전 세션의 handoff가 존재함을 의미한다.

2. **플랜 파싱**:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/load_plan.py --issue-doc-root {data.issue_doc_root} --issues {data.issues 쉼표 없이 공백 구분}
   ```
   - 결과 `data.plans[]` 의 `phases`, `target_files`, `image_paths` 확보.

3. **Handoff 초기화**:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/build_handoff.py init --branch {data.branch} --worktree {data.worktree_path} --issues {data.issues}
   ```
   - `tasks/.state/build-handoff.json` 을 생성하거나 기존 파일을 확인한다.

4. **진행 상태 확인**:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/build_handoff.py completed-step-ids
   ```
   - 전체 `plan.phases` 의 steps 중 완료된 step을 제외한 **pending_steps**를 계산한다.
   - `mark build --phase setup` 기록.

---

## Phase 2: Implementation (구현)

**분할 판정**:
- `총 pending_steps 수 < 8` → **단일 모드**: 메인 세션이 직접 수행.
- `총 pending_steps 수 >= 8` → **분할 모드**: `autopilot-builder` 서브에이전트에게 5개씩 청크 위임.

### [단일 모드]
남은 Phase와 step을 순서대로 수행한다.
- 각 Phase 완료 시 또는 맥락이 끊길 때:
  ```bash
  python3 ${CLAUDE_PLUGIN_ROOT}/scripts/build_handoff.py append-entry --actor main --steps-json '{완료된 steps}' --summary "요약"
  ```

### [분할 모드]
1. `pending_steps`를 순서대로 **5개씩 청크**로 나눈다.
2. `autopilot-builder` 서브에이전트를 순차적으로 spawn 한다.
   - **프롬프트 구성**: `agents/autopilot-builder.md` 템플릿 사용.
   - **선행 히스토리**: `build_handoff.py show` 결과의 `entries` 요약 전달.
3. 각 에이전트 완료 후 다음 청크로 진행.

**주의사항**:
- 코드 수정은 반드시 `{data.worktree_path}/` 하위만 대상으로 한다.
- `mark build --phase impl` 기록.

---

## Phase 3: Image Check (시각적 검증)

플랜에 `image_paths`가 있는 경우에만 실행한다.
1. `data.plans[].image_paths` 의 이미지를 Read로 열어 구현 결과와 대조.
2. 불일치 시 재작업 → `append-entry`.
3. 완료 시 `mark build --phase image_check` 기록.

---

## Phase 4: Verify (최종 확인)

1. **누락 확인**: `build_handoff.py completed-step-ids` 와 플랜의 전체 steps 비교.
2. **최종 마킹**:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/state_manager.py mark build
   ```
3. **Handoff 정리**:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/build_handoff.py clear
   ```

---

## 완료 안내

AskUserQuestion 으로 다음 선택지를 제시한다:
```
구현이 완료되었습니다. (Handoff 아카이브 완료)
다음 중 선택하세요:
1. /autopilot:check — lint, type-check, test 검사
2. /autopilot:merge {피처브랜치} — 머지 수행
3. 추가 작업 계속
```

---

## 경로 및 금지 규칙 (상기)

- **코드 수정**: `{data.worktree_path}/` 만 허용.
- **이슈 문서**: `{data.issue_doc_root}/` 만 허용.
- **금지**: `load_issue.py` 재호출, `semantic_search` 재탐색, WIP 커밋.
