#!/usr/bin/env python3
"""
브랜치명으로 워크트리를 제거하고 로컬 브랜치를 삭제한다.
Usage: python3 remove_worktree.py {브랜치명} [--force]
Exit 0: ok (data.branch, data.worktree_path, data.branch_deleted)
Exit 1: error
"""
import json, subprocess, sys
from pathlib import Path


def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.stdout.strip(), r.stderr.strip(), r.returncode


def ok(data):
    branch = data.get("branch", "")
    wp = data.get("worktree_path", "")
    branch_deleted = data.get("branch_deleted", False)
    data["display"] = (
        f"┌─────────────────────────────────────────────\n"
        f"│ 워크트리 제거 완료\n"
        f"│ 브랜치: {branch}\n"
        f"│ 경로:   {wp}\n"
        f"│ 브랜치 삭제: {'완료' if branch_deleted else '실패(원격 미병합 또는 없음)'}\n"
        f"└─────────────────────────────────────────────"
    )
    print(json.dumps({"status": "ok", "data": data}, ensure_ascii=False))
    sys.exit(0)


def dirty(worktree_path, files):
    print(json.dumps({
        "status": "dirty",
        "worktree_path": worktree_path,
        "files": files,
    }, ensure_ascii=False))
    sys.exit(1)


def error(code, reason):
    print(json.dumps({"status": "error", "code": code, "reason": reason}, ensure_ascii=False))
    sys.exit(1)


def find_worktree_path(branch):
    """브랜치명으로 워크트리 경로를 탐색한다."""
    out, _, rc = run("git worktree list --porcelain")
    if rc != 0:
        return None

    branch_ref = f"refs/heads/{branch}"
    current = {}
    for line in out.splitlines():
        if line.startswith("worktree "):
            current = {"path": line[9:].strip()}
        elif line.startswith("branch "):
            current["branch"] = line[7:].strip()
            if current.get("branch") in (branch_ref, branch):
                return current["path"]
    return None


def main():
    args = sys.argv[1:]
    if not args:
        error("MISSING_ARGS", "사용법: remove_worktree.py {브랜치명} [--force]")

    force = "--force" in args
    args = [a for a in args if a != "--force"]
    branch = args[0]

    worktree_path = find_worktree_path(branch)
    if not worktree_path:
        error("WORKTREE_NOT_FOUND", f"워크트리를 찾을 수 없습니다: {branch}")

    # 주 워크트리(메인 레포)는 제거 불가
    out, _, _ = run("git worktree list --porcelain")
    main_path = ""
    for line in out.splitlines():
        if line.startswith("worktree "):
            main_path = line[9:].strip()
            break
    if worktree_path == main_path:
        error("MAIN_WORKTREE", "주 워크트리는 제거할 수 없습니다")

    # 미커밋 변경 확인
    if not force:
        status_out, _, _ = run(f"git -C '{worktree_path}' status --porcelain")
        if status_out:
            files = status_out.splitlines()
            dirty(worktree_path, files)

    # 워크트리 제거
    _, err, rc = run(f"git worktree remove '{worktree_path}'" + (" --force" if force else ""))
    if rc != 0:
        error("WORKTREE_REMOVE_FAILED", err)

    # 로컬 브랜치 삭제 (-d: 병합된 경우만)
    _, _, rc_del = run(f"git branch -d '{branch}'")
    branch_deleted = rc_del == 0

    run("git worktree prune")

    ok({"branch": branch, "worktree_path": worktree_path, "branch_deleted": branch_deleted})


if __name__ == "__main__":
    main()
