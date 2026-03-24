#!/bin/bash
# Stop hook: WIP 자동 커밋 (플래그 파일이 있을 때만 동작)
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0

# git repo인지 확인
GIT_COMMON_DIR=$(git rev-parse --git-common-dir 2>/dev/null)
[ -z "$GIT_COMMON_DIR" ] && exit 0

# 메인 저장소 루트 찾기
MAIN_ROOT=$(cd "$GIT_COMMON_DIR/.." && pwd)

# 플래그 파일 확인 (메인 저장소 루트 기준) — 없으면 아무것도 안 함
[ -f "$MAIN_ROOT/.worktrees/.wip-enabled" ] || exit 0

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
