#!/usr/bin/env python3
"""
머지 완료 후 워크트리 정리. 워크트리 제거 + 브랜치 삭제.
Usage: python3 cleanup_worktrees.py {feature} --branches {브랜치명1} {브랜치명2} ...
"""
import argparse, json, os, re, sys, subprocess
from pathlib import Path


def run(cmd, cwd=None):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return r.stdout.strip(), r.stderr.strip(), r.returncode


def find_git_root():
    common, _, rc = run("git rev-parse --git-common-dir")
    if rc == 0 and common:
        return os.path.abspath(os.path.join(common, ".."))
    out, _, rc2 = run("git rev-parse --show-toplevel")
    return out if rc2 == 0 else None


def find_worktree_root(git_root):
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
    return os.path.join(git_root, ".claude", "worktrees")


def sanitize_name(branch):
    name = re.sub(r"[^a-zA-Z0-9._-]", "-", branch)
    return name[:64]


def ok(data, has_errors=False):
    print(json.dumps({"status": "ok", "data": data}, ensure_ascii=False, indent=2))
    sys.exit(1 if has_errors else 0)


def error(code, reason):
    print(json.dumps({"status": "error", "code": code, "reason": reason}, ensure_ascii=False))
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("feature")
    parser.add_argument("--branches", nargs="+", required=True)
    args = parser.parse_args()

    root = find_git_root()
    if not root:
        error("GIT_ROOT_NOT_FOUND", "Git 루트를 찾을 수 없습니다")

    worktree_root = find_worktree_root(root)
    cleaned = []
    errors = []

    for branch in args.branches:
        name = sanitize_name(branch)
        wt_path = os.path.join(worktree_root, name)

        # 워크트리 제거
        if os.path.exists(wt_path):
            _, err, code = run(f"git worktree remove '{wt_path}' --force", cwd=root)
            if code != 0:
                errors.append({"branch": branch, "error": f"worktree remove 실패: {err}"})
                continue

        # 브랜치 삭제
        _, branch_err, branch_code = run(f"git branch -D '{branch}'", cwd=root)
        if branch_code != 0:
            errors.append({"branch": branch, "error": f"브랜치 삭제 실패: {branch_err}"})
            continue
        cleaned.append({"branch": branch})

    ok({
        "feature": args.feature,
        "cleaned": cleaned,
        **({"errors": errors} if errors else {})
    }, has_errors=bool(errors))


if __name__ == "__main__":
    main()
