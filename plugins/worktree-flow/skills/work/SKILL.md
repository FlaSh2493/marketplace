---
name: work
description: 새 세션에서 기존 워크트리에 추가/수정/삭제 작업 시 사용. 요구사항을 직접 입력받아 플랜을 작성하고 구현한다. 이슈 명세 재로드 없이 요구사항 기반으로 바로 플랜을 세운다.
---

# Worktree Work

**실행 주체: Main Session**
코드 수정은 STEP 1 완료 이후부터 허용.

## 사용법
`/worktree-flow:work {이슈키} {요구사항}`

## ⚠️ 초기화 — 실행 절차 진입 전 필수

**지금 즉시 EnterWorktree를 호출하라. 다른 어떤 작업도 그 이전에 하지 않는다.**

  EnterWorktree (name: {이슈키})
  - 이미 존재하는 워크트리라면 새로 생성하지 않고 기존 워크트리 재사용
  - 성공: 아래 실행 절차로 진행
  - 실패: 오류 메시지 출력 후 즉시 [TERMINATE]

---

## 실행 절차

STEP 1: 플랜 작성
  EnterPlanMode 실행

  영향 범위 분석:
    1. {요구사항}에서 변경 예상 파일/컴포넌트/함수명 키워드 추출
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
       요구사항 기반으로 Glob/Grep으로 관련 파일 직접 탐색
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

  ExitPlanMode 실행 (승인 시 STEP 2 진행 / 거절 시 TERMINATE)

STEP 2: 이슈 문서 업데이트
  요구사항 섹션 업데이트 내용을 사용자에게 표시
  [GATE] AskUserQuestion("요구사항을 위와 같이 업데이트합니다. 맞나요? (맞으면 엔터, 수정 필요 시 내용 입력)")
  수정 입력 시: 해당 내용 반영 후 재표시 → 게이트 반복
  확인 시:
    요구사항 섹션 저장: `echo "{요구사항}" | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/write_section.py {이슈키} 요구사항`
    플랜 저장: `echo "{플랜내용}" | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/write_plan.py {이슈키}`
  실패: reason 그대로 출력 후 [STOP]

STEP 3: 구현 실행
  "구현 순서" 각 항목을 순서대로:
    3-1. 해당 파일 현재 상태 읽기
    3-2. 플랜 명세대로 코드 수정
  중간 실패 시: [STOP]

STEP 4: 완료
  출력: "구현 완료 [{이슈키}]."
  [GATE] AskUserQuestion("추가 작업이 있으면 입력하세요.\n(없으면 엔터, 머지하려면 '머지')")
  입력 있음: 해당 내용을 새 요구사항으로 보관 → STEP 1 진행
  '머지': 출력 "/worktree-flow:merge {피처브랜치} 를 실행하세요." → [TERMINATE]
  엔터: [TERMINATE]
