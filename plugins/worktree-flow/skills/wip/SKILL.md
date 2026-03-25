---
name: worktree-flow-wip
description: WIP 자동 커밋 기능을 켜거나 끕니다. (on/off)
---

# Worktree WIP Control

현재 워크트리의 WIP 자동 커밋 기능을 활성화하거나 비활성화합니다.

## 사용법
- `/worktree-flow:wip on` — 현재 워크트리의 자동 커밋 활성화
- `/worktree-flow:wip off` — 현재 워크트리의 자동 커밋 비활성화
- `/worktree-flow:wip --global on` — **전역** 마스터 스위치 켜기
- `/worktree-flow:wip --global off` — **전역** 마스터 스위치 끄기

## 실행 (Strict Protocol)

### [Case A] 현재 워크트리 제어
- **ON**: `touch .wip-active && echo "✅ 현재 워크트리 WIP 활성화"`
- **OFF**: `rm -f .wip-active && echo "⏹️ 현재 워크트리 WIP 비활성화"`

### [Case B] 전역 마스터 스위치 제어 (Global)
- **Global ON**: 
  ```bash
  mkdir -p .claude && echo '{"wip_enabled": true}' > .claude/worktree-flow.json && echo "🚀 전역 WIP 마스터 스위치 ON"
  ```
- **Global OFF**: 
  ```bash
  mkdir -p .claude && echo '{"wip_enabled": false}' > .claude/worktree-flow.json && echo "🛑 전역 WIP 마스터 스위치 OFF (전체 정지)"
  ```

### [Check] 상태 확인
- `ls -a .wip-active 2>/dev/null && echo "현재: ON" || echo "현재: OFF"`
- `cat .claude/worktree-flow.json 2>/dev/null | jq -r '.wip_enabled' | xargs -I {} echo "전역 스위치: {}"`
