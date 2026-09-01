#!/usr/bin/env python3
"""
CWD → 컨텍스트 JSON 출력. 모든 cruise 스킬의 진입점.

Usage: python3 context.py
Output: JSON {root, branch, key, key_source, unit, units,
              issue_dir, task_dir,
              task_path, task_md_exists, plan_md_exists, summary_md_exists,
              commit_md_exists,
              pr_md_exists, review_md_exists,
              has_uncommitted, has_pr, pr_number?, repo}
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import tasks_root  # noqa: E402


def run(cmd, cwd=None):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return r.stdout.strip(), r.stderr.strip(), r.returncode


def slug(branch: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "-", branch).strip("-").lower()


def unit_from_branch(branch: str, key: str, key_source: str) -> str:
    """브랜치 → 작업 단위 디렉토리명. 이슈 키를 뺀 나머지를 slug 로 쓴다.

        IET-8412-auth         → auth
        feature/IET-8412-auth → feature-auth
        IET-8412              → default   (나머지가 없음)

    key_source == "slug" 이면 이슈 키가 없어 디렉토리명이 이미 브랜치 단위로 유일하므로
    항상 "default" 다."""
    if key_source != "issue":
        return "default"
    return slug(branch.replace(key, " ")) or "default"


def main():
    # 1. Git root + branch
    root, _, rc = run("git rev-parse --show-toplevel")
    if rc != 0:
        print(json.dumps({"error": "NOT_A_GIT_REPO"}))
        sys.exit(1)

    branch, _, _ = run("git rev-parse --abbrev-ref HEAD", cwd=root)

    # 2. KEY
    m = re.search(r"[A-Z]+-\d+", branch)
    if m:
        key = m.group(0)
        key_source = "issue"
    else:
        key = slug(branch)
        key_source = "slug"

    # 2b. 작업 단위 = 브랜치 (v12).
    # 한 이슈를 여러 브랜치·워크트리로 나눠 진행하면 단위도 그만큼 생긴다. 쪼갤지 말지는
    # cruise 가 판단하지 않는다 — 사람이 브랜치를 딴 행위가 곧 분리 선언이다.
    # 브랜치가 하나면 단위도 하나이므로 기존과 동일하게 동작한다(경로만 한 단계 깊어진다).
    unit = unit_from_branch(branch, key, key_source)

    # 3. base_branch (우선순위 체인)
    base_branch = None
    base_source = "unknown"

    # 3-1. gh pr view
    out, _, rc = run("gh pr view --json baseRefName -q .baseRefName", cwd=root)
    if rc == 0 and out:
        base_branch = out
        base_source = "pr"

    # 3-2. upstream
    if not base_branch:
        out, _, rc = run("git rev-parse --abbrev-ref @{upstream}", cwd=root)
        if rc == 0 and out and "/" in out:
            base_branch = out.split("/", 1)[1]
            base_source = "upstream"

    # 3-3. reflog "Created from"
    if not base_branch:
        out, _, _ = run(f"git reflog show --format='%gs' {branch}", cwd=root)
        for line in out.splitlines():
            m2 = re.search(r"[Cc]reated from (.+)", line)
            if m2:
                base_branch = m2.group(1).strip()
                base_source = "reflog"
                break

    # 3-4. heuristic: 후보 풀 중 commit 수 최소
    if not base_branch:
        candidates = ["main", "develop", "master"]
        out, _, _ = run("git branch -r --format='%(refname:short)'", cwd=root)
        for b in out.splitlines():
            b = b.strip()
            if b.startswith("origin/release/"):
                cand = b.replace("origin/", "")
                if cand not in candidates:
                    candidates.append(cand)

        best_count = None
        best_cand = None
        for cand in candidates:
            out, _, rc = run(f"git rev-list --count {cand}..HEAD", cwd=root)
            if rc == 0 and out.isdigit():
                count = int(out)
                if best_count is None or count < best_count:
                    best_count = count
                    best_cand = cand

        if best_cand:
            base_branch = best_cand
            base_source = "heuristic"

    # 4. cruise artifact paths (v12 — 2계층)
    #   issue_dir  = tasks_root/<KEY>          이슈 레벨. task.md·raw.json·meta.json·attachments
    #   task_dir   = tasks_root/<KEY>/<unit>   작업 단위 레벨. plan/summary/review/result·상태 파일
    # 산출물 경로는 전부 task_dir 기준이고, task.md 만 issue_dir 에 있다(단위끼리 공유).
    issue_path = tasks_root() / key
    task_dir = issue_path / unit   # 생성하지 않는다 — context.py 는 조회 전용.
    task_md = issue_path / "task.md"

    task_path = str(task_md)
    task_md_exists = task_md.exists()
    plan_md_exists = (task_dir / "plan.md").exists()
    summary_md_exists = (task_dir / "summary.md").exists()
    commit_md_exists = (task_dir / "commit.md").exists()
    pr_md_exists = (task_dir / "pr.md").exists()
    review_md_exists = (task_dir / "review.md").exists()

    # 같은 이슈의 다른 단위들 — 소비자가 "이 이슈가 몇 갈래로 진행 중인지" 알 수 있도록.
    siblings = sorted(
        p.name for p in issue_path.iterdir()
        if p.is_dir() and p.name not in ("attachments",) and not p.name.endswith(".archive")
    ) if issue_path.is_dir() else []

    # 5. uncommitted
    out, _, _ = run("git status --porcelain", cwd=root)
    has_uncommitted = bool(out)

    # 6. PR
    out, _, rc = run("gh pr view --json number -q .number", cwd=root)
    has_pr = rc == 0 and bool(out)
    pr_number = int(out) if has_pr and out.isdigit() else None

    # 7. repo
    out, _, rc = run("gh repo view --json nameWithOwner -q .nameWithOwner", cwd=root)
    repo = out if rc == 0 else ""

    # 8. worktree 감지 (linked worktree면 git-common-dir != <root>/.git)
    common_dir, _, _ = run("git rev-parse --git-common-dir", cwd=root)
    common_path = Path(common_dir) if common_dir else None
    if common_path is not None and not common_path.is_absolute():
        common_path = (Path(root) / common_path).resolve()
    main_git = (Path(root) / ".git").resolve()
    is_worktree = bool(common_path) and common_path != main_git
    worktree_name = Path(root).name if is_worktree else ""

    result = {
        "root": root,
        "branch": branch,
        "key": key,
        "key_source": key_source,
        "base_branch": base_branch,
        "base_source": base_source,
        "has_uncommitted": has_uncommitted,
        "has_pr": has_pr,
        "repo": repo,
        "is_worktree": is_worktree,
        "worktree_name": worktree_name,
        "unit": unit,
        "units": siblings,
    }
    result["issue_dir"] = str(issue_path)
    result["task_dir"] = str(task_dir)
    result["task_path"] = task_path
    result["task_md_exists"] = task_md_exists
    result["plan_md_exists"] = plan_md_exists
    result["summary_md_exists"] = summary_md_exists
    result["commit_md_exists"] = commit_md_exists
    result["pr_md_exists"] = pr_md_exists
    result["review_md_exists"] = review_md_exists
    if pr_number is not None:
        result["pr_number"] = pr_number

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
