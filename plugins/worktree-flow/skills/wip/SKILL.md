---
name: worktree-flow-wip
description: WIP 자동 커밋 기능을 켜거나 끕니다. (on/off)
---

# Worktree WIP Control

WIP 자동 커밋을 활성화하거나 비활성화합니다.

## 사용법
- `/worktree-flow:wip on` — 활성화
- `/worktree-flow:wip off` — 비활성화
- `/worktree-flow:wip` — 현재 상태 확인

## 실행
인자에 따라 아래 쉘 명령어를 실행하세요:

- `on`: `mkdir -p .worktrees && touch .worktrees/.wip-enabled`
- `off`: `rm -f .worktrees/.wip-enabled`
- 인자 없음: `test -f .worktrees/.wip-enabled && echo "활성화" || echo "비활성화"`
