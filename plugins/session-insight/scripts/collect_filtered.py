#!/usr/bin/env python3
"""
collect_filtered.py — `.filtered/` 디렉토리의 세션을 한 번 훑어 구조화 markdown 출력.

스킬에서 호출:
    collect_filtered.py <cwd> --tier daily   --date 2026-04-27
    collect_filtered.py <cwd> --tier weekly  --week 2026-W17
    collect_filtered.py <cwd> --tier monthly --month 2026-04
    collect_filtered.py <cwd> --tier rollup  --from 2026-04-01 --to 2026-04-27

읽기:
    ~/.claude/projects/<encoded-cwd>/.filtered/index.jsonl   (모든 세션 메타)
    ~/.claude/projects/<encoded-cwd>/.filtered/<sid>.jsonl   (kept=true 본문)

출력: stdout markdown. 스킬이 그대로 입력으로 사용한다.
스크립트 책임은 결정적 산술·정렬·드롭 통계뿐. 정성 요약은 LLM 단계에서.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import date as date_cls, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _session_common import (  # noqa: E402
    compute_cache_hit_rate,
    encode_cwd,
    extract_skill,
    get_text,
    iter_jsonl,
    measure_tool_results,
    resolve_base_root,
)

USER_PREVIEW_CHARS = 300
DIRECT_INPUT_PREVIEW_CHARS = 100
HEAVY_TURNS_PER_SESSION = 5


# ---------------------------------------------------------------------------
# 인덱스 / 날짜 범위
# ---------------------------------------------------------------------------

def read_index(index_path: Path) -> list[dict]:
    if not index_path.exists():
        return []
    out = []
    for entry in iter_jsonl(index_path):
        out.append(entry)
    return out


def iso_week_range(label: str) -> tuple[date_cls, date_cls]:
    y_str, w_str = label.split("-W")
    y, w = int(y_str), int(w_str)
    monday = date_cls.fromisocalendar(y, w, 1)
    sunday = monday + timedelta(days=6)
    return monday, sunday


def month_range(label: str) -> tuple[date_cls, date_cls]:
    y, m = map(int, label.split("-"))
    first = date_cls(y, m, 1)
    if m == 12:
        last = date_cls(y, 12, 31)
    else:
        last = date_cls(y, m + 1, 1) - timedelta(days=1)
    return first, last


def parse_index_date(s: str) -> date_cls | None:
    if not s:
        return None
    try:
        return date_cls.fromisoformat(s[:10])
    except ValueError:
        return None


def filter_index_by_range(index: list[dict], start: date_cls, end: date_cls) -> list[dict]:
    out = []
    for r in index:
        d = parse_index_date(r.get("date", ""))
        if d and start <= d <= end:
            out.append(r)
    return out


# ---------------------------------------------------------------------------
# 세션 분석 (필터된 jsonl 기반 — thinking 은 이미 제거되어 있음)
# ---------------------------------------------------------------------------

def analyze_session(session_id: str, path: Path) -> dict:
    turns: list[dict] = []
    turn_num = 0
    pending: dict = {}
    first_ts = None

    for entry in iter_jsonl(path):
        if first_ts is None and entry.get("timestamp"):
            first_ts = entry.get("timestamp")
        t = entry.get("type", "")

        if t == "user":
            msg = entry.get("message", {})
            content = msg.get("content", [])
            text = get_text(content)
            skill = extract_skill(text) if text else None
            tc, tch = measure_tool_results(content) if isinstance(content, list) else (0, 0)
            turn_num += 1
            pending = {
                "skill": skill,
                "user_text": text,
                "tool_count": tc,
                "tool_chars": tch,
            }

        elif t == "assistant":
            msg = entry.get("message", {})
            content = msg.get("content", [])
            usage = msg.get("usage") or {}

            tool_uses: list[str] = []
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        tool_uses.append(block.get("name", ""))

            user_text = pending.get("user_text", "") or ""
            turns.append({
                "turn": turn_num,
                "skill": pending.get("skill"),
                "user_text": user_text,
                "input_tokens": usage.get("input_tokens", 0) or 0,
                "output_tokens": usage.get("output_tokens", 0) or 0,
                "cache_hit": compute_cache_hit_rate(usage),
                "tool_count": pending.get("tool_count", 0),
                "tool_chars": pending.get("tool_chars", 0),
                "tool_uses": tool_uses,
            })
            pending = {}

    start_iso = None
    if first_ts:
        try:
            start_iso = datetime.fromisoformat(first_ts.replace("Z", "+00:00")).isoformat()
        except ValueError:
            pass

    return {
        "id": session_id,
        "start": start_iso,
        "turn_count": len(turns),
        "input_tokens_total": sum(t["input_tokens"] for t in turns),
        "output_tokens_total": sum(t["output_tokens"] for t in turns),
        "turns": turns,
    }


# ---------------------------------------------------------------------------
# 집계
# ---------------------------------------------------------------------------

def aggregate_skills(sessions: list[dict]) -> list[dict]:
    agg: dict[str, dict] = defaultdict(lambda: {"count": 0, "in_sum": 0, "out_sum": 0, "cache_sum": 0.0})
    for s in sessions:
        for t in s["turns"]:
            sk = t["skill"] or "__direct__"
            d = agg[sk]
            d["count"] += 1
            d["in_sum"] += t["input_tokens"]
            d["out_sum"] += t["output_tokens"]
            d["cache_sum"] += t["cache_hit"]
    rows = [
        {
            "skill": sk,
            "count": d["count"],
            "avg_input": d["in_sum"] // max(d["count"], 1),
            "avg_output": d["out_sum"] // max(d["count"], 1),
            "cache_hit": round(d["cache_sum"] / max(d["count"], 1), 3),
            "total_input": d["in_sum"],
        }
        for sk, d in agg.items()
    ]
    rows.sort(key=lambda r: -r["total_input"])
    return rows


def select_heavy_turns(session: dict) -> list[dict]:
    if not session["turns"]:
        return []
    keys = ("input_tokens", "output_tokens", "tool_chars")
    selected: dict[int, dict] = {}
    for k in keys:
        for t in sorted(session["turns"], key=lambda x: -x[k])[:HEAVY_TURNS_PER_SESSION]:
            if t[k] > 0:
                selected.setdefault(t["turn"], t)
    return sorted(selected.values(), key=lambda t: t["turn"])


def collect_direct_inputs(sessions: list[dict]) -> list[dict]:
    out = []
    for s in sessions:
        for t in s["turns"]:
            if t.get("skill"):
                continue
            ut = (t.get("user_text") or "").strip()
            if not ut:
                continue
            out.append({
                "session_id": s["id"],
                "turn": t["turn"],
                "preview": ut[:DIRECT_INPUT_PREVIEW_CHARS],
                "full_len": len(ut),
                "input_tokens": t.get("input_tokens", 0),
            })
    return out


def short_id(sid: str) -> str:
    return sid.split("-", 1)[0] if "-" in sid else sid[:8]


# ---------------------------------------------------------------------------
# Markdown 렌더링
# ---------------------------------------------------------------------------

def signal_summary(records: list[dict]) -> dict:
    """index.jsonl 메타 기반 양적 시그널 (드롭 세션 포함)."""
    total = len(records)
    kept = sum(1 for r in records if r.get("kept"))
    dropped = total - kept
    score_buckets: dict[str, int] = defaultdict(int)
    for r in records:
        s = int(r.get("score", 0) or 0)
        bucket = "high(7+)" if s >= 7 else "mid(3-6)" if s >= 3 else "low(<3)"
        score_buckets[bucket] += 1
    edits_total = sum(int((r.get("signals") or {}).get("edits", 0) or 0) for r in records)
    abort_total = sum(1 for r in records if (r.get("signals") or {}).get("abort"))
    error_retry_total = sum(1 for r in records if (r.get("signals") or {}).get("error_retry"))
    return {
        "total": total,
        "kept": kept,
        "dropped": dropped,
        "buckets": dict(score_buckets),
        "edits_total": edits_total,
        "abort_total": abort_total,
        "error_retry_total": error_retry_total,
    }


def render(title: str, records: list[dict], sessions: list[dict]) -> str:
    out: list[str] = []
    out.append(f"# {title}")
    out.append("")

    sig = signal_summary(records)
    total_in = sum(s["input_tokens_total"] for s in sessions)
    total_out = sum(s["output_tokens_total"] for s in sessions)

    out.append(
        f"필터 통과 {sig['kept']}/{sig['total']} (드롭 {sig['dropped']}) | "
        f"input {total_in:,} | output {total_out:,} | "
        f"점수분포 {sig['buckets']} | edits {sig['edits_total']} | "
        f"abort {sig['abort_total']} | error_retry {sig['error_retry_total']}"
    )
    out.append("")

    # 드롭된 세션 메타 (양적 시그널 보존)
    dropped_recs = [r for r in records if not r.get("kept")]
    if dropped_recs:
        out.append("## 드롭된 세션 (메타만)")
        out.append("")
        out.append("| session | date | score | tools | duration_min | edits | bash | prompts |")
        out.append("|---------|------|-------|-------|--------------|-------|------|---------|")
        for r in dropped_recs:
            sg = r.get("signals") or {}
            out.append(
                f"| `{short_id(r.get('session_id',''))}` | {r.get('date','')} | "
                f"{r.get('score','')} | {sg.get('tools',0)} | {sg.get('duration_min',0)} | "
                f"{sg.get('edits',0)} | {sg.get('bash',0)} | {sg.get('prompts',0)} |"
            )
        out.append("")

    if not sessions:
        out.append("## 본문")
        out.append("")
        out.append("필터 통과 세션이 없습니다.")
        out.append("")
        return "\n".join(out)

    # 통과 세션 목록
    out.append("## 세션 목록 (필터 통과)")
    out.append("")
    out.append("| id | start | turns | input | output | score |")
    out.append("|----|-------|-------|-------|--------|-------|")
    score_by_id = {r.get("session_id"): r.get("score", "") for r in records}
    for s in sessions:
        out.append(
            f"| `{short_id(s['id'])}` | {s['start'] or '—'} | {s['turn_count']} | "
            f"{s['input_tokens_total']:,} | {s['output_tokens_total']:,} | "
            f"{score_by_id.get(s['id'], '')} |"
        )
    out.append("")

    # 스킬별 집계
    out.append("## 스킬별 집계")
    out.append("")
    out.append("| skill | count | avg input | avg output | cache hit | total input |")
    out.append("|-------|-------|-----------|------------|-----------|-------------|")
    for r in aggregate_skills(sessions):
        label = "직접입력" if r["skill"] == "__direct__" else r["skill"]
        out.append(
            f"| {label} | {r['count']} | {r['avg_input']:,} | {r['avg_output']:,} | "
            f"{r['cache_hit']:.0%} | {r['total_input']:,} |"
        )
    out.append("")

    # 고부하 turn (세션별)
    out.append("## 고부하 turn (다지표 union Top 5/세션)")
    out.append("")
    for s in sessions:
        heavy = select_heavy_turns(s)
        if not heavy:
            continue
        out.append(f"### `{short_id(s['id'])}` — {s['turn_count']} turns")
        out.append("")
        for t in heavy:
            sk = t["skill"] or "직접입력"
            out.append(
                f"#### turn {t['turn']} | {sk} | in {t['input_tokens']:,} / out {t['output_tokens']:,} "
                f"| cache {t['cache_hit']:.0%} | tools {len(t['tool_uses'])} | tool_chars {t['tool_chars']:,}"
            )
            if t["tool_uses"]:
                out.append("")
                out.append(f"tool_uses: {', '.join(t['tool_uses'])}")
            user_text = (t["user_text"] or "").strip()
            if user_text:
                preview = user_text[:USER_PREVIEW_CHARS]
                trailing = "" if len(user_text) <= USER_PREVIEW_CHARS else f" …[총 {len(user_text)}자]"
                out.append("")
                out.append("user_text:")
                out.append("```")
                out.append(preview + trailing)
                out.append("```")
            out.append("")

    # 직접입력
    direct = collect_direct_inputs(sessions)
    out.append("## 직접입력 (스킬 호출 없이 들어간 user_text)")
    out.append("")
    if not direct:
        out.append("해당 없음")
    else:
        out.append("| session | turn | input tokens | full len | preview |")
        out.append("|---------|------|--------------|----------|---------|")
        for d in direct:
            preview = d["preview"].replace("|", "\\|").replace("\n", " ")
            out.append(
                f"| `{short_id(d['session_id'])}` | {d['turn']} | "
                f"{d['input_tokens']:,} | {d['full_len']} | {preview} |"
            )
    out.append("")

    return "\n".join(out)


# ---------------------------------------------------------------------------
# tier별 처리
# ---------------------------------------------------------------------------

def resolve_range(args) -> tuple[date_cls, date_cls, str]:
    if args.tier == "daily":
        d = date_cls.fromisoformat(args.date)
        return d, d, f"일간: {d.isoformat()}"
    if args.tier == "weekly":
        a, b = iso_week_range(args.week)
        return a, b, f"주간: {args.week} ({a.isoformat()} ~ {b.isoformat()})"
    if args.tier == "monthly":
        a, b = month_range(args.month)
        return a, b, f"월간: {args.month}"
    if args.tier == "rollup":
        a = date_cls.fromisoformat(args.frm)
        b = date_cls.fromisoformat(args.to)
        if a > b:
            a, b = b, a
        return a, b, f"통합 rollup: {a.isoformat()} ~ {b.isoformat()}"
    raise ValueError(f"알 수 없는 tier: {args.tier}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cwd")
    parser.add_argument("--tier", required=True, choices=["daily", "weekly", "monthly", "rollup"])
    parser.add_argument("--date")
    parser.add_argument("--week")
    parser.add_argument("--month")
    parser.add_argument("--from", dest="frm")
    parser.add_argument("--to")
    args = parser.parse_args()

    needs = {"daily": ["date"], "weekly": ["week"], "monthly": ["month"], "rollup": ["frm", "to"]}
    for k in needs[args.tier]:
        if not getattr(args, k):
            print(f"--{k if k != 'frm' else 'from'} 필요 (tier={args.tier})", file=sys.stderr)
            sys.exit(2)

    start, end, title = resolve_range(args)

    base = resolve_base_root(args.cwd) / ".filtered"
    index_path = base / "index.jsonl"
    if not base.exists() or not index_path.exists():
        print(f"# {title}\n\n.filtered 인덱스 없음: {index_path}\n\nSessionStop 훅이 한 번 이상 실행되어야 합니다.")
        return

    index = read_index(index_path)
    in_range = filter_index_by_range(index, start, end)

    if not in_range:
        print(f"# {title}\n\n해당 범위에 인덱스 항목이 없습니다.")
        return

    sessions: list[dict] = []
    for r in in_range:
        if not r.get("kept"):
            continue
        sid = r.get("session_id", "")
        if not sid:
            continue
        path = base / r.get("date", "") / f"{sid}.jsonl"
        if not path.exists():
            continue
        sessions.append(analyze_session(sid, path))

    sessions = [s for s in sessions if s["turn_count"] > 0]
    sessions.sort(key=lambda s: s["start"] or "")

    print(render(title, in_range, sessions))


if __name__ == "__main__":
    main()
