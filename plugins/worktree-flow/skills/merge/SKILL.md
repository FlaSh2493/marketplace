---
name: merge
description: Merger 에이전트 전용. WIP 커밋을 의미 단위로 정리한 뒤 피처 브랜치에 머지하고 워크트리를 정리한다.
---

# Worktree Merge

**실행 주체: Merger 에이전트 전용**
사용자 승인 없이 git reset, git commit 실행 금지.

## 사용법
`/worktree-flow:merge {피처브랜치}`

## 실행 절차

STEP 0: 전제조건 검증
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/preflight.py merge {피처브랜치}`
  성공: data.done_issues 보관
  실패: reason 그대로 출력 후 [STOP]

STEP 1: 사전 분석 (dry-run)
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/merge_worktrees.py {피처브랜치} --dry-run`
  성공: 아래 형식으로 출력
  ```
  머지 대상: {N}개 워크트리
  ┌──────────┬────────┬──────────────────────────┐
  │ 이슈     │ WIP수  │ 충돌 예상 파일            │
  ├──────────┼────────┼──────────────────────────┤
  │ PLAT-101 │  5개   │ (없음)                   │
  │ PLAT-102 │  3개   │ src/api/order.ts         │
  └──────────┴────────┴──────────────────────────┘
  머지 순서: PLAT-101 → PLAT-102 (충돌 적은 순)
  ```
  실패: reason 그대로 출력 후 [STOP]

STEP 2: WIP 커밋 분석
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/analyze_wip.py {피처브랜치}`
  성공: data.commits_by_issue 보관

  Claude 역할: 각 이슈의 WIP 커밋을 의미 단위로 그룹화하여 제안
  출력 형식:
  ```
  커밋 재정의 제안:
  ┌──────────┬───────────────────────────────────────────────────┐
  │ PLAT-101 │ WIP 1,2,3 → feat(PLAT-101): 주문 API 페이지네이션 │
  │          │ WIP 4,5   → feat(PLAT-101): 빈 상태 UI 처리      │
  └──────────┴───────────────────────────────────────────────────┘
  ```

[GATE] STEP 3: 커밋 계획 승인
  실행: AskUserQuestion("이 커밋 계획으로 진행할까요? (수정이 필요하면 내용을 입력하세요 / no: 취소)")
  [LOCK: 응답 전 git reset 절대 실행 금지]

  응답 "yes":
    STEP 4 진행

  응답 "수정 {내용}":
    Claude 역할: 수정 내용 반영하여 그룹 재구성 후 STEP 2 출력 재표시
    [GATE] STEP 3 반복

  응답 "no":
    출력: "머지 취소."
    [TERMINATE]

STEP 4: 커밋 재정의
  승인된 그룹 계획을 JSON으로 직렬화:
  groups = [{"message": "feat(PLAT-101): ...", "commit_indices": [0,1,2]}, ...]

  각 이슈별 순서대로:
    실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/rewrite_commits.py {이슈키} \
           --branch {branch} --base {base} --groups '{groups_json}'`
    성공: "{이슈키} 커밋 재정의 완료" 출력
    실패: reason 그대로 출력 후 [STOP]

STEP 5: 머지 실행
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/merge_worktrees.py {피처브랜치}`
  성공 (exit 0): STEP 6 진행
  충돌 (exit 2): 충돌 해결 프로세스 진입

  [충돌 해결 프로세스]
    실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/show_conflicts.py`
    성공: 각 충돌 파일의 diff 출력

    충돌 파일마다:
    [GATE] AskUserQuestion("충돌: {파일명}\n{diff 내용}\n\n선택: [feature / base / 직접편집]")
    [LOCK: 응답 전 다음 파일 처리 금지]

      응답 "feature":
        실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/resolve_conflict.py {파일} feature`
      응답 "base":
        실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/resolve_conflict.py {파일} base`
      응답 "직접편집":
        출력: "파일을 직접 편집한 뒤 'done'을 입력하세요."
        [GATE] AskUserQuestion("편집 완료 후 'done' 입력")

    모든 충돌 해결 완료 후:
      실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/merge_worktrees.py {피처브랜치} --continue`
      성공: STEP 6 진행
      실패: reason 그대로 출력 후 [STOP]

STEP 6: 정리
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/cleanup_worktrees.py {피처브랜치} --issues {done_issues}`
  성공:
    각 이슈:
      실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/transition.py {이슈키} DONE MERGED`
    아래 형식으로 출력:
    ```
    ┌───────────────────────────────────────┐
    │ 머지 완료                              │
    │ 브랜치: {피처브랜치}                   │
    │ 처리된 이슈: {이슈키 목록}             │
    │ 삭제된 워크트리: {N}개                 │
    └───────────────────────────────────────┘
    ```
  실패: reason 그대로 출력 후 [STOP]

[TERMINATE]
