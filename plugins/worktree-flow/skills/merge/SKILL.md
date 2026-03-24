---
name: worktree-flow-merge
description: AI 분석을 통해 WIP 커밋을 정리한 뒤 각 워크트리 브랜치를 머지합니다.
---

# Worktree Merge (AI-Assisted)

워크트리 브랜치들을 피처 브랜치에 일반 머지합니다. 단순히 합치는 것이 아니라, AI가 작업을 분석하여 의미 있는 단위로 커밋을 정리한 뒤 병합합니다.

## 사용법
`/worktree-flow:merge {피처브랜치} [--dry-run] [--abort]`

예시: `/worktree-flow:merge feat/order-system`

## 실행 절차 (AI 어시스턴트용)

1. **내역 분석**:
   - 머지 전, 각 워크트리 브랜치의 변경 사항을 분석하세요. (`git log` 및 `git diff` 활용)
   - "UI 수정", "API 연동", "리팩토링" 등 의미 있는 단위로 커밋 그룹을 나눕니다.

2. **커밋 플랜 제안**:
   - 사용자에게 어떤 단위로 커밋을 합치고 정리할지 제안하고 승인을 받으세요.
   - 예: "3개의 WIP 커밋을 'feat: 주문 API 연동' 하나로 합칠까요?"

3. **커밋 정리**:
   - 승인된 계획에 따라 `git reset --soft`와 `git commit`을 사용하여 브랜치를 재구성하세요.

4. **최종 병합**:
   - 정리가 완료되면 아래 스크립트를 실행하여 피처 브랜치에 최종 병합합니다.
   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/scripts/merge_worktrees.py $ARGUMENTS
   ```

## 결과 처리
- 성공 시: 머지된 브랜치와 정리된 히스토리를 안내하고 해당 세션의 WIP 자동 커밋을 비활성화(`rm -f .wip-active`)하세요.
- 충돌 시: 충돌 파일과 위치를 안내하고 해결 방법을 제안하세요.
