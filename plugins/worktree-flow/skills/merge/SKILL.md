---
name: worktree-flow-merge
description: 각 워크트리 브랜치를 피처 브랜치로 머지하고 워크트리를 정리합니다. (예: /worktree-flow:merge feat/feature-name)
---

# Worktree Merge

워크트리 브랜치들을 피처 브랜치에 일반 머지합니다. 머지 전 태그를 남겨 유실을 방지하며, 완료 후 워크트리를 삭제합니다.

## 사용법
`/worktree-flow:merge {피처브랜치} [--dry-run] [--abort]`

예시: `/worktree-flow:merge feat/order-system`

## 실행
아래 스크립트를 실행하라:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/merge_worktrees.py $ARGUMENTS
```

## 결과 처리
- 성공 시: 머지된 브랜치, 생성된 태그, 정리된 워크트리 목록을 안내하고 WIP 자동 커밋을 비활성화(`rm -f .worktrees/.wip-enabled`)하세요.
- 충돌 시: 충돌 파일과 위치를 안내하고 해결 방법(수동/전략)을 제안하세요. 사용자가 충돌을 해결하면 나머지를 계속 진행합니다.
