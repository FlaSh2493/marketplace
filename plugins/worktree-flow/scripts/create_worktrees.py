#!/usr/bin/env python3
"""
피처 브랜치에서 워크트리를 일괄 생성한다.
Usage: python3 create_worktrees.py {피처브랜치} {작업1} {작업2} ...
"""
import argparse, json, os, subprocess, sys

def run(cmd, cwd=None):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return r.stdout.strip(), r.stderr.strip(), r.returncode

def find_git_root():
    out, _, _ = run("git rev-parse --show-toplevel")
    return out or None

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("feature")
    parser.add_argument("tasks", nargs="+")
    parser.add_argument("--root", default=None)
    args = parser.parse_args()

    root = args.root or find_git_root()
    if not root:
        print(json.dumps({"error": "Git 루트를 찾을 수 없습니다"}))
        sys.exit(1)

    # 피처 브랜치 확인/생성
    out, _, _ = run(f"git branch --list '{args.feature}'", cwd=root)
    if not out:
        run("git fetch upstream", cwd=root)
        base, _, _ = run("git rev-parse upstream/main 2>/dev/null || git rev-parse upstream/develop 2>/dev/null || git rev-parse origin/main", cwd=root)
        if not base:
            print(json.dumps({"error": "base 브랜치를 찾을 수 없습니다"}))
            sys.exit(1)
        run(f"git branch '{args.feature}' {base}", cwd=root)

    wt_base = os.path.join(root, ".worktrees")
    os.makedirs(wt_base, exist_ok=True)

    results, errors = [], []
    for task in args.tasks:
        branch = f"{args.feature}--wt-{task}"
        wt_path = os.path.join(wt_base, task)

        if os.path.exists(wt_path):
            errors.append({"name": task, "error": f"경로 존재: {wt_path}"})
            continue

        existing, _, _ = run(f"git branch --list '{branch}'", cwd=root)
        if existing:
            _, err, _ = run(f"git worktree add '{wt_path}' '{branch}'", cwd=root)
        else:
            _, err, _ = run(f"git worktree add -b '{branch}' '{wt_path}' '{args.feature}'", cwd=root)

        if err and "already" not in err.lower():
            errors.append({"name": task, "error": err})
        else:
            results.append({"name": task, "branch": branch, "path": wt_path})

    output = {"feature": args.feature, "root": root, "worktrees": results}
    if errors:
        output["errors"] = errors
    print(json.dumps(output, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
