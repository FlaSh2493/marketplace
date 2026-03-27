---
name: plan
description: 이슈 워크트리를 생성하고 플랜을 세운 뒤 사용자 승인 후 구현까지 진행한다.
---

# Worktree Plan

**실행 주체: Main Session**
코드 수정은 STEP 1 완료 후 {worktree_path} 기반 절대경로로만 허용.
`{이슈키}.md`의 `## 설명` 섹션 수정 절대 금지 — Jira 원본 보존. 추가 요구사항은 `## 추가 요구사항` 섹션에만 append.

## 사용법

`/worktree-flow:plan {이슈키}`

---

## 실행 절차

STEP 0: 워크트리 확보
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ensure_worktree.py {이슈키}`
  성공: data.worktree_path, data.branch 보관
  실패: reason 그대로 출력 후 [STOP]

  출력:
  - created=true:  "워크트리 생성됨: {worktree_path} ({branch})"
  - created=false: "워크트리 재사용: {worktree_path} ({branch})"

STEP 1: 이슈 명세 로드
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/load_issue.py {이슈키} --sections 설명,메타데이터`
  성공: data.content를 컨텍스트로 보관
  실패: reason 그대로 출력 후 [STOP]

  [GATE] AskUserQuestion("이슈 명세를 불러왔습니다. 플랜 작성 전에 추가로 전달할 내용이 있으면 입력하세요.\n(없으면 엔터)")
  응답이 비어있지 않은 경우:
    입력 내용을 분석하여 성격 판단:
      - 요구사항 성격 (새 기능, 조건 추가 등): 이슈 md 요구사항 섹션에 반영 예정으로 표시
      - 플랜 힌트 성격 (방식, 제약 조건 등): 플랜 컨텍스트에만 포함
    요구사항 반영이 있는 경우:
      반영할 내용을 사용자에게 표시
      [GATE] AskUserQuestion("요구사항을 위와 같이 업데이트합니다. 맞나요? (맞으면 엔터, 수정 필요 시 내용 입력)")
      수정 입력 시: 반영 후 재표시 → 게이트 반복
      확인 시: Edit 도구로 `.docs/task/{branch}/{이슈키}/{이슈키}.md` 파일 끝에 추가:
        ```
        ## 추가 요구사항

        {요구사항 내용}
        ```
        (이미 `## 추가 요구사항` 섹션이 있으면 해당 섹션 끝에 append)

STEP 2: 플랜 작성
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
    5. 영향 파일 목록 기준으로 필요한 파일만 Read ({worktree_path} 기반 절대경로)

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

  ExitPlanMode 실행
  - 거절: [TERMINATE]
  - 승인: STEP 3로 진행

STEP 3: 플랜 저장
  실행: `echo "{플랜내용}" | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/write_plan.py {이슈키}`
  실패: reason 그대로 출력 후 [STOP]

STEP 4: 구현 실행
  모든 파일 편집은 {worktree_path} 기반 절대경로를 사용한다.
  예: Edit {worktree_path}/src/components/Login.tsx

  "구현 순서" 각 항목을 순서대로:
    4-1. {worktree_path}/{파일} 읽기
    4-2. 플랜 명세대로 코드 수정
  중간 실패 시: [STOP]

  구현 완료 후 커밋:
    실행: `cd {worktree_path} && git add -A && git commit -m "wip({이슈키}): 구현"`

STEP 5: 완료
  출력: "구현 완료 [{이슈키}] — {worktree_path}"
  [GATE] AskUserQuestion("추가 작업이 있으면 입력하세요.\n(없으면 엔터, 머지하려면 '머지')")
  입력 있음:
    입력 내용을 분석하여 성격 판단:
      - 요구사항 성격: 반영할 내용을 사용자에게 표시
        [GATE] AskUserQuestion("요구사항을 위와 같이 업데이트합니다. 맞나요? (맞으면 엔터, 수정 필요 시 내용 입력)")
        수정 입력 시: 반영 후 재표시 → 게이트 반복
        확인 시: Edit 도구로 `.docs/task/{branch}/{이슈키}/{이슈키}.md` 파일 끝에 추가:
          ```
          ## 추가 요구사항

          {요구사항 내용}
          ```
          (이미 `## 추가 요구사항` 섹션이 있으면 해당 섹션 끝에 append)
      - 플랜 힌트 성격: 플랜 컨텍스트에만 포함
    → STEP 2 진행 (이슈 명세 재로드 생략)
  '머지': 출력 "/worktree-flow:merge {branch} 를 실행하세요." → [TERMINATE]
  엔터: [TERMINATE]
