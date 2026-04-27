#!/usr/bin/env python3
"""
워크트리에서 검사 가능한 앱 환경을 탐지한다.
Usage: python3 detect_env.py {wt_root} [--install] [--all]
  --install  node_modules 없으면 자동 설치
  --all      변경 파일 기준이 아닌 전체 package.json 탐색
Exit 0: ok (data.apps[])
Exit 1: error
"""
import argparse, json, os, subprocess, sys
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


def find_git_root(wt_root):
    out, _, rc = run("git rev-parse --git-common-dir", cwd=wt_root)
    if rc == 0 and out:
        return os.path.abspath(os.path.join(wt_root, out, ".."))
    out, _, rc = run("git rev-parse --show-toplevel", cwd=wt_root)
    return out if rc == 0 else None


def get_changed_files(wt_root):
    """merge-base 기준 변경 파일 + 미커밋 변경 파일 목록"""
    files = set()

    # merge-base 기준 커밋된 변경
    merge_base_cmd = (
        "MERGE_BASE=$(git merge-base HEAD "
        "\"$(git log --format='%D' HEAD | grep -oE 'origin/[^ ,]+' | head -1)\" 2>/dev/null); "
        "[ -n \"$MERGE_BASE\" ] && git diff --name-only \"$MERGE_BASE\" HEAD"
    )
    out, _, _ = run(merge_base_cmd, cwd=wt_root)
    if out:
        files.update(out.splitlines())

    # 미커밋 변경 (staged + unstaged)
    out, _, _ = run("git diff --name-only HEAD", cwd=wt_root)
    if out:
        files.update(out.splitlines())

    # untracked
    out, _, _ = run("git ls-files --others --exclude-standard", cwd=wt_root)
    if out:
        files.update(out.splitlines())

    return files


def find_package_json_dirs(wt_root, changed_files):
    """변경 파일에서 가장 가까운 package.json 디렉토리를 역추적"""
    DOT_DIRS = {".github", ".claude", ".git", ".vscode", ".idea", "node_modules"}
    found = set()

    for f in changed_files:
        # dot-디렉토리 제외
        parts = Path(f).parts
        if any(p.startswith(".") or p in DOT_DIRS for p in parts):
            continue

        # 파일의 디렉토리부터 wt_root까지 역추적
        candidate = Path(wt_root) / f
        search_dir = candidate.parent if candidate.is_file() else candidate
        while True:
            pkg = search_dir / "package.json"
            if pkg.exists():
                found.add(str(search_dir))
                break
            if str(search_dir) == wt_root or search_dir.parent == search_dir:
                break
            search_dir = search_dir.parent

    return found


def find_all_package_json_dirs(wt_root):
    """전체 package.json 탐색 (--all 모드)"""
    DOT_DIRS = {"node_modules", ".git", ".github", ".claude"}
    found = set()
    for root, dirs, files in os.walk(wt_root):
        dirs[:] = [d for d in dirs if d not in DOT_DIRS and not d.startswith(".")]
        if "package.json" in files:
            found.add(root)
    return found


def detect_pkg_manager(check_dir, wt_root):
    """lock 파일로 패키지매니저 판별. check_dir → wt_root 순으로 탐색"""
    for search in [check_dir, wt_root]:
        p = Path(search)
        if (p / "pnpm-lock.yaml").exists():
            return "pnpm", "pnpm run", "pnpm install"
        if (p / "yarn.lock").exists():
            return "yarn", "yarn run", "yarn install"
        if (p / "package-lock.json").exists():
            return "npm", "npm run", "npm install"
    return "npm", "npm run", "npm install"


def map_scripts(check_dir):
    """package.json scripts에서 검사 명령어 매핑"""
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

    lint_candidates = ["lint", "eslint"]
    for c in lint_candidates:
        if c in scripts:
            mapping["lint"] = c
            break

    type_candidates = ["check-types", "type-check", "typecheck", "tsc"]
    for c in type_candidates:
        if c in scripts:
            mapping["check-types"] = c
            break

    test_candidates = ["test", "jest", "vitest"]
    for c in test_candidates:
        if c in scripts:
            mapping["test"] = c
            break

    return mapping


def check_node_modules(check_dir, wt_root):
    """node_modules 존재 여부 확인 (check_dir 또는 wt_root hoisted)"""
    return (
        (Path(check_dir) / "node_modules").exists()
        or (Path(wt_root) / "node_modules").exists()
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("wt_root")
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--all", action="store_true", dest="scan_all")
    args = parser.parse_args()

    wt_root = os.path.abspath(args.wt_root)
    if not os.path.isdir(wt_root):
        error("NOT_A_DIR", f"디렉토리가 아닙니다: {wt_root}")

    # 앱 디렉토리 탐지
    if args.scan_all:
        check_dirs = find_all_package_json_dirs(wt_root)
    else:
        changed = get_changed_files(wt_root)
        if not changed:
            ok({"apps": [], "message": "변경된 파일이 없습니다."})
        check_dirs = find_package_json_dirs(wt_root, changed)

    if not check_dirs:
        ok({"apps": [], "message": "검사 대상 앱이 없습니다."})

    # 각 앱 환경 탐지
    install_done = False
    apps = []

    for check_dir in sorted(check_dirs):
        pkg_manager, run_cmd, install_cmd = detect_pkg_manager(check_dir, wt_root)
        checks = map_scripts(check_dir)
        has_nm = check_node_modules(check_dir, wt_root)

        # --install 시 node_modules 없으면 루트에서 1회만 설치
        if args.install and not has_nm and not install_done:
            _, err, rc = run(install_cmd, cwd=wt_root)
            if rc != 0:
                error("INSTALL_FAILED", f"패키지 설치 실패: {err}")
            has_nm = True
            install_done = True

        rel = os.path.relpath(check_dir, wt_root) or "."

        apps.append({
            "check_dir": check_dir,
            "relative_path": rel,
            "pkg_manager": pkg_manager,
            "run_cmd": run_cmd,
            "install_cmd": install_cmd,
            "has_node_modules": has_nm,
            "checks": checks,
        })

    ok({"apps": apps})


if __name__ == "__main__":
    main()
