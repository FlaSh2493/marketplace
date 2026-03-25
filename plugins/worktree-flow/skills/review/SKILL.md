---
name: review
description: Main Session 전용. 플랜을 검토하고 승인하거나 수정·재플랜·직접 지시로 분기한다. 승인 후 Executor 에이전트를 런칭한다.
---

# Worktree Review

**실행 주체: Main Session 전용**
코드 수정 금지. 사용자 승인 없이 transition.py 실행 금지.

## 사용법
`/worktree-flow:review {이슈키}`

## 실행 절차

STEP 0: 전제조건 검증
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py review {이슈키}`
  성공: data.md_path, data.has_plan, data.current_state 보관
  실패: reason 그대로 출력 후 [STOP]

STEP 1: 현재 상태에 따라 분기

  플랜 있음 (data.has_plan == true):
    실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/load_issue.py {이슈키} --section 플랜`
    성공: data.content를 채팅창에 마크다운으로 렌더링
    실패: reason 그대로 출력 후 [STOP]

  플랜 없음 (data.has_plan == false):
    출력: "{이슈키}에 저장된 플랜이 없습니다. 직접 지시로 구현을 시작할 수 있습니다."

[GATE] STEP 2: 응답 분기
  실행: AskUserQuestion("**{이슈키} 플랜 검토**\n- yes: 이 플랜으로 구현을 시작합니다\n- 수정 {내용}: 플랜 내용을 수정합니다\n- 재플랜: /worktree-flow:plan을 다시 실행합니다\n- 지시: {내용}: 플랜에 반영 후 구현을 시작합니다\n- no: 취소합니다")
  [LOCK: 응답 전 transition.py 절대 실행 금지]

  응답 "yes":
    STEP 3 진행

  응답 "수정 {내용}":
    수정 내용을 반영하여 플랜 갱신:
    실행: `echo "{수정된 플랜 전체}" | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/write_plan.py {이슈키}`
    성공: STEP 1로 돌아가 플랜 재출력 → STEP 2 루프
    실패: reason 그대로 출력 후 [STOP]

  응답 "재플랜":
    실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/transition.py {이슈키} PLANNED READY`
    성공: 출력 "플랜이 초기화되었습니다. /worktree-flow:plan {이슈키} 를 실행하세요."
    실패: reason 그대로 출력 후 [STOP]
    [TERMINATE]

  응답 "지시: {내용}":
    EnterPlanMode 실행
    [이하 Plan Mode 내 — 코드 수정 물리적 불가]
    지시 내용을 반영하여 플랜 작성 (기존 플랜이 있으면 통합, 없으면 신규 작성):
    ```
    ### 영향 파일
    | 파일 | 변경 유형 | 이유 |
    |------|----------|------|

    ### 구현 순서
    1. `{파일}` — {변경 내용}

    ### 예상 커밋 단위
    - `feat({이슈키}): {설명}`

    ### 검토 포인트
    - [ ] {항목}
    ```
    ExitPlanMode 실행
    → 작성한 플랜을 사용자에게 제시
    실행: `echo "{플랜내용}" | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/write_plan.py {이슈키}`
    성공: STEP 3 진행
    실패: reason 그대로 출력 후 [STOP]

  응답 "no":
    출력: "취소되었습니다."
    [TERMINATE]

STEP 3: 승인 처리
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/transition.py {이슈키} PLANNED APPROVED`
  성공: STEP 4 진행
  실패: reason 그대로 출력 후 [STOP]

STEP 4: Executor 에이전트 런칭
  헤드리스 Executor 에이전트 런칭:
    - 에이전트: wt-manager (executor 역할)
    - 작업 디렉토리: .worktrees/{이슈키}/
    - 프롬프트: "/worktree-flow:build {이슈키}"
  출력: "Executor 에이전트 시작됨 [{이슈키}]. 구현 완료 시 알림 예정."

[TERMINATE]
