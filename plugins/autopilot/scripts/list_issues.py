#!/usr/bin/env python3
"""
tasks/ 디렉토리에서 이슈 문서를 스캔하여 목록을 반환한다.
Usage: python3 list_issues.py
Exit 0: ok or empty  Exit 1: error
"""
import json, re, subprocess, sys
from pathlib import Path


ISSUE_KEY_RE = re.compile(r"^([A-Z]+-[0-9]+)\.md$")


def find_git_root():
    r = subprocess.run(
        "git worktree list --porcelain",
        shell=True, capture_output=True, text=True,
    )
    for line in r.stdout.splitlines():
        if line.startswith("worktree "):
            return line[9:].strip()
    r2 = subprocess.run(
        "git rev-parse --show-toplevel",
        shell=True, capture_output=True, text=True,
    )
    return r2.stdout.strip() if r2.returncode == 0 else None


def extract_title(path: Path) -> str:
    """파일에서 첫 번째 # 헤딩 또는 frontmatter title 추출."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""

    # frontmatter title 우선
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            for line in text[3:end].splitlines():
                if line.startswith("title:"):
                    return line[6:].strip().strip('"').strip("'")

    # 첫 번째 # 헤딩
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()

    return ""


def main():
    root = find_git_root()
    if not root:
        print(json.dumps({"status": "error", "reason": "git 루트를 찾을 수 없습니다"}, ensure_ascii=False))
        sys.exit(1)

    tasks_dir = Path(root) / "tasks"
    if not tasks_dir.exists():
        print(json.dumps({"status": "error", "reason": "tasks/ 디렉토리가 없습니다"}, ensure_ascii=False))
        sys.exit(1)

    issues = []
    for f in sorted(tasks_dir.iterdir()):
        if not f.is_file():
            continue
        m = ISSUE_KEY_RE.match(f.name)
        if not m:
            continue
        key = m.group(1)
        title = extract_title(f)
        issues.append({"key": key, "title": title, "path": str(f)})

    if not issues:
        print(json.dumps({"status": "empty"}, ensure_ascii=False))
        sys.exit(0)

    lines = [f"{i['key']} — {i['title']}" if i["title"] else i["key"] for i in issues]
    display = "\n".join(lines)

    print(json.dumps(
        {"status": "ok", "data": {"issues": issues, "display": display}},
        ensure_ascii=False,
    ))
    sys.exit(0)


if __name__ == "__main__":
    main()
