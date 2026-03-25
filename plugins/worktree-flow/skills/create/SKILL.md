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

## 2. 결과 처리 및 단계별 실행 (Strict Protocol)

### 🚨 STEP 1: 대상 이슈 식별 (Selection)
- **입력**: 스크립트 실행 결과 (`mode: selection`).
- **실행**: 
  - `tasks` 목록 내의 이슈들을 사용자에게 보여줌.
  - **`AskUserQuestion`**으로 사용자가 원하는 이슈들을 선택(다수 선택 가능)하도록 요청.
- **[LOCK]** 사용자의 선택이 완료될 때까지 대기하십시오.

### 🚨 STEP 2: 워크트리 일괄 생성 실행
- **입력**: 사용자가 선택한 이슈 키 목록.
- **실행**: 이슈 키들을 인자로 하여 다시 스크립트 실행.
  - `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/create_worktrees.py {피처브랜치} {선택된_이슈1} ...`
- **검증**: 생성된 워크트리 목록(`stdout` 또는 JSON 결과) 확인.

### 🚨 STEP 3: 환경 초기화 및 보고
- **실행**: 
  - 생성된 모든 워크트리 목록을 사용자에게 표 형태로 출력.
  - 성공 후 WIP 자동 커밋 기반 마련: `mkdir -p .worktrees && touch .worktrees/.wip-enabled`
- **[DONE]** 최종 생성 결과를 보고하고 스킬을 종료하십시오.

