#!/usr/bin/env python3
"""
analyze_tokens.py — 세션별 스킬 토큰 사용 통계 추출.

사용법:
    python3 analyze_tokens.py <cwd> [--days N]
    python3 analyze_tokens.py <cwd> [--from YYYY-MM-DD --to YYYY-MM-DD]
    python3 analyze_tokens.py <cwd> [--all]

기본값: 최근 30일

출력: JSON (stdout)
  {
    "period": {"from": "...", "to": "..."},
    "skills": {
      "/autopilot:build": {
        "count": 12,
        "avg_input_tokens": 42000,
        "avg_output_tokens": 1800,
        "cache_hit_rate": 0.3
      }
    },
    "sessions": [
      {
        "id": "...",
        "start": "...",
        "total_tokens": 120000,
        "turns": [
          {
            "turn": 3,
            "skill": "/autopilot:build",
            "input_tokens": 52000,
            "output_tokens": 2100,
            "cache_hit_rate": 0.1,
            "user_text_length": 120,
            "tool_results_count": 4,
            "tool_results_total_chars": 18000
          }
        ]
      }
    ],
    "total": {"sessions": 15, "input_tokens": 500000, "output_tokens": 25000}
  }

스킬 감지: user 메시지 text에서 /word:word 패턴 파싱.
토큰 귀속: 스킬 호출 직후 assistant 응답의 message.usage.
cache_hit_rate: cache_read_input_tokens / input_tokens (없으면 0).
tool_results_total_chars: filter 전 원본 길이 기준 — truncated 태그에서 복원.
"""

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SKILL_PATTERN = re.compile(r"/[\w-]+:[\w-]+")
TRUNCATED_PATTERN = re.compile(r"\.\.\. \[truncated (\d+) chars\]$")


def encode_cwd(cwd: str) -> str:
    return cwd.replace("/", "-")


def parse_args():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("cwd")
    parser.add_argument("--days", type=int, default=None)
    parser.add_argument("--from", dest="from_date", default=None)
    parser.add_argument("--to", dest="to_date", default=None)
    parser.add_argument("--all", dest="all_time", action="store_true")
    return parser.parse_args()


def resolve_period(args) -> tuple[datetime | None, datetime | None]:
    now = datetime.now(timezone.utc)
    if args.all_time:
        return None, None
    if args.from_date or args.to_date:
        from_dt = datetime.fromisoformat(args.from_date).replace(tzinfo=timezone.utc) if args.from_date else None
        to_dt = datetime.fromisoformat(args.to_date).replace(tzinfo=timezone.utc) if args.to_date else now
        return from_dt, to_dt
    days = args.days if args.days else 30
    return now - timedelta(days=days), now


