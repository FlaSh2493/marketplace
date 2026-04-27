#!/usr/bin/env python3
"""
PR 생성 전 환경 및 브랜치 상태를 통합 검증한다.
Usage: python3 precheck_pr.py --worktree {path} --base {base_branch} --branch {branch}
"""
import argparse
import json
import os
import subprocess
import sys

def run(cmd, cwd=None):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return r.stdout.strip(), r.stderr.strip(), r.returncode

def error(code, reason):
    print(json.dumps({"status": "error", "code": code, "reason": reason}, ensure_ascii=False))
    sys.exit(0)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--worktree", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--branch", required=True)
    args = parser.parse_args()

    wt = os.path.abspath(args.worktree)
    base = args.base
    branch = args.branch

    if not os.path.exists(wt):
        error("WORKTREE_NOT_FOUND", f"워크트리 경로가 존재하지 않습니다: {wt}")

    # 1. Fetch base branch
    _, err, rc = run(f"git fetch origin {base}", cwd=wt)
    if rc != 0:
        error("FETCH_FAILED", f"origin/{base}을 fetch할 수 없습니다: {err}")

    # 2. gh CLI 확인
    _, _, rc = run("gh auth status", cwd=wt)
    if rc != 0:
        error("GH_AUTH_REQUIRED", "gh CLI 인증이 필요하거나 설치되어 있지 않습니다. 'gh auth login'을 실행하세요.")

    # 3. 기존 PR 확인
    pr_url, _, _ = run(f"gh pr list --head '{branch}' --base {base} --state open --json url -q '.[0].url // empty'", cwd=wt)
    if pr_url:
        error("PR_ALREADY_EXISTS", f"이미 열린 PR이 있습니다: {pr_url}")

    # 4. 미커밋 변경사항 확인
    status_out, _, _ = run("git status --porcelain", cwd=wt)
    if status_out:
        error("UNCOMMITTED_CHANGES", "미커밋 변경사항이 있습니다. 먼저 커밋하세요.")

    # 5. 커밋 목록 및 개수 확인
    commits_out, _, _ = run(f"git log origin/{base}..HEAD --oneline", cwd=wt)
    if not commits_out:
        error("NO_NEW_COMMITS", f"{base} 대비 새 커밋이 없습니다.")
    
    commit_count = len(commits_out.splitlines())
    over_limit = commit_count > 50

    # 6. 변경 파일 존재 확인
    diff_out, _, _ = run(f"git diff --name-only origin/{base}...HEAD", cwd=wt)
    if not diff_out:
        error("NO_DIFF", f"커밋은 있지만 {base} 대비 변경된 파일이 없습니다.")

    print(json.dumps({
        "status": "ok",
        "data": {
            "commit_count": commit_count,
            "over_limit": over_limit,
            "branch": branch,
            "base_branch": base
        }
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
