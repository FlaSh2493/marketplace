#!/bin/bash
# Stop hook: WIP 자동 커밋 (플래그 파일이 있을 때만 동작)
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0

# 플래그 파일 확인 — 없으면 아무것도 안 함
[ -f .worktrees/.wip-enabled ] || exit 0

# git repo인지 확인
git rev-parse --git-dir > /dev/null 2>&1 || exit 0

# 변경사항 확인
if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
  exit 0
fi

# 변경 요약 생성
STAT=$(git diff --stat --cached 2>/dev/null; git diff --stat 2>/dev/null)
SUMMARY=$(echo "$STAT" | tail -1 | sed 's/^ *//')
[ -z "$SUMMARY" ] && SUMMARY="uncommitted changes"

git add -A
git commit -m "WIP: $SUMMARY" --no-verify > /dev/null 2>&1