def get_text_from_content(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return " ".join(parts)
    return ""


def extract_skill(text: str) -> str | None:
    m = SKILL_PATTERN.search(text)
    return m.group(0) if m else None


def measure_tool_results(content: list) -> tuple[int, int]:
    """(count, total_original_chars) — truncated メッセージから元の長さを復元"""
    count = 0
    total_chars = 0
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") != "tool_result":
            continue
        count += 1
        inner = block.get("content", "")
        if isinstance(inner, str):
            m = TRUNCATED_PATTERN.search(inner)
            if m:
                total_chars += int(m.group(1))
            else:
                total_chars += len(inner)
        elif isinstance(inner, list):
            for item in inner:
                if isinstance(item, dict) and item.get("type") == "text":
                    text = item.get("text", "")
                    m = TRUNCATED_PATTERN.search(text)
                    total_chars += int(m.group(1)) if m else len(text)
    return count, total_chars


def parse_session(path: Path) -> list[dict]:
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def get_session_start(entries: list[dict]) -> datetime | None:
    for entry in entries:
        ts = entry.get("timestamp")
        if ts:
            try:
                return datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                continue
    return None


def analyze_session(session_id: str, entries: list[dict]) -> dict:
    turns = []
    turn_num = 0
    pending_skill = None
    pending_user_text_len = 0
    pending_tool_count = 0
    pending_tool_chars = 0

    for entry in entries:
        t = entry.get("type", "")
        if t == "user":
            msg = entry.get("message", {})
            content = msg.get("content", [])
            text = get_text_from_content(content)
            skill = extract_skill(text)
            tc, tch = measure_tool_results(content) if isinstance(content, list) else (0, 0)

            turn_num += 1
            pending_skill = skill
            pending_user_text_len = len(text)
            pending_tool_count = tc
            pending_tool_chars = tch

        elif t == "assistant":
            msg = entry.get("message", {})
            usage = msg.get("usage") or {}
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            cache_read = usage.get("cache_read_input_tokens", 0)
            cache_hit_rate = round(cache_read / input_tokens, 3) if input_tokens > 0 else 0.0

            turns.append({
                "turn": turn_num,
                "skill": pending_skill,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_hit_rate": cache_hit_rate,
                "user_text_length": pending_user_text_len,
                "tool_results_count": pending_tool_count,
                "tool_results_total_chars": pending_tool_chars,
            })
            pending_skill = None
            pending_user_text_len = 0
            pending_tool_count = 0
            pending_tool_chars = 0

    total_tokens = sum(t["input_tokens"] + t["output_tokens"] for t in turns)
    start_dt = get_session_start(entries)

    return {
        "id": session_id,
        "start": start_dt.isoformat() if start_dt else None,
        "total_tokens": total_tokens,
        "turns": turns,
    }


def aggregate_skills(sessions: list[dict]) -> dict:
    skill_data: dict[str, dict] = {}
    for session in sessions:
        for turn in session["turns"]:
            skill = turn.get("skill") or "__none__"
            if skill not in skill_data:
                skill_data[skill] = {"count": 0, "input_sum": 0, "output_sum": 0, "cache_sum": 0}
            d = skill_data[skill]
            d["count"] += 1
            d["input_sum"] += turn["input_tokens"]
            d["output_sum"] += turn["output_tokens"]
            d["cache_sum"] += turn["cache_hit_rate"]

    result = {}
    for skill, d in skill_data.items():
        if skill == "__none__":
            continue
        c = d["count"]
        result[skill] = {
            "count": c,
            "avg_input_tokens": round(d["input_sum"] / c) if c else 0,
            "avg_output_tokens": round(d["output_sum"] / c) if c else 0,
            "cache_hit_rate": round(d["cache_sum"] / c, 3) if c else 0.0,
        }
    return result


def main():
    args = parse_args()
    from_dt, to_dt = resolve_period(args)

    encoded = encode_cwd(args.cwd)
    projects_dir = Path.home() / ".claude" / "projects" / encoded

    if not projects_dir.exists():
        print(json.dumps({"error": f"projects dir not found: {projects_dir}"}))
        sys.exit(1)

    filtered_files = sorted(projects_dir.glob("*.filtered.jsonl"))
    if not filtered_files:
        print(json.dumps({"error": "no .filtered.jsonl files found — run a session first"}))
        sys.exit(1)

    sessions = []
    for path in filtered_files:
        session_id = path.stem.replace(".filtered", "")
        entries = parse_session(path)
        if not entries:
            continue

        start = get_session_start(entries)
        if start:
            if from_dt and start < from_dt:
                continue
            if to_dt and start > to_dt:
                continue

        sessions.append(analyze_session(session_id, entries))

    skills = aggregate_skills(sessions)

    total_input = sum(t["input_tokens"] for s in sessions for t in s["turns"])
    total_output = sum(t["output_tokens"] for s in sessions for t in s["turns"])

    period_from = from_dt.date().isoformat() if from_dt else "all"
    period_to = to_dt.date().isoformat() if to_dt else "all"

    output = {
        "period": {"from": period_from, "to": period_to},
        "skills": skills,
        "sessions": sessions,
        "total": {
            "sessions": len(sessions),
            "input_tokens": total_input,
            "output_tokens": total_output,
        },
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
