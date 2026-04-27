#!/usr/bin/env python3
"""
변경 파일 경로에서 도메인 라벨을 추론하고, GitHub에서 존재 여부를 확인한다.
Usage: python3 infer_labels.py {worktree_path} {base_branch}
Exit 0: ok (data.labels[])
Exit 1: error
"""
import argparse, json, os, subprocess, sys


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
    parser.add_argument("worktree_path")
    parser.add_argument("base_branch")
    args = parser.parse_args()

    worktree_path = os.path.abspath(args.worktree_path)
    base = args.base_branch

    # 1. 변경 파일 목록 추출
    out, _, rc = run(f"git diff --name-only origin/{base}...HEAD", cwd=worktree_path)
    if rc != 0 or not out:
        # fallback: 최근 1개 커밋 (신규 브랜치인 경우 등)
        out, _, _ = run("git diff --name-only HEAD~1 HEAD", cwd=worktree_path)

    changed_files = out.splitlines() if out else []

    # 2. 도메인 라벨 후보 추출
    SKIP_DIRS = {"src", "app", "lib", "packages", "apps", "components", "pages",
                 "utils", "hooks", "types", "styles", "tests", "test", "__tests__",
                 ".github", ".claude", "node_modules", "dist", "build", "plugins"}

    domain_candidates = set()
    for f in changed_files:
        parts = f.split("/")
        # 최상위부터 의미 있는 폴더 탐색
        for part in parts[:-1]:
            if part and part not in SKIP_DIRS and not part.startswith("."):
                domain_candidates.add(part)
                break

    # 3. GitHub 라벨 목록 조회 (실제 존재하는 것만 필터링하기 위함)
    out, _, rc = run(
        "gh label list --limit 300 --json name -q '.[].name'",
        cwd=worktree_path
    )

    available_labels = set(out.splitlines()) if rc == 0 and out else set()

    # 4. 확정 라벨 구성
    labels = []
    
    # base_branch 라벨은 기본으로 추가 (존재할 경우)
    if base in available_labels:
        labels.append(base)
    
    # 추론된 도메인 라벨 중 실제 존재하는 것만 추가
    matched_domains = [d for d in domain_candidates if d in available_labels]
    
    # 너무 많으면 오히려 노이즈가 될 수 있으므로 상위 2개까지만 제한 (필요시 조정)
    labels.extend(matched_domains[:2])

    ok({"labels": list(dict.fromkeys(labels))}) # 중복 제거


if __name__ == "__main__":
    main()
