---
name: plan
description: 이슈 워크트리를 생성하고 플랜을 세운 뒤 사용자 승인 후 구현까지 진행한다.
---

# Worktree Plan

**실행 주체: Main Session**
코드 수정은 ExitPlanMode 승인 이후에만 허용.

## 사용법
`/worktree-flow:plan {이슈키}`

## 실행 절차

STEP 1: 워크트리 생성 및 진입
  EnterWorktree 실행 (name: {이슈키})

STEP 2: 기존 플랜 확인
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/load_issue.py {이슈키} --section 플랜`
  성공 (플랜 있음): data.content를 컨텍스트로 보관 → STEP 3-B 진행
  실패 (플랜 없음): STEP 3-A 진행

STEP 3-A: 신규 플랜 작성 (플랜 없을 때)
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/load_issue.py {이슈키} --sections 설명,메타데이터`
  성공: data.content를 컨텍스트로 보관
  실패: reason 그대로 출력 후 [STOP]

  EnterPlanMode 실행

  영향 범위 분석:
    1. 이슈 명세에서 변경 예상 파일/컴포넌트/함수명 키워드 추출
    2. MCP tool 호출: semantic_search_nodes_tool (query: {키워드}, limit: 10)
       성공 + 결과 있음: 관련 노드 목록 확보 → 3번 진행
       성공 + 결과 없음: fallback → 4번 진행
       실패 (그래프 없음):
         출력: "code-review-graph 그래프가 없습니다. /worktree-flow:init 을 먼저 실행하세요."
         [STOP]
    3. MCP tool 호출: get_impact_radius_tool (changed_files: 위에서 찾은 파일 목록, max_depth: 2)
       성공: 영향 파일 목록 확보 → 5번 진행
       실패: fallback → 4번 진행
    4. [fallback] Claude가 직접 탐색
       이슈 명세 기반으로 Glob/Grep으로 관련 파일 직접 탐색
    5. 영향 파일 목록 기준으로 필요한 파일만 Read

  플랜 작성:
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

  ExitPlanMode 실행 (승인 시 STEP 4 진행 / 거절 시 TERMINATE)

STEP 3-B: 기존 플랜 재사용 (플랜 있을 때)
  저장된 플랜을 사용자에게 표시
  [GATE] AskUserQuestion("기존 플랜이 있습니다.\n- yes: 이 플랜으로 구현\n- 재플랜: 플랜을 새로 작성\n- 수정 {내용}: 플랜 일부 수정 후 구현")

  응답 "yes": STEP 5 진행 (이슈 로드·분석 생략)
  응답 "재플랜": STEP 3-A 진행
  응답 "수정 {내용}":
    수정 내용 반영하여 플랜 업데이트
    STEP 4 진행

STEP 4: 플랜 저장
  실행: `echo "{플랜내용}" | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/write_plan.py {이슈키}`
  실패: reason 그대로 출력 후 [STOP]

STEP 5: 구현 실행
  "구현 순서" 각 항목을 순서대로:
    5-1. 해당 파일 현재 상태 읽기
    5-2. 플랜 명세대로 코드 수정
  중간 실패 시: [STOP]

STEP 6: 완료
  출력: "구현 완료 [{이슈키}]. 추가 수정은 /worktree-flow:plan {이슈키} 재실행, 머지는 /worktree-flow:merge {피처브랜치}"

[TERMINATE]
