#!/usr/bin/env bash
# WIP Commit — 워크트리 자동 감지, claude -p로 상세 커밋 메시지 생성

set -euo pipefail

WT=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0

# 메인 리포면 스킵
MAIN=$(git worktree list --porcelain 2>/dev/null | awk '/^worktree /{print $2; exit}')
[ "$WT" = "$MAIN" ] && exit 0

cd "$WT" || exit 0

git add -A 2>/dev/null || true

# 변경사항 없으면 스킵
if git diff-index --quiet HEAD 2>/dev/null; then
  exit 0
fi

BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
DIFF=$(git diff --cached 2>/dev/null | head -300)

# claude -p로 커밋 메시지 생성
COMMIT_MSG=""
if command -v claude &>/dev/null; then
  COMMIT_MSG=$(echo "$DIFF" | claude -p \
    "You are a WIP commit message generator for a worktree-based dev workflow.
Based on the following git diff, write a single commit message.

Rules:
- First line MUST be: WIP($BRANCH): <short summary> (max 72 chars)
- Add a blank line, then include:
  - 요구사항: why this change was needed / what was requested
  - 작업내용: what was actually changed (per file if helpful)
  - 특이사항: any notable decisions, tradeoffs, or constraints
- Be specific and detailed enough to reconstruct the plan without a separate doc
- Output ONLY the commit message, nothing else" 2>/dev/null) || true
fi

# claude -p 실패 시 fallback
if [ -z "$COMMIT_MSG" ]; then
  FILE_COUNT=$(git diff --cached --name-only | wc -l | tr -d ' ')
  COMMIT_MSG="WIP($BRANCH): update $FILE_COUNT files"
fi

echo "$COMMIT_MSG" | git commit -F - --no-verify 2>/dev/null || true
