---
name: worktree-flow-create
description: 피처 브랜치로부터 여러 개의 워크트리를 생성합니다. (예: /worktree-flow:create feat/feature-name task1 task2 ...)
---

# Worktree Create

피처 브랜치에서 워크트리를 일괄 생성합니다.

## 사용법
- **기본 실행 (현재 브랜치 기반)**: 
  `/worktree-flow:create`
  (현재 브랜치와 관련된 `.docs/task/{브랜치명}/` 디렉토리 하위의 개별 md 파일에서 이슈 번호를 추출하여 선택 목록을 보여줍니다.)
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

1. 만약 결과 JSON에 `"mode": "selection"`이 포함되어 있다면:
   - `tasks` 목록 내의 이슈들을 사용자에게 보여주세요.
   - **반드시 `AskUserQuestion`을 사용하여 사용자가 원하는 이슈들을 선택(다수 선택 가능)할 수 있게 하세요.**
   - 사용자가 이슈를 선택하면, 해당 이슈 키들을 인자로 하여 다시 스크립트를 실행하세요.
     예: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/create_worktrees.py {피처브랜치} {선택된_이슈1} {선택된_이슈2}`

2. 워크트리 생성이 완료되면 결과 JSON을 읽고 사용자에게 생성된 워크트리 목록을 보여주세요.

3. 성공 후 WIP 자동 커밋을 활성화하기 위해 다음을 수행합니다:
 ```bash
 mkdir -p .worktrees && touch .worktrees/.wip-enabled
 ```
