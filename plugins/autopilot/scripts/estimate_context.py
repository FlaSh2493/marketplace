#!/usr/bin/env python3
"""
pending steps를 컨텍스트 예산 기반으로 greedy packing하여 session 배열을 반환한다.
Session 0 = main session, Session 1+ = sub-agent.
"""
import argparse
import json
import os
from pathlib import Path


DEFAULT_BUDGET = 80_000
DEFAULT_BASE_OVERHEAD = 15_000
DEFAULT_STEP_OVERHEAD = 3_000


def estimate_step_tokens(step: dict, worktree: str, step_overhead: int) -> int:
    file_tokens = 0
    for f in step.get("files", []):
        # 절대 경로 또는 worktree 상대 경로 모두 처리
        p = Path(f) if Path(f).is_absolute() else Path(worktree) / f
        if p.exists():
            file_tokens += p.stat().st_size // 3
    return file_tokens + step_overhead


def pack_sessions(pending_steps: list, worktree: str, budget: int,
                  base_overhead: int, step_overhead: int) -> list:
    remaining_budget = budget - base_overhead
    sessions = []
    current_steps = []
    current_tokens = 0

    for step in pending_steps:
        cost = estimate_step_tokens(step, worktree, step_overhead)
        if current_steps and current_tokens + cost > remaining_budget:
            sessions.append(current_steps)
            current_steps = []
            current_tokens = 0
        current_steps.append((step, cost))
        current_tokens += cost

    if current_steps:
        sessions.append(current_steps)

    result = []
    for idx, session_steps in enumerate(sessions):
        steps = [s for s, _ in session_steps]
        tokens = sum(t for _, t in session_steps)
        result.append({
            "session_idx": idx,
            "actor": "main" if idx == 0 else "agent",
            "steps": steps,
            "estimated_tokens": tokens,
        })
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan-json", required=True)
    parser.add_argument("--issue", required=True)
    parser.add_argument("--worktree", required=True)
    parser.add_argument("--budget", type=int, default=DEFAULT_BUDGET)
    parser.add_argument("--base-overhead", type=int, default=DEFAULT_BASE_OVERHEAD)
    parser.add_argument("--step-overhead", type=int, default=DEFAULT_STEP_OVERHEAD)
    args = parser.parse_args()

    plan_data = json.loads(Path(args.plan_json).read_text())
    pending_steps = []
    for plan in plan_data.get("data", {}).get("plans", []):
        if plan["issue"] != args.issue:
            continue
        for phase in plan.get("phases", []):
            for step in phase.get("steps", []):
                pending_steps.append(step)

    if not pending_steps:
        print(json.dumps({"status": "error", "reason": "pending steps 없음"}, ensure_ascii=False))
        return

    sessions = pack_sessions(
        pending_steps,
        args.worktree,
        args.budget,
        args.base_overhead,
        args.step_overhead,
    )

    print(json.dumps({"status": "ok", "sessions": sessions}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
