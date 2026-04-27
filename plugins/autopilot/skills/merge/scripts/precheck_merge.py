#!/usr/bin/env python3
"""
머지 전 환경 및 브랜치 상태를 통합 검증한다.
Usage: python3 precheck_merge.py --worktree {path} --target {branch}
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
    parser.add_argument("--target", required=True)
    args = parser.parse_args()

    wt = args.worktree
    target = args.target

    if not os.path.exists(wt):
        error("WORKTREE_NOT_FOUND", f"워크트리 경로가 존재하지 않습니다: {wt}")

    # 1. 진행 중인 작업 확인 (rebase, merge, cherry-pick, revert)
    ops = {
        "rebase": ["rebase-merge", "rebase-apply"],
        "merge": ["MERGE_HEAD"],
        "cherry-pick": ["CHERRY_PICK_HEAD"],
        "revert": ["REVERT_HEAD"]
    }
    
    detected_ops = []
    for op, paths in ops.items():
        for p in paths:
            # git rev-parse --git-path {p} 는 해당 파일의 실제 경로를 반환함
            path_out, _, _ = run(f"git rev-parse --git-path {p}", cwd=wt)
            if path_out and os.path.exists(path_out):
                detected_ops.append(op)
                break
    
    if detected_ops:
        error("ONGOING_OPERATION", f"진행 중인 작업이 있습니다: {', '.join(detected_ops)}. 먼저 완료하거나 중단하세요.")

    # 2. Detached HEAD 확인
    branch, _, _ = run("git rev-parse --abbrev-ref HEAD", cwd=wt)
    if branch == "HEAD":
        error("DETACHED_HEAD", "현재 워크트리가 Detached HEAD 상태입니다.")

    # 3. Target branch 존재 확인 (local 또는 origin)
    _, _, local_rc = run(f"git rev-parse --verify '{target}'", cwd=wt)
    _, _, remote_rc = run(f"git rev-parse --verify 'origin/{target}'", cwd=wt)
    
    if local_rc != 0 and remote_rc != 0:
        error("TARGET_BRANCH_NOT_FOUND", f"대상 브랜치 '{target}'를 로컬 또는 origin에서 찾을 수 없습니다.")

    # 4. Working tree 상태 확인 (최소한의 검증)
    # merge_worktrees.py 내부에서 stash 등을 처리하지만, 여기서도 기본적인 상태를 알림
    status_out, _, _ = run("git status --porcelain", cwd=wt)
    is_clean = (status_out == "")

    print(json.dumps({
        "status": "ok",
        "data": {
            "is_clean": is_clean,
            "current_branch": branch,
            "target_branch": target,
        }
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
