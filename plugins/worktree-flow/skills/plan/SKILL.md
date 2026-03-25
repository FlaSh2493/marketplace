---
name: plan
description: Planner 에이전트 전용. 이슈 명세를 분석하여 구현 플랜을 작성하고 사용자 승인을 받는다.
---

# Worktree Plan

**실행 주체: Planner 에이전트 전용**
코드 수정, git 명령, 파일 직접 생성 절대 금지.

## 사용법
`/worktree-flow:plan {이슈키}`

## 실행 절차

STEP 0: 전제조건 검증
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py plan {이슈키}`
  성공: data.md_path 보관
  실패: reason 그대로 출력 후 [STOP]

STEP 1: 이슈 명세 로드 (필요 섹션만)
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/load_issue.py {이슈키} --sections 설명,메타데이터`
  성공: data.content를 컨텍스트로 보관
  실패: reason 그대로 출력 후 [STOP]

STEP 2: Plan Mode 진입
  EnterPlanMode 실행
  [이하 Plan Mode 내 — 코드 수정 물리적 불가]

  2-1. 영향 범위 분석
    실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/analyze_scope.py {이슈키}`
    성공: data.affected_files의 skeleton을 보고 관련성이 높은 파일만 선택하여 Read
          skeleton만으로 충분히 파악되는 파일은 Read 생략
    실패: reason 그대로 출력 후 [STOP]

  2-2. 플랜 작성 (Claude 역할)
    STEP 1 요구사항 + 영향 파일 분석을 바탕으로 아래 템플릿 형식으로 작성:
    ```
    ### 영향 파일
    | 파일 | 변경 유형 | 이유 |
    |------|----------|------|
    | src/... | 수정/신규 | ... |

    ### 구현 순서
    1. `{파일}` — {변경 내용}
    2. `{파일}` — {변경 내용}

    ### 예상 커밋 단위
    - `feat({이슈키}): {설명}`

    ### 검토 포인트
    - [ ] {항목}
    ```

  ExitPlanMode 실행
  → 작성한 플랜을 사용자에게 제시

[GATE] STEP 3: 플랜 피드백
  실행: AskUserQuestion("위 플랜을 검토해주세요.\n- 승인: 플랜을 저장하고 완료합니다\n- 수정 {내용}: 피드백을 반영하여 플랜을 다시 작성합니다\n- no: 취소합니다")

  응답 "승인":
    STEP 4 진행

  응답 "수정 {내용}":
    피드백을 반영하여 STEP 2로 돌아가 EnterPlanMode 재진입 → 플랜 재작성 → ExitPlanMode → STEP 3 루프

  응답 "no":
    출력: "플랜 작성이 취소되었습니다."
    [TERMINATE]

STEP 4: 플랜 저장
  생성한 플랜 내용을 stdin으로 전달:
  실행: `echo "{플랜내용}" | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/write_plan.py {이슈키}`
  성공: STEP 5 진행
  실패: reason 그대로 출력 후 [STOP]

STEP 5: 상태 전이 (READY → PLANNED)
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/transition.py {이슈키} READY PLANNED`
  성공: notify_user("플랜 완료 [{이슈키}]: /worktree-flow:review {이슈키} 실행 가능")
  실패: reason 그대로 출력 후 [STOP]

[TERMINATE]
코드 수정, git 명령 실행 절대 금지.
