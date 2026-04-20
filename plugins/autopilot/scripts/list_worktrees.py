#!/usr/bin/env python3
"""
워크트리 목록 조회 및 상세 정보(이슈, 커밋 수 등) 수집.
Usage: python3 list_worktrees.py [--require-autopilot] [--infer-common-base] [--exclude-main]
"""
import json, os, subprocess, sys
from pathlib import Path

def run(cmd, cwd=None):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return r.stdout.strip(), r.stderr.strip(), r.returncode

def get_autopilot_meta(wt_path):
    meta_path = Path(wt_path) / ".autopilot"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
            # legacy: issues[] → issue 단일값
            if "issues" in meta and "issue" not in meta:
                issues_list = meta.get("issues", [])
                meta["issue"] = issues_list[0] if issues_list else ""
            return meta
        except (json.JSONDecodeError, OSError):
            pass
    return {}

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-autopilot", action="store_true")
    parser.add_argument("--infer-common-base", action="store_true")
    parser.add_argument("--exclude-main", action="store_true", default=True)
    args = parser.parse_args()

    out, _, rc = run("git worktree list --porcelain")
    if rc != 0:
        print(json.dumps({"status": "error", "reason": "GIT_WORKTREE_LIST_FAILED"}))
        sys.exit(1)

    all_wt = []
    current = {}
    for line in out.splitlines():
        if line.startswith("worktree "):
            if current: all_wt.append(current)
            current = {"path": line[9:].strip()}
        elif line.startswith("branch "):
            current["branch"] = line[7:].strip().replace("refs/heads/", "")
        elif line.startswith("detached"):
            current["branch"] = "DETACHED"
    if current: all_wt.append(current)

    if not all_wt:
        print(json.dumps({"status": "ok", "data": {"worktrees": []}}))
        return

    main_root = all_wt[0]["path"]
    main_branch = all_wt[0].get("branch", "unknown")

    if args.exclude_main:
        targets = all_wt[1:]
    else:
        targets = all_wt

    res_worktrees = []
    base_branches = set()

    for wt in targets:
        path = wt["path"]
        meta = get_autopilot_meta(path)

        if args.require_autopilot and not meta:
            continue

        branch = wt.get("branch", "unknown")
        issue = meta.get("issue", "")
        base_branch = meta.get("base_branch")

        if base_branch:
            base_branches.add(base_branch)

        commit_count = 0
        if base_branch:
            c, _, _ = run(f"git log {base_branch}..HEAD --oneline", cwd=path)
            commit_count = len(c.splitlines()) if c else 0
        else:
            c, _, _ = run("git rev-list --count HEAD", cwd=path)
            commit_count = int(c) if c else 0

        last_commit, _, _ = run("git log -1 --format='%ci'", cwd=path)

        res_worktrees.append({
            "path": path,
            "branch": branch,
            "issue": issue,
            "base_branch": base_branch,
            "commits": commit_count,
            "last_commit": last_commit,
        })

    common_base = None
    candidates = sorted(list(base_branches))
    if args.infer_common_base:
        if len(candidates) == 1:
            common_base = candidates[0]
        elif len(candidates) == 0:
            common_base = None

    print(json.dumps({
        "status": "ok",
        "data": {
            "main_root": main_root,
            "main_branch": main_branch,
            "worktrees": res_worktrees,
            "common_base_branch": common_base,
            "base_branch_candidates": candidates,
        },
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()
