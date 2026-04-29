#!/usr/bin/env python3
"""
이슈 상태 전이. published 마커 생성/삭제의 유일한 주체.
Usage: python3 transition.py {issue} {from_state} {to_state}
Exit 0: ok / Exit 1: error

상태: NONE ↔ PUBLISHED
published 마커: .docs/tasks/{issue}/published
"""
import json, os, sys
from pathlib import Path
from common import find_git_root, get_task_dir, get_state_dir

TRANSITIONS = {
    ("NONE",      "PUBLISHED"): [("issue", "create", "published")],
    ("PUBLISHED", "NONE"):      [("issue", "delete", "published")],
}


def ok_msg(msg):
    print(json.dumps({"status": "ok", "data": {"message": msg}}, ensure_ascii=False))
    sys.exit(0)


def error(code, reason):
    print(json.dumps({"status": "error", "code": code, "reason": reason}, ensure_ascii=False))
    sys.exit(1)


def main():
    if len(sys.argv) < 4:
        error("MISSING_ARGS", "사용법: transition.py {issue} {from_state} {to_state}")

    issue = sys.argv[1]
    from_state = sys.argv[2].upper()
    to_state = sys.argv[3].upper()

    key = (from_state, to_state)
    if key not in TRANSITIONS:
        allowed = ", ".join(f"{f}→{t}" for f, t in TRANSITIONS)
        error("INVALID_TRANSITION",
              f"{from_state} → {to_state} 전이는 허용되지 않습니다. 허용: {allowed}")

    root = find_git_root()
    if not root:
        error("GIT_ROOT_NOT_FOUND", "Git 루트를 찾을 수 없습니다")

    task_dir = get_task_dir(root)
    state_dir = get_state_dir(root)
    os.makedirs(state_dir, exist_ok=True)

    for location, action, filename in TRANSITIONS[key]:
        filename = filename.replace("{issue}", issue)
        issue_dir = os.path.join(task_dir, issue)
        os.makedirs(issue_dir, exist_ok=True)
        path = os.path.join(issue_dir, filename)

        if action == "create":
            open(path, "w").close()
        elif action == "delete":
            if os.path.exists(path):
                os.remove(path)

    ok_msg(f"{issue}: {from_state} → {to_state} 완료")


if __name__ == "__main__":
    main()
