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
2. 선택된 워크트리(또는 현재 워크트리)의 작업 설명(Description)이 출력되면, 해당 내용을 `task.md`에 기록하고 `task_boundary`를 통해 **기획(PLANNING) 모드**로 진입하세요.
3. 기획이 확정되면(승인 요청 전), 해당 내용을 **`.docs/task/{feature}.md`** 파일에 저장하세요.
   - `{feature}`는 현재 브랜치명에서 워크트리 suffix(`--wt-XXXX`)를 제거한 값입니다. (예: `qa/data-center-bug--wt-IET-7571` → `{feature}`: `qa/data-center-bug`)
   - 파일 내 해당 이슈(`jira: IET-XXXX`)의 작업 항목 아래에 **`### 플랜`** 섹션을 추가하거나 업데이트하세요.
   - 새로운 플랜이 작성될 때마다 해당 섹션을 덮어씁니다.
4. 수립된 기획안(`implementation_plan.md`)의 내용을 **마크다운 텍스트로 채팅창에 출력**하여 사용자가 즉시 확인할 수 있게 하세요.
5. `notify_user(BlockedOnUser: true)`를 호출하여 사용자가 승인 버튼을 통해 구현을 시작할 수 있게 하세요.
   - 플랜 승인은 반드시 `notify_user`를 통한 **승인 버튼**으로만 받으세요. 채팅(`AskUserQuestion` 등)으로 승인을 묻지 마세요.
6. 사용자가 **'build'** 라고 답하거나 승인 버튼을 누르면, `task_boundary`를 통해 **수행(EXECUTION) 모드**로 전환하여 실제 구현을 진행하세요.
7. 로컬 파일(`.docs/task/{feature}.md`)에 정보가 없는 경우, 출력된 가이드에 따라 Jira 이슈 조회를 시도하세요.
