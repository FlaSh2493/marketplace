---
name: worktree-flow-status
description: 현재 활성화된 모든 워크트리의 상태(브랜치, 변경사항 수 등)를 조회합니다.
---

# Worktree Status

모든 워크트리의 상태를 조회합니다.

## 사용법
`/worktree-flow:status`

## 실행
아래 스크립트를 실행하라:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/status.py
```

## 결과 처리
결과 JSON을 읽어 각 워크트리의 경로, 브랜치명, 변경사항 수, 베이스 브랜치 대비 커밋 수를 표 형식으로 보기 좋게 출력하세요.
