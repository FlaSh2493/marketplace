#!/usr/bin/env python3
"""
이슈 md 파일을 읽어 반환. 특정 섹션만 반환할 수 있음.
Usage: python3 load_issue.py {issue} [--section {섹션명}]
"""
import argparse, json, os, sys, glob, re

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

def extract_section(content, section):
    pattern = rf"(## {re.escape(section)}\n)(.*?)(?=\n## |\Z)"
    m = re.search(pattern, content, re.DOTALL)
    return m.group(2).strip() if m else None

def ok(data):
    print(json.dumps({"status": "ok", "data": data}, ensure_ascii=False, indent=2))
    sys.exit(0)

def error(code, reason):
    print(json.dumps({"status": "error", "code": code, "reason": reason}, ensure_ascii=False))
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("issue")
    parser.add_argument("--section", default=None)
    args = parser.parse_args()

    root = find_git_root()
    if not root:
        error("GIT_ROOT_NOT_FOUND", "Git 루트를 찾을 수 없습니다")

    md_path, content = find_issue_md(root, args.issue)
    if not md_path:
        error("ISSUE_NOT_FOUND", f"{args.issue}.md 파일을 찾을 수 없습니다")

    if args.section:
        section_content = extract_section(content, args.section)
        if section_content is None:
            error("SECTION_NOT_FOUND", f"## {args.section} 섹션을 찾을 수 없습니다")
        ok({"issue": args.issue, "section": args.section, "content": section_content, "md_path": md_path})
    else:
        ok({"issue": args.issue, "content": content, "md_path": md_path})

if __name__ == "__main__":
    main()
