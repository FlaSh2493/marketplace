#!/bin/bash
# Edit/Write 툴 사용 시 워크트리 안인지 확인. 밖이면 차단.

GIT_DIR=$(git rev-parse --git-dir 2>/dev/null)

if [[ "$GIT_DIR" == *"worktrees"* ]]; then
  exit 0
fi

echo '{"decision":"block","reason":"[BLOCKED] 워크트리 밖에서 코드 수정 불가.\nEnterWorktree를 먼저 실행하여 워크트리에 진입하세요."}'
exit 0
