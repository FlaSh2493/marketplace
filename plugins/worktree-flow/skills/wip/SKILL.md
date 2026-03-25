---
name: wip
description: 현재 워크트리의 WIP 자동 커밋을 수동으로 켜거나 끈다. create 스킬이 자동으로 활성화하므로 일반적으로 직접 실행 불필요.
---

# Worktree WIP Control

**실행 주체: Main Session 전용**
create 스킬이 워크트리 생성 시 .wip-active를 자동 생성하므로 수동 실행은 예외 상황에서만 사용.

## 사용법
- `/worktree-flow:wip on` — 현재 워크트리 WIP 활성화
- `/worktree-flow:wip off` — 현재 워크트리 WIP 비활성화
- `/worktree-flow:wip --global off` — 전체 WIP 긴급 정지

## 실행 절차

[Case A] `wip on`:
  실행: `touch .wip-active`
  출력: "현재 워크트리 WIP 자동 커밋 활성화"
  [TERMINATE]

[Case B] `wip off`:
  실행: `rm -f .wip-active`
  출력: "현재 워크트리 WIP 자동 커밋 비활성화"
  [TERMINATE]

[Case C] `wip --global off`:
  실행: `python3 -c "import json,os; p='.claude/worktree-flow.json'; d=json.load(open(p)) if os.path.exists(p) else {}; d['wip_enabled']=False; json.dump(d,open(p,'w'))"`
  출력: "전역 WIP 마스터 스위치 OFF — 모든 워크트리 자동 커밋 정지"
  [TERMINATE]

[Case D] `wip --global on`:
  실행: `python3 -c "import json,os; p='.claude/worktree-flow.json'; d=json.load(open(p)) if os.path.exists(p) else {}; d['wip_enabled']=True; json.dump(d,open(p,'w'))"`
  출력: "전역 WIP 마스터 스위치 ON"
  [TERMINATE]
