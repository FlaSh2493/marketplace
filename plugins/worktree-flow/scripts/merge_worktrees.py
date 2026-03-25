#!/usr/bin/env python3
"""
워크트리 브랜치들을 피처 브랜치에 머지한다.
Usage: python3 merge_worktrees.py {피처브랜치} [--dry-run] [--abort] [--continue]
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

def get_wt_paths(root):
    out, _, _ = run("git worktree list --porcelain", cwd=root)
    paths, cur_path = {}, None
    for line in out.split("\n"):
        if line.startswith("worktree "): cur_path = line.split(" ", 1)[1]
        elif line.startswith("branch ") and cur_path:
            paths[line.split(" ", 1)[1].replace("refs/heads/", "")] = cur_path
            cur_path = None
    return paths

def count_conflicts(root, target, source):
    orig, _, _ = run("git rev-parse --abbrev-ref HEAD", cwd=root)
    run(f"git checkout '{target}'", cwd=root)
    _, _, code = run(f"git merge --no-commit --no-ff '{source}'", cwd=root)
    conflicts = []
    if code != 0:
        out, _, _ = run("git diff --name-only --diff-filter=U", cwd=root)
        if out: conflicts = [f for f in out.split("\n") if f.strip()]
    run("git merge --abort 2>/dev/null || true", cwd=root)
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

def conflict(merged_so_far, failed, remaining, conflicts):
    print(json.dumps({
        "status": "conflict",
        "merged_so_far": merged_so_far,
        "failed": {"issue": failed, "conflicts": conflicts},
        "remaining": remaining
    }, ensure_ascii=False, indent=2))
    sys.exit(2)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("feature")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--abort", action="store_true")
    parser.add_argument("--continue", action="store_true", dest="cont")
    parser.add_argument("--root", default=None)
    args = parser.parse_args()

    root = args.root or find_git_root()
    if not root:
        error("GIT_ROOT_NOT_FOUND", "Git 루트를 찾을 수 없습니다")

    if args.abort:
        run(f"git checkout '{args.feature}'", cwd=root)
        run("git merge --abort 2>/dev/null || true", cwd=root)
        print(json.dumps({"status": "ok", "data": {"aborted": True}}, ensure_ascii=False))
        return

    if args.cont:
        # 충돌 해결 후 머지 계속
        _, err, code = run("git commit --no-edit", cwd=root)
        if code != 0:
            error("CONTINUE_FAILED", f"머지 계속 실패: {err}")
        print(json.dumps({"status": "ok", "data": {"continued": True}}, ensure_ascii=False))
        return

    branches = get_wt_branches(root, args.feature)
    if not branches:
        error("NO_BRANCHES", f"'{args.feature}'의 워크트리 브랜치가 없습니다")

    # 충돌 예측 및 순서 결정 (충돌 적은 순)
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
            "data": {
                "feature": args.feature,
                "merge_order": order,
                "total": len(order)
            }
        }, ensure_ascii=False, indent=2))
        return

    # 미커밋 변경사항 확인
    wt_paths = get_wt_paths(root)
    dirty = []
    for b in branches:
        path = wt_paths.get(b["branch"])
        if path:
            out, _, _ = run("git status --porcelain", cwd=path)
            if out: dirty.append(b["issue"])
    if dirty:
        error("DIRTY_WORKTREES", f"미커밋 변경사항 있음: {', '.join(dirty)}. WIP 커밋 후 재시도하세요.")

    # 머지 실행
    run(f"git checkout '{args.feature}'", cwd=root)
    merged = []
    for item in order:
        _, err, code = run(
            f"git merge --no-ff '{item['branch']}' -m 'merge({item[\"issue\"]}): worktree integration'",
            cwd=root
        )
        if code != 0:
            out, _, _ = run("git diff --name-only --diff-filter=U", cwd=root)
            conflicts = [f for f in out.split("\n") if f.strip()]
            remaining = [x["issue"] for x in order
                         if x["issue"] not in [m["issue"] for m in merged] and x["issue"] != item["issue"]]
            conflict([m["issue"] for m in merged], item["issue"], remaining, conflicts)
        merged.append(item)

    print(json.dumps({
        "status": "ok",
        "data": {
            "feature": args.feature,
            "merged": [m["issue"] for m in merged]
        }
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
