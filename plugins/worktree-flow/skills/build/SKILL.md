---
name: build
description: Executor 에이전트 전용. 승인된 플랜을 순서대로 구현하고 파일 수정마다 WIP 커밋을 남긴다.
---

# Worktree Build

**실행 주체: Executor 에이전트 전용**
git merge, git push, git rebase 절대 실행 금지. 구현 완료 후 [TERMINATE].

## 사용법
`/worktree-flow:build {이슈키}`

## 실행 절차

STEP 0: 전제조건 검증
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py build {이슈키}`
  실패: reason 그대로 출력 후 [STOP] — 우회 시도 금지

STEP 1: 잠금 설정
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/transition.py {이슈키} APPROVED BUILDING`
  성공: STEP 2 진행
  실패: reason 그대로 출력 후 [STOP]

STEP 2: 플랜 로드
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/load_issue.py {이슈키} --section 플랜`
  성공: data.content의 "구현 순서" 항목 목록 보관
  실패: reason 그대로 출력 후 [STOP]

STEP 3: 구현 실행
  "구현 순서" 각 항목을 순서대로:

    3-1. 해당 파일 현재 상태 읽기
    3-2. 플랜 명세대로 코드 수정
    3-3. WIP 커밋 (명시적 체크포인트):
         실행: `bash ${CLAUDE_PLUGIN_ROOT}/scripts/wip_commit.sh`
         (변경사항 없으면 자동 스킵)
    3-4. 진행 기록:
         실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/log_progress.py {이슈키} --step "{파일명} 완료"`

  중간 실패 시:
    실행: `bash ${CLAUDE_PLUGIN_ROOT}/scripts/wip_commit.sh` (실패 직전까지 보존)
    실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/log_progress.py {이슈키} --error "{오류 내용}"`
    [STOP] — 임의 복구 시도 금지

STEP 4: 완료 처리
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/transition.py {이슈키} BUILDING DONE`
  성공: notify_user("구현 완료 [{이슈키}]: /worktree-flow:merge {피처브랜치} 실행 가능")
  실패: reason 그대로 출력 후 [STOP]

[TERMINATE]
git merge, git push, git rebase 실행 금지.
