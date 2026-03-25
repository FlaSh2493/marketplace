---
name: review
description: Main Session 전용. 플랜을 사용자에게 보여주고 승인 후 Executor 에이전트를 런칭한다.
---

# Worktree Review

**실행 주체: Main Session 전용**
코드 수정 금지. 사용자 승인 없이 transition.py 실행 금지.

## 사용법
`/worktree-flow:review {이슈키}`

## 실행 절차

STEP 0: 전제조건 검증
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py review {이슈키}`
  성공: data.md_path 보관
  실패: reason 그대로 출력 후 [STOP]

STEP 1: 플랜 출력
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/load_issue.py {이슈키} --section 플랜`
  성공: data.content를 채팅창에 마크다운으로 렌더링
  실패: reason 그대로 출력 후 [STOP]

[GATE] STEP 2: 승인 게이트
  실행: AskUserQuestion("**{이슈키} 플랜 검토**\n위 플랜으로 구현을 시작할까요?\n- yes: 구현 시작\n- 수정 {내용}: 플랜 수정 후 재확인\n- no: 취소")
  [LOCK: 응답 전 transition.py 절대 실행 금지]

  응답 "yes":
    STEP 3 진행

  응답 "수정 {내용}":
    생성한 수정 내용을 stdin으로 전달:
    실행: `echo "{수정된 플랜 전체}" | python3 ${CLAUDE_PLUGIN_ROOT}/scripts/write_plan.py {이슈키}`
    성공: STEP 1로 돌아가 플랜 재출력
    실패: reason 그대로 출력 후 [STOP]

  응답 "no":
    출력: "취소되었습니다. 플랜을 수정하려면 /worktree-flow:plan {이슈키}를 다시 실행하세요."
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
