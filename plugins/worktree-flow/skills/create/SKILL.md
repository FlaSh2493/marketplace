---
name: worktree-flow-create
description: 피처 브랜치로부터 여러 개의 워크트리를 생성합니다. (예: /worktree-flow:create feat/feature-name task1 task2 ...)
---

# Worktree Create

피처 브랜치에서 워크트리를 일괄 생성합니다.

## 사용법
- **기본 실행 (현재 브랜치 기반)**: 
  `/worktree-flow:create`
  (현재 브랜치와 관련된 `.docs/task/` 파일에서 이슈 번호를 추출하여 선택 목록을 보여줍니다.)
- **특정 브랜치 지정**: 
  `/worktree-flow:create {피처브랜치}`
- **수동 작업 지정**: 
  `/worktree-flow:create {피처브랜치} {이슈1} {이슈2} ...`

예시: `/worktree-flow:create .` 또는 `/worktree-flow:create feat/order-system PLAT-101 PLAT-102`

## 실행
아래 스크립트를 실행하여 워크트리를 생성하라:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/create_worktrees.py $ARGUMENTS
```

## 결과 처리
결과 JSON을 읽고 사용자에게 생성된 워크트리 목록을 보여주세요.
성공 후 WIP 자동 커밋을 활성화하기 위해 다음을 수행합니다:
```bash
mkdir -p .worktrees && touch .worktrees/.wip-enabled
```
