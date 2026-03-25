#!/bin/bash
# WIP Commit — 워크트리 자동 감지, 플래그 파일 불필요

WT=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0

# 메인 리포면 스킵
MAIN=$(git worktree list --porcelain 2>/dev/null | awk '/^worktree /{print $2; exit}')
[ "$WT" = "$MAIN" ] && exit 0

# 변경사항 없으면 스킵
git -C "$WT" diff --quiet && \
  git -C "$WT" diff --cached --quiet && \
  [ -z "$(git -C "$WT" ls-files --others --exclude-standard 2>/dev/null)" ] && exit 0

BRANCH=$(git -C "$WT" rev-parse --abbrev-ref HEAD 2>/dev/null)
git -C "$WT" add -A
git -C "$WT" commit -m "WIP($BRANCH): $(date +%H:%M:%S)" --no-verify > /dev/null 2>&1
