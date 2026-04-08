#!/usr/bin/env python3
"""
변경 파일 경로에서 도메인 라벨을 추론하고, GitHub에서 존재 여부를 확인한다.
Usage: python3 infer_labels.py {worktree_path} {owner_repo}
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
    parser.add_argument("owner_repo")
    args = parser.parse_args()

    worktree_path = os.path.abspath(args.worktree_path)
    owner_repo = args.owner_repo

    # 변경 파일 목록 (origin/develop 기준)
    out, _, rc = run("git diff --name-only origin/develop...HEAD", cwd=worktree_path)
    if rc != 0 or not out:
        out, _, _ = run("git diff --name-only HEAD~1 HEAD", cwd=worktree_path)

    changed_files = out.splitlines() if out else []

    # 도메인 라벨 후보 추출 (최상위 의미 있는 폴더명)
    SKIP_DIRS = {"src", "app", "lib", "packages", "apps", "components", "pages",
                 "utils", "hooks", "types", "styles", "tests", "test", "__tests__",
                 ".github", ".claude", "node_modules", "dist", "build"}

    domain_candidates = set()
    for f in changed_files:
        parts = f.split("/")
        for part in parts[:-1]:  # 파일명 제외
            if part and part not in SKIP_DIRS and not part.startswith("."):
                domain_candidates.add(part)
                break

    # GitHub 라벨 목록 조회
    out, err, rc = run(
        f"gh label list --limit 200 --json name -q '.[].name'",
        cwd=worktree_path
    )

    if rc != 0:
        # 권한 없거나 네트워크 오류 시 develop만 반환
        ok({"labels": ["develop"]})

    available_labels = set(out.splitlines()) if out else set()

    # 확정 라벨 구성
    labels = []
    if "develop" in available_labels:
        labels.append("develop")

    # 도메인 라벨 (available_labels에 있는 것만)
    matched_domains = [d for d in domain_candidates if d in available_labels]
    if len(matched_domains) == 1:
        labels.append(matched_domains[0])
    # 여러 개 매칭되면 생략 (애매한 경우)

    ok({"labels": labels})


if __name__ == "__main__":
    main()
