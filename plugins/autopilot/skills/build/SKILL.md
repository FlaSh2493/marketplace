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

## STEP 0.5: 프로젝트 커스텀 지침 참조 (Memory)

[_shared/CUSTOM_INSTRUCTIONS.md](../_shared/CUSTOM_INSTRUCTIONS.md)에 따라 다음 순서로 지침을 확인한다.

1. **plan.md 확인**: `plan.md`의 `## 프로젝트 커스텀 지침` 섹션에 이미 지침이 기록되어 있다면 해당 내용을 최우선으로 따른다.
2. **지침 로드**: `plan.md`에 없거나 개별 실행 시에는 다음 명령을 통해 지침을 확인한다.
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/load_custom_instructions.py build
   ```

- **필수 참조**: 로드된 지침은 **본 스킬 수행 중 반드시 준수해야 하는 필수 제약 사항**이며, 표준 절차를 왜곱하지 않고 반영한다.

---

## STEP 0: 컨텍스트 확보 및 초기화

1. **컨텍스트 확보**:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/build_context.py {브랜치명}
   ```
   - 결과 `data` (`worktree_path`, `branch`, `issue`, `issue_doc_root`, `resume`, `resume_stale`, `stale_reason`) 확보.

2. **Resume/Stale 분기**:
   - **`resume_stale: true` 인 경우**:
     - 사유(`stale_reason`)와 함께 AskUserQuestion: "이전 진행 기록이 현재 컨텍스트와 다릅니다. (A) 기존 기록 아카이브 후 새로 시작 (B) 중단"
     - 사용자가 (A) 선택 시:
       ```bash
       python3 ${CLAUDE_PLUGIN_ROOT}/scripts/build_handoff.py clear --issue {data.issue}
       ```
       이후 `init` 단계로 이동.
   - **`resume: true` 인 경우**:
     - ```bash
       python3 ${CLAUDE_PLUGIN_ROOT}/scripts/build_handoff.py resume-summary \
         --branch {data.branch} --worktree {data.worktree_path} --issue {data.issue}
       ```
       결과를 출력.
     - AskUserQuestion: "(A) 이어서 진행 (B) 처음부터 다시 시작 (기존 기록 아카이브)"
     - (A) 선택 시: 마커 초기화 없이 이어서 진행.
     - (B) 선택 시:
       ```bash
       python3 ${CLAUDE_PLUGIN_ROOT}/scripts/build_handoff.py clear --issue {data.issue}
       ```
       이후 `init` 단계로 이동.
   - **신규 또는 아카이브 후**:
     ```bash
     python3 ${CLAUDE_PLUGIN_ROOT}/scripts/init_state_dir.py --issue {data.issue} --clear build check check-all merge merge-all pr review-fix
     python3 ${CLAUDE_PLUGIN_ROOT}/scripts/build_handoff.py init \
       --branch {data.branch} --worktree {data.worktree_path} --issue {data.issue}
     ```

---

## Phase 1: 플랜 로드

1. **플랜 파싱 & 대기 작업 산출**:
   - `load_plan.py`를 실행하여 전체 플랜 확보:
     ```bash
     python3 ${CLAUDE_PLUGIN_ROOT}/scripts/load_plan.py \
       --issue-doc-root {data.issue_doc_root} --issue {data.issue}
     ```
   - **중요**: `pending-steps` 명령으로 실제 남은 작업을 JSON으로 확보한다:
     ```bash
     python3 ${CLAUDE_PLUGIN_ROOT}/scripts/build_handoff.py pending-steps \
       --plan-json {plan_output_file} --branch {data.branch} --issue {data.issue}
     ```
   - 결과 `pending_steps` 리스트 확보.
   - 완료 마커:
     ```bash
     python3 ${CLAUDE_PLUGIN_ROOT}/scripts/state_manager.py mark build --phase setup --issue {data.issue}
     ```

---

## Phase 2: Implementation (구현)

**분할 판정**:
- `총 pending_steps 수 < 8` → **단일 모드**: 메인 세션이 직접 수행.
- `총 pending_steps 수 >= 8` → **분할 모드**: `autopilot-builder` 서브에이전트에게 위임.

### [단일 모드]
`pending_steps`를 순서대로 수행한다. **각 step 완료 직후** 반드시 기록한다.
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/build_handoff.py append-step \
  --branch {data.branch} --issue {data.issue} \
  --phase-idx {N} --step-idx {M} --text "{step_text}" --actor main
```

### [분할 모드]
1. `pending_steps`를 순서대로 **5개씩 청크**로 나눈다.
2. `autopilot-builder` 서브에이전트를 순차적으로 spawn 한다.
   - **프롬프트**: `agents/autopilot-builder.md` 사용.
   - **선행 히스토리**:
     ```bash
     python3 ${CLAUDE_PLUGIN_ROOT}/scripts/build_handoff.py show --issue {data.issue}
     ```
     결과를 프롬프트에 포함.
3. 각 에이전트는 내부적으로 step 완료 시마다 `append-step`을 호출한다.

**주의사항**:
- 코드 수정은 반드시 `{data.worktree_path}/` 하위만 대상으로 한다.

완료 마커:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/state_manager.py mark build --phase impl --issue {data.issue}
```

---

## Phase 3: Image Check (시각적 검증)

플랜에 `image_paths`가 있는 경우에만 실행한다.
1. `data.plans[].image_paths` 의 이미지를 Read로 열어 구현 결과와 대조.
2. 불일치 시 재작업 → 완료 시 `append-step` (필요 시 가상 step 생성).
3. 완료 마커:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/state_manager.py mark build --phase image_check --issue {data.issue}
   ```

---

## Phase 4: Verify (최종 확인)

1. **누락 확인**:
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/build_handoff.py pending-steps \
     --plan-json {plan_output_file} --branch {data.branch} --issue {data.issue}
   ```
   - 결과가 비어있는지 확인.
   - 만약 `pending_steps`가 남아있다면 **Phase 2로 다시 진입**하여 남은 작업을 수행한다. (최대 2회 반복)
   - 반복 후에도 남은 경우 사용자에게 보고 후 중단.

2. **최종 마킹 & 정리**:
   - 전체 완료 마커:
     ```bash
     python3 ${CLAUDE_PLUGIN_ROOT}/scripts/state_manager.py mark build --issue {data.issue}
     ```
   - Handoff 아카이브:
     ```bash
     python3 ${CLAUDE_PLUGIN_ROOT}/scripts/build_handoff.py clear --issue {data.issue}
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
