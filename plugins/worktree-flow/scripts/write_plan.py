#!/usr/bin/env python3
"""
이슈 폴더에 plan-N.md 파일을 순번으로 생성.
Usage: python3 write_plan.py {issue} (플랜 내용을 stdin으로 전달)
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

def find_issue_dir(root, issue):
    for base in [os.path.join(root, ".docs", "task"), os.path.join(root, "docs", "task")]:
        for d in glob.glob(os.path.join(base, "**", issue), recursive=True):
            if os.path.isdir(d):
                return d
    return None

def next_plan_index(issue_dir):
    existing = glob.glob(os.path.join(issue_dir, "plan-*.md"))
    indices = []
    for f in existing:
        m = re.search(r"plan-(\d+)\.md$", f)
        if m:
            indices.append(int(m.group(1)))
    return max(indices) + 1 if indices else 1

def ok(msg):
    print(json.dumps({"status": "ok", "data": {"message": msg}}, ensure_ascii=False))
    sys.exit(0)

def error(code, reason):
    print(json.dumps({"status": "error", "code": code, "reason": reason}, ensure_ascii=False))
    sys.exit(1)

def main():
    if len(sys.argv) < 2:
        error("MISSING_ARGS", "사용법: write_plan.py {issue}  (내용은 stdin)")

    issue = sys.argv[1]
    plan_content = sys.stdin.read().strip()
    if not plan_content:
        error("EMPTY_PLAN", "플랜 내용이 비어 있습니다")

    root = find_git_root()
    if not root:
        error("GIT_ROOT_NOT_FOUND", "Git 루트를 찾을 수 없습니다")

    issue_dir = find_issue_dir(root, issue)
    if not issue_dir:
        error("ISSUE_NOT_FOUND", f"{issue} 폴더를 찾을 수 없습니다")

    index = next_plan_index(issue_dir)
    file_path = os.path.join(issue_dir, f"plan-{index}.md")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(plan_content)

    ok(f"{issue} plan-{index}.md 저장 완료: {file_path}")

if __name__ == "__main__":
    main()
