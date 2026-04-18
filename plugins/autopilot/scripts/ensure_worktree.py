#!/usr/bin/env python3
"""
브랜치명으로 워크트리를 보장한다. 없으면 생성, 있으면 재사용.
Usage: python3 ensure_worktree.py {브랜치명} [--issues PLAT-101 PLAT-102 ...]
Exit 0: ok (data.worktree_path, data.branch, data.issue_doc_root, data.base_branch, data.issues, data.created)
Exit 1: error
"""
import json, os, re, subprocess, sys
from pathlib import Path


def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.stdout.strip(), r.stderr.strip(), r.returncode


def ok(data):
    wp = data.get("worktree_path", "")
    created = data.get("created", False)
    branch = data.get("branch", "")
    issues = data.get("issues", [])
    if wp:
        action = "생성" if created else "재사용"
        issues_str = ", ".join(issues) if issues else "없음"
        data["display"] = (
            f"┌─────────────────────────────────────────────\n"
            f"│ 워크트리 {action} 완료\n"
            f"│ 브랜치: {branch}\n"
            f"│ 경로:   {wp}\n"
            f"│ 이슈:   {issues_str}\n"
            f"└─────────────────────────────────────────────"
        )
        data["instructions"] = (
            f"모든 코드 파일 작업에 이 경로를 사용하라: "
            f"Read/Edit/Write → {wp}/파일경로, "
            f"Glob/Grep path → {wp}, "
            f"Bash/git → cd {wp} && command. "
            f"issue_doc_root는 이슈 문서 전용이다. 코드에 사용 금지."
        )
    print(json.dumps({"status": "ok", "data": data}, ensure_ascii=False))
    sys.exit(0)


def error(code, reason):
    print(json.dumps({"status": "error", "code": code, "reason": reason}, ensure_ascii=False))
    sys.exit(1)


def find_worktree_root(git_root):
    """settings 파일에서 autopilot.worktreeRoot를 탐색, 없으면 기본값 반환.
    상대경로는 설정 파일이 있는 .claude/ 디렉토리 기준으로 resolve."""
    candidates = [
        Path(git_root) / ".claude" / "settings.local.json",
        Path(git_root) / ".claude" / "settings.json",
        Path.home() / ".claude" / "settings.local.json",
        Path.home() / ".claude" / "settings.json",
    ]
    for settings_path in candidates:
        if not settings_path.exists():
            continue
        try:
            data = json.loads(settings_path.read_text())
            raw = data.get("autopilot", {}).get("worktreeRoot")
            if raw:
                p = Path(raw)
                if not p.is_absolute():
                    p = (settings_path.parent / p).resolve()
                return str(p)
        except (json.JSONDecodeError, OSError):
            continue
    return os.path.join(git_root, "worktree")


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
    default, _, rc2 = run("git symbolic-ref refs/remotes/origin/HEAD")
    if rc2 == 0 and default:
        return default.split("/")[-1]
    return "main"


def sanitize_name(branch):
    """브랜치명을 디렉토리명 허용 형식으로 변환 (최대 64자, 영문/숫자/점/밑줄/대시)"""
    name = re.sub(r"[^a-zA-Z0-9._-]", "-", branch)
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


def read_autopilot_meta(worktree_path):
    """워크트리의 .autopilot 메타 파일 읽기"""
    meta_path = os.path.join(worktree_path, ".autopilot")
    if os.path.exists(meta_path):
        try:
            return json.loads(Path(meta_path).read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def write_autopilot_meta(worktree_path, issues, base_branch, branch=None):
    """워크트리에 .autopilot 메타 파일 저장"""
    meta_path = os.path.join(worktree_path, ".autopilot")
    data = {"issues": issues, "base_branch": base_branch}
    if branch:
        data["branch"] = branch
    Path(meta_path).write_text(json.dumps(data, ensure_ascii=False, indent=2))


def main():
    # 인수 파싱: {브랜치명} [--issues KEY1 KEY2 ...] [--find-only]
    args = sys.argv[1:]
    if not args:
        error("MISSING_ARGS", "사용법: ensure_worktree.py {브랜치명} [--issues PLAT-101 ...] [--find-only]")

    find_only = "--find-only" in args
    args = [a for a in args if a != "--find-only"]

    branch = args[0]
    issues = []
    if "--issues" in args:
        idx = args.index("--issues")
        issues = args[idx + 1:]

    root = find_git_root()
    if not root:
        error("GIT_ROOT_NOT_FOUND", "Git 루트를 찾을 수 없습니다")

    current_branch = get_current_branch()

    name = sanitize_name(branch)
    worktree_root = find_worktree_root(root)
    worktree_path = os.path.join(worktree_root, name)

    base = {"worktree_path": worktree_path, "branch": branch,
            "issue_doc_root": root, "base_branch": current_branch, "issues": issues}

    # 이미 존재하는 워크트리인지 확인
    worktrees = list_worktrees(root)
    branch_ref = f"refs/heads/{branch}"

    # 경로 일치 또는 브랜치 일치로 기존 워크트리 탐색
    existing_path = None
    if worktree_path in worktrees:
        existing_path = worktree_path
    else:
        for wt_path, wt_branch in worktrees.items():
            if wt_branch == branch_ref or wt_branch.endswith(f"/{branch}"):
                existing_path = wt_path
                break

    if existing_path:
        if os.path.isdir(existing_path):
            # 기존 .autopilot에서 이슈키 읽기 (새로 전달된 이슈 없으면 기존 유지)
            meta = read_autopilot_meta(existing_path)
            resolved_issues = issues if issues else meta.get("issues", [])
            if issues:
                # 새 이슈 전달 시 메타 업데이트
                write_autopilot_meta(existing_path, resolved_issues, current_branch, branch)
            ok({**base, "worktree_path": existing_path, "issues": resolved_issues, "created": False})
        else:
            # registry에는 있지만 디렉토리가 없음 → stale 항목 제거 후 재생성
            run("git worktree prune")
    elif find_only:
        error("WORKTREE_NOT_FOUND", f"워크트리가 없습니다: {branch}")

    # --find-only는 생성하지 않음
    if find_only:
        error("WORKTREE_NOT_FOUND", f"워크트리가 없습니다: {branch}")

    # 없으면 생성
    parent_dir = os.path.dirname(worktree_path)
    os.makedirs(parent_dir, exist_ok=True)

    # 브랜치가 이미 있는지 확인
    _, _, rc = run(f"git rev-parse --verify '{branch}'")
    if rc == 0:
        _, err, rc2 = run(f"git worktree add '{worktree_path}' '{branch}'")
    else:
        _, err, rc2 = run(f"git worktree add -b '{branch}' '{worktree_path}'")

    if rc2 != 0:
        try:
            if os.path.isdir(worktree_path) and not os.listdir(worktree_path):
                os.rmdir(worktree_path)
        except OSError:
            pass
        error("WORKTREE_CREATE_FAILED", err)

    # .autopilot 메타 저장
    write_autopilot_meta(worktree_path, issues, current_branch, branch)

    ok({**base, "created": True})


if __name__ == "__main__":
    main()
