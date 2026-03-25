#!/usr/bin/env python3
"""
피처 브랜치의 모든 워크트리 WIP 커밋 목록 분석.
Usage: python3 analyze_wip.py {feature}
"""
import json, os, sys, subprocess

def run(cmd, cwd=None):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return r.stdout.strip(), r.returncode

def find_git_root():
    common, _ = run("git rev-parse --git-common-dir")
    if common:
        return os.path.abspath(os.path.join(common, ".."))
    out, _ = run("git rev-parse --show-toplevel")
    return out or None

def ok(data):
    print(json.dumps({"status": "ok", "data": data}, ensure_ascii=False, indent=2))
    sys.exit(0)

def error(code, reason):
    print(json.dumps({"status": "error", "code": code, "reason": reason}, ensure_ascii=False))
    sys.exit(1)

def main():
    if len(sys.argv) < 2:
        error("MISSING_ARGS", "사용법: analyze_wip.py {feature}")

    feature = sys.argv[1]
    root = find_git_root()
    if not root:
        error("GIT_ROOT_NOT_FOUND", "Git 루트를 찾을 수 없습니다")

    # 해당 피처의 워크트리 브랜치 목록
    branches_out, _ = run("git branch --list", cwd=root)
    prefix = f"{feature}--wt-"
    wt_branches = [b.strip().lstrip("* ") for b in branches_out.split("\n")
                   if b.strip().lstrip("* ").startswith(prefix)]

    if not wt_branches:
        error("NO_WORKTREE_BRANCHES", f"'{feature}'의 워크트리 브랜치가 없습니다")

    commits_by_issue = {}
    for branch in wt_branches:
        issue = branch[len(prefix):]
        base, _ = run(f"git merge-base '{feature}' '{branch}'", cwd=root)
        if not base:
            continue
        log_out, _ = run(f"git log {base}..{branch} --oneline --reverse", cwd=root)
        commits = [line for line in log_out.split("\n") if line.strip()]
        diff_stat, _ = run(f"git diff {base}..{branch} --stat", cwd=root)
        commits_by_issue[issue] = {
            "branch": branch,
            "base": base,
            "commits": commits,
            "wip_count": sum(1 for c in commits if "WIP(" in c),
            "diff_stat": diff_stat.split("\n")[-1].strip() if diff_stat else ""
        }

    ok({"feature": feature, "commits_by_issue": commits_by_issue})

if __name__ == "__main__":
    main()
