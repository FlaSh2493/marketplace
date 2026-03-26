---
name: work
description: 이슈 명세서 없이 요구사항을 직접 입력받아 워크트리를 생성하고 바로 구현한다. 플랜 승인 단계 없이 즉시 작업을 시작한다.
---

# Worktree Work

**실행 주체: Main Session**
코드 수정은 STEP 2 완료 이후부터 허용.

## 사용법
`/worktree-flow:work {이슈키} {요구사항}`

## 실행 절차

STEP 1: 워크트리 생성 및 진입
  EnterWorktree 실행 (name: {이슈키})

STEP 2: 영향 범위 분석
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

STEP 3: 구현 실행
  요구사항을 분석하여 필요한 파일을 순서대로:
    3-1. 해당 파일 현재 상태 읽기
    3-2. 요구사항대로 코드 수정
  중간 실패 시: [STOP]

STEP 4: 완료
  출력: "구현 완료 [{이슈키}]. 추가 수정은 /worktree-flow:work {이슈키} {요구사항} 재실행, 머지는 /worktree-flow:merge {피처브랜치}"

[TERMINATE]
