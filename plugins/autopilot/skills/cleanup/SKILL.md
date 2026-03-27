---
name: autopilot-cleanup
description: 머지 완료된 워크트리를 정리한다. 브랜치는 태그로 보존 후 삭제.
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
  │ WIP 보존 태그: archive/{피처}/{이슈키}-wip-{날짜} (각각)  │
  └──────────────────────────────────────────────────────────┘
  ```
exit 1: data.errors 내용 출력

[TERMINATE]
