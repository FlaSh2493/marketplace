#!/usr/bin/env python3
"""
git status + diff 분석해 도메인/타입별 커밋 그룹을 제안한다.
Usage: python3 group_changes.py {root}
Output: JSON {groups: [{label, type, scope, files: []}]}
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


def run(cmd, cwd=None):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return r.stdout.strip(), r.stderr.strip(), r.returncode


def classify_file(path: str) -> tuple[str, str]:
    """(type, scope) 추론"""
    parts = Path(path).parts

    # type 추론
    file_type = "feat"
    name = Path(path).name.lower()
    if any(x in name for x in ["test", "spec", ".test.", ".spec."]):
        file_type = "test"
    elif any(x in name for x in [".md", "readme", "changelog"]):
        file_type = "docs"
    elif any(x in name for x in ["config", ".json", ".yaml", ".yml", ".toml", ".env"]):
        file_type = "chore"
    elif any(x in name for x in ["style", ".css", ".scss", ".less"]):
        file_type = "style"

    # scope 추론 (의미있는 첫 번째 디렉토리)
    SKIP = {"src", "app", "lib", "packages", "apps", "components", "pages",
            "utils", "hooks", "types", "styles", "tests", "__tests__",
            ".github", ".claude", "node_modules", "dist", "build", "plugins"}
    scope = ""
    for part in parts[:-1]:
        if part and part not in SKIP and not part.startswith("."):
            scope = part
            break

    return file_type, scope


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root")
    args = parser.parse_args()

    root = os.path.abspath(args.root)

    # 미커밋 변경 파일 수집
    out, _, _ = run("git status --porcelain", cwd=root)
    if not out:
        print(json.dumps({"groups": [], "message": "커밋할 변경사항이 없습니다."}))
        sys.exit(0)

    # 상태별 파일 분류
    new_files = []
    modified_files = []
    deleted_files = []

    for line in out.splitlines():
        if len(line) < 3:
            continue
        status = line[:2].strip()
        filepath = line[3:].strip()
        if status in ("??",):
            new_files.append(filepath)
        elif status in ("D", "DD", "AD"):
            deleted_files.append(filepath)
        else:
            modified_files.append(filepath)

    all_files = new_files + modified_files + deleted_files

    # 그룹핑: (type, scope) 기준 묶기
    groups_map: dict[tuple, list] = {}
    for f in all_files:
        ft, scope = classify_file(f)
        key_tuple = (ft, scope)
        groups_map.setdefault(key_tuple, []).append(f)

    # 그룹 정렬: feat > fix > refactor > chore > docs > style > test
    ORDER = ["feat", "fix", "refactor", "chore", "docs", "style", "test"]

    def sort_key(item):
        t, _ = item[0]
        return (ORDER.index(t) if t in ORDER else 99, item[0][1])

    groups = []
    for (ftype, scope), files in sorted(groups_map.items(), key=sort_key):
        label = f"{ftype}({scope})" if scope else ftype
        groups.append({
            "label": label,
            "type": ftype,
            "scope": scope,
            "files": sorted(files),
        })

    print(json.dumps({"groups": groups}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
