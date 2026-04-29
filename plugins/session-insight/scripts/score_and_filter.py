#!/usr/bin/env python3
"""
score_and_filter.py — SessionStop 훅에서 실행. 종료된 세션을 휴리스틱으로 점수화한 뒤
점수가 임계값 이상이면 노이즈 정제본을 .filtered/ 에 복사하고, 모든 세션의 메타를
.filtered/index.jsonl 에 1줄 append 한다.

훅 입력: stdin JSON  (Claude Code SessionStop 훅 표준)
        예) {"session_id": "...", "transcript_path": "...", "cwd": "..."}
        하위호환: $CLAUDE_SESSION_ID / $CLAUDE_PROJECT_DIR 환경변수 fallback

오버라이드:
    SESSION_INSIGHT_MIN_SCORE  (정수)        - 임계값
    SESSION_INSIGHT_WEIGHTS    (JSON 문자열) - DEFAULTS 에 머지

종료 코드는 항상 0 (훅 실패가 세션 종료를 막지 않도록).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import date as date_cls, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _session_common import (  # noqa: E402
    completed_missing_weeklies,
    encode_cwd,
    iter_jsonl,
    missing_daily,
    missing_monthly,
    previous_month,
)

# ---------------------------------------------------------------------------
# 디폴트 가중치·경계값
# ---------------------------------------------------------------------------

DEFAULTS: dict = {
    # 도구 호출 수
    "tools_high": 3,         "tools_high_at": 30,
    "tools_mid": 1,          "tools_mid_at": 5,
    "tools_low": -2,
    # 지속시간 (분)
    "duration_ok": 2,        "duration_min_ok": 5,    "duration_max_ok": 120,
    "duration_bad": -3,      "duration_too_short": 1, "duration_too_long_min": 360,
    # Edit/Write
    "edit_write": 3,
    "no_edit": -2,
    # Bash
    "bash_ok": 1,            "bash_max_ok": 50,
    "bash_spam": -2,         "bash_spam_at": 100,
    # abort
    "abort": 1,
    # 사용자 프롬프트 수
    "prompts_ok": 2,         "prompts_min_ok": 3,     "prompts_max_ok": 10,
    "single_prompt": -1,
    # 에러 후 재시도
    "error_retry": 1,
    # 같은 파일 반복 수정
    "repeated_edit": 1,
    # 첫 프롬프트 길이
    "first_prompt_long": 1,    "first_prompt_long_at": 100,
    "first_prompt_short": -1,  "first_prompt_short_at": 20,
    # 임계값
    "min_score": 3,
}

EDIT_TOOLS = {"Edit", "Write", "NotebookEdit", "MultiEdit"}
BASH_TOOL = "Bash"

NOISY_EVENT_TYPES = {
    "queue-operation",
    "file-history-snapshot",
    "ai-title",
    "last-prompt",
}

NOISY_ATTACHMENT_TYPES = {
    "deferred_tools_delta",
    "hook_success",
    "mcp_instructions_delta",
    "todo_reminder",
    "skill_listing",
}

TOOL_RESULT_MAX_CHARS = 1500


# ---------------------------------------------------------------------------
# 설정 로드
# ---------------------------------------------------------------------------

def load_config() -> dict:
    cfg = dict(DEFAULTS)
    raw = os.environ.get("SESSION_INSIGHT_WEIGHTS", "").strip()
    if raw:
        try:
            override = json.loads(raw)
            if isinstance(override, dict):
                for k, v in override.items():
                    cfg[k] = v
        except json.JSONDecodeError:
            print(f"[session-insight] SESSION_INSIGHT_WEIGHTS JSON 파싱 실패: {raw[:80]}",
                  file=sys.stderr)
    min_score = os.environ.get("SESSION_INSIGHT_MIN_SCORE", "").strip()
    if min_score:
        try:
            cfg["min_score"] = int(min_score)
        except ValueError:
            pass
    return cfg


# ---------------------------------------------------------------------------
# 시그널 추출 (raw jsonl 1-pass)
# ---------------------------------------------------------------------------

def extract_signals(path: Path) -> dict:
    tools = 0
    edits = 0
    bash = 0
    prompts = 0
    abort = False
    error_retry = False
    file_edit_counts: dict[str, int] = {}
    first_prompt_len = 0
    first_ts: str | None = None
    last_ts: str | None = None
    last_tool_was_error: dict[str, bool] = {}

    for entry in iter_jsonl(path):
        ts = entry.get("timestamp")
        if ts:
            if first_ts is None:
                first_ts = ts
            last_ts = ts

        t = entry.get("type", "")

        if t == "user-abort" or entry.get("aborted") is True:
            abort = True

        msg = entry.get("message") or {}
        content = msg.get("content")

        if t == "user":
            if isinstance(content, list):
                text_chunks: list[str] = []
                has_tool_result_only = True
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    btype = block.get("type")
                    if btype == "text":
                        text_chunks.append(block.get("text", "") or "")
                        has_tool_result_only = False
                    elif btype == "tool_result":
                        tool_use_id = block.get("tool_use_id", "")
                        if block.get("is_error") is True and tool_use_id:
                            last_tool_was_error[tool_use_id] = True
                    else:
                        has_tool_result_only = False
                full_text = " ".join(s for s in text_chunks if s).strip()
                if full_text and not has_tool_result_only:
                    prompts += 1
                    if first_prompt_len == 0:
                        first_prompt_len = len(full_text)
            elif isinstance(content, str) and content.strip():
                prompts += 1
                if first_prompt_len == 0:
                    first_prompt_len = len(content.strip())

        elif t == "assistant":
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                tools += 1
                name = block.get("name", "")
                if name in EDIT_TOOLS:
                    edits += 1
                    fp = (block.get("input") or {}).get("file_path", "")
                    if fp:
                        file_edit_counts[fp] = file_edit_counts.get(fp, 0) + 1
                elif name == BASH_TOOL:
                    bash += 1
                if last_tool_was_error and name:
                    if any(last_tool_was_error.values()):
                        error_retry = True
                        last_tool_was_error.clear()

    duration_min = 0.0
    if first_ts and last_ts:
        try:
            a = datetime.fromisoformat(first_ts.replace("Z", "+00:00"))
            b = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
            duration_min = max(0.0, (b - a).total_seconds() / 60.0)
        except ValueError:
            pass

    repeated_edit_count = sum(1 for c in file_edit_counts.values() if c >= 2)

    return {
        "tools": tools,
        "edits": edits,
        "bash": bash,
        "prompts": prompts,
        "abort": abort,
        "error_retry": error_retry,
        "repeated_edit": repeated_edit_count,
        "first_prompt_len": first_prompt_len,
        "duration_min": round(duration_min, 1),
        "first_ts": first_ts,
        "last_ts": last_ts,
    }


# ---------------------------------------------------------------------------
# 점수 계산
# ---------------------------------------------------------------------------

def score(signals: dict, cfg: dict) -> int:
    s = 0

    tools = signals["tools"]
    if tools >= cfg["tools_high_at"]:
        s += cfg["tools_high"]
    elif tools >= cfg["tools_mid_at"]:
        s += cfg["tools_mid"]
    else:
        s += cfg["tools_low"]

    d = signals["duration_min"]
    if cfg["duration_min_ok"] <= d <= cfg["duration_max_ok"]:
        s += cfg["duration_ok"]
    elif d < cfg["duration_too_short"] or d >= cfg["duration_too_long_min"]:
        s += cfg["duration_bad"]

    s += cfg["edit_write"] if signals["edits"] >= 1 else cfg["no_edit"]

    bash = signals["bash"]
    if 1 <= bash <= cfg["bash_max_ok"]:
        s += cfg["bash_ok"]
    elif bash >= cfg["bash_spam_at"]:
        s += cfg["bash_spam"]

    if signals["abort"]:
        s += cfg["abort"]

    p = signals["prompts"]
    if cfg["prompts_min_ok"] <= p <= cfg["prompts_max_ok"]:
        s += cfg["prompts_ok"]
    elif p == 1:
        s += cfg["single_prompt"]

    if signals["error_retry"]:
        s += cfg["error_retry"]

    if signals["repeated_edit"] >= 1:
        s += cfg["repeated_edit"]

    fl = signals["first_prompt_len"]
    if fl >= cfg["first_prompt_long_at"]:
        s += cfg["first_prompt_long"]
    elif 0 < fl <= cfg["first_prompt_short_at"]:
        s += cfg["first_prompt_short"]

    return s


# ---------------------------------------------------------------------------
# 노이즈 정제 (필터된 jsonl 작성)
# ---------------------------------------------------------------------------

def truncate_tool_result_inner(inner):
    if isinstance(inner, str):
        if len(inner) > TOOL_RESULT_MAX_CHARS:
            return inner[:TOOL_RESULT_MAX_CHARS] + f"\n…[truncated {len(inner) - TOOL_RESULT_MAX_CHARS} chars]"
        return inner
    if isinstance(inner, list):
        out = []
        for item in inner:
            if isinstance(item, dict) and item.get("type") == "text":
                t = item.get("text", "") or ""
                if len(t) > TOOL_RESULT_MAX_CHARS:
                    item = {**item, "text": t[:TOOL_RESULT_MAX_CHARS] + f"\n…[truncated {len(t) - TOOL_RESULT_MAX_CHARS} chars]"}
            out.append(item)
        return out
    return inner


def clean_entry(entry: dict) -> dict | None:
    if entry.get("type") in NOISY_EVENT_TYPES:
        return None

    if entry.get("type") == "attachment":
        attach = entry.get("attachment") or {}
        if attach.get("type") in NOISY_ATTACHMENT_TYPES:
            return None

    msg = entry.get("message")
    if isinstance(msg, dict):
        content = msg.get("content")
        if isinstance(content, list):
            new_content = []
            for block in content:
                if not isinstance(block, dict):
                    new_content.append(block)
                    continue
                btype = block.get("type")
                if btype == "thinking":
                    continue
                if btype == "tool_result":
                    block = {**block, "content": truncate_tool_result_inner(block.get("content", ""))}
                new_content.append(block)
            entry = {**entry, "message": {**msg, "content": new_content}}

    return entry


def write_filtered(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    with open(dst, "w", encoding="utf-8") as out:
        for entry in iter_jsonl(src):
            cleaned = clean_entry(entry)
            if cleaned is None:
                continue
            out.write(json.dumps(cleaned, ensure_ascii=False))
            out.write("\n")


def append_index(index_path: Path, record: dict) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with open(index_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False))
        f.write("\n")


# ---------------------------------------------------------------------------
# 입력 해석
# ---------------------------------------------------------------------------

def resolve_session_path(session_id: str, transcript_path: str | None, cwd: str | None) -> Path | None:
    if transcript_path:
        p = Path(transcript_path)
        if p.exists():
            return p

    if cwd and session_id:
        base = Path.home() / ".claude" / "projects" / encode_cwd(cwd)
        candidate = base / f"{session_id}.jsonl"
        if candidate.exists():
            return candidate

    return None


def read_event() -> dict:
    raw = sys.stdin.read() if not sys.stdin.isatty() else ""
    if raw.strip():
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
    return {
        "session_id": os.environ.get("CLAUDE_SESSION_ID", ""),
        "transcript_path": os.environ.get("CLAUDE_TRANSCRIPT_PATH", ""),
        "cwd": os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd()),
    }


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    event = read_event()
    session_id = event.get("session_id") or ""
    transcript_path = event.get("transcript_path") or ""
    cwd = event.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())

    src = resolve_session_path(session_id, transcript_path, cwd)
    if src is None or not src.exists():
        return 0

    cfg = load_config()
    signals = extract_signals(src)
    sc = score(signals, cfg)
    kept = sc >= cfg["min_score"]

    base_root = (Path(cwd) if cwd else Path.home()) / ".claude" / "session-insight"
    base = base_root / ".filtered"
    index_path = base / "index.jsonl"

    record = {
        "session_id": session_id or src.stem,
        "date": (signals["first_ts"] or "")[:10] or datetime.now().strftime("%Y-%m-%d"),
        "score": sc,
        "kept": bool(kept),
        "signals": {k: v for k, v in signals.items() if k not in {"first_ts", "last_ts"}},
    }

    if kept:
        dst = base / record["date"] / f"{record['session_id']}.jsonl"
        try:
            write_filtered(src, dst)
        except Exception as e:
            print(f"[session-insight] write_filtered 실패: {e}", file=sys.stderr)
            record["kept"] = False

    try:
        append_index(index_path, record)
    except Exception as e:
        print(f"[session-insight] append_index 실패: {e}", file=sys.stderr)

    # 1차 빠른 체크 — 누락된 상위 tier가 있으면 rollup_check.py를 detach 실행
    try:
        today = date_cls.today()
        yesterday = today - timedelta(days=1)
        needs_rollup = (
            missing_daily(base_root, yesterday)
            or bool(completed_missing_weeklies(today, base_root))
            or missing_monthly(base_root, previous_month(today))
        )
        if needs_rollup:
            rollup_script = Path(__file__).parent / "rollup_check.py"
            subprocess.Popen(
                [sys.executable, str(rollup_script), str(cwd)],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
    except Exception as e:
        print(f"[session-insight] rollup detach 실패: {e}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"[session-insight] 훅 처리 오류: {e}", file=sys.stderr)
        sys.exit(0)
