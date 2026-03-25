#!/usr/bin/env python3
"""
스킬 실행 전 전제조건 검증. 모든 스킬의 STEP 0에서 호출.
Usage: python3 preflight.py {skill} [{issue}] [{feature}]
Exit 0: ok / Exit 1: error
"""
import json, os, sys, glob, re

def find_git_root():
    import subprocess
    r = subprocess.run("git rev-parse --git-common-dir", shell=True, capture_output=True, text=True)
    common = r.stdout.strip()
    if common:
        return os.path.abspath(os.path.join(common, ".."))
    r2 = subprocess.run("git rev-parse --show-toplevel", shell=True, capture_output=True, text=True)
    return r2.stdout.strip() or None

def ok(data=None):
    print(json.dumps({"status": "ok", "data": data or {}}, ensure_ascii=False))
    sys.exit(0)

def error(code, reason):
    print(json.dumps({"status": "error", "code": code, "reason": reason}, ensure_ascii=False))
    sys.exit(1)

def find_issue_md(root, issue):
    """이슈 md 파일 탐색 (.docs/task/**/{issue}.md 또는 이슈키가 포함된 파일)"""
    patterns = [
        os.path.join(root, ".docs", "task", "**", f"{issue}.md"),
        os.path.join(root, "docs", "task", "**", f"{issue}.md"),
    ]
    for pattern in patterns:
        matches = glob.glob(pattern, recursive=True)
        if matches:
            return matches[0]
    # 파일명이 이슈키가 아닌 경우 내용에서 탐색 (fe-task-extractor 포맷: "- jira: {KEY}")
    for base in [os.path.join(root, ".docs", "task"), os.path.join(root, "docs", "task")]:
        for f in glob.glob(os.path.join(base, "**", "*.md"), recursive=True):
            with open(f, encoding="utf-8") as fh:
                if f"jira: {issue}" in fh.read():
                    return f
    return None

def has_plan_section(md_path):
    with open(md_path, encoding="utf-8") as f:
        return "## 플랜" in f.read()

def main():
    args = sys.argv[1:]
    if not args:
        error("MISSING_ARGS", "사용법: preflight.py {skill} [{issue}]")

    skill = args[0]
    issue = args[1] if len(args) > 1 else None

    root = find_git_root()
    if not root:
        error("GIT_ROOT_NOT_FOUND", "Git 루트를 찾을 수 없습니다")

    wt_dir = os.path.join(root, ".wt")

    if skill == "init-hooks":
        settings = os.path.join(root, ".claude", "settings.json")
        if os.path.exists(settings):
            import json as _json
            with open(settings) as f:
                data = _json.load(f)
            hooks = data.get("hooks", {}).get("Stop", [])
            for h in hooks:
                for action in h.get("actions", []):
                    if "wip_commit" in action.get("command", ""):
                        ok({"already_registered": True})
        ok({"already_registered": False})

    elif skill == "create":
        ok()

    elif skill == "plan":
        if not issue:
            error("MISSING_ISSUE", "plan 스킬에는 이슈 키가 필요합니다")
        md = find_issue_md(root, issue)
        if not md:
            error("PRECONDITION_FAILED", f"{issue}.md 파일이 없습니다. create 스킬을 먼저 실행하세요.")
        approved = os.path.join(wt_dir, f"{issue}.approved")
        if os.path.exists(approved):
            error("PRECONDITION_FAILED", f"{issue}는 이미 승인된 상태입니다. plan을 다시 실행할 수 없습니다.")
        ok({"md_path": md})

    elif skill == "review":
        if not issue:
            error("MISSING_ISSUE", "review 스킬에는 이슈 키가 필요합니다")
        md = find_issue_md(root, issue)
        if not md:
            error("PRECONDITION_FAILED", f"{issue}.md 파일이 없습니다.")
        has_plan = has_plan_section(md)
        approved = os.path.join(wt_dir, f"{issue}.approved")
        current_state = "APPROVED" if os.path.exists(approved) else ("PLANNED" if has_plan else "READY")
        ok({"md_path": md, "has_plan": has_plan, "current_state": current_state})

    elif skill == "build":
        if not issue:
            error("MISSING_ISSUE", "build 스킬에는 이슈 키가 필요합니다")
        approved = os.path.join(wt_dir, f"{issue}.approved")
        if not os.path.exists(approved):
            error("PRECONDITION_FAILED", f"{issue}가 승인되지 않았습니다. /worktree-flow:review {issue} 를 먼저 실행하세요.")
        building = os.path.join(wt_dir, f"{issue}.building")
        if os.path.exists(building):
            error("PRECONDITION_FAILED", f"{issue}는 이미 구현 중입니다.")
        done = os.path.join(wt_dir, f"{issue}.done")
        if os.path.exists(done):
            error("PRECONDITION_FAILED", f"{issue}는 이미 완료되었습니다. merge 스킬을 실행하세요.")
        ok()

    elif skill == "merge":
        feature = issue  # merge는 두 번째 인자가 feature
        done_files = glob.glob(os.path.join(wt_dir, "*.done"))
        if not done_files:
            error("PRECONDITION_FAILED", "완료된 워크트리가 없습니다. build가 완료된 이슈가 있어야 합니다.")
        ok({"done_issues": [os.path.basename(f).replace(".done", "") for f in done_files]})

    else:
        error("UNKNOWN_SKILL", f"알 수 없는 스킬: {skill}")

if __name__ == "__main__":
    main()
