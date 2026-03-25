#!/usr/bin/env python3
"""
워크트리 브랜치들을 squash merge로 피처 브랜치에 통합한다.
워크트리 브랜치 히스토리는 건드리지 않음.
Usage:
  python3 merge_worktrees.py {feature} --dry-run
  python3 merge_worktrees.py {feature} --issue {이슈키} --message "{메시지}"
  python3 merge_worktrees.py {feature} --issue {이슈키} --continue
Exit 0: 성공 / Exit 1: 실패 / Exit 2: 충돌
"""
import argparse, json, os, subprocess, sys

def run(cmd, cwd=None):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return r.stdout.strip(), r.stderr.strip(), r.returncode

def find_git_root():
    common, _, _ = run("git rev-parse --git-common-dir")
    if common:
        return os.path.abspath(os.path.join(common, ".."))
    out, _, _ = run("git rev-parse --show-toplevel")
    return out or None

def get_wt_branches(root, feature):
    out, _, _ = run("git branch --list", cwd=root)
    if not out: return []
    prefix = f"{feature}--wt-"
    return [{"branch": b.strip().lstrip("* "), "issue": b.strip().lstrip("* ")[len(prefix):]}
            for b in out.split("\n") if b.strip().lstrip("* ").startswith(prefix)]

def count_conflicts(root, target, source):
    orig, _, _ = run("git rev-parse --abbrev-ref HEAD", cwd=root)
    run(f"git checkout '{target}'", cwd=root)
    _, _, code = run(f"git merge --squash '{source}'", cwd=root)
    conflicts = []
    if code != 0:
        out, _, _ = run("git diff --name-only --diff-filter=U", cwd=root)
        if out: conflicts = [f for f in out.split("\n") if f.strip()]
    run("git reset --hard HEAD 2>/dev/null || true", cwd=root)
    run(f"git checkout '{orig}'", cwd=root)
    return conflicts

def get_wip_count(root, branch, feature):
    base, _, _ = run(f"git merge-base '{feature}' '{branch}'", cwd=root)
    if not base: return 0
    out, _, _ = run(f"git log {base}..{branch} --oneline", cwd=root)
    return sum(1 for line in out.split("\n") if "WIP(" in line)

def error(code, reason):
    print(json.dumps({"status": "error", "code": code, "reason": reason}, ensure_ascii=False))
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("feature")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--issue", default=None)
    parser.add_argument("--message", default=None)
    parser.add_argument("--continue", action="store_true", dest="cont")
    args = parser.parse_args()

    root = find_git_root()
    if not root:
        error("GIT_ROOT_NOT_FOUND", "Git 루트를 찾을 수 없습니다")

    # 충돌 해결 후 계속
    if args.cont and args.issue:
        _, err, code = run(f"git commit -m '{args.message or args.issue} (conflict resolved)'", cwd=root)
        if code != 0:
            error("CONTINUE_FAILED", f"커밋 실패: {err}")
        print(json.dumps({"status": "ok", "data": {"continued": True}}, ensure_ascii=False))
        return

    branches = get_wt_branches(root, args.feature)
    if not branches:
        error("NO_BRANCHES", f"'{args.feature}'의 워크트리 브랜치가 없습니다")

    # 충돌 예측 및 순서 결정
    matrix = []
    for b in branches:
        conflicts = count_conflicts(root, args.feature, b["branch"])
        wip_count = get_wip_count(root, b["branch"], args.feature)
        matrix.append({
            "issue": b["issue"],
            "branch": b["branch"],
            "conflict_files": conflicts,
            "conflict_count": len(conflicts),
            "wip_count": wip_count
        })
    order = sorted(matrix, key=lambda x: x["conflict_count"])

    if args.dry_run:
        print(json.dumps({
            "status": "ok",
            "data": {"feature": args.feature, "merge_order": order, "total": len(order)}
        }, ensure_ascii=False, indent=2))
        return

    # 단일 이슈 squash merge
    if args.issue:
        branch = f"{args.feature}--wt-{args.issue}"
        message = args.message or f"feat({args.issue}): squash merge"

        run(f"git checkout '{args.feature}'", cwd=root)
        _, err, code = run(f"git merge --squash '{branch}'", cwd=root)
        if code != 0:
            out, _, _ = run("git diff --name-only --diff-filter=U", cwd=root)
            conflicts = [f for f in out.split("\n") if f.strip()]
            print(json.dumps({
                "status": "conflict",
                "issue": args.issue,
                "conflicts": conflicts
            }, ensure_ascii=False, indent=2))
            sys.exit(2)

        _, err, code = run(f"git commit -m '{message}'", cwd=root)
        if code != 0:
            error("COMMIT_FAILED", f"커밋 실패: {err}")

        print(json.dumps({
            "status": "ok",
            "data": {"issue": args.issue, "branch": branch}
        }, ensure_ascii=False, indent=2))
        return

    error("MISSING_ARGS", "--issue 또는 --dry-run 필요")

if __name__ == "__main__":
    main()
