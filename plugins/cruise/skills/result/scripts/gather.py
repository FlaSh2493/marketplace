#!/usr/bin/env python3
"""
result.md 작성용 결정적 필드 수집기.

~/Documents/tasks/<KEY>/ 의 형제 산출물 frontmatter에서 스칼라 필드를 긁어
result.md frontmatter에 그대로 복사할 값들을 JSON으로 출력한다.
에이전트는 본문 학습(잘된 점/실패/결정/사용 기술)과 technologies 판단만 하면 된다.

Usage: python3 gather.py <KEY>
Output: JSON {key, key_source, summary, branch, repo, base_branch, base_source,
              pr_url, pr_number, commits_count, outcome,
              issue_keys, artifacts_present, created_existing, now}
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# commit.md/pr.md 는 폐지 — PR·커밋은 GitHub(gh)에서 파생한다.
ARTIFACTS = ["task", "plan", "summary", "merge", "review", "result"]


def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return r.stdout.strip(), r.returncode


def gh_pr_info(repo: str, branch: str) -> dict:
    """gh로 branch에 연결된 PR을 조회. GitHub이 PR·커밋의 단일 진실 원천.

    PR이 없거나 gh 미설치/미인증 등으로 실패하면 {} 반환 (호출측이 스킵)."""
    if not repo or not branch:
        return {}
    out, rc = run(
        f"gh pr list --repo {repo} --head {branch} --state all "
        f"--json number,url,state,commits --limit 1"
    )
    if rc != 0 or not out:
        return {}
    try:
        arr = json.loads(out)
    except Exception:
        return {}
    return arr[0] if arr else {}


def load_context():
    """동일 플러그인의 context.py 를 현재 repo CWD에서 실행해 live git 정보 획득."""
    ctx_py = Path(__file__).resolve().parents[3] / "scripts" / "context.py"
    try:
        out, rc = run(f'python3 "{ctx_py}"')
        return json.loads(out) if rc == 0 and out else {}
    except Exception:
        return {}


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

    summary = pick("summary", ["task", "plan", "summary"])
    # branch/repo/key_source: cruise 산출물에서 (jsync task.md에는 없음)
    cruise_order = ["plan", "summary", "merge", "review", "task"]
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

    # repo: 산출물 frontmatter 우선, 없으면 이 task 체크아웃일 때 live git에서 폴백.
    if not repo and in_task_checkout:
        repo = ctx.get("repo") or ""

    if in_task_checkout:
        base_branch = ctx.get("base_branch") or pick("base_branch", ["summary"])
        base_source = ctx.get("base_source") or "unknown"
    else:
        # 이 task의 체크아웃이 아니면 live git은 무관 → 추측하지 않는다.
        base_branch = pick("base_branch", ["summary"])
        base_source = "unknown"

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
    # PR·커밋 정보는 GitHub(gh)에서 직접 파생 (pr.md/commit.md 산출물 폐지).
    # gh 실패/PR 없음 시 pr_info == {} → 값이 비고 커밋 수는 git log로 폴백.
    pr_info = gh_pr_info(repo, branch)
    pr_url = pr_info.get("url") or ""
    pr_number = pr_info.get("number") if isinstance(pr_info.get("number"), int) else None
    pr_state = pr_info.get("state") or ""
    if isinstance(pr_info.get("commits"), list):
        commits_count = len(pr_info["commits"])
    elif in_task_checkout and base_branch:
        cnt_out, _ = run(f"git rev-list --count {base_branch}..HEAD")
        commits_count = int(cnt_out) if cnt_out.isdigit() else 0
    else:
        commits_count = 0

    # status: cruise 산출물 중 cancelled/failed 가 있으면 반영
    statuses = {fms.get(n, {}).get("status") for n in cruise_order}

    # outcome 도출
    if "cancelled" in statuses:
        outcome = "abandoned"
    elif (tasks_dir / "merge.md").exists() or pr_state == "MERGED":
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
        "issue_keys": issue_keys,
        "artifacts_present": present,
        "created_existing": created_existing,
        "now": now,
    }
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
