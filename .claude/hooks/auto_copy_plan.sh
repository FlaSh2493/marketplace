#!/bin/bash
# PostToolUse 훅: plan mode 파일 수정 시 tasks/{issue}/plan.md로 자동 복사

INPUT=$(cat)

# 파일 경로 추출
FILE_PATH=$(echo "$INPUT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(d.get('tool_input', {}).get('file_path', ''))
" 2>/dev/null)

# ~/.claude/plans/ 하위 파일이 아니면 무시
[[ "$FILE_PATH" != *"/.claude/plans/"* ]] && exit 0

# plan_sync.json에서 목적지 경로 읽기
GIT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
SYNC_FILE="$GIT_ROOT/tasks/plan_sync.json"

[ ! -f "$SYNC_FILE" ] && exit 0

DEST=$(python3 -c "
import json, sys
d = json.load(open(sys.argv[1]))
print(d.get('dest', ''))
" "$SYNC_FILE" 2>/dev/null)

[ -z "$DEST" ] && exit 0

mkdir -p "$(dirname "$DEST")"
cp "$FILE_PATH" "$DEST"
