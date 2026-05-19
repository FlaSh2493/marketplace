#!/usr/bin/env python3
"""
review-fix의 진행 상태를 meta.json["review_fix"]에 관리하고, review.md에 이력을 기록한다.
Usage:
  python3 review_fix_state.py load {issue_key}
  python3 review_fix_state.py save {issue_key} --iteration {n} --pushed-at {iso} --env-cache {json}
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "scripts"))
from state_paths import get_issue_dir, read_meta, update_meta_key

DEFAULT_STATE = {
    "iteration_count": 1,
    "pushed_at": None,
    "env_cache": None,
    "max_iterations": 20,
}


def load_state(issue_key: str) -> dict:
    meta = read_meta(issue_key)
    state = meta.get("review_fix", {})
    result = {**DEFAULT_STATE, **state}
    return result


def save_state(issue_key: str, data: dict) -> dict:
    current = load_state(issue_key)
    current.update({k: v for k, v in data.items() if v is not None})
    update_meta_key(issue_key, "review_fix", current)

    # review.md에 이터레이션 이력 추가
    _append_review_log(issue_key, current)

    return current


def _append_review_log(issue_key: str, state: dict):
    """review.md에 최신 이터레이션 상태를 추가한다."""
    issue_dir = get_issue_dir(issue_key)
    review_md = issue_dir / "review.md"

    iteration = state.get("iteration_count", 1)
    pushed_at = state.get("pushed_at", "")

    new_entry = f"\n## 이터레이션 {iteration}\n"
    if pushed_at:
        new_entry += f"- Push: {pushed_at}\n"
    new_entry += f"- 기록: {datetime.now().isoformat()}\n"

    if review_md.exists():
        existing = review_md.read_text(encoding="utf-8")
        review_md.write_text(existing + new_entry, encoding="utf-8")
    else:
        header = f"# 리뷰 대응: {issue_key}\n"
        review_md.write_text(header + new_entry, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")

    load_p = subparsers.add_parser("load")
    load_p.add_argument("issue_key")

    save_p = subparsers.add_parser("save")
    save_p.add_argument("issue_key")
    save_p.add_argument("--iteration", type=int)
    save_p.add_argument("--pushed-at")
    save_p.add_argument("--env-cache")

    args = parser.parse_args()

    if args.command == "load":
        state = load_state(args.issue_key)
        print(json.dumps(state, ensure_ascii=False))

    elif args.command == "save":
        data = {}
        if args.iteration is not None:
            data["iteration_count"] = args.iteration
        if args.pushed_at is not None:
            data["pushed_at"] = args.pushed_at
        if args.env_cache is not None:
            data["env_cache"] = json.loads(args.env_cache)
        state = save_state(args.issue_key, data)
        print(json.dumps(state, ensure_ascii=False))


if __name__ == "__main__":
    main()
