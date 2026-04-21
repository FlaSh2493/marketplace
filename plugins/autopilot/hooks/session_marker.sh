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
# 어느 워크트리에서 실행해도 항상 메인 레포의 루트를 찾아 중앙에서 관리하도록 함
main_root="$(git -C "$repo_root" worktree list --porcelain | grep "^worktree " | head -n 1 | cut -d' ' -f2-)"
[ -z "$main_root" ] && main_root="$repo_root"

wt_name="$(basename "$repo_root")"
base_dir="$main_root/tasks/.state"
sess_file="$base_dir/sessions/$wt_name.json"
mkdir -p "$base_dir/sessions" "$base_dir/by-pid" 2>/dev/null

now_iso="$(date -Iseconds 2>/dev/null || date +%Y-%m-%dT%H:%M:%S%z)"
pid="$PPID"

if [ "$state" = "busy" ]; then
  record=$(jq -cn \
    --arg s busy --arg sid "$session_id" --arg pid "$pid" --arg cwd "$cwd" \
    --arg t "$now_iso" --arg p "$prompt_preview" \
    '{state:$s, session_id:$sid, pid:($pid|tonumber), cwd:$cwd, started:$t, prompt_preview:$p}')
  echo "$record" > "$sess_file"
  echo "$session_id" > "$base_dir/by-pid/$pid.id"
  ln -sfn "sessions/$wt_name.json" "$base_dir/current"
else
  prev_started=$(jq -r '.started // ""' "$sess_file" 2>/dev/null)
  record=$(jq -cn \
    --arg s idle --arg sid "$session_id" --arg pid "$pid" --arg cwd "$cwd" \
    --arg st "$prev_started" --arg en "$now_iso" \
    '{state:$s, session_id:$sid, pid:($pid|tonumber), cwd:$cwd, started:$st, ended:$en}')
  echo "$record" > "$sess_file"
fi

echo "$record" >> "${sess_file}.log"
exit 0
