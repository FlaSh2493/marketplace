#!/usr/bin/env python3
"""
이슈 워크트리를 보장한다. 없으면 생성, 있으면 재사용.
Usage: python3 ensure_worktree.py {issue_key}
Exit 0: ok (data.worktree_path, data.branch, data.created)
Exit 1: error
"""
import json, os, re, subprocess, sys


def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.stdout.strip(), r.stderr.strip(), r.returncode


def ok(data):
    print(json.dumps({"status": "ok", "data": data}, ensure_ascii=False))
    sys.exit(0)


def error(code, reason):
    print(json.dumps({"status": "error", "code": code, "reason": reason}, ensure_ascii=False))
    sys.exit(1)


def find_git_root():
    common, _, rc = run("git rev-parse --git-common-dir")
    if rc == 0 and common:
        return os.path.abspath(os.path.join(common, ".."))
    toplevel, _, rc2 = run("git rev-parse --show-toplevel")
    return toplevel if rc2 == 0 else None


def sanitize_name(issue_key):
    """이슈키를 worktree name 허용 형식으로 변환 (최대 64자, 영문/숫자/점/밑줄/대시)"""
    name = re.sub(r"[^a-zA-Z0-9._-]", "-", issue_key)
    return name[:64]


def list_worktrees(root):
    """현재 워크트리 목록 반환 {path: branch}"""
    out, _, _ = run("git worktree list --porcelain")
    worktrees = {}
    current = {}
    for line in out.splitlines():
        if line.startswith("worktree "):
            current = {"path": line[9:]}
        elif line.startswith("branch "):
            current["branch"] = line[7:]
            worktrees[current["path"]] = current.get("branch", "")
    return worktrees


def main():
    if len(sys.argv) < 2:
        error("MISSING_ARGS", "사용법: ensure_worktree.py {issue_key}")

    issue_key = sys.argv[1]
    root = find_git_root()
    if not root:
        error("GIT_ROOT_NOT_FOUND", "Git 루트를 찾을 수 없습니다")

    name = sanitize_name(issue_key)
    worktree_path = os.path.join(root, ".claude", "worktrees", name)
    branch = f"worktree-{name}"

    # 이미 존재하는 워크트리인지 확인
    worktrees = list_worktrees(root)
    if worktree_path in worktrees:
        ok({"worktree_path": worktree_path, "branch": branch, "created": False})

    # 없으면 생성
    os.makedirs(os.path.dirname(worktree_path), exist_ok=True)

    # 브랜치가 이미 있는지 확인
    _, _, rc = run(f"git rev-parse --verify {branch}")
    if rc == 0:
        # 브랜치 있음 → 워크트리만 연결
        _, err, rc2 = run(f"git worktree add {worktree_path} {branch}")
    else:
        # 브랜치 없음 → 새로 생성
        _, err, rc2 = run(f"git worktree add -b {branch} {worktree_path}")

    if rc2 != 0:
        error("WORKTREE_CREATE_FAILED", err)

    ok({"worktree_path": worktree_path, "branch": branch, "created": True})


if __name__ == "__main__":
    main()
