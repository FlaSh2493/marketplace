#!/usr/bin/env python3
"""
이슈 요구사항 기반 코드베이스 영향 범위 분석.
Claude가 플랜 작성 시 참고할 파일 목록을 반환.
Usage: python3 analyze_scope.py {issue}
"""
import json, os, sys, glob, re, subprocess

def find_git_root():
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
                if f"jira: {issue}" in content or os.path.basename(f) == f"{issue}.md":
                    return content
    return None

def extract_keywords(content):
    """요구사항에서 파일명/컴포넌트명으로 쓰일 법한 키워드 추출"""
    # 백틱으로 감싸진 경로/파일명
    backtick = re.findall(r"`([^`]+\.[a-zA-Z]+)`", content)
    # src/, pages/, components/, hooks/, api/ 패턴
    paths = re.findall(r"(?:src|pages|components|hooks|api|utils|types|stores)/[\w/.-]+", content)
    return list(set(backtick + paths))

def find_related_files(root, keywords):
    """키워드와 관련된 실제 파일 탐색"""
    src_dirs = ["src", "app", "lib", "components", "pages", "hooks", "api"]
    all_files = []
    for d in src_dirs:
        base = os.path.join(root, d)
        if os.path.exists(base):
            all_files += glob.glob(os.path.join(base, "**", "*.*"), recursive=True)

    related = []
    for kw in keywords:
        name = os.path.basename(kw).lower()
        for f in all_files:
            if name and name in os.path.basename(f).lower():
                rel = os.path.relpath(f, root)
                if rel not in related:
                    related.append(rel)
    return related[:20]  # 최대 20개

def ok(data):
    print(json.dumps({"status": "ok", "data": data}, ensure_ascii=False, indent=2))
    sys.exit(0)

def error(code, reason):
    print(json.dumps({"status": "error", "code": code, "reason": reason}, ensure_ascii=False))
    sys.exit(1)

def main():
    if len(sys.argv) < 2:
        error("MISSING_ARGS", "사용법: analyze_scope.py {issue}")

    issue = sys.argv[1]
    root = find_git_root()
    if not root:
        error("GIT_ROOT_NOT_FOUND", "Git 루트를 찾을 수 없습니다")

    content = find_issue_md(root, issue)
    if not content:
        error("ISSUE_NOT_FOUND", f"{issue}.md 파일을 찾을 수 없습니다")

    keywords = extract_keywords(content)
    affected_files = find_related_files(root, keywords)

    ok({
        "issue": issue,
        "keywords": keywords,
        "affected_files": affected_files,
        "note": "Claude가 플랜 작성 시 이 파일들을 읽어 현재 구조를 파악하세요"
    })

if __name__ == "__main__":
    main()
