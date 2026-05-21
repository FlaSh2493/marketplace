#!/usr/bin/env python3
"""
PR 제목/본문 생성을 위한 컨텐츠 데이터를 수집한다.
Usage: python3 prepare_pr.py {root} {base_branch} {branch}
Output: JSON {commits, stats, major_areas, suggested_type, suggested_scope, issue_key, issue_keys}
"""
import argparse
import json
import os
import re
import subprocess
import sys


def run(cmd, cwd=None):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return r.stdout.strip(), r.stderr.strip(), r.returncode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root")
    parser.add_argument("base_branch")
    parser.add_argument("branch")
    args = parser.parse_args()

    root = os.path.abspath(args.root)
    base = args.base_branch
    branch = args.branch

    # 커밋 로그
    log_out, _, _ = run(f"git log origin/{base}..HEAD --pretty=format:'%h|%s'", cwd=root)
    commits = []
    for line in log_out.splitlines():
        if "|" in line:
            h, s = line.split("|", 1)
            commits.append({"hash": h.strip("'"), "subject": s})

    # diff stat
    stat_out, _, _ = run(f"git diff --stat origin/{base}...HEAD", cwd=root)
    stats = {"files_changed": 0, "insertions": 0, "deletions": 0}
    last_line = stat_out.splitlines()[-1] if stat_out else ""
    m = re.search(
        r"(\d+) files? changed(?:, (\d+) insertions?\(\+\))?(?:, (\d+) deletions?\(-\))?",
        last_line,
    )
    if m:
        stats["files_changed"] = int(m.group(1) or 0)
        stats["insertions"] = int(m.group(2) or 0)
        stats["deletions"] = int(m.group(3) or 0)

    # 주요 변경 영역 (상위 5개)
    numstat_out, _, _ = run(f"git diff --numstat origin/{base}...HEAD", cwd=root)
    major_areas = []
    for line in numstat_out.splitlines():
        parts = line.split("\t")
        if len(parts) == 3:
            added = int(parts[0]) if parts[0].isdigit() else 0
            deleted = int(parts[1]) if parts[1].isdigit() else 0
            major_areas.append({"path": parts[2], "line_count": added + deleted})
    major_areas.sort(key=lambda x: x["line_count"], reverse=True)
    major_areas = major_areas[:5]

    # 이슈 키
    seen = set()
    issue_keys = []
    for key in re.findall(r"[A-Z]+-\d+", branch):
        if key not in seen:
            seen.add(key)
            issue_keys.append(key)
    for c in commits:
        for key in re.findall(r"[A-Z]+-\d+", c["subject"]):
            if key not in seen:
                seen.add(key)
                issue_keys.append(key)

    # type/scope 제안
    suggested_type = "feat"
    for c in commits:
        if c["subject"].startswith("fix"):
            suggested_type = "fix"
            break
        elif c["subject"].startswith("refactor"):
            suggested_type = "refactor"
            break

    suggested_scope = ""
    if major_areas:
        top_path = major_areas[0]["path"]
        parts = top_path.split("/")
        if len(parts) > 1:
            if parts[0] in ("src", "packages", "apps", "plugins"):
                suggested_scope = parts[1]
            else:
                suggested_scope = parts[0]

    print(json.dumps({
        "commits": commits,
        "stats": stats,
        "major_areas": major_areas,
        "suggested_type": suggested_type,
        "suggested_scope": suggested_scope,
        "issue_key": issue_keys[0] if issue_keys else "",
        "issue_keys": issue_keys,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
