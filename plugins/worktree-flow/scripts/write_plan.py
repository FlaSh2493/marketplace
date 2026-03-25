#!/usr/bin/env python3
"""
이슈 md 파일의 ## 플랜 섹션을 작성/교체.
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
    if len(sys.argv) < 2:
        error("MISSING_ARGS", "사용법: write_plan.py {issue}  (내용은 stdin)")

    issue = sys.argv[1]
    plan_content = sys.stdin.read().strip()
    if not plan_content:
        error("EMPTY_PLAN", "플랜 내용이 비어 있습니다")

    root = find_git_root()
    if not root:
        error("GIT_ROOT_NOT_FOUND", "Git 루트를 찾을 수 없습니다")

    md_path, content = find_issue_md(root, issue)
    if not md_path:
        error("ISSUE_NOT_FOUND", f"{issue}.md 파일을 찾을 수 없습니다")

    section_block = f"## 플랜\n{plan_content}\n"

    if "## 플랜" in content:
        # 기존 섹션 교체
        new_content = re.sub(
            r"## 플랜\n.*?(?=\n## |\Z)",
            section_block,
            content,
            flags=re.DOTALL
        )
    else:
        # 진행 로그 섹션 전에 삽입, 없으면 파일 끝에 추가
        if "## 진행 로그" in content:
            new_content = content.replace("## 진행 로그", f"{section_block}\n## 진행 로그")
        else:
            new_content = content.rstrip() + f"\n\n{section_block}"

    # frontmatter status 업데이트
    new_content = re.sub(r"(status:\s*)\w+", r"\1PLANNED", new_content)

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    ok(f"{issue} 플랜 저장 완료: {md_path}")

if __name__ == "__main__":
    main()
