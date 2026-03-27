#!/usr/bin/env python3
"""
현재 머지 충돌 파일 목록과 diff 출력.
Usage: python3 show_conflicts.py
"""
import json, os, shlex, sys, subprocess

def run(cmd, cwd=None):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return r.stdout.strip(), r.stderr.strip(), r.returncode

def find_git_root():
    common, _, _ = run("git rev-parse --git-common-dir")
    if common:
        return os.path.abspath(os.path.join(common, ".."))
    out, _, _ = run("git rev-parse --show-toplevel")
    return out or None

def ok(data):
    print(json.dumps({"status": "ok", "data": data}, ensure_ascii=False, indent=2))
    sys.exit(0)

def error(code, reason):
    print(json.dumps({"status": "error", "code": code, "reason": reason}, ensure_ascii=False))
    sys.exit(1)

def main():
    root = find_git_root()
    if not root:
        error("GIT_ROOT_NOT_FOUND", "Git 루트를 찾을 수 없습니다")

    conflict_files_out, _, rc = run("git diff --name-only --diff-filter=U", cwd=root)
    if not conflict_files_out:
        ok({"conflicts": []})
        return

    files = [f for f in conflict_files_out.split("\n") if f.strip()]
    conflicts = []
    for f in files:
        diff_out, _, _ = run(f"git diff {shlex.quote(f)}", cwd=root)
        conflicts.append({"file": f, "diff": diff_out})

    ok({"conflicts": conflicts, "count": len(conflicts)})

if __name__ == "__main__":
    main()
