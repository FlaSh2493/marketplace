#!/usr/bin/env python3
"""
프로젝트 루트에서 lint/type/test 명령어를 자동 탐지한다.
Usage: python3 detect_commands.py {root}
Output: JSON {apps: [{check_dir, pkg_manager, run_cmd, checks: {lint, check-types, test}}]}
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def run(cmd, cwd=None):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return r.stdout.strip(), r.stderr.strip(), r.returncode


def ok(data):
    print(json.dumps({"status": "ok", "data": data}, ensure_ascii=False))
    sys.exit(0)


def error(code, reason):
    print(json.dumps({"status": "error", "code": code, "reason": reason}, ensure_ascii=False))
    sys.exit(1)


def get_changed_files(root):
    files = set()
    out, _, _ = run(
        "MERGE_BASE=$(git merge-base HEAD "
        "\"$(git log --format='%D' HEAD | grep -oE 'origin/[^ ,]+' | head -1)\" 2>/dev/null); "
        "[ -n \"$MERGE_BASE\" ] && git diff --name-only \"$MERGE_BASE\" HEAD",
        cwd=root,
    )
    if out:
        files.update(out.splitlines())
    out, _, _ = run("git diff --name-only HEAD", cwd=root)
    if out:
        files.update(out.splitlines())
    out, _, _ = run("git ls-files --others --exclude-standard", cwd=root)
    if out:
        files.update(out.splitlines())
    return files


def find_package_json_dirs(root, changed_files):
    DOT_DIRS = {".github", ".claude", ".git", ".vscode", ".idea", "node_modules"}
    found = set()
    for f in changed_files:
        parts = Path(f).parts
        if any(p.startswith(".") or p in DOT_DIRS for p in parts):
            continue
        candidate = Path(root) / f
        search_dir = candidate.parent if candidate.is_file() else candidate
        while True:
            if (search_dir / "package.json").exists():
                found.add(str(search_dir))
                break
            if str(search_dir) == root or search_dir.parent == search_dir:
                break
            search_dir = search_dir.parent
    return found


def detect_pkg_manager(check_dir, root):
    for search in [check_dir, root]:
        p = Path(search)
        if (p / "pnpm-lock.yaml").exists():
            return "pnpm", "pnpm run"
        if (p / "yarn.lock").exists():
            return "yarn", "yarn"
        if (p / "package-lock.json").exists():
            return "npm", "npm run"
    return "npm", "npm run"


def map_scripts(check_dir):
    pkg_file = Path(check_dir) / "package.json"
    if not pkg_file.exists():
        return {}
    try:
        with open(pkg_file, encoding="utf-8") as f:
            pkg = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}

    scripts = pkg.get("scripts", {})
    mapping = {}

    for c in ["lint", "eslint"]:
        if c in scripts:
            mapping["lint"] = c
            break

    for c in ["check-types", "type-check", "typecheck", "tsc"]:
        if c in scripts:
            mapping["check-types"] = c
            break

    for c in ["test", "jest", "vitest"]:
        if c in scripts:
            mapping["test"] = c
            break

    return mapping


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root")
    args = parser.parse_args()

    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        error("NOT_A_DIR", f"디렉토리가 아닙니다: {root}")

    changed = get_changed_files(root)

    # fallback: root package.json이 있으면 루트도 후보로 추가
    if not changed or not find_package_json_dirs(root, changed):
        if (Path(root) / "package.json").exists():
            check_dirs = {root}
        else:
            ok({"apps": [], "message": "검사 대상 앱이 없습니다."})
            return
    else:
        check_dirs = find_package_json_dirs(root, changed)

    apps = []
    for check_dir in sorted(check_dirs):
        pkg_manager, run_cmd = detect_pkg_manager(check_dir, root)
        checks = map_scripts(check_dir)
        rel = os.path.relpath(check_dir, root) or "."
        apps.append({
            "check_dir": check_dir,
            "relative_path": rel,
            "pkg_manager": pkg_manager,
            "run_cmd": run_cmd,
            "checks": checks,
        })

    ok({"apps": apps})


if __name__ == "__main__":
    main()
