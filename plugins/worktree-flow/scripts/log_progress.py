#!/usr/bin/env python3
"""
이슈 md 파일의 ## 진행 로그 섹션에 항목 추가.
Usage: python3 log_progress.py {issue} --step "{메시지}" | --error "{메시지}"
"""
import argparse, json, os, sys, glob, re
from datetime import datetime

def find_git_root():
    import subprocess
    r = subprocess.run("git rev-parse --git-common-dir", shell=True, capture_output=True, text=True)
    common = r.stdout.strip()
    if common:
        return os.path.abspath(os.path.join(common, ".."))
    r2 = subprocess.run("git rev-parse --show-toplevel", shell=True, capture_output=True, text=True)
    return r2.stdout.strip() or None

def find_issue_md(root, issue):
    for base in [os.path.join(root, ".docs", "task"), os.path.join(root, "docs", "task")]:
        for f in glob.glob(os.path.join(base, "**", "*.md"), recursive=True):
            with open(f, encoding="utf-8") as fh:
                content = fh.read()
                if f"issue: {issue}" in content or os.path.basename(f) == f"{issue}.md":
                    return f, content
    return None, None

def ok(msg):
    print(json.dumps({"status": "ok", "data": {"message": msg}}, ensure_ascii=False))
    sys.exit(0)

def error(code, reason):
    print(json.dumps({"status": "error", "code": code, "reason": reason}, ensure_ascii=False))
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("issue")
    parser.add_argument("--step", default=None)
    parser.add_argument("--error", default=None, dest="err")
    args = parser.parse_args()

    root = find_git_root()
    if not root:
        error("GIT_ROOT_NOT_FOUND", "Git 루트를 찾을 수 없습니다")

    md_path, content = find_issue_md(root, args.issue)
    if not md_path:
        error("ISSUE_NOT_FOUND", f"{args.issue}.md 파일을 찾을 수 없습니다")

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if args.step:
        entry = f"- ✅ [{ts}] {args.step}"
    elif args.err:
        entry = f"- ❌ [{ts}] {args.err}"
    else:
        error("MISSING_ARGS", "--step 또는 --error 중 하나가 필요합니다")

    if "## 진행 로그" in content:
        new_content = content.replace(
            "## 진행 로그",
            f"## 진행 로그\n{entry}"
        )
    else:
        new_content = content.rstrip() + f"\n\n## 진행 로그\n{entry}\n"

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    ok(f"진행 로그 기록: {entry}")

if __name__ == "__main__":
    main()
