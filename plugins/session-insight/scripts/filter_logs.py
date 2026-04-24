#!/usr/bin/env python3
"""
filter_logs.py — SessionStop 훅에서 자동 실행.

stdin: {"session_id": "...", "cwd": "..."}
출력: ~/.claude/projects/<encoded-cwd>/<session_id>.filtered.jsonl

필터 기준:
  KEEP:
    - type == "user"
        → message.content 내 tool_result 항목: content 500자 초과 시 truncate
    - type == "assistant"
        → message.content에서 type=="thinking" 블록 제거
        → text 또는 tool_use 블록이 남아있어야 보존
        → message.usage는 항상 보존
    - type == "attachment" AND attachment.type == "hook_failure"

  DROP:
    - type == "queue-operation"
    - type == "file-history-snapshot"
    - type == "ai-title"
    - type == "last-prompt"
    - type == "attachment" AND attachment.type in:
        ["deferred_tools_delta", "hook_success", "mcp_instructions_delta",
         "todo_reminder", "skill_listing"]
"""

import json
import sys
import os
from pathlib import Path

TOOL_RESULT_MAX_CHARS = 500

DROP_TYPES = {"queue-operation", "file-history-snapshot", "ai-title", "last-prompt"}

DROP_ATTACHMENT_TYPES = {
    "deferred_tools_delta",
    "hook_success",
    "mcp_instructions_delta",
    "todo_reminder",
    "skill_listing",
}


def encode_cwd(cwd: str) -> str:
    """'/Users/madup/my/project' → '-Users-madup-my-project'"""
    return cwd.replace("/", "-")


def truncate_tool_results(content: list) -> list:
    result = []
    for block in content:
        if not isinstance(block, dict):
            result.append(block)
            continue
        if block.get("type") == "tool_result":
            block = dict(block)
            inner = block.get("content")
            if isinstance(inner, str) and len(inner) > TOOL_RESULT_MAX_CHARS:
                block["content"] = inner[:TOOL_RESULT_MAX_CHARS] + f"... [truncated {len(inner)} chars]"
            elif isinstance(inner, list):
                new_inner = []
                for item in inner:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text = item.get("text", "")
                        if len(text) > TOOL_RESULT_MAX_CHARS:
                            item = dict(item)
                            item["text"] = text[:TOOL_RESULT_MAX_CHARS] + f"... [truncated {len(text)} chars]"
                    new_inner.append(item)
                block["content"] = new_inner
        result.append(block)
    return result


def filter_assistant(entry: dict) -> dict | None:
    """thinking 블록 제거 후 text/tool_use가 없으면 None 반환."""
    msg = entry.get("message", {})
    content = msg.get("content")
    if not isinstance(content, list):
        return entry

    filtered = [b for b in content if not (isinstance(b, dict) and b.get("type") == "thinking")]
    has_substance = any(
        isinstance(b, dict) and b.get("type") in ("text", "tool_use")
        for b in filtered
    )
    if not has_substance:
        return None

    entry = dict(entry)
    entry["message"] = dict(msg)
    entry["message"]["content"] = filtered
    return entry


def should_drop(entry: dict) -> bool:
    t = entry.get("type", "")
    if t in DROP_TYPES:
        return True
    if t == "attachment":
        att_type = entry.get("attachment", {}).get("type", "")
        if att_type in DROP_ATTACHMENT_TYPES:
            return True
    return False


def filter_entry(entry: dict) -> dict | None:
    if should_drop(entry):
        return None

    t = entry.get("type", "")

    if t == "user":
        msg = entry.get("message", {})
        content = msg.get("content")
        if isinstance(content, list):
            entry = dict(entry)
            entry["message"] = dict(msg)
            entry["message"]["content"] = truncate_tool_results(content)
        return entry

    if t == "assistant":
        return filter_assistant(entry)

    return entry


def main():
    raw = sys.stdin.read().strip()
    if not raw:
        sys.exit(0)

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        sys.exit(0)

    session_id = payload.get("session_id", "")
    cwd = payload.get("cwd", "")

    if not session_id or not cwd:
        sys.exit(0)

    encoded = encode_cwd(cwd)
    projects_dir = Path.home() / ".claude" / "projects" / encoded
    source_path = projects_dir / f"{session_id}.jsonl"
    output_path = projects_dir / f"{session_id}.filtered.jsonl"

    if not source_path.exists():
        sys.exit(0)

    kept = 0
    dropped = 0

    with open(source_path, "r", encoding="utf-8") as fin, \
         open(output_path, "w", encoding="utf-8") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            filtered = filter_entry(entry)
            if filtered is not None:
                fout.write(json.dumps(filtered, ensure_ascii=False) + "\n")
                kept += 1
            else:
                dropped += 1

    total = kept + dropped
    ratio = (dropped / total * 100) if total > 0 else 0
    print(
        f"[session-insight] filtered {session_id}: "
        f"{kept} kept / {dropped} dropped ({ratio:.0f}% reduced) → {output_path.name}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
