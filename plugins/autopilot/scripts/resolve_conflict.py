#!/usr/bin/env python3
"""
충돌 파일 단일 해결.
Usage: python3 resolve_conflict.py {file} {feature|base}
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

def ok(msg):
    print(json.dumps({"status": "ok", "data": {"message": msg}}, ensure_ascii=False))
    sys.exit(0)

def error(code, reason):
    print(json.dumps({"status": "error", "code": code, "reason": reason}, ensure_ascii=False))
    sys.exit(1)

def main():
    if len(sys.argv) < 3:
        error("MISSING_ARGS", "사용법: resolve_conflict.py {file} {feature|base}")

    filepath, choice = sys.argv[1], sys.argv[2].lower()
    if choice not in ("feature", "base"):
        error("INVALID_CHOICE", "선택값은 'feature' 또는 'base' 이어야 합니다")

    root = find_git_root()
    if not root:
        error("GIT_ROOT_NOT_FOUND", "Git 루트를 찾을 수 없습니다")

    quoted = shlex.quote(filepath)
    if choice == "feature":
        # 머지 들어오는 쪽(theirs) 선택
        _, err, code = run(f"git checkout --theirs -- {quoted}", cwd=root)
    else:
        # 베이스(ours) 선택
        _, err, code = run(f"git checkout --ours -- {quoted}", cwd=root)

    if code != 0:
        error("RESOLVE_FAILED", f"충돌 해결 실패: {err}")

    run(f"git add -- {quoted}", cwd=root)
    ok(f"{filepath} 충돌 해결 완료 ({choice} 선택)")

if __name__ == "__main__":
    main()
