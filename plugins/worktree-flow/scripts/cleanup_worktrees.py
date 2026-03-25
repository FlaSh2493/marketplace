#!/usr/bin/env python3
"""
머지 완료 후 워크트리 정리. 브랜치는 태그로 보존 후 삭제.
Usage: python3 cleanup_worktrees.py {feature} --issues {PLAT-101} {PLAT-102} ...
"""
import argparse, json, os, sys, subprocess
from datetime import datetime

def run(cmd, cwd=None):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return r.stdout.strip(), r.stderr.strip(), r.returncode

def find_git_root():
    common, _, _ = run("git rev-parse --git-common-dir")
    if common:
        return os.path.abspath(os.path.join(common, ".."))
    out, _, _ = run("git rev-parse --show-toplevel")
    return out or None

def ok(data):
    print(json.dumps({"status": "ok", "data": data}, ensure_ascii=False, indent=2))
    sys.exit(0)

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

    wt_base = os.path.join(root, ".worktrees")
    cleaned = []
    errors = []
    date = datetime.now().strftime("%Y%m%d")

    for issue in args.issues:
        branch = f"{args.feature}--wt-{issue}"
        wt_path = os.path.join(wt_base, issue)
        tag = f"archive/{issue}-wip-{date}"

        # 태그 생성 (WIP 히스토리 보존)
        run(f"git tag '{tag}' '{branch}'", cwd=root)

        # 워크트리 제거
        if os.path.exists(wt_path):
            _, err, code = run(f"git worktree remove '{wt_path}' --force", cwd=root)
            if code != 0:
                errors.append({"issue": issue, "error": f"worktree remove 실패: {err}"})
                continue

        # 브랜치 삭제
        run(f"git branch -D '{branch}'", cwd=root)

        cleaned.append({"issue": issue, "tag": tag})

    ok({
        "feature": args.feature,
        "cleaned": cleaned,
        **({"errors": errors} if errors else {})
    })

if __name__ == "__main__":
    main()
