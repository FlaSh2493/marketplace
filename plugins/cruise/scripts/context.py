#!/usr/bin/env python3
"""
CWD → 컨텍스트 JSON 출력. 모든 cruise 스킬의 진입점.

Usage: python3 context.py
Output: JSON {root, branch, key, key_source, base_branch, base_source,
              task_path?, has_uncommitted, has_pr, pr_number?, repo}
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path


def run(cmd, cwd=None):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return r.stdout.strip(), r.stderr.strip(), r.returncode


def slug(branch: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", branch).strip("-").lower()


def main():
    # 1. Git root + branch
    root, _, rc = run("git rev-parse --show-toplevel")
    if rc != 0:
        print(json.dumps({"error": "NOT_A_GIT_REPO"}))
        sys.exit(1)

    branch, _, _ = run("git rev-parse --abbrev-ref HEAD", cwd=root)

    # 2. KEY
    m = re.search(r"[A-Z]+-\d+", branch)
    if m:
        key = m.group(0)
        key_source = "issue"
    else:
        key = slug(branch)
        key_source = "slug"

    # 3. base_branch (우선순위 체인)
    base_branch = None
    base_source = "unknown"

    # 3-1. gh pr view
    out, _, rc = run("gh pr view --json baseRefName -q .baseRefName", cwd=root)
    if rc == 0 and out:
        base_branch = out
        base_source = "pr"

    # 3-2. upstream
    if not base_branch:
        out, _, rc = run("git rev-parse --abbrev-ref @{upstream}", cwd=root)
        if rc == 0 and out and "/" in out:
            base_branch = out.split("/", 1)[1]
            base_source = "upstream"

    # 3-3. reflog "Created from"
    if not base_branch:
        out, _, _ = run(f"git reflog show --format='%gs' {branch}", cwd=root)
        for line in out.splitlines():
            m2 = re.search(r"[Cc]reated from (.+)", line)
            if m2:
                base_branch = m2.group(1).strip()
                base_source = "reflog"
                break

    # 3-4. heuristic: 후보 풀 중 commit 수 최소
    if not base_branch:
        candidates = ["main", "develop", "master"]
        out, _, _ = run("git branch -r --format='%(refname:short)'", cwd=root)
        for b in out.splitlines():
            b = b.strip()
            if b.startswith("origin/release/"):
                cand = b.replace("origin/", "")
                if cand not in candidates:
                    candidates.append(cand)

        best_count = None
        best_cand = None
        for cand in candidates:
            out, _, rc = run(f"git rev-list --count {cand}..HEAD", cwd=root)
            if rc == 0 and out.isdigit():
                count = int(out)
                if best_count is None or count < best_count:
                    best_count = count
                    best_cand = cand

        if best_cand:
            base_branch = best_cand
            base_source = "heuristic"

    # 4. task_path
    task_path = None
    tasks_dir = Path.home() / "Documents" / "tasks" / key
    candidate = tasks_dir / "task.md"
    if candidate.exists():
        task_path = str(candidate)

    # 5. uncommitted
    out, _, _ = run("git status --porcelain", cwd=root)
    has_uncommitted = bool(out)

    # 6. PR
    out, _, rc = run("gh pr view --json number -q .number", cwd=root)
    has_pr = rc == 0 and bool(out)
    pr_number = int(out) if has_pr and out.isdigit() else None

    # 7. repo
    out, _, rc = run("gh repo view --json nameWithOwner -q .nameWithOwner", cwd=root)
    repo = out if rc == 0 else ""

    result = {
        "root": root,
        "branch": branch,
        "key": key,
        "key_source": key_source,
        "base_branch": base_branch,
        "base_source": base_source,
        "has_uncommitted": has_uncommitted,
        "has_pr": has_pr,
        "repo": repo,
    }
    if task_path:
        result["task_path"] = task_path
    if pr_number is not None:
        result["pr_number"] = pr_number

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
