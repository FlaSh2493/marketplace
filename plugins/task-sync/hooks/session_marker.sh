#!/usr/bin/env bash
# usage: session_marker.sh <busy|idle>
# 훅 실패해도 Claude 동작 무영향 — 항상 exit 0
set +e
state="$1"
payload="$(cat 2>/dev/null || echo '{}')"

if ! command -v jq >/dev/null 2>&1; then exit 0; fi

session_id=$(echo "$payload" | jq -r '.session_id // "unknown"' 2>/dev/null)
cwd=$(echo "$payload"       | jq -r '.cwd // ""'          2>/dev/null)
[ -z "$cwd" ] && cwd="$(pwd)"
prompt_preview=$(echo "$payload" | jq -r '.prompt // ""' 2>/dev/null | head -c 80 | tr '\n' ' ')

repo_root="$(git -C "$cwd" rev-parse --show-toplevel 2>/dev/null || echo "$cwd")"
base_dir="$repo_root/tasks"
sess_dir="$base_dir/sessions/$session_id"
mkdir -p "$sess_dir" 2>/dev/null

now_iso="$(date -Iseconds 2>/dev/null || date +%Y-%m-%dT%H:%M:%S%z)"
pid="$PPID"

if [ "$state" = "busy" ]; then
  record=$(jq -cn \
    --arg s busy --arg sid "$session_id" --arg pid "$pid" --arg cwd "$cwd" \
    --arg t "$now_iso" --arg p "$prompt_preview" \
    '{state:$s, session_id:$sid, pid:($pid|tonumber), cwd:$cwd, started:$t, prompt_preview:$p}')
  echo "$record" > "$sess_dir/status.json"
else
  prev_started=$(jq -r '.started // ""' "$sess_dir/status.json" 2>/dev/null)
  record=$(jq -cn \
    --arg s idle --arg sid "$session_id" --arg pid "$pid" --arg cwd "$cwd" \
    --arg st "$prev_started" --arg en "$now_iso" \
    '{state:$s, session_id:$sid, pid:($pid|tonumber), cwd:$cwd, started:$st, ended:$en}')
  echo "$record" > "$sess_dir/status.json"
fi

echo "$record" >> "$sess_dir/log.jsonl"
exit 0
