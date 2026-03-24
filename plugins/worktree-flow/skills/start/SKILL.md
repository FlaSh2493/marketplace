---
name: worktree-flow-start
description: 현재 워크트리 또는 선택한 워크트리에 대한 작업 기획 정보를 가져와서 기획 단계(Plan mode)를 준비합니다.
---

# Worktree Start

현재 워크트리에서 작업을 시작하기 위해 로컬 문서(`.docs/task/`) 또는 Jira에서 작업 설명을 가져옵니다.

## 사용법

1. **메인 저장소에서 실행**: 활성화된 워크트리 목록 중 하나를 선택합니다.
   `/worktree-flow:start`
2. **워크트리 내부에서 실행**: 현재 워크트리의 이슈 번호를 사용하여 정보를 가져옵니다.
   `/worktree-flow:start`

## 실행

아래 스크립트를 실행하여 워크트리 정보를 확인하세요:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/start_worktree.py
```

## 결과 처리

1. 스크립트 결과로 워크트리 목록이 나오면, 사용자에게 번호를 선택받으세요.
2. 선택된 워크트리(또는 현재 워크트리)의 작업 설명(Description)이 출력되면, 해당 내용을 바탕으로 **기획(PLANNING) 모드**로 진입하여 작업을 구체화하세요.
3. 로컬 파일(`.docs/task/{feature}.md`)에 정보가 없는 경우, 출력된 가이드에 따라 Jira 이슈 조회를 시도하세요.
