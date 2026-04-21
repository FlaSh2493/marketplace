#!/usr/bin/env python3
"""
상태별 이슈 목록 출력.
Usage: python3 list_tasks.py [--state PUBLISHED|UNPUBLISHED|ALL]
Exit 0: ok / Exit 1: error
"""
import argparse, json, os, re, sys
from common import find_git_root, get_task_dir, get_state_dir, ok, error


def get_issue_title(file_path):
    try:
        with open(file_path, encoding="utf-8") as f:
            first_line = f.readline().strip()
        m = re.match(r"^# \S+: (.+)", first_line)
        return m.group(1) if m else "(제목 없음)"
    except Exception:
        return "(읽기 실패)"


def list_issue_dirs(task_dir):
    if not os.path.exists(task_dir):
        return []
    return [
        d for d in os.listdir(task_dir)
        if os.path.isdir(os.path.join(task_dir, d))
    ]


def is_published(task_dir, issue_key):
    return os.path.exists(os.path.join(task_dir, issue_key, "published"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", default="ALL")
    args = parser.parse_args()

    root = find_git_root()
    if not root:
        error("GIT_ROOT_NOT_FOUND", "Git 루트를 찾을 수 없습니다")

    task_dir = get_task_dir(root)
    state_dir = get_state_dir(root)

    if not os.path.exists(task_dir):
        error("TASK_DIR_NOT_FOUND", f"작업 디렉토리가 없습니다: {task_dir}")

    state_upper = args.state.upper()
    valid_states = ["PUBLISHED", "UNPUBLISHED", "ALL"]
    if state_upper not in valid_states:
        error("INVALID_STATE", f"유효하지 않은 상태: {args.state}. 허용: {', '.join(valid_states)}")

    tasks = []

    for issue_key in list_issue_dirs(task_dir):
        published = is_published(task_dir, issue_key)
        state = "PUBLISHED" if published else "UNPUBLISHED"
        if state_upper not in ("ALL", state):
            continue
        md_path = os.path.join(task_dir, issue_key, f"{issue_key}.md")
        title = get_issue_title(md_path) if os.path.exists(md_path) else "(파일 없음)"
        tasks.append({
            "issue": issue_key,
            "state": state,
            "title": title,
            "md_path": md_path if os.path.exists(md_path) else None,
        })

    ok({"state_filter": state_upper, "tasks": tasks, "count": len(tasks)})


if __name__ == "__main__":
    main()
