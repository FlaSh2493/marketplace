#!/usr/bin/env python3
"""
워크트리 브랜치들을 피처 브랜치에 일반 머지한다.
머지 전 태그를 남기고, 완료 후 워크트리와 브랜치를 삭제한다.
Usage: python3 merge_worktrees.py {피처브랜치} [--dry-run] [--abort]
"""
import argparse, json, subprocess, sys

def run(cmd, cwd=None):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return r.stdout.strip(), r.stderr.strip(), r.returncode

def find_git_root():
    out, _, _ = run("git rev-parse --show-toplevel")
    return out or None

def get_wt_branches(root, feature):
    out, _, _ = run("git branch --list", cwd=root)
    if not out: return []
    prefix = f"{feature}--wt-"
    return [{"branch": b.strip().lstrip("* "), "name": b.strip().lstrip("* ")[len(prefix):]}
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
    run(f"git checkout '{target}'", cwd=root)
    _, _, code = run(f"git merge --no-commit --no-ff '{source}'", cwd=root)
    conflicts = []
    if code != 0:
        out, _, _ = run("git diff --name-only --diff-filter=U", cwd=root)
        if out: conflicts = [f for f in out.split("\n") if f.strip()]
    run("git merge --abort", cwd=root)
    return conflicts

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("feature")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--abort", action="store_true")
    parser.add_argument("--root", default=None)
    args = parser.parse_args()

    root = args.root or find_git_root()
    if not root:
        print(json.dumps({"error": "Git 루트를 찾을 수 없습니다"})); sys.exit(1)

    if args.abort:
        run(f"git checkout '{args.feature}'", cwd=root)
        run("git merge --abort", cwd=root)
        print(json.dumps({"aborted": True})); return

    branches = get_wt_branches(root, args.feature)
    if not branches:
        print(json.dumps({"error": f"'{args.feature}'의 워크트리 브랜치가 없습니다"})); sys.exit(1)

    wt_paths = get_wt_paths(root)

    # 미커밋 검사
    dirty = []
    for b in branches:
        path = wt_paths.get(b["branch"])
        if path:
            out, _, _ = run("git status --porcelain", cwd=path)
            if out: dirty.append({"branch": b["branch"], "changes": len(out.split("\n"))})
    if dirty:
        print(json.dumps({"error": "미커밋 변경사항 있음", "dirty": dirty}, ensure_ascii=False, indent=2)); sys.exit(1)

    # 태그 생성
    feat_short = args.feature.split("/")[-1] if "/" in args.feature else args.feature
    tags = []
    for b in branches:
        tag = f"wt/{feat_short}/{b['name']}"
        run(f"git tag -d '{tag}'", cwd=root)
        run(f"git tag '{tag}' '{b['branch']}'", cwd=root)
        tags.append(tag)

    # 충돌 분석 + 순서
    orig, _, _ = run("git rev-parse --abbrev-ref HEAD", cwd=root)
    matrix = []
    for b in branches:
        c = count_conflicts(root, args.feature, b["branch"])
        matrix.append({"name": b["name"], "branch": b["branch"], "conflict_files": c, "conflict_count": len(c)})
    order = sorted(matrix, key=lambda x: x["conflict_count"])

    if args.dry_run:
        run(f"git checkout '{orig}'", cwd=root)
        print(json.dumps({"dry_run": True, "feature": args.feature, "merge_order": order, "tags": tags}, ensure_ascii=False, indent=2)); return

    # 머지
    run(f"git checkout '{args.feature}'", cwd=root)
    merged = []
    for item in order:
        _, _, code = run(f"git merge --no-ff '{item['branch']}' -m 'Merge {item['name']}'", cwd=root)
        if code != 0:
            out, _, _ = run("git diff --name-only --diff-filter=U", cwd=root)
            conflicts = out.split("\n") if out else []
            print(json.dumps({
                "status": "conflict", "merged_so_far": [m["name"] for m in merged],
                "failed": {"name": item["name"], "conflicts": conflicts},
                "remaining": [x["name"] for x in order if x["name"] not in [m["name"] for m in merged] and x["name"] != item["name"]],
                "hint": f"충돌 해결 후: git add . && git commit"
            }, ensure_ascii=False, indent=2)); return
        merged.append(item)

    # 정리
    cleaned = []
    for b in branches:
        path = wt_paths.get(b["branch"])
        if path: run(f"git worktree remove '{path}' --force", cwd=root)
        run(f"git branch -D '{b['branch']}'", cwd=root)
        cleaned.append(b["name"])

    print(json.dumps({
        "status": "success", "feature": args.feature,
        "merged": [m["name"] for m in merged], "tags": tags, "cleaned": cleaned
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
