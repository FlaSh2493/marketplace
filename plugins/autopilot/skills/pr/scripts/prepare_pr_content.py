#!/usr/bin/env python3
"""
PR 제목/본문 생성을 위한 컨텐츠 데이터를 추출한다 (토큰 절약용).
Usage: python3 prepare_pr_content.py {worktree_path} {base_branch} {branch}
"""
import argparse
import json
import os
import subprocess
import re
import sys

def run(cmd, cwd=None):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return r.stdout.strip(), r.stderr.strip(), r.returncode

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("worktree_path")
    parser.add_argument("base_branch")
    parser.add_argument("branch")
    args = parser.parse_args()

    wt = os.path.abspath(args.worktree_path)
    base = args.base_branch
    branch = args.branch

    # 1. 커밋 로그 추출
    log_out, _, _ = run(f"git log origin/{base}..HEAD --pretty=format:'%h|%s'", cwd=wt)
    commits = []
    for line in log_out.splitlines():
        if "|" in line:
            h, s = line.split("|", 1)
            commits.append({"hash": h, "subject": s})

    # 2. Diff Stat 추출 및 분석
    stat_out, _, _ = run(f"git diff --stat origin/{base}...HEAD", cwd=wt)
    
    # stats: {files_changed, insertions, deletions}
    stats = {"files_changed": 0, "insertions": 0, "deletions": 0}
    last_line = stat_out.splitlines()[-1] if stat_out else ""
    # " 5 files changed, 100 insertions(+), 50 deletions(-)"
    m = re.search(r"(\d+) files? changed(?:, (\d+) insertions?\(\+\))?(?:, (\d+) deletions?\(-\))?", last_line)
    if m:
        stats["files_changed"] = int(m.group(1) or 0)
        stats["insertions"] = int(m.group(2) or 0)
        stats["deletions"] = int(m.group(3) or 0)

    # 3. 메이저 변경 영역 (상위 5개 파일)
    # diff --numstat: added deleted path
    numstat_out, _, _ = run(f"git diff --numstat origin/{base}...HEAD", cwd=wt)
    major_areas = []
    for line in numstat_out.splitlines():
        parts = line.split("\t")
        if len(parts) == 3:
            added = int(parts[0]) if parts[0].isdigit() else 0
            deleted = int(parts[1]) if parts[1].isdigit() else 0
            path = parts[2]
            major_areas.append({"path": path, "line_count": added + deleted})
    
    major_areas.sort(key=lambda x: x["line_count"], reverse=True)
    major_areas = major_areas[:5]

    # 4. 이슈 키 추출 (브랜치명 또는 커밋 메시지)
    issue_key = ""
    # 브랜치명에서 추출 (예: feature/DC-123-something -> DC-123)
    m_branch = re.search(r"([A-Z]+-\d+)", branch)
    if m_branch:
        issue_key = m_branch.group(1)
    else:
        # 커밋 메시지에서 추출
        for c in commits:
            m_commit = re.search(r"([A-Z]+-\d+)", c["subject"])
            if m_commit:
                issue_key = m_commit.group(1)
                break

    # 5. Type/Scope 제안
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
        # 가장 많이 변한 파일의 상위 폴더를 scope로 제안
        top_path = major_areas[0]["path"]
        path_parts = top_path.split("/")
        if len(path_parts) > 1:
            # src/components/Button.tsx -> components
            # packages/auth/index.ts -> auth
            if path_parts[0] in ["src", "packages", "apps", "plugins"]:
                suggested_scope = path_parts[1]
            else:
                suggested_scope = path_parts[0]

    result = {
        "commits": commits,
        "stats": stats,
        "major_areas": major_areas,
        "suggested_type": suggested_type,
        "suggested_scope": suggested_scope,
        "issue_key": issue_key
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
