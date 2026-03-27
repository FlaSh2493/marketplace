---
name: plan
description: 이슈 워크트리를 생성하고 플랜을 세운 뒤 사용자 승인 후 구현까지 진행한다. 추가 수정 요청 시 컨텍스트를 유지하며 반복한다.
---

# Worktree Plan

**실행 주체: Main Session**
`{이슈키}.md`의 `## 설명` 섹션 수정 절대 금지 — Jira 원본 보존. 추가 요구사항은 `## 추가 요구사항` 섹션에만 append.

## 사용자 인터셉트

사용자는 플랜 작성 중이든 구현 중이든 **언제든 메시지를 보낼 수 있다**.
사용자 메시지가 도착하면 현재 진행 중인 작업을 즉시 멈추고:
1. 사용자 입력을 읽고 의도를 파악한다
2. **방향 수정** (예: "그 파일 말고 이 파일을 수정해", "그 방식 대신 이렇게"): 요구사항 성격이면 `{이슈키}.md`의 `## 추가 요구사항`에 append 후, 현재 플랜을 수정하거나 새로 플랜을 세운다 → STEP 1로
3. **추가 정보 제공** (예: "참고로 이 함수는 deprecated야"): 요구사항 성격이면 문서에도 반영. 컨텍스트에 반영하고 중단된 작업을 이어간다
4. **작업 중단** (예: "그만", "멈춰", "스톱"): 즉시 멈춘다. 커밋이나 정리 작업 없이 그 자리에서 [TERMINATE]
5. **재개** (중단 후 사용자가 다시 지시): 전제조건(워크트리 진입)은 이미 완료되었으므로 다시 실행하지 않는다. 사용자 지시에 따라 중단된 STEP부터 이어가거나, 플랜 수정이 필요하면 STEP 1로 돌아간다.

## 사용법
`/worktree-flow:plan {이슈키}`

---

## 전제조건 — 워크트리 진입 (완료 전까지 아래 STEP으로 절대 넘어가지 않는다)

1. 워크트리 준비:
   `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ensure_worktree.py {이슈키}` 실행
   성공: data.worktree_path, data.branch, data.root_path, data.main_branch 보관
   실패: reason 출력 후 [STOP]
2. 워크트리로 체크아웃:
   `cd {data.worktree_path} && pwd && git branch --show-current` 실행
   워크트리 경로와 브랜치 확인 완료 후 다음 단계 진행

**중요**: Claude Bash 도구는 각 명령마다 새 셸을 생성하므로, 이후 모든 작업에서:
- 파일 작업: `{data.worktree_path}/` 를 prefix로 붙인 **절대경로** 사용
- Bash/git 명령: 매번 `cd {data.worktree_path} && command` 형태로 실행

---

## 실행 절차

STEP 0: 이슈 명세 로드 (최초 1회)
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
      확인 시: Edit 도구로 {root_path}/.docs/task/{main_branch}/{이슈키}/{이슈키}.md 파일 끝에 추가:
        ```
        ## 추가 요구사항

        {요구사항 내용}
        ```
        (이미 `## 추가 요구사항` 섹션이 있으면 해당 섹션 끝에 append)

STEP 1: 플랜 작성 ← 루프 재진입 시 여기부터
  EnterPlanMode 실행

  영향 범위 분석:
    1. 이슈 명세(또는 추가 수정 요청)에서 변경 예상 파일/컴포넌트/함수명 키워드 추출
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
       이슈 명세 기반으로 Bash에서 `cd {data.worktree_path} && rg {패턴}` 으로 직접 탐색
    5. 영향 파일 목록 기준으로 필요한 파일만 Read (`{data.worktree_path}/파일경로` 절대경로 사용)

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
  - 승인: STEP 2로 진행

STEP 2: 플랜 저장
  실행: `echo "{플랜내용}" | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/write_plan.py {이슈키}`
  실패: reason 그대로 출력 후 [STOP]

STEP 3: 구현
  모든 파일은 `{data.worktree_path}/` prefix를 붙인 절대경로로 편집한다.

  "구현 순서" 각 항목을 순서대로:
    3-1. 파일 읽기 (`{data.worktree_path}/파일경로`)
    3-2. 플랜 명세대로 코드 수정
  중간 실패 시: [STOP]

  구현 완료 후 커밋:
    실행: `cd {data.worktree_path} && git add -A && git commit -m "wip({이슈키}): 구현"`

STEP 4: 피드백 루프
  출력: "구현 완료 [{이슈키}]"
  [GATE] AskUserQuestion("추가 작업이 있으면 입력하세요.\n(없으면 엔터, 머지하려면 '머지')")

  입력 있음:
    입력 내용을 분석하여 성격 판단:
      - 요구사항 성격: 반영할 내용을 사용자에게 표시
        [GATE] AskUserQuestion("요구사항을 위와 같이 업데이트합니다. 맞나요? (맞으면 엔터, 수정 필요 시 내용 입력)")
        수정 입력 시: 반영 후 재표시 → 게이트 반복
        확인 시: Edit 도구로 {root_path}/.docs/task/{main_branch}/{이슈키}/{이슈키}.md 파일 끝에 추가:
          ```
          ## 추가 요구사항

          {요구사항 내용}
          ```
          (이미 `## 추가 요구사항` 섹션이 있으면 해당 섹션 끝에 append)
      - 플랜 힌트 성격: 플랜 컨텍스트에만 포함
    → STEP 1로 돌아간다 (이슈 명세 재로드 생략, 컨텍스트 유지)

  '머지': 출력 "/worktree-flow:merge {branch} 를 실행하세요." → [TERMINATE]
  엔터: [TERMINATE]
