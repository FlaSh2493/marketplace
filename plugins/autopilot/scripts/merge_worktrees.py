#!/usr/bin/env python3
"""
워크트리 브랜치를 rebase 후 fast-forward로 피처 브랜치에 통합한다.
Usage:
  python3 merge_worktrees.py {feature} --dry-run
  python3 merge_worktrees.py {feature} --branch {브랜치명}
  python3 merge_worktrees.py {feature} --branch {브랜치명} --continue
Exit 0: 성공 / Exit 1: 실패 / Exit 2: 충돌
"""
import argparse, json, os, subprocess, sys


def run(cmd, cwd=None):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return r.stdout.strip(), r.stderr.strip(), r.returncode


def find_git_root():
    common, _, rc = run("git rev-parse --git-common-dir")
    if rc == 0 and common:
        return os.path.abspath(os.path.join(common, ".."))
    out, _, rc2 = run("git rev-parse --show-toplevel")
    return out if rc2 == 0 else None



def read_autopilot_meta(worktree_path):
    meta_path = os.path.join(worktree_path, ".autopilot")
    if os.path.exists(meta_path):
        try:
            meta = json.loads(open(meta_path).read())
            # legacy: issues[] → issue 단일값
            if "issues" in meta and "issue" not in meta:
                issues_list = meta.get("issues", [])
                meta["issue"] = issues_list[0] if issues_list else ""
            return meta
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def get_autopilot_worktrees(root, feature):
    """autopilot 워크트리 목록 반환 — .autopilot 파일 존재 여부로 판별"""
    out, _, _ = run("git worktree list --porcelain", cwd=root)
    results = []
    current = {}
    for line in out.splitlines():
        if line.startswith("worktree "):
            current = {"path": line[9:]}
        elif line.startswith("branch "):
            current["branch"] = line[7:].removeprefix("refs/heads/")
        elif line == "" and current.get("path"):
            path = current["path"]
            branch = current.get("branch", "")
            # 메인 워크트리(root)는 제외, .autopilot 파일 있는 것만
            if path != root and os.path.exists(os.path.join(path, ".autopilot")):
                # feature 브랜치에서 분기했는지 확인
                base, _, rc = run(f"git merge-base '{feature}' '{branch}'", cwd=root)
                feature_tip, _, ft_rc = run(f"git rev-parse '{feature}'", cwd=root)
                if rc == 0 and ft_rc == 0 and feature_tip and base == feature_tip:
                    meta = read_autopilot_meta(path)
                    results.append({"branch": branch, "path": path, "issue": meta.get("issue", "")})
            current = {}
    return results


def count_conflicts(root, target, source):
    stash_out, _, stash_rc = run("git stash", cwd=root)
    stashed = stash_rc == 0 and "No local changes" not in stash_out

    orig, _, orig_rc = run("git rev-parse --abbrev-ref HEAD", cwd=root)
    if orig_rc != 0 or not orig:
        if stashed:
            run("git stash pop", cwd=root)
        return []

    _, _, checkout_rc = run(f"git checkout '{target}'", cwd=root)
    if checkout_rc != 0:
        if stashed:
            run("git stash pop", cwd=root)
        return []

    _, _, code = run(f"git merge --squash '{source}'", cwd=root)
    conflicts = []
    if code != 0:
        out, _, _ = run("git diff --name-only --diff-filter=U", cwd=root)
        if out:
            conflicts = [f for f in out.split("\n") if f.strip()]
    run("git reset --hard HEAD", cwd=root)
    run(f"git checkout '{orig}'", cwd=root)
    if stashed:
        run("git stash pop", cwd=root)
    return conflicts


def get_wip_count(root, branch, feature):
    base, _, _ = run(f"git merge-base '{feature}' '{branch}'", cwd=root)
    if not base:
        return 0
    out, _, _ = run(f"git log {base}..{branch} --oneline", cwd=root)
    return sum(1 for line in out.split("\n") if "wip(" in line.lower())


def error(code, reason):
    print(json.dumps({"status": "error", "code": code, "reason": reason}, ensure_ascii=False))
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("feature")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--branch", default=None)
    parser.add_argument("--continue", action="store_true", dest="cont")
    args = parser.parse_args()

    root = find_git_root()
    if not root:
        error("GIT_ROOT_NOT_FOUND", "Git 루트를 찾을 수 없습니다")

    if args.dry_run:
        branches = get_autopilot_worktrees(root, args.feature)
        if not branches:
            error("NO_BRANCHES", f"'{args.feature}' 기준 autopilot 워크트리가 없습니다")
        matrix = []
        for b in branches:
            conflicts = count_conflicts(root, args.feature, b["branch"])
            wip_count = get_wip_count(root, b["branch"], args.feature)
            matrix.append({
                "branch": b["branch"],
                "path": b["path"],
                "issue": b["issue"],
                "conflict_files": conflicts,
                "conflict_count": len(conflicts),
                "wip_count": wip_count,
            })
        order = sorted(matrix, key=lambda x: x["conflict_count"])
        print(json.dumps({
            "status": "ok",
            "data": {"feature": args.feature, "merge_order": order, "total": len(order)}
        }, ensure_ascii=False, indent=2))
        return

    # 단일 브랜치 merge
    if args.branch:
        branch = args.branch

        _, _, branch_rc = run(f"git rev-parse --verify '{branch}'", cwd=root)
        if branch_rc != 0:
            error("BRANCH_NOT_FOUND", f"브랜치 '{branch}'가 존재하지 않습니다")

        if args.cont:
            _, err, code = run("git merge --continue --no-edit", cwd=root)
            if code != 0:
                out, _, _ = run("git diff --name-only --diff-filter=U", cwd=root)
                conflicts = [f for f in out.split("\n") if f.strip()]
                if not conflicts:
                    error("MERGE_CONTINUE_FAILED", f"merge --continue 실패: {err}")
                print(json.dumps({
                    "status": "conflict",
                    "branch": branch,
                    "conflicts": conflicts,
                }, ensure_ascii=False, indent=2))
                sys.exit(2)
        else:
            _, err, co_rc = run(f"git checkout '{args.feature}'", cwd=root)
            if co_rc != 0:
                error("CHECKOUT_FAILED", f"'{args.feature}' 체크아웃 실패: {err}")

            _, err, code = run(f"git merge --no-edit '{branch}'", cwd=root)
            if code != 0:
                out, _, _ = run("git diff --name-only --diff-filter=U", cwd=root)
                conflicts = [f for f in out.split("\n") if f.strip()]
                if not conflicts:
                    error("MERGE_FAILED", f"머지 실패: {err}")
                print(json.dumps({
                    "status": "conflict",
                    "branch": branch,
                    "conflicts": conflicts,
                }, ensure_ascii=False, indent=2))
                sys.exit(2)

        print(json.dumps({
            "status": "ok",
            "data": {"branch": branch},
        }, ensure_ascii=False, indent=2))
        return

    error("MISSING_ARGS", "--branch 또는 --dry-run 필요")


if __name__ == "__main__":
    main()
