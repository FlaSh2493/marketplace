"""세션 분석 공통 유틸. collect_daily.py 가 사용한다."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator

SKILL_PATTERN = re.compile(r"/[\w-]+:[\w-]+")


def encode_cwd(cwd: str) -> str:
    return cwd.replace("/", "-")


def iter_jsonl(path: Path) -> Iterator[dict]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def get_session_start(entries: Iterable[dict]) -> datetime | None:
    for entry in entries:
        ts = entry.get("timestamp")
        if ts:
            try:
                return datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except ValueError:
                continue
    return None


def get_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(
            b.get("text", "") for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        )
    return ""


def extract_skill(text: str) -> str | None:
    m = SKILL_PATTERN.search(text)
    return m.group(0) if m else None


def measure_tool_results(content: list) -> tuple[int, int]:
    """(count, total_chars)."""
    count = 0
    total_chars = 0
    for block in content:
        if not isinstance(block, dict) or block.get("type") != "tool_result":
            continue
        count += 1
        inner = block.get("content", "")
        if isinstance(inner, str):
            total_chars += len(inner)
        elif isinstance(inner, list):
            for item in inner:
                if isinstance(item, dict) and item.get("type") == "text":
                    total_chars += len(item.get("text", ""))
    return count, total_chars


def compute_cache_hit_rate(usage: dict) -> float:
    """cache_read / (input + cache_read + cache_creation)."""
    if not isinstance(usage, dict):
        return 0.0
    cr = usage.get("cache_read_input_tokens", 0) or 0
    cc = usage.get("cache_creation_input_tokens", 0) or 0
    it = usage.get("input_tokens", 0) or 0
    denom = it + cr + cc
    return round(cr / denom, 3) if denom > 0 else 0.0
