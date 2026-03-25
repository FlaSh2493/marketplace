#!/usr/bin/env python3
"""
머지 완료 후 워크트리, 브랜치, 상태 파일 정리.
Usage: python3 cleanup_worktrees.py {feature} --issues {PLAT-101} {PLAT-102} ...
"""
import argparse, json, os, sys, subprocess, glob

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

    wt_dir = os.path.join(root, ".wt")
    wt_base = os.path.join(root, ".worktrees")
    cleaned = []
    errors = []

    for issue in args.issues:
        branch = f"{args.feature}--wt-{issue}"
        wt_path = os.path.join(wt_base, issue)

        # 워크트리 제거
        if os.path.exists(wt_path):
            _, err, code = run(f"git worktree remove '{wt_path}' --force", cwd=root)
            if code != 0:
                errors.append({"issue": issue, "error": f"worktree remove 실패: {err}"})
                continue

        # 브랜치 삭제
        run(f"git branch -D '{branch}'", cwd=root)

        # 상태 파일 정리
        for flag in ["approved", "building", "done", "planned"]:
            flag_path = os.path.join(wt_dir, f"{issue}.{flag}")
            if os.path.exists(flag_path):
                os.remove(flag_path)

        cleaned.append(issue)

    # .wt/ 디렉토리가 비었으면 삭제
    if os.path.exists(wt_dir) and not os.listdir(wt_dir):
        os.rmdir(wt_dir)

    ok({
        "feature": args.feature,
        "cleaned": cleaned,
        **({"errors": errors} if errors else {})
    })

if __name__ == "__main__":
    main()
