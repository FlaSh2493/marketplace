#!/usr/bin/env python3
"""
이슈 md 파일을 읽어 반환. 특정 섹션만 반환할 수 있음.
Usage: python3 load_issue.py {issue} [--section {섹션명}] [--sections 섹션1,섹션2]
"""
import argparse, json, os, sys, glob, re

def assert_worktree():
    """CWD가 git worktree 안인지 검증."""
    git_dir = os.path.join(os.getcwd(), ".git")
    if not os.path.isfile(git_dir):
        error("NOT_WORKTREE", "워크트리가 아닙니다. ensure_worktree.py 실행 후 EnterWorktree로 진입하세요.")

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
        # 폴더 구조: {base}/**/{issue}/{issue}.md 우선 탐색
        for f in glob.glob(os.path.join(base, "**", issue, f"{issue}.md"), recursive=True):
            with open(f, encoding="utf-8") as fh:
                return f, fh.read()
        # fallback: 단일 파일 구조
        for f in glob.glob(os.path.join(base, "**", "*.md"), recursive=True):
            with open(f, encoding="utf-8") as fh:
                content = fh.read()
                if f"jira: {issue}" in content or os.path.basename(f) == f"{issue}.md":
                    return f, content
    return None, None

def extract_section(content, section):
    pattern = rf"(## {re.escape(section)}\n)(.*?)(?=\n## |\Z)"
    m = re.search(pattern, content, re.DOTALL)
    return m.group(2).strip() if m else None

def extract_sections(content, sections):
    parts = []
    for s in sections:
        text = extract_section(content, s)
        if text:
            parts.append(f"## {s}\n{text}")
    return "\n\n".join(parts) if parts else None

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
    parser.add_argument("--sections", default=None, help="콤마 구분 복수 섹션. 예: 설명,메타데이터")
    args = parser.parse_args()

    assert_worktree()

    root = find_git_root()
    if not root:
        error("GIT_ROOT_NOT_FOUND", "Git 루트를 찾을 수 없습니다")

    md_path, content = find_issue_md(root, args.issue)
    if not md_path:
        error("ISSUE_NOT_FOUND", f"{args.issue}.md 파일을 찾을 수 없습니다")

    if args.sections:
        names = [s.strip() for s in args.sections.split(",")]
        combined = extract_sections(content, names)
        if not combined:
            error("SECTION_NOT_FOUND", f"섹션을 찾을 수 없습니다: {args.sections}")
        ok({"issue": args.issue, "sections": names, "content": combined, "md_path": md_path})
    elif args.section:
        section_content = extract_section(content, args.section)
        if section_content is None:
            error("SECTION_NOT_FOUND", f"## {args.section} 섹션을 찾을 수 없습니다")
        ok({"issue": args.issue, "section": args.section, "content": section_content, "md_path": md_path})
    else:
        ok({"issue": args.issue, "content": content, "md_path": md_path})

if __name__ == "__main__":
    main()
