#!/usr/bin/env python3
"""
이슈 상태 전이. 상태 파일 생성/삭제의 유일한 주체.
Usage: python3 transition.py {branch} {issue} {from_state} {to_state}
Exit 0: ok / Exit 1: error

상태: NONE → DRAFT → PUBLISHING → PUBLISHED → SYNCED
"""
import json, os, sys

TRANSITIONS = {
    ("NONE",       "DRAFT"):      [("create", "{issue}.draft")],
    ("DRAFT",      "PUBLISHING"): [("delete", "{issue}.draft"), ("create", "{issue}.publishing")],
    ("PUBLISHING", "PUBLISHED"):  [("delete", "{issue}.publishing"), ("create", "{issue}.published")],
    ("PUBLISHED",  "SYNCED"):     [("delete", "{issue}.published"), ("create", "{issue}.synced")],
    # 실패 복구용 역방향
    ("PUBLISHING", "DRAFT"):      [("delete", "{issue}.publishing"), ("create", "{issue}.draft")],
}


def find_git_root():
    import subprocess
    r = subprocess.run("git rev-parse --git-common-dir", shell=True, capture_output=True, text=True)
    common = r.stdout.strip()
    if common:
        return os.path.abspath(os.path.join(common, ".."))
    r2 = subprocess.run("git rev-parse --show-toplevel", shell=True, capture_output=True, text=True)
    return r2.stdout.strip() or None


def ok(msg):
    print(json.dumps({"status": "ok", "data": {"message": msg}}, ensure_ascii=False))
    sys.exit(0)


def error(code, reason):
    print(json.dumps({"status": "error", "code": code, "reason": reason}, ensure_ascii=False))
    sys.exit(1)


def main():
    if len(sys.argv) < 5:
        error("MISSING_ARGS", "사용법: transition.py {branch} {issue} {from_state} {to_state}")

    branch = sys.argv[1]
    issue = sys.argv[2]
    from_state = sys.argv[3].upper()
    to_state = sys.argv[4].upper()

    key = (from_state, to_state)
    if key not in TRANSITIONS:
        allowed = ", ".join(f"{f}→{t}" for f, t in TRANSITIONS)
        error("INVALID_TRANSITION",
              f"{from_state} → {to_state} 전이는 허용되지 않습니다. 허용: {allowed}")

    root = find_git_root()
    if not root:
        error("GIT_ROOT_NOT_FOUND", "Git 루트를 찾을 수 없습니다")

    task_dir = os.path.join(root, ".docs", "task", branch.replace("/", os.sep))
    state_dir = os.path.join(task_dir, ".state")
    os.makedirs(state_dir, exist_ok=True)

    for action, filename in TRANSITIONS[key]:
        path = os.path.join(state_dir, filename.replace("{issue}", issue))
        if action == "create":
            open(path, "w").close()
        elif action == "delete":
            if os.path.exists(path):
                os.remove(path)

    ok(f"{issue}: {from_state} → {to_state} 완료")


if __name__ == "__main__":
    main()
