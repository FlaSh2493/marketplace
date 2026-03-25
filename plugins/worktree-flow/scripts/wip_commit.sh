#!/bin/bash
# WIP Commit — 현재 워크트리만 처리 (Stop 훅 또는 build 스킬에서 직접 호출)

# 1. 글로벌 스위치 확인
CONFIG_FILE=".claude/worktree-flow.json"
if [ -f "$CONFIG_FILE" ]; then
    ENABLED=$(jq -r '.wip_enabled // "true"' "$CONFIG_FILE" 2>/dev/null)
    [ "$ENABLED" == "false" ] && exit 0
fi

# 2. 현재 워크트리 루트 확인
WT_PATH=$(git rev-parse --show-toplevel 2>/dev/null)
[ -z "$WT_PATH" ] && exit 0

# 3. .wip-active 확인 (이 워크트리에서만)
[ ! -f "$WT_PATH/.wip-active" ] && exit 0

# 4. 변경사항 확인
if git -C "$WT_PATH" diff --quiet && \
   git -C "$WT_PATH" diff --cached --quiet && \
   [ -z "$(git -C "$WT_PATH" ls-files --others --exclude-standard 2>/dev/null)" ]; then
    exit 0
fi

# 5. 현재 브랜치명
BRANCH=$(git -C "$WT_PATH" rev-parse --abbrev-ref HEAD 2>/dev/null)
[ -z "$BRANCH" ] && BRANCH="unknown"

# 6. WIP 커밋
TIMESTAMP=$(date +%Y-%m-%dT%H:%M:%S)
git -C "$WT_PATH" add -A
git -C "$WT_PATH" commit -m "WIP($BRANCH): $TIMESTAMP" --no-verify > /dev/null 2>&1
