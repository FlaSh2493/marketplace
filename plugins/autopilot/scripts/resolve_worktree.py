#!/usr/bin/env python3
"""
브랜치 인자 또는 현재 위치를 기반으로 워크트리 정보를 해석한다.
Usage: python3 resolve_worktree.py [branch] [--infer-base-by-commit-count]
"""
import json, os, subprocess, sys
from pathlib import Path

def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.stdout.strip(), r.stderr.strip(), r.returncode

def error(reason, data=None):
    print(json.dumps({"status": "error", "reason": reason, "data": data or {}}, ensure_ascii=False))
    sys.exit(0)

def read_autopilot_meta(worktree_path):
    """legacy issues[] 필드 자동 변환 포함."""
    meta_path = Path(worktree_path) / ".autopilot"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
            if "issues" in meta and "issue" not in meta:
                issues_list = meta.get("issues", [])
                meta["issue"] = issues_list[0] if issues_list else ""
            return meta
        except Exception:
            pass
    return {}

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("branch", nargs="?")
    parser.add_argument("--infer-base-by-commit-count", action="store_true")
    args = parser.parse_args()

    # 1. Main root & Root branch 탐색
    out, _, rc = run("git worktree list --porcelain")
    if rc != 0:
        error("GIT_WORKTREE_LIST_FAILED")

    lines = out.splitlines()
    root_path = ""
    for line in lines:
        if line.startswith("worktree "):
            root_path = line[9:].strip()
            break

    root_branch, _, _ = run(f"git -C '{root_path}' rev-parse --abbrev-ref HEAD")

    # 2. 브랜치 해석
    worktree_path = ""
    resolved_branch = ""

    if args.branch:
        env_root = os.environ.get("CLAUDE_PLUGIN_ROOT", ".")
        script_path = os.path.join(env_root, "scripts", "ensure_worktree.py")
        if not os.path.exists(script_path):
            script_path = os.path.join(os.path.dirname(__file__), "ensure_worktree.py")

        cmd = f"python3 '{script_path}' '{args.branch}' --find-only"
        res_out, _, _ = run(cmd)
        try:
            res = json.loads(res_out)
            if res.get("status") == "ok":
                worktree_path = res["data"]["worktree_path"]
                resolved_branch = res["data"]["branch"]
            else:
                resolved_branch = args.branch
                worktree_path = None
        except Exception:
            resolved_branch = args.branch
            worktree_path = None
    else:
        current_branch, _, _ = run("git rev-parse --abbrev-ref HEAD")
        if current_branch == "HEAD":
            error("DETACHED_HEAD")

        resolved_branch = current_branch
        toplevel, _, _ = run("git rev-parse --show-toplevel")
        worktree_path = toplevel

    # 3. .autopilot 정보 로드
    issue = ""
    base_branch = ""
    if worktree_path:
        meta = read_autopilot_meta(worktree_path)
        issue = meta.get("issue", "")
        base_branch = meta.get("base_branch", "")

    # 4. base_branch 추론 (2순위)
    if not base_branch and args.infer_base_by_commit_count:
        run("git fetch origin develop main")
        dev_count_out, _, _ = run("git log origin/develop..HEAD --oneline | wc -l")
        main_count_out, _, _ = run("git log origin/main..HEAD --oneline | wc -l")
        try:
            dev_count = int(dev_count_out.strip())
            main_count = int(main_count_out.strip())
            if dev_count < main_count:
                base_branch = "develop"
            elif main_count < dev_count:
                base_branch = "main"
            else:
                base_branch = "develop"
        except Exception:
            base_branch = "develop"

    # 5. 가드레일
    if resolved_branch == base_branch:
        error("SAME_BRANCH", {"branch": resolved_branch, "base_branch": base_branch})

    safe_branch = resolved_branch.replace("/", "-")

    result = {
        "status": "ok",
        "data": {
            "worktree_path": worktree_path,
            "branch": resolved_branch,
            "issue": issue,
            "base_branch": base_branch,
            "root_path": root_path,
            "root_branch": root_branch,
            "safe_branch": safe_branch,
        },
    }

    if worktree_path is None:
        result["status"] = "error"
        result["reason"] = "WORKTREE_NOT_FOUND"

    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()
