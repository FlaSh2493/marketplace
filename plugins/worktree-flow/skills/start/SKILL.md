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

1. 스크립트 결과로 목록(`mode: selection`)이 나오면:
   - **반드시 `AskUserQuestion`을 사용하여 사용자에게 작업 항목 또는 워크트리 목록을 보여주세요.**
   - 사용자가 선택한 결과를 인자로 하여 다시 기능을 수행하게 하세요.

2. 선택된 워크트리(또는 현재 워크트리)의 기획 정보가 로드되면:
   - 해당 내용을 `task.md`에 기록하고, 해당 워크트리에서 자동 WIP 커밋이 동작하도록 **`.wip-active` 파일을 생성**하세요. (`touch .wip-active`)
   - `task_boundary`를 통해 **기획(PLANNING) 모드**로 진입하세요.

3. 기획이 확정되면(승인 요청 전), 해당 내용을 **`.docs/task/{feature}.md`** 파일에 저장하세요.
   - `{feature}`는 현재 브랜치명에서 워크트리 suffix(`--wt-XXXX`)를 제거한 값입니다. (예: `qa/data-center-bug--wt-IET-7571` → `{feature}`: `qa/data-center-bug`)
   - 파일 내 해당 이슈(`jira: IET-XXXX`)의 작업 항목 아래에 **`### 플랜`** 섹션을 추가하거나 업데이트하세요.
   - 새로운 플랜이 작성될 때마다 해당 섹션을 덮어씁니다.
4. 수립된 기획안(`implementation_plan.md`)의 내용을 **마크다운 텍스트로 채팅창에 출력**하여 사용자가 즉시 확인할 수 있게 하세요.
5. `notify_user(BlockedOnUser: true)`를 호출하여 사용자가 승인 버튼을 통해 구현을 시작할 수 있게 하세요.
   - 플랜 승인은 반드시 `notify_user`를 통한 **승인 버튼**으로만 받으세요. 채팅(`AskUserQuestion` 등)으로 승인을 묻지 마세요.
6. 사용자가 **'build'** 라고 답하거나 승인 버튼을 누르면, `task_boundary`를 통해 **수행(EXECUTION) 모드**로 전환하여 실제 구현을 진행하세요.
7. 로컬 파일(`.docs/task/{feature}.md`)에 정보가 없는 경우, 출력된 가이드에 따라 Jira 이슈 조회를 시도하세요.

## 알림 (처음 사용하는 경우)

워크트리를 처음 시작했거나 훅을 등록하지 않은 경우, 다음을 안내하세요:

1. **훅 등록**: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/install_hooks.py` 명령을 실행하여 Stop 훅을 등록해야 합니다.
2. **WIP 활성화**: 훅 등록 후, `/worktree-flow:wip on` 명령을 실행해야 자동 WIP 커밋이 활성화됩니다.
   - 훅만 등록된 상태에서는 WIP 커밋이 생성되지 않으므로, 명시적으로 `wip on`을 해야 함을 강조하세요.
