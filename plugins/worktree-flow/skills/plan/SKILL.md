---
name: plan
description: Planner 에이전트 전용. 이슈 명세를 분석하여 구현 플랜을 작성하고 review를 요청한다.
---

# Worktree Plan

**실행 주체: Planner 에이전트 전용**
코드 수정, git 명령, 파일 직접 생성 절대 금지. 플랜 작성 후 [TERMINATE].

## 사용법
`/worktree-flow:plan {이슈키}`

## 실행 절차

STEP 0: 전제조건 검증
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py plan {이슈키}`
  성공: data.md_path 보관
  실패: reason 그대로 출력 후 [STOP]

STEP 1: 이슈 명세 로드
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/load_issue.py {이슈키}`
  성공: data.content를 컨텍스트로 보관
  실패: reason 그대로 출력 후 [STOP]

STEP 2: 코드베이스 영향 범위 분석
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/analyze_scope.py {이슈키}`
  성공: data.affected_files 목록을 참고하여 관련 파일 읽기
  실패: reason 그대로 출력 후 [STOP]

STEP 3: 플랜 작성 및 저장
  Claude 역할: STEP 1 요구사항 + STEP 2 영향 파일 분석을 바탕으로 아래 템플릿 형식의 플랜 생성

  플랜 템플릿:
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

  생성한 플랜 내용을 stdin으로 전달:
  실행: `echo "{플랜내용}" | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/write_plan.py {이슈키}`
  성공: STEP 4 진행
  실패: reason 그대로 출력 후 [STOP]

STEP 4: 상태 전이
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/transition.py {이슈키} READY PLANNED`
  성공: notify_user("플랜 완료 [{이슈키}]: /worktree-flow:review {이슈키} 실행 요청")
  실패: reason 그대로 출력 후 [STOP]

[TERMINATE]
코드 수정, git 명령 실행 절대 금지.
