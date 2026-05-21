#!/usr/bin/env python3
"""
변경 파일 경로에서 도메인 라벨을 추론하고 GitHub 존재 여부를 확인한다.
Usage: python3 infer_labels.py {root} {base_branch}
Output: JSON {status, data: {labels: []}}
"""
import argparse
import json
import os
import subprocess
import sys


def run(cmd, cwd=None):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return r.stdout.strip(), r.stderr.strip(), r.returncode


def ok(data):
    print(json.dumps({"status": "ok", "data": data}, ensure_ascii=False))
    sys.exit(0)


def error(code, reason):
    print(json.dumps({"status": "error", "code": code, "reason": reason}, ensure_ascii=False))
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root")
    parser.add_argument("base_branch")
    args = parser.parse_args()

    root = os.path.abspath(args.root)
    base = args.base_branch

    # 변경 파일 목록
    out, _, rc = run(f"git diff --name-only origin/{base}...HEAD", cwd=root)
    if rc != 0 or not out:
        out, _, _ = run("git diff --name-only HEAD~1 HEAD", cwd=root)

    changed_files = out.splitlines() if out else []

    SKIP_DIRS = {
        "src", "app", "lib", "packages", "apps", "components", "pages",
        "utils", "hooks", "types", "styles", "tests", "test", "__tests__",
        ".github", ".claude", "node_modules", "dist", "build", "plugins",
    }

    domain_candidates = set()
    for f in changed_files:
        parts = f.split("/")
        for part in parts[:-1]:
            if part and part not in SKIP_DIRS and not part.startswith("."):
                domain_candidates.add(part)
                break

    # GitHub 라벨 목록
    out, _, rc = run("gh label list --limit 300 --json name -q '.[].name'", cwd=root)
    available_labels = set(out.splitlines()) if rc == 0 and out else set()

    labels = []
    if base in available_labels:
        labels.append(base)

    matched = [d for d in domain_candidates if d in available_labels]
    labels.extend(matched[:2])

    ok({"labels": list(dict.fromkeys(labels))})


if __name__ == "__main__":
    main()
