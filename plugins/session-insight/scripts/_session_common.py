"""세션 분석 공통 유틸. collect_filtered.py / score_and_filter.py / rollup_check.py 가 공유."""

from __future__ import annotations

import json
import re
import subprocess
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable, Iterator

SKILL_PATTERN = re.compile(r"/[\w-]+:[\w-]+")


def git_root(cwd: str | None = None) -> str | None:
    """cwd 기준 git 루트를 반환. git 저장소가 아니면 None."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd or None,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def resolve_base_root(cwd: str | None) -> Path:
    """git 루트 → cwd → 홈 순서로 session-insight 저장 경로를 결정한다."""
    root = git_root(cwd) or cwd
    base = Path(root) if root else Path.home()
    return base / ".claude" / "session-insight"


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


# ---------------------------------------------------------------------------
# 월(month-week) 기반 주차 헬퍼
#
# 정의
#   - W1 = 그 달 1일이 속한 주의 "1일~첫 일요일" (월~일 구획)
#   - W2 부터는 다음 주 월요일 시작
#   - 마지막 주는 월말 일자로 잘림 (월 경계 부분 주)
# ---------------------------------------------------------------------------

def _first_sunday(fm: date) -> date:
    """주어진 달 1일을 받아 그 달의 W1 종료일(첫 일요일, 또는 1일이 일요일이면 1일)."""
    return fm + timedelta(days=(6 - fm.weekday()) % 7)


def _last_day_of_month(y: int, m: int) -> date:
    if m == 12:
        return date(y, 12, 31)
    return date(y, m + 1, 1) - timedelta(days=1)


def month_week_of(d: date) -> tuple[str, int]:
    """주어진 날짜의 (YYYY-MM, week_of_month)."""
    fm = d.replace(day=1)
    fs = _first_sunday(fm)
    if d <= fs:
        wn = 1
    else:
        wn = 2 + ((d - fs).days - 1) // 7
    return d.strftime("%Y-%m"), wn


def last_day_of_month_week(ym: str, wn: int) -> date:
    y, m = map(int, ym.split("-"))
    fm = date(y, m, 1)
    fs = _first_sunday(fm)
    sunday = fs if wn == 1 else fs + timedelta(days=7 * (wn - 1))
    return min(sunday, _last_day_of_month(y, m))


def first_day_of_month_week(ym: str, wn: int) -> date:
    y, m = map(int, ym.split("-"))
    fm = date(y, m, 1)
    if wn == 1:
        return fm
    fs = _first_sunday(fm)
    return fs + timedelta(days=1 + 7 * (wn - 2))


def days_in_month_week(ym: str, wn: int) -> list[date]:
    first = first_day_of_month_week(ym, wn)
    last = last_day_of_month_week(ym, wn)
    return [first + timedelta(days=i) for i in range((last - first).days + 1)]


def previous_month(today: date) -> str:
    return (today.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")


def completed_missing_weeklies(today: date, base: Path) -> list[str]:
    """오늘 시점에 완결됐지만 weekly/<key>.md 가 미생성된 month-week 키 목록."""
    result: list[str] = []
    seen: set[tuple[str, int]] = set()
    for k in range(1, 11):
        d = today - timedelta(days=k)
        ym, wn = month_week_of(d)
        if (ym, wn) in seen:
            continue
        seen.add((ym, wn))
        if last_day_of_month_week(ym, wn) >= today:
            continue
        key = f"{ym}-W{wn}"
        if not (base / "weekly" / f"{key}.md").exists():
            result.append(key)
    return result


# ---------------------------------------------------------------------------
# 파일 존재 체크 (rollup_check.py / score_and_filter.py 1차 빠른 체크 공유)
# ---------------------------------------------------------------------------

def missing_daily(base: Path, d: date) -> bool:
    return not (base / "daily" / f"{d.isoformat()}.md").exists()


def missing_monthly(base: Path, ym: str) -> bool:
    return not (base / "monthly" / f"{ym}.md").exists()


def filtered_dir_exists(base: Path, d: date) -> bool:
    p = base / ".filtered" / d.isoformat()
    if not p.exists():
        return False
    try:
        return any(p.iterdir())
    except OSError:
        return False


def any_daily_in(base: Path, week_key: str) -> bool:
    ym, wn_str = week_key.rsplit("-W", 1)
    wn = int(wn_str)
    daily_dir = base / "daily"
    if not daily_dir.exists():
        return False
    for d in days_in_month_week(ym, wn):
        if (daily_dir / f"{d.isoformat()}.md").exists():
            return True
    return False


def any_weekly_in(base: Path, ym: str) -> bool:
    weekly_dir = base / "weekly"
    if not weekly_dir.exists():
        return False
    return any(weekly_dir.glob(f"{ym}-W*.md"))


def compute_cache_hit_rate(usage: dict) -> float:
    """cache_read / (input + cache_read + cache_creation)."""
    if not isinstance(usage, dict):
        return 0.0
    cr = usage.get("cache_read_input_tokens", 0) or 0
    cc = usage.get("cache_creation_input_tokens", 0) or 0
    it = usage.get("input_tokens", 0) or 0
    denom = it + cr + cc
    return round(cr / denom, 3) if denom > 0 else 0.0
