---
name: autopilot-cleanup
description: 머지 완료된 워크트리를 정리한다. 워크트리 제거 + 브랜치 삭제.
---

# Worktree Cleanup

## 사용법
`/autopilot:cleanup {피처브랜치} {이슈키1} {이슈키2} ...`

## 실행 절차

실행:
```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/cleanup_worktrees.py {피처브랜치} --issues {이슈키1} {이슈키2} ...
```

exit 0:
  ```
  ┌──────────────────────────────────────────────────────────┐
  │ 정리 완료                                                 │
  │ 브랜치: {피처브랜치}                                      │
  │ 처리된 이슈: {이슈키 목록}                                │
  │ 처리: 워크트리 제거 + 브랜치 삭제                          │
  └──────────────────────────────────────────────────────────┘
  ```
exit 1: data.errors 내용 출력

exit 0일 때 AskUserQuestion으로 다음 선택지 제시:
```
정리가 완료되었습니다. 다음 중 선택하세요:
1. `/autopilot:status` — 활성 워크트리 상태 조회
2. 추가 작업 계속
```

[TERMINATE]
