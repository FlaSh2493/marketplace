#!/usr/bin/env python3
"""
analyze_insights.py — 세션 로그 종합 분석. 마크다운 텍스트를 stdout으로 출력한다.

분석 항목:
  - 스킬별 토큰 부하 (기간별)
  - thinking 블록 기반 시행착오 추출 (원본 .jsonl 참조)
  - 유저 입력 패턴 분류
  - 이상 반응 감지 및 유저 입력 상관관계

사용법:
    python3 analyze_insights.py <cwd> [--days N]
    python3 analyze_insights.py <cwd> [--from YYYY-MM-DD --to YYYY-MM-DD]
    python3 analyze_insights.py <cwd> [--all]
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

SKILL_PATTERN = re.compile(r"/[\w-]+:[\w-]+")
TRUNCATED_PATTERN = re.compile(r"\.\.\. \[truncated (\d+) chars\]$")
ERROR_PATTERN = re.compile(r"\b(error|exception|traceback|errno|failed|failure)\b", re.IGNORECASE)

DIRECTION_CHANGE_RE = re.compile(
    r"\bactually\b|\bwait\b|\binstead\b|\bno,\b|\bwrong\b"
    r"|\breconsider\b|\blet me try\b|\blet me re"
    r"|아니[,\s]|잠깐|다시\s*생각|틀렸|사실은",
    re.IGNORECASE,
)

QUESTION_RE = re.compile(
    r"^(뭐|어떻게|왜|언제|어디|무슨|how|what|why|when|where|is |are |can |does )",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# CLI / 기간
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("cwd")
    p.add_argument("--days", type=int, default=None)
    p.add_argument("--from", dest="from_date", default=None)
    p.add_argument("--to", dest="to_date", default=None)
    p.add_argument("--all", dest="all_time", action="store_true")
    return p.parse_args()


def resolve_period(args):
    now = datetime.now(timezone.utc)
    if args.all_time:
        return None, None
    if args.from_date or args.to_date:
        from_dt = datetime.fromisoformat(args.from_date).replace(tzinfo=timezone.utc) if args.from_date else None
        to_dt = datetime.fromisoformat(args.to_date).replace(tzinfo=timezone.utc) if args.to_date else now
        return from_dt, to_dt
    days = args.days or 30
    return now - timedelta(days=days), now


# ---------------------------------------------------------------------------
# 파싱 유틸
# ---------------------------------------------------------------------------

def load_jsonl(path: Path) -> list[dict]:
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


def get_session_start(entries: list[dict]):
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


def extract_skill(text: str):
    m = SKILL_PATTERN.search(text)
    return m.group(0) if m else None


def classify_input(text: str, skill: str) -> str:
    if skill:
        return "스킬호출형"
    stripped = text.strip()
    if len(stripped) <= 10:
        return "단어형(≤10자)"
    if stripped.endswith("?") or QUESTION_RE.match(stripped):
        return "질문형"
    return "명령형"


def measure_tool_results(content: list) -> tuple[int, int, bool]:
    """(count, total_original_chars, has_error)"""
    count = 0
    total_chars = 0
    has_error = False
    for block in content:
        if not isinstance(block, dict) or block.get("type") != "tool_result":
            continue
        count += 1
        inner = block.get("content", "")
        text = ""
        if isinstance(inner, str):
            m = TRUNCATED_PATTERN.search(inner)
            total_chars += int(m.group(1)) if m else len(inner)
            text = inner
        elif isinstance(inner, list):
            for item in inner:
                if isinstance(item, dict) and item.get("type") == "text":
                    t = item.get("text", "")
                    m = TRUNCATED_PATTERN.search(t)
                    total_chars += int(m.group(1)) if m else len(t)
                    text += t
        if ERROR_PATTERN.search(text):
            has_error = True
    return count, total_chars, has_error


# ---------------------------------------------------------------------------
# thinking 블록 분석 (원본 .jsonl)
# ---------------------------------------------------------------------------

def analyze_thinking(entries: list[dict]) -> dict:
    direction_changes = []  # (turn_num, match_count, snippet)
    stuck_points: dict[str, int] = defaultdict(int)
    total_chars = 0
    block_count = 0

    turn_num = 0
    for entry in entries:
        if entry.get("type") == "user":
            turn_num += 1
        elif entry.get("type") == "assistant":
            content = entry.get("message", {}).get("content", [])
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "thinking":
                    continue
                text = block.get("thinking", "")
                total_chars += len(text)
                block_count += 1

                matches = DIRECTION_CHANGE_RE.findall(text)
                if len(matches) >= 2:
                    m = DIRECTION_CHANGE_RE.search(text)
                    if m:
                        s = max(0, m.start() - 30)
                        e = min(len(text), m.start() + 70)
                        snippet = text[s:e].replace("\n", " ").strip()
                        direction_changes.append((turn_num, len(matches), snippet))

                # 방향전환이 있을 때 등장한 파일·함수명 기록
                if len(matches) >= 1:
                    for ref in re.findall(r"[\w/-]+\.(?:py|ts|tsx|js|md|json)\b", text):
                        stuck_points[ref] += 1

    avg_chars = total_chars / block_count if block_count else 0
    top_stuck = dict(sorted(stuck_points.items(), key=lambda x: -x[1])[:5])
    return {
        "direction_changes": direction_changes,
        "stuck_points": top_stuck,
        "avg_thinking_chars": avg_chars,
    }


# ---------------------------------------------------------------------------
# 세션 분석 (filtered.jsonl)
# ---------------------------------------------------------------------------

def analyze_session(session_id: str, entries: list[dict]) -> dict:
    turns = []
    turn_num = 0
    pending: dict = {}
    tool_tracker: dict[tuple, int] = defaultdict(int)

    for entry in entries:
        t = entry.get("type", "")

        if t == "user":
            msg = entry.get("message", {})
            content = msg.get("content", [])
            text = get_text(content)
            skill = extract_skill(text)
            tc, tch, has_err = measure_tool_results(content) if isinstance(content, list) else (0, 0, False)

            turn_num += 1
            tool_tracker.clear()
            pending = {
                "skill": skill,
                "user_text": text,
                "tool_count": tc,
                "tool_chars": tch,
                "has_error": has_err,
            }

        elif t == "assistant":
            msg = entry.get("message", {})
            usage = msg.get("usage") or {}
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            cache_read = usage.get("cache_read_input_tokens", 0)
            cache_hit = round(cache_read / input_tokens, 3) if input_tokens > 0 else 0.0

            content = msg.get("content", [])
            has_tool_use = False
            retries = 0
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        has_tool_use = True
                        key = (block.get("name", ""), str(sorted(block.get("input", {}).items()))[:100])
                        tool_tracker[key] += 1
                        if tool_tracker[key] >= 2:
                            retries += 1

            anomalies = []
            if pending.get("has_error"):
                anomalies.append("tool_error")
            if retries:
                anomalies.append(f"retry×{retries}")
            if output_tokens < 50 and not has_tool_use:
                anomalies.append("output_truncated")
            if cache_hit == 0.0 and input_tokens > 30000:
                anomalies.append("cache_miss_heavy")

            skill = pending.get("skill")
            user_text = pending.get("user_text", "")
            turns.append({
                "turn": turn_num,
                "skill": skill,
                "input_type": classify_input(user_text, skill),
                "user_preview": user_text[:60].replace("\n", " "),
                "user_len": len(user_text),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_hit": cache_hit,
                "tool_count": pending.get("tool_count", 0),
                "tool_chars": pending.get("tool_chars", 0),
                "anomalies": anomalies,
            })
            pending = {}

    total_tokens = sum(t["input_tokens"] + t["output_tokens"] for t in turns)
    start_dt = get_session_start(entries)
    return {
        "id": session_id,
        "start": start_dt.isoformat() if start_dt else None,
        "total_tokens": total_tokens,
        "turns": turns,
    }


# ---------------------------------------------------------------------------
# 마크다운 리포트 생성
# ---------------------------------------------------------------------------

def build_report(sessions: list[dict], thinking_map: dict, from_dt, to_dt) -> str:
    out = []

    total_in = sum(t["input_tokens"] for s in sessions for t in s["turns"])
    total_out = sum(t["output_tokens"] for s in sessions for t in s["turns"])
    p_from = from_dt.date().isoformat() if from_dt else "전체"
    p_to = to_dt.date().isoformat() if to_dt else "전체"

    out.append(f"## 분석 기간: {p_from} ~ {p_to}")
    out.append(f"총 {len(sessions)}개 세션 | input: {total_in:,}토큰 | output: {total_out:,}토큰")
    out.append("")

    # --- 스킬별 통계 ---
    skill_stats: dict[str, dict] = defaultdict(lambda: {"n": 0, "in": 0, "out": 0, "cache": 0.0, "anomaly": 0})
    for s in sessions:
        for t in s["turns"]:
            sk = t["skill"] or "직접입력"
            d = skill_stats[sk]
            d["n"] += 1
            d["in"] += t["input_tokens"]
            d["out"] += t["output_tokens"]
            d["cache"] += t["cache_hit"]
            if t["anomalies"]:
                d["anomaly"] += 1

    out.append("### 스킬별 토큰 사용량")
    out.append("| 스킬 | 호출 | avg input | avg output | cache hit | 이상률 | 개선방향 |")
    out.append("|------|------|-----------|------------|-----------|--------|---------|")
    for sk, d in sorted(skill_stats.items(), key=lambda x: -x[1]["in"]):
        n = d["n"]
        avg_in = d["in"] // n
        cache_rate = d["cache"] / n
        anomaly_rate = d["anomaly"] / n

        hints = []
        if cache_rate < 0.1 and avg_in > 20000:
            hints.append("캐시 미스 점검")
        if anomaly_rate >= 0.3:
            hints.append("이상 반응 높음")
        if avg_in > 50000:
            hints.append("tool_result 축소")
        if not hints:
            hints.append("-")

        out.append(
            f"| {sk} | {n} | {avg_in:,} | {d['out']//n:,} "
            f"| {cache_rate:.0%} | {anomaly_rate:.0%} | {', '.join(hints)} |"
        )
    out.append("")

    # --- 고부하 Turn (+ 이상 반응 표시) ---
    all_turns = [(s["id"], t) for s in sessions for t in s["turns"]]
    heavy = sorted(all_turns, key=lambda x: -x[1]["input_tokens"])[:10]
    shown: set[tuple] = set()

    out.append("### 고부하 Turn 인사이트")
    for sid, t in heavy:
        shown.add((sid, t["turn"]))
        tag = " ⚠️" if t["anomalies"] else ""
        out.append(
            f"- `{sid[:8]}` turn {t['turn']} | {t['skill'] or '직접입력'} | "
            f"in: {t['input_tokens']:,} / out: {t['output_tokens']:,} | "
            f"cache: {t['cache_hit']:.0%}{tag}"
        )
        if t["anomalies"]:
            out.append(f"  - 이상 신호: {', '.join(t['anomalies'])}")
            out.append(f"  - 유저 입력 ({t['input_type']}, {t['user_len']}자): \"{t['user_preview']}\"")
    out.append("")

    # 고부하에 안 포함된 이상 반응 turn
    extra = [(sid, t) for sid, t in all_turns if t["anomalies"] and (sid, t["turn"]) not in shown]
    if extra:
        out.append("### 추가 이상 반응 Turn")
        for sid, t in extra[:5]:
            out.append(
                f"- `{sid[:8]}` turn {t['turn']} | {t['skill'] or '직접입력'} | "
                f"이상: {', '.join(t['anomalies'])}"
            )
            out.append(f"  - 유저 입력 ({t['input_type']}, {t['user_len']}자): \"{t['user_preview']}\"")
        out.append("")

    # --- Thinking 시행착오 ---
    all_dc = []
    all_stuck: dict[str, int] = defaultdict(int)
    for s in sessions:
        tk = thinking_map.get(s["id"], {})
        for dc in tk.get("direction_changes", []):
            all_dc.append((s["id"][:8], dc[0], dc[1], dc[2]))
        for ref, cnt in tk.get("stuck_points", {}).items():
            all_stuck[ref] += cnt

    if all_dc or all_stuck:
        out.append("### Thinking 시행착오")
        if all_dc:
            out.append("**방향 전환 구간** (thinking 내 번복이 많은 turn):")
            for sid, turn_num, cnt, snippet in sorted(all_dc, key=lambda x: -x[2])[:5]:
                out.append(f"- `{sid}` turn {turn_num} — 번복 {cnt}회: \"…{snippet}…\"")
        if all_stuck:
            out.append("**자주 막힌 지점** (방향전환과 함께 등장한 파일):")
            for ref, cnt in sorted(all_stuck.items(), key=lambda x: -x[1])[:5]:
                out.append(f"- `{ref}` — {cnt}회")
        out.append("")

    # --- 유저 입력 상관관계 ---
    itype_stats: dict[str, dict] = defaultdict(lambda: {"n": 0, "anomaly": 0})
    for s in sessions:
        for t in s["turns"]:
            d = itype_stats[t["input_type"]]
            d["n"] += 1
            if t["anomalies"]:
                d["anomaly"] += 1

    out.append("### 유저 입력 패턴 × 이상 반응 상관관계")
    out.append("| 입력 유형 | 횟수 | 이상 반응 | 이상률 |")
    out.append("|----------|------|----------|--------|")
    for itype, d in sorted(itype_stats.items(), key=lambda x: -x[1]["n"]):
        rate = d["anomaly"] / d["n"] if d["n"] else 0
        out.append(f"| {itype} | {d['n']} | {d['anomaly']} | {rate:.0%} |")
    out.append("")

    # --- 최적화 제안 ---
    out.append("### 최적화 제안")

    worst = max(itype_stats.items(), key=lambda x: x[1]["anomaly"] / max(x[1]["n"], 1), default=None)
    if worst and worst[1]["anomaly"] > 0:
        rate = worst[1]["anomaly"] / worst[1]["n"]
        out.append(f"- **`{worst[0]}` 입력 주의**: 이상 반응률 {rate:.0%}. 맥락을 명확히 담은 문장으로 개선 권장.")

    heavy_cache_miss = [
        (sk, d) for sk, d in skill_stats.items()
        if d["n"] >= 3 and d["cache"] / d["n"] < 0.1
    ]
    for sk, d in heavy_cache_miss[:2]:
        out.append(f"- **`{sk}` 캐시 미스**: 평균 {d['cache']/d['n']:.0%}. 세션 중간 재시작 반복 여부 확인.")

    if all_stuck:
        top_ref, top_cnt = max(all_stuck.items(), key=lambda x: x[1])
        out.append(f"- **`{top_ref}` 반복 막힘**: thinking에서 {top_cnt}회 등장. 관련 명세를 더 명확히 제공 권장.")

    # --- 신규 스킬 후보 ---
    candidates = []

    # 직접입력 호출이 많으면 → 전용 스킬 후보
    direct = skill_stats.get("직접입력", {})
    if direct.get("n", 0) >= 5:
        avg_in = direct["in"] // direct["n"]
        candidates.append(
            f"- **반복 직접입력 → 스킬 전환 검토**: 직접입력이 {direct['n']}회로 가장 많음 "
            f"(avg input {avg_in:,}토큰). 자주 쓰는 명령을 전용 스킬로 만들면 SKILL.md 캐시 효과를 받을 수 있음."
        )

    # 이상 반응률 높은 스킬 → 가이드 스킬 후보
    for sk, d in skill_stats.items():
        if sk == "직접입력" or d["n"] < 3:
            continue
        rate = d["anomaly"] / d["n"]
        if rate >= 0.3:
            candidates.append(
                f"- **`{sk}` 가이드 스킬 후보**: 이상 반응률 {rate:.0%}. "
                f"호출 전 맥락을 자동으로 수집·요약하는 래퍼 스킬을 만들면 오류 감소 기대."
            )

    # 호출 빈도 높고 캐시 미스 심한 스킬 → warm-up 스킬 후보
    for sk, d in skill_stats.items():
        if d["n"] >= 5 and d["cache"] / d["n"] < 0.05 and d["in"] // d["n"] > 20000:
            candidates.append(
                f"- **`{sk}` warm-up 스킬 후보**: {d['n']}회 호출, 캐시 히트 {d['cache']/d['n']:.0%}, "
                f"avg {d['in']//d['n']:,}토큰. 세션 시작 시 컨텍스트를 미리 로드하는 init 스킬 고려."
            )

    # thinking에서 자주 막힌 파일 → 전용 조회 스킬 후보
    if all_stuck:
        top_ref, top_cnt = max(all_stuck.items(), key=lambda x: x[1])
        if top_cnt >= 3:
            candidates.append(
                f"- **`{top_ref}` 전용 조회 스킬 후보**: thinking에서 {top_cnt}회 막힘. "
                f"해당 파일·모듈의 구조를 요약해 주는 스킬을 만들면 반복 탐색 비용 절감."
            )

    if candidates:
        out.append("")
        out.append("### 신규 스킬 후보")
        out.extend(candidates)

    return "\n".join(out)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    args = parse_args()
    from_dt, to_dt = resolve_period(args)

    encoded = args.cwd.replace("/", "-")
    projects_dir = Path.home() / ".claude" / "projects" / encoded

    if not projects_dir.exists():
        print(f"오류: 프로젝트 디렉토리를 찾을 수 없습니다: {projects_dir}")
        sys.exit(1)

    filtered_files = sorted(projects_dir.glob("*.filtered.jsonl"))
    if not filtered_files:
        print("아직 필터된 세션 로그가 없습니다. 세션을 종료하면 자동으로 생성됩니다.")
        sys.exit(0)

    sessions = []
    thinking_map = {}

    for path in filtered_files:
        session_id = path.stem.replace(".filtered", "")
        filtered_entries = load_jsonl(path)
        if not filtered_entries:
            continue

        start = get_session_start(filtered_entries)
        if start:
            if from_dt and start < from_dt:
                continue
            if to_dt and start > to_dt:
                continue

        # thinking 분석: 원본 .jsonl 참조 (없어도 무시)
        original_path = projects_dir / f"{session_id}.jsonl"
        if original_path.exists():
            try:
                thinking_map[session_id] = analyze_thinking(load_jsonl(original_path))
            except Exception:
                pass

        sessions.append(analyze_session(session_id, filtered_entries))

    if not sessions:
        print("해당 기간에 세션이 없습니다. --all 옵션을 사용해보세요.")
        sys.exit(0)

    print(build_report(sessions, thinking_map, from_dt, to_dt))


if __name__ == "__main__":
    main()
