#!/bin/bash
# PostToolUse Write 훅: plan 파일 저장 시 .docs/tasks/{issue}/plan.md 로 자동 복사

INPUT=$(cat)

FILE_PATH=$(echo "$INPUT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(d.get('tool_input', {}).get('file_path', ''))
" 2>/dev/null)

# ~/.claude/plans/ 하위 파일이 아니면 무시
[[ "$FILE_PATH" != *"/.claude/plans/"* ]] && exit 0
[ ! -f "$FILE_PATH" ] && exit 0

# 플랜 파일 내용에서 이슈키 추출 (**Issue**: KEY 형식)
ISSUE=$(grep -m1 '^\*\*Issue\*\*:' "$FILE_PATH" | sed 's/\*\*Issue\*\*:[[:space:]]*//' | tr -d '[:space:]')
[ -z "$ISSUE" ] && exit 0

# 워크트리 루트
GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
[ -z "$GIT_ROOT" ] && exit 0

DEST="$GIT_ROOT/.docs/tasks/$ISSUE/plan.md"

mkdir -p "$(dirname "$DEST")"
cp "$FILE_PATH" "$DEST"
