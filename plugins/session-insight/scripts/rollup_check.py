#!/usr/bin/env python3
"""
rollup_check.py — score_and_filter.py 가 detach 로 실행하는 백그라운드 오케스트레이터.

역할
----
1. _session_common 헬퍼로 누락된 daily/weekly/monthly 키를 재계산
2. 각 tier 에 대해 `claude -p /session-insight:<tier> <key>` 를 동기 직렬 실행
3. 의존 파일이 없으면 스킵, 실패 시 `.failed-<key>` 마커 touch (24h 차단)

자체 LLM 호출은 없다 — 모든 분석은 스킬 안에서 수행.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import date as date_cls, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _session_common import (  # noqa: E402
    any_daily_in,
    any_weekly_in,
    completed_missing_weeklies,
    filtered_dir_exists,
    missing_daily,
    missing_monthly,
    previous_month,
)

TIMEOUTS = {"daily": 180, "weekly": 120, "monthly": 120}
FAIL_TTL = int(os.environ.get("SESSION_INSIGHT_FAIL_TTL", "86400"))


def attempt_tier(tier: str, key: str, base: Path, cwd: str) -> None:
    target = base / tier / f"{key}.md"
    failed = base / tier / f".failed-{key}"

    if target.exists():
        return
    if failed.exists() and (time.time() - failed.stat().st_mtime) < FAIL_TTL:
        return

    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        rc = subprocess.run(
            ["claude", "-p", f"/session-insight:{tier} {key}"],
            timeout=TIMEOUTS[tier],
            cwd=cwd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )
        if rc.returncode != 0 or not target.exists():
            failed.touch()
    except subprocess.TimeoutExpired:
        failed.touch()
    except FileNotFoundError:
        # claude CLI 가 PATH 에 없음 — 마커는 남기지 않음 (환경 문제)
        return
    except Exception:
        failed.touch()


def main() -> int:
    if len(sys.argv) < 2:
        return 0
    cwd = sys.argv[1]
    base = Path(cwd) / ".claude" / "session-insight"
    if not base.exists():
        return 0

    today = date_cls.today()
    yesterday = today - timedelta(days=1)

    # daily — 어제자
    if filtered_dir_exists(base, yesterday) and missing_daily(base, yesterday):
        attempt_tier("daily", yesterday.isoformat(), base, cwd)

    # weekly — 완결됐지만 미생성된 month-week (보통 0~2개)
    for week_key in completed_missing_weeklies(today, base):
        if any_daily_in(base, week_key):
            attempt_tier("weekly", week_key, base, cwd)

    # monthly — 직전 월 (자동 완결)
    prev_m = previous_month(today)
    if missing_monthly(base, prev_m) and any_weekly_in(base, prev_m):
        attempt_tier("monthly", prev_m, base, cwd)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
