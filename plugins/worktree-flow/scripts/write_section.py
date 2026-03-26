#!/usr/bin/env python3
"""
이슈 폴더의 requirements.md에 내용을 추가.
Usage: python3 write_section.py {issue} {섹션명} (내용을 stdin으로 전달)
"""
import json, os, sys, glob

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

def ok(msg):
    print(json.dumps({"status": "ok", "data": {"message": msg}}, ensure_ascii=False))
    sys.exit(0)

def error(code, reason):
    print(json.dumps({"status": "error", "code": code, "reason": reason}, ensure_ascii=False))
    sys.exit(1)

def main():
    if len(sys.argv) < 3:
        error("MISSING_ARGS", "사용법: write_section.py {issue} {섹션명}  (내용은 stdin)")

    issue = sys.argv[1]
    section = sys.argv[2]
    new_content_text = sys.stdin.read().strip()
    if not new_content_text:
        error("EMPTY_CONTENT", "내용이 비어 있습니다")

    root = find_git_root()
    if not root:
        error("GIT_ROOT_NOT_FOUND", "Git 루트를 찾을 수 없습니다")

    issue_dir = find_issue_dir(root, issue)
    if not issue_dir:
        error("ISSUE_NOT_FOUND", f"{issue} 폴더를 찾을 수 없습니다")

    req_path = os.path.join(issue_dir, "requirements.md")

    if os.path.exists(req_path):
        with open(req_path, encoding="utf-8") as f:
            content = f.read()
        content = content.rstrip() + f"\n\n## {section}\n{new_content_text}\n"
    else:
        content = f"## {section}\n{new_content_text}\n"

    with open(req_path, "w", encoding="utf-8") as f:
        f.write(content)

    ok(f"{issue} requirements.md 업데이트 완료: {req_path}")

if __name__ == "__main__":
    main()
