---
name: worktree-flow-wip
description: WIP 자동 커밋 기능을 켜거나 끕니다. (on/off)
---

# Worktree WIP Control

현재 워크트리의 WIP 자동 커밋 기능을 활성화하거나 비활성화합니다.

## 사용법
- `/worktree-flow:wip on` — 현재 워크트리의 자동 커밋 활성화
- `/worktree-flow:wip off` — 현재 워크트리의 자동 커밋 비활성화
- `/worktree-flow:wip status` — 현재 활성화 상태 확인

## 실행
인자에 따라 아래 쉘 명령어를 실행하세요:

- `on`: `touch .wip-active`
- `off`: `rm -f .wip-active`
- `status`: `test -f .wip-active && echo "상태: 활성화 (ON)" || echo "상태: 비활성화 (OFF)"`
- 인자 없음: `status` 명령어와 동일하게 처리
