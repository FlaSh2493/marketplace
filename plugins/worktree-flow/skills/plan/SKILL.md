---
name: plan
description: 워크트리 세션에서 이슈 명세를 분석해 플랜을 세우고, 사용자 승인 후 같은 세션에서 바로 구현을 진행한다.
---

# Worktree Plan

**실행 주체: Main Session 또는 Planner 에이전트**
코드 수정은 ExitPlanMode 승인 이후에만 허용.

## 사용법
`/worktree-flow:plan {이슈키}`

## 실행 절차

STEP 1: 이슈 명세 로드
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/load_issue.py {이슈키} --sections 설명,메타데이터`
  성공: data.content를 컨텍스트로 보관
  실패: reason 그대로 출력 후 [STOP]

STEP 2: 영향 범위 분석 및 플랜 작성
  EnterPlanMode 실행

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

  ExitPlanMode 실행 (승인 시 STEP 3 자동 진행 / 거절 시 TERMINATE)

STEP 3: 플랜 저장
  실행: `echo "{플랜내용}" | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/write_plan.py {이슈키}`
  실패: reason 그대로 출력 후 [STOP] — 저장 실패 시 구현 진입 금지

STEP 4: 구현 실행 (승인된 플랜을 컨텍스트에서 그대로 사용)
  "구현 순서" 각 항목을 순서대로:
    4-1. 해당 파일 현재 상태 읽기
    4-2. 플랜 명세대로 코드 수정

  중간 실패 시:
    [STOP] — 임의 복구 시도 금지

STEP 5: 완료 보고 및 피드백 대기
  출력: "구현 완료 [{이슈키}]. 추가 수정이 있으면 말씀하세요. 머지하려면 /worktree-flow:merge {피처브랜치}"

  사용자 응답 대기:
    응답 없음 / "머지": [TERMINATE]
    계획/플랜을 세우자는 의도 ("계획 세워", "플랜 짜줘", "설계해줘" 등):
      EnterPlanMode 재진입 → STEP 2-2부터 반복 → 완료 후 STEP 5로 돌아옴
    그 외 수정 요청: 플랜 없이 바로 수정 후 STEP 5로 돌아옴
