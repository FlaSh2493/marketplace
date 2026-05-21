#!/usr/bin/env python3
"""
~/Documents/tasks/{KEY}/task.md 섹션 로드.
Usage: python3 load_issue.py --key KEY [--sections sec1,sec2,...]
Exit 0: 섹션 내용 stdout
Exit 1: task.md 없음
Exit 2: 요청 섹션 없음
"""
import argparse
import re
import sys
from pathlib import Path


def strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4:].lstrip("\n")
    return text


def extract_sections(body: str) -> dict[str, str]:
    pattern = re.compile(r"^#{1,3} (.+)$", re.MULTILINE)
    matches = list(pattern.finditer(body))
    result = {}
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        result[title] = body[start:end].strip()
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--key", required=True)
    parser.add_argument("--sections", default="")
    args = parser.parse_args()

    task_path = Path.home() / "Documents" / "tasks" / args.key / "task.md"
    if not task_path.exists():
        print(f"task.md not found: {task_path}", file=sys.stderr)
        sys.exit(1)

    text = task_path.read_text(encoding="utf-8")
    body = strip_frontmatter(text)

    if not args.sections:
        print(body)
        sys.exit(0)

    requested = [s.strip() for s in args.sections.split(",") if s.strip()]
    all_sections = extract_sections(body)

    found = []
    for req in requested:
        for title, content in all_sections.items():
            if req.lower() in title.lower():
                found.append(f"## {title}\n\n{content}")
                break

    if not found:
        print(f"sections not found: {requested}", file=sys.stderr)
        sys.exit(2)

    print("\n\n".join(found))


if __name__ == "__main__":
    main()
