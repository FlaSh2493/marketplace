#!/usr/bin/env python3
"""
이슈 워크트리를 보장한다. 없으면 생성, 있으면 재사용.
Usage: python3 ensure_worktree.py {issue_key}
Exit 0: ok (data.worktree_path, data.branch, data.root_path, data.base_branch, data.created)
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


def get_current_branch():
    branch, _, rc = run("git rev-parse --abbrev-ref HEAD")
    if rc == 0 and branch and branch != "HEAD":
        return branch
    # detached HEAD 또는 실패 시 기본 브랜치 탐색
    default, _, rc2 = run("git symbolic-ref refs/remotes/origin/HEAD")
    if rc2 == 0 and default:
        return default.split("/")[-1]
    return "main"


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

    current_branch = get_current_branch()

    # 워크트리 브랜치 안에서 실행되면 에러 — 잘못된 base로 분기됨
    if current_branch.startswith("worktree-"):
        error("ALREADY_IN_WORKTREE",
              f"현재 워크트리 브랜치({current_branch}) 안에서 실행할 수 없습니다. "
              "메인/피처 브랜치 세션에서 실행하세요.")

    name = sanitize_name(issue_key)
    worktree_path = os.path.join(root, ".claude", "worktrees", name)
    branch = f"worktree-{name}"

    base = {"worktree_path": worktree_path, "branch": branch,
            "root_path": root, "base_branch": current_branch}

    # 이미 존재하는 워크트리인지 확인
    worktrees = list_worktrees(root)
    if worktree_path in worktrees:
        if os.path.isdir(worktree_path):
            ok({**base, "created": False})
        else:
            # registry에는 있지만 디렉토리가 없음 (수동 삭제 등) → stale 항목 제거 후 재생성
            run("git worktree prune")

    # 없으면 생성
    parent_dir = os.path.dirname(worktree_path)
    os.makedirs(parent_dir, exist_ok=True)

    # 브랜치가 이미 있는지 확인
    _, _, rc = run(f"git rev-parse --verify '{branch}'")
    if rc == 0:
        # 브랜치 있음 → 워크트리만 연결
        _, err, rc2 = run(f"git worktree add '{worktree_path}' '{branch}'")
    else:
        # 브랜치 없음 → 새로 생성
        _, err, rc2 = run(f"git worktree add -b '{branch}' '{worktree_path}'")

    if rc2 != 0:
        # 빈 디렉토리가 생성됐을 수 있으므로 정리
        try:
            if os.path.isdir(worktree_path) and not os.listdir(worktree_path):
                os.rmdir(worktree_path)
        except OSError:
            pass
        error("WORKTREE_CREATE_FAILED", err)

    ok({**base, "created": True})


if __name__ == "__main__":
    main()
