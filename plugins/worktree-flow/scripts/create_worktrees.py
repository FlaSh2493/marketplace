#!/usr/bin/env python3
"""
피처 브랜치에서 워크트리를 일괄 생성한다.
Usage: python3 create_worktrees.py {피처브랜치} {작업1} {작업2} ...
"""
import argparse, json, os, subprocess, sys, re

def run(cmd, cwd=None):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return r.stdout.strip(), r.stderr.strip(), r.returncode

def find_git_root():
    common_dir, _, _ = run("git rev-parse --git-common-dir")
    if common_dir:
        return os.path.abspath(os.path.join(common_dir, ".."))
    out, _, _ = run("git rev-parse --show-toplevel")
    return out or None

def get_current_branch(root):
    out, _, _ = run("git rev-parse --abbrev-ref HEAD", cwd=root)
    return out

def get_tasks_from_md(root, feature):
    """fe-task-extractor 구조: .docs/task/{feature}/.state/*.published 기준으로 이슈 탐색"""
    tasks = []
    for base in [os.path.join(root, ".docs", "task"), os.path.join(root, "docs", "task")]:
        state_dir = os.path.join(base, feature.replace("/", os.sep), ".state")
        if not os.path.isdir(state_dir):
            continue
        for fname in sorted(os.listdir(state_dir)):
            if not fname.endswith(".published") and not fname.endswith(".synced"):
                continue
            issue_key = fname.rsplit(".", 1)[0]  # 확장자 제거
            if issue_key not in tasks:
                tasks.append(issue_key)
    return tasks

GITIGNORE_ENTRIES = [
    "# worktree-flow",
    ".worktrees/",
    ".wt/",

]

def ensure_gitignore(root):
    gitignore_path = os.path.join(root, ".gitignore")
    existing = ""
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r", encoding="utf-8") as f:
            existing = f.read()
    to_add = [e for e in GITIGNORE_ENTRIES if e not in existing]
    if to_add:
        with open(gitignore_path, "a", encoding="utf-8") as f:
            f.write("\n" + "\n".join(to_add) + "\n")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("feature", nargs="?", default=".")
    parser.add_argument("tasks", nargs="*")
    parser.add_argument("--root", default=None)
    args = parser.parse_args()

    root = args.root or find_git_root()
    if not root:
        print(json.dumps({"status": "error", "code": "GIT_ROOT_NOT_FOUND", "reason": "Git 루트를 찾을 수 없습니다"}))
        sys.exit(1)

    feature = args.feature
    if feature == ".":
        feature = get_current_branch(root)

    tasks = args.tasks
    if not tasks:
        tasks = get_tasks_from_md(root, feature)
        if not tasks:
            print(json.dumps({
                "status": "error",
                "code": "NO_TASKS_FOUND",
                "reason": f"'.docs/task/{feature}/.state/'에 PUBLISHED 이슈가 없고, 인자로도 전달되지 않았습니다. /fe-task-extractor:fetch를 먼저 실행하세요."
            }, ensure_ascii=False))
            sys.exit(1)

        print(json.dumps({
            "status": "ok",
            "data": {
                "mode": "selection",
                "feature": feature,
                "tasks": tasks,
                "message": f"'{feature}' 관련 문서에서 발견된 이슈들입니다. 워크트리를 생성할 이슈를 선택해 주세요."
            }
        }, ensure_ascii=False, indent=2))
        return

    # .gitignore 항목 보장
    ensure_gitignore(root)

    # 피처 브랜치 확인/생성
    out, _, _ = run(f"git branch --list '{feature}'", cwd=root)
    if not out:
        run("git fetch upstream", cwd=root)
        base, _, _ = run("git rev-parse upstream/main 2>/dev/null || git rev-parse upstream/develop 2>/dev/null || git rev-parse origin/main", cwd=root)
        if not base:
            print(json.dumps({"status": "error", "code": "BASE_BRANCH_NOT_FOUND", "reason": "base 브랜치를 찾을 수 없습니다"}))
            sys.exit(1)
        run(f"git branch '{feature}' {base}", cwd=root)

    wt_base = os.path.join(root, ".worktrees")
    os.makedirs(wt_base, exist_ok=True)

    # .wt/ 디렉토리 보장
    wt_state_dir = os.path.join(root, ".wt")
    os.makedirs(wt_state_dir, exist_ok=True)

    results, errors = [], []
    for task in tasks:
        branch = f"{feature}--wt-{task}"
        wt_path = os.path.join(wt_base, task)

        if os.path.exists(wt_path):
            errors.append({"name": task, "error": f"경로 이미 존재: {wt_path}"})
            continue

        existing, _, _ = run(f"git branch --list '{branch}'", cwd=root)
        if existing:
            _, err, code = run(f"git worktree add '{wt_path}' '{branch}'", cwd=root)
        else:
            _, err, code = run(f"git worktree add -b '{branch}' '{wt_path}' '{feature}'", cwd=root)

        if code != 0 and err and "already" not in err.lower():
            errors.append({"name": task, "error": err})
            continue

        results.append({"name": task, "branch": branch, "path": wt_path})

    print(json.dumps({
        "status": "ok",
        "data": {
            "feature": feature,
            "root": root,
            "worktrees": results,
            **({"errors": errors} if errors else {})
        }
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
