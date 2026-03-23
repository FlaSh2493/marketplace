#!/usr/bin/env python3
"""
모든 워크트리 상태를 조회한다.
Usage: python3 status.py
"""
import argparse, json, subprocess, sys

def run(cmd, cwd=None):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return r.stdout.strip(), r.returncode

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=None)
    args = parser.parse_args()

    root = args.root
    if not root:
        root, _ = run("git rev-parse --show-toplevel")
        if not root:
            print(json.dumps({"error": "Git 루트를 찾을 수 없습니다"})); sys.exit(1)

    out, _ = run("git worktree list --porcelain", cwd=root)
    if not out:
        print(json.dumps({"worktrees": []})); return

    worktrees, current = [], {}
    for line in out.split("\n"):
        if line.startswith("worktree "):
            if current: worktrees.append(current)
            current = {"path": line.split(" ", 1)[1]}
        elif line.startswith("HEAD "): current["head"] = line.split(" ", 1)[1][:8]
        elif line.startswith("branch "): current["branch"] = line.split(" ", 1)[1].replace("refs/heads/", "")
        elif line == "bare": current["bare"] = True
    if current: worktrees.append(current)

    for wt in worktrees:
        if wt.get("bare"): continue
        status_out, _ = run("git status --porcelain", cwd=wt["path"])
        wt["changes"] = len(status_out.split("\n")) if status_out else 0
        branch = wt.get("branch", "")
        if "--wt-" in branch:
            feature = branch.split("--wt-")[0]
            count_out, code = run(f"git rev-list --count '{feature}..{branch}'", cwd=wt["path"])
            wt["commits_ahead"] = int(count_out) if code == 0 and count_out else 0

    print(json.dumps({"worktrees": worktrees}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
