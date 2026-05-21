#!/usr/bin/env python3
"""
머지 전 dry-run으로 충돌 예상 파일을 감지한다.
Usage: python3 precheck.py --root {path} --source {branch}
Output: JSON {conflict_count, conflict_files: [], is_clean, current_branch}
"""
import argparse
import json
import os
import subprocess
import sys


def run(cmd, cwd=None):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return r.stdout.strip(), r.stderr.strip(), r.returncode


def ok(data):
    print(json.dumps({"status": "ok", "data": data}, ensure_ascii=False))
    sys.exit(0)


def error(code, reason):
    print(json.dumps({"status": "error", "code": code, "reason": reason}, ensure_ascii=False))
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--source", required=True)
    args = parser.parse_args()

    root = os.path.abspath(args.root)
    source = args.source

    # 진행 중인 작업 확인
    for marker in ["MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-merge", "rebase-apply"]:
        out, _, _ = run(f"git rev-parse --git-path {marker}", cwd=root)
        if out and os.path.exists(out):
            error("ONGOING_OPERATION", f"진행 중인 작업이 있습니다: {marker}")

    # Detached HEAD 확인
    branch, _, _ = run("git rev-parse --abbrev-ref HEAD", cwd=root)
    if branch == "HEAD":
        error("DETACHED_HEAD", "Detached HEAD 상태입니다.")

    # source 브랜치 존재 확인
    _, _, rc = run(f"git rev-parse --verify '{source}'", cwd=root)
    _, _, rc2 = run(f"git rev-parse --verify 'origin/{source}'", cwd=root)
    if rc != 0 and rc2 != 0:
        error("SOURCE_NOT_FOUND", f"브랜치를 찾을 수 없습니다: {source}")

    # dry-run merge
    _, _, _ = run(f"git merge --no-commit --no-ff {source}", cwd=root)

    # 충돌 파일 수집
    out, _, _ = run("git diff --name-only --diff-filter=U", cwd=root)
    conflict_files = [f for f in out.splitlines() if f]

    # abort (상태 복구)
    run("git merge --abort", cwd=root)

    # working tree 상태
    status_out, _, _ = run("git status --porcelain", cwd=root)

    ok({
        "current_branch": branch,
        "source": source,
        "conflict_count": len(conflict_files),
        "conflict_files": conflict_files,
        "is_clean": not bool(status_out),
    })


if __name__ == "__main__":
    main()
