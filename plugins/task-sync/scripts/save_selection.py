#!/usr/bin/env python3
"""
Jira 이슈 선택 결과를 pending.json에 저장. fetch [GATE] 이후 호출.
Usage: python3 save_selection.py {branch} {이슈키} [{이슈키}...]
Exit 0: ok / Exit 1: error
"""
import json, os, sys
from datetime import datetime
from common import find_git_root, get_task_dir, get_state_dir, ok, error


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        error("MISSING_ARGS", "사용법: save_selection.py {branch} {이슈키} [{이슈키}...]")

    branch = args[0]
    issues = args[1:]

    root = find_git_root()
    if not root:
        error("GIT_ROOT_NOT_FOUND", "Git 루트를 찾을 수 없습니다")

    task_dir = get_task_dir(root, branch)
    state_dir = get_state_dir(task_dir)
    os.makedirs(state_dir, exist_ok=True)

    pending_path = os.path.join(state_dir, "pending.json")
    payload = {
        "selected": issues,
        "selected_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "branch": branch,
    }
    with open(pending_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    ok({"pending_path": pending_path, "selected": issues, "count": len(issues)})


if __name__ == "__main__":
    main()
