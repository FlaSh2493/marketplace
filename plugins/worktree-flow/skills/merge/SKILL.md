---
name: merge
description: Merger 에이전트 전용. WIP 커밋을 squash merge로 피처 브랜치에 통합하고 워크트리를 정리한다. 워크트리 브랜치는 태그로 보존된다.
---

# Worktree Merge

**실행 주체: Merger 에이전트 전용**
워크트리 브랜치 히스토리 직접 수정 절대 금지. git push 금지.

## 사용법
`/worktree-flow:merge {피처브랜치}`

## 실행 절차

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

STEP 2: WIP 커밋 요약 표시
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/analyze_wip.py {피처브랜치}`
  성공: 각 이슈의 WIP 커밋 목록 표시

  Claude 역할: 각 이슈의 변경 내용을 요약하여 커밋 메시지 제안
  ```
  커밋 메시지 제안:
  ┌──────────┬───────────────────────────────────────┐
  │ PLAT-101 │ feat(PLAT-101): 주문 API 페이지네이션  │
  │ PLAT-102 │ feat(PLAT-102): 빈 상태 UI 처리       │
  └──────────┴───────────────────────────────────────┘
  ```

[GATE] STEP 3: 커밋 메시지 승인
  실행: AskUserQuestion("이 커밋 메시지로 진행할까요? (수정이 필요하면 내용을 입력하세요 / no: 취소)")
  [LOCK: 응답 전 머지 실행 금지]

  응답 "yes": STEP 4 진행
  응답 "수정 {내용}": 메시지 반영 후 STEP 2 출력 재표시 → STEP 3 반복
  응답 "no": 출력 "머지 취소." [TERMINATE]

STEP 4: Squash merge 실행
  각 이슈별 순서대로:
    실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/merge_worktrees.py {피처브랜치} --issue {이슈키} --message "{커밋메시지}"`
    성공 (exit 0): 다음 이슈 진행
    충돌 (exit 2): 충돌 해결 프로세스 진입

    [충돌 해결 프로세스]
      실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/show_conflicts.py`
      충돌 파일마다:
        [GATE] AskUserQuestion("충돌: {파일명}\n{diff}\n\n선택: [feature / base / 직접편집]")
        응답 "feature": `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/resolve_conflict.py {파일} feature`
        응답 "base": `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/resolve_conflict.py {파일} base`
        응답 "직접편집":
          [GATE] AskUserQuestion("편집 완료 후 'done' 입력")
      실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/merge_worktrees.py {피처브랜치} --issue {이슈키} --continue`

STEP 5: 정리
  실행: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/cleanup_worktrees.py {피처브랜치} --issues {이슈키목록}`
  성공:
    ```
    ┌───────────────────────────────────────────────┐
    │ 머지 완료                                      │
    │ 브랜치: {피처브랜치}                           │
    │ 처리된 이슈: {이슈키 목록}                     │
    │ WIP 보존 태그: archive/{이슈키}-wip-{날짜}     │
    └───────────────────────────────────────────────┘
    ```
  실패: reason 그대로 출력 후 [STOP]

[TERMINATE]
