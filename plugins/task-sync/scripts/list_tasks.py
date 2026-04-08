#!/usr/bin/env python3
"""
상태별 이슈 목록 출력.
Usage: python3 list_tasks.py {branch} [--state DRAFT|PUBLISHED|SYNCED|ALL]
Exit 0: ok / Exit 1: error
"""
import argparse, json, os, re, sys, glob
from common import find_git_root, get_task_dir, get_state_dir, ok, error


STATE_EXT = {
    "PENDING": "pending",
    "DRAFT": "draft",
    "PUBLISHING": "publishing",
    "PUBLISHED": "published",
    "SYNCED": "synced",
}


def get_issue_title(file_path):
    try:
        with open(file_path, encoding="utf-8") as f:
            first_line = f.readline().strip()
        m = re.match(r"^# \S+: (.+)", first_line)
        return m.group(1) if m else "(제목 없음)"
    except Exception:
        return "(읽기 실패)"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("branch")
    parser.add_argument("--state", default="ALL")
    args = parser.parse_args()

    root = find_git_root()
    if not root:
        error("GIT_ROOT_NOT_FOUND", "Git 루트를 찾을 수 없습니다")

    task_dir = get_task_dir(root, args.branch)
    state_dir = get_state_dir(task_dir)

    if not os.path.exists(task_dir):
        error("TASK_DIR_NOT_FOUND", f"작업 디렉토리가 없습니다: {task_dir}")

    state_upper = args.state.upper()
    if state_upper != "ALL" and state_upper not in STATE_EXT:
        error("INVALID_STATE", f"유효하지 않은 상태: {args.state}. 허용: {', '.join(STATE_EXT.keys())}, ALL")

    tasks = []

    if state_upper == "ALL":
        target_states = list(STATE_EXT.keys())
    else:
        target_states = [state_upper]

    for state in target_states:
        ext = STATE_EXT[state]
        pattern = os.path.join(state_dir, f"*.{ext}")
        for state_file in glob.glob(pattern):
            issue_key = os.path.splitext(os.path.basename(state_file))[0]
            md_path = os.path.join(task_dir, issue_key, f"{issue_key}.md")
            title = get_issue_title(md_path) if os.path.exists(md_path) else "(파일 없음)"
            tasks.append({
                "issue": issue_key,
                "state": state,
                "title": title,
                "md_path": md_path if os.path.exists(md_path) else None,
            })

    ok({"branch": args.branch, "state_filter": state_upper, "tasks": tasks, "count": len(tasks)})


if __name__ == "__main__":
    main()
