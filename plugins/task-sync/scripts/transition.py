#!/usr/bin/env python3
"""
이슈 상태 전이. 상태 파일 생성/삭제의 유일한 주체.
Usage: python3 transition.py {branch} {issue} {from_state} {to_state}
Exit 0: ok / Exit 1: error

상태: NONE → DRAFT → PUBLISHING → PUBLISHED → SYNCED
"""
import json, os, sys
from common import find_git_root, get_task_dir, get_state_dir

TRANSITIONS = {
    ("NONE",       "DRAFT"):      [("create", "{issue}.draft")],
    ("DRAFT",      "PUBLISHING"): [("delete", "{issue}.draft"), ("create", "{issue}.publishing")],
    ("PUBLISHING", "PUBLISHED"):  [("delete", "{issue}.publishing"), ("create", "{issue}.published")],
    ("PUBLISHED",  "SYNCED"):     [("delete", "{issue}.published"), ("create", "{issue}.synced")],
    # 실패 복구용 역방향
    ("PUBLISHING", "DRAFT"):      [("delete", "{issue}.publishing"), ("create", "{issue}.draft")],
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

    for action, filename in TRANSITIONS[key]:
        path = os.path.join(state_dir, filename.replace("{issue}", issue))
        if action == "create":
            open(path, "w").close()
        elif action == "delete":
            if os.path.exists(path):
                os.remove(path)

    ok_msg(f"{issue}: {from_state} → {to_state} 완료")


if __name__ == "__main__":
    main()
