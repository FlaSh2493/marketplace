#!/usr/bin/env python3
"""
result.md 작성용 결정적 필드 수집기.

~/Documents/tasks/<KEY>/ 의 형제 산출물 frontmatter에서 스칼라 필드를 긁어
result.md frontmatter에 그대로 복사할 값들을 JSON으로 출력한다.
에이전트는 본문 학습(잘된 점/실패/결정/사용 기술)과 technologies 판단만 하면 된다.

Usage: python3 gather.py <KEY>
Output: JSON {key, key_source, summary, branch, repo, base_branch, base_source,
              pr_url, pr_number, commits_count, outcome,
              feature, feature_trusted, worktree, issue_keys,
              artifacts_present, created_existing, now}
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ARTIFACTS = ["task", "plan", "build", "summary", "check",
             "commit", "merge", "pr", "review", "result"]

# feature 도출: base가 base군이면 독립(branch), 아니면 umbrella(base_branch)
BASE_BRANCHES = {"develop", "main", "master", "staging", "stg", "stag", "dev"}
# base_source 가 이 집합이면 신뢰(feature 동결), 아니면 추측 → 미동결
TRUSTED_BASE_SOURCES = {"pr", "upstream", "reflog"}


def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.stdout.strip(), r.returncode


def load_context():
    """동일 플러그인의 context.py 를 현재 repo CWD에서 실행해 live git 정보 획득."""
    ctx_py = Path(__file__).resolve().parents[3] / "scripts" / "context.py"
    try:
        out, rc = run(f'python3 "{ctx_py}"')
        return json.loads(out) if rc == 0 and out else {}
    except Exception:
        return {}


def is_base_branch(name: str) -> bool:
    return name in BASE_BRANCHES or name.startswith("release/")


def slugify(text: str) -> str:
    text = (text or "").strip().lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def read_frontmatter(path: Path) -> dict:
    """--- ... --- 사이의 최상위 스칼라 라인만 파싱 (중첩/리스트는 무시)."""
    if not path.exists():
        return {}
    fm = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return {}
    if not lines or lines[0].strip() != "---":
        return {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        # 들여쓰기 있는 라인(중첩 값)은 건너뜀
        if line[:1] in (" ", "\t"):
            continue
        m = re.match(r"^([A-Za-z0-9_]+):\s*(.*)$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        # 따옴표 제거
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        fm[key] = val
    return fm


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "USAGE: gather.py <KEY>"}))
        sys.exit(1)
    key = sys.argv[1]
    tasks_root = Path(os.environ.get("CRUISE_TASKS_ROOT",
                                     str(Path.home() / "Documents" / "tasks")))
    tasks_dir = tasks_root / key

    fms = {name: read_frontmatter(tasks_dir / f"{name}.md") for name in ARTIFACTS}
    present = [name for name in ARTIFACTS
              if name != "result" and (tasks_dir / f"{name}.md").exists()]

    # summary: task.md 우선, 없으면 cruise 산출물에서
    def pick(field, order):
        for name in order:
            v = fms.get(name, {}).get(field)
            if v:
                return v
        return ""

    summary = pick("summary", ["task", "plan", "build", "summary",
                               "commit", "pr"])
    # branch/repo/key_source: cruise 산출물에서 (jsync task.md에는 없음)
    cruise_order = ["plan", "build", "summary", "check", "commit",
                    "merge", "pr", "review", "task"]
    repo = pick("repo", cruise_order)
    key_source = pick("key_source", cruise_order) or "slug"

    # branch: frontmatter 기록값(작업 시점 권위)을 우선.
    fm_branch = pick("branch", cruise_order)
    ctx = load_context()
    ctx_branch = ctx.get("branch") or ""
    branch = fm_branch or ctx_branch

    # 현재 CWD가 이 task의 체크아웃인가? (live git이 이 task에 대한 것인지)
    # frontmatter branch가 있고 live branch와 일치할 때만 live 신호를 신뢰.
    # branch 기록이 없으면(인라인 등) live를 채택.
    in_task_checkout = bool(ctx_branch) and (not fm_branch or fm_branch == ctx_branch)

    if in_task_checkout:
        base_branch = ctx.get("base_branch") or pick("base_branch", ["summary", "pr"])
        base_source = ctx.get("base_source") or "unknown"
        is_worktree = bool(ctx.get("is_worktree"))
        worktree_name = ctx.get("worktree_name") or ""
    else:
        # 이 task의 체크아웃이 아니면 live git은 무관 → 추측하지 않는다.
        base_branch = pick("base_branch", ["summary", "pr"])
        base_source = "unknown"      # 신뢰 불가 → feature 미동결
        is_worktree = False
        worktree_name = ""

    # feature 동결 (추측 금지): 이 task 체크아웃 + 신뢰 base일 때만.
    feature = ""
    feature_trusted = in_task_checkout and base_source in TRUSTED_BASE_SOURCES
    if feature_trusted and base_branch:
        feature = base_branch if not is_base_branch(base_branch) else branch
    feature_slug = slugify(feature) if feature else ""

    # worktree: 체크아웃일 때만 의미. 아니면 unknown.
    worktree = ({"kind": "worktree" if is_worktree else "branch", "name": worktree_name}
                if in_task_checkout else {"kind": "", "name": ""})

    # issue_keys: branch + (체크아웃이면 커밋 제목)에서 추출
    seen, issue_keys = set(), []
    for k in re.findall(r"[A-Z]+-\d+", branch or ""):
        if k not in seen:
            seen.add(k); issue_keys.append(k)
    if in_task_checkout and base_branch:
        logs, _ = run(f'git log {base_branch}..HEAD --format=%s')
        for line in logs.splitlines():
            for k in re.findall(r"[A-Z]+-\d+", line):
                if k not in seen:
                    seen.add(k); issue_keys.append(k)
    pr_url = fms.get("pr", {}).get("pr_url", "")
    pr_number_raw = fms.get("pr", {}).get("pr_number", "")
    pr_number = int(pr_number_raw) if pr_number_raw.isdigit() else None
    commits_count_raw = fms.get("commit", {}).get("commits_count", "")
    commits_count = int(commits_count_raw) if commits_count_raw.isdigit() else 0

    # status: cruise 산출물 중 cancelled/failed 가 있으면 반영
    statuses = {fms.get(n, {}).get("status") for n in cruise_order}

    # outcome 도출
    if "cancelled" in statuses:
        outcome = "abandoned"
    elif (tasks_dir / "merge.md").exists():
        outcome = "merged"
    elif pr_url or pr_number:
        outcome = "shipped"
    else:
        outcome = "in-progress"

    created_existing = fms.get("result", {}).get("created", "")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    result = {
        "key": key,
        "key_source": key_source,
        "summary": summary,
        "branch": branch,
        "repo": repo,
        "base_branch": base_branch,
        "base_source": base_source,
        "pr_url": pr_url,
        "pr_number": pr_number,
        "commits_count": commits_count,
        "outcome": outcome,
        "feature": feature,            # "" = unassigned (추측 안 함)
        "feature_slug": feature_slug,
        "feature_trusted": feature_trusted,
        "worktree": worktree,          # {kind: worktree|branch, name}
        "issue_keys": issue_keys,
        "artifacts_present": present,
        "created_existing": created_existing,
        "now": now,
    }
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
