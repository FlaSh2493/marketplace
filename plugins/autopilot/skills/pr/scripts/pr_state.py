#!/usr/bin/env python3
"""
PR 생성 진행 상태를 meta.json["pr"]에 관리하고, 완료 시 pr.md를 기록한다.
Usage:
  python3 pr_state.py write --issue <ISSUE> --phase <PHASE> [--branch <BRANCH>] [--push-done <BOOL>] [--url <URL>]
  python3 pr_state.py read --issue <ISSUE>
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "scripts"))
from state_paths import get_issue_dir, read_meta, update_meta_key


def write_pr_md(issue_dir: Path, state: dict):
    """PR 완료 시 pr.md에 사람이 읽기 쉬운 요약을 기록한다."""
    url = state.get("url", "")
    branch = state.get("branch", "")
    base = state.get("base", "")
    labels = state.get("labels", [])
    created_at = state.get("updated_at", "")

    lines = [
        f"# PR: {state.get('issue', '')}",
        "",
        f"- URL: {url}",
        f"- Branch: {branch}",
    ]
    if base:
        lines.append(f"- Base: {base}")
    if labels:
        lines.append(f"- Labels: {', '.join(labels)}")
    if created_at:
        lines.append(f"- Created: {created_at}")

    pr_md = issue_dir / "pr.md"
    pr_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("cmd", choices=["write", "read"])
    parser.add_argument("--issue", required=True)
    parser.add_argument("--phase")
    parser.add_argument("--branch")
    parser.add_argument("--base")
    parser.add_argument("--url")
    parser.add_argument("--labels", help="콤마 구분 라벨 목록")
    parser.add_argument("--push-done", choices=["true", "false"])
    args = parser.parse_args()

    issue_dir = get_issue_dir(args.issue)
    meta = read_meta(args.issue)
    state = meta.get("pr", {})

    if args.cmd == "write":
        if args.phase:
            state["phase"] = args.phase
        if args.branch:
            state["branch"] = args.branch
        if args.base:
            state["base"] = args.base
        if args.url:
            state["url"] = args.url
        if args.labels:
            state["labels"] = [l.strip() for l in args.labels.split(",")]
        if args.push_done:
            state["push_done"] = (args.push_done == "true")
        state["issue"] = args.issue
        state["updated_at"] = datetime.now().isoformat()
        if "started_at" not in state:
            state["started_at"] = state["updated_at"]

        update_meta_key(args.issue, "pr", state)

        if args.phase == "completed" and state.get("url"):
            write_pr_md(issue_dir, state)

        print(f"PR state updated: {args.phase}")

    elif args.cmd == "read":
        if not state:
            print(json.dumps({"status": "none"}))
            return

        state["status"] = "ok"
        print(json.dumps(state, indent=2))


if __name__ == "__main__":
    main()
