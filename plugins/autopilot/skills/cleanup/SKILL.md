---
name: autopilot-cleanup
description: 머지 완료된 워크트리를 정리한다. 워크트리 제거 + 브랜치 삭제.
---

# Worktree Cleanup

## 사용법
`/autopilot:cleanup {피처브랜치} {브랜치명1} [브랜치명2 ...]`

---

## STEP 0.5: 프로젝트 커스텀 지침 참조

[_shared/CUSTOM_INSTRUCTIONS.md](../_shared/CUSTOM_INSTRUCTIONS.md)에 따라 다음 명령을 실행하여 프로젝트 지침을 확인한다.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/load_custom_instructions.py cleanup
```

- **필수 참조**: 로드된 지침을 **반드시 준수**하며, 표준 절차를 왜곡하지 않고 행동한다.

---

## 실행 절차

실행:
```
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/cleanup_worktrees.py {피처브랜치} --branches {브랜치명1} [브랜치명2 ...]
```

exit 0:
  ```
  ┌──────────────────────────────────────────────────────────┐
  │ 정리 완료                                                 │
  │ 브랜치: {피처브랜치}                                      │
  │ 처리된 워크트리: {브랜치 목록}                             │
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
