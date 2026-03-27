#!/usr/bin/env python3
"""
머지 완료 후 워크트리 정리. 워크트리 제거 + 브랜치 삭제.
Usage: python3 cleanup_worktrees.py {feature} --issues {PLAT-101} {PLAT-102} ...
"""
import argparse, json, os, re, sys, subprocess


def run(cmd, cwd=None):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return r.stdout.strip(), r.stderr.strip(), r.returncode


def find_git_root():
    common, _, rc = run("git rev-parse --git-common-dir")
    if rc == 0 and common:
        return os.path.abspath(os.path.join(common, ".."))
    out, _, rc2 = run("git rev-parse --show-toplevel")
    return out if rc2 == 0 else None


def sanitize_name(issue_key):
    name = re.sub(r"[^a-zA-Z0-9._-]", "-", issue_key)
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
    parser.add_argument("--issues", nargs="+", required=True)
    args = parser.parse_args()

    root = find_git_root()
    if not root:
        error("GIT_ROOT_NOT_FOUND", "Git 루트를 찾을 수 없습니다")

    cleaned = []
    errors = []

    for issue in args.issues:
        name = sanitize_name(issue)
        branch = f"worktree-{name}"
        wt_path = os.path.join(root, ".claude", "worktrees", name)

        # 워크트리 제거
        if os.path.exists(wt_path):
            _, err, code = run(f"git worktree remove '{wt_path}' --force", cwd=root)
            if code != 0:
                errors.append({"issue": issue, "error": f"worktree remove 실패: {err}"})
                continue

        # 브랜치 삭제 (워크트리 제거 성공 후에만)
        _, branch_err, branch_code = run(f"git branch -D '{branch}'", cwd=root)
        if branch_code != 0:
            errors.append({"issue": issue, "error": f"브랜치 삭제 실패: {branch_err}"})
            continue
        cleaned.append({"issue": issue})

    ok({
        "feature": args.feature,
        "cleaned": cleaned,
        **({"errors": errors} if errors else {})
    }, has_errors=bool(errors))


if __name__ == "__main__":
    main()
