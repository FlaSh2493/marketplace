#!/usr/bin/env python3
"""
collect_daily.py — 특정 날짜의 raw jsonl 들을 한 번 훑어 구조화 markdown 출력.

사용법:
    python3 collect_daily.py <cwd> <YYYY-MM-DD>

읽기:  ~/.claude/projects/<encoded-cwd>/<sid>.jsonl  (날짜 일치하는 것만)
출력:  stdout 으로 markdown. 일간 스킬이 그대로 입력으로 사용한다.

스크립트 책임은 결정적 산술·정렬뿐. 정성 요약은 에이전트가 수행한다.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from datetime import date as date_cls, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _session_common import (  # noqa: E402
    compute_cache_hit_rate,
    encode_cwd,
    extract_skill,
    get_session_start,
    get_text,
    iter_jsonl,
    measure_tool_results,
)

USER_PREVIEW_CHARS = 300
DIRECT_INPUT_PREVIEW_CHARS = 100
HEAVY_TURNS_PER_SESSION = 5


# ---------------------------------------------------------------------------
# 세션 분석
# ---------------------------------------------------------------------------

def analyze_session(session_id: str, path: Path) -> tuple[dict, dict[int, list[str]]]:
    """raw jsonl → (session_summary, thinking_by_turn).

    한 번의 순회로 turn 별 통계와 thinking 본문을 동시에 수집한다.
    """
    turns: list[dict] = []
    turn_num = 0
    pending: dict = {}
    thinking_by_turn: dict[int, list[str]] = defaultdict(list)
    first_ts = None

    for entry in iter_jsonl(path):
        if first_ts is None and entry.get("timestamp"):
            first_ts = entry.get("timestamp")

        t = entry.get("type", "")

        if t == "user":
            msg = entry.get("message", {})
            content = msg.get("content", [])
            text = get_text(content)
            skill = extract_skill(text)
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
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "tool_use":
                        tool_uses.append(block.get("name", ""))
                    elif block.get("type") == "thinking":
                        thinking_by_turn[turn_num].append(block.get("thinking", "") or "")

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

    session = {
        "id": session_id,
        "start": start_iso,
        "turn_count": len(turns),
        "input_tokens_total": sum(t["input_tokens"] for t in turns),
        "output_tokens_total": sum(t["output_tokens"] for t in turns),
        "thinking_blocks": sum(len(v) for v in thinking_by_turn.values()),
        "thinking_chars": sum(sum(len(s) for s in v) for v in thinking_by_turn.values()),
        "turns": turns,
    }
    return session, thinking_by_turn


# ---------------------------------------------------------------------------
# 집계·선정
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
            "avg_input": d["in_sum"] // d["count"],
            "avg_output": d["out_sum"] // d["count"],
            "cache_hit": round(d["cache_sum"] / d["count"], 3),
            "total_input": d["in_sum"],
        }
        for sk, d in agg.items()
    ]
    rows.sort(key=lambda r: -r["total_input"])
    return rows


def select_heavy_turns(session: dict, thinking_by_turn: dict[int, list[str]]) -> list[dict]:
    """input_tokens / output_tokens / tool_chars / thinking_chars 각 Top N 합집합."""
    if not session["turns"]:
        return []
    enriched = [
        {**t, "thinking_chars": sum(len(s) for s in thinking_by_turn.get(t["turn"], []))}
        for t in session["turns"]
    ]
    keys = ("input_tokens", "output_tokens", "tool_chars", "thinking_chars")
    selected: dict[int, dict] = {}
    for k in keys:
        for t in sorted(enriched, key=lambda x: -x[k])[:HEAVY_TURNS_PER_SESSION]:
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


# ---------------------------------------------------------------------------
# Markdown 렌더링
# ---------------------------------------------------------------------------

def short_id(sid: str) -> str:
    return sid.split("-", 1)[0] if "-" in sid else sid[:8]


def render(date_str: str, sessions_with_thinking: list[tuple[dict, dict]]) -> str:
    sessions = [s for s, _ in sessions_with_thinking]
    out: list[str] = []

    total_in = sum(s["input_tokens_total"] for s in sessions)
    total_out = sum(s["output_tokens_total"] for s in sessions)
    total_thinking = sum(s["thinking_blocks"] for s in sessions)

    out.append(f"# 일간 raw 데이터: {date_str}")
    out.append("")
    out.append(
        f"세션 {len(sessions)}개 | input {total_in:,} 토큰 | "
        f"output {total_out:,} 토큰 | thinking 블록 {total_thinking}"
    )
    out.append("")

    # 세션 목록
    out.append("## 세션 목록")
    out.append("")
    out.append("| id | start | turns | input | output | thinking blocks |")
    out.append("|----|-------|-------|-------|--------|-----------------|")
    for s in sessions:
        out.append(
            f"| `{short_id(s['id'])}` | {s['start'] or '—'} | {s['turn_count']} | "
            f"{s['input_tokens_total']:,} | {s['output_tokens_total']:,} | {s['thinking_blocks']} |"
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
    for s, thinking_by_turn in sessions_with_thinking:
        heavy = select_heavy_turns(s, thinking_by_turn)
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
            blocks = thinking_by_turn.get(t["turn"], [])
            if blocks:
                out.append("")
                out.append(f"thinking ({len(blocks)} 블록, 총 {sum(len(b) for b in blocks):,}자):")
                for i, b in enumerate(blocks, 1):
                    out.append(f"<details><summary>thinking #{i} ({len(b):,}자)</summary>")
                    out.append("")
                    out.append("```")
                    out.append(b)
                    out.append("```")
                    out.append("")
                    out.append("</details>")
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
# main
# ---------------------------------------------------------------------------

def main() -> None:
    if len(sys.argv) != 3:
        print("usage: collect_daily.py <cwd> <YYYY-MM-DD>", file=sys.stderr)
        sys.exit(2)

    cwd = sys.argv[1]
    try:
        target = date_cls.fromisoformat(sys.argv[2])
    except ValueError:
        print(f"잘못된 날짜: {sys.argv[2]} (YYYY-MM-DD)", file=sys.stderr)
        sys.exit(2)

    base = Path.home() / ".claude" / "projects" / encode_cwd(cwd)
    if not base.exists():
        print(f"# 일간 raw 데이터: {target.isoformat()}\n\n세션 디렉토리 없음: {base}")
        return

    sessions_with_thinking: list[tuple[dict, dict]] = []
    for path in sorted(base.glob("*.jsonl")):
        if path.stem.endswith(".filtered"):
            continue  # 레거시 잔재
        start = get_session_start(iter_jsonl(path))
        if not start or start.date() != target:
            continue
        session, thinking_by_turn = analyze_session(path.stem, path)
        if session["turn_count"] == 0:
            continue
        sessions_with_thinking.append((session, thinking_by_turn))

    if not sessions_with_thinking:
        print(f"# 일간 raw 데이터: {target.isoformat()}\n\n해당 날짜에 세션이 없습니다.")
        return

    print(render(target.isoformat(), sessions_with_thinking))


if __name__ == "__main__":
    main()
